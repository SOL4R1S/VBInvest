"use client";

import { useEffect, useMemo, useState } from "react";
import {
  INITIAL_STARTUP_REFRESH,
  collectionStatusLabel,
  fetchCollectionStatus,
  fetchRuntimeSettings,
  parseStartupRefresh,
  providerSummaryLabel,
  startupStatusLabel,
  type CollectionAssetStatus,
  type ProviderSummary,
  type RuntimeSetupValues,
  type StartupRefreshView,
} from "@/lib/startup-status";
import {
  fallbackAsset,
  fetchDashboardData,
  formatMa,
  formatNumber,
  type AssetCard,
  type ChartPoint,
} from "@/lib/dashboard-data";
import {
  addAssetToWatchlist,
  createWatchlist as createWatchlistRequest,
  deleteAssetFromWatchlist,
  fetchWatchlists,
  type Watchlist,
} from "@/lib/watchlists";
import { ChartShell } from "@/components/ChartShell";
import { ResearchCard } from "@/components/ResearchCard";
import { SetupWizard } from "@/components/SetupWizard";
import type { Language, LocalizedLabels } from "@/lib/i18n";
import { isLanguage, labelsFor, persistLanguage, resolveLanguage } from "@/lib/i18n";
import {
  FALLBACK_SCHEDULER_SETTINGS,
  fetchSchedulerSettings,
  patchSchedulerSettings,
  type SchedulerSettings,
} from "@/lib/scheduler-settings";
import { sendShutdownBeacon, shutdownSystem } from "@/lib/system";

type TickerSuggestion = {
  readonly symbol: string;
  readonly name: string;
  readonly exchange: string;
  readonly quoteType: string;
};

type TickerValidationFailure = {
  readonly message: string;
  readonly suggestions: readonly TickerSuggestion[];
};

const ESTIMATED_STARTUP_REFRESH_SECONDS = 120;
const STARTUP_PROGRESS_CAP = 92;

function formatDuration(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  const remainder = seconds % 60;
  return minutes > 0 ? `${minutes}m ${remainder}s` : `${remainder}s`;
}

function estimatedStartupProgress(elapsedSeconds: number): { percent: number; remainingSeconds: number } {
  const rawPercent = Math.floor((elapsedSeconds / ESTIMATED_STARTUP_REFRESH_SECONDS) * 100);
  const percent = Math.max(5, Math.min(STARTUP_PROGRESS_CAP, rawPercent));
  const remainingSeconds = Math.max(0, ESTIMATED_STARTUP_REFRESH_SECONDS - elapsedSeconds);
  return { percent, remainingSeconds };
}

function optionalString(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}

function parseTickerSuggestion(value: unknown): TickerSuggestion | null {
  if (!isRecord(value)) {
    return null;
  }
  const symbol = optionalString(value["symbol"]);
  if (!symbol) {
    return null;
  }
  const name = optionalString(value["name"]) || optionalString(value["suggestion_label"]) || symbol;
  return {
    symbol,
    name,
    exchange: optionalString(value["exchange"]),
    quoteType: optionalString(value["quote_type"]) || optionalString(value["quoteType"]),
  };
}

function parseTickerSuggestions(value: unknown): readonly TickerSuggestion[] {
  if (!Array.isArray(value)) {
    return [];
  }
  const suggestions: TickerSuggestion[] = [];
  for (const item of value) {
    const suggestion = parseTickerSuggestion(item);
    if (suggestion !== null) {
      suggestions.push(suggestion);
    }
  }
  return suggestions;
}

async function tickerValidationFailure(response: Response, labels: LocalizedLabels): Promise<TickerValidationFailure> {
  let payload: unknown;
  try {
    payload = await response.json();
  } catch (error) {
    if (error instanceof SyntaxError || error instanceof TypeError) {
      return { message: labels.errors.invalidSymbol, suggestions: [] };
    }
    throw error;
  }
  const detail = isRecord(payload) ? payload["detail"] : null;
  if (!isRecord(detail)) {
    return { message: labels.errors.invalidSymbol, suggestions: [] };
  }
  const suggestions = parseTickerSuggestions(detail["suggestions"]);
  if (suggestions.length > 0) {
    return {
      message: labels.errors.symbolSuggestion(suggestions[0].name, suggestions[0].symbol),
      suggestions,
    };
  }
  const suggestion = optionalString(detail["suggestion"]);
  const label = optionalString(detail["suggestion_label"]) || suggestion;
  if (suggestion) {
    return {
      message: labels.errors.symbolSuggestion(label, suggestion),
      suggestions: [{ symbol: suggestion, name: label, exchange: "", quoteType: "" }],
    };
  }
  return { message: labels.errors.invalidSymbol, suggestions: [] };
}

