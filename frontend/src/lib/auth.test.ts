import { afterEach, describe, expect, it } from "vitest";

import { authFetchInit, authHeaders, localSessionToken } from "./auth";

describe("localSessionToken", () => {
  afterEach(() => {
    delete window.__VBINVEST_LOCAL_SESSION_TOKEN__;
  });

  it("returns empty string when no token is set", () => {
    expect(localSessionToken()).toBe("");
  });

  it("returns the injected token", () => {
    window.__VBINVEST_LOCAL_SESSION_TOKEN__ = "tok-abc";
    expect(localSessionToken()).toBe("tok-abc");
  });
});

describe("authHeaders", () => {
  afterEach(() => {
    delete window.__VBINVEST_LOCAL_SESSION_TOKEN__;
  });

  it("returns base headers unchanged when no token", () => {
    expect(authHeaders({ "X-Custom": "1" })).toEqual({ "X-Custom": "1" });
  });

  it("adds Authorization header when token exists", () => {
    window.__VBINVEST_LOCAL_SESSION_TOKEN__ = "tok-xyz";
    const headers = authHeaders();
    expect(headers.Authorization).toBe("Bearer tok-xyz");
  });

  it("merges with existing base headers", () => {
    window.__VBINVEST_LOCAL_SESSION_TOKEN__ = "tok-xyz";
    const headers = authHeaders({ "Content-Type": "application/json" });
    expect(headers).toEqual({
      "Content-Type": "application/json",
      Authorization: "Bearer tok-xyz",
    });
  });
});

describe("authFetchInit", () => {
  afterEach(() => {
    delete window.__VBINVEST_LOCAL_SESSION_TOKEN__;
  });

  it("returns empty init when no token and no extra", () => {
    expect(authFetchInit()).toEqual({});
  });

  it("passes through extra init when no token", () => {
    expect(authFetchInit({ method: "POST" })).toEqual({ method: "POST" });
  });

  it("injects Authorization header when token exists", () => {
    window.__VBINVEST_LOCAL_SESSION_TOKEN__ = "tok-123";
    const init = authFetchInit({ method: "DELETE" });
    expect(init.method).toBe("DELETE");
    expect((init.headers as Record<string, string>).Authorization).toBe("Bearer tok-123");
  });
});
