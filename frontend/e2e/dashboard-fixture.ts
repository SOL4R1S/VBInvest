import type { Page } from "@playwright/test";

export async function routeDashboardData(page: Page): Promise<void> {
  const nvdaHistory = buildHistory({
    startClose: 910,
    startDate: Date.UTC(2026, 3, 1),
    dayCount: 90,
    symbolOffset: 7,
  });
  const samsungHistory = buildHistory({
    startClose: 78000,
    startDate: Date.UTC(2026, 3, 1),
    dayCount: 90,
    symbolOffset: 3,
  });
  const latestNvda = lastPoint(nvdaHistory);
  const latestSamsung = lastPoint(samsungHistory);

  await page.route("**/api/watchlists/semiconductor-core/dashboard?**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        watchlist: "semiconductor-core",
        count: 2,
        items: [
          {
            asset: { symbol: "NVDA", display_name_ko: "엔비디아", currency: "USD" },
            latest: {
              date: latestNvda.date,
              close: latestNvda.close,
              return_1d: 0.0388,
              return_1m: 0.125,
              ma5: latestNvda.ma5,
              ma20: latestNvda.ma20,
              ma50: latestNvda.ma50,
              ma120: latestNvda.ma120,
              rsi14: latestNvda.rsi14,
            },
            opinion: "아웃퍼폼",
            history: nvdaHistory,
          },
          {
            asset: { symbol: "005930.KS", display_name_ko: "삼성전자", currency: "KRW" },
            latest: {
              date: latestSamsung.date,
              close: latestSamsung.close,
              return_1d: -0.005,
              return_1m: 0.031,
              ma5: latestSamsung.ma5,
              ma20: latestSamsung.ma20,
              ma50: latestSamsung.ma50,
              ma120: latestSamsung.ma120,
              rsi14: latestSamsung.rsi14,
            },
            opinion: "중립",
            history: samsungHistory,
          },
        ],
      }),
    });
  });
}

type HistoryOptions = {
  readonly startClose: number;
  readonly startDate: number;
  readonly dayCount: number;
  readonly symbolOffset: number;
};

type FixtureHistoryPoint = {
  readonly date: string;
  readonly open: number;
  readonly high: number;
  readonly low: number;
  readonly close: number;
  readonly volume: number;
  readonly ma5: number;
  readonly ma20: number;
  readonly ma50: number;
  readonly ma120: number;
  readonly rsi14: number;
};

function buildHistory(options: HistoryOptions): readonly FixtureHistoryPoint[] {
  return Array.from({ length: options.dayCount }, (_, index) => {
    const close = options.startClose + index * (options.startClose * 0.0018) + Math.sin((index + options.symbolOffset) / 5) * (options.startClose * 0.015);
    const open = close * (1 - 0.004 + (index % 3) * 0.002);
    const high = Math.max(open, close) * 1.008;
    const low = Math.min(open, close) * 0.992;
    return {
      date: new Date(options.startDate + index * 86_400_000).toISOString().slice(0, 10),
      open: round(open),
      high: round(high),
      low: round(low),
      close: round(close),
      volume: 1_000_000 + index * 12_000,
      ma5: round(close * 0.995),
      ma20: round(close * 0.982),
      ma50: round(close * 0.957),
      ma120: round(close * 0.93),
      rsi14: round(48 + Math.sin(index / 7) * 16),
    };
  });
}

function round(value: number): number {
  return Number(value.toFixed(2));
}

function lastPoint(points: readonly FixtureHistoryPoint[]): FixtureHistoryPoint {
  const point = points[points.length - 1];
  if (point === undefined) {
    throw new Error("dashboard fixture history is empty");
  }
  return point;
}
