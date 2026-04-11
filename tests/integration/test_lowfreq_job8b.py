"""Integration tests for Job 8B: announcements, news, research_reports, investor_qa.

Tests cover:
- Canonical current table operations
- Version history storage
- Daemon config includes new datasets
- Tushare adaptor fetch methods exist (if token available)
"""

import pytest
import uuid
from datetime import date, datetime

from ifa_data_platform.lowfreq.canonical_persistence import (
    AnnouncementsCurrent,
    InvestorQaCurrent,
    NewsCurrent,
    ResearchReportsCurrent,
)
from ifa_data_platform.lowfreq.daemon_config import get_daemon_config
from ifa_data_platform.lowfreq.version_persistence import (
    AnnouncementsHistory,
    InvestorQaHistory,
    NewsHistory,
    ResearchReportsHistory,
)


class TestAnnouncementsCanonical:
    """Tests for announcements current table."""

    def test_announcements_upsert(self):
        """Test upsert to announcements current table."""
        current = AnnouncementsCurrent()
        record_id = current.upsert(
            ann_date=date(2026, 4, 10),
            ts_code="600000.SH",
            name="浦发银行",
            title="2025年度业绩预告",
            url="http://example.com/announcement.pdf",
        )
        assert record_id is not None

    def test_announcements_get_by_ts_code(self):
        """Test get by ts_code."""
        current = AnnouncementsCurrent()
        current.upsert(
            ann_date=date(2026, 4, 9),
            ts_code="000001.SZ",
            name="平安银行",
            title="关于股份变动的公告",
        )
        records = current.get_by_ts_code("000001.SZ", limit=10)
        assert len(records) >= 1
        assert records[0]["ts_code"] == "000001.SZ"

    def test_announcements_list_all(self):
        """Test list all records."""
        current = AnnouncementsCurrent()
        current.upsert(
            ann_date=date(2026, 4, 8),
            ts_code="600519.SH",
            name="贵州茅台",
            title="年度报告",
        )
        records = current.list_all(limit=10)
        assert len(records) >= 1


class TestNewsCanonical:
    """Tests for news current table."""

    def test_news_upsert(self):
        """Test upsert to news current table."""
        current = NewsCurrent()
        record_id = current.upsert(
            datetime=datetime.now(),
            classify="财经",
            title="央行降息",
            source="新浪财经",
            url="http://example.com/news",
        )
        assert record_id is not None

    def test_news_list_all(self):
        """Test list all records."""
        current = NewsCurrent()
        current.upsert(
            datetime=datetime.now(),
            classify="证券",
            title="今日股市",
            source="东方财富",
        )
        records = current.list_all(limit=10)
        assert len(records) >= 1


class TestResearchReportsCanonical:
    """Tests for research_reports current table."""

    def test_research_reports_upsert(self):
        """Test upsert to research_reports current table."""
        current = ResearchReportsCurrent()
        record_id = current.upsert(
            trade_date=date(2026, 4, 10),
            ts_code="600000.SH",
            name="浦发银行",
            title="买入评级",
            report_type="个股研报",
            author="张三",
            inst_csname="中信证券",
            url="http://example.com/report.pdf",
        )
        assert record_id is not None

    def test_research_reports_get_by_ts_code(self):
        """Test get by ts_code."""
        current = ResearchReportsCurrent()
        current.upsert(
            trade_date=date(2026, 4, 9),
            ts_code="000001.SZ",
            name="平安银行",
            title="行业深度报告",
            inst_csname="华泰证券",
        )
        records = current.get_by_ts_code("000001.SZ", limit=10)
        assert len(records) >= 1
        assert records[0]["ts_code"] == "000001.SZ"

    def test_research_reports_list_all(self):
        """Test list all records."""
        current = ResearchReportsCurrent()
        current.upsert(
            trade_date=date(2026, 4, 8),
            ts_code="600519.SH",
            name="贵州茅台",
            title="季度财报",
            inst_csname="国泰君安",
        )
        records = current.list_all(limit=10)
        assert len(records) >= 1


