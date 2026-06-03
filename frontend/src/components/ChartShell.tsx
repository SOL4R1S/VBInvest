"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  CandlestickSeries,
  ColorType,
  createChart,
  CrosshairMode,
  HistogramSeries,
  LineSeries,
  type BusinessDay,
  type IChartApi,
  type ISeriesApi,
  type LogicalRange,
  type LogicalRangeChangeEventHandler,
} from "lightweight-charts";
import type { ChartPoint } from "@/lib/dashboard-data";
import type { LocalizedLabels } from "@/lib/i18n";

type Props = {
  symbol: string;
  points: ChartPoint[];
  labels: LocalizedLabels["chart"];
};

type Mode = "line" | "candle";

const PRICE_LINE_WIDTH = 2;
const RSI_LINE_WIDTH = 1;
const PRICE_PANE_INDEX = 0;
const INDICATOR_PANE_INDEX = 1;
const SERIES_COLORS = {
  close: "#111714",
  ma5: "#16823a",
  ma20: "#2458d3",
  ma50: "#b86700",
  ma120: "#7c5cc4",
  rsi14: "#fb7185",
  volume: "#38bdf8",
} as const;

const LEGEND_ITEMS = [
  ["legend-close", "종가", SERIES_COLORS.close],
  ["legend-ma5", "MA5", SERIES_COLORS.ma5],
  ["legend-ma20", "MA20", SERIES_COLORS.ma20],
  ["legend-ma50", "MA50", SERIES_COLORS.ma50],
  ["legend-ma120", "MA120", SERIES_COLORS.ma120],
  ["legend-rsi14", "RSI14", SERIES_COLORS.rsi14],
] as const;

function formatLogicalRange(range: LogicalRange | null) {
  return {
    from: range ? range.from.toFixed(2) : "pending",
    to: range ? range.to.toFixed(2) : "pending",
  };
}

