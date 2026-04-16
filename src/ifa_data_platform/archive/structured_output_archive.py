from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import date
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
    key_fields: tuple[str, ...]


STRUCTURED_OUTPUT_TARGETS = [
    StructuredOutputArchiveTarget('dragon_tiger_list_current', 'daily_structured_output_archive', 'dragon_tiger', True, 'small structured daily output', ('ts_code', 'trade_date')),
    StructuredOutputArchiveTarget('limit_up_detail_current', 'daily_structured_output_archive', 'limit_up_detail', True, 'small structured daily output', ('ts_code', 'trade_date')),
    StructuredOutputArchiveTarget('limit_up_down_status_current', 'daily_structured_output_archive', 'limit_up_down_status', True, 'small structured daily output', ('trade_date',)),
    StructuredOutputArchiveTarget('highfreq_event_stream_working', 'daily_structured_output_archive', 'event_stream_summary', True, 'working-state summarized into generic archive store', ('event_time', 'event_type')),
]


class StructuredOutputArchiveService:
    def __init__(self) -> None:
        self.engine = make_engine()

    def supported_targets(self) -> list[StructuredOutputArchiveTarget]:
        return STRUCTURED_OUTPUT_TARGETS

    def archive_supported_current_day_outputs(self, business_date: Optional[date] = None) -> dict:
        summary = {'supported_targets': [], 'unsupported_targets': []}
        with self.engine.begin() as conn:
            for target in STRUCTURED_OUTPUT_TARGETS:
                if not target.supported:
                    summary['unsupported_targets'].append({'source_table': target.source_table, 'reason': target.reason})
                    continue
                rows = conn.execute(text(f'select * from ifa2."{target.source_table}" limit 500')).mappings().all()
                inserted = 0
                for r in rows:
                    key_values = [str(r.get(k, '')) for k in target.key_fields]
                    row_key = '|'.join(key_values)
                    payload = dict(r)
                    result = conn.execute(text(
                        'insert into ifa2.daily_structured_output_archive (id, source_table, business_date, row_key, payload) '
                        'values (cast(:id as uuid), :source_table, :business_date, :row_key, cast(:payload as jsonb)) '
                        'on conflict (source_table, business_date, row_key) do nothing'
                    ), {
                        'id': str(uuid.uuid4()),
                        'source_table': target.source_table,
                        'business_date': business_date or date.today(),
                        'row_key': row_key,
                        'payload': json.dumps(payload, ensure_ascii=False, default=str),
                    })
                    inserted += result.rowcount or 0
                summary['supported_targets'].append({'source_table': target.source_table, 'archive_table': target.archive_table, 'rows_current': len(rows), 'rows_inserted': inserted})
        return summary
