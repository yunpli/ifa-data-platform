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
