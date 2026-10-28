// The workspace layout and the zone parts (ticket 95; DESIGN.md section 5, Task zone, Foot strip, Stage label, Side
// panel and Page head; section 4, Page layouts): the gallery's zones page shows each part in each state at its
// worst-case strings, and its workspace sample lays out as a workspace page does, beside the evidence drawer.
import type { Locator, Page } from "@playwright/test";
import { scan } from "./axe";
import { expect, test } from "./mocked";

const WHITE = "rgb(255, 255, 255)";
const PAGE = "rgb(245, 247, 249)";
const LINE = "rgb(218, 227, 235)";

async function openZones(page: Page, width: number, query = "") {
  await page.setViewportSize({ width, height: 900 });
  await page.goto(`/gallery/zones${query}`);
  await expect(page.locator("[data-gallery-root] h1").first()).toBeVisible();
  await page.evaluate(() => document.fonts.ready);
}

const look = (zone: Locator) =>
  zone.evaluate((el) => {
    const style = getComputedStyle(el);
    return {
      fill: style.backgroundColor,
      corner: style.borderTopLeftRadius,
      under: `${style.borderBottomWidth} ${style.borderBottomStyle} ${style.borderBottomColor}`,
    };
  });

const sequence = (page: Page) => page.locator("[data-state-section=sequence]");

test("a zone with evidence is a white panel with 8 px corners that ends in a foot strip, and a closed or sentence-only zone is a row on the page grey with a 1 px line under it", async ({ page }) => {
  await openZones(page, 1440);
  const panel = sequence(page).locator("[data-zone=panel]").first();
  expect(await look(panel)).toEqual({ fill: WHITE, corner: "8px", under: `1px solid ${LINE}` });
  const foot = panel.locator("[data-foot-strip]").last();
  await expect(foot).toBeVisible();
  expect(await foot.evaluate((el) => getComputedStyle(el).backgroundColor)).toBe(PAGE);

  const rows = sequence(page).locator("[data-zone=row]");
  await expect(rows).toHaveCount(3);
  for (const row of await rows.all()) {
    expect(await look(row)).toEqual({ fill: "rgba(0, 0, 0, 0)", corner: "0px", under: `1px solid ${LINE}` });
  }
  // Space falls only between blocks that show: the closed row's hidden body adds nothing under its summary, which ends
  // 16 px above the row's line.
  const closed = sequence(page).locator("section[data-section=steps]");
  await expect(closed.locator("[data-section-body]")).toBeHidden();
  expect(
    await closed.evaluate((el) => Math.round(el.getBoundingClientRect().bottom - 1 - el.querySelector("[data-section-summary]")!.getBoundingClientRect().bottom)),
  ).toBe(16);
});

// The workspace sample (DESIGN.md section 4, Page layouts, Workspace). Worked out by hand from section 4's grid: at
// 1440 px with the sidebar open (224 px) and at 1280 px as a rail (64 px) the frame is 1216 px, the margin 40 and the
// gutter 32, so the content is 1136 px and a column (1136 - 11 x 32) / 12 = 65.33 px. Columns 1 to 7 are then
// 7 x 65.33 + 6 x 32 = 649.33 px, and columns 9 to 12 start 8 x (65.33 + 32) = 778.67 px in and are 357.33 px wide.
const WIDE_SAMPLES = [
  { width: 1440, rest: "open", left: 264 },
  { width: 1280, rest: "rail", left: 104 },
];
const box = (locator: Locator) =>
  locator.evaluate((el) => {
    const rect = el.getBoundingClientRect();
    return { left: rect.left, right: rect.right, width: rect.width };
  });
const near = (value: number, expected: number) => expect(value).toBeCloseTo(expected, 0);

async function openSample(page: Page, width: number, rest: string, height = 900) {
  await page.setViewportSize({ width, height });
  await page.goto(`/gallery/zones?sample=workspace&sidebar=${rest}`);
  await expect(page.locator("main h1")).toBeVisible();
  await page.evaluate(() => document.fonts.ready);
}

