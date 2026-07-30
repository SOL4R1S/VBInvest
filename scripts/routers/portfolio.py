"""Portfolio holdings CRUD routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from scripts.routers.deps import (
    PortfolioHoldingCreate,
    PortfolioHoldingUpdate,
    auth_db,
    current_user,
)

router = APIRouter()


@router.get("/api/portfolio/holdings")
def list_portfolio_holdings(user=Depends(current_user)):
    return {"holdings": auth_db().list_user_portfolio_holdings(user.auth_user_id)}


@router.post("/api/portfolio/holdings", status_code=status.HTTP_201_CREATED)
def create_portfolio_holding(payload: PortfolioHoldingCreate, user=Depends(current_user)):
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


@router.patch("/api/portfolio/holdings/{holding_id}")
def update_portfolio_holding(
    holding_id: str,
    payload: PortfolioHoldingUpdate,
    user=Depends(current_user),
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


@router.delete("/api/portfolio/holdings/{holding_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_portfolio_holding(holding_id: str, user=Depends(current_user)):
    deleted = auth_db().delete_user_portfolio_holding(user.auth_user_id, holding_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="holding not found")
