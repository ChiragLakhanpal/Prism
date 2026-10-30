// The app's frame on every page (seam 4, ticket 06): the navy bar with the World Bank logo, the
// band with the box and the data-freshness stamp in its five states, the page alerts, and the
// footer, against the mocked API. The words are the 06 design brief's.
import { createHash } from "node:crypto";
import type { Page } from "@playwright/test";
import { hubApi } from "./hub-api";
import { open as openAnswerPage } from "./answer-page";
import { expect, mockApi, mockShell, openSidebar, recorded, test } from "./mocked";

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

// Ticket 113: the box left the bar. It is its own search landmark, after the page's content and before the footer, so
// it comes after the page in the Tab order.
test("one banner holds the view switch and no box, section link or stamp; the box is its own search landmark after the page", async ({ page }) => {
  await mockShell(page);
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");

  const banner = page.getByRole("banner");
  await expect(banner).toHaveCount(1);
  await expect(banner.getByRole("search")).toHaveCount(0);
  await expect(banner.getByRole("combobox")).toHaveCount(0);
  await expect(page.getByRole("search")).toHaveCount(1);
  const order = await page.evaluate(() => {
    const search = document.querySelector("[role=search]")!;
    const after = (a: Element, b: Element) => Boolean(a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING);
    return {
      inMain: Boolean(search.closest("main")),
      afterMain: after(document.querySelector("main")!, search),
      beforeFooter: after(search, document.querySelector("footer")!),
    };
  });
  expect(order).toEqual({ inMain: false, afterMain: true, beforeFooter: true });
  await expect(banner.getByRole("button", { name: "View: World Bank staff" })).toBeVisible();
  // Ticket 93: the stamp moved to the sidebar's foot.
  await expect(banner.locator("[data-stamp]")).toHaveCount(0);
  // Ticket 92: the sections left the bar for the sidebar beside the page.
  await expect(banner.getByRole("navigation")).toHaveCount(0);
  await expect(banner.getByRole("link", { name: /^(Home|Packages|Projects|Lessons|Drafts|Data)$/ })).toHaveCount(0);
});

// Ticket 113 (DESIGN.md section 5, Top bar and Ask bar): the bar is one 56 px navy row at every width, the Menu button
// below 1024 px, the logo, the wordmark and the view switch from 768 px, 24 px from the right edge from 1024 px, with no
// box. The box floats at the page column's foot, its bottom 16 px above the window's bottom edge, on surface with
// 4 px corners; ticket 127 gave it a 1 px primary edge and shadow-float, the two navy-tinted shadows DESIGN.md's
// Elevation row writes. From 1024 px the bar sticks; below, it scrolls away, and the box stays at the window's foot.
const PRIMARY_EDGE = "rgb(0, 67, 112) 0px 0px 0px 1px inset";
const FLOAT_SHADOW = ["rgba(0, 34, 68, 0.12) 0px 1px 2px 0px", "rgba(0, 34, 68, 0.16) 0px 8px 24px 0px"];
test("the bar is one 56 px navy row with no box at every width, and the box floats at the page column's foot", async ({ page }) => {
  await mockShell(page);
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  await expect(page.locator("main h1")).toBeVisible();
  const at = async (selector: string) => (await page.locator(selector).boundingBox())!;

  // Ticket 110: the rail rests at every width from 1024 px.
  for (const [width, height] of [[1440, 900], [1024, 768], [390, 844]] as const) {
    await page.setViewportSize({ width, height });
    const bar = await at("[data-nav-bar]");
    expect([bar.x, bar.y, bar.width, bar.height], `${width} px`).toEqual([0, 0, width, 56]);
    expect(await page.locator("[data-nav-bar]").evaluate((el) => getComputedStyle(el).backgroundColor)).toBe("rgb(0, 34, 68)");
    // The header is the bar alone, and the bar holds no box.
    expect((await at("header")).height, `${width} px`).toBe(56);
    await expect(page.locator("[data-nav-bar] input")).toHaveCount(0);
    const logo = await at("[data-nav-bar] img");
    expect([logo.width, logo.height], `${width} px`).toEqual([120, 24]);
    const pill = page.locator("[data-view-pill]");
    await expect(pill, `${width} px`).toBeVisible({ visible: width >= 768 });
    if (width >= 1024) expect(Math.round(width - ((await pill.boundingBox())!.x + (await pill.boundingBox())!.width)), `${width} px`).toBe(24);

    // Where the box sits across the page is ticket 127's, tested on the grid below.
    const box = await at("[data-box-slot] form > [data-focus-ring]");
    expect(Math.round(height - (box.y + box.height)), `${width} px: 16 px above the window's bottom edge`).toBe(16);
    expect(
      await page.locator("[data-box-slot] form > [data-focus-ring]").evaluate((el) => {
        const style = getComputedStyle(el);
        // The shadows the box draws, leaving out the empty ones Tailwind composes with them.
        const shadows = style.boxShadow.split(/,\s*(?![^()]*\))/).filter((shadow) => !shadow.startsWith("rgba(0, 0, 0, 0)"));
        return [style.backgroundColor, style.borderRadius, shadows];
      }),
      `${width} px`,
    ).toEqual(["rgb(255, 255, 255)", "4px", [PRIMARY_EDGE, ...FLOAT_SHADOW]]);
  }

  // From 1024 px the bar sticks: scrolled down, it stays at the top of the window, and the box at its foot.
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.addStyleTag({ content: "main { min-height: 3000px; }" });
  await page.evaluate(() => window.scrollTo(0, 600));
  await expect.poll(() => page.evaluate(() => window.scrollY)).toBe(600);
  expect((await at("[data-nav-bar]")).y).toBe(0);
  expect(Math.round(900 - ((await at("[data-box-slot] form")).y + 56))).toBe(16);
  // Below 1024 px the bar scrolls away with the page, so a phone keeps its screen for the page. Home's box is one 48 px
  // row there (ticket 127).
  await page.setViewportSize({ width: 800, height: 900 });
  await page.evaluate(() => window.scrollTo(0, 600));
  await expect.poll(() => page.evaluate(() => window.scrollY)).toBe(600);
  expect((await at("[data-nav-bar]")).y).toBeLessThan(0);
  expect(Math.round(900 - ((await at("[data-box-slot] form")).y + 48))).toBe(16);
});

