import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const PAGES = ["", "for/oyster/", "for/shrimp/", "about/", "station/west-sound/", "station/pearl-river/"];

// Each test gets a fresh browser context, so localStorage starts empty. Don't clear it with
// addInitScript: that runs before every navigation and would wipe the very choices under test.

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
  await page.getByRole("navigation", { name: "Show conditions for" }).getByRole("link", { name: "Oysters" }).click();
  await expect(page).toHaveURL(/\/for\/oyster\/$/);
  await page.goto("");
  await expect(page).toHaveURL(/\/for\/oyster\/$/);
});

test("dark theme applies and persists", async ({ page }) => {
  await page.goto("");
  await page.getByRole("radiogroup", { name: "Theme" }).getByRole("radio", { name: "Dark" }).click();
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

test("oyster page shows the closure watch with MDMR's criteria", async ({ page }) => {
  await page.goto("for/oyster/");
  await expect(page.getByRole("heading", { name: "Oyster closure watch" })).toBeVisible();
  await expect(page.getByRole("link", { name: "management plan" })).toHaveAttribute("href", /dmr\.ms\.gov/);
});

test("shrimp page shows MDMR's season notices and the wind outlook", async ({ page }) => {
  await page.goto("for/shrimp/");
  await expect(page.getByRole("heading", { name: "Shrimp season", exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "MDMR shrimp information" })).toHaveAttribute("href", /dmr\.ms\.gov/);
});
