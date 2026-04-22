from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import create_engine, text

ENGINE = create_engine('postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp')


def fmt_ts(v):
    if v is None:
        return '-'
    if isinstance(v, str):
        return v
    if getattr(v, 'tzinfo', None) is None:
        v = v.replace(tzinfo=timezone.utc)
    return v.astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')


def fmt_bjt(v):
    if v is None:
        return '-'
    if isinstance(v, str):
        return v
    if getattr(v, 'tzinfo', None) is None:
        v = v.replace(tzinfo=timezone.utc)
    bjt = timezone(timedelta(hours=8))
    return v.astimezone(bjt).strftime('%Y-%m-%d %H:%M:%S BJT')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--hours', type=int, default=12)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()

    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=args.hours)

    with ENGINE.begin() as conn:
        runs = conn.execute(text("""
            select id, lane, worker_type, trigger_mode, schedule_key, status,
                   governance_state, records_processed, error_count, duration_ms,
                   started_at, completed_at, summary
            from ifa2.unified_runtime_runs
            where started_at >= :since
            order by started_at desc
        """), {'since': since}).mappings().all()
        states = conn.execute(text("""
            select worker_type, active_run_id, last_status, last_started_at,
                   last_completed_at, next_due_at_utc, last_heartbeat_at
            from ifa2.runtime_worker_state
            order by worker_type
        """)).mappings().all()
        archive_runs = conn.execute(text("""
            select run_id, profile_name, trigger_source, status, start_time, end_time
            from ifa2.ifa_archive_runs
            where start_time >= :since
            order by start_time desc
            limit 50
        """), {'since': since}).mappings().all()

    by_lane = defaultdict(list)
    for r in runs:
        by_lane[r['lane']].append(r)

    status_counts = Counter(r['status'] for r in runs)
    lines: list[str] = []
    lines.append('Runtime Daemon 12-Hour Digest')
    lines.append(f'Generated: {fmt_bjt(now)}')
    lines.append(f'Window: {fmt_bjt(since)} -> {fmt_bjt(now)}')
    lines.append('')

    lines.append('1) 一句话结论')
    if not runs:
        lines.append('- 过去 12 小时没有看到 unified_runtime_runs 新增记录。')
    else:
        ok = status_counts.get('succeeded', 0)
        partial = status_counts.get('partial', 0)
        running = status_counts.get('running', 0)
        other = len(runs) - ok - partial - running
        lines.append(f'- 过去 12 小时共记录 {len(runs)} 次 runtime 执行：成功 {ok}，partial {partial}，仍在运行 {running}，其他状态 {other}。')
    lines.append('')

    lines.append('2) 各 lane 做了什么')
    for lane in ['lowfreq', 'midfreq', 'highfreq', 'archive_v2', 'archive']:
        lane_runs = by_lane.get(lane, [])
        if not lane_runs:
            lines.append(f'- {lane}: 过去 12 小时无记录')
            continue
        cnt = len(lane_runs)
        ok = sum(1 for r in lane_runs if r['status'] == 'succeeded')
        partial = sum(1 for r in lane_runs if r['status'] == 'partial')
        total_records = sum(int(r['records_processed'] or 0) for r in lane_runs)
        lines.append(f'- {lane}: {cnt} 次，成功 {ok}，partial {partial}，累计 records_processed={total_records}')
        for r in lane_runs[:3]:
            lines.append(f"  • {fmt_bjt(r['started_at'])} | status={r['status']} | trigger={r['trigger_mode'] or '-'} | schedule={r['schedule_key'] or '-'} | records={r['records_processed'] or 0} | duration_ms={r['duration_ms'] or 0}")
    lines.append('')

    lines.append('3) Archive V2 夜间/补档情况')
    if not archive_runs:
        lines.append('- 过去 12 小时没有新的 ifa_archive_runs 记录。')
    else:
        for r in archive_runs[:10]:
            lines.append(f"- {fmt_bjt(r['start_time'])} | profile={r['profile_name']} | trigger={r['trigger_source']} | status={r['status']}")
    lines.append('')

    lines.append('4) 当前 daemon / worker 健康快照')
    for s in states:
        lines.append(
            f"- {s['worker_type']}: last_status={s['last_status'] or '-'} | active_run_id={s['active_run_id'] or '-'} | last_completed={fmt_bjt(s['last_completed_at'])} | next_due={fmt_bjt(s['next_due_at_utc'])} | heartbeat={fmt_bjt(s['last_heartbeat_at'])}"
        )
    lines.append('')

    lines.append('5) 需要注意的点')
    stale_running = [r for r in runs if r['status'] == 'running']
    if stale_running:
        lines.append(f'- 发现 {len(stale_running)} 条仍在 running 的 runtime 记录，需要关注是否卡住。')
    else:
        lines.append('- 当前窗口内没有新的 running 残留记录。')
    partial_runs = [r for r in runs if r['status'] == 'partial']
    if partial_runs:
        lines.append(f'- 发现 {len(partial_runs)} 条 partial 记录，建议结合对应 lane/family 看是否是数据不完整，而不一定是调度故障。')
    else:
        lines.append('- 当前窗口内没有 partial 记录。')
    lines.append('')

    lines.append('6) 这封消息怎么看')
    lines.append('- 这份 digest 主要回答：daemon 过去 12 小时有没有正常做事、各 lane 大概做了什么、当前 worker 状态看起来是否健康。')
    lines.append('- 更细的业务表变化/具体 family 细节，仍应看运行报告、DB 证据或专项审计。')

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text('\n'.join(lines) + '\n')
    print(str(out))


if __name__ == '__main__':
    main()
