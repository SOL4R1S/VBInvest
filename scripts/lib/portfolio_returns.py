"""Portfolio returns computation engine.

Weighted-average cost method (YAGNI — sufficient for individual investors).
No currency conversion: KRW/USD mixed portfolios get a flag, not a rate.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class HoldingReturn:
    symbol: str
    display_name_ko: str | None
    quantity: float
    average_cost: float | None
    current_price: float | None
    currency: str | None
    cost_basis: float | None
    current_value: float | None
    unrealized_pnl: float | None
    unrealized_pnl_pct: float | None
    weight_pct: float | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "display_name_ko": self.display_name_ko,
            "quantity": self.quantity,
            "average_cost": self.average_cost,
            "current_price": self.current_price,
            "currency": self.currency,
            "cost_basis": self.cost_basis,
            "current_value": self.current_value,
            "unrealized_pnl": self.unrealized_pnl,
            "unrealized_pnl_pct": self.unrealized_pnl_pct,
            "weight_pct": self.weight_pct,
        }


@dataclass(frozen=True, slots=True)
class PortfolioSummary:
    total_cost: float
    total_value: float
    total_return: float
    total_return_pct: float
    daily_return_pct: float | None
    holding_count: int
    currency_mixed: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "total_cost": self.total_cost,
            "total_value": self.total_value,
            "total_return": self.total_return,
            "total_return_pct": self.total_return_pct,
            "daily_return_pct": self.daily_return_pct,
            "holding_count": self.holding_count,
            "currency_mixed": self.currency_mixed,
        }


def compute_portfolio_returns(
    holdings: list[dict[str, Any]],
    latest_prices: dict[str, float],
    *,
    previous_snapshot: dict[str, Any] | None = None,
) -> tuple[PortfolioSummary, list[HoldingReturn]]:
    """Compute per-holding and aggregate portfolio returns.

    Args:
        holdings: rows from list_user_portfolio_holdings.
        latest_prices: symbol → latest close price.
        previous_snapshot: most recent portfolio_snapshots row for daily return.

    Returns:
        (summary, per-holding returns)
    """
    results: list[HoldingReturn] = []
    total_cost = 0.0
    total_value = 0.0
    currencies: set[str] = set()

    for h in holdings:
        symbol = h["symbol"]
        quantity = float(h.get("quantity") or 0)
        avg_cost = h.get("average_cost")
        current_price = latest_prices.get(symbol)
        currency = h.get("currency")
        if currency:
            currencies.add(currency)

        cost_basis = quantity * avg_cost if avg_cost is not None else None
        current_value = quantity * current_price if current_price is not None else None

        unrealized_pnl: float | None = None
        unrealized_pnl_pct: float | None = None
        if cost_basis is not None and current_value is not None:
            unrealized_pnl = current_value - cost_basis
            unrealized_pnl_pct = unrealized_pnl / cost_basis if cost_basis != 0 else None

        if cost_basis is not None:
            total_cost += cost_basis
        if current_value is not None:
            total_value += current_value

        results.append(
            HoldingReturn(
                symbol=symbol,
                display_name_ko=h.get("display_name_ko"),
                quantity=quantity,
                average_cost=avg_cost,
                current_price=current_price,
                currency=currency,
                cost_basis=cost_basis,
                current_value=current_value,
                unrealized_pnl=unrealized_pnl,
                unrealized_pnl_pct=unrealized_pnl_pct,
                weight_pct=None,  # filled below
            )
        )

    # Weight percentages
    if total_value > 0:
        results = [
            HoldingReturn(
                symbol=r.symbol,
                display_name_ko=r.display_name_ko,
                quantity=r.quantity,
                average_cost=r.average_cost,
                current_price=r.current_price,
                currency=r.currency,
                cost_basis=r.cost_basis,
                current_value=r.current_value,
                unrealized_pnl=r.unrealized_pnl,
                unrealized_pnl_pct=r.unrealized_pnl_pct,
                weight_pct=r.current_value / total_value if r.current_value is not None else None,
            )
            for r in results
        ]

    total_return = total_value - total_cost
    total_return_pct = total_return / total_cost if total_cost != 0 else 0.0

    daily_return_pct: float | None = None
    if previous_snapshot is not None:
        prev_value = previous_snapshot.get("total_value")
        if prev_value is not None and prev_value != 0:
            daily_return_pct = (total_value - float(prev_value)) / float(prev_value)

    summary = PortfolioSummary(
        total_cost=total_cost,
        total_value=total_value,
        total_return=total_return,
        total_return_pct=total_return_pct,
        daily_return_pct=daily_return_pct,
        holding_count=len(holdings),
        currency_mixed=len(currencies) > 1,
    )
    return summary, results


def compute_transaction_adjusted_cost(
    transactions: list[dict[str, Any]],
) -> tuple[float, float]:
    """Weighted-average cost from transaction history.

    Returns:
        (total_quantity, weighted_average_cost)
    """
    total_qty = 0.0
    total_cost = 0.0
    for t in transactions:
        qty = float(t.get("quantity") or 0)
        price = float(t.get("price_per_unit") or 0)
        fee = float(t.get("fee") or 0)
        ttype = t.get("transaction_type")
        if ttype == "buy":
            total_cost += qty * price + fee
            total_qty += qty
        elif ttype == "sell":
            if total_qty > 0:
                avg = total_cost / total_qty
                total_cost -= qty * avg
                total_qty -= qty
                if total_qty < 0:
                    total_qty = 0.0
                    total_cost = 0.0
    avg_cost = total_cost / total_qty if total_qty > 0 else 0.0
    return total_qty, avg_cost
