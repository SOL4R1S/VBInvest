"use client";

import { useEffect, useMemo, useState } from "react";
import {
  INITIAL_STARTUP_REFRESH,
  fetchProviderSummary,
  parseStartupRefresh,
  providerSummaryLabel,
  startupStatusLabel,
  type ProviderSummary,
  type StartupRefreshView,
} from "@/lib/startup-status";
import {
  DEFAULT_WATCHLISTS,
  fallbackAsset,
  fetchDashboardData,
  formatMa,
  formatNumber,
  type AssetCard,
  type ChartPoint,
} from "@/lib/dashboard-data";
import { ChartShell } from "@/components/ChartShell";
import { ResearchCard } from "@/components/ResearchCard";

type Watchlist = {
  readonly id: string;
  readonly name: string;
  readonly symbols: readonly string[];
};

export function WatchlistDashboard() {
  const [watchlists, setWatchlists] = useState<readonly Watchlist[]>(DEFAULT_WATCHLISTS);
  const [selectedWatchlist, setSelectedWatchlist] = useState(DEFAULT_WATCHLISTS[0]?.id ?? "semiconductor-core");
  const [selectedSymbol, setSelectedSymbol] = useState(DEFAULT_WATCHLISTS[0]?.symbols[0] ?? "NVDA");
  const [assetCards, setAssetCards] = useState<Record<string, AssetCard>>({});
  const [seriesBySymbol, setSeriesBySymbol] = useState<Record<string, ChartPoint[]>>({});
  const [newWatchlist, setNewWatchlist] = useState("");
  const [newSymbol, setNewSymbol] = useState("");
  const [symbolValidationMessage, setSymbolValidationMessage] = useState("");
  const [symbolValidationPending, setSymbolValidationPending] = useState(false);
  const [startupRefresh, setStartupRefresh] = useState<StartupRefreshView>(INITIAL_STARTUP_REFRESH);
  const [providerSummary, setProviderSummary] = useState<ProviderSummary | null>(null);

  const activeWatchlist = watchlists.find((item) => item.id === selectedWatchlist) ?? watchlists[0];
  const currentSymbol = activeWatchlist?.symbols.includes(selectedSymbol) ? selectedSymbol : activeWatchlist?.symbols[0] ?? "NVDA";
  const asset = assetCards[currentSymbol] ?? fallbackAsset(currentSymbol);
  const points = useMemo(() => seriesBySymbol[currentSymbol] ?? [], [currentSymbol, seriesBySymbol]);

  useEffect(() => {
    let cancelled = false;

    async function loadDashboardData(slug: string) {
      const dashboard = await fetchDashboardData(slug);
      if (cancelled || dashboard === null) {
        return;
      }
      setAssetCards(dashboard.assets);
      setSeriesBySymbol(dashboard.series);
      setWatchlists((items) =>
        items.map((item) => (item.id === slug ? { ...item, symbols: dashboard.symbols } : item)),
      );
      setSelectedSymbol((symbol) => (dashboard.symbols.includes(symbol) ? symbol : dashboard.symbols[0] ?? symbol));
    }

    async function refreshMarketData() {
      try {
        const nextProviderSummary = await fetchProviderSummary();
        if (!cancelled) {
          setProviderSummary(nextProviderSummary);
          if (nextProviderSummary?.firstRunCompleted === false) {
            setStartupRefresh({ ...INITIAL_STARTUP_REFRESH, status: "setup_required" });
            await loadDashboardData("semiconductor-core");
            return;
          }
        }
      } catch (error) {
        logStartupWarning(error, "settings status refresh failed");
      }
      try {
        const response = await fetch("/api/backend/startup/market-refresh?no_network=false&include_news=true", { method: "POST" });
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
        await loadDashboardData("semiconductor-core");
      } catch (error) {
        logStartupWarning(error, "dashboard data refresh failed");
      }
    }

    void refreshMarketData();

    return () => {
      cancelled = true;
    };
  }, []);

  function createWatchlist() {
    const trimmed = newWatchlist.trim();
    if (!trimmed) {
      return;
    }
    const id = `wl-${trimmed.toLowerCase().replace(/[^a-z0-9가-힣]+/g, "-")}`;
    const next = { id, name: trimmed, symbols: [] };
    setWatchlists((items) => [...items, next]);
    setSelectedWatchlist(id);
    setSelectedSymbol("NVDA");
    setNewWatchlist("");
  }

  async function addSymbol() {
    const symbol = newSymbol.trim().toUpperCase();
    if (!symbol) {
      return;
    }
    setSymbolValidationPending(true);
    setSymbolValidationMessage("");
    try {
      const response = await fetch(`/api/backend/tickers/validate?symbol=${encodeURIComponent(symbol)}`);
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
    setWatchlists((items) =>
      items.map((item) =>
        item.id === selectedWatchlist && !item.symbols.includes(symbol)
          ? { ...item, symbols: [...item.symbols, symbol] }
          : item,
      ),
    );
    setSelectedSymbol(symbol);
    setNewSymbol("");
    setSymbolValidationMessage("");
  }

  return (
    <main className="page">
      {startupRefresh.status === "checking" ? (
        <div className="startup-refresh-modal" role="status" aria-live="polite">
          주식 정보를 확인하는 중
        </div>
      ) : null}
      {startupRefresh.status === "failed" ? (
        <div className="startup-refresh-banner" role="status" aria-live="polite">
          시장 데이터 갱신 실패
        </div>
      ) : null}

      <header className="hero">
        <div>
          <p className="eyebrow">VBinvest</p>
          <h1>투자 대시보드</h1>
          <p className="subtle">로컬 프로그램에서 관심 그룹과 종목을 관리하고, 차트와 리서치 의견을 같은 화면에서 확인합니다.</p>
        </div>
      </header>

      {startupRefresh.status !== "checking" ? (
        <section className={`startup-status-strip ${startupRefresh.status}`} aria-label="startup source status" data-testid="startup-status">
          <strong>{startupStatusLabel(startupRefresh.status)}</strong>
          <span>가격 {startupRefresh.priceRows} · 지표 {startupRefresh.indicatorRows}</span>
          <span>뉴스 {startupRefresh.newsItems} · 공시 {startupRefresh.disclosures}</span>
          {providerSummary ? <span>{providerSummaryLabel(providerSummary)}</span> : null}
          {startupRefresh.providerDisabled.length > 0 ? <span>비활성 소스 {startupRefresh.providerDisabled.length}개</span> : null}
        </section>
      ) : null}

      <section className="control-panel" aria-label="watchlist controls">
        <div className="panel-column">
          <h2>관심 그룹</h2>
          <div className="chips">
            {watchlists.map((watchlist) => (
              <button key={watchlist.id} type="button" className={watchlist.id === selectedWatchlist ? "chip active" : "chip"} onClick={() => {
                setSelectedWatchlist(watchlist.id);
                setSelectedSymbol(watchlist.symbols[0]);
              }}>
                {watchlist.name}
              </button>
            ))}
          </div>
        </div>

        <div className="panel-column">
          <h2>그룹 추가</h2>
          <div className="inline-form">
            <input aria-label="새 그룹 이름" value={newWatchlist} onChange={(event) => setNewWatchlist(event.target.value)} placeholder="AI Memory" />
            <button type="button" onClick={createWatchlist}>새 그룹</button>
          </div>
        </div>

        <div className="panel-column">
          <h2>종목 추가</h2>
          <div className="inline-form">
            <input aria-label="새 종목 심볼" value={newSymbol} onChange={(event) => setNewSymbol(event.target.value)} placeholder="NVDA" />
            <button type="button" onClick={() => void addSymbol()} disabled={symbolValidationPending}>
              {symbolValidationPending ? "확인 중" : "추가"}
            </button>
          </div>
          {symbolValidationMessage ? <p className="research-status error">{symbolValidationMessage}</p> : null}
        </div>
      </section>

      <section className="content-grid">
        <aside className="watchlist-card">
          <div className="card-heading">
            <h2>{activeWatchlist.name}</h2>
            <span>{activeWatchlist.symbols.length}개 종목</span>
          </div>
          <div className="symbol-list">
            {(activeWatchlist?.symbols ?? []).map((symbol) => {
              const item = assetCards[symbol];
              return (
                <button key={symbol} type="button" className={symbol === currentSymbol ? "symbol-row active" : "symbol-row"} onClick={() => setSelectedSymbol(symbol)} data-testid={`symbol-${symbol}`}>
                  <strong>{item?.displayNameKo ?? symbol}</strong>
                  <span>{symbol}</span>
                </button>
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
