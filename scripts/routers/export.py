"""Data export routes — CSV/JSON/Markdown downloads."""

from __future__ import annotations

import csv
import io
import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from scripts.routers.deps import auth_db, current_user

router = APIRouter()

# UTF-8 BOM for Excel compatibility with Korean text
_BOM = "\ufeff"


def _csv_response(rows: list[dict[str, Any]], fieldnames: list[str], filename: str) -> StreamingResponse:
    """Build a StreamingResponse with UTF-8 BOM CSV."""
    output = io.StringIO()
    output.write(_BOM)
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/api/portfolio/export")
def export_portfolio(
    format: str = Query(default="csv", pattern="^(csv|json)$"),
    user=Depends(current_user),
):
    """Export portfolio holdings as CSV or JSON."""
    store = auth_db()
    holdings = store.list_user_portfolio_holdings(user.auth_user_id)
    if format == "json":
        return StreamingResponse(
            iter([json.dumps(holdings, ensure_ascii=False, indent=2)]),
            media_type="application/json; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="vbinvest_portfolio.json"'},
        )
    fieldnames = [
        "symbol",
        "display_name_ko",
        "quantity",
        "average_cost",
        "current_price",
        "current_value",
        "unrealized_pnl",
        "unrealized_pnl_pct",
        "currency",
    ]
    return _csv_response(holdings, fieldnames, "vbinvest_portfolio.csv")


@router.get("/api/portfolio/holdings/{holding_id}/transactions/export")
def export_transactions(
    holding_id: str,
    format: str = Query(default="csv", pattern="^(csv|json)$"),
    limit: int = Query(default=500, ge=1, le=5000),
    user=Depends(current_user),
):
    """Export transaction history for a holding as CSV or JSON."""
    store = auth_db()
    transactions = store.list_portfolio_transactions(user.auth_user_id, holding_id, limit=limit)
    if format == "json":
        return StreamingResponse(
            iter([json.dumps(transactions, ensure_ascii=False, indent=2)]),
            media_type="application/json; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="vbinvest_transactions_{holding_id}.json"'},
        )
    fieldnames = [
        "transaction_id",
        "transaction_type",
        "quantity",
        "unit_price",
        "total_amount",
        "currency",
        "trade_date",
        "notes",
        "created_at",
    ]
    return _csv_response(transactions, fieldnames, f"vbinvest_transactions_{holding_id}.csv")


@router.get("/api/watchlists/{slug}/export")
def export_watchlist_prices(
    slug: str,
    days: int = Query(default=365, ge=1, le=3650),
    format: str = Query(default="csv", pattern="^(csv|json)$"),
    user=Depends(current_user),
):
    """Export watchlist price data as CSV or JSON."""
    store = auth_db()
    if not hasattr(store, "fetch_watchlist_price_history"):
        raise HTTPException(status_code=501, detail="price history export is not available")
    rows = store.fetch_watchlist_price_history(user.auth_user_id, slug, days=days)
    if format == "json":
        return StreamingResponse(
            iter([json.dumps(rows, ensure_ascii=False, indent=2)]),
            media_type="application/json; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="vbinvest_prices_{slug}.json"'},
        )
    fieldnames = ["symbol", "date", "open", "high", "low", "close", "volume"]
    return _csv_response(rows, fieldnames, f"vbinvest_prices_{slug}.csv")


@router.get("/api/research/{symbol}/export")
def export_research(
    symbol: str,
    format: str = Query(default="md", pattern="^(md|json)$"),
    user=Depends(current_user),
):
    """Export latest research view as Markdown or JSON."""
    store = auth_db()
    if not hasattr(store, "fetch_latest_research_for_asset"):
        raise HTTPException(status_code=501, detail="research export is not available")
    row = store.fetch_latest_research_for_asset(user.auth_user_id, symbol)
    if row is None:
        raise HTTPException(status_code=404, detail=f"no research found for {symbol}")

    if format == "json":
        return StreamingResponse(
            iter([json.dumps(row, ensure_ascii=False, indent=2)]),
            media_type="application/json; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="vbinvest_research_{symbol}.json"'},
        )

    # Markdown export
    md_lines = [
        f"# {symbol} 리서치 리포트",
        "",
        f"- **의견:** {row.get('opinion', '—')}",
        f"- **확신도:** {row.get('confidence', '—')}",
        f"- **생성일:** {row.get('created_at', '—')}",
        "",
        "## 투자 논지",
        "",
        row.get("thesis", ""),
        "",
        "## 리스크",
        "",
        row.get("risk", ""),
        "",
        "## 촉매",
        "",
        row.get("catalyst", ""),
        "",
        "## 소스",
        "",
    ]
    sources = row.get("sources") or []
    for i, src in enumerate(sources, 1):
        title = src.get("title", f"소스 {i}") if isinstance(src, dict) else str(src)
        url = src.get("url", "") if isinstance(src, dict) else ""
        md_lines.append(f"{i}. [{title}]({url})" if url else f"{i}. {title}")

    md_content = "\n".join(md_lines)
    return StreamingResponse(
        iter([md_content]),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="vbinvest_research_{symbol}.md"'},
    )
