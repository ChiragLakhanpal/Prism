// The gallery's navigation, box band and footer match the blueprint's Home wireframe and
// DESIGN.md sections 5 and 8 (criteria 3 and 4 of ticket 02).
import { expect, test } from "./mocked";
import { footerSentence } from "./design-md";
import { galleryPaths } from "./gallery-pages";

const NAVY = "rgb(0, 34, 68)";
const TINT = "rgb(233, 247, 253)";
const PRIMARY = "rgb(0, 67, 112)";

test("the navy bar is 56 px tall with the logo slot, the wordmark and the view pill, and no section", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/gallery/navigation");

  const bar = page.locator("[data-nav-bar]");
  const box = (await bar.boundingBox())!;
  expect(box.height).toBe(56);
  expect(await bar.evaluate((el) => getComputedStyle(el).backgroundColor)).toBe(NAVY);
  // Ticket 92: the sections are the sidebar's, beside the page.
  await expect(bar.getByRole("link")).toHaveText(["Skip to main content", "Strata"]);

  // Logo at least 24 px tall, with clear space of half its height on every side.
  const logo = (await page.locator("[data-logo]").boundingBox())!;
  const wordmark = (await page.getByRole("link", { name: "Strata", exact: true }).boundingBox())!;
  expect(logo.height).toBeGreaterThanOrEqual(24);
  const clear = logo.height / 2;
  expect(logo.y - box.y).toBeGreaterThanOrEqual(clear);
  expect(box.y + box.height - (logo.y + logo.height)).toBeGreaterThanOrEqual(clear);
  expect(logo.x).toBeGreaterThanOrEqual(clear);
  expect(wordmark.x - (logo.x + logo.width)).toBeGreaterThanOrEqual(clear);

  // Left to right: logo, wordmark, then the pill at the right edge of the grid (72 px margin).
  const pill = page.getByRole("button", { name: "View: World Bank staff" });
  const pillBox = (await pill.boundingBox())!;
  expect(wordmark.x).toBeGreaterThan(logo.x);
  expect(pillBox.x).toBeGreaterThan(wordmark.x + wordmark.width);
  expect(Math.round(1440 - (pillBox.x + pillBox.width))).toBe(72);
  await expect(pill.locator("svg.lucide-chevron-down")).toHaveCount(1);
  // DESIGN.md section 5: the view switch is a 32 px pill, like a chip, not a 44 px button.
  expect(pillBox.height).toBe(32);
});

// Ticket 92 (DESIGN.md section 5, Sidebar): Home, the sections in order, Data at the foot; 224 px from 1440 px and a
// 64 px rail from 1024 to 1439 px; the current item in tint with a 3 px primary bar. The gallery draws Projects current.
test("from 1024 px the sidebar holds Home and the sections in order, 224 px wide from 1440 px and a 64 px rail below", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/gallery/navigation");
  const main = page.getByRole("navigation", { name: "Main" });
  for (const [width, wide] of [[1440, 224], [1280, 64], [1024, 64]]) {
    await page.setViewportSize({ width, height: 900 });
    await expect(main.locator("[data-nav-item]"), `${width} px`).toHaveText(["Home", "Packages", "Projects", "Lessons", "Drafts", "Data"]);
    expect((await page.locator("[data-sidebar-column]").boundingBox())!.width, `${width} px`).toBe(wide);
    await expect(main.locator("[data-nav-item][aria-current]"), `${width} px`).toHaveText(["Projects"]);
    await expect(main.locator("[data-nav-item=projects]"), `${width} px`).toHaveAttribute("aria-current", "page");
  }
  const mark = await main.locator("[data-nav-item=projects]").evaluate((link) => {
    const bar = getComputedStyle(link, "::before");
    return { fill: getComputedStyle(link).backgroundColor, bar: [bar.width, bar.backgroundColor] };
  });
  expect(mark).toEqual({ fill: TINT, bar: ["3px", PRIMARY] });
});

// The slot for a section's own pages: they show only under the current section, and the applied view hides the ones
// it hides (config/roles.toml). The gallery's sample (?sub=1) puts Following and All projects under Projects and a
// reviewer page under Lessons, and draws All projects as the page.
test("a section's own pages show under it only while it is current, and a view leaves out the pages it hides", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  const subs = page.getByRole("navigation", { name: "Main" }).locator("[data-sub-item]");
  await page.goto("/gallery/navigation?sub=1");
  await expect(subs).toHaveText(["Following", "All projects"]);
  await expect(subs.nth(1)).toHaveAttribute("aria-current", "page");
  await expect(page.locator("[data-nav-item=projects]")).toHaveAttribute("aria-current", "true");

  await page.goto("/gallery/navigation?sub=1&pill=piu");
  await expect(subs).toHaveText(["All projects"]);
  await page.goto("/gallery/navigation?sub=1&sidebar=rail");
  await expect(subs).toHaveCount(2);
  await expect(subs.first()).toBeHidden();
});

