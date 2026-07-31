/**
 * Research history API client — fetch past research views for a symbol.
 */

import { apiGet } from "@/lib/http";

export type ResearchHistoryItem = {
  readonly target_slug: string;
  readonly opinion: string | null;
  readonly thesis: string | null;
  readonly confidence: number | null;
  readonly report_date: string | null;
  readonly created_at: string | null;
};

type ResearchHistoryResponse = {
  readonly symbol: string;
  readonly history: readonly ResearchHistoryItem[];
};

function parseResearchHistory(payload: unknown): ResearchHistoryResponse | null {
  if (typeof payload !== "object" || payload === null) return null;
  const obj = payload as Record<string, unknown>;
  if (!Array.isArray(obj.history)) return null;
  return {
    symbol: typeof obj.symbol === "string" ? obj.symbol : "",
    history: obj.history as ResearchHistoryItem[],
  };
}

export async function fetchResearchHistory(
  symbol: string,
  limit = 20,
): Promise<readonly ResearchHistoryItem[]> {
  const result = await apiGet(
    `/api/research/${encodeURIComponent(symbol)}/history?limit=${limit}`,
    parseResearchHistory,
  );
  return result?.history ?? [];
}
