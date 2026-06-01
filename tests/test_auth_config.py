import time

import pytest

from scripts.lib.auth import AuthError, LOCAL_TEST_JWT_SECRET, _encode_hs256, create_test_token, verify_bearer_token


def test_local_auth_mode_allows_default_test_secret():
    token = create_test_token("local-user", email="local@example.com")

    user = verify_bearer_token(token, {"VBINVEST_AUTH_MODE": "local"})

    assert user.auth_user_id == "local-user"
    assert user.email == "local@example.com"


def test_production_auth_mode_uses_supabase_jwt_secret():
    secret = "prod-test-secret-not-real"
    token = _encode_hs256(
        {
            "sub": "prod-user",
            "email": "prod@example.com",
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
        },
        secret,
    )

    user = verify_bearer_token(
        token,
        {
            "VBINVEST_AUTH_MODE": "production",
            "SUPABASE_JWT_SECRET": secret,
        },
    )

    assert user.auth_user_id == "prod-user"
    assert user.email == "prod@example.com"


def test_production_auth_mode_rejects_local_test_secret():
    token = create_test_token("prod-user")

    with pytest.raises(AuthError, match="local jwt secret"):
        verify_bearer_token(
            token,
            {
                "VBINVEST_AUTH_MODE": "production",
                "SUPABASE_JWT_SECRET": LOCAL_TEST_JWT_SECRET,
            },
        )


def test_node_production_rejects_implicit_local_test_secret():
    token = create_test_token("prod-user")

    with pytest.raises(AuthError, match="local jwt secret"):
        verify_bearer_token(token, {"NODE_ENV": "production"})
