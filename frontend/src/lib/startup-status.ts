export type StartupRefreshStatus = "checking" | "setup_required" | "ready" | "partial" | "skipped" | "failed";

export type ProviderDisabled = {
  readonly symbol: string;
  readonly provider: string;
  readonly reason: string;
};

export type StartupRefreshView = {
  readonly status: StartupRefreshStatus;
  readonly priceRows: number;
  readonly indicatorRows: number;
  readonly newsItems: number;
  readonly disclosures: number;
  readonly providerDisabled: readonly ProviderDisabled[];
};

export type ProviderSummary = {
  readonly firstRunCompleted: boolean;
  readonly opendartConfigured: boolean;
  readonly aiMode: string | null;
};

export type CollectionAssetStatus = {
  readonly symbol: string;
  readonly displayNameKo: string | null;
  readonly exchange: string | null;
  readonly provider: string | null;
  readonly latestPriceDate: string | null;
  readonly latestFetchedAt: string | null;
  readonly priceRows: number;
  readonly indicatorRows: number;
  readonly hasSynthetic: boolean;
  readonly status: "collected" | "synthetic" | "missing";
};

export const INITIAL_STARTUP_REFRESH: StartupRefreshView = {
  status: "checking",
  priceRows: 0,
  indicatorRows: 0,
  newsItems: 0,
  disclosures: 0,
  providerDisabled: [],
};

export async function fetchProviderSummary(): Promise<ProviderSummary | null> {
  const response = await fetch("/api/backend/settings");
  if (!response.ok) {
    return null;
  }
  const payload: unknown = await response.json();
  if (!isRecord(payload) || !isRecord(payload.provider_status)) {
    return null;
  }
  const opendart = isRecord(payload.provider_status.opendart) ? payload.provider_status.opendart : {};
  const ai = isRecord(payload.provider_status.ai) ? payload.provider_status.ai : {};
  return {
    firstRunCompleted: payload.first_run_completed !== false,
    opendartConfigured: opendart.configured === true,
    aiMode: typeof ai.mode === "string" ? ai.mode : null,
  };
}

export async function fetchCollectionStatus(slug: string): Promise<readonly CollectionAssetStatus[]> {
  const response = await fetch(`/api/backend/watchlists/${encodeURIComponent(slug)}/collection-status`);
  if (!response.ok) {
    return [];
  }
  const payload: unknown = await response.json();
  if (!isRecord(payload) || !Array.isArray(payload.assets)) {
    return [];
  }
  return payload.assets.map(parseCollectionAssetStatus).filter((item): item is CollectionAssetStatus => item !== null);
}

export function parseStartupRefresh(payload: unknown): StartupRefreshView {
  if (!isRecord(payload)) {
    return { ...INITIAL_STARTUP_REFRESH, status: "failed" };
  }
  const providerDisabled = parseProviderDisabled(payload.provider_disabled);
  return {
    status: normalizeStartupStatus(typeof payload.status === "string" ? payload.status : "", providerDisabled.length),
    priceRows: numberValue(payload.price_rows),
    indicatorRows: numberValue(payload.indicator_rows),
    newsItems: numberValue(payload.news_items),
    disclosures: numberValue(payload.disclosures),
    providerDisabled,
  };
}

export function startupStatusLabel(status: StartupRefreshStatus): string {
  switch (status) {
    case "checking":
      return "확인 중";
    case "setup_required":
      return "초기 설정 필요";
    case "ready":
      return "시장 데이터 준비 완료";
    case "partial":
      return "일부 소스 비활성화";
    case "skipped":
      return "최근 갱신 사용";
    case "failed":
      return "시장 데이터 갱신 실패";
  }
}

export function providerSummaryLabel(summary: ProviderSummary): string {
  const dart = summary.opendartConfigured ? "OpenDART 설정됨" : "OpenDART 미설정";
  const ai = summary.aiMode ? `AI ${summary.aiMode}` : "AI disabled";
  return `${dart} · ${ai}`;
}

export function collectionStatusLabel(status: CollectionAssetStatus["status"]): string {
  switch (status) {
    case "collected":
      return "실제 수집";
    case "synthetic":
      return "예시 데이터 포함";
    case "missing":
      return "수집 기록 없음";
  }
}

function parseCollectionAssetStatus(value: unknown): CollectionAssetStatus | null {
  if (!isRecord(value) || typeof value.symbol !== "string") {
    return null;
  }
  return {
    symbol: value.symbol,
    displayNameKo: stringOrNull(value.display_name_ko),
    exchange: stringOrNull(value.exchange),
    provider: stringOrNull(value.provider),
    latestPriceDate: stringOrNull(value.latest_price_date),
    latestFetchedAt: stringOrNull(value.latest_fetched_at),
    priceRows: numberValue(value.price_rows),
    indicatorRows: numberValue(value.indicator_rows),
    hasSynthetic: value.has_synthetic === true,
    status: parseCollectionStatus(value.status),
  };
}

function parseCollectionStatus(value: unknown): CollectionAssetStatus["status"] {
  if (value === "collected" || value === "synthetic" || value === "missing") {
    return value;
  }
  return "missing";
}

function normalizeStartupStatus(status: string, disabledCount: number): StartupRefreshStatus {
  if (status === "skipped") {
    return "skipped";
  }
  if (status === "partial" || disabledCount > 0) {
    return "partial";
  }
  if (status === "ok") {
    return "ready";
  }
  return "failed";
}

function parseProviderDisabled(value: unknown): readonly ProviderDisabled[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.filter(isProviderDisabled);
}

function isProviderDisabled(value: unknown): value is ProviderDisabled {
  return (
    isRecord(value)
    && typeof value.symbol === "string"
    && typeof value.provider === "string"
    && typeof value.reason === "string"
  );
}

function numberValue(value: unknown): number {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

function stringOrNull(value: unknown): string | null {
  return typeof value === "string" && value.length > 0 ? value : null;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
