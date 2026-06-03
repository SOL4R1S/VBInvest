import { expect, test } from "@playwright/test";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { routeDashboardData } from "./dashboard-fixture";

const evidenceDir = path.resolve(process.cwd(), "../.omo/ulw-loop/evidence");

async function writeEvidence(name: string, content: string | Buffer) {
  await mkdir(evidenceDir, { recursive: true });
  await writeFile(path.join(evidenceDir, name), content);
}

test("scheduled precompute setting toggles through scheduler settings API", async ({ page }) => {
  const patchBodies: readonly string[] = [];
  const mutablePatchBodies: string[] = [];

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
  await page.route("**/api/scheduler/settings", async (route) => {
    if (route.request().method() === "PATCH") {
      mutablePatchBodies.push(route.request().postData() ?? "");
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          daily_refresh_enabled: true,
          weekly_precompute_enabled: true,
          watchlist: "semiconductor-core",
          include_news: true,
        }),
      });
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        daily_refresh_enabled: true,
        weekly_precompute_enabled: false,
        watchlist: "semiconductor-core",
        include_news: true,
      }),
    });
  });

  await page.goto("/");
  const toggle = page.getByRole("checkbox", { name: "예약 사전 생성" });
  await expect(toggle).not.toBeChecked();
  await toggle.click();
  await expect(toggle).toBeChecked();
  await expect(page.getByText("예약 사전 생성 켜짐")).toBeVisible();

  await writeEvidence("task14-scheduler-toggle.png", await page.screenshot({ fullPage: true }));
  await writeEvidence(
    "task14-scheduler-toggle.json",
    JSON.stringify({ patchBodies: [...patchBodies, ...mutablePatchBodies] }, null, 2),
  );

  expect(mutablePatchBodies).toEqual([JSON.stringify({ weekly_precompute_enabled: true })]);
});
