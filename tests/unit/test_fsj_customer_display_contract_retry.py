from datetime import datetime, timezone

from tests.unit.test_fsj_report_rendering import _assembled_sections
from ifa_data_platform.fsj.report_rendering import MainReportHTMLRenderer


def test_customer_default_seed_profile_uses_summary_view_and_hides_archive_target_tokens() -> None:
    rendered = MainReportHTMLRenderer().render(
        _assembled_sections(),
        report_run_id="report-run-customer-summary-1",
        artifact_uri="file:///tmp/customer-summary.html",
        generated_at=datetime(2099, 4, 22, 8, 4, tzinfo=timezone.utc),
        output_profile="customer",
    )

    customer_presentation = rendered["metadata"]["customer_presentation"]
    focus_module = customer_presentation["focus_module"]
    assert focus_module["customer_summary_view"] is True
    assert focus_module["contract"]["display_honesty_mode"] == "default_observation_pool_sample"
    assert "并不等同于正式客户关注池" in rendered["content"]
    assert "纳入原因：" not in rendered["content"]
    assert "盘中观察要点：" not in rendered["content"]
    assert "需要下调关注的情形：" not in rendered["content"]
    assert "archive_targets" not in rendered["content"]
    assert "archive_targets_daily" not in rendered["content"]
    assert "archive_targets_15min" not in rendered["content"]
    assert "archive_targets_minute" not in rendered["content"]


def test_review_profile_keeps_full_default_seed_detail_visibility() -> None:
    rendered = MainReportHTMLRenderer().render(
        _assembled_sections(),
        report_run_id="report-run-review-1",
        artifact_uri="file:///tmp/review.html",
        generated_at=datetime(2099, 4, 22, 8, 4, tzinfo=timezone.utc),
        output_profile="review",
    )

    assert rendered["metadata"]["output_profile"] == "review"
    assert "核心关注 / 关注 模块" in rendered["content"]
    assert "机器人龙头A" in rendered["content"]
    assert "300024.SZ" in rendered["content"]
    assert "盘中重点看已有线索能否继续扩展为更明确的量价配合、资金承接与板块共振确认" in rendered["content"]
    assert "bundle-early" in rendered["content"]
    assert "phase1-main-early-v1" in rendered["content"]
    assert "source:early:robotics" in rendered["content"]
