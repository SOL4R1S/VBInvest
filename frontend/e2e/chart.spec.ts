import { expect, test } from "@playwright/test";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";

const evidenceDir = path.resolve(process.cwd(), "../evidence");

async function writeEvidence(name: string, content: string | Buffer) {
  await mkdir(evidenceDir, { recursive: true });
  await writeFile(path.join(evidenceDir, name), content);
}

test("dashboard chart interactions preserve stable stroke width", async ({ page }) => {
  const errors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") {
      errors.push(message.text());
    }
  });

  await page.goto("/");
  await expect(page.getByRole("heading", { name: "투자 대시보드" })).toBeVisible();
  await page.getByRole("button", { name: "Google로 로그인" }).click();
  await page.getByRole("button", { name: "Kakao로 로그인" }).click();
  await page.getByTestId("symbol-NVDA").click();

  const chart = page.getByTestId("chart-frame");
  await expect(chart).toBeVisible();
  await expect(chart).not.toHaveAttribute("data-range-from", "pending");

  const beforeRange = {
    from: await chart.getAttribute("data-range-from"),
    to: await chart.getAttribute("data-range-to"),
    priceLineWidth: await chart.getAttribute("data-price-line-width"),
    rsiLineWidth: await chart.getAttribute("data-rsi-line-width"),
  };
  const before = await chart.screenshot();
  await chart.hover();
  await page.mouse.wheel(0, -1200);
  await page.mouse.move(800, 360);
  await page.mouse.down();
  await page.mouse.move(680, 360, { steps: 6 });
  await page.mouse.up();
  const zoomedRange = {
    from: await chart.getAttribute("data-range-from"),
    to: await chart.getAttribute("data-range-to"),
    priceLineWidth: await chart.getAttribute("data-price-line-width"),
    rsiLineWidth: await chart.getAttribute("data-rsi-line-width"),
  };
  const after = await chart.screenshot();
  await page.getByTestId("chart-reset").click();
  await writeEvidence("task-10-chart-flow.png", after);
  await writeEvidence(
    "task-10-chart-flow.json",
    JSON.stringify({ beforeRange, zoomedRange, screenshotBytes: { before: before.length, after: after.length } }, null, 2),
  );
  await writeEvidence(
    "task-10-stroke-width.json",
    JSON.stringify(
      {
        before: { priceLineWidth: beforeRange.priceLineWidth, rsiLineWidth: beforeRange.rsiLineWidth },
        after: { priceLineWidth: zoomedRange.priceLineWidth, rsiLineWidth: zoomedRange.rsiLineWidth },
      },
      null,
      2,
    ),
  );

  expect(errors).toEqual([]);
  expect(before.length).toBeGreaterThan(0);
  expect(after.length).toBeGreaterThan(0);
  expect(zoomedRange).not.toMatchObject({ from: beforeRange.from, to: beforeRange.to });
  expect(zoomedRange.priceLineWidth).toBe(beforeRange.priceLineWidth);
  expect(zoomedRange.rsiLineWidth).toBe(beforeRange.rsiLineWidth);
});

test("mobile layout keeps toolbar readable", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");

  const toolbar = page.locator(".chart-toolbar");
  await expect(toolbar).toBeVisible();
  const box = await toolbar.boundingBox();
  expect(box).not.toBeNull();
  expect(box?.height ?? 0).toBeGreaterThan(0);
  expect(box?.width ?? 0).toBeGreaterThan(0);
  await writeEvidence("task-10-mobile.png", await page.screenshot({ fullPage: true }));
  await writeEvidence("task-10-mobile.json", JSON.stringify({ toolbarBox: box }, null, 2));
});
