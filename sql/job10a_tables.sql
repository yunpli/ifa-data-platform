-- Migration: Add Job 10A asset-layer lowfreq tables
-- Run this script to create missing tables

-- forecast_current
CREATE TABLE IF NOT EXISTS ifa2.forecast_current (
    id TEXT PRIMARY KEY,
    ts_code TEXT NOT NULL,
    ann_date DATE NOT NULL,
    end_date DATE NOT NULL,
    type TEXT,
    p_change_min NUMERIC(10,4),
    p_change_max NUMERIC(10,4),
    net_profit_min NUMERIC(20,4),
    net_profit_max NUMERIC(20,4),
    eps_min NUMERIC(20,4),
    eps_max NUMERIC(20,4),
    roe_min NUMERIC(10,4),
    roe_max NUMERIC(10,4),
    net_profit_ratio_min NUMERIC(10,4),
    net_profit_ratio_max NUMERIC(10,4),
    op_income_min NUMERIC(20,4),
    op_income_max NUMERIC(20,4),
    version_id TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    UNIQUE (ts_code, ann_date, end_date, type)
);

-- forecast_history
CREATE TABLE IF NOT EXISTS ifa2.forecast_history (
    id TEXT PRIMARY KEY,
    version_id TEXT NOT NULL,
    ts_code TEXT NOT NULL,
    ann_date DATE NOT NULL,
    end_date DATE NOT NULL,
    type TEXT,
    p_change_min NUMERIC(10,4),
    p_change_max NUMERIC(10,4),
    net_profit_min NUMERIC(20,4),
    net_profit_max NUMERIC(20,4),
    eps_min NUMERIC(20,4),
    eps_max NUMERIC(20,4),
    roe_min NUMERIC(10,4),
    roe_max NUMERIC(10,4),
    net_profit_ratio_min NUMERIC(10,4),
    net_profit_ratio_max NUMERIC(10,4),
    op_income_min NUMERIC(20,4),
    op_income_max NUMERIC(20,4),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- margin_current (exchange level summary)
CREATE TABLE IF NOT EXISTS ifa2.margin_current (
    id TEXT PRIMARY KEY,
    trade_date DATE NOT NULL,
    exchange_id TEXT NOT NULL,
    ts_code TEXT,
    rzye NUMERIC(20,4),
    rzmre NUMERIC(20,4),
    rzche NUMERIC(20,4),
    rzche_ratio NUMERIC(10,4),
    rqye NUMERIC(20,4),
    rqmcl NUMERIC(20,4),
    rqchl NUMERIC(20,4),
    rqchl_ratio NUMERIC(10,4),
    total_market NUMERIC(20,4),
    total_margin NUMERIC(20,4),
    version_id TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    UNIQUE (trade_date, ts_code)
);

-- north_south_flow_current
CREATE TABLE IF NOT EXISTS ifa2.north_south_flow_current (
    id TEXT PRIMARY KEY,
    trade_date DATE NOT NULL,
    ggt_ss NUMERIC(20,4),
    ggt_sz NUMERIC(20,4),
    hgt NUMERIC(20,4),
    sgt NUMERIC(20,4),
    north_money NUMERIC(20,4),
    south_money NUMERIC(20,4),
    version_id TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    UNIQUE (trade_date)
);

-- north_south_flow_history (add ts_code column if not exists as variant)
-- Note: moneyflow_hsgt returns market level, not stock level