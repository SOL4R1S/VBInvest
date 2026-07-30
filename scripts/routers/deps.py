"""Shared dependencies and helpers for VBinvest API routers.

Pydantic models live in scripts.routers.models — re-exported here for
backward compatibility with existing imports.
"""

from __future__ import annotations

import json
import os
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

from fastapi import Header, HTTPException, status

from scripts.lib.auth import AuthError, AuthUser, verify_bearer_token
from scripts.lib.config import (
    ConfigError,
    DatabaseMode,
    DatabaseSettings,
    LocalConfig,
    ObsidianSettings,
    ProviderSettings,
    SchedulerSettings,
    load_local_config,
)
from scripts.lib.db_repository import DBRepository
from scripts.lib.local_scheduler import LocalScheduler

# Re-export models so existing `from scripts.routers.deps import X` still works
from scripts.routers.models import (  # noqa: F401
    FirstRunDatabasePayload,
    FirstRunObsidianPayload,
    FirstRunProviderPayload,
    FirstRunSetupPayload,
    LanguageSettingsPayload,
    PortfolioHoldingCreate,
    PortfolioHoldingUpdate,
    SchedulerSettingsPayload,
    ShutdownBeaconPayload,
    WatchlistAssetChange,
    WatchlistCreate,
)

try:
    from psycopg import OperationalError as PostgresOperationalError
except ImportError:
    PostgresOperationalError = RuntimeError

ShutdownCallback = Callable[[], None]


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------


def db() -> DBRepository:
    """Delegate to api.db so tests can monkeypatch api.db."""
    from scripts import api

    return api.db()


def auth_db() -> Any:
    """Delegate to api.auth_db so tests can monkeypatch api.auth_db."""
    from scripts import api

    return api.auth_db()


def current_user(authorization: str | None = Header(default=None)) -> AuthUser:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing bearer token")
    try:
        user = verify_bearer_token(authorization.removeprefix("Bearer ").strip())
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid bearer token") from exc
    store = auth_db()
    if store.fetch_profile_by_auth_user(user.auth_user_id) is None:
        if not hasattr(store, "ensure_profile_for_auth_user"):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="authenticated profile not found")
        store.ensure_profile_for_auth_user(user.auth_user_id, user.email)
    return user


def local_scheduler() -> LocalScheduler:
    return LocalScheduler(db())


# ---------------------------------------------------------------------------
# Frontend helpers
# ---------------------------------------------------------------------------


def frontend_out_dir() -> Path:
    configured = os.environ.get("VBINVEST_FRONTEND_OUT_DIR")
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[2] / "frontend" / "out"


def frontend_index_file() -> Path | None:
    index_file = frontend_out_dir() / "index.html"
    if index_file.is_file():
        return index_file
    return None


def frontend_asset_file(asset_path: str) -> Path | None:
    root = frontend_out_dir().resolve()
    candidate = (root / asset_path).resolve()
    if candidate != root and root not in candidate.parents:
        return None
    if candidate.is_file():
        return candidate
    return None


def frontend_index_response():
    from fastapi.responses import HTMLResponse

    index_file = frontend_index_file()
    if index_file is None:
        raise HTTPException(status_code=404, detail="frontend build not found")
    html = index_file.read_text(encoding="utf-8")
    session_token = os.environ.get("VBINVEST_LOCAL_SESSION_TOKEN", "")
    if session_token:
        script = f"<script>window.__VBINVEST_LOCAL_SESSION_TOKEN__={json.dumps(session_token)};</script>"
        html = html.replace("</head>", f"{script}</head>", 1) if "</head>" in html else f"{script}{html}"
    return HTMLResponse(html)


# ---------------------------------------------------------------------------
# Misc helpers
# ---------------------------------------------------------------------------


def hosted_monetization_disabled() -> HTTPException:
    return HTTPException(status_code=status.HTTP_410_GONE, detail="hosted monetization is disabled in local mode")


def check_postgres_url(postgres_url: str) -> bool:
    try:
        import psycopg
    except ImportError:
        return False
    try:
        with psycopg.connect(postgres_url, connect_timeout=3):
            return True
    except PostgresOperationalError:
        return False


def obsidian_vault_path() -> Path | None:
    try:
        return load_local_config(environ=os.environ).obsidian.vault_path
    except ConfigError:
        return None


