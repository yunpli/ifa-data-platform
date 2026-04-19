from __future__ import annotations

import json
from pathlib import Path

ART = Path('/Users/neoclaw/repos/ifa-data-platform/artifacts')
OUT = ART / 'archive_v2_tailfix_summary_20260418.json'


def summarize(name: str) -> dict:
    obj = json.loads((ART / name).read_text())
    return {
        'run_id': obj['result'].get('run_id'),
        'status': obj['result'].get('status'),
        'duration_sec': obj['duration_sec'],
        'requested_rows_written_by_table': obj['requested_rows_written_by_table'],
        'noncompleted': [
            {'family': x['family_name'], 'status': x['status'], 'rows_written': x['rows_written'], 'date': x['business_date']}
            for x in obj['run_items'] if x['status'] != 'completed'
        ],
    }


def main() -> None:
    probe = json.loads((ART / 'archive_v2_tailfix_probe_20260418.json').read_text())
    out = {
        'probe': probe,
        'jan': summarize('tailfix_jan_single_daily_plus_60m_20260418.json'),
        'feb': summarize('tailfix_feb_single_default_20260418.json'),
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2, default=str))
    print(OUT)


if __name__ == '__main__':
    main()
