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

type Props = {
  symbol: string;
  points: ChartPoint[];
};

type Mode = "line" | "candle";

const PRICE_LINE_WIDTH = 2;
const RSI_LINE_WIDTH = 1;
const PRICE_PANE_INDEX = 0;
const INDICATOR_PANE_INDEX = 1;

function formatLogicalRange(range: LogicalRange | null) {
  return {
    from: range ? range.from.toFixed(2) : "pending",
    to: range ? range.to.toFixed(2) : "pending",
  };
}

export function ChartShell({ symbol, points }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const lineRef = useRef<ISeriesApi<"Line"> | null>(null);
  const ma5Ref = useRef<ISeriesApi<"Line"> | null>(null);
  const ma20Ref = useRef<ISeriesApi<"Line"> | null>(null);
  const ma50Ref = useRef<ISeriesApi<"Line"> | null>(null);
  const ma120Ref = useRef<ISeriesApi<"Line"> | null>(null);
  const volumeRef = useRef<ISeriesApi<"Histogram"> | null>(null);
  const [mode, setMode] = useState<Mode>("line");
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
    const line = chart.addSeries(LineSeries, { color: "#111714", lineWidth: PRICE_LINE_WIDTH }, PRICE_PANE_INDEX);
    const ma5 = chart.addSeries(LineSeries, { color: "#16823a", lineWidth: PRICE_LINE_WIDTH }, PRICE_PANE_INDEX);
    const ma20 = chart.addSeries(LineSeries, { color: "#2458d3", lineWidth: PRICE_LINE_WIDTH }, PRICE_PANE_INDEX);
    const ma50 = chart.addSeries(LineSeries, { color: "#b86700", lineWidth: PRICE_LINE_WIDTH }, PRICE_PANE_INDEX);
    const ma120 = chart.addSeries(LineSeries, { color: "#7c5cc4", lineWidth: PRICE_LINE_WIDTH }, PRICE_PANE_INDEX);
    const rsi = chart.addSeries(LineSeries, {
      color: "#fb7185",
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
    line.setData(points.map((point) => ({ time: seriesTime(point), value: point.close })));
    ma5.setData(points.map((point) => ({ time: seriesTime(point), value: point.ma5 })));
    ma20.setData(points.map((point) => ({ time: seriesTime(point), value: point.ma20 })));
    ma50.setData(points.map((point) => ({ time: seriesTime(point), value: point.ma50 })));
    ma120.setData(points.map((point) => ({ time: seriesTime(point), value: point.ma120 })));
    rsi.setData(points.map((point) => ({ time: seriesTime(point), value: point.rsi14 })));
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
          라인
        </button>
        <button type="button" className={mode === "candle" ? "active" : ""} onClick={() => setMode("candle")} data-testid="mode-candle">
          캔들
        </button>
        <button type="button" onClick={() => chartRef.current?.timeScale().fitContent()} data-testid="chart-reset">
          줌 초기화
        </button>
      </div>
      <div
        className="chart-frame"
        ref={containerRef}
        data-testid="chart-frame"
        data-range-from={visibleRange.from}
        data-range-to={visibleRange.to}
        data-price-line-width={PRICE_LINE_WIDTH}
        data-rsi-line-width={RSI_LINE_WIDTH}
        data-pane-count={paneCount}
      />
      <div className="legend">상단 가격 · 하단 거래량/RSI14 · 5일선 · 20일선 · 50일선 · 120일선 · 휠 줌 · 드래그 팬</div>
    </section>
  );
}
