from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone, timedelta, date
from decimal import Decimal

from ifa_data_platform.tushare.client import TushareClient
from sqlalchemy import text

from ifa_data_platform.archive_v2.db import engine, ensure_schema
from ifa_data_platform.archive_v2.operator import build_repair_state
from ifa_data_platform.archive_v2.profile import ArchiveProfile, load_profile, validate_profile

SUPPORTED_DAILY_FAMILIES = {
    'equity_daily', 'index_daily', 'etf_daily', 'non_equity_daily', 'macro_daily',
    'announcements_daily', 'news_daily', 'research_reports_daily', 'investor_qa_daily',
    'dragon_tiger_daily', 'limit_up_detail_daily', 'limit_up_down_status_daily', 'sector_performance_daily',
    'highfreq_signal_daily',
    'highfreq_event_stream_daily',
    'highfreq_limit_event_stream_daily',
    'highfreq_sector_breadth_daily',
    'highfreq_sector_heat_daily',
    'highfreq_leader_candidate_daily',
    'highfreq_intraday_signal_state_daily',
    'generic_structured_output_daily',
}

IMPLEMENTED_FAMILIES = {
    'equity_daily', 'index_daily', 'etf_daily', 'non_equity_daily', 'macro_daily',
    'announcements_daily', 'news_daily', 'research_reports_daily', 'investor_qa_daily',
    'dragon_tiger_daily', 'limit_up_detail_daily', 'limit_up_down_status_daily', 'sector_performance_daily',
    'highfreq_event_stream_daily',
    'highfreq_limit_event_stream_daily',
    'highfreq_sector_breadth_daily',
    'highfreq_sector_heat_daily',
    'highfreq_leader_candidate_daily',
    'highfreq_intraday_signal_state_daily',
}

NOT_IMPLEMENTED_NOTES = {
    'highfreq_signal_daily': 'legacy placeholder only; superseded by explicit Milestone 4 highfreq archive-v2 families',
    'generic_structured_output_daily': 'generic structured-output catch-all is not archive-v2 worthy because it collapses unrelated finalized truths into one lossy bucket',
}

NON_COMPLETED_STATUSES = {'partial', 'incomplete', 'retry_needed', 'missing'}
REPAIR_QUEUE_PENDING_STATUSES = {'pending', 'retry_needed'}
TARGET_POLICY_ALL = 'all'
TARGET_POLICY_GAPS = 'gaps'
TARGET_POLICY_REPAIR = 'repair'

MARKET_CALENDAR_FAMILIES = {
    'equity_daily', 'index_daily', 'etf_daily', 'non_equity_daily', 'macro_daily',
    'announcements_daily', 'news_daily', 'research_reports_daily', 'investor_qa_daily',
    'dragon_tiger_daily', 'limit_up_detail_daily', 'limit_up_down_status_daily', 'sector_performance_daily',
}

FAMILY_DATE_SOURCE = {
    'announcements_daily': ('announcements_history', 'ann_date', False),
    'news_daily': ('news_history', 'datetime', True),
    'research_reports_daily': ('research_reports_history', 'trade_date', False),
    'investor_qa_daily': ('investor_qa_history', 'trade_date', False),
    'dragon_tiger_daily': ('dragon_tiger_list_history', 'trade_date', False),
    'limit_up_detail_daily': ('limit_up_detail_history', 'trade_date', False),
    'limit_up_down_status_daily': ('limit_up_down_status_history', 'trade_date', False),
    'sector_performance_daily': ('sector_performance_history', 'trade_date', False),
    'highfreq_event_stream_daily': ('highfreq_event_stream_working', 'event_time', True),
    'highfreq_limit_event_stream_daily': ('highfreq_limit_event_stream_working', 'trade_time', True),
    'highfreq_sector_breadth_daily': ('highfreq_sector_breadth_working', 'trade_time', True),
    'highfreq_sector_heat_daily': ('highfreq_sector_heat_working', 'trade_time', True),
    'highfreq_leader_candidate_daily': ('highfreq_leader_candidate_working', 'trade_time', True),
    'highfreq_intraday_signal_state_daily': ('highfreq_intraday_signal_state_working', 'trade_time', True),
}

