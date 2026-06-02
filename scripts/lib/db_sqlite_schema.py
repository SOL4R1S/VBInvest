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
"""
