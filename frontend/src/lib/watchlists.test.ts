import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { DEFAULT_WATCHLISTS, fetchWatchlists } from "./watchlists";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("DEFAULT_WATCHLISTS", () => {
  it("contains the semiconductor core watchlist", () => {
    expect(DEFAULT_WATCHLISTS).toHaveLength(1);
    expect(DEFAULT_WATCHLISTS[0].slug).toBe("semiconductor-core");
    expect(DEFAULT_WATCHLISTS[0].symbols).toContain("NVDA");
  });
});

describe("fetchWatchlists", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("parses an array payload", async () => {
    vi.mocked(fetch).mockResolvedValue(
      jsonResponse([
        { id: "w1", slug: "w1", name: "Watch 1", symbols: ["AAPL"] },
        { id: "w2", slug: "w2", name: "Watch 2", symbols: [] },
      ]),
    );
    const result = await fetchWatchlists();
    expect(result).toHaveLength(2);
    expect(result[0].name).toBe("Watch 1");
  });

  it("parses a wrapped payload with watchlists key", async () => {
    vi.mocked(fetch).mockResolvedValue(
      jsonResponse({ watchlists: [{ id: "w1", slug: "w1", name: "W", symbols: ["TSLA"] }] }),
    );
    const result = await fetchWatchlists();
    expect(result).toHaveLength(1);
  });

  it("returns empty array on failure without fallback", async () => {
    vi.mocked(fetch).mockResolvedValue(jsonResponse({}, 500));
    const result = await fetchWatchlists(false);
    expect(result).toEqual([]);
  });

  it("returns defaults on failure with fallback", async () => {
    vi.mocked(fetch).mockResolvedValue(jsonResponse({}, 500));
    const result = await fetchWatchlists(true);
    expect(result).toEqual(DEFAULT_WATCHLISTS);
  });

  it("skips items missing required fields", async () => {
    vi.mocked(fetch).mockResolvedValue(
      jsonResponse([
        { id: "w1", name: "Valid", symbols: [] },
        { name: "No ID" },
        { id: "w3", symbols: [] },
      ]),
    );
    const result = await fetchWatchlists();
    expect(result).toHaveLength(1);
    expect(result[0].id).toBe("w1");
  });
});