// Ticket 127 (the design lead's Option A of October 29, 2026, refined after the Mobbin pass): from a frame of 75rem the
// box sits on the grid. On a workspace page it spans the work's columns 1 to 7, so it centers over the work and the draft
// bar; on a wide page it spans columns 3 to 10. At 1024 px and below it keeps its place: 640 px centered, or the window
// less its margins. The edges are the lead's measures of the work and the grid (x 104 to 847 and x 325 to 1,179 at
// 1440 px, x 104 to 753 at 1280 px, x 224 to 864 at 1024 px); 1280 px's wide columns follow from the same grid: 1,136 px
// of content, 12 columns of 65.33 px and gutters of 32 px.
const PACKAGE_127 = "KE-NWWDA-541055-CW-RFB";
const GRID_EDGES: Record<"work" | "wide", Record<number, [number, number]>> = {
  work: { 1440: [104, 847], 1280: [104, 753], 1024: [224, 864], 390: [16, 374] },
  wide: { 1440: [325, 1179], 1280: [299, 1045], 1024: [224, 864], 390: [16, 374] },
};
test("the box's edges sit on the work's columns on a workspace page and on columns 3 to 10 on a wide page, and keep their place at 1024 and 390 px", async ({ page }) => {
  await mockApi(page, {
    ...(await hubApi()),
    [`/api/packages/${PACKAGE_127}`]: { body: await recorded("package-ke-nwwda-541055.json") },
    [`/api/packages/${PACKAGE_127}/comparables`]: { body: await recorded("comparables-ke-nwwda-541055.json") },
  });
  for (const [kind, path] of [["work", `/packages/${PACKAGE_127}`], ["wide", "/projects/P130164"]] as const) {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto(path);
    await expect(page.locator("main h1")).toBeVisible();
    for (const [width, height] of [[1440, 900], [1280, 800], [1024, 768], [390, 844]] as const) {
      await page.setViewportSize({ width, height });
      const box = (await page.locator("[data-box-slot] form > [data-focus-ring]").boundingBox())!;
      expect([Math.round(box.x), Math.round(box.x + box.width)], `${kind} page at ${width} px`).toEqual(GRID_EDGES[kind][width]);
      if (kind === "work" && width >= 1280) {
        const work = (await page.locator("[data-workspace-work]").first().boundingBox())!;
        expect(Math.abs(box.x - work.x) + Math.abs(box.width - work.width), `${width} px: the box on the work's edges`).toBeLessThanOrEqual(0.5);
      }
    }
  }
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

// Ticket 92 (DESIGN.md section 5, Sidebar): from 1024 px the sections are a sidebar named "Main" beside the page, Home
// first and each section once. Ticket 110: with no stored choice it rests as the 64 px rail of icons at every width
// from 1024 px (the user's decision of October 27, 2026), and its order is the user's: Home, Projects, Packages,
// Lessons, Drafts, then Data at the foot, since a project holds the plan and the plan holds the packages.
test("with no stored choice, the sidebar named Main rests as the 64 px rail beside the page at every width from 1024 px, Home first", async ({ page }) => {
  await mockShell(page);
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");

  const main = page.getByRole("navigation", { name: "Main" });
  for (const width of [1920, 1440, 1280, 1024]) {
    await page.setViewportSize({ width, height: 900 });
    await expect(main.locator("[data-nav-item]"), `${width} px`).toHaveText(["Home", "Projects", "Packages", "Lessons", "Drafts", "Data"]);
    const sidebar = (await page.locator("[data-sidebar-column]").boundingBox())!;
    const column = (await page.locator("[data-page-column]").boundingBox())!;
    expect([sidebar.x, sidebar.width, column.x], `${width} px`).toEqual([0, 64, 64]);
    await expect(page.locator("[data-sidebar-toggle]"), `${width} px`).toHaveAccessibleName("Expand the sidebar");
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
    // In the rail the section's own pages hide (ticket 99's sub-items; Data's since ticket 104), so one mark shows.
    await expect(main.locator("[aria-current]:visible"), path).toHaveCount(1);
  }
  // Under Data its two pages are sub-items, and the page's own carries "page" (ticket 104).
  await expect(main.locator("[data-sub-items=data] [aria-current=page]")).toHaveText("Sources and licenses");
});

// "Collapse the sidebar" and "Expand the sidebar" are one button (DESIGN.md section 5, Sidebar). The width changes at
// once: it is final in the same frame as the press, and nothing on the sidebar transitions its width. Ticket 110: the
// rail is where it starts, so "Expand the sidebar" is the first press, and the choice outranks the default after a reload.
test("Expand the sidebar opens the rail to 224 px at once, Collapse the sidebar turns it back, and the choice survives a reload", async ({ page }) => {
  await mockShell(page);
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  const column = page.locator("[data-sidebar-column]");
  const toggle = page.locator("[data-sidebar-toggle]");
  await expect(toggle).toHaveAccessibleName("Expand the sidebar");
  await expect(toggle).toHaveAttribute("aria-expanded", "false");
  expect((await column.boundingBox())!.width).toBe(64);

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
  expect(pressed).toEqual({ moves: [], width: 224 });
  await expect(toggle).toHaveAccessibleName("Collapse the sidebar");
  await expect(toggle).toHaveAttribute("aria-expanded", "true");
  await expect(toggle).toBeFocused();

  await page.reload();
  await expect(page.locator("main h1")).toBeVisible();
  expect((await column.boundingBox())!.width).toBe(224);
  await page.setViewportSize({ width: 1024, height: 900 });
  await page.reload();
  await expect(toggle).toHaveAccessibleName("Collapse the sidebar");
  expect((await column.boundingBox())!.width).toBe(224);
  await toggle.click();
  expect((await column.boundingBox())!.width).toBe(64);
  await page.setViewportSize({ width: 1920, height: 900 });
  await page.reload();
  await expect(toggle).toHaveAccessibleName("Expand the sidebar");
  expect((await column.boundingBox())!.width).toBe(64);
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

  // Opened, the sidebar shows its labels and no tooltip.
  await page.keyboard.press("Enter");
  await expect(tip).toHaveCount(0);
  await lessons.hover();
  await page.waitForTimeout(200);
  await expect(tip).toHaveCount(0);
});

// Ticket 92: web/index.html's first script reads the stored choice, and its style paints the sidebar's frame at that
// width, or the width's default, before the app's script runs. The app's bundle is held back here, so the page shows
// only what index.html paints; below 1024 px no sidebar is painted and the closed Menu sheet is not shown. Ticket 113:
// the box left the bar, so the bar is one 56 px row at every width, with the logo after the Menu button below 1024 px.
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
  // Ticket 110: with no stored choice the rail rests at every width from 1024 px, in the first paint and after it.
  const cases: [number, string | null][] = [[1920, null], [1440, null], [1024, null], [1280, "open"], [1920, "rail"], [800, null], [390, null]];
  for (const [width, stored] of cases) {
    const first = await browser.newContext({ viewport: { width, height: 900 } });
    if (stored) await first.addInitScript((rest) => window.localStorage.setItem("strata.sidebar", rest), stored);
    await first.route(/\/assets\/.+\.js$/, (route) => route.abort());
    const before = await first.newPage();
    await before.goto(test.info().project.use.baseURL!);
    const painted = await before.evaluate(boxes, ["[data-boot-bar]", "[data-boot-bar] img", "[data-boot-sidebar]", "[data-boot-sidebar-column]"]);
    await first.close();

    await page.evaluate((rest) => (rest ? window.localStorage.setItem("strata.sidebar", rest) : window.localStorage.clear()), stored);
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/");
    await expect(page.locator("main h1")).toBeVisible();
    const mounted = await page.evaluate(boxes, ["[data-nav-bar]", "[data-nav-bar] img", "[data-sidebar]"]);

    expect(painted.slice(0, 3), `${width} px, stored ${stored}`).toEqual(mounted);
    expect(mounted[2] === null, `${width} px`).toBe(width < 1024);
    expect(mounted[0]![3], `${width} px: the bar's height`).toBe(56);
    if (width < 1024) continue;
    const wide = stored === "open" ? 224 : 64;
    expect(painted[3]![2], `${width} px, stored ${stored}: the painted sidebar's width`).toBe(wide);
    expect((await page.locator("[data-sidebar-column]").boundingBox())!.width, `${width} px, stored ${stored}`).toBe(wide);
  }
});

