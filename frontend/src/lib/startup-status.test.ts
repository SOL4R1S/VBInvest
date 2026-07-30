import { describe, expect, it } from "vitest";

import {
  INITIAL_STARTUP_REFRESH,
  parseStartupRefresh,
  startupStatusLabel,
} from "./startup-status";

describe("INITIAL_STARTUP_REFRESH", () => {
  it("starts in checking state with zero counts", () => {
    expect(INITIAL_STARTUP_REFRESH.status).toBe("checking");
    expect(INITIAL_STARTUP_REFRESH.queued).toBe(0);
    expect(INITIAL_STARTUP_REFRESH.succeeded).toBe(0);
    expect(INITIAL_STARTUP_REFRESH.providerDisabled).toEqual([]);
  });
});

describe("parseStartupRefresh", () => {
  it("returns failed status for non-record payloads", () => {
    const result = parseStartupRefresh(null);
    expect(result.status).toBe("failed");
  });

  it("parses a running refresh payload", () => {
    const result = parseStartupRefresh({
      status: "running",
      queued: 2,
      running: 1,
      succeeded: 3,
      failed: 0,
      price_rows: 100,
      indicator_rows: 50,
      news_items: 10,
      disclosures: 5,
    });
    expect(result.status).toBe("running");
    expect(result.queued).toBe(2);
    expect(result.running).toBe(1);
    expect(result.succeeded).toBe(3);
    expect(result.priceRows).toBe(100);
    expect(result.indicatorRows).toBe(50);
    expect(result.newsItems).toBe(10);
    expect(result.disclosures).toBe(5);
  });

  it("parses provider_disabled entries", () => {
    const result = parseStartupRefresh({
      status: "partial",
      provider_disabled: [
        { symbol: "AAPL", provider: "yahoo", reason: "rate limited" },
      ],
    });
    expect(result.providerDisabled).toHaveLength(1);
    expect(result.providerDisabled[0].symbol).toBe("AAPL");
  });

  it("parses ticker_catalog status", () => {
    const result = parseStartupRefresh({
      status: "ready",
      ticker_catalog: { status: "loaded", count: 2500, source: "krx" },
    });
    expect(result.tickerCatalog).toEqual({
      status: "loaded",
      count: 2500,
      source: "krx",
    });
  });

  it("defaults missing numeric fields to 0", () => {
    const result = parseStartupRefresh({ status: "ready" });
    expect(result.priceRows).toBe(0);
    expect(result.newsItems).toBe(0);
  });
});

describe("startupStatusLabel", () => {
  it("returns Korean labels by default", () => {
    expect(startupStatusLabel("checking")).toBe("확인 중");
    expect(startupStatusLabel("running")).toBe("데이터 갱신 진행 중");
    expect(startupStatusLabel("ready")).toContain("완료");
    expect(startupStatusLabel("failed")).toContain("실패");
  });

  it("accepts custom labels", () => {
    const labels = {
      checking: "Checking...",
      running: "Running...",
      setupRequired: "Setup needed",
      ready: "Done",
      partial: "Partial",
      skipped: "Skipped",
      failed: "Failed",
    };
    expect(startupStatusLabel("running", labels)).toBe("Running...");
  });
});
