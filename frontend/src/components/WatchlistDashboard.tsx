"use client";

import { useEffect, useMemo, useState } from "react";
import { APPROVED_OPINIONS } from "@/lib/research";
import { ASSETS, WATCHLISTS, buildSeries } from "@/lib/mock-data";
import { ChartShell } from "@/components/ChartShell";
import { signInWithProvider } from "@/lib/supabase-auth";

type Watchlist = {
  readonly id: string;
  readonly name: string;
  readonly symbols: readonly string[];
};

type StartupRefreshState = "checking" | "ready" | "failed";

function fallbackAsset(symbol: string) {
  return {
    symbol,
    displayNameKo: symbol,
    opinion: "중립" as const,
    price: 0,
    delta1d: "0.00%",
    delta1m: "0.00%",
  };
}

export function WatchlistDashboard() {
  const [watchlists, setWatchlists] = useState<readonly Watchlist[]>(WATCHLISTS);
  const [selectedWatchlist, setSelectedWatchlist] = useState(WATCHLISTS[0]?.id ?? "default");
  const [selectedSymbol, setSelectedSymbol] = useState(WATCHLISTS[0]?.symbols[0] ?? "NVDA");
  const [newWatchlist, setNewWatchlist] = useState("");
  const [newSymbol, setNewSymbol] = useState("");
  const [startupRefreshState, setStartupRefreshState] = useState<StartupRefreshState>("checking");

  const activeWatchlist = watchlists.find((item) => item.id === selectedWatchlist) ?? watchlists[0];
  const currentSymbol = activeWatchlist?.symbols.includes(selectedSymbol) ? selectedSymbol : activeWatchlist?.symbols[0] ?? "NVDA";
  const asset = ASSETS[currentSymbol] ?? fallbackAsset(currentSymbol);
  const points = useMemo(() => buildSeries(currentSymbol), [currentSymbol]);

  useEffect(() => {
    let cancelled = false;

    async function refreshMarketData() {
      try {
        const response = await fetch("/api/backend/startup/market-refresh?no_network=false", { method: "POST" });
        if (!response.ok) {
          throw new Error(`startup market refresh failed: ${response.status}`);
        }
        if (!cancelled) {
          setStartupRefreshState("ready");
        }
      } catch (error) {
        if (error instanceof Error) {
          console.warn(error.message);
        } else {
          console.warn("startup market refresh failed");
        }
        if (!cancelled) {
          setStartupRefreshState("failed");
        }
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

  function addSymbol() {
    const symbol = newSymbol.trim().toUpperCase();
    if (!symbol) {
      return;
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
  }

  return (
    <main className="page">
      {startupRefreshState === "checking" ? (
        <div className="startup-refresh-modal" role="status" aria-live="polite">
          주식 정보를 확인하는 중
        </div>
      ) : null}
      {startupRefreshState === "failed" ? (
        <div className="startup-refresh-banner" role="status" aria-live="polite">
          시장 데이터 갱신 실패
        </div>
      ) : null}

      <header className="hero">
        <div>
          <p className="eyebrow">VBinvest</p>
          <h1>투자 대시보드</h1>
          <p className="subtle">로그인 후 관심 그룹과 종목을 관리하고, 차트와 리서치 의견을 같은 화면에서 확인합니다.</p>
        </div>
        <div className="auth-buttons">
          <button type="button" onClick={() => void signInWithProvider("google")}>Google로 로그인</button>
          <button type="button" onClick={() => void signInWithProvider("kakao")}>Kakao로 로그인</button>
        </div>
      </header>

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
            <button type="button" onClick={addSymbol}>추가</button>
          </div>
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
              const item = ASSETS[symbol];
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
            <div><b>RSI14</b><span>52.4</span></div>
            <div><b>MA5 / 20 / 50 / 120</b><span>예시 값</span></div>
          </div>

          <ChartShell symbol={asset.symbol} points={points} />

          <article className="research-card">
            <h3>리서치 의견</h3>
            <p>아직 발행된 리서치가 없습니다. 현재는 DB 가격/지표를 기반으로 차트를 확인할 수 있습니다.</p>
            <button type="button">리포트 발행</button>
            <div className="badge-row">
              {APPROVED_OPINIONS.map((opinion) => (
                <span key={opinion} className={`badge ${opinion}`}>{opinion}</span>
              ))}
            </div>
          </article>
        </section>
      </section>
    </main>
  );
}
