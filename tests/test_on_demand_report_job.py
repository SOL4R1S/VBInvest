from __future__ import annotations

from datetime import date
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from threading import Thread
from typing import Final

import pandas as pd
import pytest

from scripts.lib.db import build_indicator_rows, build_price_rows
from scripts.lib.db_sqlite import SQLiteVBinvestDB
from scripts.lib.on_demand_report import generate_on_demand_research_for_asset
from scripts.lib.obsidian import GENERATED_MARKER, note_path

AI_DRAFT: Final = {
    "opinion": "중립",
    "thesis": "저장된 로컬 AI 설정으로 생성한 리포트입니다.",
    "rationale": ["로컬 엔드포인트 호출 확인"],
    "bull": "AI 응답 강세 시나리오",
    "base": "AI 응답 기준 시나리오",
    "bear": "AI 응답 약세 시나리오",
    "risks": ["AI 응답 리스크"],
    "triggers": ["AI 응답 트리거"],
    "confidence": 0.61,
}
AI_RESPONSE: Final = json.dumps(
    {"choices": [{"message": {"content": json.dumps(AI_DRAFT, ensure_ascii=False)}}]},
    ensure_ascii=False,
).encode("utf-8")
REASONING_ONLY_AI_RESPONSE: Final = json.dumps(
    {
        "choices": [
            {
                "message": {
                    "content": "",
                    "reasoning": "Thinking Process: 반복 추론만 생성하고 JSON 본문을 만들지 못했습니다.",
                },
                "finish_reason": "length",
            }
        ]
    },
    ensure_ascii=False,
).encode("utf-8")


class _AIHandler(BaseHTTPRequestHandler):
    calls = 0
    response = AI_RESPONSE

    def do_POST(self) -> None:
        _AIHandler.calls += 1
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(_AIHandler.response)))
        self.end_headers()
        self.wfile.write(_AIHandler.response)

    def log_message(self, format: str, *args: object) -> None:
        return


class _LocalAIServer:
    def __init__(self) -> None:
        self._server = HTTPServer(("127.0.0.1", 0), _AIHandler)
        self._thread = Thread(target=self._server.serve_forever, daemon=True)

    @property
    def base_url(self) -> str:
        host, port = self._server.server_address
        return f"http://{host}:{port}/v1"

    def __enter__(self) -> "_LocalAIServer":
        _AIHandler.calls = 0
        _AIHandler.response = AI_RESPONSE
        self._thread.start()
        return self

    def __exit__(self, exc_type: type[BaseException] | None, exc: BaseException | None, traceback: object) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=2)


def _seed_sqlite_asset(repo: SQLiteVBinvestDB) -> None:
    repo.ensure_profile_for_auth_user("user-a", "user-a@example.com")
    watchlist = repo.create_user_watchlist("user-a", "핵심", ["NVDA"])
    asset_id = repo.fetch_watchlist_assets(watchlist["slug"])[0]["asset_id"]
    prices = pd.DataFrame(
        [
            {"date": date(2026, 6, 1), "open": 100, "high": 105, "low": 99, "close": 104, "volume": 1000, "source": "yfinance"},
            {"date": date(2026, 6, 2), "open": 104, "high": 110, "low": 103, "close": 108, "volume": 1200, "source": "yfinance"},
        ]
    )
    indicators = pd.DataFrame(
        [
            {"date": date(2026, 6, 1), "return_1d": 0.01, "return_1m": 0.05, "ma5": 101, "ma20": 100, "ma50": 99, "ma120": 95, "rsi14": 58},
            {"date": date(2026, 6, 2), "return_1d": 0.04, "return_1m": 0.12, "ma5": 103, "ma20": 101, "ma50": 99, "ma120": 95, "rsi14": 62},
        ]
    )
    repo.upsert_prices(build_price_rows(asset_id, prices))
    repo.upsert_indicators(build_indicator_rows(asset_id, indicators))


