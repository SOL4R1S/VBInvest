from __future__ import annotations

import os
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import json
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from scripts.lib.dashboard import render_dashboard_html
from scripts.lib.api_store import ApiStore
from scripts.lib.auth import AuthError, AuthUser, verify_bearer_token
from scripts.lib.db import DatabaseConfig, VBinvestDB
from scripts.lib.entitlements import WebhookSignatureError, verify_webhook_signature
from scripts.lib.startup_market_refresh import run_startup_market_refresh
from scripts.lib.config import ConfigError, load_local_config
from scripts.lib.version import load_version_metadata

VERSION_METADATA = load_version_metadata()

app = FastAPI(title="VBinvest API", version=VERSION_METADATA.version)


def db() -> VBinvestDB:
    return VBinvestDB(DatabaseConfig.from_env(os.environ))


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


class AdUnlockRequest(BaseModel):
    ad_event_id: str = Field(min_length=1, max_length=160)


class MockPaymentWebhook(BaseModel):
    event_id: str = Field(min_length=1, max_length=160)
    auth_user_id: str = Field(min_length=1, max_length=160)
    symbol: str = Field(min_length=1, max_length=32)
    event_type: str = Field(default="ad_unlocked", max_length=80)


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
        return load_local_config().redacted()
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
    include_news: bool = False,
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
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "status": result.status,
        "watchlist": result.watchlist,
        "dry_run": result.dry_run,
        "locked": result.locked,
        "price_rows": result.price_rows,
        "indicator_rows": result.indicator_rows,
        "failed": result.failures,
        "report_run": result.report_run_id,
    }


@app.get("/api/watchlists")
def list_watchlists(user: AuthUser = Depends(current_user)):
    return {"watchlists": auth_db().list_user_watchlists(user.auth_user_id)}


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
    payload = []
    for item in items:
        latest = item["history"].iloc[-1].to_dict()
        payload.append({
            "asset": item["asset"],
            "latest": {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in latest.items()},
            "opinion": item.get("opinion", "중립"),
            "thesis": item.get("thesis"),
        })
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
    has_access = auth_db().user_has_research_entitlement(user.auth_user_id, symbol)
    if not has_access:
        return {
            "target_slug": symbol,
            "opinion": row.get("opinion", "중립"),
            "locked": True,
            "preview": "리서치 상세 내용은 발행 후 열람할 수 있습니다.",
        }
    return _jsonable_research(row, locked=False)


@app.post("/api/research/{symbol}/generate", status_code=status.HTTP_201_CREATED)
def generate_research(symbol: str, user: AuthUser = Depends(current_user)):
    store = auth_db()
    if not hasattr(store, "generate_research_for_asset"):
        raise HTTPException(status_code=501, detail="on-demand research is not available")
    try:
        row = store.generate_research_for_asset(user.auth_user_id, symbol)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _jsonable_research(row, locked=False)


@app.post("/api/research/{symbol}/ad-unlock")
def ad_unlock_research(symbol: str, payload: AdUnlockRequest, user: AuthUser = Depends(current_user)):
    result = auth_db().grant_ad_unlock(user.auth_user_id, symbol, payload.ad_event_id)
    return {
        "target_slug": symbol,
        "entitlement_state": result["entitlement_state"],
        "expires_at": result["expires_at"].isoformat() if hasattr(result["expires_at"], "isoformat") else result["expires_at"],
    }


@app.post("/api/webhooks/mock-payment")
async def mock_payment_webhook(
    request: Request,
    x_webhook_signature: str | None = Header(default=None),
):
    body = await request.body()
    try:
        verify_webhook_signature(body, x_webhook_signature, os.environ.get("VBINVEST_MOCK_PAYMENT_WEBHOOK_SECRET"))
    except WebhookSignatureError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    try:
        payload = MockPaymentWebhook.model_validate(json.loads(body.decode("utf-8")))
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="invalid webhook body") from exc

    store = auth_db()
    event = store.record_payment_webhook(
        payload.event_id,
        "mock-payment",
        payload.event_type,
        payload.model_dump(),
        True,
    )
    if event.get("duplicate"):
        return {"status": "ignored", "event_id": payload.event_id}
    if payload.event_type == "ad_unlocked":
        store.grant_ad_unlock(payload.auth_user_id, payload.symbol, payload.event_id)
    if payload.event_type == "subscription.activated":
        store.grant_subscription_entitlement(payload.auth_user_id, "mock-payment", payload.event_id)
    return {"status": "processed", "event_id": payload.event_id}


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
