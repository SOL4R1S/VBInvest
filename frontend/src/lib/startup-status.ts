export type StartupRefreshStatus = "checking" | "running" | "setup_required" | "ready" | "partial" | "skipped" | "failed";

export type ProviderDisabled = {
  readonly symbol: string;
  readonly provider: string;
  readonly reason: string;
};

export type StartupRefreshView = {
  readonly status: StartupRefreshStatus;
  readonly queued: number;
  readonly running: number;
  readonly succeeded: number;
  readonly failed: number;
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
  queued: 0,
  running: 0,
  succeeded: 0,
  failed: 0,
  priceRows: 0,
  indicatorRows: 0,
  newsItems: 0,
  disclosures: 0,
  providerDisabled: [],
};

export async function fetchProviderSummary(): Promise<ProviderSummary | null> {
  const response = await fetch("/api/settings");
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
  const response = await fetch(`/api/watchlists/${encodeURIComponent(slug)}/collection-status`);
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
  const failures = parseFailures(payload.failures);
  const providerDisabled = parseProviderDisabled(payload.provider_disabled);
  const priceRows = numberValue(payload.price_rows);
  const indicatorRows = numberValue(payload.indicator_rows);
  const rawCounts = deriveCounts({
    rawQueued: numberValue(payload.queued),
    rawRunning: numberValue(payload.running),
    rawSucceeded: numberValue(payload.succeeded),
    rawFailed: numberValue(payload.failed),
    priceRows,
    indicatorRows,
    providerDisabledCount: providerDisabled.length,
    failureCount: failures.length,
    status: typeof payload.status === "string" ? payload.status : "",
  });
  return {
    status: normalizeStartupStatus(typeof payload.status === "string" ? payload.status : "", providerDisabled.length),
    queued: rawCounts.queued,
    running: rawCounts.running,
    succeeded: rawCounts.succeeded,
    failed: rawCounts.failed,
    priceRows,
    indicatorRows,
    newsItems: numberValue(payload.news_items),
    disclosures: numberValue(payload.disclosures),
    providerDisabled,
  };
}

export function startupStatusLabel(status: StartupRefreshStatus): string {
  switch (status) {
    case "checking":
      return "확인 중";
    case "running":
      return "데이터 갱신 진행 중";
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
  if (status === "queued") {
    return "checking";
  }
  if (status === "running") {
    return "running";
  }
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

function parseFailures(value: unknown): readonly string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.filter((item): item is string => typeof item === "string");
}

function deriveCounts(args: {
  rawQueued: number;
  rawRunning: number;
  rawSucceeded: number;
  rawFailed: number;
  priceRows: number;
  indicatorRows: number;
  providerDisabledCount: number;
  failureCount: number;
  status: string;
}): { queued: number; running: number; succeeded: number; failed: number } {
  const hasExplicitCounts = hasProgressCounts(args.rawQueued, args.rawRunning, args.rawSucceeded, args.rawFailed);
  if (hasExplicitCounts) {
    return {
      queued: args.rawQueued,
      running: args.rawRunning,
      succeeded: args.rawSucceeded,
      failed: args.rawFailed,
    };
  }

  const failed = Number.isFinite(args.failureCount) && args.failureCount > 0
    ? args.failureCount + args.providerDisabledCount
    : args.providerDisabledCount;
  const baselineRows = Math.max(args.priceRows, args.indicatorRows);
  if (args.status === "failed") {
    return {
      queued: 0,
      running: 0,
      succeeded: 0,
      failed: Math.max(failed, 1),
    };
  }
  return {
    queued: 0,
    running: 0,
    succeeded: Math.max(0, baselineRows - failed),
    failed,
  };
}

function hasProgressCounts(queued: number, running: number, succeeded: number, failed: number): boolean {
  return queued > 0 || running > 0 || succeeded > 0 || failed > 0;
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
