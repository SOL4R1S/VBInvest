"use client";

/**
 * PortfolioReturnChart — line chart of total_return_pct over time.
 * Uses lightweight-charts LineSeries from portfolio snapshot history.
 */

import { useEffect, useRef } from "react";
import { ColorType, createChart, LineSeries, type IChartApi } from "lightweight-charts";
import type { PortfolioSnapshot } from "@/lib/portfolio";

type Props = {
  readonly history: readonly PortfolioSnapshot[];
};

export function PortfolioReturnChart({ history }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container || history.length === 0) return;

    const chart = createChart(container, {
      width: container.clientWidth,
      height: 220,
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "#64748b",
        fontSize: 11,
      },
      grid: {
        vertLines: { visible: false },
        horzLines: { color: "#f1f5f9" },
      },
      crosshair: { mode: 0 },
      rightPriceScale: { borderVisible: false },
      timeScale: { borderVisible: false },
    });
    chartRef.current = chart;

    const series = chart.addSeries(LineSeries, {
      color: "#2563eb",
      lineWidth: 2,
      priceFormat: { type: "percent", precision: 1, minMove: 0.1 },
    });

    const points = history
      .slice()
      .sort((a, b) => a.snapshot_date.localeCompare(b.snapshot_date))
      .map((snap) => ({
        time: snap.snapshot_date as string,
        value: snap.total_return_pct,
      }));

    series.setData(points);
    chart.timeScale().fitContent();

    const handleResize = () => {
      chart.applyOptions({ width: container.clientWidth });
    };
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
      chartRef.current = null;
    };
  }, [history]);

  if (history.length === 0) {
    return <p className="subtle">수익률 이력이 없습니다. 스냅샷이 쌓이면 차트가 표시됩니다.</p>;
  }

  return (
    <div>
      <h3 style={{ margin: "0 0 0.5rem", fontSize: "0.875rem", fontWeight: 600 }}>수익률 추이</h3>
      <div ref={containerRef} aria-label="포트폴리오 수익률 추이 차트" role="img" />
    </div>
  );
}
