#!/usr/bin/env python3
"""Minimal CLI for Trailblazer selector/manifest and unified runtime dry-runs."""

from __future__ import annotations

import argparse
import json

from ifa_data_platform.runtime.target_manifest import SelectorScope, build_target_manifest
from ifa_data_platform.runtime.unified_runtime import UnifiedRuntime
from ifa_data_platform.archive.archive_target_delta import build_archive_manifest, diff_archive_manifests


def _scope_from_args(args: argparse.Namespace) -> SelectorScope:
    return SelectorScope(
        owner_type=args.owner_type,
        owner_id=args.owner_id,
        list_names=tuple(args.list_name or []),
        list_types=tuple(args.list_type or []),
        include_inactive=args.include_inactive,
    )


def cmd_manifest(args: argparse.Namespace) -> None:
    manifest = build_target_manifest(_scope_from_args(args))
    print(json.dumps(manifest.to_dict(), ensure_ascii=False, indent=2))


def cmd_run_once(args: argparse.Namespace) -> None:
    rt = UnifiedRuntime()
    result = rt.run_once(
        lane=args.lane,
        trigger_mode=args.trigger_mode,
        scope=_scope_from_args(args),
        archive_window=args.archive_window,
        dry_run_manifest_only=args.manifest_only,
    )
    print(json.dumps(result.summary, ensure_ascii=False, indent=2))


def cmd_archive_delta_demo(args: argparse.Namespace) -> None:
    current = build_archive_manifest(_scope_from_args(args))
    reduced_items = current.items[:-1] if len(current.items) > 1 else current.items
    from ifa_data_platform.runtime.target_manifest import TargetManifest
    previous = TargetManifest(
        manifest_id=current.manifest_id + '_prev',
        manifest_hash=current.manifest_hash + '_prev',
        generated_at=current.generated_at,
        selector_scope=current.selector_scope,
        items=reduced_items,
    )
    deltas = diff_archive_manifests(previous, current)
    print(json.dumps([d.__dict__ for d in deltas], ensure_ascii=False, indent=2))


def cmd_run_status(args: argparse.Namespace) -> None:
    rt = UnifiedRuntime()
    if args.run_id:
        payload = rt.store.get_unified_run(args.run_id)
        print(json.dumps(payload or {}, ensure_ascii=False, indent=2, default=str))
        return
    payload = rt.store.list_unified_runs(limit=args.limit, lane=args.lane)
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))


def cmd_archive_status(args: argparse.Namespace) -> None:
    rt = UnifiedRuntime()
    payload = rt.store.archive_catchup_status(limit=args.limit)
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='cmd', required=True)

    p1 = sub.add_parser('manifest')
    p1.add_argument('--owner-type', default='default')
    p1.add_argument('--owner-id', default='default')
    p1.add_argument('--list-name', action='append')
    p1.add_argument('--list-type', action='append')
    p1.add_argument('--include-inactive', action='store_true')
    p1.set_defaults(func=cmd_manifest)

    p2 = sub.add_parser('run-once')
    p2.add_argument('--lane', choices=['lowfreq', 'midfreq', 'archive'], required=True)
    p2.add_argument('--trigger-mode', default='manual_once')
    p2.add_argument('--owner-type', default='default')
    p2.add_argument('--owner-id', default='default')
    p2.add_argument('--list-name', action='append')
    p2.add_argument('--list-type', action='append')
    p2.add_argument('--include-inactive', action='store_true')
    p2.add_argument('--archive-window', default='manual_archive')
    p2.add_argument('--manifest-only', action='store_true')
    p2.set_defaults(func=cmd_run_once)

    p3 = sub.add_parser('archive-delta-demo')
    p3.add_argument('--owner-type', default='default')
    p3.add_argument('--owner-id', default='default')
    p3.add_argument('--list-name', action='append')
    p3.add_argument('--list-type', action='append')
    p3.add_argument('--include-inactive', action='store_true')
    p3.set_defaults(func=cmd_archive_delta_demo)

    p4 = sub.add_parser('run-status')
    p4.add_argument('--run-id')
    p4.add_argument('--lane', choices=['lowfreq', 'midfreq', 'archive'])
    p4.add_argument('--limit', type=int, default=10)
    p4.set_defaults(func=cmd_run_status)

    p5 = sub.add_parser('archive-status')
    p5.add_argument('--limit', type=int, default=20)
    p5.set_defaults(func=cmd_archive_status)

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
