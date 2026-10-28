import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const PAGES = ["", "for/oyster/", "for/shrimp/", "about/", "station/west-sound/", "station/pearl-river/"];

test.beforeEach(async ({ page }) => {
  // Start every test without a remembered persona or theme.
  await page.addInitScript(() => { try { localStorage.clear(); } catch {} });
});

for (const path of PAGES) {
  test(`/${path} loads cleanly and passes accessibility checks`, async ({ page }) => {
    const errors: string[] = [];
    page.on("pageerror", (e) => errors.push(e.message));
    page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
    const res = await page.goto(path);
    expect(res?.status()).toBe(200);
    await expect(page.locator("h1")).not.toBeEmpty();
    const axe = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze();
    const serious = axe.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
    expect(serious, serious.map((v) => `${v.id}: ${v.help}`).join("\n")).toEqual([]);
    expect(errors).toEqual([]);
  });
}

test("persona choice navigates and is remembered", async ({ page }) => {
  await page.goto("");
  await page.getByLabel("Show conditions for").selectOption("oyster");
  await expect(page).toHaveURL(/\/for\/oyster\/$/);
  await page.goto("");
  await expect(page).toHaveURL(/\/for\/oyster\/$/);
});

test("dark theme applies and persists", async ({ page }) => {
  await page.goto("");
  await page.getByLabel("Theme").selectOption("dark");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
});

test("station charts render", async ({ page }) => {
  await page.goto("station/west-sound/");
  const chart = page.locator(".chart-box svg");
  await chart.scrollIntoViewIfNeeded();
  await expect(chart).toBeVisible();
  await page.getByRole("button", { name: "1 year" }).click();
  await expect(page.getByRole("button", { name: "1 year" })).toHaveAttribute("aria-pressed", "true");
});
