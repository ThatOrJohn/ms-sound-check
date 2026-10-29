import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const PAGES = ["", "for/oyster/", "for/shrimp/", "for/fish/", "about/", "station/west-sound/", "station/pearl-river/"];

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

test("oyster page shows the spillway watch with the Corps link and every past opening", async ({ page }) => {
  await page.goto("for/oyster/");
  const sec = page.locator("section.spillway");
  await expect(sec.getByRole("heading", { name: "Bonnet Carré Spillway" })).toBeVisible();
  await expect(sec.getByRole("link", { name: /Army Corps of Engineers/ })).toHaveAttribute("href", /usace\.army\.mil/);
  await expect(sec.getByRole("img", { name: /Spillway openings by year: 1937/ })).toBeAttached();
});

test("map replay steps back through the last 30 days and returns to today", async ({ page }) => {
  await page.goto("");
  const slider = page.getByRole("slider", { name: "Day shown on the map" });
  await slider.scrollIntoViewIfNeeded();
  await expect(slider).toBeEnabled({ timeout: 20_000 });      // enabled once the map has loaded
  await expect(page.locator(".replay-day")).toHaveText("Today");
  await slider.fill("0");
  await expect(page.locator(".replay-day")).not.toHaveText("Today");
  await page.getByRole("button", { name: "Play the last 30 days" }).click();
  await expect(page.locator(".replay-day")).toHaveText("Today", { timeout: 20_000 });
});

test("satellite layers are offered, and turning one on turns the other fills off", async ({ page, request }) => {
  const latest = await (await request.get("data/ms/latest.json")).json();
  test.skip(!latest.satellite?.clarity || !latest.satellite?.sst, "no fresh satellite pass in this build");
  await page.goto("for/fish/");
  const panel = page.locator(".map-layers");
  if (!(await panel.evaluate((d: HTMLDetailsElement) => d.open))) await panel.locator("summary").click();   // collapsed on phones
  const clarity = panel.getByRole("checkbox", { name: "Water clarity (satellite)" });
  const sst = panel.getByRole("checkbox", { name: "Surface temp (satellite)" });
  await expect(clarity).toBeEnabled({ timeout: 20_000 });
  await expect(clarity).toBeChecked();                       // the Fishing view starts with clarity on
  await sst.check();
  await expect(clarity).not.toBeChecked();
  await expect(panel.locator(".sat-key")).toContainText("Satellite,");
});

test("the Vibrio note shows on the Coast, Oysters and Fishing pages only, with calm wording and official links", async ({ page, request }) => {
  const latest = await (await request.get("data/ms/latest.json")).json();
  const heading = (p: typeof page) => p.getByRole("heading", { name: "Warm-water bacteria (Vibrio)" });
  await page.goto("for/shrimp/");
  await expect(heading(page)).toHaveCount(0);
  if (!latest.vibrio) {           // cooler months: no station in range, so nothing is said anywhere
    await page.goto("");
    await expect(heading(page)).toHaveCount(0);
    return;
  }
  for (const path of ["", "for/oyster/", "for/fish/"]) {
    await page.goto(path);
    const sec = page.locator("section.vibrio");
    await expect(heading(page)).toBeVisible();
    await expect(sec).toContainText(`Water at ${latest.vibrio.places} is warm`);
    await expect(sec).not.toContainText(/flesh|closed|danger/i);
    await expect(sec.getByRole("link", { name: "Mississippi State Department of Health" })).toHaveAttribute("href", /msdh\.ms\.gov/);
    await expect(sec.getByRole("link", { name: "CDC" })).toHaveAttribute("href", /cdc\.gov\/vibrio/);
  }
});

test("the tide strip under the map says which way the tide is heading and when it next turns", async ({ page, request }) => {
  const latest = await (await request.get("data/ms/latest.json")).json();
  test.skip(!latest.tide_strip, "no fresh tide predictions in this build");
  const [, next, after] = latest.tide_strip.events;
  await page.clock.setFixedTime(new Date(Date.parse(next.time) - 60 * 60_000));   // an hour before a turn
  await page.goto("");
  const strip = page.locator("section.tide");
  await expect(strip).toContainText(`Tide, ${latest.tide_strip.name}`);
  const ft = (v: number) => `${v < 0 ? "−" : ""}${Math.abs(v).toFixed(1)} ft`;
  await expect(strip.locator(".tide-say")).toContainText(`${next.type === "high" ? "Rising" : "Falling"}: ${next.type} ${ft(next.ft)} at`);
  if (after) await expect(strip.locator(".tide-say")).toContainText(`then ${after.type} ${ft(after.ft)}`);
  await expect(strip.getByRole("link", { name: /at NOAA$/ })).toHaveAttribute("href", new RegExp(`id=${latest.tide_strip.station}`));
});

test("a beach link from the map opens the full beach list to that beach", async ({ page, request }) => {
  const latest = await (await request.get("data/ms/latest.json")).json();
  const clear = latest.beaches?.stations.find((s: { status: string }) => s.status === "clear");
  test.skip(!clear, "no clear beach in this build");
  await page.goto(`#beach-${clear.id}`);
  await expect(page.locator("details.beach-all")).toHaveAttribute("open", "");
  await expect(page.locator(`#beach-${clear.id}`)).toBeVisible();
  await expect(page.locator(`#beach-${clear.id}`)).toContainText(clear.name);
});

test("the oyster section lists MDMR's own season notices, newest first, with links to the full notice", async ({ page, request }) => {
  const latest = await (await request.get("data/ms/latest.json")).json();
  const w = latest.oyster_watch;
  test.skip(!w || w.notices_available === undefined, "no oyster watch in this build");
  await page.goto("for/oyster/");
  const sec = page.locator("section.oyster-watch");
  await expect(sec.getByRole("heading", { name: "Latest from MDMR" })).toBeVisible();
  if (!w.notices_available) return await expect(sec).toContainText("couldn't be checked");
  if (!w.notices.length) return await expect(sec).toContainText("No oyster season notices from MDMR in the past year");
  const first = sec.locator("ol.notices li").first();
  await expect(first.getByRole("link", { name: w.notices[0].title })).toHaveAttribute("href", /dmr\.ms\.gov/);
});

test("river flow shows on phones as a strip under the map", async ({ page, request }, info) => {
  const latest = await (await request.get("data/ms/latest.json")).json();
  const river = latest.cards.find((c: { kind: string; minor?: boolean }) => c.kind === "river" && !c.minor);
  await page.goto("");
  const [strip, panel] = [page.locator(".map-rivers-row"), page.locator(".map-rivers")];
  await expect(info.project.name === "phone" ? strip : panel).toContainText(river.short ?? river.name, { timeout: 20_000 });
  await expect(info.project.name === "phone" ? panel : strip).toBeHidden();
});

test("Dauphin Island shows at the map's east edge as a labeled reference, not a station", async ({ page, request }, info) => {
  const latest = await (await request.get("data/ms/latest.json")).json();
  const ref = latest.reference?.find((r: { salinity: number | null }) => r.salinity !== null);
  test.skip(!ref, "no fresh reference reading in this build");
  await page.goto("");
  const chip = page.locator(info.project.name === "phone" ? ".map-ref-row" : ".map-ref");
  await expect(chip).toContainText(`${ref.salinity.toFixed(1)} ppt`, { timeout: 20_000 });
  await expect(chip).toContainText(`Reference, ${ref.km} km east of ${ref.nearest}`);
});
