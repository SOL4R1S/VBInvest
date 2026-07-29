/**
 * Centralized local session authentication.
 *
 * The VBinvest desktop app injects a session token into
 * `window.__VBINVEST_LOCAL_SESSION_TOKEN__` at startup.
 * Every API call should use `authHeaders()` or `authFetchInit()`
 * from this module instead of duplicating the logic.
 */

declare global {
  interface Window {
    __VBINVEST_LOCAL_SESSION_TOKEN__?: string;
  }
}

export function localSessionToken(): string {
  if (typeof window === "undefined") {
    return "";
  }
  return window.__VBINVEST_LOCAL_SESSION_TOKEN__ ?? "";
}

export function authHeaders(base: Record<string, string> = {}): Record<string, string> {
  const token = localSessionToken();
  if (!token) {
    return base;
  }
  return { ...base, Authorization: `Bearer ${token}` };
}

export function authFetchInit(extra?: RequestInit): RequestInit {
  const token = localSessionToken();
  if (!token) {
    return extra ?? {};
  }
  return {
    ...extra,
    headers: { ...(extra?.headers as Record<string, string> | undefined), Authorization: `Bearer ${token}` },
  };
}
