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

describe("WatchlistDashboard", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (_input: RequestInfo | URL, _init?: RequestInit): Promise<Response> => {
        return jsonResponse({ status: "ok", price_rows: 1, indicator_rows: 1, news_items: 0, disclosures: 0 });
      }),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders the investing dashboard shell with approved labels and chart controls", () => {
    render(<WatchlistDashboard />);

    expect(screen.getByRole("heading", { name: "투자 대시보드" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Google로 로그인" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Kakao로 로그인" })).toBeInTheDocument();
    expect(screen.getByTestId("mode-line")).toHaveTextContent("라인");
    expect(screen.getByTestId("mode-candle")).toHaveTextContent("캔들");
    expect(screen.getByTestId("chart-reset")).toHaveTextContent("줌 초기화");

    for (const opinion of APPROVED_OPINIONS) {
      expect(screen.getAllByText(opinion).length).toBeGreaterThan(0);
    }
  });

  it("creates a new group and adds NVDA through the visible controls", () => {
    render(<WatchlistDashboard />);

    fireEvent.change(screen.getByLabelText("새 그룹 이름"), { target: { value: "AI Memory Lab" } });
    fireEvent.click(screen.getByRole("button", { name: "새 그룹" }));
    fireEvent.change(screen.getByLabelText("새 종목 심볼"), { target: { value: "NVDA" } });
    fireEvent.click(screen.getByRole("button", { name: "추가" }));

    expect(screen.getByRole("button", { name: "AI Memory Lab" })).toBeInTheDocument();
    expect(screen.getByTestId("symbol-NVDA")).toHaveTextContent("NVDA");
  });

  it("refreshes market data when the local program page opens", async () => {
    const fetchMock = vi.fn(async (_input: RequestInfo | URL, _init?: RequestInit): Promise<Response> => {
      return new Response(JSON.stringify({ status: "ok", price_rows: 1, indicator_rows: 1 }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<WatchlistDashboard />);

    expect(screen.getByRole("status")).toHaveTextContent("주식 정보를 확인하는 중");
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/api/backend/startup/market-refresh?no_network=false&include_news=true", { method: "POST" });
    });
    await waitFor(() => {
      expect(screen.queryByText("주식 정보를 확인하는 중")).not.toBeInTheDocument();
    });
  });

  it("does not run startup market refresh before first-run setup is completed", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, _init?: RequestInit): Promise<Response> => {
      const url = String(input);
      if (url.includes("/api/backend/settings")) {
        return jsonResponse({
          first_run_completed: false,
          provider_status: { opendart: { configured: false }, ai: { mode: "disabled" } },
        });
      }
      return jsonResponse({ status: "ok", price_rows: 1, indicator_rows: 1, news_items: 0, disclosures: 0 });
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<WatchlistDashboard />);

    await waitFor(() => {
      expect(screen.getByText("초기 설정 필요")).toBeInTheDocument();
    });
    expect(fetchMock.mock.calls.map(([input]) => String(input))).not.toContain(
      "/api/backend/startup/market-refresh?no_network=false&include_news=true",
    );
    expect(screen.queryByText("시장 데이터 갱신 실패")).not.toBeInTheDocument();
  });

  it("shows provider-disabled partial refresh without treating it as a total failure", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, _init?: RequestInit): Promise<Response> => {
        const url = String(input);
        if (url.includes("/api/backend/settings")) {
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
        if (url.includes("/api/backend/settings")) {
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
      if (url.includes("/api/backend/settings")) {
        return jsonResponse({ provider_status: { opendart: { configured: true }, ai: { mode: "local" } } });
      }
      if (url.includes("/api/backend/research/NVDA/generate")) {
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
      expect(fetchMock).toHaveBeenCalledWith("/api/backend/research/NVDA/generate", { method: "POST" });
    });
  });

  it("shows a safe setup message when report generation returns AI provider misconfiguration", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, _init?: RequestInit): Promise<Response> => {
        const url = String(input);
        if (url.includes("/api/backend/settings")) {
          return jsonResponse({ provider_status: { opendart: { configured: true }, ai: { mode: "misconfigured" } } });
        }
        if (url.includes("/api/backend/research/NVDA/generate")) {
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
        if (url.includes("/api/backend/settings")) {
          return jsonResponse({ provider_status: { opendart: { configured: true }, ai: { mode: "local" } } });
        }
        if (url.includes("/api/backend/research/NVDA/generate")) {
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
      if (url.includes("/api/backend/settings")) {
        return jsonResponse({ provider_status: { opendart: { configured: true }, ai: { mode: "local" } } });
      }
      if (url.includes("/api/backend/research/NVDA/generate")) {
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
    expect(fetchMock.mock.calls.filter(([input]) => String(input).includes("/api/backend/research/NVDA/generate"))).toHaveLength(1);
  });

  it("generates a report for the currently selected symbol after switching rows", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, _init?: RequestInit): Promise<Response> => {
      const url = String(input);
      if (url.includes("/api/backend/settings")) {
        return jsonResponse({ provider_status: { opendart: { configured: true }, ai: { mode: "local" } } });
      }
      if (url.includes("/api/backend/research/005930.KS/generate")) {
        return jsonResponse({ target_slug: "005930.KS", opinion: "중립", thesis: "삼성전자 리포트", sources: [] }, 201);
      }
      return jsonResponse({ status: "ok", price_rows: 1, indicator_rows: 1, news_items: 0, disclosures: 0 });
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<WatchlistDashboard />);

    fireEvent.click(screen.getByTestId("symbol-005930.KS"));
    fireEvent.click(screen.getByRole("button", { name: "리포트 발행" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/api/backend/research/005930.KS/generate", { method: "POST" });
    });
    expect(screen.queryByText("DB 가격 지표와 공개 소스를 바탕으로 모멘텀을 점검했습니다.")).not.toBeInTheDocument();
  });
});
