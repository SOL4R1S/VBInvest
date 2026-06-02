import type { CollectionStatusLabels, ProviderSummaryLabels, StartupStatusLabels } from "@/lib/startup-status";

export const SUPPORTED_LANGUAGES = ["ko", "en"] as const;
export type Language = (typeof SUPPORTED_LANGUAGES)[number];

export const LANGUAGE_STORAGE_KEY = "vbinvest_language";

export type SetupLabels = {
  readonly title: string;
  readonly setupInstruction: string;
  readonly languageField: string;
  readonly languageOptionKo: string;
  readonly languageOptionEn: string;
  readonly dataDirectoryField: string;
  readonly databaseModeField: string;
  readonly databaseModeSqlite: string;
  readonly databaseModePostgresDocker: string;
  readonly databaseModePostgresUrl: string;
  readonly databaseModeDockerHint: string;
  readonly postgresDsnField: string;
  readonly postgresDsnPlaceholder: string;
  readonly obsidianVaultField: string;
  readonly obsidianVaultPlaceholder: string;
  readonly exportModeField: string;
  readonly exportModeDirect: string;
  readonly exportModeSymlink: string;
  readonly opendartApiKeyField: string;
  readonly opendartApiKeyHint: string;
  readonly aiModeField: string;
  readonly aiModeNone: string;
  readonly aiModeCompatible: string;
  readonly aiModeCodex: string;
  readonly aiModeCopilot: string;
  readonly aiTypeField: string;
  readonly aiTypeCloud: string;
  readonly aiTypeLocal: string;
  readonly cloudProviderField: string;
  readonly cloudProviderOpenai: string;
  readonly cloudProviderOpenrouter: string;
  readonly cloudProviderDeepseek: string;
  readonly cloudProviderQwen: string;
  readonly cloudProviderKimi: string;
  readonly cloudProviderGlm: string;
  readonly cloudProviderCustom: string;
  readonly localProviderHint: string;
  readonly aiBaseUrlField: string;
  readonly aiBaseUrlPlaceholder: string;
  readonly aiModelField: string;
  readonly aiModelPlaceholder: string;
  readonly aiContextSizeField: string;
  readonly completeButtonSaving: string;
  readonly completeButton: string;
  readonly defaultErrorMessage: string;
};

