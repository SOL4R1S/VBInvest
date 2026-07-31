/**
 * Alert rules API client — types + fetch helpers for price alert configuration.
 */

import { apiGet, apiPost, apiFetch } from "@/lib/http";

// -- types -------------------------------------------------------------

export type AlertCondition = "above" | "below" | "change_pct";

export interface AlertRule {
  readonly rule_id: string;
  readonly symbol: string;
  readonly condition: AlertCondition;
  readonly threshold: number;
  readonly enabled: boolean;
  readonly last_triggered_at: string | null;
  readonly created_at: string;
}

export interface AlertRuleCreatePayload {
  readonly symbol: string;
  readonly condition: AlertCondition;
  readonly threshold: number;
}

// -- parsers -----------------------------------------------------------

function parseAlertRules(payload: unknown): readonly AlertRule[] | null {
  if (!Array.isArray(payload)) return null;
  return payload as AlertRule[];
}

function parseAlertRule(payload: unknown): AlertRule | null {
  if (typeof payload !== "object" || payload === null) return null;
  return payload as AlertRule;
}

// -- API calls ---------------------------------------------------------

export async function fetchAlertRules(): Promise<readonly AlertRule[]> {
  return (await apiGet("/api/alert-rules", parseAlertRules)) ?? [];
}

export async function createAlertRule(payload: AlertRuleCreatePayload): Promise<AlertRule> {
  const result = await apiPost("/api/alert-rules", payload, parseAlertRule);
  if (result === null) throw new Error("failed to create alert rule");
  return result;
}

export async function updateAlertRule(
  ruleId: string,
  patch: { enabled?: boolean; threshold?: number },
): Promise<void> {
  const res = await apiFetch(`/api/alert-rules/${encodeURIComponent(ruleId)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(patch),
  });
  if (!res.ok) throw new Error(`update failed: ${res.status}`);
}

export async function deleteAlertRule(ruleId: string): Promise<void> {
  const res = await apiFetch(`/api/alert-rules/${encodeURIComponent(ruleId)}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error(`delete failed: ${res.status}`);
}

// -- display helpers ---------------------------------------------------

export const CONDITION_LABELS: Record<AlertCondition, string> = {
  above: "이상",
  below: "이하",
  change_pct: "일일 변동 ±%",
};
