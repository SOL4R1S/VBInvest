"""Scheduler and startup market refresh routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from scripts.lib.config import ConfigError
from scripts.lib.startup_market_refresh import run_startup_market_refresh
from scripts.routers.deps import (
    SchedulerSettingsPayload,
    current_user,
    db,
    local_scheduler,
)

router = APIRouter()


@router.post("/api/startup/market-refresh")
def startup_market_refresh(
    watchlist: str = "semiconductor-core",
    dry_run: bool = False,
    no_network: bool = False,
    include_news: bool = True,
    force: bool = False,
    limit: int = 0,
):
    from scripts import api

    ticker_catalog = api.refresh_ticker_catalog()
    try:
        result = run_startup_market_refresh(
            db(),
            watchlist=watchlist,
            dry_run=dry_run,
            no_network=no_network,
            include_news=include_news,
            limit=limit,
            force=force,
            dart_api_key=api.load_opendart_api_key(),
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
        "ticker_catalog": {
            "status": ticker_catalog.status,
            "count": ticker_catalog.count,
            "source": ticker_catalog.source,
            "reason": ticker_catalog.reason,
        },
    }


@router.get("/api/scheduler/status")
def scheduler_status():
    try:
        return local_scheduler().status()
    except (ConfigError, ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/scheduler/settings")
def scheduler_settings():
    try:
        return local_scheduler().get_settings().as_dict()
    except (ConfigError, ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/api/scheduler/settings")
def patch_scheduler_settings(payload: SchedulerSettingsPayload, user=Depends(current_user)):
    try:
        return (
            local_scheduler()
            .patch_settings(
                daily_refresh_enabled=payload.daily_refresh_enabled,
                weekly_precompute_enabled=payload.weekly_precompute_enabled,
                watchlist=payload.watchlist,
                include_news=payload.include_news,
            )
            .as_dict()
        )
    except (ConfigError, ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/scheduler/tick")
def run_scheduler_tick(
    dry_run: bool = False,
    no_network: bool = False,
    include_news: bool = True,
    limit: int = 0,
    force: bool = False,
    user=Depends(current_user),
):
    try:
        from scripts import api

        return local_scheduler().tick(
            dry_run=dry_run,
            no_network=no_network,
            include_news=include_news,
            limit=limit,
            force=force,
            dart_api_key=api.load_opendart_api_key(),
        )
    except (ConfigError, ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
