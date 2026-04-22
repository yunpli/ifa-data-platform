from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import create_engine, text

ENGINE = create_engine('postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp')

LANE_LABELS = {
    'lowfreq': '低频',
    'midfreq': '中频',
    'highfreq': '高频',
    'archive_v2': 'Archive V2',
    'archive': 'Legacy Archive',
}


def fmt_bjt(v):
    if v is None:
        return '-'
    if isinstance(v, str):
        return v
    if getattr(v, 'tzinfo', None) is None:
        v = v.replace(tzinfo=timezone.utc)
    bjt = timezone(timedelta(hours=8))
    return v.astimezone(bjt).strftime('%Y-%m-%d %H:%M:%S BJT')


def fmt_ms(ms):
    if ms in (None, 0):
        return '0s'
    sec = float(ms) / 1000.0
    if sec < 60:
        return f'{sec:.1f}s'
    mins = int(sec // 60)
    rem = sec - mins * 60
    return f'{mins}m {rem:.1f}s'


def lane_summary_line(lane, lane_runs):
    cnt = len(lane_runs)
    ok = sum(1 for r in lane_runs if r['status'] == 'succeeded')
    partial = sum(1 for r in lane_runs if r['status'] == 'partial')
    total_records = sum(int(r['records_processed'] or 0) for r in lane_runs)
    total_dur = sum(int(r['duration_ms'] or 0) for r in lane_runs)
    return f"- {LANE_LABELS.get(lane, lane)}：{cnt} 次，成功 {ok}，partial {partial}，累计处理 {total_records} 条，累计耗时 {fmt_ms(total_dur)}"


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
    lines.append('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
    lines.append('Runtime Daemon 12 小时运行摘要')
    lines.append('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
    lines.append(f'生成时间：{fmt_bjt(now)}')
    lines.append(f'统计窗口：{fmt_bjt(since)}  →  {fmt_bjt(now)}')
    lines.append('')

    lines.append('【一眼结论】')
    if not runs:
        lines.append('过去 12 小时没有看到 unified_runtime_runs 新增记录。')
    else:
        ok = status_counts.get('succeeded', 0)
        partial = status_counts.get('partial', 0)
        running = status_counts.get('running', 0)
        other = len(runs) - ok - partial - running
        lines.append(f'过去 12 小时共记录 {len(runs)} 次 runtime 执行：成功 {ok}，partial {partial}，仍在运行 {running}，其他状态 {other}。')
    lines.append('')

    lines.append('【各 lane 做了什么】')
    for lane in ['lowfreq', 'midfreq', 'highfreq', 'archive_v2', 'archive']:
        lane_runs = by_lane.get(lane, [])
        if not lane_runs:
            lines.append(f'- {LANE_LABELS.get(lane, lane)}：过去 12 小时无记录')
            continue
        lines.append(lane_summary_line(lane, lane_runs))
        for r in lane_runs[:3]:
            lines.append(
                f"  • {fmt_bjt(r['started_at'])} | 状态={r['status']} | 触发={r['trigger_mode'] or '-'} | 计划={r['schedule_key'] or '-'} | 处理={r['records_processed'] or 0} | 耗时={fmt_ms(r['duration_ms'])}"
            )
    lines.append('')

    lines.append('【Archive V2 夜间/补档】')
    if not archive_runs:
        lines.append('过去 12 小时没有新的 ifa_archive_runs 记录。')
    else:
        for r in archive_runs[:10]:
            lines.append(f"- {fmt_bjt(r['start_time'])} | profile={r['profile_name']} | trigger={r['trigger_source']} | status={r['status']}")
    lines.append('')

    lines.append('【当前 worker 健康快照】')
    for s in states:
        lines.append(
            f"- {LANE_LABELS.get(s['worker_type'], s['worker_type'])}: last_status={s['last_status'] or '-'} | active_run_id={s['active_run_id'] or '-'} | last_completed={fmt_bjt(s['last_completed_at'])} | next_due={fmt_bjt(s['next_due_at_utc'])} | heartbeat={fmt_bjt(s['last_heartbeat_at'])}"
        )
    lines.append('')

    lines.append('【值得注意】')
    stale_running = [r for r in runs if r['status'] == 'running']
    if stale_running:
        lines.append(f'- 发现 {len(stale_running)} 条仍在 running 的 runtime 记录，需要关注是否卡住。')
    else:
        lines.append('- 当前窗口内没有新的 running 残留记录。')
    partial_runs = [r for r in runs if r['status'] == 'partial']
    if partial_runs:
        lines.append(f'- 发现 {len(partial_runs)} 条 partial 记录，建议结合对应 lane / family 判断是否只是数据不完整，而不一定是调度故障。')
    else:
        lines.append('- 当前窗口内没有 partial 记录。')
    lines.append('')

    lines.append('【这份摘要怎么用】')
    lines.append('- 它回答的是：daemon 最近有没有正常做事、各 lane 大概做了什么、当前是否看起来健康。')
    lines.append('- 如果要看某张业务表、某个 family、某次 repair/backfill 的更细证据，仍应看专项运行报告和 DB 记录。')

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text('\n'.join(lines) + '\n')
    print(str(out))


if __name__ == '__main__':
    main()
