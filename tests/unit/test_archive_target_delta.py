from ifa_data_platform.archive.archive_target_delta import build_archive_manifest, diff_archive_manifests
from ifa_data_platform.runtime.target_manifest import SelectorScope, TargetManifest


def test_archive_delta_detects_added_target_from_reduced_previous_manifest():
    current = build_archive_manifest(SelectorScope(owner_type='default', owner_id='default', list_types=('archive_targets',)))
    assert current.item_count > 1
    previous = TargetManifest(
        manifest_id='prev',
        manifest_hash='prev',
        generated_at=current.generated_at,
        selector_scope=current.selector_scope,
        items=current.items[:-1],
    )
    deltas = diff_archive_manifests(previous, current)
    assert any(d.change_type == 'added' for d in deltas)


def test_archive_added_target_backfill_defaults_follow_granularity_policy():
    current = build_archive_manifest(SelectorScope(owner_type='default', owner_id='default', list_types=('archive_targets',)))
    previous = TargetManifest(
        manifest_id='prev',
        manifest_hash='prev',
        generated_at=current.generated_at,
        selector_scope=current.selector_scope,
        items=[],
    )
    deltas = diff_archive_manifests(previous, current)
    added = [d for d in deltas if d.change_type == 'added']
    assert added
    priorities = {d.granularity: d.backlog_priority for d in added}
    assert priorities['daily'] == 'medium_high'
    assert priorities['15min'] == 'medium'
    assert priorities['minute'] == 'guarded_medium_low'
