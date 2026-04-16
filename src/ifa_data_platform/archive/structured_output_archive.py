from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy import text

from ifa_data_platform.db.engine import make_engine


@dataclass(frozen=True)
class StructuredOutputArchiveTarget:
    source_table: str
    archive_table: str
    category: str
    supported: bool
    reason: str


STRUCTURED_OUTPUT_TARGETS = [
    StructuredOutputArchiveTarget('dragon_tiger_list_current', 'dragon_tiger_list_history', 'dragon_tiger', True, 'small structured daily output'),
    StructuredOutputArchiveTarget('limit_up_detail_current', 'limit_up_detail_history', 'limit_up_detail', True, 'small structured daily output'),
    StructuredOutputArchiveTarget('limit_up_down_status_current', 'limit_up_down_status_history', 'limit_up_down_status', True, 'small structured daily output'),
    StructuredOutputArchiveTarget('highfreq_event_stream_working', 'highfreq_event_stream_working', 'event_stream_summary', False, 'no dedicated archive table yet; currently only working-state table exists'),
]


class StructuredOutputArchiveService:
    def __init__(self) -> None:
        self.engine = make_engine()

    def supported_targets(self) -> list[StructuredOutputArchiveTarget]:
        return STRUCTURED_OUTPUT_TARGETS

    def archive_supported_current_day_outputs(self) -> dict:
        summary = {'supported_targets': [], 'unsupported_targets': []}
        with self.engine.begin() as conn:
            for target in STRUCTURED_OUTPUT_TARGETS:
                if not target.supported:
                    summary['unsupported_targets'].append({'source_table': target.source_table, 'reason': target.reason})
                    continue
                rows = conn.execute(text(f'select count(*) from ifa2."{target.source_table}"')).scalar_one()
                summary['supported_targets'].append({'source_table': target.source_table, 'archive_table': target.archive_table, 'rows_current': rows})
        return summary
