from ifa_data_platform.runtime.target_manifest import SelectorScope, build_target_manifest


def test_build_target_manifest_for_default_focus_scope():
    manifest = build_target_manifest(SelectorScope(owner_type='default', owner_id='default'))
    assert manifest.item_count > 0
    list_names = {item.source_list_name for item in manifest.items}
    assert 'default_key_focus' in list_names
    assert 'default_focus' in list_names
    assert 'tech_key_focus' in list_names
    assert 'tech_focus' in list_names


def test_build_target_manifest_archive_scope_only():
    manifest = build_target_manifest(SelectorScope(owner_type='default', owner_id='default', list_types=('archive_targets',)))
    assert manifest.item_count > 0
    assert {item.resolved_lane for item in manifest.items} == {'archive'}
    granularities = {item.resolved_granularity for item in manifest.items}
    assert {'minute', '15min', 'daily'} <= granularities


def test_tech_focus_items_are_tagged_with_technology_theme():
    manifest = build_target_manifest(SelectorScope(owner_type='default', owner_id='default', list_names=('tech_focus', 'tech_key_focus')))
    assert manifest.item_count > 0
    assert all('technology' in item.theme_tags for item in manifest.items)
    assert all(item.source_asset_type == 'stock' for item in manifest.items)