export function ChartShell({ symbol, points, labels }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const lineRef = useRef<ISeriesApi<"Line"> | null>(null);
  const ma5Ref = useRef<ISeriesApi<"Line"> | null>(null);
  const ma20Ref = useRef<ISeriesApi<"Line"> | null>(null);
  const ma50Ref = useRef<ISeriesApi<"Line"> | null>(null);
  const ma120Ref = useRef<ISeriesApi<"Line"> | null>(null);
  const volumeRef = useRef<ISeriesApi<"Histogram"> | null>(null);
  const [mode, setMode] = useState<Mode>("candle");
  const [visibleRange, setVisibleRange] = useState(() => formatLogicalRange(null));
  const [paneCount, setPaneCount] = useState(1);

  const priceData = useMemo(
    () =>
      points.map((point) => {
        const [year, month, day] = point.time.split("-").map((value) => Number(value));
        return {
          time: { year, month, day } satisfies BusinessDay,
          open: point.open,
          high: point.high,
          low: point.low,
          close: point.close,
        };
      }),
    [points],
  );

  useEffect(() => {
    if (!containerRef.current) {
      return;
    }
    const chart = createChart(containerRef.current, {
      autoSize: true,
      layout: {
        background: { type: ColorType.Solid, color: "#fffdf8" },
        textColor: "#454745",
      },
      grid: {
        vertLines: { color: "#eee7dc" },
        horzLines: { color: "#eee7dc" },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
      },
      rightPriceScale: {
        borderColor: "#ddd5c7",
      },
      timeScale: {
        borderColor: "#ddd5c7",
        timeVisible: true,
        secondsVisible: false,
      },
      handleScale: {
        mouseWheel: true,
        pinch: true,
        axisPressedMouseMove: true,
      },
      handleScroll: {
        mouseWheel: true,
        pressedMouseMove: true,
        horzTouchDrag: true,
        vertTouchDrag: true,
      },
    });
    chartRef.current = chart;

    const candle = chart.addSeries(CandlestickSeries, {
      upColor: "#22c55e",
      downColor: "#ef4444",
      borderVisible: true,
      wickUpColor: "#22c55e",
      wickDownColor: "#ef4444",
    }, PRICE_PANE_INDEX);
    const line = chart.addSeries(LineSeries, { color: SERIES_COLORS.close, lineWidth: PRICE_LINE_WIDTH, visible: false }, PRICE_PANE_INDEX);
    const ma5 = chart.addSeries(LineSeries, { color: SERIES_COLORS.ma5, lineWidth: PRICE_LINE_WIDTH }, PRICE_PANE_INDEX);
    const ma20 = chart.addSeries(LineSeries, { color: SERIES_COLORS.ma20, lineWidth: PRICE_LINE_WIDTH }, PRICE_PANE_INDEX);
    const ma50 = chart.addSeries(LineSeries, { color: SERIES_COLORS.ma50, lineWidth: PRICE_LINE_WIDTH }, PRICE_PANE_INDEX);
    const ma120 = chart.addSeries(LineSeries, { color: SERIES_COLORS.ma120, lineWidth: PRICE_LINE_WIDTH }, PRICE_PANE_INDEX);
    const rsi = chart.addSeries(LineSeries, {
      color: SERIES_COLORS.rsi14,
      lineWidth: RSI_LINE_WIDTH,
      priceScaleId: "right",
    }, INDICATOR_PANE_INDEX);
    const volume = chart.addSeries(HistogramSeries, {
      color: "rgba(56, 189, 248, 0.45)",
      priceFormat: { type: "volume" },
      priceScaleId: "volume",
    }, INDICATOR_PANE_INDEX);
    chart.priceScale("right", INDICATOR_PANE_INDEX).applyOptions({
      scaleMargins: { top: 0.08, bottom: 0.12 },
    });
    chart.priceScale("volume", INDICATOR_PANE_INDEX).applyOptions({
      scaleMargins: { top: 0.62, bottom: 0 },
      visible: false,
    });
    candle.setData(priceData);
    const seriesTime = (point: ChartPoint) => {
      const [year, month, day] = point.time.split("-").map((value) => Number(value));
      return { year, month, day } satisfies BusinessDay;
    };
    const nullableLineData = (selectValue: (point: ChartPoint) => number | null) =>
      points.flatMap((point) => {
        const value = selectValue(point);
        return value === null ? [] : [{ time: seriesTime(point), value }];
      });
    line.setData(points.map((point) => ({ time: seriesTime(point), value: point.close })));
    ma5.setData(nullableLineData((point) => point.ma5));
    ma20.setData(nullableLineData((point) => point.ma20));
    ma50.setData(nullableLineData((point) => point.ma50));
    ma120.setData(nullableLineData((point) => point.ma120));
    rsi.setData(nullableLineData((point) => point.rsi14));
    volume.setData(points.map((point) => ({ time: seriesTime(point), value: point.volume, color: point.close >= point.open ? "rgba(34,197,94,0.35)" : "rgba(239,68,68,0.35)" })));

    const syncPaneLayout = () => {
      const panes = chart.panes();
      panes[PRICE_PANE_INDEX]?.setHeight(470);
      panes[INDICATOR_PANE_INDEX]?.setHeight(170);
      setPaneCount(panes.length);
    };
    syncPaneLayout();
    const paneFrame = window.requestAnimationFrame(syncPaneLayout);

    candleRef.current = candle;
    lineRef.current = line;
    ma5Ref.current = ma5;
    ma20Ref.current = ma20;
    ma50Ref.current = ma50;
    ma120Ref.current = ma120;
    volumeRef.current = volume;

    chart.timeScale().fitContent();
    setVisibleRange(formatLogicalRange(chart.timeScale().getVisibleLogicalRange()));

    const rangeHandler: LogicalRangeChangeEventHandler = (range) => {
      setVisibleRange(formatLogicalRange(range));
    };
    chart.timeScale().subscribeVisibleLogicalRangeChange(rangeHandler);

    const resizeObserver = new ResizeObserver(() => {
      setVisibleRange(formatLogicalRange(chart.timeScale().getVisibleLogicalRange()));
    });
    resizeObserver.observe(containerRef.current);

    return () => {
      window.cancelAnimationFrame(paneFrame);
      chart.timeScale().unsubscribeVisibleLogicalRangeChange(rangeHandler);
      resizeObserver.disconnect();
      chart.remove();
      chartRef.current = null;
      candleRef.current = null;
      lineRef.current = null;
      ma5Ref.current = null;
      ma20Ref.current = null;
      ma50Ref.current = null;
      ma120Ref.current = null;
      volumeRef.current = null;
      setPaneCount(1);
    };
  }, [points, priceData]);

  useEffect(() => {
    if (!chartRef.current) {
      return;
    }
    const candleVisible = mode === "candle";
    candleRef.current?.applyOptions({ visible: candleVisible });
    lineRef.current?.applyOptions({ visible: !candleVisible });
  }, [mode]);

  return (
    <section className="chart-shell" aria-label={`${symbol} 차트`}>
      <div className="chart-toolbar">
        <button type="button" className={mode === "line" ? "active" : ""} onClick={() => setMode("line")} data-testid="mode-line">
          {labels.line}
        </button>
        <button type="button" className={mode === "candle" ? "active" : ""} onClick={() => setMode("candle")} data-testid="mode-candle">
          {labels.candle}
        </button>
        <button type="button" onClick={() => chartRef.current?.timeScale().fitContent()} data-testid="chart-reset">
          {labels.reset}
        </button>
      </div>
      <div
        className="chart-frame"
        ref={containerRef}
        data-testid="chart-frame"
        data-chart-mode={mode}
        data-range-from={visibleRange.from}
        data-range-to={visibleRange.to}
        data-price-line-width={PRICE_LINE_WIDTH}
        data-rsi-line-width={RSI_LINE_WIDTH}
        data-pane-count={paneCount}
      />
      <div className="legend" aria-label={labels.legend}>
        {LEGEND_ITEMS.map(([testId, label, color]) => (
          <span key={testId} className="legend-item" data-testid={testId}>
            <span className="legend-swatch" style={{ backgroundColor: color }} aria-hidden="true" />
            {label}
          </span>
        ))}
      </div>
    </section>
  );
}
