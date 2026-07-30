import { describe, expect, it } from "vitest";

import { APPROVED_OPINIONS, DEFAULT_RESEARCH, normalizeOpinion } from "./research";

describe("APPROVED_OPINIONS", () => {
  it("contains exactly five Korean opinion levels", () => {
    expect(APPROVED_OPINIONS).toHaveLength(5);
    expect(APPROVED_OPINIONS).toContain("매수");
    expect(APPROVED_OPINIONS).toContain("매도");
  });
});

describe("DEFAULT_RESEARCH", () => {
  it("has a neutral default opinion", () => {
    expect(DEFAULT_RESEARCH.opinion).toBe("중립");
  });

  it("includes all scenario fields", () => {
    expect(DEFAULT_RESEARCH.thesis).toBeTruthy();
    expect(DEFAULT_RESEARCH.bull).toBeTruthy();
    expect(DEFAULT_RESEARCH.base).toBeTruthy();
    expect(DEFAULT_RESEARCH.bear).toBeTruthy();
  });
});

describe("normalizeOpinion", () => {
  it("passes through valid opinions", () => {
    for (const opinion of APPROVED_OPINIONS) {
      expect(normalizeOpinion(opinion)).toBe(opinion);
    }
  });

  it("falls back to 중립 for invalid values", () => {
    expect(normalizeOpinion("buy")).toBe("중립");
    expect(normalizeOpinion("")).toBe("중립");
    expect(normalizeOpinion(null)).toBe("중립");
    expect(normalizeOpinion(undefined)).toBe("중립");
  });
});
