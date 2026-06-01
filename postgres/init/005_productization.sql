ALTER TABLE profiles
  ADD COLUMN IF NOT EXISTS auth_user_id UUID,
  ADD COLUMN IF NOT EXISTS email TEXT,
  ADD COLUMN IF NOT EXISTS avatar_url TEXT,
  ADD COLUMN IF NOT EXISTS auth_provider TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS ux_profiles_auth_user_id
  ON profiles(auth_user_id)
  WHERE auth_user_id IS NOT NULL;

ALTER TABLE watchlists
  ADD COLUMN IF NOT EXISTS owner_profile_id BIGINT REFERENCES profiles(profile_id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS visibility TEXT NOT NULL DEFAULT 'private'
    CHECK (visibility IN ('private', 'shared', 'public')),
  ADD COLUMN IF NOT EXISTS archived_at TIMESTAMPTZ;

UPDATE watchlists w
SET owner_profile_id = p.profile_id
FROM profiles p
WHERE w.owner_profile_id IS NULL
  AND p.slug = COALESCE(w.owner_profile, 'default');

CREATE INDEX IF NOT EXISTS idx_watchlists_owner_profile_id
  ON watchlists(owner_profile_id, active, sort_order);

ALTER TABLE daily_prices
  ADD COLUMN IF NOT EXISTS adj_close NUMERIC,
  ADD COLUMN IF NOT EXISTS currency TEXT,
  ADD COLUMN IF NOT EXISTS provider TEXT,
  ADD COLUMN IF NOT EXISTS fetched_at TIMESTAMPTZ NOT NULL DEFAULT now();

UPDATE daily_prices
SET provider = COALESCE(provider, source)
WHERE provider IS NULL;

CREATE INDEX IF NOT EXISTS idx_daily_prices_provider_date
  ON daily_prices(provider, date DESC);

CREATE TABLE IF NOT EXISTS data_providers (
  provider_slug TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  provider_type TEXT NOT NULL CHECK (provider_type IN ('price', 'news', 'disclosure', 'ai', 'payment', 'ad')),
  enabled BOOLEAN NOT NULL DEFAULT TRUE,
  requires_secret BOOLEAN NOT NULL DEFAULT FALSE,
  base_url TEXT,
  notes TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS market_calendars (
  market TEXT NOT NULL,
  trade_date DATE NOT NULL,
  is_open BOOLEAN NOT NULL DEFAULT TRUE,
  close_time_kst TIME,
  source TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (market, trade_date)
);

DROP INDEX IF EXISTS ux_asset_news_content_hash;

CREATE UNIQUE INDEX IF NOT EXISTS ux_news_provider_content_hash
  ON news_items(provider, content_hash)
  WHERE content_hash IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_news_published_at
  ON news_items(published_at DESC);

CREATE TABLE IF NOT EXISTS asset_disclosure_map (
  asset_id BIGINT NOT NULL REFERENCES assets(asset_id) ON DELETE CASCADE,
  disclosure_id BIGINT NOT NULL REFERENCES disclosures(disclosure_id) ON DELETE CASCADE,
  relevance NUMERIC,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (asset_id, disclosure_id)
);

CREATE TABLE IF NOT EXISTS ai_research_runs (
  ai_run_id UUID PRIMARY KEY,
  target_type TEXT NOT NULL CHECK (target_type IN ('asset', 'sector', 'theme', 'watchlist')),
  target_slug TEXT NOT NULL,
  run_date DATE NOT NULL,
  model_provider TEXT NOT NULL,
  model_name TEXT,
  prompt_version TEXT NOT NULL,
  source_freshness_status TEXT NOT NULL DEFAULT 'unknown'
    CHECK (source_freshness_status IN ('fresh', 'stale', 'source_gap', 'unknown')),
  status TEXT NOT NULL CHECK (status IN ('ok', 'fallback', 'partial', 'failed')),
  error_message TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ai_research_runs_target_date
  ON ai_research_runs(target_type, target_slug, run_date DESC);

ALTER TABLE research_views
  ADD COLUMN IF NOT EXISTS ai_run_id UUID REFERENCES ai_research_runs(ai_run_id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS confidence NUMERIC,
  ADD COLUMN IF NOT EXISTS source_freshness_status TEXT NOT NULL DEFAULT 'unknown'
    CHECK (source_freshness_status IN ('fresh', 'stale', 'source_gap', 'unknown')),
  ADD COLUMN IF NOT EXISTS access_tier TEXT NOT NULL DEFAULT 'free'
    CHECK (access_tier IN ('free', 'paid', 'ad_unlocked'));

CREATE TABLE IF NOT EXISTS research_sources (
  source_id BIGSERIAL PRIMARY KEY,
  view_id BIGINT REFERENCES research_views(view_id) ON DELETE CASCADE,
  ai_run_id UUID REFERENCES ai_research_runs(ai_run_id) ON DELETE CASCADE,
  source_type TEXT NOT NULL CHECK (source_type IN ('price', 'indicator', 'news', 'disclosure', 'filing', 'web', 'manual')),
  provider TEXT NOT NULL,
  title TEXT,
  url TEXT,
  published_at TIMESTAMPTZ,
  fetched_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  content_hash TEXT,
  citation_label TEXT,
  raw_json JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_research_sources_view_id
  ON research_sources(view_id);

CREATE UNIQUE INDEX IF NOT EXISTS ux_research_sources_provider_hash
  ON research_sources(provider, content_hash)
  WHERE content_hash IS NOT NULL;

CREATE TABLE IF NOT EXISTS obsidian_exports (
  export_id UUID PRIMARY KEY,
  view_id BIGINT REFERENCES research_views(view_id) ON DELETE SET NULL,
  target_slug TEXT NOT NULL,
  report_date DATE NOT NULL,
  vault_path TEXT NOT NULL,
  relative_path TEXT NOT NULL,
  file_hash TEXT,
  status TEXT NOT NULL CHECK (status IN ('ok', 'skipped', 'failed')),
  error_message TEXT,
  exported_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (target_slug, report_date, relative_path)
);

CREATE TABLE IF NOT EXISTS entitlements (
  entitlement_id UUID PRIMARY KEY,
  profile_id BIGINT NOT NULL REFERENCES profiles(profile_id) ON DELETE CASCADE,
  entitlement_type TEXT NOT NULL CHECK (entitlement_type IN ('free', 'subscriber', 'ad_unlocked', 'admin')),
  provider TEXT NOT NULL DEFAULT 'local',
  provider_subject_id TEXT,
  starts_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at TIMESTAMPTZ,
  status TEXT NOT NULL DEFAULT 'active'
    CHECK (status IN ('active', 'expired', 'cancelled', 'revoked')),
  metadata JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_entitlements_profile_status
  ON entitlements(profile_id, status, expires_at);

CREATE TABLE IF NOT EXISTS portfolio_holdings (
  holding_id UUID PRIMARY KEY,
  profile_id BIGINT NOT NULL REFERENCES profiles(profile_id) ON DELETE CASCADE,
  asset_id BIGINT NOT NULL REFERENCES assets(asset_id) ON DELETE CASCADE,
  quantity NUMERIC NOT NULL CHECK (quantity > 0),
  average_cost NUMERIC CHECK (average_cost IS NULL OR average_cost >= 0),
  note TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (profile_id, asset_id)
);

CREATE INDEX IF NOT EXISTS idx_portfolio_holdings_profile_id
  ON portfolio_holdings(profile_id);

CREATE TABLE IF NOT EXISTS ad_unlocks (
  ad_unlock_id UUID PRIMARY KEY,
  profile_id BIGINT NOT NULL REFERENCES profiles(profile_id) ON DELETE CASCADE,
  provider TEXT NOT NULL,
  ad_event_id TEXT NOT NULL,
  target_type TEXT NOT NULL CHECK (target_type IN ('asset', 'sector', 'theme', 'watchlist')),
  target_slug TEXT NOT NULL,
  unlocks_until TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (provider, ad_event_id)
);

CREATE INDEX IF NOT EXISTS idx_ad_unlocks_profile_target
  ON ad_unlocks(profile_id, target_type, target_slug, unlocks_until DESC);

CREATE TABLE IF NOT EXISTS payment_webhook_events (
  event_id TEXT NOT NULL,
  provider TEXT NOT NULL,
  event_type TEXT NOT NULL,
  profile_id BIGINT REFERENCES profiles(profile_id) ON DELETE SET NULL,
  received_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  processed_at TIMESTAMPTZ,
  status TEXT NOT NULL CHECK (status IN ('received', 'processed', 'ignored', 'failed')),
  signature_valid BOOLEAN NOT NULL DEFAULT FALSE,
  raw_json JSONB,
  error_message TEXT,
  PRIMARY KEY (provider, event_id)
);

CREATE TABLE IF NOT EXISTS job_locks (
  lock_name TEXT PRIMARY KEY,
  holder TEXT NOT NULL,
  acquired_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at TIMESTAMPTZ NOT NULL,
  metadata JSONB
);

CREATE TABLE IF NOT EXISTS audit_logs (
  audit_id BIGSERIAL PRIMARY KEY,
  actor_profile_id BIGINT REFERENCES profiles(profile_id) ON DELETE SET NULL,
  action TEXT NOT NULL,
  target_type TEXT,
  target_id TEXT,
  metadata JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_actor_created
  ON audit_logs(actor_profile_id, created_at DESC);
