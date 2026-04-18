from __future__ import annotations

import json
import subprocess
from pathlib import Path
import uuid

from sqlalchemy import create_engine, text

REPO = Path('/Users/neoclaw/repos/ifa-data-platform')
PY = REPO / '.venv/bin/python'
ENGINE = create_engine('postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp')


def _run(*args: str) -> dict:
    proc = subprocess.run(
        [str(PY), *args],
        cwd=REPO,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(proc.stdout)


def test_archive_v2_milestone5_date_range_and_rerun_stability() -> None:
    first = _run('scripts/archive_v2_run.py', '--profile', 'profiles/archive_v2_milestone5_range_write_sample.json')
    assert first['ok'] is True
    assert first['status'] == 'completed'

    with ENGINE.begin() as conn:
        before = {
            'index': conn.execute(text("select count(*) from ifa2.ifa_archive_index_daily where business_date between '2026-04-15' and '2026-04-17'" )).scalar_one(),
            'announcements': conn.execute(text("select count(*) from ifa2.ifa_archive_announcements_daily where business_date between '2026-04-15' and '2026-04-17'" )).scalar_one(),
            'news': conn.execute(text("select count(*) from ifa2.ifa_archive_news_daily where business_date between '2026-04-15' and '2026-04-17'" )).scalar_one(),
        }

    second = _run('scripts/archive_v2_run.py', '--profile', 'profiles/archive_v2_milestone5_range_write_sample.json')
    assert second['ok'] is True
    assert second['status'] == 'completed'

    with ENGINE.begin() as conn:
        after = {
            'index': conn.execute(text("select count(*) from ifa2.ifa_archive_index_daily where business_date between '2026-04-15' and '2026-04-17'" )).scalar_one(),
            'announcements': conn.execute(text("select count(*) from ifa2.ifa_archive_announcements_daily where business_date between '2026-04-15' and '2026-04-17'" )).scalar_one(),
            'news': conn.execute(text("select count(*) from ifa2.ifa_archive_news_daily where business_date between '2026-04-15' and '2026-04-17'" )).scalar_one(),
        }
        item_count = conn.execute(text("select count(*) from ifa2.ifa_archive_run_items where run_id = :run_id"), {'run_id': second['run_id']}).scalar_one()
    assert before == after
    assert item_count == 9


def test_archive_v2_milestone5_backfill_repairs_missing_gaps() -> None:
    _run('scripts/archive_v2_run.py', '--profile', 'profiles/archive_v2_milestone5_range_write_sample.json')
    with ENGINE.begin() as conn:
        conn.execute(text("delete from ifa2.ifa_archive_index_daily where business_date='2026-04-16'"))
        conn.execute(text("delete from ifa2.ifa_archive_news_daily where business_date='2026-04-16'"))
        conn.execute(text("delete from ifa2.ifa_archive_completeness where business_date='2026-04-16' and family_name in ('index_daily','news_daily') and frequency='daily' and coverage_scope='broad_market'"))

    payload = _run('scripts/archive_v2_run.py', '--profile', 'profiles/archive_v2_milestone5_backfill_write_sample.json')
    assert payload['ok'] is True
    assert payload['status'] == 'completed'

    with ENGINE.begin() as conn:
        repaired_index = conn.execute(text("select count(*) from ifa2.ifa_archive_index_daily where business_date='2026-04-16'" )).scalar_one()
        repaired_news = conn.execute(text("select count(*) from ifa2.ifa_archive_news_daily where business_date='2026-04-16'" )).scalar_one()
        completeness_rows = conn.execute(text("select family_name, status from ifa2.ifa_archive_completeness where business_date='2026-04-16' and family_name in ('index_daily','news_daily') order by family_name" )).mappings().all()
        skipped = conn.execute(text("select count(*) from ifa2.ifa_archive_run_items where run_id=:run_id and status='superseded'"), {'run_id': payload['run_id']}).scalar_one()
    assert repaired_index > 0
    assert repaired_news > 0
    assert [row['status'] for row in completeness_rows] == ['completed', 'completed']
    assert skipped > 0


def test_archive_v2_milestone5_repair_retry_uses_queue_and_keeps_reruns_sane() -> None:
    _run('scripts/runtime_manifest_cli.py', 'run-once', '--lane', 'highfreq', '--owner-type', 'default', '--owner-id', 'default')
    _run('scripts/archive_v2_run.py', '--profile', 'profiles/archive_v2_milestone4_highfreq_write_sample.json')

    with ENGINE.begin() as conn:
        conn.execute(text("delete from ifa2.ifa_archive_highfreq_event_stream_daily where business_date='2026-04-15'"))
        conn.execute(text("delete from ifa2.ifa_archive_highfreq_sector_breadth_daily where business_date='2026-04-15'"))
        conn.execute(text("update ifa2.ifa_archive_completeness set status='retry_needed', last_error='forced repair test', retry_after=now() where business_date='2026-04-15' and family_name='highfreq_event_stream_daily' and frequency='daily' and coverage_scope='broad_market'"))
        conn.execute(text("update ifa2.ifa_archive_completeness set status='partial', last_error='forced repair test', retry_after=now() where business_date='2026-04-15' and family_name='highfreq_sector_breadth_daily' and frequency='daily' and coverage_scope='broad_market'"))
        conn.execute(text("""
            insert into ifa2.ifa_archive_repair_queue(id, business_date, family_name, frequency, coverage_scope, status, reason, retry_after, last_run_id, updated_at)
            values (cast(:id as uuid), '2026-04-15', 'highfreq_event_stream_daily', 'daily', 'broad_market', 'pending', 'forced repair test', now(), null, now())
            on conflict (business_date, family_name, frequency, coverage_scope)
            do update set status='pending', reason='forced repair test', retry_after=now(), updated_at=now()
        """), {'id': str(uuid.uuid4())})
        conn.execute(text("""
            insert into ifa2.ifa_archive_repair_queue(id, business_date, family_name, frequency, coverage_scope, status, reason, retry_after, last_run_id, updated_at)
            values (cast(:id as uuid), '2026-04-15', 'highfreq_sector_breadth_daily', 'daily', 'broad_market', 'pending', 'forced repair test', now(), null, now())
            on conflict (business_date, family_name, frequency, coverage_scope)
            do update set status='pending', reason='forced repair test', retry_after=now(), updated_at=now()
        """), {'id': str(uuid.uuid4())})

    payload = _run('scripts/archive_v2_run.py', '--profile', 'profiles/archive_v2_milestone5_repair_retry_sample.json')
    assert payload['ok'] is True
    assert payload['status'] == 'completed'

    with ENGINE.begin() as conn:
        event_count = conn.execute(text("select count(*) from ifa2.ifa_archive_highfreq_event_stream_daily where business_date='2026-04-15'" )).scalar_one()
        breadth_count = conn.execute(text("select count(*) from ifa2.ifa_archive_highfreq_sector_breadth_daily where business_date='2026-04-15'" )).scalar_one()
        completeness = conn.execute(text("select family_name, status from ifa2.ifa_archive_completeness where business_date='2026-04-15' and family_name in ('highfreq_event_stream_daily','highfreq_sector_breadth_daily') order by family_name" )).mappings().all()
        queue_rows = conn.execute(text("select family_name, status from ifa2.ifa_archive_repair_queue where business_date='2026-04-15' and family_name in ('highfreq_event_stream_daily','highfreq_sector_breadth_daily') order by family_name" )).mappings().all()

    rerun = _run('scripts/archive_v2_run.py', '--profile', 'profiles/archive_v2_milestone5_repair_retry_sample.json')
    assert rerun['ok'] is True
    assert rerun['status'] == 'completed'

    with ENGINE.begin() as conn:
        rerun_event_count = conn.execute(text("select count(*) from ifa2.ifa_archive_highfreq_event_stream_daily where business_date='2026-04-15'" )).scalar_one()
    assert event_count > 0
    assert breadth_count > 0
    assert [row['status'] for row in completeness] == ['completed', 'completed']
    assert [row['status'] for row in queue_rows] == ['completed', 'completed']
    assert rerun_event_count == event_count
