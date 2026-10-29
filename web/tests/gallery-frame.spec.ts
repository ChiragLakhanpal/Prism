// The gallery's navigation, the bar, the ask bar with its box, and the footer match the blueprint's Home wireframe and
// DESIGN.md sections 5 and 8 (criteria 3 and 4 of ticket 02; ticket 93's top bar; ticket 113's ask bar).
import { expect, mockApi, recorded, test } from "./mocked";
import { footerSentence } from "./design-md";
import { galleryPaths } from "./gallery-pages";

const NAVY = "rgb(0, 34, 68)";
const TINT = "rgb(233, 247, 253)";
const PRIMARY = "rgb(0, 67, 112)";
// WCAG 1.4.12's text spacing, as a person's own style sheet sets it.
const TEXT_SPACING =
  "* { line-height: 1.5 !important; letter-spacing: 0.12em !important; word-spacing: 0.16em !important; } p { margin-bottom: 2em !important; }";
const PACKAGE = "KE-NWWDA-541055-CW-RFB";

test("the navy bar is 56 px tall with the logo slot, the wordmark and the view switch, and no section", async ({ page }) => {
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

  // Left to right: logo, wordmark, then the view switch 24 px from the right edge (ticket 93). The box left the bar for
  // the page column's foot (ticket 113).
  const pill = page.getByRole("button", { name: "View: World Bank staff" });
  const pillBox = (await pill.boundingBox())!;
  expect(wordmark.x).toBeGreaterThan(logo.x);
  expect(pillBox.x).toBeGreaterThan(wordmark.x + wordmark.width);
  expect(Math.round(1440 - (pillBox.x + pillBox.width))).toBe(24);
  await expect(bar.getByRole("combobox")).toHaveCount(0);
  await expect(pill.locator("svg.lucide-chevron-down")).toHaveCount(1);
  // DESIGN.md section 5: the view switch is a 32 px control with a control's 4 px corners, not a 44 px button.
  expect(pillBox.height).toBe(32);
  expect(await pill.evaluate((el) => getComputedStyle(el).borderRadius)).toBe("4px");
});

// Ticket 92 (DESIGN.md section 5, Sidebar): Home, the sections in order, Data at the foot; the current item in tint with
// a 3 px primary bar. Ticket 110: the rail of 64 px rests at every width from 1024 px, the order is Home, Projects,
// Packages, Lessons, Drafts and Data, and the open sidebar (?sidebar=open in the gallery) is 224 px. The gallery draws
// Projects current.
test("from 1024 px the sidebar holds Home and the sections in order, a 64 px rail at rest and 224 px wide when opened", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/gallery/navigation");
  const main = page.getByRole("navigation", { name: "Main" });
  for (const [width, wide, path] of [[1920, 64, ""], [1440, 64, ""], [1024, 64, ""], [1440, 224, "?sidebar=open"], [1024, 224, "?sidebar=open"]] as const) {
    if (path) await page.goto(`/gallery/navigation${path}`);
    await page.setViewportSize({ width, height: 900 });
    await expect(main.locator("[data-nav-item]"), `${width} px`).toHaveText(["Home", "Projects", "Packages", "Lessons", "Drafts", "Data"]);
    expect((await page.locator("[data-sidebar-column]").boundingBox())!.width, `${width} px`).toBe(wide);
    // The stamp sits under Data while the sidebar is open, and hides in the rail (ticket 93).
    await expect(main.locator("[data-stamp]"), `${width} px`).toBeVisible({ visible: wide === 224 });
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
  // The rail hides the sub-item that carries the mark, so Projects carries the tint and the bar itself (ticket 99;
  // DESIGN.md section 2's one current mark, never color alone).
  const mark = await page.locator("[data-nav-item=projects]").evaluate((link) => {
    const bar = getComputedStyle(link, "::before");
    return { fill: getComputedStyle(link).backgroundColor, bar: [bar.width, bar.backgroundColor] };
  });
  expect(mark).toEqual({ fill: TINT, bar: ["3px", PRIMARY] });
});

test("below 360 px the Menu button hides its word from sight and keeps its name, 44 by 44 px", async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 900 });
  await page.goto("/gallery/navigation");
  const menu = page.getByRole("button", { name: "Menu", exact: true });
  const size = (await menu.boundingBox())!;
  expect([size.width, size.height]).toEqual([44, 44]);
  expect(await menu.locator("span").evaluate((el) => el.getBoundingClientRect().width)).toBeLessThanOrEqual(1);
});

