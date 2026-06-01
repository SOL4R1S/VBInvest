from __future__ import annotations

import json
import uuid
from typing import Any

from scripts.lib import api_portfolio_store
from scripts.lib.db import VBinvestDB


def json_dumps(value: Any) -> str:
    return json.dumps(value if value is not None else {}, ensure_ascii=False, default=str)


class ApiStore:
    def __init__(self, db: VBinvestDB):
        self.db = db

    def fetch_profile_by_auth_user(self, auth_user_id: str) -> dict[str, Any] | None:
        query = """
        SELECT profile_id, auth_user_id::text, slug, email
        FROM profiles
        WHERE auth_user_id::text = %s
        LIMIT 1
        """
        with self.db.connect() as conn, conn.cursor() as cur:
            cur.execute(query, (auth_user_id,))
            row = cur.fetchone()
        if row is None:
            return None
        return {"profile_id": row[0], "auth_user_id": row[1], "slug": row[2], "email": row[3]}

    def list_user_watchlists(self, auth_user_id: str) -> list[dict[str, Any]]:
        query = """
        SELECT w.watchlist_id::text, w.name_ko, array_agg(a.symbol ORDER BY wm.sort_order, a.symbol)
        FROM watchlists w
        JOIN profiles p ON p.profile_id = w.owner_profile_id
        LEFT JOIN watchlist_members wm ON wm.watchlist_id = w.watchlist_id
        LEFT JOIN assets a ON a.asset_id = wm.asset_id
        WHERE p.auth_user_id::text = %s AND w.active = TRUE AND w.archived_at IS NULL
        GROUP BY w.watchlist_id, w.name_ko
        ORDER BY w.sort_order, w.name_ko
        """
        with self.db.connect() as conn, conn.cursor() as cur:
            cur.execute(query, (auth_user_id,))
            return [_watchlist_row(row) for row in cur.fetchall()]

    def create_user_watchlist(self, auth_user_id: str, name: str, symbols: list[str]) -> dict[str, Any]:
        watchlist_id = str(uuid.uuid4())
        slug = f"user-{watchlist_id}"
        with self.db.connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT profile_id FROM profiles WHERE auth_user_id::text = %s", (auth_user_id,))
            profile = cur.fetchone()
            if profile is None:
                raise LookupError("profile not found")
            cur.execute(
                """
                INSERT INTO watchlists (slug, name_ko, name_en, owner_profile_id, visibility, parent_type)
                VALUES (%s, %s, %s, %s, 'private', 'global')
                RETURNING watchlist_id::text
                """,
                (slug, name, name, profile[0]),
            )
            inserted = cur.fetchone()
            if inserted is None:
                raise LookupError("watchlist not created")
            created_id = inserted[0]
            for index, symbol in enumerate(symbols):
                cur.execute("SELECT asset_id FROM assets WHERE symbol = %s AND active = TRUE", (symbol,))
                asset = cur.fetchone()
                if asset is None:
                    raise LookupError(f"asset not found: {symbol}")
                cur.execute(
                    """
                    INSERT INTO watchlist_members (watchlist_id, asset_id, sort_order)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (watchlist_id, asset_id) DO UPDATE SET sort_order = EXCLUDED.sort_order
                    """,
                    (created_id, asset[0], index),
                )
        return self.get_user_watchlist(auth_user_id, created_id) or {
            "watchlist_id": created_id,
            "name": name,
            "symbols": symbols,
        }

    def get_user_watchlist(self, auth_user_id: str, watchlist_id: str) -> dict[str, Any] | None:
        query = """
        SELECT w.watchlist_id::text, w.name_ko, array_agg(a.symbol ORDER BY wm.sort_order, a.symbol)
        FROM watchlists w
        JOIN profiles p ON p.profile_id = w.owner_profile_id
        LEFT JOIN watchlist_members wm ON wm.watchlist_id = w.watchlist_id
        LEFT JOIN assets a ON a.asset_id = wm.asset_id
        WHERE p.auth_user_id::text = %s AND w.watchlist_id::text = %s
          AND w.active = TRUE AND w.archived_at IS NULL
        GROUP BY w.watchlist_id, w.name_ko
        """
        with self.db.connect() as conn, conn.cursor() as cur:
            cur.execute(query, (auth_user_id, watchlist_id))
            row = cur.fetchone()
        return None if row is None else _watchlist_row(row)

    def add_user_watchlist_asset(self, auth_user_id: str, watchlist_id: str, symbol: str) -> dict[str, Any] | None:
        with self.db.connect() as conn, conn.cursor() as cur:
            owner = self._owned_watchlist_id(cur, auth_user_id, watchlist_id)
            if owner is None:
                return None
            cur.execute("SELECT asset_id FROM assets WHERE symbol = %s AND active = TRUE", (symbol,))
            asset = cur.fetchone()
            if asset is None:
                raise LookupError(f"asset not found: {symbol}")
            cur.execute(
                """
                INSERT INTO watchlist_members (watchlist_id, asset_id, sort_order)
                VALUES (%s, %s, (
                  SELECT COALESCE(MAX(sort_order), 0) + 1 FROM watchlist_members WHERE watchlist_id = %s
                ))
                ON CONFLICT (watchlist_id, asset_id) DO NOTHING
                """,
                (owner, asset[0], owner),
            )
        return self.get_user_watchlist(auth_user_id, watchlist_id)

    def remove_user_watchlist_asset(self, auth_user_id: str, watchlist_id: str, symbol: str) -> dict[str, Any] | None:
        with self.db.connect() as conn, conn.cursor() as cur:
            owner = self._owned_watchlist_id(cur, auth_user_id, watchlist_id)
            if owner is None:
                return None
            cur.execute(
                """
                DELETE FROM watchlist_members wm
                USING assets a
                WHERE wm.asset_id = a.asset_id AND wm.watchlist_id = %s AND a.symbol = %s
                """,
                (owner, symbol),
            )
        return self.get_user_watchlist(auth_user_id, watchlist_id)

    def list_user_portfolio_holdings(self, auth_user_id: str) -> list[dict[str, Any]]:
        return api_portfolio_store.list_user_portfolio_holdings(self.db, auth_user_id)

    def create_user_portfolio_holding(
        self,
        auth_user_id: str,
        symbol: str,
        quantity: float,
        average_cost: float | None,
        note: str | None,
    ) -> dict[str, Any]:
        return api_portfolio_store.create_user_portfolio_holding(
            self.db,
            auth_user_id,
            symbol,
            quantity,
            average_cost,
            note,
        )

    def update_user_portfolio_holding(
        self,
        auth_user_id: str,
        holding_id: str,
        quantity: float | None,
        average_cost: float | None,
        note: str | None,
    ) -> dict[str, Any] | None:
        return api_portfolio_store.update_user_portfolio_holding(
            self.db,
            auth_user_id,
            holding_id,
            quantity,
            average_cost,
            note,
        )

    def delete_user_portfolio_holding(self, auth_user_id: str, holding_id: str) -> bool:
        return api_portfolio_store.delete_user_portfolio_holding(self.db, auth_user_id, holding_id)

    def fetch_latest_research_for_asset(self, symbol: str) -> dict[str, Any] | None:
        query = """
        SELECT target_slug, opinion, thesis, rationale, bull, base, bear, risks, triggers, sources, access_tier
        FROM research_views
        WHERE target_type = 'asset' AND horizon = 'on_demand' AND target_slug = %s
        ORDER BY report_date DESC, updated_at DESC
        LIMIT 1
        """
        with self.db.connect() as conn, conn.cursor() as cur:
            cur.execute(query, (symbol,))
            row = cur.fetchone()
        if row is None:
            return None
        return {
            "target_slug": row[0],
            "opinion": row[1],
            "thesis": row[2],
            "rationale": row[3] or [],
            "bull": row[4],
            "base": row[5],
            "bear": row[6],
            "risks": row[7] or [],
            "triggers": row[8] or [],
            "sources": row[9] or [],
            "access_tier": row[10],
        }

    def generate_research_for_asset(self, auth_user_id: str, symbol: str) -> dict[str, Any]:
        return self.db.generate_research_for_asset(auth_user_id, symbol)

    def fetch_latest_report_run(self, run_type: str, scope_slug: str | None) -> dict[str, Any] | None:
        return self.db.fetch_latest_report_run(run_type, scope_slug)

    def user_has_research_entitlement(self, auth_user_id: str, symbol: str) -> bool:
        query = """
        SELECT 1
        FROM profiles p
        JOIN entitlements e ON e.profile_id = p.profile_id
        WHERE p.auth_user_id::text = %s
          AND e.status = 'active'
          AND e.entitlement_type IN ('subscriber', 'admin')
          AND (e.expires_at IS NULL OR e.expires_at > now())
        LIMIT 1
        """
        with self.db.connect() as conn, conn.cursor() as cur:
            cur.execute(query, (auth_user_id,))
            if cur.fetchone() is not None:
                return True
            cur.execute(
                """
                SELECT 1
                FROM profiles p
                JOIN ad_unlocks a ON a.profile_id = p.profile_id
                WHERE p.auth_user_id::text = %s
                  AND a.target_type = 'asset'
                  AND a.target_slug = %s
                  AND a.unlocks_until > now()
                LIMIT 1
                """,
                (auth_user_id, symbol),
            )
            return cur.fetchone() is not None

    def grant_ad_unlock(self, auth_user_id: str, symbol: str, ad_event_id: str) -> dict[str, Any]:
        unlock_id = str(uuid.uuid4())
        with self.db.connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT profile_id FROM profiles WHERE auth_user_id::text = %s", (auth_user_id,))
            profile = cur.fetchone()
            if profile is None:
                raise LookupError("profile not found")
            cur.execute(
                """
                INSERT INTO ad_unlocks (
                  ad_unlock_id, profile_id, provider, ad_event_id, target_type, target_slug, unlocks_until
                ) VALUES (
                  %s, %s, 'mock-ad', %s, 'asset', %s, now() + interval '30 minutes'
                )
                ON CONFLICT (provider, ad_event_id) DO UPDATE SET
                  unlocks_until = GREATEST(ad_unlocks.unlocks_until, EXCLUDED.unlocks_until)
                RETURNING unlocks_until
                """,
                (unlock_id, profile[0], ad_event_id, symbol),
            )
            row = cur.fetchone()
            cur.execute(
                """
                INSERT INTO entitlements (
                  entitlement_id,
                  profile_id,
                  entitlement_type,
                  provider,
                  provider_subject_id,
                  starts_at,
                  expires_at,
                  status,
                  metadata
                )
                VALUES (%s, %s, 'ad_unlocked', 'mock-ad', %s, now(), %s, 'active', %s::jsonb)
                ON CONFLICT DO NOTHING
                """,
                (
                    str(uuid.uuid4()),
                    profile[0],
                    ad_event_id,
                    row[0],
                    json_dumps({"symbol": symbol, "ad_event_id": ad_event_id}),
                ),
            )
        return {"auth_user_id": auth_user_id, "entitlement_state": "ad_unlocked", "target_slug": symbol, "expires_at": row[0]}

    def grant_subscription_entitlement(
        self,
        auth_user_id: str,
        provider: str,
        provider_subject_id: str,
    ) -> dict[str, Any]:
        with self.db.connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT profile_id FROM profiles WHERE auth_user_id::text = %s", (auth_user_id,))
            profile = cur.fetchone()
            if profile is None:
                raise LookupError("profile not found")
            cur.execute(
                """
                INSERT INTO entitlements (
                  entitlement_id,
                  profile_id,
                  entitlement_type,
                  provider,
                  provider_subject_id,
                  starts_at,
                  expires_at,
                  status,
                  metadata
                )
                VALUES (%s, %s, 'subscriber', %s, %s, now(), NULL, 'active', %s::jsonb)
                ON CONFLICT DO NOTHING
                RETURNING starts_at
                """,
                (
                    str(uuid.uuid4()),
                    profile[0],
                    provider,
                    provider_subject_id,
                    json_dumps({"provider_subject_id": provider_subject_id}),
                ),
            )
            cur.fetchone()
        return {
            "auth_user_id": auth_user_id,
            "entitlement_state": "subscriber",
            "target_slug": None,
            "expires_at": None,
        }

    def record_payment_webhook(
        self,
        event_id: str,
        provider: str,
        event_type: str,
        payload: dict[str, Any],
        signature_valid: bool,
    ) -> dict[str, Any]:
        with self.db.connect() as conn, conn.cursor() as cur:
            profile_id = None
            auth_user_id = payload.get("auth_user_id")
            if isinstance(auth_user_id, str) and auth_user_id:
                cur.execute("SELECT profile_id FROM profiles WHERE auth_user_id::text = %s", (auth_user_id,))
                profile = cur.fetchone()
                profile_id = None if profile is None else profile[0]
            cur.execute(
                """
                INSERT INTO payment_webhook_events (
                  event_id, provider, event_type, profile_id, status, signature_valid, raw_json
                ) VALUES (%s, %s, %s, %s, 'received', %s, %s::jsonb)
                ON CONFLICT (provider, event_id) DO NOTHING
                RETURNING event_id
                """,
                (event_id, provider, event_type, profile_id, signature_valid, json_dumps(payload)),
            )
            inserted = cur.fetchone()
            if inserted is None:
                return {"status": "ignored", "duplicate": True}
            cur.execute(
                """
                UPDATE payment_webhook_events
                SET status = 'processed', processed_at = now()
                WHERE provider = %s AND event_id = %s
                """,
                (provider, event_id),
            )
        return {"status": "processed", "duplicate": False}

    def _owned_watchlist_id(self, cur: Any, auth_user_id: str, watchlist_id: str) -> str | None:
        cur.execute(
            """
            SELECT w.watchlist_id::text
            FROM watchlists w
            JOIN profiles p ON p.profile_id = w.owner_profile_id
            WHERE p.auth_user_id::text = %s AND w.watchlist_id::text = %s
            """,
            (auth_user_id, watchlist_id),
        )
        row = cur.fetchone()
        return None if row is None else row[0]

def _watchlist_row(row: tuple[Any, ...]) -> dict[str, Any]:
    symbols = [symbol for symbol in (row[2] or []) if symbol is not None]
    return {"watchlist_id": row[0], "name": row[1], "symbols": symbols}