// Ticket 93 (DESIGN.md section 5, Freshness stamp): the stamp sits at the sidebar's foot, under Data, on its label's
// left edge, in a 24 px line box. The stamp's tests open the sidebar at 1440 px, where its five states show; with no
// stored choice the sidebar rests as the rail, which hides the stamp (ticket 110).
test("the stamp sits at the sidebar's foot under Data, shows the day the server returns, and links to the Data page", async ({ page }) => {
  await page.clock.setFixedTime(TODAY);
  await mockShell(page);
  await page.setViewportSize({ width: 1440, height: 900 });
  await openSidebar(page);
  await page.goto("/");

  const stamp = page.locator("[data-stamp]").getByRole("link");
  await expect(stamp).toHaveText("Data updated Oct 23");
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
  await expect(page.locator("[data-rail-tip]")).toHaveText("DataData updated Oct 23");
  await expect(data).toHaveAccessibleDescription("Data updated Oct 23");
  await page.locator("[data-sidebar-toggle]").click();
  await expect(data).not.toHaveAttribute("aria-describedby");
  await expect(page.locator("[data-stamp]").getByRole("link")).toBeVisible();
});

test("a data date from another year shows its year", async ({ page }) => {
  await page.clock.setFixedTime(TODAY);
  await mockShell(page, { freshness: { body: '{"data_through": "2025-12-30"}' } });
  await page.setViewportSize({ width: 1440, height: 900 });
  await openSidebar(page);
  await page.goto("/");

  await expect(page.locator("[data-stamp]").getByRole("link")).toHaveText("Data updated Dec 30, 2025");
});

