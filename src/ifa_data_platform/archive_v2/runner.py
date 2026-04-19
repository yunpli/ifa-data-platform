from __future__ import annotations

import json
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta, date, time
from decimal import Decimal
from typing import Any

from sqlalchemy import text

from ifa_data_platform.archive_v2.business_contracts import (
    ANNOUNCEMENTS_SUSPICIOUS_NEAR_CAP,
    BUSINESS_DAILY_CONTRACTS,
    INVESTOR_QA_SUSPICIOUS_LOW_ROWS,
    LIMIT_LIST_EXCHANGES,
    LIMIT_LIST_LIMIT_TYPES,
    NEWS_SOURCE_BUNDLE,
    NEWS_SUSPICIOUS_NEAR_CAP,
    RESEARCH_REPORT_SUSPICIOUS_NEAR_CAP,
    RESEARCH_REPORT_TYPES,
    SECTOR_INDEX_TYPES,
    assert_archive_namespace,
    stable_hash,
)
from ifa_data_platform.archive_v2.db import engine, ensure_schema
from ifa_data_platform.archive_v2.operator import build_repair_state
from ifa_data_platform.archive_v2.profile import ArchiveProfile, load_profile, validate_profile
from ifa_data_platform.tushare.client import TushareClient, get_tushare_client

NON_COMPLETED_STATUSES = {'partial', 'incomplete', 'retry_needed', 'missing'}
REPAIR_QUEUE_PENDING_STATUSES = {'pending', 'retry_needed', 'claimed'}
TARGET_POLICY_ALL = 'all'
TARGET_POLICY_GAPS = 'gaps'
TARGET_POLICY_REPAIR = 'repair'

DAILY_TRADABLE_FAMILIES = ['equity_daily', 'index_daily', 'etf_daily', 'non_equity_daily', 'macro_daily']
DAILY_BUSINESS_FAMILIES = [
    'announcements_daily', 'news_daily', 'research_reports_daily', 'investor_qa_daily',
    'dragon_tiger_daily', 'limit_up_detail_daily', 'limit_up_down_status_daily', 'sector_performance_daily',
]
DAILY_SIGNAL_FAMILIES: list[str] = []
INTRADAY_TRADABLE_FAMILIES = {
    '60m': ['equity_60m', 'etf_60m', 'index_60m', 'futures_60m', 'commodity_60m', 'precious_metal_60m'],
    '15m': ['equity_15m', 'etf_15m', 'index_15m', 'futures_15m', 'commodity_15m', 'precious_metal_15m'],
    '1m': ['equity_1m', 'etf_1m', 'index_1m', 'futures_1m', 'commodity_1m', 'precious_metal_1m'],
}

DIRECT_DEST_TABLES = {
    'equity_daily': 'ifa_archive_equity_daily',
    'index_daily': 'ifa_archive_index_daily',
    'etf_daily': 'ifa_archive_etf_daily',
    'non_equity_daily': 'ifa_archive_non_equity_daily',
    'macro_daily': 'ifa_archive_macro_daily',
}

