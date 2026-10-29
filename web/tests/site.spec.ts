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
  // With the river low and nothing open, the section is one line and the rest opens on request (0036).
  const more = sec.locator("details.spill-more");
  if (await more.count()) {
    await expect(sec.locator(".spill-calm")).toContainText("ft on the Mississippi");
    await expect(sec.locator(".spill-timeline")).toBeHidden();
    await more.locator("summary").click();
  }
  await expect(sec.getByRole("img", { name: /Spillway openings by year: 1937/ })).toBeVisible();
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

test("every page has a share image that exists and is 1200x630", async ({ page, request }) => {
  for (const path of PAGES) {
    await page.goto(path);
    const og = await page.locator('meta[property="og:image"]').getAttribute("content");
    expect(og, path).toMatch(/\/og\/[\w-]+\.png\?v=\d{12}$/);
    await expect(page.locator('meta[name="twitter:card"]')).toHaveAttribute("content", "summary_large_image");
    // The image's path already includes the base path (/ms-sound-check/ in CI), so resolve it from the server root.
    const res = await request.get(new URL(new URL(og!).pathname, page.url()).href);
    expect(res.status(), og!).toBe(200);
    const png = await res.body();
    expect([png.readUInt32BE(16), png.readUInt32BE(20)], og!).toEqual([1200, 630]);   // IHDR width, height
  }
});