@pytest.fixture(autouse=True)
def _isolate_local_config(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("VBINVEST_CONFIG_PATH", str(tmp_path / "missing-config.toml"))


def test_sqlite_on_demand_report_writes_research_run_and_obsidian_note(tmp_path: Path) -> None:
    repo = SQLiteVBinvestDB(tmp_path / "vbinvest.sqlite3")
    vault = tmp_path / "vault"
    vault.mkdir()
    _seed_sqlite_asset(repo)

    row = repo.generate_research_for_asset("user-a", "NVDA", obsidian_vault_path=vault)

    assert row["target_slug"] == "NVDA"
    assert row["opinion"] in {"매수", "아웃퍼폼", "중립", "언더퍼폼", "매도"}
    assert row["run_id"]
    assert row["obsidian_path"]
    assert row["report_url"] is None
    note = Path(row["obsidian_path"])
    assert note.exists()
    assert GENERATED_MARKER in note.read_text(encoding="utf-8")
    assert "Disclaimer" in note.read_text(encoding="utf-8")

    latest_run = repo.fetch_latest_report_run("on-demand-research", "NVDA")
    assert latest_run is not None
    assert latest_run["status"] == "ok"
    assert latest_run["output_path"] == str(note)
    latest = repo.fetch_latest_research_for_asset("NVDA")
    assert latest is not None
    assert latest["sources"][0]["kind"] == "source_gap"


def test_sqlite_on_demand_report_failure_records_run_and_preserves_previous_report(tmp_path: Path) -> None:
    repo = SQLiteVBinvestDB(tmp_path / "vbinvest.sqlite3")
    vault = tmp_path / "vault"
    vault.mkdir()
    _seed_sqlite_asset(repo)
    previous = repo.generate_research_for_asset("user-a", "NVDA", obsidian_vault_path=vault)
    note = note_path(vault, "NVDA", previous["report_date"])
    note.write_text("# manual note\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="Obsidian export failed"):
        repo.generate_research_for_asset("user-a", "NVDA", obsidian_vault_path=vault)

    latest = repo.fetch_latest_research_for_asset("NVDA")
    assert latest is not None
    assert latest["thesis"] == previous["thesis"]
    failed_run = repo.fetch_latest_report_run("on-demand-research", "NVDA")
    assert failed_run is not None
    assert failed_run["status"] == "failed"
    assert failed_run["error_message"] == "Obsidian export failed"


def test_on_demand_report_uses_saved_local_ai_provider_config(tmp_path: Path) -> None:
    repo = SQLiteVBinvestDB(tmp_path / "vbinvest.sqlite3")
    _seed_sqlite_asset(repo)

    with _LocalAIServer() as server:
        config_path = tmp_path / "config.toml"
        config_path.write_text(
            f"""
first_run_completed = true
language = "ko"

[database]
mode = "sqlite"
sqlite_path = "{tmp_path / "vbinvest.sqlite3"}"
postgres_url = ""

[obsidian]
vault_path = ""
export_mode = "direct"

[providers]
opendart_api_key = ""
ai_provider_name = "custom"
ai_base_url = "{server.base_url}"
ai_model = "local-test-model"
ai_context_size = 8192
ai_api_key = ""

[scheduler]
daily_refresh_enabled = true
weekly_precompute_enabled = false
""".strip(),
            encoding="utf-8",
        )

        row = generate_on_demand_research_for_asset(
            repo,
            "user-a",
            "NVDA",
            environ={"VBINVEST_CONFIG_PATH": str(config_path)},
        )

    assert _AIHandler.calls == 1
    assert row["thesis"] == "저장된 로컬 AI 설정으로 생성한 리포트입니다."
    assert row["model_provider"] == "custom"
    assert row["model_name"] == "local-test-model"


def test_on_demand_report_surfaces_reasoning_only_local_ai_failure(tmp_path: Path) -> None:
    repo = SQLiteVBinvestDB(tmp_path / "vbinvest.sqlite3")
    _seed_sqlite_asset(repo)

    with _LocalAIServer() as server:
        _AIHandler.response = REASONING_ONLY_AI_RESPONSE
        config_path = tmp_path / "config.toml"
        config_path.write_text(
            f"""
first_run_completed = true
language = "ko"

[database]
mode = "sqlite"
sqlite_path = "{tmp_path / "vbinvest.sqlite3"}"
postgres_url = ""

[obsidian]
vault_path = ""
export_mode = "direct"

[providers]
opendart_api_key = ""
ai_provider_name = "custom"
ai_base_url = "{server.base_url}"
ai_model = "qwen3.5:2b"
ai_context_size = 8192
ai_api_key = ""

[scheduler]
daily_refresh_enabled = true
weekly_precompute_enabled = false
""".strip(),
            encoding="utf-8",
        )

        with pytest.raises(RuntimeError, match="reasoning-only output without JSON content") as exc_info:
            generate_on_demand_research_for_asset(
                repo,
                "user-a",
                "NVDA",
                environ={"VBINVEST_CONFIG_PATH": str(config_path)},
            )

    assert _AIHandler.calls == 1
    failed_run = repo.fetch_latest_report_run("on-demand-research", "NVDA")
    assert failed_run is not None
    assert failed_run["status"] == "failed"
    assert "reasoning-only output without JSON content" in str(exc_info.value)
    assert "reasoning-only output without JSON content" in failed_run["error_message"]


def test_sqlite_report_run_cancel_updates_running_job(tmp_path: Path) -> None:
    repo = SQLiteVBinvestDB(tmp_path / "vbinvest.sqlite3")
    run_id = repo.record_report_run(
        run_type="on-demand-research",
        status="running",
        scope_type="asset",
        scope_slug="NVDA",
        failed_assets=[],
        output_summary="started",
    )

    canceled = repo.cancel_report_run(run_id)

    assert canceled is not None
    assert canceled["run_id"] == run_id
    assert canceled["status"] == "canceled"
    assert canceled["error_message"] == "canceled by user"


def test_sqlite_report_run_cancel_updates_queued_job(tmp_path: Path) -> None:
    repo = SQLiteVBinvestDB(tmp_path / "vbinvest.sqlite3")
    run_id = repo.record_report_run(
        run_type="on-demand-research",
        status="queued",
        scope_type="asset",
        scope_slug="NVDA",
        failed_assets=[],
        output_summary="queued",
    )

    canceled = repo.cancel_report_run(run_id)

    assert canceled is not None
    assert canceled["run_id"] == run_id
    assert canceled["status"] == "canceled"
    assert canceled["error_message"] == "canceled by user"
