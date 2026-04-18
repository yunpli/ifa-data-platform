from __future__ import annotations

import argparse
import json
from ifa_data_platform.archive_v2.runner import ArchiveV2Runner


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--profile', required=True)
    args = ap.parse_args()
    result = ArchiveV2Runner(args.profile).run()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
