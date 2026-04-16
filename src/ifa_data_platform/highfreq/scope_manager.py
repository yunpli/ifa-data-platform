"""Business-Layer-driven scope management for highfreq milestone 5."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import text

from ifa_data_platform.db.engine import make_engine


@dataclass
class ScopeBuildResult:
    active_count: int
    dynamic_count: int
    active_scope_status: str
    dynamic_scope_status: str


class ScopeManager:
    def __init__(self) -> None:
        self.engine = make_engine()

    def rebuild(self) -> ScopeBuildResult:
        with self.engine.begin() as conn:
            conn.execute(text("delete from ifa2.highfreq_active_scope"))
            conn.execute(text("delete from ifa2.highfreq_dynamic_candidate"))

            rows = conn.execute(
                text(
                    """
                    select fl.list_type, fl.name, fi.symbol_or_series_id, fi.asset_category
                    from ifa2.focus_lists fl
                    join ifa2.focus_list_items fi on fi.list_id = fl.id
                    where fl.owner_type='default' and fl.owner_id='default'
                      and fl.list_type in ('key_focus','focus','tech_key_focus','tech_focus')
                    """
                )
            ).fetchall()

            priority_map = {
                'key_focus': (100, 'deep_focus'),
                'tech_key_focus': (95, 'deep_focus'),
                'focus': (70, 'medium_focus'),
                'tech_focus': (65, 'medium_focus'),
            }

            active_seen = set()
            for list_type, list_name, symbol, asset_category in rows:
                if not symbol:
                    continue
                key = (symbol, list_type)
                if key in active_seen:
                    continue
                active_seen.add(key)
                priority, tier = priority_map[list_type]
                conn.execute(
                    text(
                        """
                        insert into ifa2.highfreq_active_scope (
                            id, symbol, asset_category, source_list_type, source_list_name,
                            scope_priority, scope_tier, scope_status, reason
                        ) values (
                            :id, :symbol, :asset_category, :source_list_type, :source_list_name,
                            :scope_priority, :scope_tier, :scope_status, :reason
                        )
                        """
                    ),
                    {
                        'id': str(uuid.uuid4()),
                        'symbol': symbol,
                        'asset_category': asset_category or 'unknown',
                        'source_list_type': list_type,
                        'source_list_name': list_name,
                        'scope_priority': priority,
                        'scope_tier': tier,
                        'scope_status': 'active',
                        'reason': 'business_layer_scope',
                    },
                )

            leader_rows = conn.execute(
                text(
                    """
                    select symbol, candidate_score, confirmation_state, continuation_health
                    from ifa2.highfreq_leader_candidate_working
                    order by candidate_score desc, trade_time desc
                    limit 10
                    """
                )
            ).fetchall()

            dynamic_count = 0
            for symbol, candidate_score, confirmation_state, continuation_health in leader_rows:
                trigger_reason = 'leader_candidate'
                if confirmation_state == 'confirmed':
                    trigger_reason = 'leader_confirmed'
                elif continuation_health == 'healthy':
                    trigger_reason = 'continuation_healthy'
                conn.execute(
                    text(
                        """
                        insert into ifa2.highfreq_dynamic_candidate (
                            id, symbol, candidate_type, trigger_reason, priority_score, upgrade_status
                        ) values (
                            :id, :symbol, :candidate_type, :trigger_reason, :priority_score, :upgrade_status
                        )
                        """
                    ),
                    {
                        'id': str(uuid.uuid4()),
                        'symbol': symbol,
                        'candidate_type': 'leader_or_hot_mover',
                        'trigger_reason': trigger_reason,
                        'priority_score': float(candidate_score or 0),
                        'upgrade_status': 'upgraded' if float(candidate_score or 0) > 0 else 'watch',
                    },
                )
                dynamic_count += 1

        return ScopeBuildResult(
            active_count=len(active_seen),
            dynamic_count=dynamic_count,
            active_scope_status='active_scope_landed',
            dynamic_scope_status='dynamic_upgrade_landed',
        )
