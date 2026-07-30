-- 006_portfolio_returns.sql
-- Phase 2-1: 포트폴리오 거래 기록 + 스냅샷 테이블

ALTER TABLE portfolio_holdings
  ADD COLUMN IF NOT EXISTS currency TEXT;

CREATE TABLE IF NOT EXISTS portfolio_transactions (
  transaction_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  holding_id UUID NOT NULL REFERENCES portfolio_holdings(holding_id) ON DELETE CASCADE,
  profile_id BIGINT NOT NULL REFERENCES profiles(profile_id) ON DELETE CASCADE,
  asset_id BIGINT NOT NULL REFERENCES assets(asset_id) ON DELETE CASCADE,
  transaction_type TEXT NOT NULL CHECK (transaction_type IN ('buy', 'sell', 'dividend', 'split')),
  quantity NUMERIC NOT NULL,
  price_per_unit NUMERIC NOT NULL CHECK (price_per_unit >= 0),
  fee NUMERIC NOT NULL DEFAULT 0 CHECK (fee >= 0),
  currency TEXT,
  transaction_date DATE NOT NULL,
  note TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_portfolio_transactions_holding
  ON portfolio_transactions(holding_id, transaction_date);
CREATE INDEX IF NOT EXISTS idx_portfolio_transactions_profile_date
  ON portfolio_transactions(profile_id, transaction_date DESC);

CREATE TABLE IF NOT EXISTS portfolio_snapshots (
  snapshot_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  profile_id BIGINT NOT NULL REFERENCES profiles(profile_id) ON DELETE CASCADE,
  snapshot_date DATE NOT NULL,
  total_cost NUMERIC NOT NULL,
  total_value NUMERIC NOT NULL,
  total_return NUMERIC NOT NULL,
  total_return_pct NUMERIC NOT NULL,
  daily_return_pct NUMERIC,
  holdings_json JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (profile_id, snapshot_date)
);

CREATE INDEX IF NOT EXISTS idx_portfolio_snapshots_profile_date
  ON portfolio_snapshots(profile_id, snapshot_date DESC);
