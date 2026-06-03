import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { APPROVED_OPINIONS } from "@/lib/research";
import { WatchlistDashboard } from "@/components/WatchlistDashboard";
import { SetupWizard } from "@/components/SetupWizard";
import { labelFor, type Language } from "@/lib/i18n";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function dashboardResponse(): Response {
  return jsonResponse({
    watchlist: "semiconductor-core",
    count: 2,
    items: [
      {
        asset: { symbol: "NVDA", display_name_ko: "엔비디아", currency: "USD" },
        latest: {
          date: "2026-06-01",
          close: 999.12,
          return_1d: 0.0388,
          return_1m: 0.125,
          ma5: 990.1,
          ma20: 970.2,
          ma50: 950.3,
          ma120: 930.4,
          rsi14: 64.2,
        },
        opinion: "아웃퍼폼",
        history: [
          { date: "2026-05-29", open: 980, high: 995, low: 970, close: 990, volume: 1000, ma5: 985, ma20: 970, ma50: 950, ma120: 930, rsi14: 61.1 },
          { date: "2026-06-01", open: 990, high: 1005, low: 985, close: 999.12, volume: 1200, ma5: 990.1, ma20: 970.2, ma50: 950.3, ma120: 930.4, rsi14: 64.2 },
        ],
      },
      {
        asset: { symbol: "005930.KS", display_name_ko: "삼성전자", currency: "KRW" },
        latest: {
          date: "2026-06-01",
          close: 81200,
          return_1d: -0.005,
          return_1m: 0.031,
          ma5: 80800,
          ma20: 79900,
          ma50: 78500,
          ma120: 77100,
          rsi14: 55.5,
        },
        opinion: "중립",
        history: [
          { date: "2026-05-29", open: 80000, high: 81500, low: 79800, close: 81000, volume: 2000, ma5: 80600, ma20: 79700, ma50: 78300, ma120: 77000, rsi14: 54.1 },
          { date: "2026-06-01", open: 81000, high: 81800, low: 80600, close: 81200, volume: 2200, ma5: 80800, ma20: 79900, ma50: 78500, ma120: 77100, rsi14: 55.5 },
        ],
      },
    ],
  });
}

function singleAssetDashboardResponse(slug: string, symbol: string, displayNameKo: string, close: number): Response {
  return jsonResponse({
    watchlist: slug,
    count: 1,
    items: [
      {
        asset: { symbol, display_name_ko: displayNameKo, currency: "USD" },
        latest: {
          date: "2026-06-02",
          close,
          return_1d: 0.012,
          return_1m: 0.034,
          ma5: close - 1,
          ma20: close - 2,
          ma50: close - 3,
          ma120: close - 4,
          rsi14: 57.1,
        },
        opinion: "중립",
        history: [
          { date: "2026-06-01", open: close - 2, high: close, low: close - 3, close: close - 1, volume: 900, ma5: close - 2, ma20: close - 3, ma50: close - 4, ma120: close - 5, rsi14: 55.2 },
          { date: "2026-06-02", open: close - 1, high: close + 1, low: close - 2, close, volume: 1100, ma5: close - 1, ma20: close - 2, ma50: close - 3, ma120: close - 4, rsi14: 57.1 },
        ],
      },
    ],
  });
}

function collectionStatusResponse(): Response {
  return jsonResponse({
    watchlist: "semiconductor-core",
    assets: [
      {
        symbol: "NVDA",
        display_name_ko: "엔비디아",
        exchange: "NASDAQ",
        provider: "yfinance",
        latest_price_date: "2026-06-01",
        latest_fetched_at: "2026-06-02T01:00:00+00:00",
        price_rows: 260,
        indicator_rows: 260,
        has_synthetic: false,
        status: "collected",
      },
      {
        symbol: "005930.KS",
        display_name_ko: "삼성전자",
        exchange: "KRX",
        provider: "synthetic",
        latest_price_date: "2026-06-01",
        latest_fetched_at: "2026-06-02T01:00:00+00:00",
        price_rows: 260,
        indicator_rows: 260,
        has_synthetic: true,
        status: "synthetic",
      },
    ],
  });
}

function watchlistsResponse(): Response {
  return jsonResponse({
    watchlists: [
      { watchlist_id: "semiconductor-core", slug: "semiconductor-core", name: "Semiconductor Core", symbols: ["NVDA", "005930.KS", "000660.KS"] },
    ],
  });
}

function shutdownResponse(): Response {
  return jsonResponse({ status: "shutting_down" }, 200);
}

function watchlistsResponseWithBody(body: unknown): Response {
  return jsonResponse(body);
}

async function waitForWatchlistControls(): Promise<void> {
  await waitFor(() => {
    expect(screen.getByRole("button", { name: "새 그룹" })).not.toBeDisabled();
  });
}

function headerValue(init: RequestInit | undefined, key: string): string | null {
  const headers = init?.headers;
  if (headers instanceof Headers) {
    return headers.get(key);
  }
  if (Array.isArray(headers)) {
    const entry = headers.find(([name]) => name.toLowerCase() === key.toLowerCase());
    return entry?.[1] ?? null;
  }
  if (headers !== undefined) {
    const entries = Object.entries(headers);
    const entry = entries.find(([name]) => name.toLowerCase() === key.toLowerCase());
    return entry?.[1] ?? null;
  }
  return null;
}

function hasFetchCall(fetchMock: MockedFetch, expectedUrl: string): boolean {
  return fetchMock.mock.calls.some(([input]) => String(input) === expectedUrl);
}

function hasFetchCallWithMethod(fetchMock: MockedFetch, expectedUrl: string, expectedMethod: string): boolean {
  return fetchMock.mock.calls.some(([input, init]) => String(input) === expectedUrl && init?.method === expectedMethod);
}

function hasFetchCallWithHeaders(
  fetchMock: MockedFetch,
  expectedUrl: string,
  expectedMethod: string,
  expectedHeaders: Record<string, string>,
): boolean {
  return fetchMock.mock.calls.some(([input, init]) => {
    if (String(input) !== expectedUrl || init?.method !== expectedMethod) {
      return false;
    }
    return Object.entries(expectedHeaders).every(([key, value]) => headerValue(init, key) === value);
  });
}

type FetchMock = (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>;
type MockedFetch = { mock: { calls: Array<Parameters<FetchMock>> } };
type TestStorage = Pick<Storage, "getItem" | "setItem" | "removeItem" | "clear">;

function schedulerSettingsResponse(): Response {
  return jsonResponse({
    daily_refresh_enabled: true,
    weekly_precompute_enabled: false,
    watchlist: "semiconductor-core",
    include_news: true,
  });
}

function withSchedulerFallback(fetchMock: FetchMock): FetchMock {
  return async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    if (String(input).includes("/api/scheduler/settings") && (init?.method === undefined || init.method === "GET")) {
      return schedulerSettingsResponse();
    }
    if (init === undefined) {
      return fetchMock(input);
    }
    return fetchMock(input, init);
  };
}

