/**
 * NotificationBell — bell icon with unread badge + dropdown panel.
 */

import { useState } from "react";

import { useNotifications } from "@/hooks/useNotifications";
import type { NotificationItem } from "@/lib/notifications";

const TYPE_LABELS: Record<NotificationItem["notification_type"], string> = {
  price_alert: "가격 알림",
  research_ready: "리서치",
  scheduler_result: "스케줄러",
  system: "시스템",
};

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return "방금";
  if (mins < 60) return `${mins}분 전`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}시간 전`;
  return `${Math.floor(hours / 24)}일 전`;
}

export function NotificationBell() {
  const { notifications, unreadCount, loading, markRead, markAllRead } = useNotifications();
  const [open, setOpen] = useState(false);

  return (
    <div className="notification-bell" style={{ position: "relative", display: "inline-block" }}>
      <button
        type="button"
        aria-label={`알림 ${unreadCount > 0 ? `${unreadCount}개 미읽음` : "모두 읽음"}`}
        onClick={() => setOpen((prev) => !prev)}
        style={{ background: "none", border: "none", cursor: "pointer", fontSize: "1.3rem", position: "relative" }}
      >
        🔔
        {unreadCount > 0 && (
          <span
            aria-hidden="true"
            style={{
              position: "absolute",
              top: -4,
              right: -6,
              background: "#e53e3e",
              color: "#fff",
              borderRadius: "50%",
              fontSize: "0.65rem",
              minWidth: 16,
              height: 16,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              padding: "0 3px",
            }}
          >
            {unreadCount > 99 ? "99+" : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div
          role="dialog"
          aria-label="알림 목록"
          style={{
            position: "absolute",
            right: 0,
            top: "100%",
            width: 320,
            maxHeight: 400,
            overflowY: "auto",
            background: "var(--color-surface, #fff)",
            border: "1px solid var(--color-border, #ddd)",
            borderRadius: 8,
            boxShadow: "0 4px 16px rgba(0,0,0,0.12)",
            zIndex: 1000,
            padding: "8px 0",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "4px 12px 8px" }}>
            <strong>알림</strong>
            {unreadCount > 0 && (
              <button
                type="button"
                onClick={() => void markAllRead()}
                style={{ background: "none", border: "none", cursor: "pointer", fontSize: "0.8rem", color: "var(--color-accent, #3182ce)" }}
              >
                모두 읽음
              </button>
            )}
          </div>

          {loading && <p style={{ padding: "8px 12px", fontSize: "0.85rem" }}>불러오는 중…</p>}

          {!loading && notifications.length === 0 && (
            <p style={{ padding: "8px 12px", fontSize: "0.85rem", color: "var(--color-muted, #888)" }}>알림이 없습니다.</p>
          )}

          <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
            {notifications.map((n) => (
              <li
                key={n.notification_id}
                style={{
                  padding: "8px 12px",
                  borderBottom: "1px solid var(--color-border, #eee)",
                  background: n.read_at === null ? "var(--color-accent-bg, #ebf8ff)" : "transparent",
                  cursor: n.read_at === null ? "pointer" : "default",
                }}
                onClick={() => {
                  if (n.read_at === null) void markRead(n.notification_id);
                }}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && n.read_at === null) void markRead(n.notification_id);
                }}
                role={n.read_at === null ? "button" : undefined}
                tabIndex={n.read_at === null ? 0 : undefined}
              >
                <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                  <span style={{ fontSize: "0.7rem", color: "var(--color-muted, #888)" }}>
                    {TYPE_LABELS[n.notification_type] ?? n.notification_type}
                  </span>
                  <span style={{ fontSize: "0.7rem", color: "var(--color-muted, #aaa)", marginLeft: "auto" }}>
                    {timeAgo(n.created_at)}
                  </span>
                </div>
                <div style={{ fontWeight: n.read_at === null ? 600 : 400, fontSize: "0.85rem" }}>{n.title}</div>
                <div style={{ fontSize: "0.8rem", color: "var(--color-muted, #666)" }}>{n.body}</div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
