from collections import Counter

from ifa_data_platform.runtime.target_manifest import SelectorScope, build_target_manifest


def test_build_target_manifest_for_default_focus_scope():
    manifest = build_target_manifest(SelectorScope(owner_type='default', owner_id='default'))
    assert manifest.item_count > 0
    list_names = {item.source_list_name for item in manifest.items}
    assert 'default_stock_key_focus' in list_names
    assert 'default_stock_focus' in list_names
    assert 'default_tech_key_focus' in list_names
    assert 'default_tech_focus' in list_names


def test_focus_family_stock_targets_resolve_to_lowfreq_and_midfreq():
    manifest = build_target_manifest(SelectorScope(owner_type='default', owner_id='default', list_names=('default_stock_focus', 'default_tech_focus')))
    lanes = {item.resolved_lane for item in manifest.items if item.asset_category == 'stock'}
    assert 'lowfreq' in lanes
    assert 'midfreq' in lanes


def test_build_target_manifest_archive_scope_only():
    manifest = build_target_manifest(SelectorScope(owner_type='default', owner_id='default', list_types=('archive_targets',)))
    assert manifest.item_count > 0
    assert {item.resolved_lane for item in manifest.items} == {'archive'}
    granularities = {item.resolved_granularity for item in manifest.items}
    assert {'minute', '15min', 'daily'} <= granularities


def test_tech_focus_items_are_tagged_with_technology_theme():
    manifest = build_target_manifest(SelectorScope(owner_type='default', owner_id='default', list_names=('default_tech_focus', 'default_tech_key_focus')))
    assert manifest.item_count > 0
    assert all('technology' in item.theme_tags for item in manifest.items)
    assert all(item.source_asset_type == 'tech' for item in manifest.items)
    assert all(item.asset_category == 'tech' for item in manifest.items)


def test_default_scope_dedupes_overlapping_focus_and_key_focus_for_lowfreq_midfreq():
    manifest = build_target_manifest(SelectorScope(owner_type='default', owner_id='default'))
    low_mid_items = [item for item in manifest.items if item.resolved_lane in {'lowfreq', 'midfreq'}]
    counts = Counter(item.dedupe_key for item in low_mid_items)
    assert not [key for key, count in counts.items() if count > 1]

    retained = {
        (item.resolved_lane, item.symbol_or_series_id): item.source_list_type
        for item in low_mid_items
        if item.symbol_or_series_id in {'AU0', 'SC0', '000001.SZ'}
    }
    assert retained[('lowfreq', 'AU0')] == 'key_focus'
    assert retained[('midfreq', 'AU0')] == 'key_focus'
    assert retained[('lowfreq', 'SC0')] == 'key_focus'
    assert retained[('lowfreq', '000001.SZ')] == 'key_focus'
    assert retained[('midfreq', '000001.SZ')] == 'key_focus'
