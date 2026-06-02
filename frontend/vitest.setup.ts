import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";
import { vi } from "vitest";

vi.mock("lightweight-charts", () => {
  const series = {
    setData: vi.fn(),
    applyOptions: vi.fn(),
  };
  const timeScale = {
    fitContent: vi.fn(),
    getVisibleLogicalRange: vi.fn(() => ({ from: 0, to: 30 })),
    subscribeVisibleLogicalRangeChange: vi.fn(),
    unsubscribeVisibleLogicalRangeChange: vi.fn(),
  };
  const priceScale = {
    applyOptions: vi.fn(),
  };
  const panes = [
    { setHeight: vi.fn() },
    { setHeight: vi.fn() },
  ];
  const chart = {
    addSeries: vi.fn(() => series),
    panes: vi.fn(() => panes),
    priceScale: vi.fn(() => priceScale),
    remove: vi.fn(),
    timeScale: vi.fn(() => timeScale),
  };
  return {
    CandlestickSeries: "CandlestickSeries",
    ColorType: { Solid: "solid" },
    CrosshairMode: { Normal: 0 },
    HistogramSeries: "HistogramSeries",
    LineSeries: "LineSeries",
    createChart: vi.fn(() => chart),
  };
});

class ResizeObserverStub implements ResizeObserver {
  disconnect(): void {}
  observe(): void {}
  unobserve(): void {}
}

Object.defineProperty(window, "ResizeObserver", {
  configurable: true,
  value: ResizeObserverStub,
});

Object.defineProperty(window, "matchMedia", {
  configurable: true,
  value: (query: string): MediaQueryList => ({
    matches: false,
    media: query,
    onchange: null,
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
    addListener: () => undefined,
    removeListener: () => undefined,
    dispatchEvent: () => false,
  }),
});

afterEach(() => {
  cleanup();
});
