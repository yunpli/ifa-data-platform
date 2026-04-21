from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

from ifa_data_platform.tushare.client import get_tushare_client

FUTURE_ASSET_CATEGORIES = {
    "futures",
    "commodity",
    "precious_metal",
    "metal",
    "black_chain",
    "chemical",
    "agri",
    "agricultural",
    "base_metal",
    "energy",
}
EXCHANGE_BY_SUFFIX = {"SHF": "SHFE", "CZC": "CZCE", "DCE": "DCE", "INE": "INE", "CFX": "CFFEX", "GFE": "GFEX"}
EXCHANGE_BY_ALIAS = {
    "AU": "SHFE", "AG": "SHFE", "CU": "SHFE", "AL": "SHFE", "ZN": "SHFE", "PB": "SHFE", "NI": "SHFE", "SN": "SHFE", "RB": "SHFE", "HC": "SHFE",
    "SC": "INE", "LU": "INE", "NR": "INE",
    "I": "DCE", "J": "DCE", "JM": "DCE", "A": "DCE", "B": "DCE", "M": "DCE", "Y": "DCE", "P": "DCE", "C": "DCE", "CS": "DCE", "PP": "DCE", "V": "DCE", "EG": "DCE", "EB": "DCE",
    "TA": "CZCE", "MA": "CZCE", "FG": "CZCE", "SA": "CZCE", "SR": "CZCE", "CF": "CZCE", "RM": "CZCE", "OI": "CZCE", "UR": "CZCE", "PX": "CZCE",
    "IF": "CFFEX", "IH": "CFFEX", "IC": "CFFEX", "IM": "CFFEX", "T": "CFFEX", "TF": "CFFEX", "TS": "CFFEX",
}


@dataclass(frozen=True)
class ResolvedInstrument:
    input_symbol: str
    asset_category: str
    ts_code: str
    symbol_alias: str
    resolver: str


class ContractResolver:
    def __init__(self) -> None:
        self.client = get_tushare_client()

    def resolve(self, symbol: str, asset_category: str) -> ResolvedInstrument:
        asset_category = asset_category or "unknown"
        if asset_category not in FUTURE_ASSET_CATEGORIES:
            return ResolvedInstrument(symbol, asset_category, self._normalize_equity_like(symbol), symbol, "passthrough")
        if "." in symbol and any(ch.isdigit() for ch in symbol):
            return ResolvedInstrument(symbol, asset_category, symbol, self._series_alias(symbol), "passthrough_ts_code")
        ts_code = self._resolve_live_contract(symbol)
        return ResolvedInstrument(symbol, asset_category, ts_code, self._series_alias(ts_code), "fut_basic_live_contract")

    def _normalize_equity_like(self, symbol: str) -> str:
        if "." in symbol:
            return symbol
        if re.fullmatch(r"\d{6}", symbol):
            return f"{symbol}.SZ" if symbol.startswith(("0", "3")) else f"{symbol}.SH"
        return symbol

    def _series_alias(self, symbol: str) -> str:
        return re.sub(r"\d+", "", symbol.split(".")[0]).upper()

    @lru_cache(maxsize=256)
    def _resolve_live_contract(self, alias_or_symbol: str) -> str:
        alias = self._series_alias(alias_or_symbol)
        exchange = self._infer_exchange(alias_or_symbol, alias)
        params = {"exchange": exchange, "fut_type": "1"}
        rows = self.client.query("fut_basic", params, timeout_sec=60, max_retries=2)
        candidates = [r for r in rows if str(r.get("fut_code") or "").upper() == alias and str(r.get("delist_date") or "99999999") >= "20000101"]
        if not candidates:
            raise ValueError(f"live contract not found for alias={alias_or_symbol} exchange={exchange}")
        candidates.sort(key=lambda r: (str(r.get("delist_date") or ""), str(r.get("list_date") or "")))
        return str(candidates[0]["ts_code"])

    def _infer_exchange(self, raw: str, alias: str) -> str:
        if "." in raw:
            suffix = raw.split(".")[-1].upper()
            if suffix in EXCHANGE_BY_SUFFIX:
                return EXCHANGE_BY_SUFFIX[suffix]
        return EXCHANGE_BY_ALIAS.get(alias, "SHFE")
