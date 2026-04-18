from __future__ import annotations

import json
import subprocess
import uuid
from pathlib import Path

from sqlalchemy import create_engine, text

from ifa_data_platform.archive_v2.db import ensure_schema

REPO = Path('/Users/neoclaw/repos/ifa-data-platform')
PY = REPO / '.venv/bin/python'
ENGINE = create_engine('postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp')
ensure_schema()


def _run(*args: str) -> dict:
    proc = subprocess.run(
        [str(PY), *args],
        cwd=REPO,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(proc.stdout)


def _upsert_actionable_queue(business_date: str, family_name: str, priority: int, urgency: str, retry_after_sql: str = 'now() - interval \'5 minutes\'') -> None:
    with ENGINE.begin() as conn:
        conn.execute(text(
            f"""
            insert into ifa2.ifa_archive_repair_queue(
              id, business_date, family_name, frequency, coverage_scope, status, reason, reason_code, actionability,
              priority, urgency, retry_count, retry_after, first_seen_at, last_attempt_at,
              last_observed_status, escalation_level, last_error, last_run_id, updated_at
            )
            values (
              cast(:id as uuid), :business_date, :family_name, 'daily', 'broad_market', 'pending',
              'manual actionable repair setup', 'retry_needed', 'actionable',
              :priority, :urgency, 1, {retry_after_sql}, now(), now(),
              'retry_needed', 1, 'manual actionable repair setup', null, now()
            )
            on conflict (business_date, family_name, frequency, coverage_scope)
            do update set status='pending', reason='manual actionable repair setup', reason_code='retry_needed', actionability='actionable',
              priority=excluded.priority, urgency=excluded.urgency, retry_count=excluded.retry_count,
              retry_after=excluded.retry_after, last_attempt_at=excluded.last_attempt_at,
              last_observed_status='retry_needed', escalation_level=1, last_error='manual actionable repair setup', updated_at=now()
            """
        ), {'id': str(uuid.uuid4()), 'business_date': business_date, 'family_name': family_name, 'priority': priority, 'urgency': urgency})
        conn.execute(text("""
            insert into ifa2.ifa_archive_completeness(
              id, business_date, family_name, frequency, coverage_scope, status, source_mode, last_run_id, row_count, retry_after, last_error, updated_at
            ) values (
              cast(:id as uuid), :business_date, :family_name, 'daily', 'broad_market', 'retry_needed', 'repair_seed', null, 0, now(), 'manual actionable repair setup', now()
            )
            on conflict (business_date, family_name, frequency, coverage_scope)
            do update set status='retry_needed', source_mode='repair_seed', retry_after=now(), last_error='manual actionable repair setup', updated_at=now()
        """), {'id': str(uuid.uuid4()), 'business_date': business_date, 'family_name': family_name})


def _seed_reparable_gap(business_date: str, family_name: str, table_name: str) -> None:
    with ENGINE.begin() as conn:
        conn.execute(text(f"delete from ifa2.{table_name} where business_date=:business_date"), {'business_date': business_date})
    _upsert_actionable_queue(business_date, family_name, priority=80, urgency='high')


def test_archive_v2_milestone7_repair_batch_honors_priority_and_limit() -> None:
    _run('scripts/archive_v2_run.py', '--profile', 'profiles/archive_v2_milestone6_broad_range_history_write_sample.json')
    _seed_reparable_gap('2026-04-16', 'index_daily', 'ifa_archive_index_daily')
    _seed_reparable_gap('2026-04-17', 'research_reports_daily', 'ifa_archive_research_reports_daily')
    with ENGINE.begin() as conn:
        conn.execute(text("update ifa2.ifa_archive_repair_queue set priority=95, urgency='critical' where business_date='2026-04-16' and family_name='index_daily' and frequency='daily' and coverage_scope='broad_market'"))
        conn.execute(text("update ifa2.ifa_archive_repair_queue set priority=70, urgency='normal' where business_date='2026-04-17' and family_name='research_reports_daily' and frequency='daily' and coverage_scope='broad_market'"))

    payload = _run('scripts/archive_v2_operator_cli.py', 'repair-batch', '--limit', '1', '--retry-due-only', '--family', 'index_daily', '--family', 'research_reports_daily')
    assert payload['ok'] is True
    assert payload['selected_count'] == 1
    assert payload['targets'][0]['family_name'] == 'index_daily'

    with ENGINE.begin() as conn:
        picked = conn.execute(text("select status from ifa2.ifa_archive_repair_queue where business_date='2026-04-16' and family_name='index_daily' and frequency='daily' and coverage_scope='broad_market'" )).scalar_one()
        left_pending = conn.execute(text("select status from ifa2.ifa_archive_repair_queue where business_date='2026-04-17' and family_name='research_reports_daily' and frequency='daily' and coverage_scope='broad_market'" )).scalar_one()
        trigger_source = conn.execute(text("select trigger_source from ifa2.ifa_archive_runs where run_id=cast(:run_id as uuid)"), {'run_id': payload['run_id']}).scalar_one()
        item_count = conn.execute(text("select count(*) from ifa2.ifa_archive_run_items where run_id=cast(:run_id as uuid)"), {'run_id': payload['run_id']}).scalar_one()
    assert picked == 'completed'
    assert left_pending == 'pending'
    assert trigger_source == 'operator_repair_batch'
    assert item_count == 1


def test_archive_v2_milestone7_repair_batch_supports_family_and_date_scope() -> None:
    _run('scripts/archive_v2_run.py', '--profile', 'profiles/archive_v2_milestone6_broad_range_history_write_sample.json')
    _seed_reparable_gap('2026-04-17', 'dragon_tiger_daily', 'ifa_archive_dragon_tiger_daily')
    _seed_reparable_gap('2026-04-16', 'news_daily', 'ifa_archive_news_daily')

    payload = _run(
        'scripts/archive_v2_operator_cli.py', 'repair-batch',
        '--business-date', '2026-04-17',
        '--family', 'dragon_tiger_daily',
        '--limit', '10'
    )
    assert payload['ok'] is True
    assert payload['selected_count'] == 1
    assert payload['targets'][0]['family_name'] == 'dragon_tiger_daily'
    assert str(payload['targets'][0]['business_date']) == '2026-04-17'

    with ENGINE.begin() as conn:
        repaired = conn.execute(text("select status from ifa2.ifa_archive_repair_queue where business_date='2026-04-17' and family_name='dragon_tiger_daily' and frequency='daily' and coverage_scope='broad_market'" )).scalar_one()
        untouched = conn.execute(text("select status from ifa2.ifa_archive_repair_queue where business_date='2026-04-16' and family_name='news_daily' and frequency='daily' and coverage_scope='broad_market'" )).scalar_one()
        completeness = conn.execute(text("select status from ifa2.ifa_archive_completeness where business_date='2026-04-17' and family_name='dragon_tiger_daily' and frequency='daily' and coverage_scope='broad_market'" )).scalar_one()
    assert repaired == 'completed'
    assert untouched == 'pending'
    assert completeness == 'completed'


def test_archive_v2_milestone7_actionable_vs_nonactionable_backlog_separation() -> None:
    with ENGINE.begin() as conn:
        conn.execute(text("""
            insert into ifa2.ifa_archive_repair_queue(
              id, business_date, family_name, frequency, coverage_scope, status, reason, reason_code, actionability,
              priority, urgency, retry_count, retry_after, first_seen_at, last_attempt_at,
              last_observed_status, escalation_level, last_error, last_run_id, updated_at
            ) values (
              cast(:id as uuid), '2026-04-15', 'generic_structured_output_daily', 'daily', 'broad_market', 'pending',
              'generic structured-output catch-all is not archive-v2 worthy because it collapses unrelated finalized truths into one lossy bucket',
              'not_archive_worthy', 'non_actionable', 20, 'deferred', 0, now() + interval '7 days', now(), null,
              'incomplete', 0, null, null, now()
            )
            on conflict (business_date, family_name, frequency, coverage_scope)
            do update set status='pending', reason=excluded.reason, reason_code='not_archive_worthy', actionability='non_actionable', urgency='deferred', updated_at=now()
        """), {'id': str(uuid.uuid4())})
        conn.execute(text("""
            insert into ifa2.ifa_archive_completeness(
              id, business_date, family_name, frequency, coverage_scope, status, source_mode, last_run_id, row_count, retry_after, last_error, updated_at
            ) values (
              cast(:id as uuid), '2026-04-15', 'generic_structured_output_daily', 'daily', 'broad_market', 'incomplete', 'repair_seed', null, 0, now() + interval '7 days', 'not archive worthy', now()
            )
            on conflict (business_date, family_name, frequency, coverage_scope)
            do update set status='incomplete', source_mode='repair_seed', retry_after=excluded.retry_after, last_error='not archive worthy', updated_at=now()
        """), {'id': str(uuid.uuid4())})

    actionable = _run('scripts/archive_v2_operator_cli.py', 'actionable-backlog', '--limit', '20')
    non_actionable = _run('scripts/archive_v2_operator_cli.py', 'nonactionable-backlog', '--limit', '20')
    dry_run = _run('scripts/archive_v2_operator_cli.py', 'repair-batch', '--limit', '20', '--dry-run')

    assert not any(row['family_name'] == 'generic_structured_output_daily' for row in actionable)
    assert any(row['family_name'] == 'generic_structured_output_daily' for row in non_actionable)
    assert not any(row['family_name'] == 'generic_structured_output_daily' for row in dry_run['targets'])
    assert all(row['actionability'] == 'actionable' for row in dry_run['targets'])