IDENTITY_POLICY_BY_FAMILY = {
    'equity_daily': '(business_date, ts_code)',
    'index_daily': '(business_date, ts_code)',
    'etf_daily': '(business_date, ts_code)',
    'non_equity_daily': '(business_date, family_code, ts_code)',
    'macro_daily': '(business_date, macro_series)',
    'announcements_daily': '(business_date, ts_code, title)',
    'news_daily': '(business_date, news_time, title)',
    'research_reports_daily': '(business_date, ts_code, title)',
    'investor_qa_daily': '(business_date, ts_code, pub_time)',
    'dragon_tiger_daily': '(business_date, ts_code)',
    'limit_up_detail_daily': '(business_date, ts_code)',
    'limit_up_down_status_daily': '(business_date)',
    'sector_performance_daily': '(business_date, sector_code)',
    'highfreq_event_stream_daily': '(business_date, row_key[event_time|event_type|symbol|source|title])',
    'highfreq_limit_event_stream_daily': '(business_date, row_key[trade_time|event_type|symbol|source|title])',
    'highfreq_sector_breadth_daily': '(business_date, sector_code)',
    'highfreq_sector_heat_daily': '(business_date, sector_code)',
    'highfreq_leader_candidate_daily': '(business_date, symbol)',
    'highfreq_intraday_signal_state_daily': '(business_date, scope_key)',
}


