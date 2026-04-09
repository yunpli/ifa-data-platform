import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Integer, Numeric, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class SourceRegistry(Base):
    __tablename__ = "source_registry"
    __table_args__ = {"schema": "ifa2"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_name = Column(String(255), nullable=False, unique=True)
    source_type = Column(String(100), nullable=False)
    base_url = Column(String(500))
    credentials_secret = Column(String(255))
    config_json = Column(Text)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class JobRuns(Base):
    __tablename__ = "job_runs"
    __table_args__ = {"schema": "ifa2"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_name = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    error_message = Column(Text)
    records_processed = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class RawRecords(Base):
    __tablename__ = "raw_records"
    __table_args__ = {"schema": "ifa2"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(UUID(as_uuid=True), nullable=False)
    record_hash = Column(String(64), nullable=False)
    raw_json = Column(Text, nullable=False)
    ingested_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime)


class Items(Base):
    __tablename__ = "items"
    __table_args__ = {"schema": "ifa2"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    item_type = Column(String(100), nullable=False)
    cik = Column(String(20))
    entity_name = Column(String(255))
    data_json = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class OfficialEvents(Base):
    __tablename__ = "official_events"
    __table_args__ = {"schema": "ifa2"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(String(100), nullable=False)
    event_date = Column(DateTime, nullable=False)
    cik = Column(String(20))
    entity_name = Column(String(255))
    details_json = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class MarketBars(Base):
    __tablename__ = "market_bars"
    __table_args__ = (
        Index("ix_market_bars_symbol_date", "symbol", "bar_date"),
        {"schema": "ifa2"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol = Column(String(20), nullable=False)
    bar_date = Column(DateTime, nullable=False)
    open = Column(Numeric(18, 6))
    high = Column(Numeric(18, 6))
    low = Column(Numeric(18, 6))
    close = Column(Numeric(18, 6))
    volume = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)


class Filings(Base):
    __tablename__ = "filings"
    __table_args__ = {"schema": "ifa2"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cik = Column(String(20), nullable=False)
    entity_name = Column(String(255))
    form_type = Column(String(20), nullable=False)
    filing_date = Column(DateTime, nullable=False)
    period_of_report = Column(DateTime)
    filed_at = Column(DateTime)
    html_content = Column(Text)
    accession_number = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)


class Facts(Base):
    __tablename__ = "facts"
    __table_args__ = (
        Index("ix_facts_filing_id_tag", "filing_id", "tag"),
        {"schema": "ifa2"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filing_id = Column(UUID(as_uuid=True), nullable=False)
    tag = Column(String(256), nullable=False)
    value = Column(Text)
    unit = Column(String(20))
    context = Column(String(256))
    created_at = Column(DateTime, default=datetime.utcnow)


class FactSources(Base):
    __tablename__ = "fact_sources"
    __table_args__ = {"schema": "ifa2"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_name = Column(String(255), nullable=False, unique=True)
    entity_name = Column(String(255))
    fact_tags = Column(Text)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)


class SlotMaterializations(Base):
    __tablename__ = "slot_materializations"
    __table_args__ = {"schema": "ifa2"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slot_name = Column(String(255), nullable=False)
    version = Column(String(50), nullable=False)
    data_json = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