test("before any daily source has loaded, the stamp says no data are loaded and still links to the Data page", async ({ page }) => {
  await mockShell(page, { freshness: { body: await recorded("freshness-empty.json") } });
  await page.setViewportSize({ width: 1440, height: 900 });
  await openSidebar(page);
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
  await openSidebar(page);
  await page.goto("/");

  const stamp = page.locator("[data-stamp]");
  await expect(stamp).toHaveAttribute("aria-busy", "true");
  await expect(stamp.locator("[data-skeleton]")).toHaveCount(1);
  await expect(stamp).toHaveText("Reading the data date", { timeout: 3000 });
  answer();
  await expect(stamp.getByRole("link")).toHaveText(/^Data updated /);
});

// Ticket 59 (the 93 design review, follow-up 3; the 93 critique): below 1024 px the Menu button starts on the window's
// margin, the page's own left edge, with no outline at rest, so at 800 px the bar holds one outlined box, the view
// switch; its border turns white on hover and while the sheet is open. The wordmark is 18/24 at 700 (DESIGN.md sections 3
// and 9).
test("the Menu button starts on the window's margin with no outline at rest, and the wordmark is 18/24 at 700", async ({ page }) => {
  await mockShell(page);
  await page.setViewportSize({ width: 390, height: 900 });
  await page.goto("/");
  const menu = page.locator("[data-menu-button]");
  const border = () => menu.evaluate((element) => getComputedStyle(element).borderTopColor);
  for (const [width, margin] of [[390, 16], [800, 32]] as const) {
    await page.setViewportSize({ width, height: 900 });
    expect(Math.round((await menu.boundingBox())!.x), `${width} px`).toBe(margin);
    const h1 = page.locator("main h1").first();
    expect(Math.round((await h1.boundingBox())!.x), `${width} px: the page's own left edge`).toBe(margin);
  }
  expect(await border()).toBe("rgba(0, 0, 0, 0)");
  await menu.hover();
  await expect.poll(border).toBe("rgb(255, 255, 255)");
  await page.mouse.move(400, 600);
  await menu.click();
  await expect(menu).toHaveAttribute("aria-expanded", "true");
  await expect.poll(border).toBe("rgb(255, 255, 255)");
  const wordmark = page.locator("[data-nav-bar] a").filter({ hasText: "Strata" });
  expect(await wordmark.evaluate((element) => [getComputedStyle(element).fontSize, getComputedStyle(element).lineHeight, getComputedStyle(element).fontWeight])).toEqual(["18px", "24px", "700"]);
});

