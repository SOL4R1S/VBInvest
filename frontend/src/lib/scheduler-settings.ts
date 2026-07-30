import { authHeaders } from "@/lib/auth";
import { boolField, isRecord, readJsonPayload, stringOrEmpty } from "@/lib/guards";

export type SchedulerSettings = {
  readonly dailyRefreshEnabled: boolean;
  readonly weeklyPrecomputeEnabled: boolean;
  readonly watchlist: string;
  readonly includeNews: boolean;
};

type SchedulerSettingsPatch = {
  readonly dailyRefreshEnabled?: boolean;
  readonly weeklyPrecomputeEnabled?: boolean;
  readonly watchlist?: string;
  readonly includeNews?: boolean;
};

export const FALLBACK_SCHEDULER_SETTINGS: SchedulerSettings = {
  dailyRefreshEnabled: true,
  weeklyPrecomputeEnabled: false,
  watchlist: "",
  includeNews: true,
};

export async function fetchSchedulerSettings(): Promise<SchedulerSettings | null> {
  const response = await fetch("/api/scheduler/settings", { headers: authHeaders() });
  if (!response.ok) {
    return null;
  }
  const payload = await readJsonPayload(response);
  if (payload === null) {
    return null;
  }
  return parseSchedulerSettings(payload);
}

export async function patchSchedulerSettings(payload: SchedulerSettingsPatch): Promise<SchedulerSettings | null> {
  const encoded = encodePatchPayload(payload);
  if (Object.keys(encoded).length === 0) {
    return null;
  }
  const response = await fetch("/api/scheduler/settings", {
    method: "PATCH",
    headers: { ...authHeaders(), "Content-Type": "application/json" },
    body: JSON.stringify(encoded),
  });
  if (!response.ok) {
    return null;
  }
  const responsePayload = await readJsonPayload(response);
  if (responsePayload === null) {
    return null;
  }
  return parseSchedulerSettings(responsePayload);
}

export function parseSchedulerSettings(payload: unknown): SchedulerSettings | null {
  if (!isRecord(payload)) {
    return null;
  }
  const dailyRefreshEnabled = boolField(payload, "daily_refresh_enabled");
  const weeklyPrecomputeEnabled = boolField(payload, "weekly_precompute_enabled");
  if (dailyRefreshEnabled === null || weeklyPrecomputeEnabled === null) {
    return null;
  }
  return {
    dailyRefreshEnabled,
    weeklyPrecomputeEnabled,
    watchlist: stringOrEmpty(payload.watchlist),
    includeNews: boolField(payload, "include_news") ?? true,
  };
}

function encodePatchPayload(payload: SchedulerSettingsPatch): Record<string, boolean | string> {
  const encoded: Record<string, boolean | string> = {};
  if (payload.dailyRefreshEnabled !== undefined) {
    encoded.daily_refresh_enabled = payload.dailyRefreshEnabled;
  }
  if (payload.weeklyPrecomputeEnabled !== undefined) {
    encoded.weekly_precompute_enabled = payload.weeklyPrecomputeEnabled;
  }
  if (payload.watchlist !== undefined) {
    encoded.watchlist = payload.watchlist;
  }
  if (payload.includeNews !== undefined) {
    encoded.include_news = payload.includeNews;
  }
  return encoded;
}