export type LocalizedLabels = {
  readonly app: {
    readonly title: string;
    readonly dashboardHeading: string;
    readonly dashboardSubtitle: string;
    readonly subtitle: string;
    readonly languageSwitcherAriaLabel: string;
    readonly languageLabel: string;
    readonly languageOptionKo: string;
    readonly languageOptionEn: string;
    readonly confirmShutdownLabel: string;
  };
  readonly startup: {
    readonly checkingText: string;
    readonly failedBanner: string;
    readonly queued: string;
    readonly running: string;
    readonly success: string;
    readonly failed: string;
    readonly price: string;
    readonly indicator: string;
    readonly news: string;
    readonly disclosure: string;
    readonly providerDisabled: string;
    readonly latest: string;
    readonly noProvider: string;
    readonly collectionAria: string;
    readonly noWatchlists: string;
    readonly noSymbols: string;
    readonly startupStripQueued: string;
    readonly startupStripRunning: string;
    readonly startupStripStatus: string;
    readonly startupStripFailed: string;
    readonly startupStripPrice: string;
    readonly startupStripIndicator: string;
    readonly startupStripNews: string;
    readonly startupStripDisclosure: string;
    readonly collectionLabelNoProvider: string;
    readonly latestLabel: string;
    readonly noSymbolsInWatchlist: string;
  };
  readonly startupStatusLabels: StartupStatusLabels;
  readonly collectionStatusLabels: CollectionStatusLabels;
  readonly providerSummaryLabels: ProviderSummaryLabels;
  readonly controls: {
    readonly dashboardHeading: string;
    readonly watchlistsHeading: string;
    readonly addWatchlistHeading: string;
    readonly newWatchlistLabel: string;
    readonly watchlistNameLabel: string;
    readonly watchlistNamePlaceholder: string;
    readonly addWatchlistAction: string;
    readonly symbolHeading: string;
    readonly newSymbolLabel: string;
    readonly symbolLabel: string;
    readonly symbolPlaceholder: string;
    readonly symbolAction: string;
    readonly symbolActionBusy: string;
    readonly removeAction: string;
    readonly symbolListItemRemove: string;
    readonly weeklyReportHeading: string;
    readonly weeklyReportCheckbox: string;
    readonly weeklyReportCheckboxLabel: string;
    readonly weeklyReportDefault: string;
    readonly weeklyReportDefaultText: string;
    readonly weeklyReportManual: string;
    readonly weeklyReportManualText: string;
    readonly weeklyReportOn: string;
    readonly weeklyReportOff: string;
    readonly weeklyReportStateOn: string;
    readonly weeklyReportStateOff: string;
    readonly systemHeading: string;
    readonly shutdownAction: string;
    readonly shutdownButton: string;
    readonly shutdownBusy: string;
    readonly shutdownDone: string;
  };
  readonly summary: {
    readonly price: string;
    readonly oneDay: string;
    readonly oneMonth: string;
    readonly rsi14: string;
    readonly ma: string;
    readonly assetCount: (count: number) => string;
    readonly removeSymbol: (symbol: string) => string;
  };
  readonly cards: {
    readonly watchlist: string;
    readonly summaryPrice: string;
    readonly summaryOneDay: string;
    readonly summaryOneMonth: string;
    readonly summaryRsi14: string;
    readonly summaryMaLabel: string;
  };
  readonly setup: SetupLabels;
  readonly chart: {
    readonly line: string;
    readonly candle: string;
    readonly reset: string;
    readonly modeLine: string;
    readonly modeCandle: string;
    readonly resetView: string;
    readonly legend: string;
  };
  readonly report: {
    readonly heading: string;
    readonly opinionPrefix: string;
    readonly sources: (count: number) => string;
    readonly sourcesCountPrefix: string;
    readonly noReport: string;
    readonly noReportMessage: string;
    readonly generating: string;
    readonly generated: string;
    readonly canceled: string;
    readonly statusGenerating: string;
    readonly successMessage: string;
    readonly operationCancelledMessage: string;
    readonly progressMessage: string;
    readonly generateAction: string;
    readonly statusGenerate: string;
    readonly modalTitle: string;
    readonly progressModalTitle: string;
    readonly cancelAction: string;
    readonly modalCancelLabel: string;
    readonly reportLink: string;
    readonly linkLabel: string;
    readonly reportPath: string;
    readonly reportPathLabel: string;
    readonly obsidianPath: string;
    readonly obsidianPathLabel: string;
    readonly defaultError: string;
    readonly reportGenerateErrorDefault: string;
  };
  readonly errors: {
    readonly dashboardLoad: string;
    readonly dashboardLoadFailed: string;
    readonly watchlistLoad: string;
    readonly schedulerSave: string;
    readonly schedulerSaveFailed: string;
    readonly emptyWatchlistName: string;
    readonly createWatchlist: string;
    readonly emptySymbol: string;
    readonly selectWatchlist: string;
    readonly addAfterLoad: string;
    readonly invalidSymbol: string;
    readonly symbolLookup: string;
    readonly addSymbol: string;
    readonly removeSymbol: string;
    readonly symbolValidationInProgress: string;
  };
};

export function isLanguage(value: unknown): value is Language {
  return value === "ko" || value === "en";
}

export function resolveLanguage(
  settingsLanguage: unknown,
  storedLanguage: unknown = readStoredLanguage(),
  browserLanguage: string | undefined = browserLanguageFromEnv(),
): Language {
  if (isLanguage(settingsLanguage)) {
    return settingsLanguage;
  }
  if (isLanguage(storedLanguage)) {
    return storedLanguage;
  }
  return browserLanguage?.toLowerCase().startsWith("en") ? "en" : "ko";
}

export function readStoredLanguage(): Language | null {
  if (typeof window === "undefined") {
    return null;
  }
  const candidate = window.localStorage.getItem(LANGUAGE_STORAGE_KEY);
  return isLanguage(candidate) ? candidate : null;
}

export function persistLanguage(language: Language): void {
  if (typeof window !== "undefined") {
    window.localStorage.setItem(LANGUAGE_STORAGE_KEY, language);
  }
}

