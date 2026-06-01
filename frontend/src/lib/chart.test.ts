import { describe, expect, it } from "vitest";

import { APPROVED_OPINIONS, normalizeOpinion, rangeWindow } from "./chart";

describe("chart utilities", () => {
  it("keeps only the five approved research opinions", () => {
    expect(APPROVED_OPINIONS).toEqual(["매수", "아웃퍼폼", "중립", "언더퍼폼", "매도"]);
  });

  it("normalizes unknown opinions to 중립", () => {
    expect(normalizeOpinion("가치투자")).toBe("중립");
  });

  it("computes a clamped zoom window from a desired span", () => {
    expect(rangeWindow(100, 26, 10)).toEqual({ start: 4, end: 29 });
  });
});