for (const { width, rest, left } of WIDE_SAMPLES) {
  test(`at ${width} px with the sidebar ${rest}, the work spans columns 1 to 7 and keeps its place and width when the drawer opens, which fills from the work's end plus a gutter to the window's edge while the side panel hides`, async ({ page }) => {
    await openSample(page, width, rest);
    const work = page.locator("[data-workspace-work]");
    const side = page.locator("[data-side-slot]");
    const shut = await Promise.all((await work.all()).map(box));
    for (const part of shut) {
      near(part.left, left);
      near(part.width, 649.33);
    }
    await expect(side).toBeVisible();
    near((await box(side)).left, left + 778.67);
    near((await box(side)).width, 357.33);
    await expect(page.locator("[data-facts-line]")).toBeHidden();

    // The side panel's marker opens the plan row in the drawer, which takes the side panel's place.
    await side.getByRole("link", { name: /^Source 1:/ }).click();
    const drawer = page.locator("[data-evidence-drawer=drawer]");
    await expect(drawer).toBeVisible();
    await expect(side).toBeHidden();
    expect(await Promise.all((await work.all()).map(box))).toEqual(shut);
    const opened = await box(drawer);
    near(opened.left, left + 649.33 + 32);
    near(opened.right, width);
    expect(opened.width).toBeGreaterThanOrEqual(384);
    expect(opened.width).toBeLessThanOrEqual(600);
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(width);
  });
}

// Below a frame of 75rem: at 1200 px with the sidebar open the frame is 976 px, and at 1024 px as a rail 960 px. The
// margins are 40 and 32 px, so the one column is 976 - 80 = 896 and 960 - 64 = 896 px wide.
for (const { width, rest, left } of [
  { width: 1200, rest: "open", left: 264 },
  { width: 1024, rest: "rail", left: 96 },
]) {
  test(`at ${width} px with the sidebar ${rest}, the workspace sample is one column with its facts line in the head`, async ({ page }) => {
    await openSample(page, width, rest);
    for (const part of await page.locator("[data-workspace-work]").all()) {
      const found = await box(part);
      near(found.left, left);
      near(found.width, 896);
    }
    await expect(page.locator("[data-side-slot]")).toBeHidden();
    const facts = page.locator("[data-facts-line]");
    await expect(facts).toBeVisible();
    await expect(facts).toContainText("Request for Bids, Open - International, US$232,524,000, Pending Implementation");
    // Its button opens the same plan row in the drawer.
    await facts.getByRole("button", { name: "Show the plan row" }).click();
    await expect(page.locator("[data-evidence-drawer=drawer]")).toBeVisible();
    await expect(facts.getByRole("button", { name: "Show the plan row" })).toHaveAttribute("aria-expanded", "true");
  });
}

// Plan 7.10's worst cases: the 257-character STEP description as the h1 and the 35-character reference as the ID line.
const DESCRIPTION_257 =
  "Supply and delivery of al l small customer meters(3,510 no.) to AMR enabled meter s(DN15mm-32mm) and majo r customer meters (81 no-ult rasonic meters with integrate d radio module of size DN40, DN50-DN150mm),15nos.port able meter testing kit and 1n o. bench";
const REFERENCE_35 = "KE-UASIN GISHU COUNTY-571338-CW-RFB";

// Each part of the ID line between its spaces is on one line: none breaks inside itself.
const brokenParts = (page: Page) =>
  page.locator("main [data-id-line]").evaluate((line) =>
    Array.from(line.querySelectorAll(":scope > span")).flatMap((part) => {
      const words = document.createRange();
      words.selectNodeContents(part);
      const lines = new Set(Array.from(words.getClientRects()).map((rect) => Math.round(rect.top)));
      return lines.size > 1 ? [part.textContent] : [];
    }),
  );

