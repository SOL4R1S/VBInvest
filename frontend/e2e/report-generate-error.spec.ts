import { expect, test } from "@playwright/test";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { routeDashboardData } from "./dashboard-fixture";

const evidenceDir = path.resolve(process.cwd(), "../evidence");

async function writeEvidence(name: string, content: string | Buffer) {
  await mkdir(evidenceDir, { recursive: true });
  await writeFile(path.join(evidenceDir, name), content);
}

test("report button shows safe AI configuration error", async ({ page }) => {
  await routeDashboardData(page);
  await page.route("**/api/settings", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        providers: { ai_api_key: "raw-ai-token-fixture" },
        provider_status: { opendart: { configured: true }, ai: { mode: "misconfigured" } },
      }),
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
    await route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({ detail: "AI provider API key is required for non-local providers" }),
    });
  });

  await page.goto("/");
  await page.getByRole("button", { name: "리포트 발행" }).click();

  await expect(page.getByText("AI API 설정이 필요합니다. 설정에서 provider 키 또는 로컬 모델을 확인해주세요.")).toBeVisible();
  await expect(page.getByText("AI provider API key is required for non-local providers")).toHaveCount(0);
  await expect(page.getByText("raw-ai-token-fixture")).toHaveCount(0);

  await writeEvidence("task-7-report-generate-error.png", await page.screenshot({ fullPage: true }));
  await writeEvidence(
    "task-7-report-generate-error.json",
    JSON.stringify({ bodyText: await page.locator("body").textContent() }, null, 2),
  );
});
