from __future__ import annotations

from types import SimpleNamespace

from ifa_data_platform.runtime.unified_runtime import UnifiedRuntime


class _FakeRegistry:
    def list_enabled(self):
        return [
            SimpleNamespace(dataset_name='trade_cal'),
            SimpleNamespace(dataset_name='stock_basic'),
            SimpleNamespace(dataset_name='index_basic'),
        ]


def test_lowfreq_regular_planning_excludes_trade_cal() -> None:
    rt = UnifiedRuntime()
    rt.lowfreq_registry = _FakeRegistry()
    planned = rt._plan_lane_datasets('lowfreq', [], trigger_mode='manual_once')
    assert 'trade_cal' not in planned
    assert planned == ['stock_basic', 'index_basic']


def test_lowfreq_trade_calendar_maintenance_plans_only_trade_cal() -> None:
    rt = UnifiedRuntime()
    rt.lowfreq_registry = _FakeRegistry()
    planned = rt._plan_lane_datasets('lowfreq', [], trigger_mode='trade_calendar_monthly_maintenance')
    assert planned == ['trade_cal']


def test_lowfreq_gate_adds_trade_cal_result_when_due() -> None:
    rt = UnifiedRuntime()
    rt.lowfreq_trade_calendar_maintenance = SimpleNamespace(
        auto_sync_if_due=lambda exchange='SSE': {
            'performed': True,
            'decision': {'should_sync': True, 'reason': 'stale_sync_state'},
            'result': {'records_fetched': 12, 'watermark': '20260421'},
        }
    )

    gate = rt._maybe_run_lowfreq_trade_calendar_gate(lane='lowfreq', trigger_mode='manual_once')

    assert gate['summary']['performed'] is True
    assert gate['dataset_results'][0].dataset_name == 'trade_cal'
    assert gate['dataset_results'][0].records_processed == 12


def test_lowfreq_gate_skips_for_monthly_maintenance_trigger() -> None:
    rt = UnifiedRuntime()
    gate = rt._maybe_run_lowfreq_trade_calendar_gate(lane='lowfreq', trigger_mode='trade_calendar_monthly_maintenance')
    assert gate['summary']['performed'] is False
    assert gate['dataset_results'] == []