test("with the longest description as the h1 and the longest reference as the ID line, the first zone starts in the first screen at 390 by 844, nothing scrolls sideways at 320 px, and no part of the reference breaks inside itself", async ({ page }) => {
  await openSample(page, 390, "rail", 844);
  await expect(page.locator("main h1")).toHaveText(DESCRIPTION_257);
  await expect(page.locator("main [data-id-line]")).toHaveText(REFERENCE_35);
  const first = await page.locator("main [data-zone]").first().evaluate((el) => el.getBoundingClientRect().top + window.scrollY);
  expect(first).toBeLessThan(844);
  expect(await brokenParts(page)).toEqual([]);

  await page.setViewportSize({ width: 320, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(320);
  expect(await brokenParts(page)).toEqual([]);
});

test("a breadcrumb that wraps never starts a line with a chevron, and each link sits in a 24 px line box", async ({ page }) => {
  await openSample(page, 1440, "open");
  const trail = page.locator("main [data-breadcrumb] ol");
  await expect(trail).toBeVisible();
  const lines = await trail.evaluate((list) => {
    const left = list.getBoundingClientRect().left;
    const chevrons = Array.from(list.querySelectorAll("[data-crumb-chevron]")).map((icon) => Math.round(icon.getBoundingClientRect().left - left));
    const links = Array.from(list.querySelectorAll("a")).map((link) => link.getBoundingClientRect().height);
    return { chevrons, links, height: list.getBoundingClientRect().height };
  });
  // The project's name is too long for the 649 px column, so the trail takes more than one line here.
  expect(lines.height).toBeGreaterThan(24);
  expect(lines.chevrons.every((x) => x > 0)).toBe(true);
  expect(lines.links.every((height) => height >= 24)).toBe(true);
});

const startHere = (page: Page) => page.locator("[data-state-section=tag-under] section[data-zone]");

for (const width of [1440, 390]) {
  test(`at ${width} px a row with an action at its right has its tag under its name, a foot strip line that holds a number you can check is 24 px tall, and a failed first block leaves the header and the second block`, async ({ page }) => {
    await openZones(page, width);
    const zone = startHere(page);
    const placed = await zone.evaluate((el) => {
      const name = el.querySelector("[data-zone-name]")!.getBoundingClientRect();
      const tag = el.querySelector("[data-zone-tag]")!.getBoundingClientRect();
      return { under: tag.top >= name.bottom - 4, left: Math.round(tag.left - name.left) };
    });
    expect(placed).toEqual({ under: true, left: 0 });
    await expect(zone.getByRole("button", { name: "Remove the Start here examples" })).toBeVisible();

    const coverage = sequence(page).locator("[data-foot-strip] [data-coverage]");
    expect(await coverage.evaluate((el) => ({ height: el.getBoundingClientRect().height, line: getComputedStyle(el).lineHeight }))).toEqual({
      height: 24,
      line: "24px",
    });
    // A foot line with no number keeps caption's 20 px line.
    expect(await sequence(page).locator("[data-foot-strip]").last().locator("p").first().evaluate((el) => getComputedStyle(el).lineHeight)).toBe("20px");

    const failed = page.locator("[data-state-section=failed] section[data-zone]");
    const head = await failed.locator("[data-zone-head]").boundingBox();
    const alert = failed.locator("[data-alert=error]");
    await expect(alert).toContainText("I couldn't load the comparable packages for this section.");
    await expect(alert.getByRole("button", { name: "Try again" })).toBeVisible();
    expect((await alert.boundingBox())!.y).toBeGreaterThan(head!.y + head!.height - 1);
    // The second block, Advertised again, keeps its words and its own foot strip.
    const second = failed.locator("[data-block=again]");
    await expect(second.getByRole("heading", { name: "Advertised again" })).toBeVisible();
    await expect(second.locator("+ [data-foot-strip]")).toContainText("Records run through October 13, 2026.");
    await expect(failed.locator("[data-block=took]")).toHaveCount(0);
  });
}

// The rows whose Show button holds the header's right, and the sentence it must stay clear of.
const ringCrossings = (page: Page) =>
  page.locator("[data-zone=row]:has([data-section-toggle])").evaluateAll((rows) =>
    rows.flatMap((row) => {
      const button = row.querySelector("[data-section-toggle]")!.getBoundingClientRect();
      const summary = row.querySelector("[data-section-summary]")!.getBoundingClientRect();
      // The ring: 2 px wide at a 2 px offset.
      const ring = { top: button.top - 4, bottom: button.bottom + 4, left: button.left - 4, right: button.right + 4 };
      const crosses = ring.top < summary.bottom && ring.bottom > summary.top && ring.left < summary.right && ring.right > summary.left;
      return crosses ? [row.getAttribute("data-section")] : [];
    }),
  );

for (const width of [1440, 1024, 390]) {
  test(`at ${width} px a row's Show button's focus ring never crosses its summary`, async ({ page }) => {
    await openZones(page, width);
    expect(await page.locator("[data-zone=row]:has([data-section-toggle])").count()).toBeGreaterThan(1);
    expect(await ringCrossings(page)).toEqual([]);
  });
}

// The zones page itself is scanned by gallery-a11y.spec.ts, as every gallery page is; the workspace sample is a page
// of its own, so it is scanned here, closed at 390 px and with the drawer open at 1440 px.
test("axe finds no WCAG 2.2 AA violation on the workspace sample at 390 px, or at 1440 px with the drawer open", async ({ page }) => {
  await openSample(page, 390, "rail");
  const found = async () => (await scan(page)).violations.map((v) => `${v.id}: ${v.nodes.map((node) => node.target.join(" ")).join(", ")}`);
  expect(await found(), "390").toEqual([]);
  await openSample(page, 1440, "open");
  await page.locator("[data-side-slot]").getByRole("link", { name: /^Source 1:/ }).click();
  await expect(page.locator("[data-evidence-drawer=drawer] h2")).toBeFocused();
  await page.waitForFunction(() => document.getAnimations().every((a) => a.playState !== "running"));
  expect(await found(), "1440 with the drawer").toEqual([]);
});

// Where a zone's number and its name's first letter start on screen.
const edges = (zone: Locator) =>
  zone.evaluate((el) => {
    const number = el.querySelector("[data-zone-number]")!.getBoundingClientRect();
    const name = el.querySelector("[data-zone-name]")!;
    const text = document.createRange();
    text.selectNodeContents(name.lastChild!);
    return { number: Math.round(number.left), name: Math.round(text.getClientRects()[0].left) };
  });

// Every part of an element that has a transition or an animation, other than a control's own color change.
const moving = (zone: Locator) =>
  zone.evaluate((el) => ({
    transitions: [el, ...el.querySelectorAll("*")].filter(
      (node) => !node.matches("button, a") && getComputedStyle(node).transitionDuration.split(",").some((part) => parseFloat(part) > 0),
    ).length,
    animations: el.getAnimations({ subtree: true }).length,
  }));

for (const width of [1440, 390]) {
  test(`at ${width} px a row's number and name sit on the same x as a panel's, and opening a row makes it a panel in place, at once, with focus kept on its button`, async ({ page }) => {
    await openZones(page, width);
    const panel = sequence(page).locator("[data-zone=panel]").first();
    const row = sequence(page).locator("section[data-section=steps]");
    expect(await edges(row)).toEqual(await edges(panel));

    const place = () =>
      row.evaluate((el) => {
        const box = el.getBoundingClientRect();
        return [box.left, box.top + window.scrollY, box.width];
      });
    const before = await place();
    const show = row.getByRole("button", { name: "Show the steps" });
    await expect(show).toHaveAttribute("aria-expanded", "false");
    await show.focus();
    await page.keyboard.press("Enter");
    await expect(row).toHaveAttribute("data-zone", "panel");
    const hide = row.getByRole("button", { name: "Hide the steps" });
    await expect(hide).toBeFocused();
    await expect(hide).toHaveAttribute("aria-expanded", "true");
    // In place: the same section at the same top and width, and nothing on it moves or fades.
    expect(await place()).toEqual(before);
    expect(await moving(row)).toEqual({ transitions: 0, animations: 0 });
    expect(await edges(row)).toEqual(await edges(panel));
  });
}