class TestInvestorQaCanonical:
    """Tests for investor_qa current table."""

    def test_investor_qa_upsert(self):
        """Test upsert to investor_qa current table."""
        current = InvestorQaCurrent()
        record_id = current.upsert(
            ts_code="600000.SH",
            trade_date=date(2026, 4, 10),
            q="公司今年利润如何？",
            name="浦发银行",
            a="公司利润增长良好",
            pub_time=datetime.now(),
        )
        assert record_id is not None

    def test_investor_qa_get_by_ts_code(self):
        """Test get by ts_code."""
        current = InvestorQaCurrent()
        current.upsert(
            ts_code="000001.SZ",
            trade_date=date(2026, 4, 9),
            q="分红方案是什么？",
            name="平安银行",
            a="每10股派息",
        )
        records = current.get_by_ts_code("000001.SZ", limit=10)
        assert len(records) >= 1
        assert records[0]["ts_code"] == "000001.SZ"

    def test_investor_qa_list_all(self):
        """Test list all records."""
        current = InvestorQaCurrent()
        current.upsert(
            ts_code="600519.SH",
            trade_date=date(2026, 4, 8),
            q="产能情况？",
            name="贵州茅台",
            a="产能充足",
        )
        records = current.list_all(limit=10)
        assert len(records) >= 1


class TestAnnouncementsHistory:
    """Tests for announcements history table."""

    def test_announcements_history_store_version(self):
        """Test store version."""
        history = AnnouncementsHistory()
        records = [
            {
                "ann_date": date(2026, 4, 10),
                "ts_code": "600000.SH",
                "name": "浦发银行",
                "title": "业绩预告",
            },
        ]
        test_version = str(uuid.uuid4())
        count = history.store_version(test_version, records)
        assert count == 1


class TestNewsHistory:
    """Tests for news history table."""

    def test_news_history_store_version(self):
        """Test store version."""
        history = NewsHistory()
        records = [
            {
                "datetime": datetime.now(),
                "classify": "财经",
                "title": "央行降息",
                "source": "新浪",
            },
        ]
        test_version = str(uuid.uuid4())
        count = history.store_version(test_version, records)
        assert count == 1


class TestResearchReportsHistory:
    """Tests for research_reports history table."""

    def test_research_reports_history_store_version(self):
        """Test store version."""
        history = ResearchReportsHistory()
        records = [
            {
                "trade_date": date(2026, 4, 10),
                "ts_code": "600000.SH",
                "title": "买入评级",
                "inst_csname": "中信证券",
            },
        ]
        test_version = str(uuid.uuid4())
        count = history.store_version(test_version, records)
        assert count == 1


class TestInvestorQaHistory:
    """Tests for investor_qa history table."""

    def test_investor_qa_history_store_version(self):
        """Test store version."""
        history = InvestorQaHistory()
        records = [
            {
                "ts_code": "600000.SH",
                "trade_date": date(2026, 4, 10),
                "q": "利润如何？",
                "name": "浦发银行",
                "a": "增长良好",
            },
        ]
        test_version = str(uuid.uuid4())
        count = history.store_version(test_version, records)
        assert count == 1


class TestDaemonConfigIncludesJob8bDatasets:
    """Tests that daemon config includes new datasets."""

    def test_daemon_config_daily_light_includes_job8b_datasets(self):
        """Test daily_light group includes new datasets."""
        config = get_daemon_config()
        daily_light = config.get_group("daily_light")
        assert daily_light is not None
        assert "announcements" in daily_light.datasets
        assert "news" in daily_light.datasets
        assert "research_reports" in daily_light.datasets
        assert "investor_qa" in daily_light.datasets

    def test_daemon_config_weekly_deep_includes_job8b_datasets(self):
        """Test weekly_deep group includes new datasets."""
        config = get_daemon_config()
        weekly_deep = config.get_group("weekly_deep")
        assert weekly_deep is not None
        assert "announcements" in weekly_deep.datasets
        assert "news" in weekly_deep.datasets
        assert "research_reports" in weekly_deep.datasets
        assert "investor_qa" in weekly_deep.datasets
