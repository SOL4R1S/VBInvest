from __future__ import annotations

import os
import json
import shutil
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field, StrictBool

from scripts.lib.dashboard import render_dashboard_html
from scripts.lib.dashboard_payload import serialize_dashboard_items
from scripts.lib.api_store import ApiStore
from scripts.lib.auth import AuthError, AuthUser, verify_bearer_token
from scripts.lib.ai_provider import AIProviderConfigError
from scripts.lib.ai_catalog import provider_catalog
from scripts.lib.ai_cli import detect_ai_cli
from scripts.lib.config import (
    ConfigError,
    DatabaseMode,
    DatabaseSettings,
    ExportMode,
    LocalConfig,
    ObsidianSettings,
    ProviderSettings,
    SchedulerSettings,
    config_path_from_env,
    load_local_config,
    load_opendart_api_key,
    parse_report_run_summary,
    provider_status,
    write_local_config,
)
from scripts.lib.db_factory import build_database_from_local_config
from scripts.lib.local_scheduler import LocalScheduler
from scripts.lib.db_repository import DBRepository
from scripts.lib.disclosures import check_opendart_api_key
from scripts.lib.on_demand_report import OnDemandReportError
from scripts.lib.prices import validate_ticker_symbol
from scripts.lib.startup_market_refresh import run_startup_market_refresh
from scripts.lib.version import load_version_metadata

try:
    from psycopg import OperationalError as PostgresOperationalError
except ImportError:
    PostgresOperationalError = RuntimeError

VERSION_METADATA = load_version_metadata()

app = FastAPI(title="VBinvest API", version=VERSION_METADATA.version)
LOCAL_SHUTDOWN_CALLBACK = None


def db() -> DBRepository:
    return build_database_from_local_config(environ=os.environ)


def frontend_out_dir() -> Path:
    configured = os.environ.get("VBINVEST_FRONTEND_OUT_DIR")
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[1] / "frontend" / "out"


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


def frontend_index_response() -> HTMLResponse:
    index_file = frontend_index_file()
    if index_file is None:
        raise HTTPException(status_code=404, detail="frontend build not found")
    html = index_file.read_text(encoding="utf-8")
    session_token = os.environ.get("VBINVEST_LOCAL_SESSION_TOKEN", "")
    if session_token:
        script = (
            "<script>"
            f"window.__VBINVEST_LOCAL_SESSION_TOKEN__={json.dumps(session_token)};"
            "</script>"
        )
        html = html.replace("</head>", f"{script}</head>", 1) if "</head>" in html else f"{script}{html}"
    return HTMLResponse(html)


class WatchlistCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    symbols: list[str] = Field(default_factory=list)


class WatchlistAssetChange(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)


class PortfolioHoldingCreate(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)
    quantity: float = Field(gt=0)
    average_cost: float | None = Field(default=None, ge=0)
    note: str | None = Field(default=None, max_length=500)


class PortfolioHoldingUpdate(BaseModel):
    quantity: float | None = Field(default=None, gt=0)
    average_cost: float | None = Field(default=None, ge=0)
    note: str | None = Field(default=None, max_length=500)


class FirstRunDatabasePayload(BaseModel):
    mode: DatabaseMode = DatabaseMode.SQLITE
    sqlite_path: str | None = Field(default=None, max_length=1000)
    postgres_url: str = Field(default="", max_length=1000)


class FirstRunObsidianPayload(BaseModel):
    vault_path: str = Field(min_length=1, max_length=1000)
    export_mode: ExportMode = ExportMode.DIRECT


class FirstRunProviderPayload(BaseModel):
    opendart_api_key: str = Field(default="", max_length=200)
    ai_mode: str = Field(default="none", max_length=40)
    ai_provider_name: str = Field(default="", max_length=80)
    ai_base_url: str = Field(default="", max_length=500)
    ai_model: str = Field(default="", max_length=160)
    ai_context_size: int = Field(default=8192, ge=1024, le=262144)
    ai_api_key: str = Field(default="", max_length=500)