ALL_FAMILY_META: dict[str, dict[str, Any]] = {
    'equity_daily': {'frequency': 'daily', 'bucket': 'tradable', 'implemented': True, 'kind': 'tushare_daily'},
    'index_daily': {'frequency': 'daily', 'bucket': 'tradable', 'implemented': True, 'kind': 'history_daily', 'source_table': 'index_daily_bar_history', 'date_col': 'trade_date', 'dest_table': 'ifa_archive_index_daily', 'key_col': 'ts_code', 'note': 'index daily archive written from retained final history truth'},
    'etf_daily': {'frequency': 'daily', 'bucket': 'tradable', 'implemented': True, 'kind': 'tushare_etf'},
    'non_equity_daily': {'frequency': 'daily', 'bucket': 'tradable', 'implemented': True, 'kind': 'tushare_non_equity'},
    'macro_daily': {'frequency': 'daily', 'bucket': 'tradable', 'implemented': True, 'kind': 'macro_daily'},
    'announcements_daily': {'frequency': 'daily', 'bucket': 'business', 'implemented': True, 'kind': 'business_contract_daily', 'dest_table': 'ifa_archive_announcements_daily', 'note': 'family-specific anns_d contract with cap-aware fallback'},
    'news_daily': {'frequency': 'daily', 'bucket': 'business', 'implemented': True, 'kind': 'business_contract_daily', 'dest_table': 'ifa_archive_news_daily', 'note': 'family-specific news time-window/source bundle contract'},
    'research_reports_daily': {'frequency': 'daily', 'bucket': 'business', 'implemented': True, 'kind': 'business_contract_daily', 'dest_table': 'ifa_archive_research_reports_daily', 'note': 'family-specific research_report shard contract'},
    'investor_qa_daily': {'frequency': 'daily', 'bucket': 'business', 'implemented': True, 'kind': 'business_contract_daily', 'dest_table': 'ifa_archive_investor_qa_daily', 'note': 'family-specific SH+SZ QA contract with pub_date fallback'},
    'dragon_tiger_daily': {'frequency': 'daily', 'bucket': 'business', 'implemented': True, 'kind': 'business_contract_daily', 'dest_table': 'ifa_archive_dragon_tiger_daily', 'note': 'family-specific top_list direct contract with reason-aware identity'},
    'limit_up_detail_daily': {'frequency': 'daily', 'bucket': 'business', 'implemented': True, 'kind': 'business_contract_daily', 'dest_table': 'ifa_archive_limit_up_detail_daily', 'note': 'family-specific limit_list_d shard contract'},
    'limit_up_down_status_daily': {'frequency': 'daily', 'bucket': 'business', 'implemented': True, 'kind': 'business_contract_daily', 'dest_table': 'ifa_archive_limit_up_down_status_daily', 'note': 'family-specific limit_list_d aggregate contract'},
    'sector_performance_daily': {'frequency': 'daily', 'bucket': 'business', 'implemented': True, 'kind': 'business_contract_daily', 'dest_table': 'ifa_archive_sector_performance_daily', 'note': 'family-specific ths_index + ths_daily coverage contract'},
    'highfreq_event_stream_daily': {'frequency': 'daily', 'bucket': 'signal', 'implemented': True, 'kind': 'event_daily', 'source_table': 'highfreq_event_stream_working', 'date_col': 'event_time', 'date_via_ts': True, 'dest_table': 'ifa_archive_highfreq_event_stream_daily', 'time_col': 'event_time', 'default_enabled': False, 'support_status': 'derived_not_archived_by_default', 'raw_source_family': 'highfreq_event_stream_raw', 'note': 'derived highfreq daily family removed from the default Archive V2 truth model; preserve upstream raw truth first and derive later'},
    'highfreq_limit_event_stream_daily': {'frequency': 'daily', 'bucket': 'signal', 'implemented': True, 'kind': 'event_daily', 'source_table': 'highfreq_limit_event_stream_working', 'date_col': 'trade_time', 'date_via_ts': True, 'dest_table': 'ifa_archive_highfreq_limit_event_stream_daily', 'time_col': 'trade_time', 'default_enabled': False, 'support_status': 'derived_not_archived_by_default', 'raw_source_family': 'close_auction_raw+intraday_raw', 'note': 'derived highfreq daily family removed from the default Archive V2 truth model; keep only as temporary derived retention until raw truth coverage is complete'},
    'highfreq_sector_breadth_daily': {'frequency': 'daily', 'bucket': 'signal', 'implemented': True, 'kind': 'snapshot_daily', 'source_table': 'highfreq_sector_breadth_working', 'date_col': 'trade_time', 'date_via_ts': True, 'dest_table': 'ifa_archive_highfreq_sector_breadth_daily', 'keys': ['sector_code'], 'time_col': 'trade_time', 'default_enabled': False, 'support_status': 'derived_not_archived_by_default', 'raw_source_family': 'stock_intraday_raw+grouping_raw+auction_raw', 'note': 'derived highfreq daily family removed from the default Archive V2 truth model; move toward raw-first/derive-later when raw truth coverage is complete'},
    'highfreq_sector_heat_daily': {'frequency': 'daily', 'bucket': 'signal', 'implemented': True, 'kind': 'snapshot_daily', 'source_table': 'highfreq_sector_heat_working', 'date_col': 'trade_time', 'date_via_ts': True, 'dest_table': 'ifa_archive_highfreq_sector_heat_daily', 'keys': ['sector_code'], 'time_col': 'trade_time', 'default_enabled': False, 'support_status': 'derived_not_archived_by_default', 'raw_source_family': 'grouping_raw+market_context_raw', 'note': 'derived highfreq daily family removed from the default Archive V2 truth model; keep only as temporary derived retention while raw grouping truth remains insufficient'},
    'highfreq_leader_candidate_daily': {'frequency': 'daily', 'bucket': 'signal', 'implemented': True, 'kind': 'snapshot_daily', 'source_table': 'highfreq_leader_candidate_working', 'date_col': 'trade_time', 'date_via_ts': True, 'dest_table': 'ifa_archive_highfreq_leader_candidate_daily', 'keys': ['symbol'], 'time_col': 'trade_time', 'default_enabled': False, 'support_status': 'derived_not_archived_by_default', 'raw_source_family': 'stock_intraday_raw', 'note': 'derived highfreq daily family removed from the default Archive V2 truth model; move toward raw-first/derive-later when stock intraday raw archive coverage is complete'},
    'highfreq_intraday_signal_state_daily': {'frequency': 'daily', 'bucket': 'signal', 'implemented': True, 'kind': 'snapshot_daily', 'source_table': 'highfreq_intraday_signal_state_working', 'date_col': 'trade_time', 'date_via_ts': True, 'dest_table': 'ifa_archive_highfreq_intraday_signal_state_daily', 'keys': ['scope_key'], 'time_col': 'trade_time', 'default_enabled': False, 'support_status': 'derived_not_archived_by_default', 'raw_source_family': 'stock_intraday_raw+auction_raw+grouping_raw', 'note': 'derived highfreq daily family removed from the default Archive V2 truth model; keep only as temporary derived retention until raw truth coverage is complete'},
    'highfreq_signal_daily': {'frequency': 'daily', 'bucket': 'signal', 'implemented': False, 'kind': 'not_implemented', 'note': 'legacy placeholder only; superseded by explicit highfreq Archive V2 families'},
    'generic_structured_output_daily': {'frequency': 'daily', 'bucket': 'signal', 'implemented': False, 'kind': 'not_implemented', 'note': 'generic structured-output catch-all is not archive-v2 worthy because it collapses unrelated finalized truths into one lossy bucket'},
    'equity_60m': {'frequency': '60m', 'bucket': 'tradable', 'implemented': True, 'kind': 'intraday_bars', 'source_table': 'stock_60min_history', 'source_time_col': 'trade_time', 'source_date_expr': 'date(trade_time)', 'source_symbol_col': 'ts_code', 'dest_table': 'ifa_archive_equity_60m', 'archive_key_col': 'ts_code', 'instrument_key': 'ts_code', 'default_enabled': False, 'support_status': 'supported_later', 'source_endpoint': 'stk_mins', 'note': 'valid true-source intraday family kept as later-enable/default-off support; current path still needs source-first correction'},
    'etf_60m': {'frequency': '60m', 'bucket': 'tradable', 'implemented': True, 'kind': 'intraday_bars', 'dest_table': 'ifa_archive_etf_60m', 'archive_key_col': 'ts_code', 'default_enabled': False, 'support_status': 'supported_later', 'source_endpoint': 'stk_mins', 'instrument_key': 'ts_code', 'note': 'valid true-source ETF intraday family kept in Archive V2 model as later-enable/default-off support; current path now uses direct stk_mins with ETF ts_code'},
    'index_60m': {'frequency': '60m', 'bucket': 'tradable', 'implemented': True, 'kind': 'intraday_rollup', 'source_table': 'highfreq_index_1m_working', 'source_time_col': 'trade_time', 'source_date_expr': 'date(trade_time)', 'source_symbol_col': 'ts_code', 'bucket_minutes': 60, 'dest_table': 'ifa_archive_index_60m', 'archive_key_col': 'ts_code', 'instrument_key': 'ts_code', 'default_enabled': False, 'support_status': 'supported_later', 'source_endpoint': 'idx_mins', 'note': 'valid true-source intraday family kept as later-enable/default-off support; current path still needs source-first correction'},
    'futures_60m': {'frequency': '60m', 'bucket': 'tradable', 'implemented': True, 'kind': 'intraday_bars', 'source_table': 'futures_60min_history', 'source_time_col': 'trade_time', 'source_date_expr': 'date(trade_time)', 'source_symbol_col': 'ts_code', 'dest_table': 'ifa_archive_futures_60m', 'archive_key_col': 'ts_code', 'instrument_key': 'ts_code', 'default_enabled': False, 'support_status': 'supported_later', 'source_endpoint': 'ft_mins', 'note': 'valid true-source intraday family kept as later-enable/default-off support; current path still needs source-first correction'},
    'commodity_60m': {'frequency': '60m', 'bucket': 'tradable', 'implemented': True, 'kind': 'intraday_bars', 'source_table': 'commodity_60min_history', 'source_time_col': 'trade_time', 'source_date_expr': 'date(trade_time)', 'source_symbol_col': 'ts_code', 'dest_table': 'ifa_archive_commodity_60m', 'archive_key_col': 'ts_code', 'instrument_key': 'ts_code', 'default_enabled': False, 'support_status': 'supported_later', 'source_endpoint': 'ft_mins', 'note': 'valid true-source intraday family kept as later-enable/default-off support; current path still needs source-first correction'},
    'precious_metal_60m': {'frequency': '60m', 'bucket': 'tradable', 'implemented': True, 'kind': 'intraday_bars', 'source_table': 'precious_metal_60min_history', 'source_time_col': 'trade_time', 'source_date_expr': 'date(trade_time)', 'source_symbol_col': 'ts_code', 'dest_table': 'ifa_archive_precious_metal_60m', 'archive_key_col': 'ts_code', 'instrument_key': 'ts_code', 'default_enabled': False, 'support_status': 'supported_later', 'source_endpoint': 'ft_mins', 'note': 'valid true-source intraday family kept as later-enable/default-off support; current path still needs source-first correction'},
    'equity_15m': {'frequency': '15m', 'bucket': 'tradable', 'implemented': True, 'kind': 'intraday_bars', 'source_table': 'stock_15min_history', 'source_time_col': 'trade_time', 'source_date_expr': 'date(trade_time)', 'source_symbol_col': 'ts_code', 'dest_table': 'ifa_archive_equity_15m', 'archive_key_col': 'ts_code', 'instrument_key': 'ts_code', 'default_enabled': False, 'support_status': 'supported_later', 'source_endpoint': 'stk_mins', 'note': 'valid true-source intraday family kept as later-enable/default-off support; current path still needs source-first correction'},
    'etf_15m': {'frequency': '15m', 'bucket': 'tradable', 'implemented': False, 'kind': 'intraday_source_pending', 'default_enabled': False, 'support_status': 'supported_later', 'source_endpoint': 'stk_mins', 'instrument_key': 'ts_code', 'note': 'valid true-source ETF intraday family kept in Archive V2 model as later-enable/default-off support; correct future path is direct stk_mins with ETF ts_code'},
    'index_15m': {'frequency': '15m', 'bucket': 'tradable', 'implemented': True, 'kind': 'intraday_rollup', 'source_table': 'highfreq_index_1m_working', 'source_time_col': 'trade_time', 'source_date_expr': 'date(trade_time)', 'source_symbol_col': 'ts_code', 'bucket_minutes': 15, 'dest_table': 'ifa_archive_index_15m', 'archive_key_col': 'ts_code', 'instrument_key': 'ts_code', 'default_enabled': False, 'support_status': 'supported_later', 'source_endpoint': 'idx_mins', 'note': 'valid true-source intraday family kept as later-enable/default-off support; current path still needs source-first correction'},
    'futures_15m': {'frequency': '15m', 'bucket': 'tradable', 'implemented': True, 'kind': 'intraday_bars', 'source_table': 'futures_15min_history', 'source_time_col': 'trade_time', 'source_date_expr': 'date(trade_time)', 'source_symbol_col': 'ts_code', 'dest_table': 'ifa_archive_futures_15m', 'archive_key_col': 'ts_code', 'instrument_key': 'ts_code', 'default_enabled': False, 'support_status': 'supported_later', 'source_endpoint': 'ft_mins', 'note': 'valid true-source intraday family kept as later-enable/default-off support; current path still needs source-first correction'},
    'commodity_15m': {'frequency': '15m', 'bucket': 'tradable', 'implemented': True, 'kind': 'intraday_bars', 'source_table': 'commodity_15min_history', 'source_time_col': 'trade_time', 'source_date_expr': 'date(trade_time)', 'source_symbol_col': 'ts_code', 'dest_table': 'ifa_archive_commodity_15m', 'archive_key_col': 'ts_code', 'instrument_key': 'ts_code', 'default_enabled': False, 'support_status': 'supported_later', 'source_endpoint': 'ft_mins', 'note': 'valid true-source intraday family kept as later-enable/default-off support; current path still needs source-first correction'},
    'precious_metal_15m': {'frequency': '15m', 'bucket': 'tradable', 'implemented': True, 'kind': 'intraday_bars', 'source_table': 'precious_metal_15min_history', 'source_time_col': 'trade_time', 'source_date_expr': 'date(trade_time)', 'source_symbol_col': 'ts_code', 'dest_table': 'ifa_archive_precious_metal_15m', 'archive_key_col': 'ts_code', 'instrument_key': 'ts_code', 'default_enabled': False, 'support_status': 'supported_later', 'source_endpoint': 'ft_mins', 'note': 'valid true-source intraday family kept as later-enable/default-off support; current path still needs source-first correction'},
    'equity_1m': {'frequency': '1m', 'bucket': 'tradable', 'implemented': True, 'kind': 'intraday_bars', 'source_table': 'stock_minute_history', 'source_time_col': 'trade_time', 'source_date_expr': 'date(trade_time)', 'source_symbol_col': 'ts_code', 'dest_table': 'ifa_archive_equity_1m', 'archive_key_col': 'ts_code', 'instrument_key': 'ts_code', 'default_enabled': False, 'support_status': 'supported_later', 'source_endpoint': 'stk_mins', 'note': 'valid true-source intraday family kept as later-enable/default-off support; current path still needs source-first correction'},
    'etf_1m': {'frequency': '1m', 'bucket': 'tradable', 'implemented': False, 'kind': 'intraday_source_pending', 'default_enabled': False, 'support_status': 'supported_later', 'source_endpoint': 'stk_mins', 'instrument_key': 'ts_code', 'note': 'valid true-source ETF intraday family kept in Archive V2 model as later-enable/default-off support; correct future path is direct stk_mins with ETF ts_code'},
    'index_1m': {'frequency': '1m', 'bucket': 'tradable', 'implemented': True, 'kind': 'intraday_bars', 'source_table': 'highfreq_index_1m_working', 'source_time_col': 'trade_time', 'source_date_expr': 'date(trade_time)', 'source_symbol_col': 'ts_code', 'dest_table': 'ifa_archive_index_1m', 'archive_key_col': 'ts_code', 'instrument_key': 'ts_code', 'default_enabled': False, 'support_status': 'supported_later', 'source_endpoint': 'idx_mins', 'note': 'valid true-source intraday family kept as later-enable/default-off support; current path still needs source-first correction'},
    'futures_1m': {'frequency': '1m', 'bucket': 'tradable', 'implemented': True, 'kind': 'intraday_bars', 'source_table': 'futures_minute_history', 'source_time_col': 'trade_time', 'source_date_expr': 'date(trade_time)', 'source_symbol_col': 'ts_code', 'dest_table': 'ifa_archive_futures_1m', 'archive_key_col': 'ts_code', 'instrument_key': 'ts_code', 'default_enabled': False, 'support_status': 'supported_later', 'source_endpoint': 'ft_mins', 'note': 'valid true-source intraday family kept as later-enable/default-off support; current path still needs source-first correction'},
    'commodity_1m': {'frequency': '1m', 'bucket': 'tradable', 'implemented': True, 'kind': 'intraday_bars', 'source_table': 'commodity_minute_history', 'source_time_col': 'trade_time', 'source_date_expr': 'date(trade_time)', 'source_symbol_col': 'ts_code', 'dest_table': 'ifa_archive_commodity_1m', 'archive_key_col': 'ts_code', 'instrument_key': 'ts_code', 'default_enabled': False, 'support_status': 'supported_later', 'source_endpoint': 'ft_mins', 'note': 'valid true-source intraday family kept as later-enable/default-off support; current path still needs source-first correction'},
    'precious_metal_1m': {'frequency': '1m', 'bucket': 'tradable', 'implemented': True, 'kind': 'intraday_bars', 'source_table': 'precious_metal_minute_history', 'source_time_col': 'trade_time', 'source_date_expr': 'date(trade_time)', 'source_symbol_col': 'ts_code', 'dest_table': 'ifa_archive_precious_metal_1m', 'archive_key_col': 'ts_code', 'instrument_key': 'ts_code', 'default_enabled': False, 'support_status': 'supported_later', 'source_endpoint': 'ft_mins', 'note': 'valid true-source intraday family kept as later-enable/default-off support; current path still needs source-first correction'},
}

IDENTITY_POLICY_BY_FAMILY = {
    'equity_daily': '(business_date, ts_code)',
    'index_daily': '(business_date, ts_code)',
    'etf_daily': '(business_date, ts_code)',
    'non_equity_daily': '(business_date, family_code, ts_code)',
    'macro_daily': '(business_date, macro_series)',
    'announcements_daily': '(business_date, row_key[ts_code|title|url|rec_time])',
    'news_daily': '(business_date, row_key[src|datetime|title|content_hash])',
    'research_reports_daily': '(business_date, row_key[report_type|inst_csname|ts_code|title|author])',
    'investor_qa_daily': '(business_date, row_key[exchange_source|ts_code|pub_time|q_hash|a_hash])',
    'dragon_tiger_daily': '(business_date, row_key[ts_code|reason|net_amount|l_amount])',
    'limit_up_detail_daily': '(business_date, row_key[ts_code|limit|first_time|last_time|limit_times])',
    'limit_up_down_status_daily': '(business_date)',
    'sector_performance_daily': '(business_date, sector_code)',
    'highfreq_event_stream_daily': '(business_date, row_key[event_time|event_type|symbol|source|title])',
    'highfreq_limit_event_stream_daily': '(business_date, row_key[trade_time|event_type|symbol|source|title])',
    'highfreq_sector_breadth_daily': '(business_date, sector_code)',
    'highfreq_sector_heat_daily': '(business_date, sector_code)',
    'highfreq_leader_candidate_daily': '(business_date, symbol)',
    'highfreq_intraday_signal_state_daily': '(business_date, scope_key)',
    'equity_60m': '(business_date, ts_code, bar_time)',
    'etf_60m': '(business_date, ts_code, bar_time)',
    'index_60m': '(business_date, ts_code, bar_time)',
    'futures_60m': '(business_date, ts_code, bar_time)',
    'commodity_60m': '(business_date, ts_code, bar_time)',
    'precious_metal_60m': '(business_date, ts_code, bar_time)',
    'equity_15m': '(business_date, ts_code, bar_time)',
    'etf_15m': '(business_date, ts_code, bar_time)',
    'index_15m': '(business_date, ts_code, bar_time)',
    'futures_15m': '(business_date, ts_code, bar_time)',
    'commodity_15m': '(business_date, ts_code, bar_time)',
    'precious_metal_15m': '(business_date, ts_code, bar_time)',
    'equity_1m': '(business_date, ts_code, bar_time)',
    'etf_1m': '(business_date, ts_code, bar_time)',
    'index_1m': '(business_date, ts_code, bar_time)',
    'futures_1m': '(business_date, ts_code, bar_time)',
    'commodity_1m': '(business_date, ts_code, bar_time)',
    'precious_metal_1m': '(business_date, ts_code, bar_time)',
}

