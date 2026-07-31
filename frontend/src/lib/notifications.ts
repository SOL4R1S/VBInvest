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

// -- parse helpers --------------------------------------------------------

function parseNotifications(payload: unknown): readonly NotificationItem[] | null {
  if (typeof payload !== "object" || payload === null) return null;
  const obj = payload as Record<string, unknown>;
  if (!Array.isArray(obj.notifications)) return null;
  return obj.notifications as NotificationItem[];
}

function parseUpdated(payload: unknown): boolean | null {
  if (typeof payload !== "object" || payload === null) return null;
  const obj = payload as Record<string, unknown>;
  return typeof obj.updated === "boolean" ? obj.updated : null;
}

function parseUpdatedCount(payload: unknown): number | null {
  if (typeof payload !== "object" || payload === null) return null;
  const obj = payload as Record<string, unknown>;
  return typeof obj.updated_count === "number" ? obj.updated_count : null;
}

// -- API ------------------------------------------------------------------

export async function fetchNotifications(
  unreadOnly = false,
  limit = 20,
): Promise<readonly NotificationItem[]> {
  const params = new URLSearchParams();
  if (unreadOnly) params.set("unread", "true");
  params.set("limit", String(limit));
  const result = await apiGet(`/api/notifications?${params}`, parseNotifications);
  return result ?? [];
}

export async function markNotificationRead(notificationId: string): Promise<boolean> {
  const result = await apiPost(`/api/notifications/${notificationId}/read`, {}, parseUpdated);
  return result ?? false;
}

export async function markAllNotificationsRead(): Promise<number> {
  const result = await apiPost("/api/notifications/read-all", {}, parseUpdatedCount);
  return result ?? 0;
}