class ArchiveV2Runner:
    def __init__(self, profile_path: str):
        self.profile_path = str(profile_path)
        self.profile: ArchiveProfile = load_profile(profile_path)
        self.run_id = uuid.uuid4()
        self.client = TushareClient()

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
        family_groups = self.profile.family_groups or sorted(SUPPORTED_DAILY_FAMILIES)
        if self.profile.mode == 'single_day':
            return self._run_dates([self.profile.start_date], family_groups, TARGET_POLICY_REPAIR if self.profile.repair_incomplete else TARGET_POLICY_ALL)
        if self.profile.mode == 'date_range':
            return self._run_dates(self._expand_date_range(), family_groups, TARGET_POLICY_REPAIR if self.profile.repair_incomplete else TARGET_POLICY_ALL)
        if self.profile.mode == 'backfill':
            return self._run_dates(self._resolve_backfill_dates(family_groups), family_groups, TARGET_POLICY_REPAIR if self.profile.repair_incomplete else TARGET_POLICY_GAPS)
        if self.profile.mode == 'delete':
            self._write_item('archive_delete_scope', 'daily', None, 'partial', 0, [], notes='delete mode skeleton only; no family deletion implemented yet')
            return {'status': 'partial', 'notes': 'delete mode skeleton executed; no data deletion implemented in Milestone 5 batch'}
        return {'status': 'failed', 'error_text': f'unsupported mode {self.profile.mode}'}

    def _expand_date_range(self) -> list[str]:
        start = datetime.fromisoformat(self.profile.start_date).date()
        end = datetime.fromisoformat(self.profile.end_date).date()
        days: list[str] = []
        cur = start
        while cur <= end:
            days.append(cur.isoformat())
            cur += timedelta(days=1)
        return days

    def _resolve_backfill_dates(self, family_groups: list[str]) -> list[str]:
        anchor = datetime.fromisoformat(self.profile.end_date).date() if self.profile.end_date else datetime.now(timezone.utc).date()
        candidate_dates: set[date] = set()
        fetch_limit = max(int(self.profile.backfill_days or 0) * 4, 12)
        for family in family_groups:
            candidate_dates.update(self._available_dates_for_family(family, anchor, fetch_limit))
        ordered = sorted([d for d in candidate_dates if d <= anchor], reverse=True)
        selected = ordered[: int(self.profile.backfill_days or 0)]
        return [d.isoformat() for d in sorted(selected)]

    def _available_dates_for_family(self, family: str, anchor: date, limit: int) -> list[date]:
        if family in MARKET_CALENDAR_FAMILIES:
            sql = "select distinct trade_date as d from ifa2.index_daily_bar_history where trade_date <= :anchor order by d desc limit :limit"
            with engine.begin() as conn:
                return [r['d'] for r in conn.execute(text(sql), {'anchor': anchor, 'limit': limit}).mappings().all()]
        if family in FAMILY_DATE_SOURCE:
            table, col, is_ts = FAMILY_DATE_SOURCE[family]
            date_expr = f'date({col})' if is_ts else col
            sql = f"select distinct {date_expr} as d from ifa2.{table} where {date_expr} <= :anchor order by d desc limit :limit"
            with engine.begin() as conn:
                return [r['d'] for r in conn.execute(text(sql), {'anchor': anchor, 'limit': limit}).mappings().all()]
        return []

    def _run_dates(self, dates: list[str], family_groups: list[str], target_policy: str) -> dict:
        final_status = 'completed'
        notes = []
        executed_targets = 0
        skipped_targets = 0
        if not dates:
            return {'status': 'completed', 'notes': 'no eligible dates resolved for requested bounded execution'}

        for d in dates:
            for family in family_groups:
                if family not in SUPPORTED_DAILY_FAMILIES:
                    self._write_item(family, 'daily', d, 'incomplete', 0, [], notes='unsupported family group in Milestone 5 batch')
                    self._upsert_completeness(d, family, 'daily', self._coverage_scope(), 'incomplete', 0, 'unsupported family group in Milestone 5 batch')
                    final_status = 'partial'
                    continue

                decision, decision_note = self._target_decision(d, family, target_policy)
                if decision == 'skip':
                    self._write_item(family, 'daily', d, 'superseded', 0, [], notes=decision_note)
                    skipped_targets += 1
                    continue

                if family not in IMPLEMENTED_FAMILIES:
                    note = self._decorate_note(family, NOT_IMPLEMENTED_NOTES.get(family, 'family scaffold only; execution not implemented in current batch'))
                    self._write_item(family, 'daily', d, 'incomplete', 0, [], notes=note)
                    self._upsert_completeness(d, family, 'daily', self._coverage_scope(), 'incomplete', 0, note)
                    final_status = 'partial'
                    executed_targets += 1
                    continue

                rows_written, tables_touched, item_status, item_notes, item_error = self._execute_family(family, d)
                effective_note = self._decorate_note(family, item_notes)
                self._write_item(family, 'daily', d, item_status, rows_written, tables_touched, notes=effective_note, error_text=item_error)
                self._upsert_completeness(d, family, 'daily', self._coverage_scope(), item_status, rows_written, item_error or effective_note if item_status != 'completed' else None)
                if item_status != 'completed':
                    final_status = 'partial'
                executed_targets += 1

        if final_status == 'partial':
            notes.append('Archive V2 multi-date execution ran with truthful non-complete states preserved where families/dates were missing, unstable, or intentionally unarchived')
        else:
            notes.append('Archive V2 multi-date execution completed for the eligible requested scope')
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
            selection_note = (
                f"repair_batch selected priority={target.get('priority')} urgency={target.get('urgency')} "
                f"actionability={target.get('actionability')} reason_code={target.get('reason_code')}"
            )
            if family not in IMPLEMENTED_FAMILIES:
                note = self._decorate_note(family, f'{selection_note} | family execution not implemented in current batch')
                self._write_item(family, 'daily', business_date, 'incomplete', 0, [], notes=note)
                self._upsert_completeness(business_date, family, 'daily', self._coverage_scope(), 'incomplete', 0, note)
                final_status = 'partial'
                executed_targets += 1
                continue

            rows_written, tables_touched, item_status, item_notes, item_error = self._execute_family(family, business_date)
            effective_note = self._decorate_note(family, f'{selection_note} | {item_notes}' if item_notes else selection_note)
            self._write_item(family, 'daily', business_date, item_status, rows_written, tables_touched, notes=effective_note, error_text=item_error)
            self._upsert_completeness(business_date, family, 'daily', self._coverage_scope(), item_status, rows_written, item_error or effective_note if item_status != 'completed' else None)
            if item_status != 'completed':
                final_status = 'partial'
            executed_targets += 1

        return {
            'status': final_status,
            'selected_targets': executed_targets,
            'notes': f'operator repair batch executed selected_targets={executed_targets}'
        }

    def _target_decision(self, business_date: str, family: str, target_policy: str) -> tuple[str, str | None]:
        if target_policy == TARGET_POLICY_ALL:
            return 'run', None

        completeness = self._get_completeness(business_date, family)
        queue_row = self._get_repair_queue_row(business_date, family)

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

    def _get_completeness(self, business_date: str, family: str):
        with engine.begin() as conn:
            return conn.execute(text("""
                select status, row_count, last_error, last_run_id
                from ifa2.ifa_archive_completeness
                where business_date = :business_date
                  and family_name = :family_name
                  and frequency = 'daily'
                  and coverage_scope = :coverage_scope
            """), {
                'business_date': business_date,
                'family_name': family,
                'coverage_scope': self._coverage_scope(),
            }).mappings().first()

    def _get_repair_queue_row(self, business_date: str, family: str):
        with engine.begin() as conn:
            return conn.execute(text("""
                select status, reason, reason_code, actionability, priority, urgency, retry_count, retry_after, claim_id, claimed_by, claim_expires_at, last_run_id
                from ifa2.ifa_archive_repair_queue
                where business_date = :business_date
                  and family_name = :family_name
                  and frequency = 'daily'
                  and coverage_scope = :coverage_scope
            """), {
                'business_date': business_date,
                'family_name': family,
                'coverage_scope': self._coverage_scope(),
            }).mappings().first()

    def _execute_family(self, family: str, business_date: str):
        trade_date = business_date.replace('-', '')
        if family == 'equity_daily':
            rows = self.client.query('daily', {'trade_date': trade_date}, timeout_sec=30, max_retries=2)
            return self._write_json_rows('ifa_archive_equity_daily', business_date, rows, 'ts_code')
        if family == 'index_daily':
            rows = self._fetch_history_rows('index_daily_bar_history', 'trade_date', business_date)
            return self._write_json_rows('ifa_archive_index_daily', business_date, rows, 'ts_code', note='index daily archive written from retained final history truth')
        if family == 'etf_daily':
            rows = self.client.query('fund_daily', {'trade_date': trade_date}, timeout_sec=30, max_retries=2)
            return self._write_json_rows('ifa_archive_etf_daily', business_date, rows, 'ts_code')
        if family == 'non_equity_daily':
            rows = self.client.query('fut_daily', {'trade_date': trade_date}, timeout_sec=30, max_retries=2)
            if not rows:
                return 0, ['ifa_archive_non_equity_daily'], 'incomplete', 'source returned no non-equity daily rows for sample date', None
            return self._write_non_equity_rows('ifa_archive_non_equity_daily', business_date, rows)
        if family == 'macro_daily':
            rows = self._fetch_macro_rows(business_date)
            if not rows:
                return 0, ['ifa_archive_macro_daily'], 'incomplete', 'no macro snapshot rows available on or before business_date', None
            return self._write_macro_rows('ifa_archive_macro_daily', business_date, rows)
        if family == 'announcements_daily':
            rows = self._fetch_history_rows('announcements_history', 'ann_date', business_date)
            return self._write_multi_key_rows('ifa_archive_announcements_daily', business_date, rows, ['ts_code', 'title'], note='daily finalized announcements archived from retained history truth')
        if family == 'news_daily':
            rows = self._fetch_history_rows_by_date('news_history', 'datetime', business_date)
            return self._write_news_rows('ifa_archive_news_daily', business_date, rows)
        if family == 'research_reports_daily':
            rows = self._fetch_history_rows('research_reports_history', 'trade_date', business_date)
            return self._write_multi_key_rows('ifa_archive_research_reports_daily', business_date, rows, ['ts_code', 'title'], note='daily finalized research reports archived from retained history truth')
        if family == 'investor_qa_daily':
            rows = self._fetch_history_rows('investor_qa_history', 'trade_date', business_date)
            return self._write_investor_qa_rows('ifa_archive_investor_qa_daily', business_date, rows)
        if family == 'dragon_tiger_daily':
            rows = self._fetch_history_rows('dragon_tiger_list_history', 'trade_date', business_date)
            return self._write_json_rows('ifa_archive_dragon_tiger_daily', business_date, rows, 'ts_code', note='daily finalized dragon tiger list archived from retained history truth')
        if family == 'limit_up_detail_daily':
            rows = self._fetch_history_rows('limit_up_detail_history', 'trade_date', business_date)
            return self._write_json_rows('ifa_archive_limit_up_detail_daily', business_date, rows, 'ts_code', note='daily finalized limit-up detail archived from retained history truth')
        if family == 'limit_up_down_status_daily':
            rows = self._fetch_history_rows('limit_up_down_status_history', 'trade_date', business_date)
            return self._write_singleton_rows('ifa_archive_limit_up_down_status_daily', business_date, rows, note='daily finalized market-wide limit status archived from retained history truth')
        if family == 'sector_performance_daily':
            rows = self._fetch_history_rows('sector_performance_history', 'trade_date', business_date)
            return self._write_json_rows('ifa_archive_sector_performance_daily', business_date, rows, 'sector_code', note='daily finalized sector performance archived from retained history truth')
        if family == 'highfreq_event_stream_daily':
            rows = self._fetch_history_rows_by_date('highfreq_event_stream_working', 'event_time', business_date)
            return self._write_event_rows('ifa_archive_highfreq_event_stream_daily', business_date, rows, 'event_time', note='daily finalized highfreq event stream archived with event-semantics retention')
        if family == 'highfreq_limit_event_stream_daily':
            rows = self._fetch_history_rows_by_date('highfreq_limit_event_stream_working', 'trade_time', business_date)
            return self._write_event_rows('ifa_archive_highfreq_limit_event_stream_daily', business_date, rows, 'trade_time', note='daily finalized highfreq limit-event stream archived with event-semantics retention')
        if family == 'highfreq_sector_breadth_daily':
            rows = self._fetch_latest_daily_rows('highfreq_sector_breadth_working', business_date, ['sector_code'], 'trade_time')
            return self._write_snapshot_rows('ifa_archive_highfreq_sector_breadth_daily', business_date, rows, ['sector_code'], 'snapshot_time', 'trade_time', note='daily finalized highfreq sector breadth archived as latest per-sector snapshot')
        if family == 'highfreq_sector_heat_daily':
            rows = self._fetch_latest_daily_rows('highfreq_sector_heat_working', business_date, ['sector_code'], 'trade_time')
            return self._write_snapshot_rows('ifa_archive_highfreq_sector_heat_daily', business_date, rows, ['sector_code'], 'snapshot_time', 'trade_time', note='daily finalized highfreq sector heat archived as latest per-sector snapshot')
        if family == 'highfreq_leader_candidate_daily':
            rows = self._fetch_latest_daily_rows('highfreq_leader_candidate_working', business_date, ['symbol'], 'trade_time')
            return self._write_snapshot_rows('ifa_archive_highfreq_leader_candidate_daily', business_date, rows, ['symbol'], 'snapshot_time', 'trade_time', note='daily finalized highfreq leader candidates archived as latest per-symbol state')
        if family == 'highfreq_intraday_signal_state_daily':
            rows = self._fetch_latest_daily_rows('highfreq_intraday_signal_state_working', business_date, ['scope_key'], 'trade_time')
            return self._write_snapshot_rows('ifa_archive_highfreq_intraday_signal_state_daily', business_date, rows, ['scope_key'], 'snapshot_time', 'trade_time', note='daily finalized highfreq signal state archived as latest per-scope state')
        return 0, [], 'incomplete', 'family execution not implemented', None

    def _fetch_history_rows(self, table: str, date_col: str, business_date: str):
        with engine.begin() as conn:
            return [self._normalize_record(dict(r)) for r in conn.execute(text(f"select * from ifa2.{table} where {date_col} = :d"), {'d': business_date}).mappings().all()]

    def _fetch_history_rows_by_date(self, table: str, ts_col: str, business_date: str):
        with engine.begin() as conn:
            return [self._normalize_record(dict(r)) for r in conn.execute(text(f"select * from ifa2.{table} where date({ts_col}) = :d"), {'d': business_date}).mappings().all()]

    def _fetch_latest_daily_rows(self, table: str, business_date: str, key_cols: list[str], ts_col: str):
        partition = ', '.join(key_cols)
        sql = f"""
            select *
            from (
                select *, row_number() over (partition by {partition} order by {ts_col} desc, created_at desc nulls last) as rn
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

    def _normalize_record(self, record: dict):
        out = {}
        for k, v in record.items():
            if isinstance(v, Decimal):
                out[k] = float(v)
            elif isinstance(v, (datetime, )):
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
                    conn.execute(text(f"insert into ifa2.{table}(business_date, {key_col}, payload) values (:business_date, :key, CAST(:payload as jsonb)) on conflict (business_date, {key_col}) do update set payload=excluded.payload"), {
                        'business_date': business_date,
                        'key': r[key_col],
                        'payload': json.dumps(r, ensure_ascii=False, default=str),
                    })
        return len(rows), [table], 'completed', note, None

    def _write_multi_key_rows(self, table: str, business_date: str, rows: list[dict], keys: list[str], note: str):
        if not rows:
            return 0, [table], 'incomplete', 'source/history returned no rows', None
        if self.profile.write_enabled:
            with engine.begin() as conn:
                for r in rows:
                    conn.execute(text(f"insert into ifa2.{table}(business_date, {keys[0]}, {keys[1]}, payload) values (:business_date, :k1, :k2, CAST(:payload as jsonb)) on conflict (business_date, {keys[0]}, {keys[1]}) do update set payload=excluded.payload"), {
                        'business_date': business_date,
                        'k1': r[keys[0]],
                        'k2': r[keys[1]],
                        'payload': json.dumps(r, ensure_ascii=False, default=str),
                    })
        return len(rows), [table], 'completed', note, None

    def _write_news_rows(self, table: str, business_date: str, rows: list[dict]):
        if not rows:
            return 0, [table], 'incomplete', 'source/history returned no news rows', None
        if self.profile.write_enabled:
            with engine.begin() as conn:
                for r in rows:
                    conn.execute(text(f"insert into ifa2.{table}(business_date, news_time, title, payload) values (:business_date, :news_time, :title, CAST(:payload as jsonb)) on conflict (business_date, news_time, title) do update set payload=excluded.payload"), {
                        'business_date': business_date,
                        'news_time': r['datetime'],
                        'title': r['title'],
                        'payload': json.dumps(r, ensure_ascii=False, default=str),
                    })
        return len(rows), [table], 'completed', 'daily finalized news archived from retained history truth', None

    def _write_investor_qa_rows(self, table: str, business_date: str, rows: list[dict]):
        if not rows:
            return 0, [table], 'incomplete', 'source/history returned no investor QA rows', None
        if self.profile.write_enabled:
            with engine.begin() as conn:
                for r in rows:
                    conn.execute(text(f"insert into ifa2.{table}(business_date, ts_code, pub_time, payload) values (:business_date, :ts_code, :pub_time, CAST(:payload as jsonb)) on conflict (business_date, ts_code, pub_time) do update set payload=excluded.payload"), {
                        'business_date': business_date,
                        'ts_code': r['ts_code'],
                        'pub_time': r['pub_time'],
                        'payload': json.dumps(r, ensure_ascii=False, default=str),
                    })
        return len(rows), [table], 'completed', 'daily finalized investor QA archived from retained history truth', None

    def _write_singleton_rows(self, table: str, business_date: str, rows: list[dict], note: str):
        if not rows:
            return 0, [table], 'incomplete', 'source/history returned no rows', None
        row = rows[0]
        if self.profile.write_enabled:
            with engine.begin() as conn:
                conn.execute(text(f"insert into ifa2.{table}(business_date, payload) values (:business_date, CAST(:payload as jsonb)) on conflict (business_date) do update set payload=excluded.payload"), {
                    'business_date': business_date,
                    'payload': json.dumps(row, ensure_ascii=False, default=str),
                })
        return 1, [table], 'completed', note, None

    def _write_non_equity_rows(self, table: str, business_date: str, rows: list[dict]):
        if self.profile.write_enabled:
            with engine.begin() as conn:
                for r in rows:
                    ts_code = r.get('ts_code')
                    family_code = (ts_code.split('.')[1] if ts_code and '.' in ts_code else 'futures')
                    conn.execute(text(f"insert into ifa2.{table}(business_date, family_code, ts_code, payload) values (:business_date, :family_code, :ts_code, CAST(:payload as jsonb)) on conflict (business_date, family_code, ts_code) do update set payload=excluded.payload"), {
                        'business_date': business_date,
                        'family_code': family_code,
                        'ts_code': ts_code,
                        'payload': json.dumps(r, ensure_ascii=False),
                    })
        return len(rows), [table], 'completed', 'source-aligned non-equity daily archive written without forcing business over-split', None

    def _write_event_rows(self, table: str, business_date: str, rows: list[dict], time_col: str, note: str):
        if not rows:
            return 0, [table], 'incomplete', 'source/history returned no rows', None
        if self.profile.write_enabled:
            with engine.begin() as conn:
                for r in rows:
                    row_key = self._build_event_row_key(r, time_col)
                    conn.execute(text(f"insert into ifa2.{table}(business_date, row_key, {time_col}, event_type, symbol, payload) values (:business_date, :row_key, :event_time, :event_type, :symbol, CAST(:payload as jsonb)) on conflict (business_date, row_key) do update set {time_col}=excluded.{time_col}, event_type=excluded.event_type, symbol=excluded.symbol, payload=excluded.payload"), {
                        'business_date': business_date,
                        'row_key': row_key,
                        'event_time': r[time_col],
                        'event_type': r.get('event_type'),
                        'symbol': r.get('symbol'),
                        'payload': json.dumps(r, ensure_ascii=False, default=str),
                    })
        return len(rows), [table], 'completed', note, None

    def _build_event_row_key(self, row: dict, time_col: str) -> str:
        return '|'.join([
            str(row.get(time_col) or ''),
            str(row.get('event_type') or ''),
            str(row.get('symbol') or ''),
            str(row.get('source') or ''),
            str(row.get('title') or ''),
        ])

    def _write_snapshot_rows(self, table: str, business_date: str, rows: list[dict], key_cols: list[str], snapshot_col: str, source_time_col: str, note: str):
        if not rows:
            return 0, [table], 'incomplete', 'source/history returned no rows', None
        if self.profile.write_enabled:
            with engine.begin() as conn:
                for r in rows:
                    params = {
                        'business_date': business_date,
                        'payload': json.dumps(r, ensure_ascii=False, default=str),
                        'snapshot_time': r[source_time_col],
                    }
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
                    conn.execute(text(f"insert into ifa2.{table}(business_date, macro_series, payload) values (:business_date, :macro_series, CAST(:payload as jsonb)) on conflict (business_date, macro_series) do update set payload=excluded.payload"), {
                        'business_date': business_date,
                        'macro_series': r['macro_series'],
                        'payload': json.dumps(r, ensure_ascii=False, default=str),
                    })
        return len(rows), [table], 'completed', 'macro daily snapshot archived from retained source-side truth boundary', None

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

    def _create_run(self, status: str, trigger_source: str = 'manual_profile', notes: str | None = None):
        with engine.begin() as conn:
            conn.execute(text("""
                insert into ifa2.ifa_archive_runs(run_id, trigger_source, profile_name, profile_path, mode, start_time, status, notes)
                values (:run_id, :trigger_source, :profile_name, :profile_path, :mode, now(), :status, :notes)
            """), {
                'run_id': str(self.run_id),
                'trigger_source': trigger_source,
                'profile_name': self.profile.profile_name,
                'profile_path': self.profile_path,
                'mode': self.profile.mode,
                'status': status,
                'notes': notes or self.profile.notes,
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
                'coverage_scope': self._coverage_scope(),
                'business_date': business_date,
                'status': status,
                'rows_written': rows_written,
                'tables_touched': json.dumps(tables_touched),
                'notes': notes,
                'error_text': error_text,
            })

    def _upsert_completeness(self, business_date: str, family_name: str, frequency: str, coverage_scope: str, status: str, row_count: int, detail_text: str | None = None):
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
                'last_error': None if status == 'completed' else detail_text,
            })
        self._sync_repair_queue(business_date, family_name, frequency, coverage_scope, status, detail_text)

    def _sync_repair_queue(self, business_date: str, family_name: str, frequency: str, coverage_scope: str, status: str, detail_text: str | None):
        existing = self._get_repair_queue_row(business_date, family_name)
        if status in NON_COMPLETED_STATUSES:
            reason = detail_text or f'auto-enqueued because completeness status={status}'
            policy = build_repair_state(existing, family_name, status, reason)
            with engine.begin() as conn:
                conn.execute(text("""
                    insert into ifa2.ifa_archive_repair_queue(
                      id, business_date, family_name, frequency, coverage_scope, status, reason, reason_code, actionability,
                      priority, urgency, retry_count, retry_after, first_seen_at, last_attempt_at,
                      last_observed_status, escalation_level, last_error, last_run_id, updated_at
                    )
                    values (
                      :id, :business_date, :family_name, :frequency, :coverage_scope, 'pending', :reason, :reason_code, :actionability,
                      :priority, :urgency, :retry_count, :retry_after, now(), now(),
                      :last_observed_status, :escalation_level, :last_error, :last_run_id, now()
                    )
                    on conflict (business_date, family_name, frequency, coverage_scope)
                    do update set status='pending', reason=excluded.reason, reason_code=excluded.reason_code, actionability=excluded.actionability,
                      priority=excluded.priority, urgency=excluded.urgency, retry_count=excluded.retry_count,
                      retry_after=excluded.retry_after, claim_id=null, claimed_at=null, claimed_by=null, claim_expires_at=null,
                      last_attempt_at=excluded.last_attempt_at,
                      last_observed_status=excluded.last_observed_status, escalation_level=excluded.escalation_level,
                      last_error=excluded.last_error, last_run_id=excluded.last_run_id, updated_at=now()
                """), {
                    'id': str(uuid.uuid4()),
                    'business_date': business_date,
                    'family_name': family_name,
                    'frequency': frequency,
                    'coverage_scope': coverage_scope,
                    'reason': reason,
                    'reason_code': policy['reason_code'],
                    'actionability': policy['actionability'],
                    'priority': policy['priority'],
                    'urgency': policy['urgency'],
                    'retry_count': policy['retry_count'],
                    'retry_after': policy['retry_after'],
                    'last_observed_status': status,
                    'escalation_level': policy['escalation_level'],
                    'last_error': policy['last_error'],
                    'last_run_id': str(self.run_id),
                })
                conn.execute(text("""
                    update ifa2.ifa_archive_completeness
                    set retry_after = :retry_after,
                        last_error = :last_error,
                        updated_at = now()
                    where business_date = :business_date
                      and family_name = :family_name
                      and frequency = :frequency
                      and coverage_scope = :coverage_scope
                """), {
                    'retry_after': policy['retry_after'],
                    'last_error': reason,
                    'business_date': business_date,
                    'family_name': family_name,
                    'frequency': frequency,
                    'coverage_scope': coverage_scope,
                })
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
                where business_date = :business_date
                  and family_name = :family_name
                  and frequency = :frequency
                  and coverage_scope = :coverage_scope
            """), {
                'business_date': business_date,
                'family_name': family_name,
                'frequency': frequency,
                'coverage_scope': coverage_scope,
                'reason': 'repaired/completed by latest Archive V2 run',
                'last_observed_status': status,
                'last_run_id': str(self.run_id),
            })
            conn.execute(text("""
                update ifa2.ifa_archive_completeness
                set retry_after = null,
                    last_error = null,
                    updated_at = now()
                where business_date = :business_date
                  and family_name = :family_name
                  and frequency = :frequency
                  and coverage_scope = :coverage_scope
                  and status = 'completed'
            """), {
                'business_date': business_date,
                'family_name': family_name,
                'frequency': frequency,
                'coverage_scope': coverage_scope,
            })

    def _decorate_note(self, family_name: str, note: str | None) -> str | None:
        identity = IDENTITY_POLICY_BY_FAMILY.get(family_name)
        if not identity:
            return note
        if note:
            return f'{note} | identity={identity}'
        return f'identity={identity}'

    def _coverage_scope(self) -> str:
        return 'broad_market' if self.profile.broad_market else 'profile_scope'