export function labelFor(language: Language): LocalizedLabels {
  return translations[language];
}

export function labelsFor(language: Language): LocalizedLabels {
  return labelFor(language);
}

function browserLanguageFromEnv(): string | undefined {
  return typeof window === "undefined" ? undefined : window.navigator.language;
}

const koSetup: SetupLabels = {
  title: "초기 설정",
  setupInstruction: "로컬 데이터와 Obsidian 저장 위치를 정하면 대시보드가 시작됩니다.",
  languageField: "언어",
  languageOptionKo: "한국어",
  languageOptionEn: "English",
  dataDirectoryField: "Data Directory",
  databaseModeField: "Database Mode",
  databaseModeSqlite: "SQLite 내장 DB (권장)",
  databaseModePostgresDocker: "PostgreSQL Docker 자동 실행",
  databaseModePostgresUrl: "PostgreSQL 직접 연결",
  databaseModeDockerHint: "Docker Desktop/Engine을 사용하는 고급 모드입니다. Docker가 실행 중이면 설정을 완료할 수 있습니다.",
  postgresDsnField: "Postgres DSN",
  postgresDsnPlaceholder: "postgresql://user:password@127.0.0.1:5432/vbinvest",
  obsidianVaultField: "Obsidian Vault Path",
  obsidianVaultPlaceholder: "/Volumes/.../ObsidianVault",
  exportModeField: "Export Mode",
  exportModeDirect: "직접 저장",
  exportModeSymlink: "심링크 (고급)",
  opendartApiKeyField: "OpenDART API Key",
  opendartApiKeyHint: "OpenDART 공시를 받으려면 OpenDART에서 API 키를 발급해 입력하세요. 사용량과 제한은 사용자 키 책임이며, 비워두면 한국 공시 수집만 비활성화됩니다.",
  aiModeField: "AI Mode",
  aiModeNone: "사용 안 함",
  aiModeCompatible: "AI API 연동",
  aiModeCodex: "Codex CLI (계정 제한/정지 가능성 있음)",
  aiModeCopilot: "Copilot CLI (계정 제한/정지 가능성 있음)",
  aiTypeField: "AI API Type",
  aiTypeCloud: "Cloud model provider",
  aiTypeLocal: "Local LLM",
  cloudProviderField: "Cloud Model Provider",
  cloudProviderOpenai: "OpenAI",
  cloudProviderOpenrouter: "OpenRouter",
  cloudProviderDeepseek: "DeepSeek",
  cloudProviderQwen: "Qwen / DashScope",
  cloudProviderKimi: "Kimi / Moonshot",
  cloudProviderGlm: "GLM / Z.AI",
  cloudProviderCustom: "Custom provider",
  localProviderHint: "Ollama, LM Studio, llama.cpp 같은 로컬 OpenAI-compatible endpoint를 사용할 수 있습니다.",
  aiBaseUrlField: "AI Base URL",
  aiBaseUrlPlaceholder: "https://api.openai.com/v1",
  aiModelField: "AI Model",
  aiModelPlaceholder: "gpt-4.1-mini",
  aiContextSizeField: "Context Size",
  completeButtonSaving: "저장 중",
  completeButton: "설정 완료",
  defaultErrorMessage: "설정 저장에 실패했습니다.",
};

