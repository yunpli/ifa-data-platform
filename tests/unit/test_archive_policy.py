from ifa_data_platform.archive.archive_policy import archive_policy_matrix


def test_archive_policy_matrix_contains_required_business_rules() -> None:
    rows = archive_policy_matrix()
    assert any(r.category == 'stock' and r.frequency == 'daily' and r.supported for r in rows)
    assert any(r.category == 'stock' and r.frequency == '15min' and r.mode == 'forward_only' and r.supported for r in rows)
    assert any(r.category == 'stock' and r.frequency == '1min' and r.mode == 'forward_only' and r.supported for r in rows)
    assert any(r.frequency == '60min' and not r.supported for r in rows)
    assert any(r.category == 'commodity' and r.frequency == '1min' and 'commodity_key_focus' in r.list_types for r in rows)
