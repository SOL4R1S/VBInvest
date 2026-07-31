"""Alert rules routes — CRUD for user-configurable price alert conditions."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from scripts.lib.auth import AuthUser
from scripts.routers.deps import current_user, db

router = APIRouter(prefix="/api/alert-rules", tags=["alert-rules"])


# -- request/response models ------------------------------------------


class AlertRuleCreate(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20)
    condition: str = Field(..., pattern=r"^(above|below|change_pct)$")
    threshold: float = Field(..., gt=0)


class AlertRuleUpdate(BaseModel):
    enabled: bool | None = None
    threshold: float | None = Field(None, gt=0)


# -- endpoints ---------------------------------------------------------


@router.get("")
def list_alert_rules(user: AuthUser = Depends(current_user)) -> list[dict[str, Any]]:
    store = db()
    if not hasattr(store, "list_alert_rules"):
        return []
    return store.list_alert_rules(user.auth_user_id)


@router.post("", status_code=201)
def create_alert_rule(
    payload: AlertRuleCreate,
    user: AuthUser = Depends(current_user),
) -> dict[str, Any]:
    store = db()
    if not hasattr(store, "create_alert_rule"):
        raise HTTPException(status_code=501, detail="alert rules not supported")
    return store.create_alert_rule(
        user.auth_user_id,
        payload.symbol,
        payload.condition,
        payload.threshold,
    )


@router.patch("/{rule_id}")
def update_alert_rule(
    rule_id: str,
    payload: AlertRuleUpdate,
    user: AuthUser = Depends(current_user),
) -> dict[str, str]:
    store = db()
    if not hasattr(store, "update_alert_rule"):
        raise HTTPException(status_code=501, detail="alert rules not supported")
    updated = store.update_alert_rule(
        user.auth_user_id,
        rule_id,
        enabled=payload.enabled,
        threshold=payload.threshold,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="rule not found")
    return {"status": "ok"}


@router.delete("/{rule_id}", status_code=204)
def delete_alert_rule(
    rule_id: str,
    user: AuthUser = Depends(current_user),
) -> None:
    store = db()
    if not hasattr(store, "delete_alert_rule"):
        raise HTTPException(status_code=501, detail="alert rules not supported")
    deleted = store.delete_alert_rule(user.auth_user_id, rule_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="rule not found")
