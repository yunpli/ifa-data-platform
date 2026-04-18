from __future__ import annotations

from sqlalchemy import create_engine, text

DATABASE_URL = 'postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp'
engine = create_engine(DATABASE_URL)

DDL = [
    """
    create table if not exists ifa2.ifa_archive_runs (
      run_id uuid primary key,
      trigger_source text not null,
      profile_name text not null,
      profile_path text,
      mode text not null,
      start_time timestamptz not null default now(),
      end_time timestamptz,
      duration_ms bigint,
      status text not null,
      notes text,
      error_text text,
      created_at timestamptz not null default now()
    )
    """,
    """
    create table if not exists ifa2.ifa_archive_run_items (
      id uuid primary key,
      run_id uuid not null references ifa2.ifa_archive_runs(run_id),
      family_name text not null,
      frequency text not null,
      coverage_scope text,
      business_date date,
      status text not null,
      rows_written bigint not null default 0,
      tables_touched jsonb not null default '[]'::jsonb,
      notes text,
      error_text text,
      created_at timestamptz not null default now()
    )
    """,
    """
    create table if not exists ifa2.ifa_archive_completeness (
      id uuid primary key,
      business_date date not null,
      family_name text not null,
      frequency text not null,
      coverage_scope text,
      status text not null,
      source_mode text,
      last_run_id uuid,
      row_count bigint not null default 0,
      retry_after timestamptz,
      last_error text,
      updated_at timestamptz not null default now(),
      unique (business_date, family_name, frequency, coverage_scope)
    )
    """,
    """
    create table if not exists ifa2.ifa_archive_profiles (
      profile_name text primary key,
      profile_path text,
      profile_json jsonb not null,
      updated_at timestamptz not null default now()
    )
    """,
    """
    create table if not exists ifa2.ifa_archive_repair_queue (
      id uuid primary key,
      business_date date,
      family_name text not null,
      frequency text not null,
      coverage_scope text,
      status text not null,
      reason text,
      retry_after timestamptz,
      last_run_id uuid,
      updated_at timestamptz not null default now()
    )
    """,
    """
    create table if not exists ifa2.ifa_archive_equity_daily (
      business_date date not null,
      ts_code text not null,
      payload jsonb not null,
      created_at timestamptz not null default now(),
      primary key (business_date, ts_code)
    )
    """,
    """
    create table if not exists ifa2.ifa_archive_index_daily (
      business_date date not null,
      ts_code text not null,
      payload jsonb not null,
      created_at timestamptz not null default now(),
      primary key (business_date, ts_code)
    )
    """,
    """
    create table if not exists ifa2.ifa_archive_etf_daily (
      business_date date not null,
      ts_code text not null,
      payload jsonb not null,
      created_at timestamptz not null default now(),
      primary key (business_date, ts_code)
    )
    """,
    """
    create table if not exists ifa2.ifa_archive_non_equity_daily (
      business_date date not null,
      family_code text not null,
      ts_code text not null,
      payload jsonb not null,
      created_at timestamptz not null default now(),
      primary key (business_date, family_code, ts_code)
    )
    """,
    """
    create table if not exists ifa2.ifa_archive_macro_daily (
      business_date date not null,
      macro_series text not null,
      payload jsonb not null,
      created_at timestamptz not null default now(),
      primary key (business_date, macro_series)
    )
    """,
    """
    create table if not exists ifa2.ifa_archive_announcements_daily (
      business_date date not null,
      ts_code text not null,
      title text not null,
      payload jsonb not null,
      created_at timestamptz not null default now(),
      primary key (business_date, ts_code, title)
    )
    """,
    """
    create table if not exists ifa2.ifa_archive_news_daily (
      business_date date not null,
      news_time timestamptz not null,
      title text not null,
      payload jsonb not null,
      created_at timestamptz not null default now(),
      primary key (business_date, news_time, title)
    )
    """,
    """
    create table if not exists ifa2.ifa_archive_research_reports_daily (
      business_date date not null,
      ts_code text not null,
      title text not null,
      payload jsonb not null,
      created_at timestamptz not null default now(),
      primary key (business_date, ts_code, title)
    )
    """,
    """
    create table if not exists ifa2.ifa_archive_investor_qa_daily (
      business_date date not null,
      ts_code text not null,
      pub_time timestamptz not null,
      payload jsonb not null,
      created_at timestamptz not null default now(),
      primary key (business_date, ts_code, pub_time)
    )
    """,
    """
    create table if not exists ifa2.ifa_archive_dragon_tiger_daily (
      business_date date not null,
      ts_code text not null,
      payload jsonb not null,
      created_at timestamptz not null default now(),
      primary key (business_date, ts_code)
    )
    """,
    """
    create table if not exists ifa2.ifa_archive_limit_up_detail_daily (
      business_date date not null,
      ts_code text not null,
      payload jsonb not null,
      created_at timestamptz not null default now(),
      primary key (business_date, ts_code)
    )
    """,
    """
    create table if not exists ifa2.ifa_archive_limit_up_down_status_daily (
      business_date date primary key,
      payload jsonb not null,
      created_at timestamptz not null default now()
    )
    """,
    """
    create table if not exists ifa2.ifa_archive_sector_performance_daily (
      business_date date not null,
      sector_code text not null,
      payload jsonb not null,
      created_at timestamptz not null default now(),
      primary key (business_date, sector_code)
    )
    """,
    """
    create table if not exists ifa2.ifa_archive_highfreq_event_stream_daily (
      business_date date not null,
      row_key text not null,
      event_time timestamptz not null,
      event_type text not null,
      symbol text,
      payload jsonb not null,
      created_at timestamptz not null default now(),
      primary key (business_date, row_key)
    )
    """,
    """
    create table if not exists ifa2.ifa_archive_highfreq_limit_event_stream_daily (
      business_date date not null,
      row_key text not null,
      trade_time timestamptz not null,
      event_type text not null,
      symbol text,
      payload jsonb not null,
      created_at timestamptz not null default now(),
      primary key (business_date, row_key)
    )
    """,
    """
    create table if not exists ifa2.ifa_archive_highfreq_sector_breadth_daily (
      business_date date not null,
      sector_code text not null,
      snapshot_time timestamptz not null,
      payload jsonb not null,
      created_at timestamptz not null default now(),
      primary key (business_date, sector_code)
    )
    """,
    """
    create table if not exists ifa2.ifa_archive_highfreq_sector_heat_daily (
      business_date date not null,
      sector_code text not null,
      snapshot_time timestamptz not null,
      payload jsonb not null,
      created_at timestamptz not null default now(),
      primary key (business_date, sector_code)
    )
    """,
    """
    create table if not exists ifa2.ifa_archive_highfreq_leader_candidate_daily (
      business_date date not null,
      symbol text not null,
      snapshot_time timestamptz not null,
      payload jsonb not null,
      created_at timestamptz not null default now(),
      primary key (business_date, symbol)
    )
    """,
    """
    create table if not exists ifa2.ifa_archive_highfreq_intraday_signal_state_daily (
      business_date date not null,
      scope_key text not null,
      snapshot_time timestamptz not null,
      payload jsonb not null,
      created_at timestamptz not null default now(),
      primary key (business_date, scope_key)
    )
    """,
]


def ensure_schema() -> None:
    with engine.begin() as conn:
        for ddl in DDL:
            conn.execute(text(ddl))
