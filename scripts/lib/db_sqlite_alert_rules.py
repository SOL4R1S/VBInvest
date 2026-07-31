"""SQLiteAlertRulesMixin — alert_rules CRUD."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from scripts.lib.db_mixin_base import DBMixinBase


class SQLiteAlertRulesMixin(DBMixinBase):
    """alert_rules table CRUD."""

    def list_alert_rules(
        self,
        auth_user_id: str,
        *,
        enabled_only: bool = False,
    ) -> list[dict[str, Any]]:
        query = """
            SELECT r.rule_id, r.symbol, r.condition, r.threshold,
                   r.enabled, r.last_triggered_at, r.created_at
            FROM alert_rules r
            JOIN profiles p ON p.profile_id = r.profile_id
            WHERE p.auth_user_id = ?
        """
        params: list[Any] = [auth_user_id]
        if enabled_only:
            query += " AND r.enabled = 1"
        query += " ORDER BY r.created_at DESC"
        with self.connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [
            {
                "rule_id": row["rule_id"],
                "symbol": row["symbol"],
                "condition": row["condition"],
                "threshold": row["threshold"],
                "enabled": bool(row["enabled"]),
                "last_triggered_at": row["last_triggered_at"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def create_alert_rule(
        self,
        auth_user_id: str,
        symbol: str,
        condition: str,
        threshold: float,
    ) -> dict[str, Any]:
        rule_id = str(uuid.uuid4())
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
                INSERT INTO alert_rules
                  (rule_id, profile_id, symbol, condition, threshold, enabled, created_at)
                VALUES (?, ?, ?, ?, ?, 1, ?)
                """,
                (rule_id, profile_id, symbol.upper(), condition, threshold, now),
            )
        return {
            "rule_id": rule_id,
            "symbol": symbol.upper(),
            "condition": condition,
            "threshold": threshold,
            "enabled": True,
            "last_triggered_at": None,
            "created_at": now,
        }

    def update_alert_rule(
        self,
        auth_user_id: str,
        rule_id: str,
        *,
        enabled: bool | None = None,
        threshold: float | None = None,
    ) -> bool:
        sets: list[str] = []
        params: list[Any] = []
        if enabled is not None:
            sets.append("enabled = ?")
            params.append(int(enabled))
        if threshold is not None:
            sets.append("threshold = ?")
            params.append(threshold)
        if not sets:
            return False
        params.extend([rule_id, auth_user_id])
        with self.connect() as conn:
            cursor = conn.execute(
                f"""
                UPDATE alert_rules SET {", ".join(sets)}
                WHERE rule_id = ?
                  AND profile_id IN (SELECT profile_id FROM profiles WHERE auth_user_id = ?)
                """,
                params,
            )
            return cursor.rowcount > 0

    def delete_alert_rule(self, auth_user_id: str, rule_id: str) -> bool:
        with self.connect() as conn:
            cursor = conn.execute(
                """
                DELETE FROM alert_rules
                WHERE rule_id = ?
                  AND profile_id IN (SELECT profile_id FROM profiles WHERE auth_user_id = ?)
                """,
                (rule_id, auth_user_id),
            )
            return cursor.rowcount > 0

    def touch_alert_rule_triggered(self, auth_user_id: str, rule_id: str) -> None:
        now = datetime.now(UTC).isoformat()
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE alert_rules SET last_triggered_at = ?
                WHERE rule_id = ?
                  AND profile_id IN (SELECT profile_id FROM profiles WHERE auth_user_id = ?)
                """,
                (now, rule_id, auth_user_id),
            )
