/**
 * useNotifications — notification polling + browser Notification API.
 */

import { useCallback, useEffect, useRef, useState } from "react";

import {
  fetchNotifications,
  markAllNotificationsRead,
  markNotificationRead,
  type NotificationItem,
} from "@/lib/notifications";

const POLL_INTERVAL_MS = 60_000;

export function useNotifications() {
  const [notifications, setNotifications] = useState<readonly NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const seenIds = useRef<Set<string>>(new Set());

  const refresh = useCallback(async () => {
    try {
      const items = await fetchNotifications(false, 50);
      setNotifications(items);
      setUnreadCount(items.filter((n) => n.read_at === null).length);

      // Browser Notification API for new unread items
      const newUnread = items.filter((n) => n.read_at === null && !seenIds.current.has(n.notification_id));
      if (newUnread.length > 0 && typeof Notification !== "undefined" && Notification.permission === "granted") {
        for (const n of newUnread.slice(0, 3)) {
          new Notification(n.title, { body: n.body });
        }
      }
      for (const n of items) {
        seenIds.current.add(n.notification_id);
      }
    } catch {
      // Silently ignore fetch failures (e.g. e2e, offline) — polling will retry
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    void refresh();
    // Request browser notification permission
    if (typeof Notification !== "undefined" && Notification.permission === "default") {
      void Notification.requestPermission();
    }
    const timer = setInterval(() => void refresh(), POLL_INTERVAL_MS);
    return () => clearInterval(timer);
  }, [refresh]);

  const markRead = useCallback(
    async (notificationId: string) => {
      await markNotificationRead(notificationId);
      await refresh();
    },
    [refresh],
  );

  const markAllRead = useCallback(async () => {
    await markAllNotificationsRead();
    await refresh();
  }, [refresh]);

  return { notifications, unreadCount, loading, refresh, markRead, markAllRead };
}
