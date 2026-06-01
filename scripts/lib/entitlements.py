from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timezone
from typing import Any


RESEARCH_UNLOCK_TYPES = {"subscriber", "ad_unlocked", "admin"}


class WebhookSignatureError(RuntimeError):
    pass


def has_active_research_unlock(unlocks: list[dict[str, Any]], symbol: str, *, now: datetime | None = None) -> bool:
    current = now or datetime.now(timezone.utc)
    for unlock in unlocks:
        if unlock.get("status") != "active":
            continue
        if unlock.get("entitlement_type") not in RESEARCH_UNLOCK_TYPES:
            continue
        target_slug = unlock.get("target_slug")
        if target_slug not in (None, symbol):
            continue
        expires_at = unlock.get("expires_at")
        if expires_at is None or expires_at > current:
            return True
    return False


def sign_webhook_payload(body: bytes, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def verify_webhook_signature(body: bytes, signature: str | None, secret: str | None) -> None:
    if not secret:
        raise WebhookSignatureError("webhook verification is not configured")
    if not signature:
        raise WebhookSignatureError("missing webhook signature")
    expected = sign_webhook_payload(body, secret)
    if not hmac.compare_digest(signature, expected):
        raise WebhookSignatureError("invalid webhook signature")
