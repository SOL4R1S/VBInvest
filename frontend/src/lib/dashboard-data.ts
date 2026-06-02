import { DEFAULT_RESEARCH, normalizeOpinion, type Opinion } from "@/lib/research";

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
  opinion: Opinion;
  price: number;
  delta1d: string;
  delta1m: string;
  rsi14: number | null;
  ma5: number | null;
  ma20: number | null;
  ma50: number | null;
  ma120: number | null;
};

export type DashboardModel = {
  assets: Record<string, AssetCard>;
  series: Record<string, ChartPoint[]>;
  symbols: string[];
};

type JsonObject = Record<string, unknown>;

export const DEFAULT_WATCHLISTS = [
  { id: "semiconductor-core", name: "Semiconductor Core", symbols: ["NVDA", "005930.KS", "000660.KS"] },
];

export async function fetchDashboardData(slug: string): Promise<DashboardModel | null> {
  const response = await fetch(`/api/watchlists/${encodeURIComponent(slug)}/dashboard?days=260`);
  if (!response.ok) {
    return null;
  }
  return parseDashboardPayload(await response.json());
}

export function fallbackAsset(symbol: string): AssetCard {
  return {
    symbol,
    displayNameKo: symbol,
    opinion: DEFAULT_RESEARCH.opinion,
    price: 0,
    delta1d: "0.00%",
    delta1m: "0.00%",
    rsi14: null,
    ma5: null,
    ma20: null,
    ma50: null,
    ma120: null,
  };
}

export function parseDashboardPayload(payload: unknown): DashboardModel | null {
  if (!isRecord(payload) || !Array.isArray(payload.items)) {
    return null;
  }
  const assets: Record<string, AssetCard> = {};
  const series: Record<string, ChartPoint[]> = {};
  const symbols: string[] = [];
  for (const item of payload.items) {
    const parsed = parseDashboardItem(item);
    if (parsed === null) {
      continue;
    }
    assets[parsed.asset.symbol] = parsed.asset;
    series[parsed.asset.symbol] = parsed.points;
    symbols.push(parsed.asset.symbol);
  }
  return symbols.length > 0 ? { assets, series, symbols } : null;
}

function parseDashboardItem(value: unknown): { asset: AssetCard; points: ChartPoint[] } | null {
  if (!isRecord(value) || !isRecord(value.asset) || !isRecord(value.latest) || !Array.isArray(value.history)) {
    return null;
  }
  const symbol = stringField(value.asset, "symbol");
  if (!symbol) {
    return null;
  }
  const points = value.history.map(parseChartPoint).filter((point): point is ChartPoint => point !== null);
  if (points.length === 0) {
    return null;
  }
  const latest = value.latest;
  return {
    asset: {
      symbol,
      displayNameKo: stringField(value.asset, "display_name_ko") || symbol,
      opinion: normalizeOpinion(stringField(value, "opinion")),
      price: numberField(latest, "close") ?? points.at(-1)?.close ?? 0,
      delta1d: formatPercent(numberField(latest, "return_1d")),
      delta1m: formatPercent(numberField(latest, "return_1m")),
      rsi14: numberField(latest, "rsi14"),
      ma5: numberField(latest, "ma5"),
      ma20: numberField(latest, "ma20"),
      ma50: numberField(latest, "ma50"),
      ma120: numberField(latest, "ma120"),
    },
    points,
  };
}

function parseChartPoint(value: unknown): ChartPoint | null {
  if (!isRecord(value)) {
    return null;
  }
  const time = stringField(value, "date");
  const close = numberField(value, "close");
  if (!time || close === null) {
    return null;
  }
  const open = numberField(value, "open") ?? close;
  const high = numberField(value, "high") ?? Math.max(open, close);
  const low = numberField(value, "low") ?? Math.min(open, close);
  return {
    time,
    open,
    high,
    low,
    close,
    volume: numberField(value, "volume") ?? 0,
    ma5: numberField(value, "ma5") ?? close,
    ma20: numberField(value, "ma20") ?? close,
    ma50: numberField(value, "ma50") ?? close,
    ma120: numberField(value, "ma120") ?? close,
    rsi14: numberField(value, "rsi14") ?? 50,
  };
}

export function formatMa(asset: AssetCard): string {
  const values = [asset.ma5, asset.ma20, asset.ma50, asset.ma120];
  return values.every((value) => value !== null) ? values.map(formatNumber).join(" / ") : "데이터 없음";
}

export function formatNumber(value: number | null): string {
  return value === null ? "데이터 없음" : Number(value.toFixed(2)).toLocaleString();
}

function formatPercent(value: number | null): string {
  if (value === null) {
    return "0.00%";
  }
  const percent = value * 100;
  return `${percent >= 0 ? "+" : ""}${percent.toFixed(2)}%`;
}

function isRecord(value: unknown): value is JsonObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function stringField(record: JsonObject, key: string): string | null {
  const value = record[key];
  return typeof value === "string" ? value : null;
}

function numberField(record: JsonObject, key: string): number | null {
  const value = record[key];
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}
