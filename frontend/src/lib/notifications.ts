/**
 * Notification API client — types + fetch helpers.
 */

import { apiGet, apiPost } from "@/lib/http";

// -- types ----------------------------------------------------------------

export interface NotificationItem {
  readonly notification_id: string;
  readonly notification_type: "price_alert" | "research_ready" | "scheduler_result" | "system";
  readonly title: string;
  readonly body: string;
  readonly metadata: string | null;
  readonly read_at: string | null;
  readonly created_at: string;
}

// -- API ------------------------------------------------------------------

export async function fetchNotifications(
  unreadOnly = false,
  limit = 20,
): Promise<readonly NotificationItem[]> {
  const params = new URLSearchParams();
  if (unreadOnly) params.set("unread", "true");
  params.set("limit", String(limit));
  const result = await apiGet<{ notifications: NotificationItem[] }>(`/api/notifications?${params}`);
  return result?.notifications ?? [];
}

export async function markNotificationRead(notificationId: string): Promise<boolean> {
  const result = await apiPost<{ updated: boolean }>(`/api/notifications/${notificationId}/read`);
  return result?.updated ?? false;
}

export async function markAllNotificationsRead(): Promise<number> {
  const result = await apiPost<{ updated_count: number }>("/api/notifications/read-all");
  return result?.updated_count ?? 0;
}
