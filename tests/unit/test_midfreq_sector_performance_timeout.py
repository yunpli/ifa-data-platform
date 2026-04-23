from types import SimpleNamespace

import pytest

from ifa_data_platform.midfreq.adaptors.tushare import MidfreqTushareAdaptor
from ifa_data_platform.midfreq.runner import MidfreqRunner


class _FakeSectorClient:
    def __init__(self):
        self.daily_calls = 0

    def query(self, api_name, params, timeout_sec=30, max_retries=2):
        if api_name == 'ths_index':
            return [
                {'ts_code': '885001.TI', 'name': '机器人'},
                {'ts_code': '885002.TI', 'name': '算力'},
            ]
        if api_name == 'ths_daily':
            self.daily_calls += 1
            return [{
                'trade_date': '20260422',
                'close': 123.4,
                'pct_change': 1.2,
                'turnover_rate': 3.4,
            }]
        raise AssertionError(api_name)


def test_sector_performance_enforces_wall_clock_budget(monkeypatch):
    adaptor = MidfreqTushareAdaptor()
    adaptor._client = _FakeSectorClient()
    adaptor.SECTOR_PERFORMANCE_FETCH_BUDGET_SEC = 1

    ticks = iter([0.0, 0.4, 1.1])
    monkeypatch.setattr('ifa_data_platform.midfreq.adaptors.tushare.time.monotonic', lambda: next(ticks))

    with pytest.raises(TimeoutError, match='sector_performance fetch exceeded 1s budget'):
        adaptor._fetch_sector_performance('20260422')

    assert adaptor._client.daily_calls == 1


def test_midfreq_runner_returns_failed_when_sector_performance_times_out(monkeypatch):
    runner = MidfreqRunner(source_name='dummy')
    runner.adaptor = SimpleNamespace(
        fetch=lambda **kwargs: (_ for _ in ()).throw(TimeoutError('sector_performance fetch exceeded 300s budget'))
    )
    runner.version_registry = SimpleNamespace(
        create_version=lambda **kwargs: 'v-timeout',
        promote=lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(runner, '_persist_current_to_history', lambda *args, **kwargs: 0)

    result = runner.run('sector_performance')

    assert result.status == 'failed'
    assert result.records_processed == 0
    assert result.version_id == 'v-timeout'
    assert '300s budget' in (result.error_message or '')
