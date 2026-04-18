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
]


def ensure_schema() -> None:
    with engine.begin() as conn:
        for ddl in DDL:
            conn.execute(text(ddl))
