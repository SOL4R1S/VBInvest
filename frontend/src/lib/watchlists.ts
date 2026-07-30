import { apiDelete, apiGet, apiPost } from "@/lib/http";
import { isRecord, stringField } from "@/lib/guards";

export type Watchlist = {
  readonly id: string;
  readonly slug: string;
  readonly name: string;
  readonly symbols: readonly string[];
};

export const DEFAULT_WATCHLISTS: readonly Watchlist[] = [
  { id: "semiconductor-core", slug: "semiconductor-core", name: "Semiconductor Core", symbols: ["NVDA", "005930.KS", "000660.KS"] },
];

function symbolsField(value: Record<string, unknown>): readonly string[] {
  const candidate = value["symbols"];
  if (!Array.isArray(candidate)) {
    return [];
  }
  return candidate.filter((item): item is string => typeof item === "string");
}

function parseWatchlist(value: unknown): Watchlist | null {
  if (!isRecord(value)) {
    return null;
  }
  const id = stringField(value, "id") ?? stringField(value, "watchlist_id") ?? stringField(value, "slug");
  if (!id) {
    return null;
  }
  const slug = stringField(value, "slug") ?? id;
  const name = stringField(value, "name");
  if (!name) {
    return null;
  }
  const symbols = symbolsField(value);
  return { id, slug, name, symbols };
}

function parseWatchlistPayload(payload: unknown): readonly Watchlist[] | null {
  if (Array.isArray(payload)) {
    const items = payload.map(parseWatchlist).filter((item): item is Watchlist => item !== null);
    return items;
  }
  if (!isRecord(payload)) {
    return null;
  }
  const parsedSingle = parseWatchlist(payload);
  if (parsedSingle !== null) {
    return [parsedSingle];
  }
  const candidates = [payload.watchlists, payload.items, payload.data].filter(Array.isArray) as readonly unknown[][];
  if (candidates.length === 0) {
    return null;
  }
  const parsed = candidates
    .flatMap((batch) => batch)
    .map(parseWatchlist)
    .filter((item): item is Watchlist => item !== null);
  return parsed;
}

export async function fetchWatchlists(fallbackToDemo = false): Promise<readonly Watchlist[]> {
  const parsed = await apiGet("/api/watchlists", parseWatchlistPayload);
  if (parsed === null) {
    return fallbackToDemo ? DEFAULT_WATCHLISTS : [];
  }
  return parsed;
}

export async function createWatchlist(name: string): Promise<Watchlist | null> {
  return apiPost("/api/watchlists", { name }, parseWatchlist);
}

export async function addAssetToWatchlist(watchlistId: string, symbol: string): Promise<Watchlist | null> {
  const parsed = await apiPost(
    `/api/watchlists/${encodeURIComponent(watchlistId)}/assets`,
    { symbol },
    parseWatchlistPayload,
  );
  if (parsed === null) {
    return null;
  }
  return parsed.length > 0 ? parsed[0] : null;
}

export async function deleteAssetFromWatchlist(watchlistId: string, symbol: string): Promise<Watchlist | null> {
  const parsed = await apiDelete(
    `/api/watchlists/${encodeURIComponent(watchlistId)}/assets/${encodeURIComponent(symbol)}`,
    parseWatchlistPayload,
  );
  if (parsed === null) {
    return null;
  }
  return parsed.length > 0 ? parsed[0] : null;
}
