import { expect, test } from "@playwright/test";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { routeDashboardData } from "./dashboard-fixture";

const evidenceDir = path.resolve(process.cwd(), "../.omo/ulw-loop/evidence");

async function writeEvidence(name: string, content: string | Buffer): Promise<void> {
  await mkdir(evidenceDir, { recursive: true });
  await writeFile(path.join(evidenceDir, name), content);
}

test("dashboard persists and applies language changes", async ({ page }) => {
  const patchBodies: string[] = [];

  await routeDashboardData(page);
  await page.route("**/api/settings", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        first_run_completed: true,
        language: "en",
        provider_status: {
          opendart: { configured: true },
          ai: { mode: "local" },
        },
      }),
    });
  });
  await page.route("**/api/settings/language", async (route) => {
    patchBodies.push(route.request().postData() ?? "");
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ language: "ko" }),
    });
  });
  await page.route("**/api/startup/market-refresh?**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ status: "ready", price_rows: 2, indicator_rows: 2, news_items: 0, disclosures: 0 }),
    });
  });
  await page.route("**/api/watchlists/semiconductor-core/collection-status", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ watchlist: "semiconductor-core", assets: [] }),
    });
  });
  await page.route("**/api/scheduler/settings", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ daily_refresh_enabled: false, weekly_precompute_enabled: false }),
    });
  });

  await page.goto("/");

  await expect(page.getByRole("heading", { name: "Investment Dashboard" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "투자 대시보드" })).toHaveCount(0);

  await page.getByLabel("Language").selectOption("ko");

  await expect(page.getByRole("heading", { name: "투자 대시보드" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Investment Dashboard" })).toHaveCount(0);
  expect(patchBodies).toEqual([JSON.stringify({ language: "ko" })]);

  const screenshot = await page.screenshot({ fullPage: true });
  await writeEvidence("task17-language-switch.png", screenshot);
  await writeEvidence(
    "task17-language-switch.json",
    JSON.stringify(
      {
        patchBodies,
        heading: await page.getByRole("heading", { name: "투자 대시보드" }).textContent(),
        cleanup: "playwright closed browser context after test",
      },
      null,
      2,
    ),
  );
});
