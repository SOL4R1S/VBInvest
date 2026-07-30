import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { ChartShell } from "./ChartShell";
import type { ChartPoint } from "@/lib/dashboard-data";

// Mock lightweight-charts — canvas library cannot run in jsdom
const mockFitContent = vi.fn();
const mockGetVisibleLogicalRange = vi.fn(() => ({ from: 0, to: 10 }));
const mockSubscribe = vi.fn();
const mockUnsubscribe = vi.fn();
const mockTimeScale = vi.fn(() => ({
  fitContent: mockFitContent,
  getVisibleLogicalRange: mockGetVisibleLogicalRange,
  subscribeVisibleLogicalRangeChange: mockSubscribe,
  unsubscribeVisibleLogicalRangeChange: mockUnsubscribe,
}));
const mockApplyOptions = vi.fn();
const mockSetData = vi.fn();
const mockAddSeries = vi.fn(() => ({
  applyOptions: mockApplyOptions,
  setData: mockSetData,
}));
const mockSetHeight = vi.fn();
const mockPanes = vi.fn(() => [{ setHeight: mockSetHeight }, { setHeight: mockSetHeight }]);
const mockPriceScale = vi.fn(() => ({ applyOptions: vi.fn() }));
const mockRemove = vi.fn();
const mockCreateChart = vi.fn(() => ({
  addSeries: mockAddSeries,
  timeScale: mockTimeScale,
  panes: mockPanes,
  priceScale: mockPriceScale,
  remove: mockRemove,
}));

vi.mock("lightweight-charts", () => ({
  createChart: (...args: unknown[]) => mockCreateChart(...args),
  CandlestickSeries: "CandlestickSeries",
  LineSeries: "LineSeries",
  HistogramSeries: "HistogramSeries",
  ColorType: { Solid: "solid" },
  CrosshairMode: { Normal: 0 },
}));

// Mock ResizeObserver
class MockResizeObserver {
  observe = vi.fn();
  unobserve = vi.fn();
  disconnect = vi.fn();
}
vi.stubGlobal("ResizeObserver", MockResizeObserver);

const labels = {
  line: "라인",
  candle: "캔들",
  reset: "초기화",
  modeLine: "라인 모드",
  modeCandle: "캔들 모드",
  resetView: "뷰 초기화",
  legend: "범례",
};

function makePoint(overrides: Partial<ChartPoint> = {}): ChartPoint {
  return {
    time: "2026-01-15",
    open: 100,
    high: 110,
    low: 95,
    close: 105,
    volume: 1000000,
    ma5: 103,
    ma20: 101,
    ma50: null,
    ma120: null,
    rsi14: 55,
    ...overrides,
  };
}

const samplePoints: ChartPoint[] = [
  makePoint({ time: "2026-01-13", close: 100 }),
  makePoint({ time: "2026-01-14", close: 102 }),
  makePoint({ time: "2026-01-15", close: 105 }),
];

describe("ChartShell", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders chart section with symbol aria-label", () => {
    render(<ChartShell symbol="AAPL" points={samplePoints} labels={labels} />);
    const section = screen.getByRole("region", { name: "AAPL 차트" });
    expect(section).toBeInTheDocument();
  });

  it("renders toolbar with line/candle/reset buttons", () => {
    render(<ChartShell symbol="AAPL" points={samplePoints} labels={labels} />);
    expect(screen.getByTestId("mode-line")).toHaveTextContent("라인");
    expect(screen.getByTestId("mode-candle")).toHaveTextContent("캔들");
    expect(screen.getByTestId("chart-reset")).toHaveTextContent("초기화");
  });

  it("defaults to candle mode with aria-pressed", () => {
    render(<ChartShell symbol="AAPL" points={samplePoints} labels={labels} />);
    expect(screen.getByTestId("mode-candle")).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByTestId("mode-line")).toHaveAttribute("aria-pressed", "false");
  });

  it("switches to line mode on click", () => {
    render(<ChartShell symbol="AAPL" points={samplePoints} labels={labels} />);
    fireEvent.click(screen.getByTestId("mode-line"));
    expect(screen.getByTestId("mode-line")).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByTestId("mode-candle")).toHaveAttribute("aria-pressed", "false");
  });

  it("calls fitContent on reset button click", () => {
    render(<ChartShell symbol="AAPL" points={samplePoints} labels={labels} />);
    fireEvent.click(screen.getByTestId("chart-reset"));
    expect(mockFitContent).toHaveBeenCalled();
  });

  it("renders legend with all series items", () => {
    render(<ChartShell symbol="AAPL" points={samplePoints} labels={labels} />);
    const legend = screen.getByLabelText("범례");
    expect(legend).toBeInTheDocument();
    expect(screen.getByTestId("legend-close")).toHaveTextContent("종가");
    expect(screen.getByTestId("legend-ma5")).toHaveTextContent("MA5");
    expect(screen.getByTestId("legend-ma20")).toHaveTextContent("MA20");
    expect(screen.getByTestId("legend-ma50")).toHaveTextContent("MA50");
    expect(screen.getByTestId("legend-ma120")).toHaveTextContent("MA120");
    expect(screen.getByTestId("legend-rsi14")).toHaveTextContent("RSI14");
  });

  it("creates chart with lightweight-charts on mount", () => {
    render(<ChartShell symbol="AAPL" points={samplePoints} labels={labels} />);
    expect(mockCreateChart).toHaveBeenCalledTimes(1);
    // 8 series: candle, line, ma5, ma20, ma50, ma120, rsi, volume
    expect(mockAddSeries).toHaveBeenCalledTimes(8);
  });

  it("sets data on all series", () => {
    render(<ChartShell symbol="AAPL" points={samplePoints} labels={labels} />);
    // candle + line + ma5 + ma20 + rsi + volume = 6 with data (ma50/ma120 null-filtered but still called)
    expect(mockSetData).toHaveBeenCalledTimes(8);
  });

  it("exposes chart mode via data attribute", () => {
    render(<ChartShell symbol="AAPL" points={samplePoints} labels={labels} />);
    const frame = screen.getByTestId("chart-frame");
    expect(frame).toHaveAttribute("data-chart-mode", "candle");
    fireEvent.click(screen.getByTestId("mode-line"));
    expect(frame).toHaveAttribute("data-chart-mode", "line");
  });

  it("cleans up chart on unmount", () => {
    const { unmount } = render(<ChartShell symbol="AAPL" points={samplePoints} labels={labels} />);
    unmount();
    expect(mockRemove).toHaveBeenCalledTimes(1);
    expect(mockUnsubscribe).toHaveBeenCalledTimes(1);
  });

  it("renders legend swatches as aria-hidden", () => {
    render(<ChartShell symbol="AAPL" points={samplePoints} labels={labels} />);
    const swatches = document.querySelectorAll(".legend-swatch");
    expect(swatches.length).toBe(6);
    swatches.forEach((swatch) => {
      expect(swatch).toHaveAttribute("aria-hidden", "true");
    });
  });
});
