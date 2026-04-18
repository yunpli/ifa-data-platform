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


def _seed_queue_target(business_date: str, family_name: str, table_name: str, priority: int, urgency: str) -> None:
    with ENGINE.begin() as conn:
        conn.execute(text(f"delete from ifa2.{table_name} where business_date=:business_date"), {'business_date': business_date})
        conn.execute(text("""
            insert into ifa2.ifa_archive_completeness(
              id, business_date, family_name, frequency, coverage_scope, status, source_mode, last_run_id, row_count, retry_after, last_error, updated_at
            ) values (
              cast(:id as uuid), :business_date, :family_name, 'daily', 'broad_market', 'retry_needed', 'manual_seed', null, 0, now() - interval '5 minutes', 'milestone8 seed', now()
            )
            on conflict (business_date, family_name, frequency, coverage_scope)
            do update set status='retry_needed', source_mode='manual_seed', retry_after=now() - interval '5 minutes', last_error='milestone8 seed', updated_at=now()
        """), {'id': str(uuid.uuid4()), 'business_date': business_date, 'family_name': family_name})
        conn.execute(text("""
            insert into ifa2.ifa_archive_repair_queue(
              id, business_date, family_name, frequency, coverage_scope, status, reason, reason_code, actionability,
              priority, urgency, retry_count, retry_after, first_seen_at, last_attempt_at,
              last_observed_status, escalation_level, last_error, last_run_id, updated_at,
              suppression_state
            ) values (
              cast(:id as uuid), :business_date, :family_name, 'daily', 'broad_market', 'pending',
              'milestone8 actionable seed', 'retry_needed', 'actionable',
              :priority, :urgency, 1, now() - interval '5 minutes', now(), now(),
              'retry_needed', 1, 'milestone8 actionable seed', null, now(), 'active'
            )
            on conflict (business_date, family_name, frequency, coverage_scope)
            do update set status='pending', reason='milestone8 actionable seed', reason_code='retry_needed', actionability='actionable',
              priority=excluded.priority, urgency=excluded.urgency, retry_count=1, retry_after=now() - interval '5 minutes',
              claim_id=null, claimed_at=null, claimed_by=null, claim_expires_at=null,
              suppression_state='active', suppressed_until=null, updated_at=now()
        """), {'id': str(uuid.uuid4()), 'business_date': business_date, 'family_name': family_name, 'priority': priority, 'urgency': urgency})


def test_archive_v2_milestone8_claim_only_marks_queue_and_avoids_double_pick() -> None:
    _run('scripts/archive_v2_run.py', '--profile', 'profiles/archive_v2_milestone6_broad_range_history_write_sample.json')
    _seed_queue_target('2026-04-16', 'index_daily', 'ifa_archive_index_daily', 95, 'critical')
    _seed_queue_target('2026-04-17', 'research_reports_daily', 'ifa_archive_research_reports_daily', 70, 'normal')

    claim = _run(
        'scripts/archive_v2_operator_cli.py', 'repair-batch',
        '--claim-only', '--limit', '1', '--retry-due-only',
        '--family', 'index_daily', '--family', 'research_reports_daily',
        '--claimed-by', 'pytest_claim'
    )
    assert claim['ok'] is True
    assert claim['selected_count'] == 1
    assert claim['targets'][0]['family_name'] == 'index_daily'
    claim_id = claim['claim_id']

    claimed = _run('scripts/archive_v2_operator_cli.py', 'claimed-backlog', '--limit', '10')
    assert any(str(row['claim_id']) == claim_id and row['family_name'] == 'index_daily' for row in claimed)

    dry = _run(
        'scripts/archive_v2_operator_cli.py', 'repair-batch', '--dry-run', '--limit', '5',
        '--family', 'index_daily', '--family', 'research_reports_daily'
    )
    assert not any(row['family_name'] == 'index_daily' and str(row.get('business_date')) == '2026-04-16' for row in dry['targets'])
    assert any(row['family_name'] == 'research_reports_daily' for row in dry['targets'])

    released = _run('scripts/archive_v2_operator_cli.py', 'release-claims', '--claim-id', claim_id, '--released-by', 'pytest_claim')
    assert released['released_count'] == 1


