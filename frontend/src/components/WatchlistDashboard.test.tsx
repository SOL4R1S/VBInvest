import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { APPROVED_OPINIONS } from "@/lib/research";
import { WatchlistDashboard } from "@/components/WatchlistDashboard";

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

describe("WatchlistDashboard", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, _init?: RequestInit): Promise<Response> => {
        if (String(input).includes("/api/watchlists/semiconductor-core/dashboard")) {
          return dashboardResponse();
        }
        if (String(input).includes("/api/watchlists/semiconductor-core/collection-status")) {
          return collectionStatusResponse();
        }
        return jsonResponse({ status: "ok", price_rows: 1, indicator_rows: 1, news_items: 0, disclosures: 0 });
      }),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders the investing dashboard shell with approved labels and chart controls", async () => {
    render(<WatchlistDashboard />);

    expect(screen.getByRole("heading", { name: "투자 대시보드" })).toBeInTheDocument();
    expect(screen.queryAllByText(/로 로그인/)).toHaveLength(0);
    expect(screen.getByTestId("mode-line")).toHaveTextContent("라인");
    expect(screen.getByTestId("mode-candle")).toHaveTextContent("캔들");
    expect(screen.getByTestId("chart-reset")).toHaveTextContent("줌 초기화");

    for (const opinion of APPROVED_OPINIONS) {
      expect(screen.getAllByText(opinion).length).toBeGreaterThan(0);
    }
    await waitFor(() => {
      expect(screen.getByText("999.12")).toBeInTheDocument();
    });
  });

  it("creates a new group and adds NVDA through the visible controls", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, _init?: RequestInit): Promise<Response> => {
      const url = String(input);
      if (url.includes("/api/watchlists/semiconductor-core/dashboard")) {
        return dashboardResponse();
      }
      if (url.includes("/api/tickers/validate?symbol=NVDA")) {
        return jsonResponse({ symbol: "NVDA", valid: true, provider: "yfinance" });
      }
      return jsonResponse({ status: "ok", price_rows: 1, indicator_rows: 1, news_items: 0, disclosures: 0 });
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<WatchlistDashboard />);

    fireEvent.change(screen.getByLabelText("새 그룹 이름"), { target: { value: "AI Memory Lab" } });
    fireEvent.click(screen.getByRole("button", { name: "새 그룹" }));
    fireEvent.change(screen.getByLabelText("새 종목 심볼"), { target: { value: "NVDA" } });
    fireEvent.click(screen.getByRole("button", { name: "추가" }));

    expect(screen.getByRole("button", { name: "AI Memory Lab" })).toBeInTheDocument();
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/api/tickers/validate?symbol=NVDA");
    });
    await waitFor(() => {
      expect(screen.getByTestId("symbol-NVDA")).toHaveTextContent("NVDA");
    });
    await waitFor(() => {
      expect(screen.getByText("999.12")).toBeInTheDocument();
    });
  });

  it("does not add a symbol until the backend validates that the ticker exists", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, _init?: RequestInit): Promise<Response> => {
      const url = String(input);
      if (url.includes("/api/watchlists/semiconductor-core/dashboard")) {
        return dashboardResponse();
      }
      if (url.includes("/api/tickers/validate?symbol=NOTREAL")) {
        return jsonResponse({ detail: "ticker not found" }, 404);
      }
      return jsonResponse({ status: "ok", price_rows: 1, indicator_rows: 1, news_items: 0, disclosures: 0 });
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<WatchlistDashboard />);

    fireEvent.change(screen.getByLabelText("새 그룹 이름"), { target: { value: "검증 그룹" } });
    fireEvent.click(screen.getByRole("button", { name: "새 그룹" }));
    fireEvent.change(screen.getByLabelText("새 종목 심볼"), { target: { value: "NOTREAL" } });
    fireEvent.click(screen.getByRole("button", { name: "추가" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/api/tickers/validate?symbol=NOTREAL");
    });
    expect(screen.getByText("실제 조회 가능한 티커만 추가할 수 있습니다.")).toBeInTheDocument();
    expect(screen.queryByTestId("symbol-NOTREAL")).not.toBeInTheDocument();
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
    vi.stubGlobal("fetch", fetchMock);

    render(<WatchlistDashboard />);

    expect(screen.getByRole("status")).toHaveTextContent("주식 정보를 확인하는 중");
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/api/startup/market-refresh?no_network=false&include_news=true", { method: "POST" });
    });
    await waitFor(() => {
      expect(screen.queryByText("주식 정보를 확인하는 중")).not.toBeInTheDocument();
    });
  });

  it("uses same-origin API routes when the static frontend is served by FastAPI", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, _init?: RequestInit): Promise<Response> => {
      const url = String(input);
      if (url.includes("/api/watchlists/semiconductor-core/dashboard")) {
        return dashboardResponse();
      }
      return jsonResponse({ status: "ok", price_rows: 1, indicator_rows: 1, news_items: 0, disclosures: 0 });
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<WatchlistDashboard />);

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/api/settings");
    });
    expect(fetchMock).toHaveBeenCalledWith("/api/startup/market-refresh?no_network=false&include_news=true", { method: "POST" });
    expect(fetchMock).toHaveBeenCalledWith("/api/watchlists/semiconductor-core/dashboard?days=260");
    expect(fetchMock.mock.calls.map(([input]) => String(input))).not.toContain("/api/backend/settings");
  });

  it("renders price, indicators, and chart data from the backend dashboard payload", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, _init?: RequestInit): Promise<Response> => {
      const url = String(input);
      if (url.includes("/api/settings")) {
        return jsonResponse({ provider_status: { opendart: { configured: true }, ai: { mode: "local" } } });
      }
      if (url.includes("/api/watchlists/semiconductor-core/dashboard")) {
        return dashboardResponse();
      }
      return jsonResponse({ status: "ok", price_rows: 2, indicator_rows: 2, news_items: 0, disclosures: 0 });
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<WatchlistDashboard />);

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/api/watchlists/semiconductor-core/dashboard?days=260");
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
    vi.stubGlobal("fetch", fetchMock);

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
      "/api/watchlists/semiconductor-core/dashboard?days=260",
    );
    expect(screen.queryByText("시장 데이터 갱신 실패")).not.toBeInTheDocument();
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
    vi.stubGlobal("fetch", fetchMock);

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
    vi.stubGlobal("fetch", fetchMock);

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
    vi.stubGlobal("fetch", fetchMock);

    render(<WatchlistDashboard />);

    fireEvent.click(screen.getByRole("button", { name: "리포트 발행" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/api/research/NVDA/generate", { method: "POST" });
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
        if (url.includes("/api/research/NVDA/generate")) {
          return jsonResponse({ detail: "AI provider API key is required for non-local providers" }, 503);
        }
        return jsonResponse({ status: "ok", price_rows: 1, indicator_rows: 1, news_items: 0, disclosures: 0 });
      }),
    );

    render(<WatchlistDashboard />);

    fireEvent.click(screen.getByRole("button", { name: "리포트 발행" }));

    await waitFor(() => {
      expect(screen.getByText("AI API 설정이 필요합니다. 설정에서 provider 키 또는 로컬 모델을 확인해주세요.")).toBeInTheDocument();
    });
    expect(screen.queryByText("AI provider API key is required for non-local providers")).not.toBeInTheDocument();
  });

  it("renders generated opinion, thesis, and source count after report generation succeeds", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, _init?: RequestInit): Promise<Response> => {
        const url = String(input);
        if (url.includes("/api/settings")) {
          return jsonResponse({ provider_status: { opendart: { configured: true }, ai: { mode: "local" } } });
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

    fireEvent.click(screen.getByRole("button", { name: "리포트 발행" }));

    await waitFor(() => {
      expect(screen.getByText("투자의견 매수")).toBeInTheDocument();
    });
    expect(screen.getByText("<script>alert('x')</script>DB 소스 기반으로 수요 개선 가능성을 점검했습니다.")).toBeInTheDocument();
    expect(screen.getByText("근거 2개")).toBeInTheDocument();
    expect(document.querySelector("script")).toBeNull();
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
      if (url.includes("/api/research/NVDA/generate")) {
        return generatePromise;
      }
      return jsonResponse({ status: "ok", price_rows: 1, indicator_rows: 1, news_items: 0, disclosures: 0 });
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<WatchlistDashboard />);

    fireEvent.click(screen.getByRole("button", { name: "리포트 발행" }));
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
      if (url.includes("/api/research/005930.KS/generate")) {
        return jsonResponse({ target_slug: "005930.KS", opinion: "중립", thesis: "삼성전자 리포트", sources: [] }, 201);
      }
      return jsonResponse({ status: "ok", price_rows: 1, indicator_rows: 1, news_items: 0, disclosures: 0 });
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<WatchlistDashboard />);

    fireEvent.click(screen.getByTestId("symbol-005930.KS"));
    fireEvent.click(screen.getByRole("button", { name: "리포트 발행" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/api/research/005930.KS/generate", { method: "POST" });
    });
    expect(screen.queryByText("DB 가격 지표와 공개 소스를 바탕으로 모멘텀을 점검했습니다.")).not.toBeInTheDocument();
  });
});
