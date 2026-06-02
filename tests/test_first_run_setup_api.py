from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from scripts import api


def setup_payload(data_dir: Path, vault_dir: Path, *, mode: str = "sqlite", postgres_url: str = "") -> dict[str, object]:
    return {
        "language": "ko",
        "data_directory": str(data_dir),
        "database": {
            "mode": mode,
            "postgres_url": postgres_url,
        },
        "obsidian": {
            "vault_path": str(vault_dir),
            "export_mode": "direct",
        },
        "providers": {
            "opendart_api_key": "",
            "ai_mode": "none",
            "ai_base_url": "",
            "ai_api_key": "",
        },
    }


def test_first_run_setup_saves_sqlite_config_and_redacts_settings(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    data_dir = tmp_path / "data"
    vault_dir = tmp_path / "vault"
    vault_dir.mkdir()
    monkeypatch.setenv("VBINVEST_CONFIG_PATH", str(config_path))

    response = TestClient(api.app).post("/api/settings/first-run", json=setup_payload(data_dir, vault_dir))

    assert response.status_code == 200
    payload = response.json()
    assert payload["first_run_completed"] is True
    assert payload["database"]["mode"] == "sqlite"
    assert payload["database"]["sqlite_path"] == str(data_dir / "vbinvest.sqlite3")
    assert payload["obsidian"]["vault_path"] == str(vault_dir)
    assert payload["providers"]["opendart_api_key"] == ""
    assert config_path.read_text(encoding="utf-8")

    settings = TestClient(api.app).get("/api/settings")

    assert settings.status_code == 200
    assert settings.json()["first_run_completed"] is True


def test_first_run_setup_rejects_invalid_vault_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("VBINVEST_CONFIG_PATH", str(tmp_path / "config.toml"))

    response = TestClient(api.app).post(
        "/api/settings/first-run",
        json=setup_payload(tmp_path / "data", tmp_path / "missing-vault"),
    )

    assert response.status_code == 400
    assert "obsidian.vault_path" in response.text


def test_first_run_setup_shows_postgres_docker_guidance_when_docker_is_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    vault_dir = tmp_path / "vault"
    vault_dir.mkdir()
    monkeypatch.setenv("VBINVEST_CONFIG_PATH", str(tmp_path / "config.toml"))
    monkeypatch.setattr(api.shutil, "which", lambda _name: None)

    response = TestClient(api.app).post(
        "/api/settings/first-run",
        json=setup_payload(tmp_path / "data", vault_dir, mode="postgres_docker"),
    )

    assert response.status_code == 400
    assert "Docker" in response.text


def test_first_run_setup_rejects_failed_postgres_direct_connection(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    vault_dir = tmp_path / "vault"
    vault_dir.mkdir()
    monkeypatch.setenv("VBINVEST_CONFIG_PATH", str(tmp_path / "config.toml"))
    monkeypatch.setattr(api, "check_postgres_url", lambda _url: False)

    response = TestClient(api.app).post(
        "/api/settings/first-run",
        json=setup_payload(
            tmp_path / "data",
            vault_dir,
            mode="postgres_url",
            postgres_url="postgresql://alice:secret@127.0.0.1:6543/mydb",
        ),
    )

    assert response.status_code == 400
    assert "database.postgres_url" in response.text
    assert "secret" not in response.text
