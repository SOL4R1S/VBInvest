"""PostgreSQL notification store — module-level functions matching SQLite mixin API."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from scripts.lib.db import VBinvestDB


def list_notifications(
    db: VBinvestDB,
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
    WHERE p.auth_user_id::text = %s
    """
    params: list[Any] = [auth_user_id]
    if unread_only:
        query += " AND n.read_at IS NULL"
    query += " ORDER BY n.created_at DESC LIMIT %s"
    params.append(limit)
    with db.connect() as conn, conn.cursor() as cur:
        cur.execute(query, params)
        return [
            {
                "notification_id": row[0],
                "notification_type": row[1],
                "title": row[2],
                "body": row[3],
                "metadata": row[4],
                "read_at": row[5].isoformat() if row[5] else None,
                "created_at": row[6].isoformat() if row[6] else None,
            }
            for row in cur.fetchall()
        ]


def create_notification(
    db: VBinvestDB,
    auth_user_id: str,
    notification_type: str,
    title: str,
    body: str,
    metadata: str | None = None,
) -> dict[str, Any]:
    notification_id = str(uuid.uuid4())
    now = datetime.now(UTC)
    with db.connect() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT profile_id FROM profiles WHERE auth_user_id::text = %s",
            (auth_user_id,),
        )
        row = cur.fetchone()
        if row is None:
            raise ValueError(f"unknown auth_user_id: {auth_user_id}")
        profile_id = row[0]
        cur.execute(
            """
            INSERT INTO notifications
              (notification_id, profile_id, notification_type, title, body, metadata, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
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
        "created_at": now.isoformat(),
    }


def mark_notification_read(db: VBinvestDB, auth_user_id: str, notification_id: str) -> bool:
    now = datetime.now(UTC)
    with db.connect() as conn, conn.cursor() as cur:
        cur.execute(
            """
            UPDATE notifications
            SET read_at = %s
            WHERE notification_id = %s
              AND profile_id IN (SELECT profile_id FROM profiles WHERE auth_user_id::text = %s)
              AND read_at IS NULL
            """,
            (now, notification_id, auth_user_id),
        )
        return cur.rowcount > 0


def mark_all_notifications_read(db: VBinvestDB, auth_user_id: str) -> int:
    now = datetime.now(UTC)
    with db.connect() as conn, conn.cursor() as cur:
        cur.execute(
            """
            UPDATE notifications
            SET read_at = %s
            WHERE profile_id IN (SELECT profile_id FROM profiles WHERE auth_user_id::text = %s)
              AND read_at IS NULL
            """,
            (now, auth_user_id),
        )
        return cur.rowcount
