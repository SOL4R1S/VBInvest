import { describe, expect, it } from "vitest";

import { FALLBACK_SCHEDULER_SETTINGS, parseSchedulerSettings } from "./scheduler-settings";

describe("FALLBACK_SCHEDULER_SETTINGS", () => {
  it("has sensible defaults", () => {
    expect(FALLBACK_SCHEDULER_SETTINGS.dailyRefreshEnabled).toBe(true);
    expect(FALLBACK_SCHEDULER_SETTINGS.weeklyPrecomputeEnabled).toBe(false);
    expect(FALLBACK_SCHEDULER_SETTINGS.watchlist).toBe("");
    expect(FALLBACK_SCHEDULER_SETTINGS.includeNews).toBe(true);
  });
});

describe("parseSchedulerSettings", () => {
  it("parses a valid snake_case payload", () => {
    const result = parseSchedulerSettings({
      daily_refresh_enabled: true,
      weekly_precompute_enabled: false,
      watchlist: "semiconductor-core",
      include_news: true,
    });
    expect(result).toEqual({
      dailyRefreshEnabled: true,
      weeklyPrecomputeEnabled: false,
      watchlist: "semiconductor-core",
      includeNews: true,
    });
  });

  it("defaults includeNews to true when missing", () => {
    const result = parseSchedulerSettings({
      daily_refresh_enabled: false,
      weekly_precompute_enabled: true,
    });
    expect(result?.includeNews).toBe(true);
  });

  it("returns null for non-record payloads", () => {
    expect(parseSchedulerSettings(null)).toBeNull();
    expect(parseSchedulerSettings("str")).toBeNull();
    expect(parseSchedulerSettings([])).toBeNull();
  });

  it("returns null when required boolean fields are missing", () => {
    expect(parseSchedulerSettings({ watchlist: "x" })).toBeNull();
    expect(parseSchedulerSettings({ daily_refresh_enabled: "yes" })).toBeNull();
  });
});
