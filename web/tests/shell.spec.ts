// The app's frame on every page (seam 4, ticket 06): the navy bar with the World Bank logo, the
// band with the box and the data-freshness stamp in its five states, the page alerts, and the
// footer, against the mocked API. The words are the 06 design brief's.
import { createHash } from "node:crypto";
import type { Page } from "@playwright/test";
import { expect, mockShell, recorded, test } from "./mocked";

// web/src/assets/world-bank-logo.md: the official file's hash when it was downloaded.
const LOGO_SHA256 = "c11d30bf69ad0f6f224b350e93ea976bbac438ff18c82786d1c11454a0317aff";

// The stamp writes "Oct 21" in the current year, so the tests fix today.
const TODAY = new Date("2026-10-24T12:00:00Z");

// The Packages tab lists the viewer's packages and checked plans (ticket 15). An empty list keeps the tab's
// own alert, for a list it could not load, out of the page's alerts that these tests count.
async function noPlannedPackages(page: Page) {
  await page.route("**/api/planned-packages", async (route) =>
    route.fulfill({ contentType: "application/json", body: await recorded("planned-packages-empty.json") }),
  );
}

test("the navy bar carries the official World Bank Group logo, unaltered, 24 px tall with clear space of half its height", async ({ page }) => {
  await mockShell(page);
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");

  // worldbank.org's white mark is the World Bank Group logo, so its text alternative names the Group.
  const logo = page.getByRole("img", { name: "World Bank Group logo" });
  await expect(logo).toBeVisible();
  const file = await page.request.get(await logo.evaluate((img) => (img as HTMLImageElement).currentSrc));
  const body = await file.body();
  expect(createHash("sha256").update(body).digest("hex")).toBe(LOGO_SHA256);
  // White artwork, the file for dark backgrounds, so it reads on the navy bar.
  expect(new Set(body.toString().match(/fill="[^"]*"/g))).toEqual(new Set(['fill="#fff"', 'fill="none"']));
  // The logo is not a link.
  await expect(page.locator("a").filter({ has: logo })).toHaveCount(0);

  const bar = (await page.locator("[data-nav-bar]").boundingBox())!;
  const box = (await logo.boundingBox())!;
  const wordmark = (await page.getByRole("link", { name: "Strata", exact: true }).boundingBox())!;
  expect([box.width, box.height]).toEqual([120, 24]);
  expect(box.y - bar.y).toBeGreaterThanOrEqual(12);
  expect(bar.y + bar.height - (box.y + box.height)).toBeGreaterThanOrEqual(12);
  // Ticket 93: the bar starts 16 px from the window's edge, beside the sidebar's icons.
  expect(Math.round(box.x)).toBe(16);
  // 24 px to the wordmark, so the logo and "Strata" never read as one co-branded name.
  expect(wordmark.x - (box.x + box.width)).toBeGreaterThanOrEqual(24);
});

test("one banner holds the search landmark around the box and the view switch, and no section link or stamp", async ({ page }) => {
  await mockShell(page);
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");

  const banner = page.getByRole("banner");
  await expect(banner).toHaveCount(1);
  await expect(banner.getByRole("search")).toHaveCount(1);
  await expect(banner.getByRole("button", { name: "View: World Bank staff" })).toBeVisible();
  // Ticket 93: the stamp moved to the sidebar's foot.
  await expect(banner.locator("[data-stamp]")).toHaveCount(0);
  // Ticket 92: the sections left the bar for the sidebar beside the page.
  await expect(banner.getByRole("navigation")).toHaveCount(0);
  await expect(banner.getByRole("link", { name: /^(Home|Packages|Projects|Lessons|Drafts|Data)$/ })).toHaveCount(0);
});

// Ticket 93 (DESIGN.md section 5, Top bar): from 1024 px one 56 px navy row that sticks: the logo, the wordmark, the
// box from the page's content edge (224 + 40 px) beside the open sidebar, or from 244 px beside the rail, at most 640 px
// wide, and the view switch ending 24 px from the right edge. No white band sits under it.
test("from 1024 px the bar is one 56 px navy row that sticks, with the box from 264 px beside the open sidebar and 244 px beside the rail", async ({ page }) => {
  await mockShell(page);
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  const at = async (selector: string) => (await page.locator(selector).boundingBox())!;

  for (const [width, left] of [[1440, 264], [1280, 244], [1024, 244]]) {
    await page.setViewportSize({ width, height: 900 });
    const bar = await at("[data-nav-bar]");
    expect([bar.x, bar.y, bar.width, bar.height], `${width} px`).toEqual([0, 0, width, 56]);
    expect(await page.locator("[data-nav-bar]").evaluate((el) => getComputedStyle(el).backgroundColor)).toBe("rgb(0, 34, 68)");
    // The header is the bar alone.
    expect((await at("header")).height, `${width} px`).toBe(56);
    const logo = await at("[data-nav-bar] img");
    expect([logo.width, logo.height], `${width} px`).toEqual([120, 24]);
    const box = await at("[data-box-band] form > [data-focus-ring]");
    expect(Math.round(box.x), `${width} px: the box's left edge`).toBe(left);
    expect(box.width, `${width} px`).toBeLessThanOrEqual(640);
    expect(Math.round(box.y + box.height / 2), `${width} px: the box sits on the bar's row`).toBe(28);
    const pill = await at("[data-view-pill]");
    expect(Math.round(width - (pill.x + pill.width)), `${width} px: the view switch's right edge`).toBe(24);
    expect(pill.x, `${width} px`).toBeGreaterThanOrEqual(box.x + box.width + 24);
  }
  expect((await at("[data-box-band] form > [data-focus-ring]")).width).toBeLessThan(640);
  await page.setViewportSize({ width: 1440, height: 900 });
  expect((await at("[data-box-band] form > [data-focus-ring]")).width).toBe(640);

  // It sticks: scrolled down, the bar stays at the top of the window.
  await page.addStyleTag({ content: "main { min-height: 3000px; }" });
  await page.evaluate(() => window.scrollTo(0, 600));
  await expect.poll(() => page.evaluate(() => window.scrollY)).toBe(600);
  expect((await at("[data-nav-bar]")).y).toBe(0);
  // Below 1024 px it scrolls away with the page, so a phone keeps its screen for the page.
  await page.setViewportSize({ width: 800, height: 900 });
  await page.evaluate(() => window.scrollTo(0, 600));
  await expect.poll(() => page.evaluate(() => window.scrollY)).toBe(600);
  expect((await at("[data-nav-bar]")).y).toBeLessThan(0);
});

// Ticket 93 (DESIGN.md section 10): the focused skip link shows below the bar, over the page, so it covers neither the
// logo nor the wordmark.
test("the focused skip link shows below the bar, over the page, and covers neither the logo nor the wordmark", async ({ page }) => {
  await mockShell(page);
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/");
    await expect(page.locator("main h1")).toBeVisible();
    await page.keyboard.press("Tab");
    const skip = page.getByRole("link", { name: "Skip to main content", exact: true });
    await expect(skip).toBeFocused();
    const link = (await skip.boundingBox())!;
    const bar = (await page.locator("[data-nav-bar]").boundingBox())!;
    expect(link.y, `${width} px`).toBeGreaterThanOrEqual(bar.y + bar.height);
    for (const part of [page.locator("[data-nav-bar] img"), page.getByRole("link", { name: "Strata", exact: true })]) {
      const box = (await part.boundingBox())!;
      const overlaps = link.x < box.x + box.width && box.x < link.x + link.width && link.y < box.y + box.height && box.y < link.y + link.height;
      expect(overlaps, `${width} px`).toBe(false);
    }
  }
});

// Ticket 92 (DESIGN.md section 5, Sidebar): from 1024 px the sections are a sidebar named "Main" beside the page, open
// at 224 px from 1440 px and a 64 px rail of icons from 1024 to 1439 px by default, Home first and each section once.
test("from 1024 px the sidebar named Main sits beside the page, 224 px wide from 1440 px and a 64 px rail below, Home first", async ({ page }) => {
  await mockShell(page);
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");

  const main = page.getByRole("navigation", { name: "Main" });
  for (const [width, wide] of [[1440, 224], [1280, 64], [1024, 64]]) {
    await page.setViewportSize({ width, height: 900 });
    await expect(main.locator("[data-nav-item]"), `${width} px`).toHaveText(["Home", "Packages", "Projects", "Lessons", "Drafts", "Data"]);
    const sidebar = (await page.locator("[data-sidebar-column]").boundingBox())!;
    const column = (await page.locator("[data-page-column]").boundingBox())!;
    expect([sidebar.x, sidebar.width, column.x], `${width} px`).toEqual([0, wide, wide]);
    await expect(main.getByRole("link", { name: "Home" }), `${width} px`).toHaveAttribute("aria-current", "page");
    await expect(main.locator("[aria-current]"), `${width} px`).toHaveCount(1);
  }
});

// The current item is matchRoute's section: "page" on the page the item opens, "true" on a page inside its section.
test("the current item says page on the section's own page and true on a page inside it", async ({ page }) => {
  await mockShell(page);
  await noPlannedPackages(page);
  await page.setViewportSize({ width: 1440, height: 900 });
  const main = page.getByRole("navigation", { name: "Main" });
  for (const [path, item, current] of [
    ["/packages", "Packages", "page"],
    ["/lessons/review", "Lessons", "true"],
    // Data sits at the sidebar's foot.
    ["/data/sources", "Data", "true"],
  ]) {
    await page.goto(path);
    await expect(main.getByRole("link", { name: item, exact: true }), path).toHaveAttribute("aria-current", current);
    await expect(main.locator("[aria-current]"), path).toHaveCount(1);
  }
});

// "Collapse the sidebar" and "Expand the sidebar" are one button (DESIGN.md section 5, Sidebar). The width changes at
// once: it is final in the same frame as the press, and nothing on the sidebar transitions its width.
test("Collapse the sidebar turns it into the rail and Expand the sidebar back, at once, and the choice survives a reload", async ({ page }) => {
  await mockShell(page);
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  const column = page.locator("[data-sidebar-column]");
  const toggle = page.locator("[data-sidebar-toggle]");
  await expect(toggle).toHaveAccessibleName("Collapse the sidebar");
  await expect(toggle).toHaveAttribute("aria-expanded", "true");

  await toggle.focus();
  const pressed = await column.evaluate((el) => {
    const moves = [el, ...el.querySelectorAll<HTMLElement>("[data-sidebar], nav")].flatMap((part) => {
      const style = getComputedStyle(part);
      const names = style.transitionProperty.split(",").map((name) => name.trim());
      const times = style.transitionDuration.split(",").map((time) => parseFloat(time));
      return names.filter((name, index) => ["all", "width", "min-width", "max-width", "flex-basis"].includes(name) && (times[index] ?? times[0]) > 0);
    });
    el.querySelector<HTMLButtonElement>("[data-sidebar-toggle]")!.click();
    return { moves, width: el.getBoundingClientRect().width };
  });
  expect(pressed).toEqual({ moves: [], width: 64 });
  await expect(toggle).toHaveAccessibleName("Expand the sidebar");
  await expect(toggle).toHaveAttribute("aria-expanded", "false");
  await expect(toggle).toBeFocused();

  await page.reload();
  await expect(page.locator("main h1")).toBeVisible();
  expect((await column.boundingBox())!.width).toBe(64);
  await toggle.click();
  expect((await column.boundingBox())!.width).toBe(224);
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.reload();
  await expect(toggle).toHaveAccessibleName("Collapse the sidebar");
  expect((await column.boundingBox())!.width).toBe(224);
});

// A rail item's label shows in a tooltip on hover and on keyboard focus; the name stays in the link, so the tooltip
// is hidden from screen readers. The open sidebar shows its labels and no tooltip.
test("each rail item's tooltip shows its label on hover and on keyboard focus", async ({ page }) => {
  await mockShell(page);
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto("/");
  const main = page.getByRole("navigation", { name: "Main" });
  const tip = page.locator("[data-rail-tip]");

  const lessons = main.getByRole("link", { name: "Lessons" });
  await lessons.hover();
  await expect(tip).toHaveText("Lessons");
  await expect(tip).toHaveAttribute("aria-hidden", "true");
  const [item, label] = [(await lessons.boundingBox())!, (await tip.boundingBox())!];
  expect(label.x).toBeGreaterThan(item.x + item.width);
  expect(Math.round(label.y + label.height / 2)).toBe(Math.round(item.y + item.height / 2));
  await page.mouse.move(800, 600);
  await expect(tip).toHaveCount(0);

  await lessons.focus();
  await page.keyboard.press("Tab");
  await expect(main.getByRole("link", { name: "Drafts" })).toBeFocused();
  await expect(tip).toHaveText("Drafts");
  await page.keyboard.press("Tab");
  await page.keyboard.press("Tab");
  await expect(page.locator("[data-sidebar-toggle]")).toBeFocused();
  await expect(tip).toHaveText("Expand the sidebar");

  await page.setViewportSize({ width: 1440, height: 900 });
  await expect(tip).toHaveCount(0);
  await lessons.hover();
  await page.waitForTimeout(200);
  await expect(tip).toHaveCount(0);
});

// Ticket 92: web/index.html's first script reads the stored choice, and its style paints the sidebar's frame at that
// width, or the width's default, before the app's script runs. The app's bundle is held back here, so the page shows
// only what index.html paints; below 1024 px no sidebar is painted and the closed Menu sheet is not shown. Ticket 93:
// the bar holds the box, one 56 px row from 1024 px and two rows below, with the logo after the Menu button.
test("the first paint holds the bar, the logo and the sidebar where the app puts them, before the app's script runs", async ({ browser, page }) => {
  const boxes = (selectors: string[]) =>
    selectors.map((selector) => {
      const element = document.querySelector(selector);
      if (!element?.checkVisibility({ visibilityProperty: true })) return null;
      const box = element.getBoundingClientRect();
      return [Math.round(box.x), Math.round(box.y), Math.round(box.width), Math.round(box.height)];
    });
  await mockShell(page);
  await page.goto("/");
  const cases: [number, string | null][] = [[1440, null], [1280, null], [1280, "open"], [1440, "rail"], [800, null], [390, null]];
  for (const [width, stored] of cases) {
    const first = await browser.newContext({ viewport: { width, height: 900 } });
    if (stored) await first.addInitScript((rest) => window.localStorage.setItem("strata.sidebar", rest), stored);
    await first.route(/\/assets\/.+\.js$/, (route) => route.abort());
    const before = await first.newPage();
    await before.goto(test.info().project.use.baseURL!);
    const painted = await before.evaluate(boxes, ["[data-boot-bar]", "[data-boot-bar] img", "[data-boot-sidebar]"]);
    await first.close();

    await page.evaluate((rest) => (rest ? window.localStorage.setItem("strata.sidebar", rest) : window.localStorage.clear()), stored);
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/");
    await expect(page.locator("main h1")).toBeVisible();
    const mounted = await page.evaluate(boxes, ["[data-nav-bar]", "[data-nav-bar] img", "[data-sidebar]"]);

    expect(painted, `${width} px, stored ${stored}`).toEqual(mounted);
    expect(mounted[2] === null, `${width} px`).toBe(width < 1024);
    expect(mounted[0]![3], `${width} px: the bar's height`).toBe(width < 1024 ? 108 : 56);
  }
});

// Ticket 93 (DESIGN.md section 5, Freshness stamp): the stamp sits at the sidebar's foot, under Data, on its label's
// left edge, in a 24 px line box. The stamp's tests open the sidebar at 1440 px, where its five states show.
test("the stamp sits at the sidebar's foot under Data, shows the day the server returns, and links to the Data page", async ({ page }) => {
  await page.clock.setFixedTime(TODAY);
  await mockShell(page);
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");

  const stamp = page.locator("[data-stamp]").getByRole("link");
  await expect(stamp).toHaveText("Data through Oct 23");
  await expect(stamp).toHaveAttribute("href", "/data");
  await expect(stamp).toHaveAccessibleDescription("Open the Data page.");
  await expect(page.locator("[data-stamp]")).not.toHaveAttribute("aria-busy");
  // The stamp's description is read once, through aria-describedby, and never as page text.
  await expect(page.getByText("Open the Data page.")).toBeHidden();

  const main = page.getByRole("navigation", { name: "Main" });
  await expect(main.locator("[data-stamp]")).toHaveCount(1);
  const label = (await main.locator("[data-nav-item=data] span").boundingBox())!;
  const line = (await page.locator("[data-stamp]").boundingBox())!;
  const toggle = (await page.locator("[data-sidebar-toggle]").boundingBox())!;
  expect(Math.round(line.x)).toBe(Math.round(label.x));
  expect(line.y).toBeGreaterThanOrEqual(label.y + label.height);
  expect(line.y + line.height).toBeLessThanOrEqual(toggle.y);
  expect(line.height).toBe(24);
});

// As a rail, the sidebar hides the stamp, and the Data item's tooltip and its description say the stamp's words.
test("as a rail, the sidebar hides the stamp, and the Data item's tooltip and description carry its words", async ({ page }) => {
  await page.clock.setFixedTime(TODAY);
  await mockShell(page);
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto("/");

  await expect(page.locator("[data-stamp]")).toBeHidden();
  const data = page.getByRole("navigation", { name: "Main" }).getByRole("link", { name: "Data", exact: true });
  await data.focus();
  await expect(page.locator("[data-rail-tip]")).toHaveText("DataData through Oct 23");
  await expect(data).toHaveAccessibleDescription("Data through Oct 23");
  await page.locator("[data-sidebar-toggle]").click();
  await expect(data).not.toHaveAttribute("aria-describedby");
  await expect(page.locator("[data-stamp]").getByRole("link")).toBeVisible();
});

test("a data date from another year shows its year", async ({ page }) => {
  await page.clock.setFixedTime(TODAY);
  await mockShell(page, { freshness: { body: '{"data_through": "2025-12-30"}' } });
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");

  await expect(page.locator("[data-stamp]").getByRole("link")).toHaveText("Data through Dec 30, 2025");
});

test("before any daily source has loaded, the stamp says no data are loaded and still links to the Data page", async ({ page }) => {
  await mockShell(page, { freshness: { body: await recorded("freshness-empty.json") } });
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");

  await expect(page.locator("[data-stamp]").getByRole("link")).toHaveText("No data loaded yet");
  await expect(page.locator("[data-stamp]").getByRole("link")).toHaveAttribute("href", "/data");
});

test("while it loads, the stamp holds a static bar for the first second and then says it is reading the date", async ({ page }) => {
  await mockShell(page);
  let answer: () => void = () => {};
  const answered = new Promise<void>((resolve) => (answer = resolve));
  await page.route("**/api/freshness", async (route) => {
    await answered;
    await route.fulfill({ status: 200, contentType: "application/json", body: await recorded("freshness.json") });
  });
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");

  const stamp = page.locator("[data-stamp]");
  await expect(stamp).toHaveAttribute("aria-busy", "true");
  await expect(stamp.locator("[data-skeleton]")).toHaveCount(1);
  await expect(stamp).toHaveText("Reading the data date", { timeout: 3000 });
  answer();
  await expect(stamp.getByRole("link")).toHaveText(/^Data through /);
});

test("when the server fails, the stamp says it can't read the date, and tries again on a later page at most once a minute", async ({ page }) => {
  await page.clock.install({ time: TODAY });
  await mockShell(page);
  let reads = 0;
  await page.route("**/api/freshness", async (route) => {
    reads += 1;
    if (reads === 1) return route.fulfill({ status: 502, contentType: "application/json", body: '{"code": "unreadable"}' });
    return route.fulfill({ status: 200, contentType: "application/json", body: await recorded("freshness.json") });
  });
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");

  const stamp = page.locator("[data-stamp]");
  await expect(stamp).toHaveText("I can't read the data date.");
  await expect(stamp.getByRole("link")).toHaveCount(0);
  await expect(stamp.locator("svg.lucide-circle-x")).toHaveCount(1);

  const tabs = page.getByRole("navigation", { name: "Main" });
  await tabs.getByRole("link", { name: "Packages" }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Packages");
  expect(reads).toBe(1);

  await page.clock.fastForward("01:01");
  await tabs.getByRole("link", { name: "Projects" }).click();
  await expect(stamp.getByRole("link")).toHaveText("Data through Oct 23");
  expect(reads).toBe(2);
});

test("an account the warehouse refuses gets one error alert that says how to get access", async ({ page }) => {
  await mockShell(page, { freshness: { status: 403, body: await recorded("freshness-no-access.json") } });
  await noPlannedPackages(page);
  await page.goto("/packages");

  await expect(page.getByRole("alert")).toHaveText(
    "Your account can't read the data I hold yet; ask the person who shared Strata with you for access.",
  );
  await expect(page.locator("[data-stamp]")).toHaveText("I can't read the data date.");
});

test("while the stamp tries again, the access alert stays where it is, so it is not announced twice", async ({ page }) => {
  await page.clock.install({ time: TODAY });
  await mockShell(page);
  // The Packages tab lists the viewer's packages (ticket 15); an empty list keeps its own alert out of the count.
  await page.route("**/api/planned-packages", async (route) =>
    route.fulfill({ contentType: "application/json", body: await recorded("planned-packages-empty.json") }),
  );
  let reads = 0;
  let answer: () => void = () => {};
  const answered = new Promise<void>((resolve) => (answer = resolve));
  await page.route("**/api/freshness", async (route) => {
    reads += 1;
    if (reads > 1) await answered;
    await route.fulfill({ status: 403, contentType: "application/json", body: await recorded("freshness-no-access.json") });
  });
  await page.goto("/");
  const alert = page.getByRole("alert");
  await expect(alert).toHaveCount(1);

  await page.clock.fastForward("01:01");
  await page.getByRole("navigation", { name: "Main" }).getByRole("link", { name: "Packages" }).click();

  await expect(page.locator("[data-stamp]")).toHaveText("Reading the data date");
  await expect(alert).toHaveCount(1);
  answer();
  await expect(page.locator("[data-stamp]")).toHaveText("I can't read the data date.");
  await expect(alert).toHaveCount(1);
  expect(reads).toBe(2);
});

test("with no forwarded identity, one error alert says to open Strata from its link in the workspace", async ({ page }) => {
  await mockShell(page, {
    me: { body: '{"email": null, "name": null, "signed_in": false, "has_token": false}' },
    freshness: { status: 401, body: await recorded("freshness-no-identity.json") },
  });
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");

  await expect(page.getByRole("alert")).toHaveText(
    "I can't tell who you are, so I can't read any data; open Strata from its link in the workspace.",
  );
  await page.getByRole("button", { name: "View: World Bank staff" }).click();
  await expect(page.getByRole("dialog", { name: "Your view" })).toContainText("You are not signed in.");
});

test("the view popover says who is signed in and offers each view as a link, with yours current", async ({ page }) => {
  await mockShell(page);
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");

  await page.getByRole("button", { name: "View: World Bank staff" }).click();

  // Who is viewing comes first, then the views as link rows and the past date (ticket 40), then the language of answers
  // and drafts (ticket 42).
  const dialog = page.getByRole("dialog", { name: "Your view" });
  await expect(dialog.locator("[data-view-popover] p").first()).toHaveText("Signed in as ana.example@worldbank.org");
  await expect(dialog.locator("[data-view-row]")).toHaveText([
    "World Bank staffYour own view, with everything I show.",
    "Implementing agency officerA preview of what an officer at the Northern Water Works Development Agency (NWWDA) sees.",
    "The publicA preview of what a member of the public sees. It has projects, lessons and data only.",
  ]);
  const own = dialog.getByRole("link", { name: "World Bank staff" });
  await expect(own).toHaveAttribute("aria-current", "true");
  await expect(own).toBeFocused();
  await expect(dialog.getByRole("link", { name: "The public" })).toHaveAttribute("href", "/?view=public");
  await expect(dialog.getByRole("group")).toHaveAccessibleName("Language of answers and drafts");
});

test("Tab in the view popover closes it and moves on to the sidebar; Shift+Tab closes it and returns to the view switch", async ({ page }) => {
  await mockShell(page);
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  const pill = page.getByRole("button", { name: "View: World Bank staff" });

  await pill.click();
  await expect(page.getByRole("dialog", { name: "Your view" })).toBeVisible();
  // Tab moves through the view rows, the past date and the language group (tickets 40 and 42); past the last control
  // it leaves the popover for what follows the view switch in the page: the box comes before it in the bar since
  // ticket 93, so that is the sidebar's first item.
  await expect(page.getByRole("link", { name: "World Bank staff" })).toBeFocused();
  for (let press = 0; press < 12 && (await page.getByRole("dialog").count()) > 0; press += 1) await page.keyboard.press("Tab");

  await expect(page.getByRole("navigation", { name: "Main" }).getByRole("link", { name: "Home" })).toBeFocused();
  await expect(page.getByRole("dialog")).toHaveCount(0);

  await pill.click();
  await expect(page.getByRole("dialog", { name: "Your view" })).toBeVisible();
  await page.keyboard.press("Shift+Tab");

  await expect(pill).toBeFocused();
  await expect(page.getByRole("dialog")).toHaveCount(0);
});

// The view switch's banners and the alerts for what the server could not apply (ticket 40; the 40 brief, 6.2 and 6.3).
const ADDRESS_ALERTS: [string, string][] = [
  ["?view=piu", "Preview of what an implementing agency officer at the Northern Water Works Development Agency (NWWDA) sees. You are still signed in as yourself."],
  ["?view=public", "Preview of what the public sees. You are still signed in as yourself."],
  ["?view=board", "I don't know the view in this link, so you are seeing the World Bank staff view."],
  ["?asof=2016-08-26", "I'm showing this page as of August 26, 2016. I use only what was disclosed by that date."],
  ["?asof=last-tuesday", "I can't read the date in this link, so you are seeing today's data."],
];

for (const [query, sentence] of ADDRESS_ALERTS) {
  test(`a link with ${query} says so above the title`, async ({ page }) => {
    await mockShell(page);
    await page.goto(`/${query}`);

    const alert = page.locator("[data-alert=info]");
    await expect(alert.locator("p").first()).toHaveText(sentence);
    const [alertBox, title] = [await alert.boundingBox(), await page.getByRole("heading", { level: 1 }).boundingBox()];
    expect(alertBox!.y).toBeLessThan(title!.y);
  });
}

test("a link with ?view=staff, ?lang= or ?evidence= shows no alert", async ({ page }) => {
  await mockShell(page);
  await noPlannedPackages(page);
  await page.goto("/packages?view=staff&lang=fr&evidence=ev-1");

  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Packages");
  // The page's alert slot stays empty; the evidence drawer beside the page answers ?evidence= itself.
  await expect(page.getByRole("main").locator("[data-alert]")).toHaveCount(0);
});

test("error alerts come before the address's info alerts", async ({ page }) => {
  await mockShell(page, { freshness: { status: 403, body: await recorded("freshness-no-access.json") } });
  await page.goto("/?view=public&asof=2016-08-26");

  await expect(page.locator("[data-alert]")).toHaveCount(3);
  await expect(page.locator("[data-alert]").first()).toHaveAttribute("data-alert", "error");
});

// Ticket 92: the Menu sheet opened from the keyboard puts focus on the current page's item, whose focus ring stays
// inside the sheet's scrolling list, so the list's edge never clips it.
test("a Menu sheet item's focus ring stays inside the sheet, so its edge never clips it", async ({ page }) => {
  await mockShell(page);
  await noPlannedPackages(page);
  await page.setViewportSize({ width: 390, height: 900 });
  await page.goto("/packages");
  await page.getByRole("button", { name: "Menu", exact: true }).focus();
  await page.keyboard.press("Enter");

  const row = page.getByRole("navigation", { name: "Main" }).getByRole("link", { name: "Packages" });
  await expect(row).toBeFocused();
  const ring = await row.evaluate((el) => {
    const style = getComputedStyle(el);
    const box = el.getBoundingClientRect();
    const list = el.closest("nav")!.getBoundingClientRect();
    const reach = parseFloat(style.outlineOffset) + parseFloat(style.outlineWidth);
    return { inside: box.left - reach >= list.left && box.right + reach <= list.right, style: style.outlineStyle };
  });
  expect(ring).toEqual({ inside: true, style: "solid" });
});

// An element's last line of text: how wide it is, as a share of the widest line, and how many words it holds.
const lastLine = (el: Element) => {
  const lines = new Map<number, { left: number; right: number; words: number }>();
  const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
  for (let node = walker.nextNode(); node; node = walker.nextNode()) {
    for (const word of node.textContent!.matchAll(/\S+/g)) {
      const range = document.createRange();
      range.setStart(node, word.index!);
      range.setEnd(node, word.index! + word[0].length);
      const box = range.getClientRects()[0];
      const top = Math.round(box.top);
      const line = lines.get(top) ?? { left: box.left, right: box.right, words: 0 };
      lines.set(top, { left: Math.min(line.left, box.left), right: Math.max(line.right, box.right), words: line.words + 1 });
    }
  }
  const sorted = [...lines.entries()].sort(([a], [b]) => a - b).map(([, line]) => line);
  const last = sorted[sorted.length - 1];
  const widest = Math.max(...sorted.map((line) => line.right - line.left));
  return { share: (last.right - last.left) / widest, words: last.words };
};

for (const width of [390, 320]) {
  test(`at ${width} px the Home card's title wraps into even lines, and the Menu's view line never ends on one word`, async ({ page }) => {
    // Home's first run (ticket 41): its empty-state card, as a viewer who follows nothing sees it.
    await mockShell(page, { home: { body: await recorded("home-first-run.json") } });
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/");

    const title = page.locator("[data-empty-state]").getByRole("heading");
    await expect(title).toHaveText("I brief you on the projects you follow.");
    expect((await title.evaluate(lastLine)).share).toBeGreaterThan(0.5);

    // The Menu's view rows wrap with text-pretty, so no description ends on one word (ticket 40).
    await page.getByRole("button", { name: "Menu", exact: true }).click();
    const view = page.locator("[data-menu-panel]").getByText("A preview of what a member of the public sees. It has projects, lessons and data only.");
    await expect(view).toBeVisible();
    expect((await view.evaluate(lastLine)).words).toBeGreaterThan(1);
  });
}

test("/ closes an open Menu and focuses the box", async ({ page }) => {
  await mockShell(page);
  await page.setViewportSize({ width: 390, height: 900 });
  await page.goto("/");
  await page.getByRole("button", { name: "Menu", exact: true }).click();
  // Focus is on the sheet's Home item, and the box behind the sheet is inert until the sheet closes.
  await expect(page.getByRole("dialog", { name: "Menu" }).getByRole("link", { name: "Home" })).toBeFocused();

  await page.keyboard.press("/");

  await expect(page.getByRole("button", { name: "Menu", exact: true })).toHaveAttribute("aria-expanded", "false");
  await expect(page.locator("[data-box-band]").getByRole("combobox")).toBeFocused();
});
