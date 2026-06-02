import { expect, test } from "@playwright/test";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { routeDashboardData } from "./dashboard-fixture";

const evidenceDir = path.resolve(process.cwd(), "../.omo/ulw-loop/evidence");

async function writeEvidence(name: string, content: string | Buffer) {
  await mkdir(evidenceDir, { recursive: true });
  await writeFile(path.join(evidenceDir, name), content);
}

test("report button generates and renders research", async ({ page }) => {
  const seenGenerateRequests: string[] = [];
  let completeGenerate: () => void = () => undefined;

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
    await new Promise<void>((resolve) => {
      completeGenerate = resolve;
    });
    await route.fulfill({
      status: 201,
      contentType: "application/json",
      body: JSON.stringify({
        target_slug: "NVDA",
        opinion: "매수",
        thesis: "DB 가격 지표와 공개 소스를 바탕으로 수요 개선 가능성을 점검했습니다.",
        sources: [{ kind: "news" }, { kind: "disclosure" }],
        run_id: "run-task13",
        report_url: "/api/research/NVDA/latest",
        report_path: "/tmp/vbinvest/reports/NVDA.md",
        obsidian_path: "/tmp/vbinvest/vault/30 Projects/VBinvest/NVDA/2026-06-02.md",
      }),
    });
  });

  await page.goto("/");
  await page.getByRole("button", { name: "리포트 발행" }).click();
  const generationDialog = page.getByRole("dialog", { name: "리포트 발행 중" });
  await expect(generationDialog).toBeVisible();
  await expect(generationDialog.getByText("실시간 분석 중")).toBeVisible();
  await writeEvidence("task13-report-generate-modal.png", await page.screenshot({ fullPage: true }));
  completeGenerate();
  await expect(page.getByText("투자의견 매수")).toBeVisible();
  await expect(page.getByText("DB 가격 지표와 공개 소스를 바탕으로 수요 개선 가능성을 점검했습니다.")).toBeVisible();
  await expect(page.getByText("근거 2개")).toBeVisible();
  await expect(page.getByRole("link", { name: "리포트 링크 보기" })).toBeVisible();
  await expect(page.getByText(/Obsidian 경로:/)).toBeVisible();

  await writeEvidence("task13-report-generate-complete.png", await page.screenshot({ fullPage: true }));
  await writeEvidence(
    "task13-report-generate-modal.json",
    JSON.stringify({ generateRequests: seenGenerateRequests }, null, 2),
  );

  expect(seenGenerateRequests).toHaveLength(1);
  expect(seenGenerateRequests[0]).toContain("POST ");
});

test("report generation can be canceled from the blocking modal", async ({ page }) => {
  const seenRequests: string[] = [];

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
    seenRequests.push(`${route.request().method()} ${route.request().url()}`);
    await new Promise((resolve) => setTimeout(resolve, 150));
    await route.fulfill({
      status: 201,
      contentType: "application/json",
      body: JSON.stringify({ target_slug: "NVDA", opinion: "중립", thesis: "취소 이후 늦게 온 응답", sources: [] }),
    });
  });

  await page.goto("/");
  await page.getByRole("button", { name: "리포트 발행" }).click();
  await expect(page.getByRole("dialog", { name: "리포트 발행 중" })).toBeVisible();
  await page.getByRole("button", { name: "취소" }).click();
  await expect(page.getByText("취소됨")).toBeVisible();
  await expect(page.getByText("취소 이후 늦게 온 응답")).not.toBeVisible();

  await writeEvidence(
    "task13-report-generate-cancel.json",
    JSON.stringify({ seenRequests, bodyText: await page.locator("body").textContent() }, null, 2),
  );

  expect(seenRequests).toHaveLength(1);
  expect(seenRequests[0]).toContain("POST ");
});
