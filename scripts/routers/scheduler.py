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

        result = local_scheduler().tick(
            dry_run=dry_run,
            no_network=no_network,
            include_news=include_news,
            limit=limit,
            force=force,
            dart_api_key=api.load_opendart_api_key(),
        )
    except (ConfigError, ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Post-tick notifications
    _emit_tick_notifications(user.auth_user_id, result)
    return result


def _emit_tick_notifications(auth_user_id: str, result: dict) -> None:
    """Create scheduler_result + price_alert notifications after a tick."""
    store = db()
    if not hasattr(store, "create_notification"):
        return

    status = result.get("last_tick_status") or "unknown"
    daily = result.get("daily") or {}
    succeeded = daily.get("succeeded", 0)
    failed = daily.get("failed", 0)

    # scheduler_result notification
    store.create_notification(
        auth_user_id,
        "scheduler_result",
        f"스케줄러 실행 완료 ({status})",
        f"성공 {succeeded}건, 실패 {failed}건",
    )

    # price_alert: check daily_indicators for ±5% moves
    if not hasattr(store, "list_daily_indicators"):
        return
    try:
        rows = store.list_daily_indicators(auth_user_id, limit=50)
        for row in rows:
            ret = row.get("return_1d")
            if ret is not None and abs(float(ret)) >= 0.05:
                symbol = row.get("symbol", "?")
                pct = float(ret) * 100
                direction = "상승" if pct > 0 else "하락"
                store.create_notification(
                    auth_user_id,
                    "price_alert",
                    f"{symbol} 일일 {abs(pct):.1f}% {direction}",
                    f"일일 수익률 {pct:+.1f}% — 임계값(±5%) 초과",
                )
    except Exception:
        pass  # price alerts are best-effort
