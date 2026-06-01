CREATE TABLE IF NOT EXISTS profiles (
  profile_id BIGSERIAL PRIMARY KEY,
  slug TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO profiles (slug, name)
VALUES ('default', 'Default')
ON CONFLICT (slug) DO UPDATE SET name = EXCLUDED.name, updated_at = now();

ALTER TABLE watchlists
  ADD COLUMN IF NOT EXISTS owner_profile TEXT DEFAULT 'default';

CREATE TABLE IF NOT EXISTS watchlist_indicator_settings (
  watchlist_id BIGINT NOT NULL REFERENCES watchlists(watchlist_id) ON DELETE CASCADE,
  profile_id BIGINT NOT NULL REFERENCES profiles(profile_id) ON DELETE CASCADE,
  ma_periods INT[] NOT NULL DEFAULT ARRAY[5,20,50,120],
  rsi_period INT NOT NULL DEFAULT 14,
  chart_type TEXT NOT NULL DEFAULT 'line' CHECK (chart_type IN ('line', 'candle', 'both')),
  default_time_range TEXT NOT NULL DEFAULT '1y',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (watchlist_id, profile_id)
);

INSERT INTO watchlist_indicator_settings (watchlist_id, profile_id)
SELECT w.watchlist_id, p.profile_id
FROM watchlists w CROSS JOIN profiles p
WHERE w.slug = 'semiconductor-core' AND p.slug = 'default'
ON CONFLICT (watchlist_id, profile_id) DO UPDATE SET
  ma_periods = EXCLUDED.ma_periods,
  rsi_period = EXCLUDED.rsi_period,
  chart_type = EXCLUDED.chart_type,
  default_time_range = EXCLUDED.default_time_range,
  updated_at = now();