class FirstRunSetupPayload(BaseModel):
    language: str = Field(default="ko", max_length=10)
    data_directory: str = Field(min_length=1, max_length=1000)
    database: FirstRunDatabasePayload = Field(default_factory=FirstRunDatabasePayload)
    obsidian: FirstRunObsidianPayload
    providers: FirstRunProviderPayload = Field(default_factory=FirstRunProviderPayload)


class SchedulerSettingsPayload(BaseModel):
    daily_refresh_enabled: StrictBool | None = None
    weekly_precompute_enabled: StrictBool | None = None
    watchlist: str | None = Field(default=None, max_length=1000)
    include_news: StrictBool | None = None


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


def _local_scheduler() -> LocalScheduler:
    return LocalScheduler(db())


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
            sqlite_path = Path(payload.sqlite_path).expanduser() if payload.sqlite_path else data_dir / "vbinvest.sqlite3"
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


def auth_db() -> Any:
    backend = db()
    if hasattr(backend, "fetch_profile_by_auth_user"):
        return backend
    return ApiStore(backend)


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


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "vbinvest",
        "version": VERSION_METADATA.version,
        "build_version": VERSION_METADATA.build_version,
    }


@app.get("/", response_class=HTMLResponse)
def frontend_root():
    return frontend_index_response()


@app.get("/_next/{asset_path:path}")
def frontend_next_asset(asset_path: str):
    asset_file = frontend_asset_file(f"_next/{asset_path}")
    if asset_file is None:
        raise HTTPException(status_code=404, detail="frontend asset not found")
    return FileResponse(asset_file)


@app.get("/api/settings")
def settings():
    try:
        config = load_local_config()
        latest_summary = {
            "status": None,
            "watchlist": None,
            "completed_at": None,
            "news_items": 0,
            "disclosures": 0,
            "provider_disabled": [],
        }
        try:
            latest_run = db().fetch_latest_report_run("startup-market-refresh", "semiconductor-core")
        except PostgresOperationalError:
            latest_run = None
        if latest_run is not None:
            latest_summary.update(
                {
                    "status": latest_run.get("status"),
                    "watchlist": latest_run.get("scope_slug"),
                    "completed_at": (
                        latest_run["completed_at"].isoformat()
                        if hasattr(latest_run.get("completed_at"), "isoformat")
                        else latest_run.get("completed_at")
                    ),
                }
            )
            parsed = parse_report_run_summary(latest_run.get("output_summary"))
            if isinstance(parsed, dict):
                latest_summary["news_items"] = parsed.get("news_items", 0)
                latest_summary["disclosures"] = parsed.get("disclosures", 0)
                latest_summary["provider_disabled"] = parsed.get("provider_disabled", [])
        return {
            **config.redacted(),
            "provider_status": provider_status(config, os.environ),
            "latest_startup_refresh": latest_summary,
        }
    except ConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/settings/first-run")
def save_first_run_settings(payload: FirstRunSetupPayload):
    try:
        config = build_first_run_config(payload)
        write_local_config(config, config_path_from_env(os.environ))
    except ConfigError as exc:
        raise HTTPException(status_code=400, detail=f"{exc.field}: {exc.reason}") from exc
    return {
        **config.redacted(),
        "provider_status": provider_status(config, os.environ),
    }


@app.get("/api/providers/opendart/status")
def opendart_provider_status(check: bool = False):
    try:
        config = load_local_config()
    except ConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    status_payload = provider_status(config, os.environ)["opendart"]
    status_text = status_payload.get("status")
    source = status_payload.get("source")
    if status_text == "missing_key":
        return {"status": "missing_key", "source": source, "configured": False}
    if not check:
        return {"status": "enabled", "source": source, "configured": True}
    result = check_opendart_api_key(load_opendart_api_key())
    return {
        "status": result.status,
        "source": source,
        "configured": result.status == "enabled",
        "provider_code": result.provider_code,
        "message": result.message,
    }