describe("WatchlistDashboard", () => {
  beforeEach(() => {
    const storage = createTestStorage({ vbinvest_language: "ko" });
    Object.defineProperty(window, "localStorage", { value: storage, configurable: true });
    Object.defineProperty(window.navigator, "language", { value: "ko-KR", configurable: true });
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, _init?: RequestInit): Promise<Response> => {
        if (String(input).includes("/api/watchlists/semiconductor-core/dashboard")) {
          return dashboardResponse();
        }
        if (String(input).includes("/api/watchlists/semiconductor-core/collection-status")) {
          return collectionStatusResponse();
        }
        if (String(input).includes("/api/scheduler/settings")) {
          return schedulerSettingsResponse();
        }
        if (String(input).includes("/api/watchlists")) {
          return watchlistsResponse();
        }
        return jsonResponse({ status: "ok", price_rows: 1, indicator_rows: 1, news_items: 0, disclosures: 0 });
      }),
    );
  });

  afterEach(() => {
    delete window.__VBINVEST_LOCAL_SESSION_TOKEN__;
    vi.unstubAllGlobals();
  });

  it("renders the investing dashboard shell with approved labels and chart controls", async () => {
    render(<WatchlistDashboard />);

    expect(screen.getByRole("heading", { name: "투자 대시보드" })).toBeInTheDocument();
    expect(screen.queryAllByText(/로 로그인/)).toHaveLength(0);
    expect(await screen.findByTestId("mode-line")).toHaveTextContent("라인");
    expect(screen.getByTestId("mode-candle")).toHaveTextContent("캔들");
    expect(screen.getByTestId("mode-candle")).toHaveClass("active");
    expect(screen.getByTestId("chart-frame")).toHaveAttribute("data-chart-mode", "candle");
    expect(screen.getByTestId("chart-reset")).toHaveTextContent("줌 초기화");
    expect(screen.getByTestId("legend-close")).toHaveTextContent("종가");
    expect(screen.getByTestId("legend-ma5")).toHaveTextContent("MA5");
    expect(screen.getByTestId("legend-ma20")).toHaveTextContent("MA20");
    expect(screen.getByTestId("legend-ma50")).toHaveTextContent("MA50");
    expect(screen.getByTestId("legend-ma120")).toHaveTextContent("MA120");

    for (const opinion of APPROVED_OPINIONS) {
      expect(screen.getAllByText(opinion).length).toBeGreaterThan(0);
    }
    await waitFor(() => {
      expect(screen.getByText("999.12")).toBeInTheDocument();
    });
  });

  it("switches dashboard language and persists it with the local session token", async () => {
    window.__VBINVEST_LOCAL_SESSION_TOKEN__ = "local-token";
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
      const url = String(input);
      if (url === "/api/settings/language" && init?.method === "PATCH") {
        return jsonResponse({ language: "en" });
      }
      if (url === "/api/settings") {
        return jsonResponse({
          language: "ko",
          provider_status: { opendart: { configured: true }, ai: { mode: "local" } },
        });
      }
      if (url.includes("/api/watchlists/semiconductor-core/dashboard")) {
        return dashboardResponse();
      }
      if (url.includes("/api/watchlists/semiconductor-core/collection-status")) {
        return collectionStatusResponse();
      }
      if (url === "/api/watchlists") {
        return watchlistsResponse();
      }
      return jsonResponse({ status: "ok", price_rows: 1, indicator_rows: 1, news_items: 0, disclosures: 0 });
    });
    vi.stubGlobal("fetch", withSchedulerFallback(fetchMock));

    render(<WatchlistDashboard />);

    expect(await screen.findByRole("heading", { name: "투자 대시보드" })).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("언어"), { target: { value: "en" } });

    expect(await screen.findByRole("heading", { name: "Investment Dashboard" })).toBeInTheDocument();
    const patchCall = fetchMock.mock.calls.find(([input, init]) => String(input) === "/api/settings/language" && init?.method === "PATCH");
    expect(patchCall).toBeDefined();
    const patchInit = patchCall?.[1];
    expect(headerValue(patchInit, "Authorization")).toBe("Bearer local-token");
    expect(JSON.parse(String(patchInit?.body))).toEqual({ language: "en" });
    expect(window.localStorage.getItem("vbinvest_language")).toBe("en");
  });

  it("loads persisted watchlists from backend and renders them from /api/watchlists", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, _init?: RequestInit): Promise<Response> => {
      const url = String(input);
      if (url === "/api/watchlists") {
        return watchlistsResponseWithBody({ watchlists: [{ watchlist_id: "qa-persisted-id", slug: "qa-persisted", name: "QA Persisted", symbols: ["AAPL", "005930.KS"] }] });
      }
      if (url.includes("/api/watchlists/qa-persisted/dashboard")) {
        return jsonResponse({
          watchlist: "qa-persisted",
          count: 1,
          items: [
            {
              asset: { symbol: "AAPL", display_name_ko: "애플", currency: "USD" },
              latest: {
                date: "2026-06-01",
                close: 180.25,
                return_1d: 0.01,
                return_1m: 0.03,
                ma5: 178.5,
                ma20: 175.1,
                ma50: 170.2,
                ma120: 165.4,
                rsi14: 63.5,
              },
              opinion: "중립",
              history: [{ date: "2026-06-01", open: 179, high: 181, low: 178, close: 180.25, volume: 1200, ma5: 178.5, ma20: 175.1, ma50: 170.2, ma120: 165.4, rsi14: 63.5 }],
            },
          ],
        });
      }
      return jsonResponse({ status: "ok", price_rows: 1, indicator_rows: 1, news_items: 0, disclosures: 0 });
    });
    vi.stubGlobal("fetch", withSchedulerFallback(fetchMock));

    render(<WatchlistDashboard />);

    await waitFor(() => {
      expect(hasFetchCall(fetchMock, "/api/watchlists")).toBe(true);
    });
    expect(await screen.findByRole("button", { name: "QA Persisted" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Semiconductor Core" })).not.toBeInTheDocument();
    expect(await screen.findByTestId("symbol-AAPL")).toHaveTextContent("AAPL");
    expect(await screen.findByTestId("symbol-005930.KS")).toHaveTextContent("005930.KS");
    expect(screen.getByRole("heading", { name: "애플" })).toBeInTheDocument();

    fireEvent.click(screen.getByTestId("symbol-005930.KS"));

    expect(screen.getByRole("heading", { name: "005930.KS" })).toBeInTheDocument();
  });

  it("calls /api/system/shutdown after confirmation and shows shutdown state", async () => {
    const confirmMock = vi.spyOn(window, "confirm").mockReturnValue(true);
    window.__VBINVEST_LOCAL_SESSION_TOKEN__ = "qa-task15-token";
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
      const url = String(input);
      if (url === "/api/system/shutdown" && init?.method === "POST") {
        return shutdownResponse();
      }
      if (url.includes("/api/watchlists/semiconductor-core/dashboard")) {
        return dashboardResponse();
      }
      if (url.includes("/api/watchlists/semiconductor-core/collection-status")) {
        return collectionStatusResponse();
      }
      if (url.includes("/api/scheduler/settings")) {
        return schedulerSettingsResponse();
      }
      if (url.includes("/api/watchlists")) {
        return watchlistsResponse();
      }
      return jsonResponse({ status: "ok", price_rows: 1, indicator_rows: 1, news_items: 0, disclosures: 0 });
    });
    vi.stubGlobal("fetch", withSchedulerFallback(fetchMock));

    render(<WatchlistDashboard />);

    await waitForWatchlistControls();
    fireEvent.click(screen.getByRole("button", { name: "종료" }));
    expect(confirmMock).toHaveBeenCalledTimes(1);
    await waitFor(() => {
      expect(screen.getByText("종료 요청이 접수되었습니다.")).toBeInTheDocument();
    });
    expect(
      hasFetchCallWithHeaders(fetchMock, "/api/system/shutdown", "POST", { Authorization: "Bearer qa-task15-token" }),
    ).toBe(true);

    const shutdownButton = screen.getByRole("button", { name: "종료" });
    expect(shutdownButton).toBeDisabled();
    fireEvent.click(shutdownButton);
    expect(
      fetchMock.mock.calls.filter(([input, requestInit]) => String(input) === "/api/system/shutdown" && requestInit?.method === "POST")
        .length,
    ).toBe(1);
    confirmMock.mockRestore();
  });

  it("places shutdown beside settings in the top action area", async () => {
    render(<WatchlistDashboard />);

    await waitForWatchlistControls();
    const actionArea = screen.getByLabelText("application actions");
    expect(within(actionArea).getByRole("button", { name: "설정" })).toBeInTheDocument();
    expect(within(actionArea).getByRole("button", { name: "종료" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "시스템 제어" })).not.toBeInTheDocument();
  });

  it("sends a shutdown beacon when the local app page is closed", async () => {
    window.__VBINVEST_LOCAL_SESSION_TOKEN__ = "qa-beacon-token";
    const sendBeacon = vi.fn<(url: string, data?: BodyInit | null) => boolean>(() => true);
    vi.stubGlobal("navigator", { ...window.navigator, sendBeacon });

    render(<WatchlistDashboard />);

    await waitForWatchlistControls();
    fireEvent(window, new Event("pagehide"));

    expect(sendBeacon).toHaveBeenCalledTimes(1);
    const [url, payload] = sendBeacon.mock.calls[0] ?? [];
    expect(url).toBe("/api/system/shutdown-beacon");
    expect(payload).toBeInstanceOf(Blob);
    expect((payload as Blob).type).toBe("application/json");
  });

  it("shows a safe shutdown error message when shutdown is not available", async () => {
    const confirmMock = vi.spyOn(window, "confirm").mockReturnValue(true);
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
      const url = String(input);
      if (url === "/api/system/shutdown" && init?.method === "POST") {
        return jsonResponse({ detail: "shutdown unavailable" }, 503);
      }
      if (url.includes("/api/watchlists/semiconductor-core/dashboard")) {
        return dashboardResponse();
      }
      if (url.includes("/api/watchlists/semiconductor-core/collection-status")) {
        return collectionStatusResponse();
      }
      if (url.includes("/api/scheduler/settings")) {
        return schedulerSettingsResponse();
      }
      if (url.includes("/api/watchlists")) {
        return watchlistsResponse();
      }
      return jsonResponse({ status: "ok", price_rows: 1, indicator_rows: 1, news_items: 0, disclosures: 0 });
    });
    vi.stubGlobal("fetch", withSchedulerFallback(fetchMock));

    render(<WatchlistDashboard />);

    await waitForWatchlistControls();
    fireEvent.click(screen.getByRole("button", { name: "종료" }));
    expect(confirmMock).toHaveBeenCalledTimes(1);
    await waitFor(() => {
      expect(screen.getByText("종료 요청이 현재 비활성화되어 있습니다.")).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: "종료" })).not.toBeDisabled();
    confirmMock.mockRestore();
  });

  it("does not render demo symbols before persisted watchlists resolve", async () => {
    let resolveWatchlists: (response: Response) => void = () => undefined;
    const watchlistsPromise = new Promise<Response>((resolve) => {
      resolveWatchlists = resolve;
    });
    const fetchMock = vi.fn(async (input: RequestInfo | URL, _init?: RequestInit): Promise<Response> => {
      const url = String(input);
      if (url === "/api/watchlists") {
        return watchlistsPromise;
      }
      if (url.includes("/api/watchlists/semiconductor-core/dashboard")) {
        return dashboardResponse();
      }
      return jsonResponse({ status: "ok", price_rows: 1, indicator_rows: 1, news_items: 0, disclosures: 0 });
    });
    vi.stubGlobal("fetch", withSchedulerFallback(fetchMock));

    render(<WatchlistDashboard />);

    expect(screen.queryByTestId("symbol-NVDA")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Semiconductor Core" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "새 그룹" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "추가" })).toBeDisabled();

    resolveWatchlists(watchlistsResponse());

    expect(await screen.findByTestId("symbol-NVDA")).toHaveTextContent("NVDA");
  });

  it("creates a new group via POST /api/watchlists and adds a symbol via POST /api/watchlists/{id}/assets", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, _init?: RequestInit): Promise<Response> => {
      const url = String(input);
      if (url === "/api/watchlists" && _init?.method === "POST") {
        return jsonResponse({ watchlist_id: "qa-persist-id", slug: "qa-persist", name: "QA Persist", symbols: [] });
      }
      if (url === "/api/watchlists") {
        return watchlistsResponse();
      }
      if (url.includes("/api/watchlists/semiconductor-core/dashboard")) {
        return dashboardResponse();
      }
      if (url.includes("/api/watchlists/qa-persist-id/assets")) {
        return jsonResponse({ watchlist_id: "qa-persist-id", slug: "qa-persist", name: "QA Persist", symbols: ["AAPL"] });
      }
      if (url.includes("/api/tickers/validate?symbol=NVDA")) {
        return jsonResponse({ symbol: "NVDA", valid: true, provider: "yfinance" });
      }
      if (url.includes("/api/tickers/validate?symbol=AAPL")) {
        return jsonResponse({ symbol: "AAPL", valid: true, provider: "yfinance" });
      }
      return jsonResponse({ status: "ok", price_rows: 1, indicator_rows: 1, news_items: 0, disclosures: 0 });
    });
    vi.stubGlobal("fetch", withSchedulerFallback(fetchMock));

    render(<WatchlistDashboard />);

    await waitForWatchlistControls();
    fireEvent.change(screen.getByLabelText("새 그룹 이름"), { target: { value: "QA Persist" } });
    fireEvent.click(screen.getByRole("button", { name: "새 그룹" }));
    await waitFor(() => {
      expect(hasFetchCallWithMethod(fetchMock, "/api/watchlists", "POST")).toBe(true);
    });
    expect(await screen.findByRole("button", { name: "QA Persist" })).toBeInTheDocument();
    expect(await screen.findByText("선택한 관심 그룹에 종목이 없습니다.")).toBeInTheDocument();
    expect(screen.queryByTestId("symbol-NVDA")).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "엔비디아" })).not.toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("새 종목 심볼"), { target: { value: "AAPL" } });
    fireEvent.click(screen.getByRole("button", { name: "추가" }));
    await waitFor(() => {
      expect(hasFetchCall(fetchMock, "/api/tickers/validate?symbol=AAPL")).toBe(true);
    });
    await waitFor(() => {
      expect(hasFetchCallWithMethod(fetchMock, "/api/watchlists/qa-persist-id/assets", "POST")).toBe(true);
    });
    await waitFor(() => {
      expect(screen.getByTestId("symbol-AAPL")).toHaveTextContent("AAPL");
    });
    expect(screen.getByRole("heading", { name: "AAPL" })).toBeInTheDocument();
  });

  it("reloads chart data for the selected group after a validated symbol is added", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
      const url = String(input);
      if (url === "/api/watchlists" && init?.method === "POST") {
        return jsonResponse({ watchlist_id: "qa-persist-id", slug: "qa-persist", name: "QA Persist", symbols: [] });
      }
      if (url === "/api/watchlists") {
        return watchlistsResponse();
      }
      if (url.includes("/api/watchlists/semiconductor-core/dashboard")) {
        return dashboardResponse();
      }
      if (url === "/api/watchlists/qa-persist/dashboard?days=1260") {
        return singleAssetDashboardResponse("qa-persist", "AAPL", "애플", 214.55);
      }
      if (url.includes("/api/watchlists/qa-persist/collection-status")) {
        return jsonResponse({
          watchlist: "qa-persist",
          assets: [
            {
              symbol: "AAPL",
              display_name_ko: "애플",
              exchange: "NASDAQ",
              provider: "yahoo-chart",
              latest_price_date: "2026-06-02",
              latest_fetched_at: "2026-06-03T11:00:00+00:00",
              price_rows: 179,
              indicator_rows: 179,
              has_synthetic: false,
              status: "collected",
            },
          ],
        });
      }
      if (url.includes("/api/watchlists/qa-persist-id/assets")) {
        return jsonResponse({ watchlist_id: "qa-persist-id", slug: "qa-persist", name: "QA Persist", symbols: ["AAPL"] });
      }
      if (url.includes("/api/tickers/validate?symbol=AAPL")) {
        return jsonResponse({ symbol: "AAPL", valid: true, provider: "yahoo-chart" });
      }
      return jsonResponse({ status: "ok", price_rows: 1, indicator_rows: 1, news_items: 0, disclosures: 0 });
    });
    vi.stubGlobal("fetch", withSchedulerFallback(fetchMock));

    render(<WatchlistDashboard />);

    await waitForWatchlistControls();
    fireEvent.change(screen.getByLabelText("새 그룹 이름"), { target: { value: "QA Persist" } });
    fireEvent.click(screen.getByRole("button", { name: "새 그룹" }));
    await screen.findByRole("button", { name: "QA Persist" });

    fireEvent.change(screen.getByLabelText("새 종목 심볼"), { target: { value: "AAPL" } });
    fireEvent.click(screen.getByRole("button", { name: "추가" }));

    await waitFor(() => {
      expect(hasFetchCall(fetchMock, "/api/watchlists/qa-persist/dashboard?days=1260")).toBe(true);
    });
    expect(await screen.findByRole("heading", { name: "애플" })).toBeInTheDocument();
    expect(screen.getByText("214.55")).toBeInTheDocument();
    expect(screen.getByTestId("collection-status")).toHaveTextContent("AAPL");
    expect(screen.getByTestId("collection-status")).toHaveTextContent("가격 179 / 지표 179");
  });

  it("does not add a symbol until the backend validates that the ticker exists", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, _init?: RequestInit): Promise<Response> => {
      const url = String(input);
      if (url === "/api/watchlists" && _init?.method === "POST") {
        return jsonResponse({ watchlist_id: "verify-group-id", slug: "verify-group", name: "검증 그룹", symbols: [] });
      }
      if (url.includes("/api/watchlists/semiconductor-core/dashboard")) {
        return dashboardResponse();
      }
      if (url.includes("/api/watchlists/verify-group-id/assets")) {
        return jsonResponse({ watchlist_id: "verify-group-id", slug: "verify-group", name: "검증 그룹", symbols: ["NOTREAL"] });
      }
      if (url.includes("/api/tickers/validate?symbol=NOTREAL")) {
        return jsonResponse({ detail: "ticker not found" }, 404);
      }
      if (url === "/api/watchlists") {
        return watchlistsResponse();
      }
      return jsonResponse({ status: "ok", price_rows: 1, indicator_rows: 1, news_items: 0, disclosures: 0 });
    });
    vi.stubGlobal("fetch", withSchedulerFallback(fetchMock));

    render(<WatchlistDashboard />);

    await waitForWatchlistControls();
    fireEvent.change(screen.getByLabelText("새 그룹 이름"), { target: { value: "검증 그룹" } });
    fireEvent.click(screen.getByRole("button", { name: "새 그룹" }));
    fireEvent.change(screen.getByLabelText("새 종목 심볼"), { target: { value: "NOTREAL" } });
    fireEvent.click(screen.getByRole("button", { name: "추가" }));

    await waitFor(() => {
      expect(hasFetchCall(fetchMock, "/api/tickers/validate?symbol=NOTREAL")).toBe(true);
    });
    expect(screen.getByText("실제 조회 가능한 티커만 추가할 수 있습니다.")).toBeInTheDocument();
    expect(screen.queryByTestId("symbol-NOTREAL")).not.toBeInTheDocument();
  });

  it("shows a Samsung Electronics ticker suggestion for a common typo", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, _init?: RequestInit): Promise<Response> => {
      const url = String(input);
      if (url.includes("/api/watchlists/semiconductor-core/dashboard")) {
        return dashboardResponse();
      }
      if (url.includes("/api/watchlists/semiconductor-core/collection-status")) {
        return collectionStatusResponse();
      }
      if (url.includes("/api/scheduler/settings")) {
        return schedulerSettingsResponse();
      }
      if (url.includes("/api/tickers/validate?symbol=009530.KS")) {
        return jsonResponse(
          {
            detail: {
              symbol: "009530.KS",
              valid: false,
              reason: "ticker_not_found",
              suggestion: "005930.KS",
              suggestion_label: "삼성전자",
              suggestions: [
                {
                  symbol: "005930.KS",
                  name: "삼성전자",
                  exchange: "KSC",
                  quote_type: "EQUITY",
                },
              ],
            },
          },
          404,
        );
      }
      if (url === "/api/watchlists") {
        return watchlistsResponse();
      }
      return jsonResponse({ status: "ok", price_rows: 1, indicator_rows: 1, news_items: 0, disclosures: 0 });
    });
    vi.stubGlobal("fetch", withSchedulerFallback(fetchMock));

    render(<WatchlistDashboard />);

    await waitForWatchlistControls();
    fireEvent.change(screen.getByLabelText("새 종목 심볼"), { target: { value: "009530.KS" } });
    fireEvent.click(screen.getByRole("button", { name: "추가" }));

    await waitFor(() => {
      expect(screen.getByText("삼성전자는 005930.KS를 사용하세요.")).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: "005930.KS 삼성전자 KSC" })).toBeInTheDocument();
    expect(screen.queryByTestId("symbol-009530.KS")).not.toBeInTheDocument();
  });

  it("adds a ticker from company name search suggestions", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, _init?: RequestInit): Promise<Response> => {
      const url = String(input);
      if (url.includes("/api/watchlists/semiconductor-core/dashboard")) {
        return dashboardResponse();
      }
      if (url.includes("/api/watchlists/semiconductor-core/collection-status")) {
        return collectionStatusResponse();
      }
      if (url.includes("/api/scheduler/settings")) {
        return schedulerSettingsResponse();
      }
      if (url.includes("/api/tickers/validate?symbol=Samsung%20Electronics")) {
        return jsonResponse(
          {
            detail: {
              symbol: "SAMSUNG ELECTRONICS",
              valid: false,
              reason: "ticker_not_found",
              suggestion: "005930.KS",
              suggestion_label: "SamsungElec",
              suggestions: [
                {
                  symbol: "005930.KS",
                  name: "SamsungElec",
                  exchange: "KSC",
                  quote_type: "EQUITY",
                },
                {
                  symbol: "SSNLF",
                  name: "SAMSUNG ELECTRONICS CO",
                  exchange: "PNK",
                  quote_type: "EQUITY",
                },
              ],
            },
          },
          404,
        );
      }
      if (url.includes("/api/tickers/validate?symbol=005930.KS")) {
        return jsonResponse({ symbol: "005930.KS", valid: true, provider: "yfinance" });
      }
      if (url.includes("/api/watchlists/semiconductor-core/assets")) {
        return jsonResponse({
          id: "semiconductor-core",
          slug: "semiconductor-core",
          name: "Semiconductor Core",
          symbols: ["NVDA", "005930.KS"],
        });
      }
      if (url.includes("/api/watchlists/semiconductor-core/dashboard")) {
        return singleAssetDashboardResponse("semiconductor-core", "005930.KS", "삼성전자", 81200);
      }
      if (url === "/api/watchlists") {
        return watchlistsResponseWithBody({
          watchlists: [
            { watchlist_id: "semiconductor-core", slug: "semiconductor-core", name: "Semiconductor Core", symbols: ["NVDA"] },
          ],
        });
      }
      return jsonResponse({ status: "ok", price_rows: 1, indicator_rows: 1, news_items: 0, disclosures: 0 });
    });
    vi.stubGlobal("fetch", withSchedulerFallback(fetchMock));

    render(<WatchlistDashboard />);

    await waitForWatchlistControls();
    fireEvent.change(screen.getByLabelText("새 종목 심볼"), { target: { value: "Samsung Electronics" } });
    fireEvent.click(screen.getByRole("button", { name: "추가" }));

    const suggestion = await screen.findByRole("button", { name: "005930.KS SamsungElec KSC" });
    fireEvent.click(suggestion);

    await waitFor(() => {
      expect(hasFetchCall(fetchMock, "/api/tickers/validate?symbol=005930.KS")).toBe(true);
    });
    expect(hasFetchCall(fetchMock, "/api/watchlists/semiconductor-core/assets")).toBe(true);
  });

  it("shows ticker autocomplete suggestions while typing Korean company prefixes", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, _init?: RequestInit): Promise<Response> => {
      const url = String(input);
      if (url.includes("/api/watchlists/semiconductor-core/dashboard")) {
        return dashboardResponse();
      }
      if (url.includes("/api/watchlists/semiconductor-core/collection-status")) {
        return collectionStatusResponse();
      }
      if (url.includes("/api/scheduler/settings")) {
        return schedulerSettingsResponse();
      }
      if (url.includes("/api/tickers/search?query=%EC%82%BC")) {
        return jsonResponse({
          query: "삼",
          suggestions: [
            { symbol: "005930.KS", name: "삼성전자", exchange: "KSC", quote_type: "EQUITY" },
            { symbol: "009150.KS", name: "삼성전기", exchange: "KSC", quote_type: "EQUITY" },
          ],
        });
      }
      if (url === "/api/watchlists") {
        return watchlistsResponse();
      }
      return jsonResponse({ status: "ok", price_rows: 1, indicator_rows: 1, news_items: 0, disclosures: 0 });
    });
    vi.stubGlobal("fetch", withSchedulerFallback(fetchMock));

    render(<WatchlistDashboard />);

    await waitForWatchlistControls();
    fireEvent.change(screen.getByLabelText("새 종목 심볼"), { target: { value: "삼" } });

    expect(await screen.findByRole("button", { name: "005930.KS 삼성전자 KSC" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "009150.KS 삼성전기 KSC" })).toBeInTheDocument();
    expect(hasFetchCall(fetchMock, "/api/tickers/search?query=%EC%82%BC&limit=8")).toBe(true);
  });

  it("rejects empty group names with a Korean error", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, _init?: RequestInit): Promise<Response> => {
      const url = String(input);
      if (url.includes("/api/watchlists/semiconductor-core/dashboard")) {
        return dashboardResponse();
      }
      return jsonResponse({ status: "ok", price_rows: 1, indicator_rows: 1, news_items: 0, disclosures: 0 });
    });
    vi.stubGlobal("fetch", withSchedulerFallback(fetchMock));

    render(<WatchlistDashboard />);

    await waitForWatchlistControls();
    fireEvent.click(screen.getByRole("button", { name: "새 그룹" }));
    await waitFor(() => {
      expect(screen.getByText("그룹 이름은 비워둘 수 없습니다.")).toBeInTheDocument();
    });
    expect(
      fetchMock.mock.calls.every(([input, init]) => !(String(input) === "/api/watchlists" && init?.method === "POST")),
    ).toBe(true);
  });

  it("rejects empty symbols and keeps the watchlist unchanged", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, _init?: RequestInit): Promise<Response> => {
      const url = String(input);
      if (url === "/api/watchlists") {
        return watchlistsResponse();
      }
      if (url.includes("/api/watchlists/semiconductor-core/dashboard")) {
        return dashboardResponse();
      }
      if (url.includes("/api/watchlists/semiconductor-core/collection-status")) {
        return collectionStatusResponse();
      }
      return jsonResponse({ status: "ok", price_rows: 1, indicator_rows: 1, news_items: 0, disclosures: 0 });
    });
    vi.stubGlobal("fetch", withSchedulerFallback(fetchMock));

    render(<WatchlistDashboard />);

    await waitForWatchlistControls();
    fireEvent.change(screen.getByLabelText("새 종목 심볼"), { target: { value: "   " } });
    fireEvent.click(screen.getByRole("button", { name: "추가" }));

    await waitFor(() => {
      expect(screen.getByText("종목 코드를 입력해 주세요.")).toBeInTheDocument();
    });
    expect(screen.queryByTestId("symbol-NVDA")).toBeInTheDocument();
    expect(screen.queryByTestId("symbol-005930.KS")).toBeInTheDocument();
  });

  it("shows dashboard fetch error when the backend dashboard payload is invalid", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, _init?: RequestInit): Promise<Response> => {
      const url = String(input);
      if (url.includes("/api/watchlists/semiconductor-core/dashboard")) {
        return jsonResponse({ data: "bad" });
      }
      if (url.includes("/api/watchlists")) {
        return watchlistsResponse();
      }
      return jsonResponse({ status: "ok", price_rows: 1, indicator_rows: 1, news_items: 0, disclosures: 0 });
    });
    vi.stubGlobal("fetch", withSchedulerFallback(fetchMock));

    render(<WatchlistDashboard />);

    await waitFor(() => {
      expect(screen.getByText("대시보드 데이터를 불러오지 못했습니다.")).toBeInTheDocument();
    });
  });

  it("shows an empty watchlist message when /api/watchlists has no items", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, _init?: RequestInit): Promise<Response> => {
      const url = String(input);
      if (url.includes("/api/watchlists")) {
        return watchlistsResponseWithBody([]);
      }
      return jsonResponse({ status: "ok", price_rows: 1, indicator_rows: 1, news_items: 0, disclosures: 0 });
    });
    vi.stubGlobal("fetch", withSchedulerFallback(fetchMock));

    render(<WatchlistDashboard />);

    await waitFor(() => {
      expect(screen.getAllByText("저장된 관심 그룹이 없습니다.")).toHaveLength(1);
    });
    expect(fetchMock.mock.calls.some(([request]) => String(request).includes("/api/watchlists/semiconductor-core/dashboard"))).toBe(false);
  });

  it("keeps watchlist controls disabled until persisted watchlists finish loading", async () => {
    let resolveWatchlists: (response: Response) => void = () => undefined;
    const watchlistsPromise = new Promise<Response>((resolve) => {
      resolveWatchlists = resolve;
    });
    const fetchMock = vi.fn(async (input: RequestInfo | URL, _init?: RequestInit): Promise<Response> => {
      const url = String(input);
      if (url === "/api/watchlists") {
        return watchlistsPromise;
      }
      if (url.includes("/api/watchlists/semiconductor-core/dashboard")) {
        return dashboardResponse();
      }
      return jsonResponse({ status: "ok", price_rows: 1, indicator_rows: 1, news_items: 0, disclosures: 0 });
    });
    vi.stubGlobal("fetch", withSchedulerFallback(fetchMock));

    render(<WatchlistDashboard />);

    expect(screen.getByRole("button", { name: "새 그룹" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "추가" })).toBeDisabled();
    resolveWatchlists(watchlistsResponse());

    await waitForWatchlistControls();
    expect(screen.getByRole("button", { name: "추가" })).not.toBeDisabled();
  });

  it("does not add a symbol locally when POST /api/watchlists/{id}/assets fails", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
      const url = String(input);
      if (url === "/api/watchlists") {
        return watchlistsResponse();
      }
      if (url.includes("/api/watchlists/semiconductor-core/dashboard")) {
        return dashboardResponse();
      }
      if (url.includes("/api/tickers/validate?symbol=AAPL")) {
        return jsonResponse({ symbol: "AAPL", valid: true, provider: "yfinance" });
      }
      if (url === "/api/watchlists/semiconductor-core/assets" && init?.method === "POST") {
        return jsonResponse({ detail: "failed" }, 500);
      }
      return jsonResponse({ status: "ok", price_rows: 1, indicator_rows: 1, news_items: 0, disclosures: 0 });
    });
    vi.stubGlobal("fetch", withSchedulerFallback(fetchMock));

    render(<WatchlistDashboard />);

    await waitForWatchlistControls();
    fireEvent.change(screen.getByLabelText("새 종목 심볼"), { target: { value: "AAPL" } });
    fireEvent.click(screen.getByRole("button", { name: "추가" }));

    await waitFor(() => {
      expect(screen.getByText("종목 추가에 실패했습니다.")).toBeInTheDocument();
    });
    expect(screen.queryByTestId("symbol-AAPL")).not.toBeInTheDocument();
  });

  it("removes a symbol via DELETE /api/watchlists/{id}/assets/{symbol}", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
      const url = String(input);
      if (url === "/api/watchlists") {
        return watchlistsResponse();
      }
      if (url.includes("/api/watchlists/semiconductor-core/dashboard")) {
        return dashboardResponse();
      }
      if (url === "/api/watchlists/semiconductor-core/assets/NVDA" && init?.method === "DELETE") {
        return jsonResponse({ watchlist_id: "semiconductor-core", slug: "semiconductor-core", name: "Semiconductor Core", symbols: ["005930.KS"] });
      }
      return jsonResponse({ status: "ok", price_rows: 1, indicator_rows: 1, news_items: 0, disclosures: 0 });
    });
    vi.stubGlobal("fetch", withSchedulerFallback(fetchMock));

    render(<WatchlistDashboard />);

    await waitForWatchlistControls();
    fireEvent.click(screen.getByRole("button", { name: "NVDA 제거" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/watchlists/semiconductor-core/assets/NVDA",
        expect.objectContaining({ method: "DELETE" }),
      );
    });
    expect(screen.queryByTestId("symbol-NVDA")).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "삼성전자" })).toBeInTheDocument();
  });

  it("sends the local session token on GET, POST, and DELETE watchlist calls", async () => {
    window.__VBINVEST_LOCAL_SESSION_TOKEN__ = "session-token";
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
      const url = String(input);
      if (url === "/api/watchlists" && init?.method === "POST") {
        return jsonResponse({ watchlist_id: "auth-group-id", slug: "auth-group", name: "Auth Group", symbols: [] });
      }
      if (url === "/api/watchlists") {
        return watchlistsResponse();
      }
      if (url.includes("/api/watchlists/semiconductor-core/dashboard")) {
        return dashboardResponse();
      }
      if (url.includes("/api/tickers/validate?symbol=AAPL")) {
        return jsonResponse({ symbol: "AAPL", valid: true, provider: "yfinance" });
      }
      if (url === "/api/watchlists/semiconductor-core/assets" && init?.method === "POST") {
        return jsonResponse({ watchlist_id: "semiconductor-core", slug: "semiconductor-core", name: "Semiconductor Core", symbols: ["NVDA", "005930.KS", "AAPL"] });
      }
      if (url === "/api/watchlists/semiconductor-core/assets/NVDA" && init?.method === "DELETE") {
        return jsonResponse({ watchlist_id: "semiconductor-core", slug: "semiconductor-core", name: "Semiconductor Core", symbols: ["005930.KS"] });
      }
      return jsonResponse({ status: "ok", price_rows: 1, indicator_rows: 1, news_items: 0, disclosures: 0 });
    });
    vi.stubGlobal("fetch", withSchedulerFallback(fetchMock));

    render(<WatchlistDashboard />);

    await waitForWatchlistControls();
    fireEvent.change(screen.getByLabelText("새 그룹 이름"), { target: { value: "Auth Group" } });
    fireEvent.click(screen.getByRole("button", { name: "새 그룹" }));
    fireEvent.click(screen.getByRole("button", { name: "Semiconductor Core" }));
    fireEvent.change(screen.getByLabelText("새 종목 심볼"), { target: { value: "AAPL" } });
    fireEvent.click(screen.getByRole("button", { name: "추가" }));
    fireEvent.click(screen.getByRole("button", { name: "NVDA 제거" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/watchlists/semiconductor-core/assets/NVDA",
        expect.objectContaining({ method: "DELETE" }),
      );
    });
    const calls = fetchMock.mock.calls;
    expect(calls.some(([input, init]) => String(input) === "/api/watchlists" && headerValue(init, "Authorization") === "Bearer session-token")).toBe(true);
    expect(calls.some(([input, init]) => String(input) === "/api/watchlists" && init?.method === "POST" && headerValue(init, "Authorization") === "Bearer session-token")).toBe(true);
    expect(calls.some(([input, init]) => String(input) === "/api/watchlists/semiconductor-core/assets" && init?.method === "POST" && headerValue(init, "Authorization") === "Bearer session-token")).toBe(true);
    expect(calls.some(([input, init]) => String(input) === "/api/watchlists/semiconductor-core/assets/NVDA" && init?.method === "DELETE" && headerValue(init, "Authorization") === "Bearer session-token")).toBe(true);
  });

  it("loads scheduler settings on dashboard load and enables scheduled precompute on toggle", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
      const url = String(input);
      if (url === "/api/scheduler/settings" && init?.method === "PATCH") {
        const body =
          typeof init.body === "string"
            ? init.body
            : init.body instanceof URLSearchParams
              ? init.body.toString()
              : JSON.stringify(init.body);
        expect(body).toBe(JSON.stringify({ weekly_precompute_enabled: true }));
        return jsonResponse({
          daily_refresh_enabled: true,
          weekly_precompute_enabled: true,
          watchlist: "semiconductor-core",
          include_news: true,
        });
      }
      if (url.includes("/api/watchlists/semiconductor-core/dashboard")) {
        return dashboardResponse();
      }
      if (url === "/api/watchlists") {
        return watchlistsResponse();
      }
      return jsonResponse({ status: "ok", price_rows: 1, indicator_rows: 1, news_items: 0, disclosures: 0 });
    });
    vi.stubGlobal("fetch", withSchedulerFallback(fetchMock));

    render(<WatchlistDashboard />);

    const precomputeCheckbox = await screen.findByRole("checkbox", { name: "예약 사전 생성" });
    expect(precomputeCheckbox).not.toBeChecked();

    fireEvent.click(precomputeCheckbox);

    await waitFor(() => {
      expect(precomputeCheckbox).toBeChecked();
    });
    expect(hasFetchCallWithHeaders(fetchMock, "/api/scheduler/settings", "PATCH", { "Content-Type": "application/json" })).toBe(true);
  });

  it("keeps previous scheduled precompute state when PATCH settings fails", async () => {
    window.__VBINVEST_LOCAL_SESSION_TOKEN__ = "task14-session-token";
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
      const url = String(input);
      if (url === "/api/scheduler/settings" && init?.method === "PATCH") {
        return jsonResponse({ detail: "patch failed" }, 500);
      }
      if (url.includes("/api/watchlists/semiconductor-core/dashboard")) {
        return dashboardResponse();
      }
      if (url === "/api/watchlists") {
        return watchlistsResponse();
      }
      return jsonResponse({ status: "ok", price_rows: 1, indicator_rows: 1, news_items: 0, disclosures: 0 });
    });
    vi.stubGlobal("fetch", withSchedulerFallback(fetchMock));

    render(<WatchlistDashboard />);

    const precomputeCheckbox = await screen.findByRole("checkbox", { name: "예약 사전 생성" });
    fireEvent.click(precomputeCheckbox);

    await waitFor(() => {
      expect(precomputeCheckbox).not.toBeChecked();
    });
    expect(
      hasFetchCallWithHeaders(fetchMock, "/api/scheduler/settings", "PATCH", { Authorization: "Bearer task14-session-token" }),
    ).toBe(true);
    expect(screen.getByText("스케줄러 설정 저장 실패")).toBeInTheDocument();
  });

  it("writes watchlist component evidence for manual QA", async () => {
    render(<WatchlistDashboard />);

    await waitForWatchlistControls();
    await mkdir(path.resolve(process.cwd(), "../.omo/ulw-loop/evidence"), { recursive: true });
    await writeFile(
      path.resolve(process.cwd(), "../.omo/ulw-loop/evidence/task12-frontend-component.txt"),
      [
        "loads persisted watchlists from backend and renders them from /api/watchlists",
        "creates a new group via POST /api/watchlists and adds a symbol via POST /api/watchlists/{id}/assets",
        "does not add a symbol locally when POST /api/watchlists/{id}/assets fails",
        "removes a symbol via DELETE /api/watchlists/{id}/assets/{symbol}",
        "sends the local session token on GET, POST, and DELETE watchlist calls",
      ].join("\n"),
    );
  });

  it("refreshes market data when the local program page opens", async () => {
    const fetchMock = vi.fn(async (_input: RequestInfo | URL, _init?: RequestInit): Promise<Response> => {
      if (String(_input).includes("/api/watchlists/semiconductor-core/dashboard")) {
        return dashboardResponse();
      }
      return new Response(JSON.stringify({ status: "ok", price_rows: 1, indicator_rows: 1 }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    });
    vi.stubGlobal("fetch", withSchedulerFallback(fetchMock));

    render(<WatchlistDashboard />);

    expect(screen.getByRole("status")).toHaveTextContent("주식 정보를 확인하는 중");
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/api/startup/market-refresh?no_network=false&include_news=true", { method: "POST" });
    });
    await waitFor(() => {
      expect(screen.queryByText("주식 정보를 확인하는 중")).not.toBeInTheDocument();
    });
  });

  it("shows estimated progress while startup market refresh is still pending", async () => {
    let resolveRefresh: (response: Response) => void = () => undefined;
    const refreshPromise = new Promise<Response>((resolve) => {
      resolveRefresh = resolve;
    });
    const fetchMock = vi.fn(async (input: RequestInfo | URL, _init?: RequestInit): Promise<Response> => {
      const url = String(input);
      if (url.includes("/api/startup/market-refresh")) {
        return refreshPromise;
      }
      if (url.includes("/api/watchlists/semiconductor-core/dashboard")) {
        return dashboardResponse();
      }
      if (url === "/api/watchlists") {
        return watchlistsResponse();
      }
      return jsonResponse({ provider_status: { opendart: { configured: true }, ai: { mode: "local" } } });
    });
    vi.stubGlobal("fetch", withSchedulerFallback(fetchMock));

    render(<WatchlistDashboard />);

    const status = await screen.findByRole("status");
    expect(status).toHaveTextContent("주식 정보를 확인하는 중");
    expect(status).toHaveTextContent("예상 진행률 5%");
    expect(status).toHaveTextContent("경과 0s");
    expect(status).toHaveTextContent("예상 남은 시간 2m 0s");
    expect(status).toHaveTextContent("네트워크와 종목 수에 따라 실제 시간은 달라질 수 있습니다.");

    resolveRefresh(jsonResponse({ status: "ok", price_rows: 1, indicator_rows: 1 }));
    await waitFor(() => {
      expect(screen.queryByText("주식 정보를 확인하는 중")).not.toBeInTheDocument();
    });
  });

  it("shows startup progress counts from backend response on completion", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, _init?: RequestInit): Promise<Response> => {
      const url = String(input);
      if (url.includes("/api/watchlists/semiconductor-core/dashboard")) {
        return dashboardResponse();
      }
      if (url === "/api/watchlists") {
        return watchlistsResponse();
      }
      if (url.includes("/api/startup/market-refresh")) {
        return jsonResponse({
          status: "ok",
          queued: 2,
          running: 0,
          succeeded: 2,
          failed: 1,
          provider_disabled: [{ symbol: "005930.KS", provider: "dart", reason: "missing-api-key" }],
          news_items: 4,
          disclosures: 1,
          ticker_catalog: { status: "ok", count: 3000, source: "kind" },
        });
      }
      return jsonResponse({ provider_status: { opendart: { configured: true }, ai: { mode: "local" } } });
    });
    vi.stubGlobal("fetch", withSchedulerFallback(fetchMock));

    render(<WatchlistDashboard />);

    await waitFor(() => {
      expect(screen.getByTestId("startup-status")).toHaveTextContent("대기 2");
    });
    expect(screen.getByTestId("startup-status")).toHaveTextContent("진행 0");
    expect(screen.getByTestId("startup-status")).toHaveTextContent("성공 2");
    expect(screen.getByTestId("startup-status")).toHaveTextContent("실패 1");
    expect(screen.getByTestId("startup-status")).toHaveTextContent("종목목록 3000");
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("writes startup count component evidence for manual QA", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, _init?: RequestInit): Promise<Response> => {
      const url = String(input);
      if (url.includes("/api/watchlists/semiconductor-core/dashboard")) {
        return dashboardResponse();
      }
      if (url.includes("/api/startup/market-refresh")) {
        return jsonResponse({
          status: "ok",
          queued: 2,
          running: 0,
          succeeded: 2,
          failed: 1,
          provider_disabled: [{ symbol: "005930.KS", provider: "dart", reason: "missing-api-key" }],
          news_items: 4,
          disclosures: 1,
        });
      }
      return jsonResponse({ provider_status: { opendart: { configured: true }, ai: { mode: "local" } } });
    });
    vi.stubGlobal("fetch", withSchedulerFallback(fetchMock));

    render(<WatchlistDashboard />);

    await waitFor(() => {
      expect(screen.getByTestId("startup-status")).toHaveTextContent("성공 2");
    });
    const statusText = screen.getByTestId("startup-status").textContent ?? "";
    await mkdir(path.resolve(process.cwd(), "../.omo/ulw-loop/evidence"), { recursive: true });
    await writeFile(path.resolve(process.cwd(), "../.omo/ulw-loop/evidence/task11-frontend-component.txt"), statusText);
  });

  it("handles malformed startup payload as a startup failure", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, _init?: RequestInit): Promise<Response> => {
      const url = String(input);
      if (url.includes("/api/watchlists/semiconductor-core/dashboard")) {
        return dashboardResponse();
      }
      if (url === "/api/watchlists") {
        return watchlistsResponse();
      }
      if (url.includes("/api/startup/market-refresh")) {
        return new Response("not-json", { status: 200 });
      }
      return jsonResponse({ provider_status: { opendart: { configured: true }, ai: { mode: "local" } } });
    });
    vi.stubGlobal("fetch", withSchedulerFallback(fetchMock));

    render(<WatchlistDashboard />);

    await waitFor(() => {
      const statusBanners = screen.getAllByRole("status");
      expect(statusBanners).toHaveLength(1);
      expect(statusBanners[0]).toHaveTextContent("시장 데이터 갱신 실패");
    });
  });

  it("shows stale skipped status without treating it as a hard failure", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, _init?: RequestInit): Promise<Response> => {
      const url = String(input);
      if (url.includes("/api/watchlists/semiconductor-core/dashboard")) {
        return dashboardResponse();
      }
      if (url === "/api/watchlists") {
        return watchlistsResponse();
      }
      if (url.includes("/api/startup/market-refresh")) {
        return jsonResponse({
          status: "skipped",
          price_rows: 1,
          indicator_rows: 1,
          news_items: 0,
          disclosures: 0,
        });
      }
      return jsonResponse({ provider_status: { opendart: { configured: true }, ai: { mode: "local" } } });
    });
    vi.stubGlobal("fetch", withSchedulerFallback(fetchMock));

    render(<WatchlistDashboard />);

    await waitFor(() => {
      expect(screen.getByTestId("startup-status")).toHaveTextContent("최근 갱신 사용");
    });
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("keeps the startup modal while a running status is reported", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, _init?: RequestInit): Promise<Response> => {
      const url = String(input);
      if (url.includes("/api/settings")) {
        return jsonResponse({ provider_status: { opendart: { configured: true }, ai: { mode: "local" } } });
      }
      if (url.includes("/api/watchlists/semiconductor-core/dashboard")) {
        return dashboardResponse();
      }
      if (url.includes("/api/startup/market-refresh")) {
        return jsonResponse({
          status: "running",
          queued: 1,
          running: 3,
          succeeded: 0,
          failed: 0,
          provider_disabled: [],
          news_items: 0,
          disclosures: 0,
        });
      }
      return jsonResponse({ status: "ok", price_rows: 1, indicator_rows: 1, news_items: 0, disclosures: 0 });
    });
    vi.stubGlobal("fetch", withSchedulerFallback(fetchMock));

    render(<WatchlistDashboard />);

    await waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent("주식 정보를 확인하는 중");
    });
    expect(screen.queryByTestId("startup-status")).not.toBeInTheDocument();
  });

  it("derives startup counts from legacy fields when queued/running/succeeded/failed are absent", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, _init?: RequestInit): Promise<Response> => {
      const url = String(input);
      if (url.includes("/api/settings")) {
        return jsonResponse({ provider_status: { opendart: { configured: true }, ai: { mode: "local" } } });
      }
      if (url.includes("/api/watchlists/semiconductor-core/dashboard")) {
        return dashboardResponse();
      }
      if (url.includes("/api/startup/market-refresh")) {
        return jsonResponse({
          status: "partial",
          price_rows: 2,
          indicator_rows: 2,
          news_items: 4,
          disclosures: 1,
          provider_disabled: [{ symbol: "005930.KS", provider: "dart", reason: "missing-api-key" }],
          failures: ["x"],
        });
      }
      return jsonResponse({ status: "ok", price_rows: 1, indicator_rows: 1, news_items: 0, disclosures: 0 });
    });
    vi.stubGlobal("fetch", withSchedulerFallback(fetchMock));

    render(<WatchlistDashboard />);

    await waitFor(() => {
      expect(screen.getByTestId("startup-status")).toHaveTextContent("가격 2 · 지표 2");
    });
    expect(screen.getByTestId("startup-status")).toHaveTextContent("대기 0");
    expect(screen.getByTestId("startup-status")).toHaveTextContent("진행 0");
    expect(screen.getByTestId("startup-status")).toHaveTextContent("실패 2");
    expect(screen.getByTestId("startup-status")).toHaveTextContent("성공 0");
  });

  it("uses same-origin API routes when the static frontend is served by FastAPI", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, _init?: RequestInit): Promise<Response> => {
      const url = String(input);
      if (url.includes("/api/watchlists/semiconductor-core/dashboard")) {
        return dashboardResponse();
      }
      if (url === "/api/watchlists") {
        return watchlistsResponse();
      }
      return jsonResponse({ status: "ok", price_rows: 1, indicator_rows: 1, news_items: 0, disclosures: 0 });
    });
    vi.stubGlobal("fetch", withSchedulerFallback(fetchMock));

    render(<WatchlistDashboard />);

    await waitFor(() => {
      expect(hasFetchCall(fetchMock, "/api/settings")).toBe(true);
    });
    expect(hasFetchCallWithMethod(fetchMock, "/api/startup/market-refresh?no_network=false&include_news=true", "POST")).toBe(true);
    expect(hasFetchCall(fetchMock, "/api/watchlists/semiconductor-core/dashboard?days=1260")).toBe(true);
    expect(fetchMock.mock.calls.map(([input]) => String(input))).not.toContain("/api/backend/settings");
  });

  it("renders price, indicators, and chart data from the backend dashboard payload", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, _init?: RequestInit): Promise<Response> => {
      const url = String(input);
      if (url.includes("/api/settings")) {
        return jsonResponse({ provider_status: { opendart: { configured: true }, ai: { mode: "local" } } });
      }
      if (url === "/api/watchlists") {
        return watchlistsResponse();
      }
      if (url.includes("/api/watchlists/semiconductor-core/dashboard")) {
        return dashboardResponse();
      }
      return jsonResponse({ status: "ok", price_rows: 2, indicator_rows: 2, news_items: 0, disclosures: 0 });
    });
    vi.stubGlobal("fetch", withSchedulerFallback(fetchMock));

    render(<WatchlistDashboard />);

    await waitFor(() => {
      expect(hasFetchCall(fetchMock, "/api/watchlists/semiconductor-core/dashboard?days=1260")).toBe(true);
    });
    expect(screen.getByText("999.12")).toBeInTheDocument();
    expect(screen.getByText("+3.88%")).toBeInTheDocument();
    expect(screen.getByText("+12.50%")).toBeInTheDocument();
    expect(screen.getByText("64.2")).toBeInTheDocument();
    expect(screen.getByText("990.1 / 970.2 / 950.3 / 930.4")).toBeInTheDocument();
    expect(screen.queryByText("예시 값")).not.toBeInTheDocument();
  });

  it("shows whether stored market rows came from real providers or synthetic fixtures", async () => {
    render(<WatchlistDashboard />);

    await waitFor(() => {
      expect(screen.getByTestId("collection-status")).toHaveTextContent("NVDA");
    });
    expect(screen.getByTestId("collection-status")).toHaveTextContent("실제 수집");
    expect(screen.getByTestId("collection-status")).toHaveTextContent("예시 데이터 포함");
    expect(screen.getByTestId("collection-status")).toHaveTextContent("최신 2026-06-01");
    expect(screen.getByTestId("collection-status")).toHaveTextContent("가격 260 / 지표 260");
  });

  it("does not run startup market refresh before first-run setup is completed", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, _init?: RequestInit): Promise<Response> => {
      const url = String(input);
      if (url.includes("/api/settings")) {
        return jsonResponse({
          first_run_completed: false,
          provider_status: { opendart: { configured: false }, ai: { mode: "disabled" } },
        });
      }
      if (url.includes("/api/watchlists/semiconductor-core/dashboard")) {
        return dashboardResponse();
      }
      return jsonResponse({ status: "ok", price_rows: 1, indicator_rows: 1, news_items: 0, disclosures: 0 });
    });
    vi.stubGlobal("fetch", withSchedulerFallback(fetchMock));

    render(<WatchlistDashboard />);

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "초기 설정" })).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: "설정 완료" })).toBeDisabled();
    expect(screen.getByText(/OpenDART 공시를 받으려면/)).toBeInTheDocument();
    expect(screen.getByText(/사용량과 제한은 사용자 키 책임/)).toBeInTheDocument();
    expect(fetchMock.mock.calls.map(([input]) => String(input))).not.toContain(
      "/api/startup/market-refresh?no_network=false&include_news=true",
    );
    expect(fetchMock.mock.calls.map(([input]) => String(input))).not.toContain(
      "/api/watchlists/semiconductor-core/dashboard?days=1260",
    );
    expect(screen.queryByText("시장 데이터 갱신 실패")).not.toBeInTheDocument();
  });

  it("switches first-run setup language locally and stores it in the setup payload", async () => {
    const selectedLanguages: Language[] = [];
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
      const url = String(input);
      if (url === "/api/settings/first-run" && init?.method === "POST") {
        return jsonResponse({
          first_run_completed: true,
          provider_status: { opendart: { configured: false }, ai: { mode: "disabled" } },
        });
      }
      return jsonResponse({ status: "ok", price_rows: 1, indicator_rows: 1, news_items: 0, disclosures: 0 });
    });
    vi.stubGlobal("fetch", withSchedulerFallback(fetchMock));

    render(
      <SetupWizard
        onCompleted={() => undefined}
        language="ko"
        labels={labelFor("ko").setup}
        onLanguageChange={(nextLanguage) => selectedLanguages.push(nextLanguage)}
      />,
    );

    const languageSelect = await screen.findByRole("combobox", { name: "언어" });
    fireEvent.change(languageSelect, { target: { value: "en" } });

    await waitFor(() => {
      expect(languageSelect).toHaveValue("en");
    });
    expect(selectedLanguages).toEqual(["en"]);
    expect(fetchMock.mock.calls.some(([input]) => String(input) === "/api/settings/language")).toBe(false);
    expect(window.localStorage.getItem("vbinvest_language")).toBe("en");

    fireEvent.change(screen.getByLabelText("Obsidian Vault Path"), { target: { value: "/tmp/vault" } });
    fireEvent.click(screen.getByRole("button", { name: "Finish setup" }));

    await waitFor(() => {
      expect(hasFetchCallWithMethod(fetchMock, "/api/settings/first-run", "POST")).toBe(true);
    });
    const setupCall = fetchMock.mock.calls.find(([input, init]) => String(input) === "/api/settings/first-run" && init?.method === "POST");
    expect(setupCall).toBeDefined();
    expect(JSON.parse(String(setupCall?.[1]?.body))).toEqual(
      expect.objectContaining({
        language: "en",
        obsidian: expect.objectContaining({ vault_path: "/tmp/vault" }),
      }),
    );
  });

  it("shows a first-run setup error when the selected Obsidian vault is invalid", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
      const url = String(input);
      if (url.includes("/api/settings") && init?.method !== "POST") {
        return jsonResponse({
          first_run_completed: false,
          provider_status: { opendart: { configured: false }, ai: { mode: "disabled" } },
        });
      }
      if (url.includes("/api/settings/first-run")) {
        return jsonResponse({ detail: "obsidian.vault_path: does not exist" }, 400);
      }
      return jsonResponse({ status: "ok", price_rows: 1, indicator_rows: 1, news_items: 0, disclosures: 0 });
    });
    vi.stubGlobal("fetch", withSchedulerFallback(fetchMock));

    render(<WatchlistDashboard />);

    fireEvent.change(await screen.findByLabelText("Obsidian Vault Path"), { target: { value: "/missing-vault" } });
    fireEvent.click(screen.getByRole("button", { name: "설정 완료" }));

    expect(await screen.findByText("obsidian.vault_path: does not exist")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/settings/first-run",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("shows AI API and local LLM settings when AI API integration is selected", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
      const url = String(input);
      if (url.includes("/api/settings") && init?.method !== "POST") {
        return jsonResponse({
          first_run_completed: false,
          provider_status: { opendart: { configured: false }, ai: { mode: "disabled" } },
        });
      }
      return jsonResponse({ status: "ok", price_rows: 1, indicator_rows: 1, news_items: 0, disclosures: 0 });
    });
    vi.stubGlobal("fetch", withSchedulerFallback(fetchMock));

    render(<WatchlistDashboard />);

    fireEvent.change(await screen.findByLabelText("AI Mode"), { target: { value: "openai_compatible" } });

    expect(screen.getByLabelText("AI API Type")).toBeInTheDocument();
    expect(screen.getByLabelText("Cloud Model Provider")).toBeInTheDocument();
    expect(screen.getByLabelText("AI Base URL")).toBeInTheDocument();
    expect(screen.getByLabelText("AI Model")).toBeInTheDocument();
    expect(screen.getByLabelText("Context Size")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("AI API Type"), { target: { value: "local" } });

    expect(screen.getByText(/Ollama/)).toBeInTheDocument();
  });

  it("opens runtime settings from the dashboard and saves a local AI model change", async () => {
    window.__VBINVEST_LOCAL_SESSION_TOKEN__ = "settings-session-token";
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
      const url = String(input);
      if (url === "/api/settings" && init?.method === undefined) {
        return jsonResponse({
          first_run_completed: true,
          language: "ko",
          database: {
            mode: "sqlite",
            sqlite_path: "/Users/solaris/Library/Application Support/VBinvest/vbinvest.sqlite3",
            postgres_url: "",
          },
          obsidian: {
            vault_path: "/Volumes/nv6000t/ObsidianVault/옵시디언",
            export_mode: "direct",
          },
          providers: {
            opendart_api_key: "",
            ai_provider_name: "custom",
            ai_base_url: "http://127.0.0.1:11434/v1",
            ai_model: "qwen3.5:2b",
            ai_context_size: 4096,
            ai_api_key: "",
          },
          provider_status: { opendart: { configured: false }, ai: { mode: "local" } },
        });
      }
      if (url === "/api/settings/first-run" && init?.method === "POST") {
        return jsonResponse({
          first_run_completed: true,
          language: "ko",
          provider_status: { opendart: { configured: false }, ai: { mode: "local" } },
        });
      }
      if (url.includes("/api/watchlists/semiconductor-core/dashboard")) {
        return dashboardResponse();
      }
      if (url.includes("/api/watchlists/semiconductor-core/collection-status")) {
        return collectionStatusResponse();
      }
      if (url === "/api/watchlists") {
        return watchlistsResponse();
      }
      return jsonResponse({ status: "ok", price_rows: 1, indicator_rows: 1, news_items: 0, disclosures: 0 });
    });
    vi.stubGlobal("fetch", withSchedulerFallback(fetchMock));

    render(<WatchlistDashboard />);

    fireEvent.click(await screen.findByRole("button", { name: "설정" }));

    expect(await screen.findByRole("dialog", { name: "설정" })).toBeInTheDocument();
    expect(screen.getByLabelText("AI Model")).toHaveValue("qwen3.5:2b");
    fireEvent.change(screen.getByLabelText("AI Model"), { target: { value: "gemma4:e4b-it-q4_K_M" } });
    fireEvent.click(screen.getByRole("button", { name: "설정 저장" }));

    await waitFor(() => {
      expect(hasFetchCallWithMethod(fetchMock, "/api/settings/first-run", "POST")).toBe(true);
    });
    const saveCall = fetchMock.mock.calls.find(([input, init]) => String(input) === "/api/settings/first-run" && init?.method === "POST");
    expect(saveCall).toBeDefined();
    expect(headerValue(saveCall?.[1], "Authorization")).toBe("Bearer settings-session-token");
    expect(JSON.parse(String(saveCall?.[1]?.body))).toMatchObject({
      data_directory: "/Users/solaris/Library/Application Support/VBinvest",
      obsidian: { vault_path: "/Volumes/nv6000t/ObsidianVault/옵시디언" },
      providers: {
        ai_mode: "openai_compatible",
        ai_provider_name: "custom",
        ai_base_url: "http://127.0.0.1:11434/v1",
        ai_model: "gemma4:e4b-it-q4_K_M",
        ai_context_size: 4096,
      },
    });
    await waitFor(() => {
      expect(screen.queryByRole("dialog", { name: "설정" })).not.toBeInTheDocument();
    });
  });

  it("shows provider-disabled partial refresh without treating it as a total failure", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, _init?: RequestInit): Promise<Response> => {
        const url = String(input);
        if (url.includes("/api/settings")) {
          return jsonResponse({
            provider_status: {
              opendart: { configured: false, source: "none" },
              ai: { mode: "local", provider: "ollama", key_required: false, key_configured: false, base_url: "http://127.0.0.1:11434/v1", model: "qwen2.5", error: null },
            },
          });
        }
        return jsonResponse({
          status: "partial",
          price_rows: 2,
          indicator_rows: 2,
          news_items: 4,
          disclosures: 1,
          provider_disabled: [{ symbol: "005930.KS", provider: "dart", reason: "missing-api-key" }],
        });
      }),
    );

    render(<WatchlistDashboard />);

    await waitFor(() => {
      expect(screen.getByText("일부 소스 비활성화")).toBeInTheDocument();
    });
    expect(screen.getByText("뉴스 4 · 공시 1")).toBeInTheDocument();
    expect(screen.getByText("OpenDART 미설정 · AI local")).toBeInTheDocument();
    expect(screen.queryByText("시장 데이터 갱신 실패")).not.toBeInTheDocument();
  });

  it("renders safe provider status without raw key-like strings", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, _init?: RequestInit): Promise<Response> => {
        const url = String(input);
        if (url.includes("/api/settings")) {
          return jsonResponse({
            providers: { ai_api_key: "raw-ai-token-fixture", opendart_api_key: "raw-dart-token-fixture" },
            provider_status: {
              opendart: { configured: true, source: "secure-storage" },
              ai: { mode: "cloud", provider: "openai", key_required: true, key_configured: true, base_url: "https://api.openai.com/v1", model: "gpt-test", error: null },
            },
          });
        }
        return jsonResponse({ status: "ok", price_rows: 1, indicator_rows: 1, news_items: 0, disclosures: 0 });
      }),
    );

    render(<WatchlistDashboard />);

    await waitFor(() => {
      expect(screen.getByText("OpenDART 설정됨 · AI cloud")).toBeInTheDocument();
    });
    expect(screen.queryByText(/raw-ai-token-fixture|raw-dart-token-fixture|<redacted>/)).not.toBeInTheDocument();
  });

  it("calls the on-demand research generation endpoint for the selected symbol", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, _init?: RequestInit): Promise<Response> => {
      const url = String(input);
      if (url.includes("/api/settings")) {
        return jsonResponse({ provider_status: { opendart: { configured: true }, ai: { mode: "local" } } });
      }
      if (url === "/api/watchlists") {
        return watchlistsResponse();
      }
      if (url.includes("/api/watchlists/semiconductor-core/dashboard")) {
        return dashboardResponse();
      }
      if (url.includes("/api/research/NVDA/generate")) {
        return jsonResponse({
          target_slug: "NVDA",
          opinion: "아웃퍼폼",
          thesis: "DB 가격 지표와 공개 소스를 바탕으로 모멘텀을 점검했습니다.",
          sources: [{ kind: "db_price_indicator" }],
        }, 201);
      }
      return jsonResponse({ status: "ok", price_rows: 1, indicator_rows: 1, news_items: 0, disclosures: 0 });
    });
    vi.stubGlobal("fetch", withSchedulerFallback(fetchMock));

    render(<WatchlistDashboard />);

    fireEvent.click(await screen.findByRole("button", { name: "리포트 발행" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/research/NVDA/generate",
        expect.objectContaining({ method: "POST" }),
      );
    });
  });

  it("shows a safe setup message when report generation returns AI provider misconfiguration", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, _init?: RequestInit): Promise<Response> => {
        const url = String(input);
        if (url.includes("/api/settings")) {
          return jsonResponse({ provider_status: { opendart: { configured: true }, ai: { mode: "misconfigured" } } });
        }
        if (url === "/api/watchlists") {
          return watchlistsResponse();
        }
        if (url.includes("/api/watchlists/semiconductor-core/dashboard")) {
          return dashboardResponse();
        }
        if (url.includes("/api/research/NVDA/generate")) {
          return jsonResponse({ detail: "AI provider API key is required for non-local providers" }, 503);
        }
        return jsonResponse({ status: "ok", price_rows: 1, indicator_rows: 1, news_items: 0, disclosures: 0 });
      }),
    );

    render(<WatchlistDashboard />);

    fireEvent.click(await screen.findByRole("button", { name: "리포트 발행" }));

    await waitFor(() => {
      expect(screen.getByText("AI API 설정이 필요합니다. 설정에서 provider 키 또는 로컬 모델을 확인해주세요.")).toBeInTheDocument();
    });
    expect(screen.queryByText("AI provider API key is required for non-local providers")).not.toBeInTheDocument();
  });

  it("shows a local model guidance message when report generation returns reasoning-only output", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, _init?: RequestInit): Promise<Response> => {
        const url = String(input);
        if (url.includes("/api/settings")) {
          return jsonResponse({ provider_status: { opendart: { configured: true }, ai: { mode: "local" } } });
        }
        if (url === "/api/watchlists") {
          return watchlistsResponse();
        }
        if (url.includes("/api/watchlists/semiconductor-core/dashboard")) {
          return dashboardResponse();
        }
        if (url.includes("/api/research/NVDA/generate")) {
          return jsonResponse(
            {
              detail:
                "AI provider returned reasoning-only output without JSON content. Choose a non-reasoning local model or disable thinking mode.",
            },
            503,
          );
        }
        return jsonResponse({ status: "ok", price_rows: 1, indicator_rows: 1, news_items: 0, disclosures: 0 });
      }),
    );

    render(<WatchlistDashboard />);

    fireEvent.click(await screen.findByRole("button", { name: "리포트 발행" }));

    await waitFor(() => {
      expect(
        screen.getByText("로컬 AI가 JSON 리포트를 생성하지 못했습니다. Ollama 설정에서 non-reasoning/instruct 모델을 선택하거나 다른 모델로 바꿔주세요."),
      ).toBeInTheDocument();
    });
    expect(screen.queryByText(/reasoning-only output without JSON content/)).not.toBeInTheDocument();
  });

  it("renders generated opinion, thesis, and source count after report generation succeeds", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, _init?: RequestInit): Promise<Response> => {
        const url = String(input);
        if (url.includes("/api/settings")) {
          return jsonResponse({ provider_status: { opendart: { configured: true }, ai: { mode: "local" } } });
        }
        if (url === "/api/watchlists") {
          return watchlistsResponse();
        }
        if (url.includes("/api/watchlists/semiconductor-core/dashboard")) {
          return dashboardResponse();
        }
        if (url.includes("/api/research/NVDA/generate")) {
          return jsonResponse({
            target_slug: "NVDA",
            opinion: "매수",
            thesis: "<script>alert('x')</script>DB 소스 기반으로 수요 개선 가능성을 점검했습니다.",
            sources: [{ kind: "news" }, { kind: "disclosure" }],
          }, 201);
        }
        return jsonResponse({ status: "ok", price_rows: 1, indicator_rows: 1, news_items: 0, disclosures: 0 });
      }),
    );

    render(<WatchlistDashboard />);

    fireEvent.click(await screen.findByRole("button", { name: "리포트 발행" }));

    await waitFor(() => {
      expect(screen.getByText("투자의견 매수")).toBeInTheDocument();
    });
    expect(screen.getByText("<script>alert('x')</script>DB 소스 기반으로 수요 개선 가능성을 점검했습니다.")).toBeInTheDocument();
    expect(screen.getByText("근거 2개")).toBeInTheDocument();
    expect(document.querySelector("script")).toBeNull();
  });

  it("shows a blocking generation modal with cancellation option while generating", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, _init?: RequestInit): Promise<Response> => {
      const url = String(input);
      const init = _init;
      if (url.includes("/api/settings")) {
        return jsonResponse({ provider_status: { opendart: { configured: true }, ai: { mode: "local" } } });
      }
      if (url === "/api/watchlists") {
        return watchlistsResponse();
      }
      if (url.includes("/api/watchlists/semiconductor-core/dashboard")) {
        return dashboardResponse();
      }
      if (url.includes("/api/research/NVDA/generate")) {
        if (init?.method === "DELETE") {
          return jsonResponse({ run_id: "cancel-run", status: "canceled", error_message: "canceled by user" });
        }
        return new Promise<Response>((_, reject) => {
          const signal = init?.signal;
          if (signal instanceof AbortSignal) {
            signal.addEventListener(
              "abort",
              () => reject(new DOMException("request aborted", "AbortError")),
              { once: true },
            );
          }
        });
      }
      return jsonResponse({ status: "ok", price_rows: 1, indicator_rows: 1, news_items: 0, disclosures: 0 });
    });
    vi.stubGlobal("fetch", withSchedulerFallback(fetchMock));

    render(<WatchlistDashboard />);

    fireEvent.click(await screen.findByRole("button", { name: "리포트 발행" }));
    const generationDialog = await screen.findByRole("dialog", { name: "리포트 발행 중" });
    expect(generationDialog).toBeInTheDocument();
    expect(within(generationDialog).getByText("실시간 분석 중")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "취소" })).toBeInTheDocument();

    fireEvent.click(screen.getByTestId("report-generation-backdrop"));
    expect(screen.getByRole("dialog", { name: "리포트 발행 중" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "취소" }));
    expect(screen.getByText("취소됨")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.queryByRole("dialog", { name: "리포트 발행 중" })).not.toBeInTheDocument();
    });
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/research/NVDA/generate",
      expect.objectContaining({ method: "POST", signal: expect.any(AbortSignal) }),
    );
  });

  it("shows report links and paths when API includes report_path, obsidian_path, or report_url", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, _init?: RequestInit): Promise<Response> => {
        const url = String(input);
        if (url.includes("/api/settings")) {
          return jsonResponse({ provider_status: { opendart: { configured: true }, ai: { mode: "local" } } });
        }
        if (url === "/api/watchlists") {
          return watchlistsResponse();
        }
        if (url.includes("/api/watchlists/semiconductor-core/dashboard")) {
          return dashboardResponse();
        }
        if (url.includes("/api/research/NVDA/generate")) {
          return jsonResponse({
            target_slug: "NVDA",
            opinion: "중립",
            thesis: "경로 정보가 포함된 리포트입니다.",
            sources: [{ kind: "news" }],
            report_url: "https://report.local/semiconductor/nvda.html",
            report_path: "/output/VBinvest/reports/semiconductor/nvda.html",
            obsidian_path: "/vault/Research/semiconductor/NVDA.md",
          }, 201);
        }
        return jsonResponse({ status: "ok", price_rows: 1, indicator_rows: 1, news_items: 0, disclosures: 0 });
      }),
    );

    render(<WatchlistDashboard />);

    fireEvent.click(await screen.findByRole("button", { name: "리포트 발행" }));

    await waitFor(() => {
      expect(screen.getByRole("link", { name: "리포트 링크 보기" })).toHaveAttribute("href", "https://report.local/semiconductor/nvda.html");
    });
    expect(screen.getByText((content) => content.includes("/output/VBinvest/reports/semiconductor/nvda.html"))).toBeInTheDocument();
    expect(screen.getByText((content) => content.includes("/vault/Research/semiconductor/NVDA.md"))).toBeInTheDocument();
  });

  it("preserves the previous report when a later report generation fails", async () => {
    let generateCall = 0;
    const fetchMock = vi.fn(async (input: RequestInfo | URL, _init?: RequestInit): Promise<Response> => {
      const url = String(input);
      if (url.includes("/api/settings")) {
        return jsonResponse({ provider_status: { opendart: { configured: true }, ai: { mode: "local" } } });
      }
      if (url === "/api/watchlists") {
        return watchlistsResponse();
      }
      if (url.includes("/api/watchlists/semiconductor-core/dashboard")) {
        return dashboardResponse();
      }
      if (url.includes("/api/research/NVDA/generate")) {
        generateCall += 1;
        if (generateCall === 1) {
          return jsonResponse({
            target_slug: "NVDA",
            opinion: "매수",
            thesis: "첫 번째 리포트 본문입니다.",
            sources: [{ kind: "news" }, { kind: "news" }],
          }, 201);
        }
        return jsonResponse({ detail: "unexpected error from backend" }, 500);
      }
      return jsonResponse({ status: "ok", price_rows: 1, indicator_rows: 1, news_items: 0, disclosures: 0 });
    });
    vi.stubGlobal("fetch", withSchedulerFallback(fetchMock));

    render(<WatchlistDashboard />);

    fireEvent.click(await screen.findByRole("button", { name: "리포트 발행" }));
    await waitFor(() => {
      expect(screen.getByText("첫 번째 리포트 본문입니다.")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "리포트 발행" }));
    await waitFor(() => {
      expect(screen.getByText("리포트 발행에 실패했습니다. 설정과 백엔드 연결을 확인해주세요.")).toBeInTheDocument();
    });

    expect(screen.getByText("첫 번째 리포트 본문입니다.")).toBeInTheDocument();
  });

  it("includes the local session token in Authorization header for report generation", async () => {
    window.__VBINVEST_LOCAL_SESSION_TOKEN__ = "test-task13-token";
    const fetchMock = vi.fn(async (input: RequestInfo | URL, _init?: RequestInit): Promise<Response> => {
      const url = String(input);
      if (url.includes("/api/settings")) {
        return jsonResponse({ provider_status: { opendart: { configured: true }, ai: { mode: "local" } } });
      }
      if (url === "/api/watchlists") {
        return watchlistsResponse();
      }
      if (url.includes("/api/watchlists/semiconductor-core/dashboard")) {
        return dashboardResponse();
      }
      if (url.includes("/api/research/NVDA/generate")) {
        return jsonResponse({
          target_slug: "NVDA",
          opinion: "중립",
          thesis: "토큰 인증 요청 체크",
          sources: [],
        }, 201);
      }
      return jsonResponse({ status: "ok", price_rows: 1, indicator_rows: 1, news_items: 0, disclosures: 0 });
    });
    vi.stubGlobal("fetch", withSchedulerFallback(fetchMock));

    render(<WatchlistDashboard />);

    fireEvent.click(await screen.findByRole("button", { name: "리포트 발행" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/research/NVDA/generate",
        expect.objectContaining({
          method: "POST",
          headers: expect.objectContaining({
            Authorization: "Bearer test-task13-token",
          }),
        }),
      );
    });
  });

  it("shows a safe error message when the report payload is malformed", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, _init?: RequestInit): Promise<Response> => {
        const url = String(input);
        if (url.includes("/api/settings")) {
          return jsonResponse({ provider_status: { opendart: { configured: true }, ai: { mode: "local" } } });
        }
        if (url === "/api/watchlists") {
          return watchlistsResponse();
        }
        if (url.includes("/api/watchlists/semiconductor-core/dashboard")) {
          return dashboardResponse();
        }
        if (url.includes("/api/research/NVDA/generate")) {
          return jsonResponse({ wrong: "shape" }, 201);
        }
        return jsonResponse({ status: "ok", price_rows: 1, indicator_rows: 1, news_items: 0, disclosures: 0 });
      }),
    );

    render(<WatchlistDashboard />);

    fireEvent.click(await screen.findByRole("button", { name: "리포트 발행" }));

    await waitFor(() => {
      expect(screen.getByText("리포트 응답 형식이 올바르지 않습니다. 백엔드 상태를 확인해주세요.")).toBeInTheDocument();
    });
  });

  it("keeps the report button disabled while generation is in flight", async () => {
    let resolveGenerate: (response: Response) => void = () => undefined;
    const generatePromise = new Promise<Response>((resolve) => {
      resolveGenerate = resolve;
    });
    const fetchMock = vi.fn(async (input: RequestInfo | URL, _init?: RequestInit): Promise<Response> => {
      const url = String(input);
      if (url.includes("/api/settings")) {
        return jsonResponse({ provider_status: { opendart: { configured: true }, ai: { mode: "local" } } });
      }
      if (url === "/api/watchlists") {
        return watchlistsResponse();
      }
      if (url.includes("/api/watchlists/semiconductor-core/dashboard")) {
        return dashboardResponse();
      }
      if (url.includes("/api/research/NVDA/generate")) {
        return generatePromise;
      }
      return jsonResponse({ status: "ok", price_rows: 1, indicator_rows: 1, news_items: 0, disclosures: 0 });
    });
    vi.stubGlobal("fetch", withSchedulerFallback(fetchMock));

    render(<WatchlistDashboard />);

    await waitFor(() => {
      expect(screen.getByText("999.12")).toBeInTheDocument();
    });
    fireEvent.click(await screen.findByRole("button", { name: "리포트 발행" }));
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "실시간 분석 중" })).toBeDisabled();
    });
    fireEvent.click(screen.getByRole("button", { name: "실시간 분석 중" }));
    resolveGenerate(jsonResponse({ target_slug: "NVDA", opinion: "중립", thesis: "완료", sources: [] }, 201));

    await waitFor(() => {
      expect(screen.getByText("리포트 발행 완료")).toBeInTheDocument();
    });
    expect(fetchMock.mock.calls.filter(([input]) => String(input).includes("/api/research/NVDA/generate"))).toHaveLength(1);
  });

  it("generates a report for the currently selected symbol after switching rows", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, _init?: RequestInit): Promise<Response> => {
      const url = String(input);
      if (url.includes("/api/settings")) {
        return jsonResponse({ provider_status: { opendart: { configured: true }, ai: { mode: "local" } } });
      }
      if (url === "/api/watchlists") {
        return watchlistsResponse();
      }
      if (url.includes("/api/watchlists/semiconductor-core/dashboard")) {
        return dashboardResponse();
      }
      if (url.includes("/api/research/005930.KS/generate")) {
        return jsonResponse({ target_slug: "005930.KS", opinion: "중립", thesis: "삼성전자 리포트", sources: [] }, 201);
      }
      return jsonResponse({ status: "ok", price_rows: 1, indicator_rows: 1, news_items: 0, disclosures: 0 });
    });
    vi.stubGlobal("fetch", withSchedulerFallback(fetchMock));

    render(<WatchlistDashboard />);

    fireEvent.click(await screen.findByTestId("symbol-005930.KS"));
    fireEvent.click(screen.getByRole("button", { name: "리포트 발행" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/research/005930.KS/generate",
        expect.objectContaining({ method: "POST" }),
      );
    });
    expect(screen.queryByText("DB 가격 지표와 공개 소스를 바탕으로 모멘텀을 점검했습니다.")).not.toBeInTheDocument();
  });
});

function createTestStorage(initial: Record<string, string> = {}): TestStorage {
  const values = new Map(Object.entries(initial));
  return {
    getItem: (key: string) => values.get(key) ?? null,
    setItem: (key: string, value: string) => {
      values.set(key, value);
    },
    removeItem: (key: string) => {
      values.delete(key);
    },
    clear: () => {
      values.clear();
    },
  };
}
