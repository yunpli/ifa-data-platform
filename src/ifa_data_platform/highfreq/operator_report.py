"""Operator-facing status summary for highfreq lane."""

from __future__ import annotations

from sqlalchemy import text

from ifa_data_platform.db.engine import make_engine


class OperatorReport:
    def __init__(self) -> None:
        self.engine = make_engine()

    def build(self) -> dict:
        with self.engine.begin() as conn:
            latest_run = conn.execute(
                text(
                    """
                    select id, status, summary
                    from ifa2.unified_runtime_runs
                    where lane='highfreq'
                    order by started_at desc
                    limit 1
                    """
                )
            ).mappings().first()
            run_count = conn.execute(text("select count(*) from ifa2.highfreq_runs")).scalar_one()
            active_scope_count = conn.execute(text("select count(*) from ifa2.highfreq_active_scope")).scalar_one()
            dynamic_count = conn.execute(text("select count(*) from ifa2.highfreq_dynamic_candidate")).scalar_one()
            summary_count = conn.execute(text("select count(*) from ifa2.highfreq_execution_summary")).scalar_one()
            rows = conn.execute(
                text(
                    """
                    select window_type, group_name, last_status, sla_status, duration_ms
                    from ifa2.highfreq_window_state
                    order by last_run_time desc nulls last
                    limit 10
                    """
                )
            ).fetchall()
            recent_windows = [
                {
                    'window_type': r[0],
                    'group_name': r[1],
                    'last_status': r[2],
                    'sla_status': r[3],
                    'duration_ms': r[4],
                }
                for r in rows
            ]
        return {
            'lane': 'highfreq',
            'latest_run': dict(latest_run) if latest_run else None,
            'highfreq_run_rows': run_count,
            'active_scope_count': active_scope_count,
            'dynamic_candidate_count': dynamic_count,
            'execution_summary_count': summary_count,
            'recent_windows': recent_windows,
        }