test("salinity history: home section, table alternative, and a picked year on the station chart", async ({ page }) => {
  await page.goto("");
  const home = page.locator("section", { has: page.locator("#g-history") });
  await expect(home.getByRole("heading", { name: /years of the Sound/ })).toBeVisible();
  await expect(home.locator("canvas.stripes-canvas")).toHaveCount(1);   // one picture on home; the rest are linked (0036)
  await expect(home.locator(".history-more").getByRole("link").first()).toHaveAttribute("href", /station\/[\w-]+\/#history$/);
  await page.goto("station/west-sound/#year-2019");
  const hist = page.locator("#history");
  await expect(hist.getByRole("combobox")).toHaveValue("2019");
  await hist.getByText("Show as table").click();
  await expect(hist.getByRole("rowheader", { name: "2019" })).toBeVisible();
  await page.locator(".chart-box").scrollIntoViewIfNeeded();
  await expect(page.locator(".chart-note").first()).toContainText("2019 on the same dates");
  for (const scheme of ["light", "dark"] as const) {
    await page.emulateMedia({ colorScheme: scheme, reducedMotion: "reduce" });   // no mid-transition colors for axe
    const axe = await new AxeBuilder({ page }).include("#history").withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze();
    expect(axe.violations.filter((v) => v.impact === "serious" || v.impact === "critical"), scheme).toEqual([]);
  }
});

test("years like this one: the river section names past years, each linking to that year on the history picture", async ({ page }) => {
  await page.goto("");
  const line = page.locator(".similar-years");
  test.skip(!(await line.count()), "no close match in the current data");
  await expect(line).toContainText("not a forecast");
  const link = line.getByRole("link").first();
  const year = (await link.textContent())!.trim();
  await link.click();
  await expect(page.locator("#history").getByRole("combobox")).toHaveValue(year);
});

test("the weekly digest feed is valid RSS and every page links to it", async ({ page, request }) => {
  await page.goto("");
  const feed = await page.locator('link[rel="alternate"][type="application/rss+xml"]').getAttribute("href");
  const res = await request.get(feed!);
  expect(res.status()).toBe(200);
  expect(res.headers()["content-type"]).toMatch(/xml/);   // static hosts serve .xml as text/xml; readers accept it
  const xml = await res.text();
  expect(xml).toContain("<rss version=\"2.0\">");
  expect(xml).toContain("Not for navigation or harvest decisions");
});

// ---------- Showing the Sound (decisions 0032-0035)

test("the home history pictures draw once scrolled to, keep partial years apart, and a tapped day links onward", async ({ page }) => {
  await page.goto("");
  const canvases = page.locator("section:has(#g-history) canvas.stripes-canvas");
  await expect(canvases).toHaveCount(1);
  for (const c of await canvases.all()) {
    await c.scrollIntoViewIfNeeded();
    await expect(c).toHaveAttribute("data-drawn", "", { timeout: 10_000 });   // client:visible fired and it drew
  }
  const first = canvases.first();
  const box = (await first.boundingBox())!;
  await first.click({ position: { x: box.width * 0.4, y: 8 } });           // a day in the first counted year
  const links = page.locator("section:has(#g-history) .stripes-links").first();
  await expect(links.getByRole("link", { name: /^\d{4} at / })).toHaveAttribute("href", /station\/[\w-]+\/#year-\d{4}$/);
  await expect(links.getByRole("link", { name: /on the map$/ })).toHaveAttribute("href", /#\d{4}-\d{2}-\d{2}$/);
});

test("year dots on a station page agree with its record line", async ({ page, request }) => {
  const latest = await (await request.get("data/ms/latest.json")).json();
  const card = latest.cards.find((c: any) => Object.values(c.vars).some((r: any) => r.years) && !c.retired);
  test.skip(!card, "no ranked reading in this build");
  const [vn, r] = Object.entries(card.vars).find(([, r]: any) => r.years) as [string, any];
  await page.goto(`station/${card.slug}/`);
  const dots = page.locator(".now .yeardots");
  await expect(dots.locator("circle")).toHaveCount(r.years.of);
  const high = r.years.rank_high <= r.years.rank_low, rank = high ? r.years.rank_high : r.years.rank_low;
  await expect(dots.locator(".yd-say")).toContainText(`${high ? "highest" : "lowest"} of ${r.years.of} years`);
  const f = latest.findings.find((f: any) => f.site === card.id && f.var === vn && f.rank);
  if (f) expect(f.rank).toBe(rank);                       // the picture and the sentence say the same thing
  await dots.locator("circle").first().hover();
  await expect(dots.locator(".yd-read")).toHaveText(/^\d{4}: /);
});

test("the long replay opens a #YYYY-MM-DD day, jumps to notable days and returns to the last 30 days", async ({ page, request }) => {
  const latest = await (await request.get("data/ms/latest.json")).json();
  test.skip(!latest.replay_index?.years.includes(2019), "no 2019 replay in this build");
  await page.goto("#2019-05-10");
  const day = page.locator(".replay-day");
  await expect(day).toHaveText("May 10, 2019", { timeout: 20_000 });
  await expect(page.locator(".replay").getByRole("combobox", { name: "Year" })).toHaveValue("2019");
  await expect(page.locator(".replay [aria-live]")).toContainText("May 10, 2019:");
  await page.locator(".replay").getByRole("combobox", { name: "Month" }).selectOption({ label: "Aug" });
  await expect(day).toHaveText("Aug 1, 2019");
  await expect(page).toHaveURL(/#2019-08-01$/);
  const katrina = latest.replay_index.shortcuts.find((s: any) => s.label === "Katrina");
  if (katrina) {
    await page.locator(".replay").getByRole("combobox", { name: "Jump to" }).selectOption(katrina.date);
    await expect(day).toHaveText("Aug 29, 2005");
  }
  await page.locator(".replay").getByRole("combobox", { name: "Year" }).selectOption({ label: "Last 30 days" });
  await expect(day).toHaveText("Today");
  await expect(page).not.toHaveURL(/#\d{4}-/);
});

test("the Fishing map shows wind, labeled as wind and not a current, and reduced motion still works", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("for/fish/");
  const panel = page.locator(".map-layers");
  if (!(await panel.evaluate((d: HTMLDetailsElement) => d.open))) await panel.locator("summary").click();
  const wind = panel.getByRole("checkbox", { name: "Wind" });
  await expect(wind).toBeEnabled({ timeout: 20_000 });
  await expect(wind).toBeChecked();
  await expect(panel).toContainText("Not a water current.");
  await expect(page.locator("canvas.map-wind")).toBeAttached();
});

test("home: headline, then map, then Signals in the DOM, and one instrument table for the readings", async ({ page }) => {
  await page.goto("");
  const order = await page.locator(".console > *").evaluateAll((els) => els.map((e) => e.className.split(" ")[0]));
  expect(order).toEqual(["brief", "sound", "rail"]);
  const table = page.locator("table.instr");
  await expect(table).toHaveCount(1);
  await expect(table.getByRole("columnheader", { name: "Out in the Sound" })).toBeVisible();
  await expect(page.locator(".cards")).toHaveCount(0);
  for (const scheme of ["light", "dark"] as const) {
    await page.emulateMedia({ colorScheme: scheme, reducedMotion: "reduce" });   // no mid-transition colors for axe
    const axe = await new AxeBuilder({ page }).include(".instruments").include(".replay").withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze();
    expect(axe.violations.filter((v) => v.impact === "serious" || v.impact === "critical"), scheme).toEqual([]);
  }
});

// ---------- The Sound west to east (decision 0037)

test("the Sound west to east: stations in order, named and linked, with a text version of the bars", async ({ page, request }) => {
  const latest = await (await request.get("data/ms/latest.json")).json();
  await page.goto("");
  const sec = page.locator("section.strip");
  await expect(sec.getByRole("heading", { name: "The Sound, west to east" })).toBeVisible();
  const bars = sec.getByRole("img", { name: /^Salinity from west to east: / });
  await expect(bars).toBeVisible();
  // Every salinity station on the map is named, west to east, in the text version.
  const shown = latest.cards.filter((c: any) => ["sound", "estuary"].includes(c.kind) && c.vars.salinity && !(c.retired && !c.vars.salinity.estimate))
    .sort((a: any, b: any) => a.lon - b.lon).map((c: any) => c.short);
  const text = (await bars.getAttribute("aria-label"))!;
  expect(shown.map((s: string) => text.indexOf(s))).toEqual(shown.map((s: string) => text.indexOf(s)).sort((a: number, b: number) => a - b));
  for (const s of shown) await expect(sec.locator(".strip-label").getByRole("link", { name: s, exact: true })).toHaveAttribute("href", /station\/[\w-]+\/$/);
  for (const scheme of ["light", "dark"] as const) {
    await page.emulateMedia({ colorScheme: scheme, reducedMotion: "reduce" });
    const axe = await new AxeBuilder({ page }).include("section.strip").withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze();
    expect(axe.violations.filter((v) => v.impact === "serious" || v.impact === "critical"), scheme).toEqual([]);
  }
});

test("the Oysters share image is the strip, at 1200x630", async ({ request }) => {
  const res = await request.get("og/oyster.png");
  expect(res.status()).toBe(200);
  const png = await res.body();
  expect([png.readUInt32BE(16), png.readUInt32BE(20)]).toEqual([1200, 630]);
});
