"""Research generation and job management routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from scripts.lib.ai_provider import AIProviderConfigError
from scripts.lib.on_demand_report import OnDemandReportError
from scripts.routers.deps import (
    auth_db,
    current_user,
    hosted_monetization_disabled,
    jsonable_research,
    obsidian_vault_path,
)

router = APIRouter()


@router.get("/api/research/{symbol}/latest")
def latest_research(symbol: str, user=Depends(current_user)):
    row = auth_db().fetch_latest_research_for_asset(symbol)
    if row is None:
        raise HTTPException(status_code=404, detail="research not found")
    return jsonable_research(row, locked=False)


@router.post("/api/research/{symbol}/generate", status_code=status.HTTP_201_CREATED)
def generate_research(symbol: str, user=Depends(current_user)):
    store = auth_db()
    if not hasattr(store, "generate_research_for_asset"):
        raise HTTPException(status_code=501, detail="on-demand research is not available")
    try:
        row = store.generate_research_for_asset(user.auth_user_id, symbol, obsidian_vault_path=obsidian_vault_path())
    except OnDemandReportError as exc:
        raise HTTPException(status_code=503, detail=exc.user_message) from exc
    except AIProviderConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return jsonable_research(row, locked=False)


@router.delete("/api/research-jobs/{run_id}")
def cancel_research_job(run_id: str, user=Depends(current_user)):
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


@router.delete("/api/research/{symbol}/generate")
def cancel_research_generation(symbol: str, user=Depends(current_user)):
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


@router.post("/api/research/{symbol}/ad-unlock")
def ad_unlock_research(symbol: str, user=Depends(current_user)):
    raise hosted_monetization_disabled()


@router.post("/api/webhooks/mock-payment")
async def mock_payment_webhook():
    raise hosted_monetization_disabled()
