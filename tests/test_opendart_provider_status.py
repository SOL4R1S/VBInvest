from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from scripts import api
from scripts.lib.disclosures import classify_opendart_status


def test_opendart_status_endpoint_reports_missing_key(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("VBINVEST_CONFIG_PATH", str(tmp_path / "missing.toml"))

    response = TestClient(api.app).get("/api/providers/opendart/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "missing_key"
    assert payload["source"] == "none"


def test_opendart_status_endpoint_prefers_env_key_over_config(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text("[providers]\nopendart_api_key = \"config-secret\"\n", encoding="utf-8")
    monkeypatch.setenv("VBINVEST_CONFIG_PATH", str(config_path))
    monkeypatch.setenv("OPENDART_API_KEY", "env-secret")
    captured: dict[str, str] = {}

    def fake_check(api_key: str):
        captured["api_key"] = api_key
        return classify_opendart_status({"status": "000", "message": "정상"})

    monkeypatch.setattr(api, "check_opendart_api_key", fake_check)

    response = TestClient(api.app).get("/api/providers/opendart/status?check=true")

    assert response.status_code == 200
    assert response.json()["status"] == "enabled"
    assert response.json()["source"] == "env"
    assert captured == {"api_key": "env-secret"}
    assert "env-secret" not in response.text
    assert "config-secret" not in response.text


def test_classify_opendart_status_maps_provider_error_and_rate_limit() -> None:
    assert classify_opendart_status({"status": "000", "message": "정상"}).status == "enabled"
    assert classify_opendart_status({"status": "020", "message": "요청 제한"}).status == "rate_limited"
    assert classify_opendart_status({"status": "013", "message": "조회된 데이타가 없습니다."}).status == "provider_error"
