-- 008: Alert rules — user-configurable price alert conditions
-- Phase B: 알림 설정 UI

CREATE TABLE IF NOT EXISTS alert_rules (
  rule_id TEXT PRIMARY KEY,
  profile_id INTEGER NOT NULL REFERENCES profiles(profile_id) ON DELETE CASCADE,
  symbol TEXT NOT NULL,
  condition TEXT NOT NULL CHECK (condition IN ('above', 'below', 'change_pct')),
  threshold REAL NOT NULL,
  enabled BOOLEAN NOT NULL DEFAULT TRUE,
  last_triggered_at TIMESTAMP,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (profile_id, symbol, condition, threshold)
);

CREATE INDEX IF NOT EXISTS idx_alert_rules_profile
  ON alert_rules(profile_id, enabled);
