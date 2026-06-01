export type StartupRefreshStatus = "checking" | "ready" | "partial" | "skipped" | "failed";

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
  readonly opendartConfigured: boolean;
  readonly aiMode: string | null;
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
    opendartConfigured: opendart.configured === true,
    aiMode: typeof ai.mode === "string" ? ai.mode : null,
  };
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

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
