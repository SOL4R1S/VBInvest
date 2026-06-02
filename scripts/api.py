from __future__ import annotations

import os
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from scripts.lib.dashboard import render_dashboard_html
from scripts.lib.dashboard_payload import serialize_dashboard_items
from scripts.lib.api_store import ApiStore
from scripts.lib.auth import AuthError, AuthUser, verify_bearer_token
from scripts.lib.ai_provider import AIProviderConfigError
from scripts.lib.config import (
    ConfigError,
    load_local_config,
    load_opendart_api_key,
    parse_report_run_summary,
    provider_status,
)
from scripts.lib.db_factory import build_database_from_local_config
from scripts.lib.db_repository import DBRepository
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


def hosted_monetization_disabled() -> HTTPException:
    return HTTPException(status_code=status.HTTP_410_GONE, detail="hosted monetization is disabled in local mode")


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
        row = store.generate_research_for_asset(user.auth_user_id, symbol)
    except AIProviderConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _jsonable_research(row, locked=False)


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


def _jsonable_research(row: dict[str, Any], *, locked: bool) -> dict[str, Any]:
    return {
        "target_slug": row.get("target_slug"),
        "opinion": row.get("opinion", "중립"),
        "locked": locked,
        "thesis": row.get("thesis"),
        "bull": row.get("bull"),
        "base": row.get("base"),
        "bear": row.get("bear"),
        "sources": row.get("sources") or [],
    }
