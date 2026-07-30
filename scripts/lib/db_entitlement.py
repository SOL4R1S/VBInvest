"""VBinvestDB EntitlementMixin — extracted from db.py."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from scripts.lib.db_base import json_dumps


class EntitlementMixin:
    """Mixin — requires self.connect() from VBinvestDB."""

    def user_has_research_entitlement(self, auth_user_id: str, symbol: str) -> bool:
        query = """
        SELECT 1
        FROM profiles p
        JOIN entitlements e ON e.profile_id = p.profile_id
        WHERE p.auth_user_id = %s
          AND e.status = 'active'
          AND (e.expires_at IS NULL OR e.expires_at > now())
          AND e.entitlement_type IN ('subscriber', 'admin')
        LIMIT 1
        """
        with self.connect() as conn, conn.cursor() as cur:
            cur.execute(query, (auth_user_id,))
            if cur.fetchone() is not None:
                return True
            cur.execute(
                """
                SELECT 1
                FROM profiles p
                JOIN ad_unlocks a ON a.profile_id = p.profile_id
                WHERE p.auth_user_id = %s
                  AND a.target_type = 'asset'
                  AND a.target_slug = %s
                  AND a.unlocks_until > now()
                LIMIT 1
                """,
                (auth_user_id, symbol),
            )
            return cur.fetchone() is not None

    def grant_ad_unlock(self, auth_user_id: str, symbol: str, ad_event_id: str) -> dict[str, Any]:
        unlock_expires_at = datetime.now(UTC) + timedelta(minutes=30)
        with self.connect() as conn, conn.cursor() as cur:
            profile_id = self._ensure_profile(cur, auth_user_id)
            cur.execute(
                """
                INSERT INTO ad_unlocks (
                  ad_unlock_id,
                  profile_id,
                  provider,
                  ad_event_id,
                  target_type,
                  target_slug,
                  unlocks_until
                )
                VALUES (%s, %s, %s, %s, 'asset', %s, %s)
                ON CONFLICT (provider, ad_event_id) DO UPDATE SET
                  unlocks_until = GREATEST(ad_unlocks.unlocks_until, EXCLUDED.unlocks_until)
                RETURNING unlocks_until
                """,
                (str(uuid.uuid4()), profile_id, "local", ad_event_id, symbol, unlock_expires_at),
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
                VALUES (%s, %s, 'ad_unlocked', 'local', %s, now(), %s, 'active', %s::jsonb)
                ON CONFLICT DO NOTHING
                """,
                (
                    str(uuid.uuid4()),
                    profile_id,
                    ad_event_id,
                    unlock_expires_at,
                    json_dumps({"symbol": symbol, "ad_event_id": ad_event_id}),
                ),
            )
        return {
            "auth_user_id": auth_user_id,
            "target_slug": symbol,
            "entitlement_state": "ad_unlocked",
            "expires_at": row[0] if row else unlock_expires_at,
        }

    def grant_subscription_entitlement(
        self,
        auth_user_id: str,
        provider: str,
        provider_subject_id: str,
    ) -> dict[str, Any]:
        with self.connect() as conn, conn.cursor() as cur:
            profile_id = self._ensure_profile(cur, auth_user_id)
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
                    profile_id,
                    provider,
                    provider_subject_id,
                    json_dumps({"provider_subject_id": provider_subject_id}),
                ),
            )
            cur.fetchone()
        return {
            "auth_user_id": auth_user_id,
            "target_slug": None,
            "entitlement_state": "subscriber",
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
        with self.connect() as conn, conn.cursor() as cur:
            profile_id = None
            auth_user_id = payload.get("auth_user_id")
            if isinstance(auth_user_id, str) and auth_user_id:
                cur.execute("SELECT profile_id FROM profiles WHERE auth_user_id = %s LIMIT 1", (auth_user_id,))
                profile_row = cur.fetchone()
                profile_id = None if profile_row is None else profile_row[0]
            cur.execute(
                """
                INSERT INTO payment_webhook_events (
                  event_id,
                  provider,
                  event_type,
                  profile_id,
                  status,
                  signature_valid,
                  raw_json
                )
                VALUES (%s, %s, %s, %s, 'received', %s, %s::jsonb)
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
