from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from sqlalchemy import text

from ifa_data_platform.archive_v2.db import engine, ensure_schema
from ifa_data_platform.archive_v2.profile import ArchiveProfile, load_profile, validate_profile

SUPPORTED_DAILY_FAMILIES = {
    'equity_daily', 'index_daily', 'etf_daily', 'non_equity_daily', 'macro_daily',
    'announcements_daily', 'news_daily', 'research_reports_daily', 'investor_qa_daily',
    'dragon_tiger_daily', 'limit_up_detail_daily', 'limit_up_down_status_daily', 'sector_performance_daily',
    'highfreq_signal_daily',
}

IMPLEMENTED_FAMILIES = set()


class ArchiveV2Runner:
    def __init__(self, profile_path: str):
        self.profile_path = str(profile_path)
        self.profile: ArchiveProfile = load_profile(profile_path)
        self.run_id = uuid.uuid4()

    def run(self) -> dict:
        ensure_schema()
        errors = validate_profile(self.profile)
        if errors:
            return {'ok': False, 'errors': errors}
        self._persist_profile()
        self._create_run('running')
        try:
            result = self._dispatch()
            self._finish_run(result['status'], result.get('notes'), result.get('error_text'))
            return {'ok': True, 'run_id': str(self.run_id), **result}
        except Exception as e:
            self._finish_run('failed', error_text=str(e))
            raise

    def _dispatch(self) -> dict:
        if self.profile.mode == 'single_day':
            return self._run_dates([self.profile.start_date])
        if self.profile.mode == 'date_range':
            return self._run_dates([self.profile.start_date, self.profile.end_date], range_mode=True)
        if self.profile.mode == 'backfill':
            days = [datetime.now(timezone.utc).date() - timedelta(days=i+1) for i in range(int(self.profile.backfill_days or 0))]
            return self._run_dates([d.isoformat() for d in days])
        if self.profile.mode == 'delete':
            self._write_item('archive_delete_scope', 'daily', None, 'partial', 0, [], notes='delete mode skeleton only; no family deletion implemented yet')
            return {'status': 'partial', 'notes': 'delete mode skeleton executed; no data deletion implemented in Milestone 1'}
        return {'status': 'failed', 'error_text': f'unsupported mode {self.profile.mode}'}

    def _run_dates(self, dates: list[str], range_mode: bool = False) -> dict:
        family_groups = self.profile.family_groups or sorted(SUPPORTED_DAILY_FAMILIES)
        final_status = 'completed'
        notes = []
        for d in dates:
            if range_mode and len(dates) == 2 and d == dates[1]:
                continue
            for family in family_groups:
                if family not in SUPPORTED_DAILY_FAMILIES:
                    self._write_item(family, 'daily', d, 'incomplete', 0, [], notes='unsupported family group in Milestone 1')
                    final_status = 'partial'
                    continue
                if family not in IMPLEMENTED_FAMILIES:
                    self._write_item(family, 'daily', d, 'incomplete', 0, [], notes='family scaffold only; execution not implemented in Milestone 1')
                    self._upsert_completeness(d, family, 'daily', 'broad_market' if self.profile.broad_market else 'profile_scope', 'incomplete', 0, 'family not yet implemented in Milestone 1')
                    final_status = 'partial'
                    continue
        if final_status == 'partial':
            notes.append('daily-only archive skeleton ran truthfully; selected families are scaffolded but not yet implemented')
        else:
            notes.append('daily-only archive skeleton completed')
        return {'status': final_status, 'notes': '; '.join(notes)}

    def _persist_profile(self):
        with engine.begin() as conn:
            conn.execute(text("""
                insert into ifa2.ifa_archive_profiles(profile_name, profile_path, profile_json, updated_at)
                values (:name, :path, CAST(:profile_json as jsonb), now())
                on conflict (profile_name)
                do update set profile_path=excluded.profile_path, profile_json=excluded.profile_json, updated_at=now()
            """), {
                'name': self.profile.profile_name,
                'path': self.profile_path,
                'profile_json': json.dumps(self.profile.__dict__, ensure_ascii=False),
            })

    def _create_run(self, status: str):
        with engine.begin() as conn:
            conn.execute(text("""
                insert into ifa2.ifa_archive_runs(run_id, trigger_source, profile_name, profile_path, mode, start_time, status, notes)
                values (:run_id, :trigger_source, :profile_name, :profile_path, :mode, now(), :status, :notes)
            """), {
                'run_id': str(self.run_id),
                'trigger_source': 'manual_profile',
                'profile_name': self.profile.profile_name,
                'profile_path': self.profile_path,
                'mode': self.profile.mode,
                'status': status,
                'notes': self.profile.notes,
            })

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
            """), {
                'id': str(uuid.uuid4()),
                'run_id': str(self.run_id),
                'family_name': family_name,
                'frequency': frequency,
                'coverage_scope': 'broad_market' if self.profile.broad_market else 'profile_scope',
                'business_date': business_date,
                'status': status,
                'rows_written': rows_written,
                'tables_touched': json.dumps(tables_touched),
                'notes': notes,
                'error_text': error_text,
            })

    def _upsert_completeness(self, business_date: str, family_name: str, frequency: str, coverage_scope: str, status: str, row_count: int, last_error: str | None = None):
        with engine.begin() as conn:
            conn.execute(text("""
                insert into ifa2.ifa_archive_completeness(id, business_date, family_name, frequency, coverage_scope, status, source_mode, last_run_id, row_count, retry_after, last_error, updated_at)
                values (:id, :business_date, :family_name, :frequency, :coverage_scope, :status, :source_mode, :last_run_id, :row_count, :retry_after, :last_error, now())
                on conflict (business_date, family_name, frequency, coverage_scope)
                do update set status=excluded.status, source_mode=excluded.source_mode, last_run_id=excluded.last_run_id, row_count=excluded.row_count, retry_after=excluded.retry_after, last_error=excluded.last_error, updated_at=now()
            """), {
                'id': str(uuid.uuid4()),
                'business_date': business_date,
                'family_name': family_name,
                'frequency': frequency,
                'coverage_scope': coverage_scope,
                'status': status,
                'source_mode': self.profile.mode,
                'last_run_id': str(self.run_id),
                'row_count': row_count,
                'retry_after': None,
                'last_error': last_error,
            })
