from __future__ import annotations

import argparse
import json
from pathlib import Path

from sqlalchemy import text

from ifa_data_platform.archive_v2.db import engine
from ifa_data_platform.archive_v2.runner import ALL_FAMILY_META
from ifa_data_platform.archive_v2.production import PRODUCTION_NIGHTLY_FAMILIES

DIRECT_DEST = {
    'equity_daily': 'ifa_archive_equity_daily',
    'index_daily': 'ifa_archive_index_daily',
    'etf_daily': 'ifa_archive_etf_daily',
    'non_equity_daily': 'ifa_archive_non_equity_daily',
    'macro_daily': 'ifa_archive_macro_daily',
}


def dest_table(fam: str) -> str | None:
    meta = ALL_FAMILY_META.get(fam, {})
    return meta.get('dest_table') or DIRECT_DEST.get(fam)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--dates', nargs='+', required=True)
    ap.add_argument('--families', nargs='*')
    ap.add_argument('--include-default', action='store_true')
    ap.add_argument('--output', default='artifacts/archive_v2_reset_20260418.json')
    args = ap.parse_args()

    families = list(args.families or [])
    if args.include_default:
        families += list(PRODUCTION_NIGHTLY_FAMILIES)
    families = sorted(dict.fromkeys(families))
    tables = sorted({t for f in families if (t := dest_table(f))})
    out = {'dates': args.dates, 'families': families, 'tables': tables, 'rows_deleted': {}}
    with engine.begin() as conn:
        for table in tables:
            deleted = conn.execute(text(f"delete from ifa2.{table} where business_date = any(:dates)"), {'dates': args.dates})
            out['rows_deleted'][table] = int(deleted.rowcount or 0)
        for table in ['ifa_archive_completeness', 'ifa_archive_repair_queue']:
            deleted = conn.execute(text(f"delete from ifa2.{table} where business_date = any(:dates) and family_name = any(:families) and coverage_scope='broad_market'"), {'dates': args.dates, 'families': families})
            out['rows_deleted'][table] = int(deleted.rowcount or 0)
        deleted = conn.execute(text("delete from ifa2.ifa_archive_run_items where business_date = any(:dates) and family_name = any(:families)"), {'dates': args.dates, 'families': families})
        out['rows_deleted']['ifa_archive_run_items'] = int(deleted.rowcount or 0)
        deleted = conn.execute(text("delete from ifa2.ifa_archive_runs r where not exists (select 1 from ifa2.ifa_archive_run_items i where i.run_id = r.run_id) and (r.trigger_source like 'manual_validation_%' or r.trigger_source like 'manual_tailfix_%')"))
        out['rows_deleted']['ifa_archive_runs_orphan_manual_only'] = int(deleted.rowcount or 0)
    out_path = Path(args.output)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print(out_path)
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
