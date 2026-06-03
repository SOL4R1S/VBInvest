import { render } from "@testing-library/react";
import { createChart } from "lightweight-charts";
import { describe, expect, it, vi } from "vitest";

import { ChartShell } from "./ChartShell";

const labels = {
  line: "라인",
  candle: "캔들",
  reset: "줌 초기화",
  modeLine: "라인",
  modeCandle: "캔들",
  resetView: "줌 초기화",
  legend: "범례",
};

describe("ChartShell", () => {
  it("does not plot missing MA120 warmup values as close prices", () => {
    vi.clearAllMocks();

    render(
      <ChartShell
        symbol="NVDA"
        labels={labels}
        points={[
          {
            time: "2026-01-02",
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
            time: "2026-06-02",
            open: 138,
            high: 142,
            low: 137,
            close: 140,
            volume: 2000,
            ma5: 138,
            ma20: 132,
            ma50: 125,
            ma120: 118,
            rsi14: 62,
          },
        ]}
      />,
    );

    const chart = vi.mocked(createChart).mock.results[0]?.value;
    const setDataCalls = chart.addSeries.mock.results[0]?.value.setData.mock.calls;

    expect(setDataCalls[5]?.[0]).toEqual([{ time: { year: 2026, month: 6, day: 2 }, value: 118 }]);
    expect(setDataCalls[6]?.[0]).toEqual([{ time: { year: 2026, month: 6, day: 2 }, value: 62 }]);
  });
});
