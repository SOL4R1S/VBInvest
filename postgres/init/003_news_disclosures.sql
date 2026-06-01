CREATE TABLE IF NOT EXISTS news_items (
  news_id BIGSERIAL PRIMARY KEY,
  provider TEXT NOT NULL,
  source TEXT,
  source_id TEXT,
  url TEXT,
  canonical_url TEXT,
  title TEXT NOT NULL,
  published_at TIMESTAMPTZ,
  content_hash TEXT,
  language TEXT,
  summary TEXT,
  raw_json JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_news_provider_source_id
  ON news_items(provider, source_id)
  WHERE source_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS ux_news_canonical_url
  ON news_items(canonical_url)
  WHERE canonical_url IS NOT NULL;

CREATE TABLE IF NOT EXISTS asset_news_map (
  asset_id BIGINT NOT NULL REFERENCES assets(asset_id) ON DELETE CASCADE,
  news_id BIGINT NOT NULL REFERENCES news_items(news_id) ON DELETE CASCADE,
  relevance NUMERIC,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (asset_id, news_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_asset_news_asset_news
  ON asset_news_map(asset_id, news_id);

CREATE TABLE IF NOT EXISTS disclosures (
  disclosure_id BIGSERIAL PRIMARY KEY,
  asset_id BIGINT REFERENCES assets(asset_id) ON DELETE SET NULL,
  market TEXT,
  provider TEXT NOT NULL,
  provider_disclosure_id TEXT,
  title TEXT NOT NULL,
  published_at TIMESTAMPTZ,
  url TEXT,
  raw_json JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_disclosures_provider_id
  ON disclosures(provider, provider_disclosure_id)
  WHERE provider_disclosure_id IS NOT NULL;
