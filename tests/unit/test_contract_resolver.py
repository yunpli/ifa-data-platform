from ifa_data_platform.runtime import contract_resolver as resolver_module
from ifa_data_platform.runtime.contract_resolver import ContractResolver


class _FakeClient:
    def __init__(self, rows):
        self.rows = rows

    def query(self, name, params, timeout_sec=60, max_retries=2):
        assert name == 'fut_basic'
        return list(self.rows)


def test_resolver_prefers_nearest_active_contract_for_canonical_alias(monkeypatch):
    rows = [
        {'fut_code': 'AU', 'ts_code': 'AU0806.SHF', 'list_date': '20080109', 'delist_date': '20080616'},
        {'fut_code': 'AU', 'ts_code': 'AU2604.SHF', 'list_date': '20250401', 'delist_date': '20260415'},
        {'fut_code': 'AU', 'ts_code': 'AU2605.SHF', 'list_date': '20260225', 'delist_date': '20260515'},
        {'fut_code': 'AU', 'ts_code': 'AU2606.SHF', 'list_date': '20250516', 'delist_date': '20260615'},
        {'fut_code': 'AU', 'ts_code': 'AU2704.SHF', 'list_date': '20260317', 'delist_date': '20270415'},
    ]

    class _FrozenDatetime:
        @staticmethod
        def now(tz=None):
            from datetime import datetime
            return datetime(2026, 4, 21, 0, 0, 0, tzinfo=tz)

    monkeypatch.setattr(resolver_module, 'get_tushare_client', lambda: _FakeClient(rows))
    monkeypatch.setattr(resolver_module, 'datetime', _FrozenDatetime)

    resolver = ContractResolver()
    resolved = resolver.resolve('AU0', 'precious_metal')

    assert resolved.ts_code == 'AU2605.SHF'
    assert resolved.symbol_alias == 'AU'
    assert resolved.resolver == 'fut_basic_live_contract'


def test_resolver_passthroughs_explicit_ts_code(monkeypatch):
    monkeypatch.setattr(resolver_module, 'get_tushare_client', lambda: _FakeClient([]))
    resolver = ContractResolver()
    resolved = resolver.resolve('SC2605.INE', 'commodity')
    assert resolved.ts_code == 'SC2605.INE'
    assert resolved.symbol_alias == 'SC'
    assert resolved.resolver == 'passthrough_ts_code'
