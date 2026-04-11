"""Integration tests for Job 8A: index_basic, fund_basic_etf, sw_industry_mapping.

Tests cover:
- Canonical current table operations
- Version history storage
- Daemon config includes new datasets
- Tushare adaptor fetch methods exist (if token available)
"""

import pytest
import uuid
from datetime import date

from ifa_data_platform.lowfreq.canonical_persistence import (
    FundBasicEtfCurrent,
    IndexBasicCurrent,
    SwIndustryMappingCurrent,
)
from ifa_data_platform.lowfreq.daemon_config import get_daemon_config
from ifa_data_platform.lowfreq.version_persistence import (
    FundBasicEtfHistory,
    IndexBasicHistory,
    SwIndustryMappingHistory,
)


class TestIndexBasicCanonical:
    """Tests for index_basic current table."""

    def test_index_basic_upsert(self):
        """Test upsert to index_basic current table."""
        current = IndexBasicCurrent()
        record_id = current.upsert(
            ts_code="000001.SH",
            name="上证指数",
            market="SSE",
            publisher="上交所",
            category="指数",
            base_date=date(1990, 12, 19),
            base_point=100.0,
            list_date=date(1991, 7, 15),
            weight_rule="市值加权",
        )
        assert record_id is not None

    def test_index_basic_get_by_ts_code(self):
        """Test get by ts_code."""
        current = IndexBasicCurrent()
        current.upsert(
            ts_code="399001.SZ",
            name="深证成指",
            market="SZSE",
        )
        record = current.get_by_ts_code("399001.SZ")
        assert record is not None
        assert record["ts_code"] == "399001.SZ"
        assert record["name"] == "深证成指"

    def test_index_basic_list_all(self):
        """Test list all records."""
        current = IndexBasicCurrent()
        current.upsert(ts_code="000016.SH", name="上证50", market="SSE")
        records = current.list_all(limit=10)
        assert len(records) >= 1


class TestFundBasicEtfCanonical:
    """Tests for fund_basic_etf current table."""

    def test_fund_basic_etf_upsert(self):
        """Test upsert to fund_basic_etf current table."""
        current = FundBasicEtfCurrent()
        record_id = current.upsert(
            ts_code="510050.SH",
            name="上证50ETF",
            market="SSE",
            fund_type="ETF",
            management="华夏基金",
            custodian="招商银行",
            list_date=date(2004, 12, 30),
            invest_type="股票型",
            benchmark="上证50指数",
            status="L",
        )
        assert record_id is not None

    def test_fund_basic_etf_get_by_ts_code(self):
        """Test get by ts_code."""
        current = FundBasicEtfCurrent()
        current.upsert(
            ts_code="159915.SZ",
            name="创业板50ETF",
            market="SZSE",
            fund_type="ETF",
        )
        record = current.get_by_ts_code("159915.SZ")
        assert record is not None
        assert record["ts_code"] == "159915.SZ"

    def test_fund_basic_etf_list_all(self):
        """Test list all records."""
        current = FundBasicEtfCurrent()
        current.upsert(
            ts_code="512880.SH", name="证券ETF", market="SSE", fund_type="ETF"
        )
        records = current.list_all(limit=10)
        assert len(records) >= 1


