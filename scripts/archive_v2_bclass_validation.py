from __future__ import annotations

import json
from pathlib import Path

from ifa_data_platform.archive_v2.runner import ArchiveV2Runner, SOURCE_FIRST_DAILY_FAMILIES, DAILY_SIGNAL_FAMILIES, INTRADAY_TRADABLE_FAMILIES, SUPPORTED_FAMILIES
from ifa_data_platform.archive_v2.production import PRODUCTION_NIGHTLY_FAMILIES, PRODUCTION_MANUAL_BACKFILL_FAMILIES, build_nightly_profile


FAMILIES = [
    'index_daily',
    'macro_daily',
    'announcements_daily',
    'news_daily',
    'research_reports_daily',
    'investor_qa_daily',
    'dragon_tiger_daily',
    'limit_up_detail_daily',
    'limit_up_down_status_daily',
    'sector_performance_daily',
]


def main() -> None:
    runner = ArchiveV2Runner('profiles/archive_v2_milestone10_daily_index_only.json')
    out = {
        'source_first_daily_families': sorted(SOURCE_FIRST_DAILY_FAMILIES),
        'daily_signal_families': DAILY_SIGNAL_FAMILIES,
        'production_nightly_families': PRODUCTION_NIGHTLY_FAMILIES,
        'production_manual_backfill_families': PRODUCTION_MANUAL_BACKFILL_FAMILIES,
        'proxy_in_supported': [x for x in ['proxy_1m', 'proxy_15m', 'proxy_60m'] if x in SUPPORTED_FAMILIES],
        'intraday_tradable_families': INTRADAY_TRADABLE_FAMILIES,
        'nightly_profile': {
            'include_signal_families': build_nightly_profile('2026-04-15').include_signal_families,
            'family_groups': build_nightly_profile('2026-04-15').family_groups,
        },
        'family_fetch_results': {},
    }
    for fam in FAMILIES:
        try:
            rows = runner._fetch_source_first_daily_rows(fam, '2026-04-15')
            out['family_fetch_results'][fam] = {
                'ok': True,
                'row_count': len(rows),
                'sample_keys': sorted(list(rows[0].keys()))[:12] if rows else [],
            }
        except Exception as e:
            out['family_fetch_results'][fam] = {
                'ok': False,
                'error_type': type(e).__name__,
                'error': str(e),
            }
    output = Path('artifacts/archive_v2_bclass_validation_20260418.json')
    output.write_text(json.dumps(out, ensure_ascii=False, indent=2, default=str))
    print(output)


if __name__ == '__main__':
    main()
