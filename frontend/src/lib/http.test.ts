import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { apiDelete, apiFetch, apiGet, apiPatch, apiPost } from "./http";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

const identity = (payload: unknown) => payload as Record<string, unknown> | null;

describe("apiGet", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    delete window.__VBINVEST_LOCAL_SESSION_TOKEN__;
  });

  it("returns parsed data on ok response", async () => {
    vi.mocked(fetch).mockResolvedValue(jsonResponse({ id: 1 }));
    const result = await apiGet("/api/test", identity);
    expect(result).toEqual({ id: 1 });
    expect(fetch).toHaveBeenCalledWith("/api/test", expect.objectContaining({ headers: expect.any(Object) }));
  });

  it("returns null on non-ok response", async () => {
    vi.mocked(fetch).mockResolvedValue(jsonResponse({ detail: "nope" }, 404));
    const result = await apiGet("/api/test", identity);
    expect(result).toBeNull();
  });

  it("returns null when JSON is malformed", async () => {
    vi.mocked(fetch).mockResolvedValue(new Response("not json", { status: 200 }));
    const result = await apiGet("/api/test", identity);
    expect(result).toBeNull();
  });
});

describe("apiPost", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    delete window.__VBINVEST_LOCAL_SESSION_TOKEN__;
  });

  it("sends POST with JSON body", async () => {
    vi.mocked(fetch).mockResolvedValue(jsonResponse({ created: true }));
    const result = await apiPost("/api/items", { name: "test" }, identity);
    expect(result).toEqual({ created: true });
    expect(fetch).toHaveBeenCalledWith(
      "/api/items",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ name: "test" }),
      }),
    );
  });

  it("returns null on server error", async () => {
    vi.mocked(fetch).mockResolvedValue(jsonResponse({}, 500));
    const result = await apiPost("/api/items", {}, identity);
    expect(result).toBeNull();
  });
});

describe("apiPatch", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("sends PATCH with JSON body", async () => {
    vi.mocked(fetch).mockResolvedValue(jsonResponse({ updated: true }));
    const result = await apiPatch("/api/items/1", { name: "new" }, identity);
    expect(result).toEqual({ updated: true });
    expect(fetch).toHaveBeenCalledWith(
      "/api/items/1",
      expect.objectContaining({ method: "PATCH" }),
    );
  });
});

describe("apiDelete", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("sends DELETE request", async () => {
    vi.mocked(fetch).mockResolvedValue(jsonResponse({ deleted: true }));
    const result = await apiDelete("/api/items/1", identity);
    expect(result).toEqual({ deleted: true });
    expect(fetch).toHaveBeenCalledWith(
      "/api/items/1",
      expect.objectContaining({ method: "DELETE" }),
    );
  });
});

describe("apiFetch", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    delete window.__VBINVEST_LOCAL_SESSION_TOKEN__;
  });

  it("returns raw Response", async () => {
    const raw = jsonResponse({ ok: true });
    vi.mocked(fetch).mockResolvedValue(raw);
    const result = await apiFetch("/api/raw");
    expect(result).toBe(raw);
  });

  it("attaches auth header when token exists", async () => {
    window.__VBINVEST_LOCAL_SESSION_TOKEN__ = "tok-999";
    vi.mocked(fetch).mockResolvedValue(jsonResponse({}));
    await apiFetch("/api/secure", { method: "POST" });
    expect(fetch).toHaveBeenCalledWith(
      "/api/secure",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({ Authorization: "Bearer tok-999" }),
      }),
    );
  });
});
