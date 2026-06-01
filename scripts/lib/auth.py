from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass
from typing import Final


LOCAL_TEST_JWT_SECRET: Final = "vbinvest-local-test-jwt-secret"


class AuthError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class AuthUser:
    auth_user_id: str
    email: str | None = None


AuthClaims = AuthUser


def create_test_token(auth_user_id: str, *, email: str | None = None) -> str:
    payload: dict[str, str | int] = {
        "sub": auth_user_id,
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,
    }
    if email is not None:
        payload["email"] = email
    return _encode_hs256(payload, LOCAL_TEST_JWT_SECRET)


def verify_bearer_token(token: str, env: dict[str, str] | None = None) -> AuthUser:
    auth_env = os.environ if env is None else env
    mode = auth_env.get("VBINVEST_AUTH_MODE", "local")
    secret = auth_env.get("SUPABASE_JWT_SECRET") or auth_env.get("VBINVEST_JWT_SECRET")
    if secret is None and mode == "local":
        secret = LOCAL_TEST_JWT_SECRET
    if secret == LOCAL_TEST_JWT_SECRET and mode != "local":
        raise AuthError("local jwt secret is not allowed outside local auth mode")
    if secret == LOCAL_TEST_JWT_SECRET and auth_env.get("NODE_ENV") == "production":
        raise AuthError("local jwt secret is not allowed in production")
    if not secret:
        raise AuthError("jwt verification is not configured")

    payload = _decode_hs256(token, secret)
    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject:
        raise AuthError("jwt subject is missing")
    email = payload.get("email")
    if email is not None and not isinstance(email, str):
        raise AuthError("jwt email is invalid")
    return AuthUser(auth_user_id=subject, email=email)


def _encode_hs256(payload: dict[str, str | int], secret: str) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    signing_input = ".".join(
        [
            _b64url_json(header),
            _b64url_json(payload),
        ]
    )
    signature = hmac.new(secret.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256).digest()
    return f"{signing_input}.{_b64url_bytes(signature)}"


def _decode_hs256(token: str, secret: str) -> dict[str, str | int]:
    parts = token.split(".")
    if len(parts) != 3:
        raise AuthError("jwt format is invalid")
    header = _decode_json(parts[0])
    if header.get("alg") != "HS256":
        raise AuthError("jwt algorithm is unsupported")
    signing_input = f"{parts[0]}.{parts[1]}"
    expected = hmac.new(secret.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256).digest()
    actual = _b64url_decode(parts[2])
    if not hmac.compare_digest(actual, expected):
        raise AuthError("jwt signature is invalid")
    payload = _decode_json(parts[1])
    exp = payload.get("exp")
    if isinstance(exp, int) and exp < int(time.time()):
        raise AuthError("jwt is expired")
    return payload


def _b64url_json(value: dict[str, str | int]) -> str:
    return _b64url_bytes(json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8"))


def _b64url_bytes(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    try:
        return base64.urlsafe_b64decode(value + padding)
    except binascii.Error as exc:
        raise AuthError("jwt base64 is invalid") from exc


def _decode_json(value: str) -> dict[str, str | int]:
    try:
        decoded = json.loads(_b64url_decode(value).decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise AuthError("jwt json is invalid") from exc
    if not isinstance(decoded, dict):
        raise AuthError("jwt json is invalid")
    payload: dict[str, str | int] = {}
    for key, item in decoded.items():
        if isinstance(key, str) and isinstance(item, (str, int)):
            payload[key] = item
    return payload
