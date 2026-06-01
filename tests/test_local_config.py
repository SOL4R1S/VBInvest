from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from scripts.api import app
from scripts.lib.config import ConfigError, DatabaseMode, ExportMode, load_local_config, provider_status, write_local_config


def test_missing_config_loads_safe_defaults(tmp_path: Path) -> None:
    config = load_local_config(config_path=tmp_path / "missing.toml")

    assert config.first_run_completed is False
    assert config.database.mode is DatabaseMode.SQLITE
    assert config.database.sqlite_path.name == "vbinvest.sqlite3"
    assert config.obsidian.export_mode is ExportMode.DIRECT


def test_missing_ai_provider_config_reports_disabled(tmp_path: Path) -> None:
    config = load_local_config(config_path=tmp_path / "missing.toml", environ={})

    status = provider_status(config, environ={})

    assert status["ai"]["mode"] == "disabled"
    assert status["ai"]["provider"] is None
    assert status["ai"]["error"] is None


def test_valid_config_loads_and_redacts_secrets(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        "\n".join(
            [
                "first_run_completed = true",
                "language = \"en\"",
                "[database]",
                "mode = \"postgres_url\"",
                "postgres_url = \"postgresql://vbinvest:secret@127.0.0.1:5432/vbinvest\"",
                "[obsidian]",
                f"vault_path = \"{tmp_path}\"",
                "export_mode = \"direct\"",
                "[providers]",
                "opendart_api_key = \"dart-secret\"",
                "ai_base_url = \"http://127.0.0.1:11434/v1\"",
                "ai_api_key = \"ai-secret\"",
            ]
        ),
        encoding="utf-8",
    )

    config = load_local_config(config_path=config_path)
    redacted = config.redacted()

    assert config.first_run_completed is True
    assert redacted["database"]["postgres_url"] == "postgresql://vbinvest:***@127.0.0.1:5432/vbinvest"
    assert redacted["providers"]["opendart_api_key"] == "<redacted>"
    assert redacted["providers"]["ai_api_key"] == "<redacted>"
    assert "secret" not in repr(redacted)


def test_load_config_prefers_macos_keychain_for_provider_secrets(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        "\n".join(
            [
                "[providers]",
                "opendart_api_key = \"toml-dart\"",
                "ai_base_url = \"https://api.example.com/v1\"",
                "ai_api_key = \"toml-ai\"",
            ]
        ),
        encoding="utf-8",
    )

    class FakeStore:
        def get(self, account: str) -> str:
            return {
                "OPENDART_API_KEY": "keychain-dart",
                "AI_API_KEY": "keychain-ai",
            }.get(account, "")

    config = load_local_config(config_path=config_path, environ={}, system_name="Darwin", secret_store=FakeStore())

    assert config.providers.opendart_api_key == "keychain-dart"
    assert config.providers.ai_api_key == "keychain-ai"


def test_invalid_database_mode_returns_typed_error(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text("[database]\nmode = \"mysql\"\n", encoding="utf-8")

    with pytest.raises(ConfigError, match="database.mode"):
        load_local_config(config_path=config_path)


def test_malformed_ai_provider_url_returns_typed_error(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text("[providers]\nai_base_url = \"not a url\"\n", encoding="utf-8")

    with pytest.raises(ConfigError, match="providers.ai_base_url"):
        load_local_config(config_path=config_path)


def test_write_local_config_is_atomic_and_owner_only(tmp_path: Path) -> None:
    config = load_local_config(config_path=tmp_path / "missing.toml")
    config_path = tmp_path / "config.toml"

    write_local_config(config, config_path)

    assert config_path.read_text(encoding="utf-8")
    assert config_path.stat().st_mode & 0o077 == 0


def test_write_local_config_saves_macos_provider_secrets_to_keychain_not_toml(tmp_path: Path) -> None:
    config = load_local_config(
        config_path=tmp_path / "missing.toml",
        environ={"AI_API_KEY": "ai-secret", "OPENDART_API_KEY": "dart-secret"},
        system_name="Linux",
    )
    config_path = tmp_path / "config.toml"
    saved: dict[str, str] = {}

    class FakeStore:
        def get(self, account: str) -> str:
            return ""

        def set(self, account: str, value: str) -> None:
            saved[account] = value

    write_local_config(config, config_path, system_name="Darwin", secret_store=FakeStore())

    text = config_path.read_text(encoding="utf-8")
    assert saved == {"OPENDART_API_KEY": "dart-secret", "AI_API_KEY": "ai-secret"}
    assert "dart-secret" not in text
    assert "ai-secret" not in text
    assert 'opendart_api_key = ""' in text
    assert 'ai_api_key = ""' in text


def test_write_local_config_saves_windows_provider_secrets_to_credential_manager(tmp_path: Path) -> None:
    config = load_local_config(
        config_path=tmp_path / "missing.toml",
        environ={"AI_API_KEY": "ai-secret", "OPENDART_API_KEY": "dart-secret"},
        system_name="Linux",
    )
    saved: dict[str, str] = {}

    class FakeStore:
        def get(self, account: str) -> str:
            return ""

        def set(self, account: str, value: str) -> None:
            saved[account] = value

    write_local_config(config, tmp_path / "config.toml", system_name="Windows", secret_store=FakeStore())

    assert saved == {"OPENDART_API_KEY": "dart-secret", "AI_API_KEY": "ai-secret"}


def test_settings_endpoint_returns_redacted_config(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        "\n".join(
            [
                "[providers]",
                "ai_api_key = \"ai-secret\"",
                "ai_base_url = \"http://127.0.0.1:11434/v1\"",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("VBINVEST_CONFIG_PATH", str(config_path))

    response = TestClient(app).get("/api/settings")

    assert response.status_code == 200
    payload = response.json()
    assert payload["providers"]["ai_api_key"] == "<redacted>"
    assert "ai-secret" not in response.text