SUPPORTED_FAMILIES = set(ALL_FAMILY_META.keys())
IMPLEMENTED_FAMILIES = {family for family, meta in ALL_FAMILY_META.items() if meta.get('implemented')}
MARKET_CALENDAR_FAMILIES = {family for family, meta in ALL_FAMILY_META.items() if meta['bucket'] in {'tradable', 'business'} and meta['frequency'] == 'daily'}
SOURCE_FIRST_DAILY_FAMILIES = {
    'index_daily',
    'macro_daily',
}
SOURCE_FIRST_60M_FAMILIES = {
    'equity_60m',
    'etf_60m',
    'index_60m',
    'futures_60m',
    'commodity_60m',
    'precious_metal_60m',
}
ZERO_OK_DAILY_FAMILIES = {
    'investor_qa_daily',
    'research_reports_daily',
}


class ArchiveV2Runner:
    def __init__(self, profile_path: str):
        self.profile_path = str(profile_path)
        self.profile: ArchiveProfile = load_profile(profile_path)
        self.run_id = uuid.uuid4()
        self.client = TushareClient()
        self._column_cache: dict[str, list[str]] = {}

    def run(self) -> dict:
        return self.run_with_context()

    def run_with_context(self, trigger_source: str = 'manual_profile', notes: str | None = None) -> dict:
        ensure_schema()
        errors = validate_profile(self.profile)
        if errors:
            return {'ok': False, 'errors': errors}
        self._persist_profile()
        self._create_run('running', trigger_source=trigger_source, notes=notes)
        try:
            result = self._dispatch()
            self._finish_run(result['status'], result.get('notes'), result.get('error_text'))
            return {'ok': True, 'run_id': str(self.run_id), **result}
        except Exception as e:
            self._finish_run('failed', error_text=str(e))
            raise

    def run_selected_targets(self, targets: list[dict], trigger_source: str = 'operator_repair_batch', notes: str | None = None) -> dict:
        ensure_schema()
        errors = validate_profile(self.profile)
        if errors:
            return {'ok': False, 'errors': errors}
        self._persist_profile()
        self._create_run('running', trigger_source=trigger_source, notes=notes)
        try:
            result = self._run_selected_targets(targets)
            self._finish_run(result['status'], result.get('notes'), result.get('error_text'))
            return {'ok': True, 'run_id': str(self.run_id), **result}
        except Exception as e:
            self._finish_run('failed', error_text=str(e))
            raise

    def _dispatch(self) -> dict:
        families = self._resolve_requested_families()
        if self.profile.mode == 'single_day':
            return self._run_dates([self.profile.start_date], families, TARGET_POLICY_REPAIR if self.profile.repair_incomplete else TARGET_POLICY_ALL)
        if self.profile.mode == 'date_range':
            return self._run_dates(self._expand_date_range(), families, TARGET_POLICY_REPAIR if self.profile.repair_incomplete else TARGET_POLICY_ALL)
        if self.profile.mode == 'backfill':
            return self._run_dates(self._resolve_backfill_dates(families), families, TARGET_POLICY_REPAIR if self.profile.repair_incomplete else TARGET_POLICY_GAPS)
        if self.profile.mode == 'delete':
            self._write_item('archive_delete_scope', 'daily', None, 'partial', 0, [], notes='delete mode skeleton only; no family deletion implemented yet')
            return {'status': 'partial', 'notes': 'delete mode skeleton executed; no data deletion implemented in current batch'}
        return {'status': 'failed', 'error_text': f'unsupported mode {self.profile.mode}'}

    def _resolve_requested_families(self) -> list[str]:
        if self.profile.family_groups:
            return list(self.profile.family_groups)
        families: list[str] = []
        if self.profile.include_daily:
            if self.profile.include_tradable_families:
                families.extend(DAILY_TRADABLE_FAMILIES)
            if self.profile.include_business_families:
                families.extend(DAILY_BUSINESS_FAMILIES)
            if self.profile.include_signal_families:
                families.extend(DAILY_SIGNAL_FAMILIES)
        if self.profile.include_60m and self.profile.include_tradable_families:
            families.extend(INTRADAY_TRADABLE_FAMILIES['60m'])
        if self.profile.include_15m and self.profile.include_tradable_families:
            families.extend(INTRADAY_TRADABLE_FAMILIES['15m'])
        if self.profile.include_1m and self.profile.include_tradable_families:
            families.extend(INTRADAY_TRADABLE_FAMILIES['1m'])
        # preserve order + dedupe
        seen = set()
        out = []
        for f in families:
            if f not in seen:
                seen.add(f)
                out.append(f)
        return out

    def _expand_date_range(self) -> list[str]:
        start = datetime.fromisoformat(self.profile.start_date).date()
        end = datetime.fromisoformat(self.profile.end_date).date()
        days: list[str] = []
        cur = start
        while cur <= end:
            days.append(cur.isoformat())
            cur += timedelta(days=1)
        return days

    def _resolve_backfill_dates(self, families: list[str]) -> list[str]:
        anchor = datetime.fromisoformat(self.profile.end_date).date() if self.profile.end_date else datetime.now(timezone.utc).date()
        candidate_dates: set[date] = set()
        fetch_limit = max(int(self.profile.backfill_days or 0) * 4, 12)
        for family in families:
            candidate_dates.update(self._available_dates_for_family(family, anchor, fetch_limit))
        ordered = sorted([d for d in candidate_dates if d <= anchor], reverse=True)
        selected = ordered[: int(self.profile.backfill_days or 0)]
        return [d.isoformat() for d in sorted(selected)]

    def _available_dates_for_family(self, family: str, anchor: date, limit: int) -> list[date]:
        meta = ALL_FAMILY_META.get(family)
        if not meta:
            return []
        if family in MARKET_CALENDAR_FAMILIES:
            sql = "select distinct trade_date as d from ifa2.index_daily_bar_history where trade_date <= :anchor order by d desc limit :limit"
            with engine.begin() as conn:
                return [r['d'] for r in conn.execute(text(sql), {'anchor': anchor, 'limit': limit}).mappings().all()]
        if meta['kind'] in {'intraday_bars', 'intraday_rollup'}:
            table = meta['source_table']
            date_expr = self._intraday_date_expr(meta)
            with engine.begin() as conn:
                return [r['d'] for r in conn.execute(text(f"select distinct {date_expr} as d from ifa2.{table} where {date_expr} <= :anchor order by d desc limit :limit"), {'anchor': anchor, 'limit': limit}).mappings().all()]
        table = meta.get('source_table')
        date_col = meta.get('date_col')
        if table and date_col:
            expr = f'date({date_col})' if meta.get('date_via_ts') else date_col
            with engine.begin() as conn:
                return [r['d'] for r in conn.execute(text(f"select distinct {expr} as d from ifa2.{table} where {expr} <= :anchor order by d desc limit :limit"), {'anchor': anchor, 'limit': limit}).mappings().all()]
        return []

    def _run_dates(self, dates: list[str], families: list[str], target_policy: str) -> dict:
        final_status = 'completed'
        notes: list[str] = []
        executed_targets = 0
        skipped_targets = 0
        if not dates:
            return {'status': 'completed', 'notes': 'no eligible dates resolved for requested bounded execution'}

        for business_date in dates:
            for family in families:
                meta = ALL_FAMILY_META.get(family)
                if family not in SUPPORTED_FAMILIES or not meta:
                    self._write_item(family, 'daily', business_date, 'incomplete', 0, [], notes='unsupported family group in current batch')
                    self._upsert_completeness(business_date, family, 'daily', self._coverage_scope(), 'incomplete', 0, 'unsupported family group in current batch')
                    final_status = 'partial'
                    continue

                frequency = meta['frequency']
                decision, decision_note = self._target_decision(business_date, family, frequency, target_policy)
                if decision == 'skip':
                    self._write_item(family, frequency, business_date, 'superseded', 0, [], notes=decision_note)
                    skipped_targets += 1
                    continue

                if family not in IMPLEMENTED_FAMILIES:
                    note = self._decorate_note(family, meta.get('note') or 'family scaffold only; execution not implemented in current batch')
                    self._write_item(family, frequency, business_date, 'incomplete', 0, [], notes=note)
                    self._upsert_completeness(business_date, family, frequency, self._coverage_scope(), 'incomplete', 0, note)
                    final_status = 'partial'
                    executed_targets += 1
                    continue

                rows_written, tables_touched, item_status, item_notes, item_error = self._execute_family(family, business_date)
                effective_note = self._decorate_note(family, item_notes)
                self._write_item(family, frequency, business_date, item_status, rows_written, tables_touched, notes=effective_note, error_text=item_error)
                self._upsert_completeness(business_date, family, frequency, self._coverage_scope(), item_status, rows_written, item_error or (effective_note if item_status != 'completed' else None))
                if item_status != 'completed':
                    final_status = 'partial'
                executed_targets += 1

        if final_status == 'partial':
            notes.append('Archive V2 execution ran with truthful non-complete states preserved where families/frequencies/dates were missing, unstable, or intentionally unarchived')
        else:
            notes.append('Archive V2 execution completed for the eligible requested scope')
        notes.append(f'dates={len(dates)} executed_targets={executed_targets} skipped_targets={skipped_targets} target_policy={target_policy}')
        return {'status': final_status, 'notes': '; '.join(notes)}

    def _run_selected_targets(self, targets: list[dict]) -> dict:
        final_status = 'completed'
        executed_targets = 0
        if not targets:
            return {'status': 'completed', 'notes': 'operator repair batch resolved no eligible actionable targets'}

        for target in targets:
            business_date = str(target['business_date'])
            family = target['family_name']
            meta = ALL_FAMILY_META.get(family, {})
            frequency = meta.get('frequency', target.get('frequency', 'daily'))
            selection_note = (
                f"repair_batch selected priority={target.get('priority')} urgency={target.get('urgency')} "
                f"actionability={target.get('actionability')} reason_code={target.get('reason_code')}"
            )
            if family not in IMPLEMENTED_FAMILIES:
                note = self._decorate_note(family, f'{selection_note} | family execution not implemented in current batch')
                self._write_item(family, frequency, business_date, 'incomplete', 0, [], notes=note)
                self._upsert_completeness(business_date, family, frequency, self._coverage_scope(), 'incomplete', 0, note)
                final_status = 'partial'
                executed_targets += 1
                continue

            rows_written, tables_touched, item_status, item_notes, item_error = self._execute_family(family, business_date)
            effective_note = self._decorate_note(family, f'{selection_note} | {item_notes}' if item_notes else selection_note)
            self._write_item(family, frequency, business_date, item_status, rows_written, tables_touched, notes=effective_note, error_text=item_error)
            self._upsert_completeness(business_date, family, frequency, self._coverage_scope(), item_status, rows_written, item_error or (effective_note if item_status != 'completed' else None))
            if item_status != 'completed':
                final_status = 'partial'
            executed_targets += 1

        return {'status': final_status, 'selected_targets': executed_targets, 'notes': f'operator repair batch executed selected_targets={executed_targets}'}

    def _target_decision(self, business_date: str, family: str, frequency: str, target_policy: str) -> tuple[str, str | None]:
        if target_policy == TARGET_POLICY_ALL:
            return 'run', None
        completeness = self._get_completeness(business_date, family, frequency)
        queue_row = self._get_repair_queue_row(business_date, family, frequency)
        if target_policy == TARGET_POLICY_GAPS:
            if completeness is None:
                return 'run', 'bounded backfill targeting missing completeness state'
            if completeness['status'] in NON_COMPLETED_STATUSES:
                return 'run', f"bounded backfill targeting non-complete state={completeness['status']}"
            return 'skip', 'already completed; skipped by bounded backfill gap policy'
        if target_policy == TARGET_POLICY_REPAIR:
            if queue_row and queue_row['status'] in REPAIR_QUEUE_PENDING_STATUSES:
                return 'run', f"repair queue requested retry status={queue_row['status']}"
            if completeness and completeness['status'] in NON_COMPLETED_STATUSES:
                return 'run', f"repair mode targeting completeness status={completeness['status']}"
            return 'skip', 'not in repair scope; skipped by repair/retry policy'
        return 'run', None

    def _get_completeness(self, business_date: str, family: str, frequency: str):
        with engine.begin() as conn:
            return conn.execute(text("""
                select status, row_count, last_error, last_run_id
                from ifa2.ifa_archive_completeness
                where business_date = :business_date
                  and family_name = :family_name
                  and frequency = :frequency
                  and coverage_scope = :coverage_scope
            """), {'business_date': business_date, 'family_name': family, 'frequency': frequency, 'coverage_scope': self._coverage_scope()}).mappings().first()

    def _get_repair_queue_row(self, business_date: str, family: str, frequency: str):
        with engine.begin() as conn:
            return conn.execute(text("""
                select status, reason, reason_code, actionability, priority, urgency, retry_count, retry_after, claim_id, claimed_by, claim_expires_at, last_run_id
                from ifa2.ifa_archive_repair_queue
                where business_date = :business_date
                  and family_name = :family_name
                  and frequency = :frequency
                  and coverage_scope = :coverage_scope
            """), {'business_date': business_date, 'family_name': family, 'frequency': frequency, 'coverage_scope': self._coverage_scope()}).mappings().first()

    def _execute_family(self, family: str, business_date: str):
        meta = ALL_FAMILY_META[family]
        trade_date = business_date.replace('-', '')
        kind = meta['kind']
        if family in BUSINESS_DAILY_CONTRACTS:
            return self._execute_business_contract_family(family, business_date)
        if family in SOURCE_FIRST_DAILY_FAMILIES:
            table = meta.get('dest_table') or DIRECT_DEST_TABLES.get(family)
            rows = self._fetch_source_first_daily_rows(family, business_date)
            if not rows and family in ZERO_OK_DAILY_FAMILIES:
                return 0, [table], 'completed', 'source-empty but truthful zero-row day', None
            return self._write_daily_rows(table, business_date, rows, note=meta.get('note', 'source-first daily archived'))
        if family in SOURCE_FIRST_60M_FAMILIES:
            rows = self._fetch_source_first_60m_rows(family, business_date)
            return self._write_intraday_rows(meta, business_date, rows, note=meta.get('note', 'source-first 60m archived'))
        if kind == 'tushare_daily':
            rows = self.client.query('daily', {'trade_date': trade_date}, timeout_sec=30, max_retries=2)
            return self._write_json_rows('ifa_archive_equity_daily', business_date, rows, 'ts_code')
        if kind == 'tushare_etf':
            rows = self.client.query('fund_daily', {'trade_date': trade_date}, timeout_sec=30, max_retries=2)
            return self._write_json_rows('ifa_archive_etf_daily', business_date, rows, 'ts_code')
        if kind == 'tushare_non_equity':
            rows = self.client.query('fut_daily', {'trade_date': trade_date}, timeout_sec=30, max_retries=2)
            if not rows:
                return 0, ['ifa_archive_non_equity_daily'], 'incomplete', 'source returned no non-equity daily rows for sample date', None
            return self._write_non_equity_rows('ifa_archive_non_equity_daily', business_date, rows)
        if kind == 'macro_daily':
            rows = self._fetch_macro_rows(business_date)
            if not rows:
                return 0, ['ifa_archive_macro_daily'], 'incomplete', 'no macro snapshot rows available on or before business_date', None
            return self._write_macro_rows('ifa_archive_macro_daily', business_date, rows)
        if kind == 'history_daily':
            rows = self._fetch_history_rows(meta['source_table'], meta['date_col'], business_date)
            return self._write_json_rows(meta['dest_table'], business_date, rows, meta['key_col'], note=meta.get('note', 'history-backed archive written'))
        if kind == 'multi_key_daily':
            rows = self._fetch_history_rows(meta['source_table'], meta['date_col'], business_date)
            return self._write_multi_key_rows(meta['dest_table'], business_date, rows, meta['keys'], note=meta.get('note', 'history-backed archive written'))
        if kind == 'news_daily':
            rows = self._fetch_history_rows_by_date(meta['source_table'], meta['date_col'], business_date)
            return self._write_news_rows(meta['dest_table'], business_date, rows)
        if kind == 'investor_qa_daily':
            rows = self._fetch_history_rows(meta['source_table'], meta['date_col'], business_date)
            return self._write_investor_qa_rows(meta['dest_table'], business_date, rows)
        if kind == 'singleton_daily':
            rows = self._fetch_history_rows(meta['source_table'], meta['date_col'], business_date)
            return self._write_singleton_rows(meta['dest_table'], business_date, rows, note=meta.get('note', 'singleton archive written'))
        if kind == 'event_daily':
            rows = self._fetch_history_rows_by_date(meta['source_table'], meta['date_col'], business_date)
            return self._write_event_rows(meta['dest_table'], business_date, rows, meta['time_col'], note=meta.get('note', 'event archive written'))
        if kind == 'snapshot_daily':
            rows = self._fetch_latest_daily_rows(meta['source_table'], business_date, meta['keys'], meta['time_col'])
            return self._write_snapshot_rows(meta['dest_table'], business_date, rows, meta['keys'], 'snapshot_time', meta['time_col'], note=meta.get('note', 'snapshot archive written'))
        if kind == 'intraday_bars':
            rows = self._fetch_intraday_rows(meta, business_date)
            return self._write_intraday_rows(meta, business_date, rows, note=meta.get('note', 'intraday bars archived'))
        if kind == 'intraday_rollup':
            rows = self._fetch_intraday_rollup_rows(meta, business_date)
            return self._write_intraday_rows(meta, business_date, rows, note=meta.get('note', 'intraday bars archived'))
        return 0, [], 'incomplete', 'family execution not implemented', None

    def _intraday_time_col(self, meta: dict[str, Any]) -> str:
        return meta.get('source_time_col') or self._resolve_source_time_col(meta['source_table'])

    def _intraday_symbol_col(self, meta: dict[str, Any]) -> str:
        if meta.get('source_symbol_col'):
            return meta['source_symbol_col']
        cols = self._source_columns(meta['source_table'])
        return 'ts_code' if 'ts_code' in cols else 'symbol'

    def _intraday_date_expr(self, meta: dict[str, Any]) -> str:
        if meta.get('source_date_expr'):
            return meta['source_date_expr']
        date_col = meta.get('source_date_col')
        if date_col:
            return date_col
        return f"date({self._intraday_time_col(meta)})"

    def _source_columns(self, table: str) -> list[str]:
        if table not in self._column_cache:
            with engine.begin() as conn:
                self._column_cache[table] = conn.execute(text("""
                    select column_name
                    from information_schema.columns
                    where table_schema='ifa2' and table_name=:t
                    order by ordinal_position
                """), {'t': table}).scalars().all()
        return self._column_cache[table]

    def _resolve_source_date_col(self, table: str) -> str:
        cols = self._source_columns(table)
        for candidate in ['trade_date', 'business_date', 'biz_date', 'date']:
            if candidate in cols:
                return candidate
        raise ValueError(f'could not resolve date column for {table}')

    def _resolve_source_time_col(self, table: str) -> str:
        cols = self._source_columns(table)
        for candidate in ['trade_time', 'bar_time', 'datetime', 'event_time', 'ts', 'timestamp']:
            if candidate in cols:
                return candidate
        raise ValueError(f'could not resolve time column for {table}')

    def _fetch_history_rows(self, table: str, date_col: str, business_date: str):
        with engine.begin() as conn:
            return [self._normalize_record(dict(r)) for r in conn.execute(text(f"select * from ifa2.{table} where {date_col} = :d"), {'d': business_date}).mappings().all()]

    def _fetch_history_rows_by_date(self, table: str, ts_col: str, business_date: str):
        with engine.begin() as conn:
            return [self._normalize_record(dict(r)) for r in conn.execute(text(f"select * from ifa2.{table} where date({ts_col}) = :d"), {'d': business_date}).mappings().all()]

    def _fetch_latest_daily_rows(self, table: str, business_date: str, key_cols: list[str], ts_col: str):
        partition = ', '.join(key_cols)
        order_cols = [ts_col]
        if 'created_at' in self._source_columns(table):
            order_cols.append('created_at')
        order_expr = ', '.join([f'{c} desc nulls last' for c in order_cols])
        sql = f"""
            select *
            from (
                select *, row_number() over (partition by {partition} order by {order_expr}) as rn
                from ifa2.{table}
                where date({ts_col}) = :d
            ) ranked
            where rn = 1
        """
        with engine.begin() as conn:
            return [self._normalize_record(dict(r)) for r in conn.execute(text(sql), {'d': business_date}).mappings().all()]

    def _fetch_macro_rows(self, business_date: str):
        with engine.begin() as conn:
            return [self._normalize_record(dict(r)) for r in conn.execute(text("select macro_series, report_date, value, source from ifa2.macro_history where report_date = (select max(report_date) from ifa2.macro_history where report_date <= :d)"), {'d': business_date}).mappings().all()]

    def _fetch_source_first_daily_rows(self, family: str, business_date: str) -> list[dict]:
        if family == 'index_daily':
            return self._fetch_index_daily_direct(business_date)
        if family == 'macro_daily':
            return self._fetch_macro_rows(business_date)
        raise ValueError(f'unsupported source-first daily family: {family}')

    def _execute_business_contract_family(self, family: str, business_date: str):
        contract = BUSINESS_DAILY_CONTRACTS[family]
        assert_archive_namespace(contract.archive_table_name)
        result = self._fetch_business_contract_rows(family, business_date)
        rows = result['rows']
        status = result['status']
        note = result['note']
        if family == 'announcements_daily':
            return self._write_announcements_rows(contract.archive_table_name, business_date, rows, status, note)
        if family == 'news_daily':
            return self._write_news_rows(contract.archive_table_name, business_date, rows, status, note)
        if family == 'research_reports_daily':
            return self._write_research_report_rows(contract.archive_table_name, business_date, rows, status, note)
        if family == 'investor_qa_daily':
            return self._write_investor_qa_rows(contract.archive_table_name, business_date, rows, status, note)
        if family == 'dragon_tiger_daily':
            return self._write_dragon_tiger_rows(contract.archive_table_name, business_date, rows, status, note)
        if family == 'limit_up_detail_daily':
            return self._write_limit_up_detail_rows(contract.archive_table_name, business_date, rows, status, note)
        if family == 'limit_up_down_status_daily':
            return self._write_limit_up_down_status_row(contract.archive_table_name, business_date, result['aggregate_row'], status, note)
        if family == 'sector_performance_daily':
            return self._write_sector_performance_rows(contract.archive_table_name, business_date, rows, status, note)
        raise ValueError(f'unsupported business contract family: {family}')

    def _fetch_business_contract_rows(self, family: str, business_date: str) -> dict[str, Any]:
        if family == 'announcements_daily':
            return self._fetch_announcements_contract_rows(business_date)
        if family == 'news_daily':
            return self._fetch_news_contract_rows(business_date)
        if family == 'research_reports_daily':
            return self._fetch_research_reports_contract_rows(business_date)
        if family == 'investor_qa_daily':
            return self._fetch_investor_qa_contract_rows(business_date)
        if family == 'dragon_tiger_daily':
            return self._fetch_dragon_tiger_contract_rows(business_date)
        if family == 'limit_up_detail_daily':
            return self._fetch_limit_up_detail_contract_rows(business_date)
        if family == 'limit_up_down_status_daily':
            return self._fetch_limit_up_down_status_contract_rows(business_date)
        if family == 'sector_performance_daily':
            return self._fetch_sector_performance_contract_rows(business_date)
        raise ValueError(f'no business contract fetcher for {family}')

    def _fetch_announcements_contract_rows(self, business_date: str) -> dict[str, Any]:
        trade_date = business_date.replace('-', '')
        bulk_rows = self._query_tushare_safe('anns_d', {'ann_date': trade_date})
        suspicious = len(bulk_rows) >= ANNOUNCEMENTS_SUSPICIOUS_NEAR_CAP
        rows = list(bulk_rows)
        note = f"anns_d ann_date bulk_rows={len(bulk_rows)}"
        if suspicious:
            fallback_rows: list[dict[str, Any]] = []
            symbols = self._load_equity_trade_date_symbols(business_date)
            max_workers = 24 if len(symbols) > 120 else max(1, min(12, len(symbols)))
            with ThreadPoolExecutor(max_workers=max_workers) as pool:
                futures = [pool.submit(self._query_tushare_safe, 'anns_d', {'ann_date': trade_date, 'ts_code': ts_code}) for ts_code in symbols]
                for fut in as_completed(futures):
                    fallback_rows.extend(fut.result())
            rows.extend(fallback_rows)
            note = f"anns_d ann_date near cap bulk_rows={len(bulk_rows)}; ts_code fallback_rows={len(fallback_rows)}; union_rows={len(rows)}"
        deduped = self._dedupe_rows('announcements_daily', business_date, rows)
        if not deduped:
            return {'rows': [], 'status': 'incomplete', 'note': note + '; zero rows after bulk/fallback'}
        return {'rows': deduped, 'status': 'completed', 'note': note + f'; deduped_rows={len(deduped)}'}

    def _fetch_news_contract_rows(self, business_date: str) -> dict[str, Any]:
        rows: list[dict[str, Any]] = []
        suspicious_windows: list[str] = []
        tasks = [(src, start_dt, end_dt) for src in NEWS_SOURCE_BUNDLE for start_dt, end_dt in self._split_day_windows(business_date, hours=6)]
        with ThreadPoolExecutor(max_workers=12) as pool:
            futures = [pool.submit(self._fetch_news_window, src, start_dt, end_dt) for src, start_dt, end_dt in tasks]
            for (src, start_dt, end_dt), fut in zip(tasks, futures):
                pulled, suspicious = fut.result()
                rows.extend(pulled)
                if suspicious:
                    suspicious_windows.append(f'{src}:{start_dt}->{end_dt}')
        deduped = self._dedupe_rows('news_daily', business_date, rows)
        if not deduped:
            return {'rows': [], 'status': 'completed', 'note': f'news checked all configured src/windows with truthful zero; suspicious_windows={len(suspicious_windows)}'}
        status = 'completed' if not suspicious_windows else 'incomplete'
        return {'rows': deduped, 'status': status, 'note': f'news srcs={len(NEWS_SOURCE_BUNDLE)} deduped_rows={len(deduped)} suspicious_windows={len(suspicious_windows)}'}

    def _fetch_research_reports_contract_rows(self, business_date: str) -> dict[str, Any]:
        trade_date = business_date.replace('-', '')
        brokers = self._load_recent_broker_universe()
        rows: list[dict[str, Any]] = []
        shard_count = 0
        for report_type in RESEARCH_REPORT_TYPES:
            for inst_csname in brokers:
                shard_rows = self._query_tushare_safe('research_report', {'trade_date': trade_date, 'report_type': report_type, 'inst_csname': inst_csname})
                rows.extend(shard_rows)
                shard_count += 1
        deduped = self._dedupe_rows('research_reports_daily', business_date, rows)
        if not deduped:
            return {'rows': [], 'status': 'completed', 'note': f'research_report report_type×broker shards exhausted with truthful zero; shards={shard_count}'}
        suspicious = any(len(self._query_tushare_safe('research_report', {'trade_date': trade_date, 'report_type': rt})) >= RESEARCH_REPORT_SUSPICIOUS_NEAR_CAP for rt in RESEARCH_REPORT_TYPES)
        status = 'completed' if not suspicious else 'incomplete'
        return {'rows': deduped, 'status': status, 'note': f'research_report shards={shard_count} deduped_rows={len(deduped)} suspicious_bulk={suspicious}'}

    def _fetch_investor_qa_contract_rows(self, business_date: str) -> dict[str, Any]:
        trade_date = business_date.replace('-', '')
        all_rows: list[dict[str, Any]] = []
        low_or_zero = False
        for exchange_source, endpoint in [('sh', 'irm_qa_sh'), ('sz', 'irm_qa_sz')]:
            rows = self._query_tushare_safe(endpoint, {'trade_date': trade_date})
            for row in rows:
                row['exchange_source'] = exchange_source
            all_rows.extend(rows)
            if len(rows) <= INVESTOR_QA_SUSPICIOUS_LOW_ROWS:
                low_or_zero = True
                start_dt, end_dt = self._full_day_window(business_date)
                fallback = self._query_tushare_safe(endpoint, {'start_date': trade_date, 'end_date': trade_date, 'pub_date': start_dt})
                if not fallback:
                    fallback = self._query_tushare_safe(endpoint, {'start_date': trade_date, 'end_date': trade_date})
                for row in fallback:
                    row['exchange_source'] = exchange_source
                all_rows.extend(fallback)
        deduped = self._dedupe_rows('investor_qa_daily', business_date, all_rows)
        if not deduped:
            return {'rows': [], 'status': 'completed', 'note': 'irm_qa_sh + irm_qa_sz exhausted including fallback; truthful zero'}
        return {'rows': deduped, 'status': 'completed', 'note': f'irm_qa_sh+sz rows={len(deduped)} low_or_zero_fallback={low_or_zero}'}

    def _fetch_dragon_tiger_contract_rows(self, business_date: str) -> dict[str, Any]:
        trade_date = business_date.replace('-', '')
        rows = self._query_tushare_safe('top_list', {'trade_date': trade_date})
        deduped = self._dedupe_rows('dragon_tiger_daily', business_date, rows)
        if not deduped:
            return {'rows': [], 'status': 'incomplete', 'note': 'top_list returned zero rows on trading-day contract path'}
        return {'rows': deduped, 'status': 'completed', 'note': f'top_list direct rows={len(deduped)}'}

    def _fetch_limit_up_detail_contract_rows(self, business_date: str) -> dict[str, Any]:
        trade_date = business_date.replace('-', '')
        rows: list[dict[str, Any]] = []
        shards = 0
        for limit_type in LIMIT_LIST_LIMIT_TYPES:
            for exchange in LIMIT_LIST_EXCHANGES:
                shard_rows = self._query_tushare_safe('limit_list_d', {'trade_date': trade_date, 'limit_type': limit_type, 'exchange': exchange})
                for row in shard_rows:
                    row['exchange'] = exchange
                    row['limit_type_shard'] = limit_type
                rows.extend(shard_rows)
                shards += 1
        detail_rows = [r for r in rows if (r.get('limit') or r.get('limit_type_shard')) in {'U', 'Z'}]
        deduped = self._dedupe_rows('limit_up_detail_daily', business_date, detail_rows)
        if not deduped:
            return {'rows': [], 'status': 'incomplete', 'note': f'limit_list_d shards exhausted but no limit-up detail rows; shards={shards}'}
        return {'rows': deduped, 'status': 'completed', 'note': f'limit_list_d shards={shards} detail_rows={len(deduped)}'}

    def _fetch_limit_up_down_status_contract_rows(self, business_date: str) -> dict[str, Any]:
        detail = self._fetch_limit_up_detail_contract_rows(business_date)
        rows = detail['rows']
        aggregate = {
            'business_date': business_date,
            'source_endpoint': 'limit_list_d',
            'source_mode': 'source_plus_aggregate',
            'up_count': sum(1 for r in rows if (r.get('limit') or r.get('limit_type_shard')) == 'U'),
            'blow_open_count': sum(1 for r in rows if (r.get('limit') or r.get('limit_type_shard')) == 'Z'),
            'raw_rows': len(rows),
        }
        if not rows:
            return {'rows': [], 'aggregate_row': aggregate, 'status': detail['status'], 'note': detail['note'] + '; no aggregate rows'}
        return {'rows': rows, 'aggregate_row': aggregate, 'status': 'completed', 'note': detail['note'] + '; aggregate generated from canonical limit_list_d'}

    def _fetch_sector_performance_contract_rows(self, business_date: str) -> dict[str, Any]:
        trade_date = business_date.replace('-', '')
        universe = self._load_ths_sector_universe()
        rows: list[dict[str, Any]] = []
        for item in universe:
            shard = self._query_tushare_safe('ths_daily', {'ts_code': item['ts_code'], 'trade_date': trade_date})
            for row in shard:
                row['sector_name'] = item.get('name')
                row['sector_type'] = item.get('type')
                row['sector_code'] = item.get('ts_code')
            rows.extend(shard)
        deduped = self._dedupe_rows('sector_performance_daily', business_date, rows)
        expected = len(universe)
        actual = len({r.get('sector_code') or r.get('ts_code') for r in deduped if r.get('sector_code') or r.get('ts_code')})
        coverage = 0.0 if expected == 0 else actual / expected
        if not deduped:
            return {'rows': [], 'status': 'incomplete', 'note': f'ths_index supported-universe expected={expected} actual=0 coverage=0.000'}
        status = 'completed' if coverage >= 0.90 else 'incomplete'
        return {'rows': deduped, 'status': status, 'note': f'ths_index+ths_daily supported-universe expected={expected} actual={actual} coverage={coverage:.3f} threshold=0.900 excluded_types=I,BB'}

    def _query_tushare_safe(self, api_name: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        try:
            return [self._normalize_record(dict(r)) for r in self.client.query(api_name, params, timeout_sec=30, max_retries=2)]
        except Exception:
            return []

    def _split_day_windows(self, business_date: str, hours: int) -> list[tuple[str, str]]:
        start = datetime.fromisoformat(business_date + 'T00:00:00')
        end = datetime.fromisoformat(business_date + 'T23:59:59')
        out: list[tuple[str, str]] = []
        cur = start
        while cur < end:
            nxt = min(cur + timedelta(hours=hours), end)
            out.append((cur.strftime('%Y-%m-%d %H:%M:%S'), nxt.strftime('%Y-%m-%d %H:%M:%S')))
            cur = nxt
        return out

    def _full_day_window(self, business_date: str) -> tuple[str, str]:
        windows = self._split_day_windows(business_date, hours=24)
        return windows[0]

    def _fetch_news_window(self, src: str, start_dt: str, end_dt: str) -> tuple[list[dict[str, Any]], bool]:
        rows = self._query_tushare_safe('news', {'src': src, 'start_date': start_dt, 'end_date': end_dt})
        if len(rows) < NEWS_SUSPICIOUS_NEAR_CAP:
            for row in rows:
                row['src'] = src
            return rows, False
        start = datetime.fromisoformat(start_dt.replace(' ', 'T'))
        end = datetime.fromisoformat(end_dt.replace(' ', 'T'))
        if (end - start).total_seconds() <= 3600:
            for row in rows:
                row['src'] = src
            return rows, True
        mid = start + (end - start) / 2
        left_rows, left_suspicious = self._fetch_news_window(src, start.strftime('%Y-%m-%d %H:%M:%S'), mid.strftime('%Y-%m-%d %H:%M:%S'))
        right_rows, right_suspicious = self._fetch_news_window(src, mid.strftime('%Y-%m-%d %H:%M:%S'), end.strftime('%Y-%m-%d %H:%M:%S'))
        return left_rows + right_rows, left_suspicious or right_suspicious

    def _load_recent_broker_universe(self) -> list[str]:
        with engine.begin() as conn:
            rows = conn.execute(text("""
                select distinct inst_csname
                from ifa2.research_reports_history
                where inst_csname is not null and trade_date >= current_date - interval '180 days'
                order by inst_csname
            """)).scalars().all()
        return [str(x) for x in rows if x]

    def _load_ths_sector_universe(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        seen: set[str] = set()
        for index_type in SECTOR_INDEX_TYPES:
            shard = self._query_tushare_safe('ths_index', {'exchange': 'A', 'type': index_type})
            for row in shard:
                ts_code = str(row.get('ts_code') or '')
                if not ts_code or ts_code in seen:
                    continue
                seen.add(ts_code)
                rows.append(row)
        return rows

    def _dedupe_rows(self, family: str, business_date: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        deduped: list[dict[str, Any]] = []
        seen: set[str] = set()
        for row in rows:
            row_key = self._build_business_row_key(family, business_date, row)
            if row_key in seen:
                continue
            seen.add(row_key)
            row['row_key'] = row_key
            deduped.append(row)
        return deduped

    def _build_business_row_key(self, family: str, business_date: str, row: dict[str, Any]) -> str:
        if family == 'announcements_daily':
            return stable_hash(business_date, row.get('ts_code'), row.get('title'), row.get('url'), row.get('rec_time'))
        if family == 'news_daily':
            title = row.get('title') or (str(row.get('content') or '')[:80] or f"{row.get('src') or 'news'}@{row.get('datetime')}")
            row['title'] = title
            content_hash = stable_hash(row.get('content'), title)
            row['content_hash'] = content_hash
            return stable_hash(business_date, row.get('src'), row.get('datetime'), title, content_hash)
        if family == 'research_reports_daily':
            return stable_hash(business_date, row.get('report_type'), row.get('inst_csname'), row.get('ts_code'), row.get('title'), row.get('author'))
        if family == 'investor_qa_daily':
            q_hash = stable_hash(row.get('q'))
            a_hash = stable_hash(row.get('a'))
            row['q_hash'] = q_hash
            row['a_hash'] = a_hash
            return stable_hash(business_date, row.get('exchange_source'), row.get('ts_code'), row.get('pub_time'), q_hash, a_hash)
        if family == 'dragon_tiger_daily':
            return stable_hash(business_date, row.get('ts_code'), row.get('reason'), row.get('net_amount'), row.get('l_amount'))
        if family == 'limit_up_detail_daily':
            return stable_hash(business_date, row.get('ts_code'), row.get('limit') or row.get('limit_type_shard'), row.get('first_time'), row.get('last_time'), row.get('limit_times'))
        if family == 'sector_performance_daily':
            return stable_hash(business_date, row.get('ts_code'))
        raise ValueError(f'unsupported business row_key family: {family}')

    def _fetch_index_daily_direct(self, business_date: str) -> list[dict]:
        trade_date = business_date.replace('-', '')
        index_codes = [
            '000001.SH',
            '399001.SZ',
            '399006.SZ',
            '000300.SH',
            '000905.SH',
            '000016.SH',
            '000688.SH',
            '399300.SZ',
        ]
        out: list[dict] = []
        seen: set[tuple[str, str]] = set()
        for ts_code in index_codes:
            try:
                rows = self.client.query('index_daily', {'ts_code': ts_code, 'trade_date': trade_date}, timeout_sec=30, max_retries=2)
            except Exception:
                rows = []
            for row in rows:
                rec = self._normalize_record(dict(row))
                key = (str(rec.get('ts_code') or ts_code), str(rec.get('trade_date') or trade_date))
                if key in seen:
                    continue
                seen.add(key)
                out.append(rec)
        return out

    def _fetch_source_first_60m_rows(self, family: str, business_date: str) -> list[dict]:
        if family == 'equity_60m':
            return self._fetch_stk_mins_direct(self._load_equity_trade_date_symbols(business_date), business_date, '60min')
        if family == 'etf_60m':
            return self._fetch_stk_mins_direct(self._load_etf_trade_date_symbols(business_date), business_date, '60min')
        if family == 'index_60m':
            return self._fetch_idx_mins_direct([
                '000001.SH', '399001.SZ', '399006.SZ', '000300.SH',
                '000905.SH', '000016.SH', '000688.SH', '399300.SZ',
            ], business_date, '60min')
        if family == 'futures_60m':
            return self._fetch_ft_mins_direct(self._load_symbol_universe('futures_history'), business_date, '60min')
        if family == 'commodity_60m':
            return self._fetch_ft_mins_direct(self._load_symbol_universe('commodity_60min_history'), business_date, '60min')
        if family == 'precious_metal_60m':
            return self._fetch_ft_mins_direct(self._load_symbol_universe('precious_metal_60min_history'), business_date, '60min')
        raise ValueError(f'unsupported source-first 60m family: {family}')

    def _load_symbol_universe(self, table: str) -> list[str]:
        with engine.begin() as conn:
            return [x for x in conn.execute(text(f"select distinct ts_code from ifa2.{table} where ts_code is not null order by ts_code")).scalars().all() if x]

    def _load_equity_trade_date_symbols(self, business_date: str) -> list[str]:
        trade_date = business_date.replace('-', '')
        try:
            rows = self.client.query('daily', {'trade_date': trade_date}, timeout_sec=30, max_retries=2)
        except Exception:
            rows = []
        return sorted({str(r.get('ts_code')) for r in rows if r.get('ts_code')})

    def _load_etf_trade_date_symbols(self, business_date: str) -> list[str]:
        trade_date = business_date.replace('-', '')
        try:
            rows = self.client.query('fund_daily', {'trade_date': trade_date}, timeout_sec=30, max_retries=2)
        except Exception:
            rows = []
        return sorted({str(r.get('ts_code')) for r in rows if r.get('ts_code')})

    def _fetch_stk_mins_direct(self, ts_codes: list[str], business_date: str, freq: str) -> list[dict]:
        return self._fetch_intraday_api_parallel('stk_mins', ts_codes, business_date, freq)

    def _fetch_idx_mins_direct(self, ts_codes: list[str], business_date: str, freq: str) -> list[dict]:
        return self._fetch_intraday_api_parallel('idx_mins', ts_codes, business_date, freq)

    def _fetch_ft_mins_direct(self, ts_codes: list[str], business_date: str, freq: str) -> list[dict]:
        return self._fetch_intraday_api_parallel('ft_mins', ts_codes, business_date, freq)

    def _fetch_intraday_api_parallel(self, api_name: str, ts_codes: list[str], business_date: str, freq: str) -> list[dict]:
        start = business_date + ' 09:00:00'
        end = business_date + ' 16:00:00'
        out: list[dict] = []

        def fetch_one(ts_code: str) -> list[dict]:
            try:
                rows = self.client.query(api_name, {'ts_code': ts_code, 'freq': freq, 'start_date': start, 'end_date': end}, timeout_sec=30, max_retries=2)
            except Exception:
                rows = []
            local: list[dict] = []
            for row in rows:
                rec = self._normalize_record(dict(row))
                rec['bar_time'] = rec.get('trade_time') or rec.get('trade_date')
                rec['instrument_code'] = rec.get('ts_code') or ts_code
                local.append(rec)
            return local

        max_workers = 12 if len(ts_codes) > 24 else max(1, min(6, len(ts_codes)))
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = [pool.submit(fetch_one, ts_code) for ts_code in ts_codes]
            for fut in as_completed(futures):
                out.extend(fut.result())
        return out

    def _fetch_intraday_rows(self, meta: dict[str, Any], business_date: str) -> list[dict]:
        table = meta['source_table']
        date_expr = self._intraday_date_expr(meta)
        time_col = self._intraday_time_col(meta)
        symbol_col = self._intraday_symbol_col(meta)
        params: dict[str, Any] = {'d': business_date}
        symbol_filter = ''
        qualified_date_expr = date_expr.replace(time_col, f't.{time_col}') if time_col in date_expr else date_expr
        qualified_date_expr = qualified_date_expr.replace(symbol_col, f't.{symbol_col}') if symbol_col in qualified_date_expr else qualified_date_expr
        if self.profile.symbol_allowlist:
            params['symbols'] = self.profile.symbol_allowlist
            symbol_filter = f' and {symbol_col} = any(:symbols)'
        elif self.profile.symbol_limit:
            params['symbol_limit'] = self.profile.symbol_limit
            sql = f"""
                with picked as (
                    select distinct {symbol_col}
                    from ifa2.{table}
                    where {date_expr} = :d
                    order by {symbol_col}
                    limit :symbol_limit
                )
                select t.*
                from ifa2.{table} t
                join picked p on t.{symbol_col} = p.{symbol_col}
                where {qualified_date_expr} = :d
                order by t.{symbol_col}, t.{time_col}
            """
            with engine.begin() as conn:
                rows = conn.execute(text(sql), params).mappings().all()
                normalized = []
                for row in rows:
                    rec = self._normalize_record(dict(row))
                    rec['bar_time'] = rec.get(time_col)
                    rec['instrument_code'] = rec.get(symbol_col)
                    normalized.append(rec)
                return normalized
        sql = f"select * from ifa2.{table} where {date_expr} = :d{symbol_filter} order by {symbol_col}, {time_col}"
        with engine.begin() as conn:
            rows = conn.execute(text(sql), params).mappings().all()
            normalized = []
            for row in rows:
                rec = self._normalize_record(dict(row))
                rec['bar_time'] = rec.get(time_col)
                rec['instrument_code'] = rec.get(symbol_col)
                normalized.append(rec)
            return normalized

    def _fetch_intraday_rollup_rows(self, meta: dict[str, Any], business_date: str) -> list[dict]:
        base_rows = self._fetch_intraday_rows(meta, business_date)
        bucket_minutes = int(meta['bucket_minutes'])
        grouped: dict[tuple[str, str], dict[str, Any]] = {}
        ordered_rows = sorted(base_rows, key=lambda r: (str(r.get('instrument_code') or ''), str(r['bar_time'])))
        for row in ordered_rows:
            trade_dt = datetime.fromisoformat(str(row['bar_time'])) if isinstance(row['bar_time'], str) else row['bar_time']
            bucket_time = self._bucket_intraday_time(trade_dt, bucket_minutes)
            instrument_code = row.get('instrument_code') or row.get(meta.get('instrument_key', 'ts_code')) or row.get('ts_code')
            archive_key_col = meta.get('archive_key_col', 'ts_code')
            bucket_key = (str(instrument_code), bucket_time.isoformat())
            current = grouped.get(bucket_key)
            if current is None:
                grouped[bucket_key] = {
                    'instrument_code': instrument_code,
                    archive_key_col: instrument_code,
                    'bar_time': bucket_time.isoformat(),
                    'trade_time': bucket_time.isoformat(),
                    'open': row.get('open'),
                    'high': row.get('high'),
                    'low': row.get('low'),
                    'close': row.get('close'),
                    'vol': row.get('vol') or 0,
                    'amount': row.get('amount') or 0,
                    'source_table': meta['source_table'],
                    'source_frequency': '1m',
                    'rollup_frequency': meta['frequency'],
                    'source_row_count': 1,
                }
                continue
            current['high'] = max(current.get('high') if current.get('high') is not None else row.get('high'), row.get('high'))
            current['low'] = min(current.get('low') if current.get('low') is not None else row.get('low'), row.get('low'))
            current['close'] = row.get('close')
            current['vol'] = (current.get('vol') or 0) + (row.get('vol') or 0)
            current['amount'] = (current.get('amount') or 0) + (row.get('amount') or 0)
            current['source_row_count'] = int(current.get('source_row_count') or 0) + 1
        return list(grouped.values())

    def _bucket_intraday_time(self, trade_dt: datetime, bucket_minutes: int) -> datetime:
        market_anchor = datetime.combine(trade_dt.date(), time(9, 30))
        if trade_dt >= market_anchor:
            delta_minutes = int((trade_dt - market_anchor).total_seconds() // 60)
            bucket_start_minutes = (delta_minutes // bucket_minutes) * bucket_minutes
            return market_anchor + timedelta(minutes=bucket_start_minutes)
        midnight_anchor = datetime.combine(trade_dt.date(), time(0, 0))
        delta_minutes = int((trade_dt - midnight_anchor).total_seconds() // 60)
        bucket_start_minutes = (delta_minutes // bucket_minutes) * bucket_minutes
        return midnight_anchor + timedelta(minutes=bucket_start_minutes)

    def _normalize_record(self, record: dict):
        out = {}
        for k, v in record.items():
            if isinstance(v, Decimal):
                out[k] = float(v)
            elif isinstance(v, datetime):
                out[k] = v.isoformat()
            else:
                out[k] = v
        return out

    def _write_json_rows(self, table: str, business_date: str, rows: list[dict], key_col: str, note: str = 'source-side direct daily pull archived'):
        if not rows:
            return 0, [table], 'incomplete', 'source returned no rows', None
        if self.profile.write_enabled:
            with engine.begin() as conn:
                for r in rows:
                    conn.execute(text(f"insert into ifa2.{table}(business_date, {key_col}, payload) values (:business_date, :key, CAST(:payload as jsonb)) on conflict (business_date, {key_col}) do update set payload=excluded.payload"), {'business_date': business_date, 'key': r[key_col], 'payload': json.dumps(r, ensure_ascii=False, default=str)})
        return len(rows), [table], 'completed', note, None

    def _write_multi_key_rows(self, table: str, business_date: str, rows: list[dict], keys: list[str], note: str):
        if not rows:
            return 0, [table], 'incomplete', 'source/history returned no rows', None
        if self.profile.write_enabled:
            with engine.begin() as conn:
                for r in rows:
                    conn.execute(text(f"insert into ifa2.{table}(business_date, {keys[0]}, {keys[1]}, payload) values (:business_date, :k1, :k2, CAST(:payload as jsonb)) on conflict (business_date, {keys[0]}, {keys[1]}) do update set payload=excluded.payload"), {'business_date': business_date, 'k1': r[keys[0]], 'k2': r[keys[1]], 'payload': json.dumps(r, ensure_ascii=False, default=str)})
        return len(rows), [table], 'completed', note, None

    def _write_announcements_rows(self, table: str, business_date: str, rows: list[dict], status: str, note: str):
        if not rows:
            return 0, [table], status, note, None
        if self.profile.write_enabled:
            with engine.begin() as conn:
                for r in rows:
                    conn.execute(text(f"insert into ifa2.{table}(business_date, row_key, ts_code, title, url, rec_time, payload) values (:business_date, :row_key, :ts_code, :title, :url, :rec_time, CAST(:payload as jsonb)) on conflict (business_date, row_key) do update set ts_code=excluded.ts_code, title=excluded.title, url=excluded.url, rec_time=excluded.rec_time, payload=excluded.payload"), {'business_date': business_date, 'row_key': r['row_key'], 'ts_code': r.get('ts_code'), 'title': r.get('title'), 'url': r.get('url'), 'rec_time': r.get('rec_time'), 'payload': json.dumps(r, ensure_ascii=False, default=str)})
        return len(rows), [table], status, note, None

    def _write_news_rows(self, table: str, business_date: str, rows: list[dict], status: str, note: str):
        if not rows:
            return 0, [table], status, note, None
        if self.profile.write_enabled:
            with engine.begin() as conn:
                for r in rows:
                    conn.execute(text(f"insert into ifa2.{table}(business_date, row_key, src, news_time, title, content_hash, payload) values (:business_date, :row_key, :src, :news_time, :title, :content_hash, CAST(:payload as jsonb)) on conflict (business_date, row_key) do update set src=excluded.src, news_time=excluded.news_time, title=excluded.title, content_hash=excluded.content_hash, payload=excluded.payload"), {'business_date': business_date, 'row_key': r['row_key'], 'src': r.get('src'), 'news_time': r.get('datetime'), 'title': r.get('title'), 'content_hash': r.get('content_hash'), 'payload': json.dumps(r, ensure_ascii=False, default=str)})
        return len(rows), [table], status, note, None

    def _write_research_report_rows(self, table: str, business_date: str, rows: list[dict], status: str, note: str):
        if not rows:
            return 0, [table], status, note, None
        if self.profile.write_enabled:
            with engine.begin() as conn:
                for r in rows:
                    conn.execute(text(f"insert into ifa2.{table}(business_date, row_key, ts_code, title, report_type, inst_csname, author, payload) values (:business_date, :row_key, :ts_code, :title, :report_type, :inst_csname, :author, CAST(:payload as jsonb)) on conflict (business_date, row_key) do update set ts_code=excluded.ts_code, title=excluded.title, report_type=excluded.report_type, inst_csname=excluded.inst_csname, author=excluded.author, payload=excluded.payload"), {'business_date': business_date, 'row_key': r['row_key'], 'ts_code': r.get('ts_code'), 'title': r.get('title'), 'report_type': r.get('report_type'), 'inst_csname': r.get('inst_csname'), 'author': r.get('author'), 'payload': json.dumps(r, ensure_ascii=False, default=str)})
        return len(rows), [table], status, note, None

    def _write_investor_qa_rows(self, table: str, business_date: str, rows: list[dict], status: str, note: str):
        if not rows:
            return 0, [table], status, note, None
        if self.profile.write_enabled:
            with engine.begin() as conn:
                for r in rows:
                    conn.execute(text(f"insert into ifa2.{table}(business_date, row_key, exchange_source, ts_code, pub_time, q_hash, a_hash, payload) values (:business_date, :row_key, :exchange_source, :ts_code, :pub_time, :q_hash, :a_hash, CAST(:payload as jsonb)) on conflict (business_date, row_key) do update set exchange_source=excluded.exchange_source, ts_code=excluded.ts_code, pub_time=excluded.pub_time, q_hash=excluded.q_hash, a_hash=excluded.a_hash, payload=excluded.payload"), {'business_date': business_date, 'row_key': r['row_key'], 'exchange_source': r.get('exchange_source'), 'ts_code': r.get('ts_code'), 'pub_time': r.get('pub_time'), 'q_hash': r.get('q_hash'), 'a_hash': r.get('a_hash'), 'payload': json.dumps(r, ensure_ascii=False, default=str)})
        return len(rows), [table], status, note, None

    def _write_dragon_tiger_rows(self, table: str, business_date: str, rows: list[dict], status: str, note: str):
        if not rows:
            return 0, [table], status, note, None
        if self.profile.write_enabled:
            with engine.begin() as conn:
                for r in rows:
                    conn.execute(text(f"insert into ifa2.{table}(business_date, row_key, ts_code, reason, payload) values (:business_date, :row_key, :ts_code, :reason, CAST(:payload as jsonb)) on conflict (business_date, row_key) do update set ts_code=excluded.ts_code, reason=excluded.reason, payload=excluded.payload"), {'business_date': business_date, 'row_key': r['row_key'], 'ts_code': r.get('ts_code'), 'reason': r.get('reason'), 'payload': json.dumps(r, ensure_ascii=False, default=str)})
        return len(rows), [table], status, note, None

    def _write_limit_up_detail_rows(self, table: str, business_date: str, rows: list[dict], status: str, note: str):
        if not rows:
            return 0, [table], status, note, None
        if self.profile.write_enabled:
            with engine.begin() as conn:
                for r in rows:
                    conn.execute(text(f"insert into ifa2.{table}(business_date, row_key, ts_code, limit_type, exchange, first_time, last_time, limit_times, payload) values (:business_date, :row_key, :ts_code, :limit_type, :exchange, :first_time, :last_time, :limit_times, CAST(:payload as jsonb)) on conflict (business_date, row_key) do update set ts_code=excluded.ts_code, limit_type=excluded.limit_type, exchange=excluded.exchange, first_time=excluded.first_time, last_time=excluded.last_time, limit_times=excluded.limit_times, payload=excluded.payload"), {'business_date': business_date, 'row_key': r['row_key'], 'ts_code': r.get('ts_code'), 'limit_type': r.get('limit') or r.get('limit_type_shard'), 'exchange': r.get('exchange'), 'first_time': r.get('first_time'), 'last_time': r.get('last_time'), 'limit_times': r.get('limit_times'), 'payload': json.dumps(r, ensure_ascii=False, default=str)})
        return len(rows), [table], status, note, None

    def _write_limit_up_down_status_row(self, table: str, business_date: str, row: dict[str, Any], status: str, note: str):
        if self.profile.write_enabled:
            with engine.begin() as conn:
                conn.execute(text(f"insert into ifa2.{table}(business_date, payload) values (:business_date, CAST(:payload as jsonb)) on conflict (business_date) do update set payload=excluded.payload"), {'business_date': business_date, 'payload': json.dumps(row, ensure_ascii=False, default=str)})
        return 1 if row else 0, [table], status, note, None

    def _write_sector_performance_rows(self, table: str, business_date: str, rows: list[dict], status: str, note: str):
        if not rows:
            return 0, [table], status, note, None
        if self.profile.write_enabled:
            with engine.begin() as conn:
                for r in rows:
                    sector_code = r.get('ts_code') or r.get('sector_code')
                    conn.execute(text(f"insert into ifa2.{table}(business_date, sector_code, payload) values (:business_date, :sector_code, CAST(:payload as jsonb)) on conflict (business_date, sector_code) do update set payload=excluded.payload"), {'business_date': business_date, 'sector_code': sector_code, 'payload': json.dumps(r, ensure_ascii=False, default=str)})
        return len(rows), [table], status, note, None

    def _write_singleton_rows(self, table: str, business_date: str, rows: list[dict], note: str):
        if not rows:
            return 0, [table], 'incomplete', 'source/history returned no rows', None
        row = rows[0]
        if self.profile.write_enabled:
            with engine.begin() as conn:
                conn.execute(text(f"insert into ifa2.{table}(business_date, payload) values (:business_date, CAST(:payload as jsonb)) on conflict (business_date) do update set payload=excluded.payload"), {'business_date': business_date, 'payload': json.dumps(row, ensure_ascii=False, default=str)})
        return 1, [table], 'completed', note, None

    def _write_non_equity_rows(self, table: str, business_date: str, rows: list[dict]):
        if self.profile.write_enabled:
            with engine.begin() as conn:
                for r in rows:
                    ts_code = r.get('ts_code')
                    family_code = (ts_code.split('.')[1] if ts_code and '.' in ts_code else 'futures')
                    conn.execute(text(f"insert into ifa2.{table}(business_date, family_code, ts_code, payload) values (:business_date, :family_code, :ts_code, CAST(:payload as jsonb)) on conflict (business_date, family_code, ts_code) do update set payload=excluded.payload"), {'business_date': business_date, 'family_code': family_code, 'ts_code': ts_code, 'payload': json.dumps(r, ensure_ascii=False, default=str)})
        return len(rows), [table], 'completed', 'source-aligned non-equity daily archive written without forcing business over-split', None

    def _write_event_rows(self, table: str, business_date: str, rows: list[dict], time_col: str, note: str):
        if not rows:
            return 0, [table], 'incomplete', 'source/history returned no rows', None
        if self.profile.write_enabled:
            with engine.begin() as conn:
                for r in rows:
                    row_key = self._build_event_row_key(r, time_col)
                    conn.execute(text(f"insert into ifa2.{table}(business_date, row_key, {time_col}, event_type, symbol, payload) values (:business_date, :row_key, :event_time, :event_type, :symbol, CAST(:payload as jsonb)) on conflict (business_date, row_key) do update set {time_col}=excluded.{time_col}, event_type=excluded.event_type, symbol=excluded.symbol, payload=excluded.payload"), {'business_date': business_date, 'row_key': row_key, 'event_time': r[time_col], 'event_type': r.get('event_type'), 'symbol': r.get('symbol'), 'payload': json.dumps(r, ensure_ascii=False, default=str)})
        return len(rows), [table], 'completed', note, None

    def _build_event_row_key(self, row: dict, time_col: str) -> str:
        return '|'.join([str(row.get(time_col) or ''), str(row.get('event_type') or ''), str(row.get('symbol') or ''), str(row.get('source') or ''), str(row.get('title') or '')])

    def _write_snapshot_rows(self, table: str, business_date: str, rows: list[dict], key_cols: list[str], snapshot_col: str, source_time_col: str, note: str):
        if not rows:
            return 0, [table], 'incomplete', 'source/history returned no rows', None
        if self.profile.write_enabled:
            with engine.begin() as conn:
                for r in rows:
                    params = {'business_date': business_date, 'payload': json.dumps(r, ensure_ascii=False, default=str), 'snapshot_time': r[source_time_col]}
                    for key in key_cols:
                        params[key] = r[key]
                    key_columns = ', '.join(key_cols)
                    value_columns = ', '.join([f':{key}' for key in key_cols])
                    conflict_columns = ', '.join(['business_date', *key_cols])
                    update_columns = ', '.join([f'{key}=excluded.{key}' for key in key_cols] + [f'{snapshot_col}=excluded.{snapshot_col}', 'payload=excluded.payload'])
                    conn.execute(text(f"insert into ifa2.{table}(business_date, {key_columns}, {snapshot_col}, payload) values (:business_date, {value_columns}, :snapshot_time, CAST(:payload as jsonb)) on conflict ({conflict_columns}) do update set {update_columns}"), params)
        return len(rows), [table], 'completed', note, None

    def _write_macro_rows(self, table: str, business_date: str, rows: list[dict]):
        if self.profile.write_enabled:
            with engine.begin() as conn:
                for r in rows:
                    conn.execute(text(f"insert into ifa2.{table}(business_date, macro_series, payload) values (:business_date, :macro_series, CAST(:payload as jsonb)) on conflict (business_date, macro_series) do update set payload=excluded.payload"), {'business_date': business_date, 'macro_series': r['macro_series'], 'payload': json.dumps(r, ensure_ascii=False, default=str)})
        return len(rows), [table], 'completed', 'macro daily snapshot archived from retained source-side truth boundary', None

    def _write_daily_rows(self, table: str, business_date: str, rows: list[dict], note: str):
        if table == 'ifa_archive_index_daily':
            return self._write_json_rows(table, business_date, rows, 'ts_code', note=note)
        if table == 'ifa_archive_macro_daily':
            return self._write_macro_rows(table, business_date, rows)
        raise ValueError(f'unsupported direct daily write table: {table}')

    def _write_intraday_rows(self, meta: dict[str, Any], business_date: str, rows: list[dict], note: str):
        table = meta['dest_table']
        archive_key_col = meta.get('archive_key_col', 'ts_code')
        if not rows:
            return 0, [table], 'incomplete', 'source/history returned no intraday rows', None
        if self.profile.write_enabled:
            with engine.begin() as conn:
                for r in rows:
                    key_value = r.get(archive_key_col) or r.get('instrument_code') or r.get(meta.get('instrument_key', archive_key_col))
                    conn.execute(text(f"insert into ifa2.{table}(business_date, {archive_key_col}, bar_time, payload) values (:business_date, :key_value, :bar_time, CAST(:payload as jsonb)) on conflict (business_date, {archive_key_col}, bar_time) do update set payload=excluded.payload"), {'business_date': business_date, 'key_value': key_value, 'bar_time': r['bar_time'], 'payload': json.dumps(r, ensure_ascii=False, default=str)})
        return len(rows), [table], 'completed', note, None

    def _persist_profile(self):
        with engine.begin() as conn:
            conn.execute(text("""
                insert into ifa2.ifa_archive_profiles(profile_name, profile_path, profile_json, updated_at)
                values (:name, :path, CAST(:profile_json as jsonb), now())
                on conflict (profile_name)
                do update set profile_path=excluded.profile_path, profile_json=excluded.profile_json, updated_at=now()
            """), {'name': self.profile.profile_name, 'path': self.profile_path, 'profile_json': json.dumps(self.profile.__dict__, ensure_ascii=False)})

    def _create_run(self, status: str, trigger_source: str = 'manual_profile', notes: str | None = None):
        with engine.begin() as conn:
            conn.execute(text("""
                insert into ifa2.ifa_archive_runs(run_id, trigger_source, profile_name, profile_path, mode, start_time, status, notes)
                values (:run_id, :trigger_source, :profile_name, :profile_path, :mode, now(), :status, :notes)
            """), {'run_id': str(self.run_id), 'trigger_source': trigger_source, 'profile_name': self.profile.profile_name, 'profile_path': self.profile_path, 'mode': self.profile.mode, 'status': status, 'notes': notes or self.profile.notes})

    def _finish_run(self, status: str, notes: str | None = None, error_text: str | None = None):
        with engine.begin() as conn:
            conn.execute(text("""
                update ifa2.ifa_archive_runs
                set end_time = now(),
                    duration_ms = greatest(0, floor(extract(epoch from (now() - start_time)) * 1000))::bigint,
                    status = :status,
                    notes = coalesce(:notes, notes),
                    error_text = :error_text
                where run_id = :run_id
            """), {'run_id': str(self.run_id), 'status': status, 'notes': notes, 'error_text': error_text})

    def _write_item(self, family_name: str, frequency: str, business_date: str | None, status: str, rows_written: int, tables_touched: list[str], notes: str | None = None, error_text: str | None = None):
        with engine.begin() as conn:
            conn.execute(text("""
                insert into ifa2.ifa_archive_run_items(id, run_id, family_name, frequency, coverage_scope, business_date, status, rows_written, tables_touched, notes, error_text)
                values (:id, :run_id, :family_name, :frequency, :coverage_scope, :business_date, :status, :rows_written, CAST(:tables_touched as jsonb), :notes, :error_text)
            """), {'id': str(uuid.uuid4()), 'run_id': str(self.run_id), 'family_name': family_name, 'frequency': frequency, 'coverage_scope': self._coverage_scope(), 'business_date': business_date, 'status': status, 'rows_written': rows_written, 'tables_touched': json.dumps(tables_touched), 'notes': notes, 'error_text': error_text})

    def _upsert_completeness(self, business_date: str, family_name: str, frequency: str, coverage_scope: str, status: str, row_count: int, detail_text: str | None = None):
        with engine.begin() as conn:
            conn.execute(text("""
                insert into ifa2.ifa_archive_completeness(id, business_date, family_name, frequency, coverage_scope, status, source_mode, last_run_id, row_count, retry_after, last_error, updated_at)
                values (:id, :business_date, :family_name, :frequency, :coverage_scope, :status, :source_mode, :last_run_id, :row_count, :retry_after, :last_error, now())
                on conflict (business_date, family_name, frequency, coverage_scope)
                do update set status=excluded.status, source_mode=excluded.source_mode, last_run_id=excluded.last_run_id, row_count=excluded.row_count, retry_after=excluded.retry_after, last_error=excluded.last_error, updated_at=now()
            """), {'id': str(uuid.uuid4()), 'business_date': business_date, 'family_name': family_name, 'frequency': frequency, 'coverage_scope': coverage_scope, 'status': status, 'source_mode': self.profile.mode, 'last_run_id': str(self.run_id), 'row_count': row_count, 'retry_after': None, 'last_error': None if status == 'completed' else detail_text})
        self._sync_repair_queue(business_date, family_name, frequency, coverage_scope, status, detail_text)

    def _sync_repair_queue(self, business_date: str, family_name: str, frequency: str, coverage_scope: str, status: str, detail_text: str | None):
        existing = self._get_repair_queue_row(business_date, family_name, frequency)
        if status in NON_COMPLETED_STATUSES:
            reason = detail_text or f'auto-enqueued because completeness status={status}'
            policy = build_repair_state(existing, family_name, status, reason)
            with engine.begin() as conn:
                conn.execute(text("""
                    insert into ifa2.ifa_archive_repair_queue(
                      id, business_date, family_name, frequency, coverage_scope, status, reason, reason_code, actionability,
                      priority, urgency, retry_count, retry_after, first_seen_at, last_attempt_at,
                      last_observed_status, escalation_level, last_error, last_run_id, updated_at,
                      claim_id, claimed_at, claimed_by, claim_expires_at
                    )
                    values (
                      :id, :business_date, :family_name, :frequency, :coverage_scope, 'pending', :reason, :reason_code, :actionability,
                      :priority, :urgency, :retry_count, :retry_after, now(), now(),
                      :last_observed_status, :escalation_level, :last_error, :last_run_id, now(),
                      null, null, null, null
                    )
                    on conflict (business_date, family_name, frequency, coverage_scope)
                    do update set status='pending', reason=excluded.reason, reason_code=excluded.reason_code, actionability=excluded.actionability,
                      priority=excluded.priority, urgency=excluded.urgency, retry_count=excluded.retry_count,
                      retry_after=excluded.retry_after, claim_id=null, claimed_at=null, claimed_by=null, claim_expires_at=null,
                      last_attempt_at=excluded.last_attempt_at,
                      last_observed_status=excluded.last_observed_status, escalation_level=excluded.escalation_level,
                      last_error=excluded.last_error, last_run_id=excluded.last_run_id, updated_at=now()
                """), {'id': str(uuid.uuid4()), 'business_date': business_date, 'family_name': family_name, 'frequency': frequency, 'coverage_scope': coverage_scope, 'reason': reason, 'reason_code': policy['reason_code'], 'actionability': policy['actionability'], 'priority': policy['priority'], 'urgency': policy['urgency'], 'retry_count': policy['retry_count'], 'retry_after': policy['retry_after'], 'last_observed_status': status, 'escalation_level': policy['escalation_level'], 'last_error': policy['last_error'], 'last_run_id': str(self.run_id)})
                conn.execute(text("""
                    update ifa2.ifa_archive_completeness
                    set retry_after = :retry_after,
                        last_error = :last_error,
                        updated_at = now()
                    where business_date = :business_date and family_name = :family_name and frequency = :frequency and coverage_scope = :coverage_scope
                """), {'retry_after': policy['retry_after'], 'last_error': reason, 'business_date': business_date, 'family_name': family_name, 'frequency': frequency, 'coverage_scope': coverage_scope})
            return
        with engine.begin() as conn:
            conn.execute(text("""
                update ifa2.ifa_archive_repair_queue
                set status = 'completed',
                    reason = :reason,
                    reason_code = 'resolved',
                    actionability = coalesce(actionability, 'actionable'),
                    urgency = 'low',
                    retry_after = null,
                    claim_id = null,
                    claimed_at = null,
                    claimed_by = null,
                    claim_expires_at = null,
                    last_attempt_at = now(),
                    last_observed_status = :last_observed_status,
                    last_error = null,
                    last_run_id = :last_run_id,
                    updated_at = now()
                where business_date = :business_date and family_name = :family_name and frequency = :frequency and coverage_scope = :coverage_scope
            """), {'business_date': business_date, 'family_name': family_name, 'frequency': frequency, 'coverage_scope': coverage_scope, 'reason': 'repaired/completed by latest Archive V2 run', 'last_observed_status': status, 'last_run_id': str(self.run_id)})
            conn.execute(text("""
                update ifa2.ifa_archive_completeness
                set retry_after = null,
                    last_error = null,
                    updated_at = now()
                where business_date = :business_date and family_name = :family_name and frequency = :frequency and coverage_scope = :coverage_scope and status = 'completed'
            """), {'business_date': business_date, 'family_name': family_name, 'frequency': frequency, 'coverage_scope': coverage_scope})

    def _decorate_note(self, family_name: str, note: str | None) -> str | None:
        identity = IDENTITY_POLICY_BY_FAMILY.get(family_name)
        if not identity:
            return note
        return f'{note} | identity={identity}' if note else f'identity={identity}'

    def _coverage_scope(self) -> str:
        return 'broad_market' if self.profile.broad_market else 'profile_scope'
