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

export type StartupStatusLabels = {
  readonly checking: string;
  readonly running: string;
  readonly setupRequired: string;
  readonly ready: string;
  readonly partial: string;
  readonly skipped: string;
  readonly failed: string;
};

export type ProviderSummaryLabels = {
  readonly opendartEnabled: string;
  readonly opendartDisabled: string;
  readonly aiDisabled: string;
};

export type CollectionStatusLabels = {
  readonly collected: string;
  readonly synthetic: string;
  readonly missing: string;
};

export type RuntimeSettings = {
  readonly providerSummary: ProviderSummary | null;
  readonly language: "ko" | "en" | null;
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

export async function fetchRuntimeSettings(): Promise<RuntimeSettings> {
  const response = await fetch("/api/settings");
  if (!response.ok) {
    return { providerSummary: null, language: null };
  }
  const payload: unknown = await response.json();
  if (!isRecord(payload)) {
    return { providerSummary: null, language: null };
  }

  const providerStatus = isRecord(payload.provider_status) ? payload.provider_status : {};
  const opendart = isRecord(providerStatus.opendart) ? providerStatus.opendart : {};
  const ai = isRecord(providerStatus.ai) ? providerStatus.ai : {};

  return {
    providerSummary: {
      firstRunCompleted: payload.first_run_completed !== false,
      opendartConfigured: opendart.configured === true,
      aiMode: typeof ai.mode === "string" ? ai.mode : null,
    },
    language: parseLanguage(payload.language),
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

export function startupStatusLabel(
  status: StartupRefreshStatus,
  labels: StartupStatusLabels = {
    checking: "확인 중",
    running: "데이터 갱신 진행 중",
    setupRequired: "초기 설정 필요",
    ready: "시장 데이터 준비 완료",
    partial: "일부 소스 비활성화",
    skipped: "최근 갱신 사용",
    failed: "시장 데이터 갱신 실패",
  },
): string {
  switch (status) {
    case "checking":
      return labels.checking;
    case "running":
      return labels.running;
    case "setup_required":
      return labels.setupRequired;
    case "ready":
      return labels.ready;
    case "partial":
      return labels.partial;
    case "skipped":
      return labels.skipped;
    case "failed":
      return labels.failed;
  }
}

export function providerSummaryLabel(
  summary: ProviderSummary,
  labels: ProviderSummaryLabels = {
    opendartEnabled: "OpenDART 설정됨",
    opendartDisabled: "OpenDART 미설정",
    aiDisabled: "AI disabled",
  },
): string {
  const dart = summary.opendartConfigured ? labels.opendartEnabled : labels.opendartDisabled;
  const ai = summary.aiMode ? `AI ${summary.aiMode}` : labels.aiDisabled;
  return `${dart} · ${ai}`;
}

export function collectionStatusLabel(
  status: CollectionAssetStatus["status"],
  labels: CollectionStatusLabels = {
    collected: "실제 수집",
    synthetic: "예시 데이터 포함",
    missing: "수집 기록 없음",
  },
): string {
  switch (status) {
    case "collected":
      return labels.collected;
    case "synthetic":
      return labels.synthetic;
    case "missing":
      return labels.missing;
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

function parseLanguage(value: unknown): "ko" | "en" | null {
  return value === "ko" || value === "en" ? value : null;
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