// Ticket 113: the box floats at the page column's foot, centered in it, 640 px wide and 16 px above the window's bottom
// edge, on surface with 4 px corners; the stamp sits at the sidebar's foot. The gallery draws the sidebar open here, so
// the page column is the window less 224 px. Off the navy bar, its focus ring is focus.
test("the box floats centered at the page column's foot, the stamp sits at the sidebar's foot, and / focuses the box", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/gallery/navigation?sidebar=open");

  const box = page.locator("[data-box-slot] form > [data-focus-ring]");
  expect(Object.values((await box.boundingBox())!)).toEqual([224 + (1440 - 224 - 640) / 2, 900 - 16 - 40, 640, 40]);
  expect(await box.evaluate((el) => [getComputedStyle(el).backgroundColor, getComputedStyle(el).borderRadius])).toEqual(["rgb(255, 255, 255)", "4px"]);
  await expect(page.locator("[data-box-slot] [data-stamp]")).toHaveCount(0);
  await expect(page.locator("[data-sidebar] [data-stamp] a")).toHaveText("Data updated Oct 21");

  await page.locator("h1").click();
  await page.keyboard.press("/");
  await expect(page.locator("[data-box-slot]").getByRole("combobox", { name: /Open a project/ })).toBeFocused();
  // While anything in it has focus, the box shows the focus ring around it.
  expect(await box.evaluate((el) => [getComputedStyle(el).outlineStyle, getComputedStyle(el).outlineColor])).toEqual(["solid", "rgb(182, 73, 12)"]);
});

// Ticket 93: on a package page the box keeps one row from 1024 px, with the chip's reference and "Ask about this package"
// uncut, and the page never scrolls sideways.
test("on a package page the box keeps one row from 1024 px, with the chip's reference and its placeholder uncut", async ({ page }) => {
  await mockApi(page, {
    "/api/me": { body: await recorded("me.json") },
    "/api/freshness": { body: await recorded("freshness.json") },
    [`/api/packages/${PACKAGE}`]: { body: await recorded("package-ke-nwwda-541055.json") },
    [`/api/packages/${PACKAGE}/comparables`]: { body: await recorded("comparables-ke-nwwda-541055.json") },
  });
  await page.goto(`/packages/${PACKAGE}`);
  await expect(page.locator("main h1")).toBeVisible();
  for (const width of [1440, 1280, 1024]) {
    await page.setViewportSize({ width, height: 900 });
    expect((await page.locator("[data-box-slot] form > [data-focus-ring]").boundingBox())!.height, `${width} px`).toBe(40);
    const chip = page.locator("[data-box-slot] [data-scope-chip]");
    await expect(chip, `${width} px`).toContainText(PACKAGE);
    expect((await chip.boundingBox())!.height, `${width} px: the reference on one line`).toBe(32);
    const placeholder = page.locator("[data-box-slot] [data-placeholder]");
    await expect(placeholder).toHaveText("Ask about this package");
    expect(await placeholder.evaluate((el) => el.scrollWidth <= el.clientWidth), `${width} px: the placeholder is cut`).toBe(true);
    expect(await page.evaluate(() => document.documentElement.scrollWidth), `${width} px`).toBeLessThanOrEqual(width);
  }
});

