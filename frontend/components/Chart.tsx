"use client";

import { useMemo, useState } from "react";
import type { DashboardItem, ChartPoint } from "../lib/types";

type Props = {
  items: DashboardItem[];
  symbol: string;
  onReset: () => void;
  onZoomChange: (range: { start: string; end: string }) => void;
};

function fallbackHistory(): ChartPoint[] {
  return Array.from({ length: 90 }, (_, index) => {
    const close = 100 + index * 2 + Math.sin(index / 6) * 8;
    return {
      date: `2026-03-${String((index % 30) + 1).padStart(2, "0")}`,
      close,
      open: close - 1.5,
      high: close + 4,
      low: close - 5,
      volume: 1000 + index * 25,
      ma5: close - 1,
      ma20: close - 2,
      ma50: close - 3,
      ma120: close - 4,
      rsi: 45 + Math.sin(index / 8) * 15,
    };
  });
}

export function Chart({ items, symbol, onReset, onZoomChange }: Props) {
  const [zoom, setZoom] = useState(1);
  const [offset, setOffset] = useState(0);

  const history = useMemo(() => {
    const first = items[0];
    const source = (first?.latest ? [first.latest] : []) as Array<Record<string, string | number>>;
    if (source.length === 0) return fallbackHistory();
    return source.map((entry, index) => ({
      date: String(entry.date ?? `2026-06-${String(index + 1).padStart(2, "0")}`),
      close: Number(entry.close ?? entry.adjusted_close ?? 100),
      open: Number(entry.open ?? entry.close ?? 100) - 1,
      high: Number(entry.high ?? entry.close ?? 100) + 3,
      low: Number(entry.low ?? entry.close ?? 100) - 3,
      volume: Number(entry.volume ?? 1000),
      ma5: Number(entry.ma5 ?? entry.close ?? 100),
      ma20: Number(entry.ma20 ?? entry.close ?? 100),
      ma50: Number(entry.ma50 ?? entry.close ?? 100),
      ma120: Number(entry.ma120 ?? entry.close ?? 100),
      rsi: Number(entry.rsi ?? 50),
    }));
  }, [items]);

  const visible = useMemo(() => {
    const size = Math.max(12, Math.floor(history.length / zoom));
    const end = Math.min(history.length, Math.max(size, size + offset));
    const start = Math.max(0, end - size);
    return history.slice(start, end);
  }, [history, offset, zoom]);

  const width = 1200;
  const height = 520;
  const prices = visible.map((point) => point.close);
  const min = Math.min(...prices) - 5;
  const max = Math.max(...prices) + 5;
  const step = width / Math.max(1, visible.length - 1);
  const scaleY = (value: number) => height - ((value - min) / (max - min)) * (height - 60) - 30;
  const path = visible.map((point, index) => `${index === 0 ? "M" : "L"} ${index * step} ${scaleY(point.close)}`).join(" ");

  function handleWheel(event: React.WheelEvent<SVGSVGElement>) {
    event.preventDefault();
    const direction = Math.sign(event.deltaY);
    const nextZoom = Math.min(6, Math.max(1, zoom + (direction > 0 ? -0.2 : 0.2)));
    setZoom(nextZoom);
    onZoomChange({
      start: visible[0]?.date ?? "",
      end: visible[visible.length - 1]?.date ?? "",
    });
  }

  function handleDrag(direction: number) {
    setOffset((value) => Math.min(0, Math.max(-(history.length - 12), value + direction)));
  }

  return (
    <section>
      <div className="chart-toolbar">
        <span>{symbol}</span>
        <button onClick={() => handleDrag(-4)}>◀ pan</button>
        <button onClick={() => handleDrag(4)}>pan ▶</button>
        <button
          onClick={() => {
            setZoom(1);
            setOffset(0);
            onReset();
          }}
        >
          줌 초기화
        </button>
      </div>
      <svg
        aria-label="price chart"
        role="img"
        viewBox={`0 0 ${width} ${height}`}
        onWheel={handleWheel}
        className="chart-svg"
      >
        <defs>
          <linearGradient id="priceFill" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="#7dd3fc" stopOpacity="0.5" />
            <stop offset="100%" stopColor="#7dd3fc" stopOpacity="0.05" />
          </linearGradient>
        </defs>
        <rect width={width} height={height} rx="16" fill="#08101d" />
        <path d={path} fill="none" stroke="url(#priceFill)" strokeWidth="3" vectorEffect="non-scaling-stroke" />
        <path d={path} fill="none" stroke="#7dd3fc" strokeWidth="2" vectorEffect="non-scaling-stroke" />
        {visible.map((point, index) => (
          <circle key={point.date} cx={index * step} cy={scaleY(point.close)} r="3" fill="#edf3ff" />
        ))}
      </svg>
      <div className="chart-meta">
        <p>매수/아웃퍼폼/중립/언더퍼폼/매도 레이블 지원</p>
        <p>{visible.length}개 캔들 표시, wheel zoom + drag pan + reset</p>
      </div>
    </section>
  );
}
