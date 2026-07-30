import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { generateResearchReport, ReportGenerationError } from "./report-generation";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

const VALID_REPORT = {
  target_slug: "NVDA",
  opinion: "매수",
  thesis: "AI 수요 강세",
  sources: ["src1", "src2", "src3", "src4", "src5"],
  run_id: "run-1",
  report_path: "/reports/nvda.md",
  obsidian_path: "/vault/nvda.md",
  report_url: "http://localhost/reports/nvda",
};

describe("generateResearchReport", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("parses a successful report response", async () => {
    vi.mocked(fetch).mockResolvedValue(jsonResponse(VALID_REPORT));
    const report = await generateResearchReport("NVDA");
    expect(report.targetSlug).toBe("NVDA");
    expect(report.opinion).toBe("매수");
    expect(report.thesis).toBe("AI 수요 강세");
    expect(report.sourcesCount).toBe(5);
  });

  it("throws ReportGenerationError on 401", async () => {
    vi.mocked(fetch).mockImplementation(() =>
      Promise.resolve(jsonResponse({ detail: "unauthorized" }, 401)),
    );
    await expect(generateResearchReport("NVDA")).rejects.toThrow(ReportGenerationError);
    await expect(generateResearchReport("NVDA")).rejects.toThrow("로컬 세션");
  });

  it("throws ReportGenerationError on 404", async () => {
    vi.mocked(fetch).mockResolvedValue(jsonResponse({ detail: "not found" }, 404));
    await expect(generateResearchReport("FAKE")).rejects.toThrow("종목 데이터");
  });

  it("throws specific message for AI provider key error", async () => {
    vi.mocked(fetch).mockResolvedValue(
      jsonResponse({ detail: "AI provider API key not configured" }, 503),
    );
    await expect(generateResearchReport("NVDA")).rejects.toThrow("AI API 설정");
  });

  it("throws specific message for reasoning-only output", async () => {
    vi.mocked(fetch).mockResolvedValue(
      jsonResponse({ detail: "reasoning-only output without JSON content" }, 503),
    );
    await expect(generateResearchReport("NVDA")).rejects.toThrow("non-reasoning");
  });

  it("throws specific message for timeout", async () => {
    vi.mocked(fetch).mockResolvedValue(
      jsonResponse({ detail: "AI provider request timed out" }, 503),
    );
    await expect(generateResearchReport("NVDA")).rejects.toThrow("응답 시간이 초과");
  });

  it("throws generic message for unknown 503", async () => {
    vi.mocked(fetch).mockResolvedValue(jsonResponse({ detail: "something else" }, 503));
    await expect(generateResearchReport("NVDA")).rejects.toThrow("리포트 발행에 실패");
  });

  it("wraps network errors as ReportGenerationError", async () => {
    vi.mocked(fetch).mockRejectedValue(new TypeError("Failed to fetch"));
    await expect(generateResearchReport("NVDA")).rejects.toThrow("백엔드 연결");
  });

  it("re-throws AbortError without wrapping", async () => {
    const abortError = new DOMException("Aborted", "AbortError");
    vi.mocked(fetch).mockRejectedValue(abortError);
    await expect(generateResearchReport("NVDA")).rejects.toMatchObject({
      name: "AbortError",
    });
  });

  it("throws on malformed success payload", async () => {
    vi.mocked(fetch).mockResolvedValue(jsonResponse({ garbage: true }));
    await expect(generateResearchReport("NVDA")).rejects.toThrow("응답 형식");
  });
});
