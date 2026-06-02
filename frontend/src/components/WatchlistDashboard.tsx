"use client";

import { useEffect, useMemo, useState } from "react";
import {
  INITIAL_STARTUP_REFRESH,
  collectionStatusLabel,
  fetchCollectionStatus,
  fetchProviderSummary,
  parseStartupRefresh,
  providerSummaryLabel,
  startupStatusLabel,
  type CollectionAssetStatus,
  type ProviderSummary,
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
import {
  FALLBACK_SCHEDULER_SETTINGS,
  fetchSchedulerSettings,
  patchSchedulerSettings,
  type SchedulerSettings,
} from "@/lib/scheduler-settings";
import { shutdownSystem } from "@/lib/system";

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
  const [symbolValidationPending, setSymbolValidationPending] = useState(false);
  const [startupRefresh, setStartupRefresh] = useState<StartupRefreshView>(INITIAL_STARTUP_REFRESH);
  const [providerSummary, setProviderSummary] = useState<ProviderSummary | null>(null);
  const [collectionStatus, setCollectionStatus] = useState<readonly CollectionAssetStatus[]>([]);
  const [watchlistLoadError, setWatchlistLoadError] = useState<string | null>(null);
  const [watchlistsLoaded, setWatchlistsLoaded] = useState(false);
  const [dashboardLoadError, setDashboardLoadError] = useState<string | null>(null);
  const [setupRequired, setSetupRequired] = useState(false);
  const [setupRevision, setSetupRevision] = useState(0);
  const [schedulerSettings, setSchedulerSettings] = useState<SchedulerSettings>(FALLBACK_SCHEDULER_SETTINGS);
  const [schedulerStateError, setSchedulerStateError] = useState<string | null>(null);
  const [schedulerSaving, setSchedulerSaving] = useState(false);
  const [schedulerLoading, setSchedulerLoading] = useState(false);
  const [systemShutdownMessage, setSystemShutdownMessage] = useState<string | null>(null);
  const [systemShuttingDown, setSystemShuttingDown] = useState(false);
  const [systemShutdownComplete, setSystemShutdownComplete] = useState(false);

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
  const schedulerText = schedulerSettings.weeklyPrecomputeEnabled ? "주간 사전 리포트 켜짐" : "주간 사전 리포트 꺼짐";

  useEffect(() => {
    let cancelled = false;

    async function loadDashboardData(slug: string) {
      const dashboard = await fetchDashboardData(slug);
      if (cancelled) {
        return;
      }
      if (dashboard === null) {
        setDashboardLoadError("대시보드 데이터를 불러오지 못했습니다.");
        return;
      }
      setDashboardLoadError(null);
      setAssetCards(dashboard.assets);
      setSeriesBySymbol(dashboard.series);
    }

    async function loadCollectionStatus(slug: string) {
      const statusRows = await fetchCollectionStatus(slug);
      if (!cancelled) {
        setCollectionStatus(statusRows);
      }
    }

    async function loadSchedulerSettings() {
      setSchedulerLoading(true);
      setSchedulerStateError(null);
      try {
        const nextStatus = await fetchSchedulerSettings();
        if (!cancelled) {
          if (nextStatus === null) {
            setSchedulerSettings(FALLBACK_SCHEDULER_SETTINGS);
            setSchedulerStateError("스케줄러 설정 저장 실패");
          } else {
            setSchedulerSettings(nextStatus);
          }
        }
      } catch (error) {
        logStartupWarning(error, "scheduler status refresh failed");
        if (!cancelled) {
          setSchedulerSettings(FALLBACK_SCHEDULER_SETTINGS);
          setSchedulerStateError("스케줄러 설정 저장 실패");
        }
      } finally {
        if (!cancelled) {
          setSchedulerLoading(false);
        }
      }
    }

    async function refreshMarketData() {
      setWatchlistsLoaded(false);
      try {
        const nextProviderSummary = await fetchProviderSummary();
        if (!cancelled) {
          setProviderSummary(nextProviderSummary);
          if (nextProviderSummary?.firstRunCompleted === false) {
            setSetupRequired(true);
            setStartupRefresh({ ...INITIAL_STARTUP_REFRESH, status: "setup_required" });
            return;
          }
          setSetupRequired(false);
          void loadSchedulerSettings();
        }
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
          setWatchlistLoadError("저장된 관심 그룹이 없습니다.");
          setWatchlists([]);
          setSelectedWatchlist(null);
          setSelectedSymbol("NVDA");
          setCollectionStatus([]);
          setAssetCards({});
          setSeriesBySymbol({});
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
          await loadDashboardData(nextWatchlist.slug);
          await loadCollectionStatus(nextWatchlist.slug);
        }
      } catch (error) {
        logStartupWarning(error, "watchlist load failed");
        if (!cancelled) {
          setWatchlistsLoaded(true);
          setWatchlistLoadError("관심 그룹 목록을 불러오는 데 실패했습니다.");
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
    setStartupRefresh(INITIAL_STARTUP_REFRESH);
    setSetupRevision((value) => value + 1);
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
      setSchedulerStateError("스케줄러 설정 저장 실패");
    } finally {
      setSchedulerSaving(false);
    }
  }

  async function createWatchlist() {
    const trimmed = newWatchlist.trim();
    if (!trimmed) {
      setWatchlistValidationMessage("그룹 이름은 비워둘 수 없습니다.");
      return;
    }
    if (!watchlistsLoaded) {
      setWatchlistValidationMessage("관심 그룹을 불러온 뒤 추가해 주세요.");
      return;
    }

    setWatchlistValidationMessage("");
    try {
      const next = await createWatchlistRequest(trimmed);
      if (next === null) {
        setWatchlistValidationMessage("그룹 생성에 실패했습니다.");
        return;
      }
      setWatchlists((items) => [...items, next]);
      setSelectedWatchlist(next.id);
      setSelectedSymbol(next.symbols[0] ?? "NVDA");
      setNewWatchlist("");
      setWatchlistValidationMessage("");
    } catch (error) {
      logStartupWarning(error, "watchlist create failed");
      setWatchlistValidationMessage("그룹 생성에 실패했습니다.");
    }
  }

  async function addSymbol() {
    const symbol = newSymbol.trim().toUpperCase();
    if (!symbol) {
      setSymbolValidationMessage("종목 코드를 입력해 주세요.");
      return;
    }
    if (selectedWatchlist === null) {
      setSymbolValidationMessage("먼저 관심 그룹을 선택해 주세요.");
      return;
    }
    if (!watchlistsLoaded) {
      setSymbolValidationMessage("관심 그룹을 불러온 뒤 추가해 주세요.");
      return;
    }
    setSymbolValidationPending(true);
    setSymbolValidationMessage("");
    try {
      const response = await fetch(`/api/tickers/validate?symbol=${encodeURIComponent(symbol)}`);
      if (!response.ok) {
        setSymbolValidationMessage("실제 조회 가능한 티커만 추가할 수 있습니다.");
        return;
      }
    } catch (error) {
      logStartupWarning(error, "ticker validation failed");
      setSymbolValidationMessage("티커 확인에 실패했습니다. 네트워크와 데이터 제공자를 확인해주세요.");
      return;
    } finally {
      setSymbolValidationPending(false);
    }

    const addResponse = await addAssetToWatchlist(selectedWatchlist, symbol);
    if (addResponse === null) {
      setSymbolValidationMessage("종목 추가에 실패했습니다.");
      return;
    } else {
      setWatchlists((items) => items.map((item) => (item.id === addResponse.id ? addResponse : item)));
    }

    setSelectedSymbol(symbol);
    setNewSymbol("");
    setSymbolValidationMessage("");
  }

  async function removeSymbol(symbol: string) {
    if (selectedWatchlist === null) {
      setSymbolValidationMessage("먼저 관심 그룹을 선택해 주세요.");
      return;
    }
    setSymbolValidationMessage("");
    try {
      const next = await deleteAssetFromWatchlist(selectedWatchlist, symbol);
      if (next === null) {
        setSymbolValidationMessage("종목 제거에 실패했습니다.");
        return;
      }
      setWatchlists((items) => items.map((item) => (item.id === next.id ? next : item)));
      if (symbol === currentSymbol) {
        setSelectedSymbol(next.symbols[0] ?? "NVDA");
      }
    } catch (error) {
      logStartupWarning(error, "watchlist asset delete failed");
      setSymbolValidationMessage("종목 제거에 실패했습니다.");
    }
  }

  async function shutdownLocalProgram() {
    if (systemShuttingDown || systemShutdownComplete) {
      return;
    }
    const confirm = window.confirm("로컬 프로그램을 종료하시겠습니까?");
    if (!confirm) {
      return;
    }
    setSystemShuttingDown(true);
    setSystemShutdownMessage("종료 처리 중입니다.");
    const result = await shutdownSystem();
    if (!result.ok) {
      setSystemShutdownMessage(result.message);
      setSystemShuttingDown(false);
      return;
    }
    setSystemShuttingDown(false);
    setSystemShutdownMessage("종료 요청이 접수되었습니다.");
    setSystemShutdownComplete(true);
  }

  return (
    <main className="page">
      {setupRequired ? <SetupWizard onCompleted={completeSetup} /> : null}
      {setupRequired ? null : (
        <>
      {startupInProgress ? (
        <div className="startup-refresh-modal" role="status" aria-live="polite">
          주식 정보를 확인하는 중
        </div>
      ) : null}
      {startupRefresh.status === "failed" ? (
        <div className="startup-refresh-banner" role="status" aria-live="polite">
          시장 데이터 갱신 실패
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
          <p className="eyebrow">VBinvest</p>
          <h1>투자 대시보드</h1>
          <p className="subtle">로컬 프로그램에서 관심 그룹과 종목을 관리하고, 차트와 리서치 의견을 같은 화면에서 확인합니다.</p>
        </div>
      </header>

      {!startupInProgress ? (
        <section className={`startup-status-strip ${startupRefresh.status}`} aria-label="startup source status" data-testid="startup-status">
          <strong>{startupStatusLabel(startupRefresh.status)}</strong>
          <span>대기 {startupRefresh.queued} · 진행 {startupRefresh.running} · 성공 {startupRefresh.succeeded} · 실패 {startupRefresh.failed}</span>
          <span>가격 {startupRefresh.priceRows} · 지표 {startupRefresh.indicatorRows}</span>
          <span>뉴스 {startupRefresh.newsItems} · 공시 {startupRefresh.disclosures}</span>
          {providerSummary ? <span>{providerSummaryLabel(providerSummary)}</span> : null}
          {startupRefresh.providerDisabled.length > 0 ? <span>비활성 소스 {startupRefresh.providerDisabled.length}개</span> : null}
        </section>
      ) : null}

      {collectionStatus.length > 0 ? (
        <section className="collection-status-strip" aria-label="data collection status" data-testid="collection-status">
          {collectionStatus.map((item) => (
            <span key={item.symbol} className={`collection-status-pill ${item.status}`}>
              <strong>{item.symbol}</strong>
              <span>{collectionStatusLabel(item.status)}</span>
              <span>최신 {item.latestPriceDate ?? "-"}</span>
              <span>{item.provider ?? "provider 없음"}</span>
              <span>가격 {item.priceRows} / 지표 {item.indicatorRows}</span>
            </span>
          ))}
        </section>
      ) : null}

      <section className="control-panel" aria-label="watchlist controls">
        {watchlistsLoaded && hasWatchlists ? (
          <div className="panel-column">
            <h2>관심 그룹</h2>
            <div className="chips">
              {watchlists.map((watchlist) => (
                <button
                  key={watchlist.id}
                  type="button"
                  className={watchlist.id === selectedWatchlist ? "chip active" : "chip"}
                  onClick={() => {
                    setSelectedWatchlist(watchlist.id);
                    setSelectedSymbol(watchlist.symbols[0] ?? "NVDA");
                  }}
                >
                  {watchlist.name}
                </button>
              ))}
            </div>
          </div>
        ) : null}

        <div className="panel-column">
          <h2>그룹 추가</h2>
          <div className="inline-form">
            <input aria-label="새 그룹 이름" value={newWatchlist} onChange={(event) => setNewWatchlist(event.target.value)} placeholder="AI Memory" />
            <button type="button" onClick={() => void createWatchlist()} disabled={!watchlistsLoaded}>새 그룹</button>
          </div>
          {watchlistValidationMessage ? <p className="research-status error">{watchlistValidationMessage}</p> : null}
        </div>

        <div className="panel-column">
          <h2>종목 추가</h2>
          <div className="inline-form">
            <input aria-label="새 종목 심볼" value={newSymbol} onChange={(event) => setNewSymbol(event.target.value)} placeholder="NVDA" />
            <button type="button" onClick={() => void addSymbol()} disabled={symbolValidationPending || !watchlistsLoaded}>
              {symbolValidationPending ? "확인 중" : "추가"}
            </button>
          </div>
          {symbolValidationMessage ? <p className="research-status error">{symbolValidationMessage}</p> : null}
        </div>

        <div className="panel-column">
          <h2>주간 사전 리포트</h2>
          <div className="inline-form scheduler-toggle-row">
            <span>주간 사전 리포트 계산</span>
            <input
              aria-label="주간 사전 리포트"
              type="checkbox"
              checked={schedulerSettings.weeklyPrecomputeEnabled}
              onChange={(event) => {
                void updateWeeklyPrecompute(event.target.checked);
              }}
              disabled={schedulerLoading || schedulerSaving}
            />
          </div>
          <p className="research-status">기본은 꺼짐(오프)이며 필요할 때만 사용합니다.</p>
          <p className="research-status">리포트 발행은 수동 버튼으로 동일하게 실행할 수 있습니다.</p>
          <p className="research-status">{schedulerText}</p>
          {schedulerStateError ? <p className="research-status error">{schedulerStateError}</p> : null}
        </div>

        <div className="panel-column">
          <h2>시스템 제어</h2>
          <button
            type="button"
            onClick={() => void shutdownLocalProgram()}
            disabled={systemShuttingDown || systemShutdownComplete}
          >
            종료
          </button>
          {systemShutdownMessage ? (
            <p className={`research-status ${systemShutdownComplete ? "success" : systemShuttingDown ? "" : "error"}`}>
              {systemShutdownMessage}
            </p>
          ) : null}
        </div>
      </section>

      {watchlistsLoaded && !hasWatchlists ? (
        <section className="startup-refresh-banner" role="status" aria-live="polite">
          표시할 관심 그룹이 없습니다.
        </section>
      ) : null}

      {watchlistsLoaded && hasWatchlists && !activeWatchlistHasSymbols ? (
        <section className="startup-refresh-banner" role="status" aria-live="polite">
          선택한 관심 그룹에 종목이 없습니다.
        </section>
      ) : null}

      {canShowDashboard ? (
        <section className="content-grid">
          <aside className="watchlist-card">
            <div className="card-heading">
              <h2>{activeWatchlist?.name}</h2>
              <span>{activeWatchlist?.symbols.length ?? 0}개 종목</span>
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
                      aria-label={`${symbol} 제거`}
                    >
                      제거
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
              <div><b>현재가</b><span>{asset.price.toLocaleString()}</span></div>
              <div><b>1D</b><span>{asset.delta1d}</span></div>
              <div><b>1M</b><span>{asset.delta1m}</span></div>
              <div><b>RSI14</b><span>{formatNumber(asset.rsi14)}</span></div>
              <div><b>MA5 / 20 / 50 / 120</b><span>{formatMa(asset)}</span></div>
            </div>

            <ChartShell symbol={asset.symbol} points={points} />

            <ResearchCard symbol={asset.symbol} />
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