test("below 360 px the Menu button hides its word from sight and keeps its name, 44 by 44 px", async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 900 });
  await page.goto("/gallery/navigation");
  const menu = page.getByRole("button", { name: "Menu", exact: true });
  const size = (await menu.boundingBox())!;
  expect([size.width, size.height]).toEqual([44, 44]);
  expect(await menu.locator("span").evaluate((el) => el.getBoundingClientRect().width)).toBeLessThanOrEqual(1);
});

test("the band holds the box over columns 1 to 8 and the stamp at the right, and / focuses the box", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/gallery/navigation");

  const band = (await page.locator("[data-box-band]").boundingBox())!;
  expect(band.height).toBeGreaterThanOrEqual(69);
  const box = (await page.locator("[data-box-band] [data-focus-ring]").boundingBox())!;
  const stamp = (await page.locator("[data-box-band] [data-stamp] a").boundingBox())!;
  // Content is 1296 px wide: 12 columns and 11 gutters of 32 px. The box ends after column 8.
  const column = (1296 - 11 * 32) / 12;
  expect(Math.round(box.x)).toBe(72);
  expect(Math.round(box.x + box.width)).toBe(Math.round(72 + 8 * column + 7 * 32));
  expect(Math.round(stamp.x + stamp.width)).toBe(1440 - 72);
  await expect(page.locator("[data-box-band] [data-stamp] a")).toHaveText("Data through Oct 21");

  await page.locator("h1").click();
  await page.keyboard.press("/");
  await expect(page.locator("[data-box-band]").getByRole("combobox", { name: /Open a project/ })).toBeFocused();
});

// Ticket 92 (DESIGN.md section 5, Menu sheet): below 1024 px the sidebar's items are the Menu sheet, a modal dialog from
// the left that slides in over 200 ms on ease-drawer and out over 120 ms, with the page and the bar inert behind it.
test("below 1024 px the Menu button opens the Menu sheet, a modal dialog; Escape, Close the menu and the scrim close it", async ({ page }) => {
  await page.setViewportSize({ width: 1023, height: 900 });
  await page.goto("/gallery/navigation");
  await expect(page.getByRole("button", { name: "View: World Bank staff" })).toBeHidden();
  await expect(page.getByRole("navigation", { name: "Main" })).toHaveCount(0);

  const menu = page.getByRole("button", { name: "Menu", exact: true });
  const sheet = page.getByRole("dialog", { name: "Menu" });
  await expect(menu).toHaveAttribute("aria-expanded", "false");
  await menu.click();
  await expect(menu).toHaveAttribute("aria-expanded", "true");
  await expect(sheet).toHaveAttribute("aria-modal", "true");
  await expect(menu).toHaveAttribute("aria-controls", (await sheet.getAttribute("id"))!);
  const main = sheet.getByRole("navigation", { name: "Main" });
  await expect(main.getByRole("link")).toHaveText(["Home", "Packages", "Projects", "Lessons", "Drafts", "Data"]);
  // Focus moves to the current page's item, and the view lines sit at the sheet's foot.
  await expect(main.getByRole("link", { name: "Projects" })).toBeFocused();
  await expect(sheet.locator("[data-menu-panel]").getByRole("link", { name: "World Bank staff" })).toHaveAttribute("aria-current", "true");
  expect(await page.evaluate(() => ["header", "[data-page-column]"].map((part) => document.querySelector<HTMLElement>(part)!.inert))).toEqual([true, true]);
  // It slides in from the left edge, 320 px wide and the window's height.
  await expect.poll(async () => Object.values((await sheet.boundingBox())!)).toEqual([0, 0, 320, 900]);
  const motion = (el: Element) => [getComputedStyle(el).transitionDuration, getComputedStyle(el).transitionTimingFunction];
  expect(await sheet.evaluate(motion)).toEqual(["0.2s", "cubic-bezier(0.32, 0.72, 0, 1)"]);

  await page.keyboard.press("Escape");
  await expect(sheet).toHaveCount(0);
  await expect(menu).toHaveAttribute("aria-expanded", "false");
  await expect(menu).toBeFocused();
  expect(await page.locator("[data-sidebar]").evaluate(motion)).toEqual(["0.12s, 0s", "cubic-bezier(0.23, 1, 0.32, 1), linear"]);

  await menu.click();
  await sheet.getByRole("button", { name: "Close the menu" }).click();
  await expect(sheet).toHaveCount(0);
  await expect(menu).toBeFocused();

  await menu.click();
  await page.locator("[data-scrim]").click({ position: { x: 1000, y: 450 } });
  await expect(sheet).toHaveCount(0);
  await expect(menu).toBeFocused();
  expect(await page.evaluate(() => document.querySelector<HTMLElement>("header")!.inert)).toBe(false);

  await page.setViewportSize({ width: 1024, height: 900 });
  await expect(page.getByRole("button", { name: "View: World Bank staff" })).toBeVisible();
  await expect(menu).toBeHidden();
});

