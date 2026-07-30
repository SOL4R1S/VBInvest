/**
 * Portfolio API client — types + fetch helpers.
 */

import { apiGet, apiPost } from "@/lib/http";

// -- types ----------------------------------------------------------------

export type PortfolioHolding = {
  holding_id: string;
  symbol: string;
  display_name_ko: string | null;
  currency: string | null;
  quantity: number;
  average_cost: number | null;
  note: string | null;
};

export type PortfolioTransaction = {
  transaction_id: string;
  holding_id: string;
  symbol: string;
  transaction_type: "buy" | "sell" | "dividend" | "split";
  quantity: number;
  price_per_unit: number;
  fee: number;
  currency: string | null;
  transaction_date: string;
  note: string | null;
  created_at: string | null;
};

export type HoldingReturn = {
  symbol: string;
  display_name_ko: string | null;
  quantity: number;
  average_cost: number | null;
  current_price: number | null;
  currency: string | null;
  cost_basis: number | null;
  current_value: number | null;
  unrealized_pnl: number | null;
  unrealized_pnl_pct: number | null;
  weight_pct: number | null;
};

export type PortfolioSummary = {
  total_cost: number;
  total_value: number;
  total_return: number;
  total_return_pct: number;
  daily_return_pct: number | null;
  holding_count: number;
  currency_mixed: boolean;
};

export type PortfolioSnapshot = {
  snapshot_id: string;
  snapshot_date: string;
  total_cost: number;
  total_value: number;
  total_return: number;
  total_return_pct: number;
  daily_return_pct: number | null;
  holdings: unknown[];
  created_at: string | null;
};

export type PortfolioReturns = {
  summary: PortfolioSummary | null;
  holdings: HoldingReturn[];
  history: PortfolioSnapshot[];
};

// -- parsers --------------------------------------------------------------

function parseHoldings(payload: unknown): PortfolioHolding[] | null {
  if (typeof payload !== "object" || payload === null) return null;
  const obj = payload as Record<string, unknown>;
  if (!Array.isArray(obj.holdings)) return null;
  return obj.holdings as PortfolioHolding[];
}

function parseTransactions(payload: unknown): PortfolioTransaction[] | null {
  if (typeof payload !== "object" || payload === null) return null;
  const obj = payload as Record<string, unknown>;
  if (!Array.isArray(obj.transactions)) return null;
  return obj.transactions as PortfolioTransaction[];
}

function parseReturns(payload: unknown): PortfolioReturns | null {
  if (typeof payload !== "object" || payload === null) return null;
  const obj = payload as Record<string, unknown>;
  return {
    summary: (obj.summary as PortfolioSummary) ?? null,
    holdings: Array.isArray(obj.holdings) ? (obj.holdings as HoldingReturn[]) : [],
    history: Array.isArray(obj.history) ? (obj.history as PortfolioSnapshot[]) : [],
  };
}

// -- API calls ------------------------------------------------------------

export function fetchHoldings(): Promise<PortfolioHolding[] | null> {
  return apiGet("/api/portfolio/holdings", parseHoldings);
}

export function fetchTransactions(holdingId?: string, limit = 100): Promise<PortfolioTransaction[] | null> {
  const params = new URLSearchParams();
  if (holdingId) params.set("holding_id", holdingId);
  params.set("limit", String(limit));
  return apiGet(`/api/portfolio/transactions?${params.toString()}`, parseTransactions);
}

export function fetchReturns(days = 365): Promise<PortfolioReturns | null> {
  return apiGet(`/api/portfolio/returns?days=${days}`, parseReturns);
}

export type TransactionPayload = {
  holding_id: string;
  transaction_type: "buy" | "sell" | "dividend" | "split";
  quantity: number;
  price_per_unit: number;
  fee?: number;
  transaction_date: string;
  note?: string | null;
};

export function createTransaction(payload: TransactionPayload): Promise<PortfolioTransaction | null> {
  return apiPost("/api/portfolio/transactions", payload, (p) =>
    typeof p === "object" && p !== null ? (p as PortfolioTransaction) : null,
  );
}
