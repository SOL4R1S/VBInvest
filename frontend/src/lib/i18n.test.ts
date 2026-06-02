import { describe, expect, it } from "vitest";

import { SUPPORTED_LANGUAGES, labelFor, resolveLanguage } from "./i18n";

describe("i18n resources", () => {
  it("supports exactly Korean and English", () => {
    expect(SUPPORTED_LANGUAGES).toEqual(["ko", "en"]);
  });

  it("resolves the saved language before browser locale", () => {
    expect(resolveLanguage(undefined, "en", "ko-KR")).toBe("en");
  });

  it("maps supported browser locales and falls back to Korean", () => {
    expect(resolveLanguage(undefined, null, "en-US")).toBe("en");
    expect(resolveLanguage(undefined, null, "ko-KR")).toBe("ko");
    expect(resolveLanguage(undefined, null, "fr-FR")).toBe("ko");
    expect(resolveLanguage("ja", null, "zz-ZZ")).toBe("ko");
  });

  it("keeps Korean and English resources in the same nested shape", () => {
    expect(sortedKeyPaths(labelFor("en"))).toEqual(sortedKeyPaths(labelFor("ko")));
  });

  it("contains the common dashboard, setup, report, shutdown, provider, and chart labels", () => {
    const ko = labelFor("ko");
    const en = labelFor("en");

    expect(ko.app.dashboardHeading).toBe("투자 대시보드");
    expect(en.app.dashboardHeading).toBe("Investment Dashboard");
    expect(ko.setup.title).toBe("초기 설정");
    expect(en.setup.title).toBe("First Run Setup");
    expect(ko.setup.databaseModeDockerHint).not.toContain("설치 후 다시 시도");
    expect(en.setup.databaseModeDockerHint).not.toContain("Install it and try again");
    expect(ko.report.generateAction).toBe("리포트 발행");
    expect(en.report.generateAction).toBe("Generate report");
    expect(ko.controls.shutdownAction).toBe("종료");
    expect(en.controls.shutdownAction).toBe("Shutdown");
    expect(ko.setup.aiModeCodex).toContain("계정 제한");
    expect(en.setup.aiModeCodex).toContain("account restriction");
    expect(ko.providerSummaryLabels.opendartEnabled).toBe("OpenDART 설정됨");
    expect(en.providerSummaryLabels.opendartEnabled).toBe("OpenDART configured");
    expect(ko.chart.line).toBe("라인");
    expect(en.chart.candle).toBe("Candle");
  });
});

function sortedKeyPaths(value: Record<string, unknown>): readonly string[] {
  return collectKeyPaths(value).sort();
}

function collectKeyPaths(value: Record<string, unknown>, prefix = ""): string[] {
  const paths: string[] = [];
  for (const [key, child] of Object.entries(value)) {
    const path = prefix === "" ? key : `${prefix}.${key}`;
    paths.push(path);
    if (isPlainObject(child)) {
      paths.push(...collectKeyPaths(child, path));
    }
  }
  return paths;
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
