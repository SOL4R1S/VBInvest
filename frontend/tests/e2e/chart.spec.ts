import { expect, test } from "@playwright/test";

test("chart flow exposes the baseline selectors", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByTestId("dashboard-disclaimer")).toContainText("투자 조언이 아닙니다");
  await expect(page.getByTestId("create-watchlist")).toBeVisible();
  await expect(page.getByTestId("add-nvda")).toBeVisible();
  await expect(page.getByTestId("chart-zoom-reset")).toBeVisible();
  await expect(page.getByTestId("chart-window")).toHaveAttribute("data-window-start", "0");
  await expect(page.getByTestId("chart-window")).toHaveAttribute("data-window-end", "120");
});
