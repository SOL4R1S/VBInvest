from __future__ import annotations

import re
import sqlite3
import uuid
from typing import Any

from scripts.lib.db import _profile_slug


class SQLiteIdentityMixin:
    def fetch_watchlist_assets(self, slug: str) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT a.asset_id, a.symbol, a.display_name_ko, a.exchange, a.currency
                FROM watchlists w
                JOIN watchlist_members wm ON wm.watchlist_id = w.watchlist_id
                JOIN assets a ON a.asset_id = wm.asset_id
                WHERE w.slug = ? AND w.archived_at IS NULL AND a.active = 1
                ORDER BY wm.sort_order, a.symbol
                """,
                (slug,),
            ).fetchall()
        return [
            {
                "asset_id": row["asset_id"],
                "symbol": row["symbol"],
                "display_name_ko": row["display_name_ko"],
                "exchange": row["exchange"],
                "currency": row["currency"],
            }
            for row in rows
        ]

    def fetch_profile_by_auth_user(self, auth_user_id: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT profile_id, auth_user_id, slug, name, email, auth_provider
                FROM profiles
                WHERE auth_user_id = ?
                LIMIT 1
                """,
                (auth_user_id,),
            ).fetchone()
        return None if row is None else self._profile_row(row)

    def ensure_profile_for_auth_user(self, auth_user_id: str, email: str | None) -> dict[str, Any]:
        slug = _profile_slug(auth_user_id)
        name = email.split("@", 1)[0] if email else slug
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO profiles (slug, name, auth_user_id, email, auth_provider)
                VALUES (?, ?, ?, ?, 'local')
                ON CONFLICT (auth_user_id) DO UPDATE SET
                  email = COALESCE(profiles.email, excluded.email),
                  updated_at = CURRENT_TIMESTAMP
                """,
                (slug, name, auth_user_id, email),
            )
            row = conn.execute(
                "SELECT profile_id, auth_user_id, slug, name, email, auth_provider FROM profiles WHERE auth_user_id = ?",
                (auth_user_id,),
            ).fetchone()
        if row is None:
            raise LookupError("profile not found")
        return self._profile_row(row)

    def list_user_watchlists(self, auth_user_id: str) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT w.watchlist_id, w.name_ko, w.slug
                FROM watchlists w
                JOIN profiles p ON p.profile_id = w.owner_profile_id
                WHERE p.auth_user_id = ? AND w.archived_at IS NULL
                ORDER BY w.sort_order, w.watchlist_id
                """,
                (auth_user_id,),
            ).fetchall()
            return [self._watchlist_row(conn, row) for row in rows]

    def create_user_watchlist(self, auth_user_id: str, name: str, symbols: list[str]) -> dict[str, Any]:
        with self.connect() as conn:
            profile_id = self._ensure_profile(conn, auth_user_id)
            slug = self._watchlist_slug(auth_user_id, name)
            conn.execute(
                """
                INSERT INTO watchlists (slug, name_ko, parent_type, sort_order, owner_profile_id, visibility)
                VALUES (?, ?, 'global', 0, ?, 'private')
                ON CONFLICT (slug) DO UPDATE SET
                  name_ko = excluded.name_ko,
                  owner_profile_id = excluded.owner_profile_id,
                  archived_at = NULL,
                  updated_at = CURRENT_TIMESTAMP
                """,
                (slug, name, profile_id),
            )
            watchlist_row = conn.execute("SELECT watchlist_id, name_ko, slug FROM watchlists WHERE slug = ?", (slug,)).fetchone()
            if watchlist_row is None:
                raise LookupError("watchlist not created")
            watchlist_id = int(watchlist_row["watchlist_id"])
            conn.execute("DELETE FROM watchlist_members WHERE watchlist_id = ?", (watchlist_id,))
            clean_symbols = [symbol.strip().upper() for symbol in symbols if symbol.strip()]
            for index, symbol in enumerate(clean_symbols, start=1):
                asset_id = self._ensure_asset(conn, symbol)
                conn.execute(
                    """
                    INSERT INTO watchlist_members (watchlist_id, asset_id, sort_order)
                    VALUES (?, ?, ?)
                    ON CONFLICT (watchlist_id, asset_id) DO UPDATE SET sort_order = excluded.sort_order
                    """,
                    (watchlist_id, asset_id, index),
                )
        return {"watchlist_id": str(watchlist_row["watchlist_id"]), "name": watchlist_row["name_ko"], "slug": watchlist_row["slug"], "symbols": clean_symbols}

    def get_user_watchlist(self, auth_user_id: str, watchlist_id: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT w.watchlist_id, w.name_ko, w.slug
                FROM watchlists w
                JOIN profiles p ON p.profile_id = w.owner_profile_id
                WHERE p.auth_user_id = ? AND CAST(w.watchlist_id AS TEXT) = ? AND w.archived_at IS NULL
                LIMIT 1
                """,
                (auth_user_id, watchlist_id),
            ).fetchone()
            return None if row is None else self._watchlist_row(conn, row)

    def add_user_watchlist_asset(self, auth_user_id: str, watchlist_id: str, symbol: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            owned_watchlist_id = self._owned_watchlist_id(conn, auth_user_id, watchlist_id)
            if owned_watchlist_id is None:
                return None
            asset_id = self._ensure_asset(conn, symbol.strip().upper())
            sort_order_row = conn.execute(
                "SELECT COALESCE(MAX(sort_order), 0) + 1 FROM watchlist_members WHERE watchlist_id = ?",
                (owned_watchlist_id,),
            ).fetchone()
            sort_order = 1 if sort_order_row is None else int(sort_order_row[0])
            conn.execute(
                "INSERT INTO watchlist_members (watchlist_id, asset_id, sort_order) VALUES (?, ?, ?) ON CONFLICT (watchlist_id, asset_id) DO NOTHING",
                (owned_watchlist_id, asset_id, sort_order),
            )
        return self.get_user_watchlist(auth_user_id, watchlist_id)

    def remove_user_watchlist_asset(self, auth_user_id: str, watchlist_id: str, symbol: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            owned_watchlist_id = self._owned_watchlist_id(conn, auth_user_id, watchlist_id)
            if owned_watchlist_id is None:
                return None
            conn.execute(
                "DELETE FROM watchlist_members WHERE watchlist_id = ? AND asset_id IN (SELECT asset_id FROM assets WHERE symbol = ?)",
                (owned_watchlist_id, symbol.strip().upper()),
            )
        return self.get_user_watchlist(auth_user_id, watchlist_id)

    def _profile_row(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "profile_id": row["profile_id"],
            "auth_user_id": row["auth_user_id"],
            "slug": row["slug"],
            "name": row["name"],
            "email": row["email"],
            "auth_provider": row["auth_provider"],
        }

    def _watchlist_row(self, conn: sqlite3.Connection, row: sqlite3.Row) -> dict[str, Any]:
        symbols = [
            item["symbol"]
            for item in conn.execute(
                """
                SELECT a.symbol
                FROM watchlist_members wm
                JOIN assets a ON a.asset_id = wm.asset_id
                WHERE wm.watchlist_id = ?
                ORDER BY wm.sort_order, a.symbol
                """,
                (row["watchlist_id"],),
            ).fetchall()
        ]
        return {"watchlist_id": str(row["watchlist_id"]), "name": row["name_ko"], "slug": row["slug"], "symbols": symbols}

    def _ensure_profile(self, conn: sqlite3.Connection, auth_user_id: str) -> int:
        slug = _profile_slug(auth_user_id)
        conn.execute(
            "INSERT INTO profiles (slug, name, auth_user_id, auth_provider) VALUES (?, ?, ?, 'local') ON CONFLICT (auth_user_id) DO UPDATE SET updated_at = CURRENT_TIMESTAMP",
            (slug, slug, auth_user_id),
        )
        row = conn.execute("SELECT profile_id FROM profiles WHERE auth_user_id = ?", (auth_user_id,)).fetchone()
        if row is None:
            raise LookupError("profile not found")
        return int(row["profile_id"])

    def _ensure_asset(self, conn: sqlite3.Connection, symbol: str) -> int:
        normalized = symbol.strip().upper()
        conn.execute("INSERT INTO assets (symbol) VALUES (?) ON CONFLICT (symbol) DO UPDATE SET updated_at = CURRENT_TIMESTAMP", (normalized,))
        row = conn.execute("SELECT asset_id FROM assets WHERE symbol = ?", (normalized,)).fetchone()
        if row is None:
            raise LookupError(f"asset not found: {normalized}")
        return int(row["asset_id"])

    def _watchlist_slug(self, auth_user_id: str, name: str) -> str:
        base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "watchlist"
        digest = uuid.uuid5(uuid.NAMESPACE_URL, auth_user_id).hex[:12]
        return f"{digest}-{base}"

    def _owned_watchlist_id(self, conn: sqlite3.Connection, auth_user_id: str, watchlist_id: str) -> int | None:
        row = conn.execute(
            """
            SELECT w.watchlist_id
            FROM watchlists w
            JOIN profiles p ON p.profile_id = w.owner_profile_id
            WHERE p.auth_user_id = ? AND CAST(w.watchlist_id AS TEXT) = ? AND w.archived_at IS NULL
            LIMIT 1
            """,
            (auth_user_id, watchlist_id),
        ).fetchone()
        return None if row is None else int(row["watchlist_id"])
