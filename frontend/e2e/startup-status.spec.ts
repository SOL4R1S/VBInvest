import { expect, test } from "@playwright/test";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { routeDashboardData } from "./dashboard-fixture";

const evidenceDir = path.resolve(process.cwd(), "../evidence");

async function writeEvidence(name: string, content: string | Buffer) {
  await mkdir(evidenceDir, { recursive: true });
  await writeFile(path.join(evidenceDir, name), content);
}

test("dashboard shows startup source counts without raw provider secrets", async ({ page }) => {
  const consoleErrors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") {
      consoleErrors.push(message.text());
    }
  });

  await routeDashboardData(page);
  await page.route("**/api/settings", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        providers: {
          ai_api_key: "raw-ai-token-fixture",
          opendart_api_key: "raw-dart-token-fixture",
        },
        provider_status: {
          opendart: { configured: false, source: "none" },
          ai: {
            mode: "local",
            provider: "ollama",
            key_required: false,
            key_configured: false,
            base_url: "http://127.0.0.1:11434/v1",
            model: "qwen2.5",
            error: null,
          },
        },
      }),
    });
  });
  await page.route("**/api/startup/market-refresh?**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        status: "partial",
        price_rows: 2,
        indicator_rows: 2,
        news_items: 4,
        disclosures: 1,
        provider_disabled: [{ symbol: "005930.KS", provider: "dart", reason: "missing-api-key" }],
      }),
    });
  });

  await page.goto("/");
  const status = page.getByTestId("startup-status");
  await expect(status).toContainText("일부 소스 비활성화");
  await expect(status).toContainText("가격 2 · 지표 2");
  await expect(status).toContainText("뉴스 4 · 공시 1");
  await expect(status).toContainText("OpenDART 미설정 · AI local");
  await expect(page.getByText("raw-ai-token-fixture")).toHaveCount(0);
  await expect(page.getByText("raw-dart-token-fixture")).toHaveCount(0);

  const screenshot = await page.screenshot({ fullPage: true });
  await writeEvidence("task-6-startup-status.png", screenshot);
  await writeEvidence(
    "task-6-startup-status.json",
    JSON.stringify(
      {
        statusText: await status.textContent(),
        consoleErrors,
        rawSecretVisible: (await page.locator("body").textContent())?.includes("raw-ai-token-fixture") ?? true,
      },
      null,
      2,
    ),
  );

  expect(consoleErrors).toEqual([]);
});

test("dashboard loads global styling on first render", async ({ page }) => {
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
      body: JSON.stringify({ status: "ok", price_rows: 1, indicator_rows: 1, news_items: 0, disclosures: 0 }),
    });
  });

  await page.goto("/");

  const backgroundImage = await page.locator("body").evaluate((node) => getComputedStyle(node).backgroundImage);
  expect(backgroundImage).toContain("linear-gradient");
  const paddingTop = await page.locator(".page").evaluate((node) => Number.parseFloat(getComputedStyle(node).paddingTop));
  expect(paddingTop).toBeGreaterThanOrEqual(12);
});
