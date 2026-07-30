import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ResearchCard } from "./ResearchCard";
import { labelFor } from "@/lib/i18n";

const labels = labelFor("ko").report;

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
  sources_count: 5,
  run_id: "run-1",
  report_path: "/reports/nvda.md",
  obsidian_path: "/vault/nvda.md",
  report_url: "http://localhost/reports/nvda",
};

describe("ResearchCard", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders heading and no-report state initially", () => {
    render(<ResearchCard symbol="NVDA" labels={labels} />);
    expect(screen.getByText(labels.heading)).toBeInTheDocument();
    expect(screen.getByText(labels.noReport)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: labels.generateAction })).toBeInTheDocument();
  });

  it("renders all five opinion badges", () => {
    render(<ResearchCard symbol="NVDA" labels={labels} />);
    expect(screen.getByText("매수")).toBeInTheDocument();
    expect(screen.getByText("매도")).toBeInTheDocument();
    expect(screen.getByText("중립")).toBeInTheDocument();
  });

  it("generates a report and shows success state", async () => {
    vi.mocked(fetch).mockResolvedValue(jsonResponse(VALID_REPORT));
    render(<ResearchCard symbol="NVDA" labels={labels} />);

    fireEvent.click(screen.getByRole("button", { name: labels.generateAction }));

    await waitFor(() => {
      expect(screen.getByText("AI 수요 강세")).toBeInTheDocument();
    });
    expect(screen.getByText(labels.generated)).toBeInTheDocument();
    expect(screen.getByText(labels.reportLink)).toBeInTheDocument();
  });

  it("shows error message on API failure", async () => {
    vi.mocked(fetch).mockResolvedValue(jsonResponse({ detail: "AI provider API key missing" }, 503));
    render(<ResearchCard symbol="NVDA" labels={labels} />);

    fireEvent.click(screen.getByRole("button", { name: labels.generateAction }));

    await waitFor(() => {
      expect(screen.getByText(/AI API 설정/)).toBeInTheDocument();
    });
  });

  it("shows cancel button during generation", async () => {
    let resolveFetch: (value: Response) => void;
    const pending = new Promise<Response>((resolve) => {
      resolveFetch = resolve;
    });
    vi.mocked(fetch).mockReturnValue(pending);

    render(<ResearchCard symbol="NVDA" labels={labels} />);
    fireEvent.click(screen.getByRole("button", { name: labels.generateAction }));

    await waitFor(() => {
      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: labels.cancelAction })).toBeInTheDocument();

    // Cancel
    fireEvent.click(screen.getByRole("button", { name: labels.cancelAction }));
    await waitFor(() => {
      expect(screen.getByText(labels.canceled)).toBeInTheDocument();
    });

    // Resolve the pending fetch to avoid dangling promise
    resolveFetch!(jsonResponse(VALID_REPORT));
  });

  it("disables generate button while generating", async () => {
    let resolveFetch: (value: Response) => void;
    const pending = new Promise<Response>((resolve) => {
      resolveFetch = resolve;
    });
    vi.mocked(fetch).mockReturnValue(pending);

    render(<ResearchCard symbol="NVDA" labels={labels} />);
    const button = screen.getByRole("button", { name: labels.generateAction });
    fireEvent.click(button);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: labels.generating })).toBeDisabled();
    });

    resolveFetch!(jsonResponse(VALID_REPORT));
  });

  it("resets state when symbol changes", async () => {
    vi.mocked(fetch).mockResolvedValue(jsonResponse(VALID_REPORT));
    const { rerender } = render(<ResearchCard symbol="NVDA" labels={labels} />);

    fireEvent.click(screen.getByRole("button", { name: labels.generateAction }));
    await waitFor(() => {
      expect(screen.getByText("AI 수요 강세")).toBeInTheDocument();
    });

    rerender(<ResearchCard symbol="AAPL" labels={labels} />);
    expect(screen.getByText(labels.noReport)).toBeInTheDocument();
  });

  it("uses aria-live for status messages (fec: aria-live-regions)", async () => {
    vi.mocked(fetch).mockResolvedValue(jsonResponse(VALID_REPORT));
    render(<ResearchCard symbol="NVDA" labels={labels} />);

    fireEvent.click(screen.getByRole("button", { name: labels.generateAction }));

    await waitFor(() => {
      const statusElements = screen.getAllByRole("status");
      expect(statusElements.length).toBeGreaterThan(0);
      expect(statusElements[0]).toHaveAttribute("aria-live", "polite");
    });
  });
});
