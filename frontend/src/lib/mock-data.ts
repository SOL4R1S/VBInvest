import { DEFAULT_RESEARCH } from "@/lib/research";

export type ChartPoint = {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  ma5: number;
  ma20: number;
  ma50: number;
  ma120: number;
  rsi14: number;
};

export type AssetCard = {
  symbol: string;
  displayNameKo: string;
  opinion: typeof DEFAULT_RESEARCH.opinion;
  price: number;
  delta1d: string;
  delta1m: string;
};

export const WATCHLISTS = [
  { id: "wl-ai-memory", name: "AI Memory", symbols: ["NVDA", "005930.KS"] },
  { id: "wl-semiconductor-core", name: "Semiconductor Core", symbols: ["NVDA", "005930.KS", "000660.KS"] },
];

export const ASSETS: Record<string, AssetCard> = {
  NVDA: {
    symbol: "NVDA",
    displayNameKo: "엔비디아",
    opinion: "아웃퍼폼",
    price: 145.28,
    delta1d: "+2.14%",
    delta1m: "+11.62%",
  },
  "005930.KS": {
    symbol: "005930.KS",
    displayNameKo: "삼성전자",
    opinion: "중립",
    price: 78200,
    delta1d: "-0.31%",
    delta1m: "+4.03%",
  },
};

export function buildSeries(symbol: string): ChartPoint[] {
  const seed = symbol === "NVDA" ? 145 : 78200;
  return Array.from({ length: 180 }, (_, index) => {
    const trend = index * (symbol === "NVDA" ? 0.22 : 18);
    const noise = Math.sin(index / 4) * (symbol === "NVDA" ? 2.2 : 180);
    const close = seed + trend + noise;
    const open = close - (symbol === "NVDA" ? 0.8 : 40);
    const high = Math.max(open, close) + (symbol === "NVDA" ? 1.8 : 130);
    const low = Math.min(open, close) - (symbol === "NVDA" ? 1.7 : 120);
    return {
      time: new Date(Date.UTC(2026, 0, index + 1)).toISOString().slice(0, 10),
      open,
      high,
      low,
      close,
      volume: 1_000_000 + index * 12_000,
      ma5: close - (symbol === "NVDA" ? 0.6 : 260),
      ma20: close - (symbol === "NVDA" ? 1.4 : 520),
      ma50: close - (symbol === "NVDA" ? 2.8 : 740),
      ma120: close - (symbol === "NVDA" ? 4.4 : 960),
      rsi14: 42 + (index % 18),
    };
  });
}