def test_archive_v2_milestone8_execute_claimed_batch_resolves_claim_and_updates_history() -> None:
    _run('scripts/archive_v2_run.py', '--profile', 'profiles/archive_v2_milestone6_broad_range_history_write_sample.json')
    _seed_queue_target('2026-04-17', 'dragon_tiger_daily', 'ifa_archive_dragon_tiger_daily', 88, 'high')
    claim = _run(
        'scripts/archive_v2_operator_cli.py', 'repair-batch',
        '--claim-only', '--limit', '1', '--family', 'dragon_tiger_daily',
        '--business-date', '2026-04-17', '--claimed-by', 'pytest_exec'
    )
    claim_id = claim['claim_id']

    executed = _run(
        'scripts/archive_v2_operator_cli.py', 'repair-batch',
        '--claim-id', claim_id, '--claimed-by', 'pytest_exec'
    )
    assert executed['ok'] is True
    assert executed['status'] == 'completed'
    assert executed['selected_count'] == 1

    with ENGINE.begin() as conn:
        queue = conn.execute(text("select status, claim_id, claimed_by, claim_expires_at from ifa2.ifa_archive_repair_queue where business_date='2026-04-17' and family_name='dragon_tiger_daily' and frequency='daily' and coverage_scope='broad_market'" )).mappings().one()
        completeness = conn.execute(text("select status, retry_after, last_run_id::text as last_run_id from ifa2.ifa_archive_completeness where business_date='2026-04-17' and family_name='dragon_tiger_daily' and frequency='daily' and coverage_scope='broad_market'" )).mappings().one()
    assert queue['status'] == 'completed'
    assert queue['claim_id'] is None
    assert queue['claimed_by'] is None
    assert queue['claim_expires_at'] is None
    assert completeness['status'] == 'completed'
    assert completeness['retry_after'] is None

    history = _run('scripts/archive_v2_operator_cli.py', 'repair-history', '--limit', '20')
    assert any(row['run_id'] == executed['run_id'] and row['family_name'] == 'dragon_tiger_daily' for row in history)


def test_archive_v2_milestone8_acknowledge_suppression_hides_nonactionable_from_default_surfaces() -> None:
    with ENGINE.begin() as conn:
        conn.execute(text("""
            insert into ifa2.ifa_archive_repair_queue(
              id, business_date, family_name, frequency, coverage_scope, status, reason, reason_code, actionability,
              priority, urgency, retry_count, retry_after, first_seen_at, updated_at, suppression_state
            ) values (
              cast(:id as uuid), '2026-04-15', 'generic_structured_output_daily', 'daily', 'broad_market', 'pending',
              'generic structured-output catch-all is not archive-v2 worthy because it collapses unrelated finalized truths into one lossy bucket',
              'not_archive_worthy', 'non_actionable', 20, 'deferred', 0, now() + interval '7 days', now(), now(), 'active'
            )
            on conflict (business_date, family_name, frequency, coverage_scope)
            do update set status='pending', reason=excluded.reason, reason_code='not_archive_worthy', actionability='non_actionable', suppression_state='active', suppressed_until=null, updated_at=now()
        """), {'id': str(uuid.uuid4())})
        conn.execute(text("""
            insert into ifa2.ifa_archive_completeness(
              id, business_date, family_name, frequency, coverage_scope, status, source_mode, last_run_id, row_count, retry_after, last_error, updated_at
            ) values (
              cast(:id as uuid), '2026-04-15', 'generic_structured_output_daily', 'daily', 'broad_market', 'incomplete', 'manual_seed', null, 0, now() + interval '7 days', 'not archive worthy', now()
            )
            on conflict (business_date, family_name, frequency, coverage_scope)
            do update set status='incomplete', retry_after=excluded.retry_after, last_error='not archive worthy', updated_at=now()
        """), {'id': str(uuid.uuid4())})

    ack = _run(
        'scripts/archive_v2_operator_cli.py', 'acknowledge-backlog',
        '--business-date', '2026-04-15', '--family', 'generic_structured_output_daily',
        '--reason', 'known intentional non-actionable backlog', '--acknowledged-by', 'pytest_ack', '--suppress-hours', '24'
    )
    assert ack['count'] == 1
    assert ack['targets'][0]['suppression_state'] == 'suppressed'

    suppressed = _run('scripts/archive_v2_operator_cli.py', 'suppressed-backlog', '--limit', '20')
    assert any(row['family_name'] == 'generic_structured_output_daily' for row in suppressed)

    backlog = _run('scripts/archive_v2_operator_cli.py', 'repair-backlog', '--limit', '50')
    assert not any(row['family_name'] == 'generic_structured_output_daily' for row in backlog)

    non_actionable = _run('scripts/archive_v2_operator_cli.py', 'nonactionable-backlog', '--limit', '50')
    assert any(row['family_name'] == 'generic_structured_output_daily' for row in non_actionable)

    summary = _run('scripts/archive_v2_operator_cli.py', 'summary', '--days', '14', '--limit', '20')
    assert summary['suppressed_backlog_count'] >= 1
