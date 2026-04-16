from __future__ import annotations

import json
from pathlib import Path
from sqlalchemy import create_engine, text

DB_URL = 'postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp'
engine = create_engine(DB_URL)
OUT = Path('artifacts/full_chain_analysis_2026-04-16_0905.json')

PLATFORM_WORKERS = {
    'lowfreq': {
        'tables': [
            'unified_runtime_runs', 'runtime_worker_state', 'job_runs', 'lowfreq_runs',
            'trade_cal_current', 'trade_cal_history', 'stock_basic_current', 'stock_basic_history',
            'index_basic_current', 'index_basic_history', 'fund_basic_etf_current', 'fund_basic_etf_history',
            'sw_industry_mapping_current', 'sw_industry_mapping_history', 'announcements_current', 'announcements_history',
            'news_current', 'news_history', 'research_reports_current', 'research_reports_history',
            'investor_qa_current', 'investor_qa_history', 'index_weight_current', 'index_weight_history',
            'etf_daily_basic_current', 'etf_daily_basic_history', 'share_float_current', 'share_float_history',
            'company_basic_current', 'company_basic_history', 'stk_managers_current', 'stk_managers_history',
            'new_share_current', 'new_share_history', 'name_change_current', 'name_change_history',
            'top10_holders_current', 'top10_holders_history', 'top10_floatholders_current', 'top10_floatholders_history',
            'pledge_stat_current', 'pledge_stat_history'
        ]
    },
    'midfreq': {
        'tables': [
            'unified_runtime_runs', 'runtime_worker_state', 'job_runs', 'midfreq_execution_summary',
            'equity_daily_bar_current', 'equity_daily_bar_history', 'index_daily_bar_current', 'index_daily_bar_history',
            'etf_daily_bar_current', 'etf_daily_bar_history', 'northbound_flow_current', 'northbound_flow_history',
            'limit_up_down_status_current', 'limit_up_down_status_history', 'margin_financing_current', 'margin_financing_history',
            'southbound_flow_current', 'southbound_flow_history', 'turnover_rate_current', 'turnover_rate_history',
            'main_force_flow_current', 'main_force_flow_history', 'sector_performance_current', 'sector_performance_history',
            'dragon_tiger_list_current', 'dragon_tiger_list_history', 'limit_up_detail_current', 'limit_up_detail_history'
        ]
    },
    'highfreq': {
        'tables': [
            'unified_runtime_runs', 'runtime_worker_state', 'job_runs', 'highfreq_execution_summary', 'highfreq_runs',
            'highfreq_stock_1m_working', 'highfreq_index_1m_working', 'highfreq_proxy_1m_working', 'highfreq_futures_minute_working',
            'highfreq_open_auction_working', 'highfreq_close_auction_working', 'highfreq_event_stream_working',
            'highfreq_sector_breadth_working', 'highfreq_sector_heat_working', 'highfreq_leader_candidate_working',
            'highfreq_intraday_signal_state_working', 'highfreq_limit_event_stream_working', 'highfreq_active_scope', 'highfreq_dynamic_candidate'
        ]
    },
    'archive': {
        'tables': [
            'unified_runtime_runs', 'runtime_worker_state', 'archive_runs', 'archive_checkpoints', 'archive_target_catchup', 'archive_summary_daily',
            'stock_15min_history', 'stock_minute_history', 'futures_15min_history', 'futures_minute_history',
            'commodity_15min_history', 'commodity_minute_history', 'precious_metal_15min_history', 'precious_metal_minute_history',
            'futures_history', 'stock_daily_history', 'macro_history'
        ]
    },
}

BL_TABLES = ['focus_lists', 'focus_list_items', 'focus_list_rules']
LIST_NAMES = ['default_key_focus', 'default_focus', 'default_tech_key_focus', 'default_tech_focus', 'default_archive_targets_15min', 'default_archive_targets_minute']


def count(conn, table):
    return conn.execute(text(f'select count(*) from ifa2."{table}"')).scalar_one()


def list_rows(conn):
    rows = conn.execute(text(
        "select fl.name, fl.list_type, fl.asset_type, fl.frequency_type, count(fli.id) as item_count "
        "from ifa2.focus_lists fl left join ifa2.focus_list_items fli on fl.id=fli.list_id "
        "where fl.name = any(:names) group by fl.name, fl.list_type, fl.asset_type, fl.frequency_type order by fl.name"
    ), {'names': LIST_NAMES}).mappings().all()
    return [dict(r) for r in rows]


def list_rule_rows(conn):
    rows = conn.execute(text(
        "select fl.name, fr.rule_key, fr.rule_value "
        "from ifa2.focus_lists fl join ifa2.focus_list_rules fr on fl.id=fr.list_id "
        "where fl.name = any(:names) order by fl.name, fr.rule_key"
    ), {'names': LIST_NAMES}).mappings().all()
    return [dict(r) for r in rows]


def latest_unified_run(conn, worker):
    row = conn.execute(text(
        "select id, lane, trigger_mode, status, governance_state, runtime_budget_sec, started_at, completed_at, duration_ms, tasks_executed, tables_updated, summary "
        "from ifa2.unified_runtime_runs where lane=:w order by started_at desc limit 1"
    ), {'w': worker}).mappings().first()
    return dict(row) if row else None

payload = {'business_layer': {}, 'workers': {}}
with engine.begin() as conn:
    payload['business_layer']['lists'] = list_rows(conn)
    payload['business_layer']['rules'] = list_rule_rows(conn)
    for worker, spec in PLATFORM_WORKERS.items():
        payload['workers'][worker] = {
            'latest_run': latest_unified_run(conn, worker),
            'table_counts': {t: count(conn, t) for t in spec['tables']},
        }
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
print(OUT)
