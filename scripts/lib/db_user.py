"""VBinvestDB UserMixin — extracted from db.py."""

from __future__ import annotations

import re
from typing import Any

from scripts.lib.db_base import _profile_slug, hashlib_sha
from scripts.lib.db_mixin_base import DBMixinBase


class UserMixin(DBMixinBase):
    """Mixin — requires self.connect() from VBinvestDB."""

    def fetch_profile_by_auth_user(self, auth_user_id: str) -> dict[str, Any] | None:
        query = """
        SELECT profile_id, auth_user_id, slug, name, email, auth_provider
        FROM profiles
        WHERE auth_user_id = %s
        """
        with self.connect() as conn, conn.cursor() as cur:
            cur.execute(query, (auth_user_id,))
            row = cur.fetchone()
            if row is None:
                return None
            return {
                "profile_id": row[0],
                "auth_user_id": str(row[1]),
                "slug": row[2],
                "name": row[3],
                "email": row[4],
                "auth_provider": row[5],
            }

    def ensure_profile_for_auth_user(self, auth_user_id: str, email: str | None) -> dict[str, Any]:
        slug = _profile_slug(auth_user_id)
        name = email.split("@", 1)[0] if email else slug
        query = """
        INSERT INTO profiles (slug, name, auth_user_id, email, auth_provider)
        VALUES (%s, %s, %s, %s, 'local')
        ON CONFLICT (auth_user_id) WHERE auth_user_id IS NOT NULL DO UPDATE SET
          email = COALESCE(profiles.email, EXCLUDED.email),
          updated_at = now()
        RETURNING profile_id, auth_user_id, slug, name, email, auth_provider
        """
        with self.connect() as conn, conn.cursor() as cur:
            cur.execute(query, (slug, name, auth_user_id, email))
            row = cur.fetchone()
            return {
                "profile_id": row[0],
                "auth_user_id": str(row[1]),
                "slug": row[2],
                "name": row[3],
                "email": row[4],
                "auth_provider": row[5],
            }

    def list_user_watchlists(self, auth_user_id: str) -> list[dict[str, Any]]:
        query = """
        SELECT w.watchlist_id, w.name_ko, w.slug, COALESCE(json_agg(a.symbol ORDER BY wm.sort_order) FILTER (WHERE a.symbol IS NOT NULL), '[]'::json)
        FROM watchlists w
        JOIN profiles p ON p.profile_id = w.owner_profile_id
        LEFT JOIN watchlist_members wm ON wm.watchlist_id = w.watchlist_id
        LEFT JOIN assets a ON a.asset_id = wm.asset_id
        WHERE p.auth_user_id = %s AND w.archived_at IS NULL
        GROUP BY w.watchlist_id, w.name_ko, w.slug
        ORDER BY w.sort_order, w.watchlist_id
        """
        with self.connect() as conn, conn.cursor() as cur:
            cur.execute(query, (auth_user_id,))
            return [
                {"watchlist_id": str(row[0]), "name": row[1], "slug": row[2], "symbols": row[3] or []}
                for row in cur.fetchall()
            ]

    def create_user_watchlist(self, auth_user_id: str, name: str, symbols: list[str]) -> dict[str, Any]:
        with self.connect() as conn, conn.cursor() as cur:
            profile_id = self._ensure_profile(cur, auth_user_id)
            slug = self._watchlist_slug(auth_user_id, name)
            cur.execute(
                """
                INSERT INTO watchlists (slug, name_ko, parent_type, sort_order, owner_profile_id, visibility)
                VALUES (%s, %s, 'global', 0, %s, 'private')
                ON CONFLICT (slug) DO UPDATE SET
                  name_ko = EXCLUDED.name_ko,
                  owner_profile_id = EXCLUDED.owner_profile_id,
                  archived_at = NULL,
                  updated_at = now()
                RETURNING watchlist_id, name_ko, slug
                """,
                (slug, name, profile_id),
            )
            row = cur.fetchone()
            watchlist_id = row[0]
            cur.execute("DELETE FROM watchlist_members WHERE watchlist_id = %s", (watchlist_id,))
            clean_symbols = [symbol.strip().upper() for symbol in symbols if symbol.strip()]
            for index, symbol in enumerate(clean_symbols, start=1):
                asset_id = self._ensure_asset(cur, symbol)
                cur.execute(
                    """
                    INSERT INTO watchlist_members (watchlist_id, asset_id, sort_order)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (watchlist_id, asset_id) DO UPDATE SET sort_order = EXCLUDED.sort_order
                    """,
                    (watchlist_id, asset_id, index),
                )
            return {"watchlist_id": str(row[0]), "name": row[1], "slug": row[2], "symbols": clean_symbols}

    def get_user_watchlist(self, auth_user_id: str, watchlist_id: str) -> dict[str, Any] | None:
        query = """
        SELECT w.watchlist_id, w.name_ko, w.slug, COALESCE(json_agg(a.symbol ORDER BY wm.sort_order) FILTER (WHERE a.symbol IS NOT NULL), '[]'::json)
        FROM watchlists w
        JOIN profiles p ON p.profile_id = w.owner_profile_id
        LEFT JOIN watchlist_members wm ON wm.watchlist_id = w.watchlist_id
        LEFT JOIN assets a ON a.asset_id = wm.asset_id
        WHERE p.auth_user_id = %s AND w.watchlist_id::text = %s AND w.archived_at IS NULL
        GROUP BY w.watchlist_id, w.name_ko, w.slug
        """
        with self.connect() as conn, conn.cursor() as cur:
            cur.execute(query, (auth_user_id, watchlist_id))
            row = cur.fetchone()
            if row is None:
                return None
            return {"watchlist_id": str(row[0]), "name": row[1], "slug": row[2], "symbols": row[3] or []}

    def _ensure_profile(self, cur, auth_user_id: str) -> int:
        slug = f"user-{hashlib_sha(auth_user_id)[:12]}"
        cur.execute(
            """
            INSERT INTO profiles (slug, name, auth_user_id, auth_provider)
            VALUES (%s, %s, %s, 'local-test')
            ON CONFLICT (auth_user_id) WHERE auth_user_id IS NOT NULL DO UPDATE SET updated_at = now()
            RETURNING profile_id
            """,
            (slug, slug, auth_user_id),
        )
        return cur.fetchone()[0]

    def _ensure_asset(self, cur, symbol: str) -> int:
        cur.execute(
            """
            INSERT INTO assets (symbol, exchange, currency)
            VALUES (%s, NULL, NULL)
            ON CONFLICT (symbol) DO UPDATE SET updated_at = now()
            RETURNING asset_id
            """,
            (symbol,),
        )
        return cur.fetchone()[0]

    def _watchlist_slug(self, auth_user_id: str, name: str) -> str:
        base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "watchlist"
        return f"{hashlib_sha(auth_user_id)[:12]}-{base}"
