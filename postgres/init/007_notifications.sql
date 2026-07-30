-- 007: Notifications system
-- Phase 2-3: 알림 시스템

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
