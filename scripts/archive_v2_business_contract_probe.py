from __future__ import annotations

import argparse
import json
from pathlib import Path

from ifa_data_platform.archive_v2.business_contracts import BUSINESS_DAILY_CONTRACTS
from ifa_data_platform.archive_v2.runner import ArchiveV2Runner


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--profile', required=True)
    ap.add_argument('--date', required=True)
    ap.add_argument('--families', nargs='*')
    ap.add_argument('--output', required=True)
    args = ap.parse_args()

    runner = ArchiveV2Runner(args.profile)
    out: dict[str, object] = {
        'business_date': args.date,
        'families': {},
    }
    families = args.families or list(BUSINESS_DAILY_CONTRACTS.keys())
    for family in families:
        contract = BUSINESS_DAILY_CONTRACTS[family]
        result = runner._fetch_business_contract_rows(family, args.date)
        payload = {
            'source_endpoints': list(contract.source_endpoints),
            'source_mode': contract.source_mode,
            'shard_strategy': contract.shard_strategy,
            'dedupe_identity': contract.dedupe_identity,
            'zero_row_policy': contract.zero_row_policy,
            'completeness_rule': contract.completeness_rule,
            'archive_table_name': contract.archive_table_name,
            'status': result['status'],
            'note': result['note'],
            'row_count': len(result.get('rows', [])),
        }
        if 'aggregate_row' in result:
            payload['aggregate_row'] = result['aggregate_row']
        out['families'][family] = payload

    output = Path(args.output)
    output.write_text(json.dumps(out, ensure_ascii=False, indent=2, default=str))
    print(output)


if __name__ == '__main__':
    main()
