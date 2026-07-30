/**
 * Centralized HTTP client for all VBinvest API calls.
 *
 * - Automatically attaches the local session Authorization header.
 * - Normalizes error handling: returns `null` on non-ok responses
 *   (callers decide fallback behavior).
 * - JSON parsing is safe (SyntaxError → null).
 */

import { authHeaders } from "@/lib/auth";
import { readJsonPayload } from "@/lib/guards";

export type ApiResult<T> = { readonly ok: true; readonly data: T } | { readonly ok: false; readonly status: number };

export async function apiGet<T>(url: string, parse: (payload: unknown) => T | null): Promise<T | null> {
  const response = await fetch(url, { headers: authHeaders() });
  if (!response.ok) {
    return null;
  }
  const payload = await readJsonPayload(response);
  return parse(payload);
}

export async function apiPost<T>(
  url: string,
  body: unknown,
  parse: (payload: unknown) => T | null,
  signal?: AbortSignal,
): Promise<T | null> {
  const response = await fetch(url, {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(body),
    signal,
  });
  if (!response.ok) {
    return null;
  }
  const payload = await readJsonPayload(response);
  return parse(payload);
}

export async function apiPatch<T>(
  url: string,
  body: unknown,
  parse: (payload: unknown) => T | null,
): Promise<T | null> {
  const response = await fetch(url, {
    method: "PATCH",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    return null;
  }
  const payload = await readJsonPayload(response);
  return parse(payload);
}

export async function apiDelete<T>(
  url: string,
  parse: (payload: unknown) => T | null,
): Promise<T | null> {
  const response = await fetch(url, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!response.ok) {
    return null;
  }
  const payload = await readJsonPayload(response);
  return parse(payload);
}

/**
 * Low-level fetch wrapper that attaches auth headers automatically.
 * Returns the raw Response so callers can implement custom error handling
 * (e.g. reading error bodies, status-specific fallbacks).
 */
export async function apiFetch(url: string, init?: RequestInit): Promise<Response> {
  return fetch(url, {
    ...init,
    headers: authHeaders(init?.headers as Record<string, string> | undefined),
  });
}
