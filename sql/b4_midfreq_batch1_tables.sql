-- Migration: B4 Midfreq Batch 1 tables
-- Run this script to create midfreq tables

-- Equity daily bar current
CREATE TABLE IF NOT EXISTS ifa2.equity_daily_bar_current (
    id TEXT PRIMARY KEY,
    ts_code TEXT NOT NULL,
    trade_date DATE NOT NULL,
    open NUMERIC(20,4),
    high NUMERIC(20,4),
    low NUMERIC(20,4),
    close NUMERIC(20,4),
    vol NUMERIC(20,4),
    amount NUMERIC(20,4),
    pre_close NUMERIC(20,4),
    change NUMERIC(20,4),
    pct_chg NUMERIC(10,4),
    version_id TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    UNIQUE (ts_code, trade_date)
);

CREATE TABLE IF NOT EXISTS ifa2.equity_daily_bar_history (
    id TEXT PRIMARY KEY,
    version_id TEXT NOT NULL,
    ts_code TEXT NOT NULL,
    trade_date DATE NOT NULL,
    open NUMERIC(20,4),
    high NUMERIC(20,4),
    low NUMERIC(20,4),
    close NUMERIC(20,4),
    vol NUMERIC(20,4),
    amount NUMERIC(20,4),
    pre_close NUMERIC(20,4),
    change NUMERIC(20,4),
    pct_chg NUMERIC(10,4),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Index daily bar current
CREATE TABLE IF NOT EXISTS ifa2.index_daily_bar_current (
    id TEXT PRIMARY KEY,
    ts_code TEXT NOT NULL,
    trade_date DATE NOT NULL,
    open NUMERIC(20,4),
    high NUMERIC(20,4),
    low NUMERIC(20,4),
    close NUMERIC(20,4),
    vol NUMERIC(20,4),
    amount NUMERIC(20,4),
    pre_close NUMERIC(20,4),
    change NUMERIC(20,4),
    pct_chg NUMERIC(10,4),
    version_id TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    UNIQUE (ts_code, trade_date)
);

CREATE TABLE IF NOT EXISTS ifa2.index_daily_bar_history (
    id TEXT PRIMARY KEY,
    version_id TEXT NOT NULL,
    ts_code TEXT NOT NULL,
    trade_date DATE NOT NULL,
    open NUMERIC(20,4),
    high NUMERIC(20,4),
    low NUMERIC(20,4),
    close NUMERIC(20,4),
    vol NUMERIC(20,4),
    amount NUMERIC(20,4),
    pre_close NUMERIC(20,4),
    change NUMERIC(20,4),
    pct_chg NUMERIC(10,4),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- ETF daily bar current
CREATE TABLE IF NOT EXISTS ifa2.etf_daily_bar_current (
    id TEXT PRIMARY KEY,
    ts_code TEXT NOT NULL,
    trade_date DATE NOT NULL,
    open NUMERIC(20,4),
    high NUMERIC(20,4),
    low NUMERIC(20,4),
    close NUMERIC(20,4),
    vol NUMERIC(20,4),
    amount NUMERIC(20,4),
    pre_close NUMERIC(20,4),
    change NUMERIC(20,4),
    pct_chg NUMERIC(10,4),
    version_id TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    UNIQUE (ts_code, trade_date)
);

CREATE TABLE IF NOT EXISTS ifa2.etf_daily_bar_history (
    id TEXT PRIMARY KEY,
    version_id TEXT NOT NULL,
    ts_code TEXT NOT NULL,
    trade_date DATE NOT NULL,
    open NUMERIC(20,4),
    high NUMERIC(20,4),
    low NUMERIC(20,4),
    close NUMERIC(20,4),
    vol NUMERIC(20,4),
    amount NUMERIC(20,4),
    pre_close NUMERIC(20,4),
    change NUMERIC(20,4),
    pct_chg NUMERIC(10,4),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Northbound flow current
CREATE TABLE IF NOT EXISTS ifa2.northbound_flow_current (
    id TEXT PRIMARY KEY,
    trade_date DATE NOT NULL,
    north_money NUMERIC(20,4),
    north_bal NUMERIC(20,4),
    north_buy NUMERIC(20,4),
    north_sell NUMERIC(20,4),
    version_id TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    UNIQUE (trade_date)
);

CREATE TABLE IF NOT EXISTS ifa2.northbound_flow_history (
    id TEXT PRIMARY KEY,
    version_id TEXT NOT NULL,
    trade_date DATE NOT NULL,
    north_money NUMERIC(20,4),
    north_bal NUMERIC(20,4),
    north_buy NUMERIC(20,4),
    north_sell NUMERIC(20,4),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Limit up/down status current
CREATE TABLE IF NOT EXISTS ifa2.limit_up_down_status_current (
    id TEXT PRIMARY KEY,
    trade_date DATE NOT NULL,
    limit_up_count INTEGER,
    limit_down_count INTEGER,
    limit_up_streak_high INTEGER,
    limit_down_streak_high INTEGER,
    version_id TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    UNIQUE (trade_date)
);

CREATE TABLE IF NOT EXISTS ifa2.limit_up_down_status_history (
    id TEXT PRIMARY KEY,
    version_id TEXT NOT NULL,
    trade_date DATE NOT NULL,
    limit_up_count INTEGER,
    limit_down_count INTEGER,
    limit_up_streak_high INTEGER,
    limit_down_streak_high INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Midfreq dataset registry (similar to lowfreq_datasets)
CREATE TABLE IF NOT EXISTS ifa2.midfreq_datasets (
    id TEXT PRIMARY KEY,
    dataset_name TEXT NOT NULL UNIQUE,
    market TEXT NOT NULL,
    source_name TEXT NOT NULL,
    job_type TEXT NOT NULL,
    enabled INTEGER DEFAULT 1,
    timezone_semantics TEXT DEFAULT 'china_shanghai',
    runner_type TEXT DEFAULT 'generic',
    watermark_strategy TEXT DEFAULT 'date_based',
    budget_records_max INTEGER,
    budget_seconds_max INTEGER,
    metadata TEXT,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Midfreq daemon state
CREATE TABLE IF NOT EXISTS ifa2.midfreq_daemon_state (
    daemon_name TEXT PRIMARY KEY,
    latest_loop_at TIMESTAMP WITH TIME ZONE,
    latest_status TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Midfreq window state
CREATE TABLE IF NOT EXISTS ifa2.midfreq_window_state (
    window_type TEXT PRIMARY KEY,
    group_name TEXT,
    succeeded_today INTEGER DEFAULT 0,
    retry_count INTEGER DEFAULT 0,
    last_status TEXT,
    last_run_time TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_equity_daily_bar_ts_code ON ifa2.equity_daily_bar_current(ts_code);
CREATE INDEX IF NOT EXISTS idx_equity_daily_bar_date ON ifa2.equity_daily_bar_current(trade_date);
CREATE INDEX IF NOT EXISTS idx_index_daily_bar_ts_code ON ifa2.index_daily_bar_current(ts_code);
CREATE INDEX IF NOT EXISTS idx_index_daily_bar_date ON ifa2.index_daily_bar_current(trade_date);
CREATE INDEX IF NOT EXISTS idx_etf_daily_bar_ts_code ON ifa2.etf_daily_bar_current(ts_code);
CREATE INDEX IF NOT EXISTS idx_etf_daily_bar_date ON ifa2.etf_daily_bar_current(trade_date);
CREATE INDEX IF NOT EXISTS idx_northbound_flow_date ON ifa2.northbound_flow_current(trade_date);
CREATE INDEX IF NOT EXISTS idx_limit_up_down_date ON ifa2.limit_up_down_status_current(trade_date);
CREATE INDEX IF NOT EXISTS idx_midfreq_datasets_name ON ifa2.midfreq_datasets(dataset_name);