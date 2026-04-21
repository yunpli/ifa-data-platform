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
      dry_run boolean not null default false,
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
      would_write_rows bigint not null default 0,
      would_write_tables jsonb not null default '[]'::jsonb,
      family_expected_rows bigint,
      family_observed_rows bigint,
      family_coverage_ratio numeric,
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
      family_expected_rows bigint,
      family_observed_rows bigint,
      family_coverage_ratio numeric,
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
    alter table if exists ifa2.ifa_archive_runs add column if not exists dry_run boolean not null default false
    """,
    """
    alter table if exists ifa2.ifa_archive_run_items add column if not exists would_write_rows bigint not null default 0
    """,
    """
    alter table if exists ifa2.ifa_archive_run_items add column if not exists would_write_tables jsonb not null default '[]'::jsonb
    """,
    """
    alter table if exists ifa2.ifa_archive_run_items add column if not exists family_expected_rows bigint
    """,
    """
    alter table if exists ifa2.ifa_archive_run_items add column if not exists family_observed_rows bigint
    """,
    """
    alter table if exists ifa2.ifa_archive_run_items add column if not exists family_coverage_ratio numeric
    """,
    """
    alter table if exists ifa2.ifa_archive_completeness add column if not exists family_expected_rows bigint
    """,
    """
    alter table if exists ifa2.ifa_archive_completeness add column if not exists family_observed_rows bigint
    """,
    """
    alter table if exists ifa2.ifa_archive_completeness add column if not exists family_coverage_ratio numeric
    """,
    """
    create unique index if not exists uq_ifa_archive_repair_queue_target
      on ifa2.ifa_archive_repair_queue (business_date, family_name, frequency, coverage_scope)
    """,
    """
    alter table if exists ifa2.ifa_archive_repair_queue add column if not exists reason_code text
    """,
    """
    alter table if exists ifa2.ifa_archive_repair_queue add column if not exists actionability text not null default 'actionable'
    """,
    """
    alter table if exists ifa2.ifa_archive_repair_queue add column if not exists priority integer not null default 50
    """,
    """
    alter table if exists ifa2.ifa_archive_repair_queue add column if not exists urgency text not null default 'normal'
    """,
    """
    alter table if exists ifa2.ifa_archive_repair_queue add column if not exists retry_count integer not null default 0
    """,
    """
    alter table if exists ifa2.ifa_archive_repair_queue add column if not exists first_seen_at timestamptz not null default now()
    """,
    """
    alter table if exists ifa2.ifa_archive_repair_queue add column if not exists last_attempt_at timestamptz
    """,
    """
    alter table if exists ifa2.ifa_archive_repair_queue add column if not exists last_observed_status text
    """,
    """
    alter table if exists ifa2.ifa_archive_repair_queue add column if not exists escalation_level integer not null default 0
    """,
    """
    alter table if exists ifa2.ifa_archive_repair_queue add column if not exists last_error text
    """,
    """
    alter table if exists ifa2.ifa_archive_repair_queue add column if not exists claim_id uuid
    """,
    """
    alter table if exists ifa2.ifa_archive_repair_queue add column if not exists claimed_at timestamptz
    """,
    """
    alter table if exists ifa2.ifa_archive_repair_queue add column if not exists claimed_by text
    """,
    """
    alter table if exists ifa2.ifa_archive_repair_queue add column if not exists claim_expires_at timestamptz
    """,
    """
    alter table if exists ifa2.ifa_archive_repair_queue add column if not exists suppression_state text not null default 'active'
    """,
    """
    alter table if exists ifa2.ifa_archive_repair_queue add column if not exists acknowledged_at timestamptz
    """,
    """
    alter table if exists ifa2.ifa_archive_repair_queue add column if not exists acknowledged_by text
    """,
    """
    alter table if exists ifa2.ifa_archive_repair_queue add column if not exists acknowledgement_reason text
    """,
    """
    alter table if exists ifa2.ifa_archive_repair_queue add column if not exists suppressed_until timestamptz
    """,
    """
    create index if not exists ix_ifa_archive_repair_queue_claim
      on ifa2.ifa_archive_repair_queue (status, claim_expires_at, priority desc, updated_at)
    """,
    """
    create index if not exists ix_ifa_archive_repair_queue_suppression
      on ifa2.ifa_archive_repair_queue (suppression_state, suppressed_until, updated_at)
    """,
    """
    create index if not exists ix_ifa_archive_repair_queue_priority
      on ifa2.ifa_archive_repair_queue (status, priority desc, retry_after, updated_at)
    """,
    """
    create index if not exists ix_ifa_archive_completeness_status_date
      on ifa2.ifa_archive_completeness (status, business_date desc, family_name)
    """,
    """
    update ifa2.ifa_archive_repair_queue
       set reason_code = case
         when reason_code is not null then reason_code
         when family_name = 'highfreq_signal_daily' then 'legacy_placeholder'
         when family_name = 'generic_structured_output_daily' then 'not_archive_worthy'
         when reason ilike '%not archive-v2 worthy%' then 'not_archive_worthy'
         when reason ilike '%legacy placeholder%' then 'legacy_placeholder'
         when reason ilike '%source returned no rows%' or reason ilike '%source/history returned no rows%' then 'source_empty'
         when status = 'retry_needed' then 'retry_needed'
         when status = 'pending' then 'legacy_pending'
         else 'unknown'
       end,
           actionability = case
             when family_name in ('generic_structured_output_daily', 'highfreq_signal_daily') then 'non_actionable'
             when coalesce(reason_code, '') in ('not_archive_worthy', 'unsupported_family', 'intentional_exclusion', 'legacy_placeholder') then 'non_actionable'
             when reason ilike '%not archive-v2 worthy%' then 'non_actionable'
             when reason ilike '%legacy placeholder%' then 'non_actionable'
             else 'actionable'
           end,
           suppression_state = coalesce(suppression_state, 'active'),
           last_observed_status = coalesce(last_observed_status, status)
     where reason_code is null or last_observed_status is null or actionability is null or suppression_state is null
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
    """
    create table if not exists ifa2.ifa_archive_equity_60m (
      business_date date not null,
      ts_code text not null,
      bar_time text not null,
      payload jsonb not null,
      created_at timestamptz not null default now(),
      primary key (business_date, ts_code, bar_time)
    )
    """,
    """
    create table if not exists ifa2.ifa_archive_etf_60m (
      business_date date not null,
      ts_code text not null,
      bar_time text not null,
      payload jsonb not null,
      created_at timestamptz not null default now(),
      primary key (business_date, ts_code, bar_time)
    )
    """,
    """
    create table if not exists ifa2.ifa_archive_index_60m (
      business_date date not null,
      ts_code text not null,
      bar_time text not null,
      payload jsonb not null,
      created_at timestamptz not null default now(),
      primary key (business_date, ts_code, bar_time)
    )
    """,
    """
    create table if not exists ifa2.ifa_archive_equity_15m (
      business_date date not null,
      ts_code text not null,
      bar_time text not null,
      payload jsonb not null,
      created_at timestamptz not null default now(),
      primary key (business_date, ts_code, bar_time)
    )
    """,
    """
    create table if not exists ifa2.ifa_archive_index_15m (
      business_date date not null,
      ts_code text not null,
      bar_time text not null,
      payload jsonb not null,
      created_at timestamptz not null default now(),
      primary key (business_date, ts_code, bar_time)
    )
    """,
    """
    create table if not exists ifa2.ifa_archive_equity_1m (
      business_date date not null,
      ts_code text not null,
      bar_time text not null,
      payload jsonb not null,
      created_at timestamptz not null default now(),
      primary key (business_date, ts_code, bar_time)
    )
    """,
    """
    create table if not exists ifa2.ifa_archive_index_1m (
      business_date date not null,
      ts_code text not null,
      bar_time text not null,
      payload jsonb not null,
      created_at timestamptz not null default now(),
      primary key (business_date, ts_code, bar_time)
    )
    """,
    """
    create table if not exists ifa2.ifa_archive_futures_60m (
      business_date date not null,
      ts_code text not null,
      bar_time text not null,
      payload jsonb not null,
      created_at timestamptz not null default now(),
      primary key (business_date, ts_code, bar_time)
    )
    """,
    """
    create table if not exists ifa2.ifa_archive_futures_15m (
      business_date date not null,
      ts_code text not null,
      bar_time text not null,
      payload jsonb not null,
      created_at timestamptz not null default now(),
      primary key (business_date, ts_code, bar_time)
    )
    """,
    """
    create table if not exists ifa2.ifa_archive_futures_1m (
      business_date date not null,
      ts_code text not null,
      bar_time text not null,
      payload jsonb not null,
      created_at timestamptz not null default now(),
      primary key (business_date, ts_code, bar_time)
    )
    """,
    """
    create table if not exists ifa2.ifa_archive_commodity_60m (
      business_date date not null,
      ts_code text not null,
      bar_time text not null,
      payload jsonb not null,
      created_at timestamptz not null default now(),
      primary key (business_date, ts_code, bar_time)
    )
    """,
    """
    create table if not exists ifa2.ifa_archive_commodity_15m (
      business_date date not null,
      ts_code text not null,
      bar_time text not null,
      payload jsonb not null,
      created_at timestamptz not null default now(),
      primary key (business_date, ts_code, bar_time)
    )
    """,
    """
    create table if not exists ifa2.ifa_archive_commodity_1m (
      business_date date not null,
      ts_code text not null,
      bar_time text not null,
      payload jsonb not null,
      created_at timestamptz not null default now(),
      primary key (business_date, ts_code, bar_time)
    )
    """,
    """
    create table if not exists ifa2.ifa_archive_precious_metal_60m (
      business_date date not null,
      ts_code text not null,
      bar_time text not null,
      payload jsonb not null,
      created_at timestamptz not null default now(),
      primary key (business_date, ts_code, bar_time)
    )
    """,
    """
    create table if not exists ifa2.ifa_archive_precious_metal_15m (
      business_date date not null,
      ts_code text not null,
      bar_time text not null,
      payload jsonb not null,
      created_at timestamptz not null default now(),
      primary key (business_date, ts_code, bar_time)
    )
    """,
    """
    create table if not exists ifa2.ifa_archive_precious_metal_1m (
      business_date date not null,
      ts_code text not null,
      bar_time text not null,
      payload jsonb not null,
      created_at timestamptz not null default now(),
      primary key (business_date, ts_code, bar_time)
    )
    """,
    """
    alter table if exists ifa2.ifa_archive_announcements_daily add column if not exists row_key text
    """,
    """
    alter table if exists ifa2.ifa_archive_announcements_daily add column if not exists url text
    """,
    """
    alter table if exists ifa2.ifa_archive_announcements_daily add column if not exists rec_time timestamptz
    """,
    """
    update ifa2.ifa_archive_announcements_daily set row_key = coalesce(row_key, md5(payload::text)) where row_key is null
    """,
    """
    alter table if exists ifa2.ifa_archive_news_daily add column if not exists row_key text
    """,
    """
    alter table if exists ifa2.ifa_archive_news_daily add column if not exists src text
    """,
    """
    alter table if exists ifa2.ifa_archive_news_daily add column if not exists content_hash text
    """,
    """
    update ifa2.ifa_archive_news_daily set row_key = coalesce(row_key, md5(payload::text)), src = coalesce(src, payload->>'src'), content_hash = coalesce(content_hash, md5(coalesce(payload->>'content','') || '|' || coalesce(payload->>'title',''))) where row_key is null or src is null or content_hash is null
    """,
    """
    alter table if exists ifa2.ifa_archive_research_reports_daily add column if not exists row_key text
    """,
    """
    alter table if exists ifa2.ifa_archive_research_reports_daily add column if not exists report_type text
    """,
    """
    alter table if exists ifa2.ifa_archive_research_reports_daily add column if not exists inst_csname text
    """,
    """
    alter table if exists ifa2.ifa_archive_research_reports_daily add column if not exists author text
    """,
    """
    update ifa2.ifa_archive_research_reports_daily set row_key = coalesce(row_key, md5(payload::text)), report_type = coalesce(report_type, payload->>'report_type'), inst_csname = coalesce(inst_csname, payload->>'inst_csname'), author = coalesce(author, payload->>'author') where row_key is null or report_type is null or inst_csname is null or author is null
    """,
    """
    alter table if exists ifa2.ifa_archive_research_reports_daily alter column ts_code drop not null
    """,
    """
    alter table if exists ifa2.ifa_archive_investor_qa_daily add column if not exists row_key text
    """,
    """
    alter table if exists ifa2.ifa_archive_investor_qa_daily add column if not exists exchange_source text
    """,
    """
    alter table if exists ifa2.ifa_archive_investor_qa_daily add column if not exists q_hash text
    """,
    """
    alter table if exists ifa2.ifa_archive_investor_qa_daily add column if not exists a_hash text
    """,
    """
    update ifa2.ifa_archive_investor_qa_daily set row_key = coalesce(row_key, md5(payload::text)), exchange_source = coalesce(exchange_source, payload->>'exchange_source'), q_hash = coalesce(q_hash, md5(coalesce(payload->>'q',''))), a_hash = coalesce(a_hash, md5(coalesce(payload->>'a',''))) where row_key is null or exchange_source is null or q_hash is null or a_hash is null
    """,
    """
    alter table if exists ifa2.ifa_archive_dragon_tiger_daily add column if not exists row_key text
    """,
    """
    alter table if exists ifa2.ifa_archive_dragon_tiger_daily add column if not exists reason text
    """,
    """
    update ifa2.ifa_archive_dragon_tiger_daily set row_key = coalesce(row_key, md5(payload::text)), reason = coalesce(reason, payload->>'reason') where row_key is null or reason is null
    """,
    """
    alter table if exists ifa2.ifa_archive_limit_up_detail_daily add column if not exists row_key text
    """,
    """
    alter table if exists ifa2.ifa_archive_limit_up_detail_daily add column if not exists limit_type text
    """,
    """
    alter table if exists ifa2.ifa_archive_limit_up_detail_daily add column if not exists exchange text
    """,
    """
    alter table if exists ifa2.ifa_archive_limit_up_detail_daily add column if not exists first_time text
    """,
    """
    alter table if exists ifa2.ifa_archive_limit_up_detail_daily add column if not exists last_time text
    """,
    """
    alter table if exists ifa2.ifa_archive_limit_up_detail_daily add column if not exists limit_times integer
    """,
    """
    update ifa2.ifa_archive_limit_up_detail_daily set row_key = coalesce(row_key, md5(payload::text)), limit_type = coalesce(limit_type, payload->>'limit'), exchange = coalesce(exchange, payload->>'exchange'), first_time = coalesce(first_time, payload->>'first_time'), last_time = coalesce(last_time, payload->>'last_time'), limit_times = coalesce(limit_times, nullif(payload->>'limit_times','')::integer) where row_key is null or limit_type is null or exchange is null or first_time is null or last_time is null or limit_times is null
    """,
    """
    alter table if exists ifa2.ifa_archive_announcements_daily drop constraint if exists ifa_archive_announcements_daily_pkey
    """,
    """
    alter table if exists ifa2.ifa_archive_news_daily drop constraint if exists ifa_archive_news_daily_pkey
    """,
    """
    alter table if exists ifa2.ifa_archive_research_reports_daily drop constraint if exists ifa_archive_research_reports_daily_pkey
    """,
    """
    alter table if exists ifa2.ifa_archive_investor_qa_daily drop constraint if exists ifa_archive_investor_qa_daily_pkey
    """,
    """
    alter table if exists ifa2.ifa_archive_dragon_tiger_daily drop constraint if exists ifa_archive_dragon_tiger_daily_pkey
    """,
    """
    alter table if exists ifa2.ifa_archive_limit_up_detail_daily drop constraint if exists ifa_archive_limit_up_detail_daily_pkey
    """,
    """
    alter table if exists ifa2.ifa_archive_announcements_daily add constraint ifa_archive_announcements_daily_pkey primary key (business_date, row_key)
    """,
    """
    alter table if exists ifa2.ifa_archive_news_daily add constraint ifa_archive_news_daily_pkey primary key (business_date, row_key)
    """,
    """
    alter table if exists ifa2.ifa_archive_research_reports_daily add constraint ifa_archive_research_reports_daily_pkey primary key (business_date, row_key)
    """,
    """
    alter table if exists ifa2.ifa_archive_investor_qa_daily add constraint ifa_archive_investor_qa_daily_pkey primary key (business_date, row_key)
    """,
    """
    alter table if exists ifa2.ifa_archive_dragon_tiger_daily add constraint ifa_archive_dragon_tiger_daily_pkey primary key (business_date, row_key)
    """,
    """
    alter table if exists ifa2.ifa_archive_limit_up_detail_daily add constraint ifa_archive_limit_up_detail_daily_pkey primary key (business_date, row_key)
    """,
    """
    create table if not exists ifa2.ifa_archive_proxy_60m (
      business_date date not null,
      proxy_code text not null,
      bar_time text not null,
      payload jsonb not null,
      created_at timestamptz not null default now(),
      primary key (business_date, proxy_code, bar_time)
    )
    """,
    """
    create table if not exists ifa2.ifa_archive_proxy_15m (
      business_date date not null,
      proxy_code text not null,
      bar_time text not null,
      payload jsonb not null,
      created_at timestamptz not null default now(),
      primary key (business_date, proxy_code, bar_time)
    )
    """,
    """
    create table if not exists ifa2.ifa_archive_proxy_1m (
      business_date date not null,
      proxy_code text not null,
      bar_time text not null,
      payload jsonb not null,
      created_at timestamptz not null default now(),
      primary key (business_date, proxy_code, bar_time)
    )
    """,
    """
    drop view if exists ifa2.ifa_archive_operator_claimed_backlog_v
    """,
    """
    drop view if exists ifa2.ifa_archive_operator_suppressed_backlog_v
    """,
    """
    drop view if exists ifa2.ifa_archive_operator_repair_execution_history_v
    """,
    """
    drop view if exists ifa2.ifa_archive_operator_gap_summary_v
    """,
    """
    drop view if exists ifa2.ifa_archive_operator_repair_backlog_v
    """,
    """
    drop view if exists ifa2.ifa_archive_operator_recent_runs_v
    """,
    """
    drop view if exists ifa2.ifa_archive_operator_family_health_v
    """,
    """
    drop view if exists ifa2.ifa_archive_operator_date_health_v
    """,
    """
    create or replace view ifa2.ifa_archive_operator_gap_summary_v as
    select
      c.business_date,
      c.family_name,
      c.frequency,
      c.coverage_scope,
      c.status as completeness_status,
      c.row_count,
      c.retry_after,
      c.last_error,
      c.family_expected_rows,
      c.family_observed_rows,
      c.family_coverage_ratio,
      q.status as repair_status,
      coalesce(q.reason_code,
        case
          when q.family_name = 'highfreq_signal_daily' then 'legacy_placeholder'
          when q.family_name = 'generic_structured_output_daily' then 'not_archive_worthy'
          when q.reason ilike '%not archive-v2 worthy%' then 'not_archive_worthy'
          when q.reason ilike '%legacy placeholder%' then 'legacy_placeholder'
          when q.reason ilike '%source returned no rows%' or q.reason ilike '%source/history returned no rows%' then 'source_empty'
          when q.status = 'retry_needed' then 'retry_needed'
          when q.status = 'pending' then 'legacy_pending'
          else 'unknown'
        end) as reason_code,
      coalesce(q.actionability,
        case
          when q.family_name in ('generic_structured_output_daily', 'highfreq_signal_daily') then 'non_actionable'
          when q.reason ilike '%not archive-v2 worthy%' then 'non_actionable'
          when q.reason ilike '%legacy placeholder%' then 'non_actionable'
          else 'actionable'
        end) as actionability,
      case
        when coalesce(q.actionability,
          case
            when q.family_name in ('generic_structured_output_daily', 'highfreq_signal_daily') then 'non_actionable'
            when q.reason ilike '%not archive-v2 worthy%' then 'non_actionable'
            when q.reason ilike '%legacy placeholder%' then 'non_actionable'
            else 'actionable'
          end) = 'actionable' then 0 else 1 end as actionability_sort,
      q.reason,
      q.priority,
      q.urgency,
      q.retry_count,
      q.escalation_level,
      q.claim_id,
      q.claimed_at,
      q.claimed_by,
      q.claim_expires_at,
      coalesce(q.suppression_state, 'active') as suppression_state,
      q.suppressed_until,
      (coalesce(q.suppression_state, 'active') in ('acknowledged', 'suppressed') and (q.suppressed_until is null or q.suppressed_until > now())) as suppression_active,
      q.acknowledged_at,
      q.acknowledged_by,
      q.acknowledgement_reason,
      q.last_attempt_at,
      q.last_run_id as repair_last_run_id
    from ifa2.ifa_archive_completeness c
    left join ifa2.ifa_archive_repair_queue q
      on q.business_date = c.business_date
     and q.family_name = c.family_name
     and q.frequency = c.frequency
     and q.coverage_scope = c.coverage_scope
    where c.status in ('partial', 'incomplete', 'retry_needed', 'missing')
    """,
    """
    create or replace view ifa2.ifa_archive_operator_repair_backlog_v as
    select
      q.business_date,
      q.family_name,
      q.frequency,
      q.coverage_scope,
      q.status as repair_status,
      coalesce(q.reason_code,
        case
          when q.family_name = 'highfreq_signal_daily' then 'legacy_placeholder'
          when q.family_name = 'generic_structured_output_daily' then 'not_archive_worthy'
          when q.reason ilike '%not archive-v2 worthy%' then 'not_archive_worthy'
          when q.reason ilike '%legacy placeholder%' then 'legacy_placeholder'
          when q.reason ilike '%source returned no rows%' or q.reason ilike '%source/history returned no rows%' then 'source_empty'
          when q.status = 'retry_needed' then 'retry_needed'
          when q.status = 'pending' then 'legacy_pending'
          else 'unknown'
        end) as reason_code,
      coalesce(q.actionability,
        case
          when q.family_name in ('generic_structured_output_daily', 'highfreq_signal_daily') then 'non_actionable'
          when q.reason ilike '%not archive-v2 worthy%' then 'non_actionable'
          when q.reason ilike '%legacy placeholder%' then 'non_actionable'
          else 'actionable'
        end) as actionability,
      case
        when coalesce(q.actionability,
          case
            when q.family_name in ('generic_structured_output_daily', 'highfreq_signal_daily') then 'non_actionable'
            when q.reason ilike '%not archive-v2 worthy%' then 'non_actionable'
            when q.reason ilike '%legacy placeholder%' then 'non_actionable'
            else 'actionable'
          end) = 'actionable' then 0 else 1 end as actionability_sort,
      q.reason,
      q.priority,
      q.urgency,
      q.retry_count,
      q.escalation_level,
      q.retry_after,
      q.claim_id,
      q.claimed_at,
      q.claimed_by,
      q.claim_expires_at,
      case when q.status = 'claimed' and (q.claim_expires_at is null or q.claim_expires_at > now()) then 'active'
           when q.status = 'claimed' and q.claim_expires_at <= now() then 'expired'
           else 'none' end as claim_state,
      case when q.status = 'claimed' and (q.claim_expires_at is null or q.claim_expires_at > now()) then 0
           when q.status = 'claimed' then 1 else 2 end as claim_state_sort,
      q.first_seen_at,
      q.last_attempt_at,
      q.updated_at,
      coalesce(q.suppression_state, 'active') as suppression_state,
      q.suppressed_until,
      (coalesce(q.suppression_state, 'active') in ('acknowledged', 'suppressed') and (q.suppressed_until is null or q.suppressed_until > now())) as suppression_active,
      q.acknowledged_at,
      q.acknowledged_by,
      q.acknowledgement_reason,
      q.last_observed_status,
      q.last_error,
      c.status as completeness_status,
      c.row_count,
      c.family_expected_rows,
      c.family_observed_rows,
      c.family_coverage_ratio,
      c.last_run_id as completeness_last_run_id
    from ifa2.ifa_archive_repair_queue q
    left join ifa2.ifa_archive_completeness c
      on q.business_date = c.business_date
     and q.family_name = c.family_name
     and q.frequency = c.frequency
     and q.coverage_scope = c.coverage_scope
    where q.status in ('pending', 'retry_needed', 'claimed')
    """,
    """
    create or replace view ifa2.ifa_archive_operator_claimed_backlog_v as
    select *
    from ifa2.ifa_archive_operator_repair_backlog_v
    where repair_status = 'claimed'
    """,
    """
    create or replace view ifa2.ifa_archive_operator_suppressed_backlog_v as
    select *
    from ifa2.ifa_archive_operator_repair_backlog_v
    where suppression_active = true
    """,
    """
    create or replace view ifa2.ifa_archive_operator_recent_runs_v as
    select
      r.run_id,
      r.profile_name,
      r.mode,
      r.status,
      r.start_time,
      r.end_time,
      r.duration_ms,
      r.notes,
      r.dry_run,
      count(i.id) as item_count,
      sum(i.rows_written) as rows_written,
      sum(i.would_write_rows) as would_write_rows,
      count(*) filter (where i.status = 'completed') as completed_items,
      count(*) filter (where i.status = 'incomplete') as incomplete_items,
      count(*) filter (where i.status = 'partial') as partial_items,
      count(*) filter (where i.status = 'superseded') as superseded_items,
      count(*) filter (where i.status = 'failed') as failed_items
    from ifa2.ifa_archive_runs r
    left join ifa2.ifa_archive_run_items i on i.run_id = r.run_id
    group by r.run_id, r.profile_name, r.mode, r.status, r.start_time, r.end_time, r.duration_ms, r.notes, r.dry_run
    """,
    """
    create or replace view ifa2.ifa_archive_operator_family_health_v as
    select
      family_name,
      frequency,
      count(*) as total_dates,
      count(*) filter (where status = 'completed') as completed_dates,
      count(*) filter (where status in ('partial', 'incomplete', 'retry_needed', 'missing')) as non_completed_dates,
      max(business_date) as latest_business_date,
      max(business_date) filter (where status = 'completed') as latest_completed_date,
      max(business_date) filter (where status in ('partial', 'incomplete', 'retry_needed', 'missing')) as latest_problem_date,
      max(family_expected_rows) filter (where status in ('partial', 'incomplete', 'retry_needed', 'missing')) as latest_family_expected_rows,
      max(family_observed_rows) filter (where status in ('partial', 'incomplete', 'retry_needed', 'missing')) as latest_family_observed_rows,
      min(family_coverage_ratio) filter (where status in ('partial', 'incomplete', 'retry_needed', 'missing')) as worst_family_coverage_ratio,
      round((100.0 * count(*) filter (where status = 'completed') / greatest(count(*), 1))::numeric, 2) as completion_ratio
    from ifa2.ifa_archive_completeness
    group by family_name, frequency
    """,
    """
    create or replace view ifa2.ifa_archive_operator_date_health_v as
    select
      business_date,
      count(*) as families_observed,
      count(*) filter (where status = 'completed') as completed_families,
      count(*) filter (where status in ('partial', 'incomplete', 'retry_needed', 'missing')) as non_completed_families,
      min(family_coverage_ratio) filter (where status in ('partial', 'incomplete', 'retry_needed', 'missing')) as worst_family_coverage_ratio
    from ifa2.ifa_archive_completeness
    group by business_date
    """,
    """
    create or replace view ifa2.ifa_archive_operator_repair_execution_history_v as
    select
      r.run_id,
      r.trigger_source,
      r.profile_name,
      r.mode,
      r.start_time,
      r.end_time,
      r.status as run_status,
      i.business_date,
      i.family_name,
      i.status as item_status,
      i.rows_written,
      i.would_write_rows,
      i.family_expected_rows,
      i.family_observed_rows,
      i.family_coverage_ratio,
      i.notes,
      i.error_text
    from ifa2.ifa_archive_runs r
    join ifa2.ifa_archive_run_items i on i.run_id = r.run_id
    where r.trigger_source = 'operator_repair_batch'
    """,
]


def ensure_schema() -> None:
    with engine.begin() as conn:
        for ddl in DDL:
            conn.execute(text(ddl))
