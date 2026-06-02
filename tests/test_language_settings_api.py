from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from scripts import api
from scripts.lib import config as config_lib


class FakeLanguageSettingsDB:
    def fetch_latest_report_run(self, run_type: str, scope_slug: str | None):
        return None

    def fetch_profile_by_auth_user(self, auth_user_id: str):
        return {
            "profile_id": 1,
            "auth_user_id": auth_user_id,
            "slug": "local-owner",
            "email": "owner@example.com",
        }


class FakeSecretStore:
    def __init__(self) -> None:
        self.saved: dict[str, str] = {}

    def get(self, account: str) -> str:
        return ""

    def set(self, account: str, value: str) -> None:
        self.saved[account] = value


def write_config(path: Path, *, language: str = "ko") -> None:
    path.write_text(
        "\n".join(
            [
                "first_run_completed = true",
                f'language = "{language}"',
                "[database]",
                "mode = \"sqlite\"",
                f'sqlite_path = "{path.parent / "vbinvest.sqlite3"}"',
                "[obsidian]",
                f'vault_path = "{path.parent}"',
                "export_mode = \"direct\"",
                "[providers]",
                "opendart_api_key = \"dart-secret\"",
                "ai_base_url = \"http://127.0.0.1:11434/v1\"",
                "ai_api_key = \"ai-secret\"",
            ]
        ),
        encoding="utf-8",
    )


def language_client(monkeypatch: pytest.MonkeyPatch, config_path: Path) -> TestClient:
    fake_db = FakeLanguageSettingsDB()
    fake_store = FakeSecretStore()
    monkeypatch.setenv("VBINVEST_CONFIG_PATH", str(config_path))
    monkeypatch.setenv("VBINVEST_LOCAL_SESSION_TOKEN", "local-test-token")
    monkeypatch.setattr(api, "db", lambda: fake_db)
    monkeypatch.setattr(api, "auth_db", lambda: fake_db)
    monkeypatch.setattr(config_lib, "platform_secret_store", lambda _system_name: fake_store)
    return TestClient(api.app)


def test_settings_get_exposes_persisted_language_from_config(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "config.toml"
    write_config(config_path, language="en")
    client = language_client(monkeypatch, config_path)

    response = client.get("/api/settings")

    assert response.status_code == 200
    assert response.json()["language"] == "en"
    assert "dart-secret" not in response.text
    assert "ai-secret" not in response.text


def test_settings_language_patch_requires_bearer_auth(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "config.toml"
    write_config(config_path, language="ko")
    client = language_client(monkeypatch, config_path)

    response = client.patch("/api/settings/language", json={"language": "en"})

    assert response.status_code == 401


def test_settings_language_patch_persists_language_and_redacts_secrets(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "config.toml"
    write_config(config_path, language="ko")
    client = language_client(monkeypatch, config_path)

    response = client.patch(
        "/api/settings/language",
        headers={"Authorization": "Bearer local-test-token"},
        json={"language": "en"},
    )

    assert response.status_code == 200
    assert response.json()["language"] == "en"
    assert "dart-secret" not in response.text
    assert "ai-secret" not in response.text
    assert 'language = "en"' in config_path.read_text(encoding="utf-8")

    settings = client.get("/api/settings")

    assert settings.status_code == 200
    assert settings.json()["language"] == "en"
    assert "dart-secret" not in settings.text
    assert "ai-secret" not in settings.text


def test_settings_language_patch_rejects_unsupported_language_without_mutating_config(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "config.toml"
    write_config(config_path, language="ko")
    client = language_client(monkeypatch, config_path)

    response = client.patch(
        "/api/settings/language",
        headers={"Authorization": "Bearer local-test-token"},
        json={"language": "fr"},
    )

    assert response.status_code == 422
    assert 'language = "ko"' in config_path.read_text(encoding="utf-8")
