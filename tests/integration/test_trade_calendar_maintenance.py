from __future__ import annotations

from datetime import date
from types import SimpleNamespace

from sqlalchemy import text

from ifa_data_platform.db.engine import make_engine
from ifa_data_platform.lowfreq.trade_calendar_maintenance import TradeCalendarMaintenanceService


class _FakeTushareClient:
    def __init__(self, records):
        self.records = records
        self.calls = []

    def query(self, endpoint, params):
        self.calls.append((endpoint, params))
        assert endpoint == 'trade_cal'
        return list(self.records)


def _delete_trade_cal_range(start_date: str, end_date: str) -> None:
    engine = make_engine()
    with engine.begin() as conn:
        conn.execute(
            text(
                "delete from ifa2.trade_cal_current where exchange='SSE' and cal_date between :start_date and :end_date"
            ),
            {'start_date': start_date, 'end_date': end_date},
        )


def test_trade_calendar_manual_sync_persists_current_and_history(monkeypatch) -> None:
    records = [
        {'exchange': 'SSE', 'cal_date': '20260428', 'is_open': '1', 'pretrade_date': '20260427'},
        {'exchange': 'SSE', 'cal_date': '20260429', 'is_open': '0', 'pretrade_date': '20260428'},
        {'exchange': 'SSE', 'cal_date': '20260430', 'is_open': '1', 'pretrade_date': '20260428'},
    ]
    fake_client = _FakeTushareClient(records)
    monkeypatch.setattr(
        'ifa_data_platform.lowfreq.trade_calendar_maintenance.get_tushare_client',
        lambda: fake_client,
    )
    _delete_trade_cal_range('2026-04-28', '2026-04-30')

    svc = TradeCalendarMaintenanceService()
    result = svc.sync_range(date(2026, 4, 28), date(2026, 4, 30))

    assert result.records_fetched == 3
    assert fake_client.calls[0][1]['start_date'] == '20260428'
    assert fake_client.calls[0][1]['end_date'] == '20260430'

    engine = make_engine()
    with engine.begin() as conn:
        current_rows = conn.execute(
            text(
                "select cal_date, is_open, pretrade_date, version_id from ifa2.trade_cal_current where exchange='SSE' and cal_date between '2026-04-28' and '2026-04-30' order by cal_date"
            )
        ).mappings().all()
        history_rows = conn.execute(
            text(
                "select cal_date, is_open from ifa2.trade_cal_history where version_id=:version_id order by cal_date"
            ),
            {'version_id': result.version_id},
        ).mappings().all()
    assert [row['cal_date'].isoformat() for row in current_rows] == ['2026-04-28', '2026-04-29', '2026-04-30']
    assert [bool(row['is_open']) for row in current_rows] == [True, False, True]
    assert all(str(row['version_id']) == result.version_id for row in current_rows)
    assert len(history_rows) == 3


def test_trade_calendar_health_check_reports_missing_dates(monkeypatch) -> None:
    fake_client = _FakeTushareClient([])
    monkeypatch.setattr(
        'ifa_data_platform.lowfreq.trade_calendar_maintenance.get_tushare_client',
        lambda: fake_client,
    )
    _delete_trade_cal_range('2026-04-16', '2026-04-20')

    svc = TradeCalendarMaintenanceService()
    report = svc.health_check(
        anchor_date=date(2026, 4, 18),
        past_days_required=2,
        future_days_required=2,
        max_active_version_age_days=9999,
    )

    assert report.status == 'error'
    codes = {item['code'] for item in report.findings}
    assert 'missing_dates_in_required_window' in codes or 'coverage_end_too_early' in codes or 'coverage_start_too_recent' in codes


def test_trade_calendar_monthly_sync_uses_bounded_window(monkeypatch) -> None:
    fake_client = _FakeTushareClient([
        {'exchange': 'SSE', 'cal_date': '20260401', 'is_open': '1', 'pretrade_date': '20260331'},
    ])
    monkeypatch.setattr(
        'ifa_data_platform.lowfreq.trade_calendar_maintenance.get_tushare_client',
        lambda: fake_client,
    )

    svc = TradeCalendarMaintenanceService()
    svc.monthly_sync(anchor_date=date(2026, 4, 15), lookback_days=14, forward_days=10)

    params = fake_client.calls[0][1]
    assert params['start_date'] == '20260401'
    assert params['end_date'] == '20260425'
