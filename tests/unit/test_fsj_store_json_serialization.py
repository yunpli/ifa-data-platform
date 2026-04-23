from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from ifa_data_platform.fsj.store import FSJStore


def test_json_dumps_normalizes_non_native_json_types() -> None:
    store = FSJStore()

    dumped = store._json_dumps(
        {
            "whole": Decimal("12"),
            "fraction": Decimal("12.34"),
            "date": date(2026, 4, 23),
            "dt": datetime(2026, 4, 23, 11, 42, 0),
            "path": Path("/tmp/example"),
        }
    )

    payload = json.loads(dumped)
    assert payload == {
        "whole": 12,
        "fraction": 12.34,
        "date": "2026-04-23",
        "dt": "2026-04-23T11:42:00",
        "path": "/tmp/example",
    }