class TestSwIndustryMappingCanonical:
    """Tests for sw_industry_mapping current table."""

    def test_sw_industry_mapping_upsert(self):
        """Test upsert to sw_industry_mapping current table."""
        current = SwIndustryMappingCurrent()
        record_id = current.upsert(
            index_code="801010",
            industry_name="农林牧渔",
            level=1,
            parent_code=None,
            src="sw",
            member_ts_code=None,
            member_name=None,
            is_active=True,
        )
        assert record_id is not None

    def test_sw_industry_mapping_upsert_with_member(self):
        """Test upsert with member mapping."""
        current = SwIndustryMappingCurrent()
        record_id = current.upsert(
            index_code="801010",
            industry_name="农林牧渔",
            level=2,
            parent_code="801010",
            src="sw",
            member_ts_code="600019.SH",
            member_name="宝钢股份",
            in_date=date(2020, 1, 1),
            is_active=True,
        )
        assert record_id is not None

    def test_sw_industry_mapping_get_by_member(self):
        """Test get by member ts_code."""
        current = SwIndustryMappingCurrent()
        current.upsert(
            index_code="801030",
            industry_name="化工",
            level=1,
            src="sw",
            member_ts_code="600309.SH",
            member_name="万华化学",
            in_date=date(2021, 1, 1),
            is_active=True,
        )
        records = current.get_by_member("600309.SH")
        assert len(records) >= 1
        assert records[0]["member_ts_code"] == "600309.SH"

    def test_sw_industry_mapping_list_all(self):
        """Test list all records."""
        current = SwIndustryMappingCurrent()
        current.upsert(index_code="801010", industry_name="农林牧渔", level=1, src="sw")
        records = current.list_all(limit=10)
        assert len(records) >= 1


class TestIndexBasicHistory:
    """Tests for index_basic history table."""

    def test_index_basic_history_store_version(self):
        """Test store version."""
        history = IndexBasicHistory()
        records = [
            {"ts_code": "000001.SH", "name": "上证指数", "market": "SSE"},
            {"ts_code": "399001.SZ", "name": "深证成指", "market": "SZSE"},
        ]
        test_version = str(uuid.uuid4())
        count = history.store_version(test_version, records)
        assert count == 2

    def test_index_basic_history_query_by_version(self):
        """Test query by version."""
        history = IndexBasicHistory()
        records = [
            {"ts_code": "000016.SH", "name": "上证50", "market": "SSE"},
        ]
        test_version = str(uuid.uuid4())
        history.store_version(test_version, records)
        retrieved = history.query_by_version(test_version)
        assert len(retrieved) == 1
        assert retrieved[0]["ts_code"] == "000016.SH"


class TestFundBasicEtfHistory:
    """Tests for fund_basic_etf history table."""

    def test_fund_basic_etf_history_store_version(self):
        """Test store version."""
        history = FundBasicEtfHistory()
        records = [
            {"ts_code": "510050.SH", "name": "上证50ETF", "fund_type": "ETF"},
        ]
        test_version = str(uuid.uuid4())
        count = history.store_version(test_version, records)
        assert count == 1


class TestSwIndustryMappingHistory:
    """Tests for sw_industry_mapping history table."""

    def test_sw_industry_mapping_history_store_version(self):
        """Test store version."""
        history = SwIndustryMappingHistory()
        records = [
            {
                "index_code": "801010",
                "industry_name": "农林牧渔",
                "level": 1,
                "src": "sw",
            },
        ]
        test_version = str(uuid.uuid4())
        count = history.store_version(test_version, records)
        assert count == 1


class TestSwIndustryMappingHistory:
    """Tests for sw_industry_mapping history table."""

    def test_sw_industry_mapping_history_store_version(self):
        """Test store version."""
        history = SwIndustryMappingHistory()
        records = [
            {
                "index_code": "801010",
                "industry_name": "农林牧渔",
                "level": 1,
                "src": "sw",
            },
        ]
        test_version = str(uuid.uuid4())
        count = history.store_version(test_version, records)
        assert count == 1


class TestDaemonConfigIncludesNewDatasets:
    """Tests that daemon config includes new datasets."""

    def test_daemon_config_daily_light_includes_new_datasets(self):
        """Test daily_light group includes new datasets."""
        config = get_daemon_config()
        daily_light = config.get_group("daily_light")
        assert daily_light is not None
        assert "index_basic" in daily_light.datasets
        assert "fund_basic_etf" in daily_light.datasets
        assert "sw_industry_mapping" in daily_light.datasets

    def test_daemon_config_weekly_deep_includes_new_datasets(self):
        """Test weekly_deep group includes new datasets."""
        config = get_daemon_config()
        weekly_deep = config.get_group("weekly_deep")
        assert weekly_deep is not None
        assert "index_basic" in weekly_deep.datasets
        assert "fund_basic_etf" in weekly_deep.datasets
        assert "sw_industry_mapping" in weekly_deep.datasets
