"""Derived highfreq signal layer for milestone 4."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import text

from ifa_data_platform.db.engine import make_engine


class DerivedSignalBuilder:
    def __init__(self) -> None:
        self.engine = make_engine()

    def _reset_working_tables(self, conn) -> None:
        conn.execute(text("TRUNCATE TABLE ifa2.highfreq_sector_breadth_working"))
        conn.execute(text("TRUNCATE TABLE ifa2.highfreq_sector_heat_working"))
        conn.execute(text("TRUNCATE TABLE ifa2.highfreq_leader_candidate_working"))
        conn.execute(text("TRUNCATE TABLE ifa2.highfreq_limit_event_stream_working"))
        conn.execute(text("TRUNCATE TABLE ifa2.highfreq_intraday_signal_state_working"))

    def build(self) -> dict:
        with self.engine.begin() as conn:
            self._reset_working_tables(conn)
            stock_rows = conn.execute(
                text(
                    """
                    SELECT ts_code, trade_time, open, close, amount
                    FROM ifa2.highfreq_stock_1m_working
                    ORDER BY trade_time DESC
                    LIMIT 50
                    """
                )
            ).mappings().all()
            proxy_rows = conn.execute(
                text(
                    """
                    SELECT proxy_code, trade_time, open, close, vol
                    FROM ifa2.highfreq_proxy_1m_working
                    ORDER BY trade_time DESC
                    LIMIT 20
                    """
                )
            ).mappings().all()
            limit_rows = conn.execute(
                text(
                    """
                    SELECT ts_code, trade_date, close, vol, amount
                    FROM ifa2.highfreq_close_auction_working
                    ORDER BY trade_date DESC
                    LIMIT 20
                    """
                )
            ).mappings().all()

            latest_time = stock_rows[0]['trade_time'] if stock_rows else datetime.utcnow()

            up_count = sum(1 for r in stock_rows if r['close'] is not None and r['open'] is not None and r['close'] > r['open'])
            down_count = sum(1 for r in stock_rows if r['close'] is not None and r['open'] is not None and r['close'] < r['open'])
            strong_count = sum(1 for r in stock_rows if r['amount'] is not None and float(r['amount']) > 0)
            limit_up_count = len(limit_rows)
            spread_ratio = (up_count - down_count) / max(up_count + down_count, 1)

            sector_code = proxy_rows[0]['proxy_code'] if proxy_rows else 'proxy_unavailable'
            heat_score = max(float(proxy_rows[0]['close'] or 0) - float(proxy_rows[0]['open'] or 0), 0) if proxy_rows else 0.0

            leader_candidates = []
            for r in stock_rows[:10]:
                score = 0.0
                if r['open'] is not None and r['close'] is not None and float(r['open']) != 0:
                    score = (float(r['close']) - float(r['open'])) / float(r['open'])
                leader_candidates.append(
                    {
                        'symbol': r['ts_code'],
                        'candidate_score': score,
                        'confirmation_state': 'confirmed' if score > 0.01 else 'watch',
                        'continuation_health': 'healthy' if score > 0 else 'fragile',
                    }
                )

            event_rows = []
            for r in limit_rows:
                event_rows.append(
                    {
                        'symbol': r['ts_code'],
                        'event_type': 'limit_event_proxy',
                        'price': r['close'],
                        'payload': str(dict(r)),
                    }
                )

            turnover_progress = strong_count / max(len(stock_rows), 1)
            amount_progress = sum(float(r['amount'] or 0) for r in stock_rows) / max(len(stock_rows), 1)
            emotion_stage = 'warm' if spread_ratio > 0 else 'cool'
            validation_state = 'confirmed' if up_count >= down_count else 'challenged'
            risk_state = 'opportunity' if heat_score > 0 else 'risk_watch'

            conn.execute(
                text(
                    """
                    INSERT INTO ifa2.highfreq_sector_breadth_working (
                        id, trade_time, sector_code, up_count, down_count, limit_up_count, strong_count, spread_ratio
                    ) VALUES (
                        :id, :trade_time, :sector_code, :up_count, :down_count, :limit_up_count, :strong_count, :spread_ratio
                    )
                    """
                ),
                {
                    'id': str(uuid.uuid4()),
                    'trade_time': latest_time,
                    'sector_code': sector_code,
                    'up_count': up_count,
                    'down_count': down_count,
                    'limit_up_count': limit_up_count,
                    'strong_count': strong_count,
                    'spread_ratio': spread_ratio,
                },
            )

            conn.execute(
                text(
                    """
                    INSERT INTO ifa2.highfreq_sector_heat_working (
                        id, trade_time, sector_code, heat_score
                    ) VALUES (
                        :id, :trade_time, :sector_code, :heat_score
                    )
                    """
                ),
                {
                    'id': str(uuid.uuid4()),
                    'trade_time': latest_time,
                    'sector_code': sector_code,
                    'heat_score': heat_score,
                },
            )

            for item in leader_candidates:
                conn.execute(
                    text(
                        """
                        INSERT INTO ifa2.highfreq_leader_candidate_working (
                            id, trade_time, symbol, candidate_score, confirmation_state, continuation_health
                        ) VALUES (
                            :id, :trade_time, :symbol, :candidate_score, :confirmation_state, :continuation_health
                        )
                        """
                    ),
                    {
                        'id': str(uuid.uuid4()),
                        'trade_time': latest_time,
                        **item,
                    },
                )

            for item in event_rows:
                conn.execute(
                    text(
                        """
                        INSERT INTO ifa2.highfreq_limit_event_stream_working (
                            id, trade_time, symbol, event_type, price, payload
                        ) VALUES (
                            :id, :trade_time, :symbol, :event_type, :price, :payload
                        )
                        """
                    ),
                    {
                        'id': str(uuid.uuid4()),
                        'trade_time': latest_time,
                        **item,
                    },
                )

            conn.execute(
                text(
                    """
                    INSERT INTO ifa2.highfreq_intraday_signal_state_working (
                        id, trade_time, scope_key, emotion_stage, validation_state, risk_opportunity_state, turnover_progress, amount_progress
                    ) VALUES (
                        :id, :trade_time, :scope_key, :emotion_stage, :validation_state, :risk_opportunity_state, :turnover_progress, :amount_progress
                    )
                    """
                ),
                {
                    'id': str(uuid.uuid4()),
                    'trade_time': latest_time,
                    'scope_key': 'market_scope',
                    'emotion_stage': emotion_stage,
                    'validation_state': validation_state,
                    'risk_opportunity_state': risk_state,
                    'turnover_progress': turnover_progress,
                    'amount_progress': amount_progress,
                },
            )

        return {
            'sector_code': sector_code,
            'up_count': up_count,
            'down_count': down_count,
            'limit_up_count': limit_up_count,
            'strong_count': strong_count,
            'spread_ratio': spread_ratio,
            'heat_score': heat_score,
            'leader_candidate_count': len(leader_candidates),
            'limit_event_count': len(event_rows),
            'emotion_stage': emotion_stage,
            'validation_state': validation_state,
            'risk_opportunity_state': risk_state,
            'turnover_progress': turnover_progress,
            'amount_progress': amount_progress,
        }
