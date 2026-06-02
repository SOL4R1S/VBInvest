export type Watchlist = {
  readonly id: string;
  readonly slug: string;
  readonly name: string;
  readonly symbols: readonly string[];
};

export const DEFAULT_WATCHLISTS: readonly Watchlist[] = [
  { id: "semiconductor-core", slug: "semiconductor-core", name: "Semiconductor Core", symbols: ["NVDA", "005930.KS", "000660.KS"] },
];

type JsonObject = Record<string, unknown>;

function isRecord(value: unknown): value is JsonObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function stringField(value: JsonObject, key: string): string | null {
  const candidate = value[key];
  return typeof candidate === "string" ? candidate : null;
}

function symbolsField(value: JsonObject): readonly string[] {
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
  const init = authFetchInit();
  const response = init === undefined ? await fetch("/api/watchlists") : await fetch("/api/watchlists", init);
  if (!response.ok) {
    return fallbackToDemo ? DEFAULT_WATCHLISTS : [];
  }
  const payload = await response.json();
  const parsed = parseWatchlistPayload(payload);
  if (parsed === null) {
    return fallbackToDemo ? DEFAULT_WATCHLISTS : [];
  }
  return parsed;
}

export async function createWatchlist(name: string): Promise<Watchlist | null> {
  const headers = authHeaders({ "Content-Type": "application/json" });
  const response = await fetch("/api/watchlists", {
    method: "POST",
    headers,
    body: JSON.stringify({ name }),
  });
  if (!response.ok) {
    return null;
  }
  const payload = await response.json();
  return parseWatchlist(payload);
}

export async function addAssetToWatchlist(watchlistId: string, symbol: string): Promise<Watchlist | null> {
  const headers = authHeaders({ "Content-Type": "application/json" });
  const response = await fetch(`/api/watchlists/${encodeURIComponent(watchlistId)}/assets`, {
    method: "POST",
    headers,
    body: JSON.stringify({ symbol }),
  });
  if (!response.ok) {
    return null;
  }
  const payload = await response.json();
  const parsed = parseWatchlistPayload(payload);
  if (parsed === null) {
    return null;
  }
  return parsed.length > 0 ? parsed[0] : null;
}

export async function deleteAssetFromWatchlist(watchlistId: string, symbol: string): Promise<Watchlist | null> {
  const response = await fetch(`/api/watchlists/${encodeURIComponent(watchlistId)}/assets/${encodeURIComponent(symbol)}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!response.ok) {
    return null;
  }
  const payload = await response.json();
  const parsed = parseWatchlistPayload(payload);
  if (parsed === null) {
    return null;
  }
  return parsed.length > 0 ? parsed[0] : null;
}

function authHeaders(base: Record<string, string> = {}): Record<string, string> {
  const token = localSessionToken();
  if (!token) {
    return base;
  }
  return { ...base, Authorization: `Bearer ${token}` };
}

function authFetchInit(): RequestInit | undefined {
  const token = localSessionToken();
  if (!token) {
    return undefined;
  }
  return { headers: { Authorization: `Bearer ${token}` } };
}

function localSessionToken(): string {
  if (typeof window === "undefined") {
    return "";
  }
  return window.__VBINVEST_LOCAL_SESSION_TOKEN__ ?? "";
}

declare global {
  interface Window {
    __VBINVEST_LOCAL_SESSION_TOKEN__?: string;
  }
}
