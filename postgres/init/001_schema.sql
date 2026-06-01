CREATE TABLE IF NOT EXISTS assets (
  asset_id BIGSERIAL PRIMARY KEY,
  symbol TEXT NOT NULL UNIQUE,
  display_name_ko TEXT,
  display_name_en TEXT,
  asset_type TEXT NOT NULL DEFAULT 'stock',
  exchange TEXT,
  currency TEXT,
  country TEXT,
  active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS sectors (
  sector_id BIGSERIAL PRIMARY KEY,
  slug TEXT NOT NULL UNIQUE,
  name_ko TEXT NOT NULL,
  name_en TEXT,
  description TEXT,
  sort_order INT NOT NULL DEFAULT 0,
  active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS themes (
  theme_id BIGSERIAL PRIMARY KEY,
  slug TEXT NOT NULL UNIQUE,
  name_ko TEXT NOT NULL,
  name_en TEXT,
  description TEXT,
  sort_order INT NOT NULL DEFAULT 0,
  active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS watchlists (
  watchlist_id BIGSERIAL PRIMARY KEY,
  slug TEXT NOT NULL UNIQUE,
  name_ko TEXT NOT NULL,
  name_en TEXT,
  description TEXT,
  parent_type TEXT CHECK (parent_type IN ('sector', 'theme', 'global')),
  parent_slug TEXT,
  sort_order INT NOT NULL DEFAULT 0,
  active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS watchlist_members (
  watchlist_id BIGINT NOT NULL REFERENCES watchlists(watchlist_id) ON DELETE CASCADE,
  asset_id BIGINT NOT NULL REFERENCES assets(asset_id) ON DELETE CASCADE,
  weight NUMERIC,
  sort_order INT NOT NULL DEFAULT 0,
  note TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (watchlist_id, asset_id)
);

CREATE TABLE IF NOT EXISTS asset_sector_map (
  asset_id BIGINT NOT NULL REFERENCES assets(asset_id) ON DELETE CASCADE,
  sector_id BIGINT NOT NULL REFERENCES sectors(sector_id) ON DELETE CASCADE,
  is_primary BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (asset_id, sector_id)
);

CREATE TABLE IF NOT EXISTS asset_theme_map (
  asset_id BIGINT NOT NULL REFERENCES assets(asset_id) ON DELETE CASCADE,
  theme_id BIGINT NOT NULL REFERENCES themes(theme_id) ON DELETE CASCADE,
  relevance NUMERIC,
  note TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (asset_id, theme_id)
);

CREATE TABLE IF NOT EXISTS daily_prices (
  asset_id BIGINT NOT NULL REFERENCES assets(asset_id) ON DELETE CASCADE,
  date DATE NOT NULL,
  open NUMERIC,
  high NUMERIC,
  low NUMERIC,
  close NUMERIC,
  volume NUMERIC,
  source TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (asset_id, date)
);

CREATE TABLE IF NOT EXISTS daily_indicators (
  asset_id BIGINT NOT NULL REFERENCES assets(asset_id) ON DELETE CASCADE,
  date DATE NOT NULL,
  return_1d NUMERIC,
  return_1w NUMERIC,
  return_1m NUMERIC,
  return_3m NUMERIC,
  return_6m NUMERIC,
  return_ytd NUMERIC,
  ma5 NUMERIC,
  ma20 NUMERIC,
  ma50 NUMERIC,
  ma120 NUMERIC,
  rsi14 NUMERIC,
  vol20 NUMERIC,
  drawdown_52w NUMERIC,
  high_52w NUMERIC,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (asset_id, date)
);

CREATE TABLE IF NOT EXISTS research_views (
  view_id BIGSERIAL PRIMARY KEY,
  target_type TEXT NOT NULL CHECK (target_type IN ('asset', 'sector', 'theme', 'watchlist')),
  target_slug TEXT NOT NULL,
  report_date DATE NOT NULL,
  horizon TEXT NOT NULL DEFAULT 'on_demand',
  opinion TEXT CHECK (opinion IN ('매수', '아웃퍼폼', '중립', '언더퍼폼', '매도')),
  thesis TEXT,
  rationale JSONB,
  bull TEXT,
  base TEXT,
  bear TEXT,
  risks JSONB,
  triggers JSONB,
  sources JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (target_type, target_slug, report_date, horizon)
);

CREATE TABLE IF NOT EXISTS report_runs (
  run_id UUID PRIMARY KEY,
  run_type TEXT NOT NULL CHECK (run_type IN ('startup-market-refresh', 'on-demand-research', 'dashboard-refresh')),
  scope_type TEXT CHECK (scope_type IN ('global', 'sector', 'theme', 'watchlist', 'asset')),
  scope_slug TEXT,
  started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at TIMESTAMPTZ,
  status TEXT NOT NULL,
  failed_assets JSONB,
  output_summary TEXT,
  output_path TEXT,
  error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_assets_symbol ON assets(symbol);
CREATE INDEX IF NOT EXISTS idx_daily_prices_asset_date ON daily_prices(asset_id, date DESC);
CREATE INDEX IF NOT EXISTS idx_daily_indicators_asset_date ON daily_indicators(asset_id, date DESC);
CREATE INDEX IF NOT EXISTS idx_research_views_target_date ON research_views(target_type, target_slug, report_date DESC);
CREATE INDEX IF NOT EXISTS idx_report_runs_scope_started ON report_runs(scope_type, scope_slug, started_at DESC);
