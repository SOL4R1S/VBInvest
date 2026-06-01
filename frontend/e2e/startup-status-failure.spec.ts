import { expect, test } from "@playwright/test";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { routeDashboardData } from "./dashboard-fixture";

const evidenceDir = path.resolve(process.cwd(), "../evidence");

async function writeEvidence(name: string, content: string | Buffer) {
  await mkdir(evidenceDir, { recursive: true });
  await writeFile(path.join(evidenceDir, name), content);
}

test("dashboard shows failed refresh banner without layout overlap", async ({ page }) => {
  await routeDashboardData(page);
  await page.route("**/api/backend/settings", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        provider_status: {
          opendart: { configured: true, source: "secure-storage" },
          ai: {
            mode: "cloud",
            provider: "openai",
            key_required: true,
            key_configured: true,
            base_url: "https://api.openai.com/v1",
            model: "gpt-test",
            error: null,
          },
        },
      }),
    });
  });
  await page.route("**/api/backend/startup/market-refresh?**", async (route) => {
    await route.fulfill({
      status: 500,
      contentType: "application/json",
      body: JSON.stringify({ detail: "boom" }),
    });
  });

  await page.goto("/");
  const banner = page.getByText("시장 데이터 갱신 실패").first();
  const hero = page.getByRole("heading", { name: "투자 대시보드" });
  await expect(banner).toBeVisible();
  await expect(hero).toBeVisible();

  const bannerBox = await banner.boundingBox();
  const heroBox = await hero.boundingBox();
  expect(bannerBox).not.toBeNull();
  expect(heroBox).not.toBeNull();
  expect((bannerBox?.y ?? 0) + (bannerBox?.height ?? 0)).toBeLessThan(heroBox?.y ?? 0);

  const screenshot = await page.screenshot({ fullPage: true });
  await writeEvidence("task-6-startup-status-error.png", screenshot);
  await writeEvidence(
    "task-6-startup-status-error.json",
    JSON.stringify({ bannerBox, heroBox, bannerText: await banner.textContent() }, null, 2),
  );
});