const enSetup: SetupLabels = {
  title: "First Run Setup",
  setupInstruction: "Set local storage and Obsidian path to start the dashboard.",
  languageField: "Language",
  languageOptionKo: "한국어",
  languageOptionEn: "English",
  dataDirectoryField: "Data Directory",
  databaseModeField: "Database Mode",
  databaseModeSqlite: "Built-in SQLite (recommended)",
  databaseModePostgresDocker: "Start PostgreSQL with Docker",
  databaseModePostgresUrl: "Direct PostgreSQL connection",
  databaseModeDockerHint: "Advanced mode for Docker-hosted PostgreSQL. Continue if Docker is running.",
  postgresDsnField: "Postgres DSN",
  postgresDsnPlaceholder: "postgresql://user:password@127.0.0.1:5432/vbinvest",
  obsidianVaultField: "Obsidian Vault Path",
  obsidianVaultPlaceholder: "/Volumes/.../ObsidianVault",
  exportModeField: "Export Mode",
  exportModeDirect: "Direct write",
  exportModeSymlink: "Symlink (advanced)",
  opendartApiKeyField: "OpenDART API Key",
  opendartApiKeyHint: "Issue an OpenDART API key to collect Korean disclosures. Leave it empty to disable only Korean disclosure collection.",
  aiModeField: "AI Mode",
  aiModeNone: "Disabled",
  aiModeCompatible: "AI API integration",
  aiModeCodex: "Codex CLI (account restriction risk)",
  aiModeCopilot: "Copilot CLI (account restriction risk)",
  aiTypeField: "AI API Type",
  aiTypeCloud: "Cloud model provider",
  aiTypeLocal: "Local LLM",
  cloudProviderField: "Cloud Model Provider",
  cloudProviderOpenai: "OpenAI",
  cloudProviderOpenrouter: "OpenRouter",
  cloudProviderDeepseek: "DeepSeek",
  cloudProviderQwen: "Qwen / DashScope",
  cloudProviderKimi: "Kimi / Moonshot",
  cloudProviderGlm: "GLM / Z.AI",
  cloudProviderCustom: "Custom provider",
  localProviderHint: "You can use local OpenAI-compatible endpoints such as Ollama, LM Studio, or llama.cpp.",
  aiBaseUrlField: "AI Base URL",
  aiBaseUrlPlaceholder: "https://api.openai.com/v1",
  aiModelField: "AI Model",
  aiModelPlaceholder: "gpt-4.1-mini",
  aiContextSizeField: "Context Size",
  completeButtonSaving: "Saving",
  completeButton: "Finish setup",
  defaultErrorMessage: "Failed to save settings.",
};