@app.get("/api/providers/ai/status")
def ai_provider_status():
    try:
        config = load_local_config()
    except ConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    ai_status = provider_status(config, os.environ)["ai"]
    return {
        **ai_status,
        "catalog": [entry.as_dict() for entry in provider_catalog()],
        "cli": {
            "codex": detect_ai_cli(
                "codex",
                executable_path=os.environ.get("CODEX_CLI_PATH"),
                login_command="codex login --device-auth",
            ).as_dict(),
            "copilot": detect_ai_cli(
                "copilot",
                executable_path=os.environ.get("COPILOT_CLI_PATH"),
                login_command="copilot login",
            ).as_dict(),
        },
    }


@app.get("/api/me")
def me(user: AuthUser = Depends(current_user)):
    profile = auth_db().fetch_profile_by_auth_user(user.auth_user_id)
    return {"auth_user_id": user.auth_user_id, "email": user.email, "provider": "local", "profile": profile}


@app.post("/api/startup/market-refresh")
def startup_market_refresh(
    watchlist: str = "semiconductor-core",
    dry_run: bool = False,
    no_network: bool = False,
    include_news: bool = True,
    force: bool = False,
    limit: int = 0,
):
    try:
        result = run_startup_market_refresh(
            db(),
            watchlist=watchlist,
            dry_run=dry_run,
            no_network=no_network,
            include_news=include_news,
            limit=limit,
            force=force,
            dart_api_key=load_opendart_api_key(),
        )
    except (ConfigError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "status": result.status,
        "watchlist": result.watchlist,
        "dry_run": result.dry_run,
        "queued": result.queued,
        "running": result.running,
        "succeeded": result.succeeded,
        "failed": result.failed,
        "locked": result.locked,
        "stale": result.stale,
        "price_rows": result.price_rows,
        "indicator_rows": result.indicator_rows,
        "news_items": result.news_items,
        "disclosures": result.disclosures,
        "provider_disabled": result.provider_disabled,
        "failures": result.failures,
        "report_run_id": result.report_run_id,
        "last_success_at": result.last_success_at,
    }


