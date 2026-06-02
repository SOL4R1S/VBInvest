from fastapi.testclient import TestClient

from scripts import api
from scripts.lib.auth import create_test_token


class BootstrapDB:
    def __init__(self):
        self.profiles = {}
        self.created = []

    def fetch_profile_by_auth_user(self, auth_user_id: str):
        return self.profiles.get(auth_user_id)

    def ensure_profile_for_auth_user(self, auth_user_id: str, email: str | None):
        profile = {
            "profile_id": f"profile-{len(self.profiles) + 1}",
            "auth_user_id": auth_user_id,
            "slug": auth_user_id,
            "email": email,
            "auth_provider": "local",
        }
        self.profiles[auth_user_id] = profile
        self.created.append(profile)
        return profile


def client_with_db(monkeypatch, fake_db: BootstrapDB):
    monkeypatch.setattr(api, "db", lambda: fake_db)
    return TestClient(api.app)


def test_first_login_bootstraps_profile(monkeypatch):
    fake_db = BootstrapDB()
    client = client_with_db(monkeypatch, fake_db)
    token = create_test_token("local-user", email="local@example.com")

    response = client.get("/api/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["profile"]["auth_user_id"] == "local-user"
    assert response.json()["profile"]["auth_provider"] == "local"
    assert fake_db.created[0]["email"] == "local@example.com"


def test_local_session_without_email_bootstraps_profile(monkeypatch):
    fake_db = BootstrapDB()
    client = client_with_db(monkeypatch, fake_db)
    token = create_test_token("local-user-without-email")

    response = client.get("/api/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["profile"]["auth_user_id"] == "local-user-without-email"
    assert response.json()["profile"]["email"] is None
