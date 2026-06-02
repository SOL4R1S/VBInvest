import { expect, test } from "@playwright/test";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { routeDashboardData } from "./dashboard-fixture";

const evidenceDir = path.resolve(process.cwd(), "../evidence");

async function writeEvidence(name: string, content: string | Buffer) {
  await mkdir(evidenceDir, { recursive: true });
  await writeFile(path.join(evidenceDir, name), content);
}

test("report button generates and renders research", async ({ page }) => {
  const generateRequests: readonly string[] = [];
  const seenGenerateRequests: string[] = [];

  await routeDashboardData(page);
  await page.route("**/api/settings", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ provider_status: { opendart: { configured: true }, ai: { mode: "local" } } }),
    });
  });
  await page.route("**/api/startup/market-refresh?**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ status: "ok", price_rows: 2, indicator_rows: 2, news_items: 4, disclosures: 1 }),
    });
  });
  await page.route("**/api/research/NVDA/generate", async (route) => {
    seenGenerateRequests.push(`${route.request().method()} ${route.request().url()}`);
    await route.fulfill({
      status: 201,
      contentType: "application/json",
      body: JSON.stringify({
        target_slug: "NVDA",
        opinion: "매수",
        thesis: "DB 가격 지표와 공개 소스를 바탕으로 수요 개선 가능성을 점검했습니다.",
        sources: [{ kind: "news" }, { kind: "disclosure" }],
      }),
    });
  });

  await page.goto("/");
  await page.getByRole("button", { name: "리포트 발행" }).click();
  await expect(page.getByText("투자의견 매수")).toBeVisible();
  await expect(page.getByText("DB 가격 지표와 공개 소스를 바탕으로 수요 개선 가능성을 점검했습니다.")).toBeVisible();
  await expect(page.getByText("근거 2개")).toBeVisible();

  await writeEvidence("task-7-report-generate.png", await page.screenshot({ fullPage: true }));
  await writeEvidence(
    "task-7-report-generate.json",
    JSON.stringify({ generateRequests: seenGenerateRequests, initialRequests: generateRequests }, null, 2),
  );

  expect(seenGenerateRequests).toHaveLength(1);
  expect(seenGenerateRequests[0]).toContain("POST ");
});
