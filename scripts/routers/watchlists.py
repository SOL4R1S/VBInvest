"""Watchlist, ticker, and dashboard data routes."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from scripts.lib.dashboard_payload import serialize_dashboard_items
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


@router.get("/api/watchlists/export/all")
def export_all_watchlists(user=Depends(current_user)):
    """Export all user watchlists as a JSON backup."""
    watchlists = auth_db().list_user_watchlists(user.auth_user_id)
    export_data = {
        "version": 1,
        "watchlists": watchlists,
    }
    content = json.dumps(export_data, ensure_ascii=False, indent=2)
    return StreamingResponse(
        iter([content]),
        media_type="application/json; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="vbinvest-watchlists.json"'},
    )


@router.post("/api/watchlists/import", status_code=status.HTTP_201_CREATED)
async def import_watchlists(request: Request, user=Depends(current_user)):
    """Import watchlists from a JSON backup. Creates new watchlists; skips duplicates by name."""
    try:
        body = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="invalid JSON body") from exc

    watchlists = body.get("watchlists") if isinstance(body, dict) else body
    if not isinstance(watchlists, list):
        raise HTTPException(status_code=400, detail="expected 'watchlists' array")

    existing = auth_db().list_user_watchlists(user.auth_user_id)
    existing_names = {w.get("name", "").lower() for w in existing}

    created = 0
    skipped = 0
    for item in watchlists:
        name = item.get("name", "").strip()
        symbols = item.get("symbols", [])
        if not name or not isinstance(symbols, list):
            skipped += 1
            continue
        if name.lower() in existing_names:
            skipped += 1
            continue
        auth_db().create_user_watchlist(user.auth_user_id, name, symbols)
        existing_names.add(name.lower())
        created += 1

    return {"created": created, "skipped": skipped}


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
    from scripts import api

    result = api.validate_ticker_symbol(symbol)
    if not result["valid"]:
        raise HTTPException(status_code=404, detail=result)
    return result


@router.get("/api/tickers/search")
def search_tickers(query: str, limit: int = 8):
    from scripts import api

    safe_limit = max(1, min(limit, 20))
    return {"query": query, "suggestions": api.search_ticker_suggestions(query, limit=safe_limit)}


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