export const translations = {
  ko: {
    app: {
      title: "VBinvest",
      dashboardHeading: "투자 대시보드",
      dashboardSubtitle: "로컬 프로그램에서 관심 그룹과 종목을 관리하고, 차트와 리서치 의견을 같은 화면에서 확인합니다.",
      subtitle: "로컬 프로그램에서 관심 그룹과 종목을 관리하고, 차트와 리서치 의견을 같은 화면에서 확인합니다.",
      languageSwitcherAriaLabel: "언어 선택",
      languageLabel: "언어",
      languageOptionKo: "한국어",
      languageOptionEn: "English",
      confirmShutdownLabel: "로컬 프로그램을 종료하시겠습니까?",
    },
    startup: {
      checkingText: "주식 정보를 확인하는 중",
      failedBanner: "시장 데이터 갱신 실패",
      queued: "대기",
      running: "진행",
      success: "성공",
      failed: "실패",
      price: "가격",
      indicator: "지표",
      news: "뉴스",
      disclosure: "공시",
      providerDisabled: "비활성 소스",
      latest: "최신",
      noProvider: "provider 없음",
      collectionAria: "데이터 수집 상태",
      noWatchlists: "저장된 관심 그룹이 없습니다.",
      noSymbols: "선택한 관심 그룹에 종목이 없습니다.",
      startupStripQueued: "대기",
      startupStripRunning: "진행",
      startupStripStatus: "성공",
      startupStripFailed: "실패",
      startupStripPrice: "가격",
      startupStripIndicator: "지표",
      startupStripNews: "뉴스",
      startupStripDisclosure: "공시",
      collectionLabelNoProvider: "provider 없음",
      latestLabel: "최신",
      noSymbolsInWatchlist: "선택한 관심 그룹에 종목이 없습니다.",
    },
    startupStatusLabels: {
      checking: "확인 중",
      running: "데이터 갱신 진행 중",
      setupRequired: "초기 설정 필요",
      ready: "시장 데이터 준비 완료",
      partial: "일부 소스 비활성화",
      skipped: "최근 갱신 사용",
      failed: "시장 데이터 갱신 실패",
    },
    collectionStatusLabels: {
      collected: "실제 수집",
      synthetic: "예시 데이터 포함",
      missing: "수집 기록 없음",
    },
    providerSummaryLabels: {
      opendartEnabled: "OpenDART 설정됨",
      opendartDisabled: "OpenDART 미설정",
      aiDisabled: "AI disabled",
    },
    controls: {
      dashboardHeading: "투자 대시보드",
      watchlistsHeading: "관심 그룹",
      addWatchlistHeading: "그룹 추가",
      newWatchlistLabel: "새 그룹 이름",
      watchlistNameLabel: "새 그룹 이름",
      watchlistNamePlaceholder: "새 그룹 이름",
      addWatchlistAction: "새 그룹",
      symbolHeading: "종목 추가",
      newSymbolLabel: "새 종목 심볼",
      symbolLabel: "새 종목 심볼",
      symbolPlaceholder: "새 종목 심볼",
      symbolAction: "추가",
      symbolActionBusy: "확인 중",
      removeAction: "제거",
      symbolListItemRemove: "제거",
      weeklyReportHeading: "주간 사전 리포트",
      weeklyReportCheckbox: "주간 사전 리포트",
      weeklyReportCheckboxLabel: "주간 사전 리포트",
      weeklyReportDefault: "기본은 꺼짐(오프)이며 필요할 때만 사용합니다.",
      weeklyReportDefaultText: "기본은 꺼짐(오프)이며 필요할 때만 사용합니다.",
      weeklyReportManual: "리포트 발행은 수동 버튼으로 동일하게 실행할 수 있습니다.",
      weeklyReportManualText: "리포트 발행은 수동 버튼으로 동일하게 실행할 수 있습니다.",
      weeklyReportOn: "주간 사전 리포트 켜짐",
      weeklyReportOff: "주간 사전 리포트 꺼짐",
      weeklyReportStateOn: "주간 사전 리포트 켜짐",
      weeklyReportStateOff: "주간 사전 리포트 꺼짐",
      systemHeading: "시스템 제어",
      shutdownAction: "종료",
      shutdownButton: "종료",
      shutdownBusy: "종료 처리 중입니다.",
      shutdownDone: "종료 요청이 접수되었습니다.",
    },
    summary: {
      price: "현재가",
      oneDay: "1D",
      oneMonth: "1M",
      rsi14: "RSI14",
      ma: "MA5 / 20 / 50 / 120",
      assetCount: (count) => `${count}개 종목`,
      removeSymbol: (symbol) => `${symbol} 제거`,
    },
    cards: {
      watchlist: "종목",
      summaryPrice: "현재가",
      summaryOneDay: "1D",
      summaryOneMonth: "1M",
      summaryRsi14: "RSI14",
      summaryMaLabel: "MA5 / 20 / 50 / 120",
    },
    setup: koSetup,
    chart: {
      line: "라인",
      candle: "캔들",
      reset: "줌 초기화",
      modeLine: "라인",
      modeCandle: "캔들",
      resetView: "줌 초기화",
      legend: "상단 가격 · 하단 거래량/RSI14 · 5일선 · 20일선 · 50일선 · 120일선 · 휠 줌 · 드래그 팬",
    },
    report: {
      heading: "리서치 의견",
      opinionPrefix: "투자의견",
      sources: (count) => `근거 ${count}개`,
      sourcesCountPrefix: "근거",
      noReport: "아직 발행된 리서치가 없습니다. 현재는 DB 가격/지표를 기반으로 차트를 확인할 수 있습니다.",
      noReportMessage: "아직 발행된 리서치가 없습니다. 현재는 DB 가격/지표를 기반으로 차트를 확인할 수 있습니다.",
      generating: "실시간 분석 중",
      generated: "리포트 발행 완료",
      canceled: "취소됨",
      statusGenerating: "실시간 분석 중",
      successMessage: "리포트 발행 완료",
      operationCancelledMessage: "취소됨",
      progressMessage: "실시간 분석 중",
      generateAction: "리포트 발행",
      statusGenerate: "리포트 발행",
      modalTitle: "리포트 발행 중",
      progressModalTitle: "리포트 발행 중",
      cancelAction: "취소",
      modalCancelLabel: "취소",
      reportLink: "리포트 링크 보기",
      linkLabel: "리포트 링크 보기",
      reportPath: "리포트 경로",
      reportPathLabel: "리포트 경로",
      obsidianPath: "Obsidian 경로",
      obsidianPathLabel: "Obsidian 경로",
      defaultError: "리포트 발행에 실패했습니다. 설정과 백엔드 연결을 확인해주세요.",
      reportGenerateErrorDefault: "리포트 발행에 실패했습니다. 설정과 백엔드 연결을 확인해주세요.",
    },
    errors: {
      dashboardLoad: "대시보드 데이터를 불러오지 못했습니다.",
      dashboardLoadFailed: "대시보드 데이터를 불러오지 못했습니다.",
      watchlistLoad: "관심 그룹 목록을 불러오는 데 실패했습니다.",
      schedulerSave: "스케줄러 설정 저장 실패",
      schedulerSaveFailed: "스케줄러 설정 저장 실패",
      emptyWatchlistName: "그룹 이름은 비워둘 수 없습니다.",
      createWatchlist: "그룹 생성에 실패했습니다.",
      emptySymbol: "종목 코드를 입력해 주세요.",
      selectWatchlist: "먼저 관심 그룹을 선택해 주세요.",
      addAfterLoad: "관심 그룹을 불러온 뒤 추가해 주세요.",
      invalidSymbol: "실제 조회 가능한 티커만 추가할 수 있습니다.",
      symbolLookup: "티커 확인에 실패했습니다. 네트워크와 데이터 제공자를 확인해주세요.",
      addSymbol: "종목 추가에 실패했습니다.",
      removeSymbol: "종목 제거에 실패했습니다.",
      symbolValidationInProgress: "확인 중",
    },
  },
  en: {
    app: {
      title: "VBinvest",
      dashboardHeading: "Investment Dashboard",
      dashboardSubtitle: "Manage watchlists and symbols locally, then review charts and research opinions in one screen.",
      subtitle: "Manage watchlists and symbols locally, then review charts and research opinions in one screen.",
      languageSwitcherAriaLabel: "Select language",
      languageLabel: "Language",
      languageOptionKo: "한국어",
      languageOptionEn: "English",
      confirmShutdownLabel: "Stop the local program?",
    },
    startup: {
      checkingText: "Checking market data",
      failedBanner: "Market data refresh failed",
      queued: "Queued",
      running: "Running",
      success: "Succeeded",
      failed: "Failed",
      price: "Price",
      indicator: "Indicators",
      news: "News",
      disclosure: "Disclosures",
      providerDisabled: "Disabled sources",
      latest: "Latest",
      noProvider: "No provider",
      collectionAria: "Data collection status",
      noWatchlists: "No watchlists to show.",
      noSymbols: "No symbols in the selected watchlist.",
      startupStripQueued: "Queued",
      startupStripRunning: "Running",
      startupStripStatus: "Succeeded",
      startupStripFailed: "Failed",
      startupStripPrice: "Price",
      startupStripIndicator: "Indicators",
      startupStripNews: "News",
      startupStripDisclosure: "Disclosures",
      collectionLabelNoProvider: "No provider",
      latestLabel: "Latest",
      noSymbolsInWatchlist: "No symbols in the selected watchlist.",
    },
    startupStatusLabels: {
      checking: "Checking",
      running: "Market refresh running",
      setupRequired: "First-run setup required",
      ready: "Market data ready",
      partial: "Some sources disabled",
      skipped: "Using cached refresh",
      failed: "Market refresh failed",
    },
    collectionStatusLabels: {
      collected: "Collected",
      synthetic: "Includes sample data",
      missing: "No collection record",
    },
    providerSummaryLabels: {
      opendartEnabled: "OpenDART configured",
      opendartDisabled: "OpenDART not configured",
      aiDisabled: "AI disabled",
    },
    controls: {
      dashboardHeading: "Investment Dashboard",
      watchlistsHeading: "Watchlists",
      addWatchlistHeading: "Add group",
      newWatchlistLabel: "New group name",
      watchlistNameLabel: "New group name",
      watchlistNamePlaceholder: "New group name",
      addWatchlistAction: "Add group",
      symbolHeading: "Add symbol",
      newSymbolLabel: "New symbol",
      symbolLabel: "New symbol",
      symbolPlaceholder: "New symbol",
      symbolAction: "Add",
      symbolActionBusy: "Checking",
      removeAction: "Remove",
      symbolListItemRemove: "Remove",
      weeklyReportHeading: "Weekly precompute",
      weeklyReportCheckbox: "Weekly precompute",
      weeklyReportCheckboxLabel: "Weekly precompute",
      weeklyReportDefault: "Default is off; enable only when needed.",
      weeklyReportDefaultText: "Default is off; enable only when needed.",
      weeklyReportManual: "Manual report generation remains available.",
      weeklyReportManualText: "Manual report generation remains available.",
      weeklyReportOn: "Weekly precompute enabled",
      weeklyReportOff: "Weekly precompute disabled",
      weeklyReportStateOn: "Weekly precompute enabled",
      weeklyReportStateOff: "Weekly precompute disabled",
      systemHeading: "System control",
      shutdownAction: "Shutdown",
      shutdownButton: "Shutdown",
      shutdownBusy: "Processing shutdown.",
      shutdownDone: "Shutdown request accepted.",
    },
    summary: {
      price: "Price",
      oneDay: "1D",
      oneMonth: "1M",
      rsi14: "RSI14",
      ma: "MA5 / 20 / 50 / 120",
      assetCount: (count) => `${count} symbols`,
      removeSymbol: (symbol) => `Remove ${symbol}`,
    },
    cards: {
      watchlist: "symbols",
      summaryPrice: "Price",
      summaryOneDay: "1D",
      summaryOneMonth: "1M",
      summaryRsi14: "RSI14",
      summaryMaLabel: "MA5 / 20 / 50 / 120",
    },
    setup: enSetup,
    chart: {
      line: "Line",
      candle: "Candle",
      reset: "Reset zoom",
      modeLine: "Line",
      modeCandle: "Candle",
      resetView: "Reset zoom",
      legend: "Top price · bottom volume/RSI14 · MA5 · MA20 · MA50 · MA120 · wheel zoom · drag pan",
    },
    report: {
      heading: "Research Opinion",
      opinionPrefix: "Opinion",
      sources: (count) => `Sources ${count}`,
      sourcesCountPrefix: "Sources",
      noReport: "No research report has been issued yet. You can inspect charts based on DB prices and indicators.",
      noReportMessage: "No research report has been issued yet. You can inspect charts based on DB prices and indicators.",
      generating: "Analyzing now",
      generated: "Report generated",
      canceled: "Canceled",
      statusGenerating: "Analyzing now",
      successMessage: "Report generated",
      operationCancelledMessage: "Canceled",
      progressMessage: "Analyzing now",
      generateAction: "Generate report",
      statusGenerate: "Generate report",
      modalTitle: "Generating report",
      progressModalTitle: "Generating report",
      cancelAction: "Cancel",
      modalCancelLabel: "Cancel",
      reportLink: "Open report",
      linkLabel: "Open report",
      reportPath: "Report path",
      reportPathLabel: "Report path",
      obsidianPath: "Obsidian path",
      obsidianPathLabel: "Obsidian path",
      defaultError: "Report generation failed. Check settings and backend connection.",
      reportGenerateErrorDefault: "Report generation failed. Check settings and backend connection.",
    },
    errors: {
      dashboardLoad: "Failed to load dashboard data.",
      dashboardLoadFailed: "Failed to load dashboard data.",
      watchlistLoad: "Failed to load watchlists.",
      schedulerSave: "Failed to save scheduler settings.",
      schedulerSaveFailed: "Failed to save scheduler settings.",
      emptyWatchlistName: "Group name cannot be empty.",
      createWatchlist: "Failed to create group.",
      emptySymbol: "Enter a symbol.",
      selectWatchlist: "Select a watchlist first.",
      addAfterLoad: "Add after watchlists finish loading.",
      invalidSymbol: "Only valid tickers can be added.",
      symbolLookup: "Failed to validate ticker. Check network and data provider.",
      addSymbol: "Failed to add symbol.",
      removeSymbol: "Failed to remove symbol.",
      symbolValidationInProgress: "Checking",
    },
  },
} satisfies Record<Language, LocalizedLabels>;
