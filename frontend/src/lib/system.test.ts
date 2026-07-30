import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { sendShutdownBeacon, shutdownSystem } from "./system";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("shutdownSystem", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    delete window.__VBINVEST_LOCAL_SESSION_TOKEN__;
  });

  it("returns ok on successful shutdown", async () => {
    vi.mocked(fetch).mockResolvedValue(jsonResponse({}));
    const result = await shutdownSystem();
    expect(result).toEqual({ ok: true, message: null });
  });

  it("returns session error on 401", async () => {
    vi.mocked(fetch).mockResolvedValue(jsonResponse({}, 401));
    const result = await shutdownSystem();
    expect(result.ok).toBe(false);
    expect(result.message).toContain("로컬 세션");
  });

  it("returns disabled message on 503", async () => {
    vi.mocked(fetch).mockResolvedValue(jsonResponse({}, 503));
    const result = await shutdownSystem();
    expect(result.ok).toBe(false);
    expect(result.message).toContain("비활성화");
  });

  it("returns generic error on other failures", async () => {
    vi.mocked(fetch).mockResolvedValue(jsonResponse({}, 500));
    const result = await shutdownSystem();
    expect(result.ok).toBe(false);
    expect(result.message).toContain("실패");
  });

  it("handles network errors gracefully", async () => {
    vi.mocked(fetch).mockRejectedValue(new Error("network down"));
    const result = await shutdownSystem();
    expect(result.ok).toBe(false);
    expect(result.message).toContain("네트워크");
  });
});

describe("sendShutdownBeacon", () => {
  afterEach(() => {
    delete window.__VBINVEST_LOCAL_SESSION_TOKEN__;
    vi.restoreAllMocks();
  });

  it("returns false when no token", () => {
    expect(sendShutdownBeacon()).toBe(false);
  });

  it("sends beacon when token exists", () => {
    window.__VBINVEST_LOCAL_SESSION_TOKEN__ = "tok-beacon";
    const sendBeacon = vi.fn(() => true);
    vi.stubGlobal("navigator", { sendBeacon });
    const result = sendShutdownBeacon();
    expect(result).toBe(true);
    expect(sendBeacon).toHaveBeenCalledWith(
      "/api/system/shutdown-beacon",
      expect.any(Blob),
    );
  });
});
