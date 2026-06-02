from datetime import datetime, timezone

import pandas as pd
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


class FakeDashboardDB:
    def fetch_watchlist_collection_status(self, slug: str):
        assert slug == "semiconductor-core"
        return [
            {
                "symbol": "NVDA",
                "display_name_ko": "엔비디아",
                "exchange": "NASDAQ",
                "provider": "yfinance",
                "latest_price_date": datetime(2026, 6, 1, tzinfo=timezone.utc).date(),
                "latest_fetched_at": datetime(2026, 6, 2, 1, 0, tzinfo=timezone.utc),
                "price_rows": 260,
                "indicator_rows": 260,
                "has_synthetic": False,
                "status": "collected",
            },
            {
                "symbol": "005930.KS",
                "display_name_ko": "삼성전자",
                "exchange": "KRX",
                "provider": "synthetic",
                "latest_price_date": datetime(2026, 6, 1, tzinfo=timezone.utc).date(),
                "latest_fetched_at": datetime(2026, 6, 2, 1, 0, tzinfo=timezone.utc),
                "price_rows": 260,
                "indicator_rows": 260,
                "has_synthetic": True,
                "status": "synthetic",
            },
        ]

    def fetch_dashboard_items(self, slug: str, *, days: int = 260):
        assert slug == "semiconductor-core"
        assert days == 260
        return [
            {
                "asset": {
                    "asset_id": 1,
                    "symbol": "NVDA",
                    "display_name_ko": "엔비디아",
                    "exchange": "NASDAQ",
                    "currency": "USD",
                },
                "history": pd.DataFrame(
                    [
                        {
                            "date": datetime(2026, 5, 29, tzinfo=timezone.utc).date(),
                            "open": 100.0,
                            "high": 104.0,
                            "low": 99.0,
                            "close": 103.0,
                            "volume": 1000,
                            "source": "yfinance",
                            "return_1d": 0.01,
                            "return_1m": 0.08,
                            "ma5": 101.0,
                            "ma20": 98.0,
                            "ma50": 95.0,
                            "ma120": None,
                            "rsi14": 62.5,
                        },
                        {
                            "date": datetime(2026, 5, 30, tzinfo=timezone.utc).date(),
                            "open": 104.0,
                            "high": 105.0,
                            "low": 101.0,
                            "close": 102.0,
                            "volume": 900,
                            "source": "synthetic",
                            "return_1d": -0.0097,
                            "return_1m": 0.07,
                            "ma5": 101.5,
                            "ma20": 98.5,
                            "ma50": 95.5,
                            "ma120": None,
                            "rsi14": 60.0,
                        },
                        {
                            "date": datetime(2026, 6, 1, tzinfo=timezone.utc).date(),
                            "open": 103.0,
                            "high": 108.0,
                            "low": 102.0,
                            "close": 107.0,
                            "volume": 1200,
                            "source": "yfinance",
                            "return_1d": 0.0388,
                            "return_1m": 0.125,
                            "ma5": 102.0,
                            "ma20": 99.0,
                            "ma50": 96.0,
                            "ma120": None,
                            "rsi14": 64.2,
                        },
                    ]
                ),
                "opinion": "아웃퍼폼",
                "thesis": "실제 DB 가격을 기반으로 합니다.",
            }
        ]


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


def test_watchlist_dashboard_api_includes_serialized_history(monkeypatch):
    client = client_with_db(monkeypatch, FakeDashboardDB())

    response = client.get("/api/watchlists/semiconductor-core/dashboard?days=260")

    assert response.status_code == 200
    payload = response.json()
    assert payload["watchlist"] == "semiconductor-core"
    assert payload["items"][0]["asset"]["symbol"] == "NVDA"
    assert payload["items"][0]["latest"]["close"] == 107.0
    assert payload["items"][0]["latest"]["rsi14"] == 64.2
    assert all(row["source"] != "synthetic" for row in payload["items"][0]["history"])
    assert payload["items"][0]["history"] == [
        {
            "date": "2026-05-29",
            "open": 100.0,
            "high": 104.0,
            "low": 99.0,
            "close": 103.0,
            "volume": 1000,
            "source": "yfinance",
            "return_1d": 0.01,
            "return_1m": 0.08,
            "ma5": 101.0,
            "ma20": 98.0,
            "ma50": 95.0,
            "ma120": None,
            "rsi14": 62.5,
        },
        {
            "date": "2026-06-01",
            "open": 103.0,
            "high": 108.0,
            "low": 102.0,
            "close": 107.0,
            "volume": 1200,
            "source": "yfinance",
            "return_1d": 0.0388,
            "return_1m": 0.125,
            "ma5": 102.0,
            "ma20": 99.0,
            "ma50": 96.0,
            "ma120": None,
            "rsi14": 64.2,
        },
    ]


def test_watchlist_collection_status_exposes_data_provenance(monkeypatch):
    client = client_with_db(monkeypatch, FakeDashboardDB())

    response = client.get("/api/watchlists/semiconductor-core/collection-status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["watchlist"] == "semiconductor-core"
    assert payload["assets"][0] == {
        "symbol": "NVDA",
        "display_name_ko": "엔비디아",
        "exchange": "NASDAQ",
        "provider": "yfinance",
        "latest_price_date": "2026-06-01",
        "latest_fetched_at": "2026-06-02T01:00:00+00:00",
        "price_rows": 260,
        "indicator_rows": 260,
        "has_synthetic": False,
        "status": "collected",
    }
    assert payload["assets"][1]["status"] == "synthetic"
