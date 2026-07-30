import { apiGet, apiPatch } from "@/lib/http";
import { boolField, isRecord, stringOrEmpty } from "@/lib/guards";

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
  return apiGet("/api/scheduler/settings", parseSchedulerSettings);
}

export async function patchSchedulerSettings(payload: SchedulerSettingsPatch): Promise<SchedulerSettings | null> {
  const encoded = encodePatchPayload(payload);
  if (Object.keys(encoded).length === 0) {
    return null;
  }
  return apiPatch("/api/scheduler/settings", encoded, parseSchedulerSettings);
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
