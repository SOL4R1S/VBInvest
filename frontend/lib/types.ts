export type WatchlistState = {
  watchlist_id: string;
  name: string;
  slug?: string;
  symbols: string[];
};

export type ChartPoint = {
  date: string;
  close: number;
  open?: number;
  high?: number;
  low?: number;
  volume?: number;
  ma5?: number;
  ma20?: number;
  ma50?: number;
  ma120?: number;
  rsi?: number;
};

export type DashboardItem = {
  asset?: { symbol?: string; display_name_ko?: string };
  opinion: "매수" | "아웃퍼폼" | "중립" | "언더퍼폼" | "매도";
  latest?: Record<string, string | number>;
  thesis?: string;
  locked?: boolean;
  preview?: string;
  source_count?: number;
  sources?: Array<{ title?: string; url?: string }>;
};

export type DashboardState = {
  watchlist?: string;
  items?: DashboardItem[];
  research?: Record<string, unknown> | null;
  chart?: { history: ChartPoint[]; symbol: string };
};
