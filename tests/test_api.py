from datetime import datetime, timezone

from fastapi.testclient import TestClient

from scripts import api
from scripts.api import app
from scripts.lib.auth import create_test_token
from scripts.lib.ai_provider import AIProviderConfigError
from scripts.lib.version import load_version_metadata


class FakeSettingsDB:
    def fetch_latest_report_run(self, run_type: str, scope_slug: str):
        if run_type != "startup-market-refresh" or scope_slug != "semiconductor-core":
            return None
        return {
            "run_id": "run-123",
            "run_type": run_type,
            "scope_type": "watchlist",
            "scope_slug": scope_slug,
            "completed_at": datetime(2026, 6, 1, 0, 0, tzinfo=timezone.utc),
            "status": "ok",
            "output_summary": (
                "dry_run=False stale=False assets=1 price_rows=2 indicator_rows=3 news_items=4 disclosures=5 "
                ' | meta={"watchlist":"semiconductor-core","news_items":4,"disclosures":5,'
                '"provider_disabled":[{"symbol":"NVDA","provider":"dart","reason":"missing-api-key"}]}'
            ),
        }


class FakeResearchDB:
    def fetch_profile_by_auth_user(self, auth_user_id: str):
        return {"profile_id": 1, "auth_user_id": auth_user_id, "slug": auth_user_id, "email": f"{auth_user_id}@example.com"}

    def fetch_latest_research_for_asset(self, symbol: str):
        return {"target_slug": symbol, "opinion": "중립", "thesis": "thesis", "bull": "bull", "base": "base", "bear": "bear", "risks": [], "triggers": [], "sources": []}

    def user_has_research_entitlement(self, auth_user_id: str, symbol: str):
        return True

    def generate_research_for_asset(self, auth_user_id: str, symbol: str):
        raise AIProviderConfigError("AI provider API key is required for non-local providers")


def client_with_db(monkeypatch, fake_db):
    monkeypatch.setattr(api, "db", lambda: fake_db)
    monkeypatch.setattr(api, "auth_db", lambda: fake_db)
    return TestClient(api.app)


def test_health_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "vbinvest"
    assert payload["version"] == load_version_metadata().version
    assert payload["build_version"]


def test_settings_exposes_safe_provider_status(monkeypatch, tmp_path):
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        "\n".join(
            [
                "[providers]",
                "opendart_api_key = \"config-dart-key\"",
                "ai_base_url = \"http://127.0.0.1:11434/v1\"",
                "ai_api_key = \"\"",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("VBINVEST_CONFIG_PATH", str(config_path))
    monkeypatch.setenv("AI_PROVIDER_MODEL", "qwen2.5")
    client = client_with_db(monkeypatch, FakeSettingsDB())

    response = client.get("/api/settings")

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider_status"]["opendart"]["configured"] is True
    assert payload["provider_status"]["ai"]["mode"] == "local"
    assert payload["provider_status"]["ai"]["key_required"] is False
    assert payload["provider_status"]["ai"]["key_configured"] is False
    assert payload["provider_status"]["ai"]["base_url"] == "http://127.0.0.1:11434/v1"
    assert payload["provider_status"]["ai"]["model"] == "qwen2.5"
    assert payload["provider_status"]["ai"]["provider"] == "openai-compatible"
    assert payload["provider_status"]["ai"]["error"] is None
    assert "config-dart-key" not in response.text


def test_settings_exposes_latest_startup_refresh_summary(monkeypatch, tmp_path):
    config_path = tmp_path / "config.toml"
    config_path.write_text("[providers]\nai_base_url = \"http://127.0.0.1:11434/v1\"\n", encoding="utf-8")
    monkeypatch.setenv("VBINVEST_CONFIG_PATH", str(config_path))
    monkeypatch.setenv("AI_PROVIDER_MODEL", "qwen2.5")
    client = client_with_db(monkeypatch, FakeSettingsDB())

    response = client.get("/api/settings")

    assert response.status_code == 200
    payload = response.json()
    assert payload["latest_startup_refresh"]["status"] == "ok"
    assert payload["latest_startup_refresh"]["watchlist"] == "semiconductor-core"
    assert payload["latest_startup_refresh"]["news_items"] == 4
    assert payload["latest_startup_refresh"]["disclosures"] == 5
    assert payload["latest_startup_refresh"]["provider_disabled"] == [
        {"symbol": "NVDA", "provider": "dart", "reason": "missing-api-key"}
    ]


def test_generate_research_returns_503_for_cloud_ai_missing_key(monkeypatch):
    token = create_test_token("user-a", email="user-a@example.com")
    client = client_with_db(monkeypatch, FakeResearchDB())

    response = client.post(
        "/api/research/NVDA/generate",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "AI provider API key is required for non-local providers"