async function validatedTickerSymbol(response: Response, fallbackSymbol: string): Promise<string> {
  let payload: unknown;
  try {
    payload = await response.json();
  } catch (error) {
    if (error instanceof SyntaxError || error instanceof TypeError) {
      return fallbackSymbol;
    }
    throw error;
  }
  if (!isRecord(payload)) {
    return fallbackSymbol;
  }
  const symbol = optionalString(payload["symbol"]);
  return symbol || fallbackSymbol;
}

async function tickerSearchSuggestions(query: string, signal: AbortSignal): Promise<readonly TickerSuggestion[]> {
  const response = await fetch(`/api/tickers/search?query=${encodeURIComponent(query)}&limit=8`, { signal });
  if (!response.ok) {
    return [];
  }
  const payload: unknown = await response.json();
  if (!isRecord(payload)) {
    return [];
  }
  return parseTickerSuggestions(payload["suggestions"]);
}

export function WatchlistDashboard() {
  const [watchlists, setWatchlists] = useState<readonly Watchlist[]>([]);
  const [selectedWatchlist, setSelectedWatchlist] = useState<Watchlist["id"] | null>(null);
  const [selectedSymbol, setSelectedSymbol] = useState("NVDA");
  const [assetCards, setAssetCards] = useState<Record<string, AssetCard>>({});
  const [seriesBySymbol, setSeriesBySymbol] = useState<Record<string, ChartPoint[]>>({});
  const [newWatchlist, setNewWatchlist] = useState("");
  const [newSymbol, setNewSymbol] = useState("");
  const [watchlistValidationMessage, setWatchlistValidationMessage] = useState("");
  const [symbolValidationMessage, setSymbolValidationMessage] = useState("");
  const [symbolSuggestions, setSymbolSuggestions] = useState<readonly TickerSuggestion[]>([]);
  const [symbolValidationPending, setSymbolValidationPending] = useState(false);
  const [startupRefresh, setStartupRefresh] = useState<StartupRefreshView>(INITIAL_STARTUP_REFRESH);
  const [providerSummary, setProviderSummary] = useState<ProviderSummary | null>(null);
  const [collectionStatus, setCollectionStatus] = useState<readonly CollectionAssetStatus[]>([]);
  const [watchlistLoadError, setWatchlistLoadError] = useState<string | null>(null);
  const [watchlistsLoaded, setWatchlistsLoaded] = useState(false);
  const [dashboardLoadError, setDashboardLoadError] = useState<string | null>(null);
  const [setupRequired, setSetupRequired] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [runtimeSetupValues, setRuntimeSetupValues] = useState<RuntimeSetupValues | null>(null);
  const [setupRevision, setSetupRevision] = useState(0);
  const [schedulerSettings, setSchedulerSettings] = useState<SchedulerSettings>(FALLBACK_SCHEDULER_SETTINGS);
  const [schedulerStateError, setSchedulerStateError] = useState<string | null>(null);
  const [schedulerSaving, setSchedulerSaving] = useState(false);
  const [schedulerLoading, setSchedulerLoading] = useState(false);
  const [systemShutdownMessage, setSystemShutdownMessage] = useState<string | null>(null);
  const [systemShuttingDown, setSystemShuttingDown] = useState(false);
  const [systemShutdownComplete, setSystemShutdownComplete] = useState(false);
  const [language, setLanguage] = useState<Language>(() => resolveLanguage(undefined, null, undefined));
  const [labels, setLabels] = useState<LocalizedLabels>(() => labelsFor(language));
  const [startupElapsedSeconds, setStartupElapsedSeconds] = useState(0);

  const activeWatchlist = watchlists.find((item) => item.id === selectedWatchlist) ?? watchlists[0] ?? null;
  const hasWatchlists = watchlists.length > 0;
  const activeWatchlistHasSymbols = (activeWatchlist?.symbols.length ?? 0) > 0;
  const canShowDashboard = watchlistsLoaded && hasWatchlists && activeWatchlistHasSymbols;
  const currentSymbol = activeWatchlist?.symbols.includes(selectedSymbol)
    ? selectedSymbol
    : activeWatchlist?.symbols[0] ?? "";
  const asset = assetCards[currentSymbol] ?? fallbackAsset(currentSymbol);
  const points = useMemo(() => seriesBySymbol[currentSymbol] ?? [], [currentSymbol, seriesBySymbol]);
  const startupInProgress = startupRefresh.status === "checking" || startupRefresh.status === "running";
  const startupProgress = estimatedStartupProgress(startupElapsedSeconds);
  const schedulerText = schedulerSettings.weeklyPrecomputeEnabled ? labels.controls.weeklyReportOn : labels.controls.weeklyReportOff;

  async function loadDashboardData(slug: string, shouldApply: () => boolean = () => true) {
    const dashboard = await fetchDashboardData(slug);
    if (!shouldApply()) {
      return;
    }
    if (dashboard === null) {
      setDashboardLoadError(labels.errors.dashboardLoad);
      return;
    }
    setDashboardLoadError(null);
    setAssetCards(dashboard.assets);
    setSeriesBySymbol(dashboard.series);
  }

  async function loadCollectionStatus(slug: string, shouldApply: () => boolean = () => true) {
    const statusRows = await fetchCollectionStatus(slug);
    if (shouldApply()) {
      setCollectionStatus(statusRows);
    }
  }

  async function loadWatchlistMarketView(slug: string, shouldApply: () => boolean = () => true) {
    await loadDashboardData(slug, shouldApply);
    await loadCollectionStatus(slug, shouldApply);
  }

  function clearWatchlistMarketView() {
    setCollectionStatus([]);
    setAssetCards({});
    setSeriesBySymbol({});
  }

  useEffect(() => {
    const shutdownOnPageHide = () => {
      sendShutdownBeacon();
    };
    window.addEventListener("pagehide", shutdownOnPageHide);
    return () => {
      window.removeEventListener("pagehide", shutdownOnPageHide);
    };
  }, []);

  useEffect(() => {
    if (!startupInProgress) {
      setStartupElapsedSeconds(0);
      return;
    }
    setStartupElapsedSeconds(0);
    const timer = window.setInterval(() => {
      setStartupElapsedSeconds((value) => value + 1);
    }, 1000);
    return () => {
      window.clearInterval(timer);
    };
  }, [startupInProgress]);

  useEffect(() => {
    const query = newSymbol.trim();
    if (!query || !watchlistsLoaded) {
      setSymbolSuggestions([]);
      return;
    }
    const controller = new AbortController();
    let cancelled = false;
    tickerSearchSuggestions(query, controller.signal)
      .then((suggestions) => {
        if (!cancelled) {
          setSymbolSuggestions(suggestions);
        }
      })
      .catch((error) => {
        if (error instanceof DOMException && error.name === "AbortError") {
          return;
        }
        logStartupWarning(error, "ticker search failed");
      });
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [newSymbol, watchlistsLoaded]);

  useEffect(() => {
    let cancelled = false;

    async function loadSchedulerSettings() {
      setSchedulerLoading(true);
      setSchedulerStateError(null);
      try {
        const nextStatus = await fetchSchedulerSettings();
        if (!cancelled) {
          if (nextStatus === null) {
            setSchedulerSettings(FALLBACK_SCHEDULER_SETTINGS);
            setSchedulerStateError(labels.errors.schedulerSave);
          } else {
            setSchedulerSettings(nextStatus);
          }
        }
      } catch (error) {
        logStartupWarning(error, "scheduler status refresh failed");
        if (!cancelled) {
          setSchedulerSettings(FALLBACK_SCHEDULER_SETTINGS);
          setSchedulerStateError(labels.errors.schedulerSave);
        }
      } finally {
        if (!cancelled) {
          setSchedulerLoading(false);
        }
      }
    }

    function applyLanguage(nextLanguage: Language | null) {
      const resolvedLanguage = resolveLanguage(nextLanguage, language, undefined);
      if (resolvedLanguage === language) {
        return;
      }
      setLanguage(resolvedLanguage);
      setLabels(labelsFor(resolvedLanguage));
      persistLanguage(resolvedLanguage);
    }

    async function loadRuntimeSettings() {
      const settings = await fetchRuntimeSettings();
      if (cancelled) {
        return null;
      }
      applyLanguage(settings.language);
      setProviderSummary(settings.providerSummary);
      setRuntimeSetupValues(settings.setupValues);
      return settings;
    }

    async function refreshMarketData() {
      setWatchlistsLoaded(false);
      try {
        const nextRuntimeSettings = await loadRuntimeSettings();
        if (cancelled) {
          return;
        }
        if (nextRuntimeSettings?.providerSummary?.firstRunCompleted === false) {
          setSetupRequired(true);
          setStartupRefresh({ ...INITIAL_STARTUP_REFRESH, status: "setup_required" });
          return;
        }
        setSetupRequired(false);
        void loadSchedulerSettings();
      } catch (error) {
        logStartupWarning(error, "settings status refresh failed");
      }
      try {
        const response = await fetch("/api/startup/market-refresh?no_network=false&include_news=true", { method: "POST" });
        if (!response.ok) {
          throw new Error(`startup market refresh failed: ${response.status}`);
        }
        const payload: unknown = await response.json();
        if (!cancelled) {
          setStartupRefresh(parseStartupRefresh(payload));
        }
      } catch (error) {
        logStartupWarning(error, "startup market refresh failed");
        if (!cancelled) {
          setStartupRefresh({ ...INITIAL_STARTUP_REFRESH, status: "failed" });
        }
      }
      try {
        const nextWatchlists = await fetchWatchlists();
        if (cancelled) {
          return;
        }
        if (nextWatchlists.length === 0) {
          setWatchlistsLoaded(true);
          setWatchlistLoadError(null);
          setWatchlists([]);
          setSelectedWatchlist(null);
          setSelectedSymbol("NVDA");
          clearWatchlistMarketView();
          return;
        }
        setWatchlistsLoaded(true);
        setWatchlistLoadError(null);
        setWatchlists(nextWatchlists);
        const nextSelected = selectedWatchlist !== null && nextWatchlists.some((item) => item.id === selectedWatchlist)
          ? selectedWatchlist
          : nextWatchlists[0]?.id ?? null;
        setSelectedWatchlist(nextSelected);
        const nextWatchlist = nextSelected === null ? null : nextWatchlists.find((item) => item.id === nextSelected);
        const nextSymbol = nextWatchlist?.symbols.includes(selectedSymbol) ? selectedSymbol : nextWatchlist?.symbols[0] ?? "NVDA";
        setSelectedSymbol(nextSymbol);
        if (nextWatchlist !== undefined && nextWatchlist !== null) {
          await loadWatchlistMarketView(nextWatchlist.slug, () => !cancelled);
        }
      } catch (error) {
        logStartupWarning(error, "watchlist load failed");
        if (!cancelled) {
          setWatchlistsLoaded(true);
          setWatchlistLoadError(labels.errors.watchlistLoad);
        }
      }
    }

    void refreshMarketData();

    return () => {
      cancelled = true;
    };
  }, [setupRevision]);

  function completeSetup() {
    setSetupRequired(false);
    setSettingsOpen(false);
    setStartupRefresh(INITIAL_STARTUP_REFRESH);
    setSetupRevision((value) => value + 1);
  }

  async function changeLanguage(nextLanguage: Language) {
    if (nextLanguage === language) {
      return;
    }
    setLanguage(nextLanguage);
    setLabels(labelsFor(nextLanguage));
    persistLanguage(nextLanguage);
    if (setupRequired) {
      return;
    }
    try {
      const response = await fetch("/api/settings/language", {
        method: "PATCH",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify({ language: nextLanguage }),
      });
      if (!response.ok) {
        throw new Error(`language update failed: ${response.status}`);
      }
      const payload: unknown = await response.json();
      if (!isLanguageResponse(payload)) {
        throw new Error("invalid language response");
      }
      setLanguage(payload.language);
      setLabels(labelsFor(payload.language));
      persistLanguage(payload.language);
    } catch (error) {
      logStartupWarning(error, "language change failed");
    }
  }

  async function updateWeeklyPrecompute(enabled: boolean) {
    const previousStatus = schedulerSettings;
    const optimisticStatus = { ...schedulerSettings, weeklyPrecomputeEnabled: enabled };
    setSchedulerSaving(true);
    setSchedulerStateError(null);
    setSchedulerSettings(optimisticStatus);
    try {
      const nextStatus = await patchSchedulerSettings({ weeklyPrecomputeEnabled: enabled });
      if (nextStatus === null) {
        throw new Error("invalid patch response");
      }
      setSchedulerSettings(nextStatus);
    } catch (error) {
      logStartupWarning(error, "scheduler settings update failed");
      setSchedulerSettings(previousStatus);
      setSchedulerStateError(labels.errors.schedulerSave);
    } finally {
      setSchedulerSaving(false);
    }
  }

  async function createWatchlist() {
    const trimmed = newWatchlist.trim();
    if (!trimmed) {
      setWatchlistValidationMessage(labels.errors.emptyWatchlistName);
      return;
    }
    if (!watchlistsLoaded) {
      setWatchlistValidationMessage(labels.errors.addAfterLoad);
      return;
    }

    setWatchlistValidationMessage("");
    try {
      const next = await createWatchlistRequest(trimmed);
      if (next === null) {
        setWatchlistValidationMessage(labels.errors.createWatchlist);
        return;
      }
      setWatchlists((items) => [...items, next]);
      setSelectedWatchlist(next.id);
      setSelectedSymbol(next.symbols[0] ?? "NVDA");
      if (next.symbols.length > 0) {
        await loadWatchlistMarketView(next.slug);
      } else {
        clearWatchlistMarketView();
      }
      setNewWatchlist("");
      setWatchlistValidationMessage("");
    } catch (error) {
      logStartupWarning(error, "watchlist create failed");
      setWatchlistValidationMessage(labels.errors.createWatchlist);
    }
  }

  async function addSymbol() {
    await addSymbolValue(newSymbol);
  }

  async function addSymbolValue(rawSymbol: string) {
    const query = rawSymbol.trim();
    const fallbackSymbol = query.toUpperCase();
    if (!query) {
      setSymbolValidationMessage(labels.errors.emptySymbol);
      setSymbolSuggestions([]);
      return;
    }
    if (selectedWatchlist === null) {
      setSymbolValidationMessage(labels.errors.selectWatchlist);
      setSymbolSuggestions([]);
      return;
    }
    if (!watchlistsLoaded) {
      setSymbolValidationMessage(labels.errors.addAfterLoad);
      setSymbolSuggestions([]);
      return;
    }
    setSymbolValidationPending(true);
    setSymbolValidationMessage("");
    setSymbolSuggestions([]);
    let symbol = fallbackSymbol;
    try {
      const response = await fetch(`/api/tickers/validate?symbol=${encodeURIComponent(query)}`);
      if (!response.ok) {
        const validation = await tickerValidationFailure(response, labels);
        setSymbolValidationMessage(validation.message);
        setSymbolSuggestions(validation.suggestions);
        return;
      }
      symbol = await validatedTickerSymbol(response, fallbackSymbol);
    } catch (error) {
      logStartupWarning(error, "ticker validation failed");
      setSymbolValidationMessage(labels.errors.symbolLookup);
      setSymbolSuggestions([]);
      return;
    } finally {
      setSymbolValidationPending(false);
    }

    const addResponse = await addAssetToWatchlist(selectedWatchlist, symbol);
    if (addResponse === null) {
      setSymbolValidationMessage(labels.errors.addSymbol);
      return;
    } else {
      setWatchlists((items) => items.map((item) => (item.id === addResponse.id ? addResponse : item)));
    }

    setSelectedSymbol(symbol);
    await loadWatchlistMarketView(addResponse.slug);
    setNewSymbol("");
    setSymbolValidationMessage("");
    setSymbolSuggestions([]);
  }

  async function removeSymbol(symbol: string) {
    if (selectedWatchlist === null) {
      setSymbolValidationMessage(labels.errors.selectWatchlist);
      return;
    }
    setSymbolValidationMessage("");
    try {
      const next = await deleteAssetFromWatchlist(selectedWatchlist, symbol);
      if (next === null) {
        setSymbolValidationMessage(labels.errors.removeSymbol);
        return;
      }
      setWatchlists((items) => items.map((item) => (item.id === next.id ? next : item)));
      if (symbol === currentSymbol) {
        setSelectedSymbol(next.symbols[0] ?? "NVDA");
      }
      if (next.symbols.length > 0) {
        await loadWatchlistMarketView(next.slug);
      } else {
        clearWatchlistMarketView();
      }
    } catch (error) {
      logStartupWarning(error, "watchlist asset delete failed");
      setSymbolValidationMessage(labels.errors.removeSymbol);
    }
  }

  async function shutdownLocalProgram() {
    if (systemShuttingDown || systemShutdownComplete) {
      return;
    }
    const confirm = window.confirm(labels.app.confirmShutdownLabel);
    if (!confirm) {
      return;
    }
    setSystemShuttingDown(true);
    setSystemShutdownMessage(labels.controls.shutdownBusy);
    const result = await shutdownSystem();
    if (!result.ok) {
      setSystemShutdownMessage(result.message);
      setSystemShuttingDown(false);
      return;
    }
    setSystemShuttingDown(false);
    setSystemShutdownMessage(labels.controls.shutdownDone);
    setSystemShutdownComplete(true);
  }

  return (
    <main className="page">
      {setupRequired ? (
        <SetupWizard
          onCompleted={completeSetup}
          language={language}
          labels={labels.setup}
          onLanguageChange={changeLanguage}
        />
      ) : null}
      {setupRequired ? null : (
        <>
      {settingsOpen ? (
        <div className="settings-modal-backdrop">
          <div className="settings-modal" role="dialog" aria-label={labels.controls.settingsAction}>
            <SetupWizard
              onCompleted={completeSetup}
              onCancel={() => setSettingsOpen(false)}
              language={language}
              labels={labels.setup}
              onLanguageChange={changeLanguage}
              initialValues={runtimeSetupValues}
              submitLabel={labels.controls.settingsSaveAction}
              cancelLabel={labels.controls.settingsCancelAction}
            />
          </div>
        </div>
      ) : null}
      {startupInProgress ? (
        <div className="startup-refresh-modal" role="status" aria-live="polite">
          <strong>{labels.startup.checkingText}</strong>
          <div className="startup-refresh-progress" aria-label={labels.startup.progressLabel}>
            <span style={{ width: `${startupProgress.percent}%` }} />
          </div>
          <div className="startup-refresh-progress-copy">
            <span>{labels.startup.progressLabel} {startupProgress.percent}%</span>
            <span>{labels.startup.elapsedLabel} {formatDuration(startupElapsedSeconds)}</span>
            <span>{labels.startup.remainingLabel} {formatDuration(startupProgress.remainingSeconds)}</span>
          </div>
          <small>{labels.startup.progressEstimateNotice}</small>
        </div>
      ) : null}
      {startupRefresh.status === "failed" ? (
        <div className="startup-refresh-banner" role="status" aria-live="polite">
          {labels.startup.failedBanner}
        </div>
      ) : null}
      {watchlistLoadError ? (
        <div className="startup-refresh-banner" role="status" aria-live="polite">
          {watchlistLoadError}
        </div>
      ) : null}
      {dashboardLoadError ? (
        <div className="startup-refresh-banner" role="status" aria-live="polite">
          {dashboardLoadError}
        </div>
      ) : null}

      <header className="hero">
        <div>
          <p className="eyebrow">{labels.app.title}</p>
          <h1>{labels.app.dashboardHeading}</h1>
          <p className="subtle">{labels.app.dashboardSubtitle}</p>
        </div>
        <div className="hero-actions" aria-label="application actions">
          <div className="hero-action-row">
            <button type="button" className="hero-action-button" onClick={() => setSettingsOpen(true)}>
              {labels.controls.settingsAction}
            </button>
            <button
              type="button"
              className="hero-action-button shutdown"
              onClick={() => void shutdownLocalProgram()}
              disabled={systemShuttingDown || systemShutdownComplete}
            >
              {labels.controls.shutdownAction}
            </button>
          </div>
          {systemShutdownMessage ? (
            <p className={`hero-action-status ${systemShutdownComplete ? "success" : systemShuttingDown ? "" : "error"}`}>
              {systemShutdownMessage}
            </p>
          ) : null}
          <label>
            <span className="sr-only">{labels.app.languageLabel}</span>
            <select
              value={language}
              aria-label={labels.app.languageLabel}
              onChange={(event) => {
                if (isLanguage(event.target.value)) {
                  void changeLanguage(event.target.value);
                }
              }}
            >
              <option value="ko">{labels.app.languageOptionKo}</option>
              <option value="en">{labels.app.languageOptionEn}</option>
            </select>
          </label>
        </div>
      </header>

      {!startupInProgress ? (
        <section className={`startup-status-strip ${startupRefresh.status}`} aria-label="startup source status" data-testid="startup-status">
          <strong>{startupStatusLabel(startupRefresh.status, labels.startupStatusLabels)}</strong>
          <span>{labels.startup.queued} {startupRefresh.queued} · {labels.startup.running} {startupRefresh.running} · {labels.startup.success} {startupRefresh.succeeded} · {labels.startup.failed} {startupRefresh.failed}</span>
          <span>{labels.startup.price} {startupRefresh.priceRows} · {labels.startup.indicator} {startupRefresh.indicatorRows}</span>
          <span>{labels.startup.news} {startupRefresh.newsItems} · {labels.startup.disclosure} {startupRefresh.disclosures}</span>
          {startupRefresh.tickerCatalog ? (
            <span>{labels.startup.tickerCatalog} {startupRefresh.tickerCatalog.count}</span>
          ) : null}
          {providerSummary ? <span>{providerSummaryLabel(providerSummary, labels.providerSummaryLabels)}</span> : null}
          {startupRefresh.providerDisabled.length > 0 ? (
            <span>{labels.startup.providerDisabled} {startupRefresh.providerDisabled.length}</span>
          ) : null}
        </section>
      ) : null}

      {collectionStatus.length > 0 ? (
        <section className="collection-status-strip" aria-label={labels.startup.collectionAria} data-testid="collection-status">
          {collectionStatus.map((item) => (
            <span key={item.symbol} className={`collection-status-pill ${item.status}`}>
              <strong>{item.symbol}</strong>
              <span>{collectionStatusLabel(item.status, labels.collectionStatusLabels)}</span>
              <span>{labels.startup.latest} {item.latestPriceDate ?? "-"}</span>
              <span>{item.provider ?? labels.startup.noProvider}</span>
              <span>{labels.startup.price} {item.priceRows} / {labels.startup.indicator} {item.indicatorRows}</span>
            </span>
          ))}
        </section>
      ) : null}

      <section className="control-panel" aria-label="watchlist controls">
        {watchlistsLoaded && hasWatchlists ? (
          <div className="panel-column">
            <h2>{labels.controls.watchlistsHeading}</h2>
            <div className="chips">
              {watchlists.map((watchlist) => (
                <button
                  key={watchlist.id}
                  type="button"
                  className={watchlist.id === selectedWatchlist ? "chip active" : "chip"}
                  onClick={() => {
                    setSelectedWatchlist(watchlist.id);
                    setSelectedSymbol(watchlist.symbols[0] ?? "NVDA");
                    if (watchlist.symbols.length > 0) {
                      void loadWatchlistMarketView(watchlist.slug);
                    } else {
                      clearWatchlistMarketView();
                    }
                  }}
                >
                  {watchlist.name}
                </button>
              ))}
            </div>
          </div>
        ) : null}

        <div className="panel-column">
          <h2>{labels.controls.addWatchlistHeading}</h2>
          <div className="inline-form">
            <input
              aria-label={labels.controls.newWatchlistLabel}
              value={newWatchlist}
              onChange={(event) => setNewWatchlist(event.target.value)}
              placeholder={labels.controls.watchlistNamePlaceholder}
            />
            <button type="button" onClick={() => void createWatchlist()} disabled={!watchlistsLoaded}>
              {labels.controls.addWatchlistAction}
            </button>
          </div>
          {watchlistValidationMessage ? <p className="research-status error">{watchlistValidationMessage}</p> : null}
        </div>

        <div className="panel-column">
          <h2>{labels.controls.symbolHeading}</h2>
          <div className="inline-form">
            <input
              aria-label={labels.controls.newSymbolLabel}
              value={newSymbol}
              onChange={(event) => {
                setNewSymbol(event.target.value);
                setSymbolSuggestions([]);
              }}
              placeholder={labels.controls.symbolPlaceholder}
            />
            <button
              type="button"
              onClick={() => void addSymbol()}
              disabled={symbolValidationPending || !watchlistsLoaded}
            >
              {symbolValidationPending ? labels.controls.symbolActionBusy : labels.controls.symbolAction}
            </button>
          </div>
          {symbolValidationMessage ? <p className="research-status error">{symbolValidationMessage}</p> : null}
          {symbolSuggestions.length > 0 ? (
            <div className="ticker-suggestions" aria-label={labels.controls.symbolSuggestionsLabel}>
              {symbolSuggestions.map((suggestion) => (
                <button
                  key={suggestion.symbol}
                  type="button"
                  className="ticker-suggestion"
                  onClick={() => void addSymbolValue(suggestion.symbol)}
                  disabled={symbolValidationPending || !watchlistsLoaded}
                  aria-label={`${suggestion.symbol} ${suggestion.name} ${suggestion.exchange}`.trim()}
                >
                  <span className="ticker-suggestion-symbol">{suggestion.symbol}</span>
                  <span className="ticker-suggestion-name">{suggestion.name}</span>
                  {suggestion.exchange ? <span className="ticker-suggestion-exchange">{suggestion.exchange}</span> : null}
                </button>
              ))}
            </div>
          ) : null}
        </div>

        <div className="panel-column">
          <h2>{labels.controls.weeklyReportHeading}</h2>
          <div className="inline-form scheduler-toggle-row">
            <span>{labels.controls.weeklyReportCheckbox}</span>
            <input
              aria-label={labels.controls.weeklyReportCheckbox}
              type="checkbox"
              checked={schedulerSettings.weeklyPrecomputeEnabled}
              onChange={(event) => {
                void updateWeeklyPrecompute(event.target.checked);
              }}
              disabled={schedulerLoading || schedulerSaving}
            />
          </div>
          <p className="research-status">{labels.controls.weeklyReportDefault}</p>
          <p className="research-status">{labels.controls.weeklyReportManual}</p>
          <p className="research-status">{schedulerText}</p>
          {schedulerStateError ? <p className="research-status error">{schedulerStateError}</p> : null}
        </div>

      </section>

      {watchlistsLoaded && !hasWatchlists ? (
        <section className="startup-refresh-banner" role="status" aria-live="polite">
          {labels.startup.noWatchlists}
        </section>
      ) : null}

      {watchlistsLoaded && hasWatchlists && !activeWatchlistHasSymbols ? (
        <section className="startup-refresh-banner" role="status" aria-live="polite">
          {labels.startup.noSymbols}
        </section>
      ) : null}

      {canShowDashboard ? (
        <section className="content-grid">
          <aside className="watchlist-card">
            <div className="card-heading">
              <h2>{activeWatchlist?.name}</h2>
              <span>{labels.summary.assetCount(activeWatchlist?.symbols.length ?? 0)}</span>
            </div>
            <div className="symbol-list">
              {(activeWatchlist?.symbols ?? []).map((symbol) => {
                const item = assetCards[symbol];
                return (
                  <div
                    key={symbol}
                    className={symbol === currentSymbol ? "symbol-row active" : "symbol-row"}
                  >
                    <button type="button" onClick={() => setSelectedSymbol(symbol)} data-testid={`symbol-${symbol}`}>
                      <strong>{item?.displayNameKo ?? symbol}</strong>
                      <span>{symbol}</span>
                    </button>
                    <button
                      type="button"
                      onClick={(event) => {
                        event.stopPropagation();
                        void removeSymbol(symbol);
                      }}
                      aria-label={labels.summary.removeSymbol(symbol)}
                    >
                      {labels.controls.removeAction}
                    </button>
                  </div>
                );
              })}
            </div>
          </aside>

          <section className="detail-card">
            <div className="detail-header">
              <div>
                <h2>{asset.displayNameKo}</h2>
                <p>{asset.symbol}</p>
              </div>
              <div className={`badge ${asset.opinion}`}>
                {asset.opinion}
              </div>
            </div>

            <div className="summary-grid">
              <div><b>{labels.summary.price}</b><span>{asset.price.toLocaleString()}</span></div>
              <div><b>{labels.summary.oneDay}</b><span>{asset.delta1d}</span></div>
              <div><b>{labels.summary.oneMonth}</b><span>{asset.delta1m}</span></div>
              <div><b>{labels.summary.rsi14}</b><span>{formatNumber(asset.rsi14)}</span></div>
              <div><b>{labels.summary.ma}</b><span>{formatMa(asset)}</span></div>
            </div>

            <ChartShell symbol={asset.symbol} points={points} labels={labels.chart} />

            <ResearchCard symbol={asset.symbol} labels={labels.report} />
          </section>
        </section>
      ) : null}
        </>
      )}
    </main>
  );
}

function logStartupWarning(error: unknown, fallback: string): void {
  if (error instanceof Error) {
    console.warn(error.message);
    return;
  }
  console.warn(fallback);
}

function isLanguageResponse(value: unknown): value is { readonly language: Language } {
  return isRecord(value) && (value.language === "ko" || value.language === "en");
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function authHeaders(): Record<string, string> {
  const token = typeof window === "undefined" ? "" : window.__VBINVEST_LOCAL_SESSION_TOKEN__ ?? "";
  return token ? { Authorization: `Bearer ${token}` } : {};
}

declare global {
  interface Window {
    __VBINVEST_LOCAL_SESSION_TOKEN__?: string;
  }
}