// Ticket 92 (DESIGN.md section 5, Menu sheet): below 1024 px the sidebar's items are the Menu sheet, a modal dialog from
// the left that slides in over 200 ms on ease-drawer and out over 120 ms, with the page and the bar inert behind it.
test("below 1024 px the Menu button opens the Menu sheet, a modal dialog; Escape, Close the menu and the scrim close it", async ({ page }) => {
  await page.setViewportSize({ width: 1023, height: 900 });
  await page.goto("/gallery/navigation");
  // From 768 px the view switch stays in the bar (ticket 93).
  await expect(page.getByRole("button", { name: "View: World Bank staff" })).toBeVisible();
  await expect(page.getByRole("navigation", { name: "Main" })).toHaveCount(0);

  const menu = page.getByRole("button", { name: "Menu", exact: true });
  const sheet = page.getByRole("dialog", { name: "Menu" });
  await expect(menu).toHaveAttribute("aria-expanded", "false");
  await menu.click();
  await expect(menu).toHaveAttribute("aria-expanded", "true");
  await expect(sheet).toHaveAttribute("aria-modal", "true");
  await expect(menu).toHaveAttribute("aria-controls", (await sheet.getAttribute("id"))!);
  const main = sheet.getByRole("navigation", { name: "Main" });
  await expect(main.locator("[data-nav-item]")).toHaveText(["Home", "Projects", "Packages", "Lessons", "Drafts", "Data"]);
  // Focus moves to the current page's item. The stamp sits under Data; the view lines join the sheet's foot only below
  // 768 px, where the view switch leaves the bar (ticket 93).
  await expect(main.getByRole("link", { name: "Projects" })).toBeFocused();
  await expect(main.locator("[data-stamp] a")).toHaveText("Data updated Oct 21");
  await expect(sheet.locator("[data-menu-panel]")).toBeHidden();
  expect(await page.evaluate(() => ["header", "[data-page-column]"].map((part) => document.querySelector<HTMLElement>(part)!.inert))).toEqual([true, true]);
  // It slides in from the left edge, 320 px wide and the window's height.
  await expect.poll(async () => Object.values((await sheet.boundingBox())!)).toEqual([0, 0, 320, 900]);
  const motion = (el: Element) => [getComputedStyle(el).transitionDuration, getComputedStyle(el).transitionTimingFunction];
  expect(await sheet.evaluate(motion)).toEqual(["0.2s", "cubic-bezier(0.32, 0.72, 0, 1)"]);

  await page.keyboard.press("Escape");
  // A sheet that closes slides out; a narrowing window hides the sidebar with no motion (ticket 60).
  expect(await page.locator("[data-sidebar]").evaluate(motion)).toEqual(["0.12s, 0s", "cubic-bezier(0.23, 1, 0.32, 1), linear"]);
  await expect(sheet).toHaveCount(0);
  await expect(menu).toHaveAttribute("aria-expanded", "false");
  await expect(menu).toBeFocused();

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

// Every label the view switch shows (ticket 40; the 40 brief, 3.2) fits the bar at 1024 px, with WCAG 1.4.12's text
// spacing too (ticket 93): the label is whole, the bar keeps its one row, the package's box at the page's foot keeps its
// one row (ticket 113), and nothing scrolls sideways.
const PILLS: [string, string][] = [
  ["", "View: World Bank staff"],
  ["&pill=officer", "View: Agency officer"],
  ["&pill=piu", "Preview: Agency officer"],
  ["&pill=public", "Preview: Public"],
];

test("at 1024 px the whole bar fits on one row with every view label, and a package's box keeps one row, with text spacing too", async ({ page }) => {
  await page.setViewportSize({ width: 1024, height: 900 });
  for (const spacing of [false, true]) {
    for (const [query, label] of PILLS) {
      const named = `${label}${spacing ? ", with text spacing" : ""}`;
      await page.goto(`/gallery/navigation?scope=${PACKAGE}${query}`);
      if (spacing) await page.addStyleTag({ content: TEXT_SPACING });
      const pill = page.getByRole("button", { name: label });
      await expect(pill).toBeVisible();
      expect(await pill.evaluate((el) => el.scrollWidth <= el.clientWidth), `${named}: the label is whole`).toBe(true);
      const at = (await pill.boundingBox())!;
      const box = (await page.locator("[data-box-slot] form > [data-focus-ring]").boundingBox())!;
      expect(Math.round(1024 - (at.x + at.width)), named).toBe(24);
      expect(box.height, `${named}: the box keeps one row`).toBe(40);
      expect(await page.locator("[data-bar-row]").evaluate((el) => el.scrollWidth <= el.clientWidth), named).toBe(true);
      expect((await page.locator("[data-nav-bar]").boundingBox())!.height, named).toBe(56);
      expect(await page.evaluate(() => document.documentElement.scrollWidth), named).toBeLessThanOrEqual(1024);
    }
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

// Narrowing the window below 768 px hides the view switch (ticket 93). The popover closes with it, as the
// Menu closes when the window widens, rather than hang from nothing at the top of the page.
test("narrowing the window below 768 px closes the open view popover", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/gallery/navigation");
  await page.getByRole("button", { name: "View: World Bank staff" }).click();
  const dialog = page.getByRole("dialog", { name: "Your view" });
  await expect(dialog).toBeVisible();
  await page.setViewportSize({ width: 900, height: 900 });
  await expect(dialog).toBeVisible();
  await page.setViewportSize({ width: 700, height: 900 });
  await expect(dialog).toBeHidden();
  await expect(page.getByRole("button", { name: "Menu", exact: true })).toHaveAttribute("aria-expanded", "false");
});

// DESIGN.md section 10: a focus order people can follow. When the window crosses 768 or 1024 px, the
// control that had focus can vanish with its part of the bar. Focus then moves to the control
// that now holds the same thing, so the next Tab starts from where the reader was.
test("a resize across 768 or 1024 px moves focus to the control that now holds the same thing", async ({ page }) => {
  const pill = page.getByRole("button", { name: "View: World Bank staff" });
  const menu = page.getByRole("button", { name: "Menu", exact: true });

  // The view popover, opened from the keyboard, closes when the window narrows below 768 px, and focus goes
  // to the Menu button, which holds the view lines there (ticket 93).
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/gallery/navigation");
  await pill.focus();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("dialog", { name: "Your view" })).toBeVisible();
  await page.setViewportSize({ width: 700, height: 900 });
  await expect(page.getByRole("dialog", { name: "Your view" })).toBeHidden();
  await expect(menu).toBeFocused();
  // The view switch, focused at 900 px, goes to the Menu button below 768 px too.
  await page.setViewportSize({ width: 900, height: 900 });
  await pill.focus();
  await page.setViewportSize({ width: 700, height: 900 });
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

  // Ticket 60 (ticket 92's review, follow-up 2): "Close the menu", which hides from 1024 px, hands focus to the view pill
  // when the window widens with the sheet open, never to the page.
  await page.setViewportSize({ width: 900, height: 900 });
  await menu.click();
  await page.getByRole("button", { name: "Close the menu" }).focus();
  await page.setViewportSize({ width: 1440, height: 900 });
  await expect(page.getByRole("dialog", { name: "Menu" })).toHaveCount(0);
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
