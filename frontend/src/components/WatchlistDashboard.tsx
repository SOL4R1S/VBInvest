"use client";

import { useEffect, useMemo, useState } from "react";
import { apiFetch } from "@/lib/http";
import {
  INITIAL_STARTUP_REFRESH,
  fetchCollectionStatus,
  type CollectionAssetStatus,
  type ProviderSummary,
  type RuntimeSetupValues,
  type StartupRefreshView,
} from "@/lib/startup-status";
import {
  fallbackAsset,
  fetchDashboardData,
  type AssetCard,
  type ChartPoint,
} from "@/lib/dashboard-data";
import {
  addAssetToWatchlist,
  createWatchlist as createWatchlistRequest,
  deleteAssetFromWatchlist,
  type Watchlist,
} from "@/lib/watchlists";
import { SetupWizard } from "@/components/SetupWizard";
import { isLanguage, labelsFor, persistLanguage, resolveLanguage, type Language, type LocalizedLabels } from "@/lib/i18n";
import {
  FALLBACK_SCHEDULER_SETTINGS,
  patchSchedulerSettings,
  type SchedulerSettings,
} from "@/lib/scheduler-settings";
import { sendShutdownBeacon, shutdownSystem } from "@/lib/system";
import {
  logStartupWarning,
  tickerValidationFailure,
  validatedTickerSymbol,
  type TickerSuggestion,
} from "@/lib/ticker-utils";
import { isRecord } from "@/lib/guards";
import { useDashboardBootstrap } from "@/hooks/useDashboardBootstrap";
import { useTickerSearch } from "@/hooks/useTickerSearch";
import { StartupProgressModal, estimatedStartupProgress } from "@/components/dashboard/StartupProgressModal";
import { StartupStatusStrip } from "@/components/dashboard/StartupStatusStrip";
import { CollectionStatusStrip } from "@/components/dashboard/CollectionStatusStrip";
import { SettingsModal } from "@/components/dashboard/SettingsModal";
import { DashboardHeader } from "@/components/dashboard/DashboardHeader";
import { AlertRulesPanel } from "@/components/notifications/AlertRulesPanel";
import { ControlPanel } from "@/components/dashboard/ControlPanel";
import { SymbolSidebar } from "@/components/dashboard/SymbolSidebar";
import { AssetDetailPanel } from "@/components/dashboard/AssetDetailPanel";

function isLanguageResponse(value: unknown): value is { readonly language: Language } {
  return isRecord(value) && (value.language === "ko" || value.language === "en");
}

export function WatchlistDashboard() {
  // --- Core state (orchestrator owns all, passes down) ---
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
  const [alertRulesOpen, setAlertRulesOpen] = useState(false);
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

  // --- Derived values ---
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

  // --- Data loading helpers ---
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

  // --- Hooks ---
  useDashboardBootstrap(
    {
      watchlists, selectedWatchlist, selectedSymbol, watchlistsLoaded, watchlistLoadError,
      startupRefresh, providerSummary, runtimeSetupValues, setupRequired,
      schedulerSettings, schedulerStateError, schedulerLoading, language, labels,
    },
    {
      setWatchlists, setSelectedWatchlist, setSelectedSymbol, setWatchlistsLoaded,
      setWatchlistLoadError, setStartupRefresh, setProviderSummary, setRuntimeSetupValues,
      setSetupRequired, setSchedulerSettings, setSchedulerStateError, setSchedulerLoading,
      setLanguage, setLabels, loadWatchlistMarketView, clearWatchlistMarketView, setupRevision,
    },
  );

  useTickerSearch(newSymbol, watchlistsLoaded, setSymbolSuggestions);

  // --- Effects ---
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

  // --- Actions ---
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
      const response = await apiFetch("/api/settings/language", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
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
      const response = await apiFetch(`/api/tickers/validate?symbol=${encodeURIComponent(query)}`);
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

  function handleWatchlistSelect(watchlist: Watchlist) {
    setSelectedWatchlist(watchlist.id);
    setSelectedSymbol(watchlist.symbols[0] ?? "NVDA");
    if (watchlist.symbols.length > 0) {
      void loadWatchlistMarketView(watchlist.slug);
    } else {
      clearWatchlistMarketView();
    }
  }

  // --- Render ---
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
        <SettingsModal
          onCompleted={completeSetup}
          onClose={() => setSettingsOpen(false)}
          language={language}
          labels={labels}
          onLanguageChange={changeLanguage}
          initialValues={runtimeSetupValues}
        />
      ) : null}
      {alertRulesOpen ? (
        <AlertRulesPanel onClose={() => setAlertRulesOpen(false)} />
      ) : null}
      {startupInProgress ? (
        <StartupProgressModal
          percent={startupProgress.percent}
          remainingSeconds={startupProgress.remainingSeconds}
          elapsedSeconds={startupElapsedSeconds}
          labels={labels.startup}
        />
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

      <DashboardHeader
        labels={labels}
        language={language}
        onLanguageChange={changeLanguage}
        onSettingsOpen={() => setSettingsOpen(true)}
        onAlertRulesOpen={() => setAlertRulesOpen(true)}
        onShutdown={() => void shutdownLocalProgram()}
        systemShuttingDown={systemShuttingDown}
        systemShutdownComplete={systemShutdownComplete}
        systemShutdownMessage={systemShutdownMessage}
      />

      {!startupInProgress ? (
        <StartupStatusStrip
          startupRefresh={startupRefresh}
          providerSummary={providerSummary}
          labels={labels}
        />
      ) : null}

      <CollectionStatusStrip collectionStatus={collectionStatus} labels={labels} />

      <ControlPanel
        labels={labels}
        watchlists={watchlists}
        selectedWatchlist={selectedWatchlist}
        watchlistsLoaded={watchlistsLoaded}
        hasWatchlists={hasWatchlists}
        newWatchlist={newWatchlist}
        newSymbol={newSymbol}
        watchlistValidationMessage={watchlistValidationMessage}
        symbolValidationMessage={symbolValidationMessage}
        symbolSuggestions={symbolSuggestions}
        symbolValidationPending={symbolValidationPending}
        schedulerSettings={schedulerSettings}
        schedulerLoading={schedulerLoading}
        schedulerSaving={schedulerSaving}
        schedulerStateError={schedulerStateError}
        schedulerText={schedulerText}
        onWatchlistSelect={handleWatchlistSelect}
        onNewWatchlistChange={setNewWatchlist}
        onCreateWatchlist={() => void createWatchlist()}
        onNewSymbolChange={(value) => { setNewSymbol(value); setSymbolSuggestions([]); }}
        onAddSymbol={() => void addSymbol()}
        onAddSymbolValue={(symbol) => void addSymbolValue(symbol)}
        onWeeklyPrecomputeToggle={(enabled) => void updateWeeklyPrecompute(enabled)}
      />

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
          <SymbolSidebar
            watchlist={activeWatchlist}
            assetCards={assetCards}
            currentSymbol={currentSymbol}
            labels={labels}
            onSelectSymbol={setSelectedSymbol}
            onRemoveSymbol={(symbol) => void removeSymbol(symbol)}
          />

          <AssetDetailPanel asset={asset} points={points} labels={labels} />
        </section>
      ) : null}
        </>
      )}
    </main>
  );
}