@app.get("/api/scheduler/status")
def scheduler_status():
    try:
        return _local_scheduler().status()
    except (ConfigError, ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/scheduler/settings")
def scheduler_settings():
    try:
        return _local_scheduler().get_settings().as_dict()
    except (ConfigError, ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.patch("/api/scheduler/settings")
def patch_scheduler_settings(payload: SchedulerSettingsPayload, user: AuthUser = Depends(current_user)):
    try:
        return _local_scheduler().patch_settings(
            daily_refresh_enabled=payload.daily_refresh_enabled,
            weekly_precompute_enabled=payload.weekly_precompute_enabled,
            watchlist=payload.watchlist,
            include_news=payload.include_news,
        ).as_dict()
    except (ConfigError, ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/scheduler/tick")
def run_scheduler_tick(
    dry_run: bool = False,
    no_network: bool = False,
    include_news: bool = True,
    limit: int = 0,
    force: bool = False,
    user: AuthUser = Depends(current_user),
):
    try:
        return _local_scheduler().tick(
            dry_run=dry_run,
            no_network=no_network,
            include_news=include_news,
            limit=limit,
            force=force,
            dart_api_key=load_opendart_api_key(),
        )
    except (ConfigError, ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/system/shutdown")
def system_shutdown(user: AuthUser = Depends(current_user)):
    if LOCAL_SHUTDOWN_CALLBACK is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="local launcher shutdown is not available")
    LOCAL_SHUTDOWN_CALLBACK()
    return {"status": "shutting_down"}


@app.get("/api/watchlists")
def list_watchlists(user: AuthUser = Depends(current_user)):
    return {"watchlists": auth_db().list_user_watchlists(user.auth_user_id)}


@app.get("/api/tickers/validate")
def validate_ticker(symbol: str):
    result = validate_ticker_symbol(symbol)
    if not result["valid"]:
        raise HTTPException(status_code=404, detail="ticker not found")
    return result


@app.post("/api/watchlists", status_code=status.HTTP_201_CREATED)
def create_watchlist(payload: WatchlistCreate, user: AuthUser = Depends(current_user)):
    return auth_db().create_user_watchlist(user.auth_user_id, payload.name, payload.symbols)


@app.get("/api/watchlists/{watchlist_id}")
def get_watchlist(watchlist_id: str, user: AuthUser = Depends(current_user)):
    watchlist = auth_db().get_user_watchlist(user.auth_user_id, watchlist_id)
    if watchlist is None:
        raise HTTPException(status_code=404, detail="watchlist not found")
    return watchlist


@app.post("/api/watchlists/{watchlist_id}/assets")
def add_watchlist_asset(
    watchlist_id: str,
    payload: WatchlistAssetChange,
    user: AuthUser = Depends(current_user),
):
    try:
        watchlist = auth_db().add_user_watchlist_asset(user.auth_user_id, watchlist_id, payload.symbol)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if watchlist is None:
        raise HTTPException(status_code=404, detail="watchlist not found")
    return watchlist


@app.delete("/api/watchlists/{watchlist_id}/assets/{symbol}")
def remove_watchlist_asset(watchlist_id: str, symbol: str, user: AuthUser = Depends(current_user)):
    watchlist = auth_db().remove_user_watchlist_asset(user.auth_user_id, watchlist_id, symbol)
    if watchlist is None:
        raise HTTPException(status_code=404, detail="watchlist not found")
    return watchlist


@app.get("/api/watchlists/{slug}/assets")
def watchlist_assets(slug: str):
    assets = db().fetch_watchlist_assets(slug)
    if not assets:
        raise HTTPException(status_code=404, detail="watchlist not found or empty")
    return {"watchlist": slug, "assets": assets}


@app.get("/api/watchlists/{slug}/collection-status")
def watchlist_collection_status(slug: str):
    assets = db().fetch_watchlist_collection_status(slug)
    if not assets:
        raise HTTPException(status_code=404, detail="watchlist not found or empty")
    return {"watchlist": slug, "assets": assets}


@app.get("/api/watchlists/{slug}/dashboard")
def dashboard_data(slug: str, days: int = 260):
    items = db().fetch_dashboard_items(slug, days=days)
    if not items:
        raise HTTPException(status_code=404, detail="dashboard data not found")
    payload = serialize_dashboard_items(items)
    return {"watchlist": slug, "count": len(payload), "items": payload}


@app.get("/api/portfolio/holdings")
def list_portfolio_holdings(user: AuthUser = Depends(current_user)):
    return {"holdings": auth_db().list_user_portfolio_holdings(user.auth_user_id)}


@app.post("/api/portfolio/holdings", status_code=status.HTTP_201_CREATED)
def create_portfolio_holding(payload: PortfolioHoldingCreate, user: AuthUser = Depends(current_user)):
    try:
        return auth_db().create_user_portfolio_holding(
            user.auth_user_id,
            payload.symbol,
            payload.quantity,
            payload.average_cost,
            payload.note,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.patch("/api/portfolio/holdings/{holding_id}")
def update_portfolio_holding(
    holding_id: str,
    payload: PortfolioHoldingUpdate,
    user: AuthUser = Depends(current_user),
):
    holding = auth_db().update_user_portfolio_holding(
        user.auth_user_id,
        holding_id,
        payload.quantity,
        payload.average_cost,
        payload.note,
    )
    if holding is None:
        raise HTTPException(status_code=404, detail="holding not found")
    return holding


@app.delete("/api/portfolio/holdings/{holding_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_portfolio_holding(holding_id: str, user: AuthUser = Depends(current_user)):
    deleted = auth_db().delete_user_portfolio_holding(user.auth_user_id, holding_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="holding not found")


@app.get("/api/research/{symbol}/latest")
def latest_research(symbol: str, user: AuthUser = Depends(current_user)):
    row = auth_db().fetch_latest_research_for_asset(symbol)
    if row is None:
        raise HTTPException(status_code=404, detail="research not found")
    return _jsonable_research(row, locked=False)


@app.post("/api/research/{symbol}/generate", status_code=status.HTTP_201_CREATED)
def generate_research(symbol: str, user: AuthUser = Depends(current_user)):
    store = auth_db()
    if not hasattr(store, "generate_research_for_asset"):
        raise HTTPException(status_code=501, detail="on-demand research is not available")
    try:
        row = store.generate_research_for_asset(user.auth_user_id, symbol, obsidian_vault_path=_obsidian_vault_path())
    except OnDemandReportError as exc:
        raise HTTPException(status_code=503, detail=exc.user_message) from exc
    except AIProviderConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _jsonable_research(row, locked=False)


@app.delete("/api/research-jobs/{run_id}")
def cancel_research_job(run_id: str, user: AuthUser = Depends(current_user)):
    store = auth_db()
    if not hasattr(store, "cancel_report_run"):
        raise HTTPException(status_code=501, detail="research job cancellation is not available")
    row = store.cancel_report_run(run_id)
    if row is None:
        raise HTTPException(status_code=404, detail="research job not found")
    return {
        "run_id": row.get("run_id"),
        "status": row.get("status"),
        "error_message": row.get("error_message"),
    }


@app.delete("/api/research/{symbol}/generate")
def cancel_research_generation(symbol: str, user: AuthUser = Depends(current_user)):
    store = auth_db()
    run_id = store.record_report_run(
        run_type="on-demand-research",
        status="canceled",
        scope_type="asset",
        scope_slug=symbol,
        failed_assets=[],
        output_summary="user-canceled",
        output_path=None,
        error_message="canceled by user",
    )
    return {"run_id": run_id, "status": "canceled", "error_message": "canceled by user"}


@app.post("/api/research/{symbol}/ad-unlock")
def ad_unlock_research(symbol: str, user: AuthUser = Depends(current_user)):
    raise hosted_monetization_disabled()


@app.post("/api/webhooks/mock-payment")
async def mock_payment_webhook():
    raise hosted_monetization_disabled()


@app.get("/dashboard/{slug}", response_class=HTMLResponse)
def dashboard_html(slug: str, days: int = 260):
    items = db().fetch_dashboard_items(slug, days=days)
    if not items:
        raise HTTPException(status_code=404, detail="dashboard data not found")
    return render_dashboard_html(items, title=f"VBinvest {slug}")


@app.get("/{asset_path:path}")
def frontend_asset_or_route(asset_path: str):
    if asset_path.startswith("api/") or asset_path == "health" or asset_path.startswith("dashboard/"):
        raise HTTPException(status_code=404, detail="not found")
    asset_file = frontend_asset_file(asset_path)
    if asset_file is not None:
        return FileResponse(asset_file)
    return frontend_index_response()


def _jsonable_research(row: dict[str, Any], *, locked: bool) -> dict[str, Any]:
    return {
        "target_slug": row.get("target_slug"),
        "opinion": row.get("opinion", "중립"),
        "locked": locked,
        "thesis": row.get("thesis"),
        "bull": row.get("bull"),
        "base": row.get("base"),
        "bear": row.get("bear"),
        "sources": _jsonable_list(row.get("sources")),
        "run_id": row.get("run_id"),
        "report_date": row.get("report_date"),
        "report_path": row.get("report_path"),
        "obsidian_path": row.get("obsidian_path"),
        "report_url": row.get("report_url"),
    }


def _obsidian_vault_path() -> Path | None:
    try:
        return load_local_config(environ=os.environ).obsidian.vault_path
    except ConfigError:
        return None


def _jsonable_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return []
        return parsed if isinstance(parsed, list) else []
    return []
