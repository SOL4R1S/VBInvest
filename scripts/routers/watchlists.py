"""Watchlist, ticker, and dashboard data routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from scripts.lib.dashboard import render_dashboard_html
from scripts.lib.dashboard_payload import serialize_dashboard_items
from scripts.lib.prices import search_ticker_suggestions, validate_ticker_symbol

from scripts.routers.deps import (
    WatchlistAssetChange,
    WatchlistCreate,
    auth_db,
    current_user,
    db,
)

router = APIRouter()


@router.get("/api/watchlists")
def list_watchlists(user=Depends(current_user)):
    return {"watchlists": auth_db().list_user_watchlists(user.auth_user_id)}


@router.post("/api/watchlists", status_code=status.HTTP_201_CREATED)
def create_watchlist(payload: WatchlistCreate, user=Depends(current_user)):
    return auth_db().create_user_watchlist(user.auth_user_id, payload.name, payload.symbols)


@router.get("/api/watchlists/{watchlist_id}")
def get_watchlist(watchlist_id: str, user=Depends(current_user)):
    watchlist = auth_db().get_user_watchlist(user.auth_user_id, watchlist_id)
    if watchlist is None:
        raise HTTPException(status_code=404, detail="watchlist not found")
    return watchlist


@router.post("/api/watchlists/{watchlist_id}/assets")
def add_watchlist_asset(
    watchlist_id: str,
    payload: WatchlistAssetChange,
    user=Depends(current_user),
):
    try:
        watchlist = auth_db().add_user_watchlist_asset(user.auth_user_id, watchlist_id, payload.symbol)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if watchlist is None:
        raise HTTPException(status_code=404, detail="watchlist not found")
    return watchlist


@router.delete("/api/watchlists/{watchlist_id}/assets/{symbol}")
def remove_watchlist_asset(watchlist_id: str, symbol: str, user=Depends(current_user)):
    watchlist = auth_db().remove_user_watchlist_asset(user.auth_user_id, watchlist_id, symbol)
    if watchlist is None:
        raise HTTPException(status_code=404, detail="watchlist not found")
    return watchlist


@router.get("/api/tickers/validate")
def validate_ticker(symbol: str):
    result = validate_ticker_symbol(symbol)
    if not result["valid"]:
        raise HTTPException(status_code=404, detail=result)
    return result


@router.get("/api/tickers/search")
def search_tickers(query: str, limit: int = 8):
    safe_limit = max(1, min(limit, 20))
    return {"query": query, "suggestions": search_ticker_suggestions(query, limit=safe_limit)}


@router.get("/api/watchlists/{slug}/assets")
def watchlist_assets(slug: str):
    assets = db().fetch_watchlist_assets(slug)
    if not assets:
        raise HTTPException(status_code=404, detail="watchlist not found or empty")
    return {"watchlist": slug, "assets": assets}


@router.get("/api/watchlists/{slug}/collection-status")
def watchlist_collection_status(slug: str):
    assets = db().fetch_watchlist_collection_status(slug)
    if not assets:
        raise HTTPException(status_code=404, detail="watchlist not found or empty")
    return {"watchlist": slug, "assets": assets}


@router.get("/api/watchlists/{slug}/dashboard")
def dashboard_data(slug: str, days: int = 1260):
    items = db().fetch_dashboard_items(slug, days=days)
    if not items:
        raise HTTPException(status_code=404, detail="dashboard data not found")
    payload = serialize_dashboard_items(items)
    return {"watchlist": slug, "count": len(payload), "items": payload}
