"""SQLiteNotificationsMixin — notifications CRUD."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from scripts.lib.db_mixin_base import DBMixinBase


class SQLiteNotificationsMixin(DBMixinBase):
    """notifications table CRUD."""

    def list_notifications(
        self,
        auth_user_id: str,
        *,
        unread_only: bool = False,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        query = """
            SELECT n.notification_id, n.notification_type, n.title, n.body,
                   n.metadata, n.read_at, n.created_at
            FROM notifications n
            JOIN profiles p ON p.profile_id = n.profile_id
            WHERE p.auth_user_id = ?
        """
        params: list[Any] = [auth_user_id]
        if unread_only:
            query += " AND n.read_at IS NULL"
        query += " ORDER BY n.created_at DESC LIMIT ?"
        params.append(limit)
        with self.connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [
            {
                "notification_id": row["notification_id"],
                "notification_type": row["notification_type"],
                "title": row["title"],
                "body": row["body"],
                "metadata": row["metadata"],
                "read_at": row["read_at"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def create_notification(
        self,
        auth_user_id: str,
        notification_type: str,
        title: str,
        body: str,
        metadata: str | None = None,
    ) -> dict[str, Any]:
        notification_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()
        with self.connect() as conn:
            profile_row = conn.execute(
                "SELECT profile_id FROM profiles WHERE auth_user_id = ?",
                (auth_user_id,),
            ).fetchone()
            if profile_row is None:
                raise ValueError(f"unknown auth_user_id: {auth_user_id}")
            profile_id = profile_row["profile_id"]
            conn.execute(
                """
                INSERT INTO notifications
                  (notification_id, profile_id, notification_type, title, body, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (notification_id, profile_id, notification_type, title, body, metadata, now),
            )
        return {
            "notification_id": notification_id,
            "notification_type": notification_type,
            "title": title,
            "body": body,
            "metadata": metadata,
            "read_at": None,
            "created_at": now,
        }

    def mark_notification_read(self, auth_user_id: str, notification_id: str) -> bool:
        now = datetime.now(UTC).isoformat()
        with self.connect() as conn:
            cursor = conn.execute(
                """
                UPDATE notifications
                SET read_at = ?
                WHERE notification_id = ?
                  AND profile_id IN (SELECT profile_id FROM profiles WHERE auth_user_id = ?)
                  AND read_at IS NULL
                """,
                (now, notification_id, auth_user_id),
            )
            return cursor.rowcount > 0

    def mark_all_notifications_read(self, auth_user_id: str) -> int:
        now = datetime.now(UTC).isoformat()
        with self.connect() as conn:
            cursor = conn.execute(
                """
                UPDATE notifications
                SET read_at = ?
                WHERE profile_id IN (SELECT profile_id FROM profiles WHERE auth_user_id = ?)
                  AND read_at IS NULL
                """,
                (now, auth_user_id),
            )
            return cursor.rowcount