// Ticket 59 (the 92 design review, follow-ups 5 and 6): until GET /api/me says which sections a preview has, the
// sidebar draws one bar for Home, four for the sections 16 px under it and one for Data at its foot, each where its item
// will be, and "Collapse the sidebar" is already there. On the rail its items sit 12 px from its edges.
test("while the view loads, the sidebar's bars stand where Home, the sections and Data will be", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await openSidebar(page);
  let answer: () => void = () => {};
  const answered = new Promise<void>((resolve) => (answer = resolve));
  await mockShell(page);
  await page.route((url) => url.pathname === "/api/me", async (route) => {
    await answered;
    await route.fulfill({ status: 200, contentType: "application/json", body: await recorded("me-preview-piu.json") });
  });
  await page.goto("/?view=piu");
  const sidebar = page.locator("[data-sidebar]");
  await expect(sidebar.locator("[data-sidebar-loading]")).toBeVisible();
  await expect(sidebar.getByRole("button", { name: "Collapse the sidebar" })).toBeVisible();
  const bars = await sidebar.locator("nav [data-skeleton]").evaluateAll((all) => all.map((bar) => Math.round(bar.getBoundingClientRect().top)));
  expect(bars).toHaveLength(6);
  expect(bars[1] - bars[0], "16 px between Home and the sections, as between their lists").toBe(36 + 16);
  answer();
  await expect(sidebar.locator("[data-nav-item=home]")).toBeVisible();
  const items: Record<string, number> = await sidebar.locator("nav [data-nav-item]").evaluateAll((all) =>
    Object.fromEntries(all.map((item) => [item.getAttribute("data-nav-item") ?? "", Math.round(item.getBoundingClientRect().top)])),
  );
  expect(items.home, "Home where its bar was").toBe(bars[0]);
  const sections = Object.entries(items).filter(([key]) => key !== "home" && key !== "data" && key !== "start-here");
  expect(Math.min(...sections.map(([, top]) => top)), "the first section where its bar was").toBe(bars[1]);
  if (items.data !== undefined) expect(items.data, "Data where its bar was").toBe(bars[5]);

  // The rail: its items 12 px in from its edges.
  await sidebar.getByRole("button", { name: "Collapse the sidebar" }).click();
  const [rail, home] = await page.evaluate(() =>
    ["[data-sidebar] nav", "[data-sidebar] [data-nav-item=home]"].map((selector) => document.querySelector(selector)!.getBoundingClientRect().toJSON()),
  );
  expect([Math.round(home.left - rail.left), Math.round(rail.right - home.right)]).toEqual([12, 12]);
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
  await openSidebar(page);
  await page.goto("/");

  const stamp = page.locator("[data-stamp]");
  await expect(stamp).toHaveText("I can't read the data date.");
  await expect(stamp.getByRole("link")).toHaveCount(0);
  await expect(stamp.locator("svg.lucide-circle-x")).toHaveCount(1);
  // Ticket 59 (the 93 review): the icon hangs left of the stamp's edge, so the words start at x 48, on Data's label's
  // edge, on one 24 px line.
  const words = await stamp.evaluate((element) => {
    const text = [...element.querySelectorAll("span")].flatMap((span) => [...span.childNodes]).find((node) => node.nodeType === Node.TEXT_NODE)!;
    const range = document.createRange();
    range.selectNodeContents(text);
    const lines = new Set([...range.getClientRects()].map((box) => Math.round(box.top))).size;
    return { left: Math.round(range.getBoundingClientRect().left), lines, height: Math.round(element.getBoundingClientRect().height) };
  });
  expect(words).toEqual({ left: 48, lines: 1, height: 24 });

  const tabs = page.getByRole("navigation", { name: "Main" });
  await tabs.getByRole("link", { name: "Packages" }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Packages");
  expect(reads).toBe(1);

  await page.clock.fastForward("01:01");
  await tabs.getByRole("link", { name: "Projects" }).click();
  await expect(stamp.getByRole("link")).toHaveText("Data updated Oct 23");
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

// Ticket 59, the pm's routed item from ticket 93's critique: below 768 px the Menu sheet's foot held the whole view panel,
// about three times the navigation's height, with a second current mark. Now the foot holds Data, the stamp under it and
// one view button, the bar's view switch, pinned to the sheet's bottom. Pressed, it opens the view switch's popover above
// it (round 3: the rows opened in place, which moved the button 355 px up and drew a second mark), and the button stays
// where the thumb is. The chosen view is marked by its check alone, so the page's item keeps the one tint and bar.
test("at 390 px the Menu sheet's foot holds one view button under Data and the stamp, and it opens its popover above it", async ({ page }) => {
  await mockShell(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page.getByRole("button", { name: "Menu", exact: true }).click();
  const sheet = page.getByRole("dialog", { name: "Menu" });
  const view = sheet.getByRole("button", { name: "View: World Bank staff", exact: true });
  await expect(view).toHaveAttribute("aria-expanded", "false");
  await expect(sheet.locator("[data-view-row]")).toHaveCount(0);
  await expect(sheet.getByText("See Strata as", { exact: true })).toHaveCount(0);
  // Data, then the stamp, then the view button, which ends the sheet.
  const data = (await sheet.locator("[data-nav-item=data]").boundingBox())!;
  const stamp = (await sheet.locator("[data-sidebar-stamp]").boundingBox())!;
  const button = (await view.boundingBox())!;
  const box = (await sheet.boundingBox())!;
  expect(stamp.y, "the stamp under Data").toBeGreaterThanOrEqual(data.y + data.height - 1);
  expect(button.y, "the view button under the stamp").toBeGreaterThan(stamp.y + stamp.height - 1);
  expect(box.y + box.height - (button.y + button.height), "pinned to the sheet's bottom").toBeLessThanOrEqual(24);
  // One current mark: the page's item.
  await expect(sheet.locator("[aria-current]")).toHaveCount(1);
  // The marks a reader sees: a tinted link row, or one with the 3 px bar.
  const marks = () =>
    sheet.evaluate((root) =>
      [...root.querySelectorAll("a")]
        .filter((element) => element.getClientRects().length > 0)
        .filter((element) => getComputedStyle(element).backgroundColor !== "rgba(0, 0, 0, 0)" || getComputedStyle(element, "::before").backgroundColor.startsWith("rgb("))
        .map((element) => (element.textContent ?? "").trim().split(/\s{2,}|\n/)[0]),
    );
  expect(await marks()).toEqual(["Home"]);

  await view.click();
  await expect(view).toHaveAttribute("aria-expanded", "true");
  const popover = sheet.getByRole("dialog", { name: "Your view" });
  await expect(popover.locator("[data-view-row]")).toHaveCount(3);
  await expect(popover.getByText("See Strata as", { exact: true })).toBeVisible();
  // Focus lands on the current view's row, as in the bar's popover.
  await expect(popover.locator("[data-view-row=staff]")).toBeFocused();
  await expect(popover.locator("[data-view-row=staff] svg")).toHaveCount(1);
  // The button has not moved, and the popover sits 8 px above it on its left edge, as wide as it is.
  const pressed = (await view.boundingBox())!;
  expect(Math.round(pressed.y), "the view button stays put").toBe(Math.round(button.y));
  const above = (await popover.boundingBox())!;
  expect(Math.round(pressed.y - (above.y + above.height)), "8 px above the button").toBe(8);
  expect(Math.round(above.x), "on the button's left edge").toBe(Math.round(pressed.x));
  expect(Math.round(above.width), "as wide as the button").toBe(Math.round(pressed.width));
  // Still one mark: the chosen view has its check alone, with no tint and no bar.
  expect(await marks()).toEqual(["Home"]);

  // Escape closes the popover only, and focus goes back to the button.
  await page.keyboard.press("Escape");
  await expect(popover).toBeHidden();
  await expect(sheet).toBeVisible();
  await expect(view).toBeFocused();
  await expect(view).toHaveAttribute("aria-expanded", "false");
  await view.click();
  await expect(popover.locator("[data-view-row]")).toHaveCount(3);
  await view.click();
  await expect(sheet.locator("[data-view-row]")).toHaveCount(0);
});

// On the smallest phone the popover keeps to the room above the button and scrolls inside itself, so the language choice
// can still be reached.
test("at 320 x 568 the Menu sheet's view popover fits above its button and scrolls to the language choice", async ({ page }) => {
  await mockShell(page);
  await page.setViewportSize({ width: 320, height: 568 });
  await page.goto("/");
  await page.getByRole("button", { name: "Menu", exact: true }).click();
  const sheet = page.getByRole("dialog", { name: "Menu" });
  const view = sheet.getByRole("button", { name: "View: World Bank staff", exact: true });
  await view.click();
  const popover = sheet.getByRole("dialog", { name: "Your view" });
  await expect(popover).toBeVisible();
  const above = (await popover.boundingBox())!;
  const button = (await view.boundingBox())!;
  const close = (await sheet.getByRole("button", { name: "Close the menu" }).boundingBox())!;
  expect(above.y, "clear of the sheet's head, so Close the menu stays in reach").toBeGreaterThanOrEqual(close.y + close.height + 8);
  expect(above.y + above.height, "above the button").toBeLessThanOrEqual(button.y);
  const last = popover.locator("[data-language-choice] label").last();
  await last.scrollIntoViewIfNeeded();
  await expect(last).toBeInViewport();
  const at = (await last.boundingBox())!;
  expect(at.y + at.height, "the last language above the button").toBeLessThanOrEqual(button.y);
});

// Ticket 110, from the user's review of October 27, 2026: "See Strata as" names the group in the label style (DESIGN.md
// section 3: 13/16, 600, ink-muted), so it no longer reads as a fourth view. It sits 16 px under the signed-in line
// (between blocks) and 8 px above the first view row (a heading to its first line; section 4). DESIGN.md keeps 700 for
// the h1 and the wordmark, so nothing in the panel is bold. The Menu sheet shows the same panel below 768 px.
for (const width of [1440, 390]) {
  test(`at ${width} px "See Strata as" is a label 16 px under the signed-in line and 8 px over the first view, and nothing in the panel is bold`, async ({ page }) => {
    await mockShell(page);
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/");
    const sheet = width < 768;
    await page.getByRole("button", { name: sheet ? "Menu" : "View: World Bank staff", exact: true }).click();
    // In the Menu sheet the view rows show once its view button is pressed (ticket 59).
    if (sheet) await page.locator("[data-menu-panel]").getByRole("button", { name: "View: World Bank staff", exact: true }).click();
    const panel = sheet ? page.locator("[data-menu-panel]") : page.getByRole("dialog", { name: "Your view" });
    const label = panel.getByText("See Strata as", { exact: true });
    await expect(label).toBeVisible();
    const look = await label.evaluate((el) => {
      const style = getComputedStyle(el);
      return [style.fontSize, style.lineHeight, style.fontWeight, style.color];
    });
    expect(look).toEqual(["13px", "16px", "600", "rgb(75, 94, 113)"]);
    const who = (await panel.getByText("Signed in as ana.example@worldbank.org", { exact: true }).boundingBox())!;
    const group = (await label.boundingBox())!;
    const row = (await panel.locator("[data-view-row]").first().boundingBox())!;
    expect(Math.round(group.y - (who.y + who.height)), "from the signed-in line").toBe(16);
    expect(Math.round(row.y - (group.y + group.height)), "to the first view row").toBe(8);

    const bold = await panel.evaluate((root) =>
      [...root.querySelectorAll("*")]
        .filter((el) => [...el.childNodes].some((node) => node.nodeType === Node.TEXT_NODE && node.textContent!.trim()))
        .filter((el) => getComputedStyle(el).fontWeight === "700")
        .map((el) => el.textContent!.trim()),
    );
    expect(bold).toEqual([]);
  });
}

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
  test(`at ${width} px Home's first-run row never ends its sentence on one word, and the Menu's view line never ends on one word`, async ({ page }) => {
    // Home's first run (ticket 41), as a viewer who follows nothing sees it: since ticket 98, Worth knowing is a Task
    // zone row with its sentence and one link.
    await mockShell(page, { home: { body: await recorded("home-first-run.json") } });
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/");

    const sentence = page.locator("[data-worth] [data-section-summary] p").first();
    await expect(sentence).toHaveText(
      "I brief you on the projects you follow. Follow a project from its page, and each day I list its changed plans and new signals here.",
    );
    expect((await sentence.evaluate(lastLine)).words).toBeGreaterThan(1);

    // The Menu's view rows wrap with text-pretty, so no description ends on one word (ticket 40).
    await page.getByRole("button", { name: "Menu", exact: true }).click();
    await page.locator("[data-menu-panel]").getByRole("button", { name: "View: World Bank staff", exact: true }).click();
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
  await expect(page.locator("[data-box-slot]").getByRole("combobox")).toBeFocused();
});

// Ticket 94: the page's margin follows the window, never the page area, so opening the evidence drawer narrows the
// page and keeps its left edge. Each page opens with a source in the drawer, then closes it; its h1 does not move.
const PLAN_CHECK = "/projects/P156634/procurement/northern-water-works-development-agency/2026-10-09";
const ICR_54 = "strata.gold.passage:31525018/v1/54";
const LEFT_EDGE_PAGES: [string, string, string][] = [
  ["the project Summary", "/projects/P130164", ICR_54],
  ["the plan check", PLAN_CHECK, ICR_54],
  ["a draft", "/drafts/draft-0001", "strata.silver.plan_rows:40132287/KE-NWWDA-229129-CW-RFB"],
];
for (const width of [1440, 1024]) {
  test(`at ${width} px opening the drawer never moves the h1's left edge on the project Summary, the plan check and a draft`, async ({ page }) => {
    await mockApi(page, {
      ...(await hubApi()),
      [`/api${PLAN_CHECK}`]: { body: await recorded("check-plan-p156634-nwwda-2026-10-09.json") },
      "/api/drafts/existing": { body: '{"draft":null}' },
      "/api/drafts/draft-0001": { body: await recorded("drafts-review-notes-draft.json") },
    });
    await page.setViewportSize({ width, height: 900 });
    for (const [name, path, source] of LEFT_EDGE_PAGES) {
      await page.goto(`${path}?evidence=${encodeURIComponent(source)}`);
      const drawer = page.getByRole("dialog");
      const h1 = page.locator("main h1");
      await expect(drawer).toBeVisible();
      await expect(h1).toBeVisible();
      const beside = (await h1.boundingBox())!.x;
      // Ticket 113: the box covers no part of the drawer. On a wide page it centers in the page column the drawer
      // narrowed; on a draft, a workspace page, it keeps the work's columns, as the work does (ticket 127).
      if (width === 1440) {
        const box = (await page.locator("[data-box-slot] form > [data-focus-ring]").boundingBox())!;
        const column = (await page.locator("[data-page-column]").boundingBox())!;
        const pane = (await drawer.boundingBox())!;
        expect(column.width, `${name}: the narrowed page column`).toBeLessThan(1440 - 64);
        if (name === "a draft") {
          const work = (await page.locator("[data-document-column]").boundingBox())!;
          expect(Math.abs(box.x - work.x) + Math.abs(box.width - work.width), `${name}: the box on the work's columns`).toBeLessThanOrEqual(0.5);
        } else {
          expect(Math.abs(box.x + box.width / 2 - (column.x + column.width / 2)), `${name}: the box centered`).toBeLessThanOrEqual(0.5);
        }
        expect(box.x + box.width, `${name}: the box clear of the drawer`).toBeLessThanOrEqual(pane.x);
      }
      await drawer.getByRole("button", { name: /^Close/ }).click();
      await expect(drawer).toBeHidden();
      expect((await h1.boundingBox())!.x, `${name} at ${width} px`).toBe(beside);
    }
  });
}

// Ticket 110, from the user's review of October 27, 2026: even margins. With the rail at rest, the gap from the
// content's right edge to the window's edge is within 16 px of the gap from the rail to the content's left edge: wide
// content may take 1440 px, and Lessons and the Drafts list use all 12 columns. The content is what the page paints:
// a line of text as far as its words go, a table, or a box with a fill or a border, never an empty wrapper, as far as
// a row that scrolls sideways shows it. At 390 px both gaps are the 16 px margin, and at 320 px nothing scrolls
// sideways. One page load each; the widths change in place.
const painted = (main: Element) => {
  let [left, right] = [Infinity, -Infinity];
  const add = (el: Element, from: number, to: number) => {
    // A row that scrolls sideways, or a line cut short, shows only what is inside its own box.
    for (let parent: Element | null = el; parent && parent !== main; parent = parent.parentElement) {
      if (getComputedStyle(parent).overflowX === "visible") continue;
      const frame = parent.getBoundingClientRect();
      [from, to] = [Math.max(from, frame.left), Math.min(to, frame.right)];
    }
    if (to - from <= 1) return;
    [left, right] = [Math.min(left, from), Math.max(right, to)];
  };
  for (const el of main.querySelectorAll<HTMLElement>("*")) {
    const box = el.getBoundingClientRect();
    if (box.width <= 1 || box.height <= 1 || !el.checkVisibility({ visibilityProperty: true, opacityProperty: true })) continue;
    const style = getComputedStyle(el);
    const words = [...el.childNodes].filter((node) => node.nodeType === Node.TEXT_NODE && node.textContent!.trim());
    const fill = style.backgroundColor !== "rgba(0, 0, 0, 0)" || parseFloat(style.borderLeftWidth) > 0 || parseFloat(style.borderRightWidth) > 0;
    if (fill || ["TABLE", "svg", "IMG"].includes(el.tagName)) add(el, box.left, box.right);
    // The element's own words, line by line; a child's words count with the child, which may be hidden.
    for (const node of words) {
      const range = document.createRange();
      range.selectNodeContents(node);
      for (const line of range.getClientRects()) add(el, line.left, line.right);
    }
  }
  return { left: Math.round(left), right: Math.round(right) };
};
const MARGIN_PAGES: [string, string, (page: Page) => Promise<unknown>][] = [
  ["Home", "/", (page) => mockShell(page)],
  ["Packages", "/packages", async (page) => mockApi(page, { ...(await hubApi()), "/api/planned-packages": { body: await recorded("planned-packages-list.json") } })],
  ["the plan check", PLAN_CHECK, async (page) => mockApi(page, { ...(await hubApi()), [`/api${PLAN_CHECK}`]: { body: await recorded("check-plan-p156634-nwwda-2026-10-09.json") } })],
  [
    "Lessons",
    "/lessons",
    async (page) =>
      mockApi(page, {
        ...(await hubApi()),
        "/api/lessons/me": { body: await recorded("lessons-me-viewer.json") },
        "/api/lessons/page": { body: await recorded("lessons-page.json") },
      }),
  ],
  ["the Drafts list", "/drafts", async (page) => mockApi(page, { ...(await hubApi()), "/api/drafts": { body: await recorded("drafts-list.json") } })],
];
for (const [name, path, serve] of MARGIN_PAGES) {
  test(`with the rail at rest, ${name} has even margins at 1440 and 1512 px, 16 px margins at 390 px and no sideways scroll at 320 px`, async ({ page }) => {
    await serve(page);
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto(path);
    await expect(page.locator("main h1")).toBeVisible();
    await page.evaluate(() => document.fonts.ready);
    for (const [width, height] of [[1440, 900], [1512, 982], [390, 844]]) {
      await page.setViewportSize({ width, height });
      const rail = width < 1024 ? 0 : 64;
      const gaps = async () => {
        const { left, right } = await page.locator("main").evaluate(painted);
        return [left - rail, width - right];
      };
      if (width < 1024) {
        await expect.poll(gaps, { message: `${name} at ${width} px` }).toEqual([16, 16]);
        continue;
      }
      await expect.poll(async () => {
        const [left, right] = await gaps();
        return { left, even: Math.abs(right - left) <= 16 };
      }, { message: `${name} at ${width} px` }).toEqual({ left: 40, even: true });
    }
    await page.setViewportSize({ width: 320, height: 800 });
    await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth), { message: `${name} at 320 px` }).toBeLessThanOrEqual(320);
  });
}

// Ticket 110, for someone dropped into the app: each section's page says in one sentence what the tab is for and what
// to do there, in at most two lines at 1440 px. Home has none, because its date line and briefing say what it is. The
// sentences are the ticket's, copied here so the test checks the copy file against an independent source.
const TAB_PURPOSES: [string, string, string][] = [
  ["Packages", "/packages", "Check a published Procurement Plan or plan a new package, and find the ones you worked on here."],
  ["Projects", "/projects", "Find a World Bank-financed project by name, project ID or country, then open it to see its plans and documents."],
  // World Bank staff open Projects at Following, whose sentence also says what to do there.
  ["Following, under Projects", "/projects/following", "Follow the projects you work on, or find any World Bank-financed project by its name, project ID or country."],
  // The ticket's proposal, reordered so it keeps to two lines at 1440 px.
  ["Lessons", "/lessons", "These are lessons quoted from completion reports on finished World Bank projects, and I also show them on a package's page where they apply."],
  ["Drafts", "/drafts", "These are the drafts I wrote for you to check and export, and exporting sends nothing."],
  ["Data", "/data", "See how far each source can support an answer and where each dataset comes from."],
];
test("Packages, Projects, Lessons, Drafts and Data each say what the tab is for in one sentence of at most two lines at 1440 px", async ({ page }) => {
  await mockApi(page, {
    ...(await hubApi()),
    "/api/planned-packages": { body: await recorded("planned-packages-empty.json") },
    "/api/projects": { body: await recorded("projects.json") },
    "/api/following": { body: await recorded("following-examples.json") },
    "/api/lessons/me": { body: await recorded("lessons-me-viewer.json") },
    "/api/lessons/page": { body: await recorded("lessons-page-empty.json") },
    "/api/drafts": { body: await recorded("drafts-list-empty.json") },
  });
  await page.setViewportSize({ width: 1440, height: 900 });
  for (const [name, path, sentence] of TAB_PURPOSES) {
    await page.goto(path);
    const purpose = page.locator("main h1 + p");
    await expect(purpose, name).toHaveText(sentence);
    await page.evaluate(() => document.fonts.ready);
    const lines = await purpose.evaluate((el) => Math.round(el.getBoundingClientRect().height / parseFloat(getComputedStyle(el).lineHeight)));
    expect(lines, `${name}: lines at 1440 px`).toBeLessThanOrEqual(2);
  }
});

// Round 1's design review: the page's bottom scroll padding counts the box only while focus is in main, so focus on
// the sidebar's foot, or low in the evidence drawer, which both stick at the window's foot, never scrolls the page.
test("Tab down the sidebar to its foot, or focus low in the evidence drawer, leaves the page where it was", async ({ page }) => {
  await openAnswerPage(page);
  await expect(page.locator("[data-box-slot]")).toBeVisible();
  await page.locator("a[href='/drafts']").first().focus();
  const toggle = page.locator("[data-sidebar-toggle]");
  for (let press = 0; press < 6 && !(await toggle.evaluate((el) => el === document.activeElement)); press++) {
    await page.keyboard.press("Tab");
  }
  await expect(toggle).toBeFocused();
  expect(await page.evaluate(() => window.scrollY), "the page after Tab to the sidebar's foot").toBe(0);

  await openAnswerPage(page, { path: `/projects/P130164?evidence=${encodeURIComponent(ICR_54)}` });
  await page.setViewportSize({ width: 1440, height: 640 });
  const low = page.getByRole("dialog").getByRole("link", { name: /Open at page/ }).first();
  await expect(low).toBeVisible();
  await low.focus();
  expect(await page.evaluate(() => window.scrollY), "the page after focus low in the drawer").toBe(0);
});
