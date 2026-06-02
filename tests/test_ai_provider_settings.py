from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from scripts import api
from scripts.lib.ai_catalog import provider_catalog
from scripts.lib.ai_cli import detect_ai_cli


def write_executable(path: Path, body: str) -> Path:
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755)
    return path


def test_ai_provider_catalog_contains_required_cloud_and_local_options() -> None:
    providers = {entry.id: entry for entry in provider_catalog()}

    for provider_id in ["openai", "openrouter", "deepseek", "qwen_dashscope", "kimi_moonshot", "glm_zai", "custom", "ollama"]:
        assert provider_id in providers
        assert providers[provider_id].display_name
        assert providers[provider_id].default_base_url
        assert providers[provider_id].model_examples
        assert providers[provider_id].docs_url


def test_detect_ai_cli_reports_installed_authenticated_and_missing(tmp_path: Path) -> None:
    authenticated = write_executable(tmp_path / "codex", "#!/bin/sh\necho authenticated\n")
    unauthenticated = write_executable(tmp_path / "copilot", "#!/bin/sh\necho not logged in\nexit 1\n")

    codex = detect_ai_cli("codex", executable_path=str(authenticated), login_command="codex login --device-auth")
    copilot = detect_ai_cli("copilot", executable_path=str(unauthenticated), login_command="copilot login")
    missing = detect_ai_cli("codex", executable_path=str(tmp_path / "missing"), login_command="codex login --device-auth")

    assert codex.installed is True
    assert codex.authenticated is True
    assert copilot.installed is True
    assert copilot.authenticated is False
    assert missing.installed is False
    assert missing.authenticated is False
    assert "계정 제한/정지 가능성 있음" in codex.risk_label


def test_ai_status_endpoint_returns_catalog_and_redacted_cli_status(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    fake_codex = write_executable(tmp_path / "codex", "#!/bin/sh\necho authenticated\n")
    monkeypatch.setenv("VBINVEST_CONFIG_PATH", str(tmp_path / "missing.toml"))
    monkeypatch.setenv("CODEX_CLI_PATH", str(fake_codex))

    response = TestClient(api.app).get("/api/providers/ai/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "disabled"
    assert payload["catalog"][0]["id"]
    assert payload["cli"]["codex"]["installed"] is True
    assert payload["cli"]["codex"]["authenticated"] is True
    assert "token" not in response.text.lower()
