import { describe, expect, it } from "vitest";

import { parseDashboardPayload } from "./dashboard-data";

describe("parseDashboardPayload", () => {
  it("preserves missing moving-average warmup values instead of replacing them with close", () => {
    const model = parseDashboardPayload({
      items: [
        {
          asset: { symbol: "NVDA", display_name_ko: "엔비디아" },
          latest: {
            close: 140,
            ma5: 138,
            ma20: 132,
            ma50: null,
            ma120: null,
            rsi14: null,
          },
          opinion: "중립",
          history: [
            {
              date: "2026-01-02",
              open: 100,
              high: 102,
              low: 99,
              close: 101,
              volume: 1000,
              ma5: null,
              ma20: null,
              ma50: null,
              ma120: null,
              rsi14: null,
            },
            {
              date: "2026-06-02",
              open: 138,
              high: 142,
              low: 137,
              close: 140,
              volume: 2000,
              ma5: 138,
              ma20: 132,
              ma50: null,
              ma120: null,
              rsi14: 62,
            },
          ],
        },
      ],
    });

    expect(model?.series.NVDA[0]).toMatchObject({
      close: 101,
      ma5: null,
      ma20: null,
      ma50: null,
      ma120: null,
      rsi14: null,
    });
    expect(model?.series.NVDA[1]).toMatchObject({
      close: 140,
      ma5: 138,
      ma20: 132,
      ma50: null,
      ma120: null,
      rsi14: 62,
    });
  });
});
