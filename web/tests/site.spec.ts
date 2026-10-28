import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const PAGES = ["", "for/oyster/", "for/shrimp/", "about/", "station/west-sound/", "station/pearl-river/"];

// The page refreshes air temp from api.weather.gov on load; answer with a fixed, newer reading so tests don't depend
// on the network. 26.1 °C is 79 °F.
const LIVE_TEMP_C = 26.1;
test.beforeEach(async ({ page }) => {
  await page.route("https://api.weather.gov/**", (route) => route.fulfill({
    contentType: "application/geo+json",
    body: JSON.stringify({ properties: { timestamp: new Date(Date.now() - 5 * 60_000).toISOString(),
      temperature: { unitCode: "wmoUnit:degC", value: LIVE_TEMP_C } } }),
  }));
});

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

test("oyster page puts the river level in typical-year context", async ({ page }) => {
  await page.goto("for/oyster/");
  const line = page.getByText(/daily average has reached/);
  test.skip(await line.count() === 0, "no PERL1 history in this build's data");
  await expect(line).toContainText("not how often areas close");
});

test("shrimp page shows MDMR's season notices and the wind outlook", async ({ page }) => {
  await page.goto("for/shrimp/");
  await expect(page.getByRole("heading", { name: "Shrimp season", exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "MDMR shrimp information" }).first()).toHaveAttribute("href", /dmr\.ms\.gov/);
});

test("air temp refreshes from the latest observation on load", async ({ page }) => {
  await page.goto("");
  const tile = page.locator(".readout[data-live]");
  test.skip(await tile.count() === 0, "no fresh air temp in this build's data");
  await expect(tile).toHaveAttribute("data-live-updated", "");
  await expect(tile.locator("[data-live-value]")).toHaveText("79");
  await expect(tile.locator("[data-live-text]")).toContainText("79°F");
});

test("air temp keeps the built reading when the live request fails", async ({ page }) => {
  await page.route("https://api.weather.gov/**", (route) => route.abort());
  await page.goto("");
  const tile = page.locator(".readout[data-live]");
  test.skip(await tile.count() === 0, "no fresh air temp in this build's data");
  const built = JSON.parse((await tile.getAttribute("data-live"))!);
  await page.waitForLoadState("networkidle");
  await expect(tile.locator("[data-live-value]")).toHaveText(String(Math.round(built.value)));
  await expect(tile).not.toHaveAttribute("data-live-updated", "");
});

test("home page flags the not-official notice and expands to links to the agencies", async ({ page }) => {
  await page.goto("");
  const notice = page.locator("details.official:not(.official-inline)");
  await expect(notice.locator("summary")).toBeVisible();
  await expect(notice.getByRole("link", { name: "MDMR shellfish" })).toBeHidden();
  await notice.locator("summary").click();
  await expect(notice.getByRole("link", { name: "MDMR shellfish" })).toHaveAttribute("href", /dmr\.ms\.gov/);
  await expect(notice.getByRole("link", { name: "MDEQ beach monitoring" })).toHaveAttribute("href", /beaches\.mdeq\.ms\.gov/);
  await expect(page.getByRole("link", { name: "How the data gets here" })).toHaveAttribute("href", /about\/#official/);
});
