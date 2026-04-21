from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

ANNOUNCEMENTS_SUSPICIOUS_NEAR_CAP = 1950
NEWS_SUSPICIOUS_NEAR_CAP = 1400
RESEARCH_REPORT_SUSPICIOUS_NEAR_CAP = 900
INVESTOR_QA_SUSPICIOUS_LOW_ROWS = 3

NEWS_SOURCE_BUNDLE = [
    'sina',
    'wallstreetcn',
    '10jqka',
    'eastmoney',
    'yuncaijing',
    'fenghuang',
    'jinrongjie',
    'cls',
    'yicai',
]

RESEARCH_REPORT_TYPES = [
    '个股研报',
    '行业研报',
]

SECTOR_INDEX_TYPES = [
    'N',
    'S',
    'TH',
    'ST',
    'R',
]
SECTOR_INDEX_TYPES_EXCLUDED = [
    'I',
    'BB',
]

LIMIT_LIST_LIMIT_TYPES = ['U', 'Z', 'D']
LIMIT_LIST_EXCHANGES = ['SH', 'SZ', 'BJ']


@dataclass(frozen=True)
class BusinessDailyContract:
    family_name: str
    source_endpoints: tuple[str, ...]
    source_mode: str
    shard_strategy: str
    dedupe_identity: str
    zero_row_policy: str
    completeness_rule: str
    archive_table_name: str


BUSINESS_DAILY_CONTRACTS: dict[str, BusinessDailyContract] = {
    'announcements_daily': BusinessDailyContract(
        family_name='announcements_daily',
        source_endpoints=('anns_d',),
        source_mode='single_day_bulk',
        shard_strategy='direct ann_date bulk pull; treat returned bulk as authoritative for production account behavior',
        dedupe_identity='(business_date, ts_code, title, url, rec_time?) -> row_key',
        zero_row_policy='incomplete on zero rows; truthful zero not assumed for active trading day announcements',
        completeness_rule='completed when direct ann_date bulk yields rows; incomplete only on zero-row or exact-cap suspicious edge',
        archive_table_name='ifa_archive_announcements_daily',
    ),
    'news_daily': BusinessDailyContract(
        family_name='news_daily',
        source_endpoints=('news',),
        source_mode='time_window_stream',
        shard_strategy='explicit src bundle × day windows; recursively split windows near cap',
        dedupe_identity='(business_date, src, datetime, title, content_hash) -> row_key',
        zero_row_policy='completed_zero only after all configured sources and required windows are exhausted',
        completeness_rule='completed when all configured sources/windows checked with no suspicious near-cap windows left',
        archive_table_name='ifa_archive_news_daily',
    ),
    'research_reports_daily': BusinessDailyContract(
        family_name='research_reports_daily',
        source_endpoints=('research_report',),
        source_mode='single_day_bulk',
        shard_strategy='trade_date bulk first; mark suspicious only if near documented cap',
        dedupe_identity='(business_date, report_type, inst_csname, ts_code, title, author) -> row_key',
        zero_row_policy='completed_zero after direct trade_date bulk is exhausted',
        completeness_rule='completed when direct trade_date bulk succeeds below suspicious cap; incomplete only on cap-pressure/path failure',
        archive_table_name='ifa_archive_research_reports_daily',
    ),
    'investor_qa_daily': BusinessDailyContract(
        family_name='investor_qa_daily',
        source_endpoints=('irm_qa_sh', 'irm_qa_sz'),
        source_mode='source_plus_aggregate',
        shard_strategy='SH+SZ trade_date first; suspicious low/zero fallback to pub_date windows per exchange',
        dedupe_identity='(business_date, exchange_source, ts_code, pub_time, q_hash, a_hash) -> row_key',
        zero_row_policy='completed_zero only after SH+SZ plus pub_date fallback are exhausted',
        completeness_rule='completed when both exchanges and fallback branches are checked',
        archive_table_name='ifa_archive_investor_qa_daily',
    ),
    'dragon_tiger_daily': BusinessDailyContract(
        family_name='dragon_tiger_daily',
        source_endpoints=('top_list',),
        source_mode='single_day_bulk',
        shard_strategy='trade_date bulk only',
        dedupe_identity='(business_date, ts_code, reason, net_amount, l_amount) -> row_key',
        zero_row_policy='incomplete on zero rows for active trading day unless source truth proves true empty day',
        completeness_rule='completed when direct trade_date pull succeeds and rows persist under reason-aware identity',
        archive_table_name='ifa_archive_dragon_tiger_daily',
    ),
    'limit_up_detail_daily': BusinessDailyContract(
        family_name='limit_up_detail_daily',
        source_endpoints=('limit_list_d',),
        source_mode='single_day_bulk',
        shard_strategy='trade_date bulk first; normalize U/Z rows from canonical raw limit_list_d',
        dedupe_identity='(business_date, ts_code, limit, first_time, last_time, limit_times) -> row_key',
        zero_row_policy='incomplete on zero rows for active trading day unless direct bulk proves true empty day',
        completeness_rule='completed when direct trade_date bulk succeeds and canonical U/Z rows persist',
        archive_table_name='ifa_archive_limit_up_detail_daily',
    ),
    'limit_up_down_status_daily': BusinessDailyContract(
        family_name='limit_up_down_status_daily',
        source_endpoints=('limit_list_d',),
        source_mode='source_plus_aggregate',
        shard_strategy='reuse canonical limit_list_d trade_date bulk pull and aggregate internally',
        dedupe_identity='(business_date)',
        zero_row_policy='completed_zero only after canonical raw bulk is exhausted and true empty is established',
        completeness_rule='completed when canonical raw bulk was checked and internal aggregate generated',
        archive_table_name='ifa_archive_limit_up_down_status_daily',
    ),
    'sector_performance_daily': BusinessDailyContract(
        family_name='sector_performance_daily',
        source_endpoints=('ths_index', 'ths_daily'),
        source_mode='single_day_bulk',
        shard_strategy='ths_index(exchange=A,type in [N,S,TH,ST,R]) supported sector/theme universe + one ths_daily(trade_date) bulk pull; exclude low-support I/BB classes from production expected universe',
        dedupe_identity='(business_date, sector_code)',
        zero_row_policy='incomplete on zero rows unless supported expected universe itself is empty',
        completeness_rule='completed when supported-universe coverage >= 0.90 after one trade_date bulk pull; I/BB are excluded from production expected universe as structurally low-support classes',
        archive_table_name='ifa_archive_sector_performance_daily',
    ),
}


def assert_archive_namespace(table_name: str) -> None:
    if not table_name.startswith('ifa_archive_'):
        raise ValueError(f'Archive V2 table must use ifa_archive_* namespace: {table_name}')


for _contract in BUSINESS_DAILY_CONTRACTS.values():
    assert_archive_namespace(_contract.archive_table_name)


def stable_hash(*parts: Any) -> str:
    raw = '||'.join('' if p is None else str(p) for p in parts)
    return hashlib.md5(raw.encode('utf-8')).hexdigest()
