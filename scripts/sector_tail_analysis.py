from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from ifa_data_platform.archive_v2.runner import ArchiveV2Runner


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--profile', required=True)
    ap.add_argument('--date', required=True)
    ap.add_argument('--output', required=True)
    args = ap.parse_args()

    runner = ArchiveV2Runner(args.profile)
    universe = runner._load_ths_sector_universe()
    trade_date = args.date.replace('-', '')
    by_type = Counter()
    listed_after = Counter()
    hit_by_type = Counter()
    miss_by_type = Counter()
    sample_miss = defaultdict(list)

    for item in universe:
        idx_type = item.get('type') or 'UNKNOWN'
        by_type[idx_type] += 1
        list_date = str(item.get('list_date') or '')
        if list_date and list_date > trade_date:
            listed_after[idx_type] += 1
            continue
        rows = runner._query_tushare_safe('ths_daily', {'ts_code': item['ts_code'], 'trade_date': trade_date})
        if rows:
            hit_by_type[idx_type] += 1
        else:
            miss_by_type[idx_type] += 1
            if len(sample_miss[idx_type]) < 20:
                sample_miss[idx_type].append({'ts_code': item.get('ts_code'), 'name': item.get('name'), 'list_date': list_date})

    out = {
        'business_date': args.date,
        'universe_total': len(universe),
        'by_type': dict(by_type),
        'listed_after_by_type': dict(listed_after),
        'hit_by_type': dict(hit_by_type),
        'miss_by_type': dict(miss_by_type),
        'coverage_by_type': {
            t: {
                'expected': by_type[t] - listed_after[t],
                'hits': hit_by_type[t],
                'misses': miss_by_type[t],
                'coverage': 0 if (by_type[t] - listed_after[t]) == 0 else round(hit_by_type[t] / (by_type[t] - listed_after[t]), 4),
            }
            for t in by_type
        },
        'sample_miss': dict(sample_miss),
    }
    Path(args.output).write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print(args.output)


if __name__ == '__main__':
    main()
