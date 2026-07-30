from __future__ import annotations

SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS profiles (
  profile_id INTEGER PRIMARY KEY AUTOINCREMENT,
  auth_user_id TEXT UNIQUE,
  slug TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  email TEXT,
  auth_provider TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS assets (
  asset_id INTEGER PRIMARY KEY AUTOINCREMENT,
  symbol TEXT NOT NULL UNIQUE,
  display_name_ko TEXT,
  exchange TEXT,
  currency TEXT,
  active INTEGER NOT NULL DEFAULT 1,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS watchlists (
  watchlist_id INTEGER PRIMARY KEY AUTOINCREMENT,
  slug TEXT NOT NULL UNIQUE,
  name_ko TEXT NOT NULL,
  parent_type TEXT NOT NULL DEFAULT 'global',
  sort_order INTEGER NOT NULL DEFAULT 0,
  owner_profile_id INTEGER REFERENCES profiles(profile_id) ON DELETE SET NULL,
  visibility TEXT NOT NULL DEFAULT 'private',
  archived_at TIMESTAMP,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS watchlist_members (
  watchlist_id INTEGER NOT NULL REFERENCES watchlists(watchlist_id) ON DELETE CASCADE,
  asset_id INTEGER NOT NULL REFERENCES assets(asset_id) ON DELETE CASCADE,
  sort_order INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (watchlist_id, asset_id)
);

CREATE TABLE IF NOT EXISTS daily_prices (
  asset_id INTEGER NOT NULL REFERENCES assets(asset_id) ON DELETE CASCADE,
  date DATE NOT NULL,
  open REAL,
  high REAL,
  low REAL,
  close REAL,
  adj_close REAL,
  volume REAL,
  source TEXT,
  provider TEXT,
  currency TEXT,
  fetched_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (asset_id, date)
);

CREATE TABLE IF NOT EXISTS daily_indicators (
  asset_id INTEGER NOT NULL REFERENCES assets(asset_id) ON DELETE CASCADE,
  date DATE NOT NULL,
  return_1d REAL,
  return_1w REAL,
  return_1m REAL,
  return_3m REAL,
  return_6m REAL,
  return_ytd REAL,
  ma5 REAL,
  ma20 REAL,
  ma50 REAL,
  ma120 REAL,
  rsi14 REAL,
  vol20 REAL,
  drawdown_52w REAL,
  high_52w REAL,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (asset_id, date)
);

CREATE TABLE IF NOT EXISTS news_items (
  news_id INTEGER PRIMARY KEY AUTOINCREMENT,
  provider TEXT NOT NULL,
  source TEXT,
  source_id TEXT,
  url TEXT,
  canonical_url TEXT,
  title TEXT NOT NULL,
  published_at TIMESTAMP,
  content_hash TEXT,
  language TEXT,
  summary TEXT,
  raw_json TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_news_provider_source_id
  ON news_items(provider, source_id) WHERE source_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS ux_news_provider_content_hash
  ON news_items(provider, content_hash) WHERE content_hash IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS ux_news_canonical_url
  ON news_items(canonical_url) WHERE canonical_url IS NOT NULL;

CREATE TABLE IF NOT EXISTS asset_news_map (
  asset_id INTEGER NOT NULL REFERENCES assets(asset_id) ON DELETE CASCADE,
  news_id INTEGER NOT NULL REFERENCES news_items(news_id) ON DELETE CASCADE,
  relevance REAL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (asset_id, news_id)
);

CREATE TABLE IF NOT EXISTS disclosures (
  disclosure_id INTEGER PRIMARY KEY AUTOINCREMENT,
  asset_id INTEGER REFERENCES assets(asset_id) ON DELETE SET NULL,
  market TEXT,
  provider TEXT NOT NULL,
  provider_disclosure_id TEXT,
  title TEXT NOT NULL,
  published_at TIMESTAMP,
  url TEXT,
  raw_json TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_disclosures_provider_id
  ON disclosures(provider, provider_disclosure_id) WHERE provider_disclosure_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS research_views (
  view_id INTEGER PRIMARY KEY AUTOINCREMENT,
  target_type TEXT NOT NULL,
  target_slug TEXT NOT NULL,
  report_date DATE NOT NULL,
  horizon TEXT NOT NULL DEFAULT 'on_demand',
  opinion TEXT,
  thesis TEXT,
  rationale TEXT,
  bull TEXT,
  base TEXT,
  bear TEXT,
  risks TEXT,
  triggers TEXT,
  sources TEXT,
  confidence REAL,
  source_freshness_status TEXT NOT NULL DEFAULT 'unknown',
  access_tier TEXT NOT NULL DEFAULT 'free',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (target_type, target_slug, report_date, horizon)
);

CREATE TABLE IF NOT EXISTS report_runs (
  run_id TEXT PRIMARY KEY,
  run_type TEXT NOT NULL,
  scope_type TEXT,
  scope_slug TEXT,
  completed_at TIMESTAMP NOT NULL,
  status TEXT NOT NULL,
  failed_assets TEXT,
  output_summary TEXT,
  output_path TEXT,
  error_message TEXT
);
CREATE INDEX IF NOT EXISTS idx_report_runs_scope_completed
  ON report_runs(run_type, scope_slug, completed_at DESC);

CREATE TABLE IF NOT EXISTS obsidian_exports (
  export_id TEXT PRIMARY KEY,
  view_id INTEGER,
  target_slug TEXT NOT NULL,
  report_date DATE NOT NULL,
  vault_path TEXT NOT NULL,
  relative_path TEXT NOT NULL,
  file_hash TEXT NOT NULL,
  status TEXT NOT NULL,
  error_message TEXT,
  exported_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (target_slug, report_date, relative_path)
);

CREATE TABLE IF NOT EXISTS job_locks (
  lock_name TEXT PRIMARY KEY,
  holder TEXT NOT NULL,
  acquired_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  expires_at TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS settings_metadata (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS portfolio_holdings (
  holding_id TEXT PRIMARY KEY,
  profile_id INTEGER NOT NULL REFERENCES profiles(profile_id) ON DELETE CASCADE,
  asset_id INTEGER NOT NULL REFERENCES assets(asset_id) ON DELETE CASCADE,
  quantity REAL NOT NULL CHECK (quantity > 0),
  average_cost REAL CHECK (average_cost IS NULL OR average_cost >= 0),
  currency TEXT,
  note TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (profile_id, asset_id)
);
CREATE INDEX IF NOT EXISTS idx_portfolio_holdings_profile_id
  ON portfolio_holdings(profile_id);

CREATE TABLE IF NOT EXISTS portfolio_transactions (
  transaction_id TEXT PRIMARY KEY,
  holding_id TEXT NOT NULL REFERENCES portfolio_holdings(holding_id) ON DELETE CASCADE,
  profile_id INTEGER NOT NULL REFERENCES profiles(profile_id) ON DELETE CASCADE,
  asset_id INTEGER NOT NULL REFERENCES assets(asset_id) ON DELETE CASCADE,
  transaction_type TEXT NOT NULL CHECK (transaction_type IN ('buy', 'sell', 'dividend', 'split')),
  quantity REAL NOT NULL,
  price_per_unit REAL NOT NULL CHECK (price_per_unit >= 0),
  fee REAL NOT NULL DEFAULT 0 CHECK (fee >= 0),
  currency TEXT,
  transaction_date DATE NOT NULL,
  note TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_portfolio_transactions_holding
  ON portfolio_transactions(holding_id, transaction_date);
CREATE INDEX IF NOT EXISTS idx_portfolio_transactions_profile_date
  ON portfolio_transactions(profile_id, transaction_date DESC);

CREATE TABLE IF NOT EXISTS portfolio_snapshots (
  snapshot_id TEXT PRIMARY KEY,
  profile_id INTEGER NOT NULL REFERENCES profiles(profile_id) ON DELETE CASCADE,
  snapshot_date DATE NOT NULL,
  total_cost REAL NOT NULL,
  total_value REAL NOT NULL,
  total_return REAL NOT NULL,
  total_return_pct REAL NOT NULL,
  daily_return_pct REAL,
  holdings_json TEXT NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (profile_id, snapshot_date)
);
CREATE INDEX IF NOT EXISTS idx_portfolio_snapshots_profile_date
  ON portfolio_snapshots(profile_id, snapshot_date DESC);

CREATE TABLE IF NOT EXISTS notifications (
  notification_id TEXT PRIMARY KEY,
  profile_id INTEGER NOT NULL REFERENCES profiles(profile_id) ON DELETE CASCADE,
  notification_type TEXT NOT NULL CHECK (notification_type IN (
    'price_alert', 'research_ready', 'scheduler_result', 'system'
  )),
  title TEXT NOT NULL,
  body TEXT NOT NULL,
  metadata TEXT,
  read_at TIMESTAMP,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_notifications_profile_unread
  ON notifications(profile_id, read_at, created_at DESC);
"""