def jsonable_research(row: dict[str, Any], *, locked: bool) -> dict[str, Any]:
    return {
        "target_slug": row.get("target_slug"),
        "opinion": row.get("opinion", "중립"),
        "locked": locked,
        "thesis": row.get("thesis"),
        "bull": row.get("bull"),
        "base": row.get("base"),
        "bear": row.get("bear"),
        "sources": jsonable_list(row.get("sources")),
        "run_id": row.get("run_id"),
        "report_date": row.get("report_date"),
        "report_path": row.get("report_path"),
        "obsidian_path": row.get("obsidian_path"),
        "report_url": row.get("report_url"),
    }


def jsonable_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return []
        return parsed if isinstance(parsed, list) else []
    return []


# ---------------------------------------------------------------------------
# First-run config builder
# ---------------------------------------------------------------------------


def build_first_run_config(payload: FirstRunSetupPayload) -> LocalConfig:
    data_dir = Path(payload.data_directory).expanduser()
    if data_dir.exists() and not data_dir.is_dir():
        raise ConfigError("data_directory", "must be a directory")

    vault_path = Path(payload.obsidian.vault_path).expanduser()
    if not vault_path.exists() or not vault_path.is_dir():
        raise ConfigError("obsidian.vault_path", "does not exist")
    if not os.access(vault_path, os.W_OK):
        raise ConfigError("obsidian.vault_path", "must be writable")

    data_dir.mkdir(parents=True, exist_ok=True)
    if not os.access(data_dir, os.W_OK):
        raise ConfigError("data_directory", "must be writable")

    database = build_first_run_database(payload.database, data_dir)
    providers = ProviderSettings(
        opendart_api_key=payload.providers.opendart_api_key.strip(),
        ai_provider_name="" if payload.providers.ai_mode == "none" else payload.providers.ai_provider_name.strip(),
        ai_base_url="" if payload.providers.ai_mode == "none" else payload.providers.ai_base_url.strip(),
        ai_model="" if payload.providers.ai_mode == "none" else payload.providers.ai_model.strip(),
        ai_context_size=payload.providers.ai_context_size,
        ai_api_key="" if payload.providers.ai_mode == "none" else payload.providers.ai_api_key.strip(),
    )
    return LocalConfig(
        first_run_completed=True,
        language=payload.language or "ko",
        database=database,
        obsidian=ObsidianSettings(vault_path=vault_path, export_mode=payload.obsidian.export_mode),
        providers=providers,
        scheduler=SchedulerSettings(
            daily_refresh_enabled=True,
            weekly_precompute_enabled=False,
        ),
    )


def build_first_run_database(payload: FirstRunDatabasePayload, data_dir: Path) -> DatabaseSettings:
    match payload.mode:
        case DatabaseMode.SQLITE:
            sqlite_path = (
                Path(payload.sqlite_path).expanduser() if payload.sqlite_path else data_dir / "vbinvest.sqlite3"
            )
            if sqlite_path.exists() and sqlite_path.is_dir():
                raise ConfigError("database.sqlite_path", "must be a file path")
            return DatabaseSettings(mode=DatabaseMode.SQLITE, sqlite_path=sqlite_path, postgres_url="")
        case DatabaseMode.POSTGRES_DOCKER:
            if shutil.which("docker") is None:
                raise ConfigError("database.mode", "Docker Desktop/Engine is required for postgres_docker mode")
            return DatabaseSettings(
                mode=DatabaseMode.POSTGRES_DOCKER,
                sqlite_path=data_dir / "vbinvest.sqlite3",
                postgres_url=payload.postgres_url or "postgresql://vbinvest@127.0.0.1:5432/vbinvest",
            )
        case DatabaseMode.POSTGRES_URL:
            postgres_url = payload.postgres_url.strip()
            if not postgres_url:
                raise ConfigError("database.postgres_url", "is required for postgres_url mode")
            if not check_postgres_url(postgres_url):
                raise ConfigError("database.postgres_url", "connection failed")
            return DatabaseSettings(
                mode=DatabaseMode.POSTGRES_URL,
                sqlite_path=data_dir / "vbinvest.sqlite3",
                postgres_url=postgres_url,
            )
