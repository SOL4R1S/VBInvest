"use client";

import { useEffect } from "react";
import { apiFetch } from "@/lib/http";
import {
  INITIAL_STARTUP_REFRESH,
  fetchRuntimeSettings,
  parseStartupRefresh,
  type ProviderSummary,
  type RuntimeSetupValues,
  type StartupRefreshView,
} from "@/lib/startup-status";
import { fetchWatchlists, type Watchlist } from "@/lib/watchlists";
import {
  FALLBACK_SCHEDULER_SETTINGS,
  fetchSchedulerSettings,
  type SchedulerSettings,
} from "@/lib/scheduler-settings";
import { isLanguage, labelsFor, persistLanguage, resolveLanguage, type Language, type LocalizedLabels } from "@/lib/i18n";
import { logStartupWarning } from "@/lib/ticker-utils";

export type DashboardBootstrapState = {
  readonly watchlists: readonly Watchlist[];
  readonly selectedWatchlist: Watchlist["id"] | null;
  readonly selectedSymbol: string;
  readonly watchlistsLoaded: boolean;
  readonly watchlistLoadError: string | null;
  readonly startupRefresh: StartupRefreshView;
  readonly providerSummary: ProviderSummary | null;
  readonly runtimeSetupValues: RuntimeSetupValues | null;
  readonly setupRequired: boolean;
  readonly schedulerSettings: SchedulerSettings;
  readonly schedulerStateError: string | null;
  readonly schedulerLoading: boolean;
  readonly language: Language;
  readonly labels: LocalizedLabels;
};

export type DashboardBootstrapActions = {
  readonly setWatchlists: React.Dispatch<React.SetStateAction<readonly Watchlist[]>>;
  readonly setSelectedWatchlist: React.Dispatch<React.SetStateAction<Watchlist["id"] | null>>;
  readonly setSelectedSymbol: React.Dispatch<React.SetStateAction<string>>;
  readonly setWatchlistsLoaded: React.Dispatch<React.SetStateAction<boolean>>;
  readonly setWatchlistLoadError: React.Dispatch<React.SetStateAction<string | null>>;
  readonly setStartupRefresh: React.Dispatch<React.SetStateAction<StartupRefreshView>>;
  readonly setProviderSummary: React.Dispatch<React.SetStateAction<ProviderSummary | null>>;
  readonly setRuntimeSetupValues: React.Dispatch<React.SetStateAction<RuntimeSetupValues | null>>;
  readonly setSetupRequired: React.Dispatch<React.SetStateAction<boolean>>;
  readonly setSchedulerSettings: React.Dispatch<React.SetStateAction<SchedulerSettings>>;
  readonly setSchedulerStateError: React.Dispatch<React.SetStateAction<string | null>>;
  readonly setSchedulerLoading: React.Dispatch<React.SetStateAction<boolean>>;
  readonly setLanguage: React.Dispatch<React.SetStateAction<Language>>;
  readonly setLabels: React.Dispatch<React.SetStateAction<LocalizedLabels>>;
  readonly loadWatchlistMarketView: (slug: string, shouldApply?: () => boolean) => Promise<void>;
  readonly clearWatchlistMarketView: () => void;
  readonly setupRevision: number;
};

/**
 * Handles the big startup effect: runtime settings → market refresh → watchlists → dashboard data.
 * Extracted from WatchlistDashboard to reduce component complexity.
 */
export function useDashboardBootstrap(state: DashboardBootstrapState, actions: DashboardBootstrapActions): void {
  const {
    selectedWatchlist,
    selectedSymbol,
    language,
    labels,
  } = state;

  const {
    setWatchlists,
    setSelectedWatchlist,
    setSelectedSymbol,
    setWatchlistsLoaded,
    setWatchlistLoadError,
    setStartupRefresh,
    setProviderSummary,
    setRuntimeSetupValues,
    setSetupRequired,
    setSchedulerSettings,
    setSchedulerStateError,
    setSchedulerLoading,
    setLanguage,
    setLabels,
    loadWatchlistMarketView,
    clearWatchlistMarketView,
    setupRevision,
  } = actions;

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
        const response = await apiFetch("/api/startup/market-refresh?no_network=false&include_news=true", { method: "POST" });
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
}
