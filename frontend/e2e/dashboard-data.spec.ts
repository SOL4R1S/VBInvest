import { expect, test } from "@playwright/test";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";

const evidenceDir = path.resolve(process.cwd(), "../evidence");

async function writeEvidence(name: string, content: string | Buffer) {
  await mkdir(evidenceDir, { recursive: true });
  await writeFile(path.join(evidenceDir, name), content);
}

test("dashboard renders DB-backed market data instead of example values", async ({ page }) => {
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
      body: JSON.stringify({ status: "ok", price_rows: 2, indicator_rows: 2, news_items: 0, disclosures: 0 }),
    });
  });
  await page.route("**/api/watchlists/semiconductor-core/dashboard?**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        watchlist: "semiconductor-core",
        count: 1,
        items: [
          {
            asset: { symbol: "NVDA", display_name_ko: "엔비디아", currency: "USD" },
            latest: {
              date: "2026-06-01",
              close: 999.12,
              return_1d: 0.0388,
              return_1m: 0.125,
              ma5: 990.1,
              ma20: 970.2,
              ma50: 950.3,
              ma120: 930.4,
              rsi14: 64.2,
            },
            opinion: "아웃퍼폼",
            history: [
              { date: "2026-05-29", open: 980, high: 995, low: 970, close: 990, volume: 1000, ma5: 985, ma20: 970, ma50: 950, ma120: 930, rsi14: 61.1 },
              { date: "2026-06-01", open: 990, high: 1005, low: 985, close: 999.12, volume: 1200, ma5: 990.1, ma20: 970.2, ma50: 950.3, ma120: 930.4, rsi14: 64.2 },
            ],
          },
        ],
      }),
    });
  });

  await page.goto("/");

  await expect(page.getByText("999.12")).toBeVisible();
  await expect(page.getByText("+3.88%")).toBeVisible();
  await expect(page.getByText("+12.50%")).toBeVisible();
  await expect(page.getByText("64.2")).toBeVisible();
  await expect(page.getByText("990.1 / 970.2 / 950.3 / 930.4")).toBeVisible();
  await expect(page.getByText("예시 값")).toHaveCount(0);

  const chart = page.getByTestId("chart-frame");
  await expect(chart).not.toHaveAttribute("data-range-from", "pending");
  const screenshot = await page.screenshot({ fullPage: true });
  await writeEvidence("dashboard-data-connection.png", screenshot);
  await writeEvidence(
    "dashboard-data-connection.json",
    JSON.stringify({ bodyText: await page.locator("body").textContent(), rangeFrom: await chart.getAttribute("data-range-from") }, null, 2),
  );
});