// Every pill label the view switch shows (ticket 40; the 40 brief, 3.2) fits the bar at 1024 px.
const PILLS: [string, string][] = [
  ["", "View: World Bank staff"],
  ["?pill=officer", "View: Agency officer"],
  ["?pill=piu", "Preview: Agency officer"],
  ["?pill=public", "Preview: Public"],
];

test("at 1024 px the whole bar fits on one line, with no overflow, with every pill label", async ({ page }) => {
  await page.setViewportSize({ width: 1024, height: 900 });
  for (const [query, label] of PILLS) {
    await page.goto(`/gallery/navigation${query}`);
    await expect(page.getByRole("button", { name: label })).toBeVisible();
    const bar = page.locator("[data-nav-bar] > .layout");
    expect(await bar.evaluate((el) => el.scrollWidth <= el.clientWidth), label).toBe(true);
    expect((await page.locator("[data-nav-bar]").boundingBox())!.height, label).toBe(56);
  }
});

test("the view pill opens who is signed in and which view this is", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/gallery/navigation");
  await page.getByRole("button", { name: "View: World Bank staff" }).click();
  const dialog = page.getByRole("dialog", { name: "Your view" });
  await expect(dialog).toContainText("Signed in as ana.example@worldbank.org");
  await expect(dialog.getByRole("link", { name: "World Bank staff" })).toHaveAttribute("aria-current", "true");
  await page.keyboard.press("Escape");
  await expect(dialog).toBeHidden();
  await expect(page.getByRole("button", { name: "View: World Bank staff" })).toBeFocused();
});

// Turning a tablet to portrait hides the pill below 1024 px. The popover closes with it, as the
// Menu closes when the window widens, rather than hang from nothing at the top of the page.
test("narrowing the window below 1024 px closes the open view popover", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/gallery/navigation");
  await page.getByRole("button", { name: "View: World Bank staff" }).click();
  const dialog = page.getByRole("dialog", { name: "Your view" });
  await expect(dialog).toBeVisible();
  await page.setViewportSize({ width: 900, height: 900 });
  await expect(dialog).toBeHidden();
  await expect(page.getByRole("button", { name: "Menu", exact: true })).toHaveAttribute("aria-expanded", "false");
});

// DESIGN.md section 10: a focus order people can follow. When the window crosses 1024 px, the
// control that had focus can vanish with its half of the bar. Focus then moves to the control
// that now holds the same thing, so the next Tab starts from where the reader was.
test("a resize across 1024 px moves focus to the control that now holds the same thing", async ({ page }) => {
  const pill = page.getByRole("button", { name: "View: World Bank staff" });
  const menu = page.getByRole("button", { name: "Menu", exact: true });

  // The view popover, opened from the keyboard, closes when the window narrows, and focus goes
  // to the Menu button, which holds the view lines below 1024 px.
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/gallery/navigation");
  await pill.focus();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("dialog", { name: "Your view" })).toBeVisible();
  await page.setViewportSize({ width: 900, height: 900 });
  await expect(page.getByRole("dialog", { name: "Your view" })).toBeHidden();
  await expect(menu).toBeFocused();

  // An item in the open Menu sheet stays focused when the window widens: the sheet closes and the item is the
  // sidebar's (ticket 92).
  await menu.press("Enter");
  const lessons = page.locator("[data-sidebar] [data-nav-item=lessons]");
  await lessons.focus();
  await page.setViewportSize({ width: 1440, height: 900 });
  await expect(page.getByRole("dialog", { name: "Menu" })).toHaveCount(0);
  await expect(page.locator("[data-menu-button]")).toHaveAttribute("aria-expanded", "false");
  await expect(lessons).toBeFocused();

  // An item in the sidebar goes to the Menu button when the window narrows, and the Menu button goes
  // to the pill when it widens again.
  await page.setViewportSize({ width: 900, height: 900 });
  await expect(menu).toBeFocused();
  await page.setViewportSize({ width: 1440, height: 900 });
  await expect(pill).toBeFocused();
});

test("the footer reads DESIGN.md section 8's disclaimer word for word on every page the gallery renders", async ({ page }) => {
  const footer = await footerSentence();
  const paths = await galleryPaths(page);
  expect(paths.length).toBeGreaterThan(10);
  for (const path of paths) {
    await page.goto(path);
    await expect(page.getByRole("contentinfo"), path).toHaveText(footer);
  }
});
