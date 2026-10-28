// The space line (ticket 110; DESIGN.md section 5, Space line), at seam 4: where a reading page keeps columns 9 to 12
// free for the evidence drawer (the package page from a page area of 75rem, a draft's page from a frame of 75rem), one
// caption line in those columns says what the space is for while no drawer is open. It hides when the drawer opens and
// moves nothing else. The words are the ticket's, copied here so the test checks the copy file against an independent
// source.
import type { Page } from "@playwright/test";
import { scan } from "./axe";
import { expect, mockApi, recorded, test } from "./mocked";

const PACKAGE = "KE-NWWDA-541055-CW-RFB";
const MOWI = "KE-MOWI-47509-CW-RFB";
const DRAFT = "/drafts/draft-0001";
const PACKAGE_LINE = "Select a dot on the chart, an underlined number or a numbered source, and its records open here.";
const DRAFT_LINE = "Select a numbered source, and its record opens here.";

// At 1440 px beside the 64 px rail the frame is 1376 px: 40 px margins leave 1296 px, whose 12 columns of 78.67 px and
// 11 gutters of 32 px put column 9 at 64 + 40 + 8 * 110.67 = 989 px, and column 12's end at 1440 - 40 = 1400 px.
const COLUMN_9 = 989;
const COLUMN_12_END = 1400;

async function openPackage(page: Page, width: number) {
  const api = `/api/packages/${PACKAGE}`;
  await mockApi(page, {
    "/api/me": { body: await recorded("me.json") },
    "/api/freshness": { body: await recorded("freshness.json") },
    [api]: { body: await recorded("package-ke-nwwda-541055.json") },
    [`${api}/comparables`]: { body: await recorded("comparables-ke-nwwda-541055.json") },
    [`${api}/estimate`]: { body: await recorded("estimate-ke-nwwda-541055.json") },
    [`${api}/risks`]: { body: await recorded("risks-ke-nwwda-541055.json") },
    [`${api}/steps`]: { body: await recorded("steps-ke-nwwda-541055.json") },
    "/api/evidence": { body: await recorded("evidence-package-ke-mowi-47509.json") },
    "/api/evidence/opened": { body: '{"opened":[],"recorded":true}' },
  });
  await page.setViewportSize({ width, height: width < 768 ? 844 : 900 });
  await page.goto(`/packages/${PACKAGE}`);
  await expect(page.locator("[data-range-chart]")).toBeVisible();
  await page.evaluate(() => document.fonts.ready);
}

async function openDraft(page: Page, width: number) {
  await mockApi(page, {
    "/api/me": { body: await recorded("me.json") },
    "/api/freshness": { body: await recorded("freshness.json") },
    "/api/drafts/existing": { body: '{"draft":null}' },
    [`/api${DRAFT}`]: { body: await recorded("drafts-review-notes-draft.json") },
    "/api/evidence": { body: await recorded("evidence-icr-p130164-54.json") },
    "/api/evidence/opened": { body: '{"opened":[],"recorded":true}' },
  });
  await page.setViewportSize({ width, height: width < 768 ? 844 : 900 });
  await page.goto(DRAFT);
  await expect(page.locator("[data-draft-page=draft]")).toBeVisible();
  await page.evaluate(() => document.fonts.ready);
}

async function violations(page: Page) {
  await page.waitForFunction(() => document.getAnimations().every((animation) => animation.playState !== "running"));
  const results = await scan(page);
  return results.violations.map((v) => `${v.id}: ${v.nodes.map((node) => node.target.join(" ")).join(", ")}`);
}

const PAGES = [
  {
    name: "the package page",
    line: PACKAGE_LINE,
    open: openPackage,
    // The work: the column the page's head and sections sit in.
    work: "[data-package-page]",
    head: "[data-breadcrumb]",
    // A dot on the chart opens its package's records.
    opener: (page: Page) => page.locator(`[data-dot-target][aria-label^="${MOWI},"]`),
  },
  {
    name: "a draft",
    line: DRAFT_LINE,
    open: openDraft,
    work: "[data-document-column]",
    head: "[data-breadcrumb]",
    // A numbered source in a note opens its record.
    opener: (page: Page) => page.locator("[data-draft-notes] [data-view]:visible [data-citation='2']").first(),
  },
];

for (const { name, line, open, work, head, opener } of PAGES) {
  test(`at 1440 px the space line on ${name} sits in columns 9 to 12 level with the page head, and hides when the drawer opens while the work stays put`, async ({ page }) => {
    await open(page, 1440);
    const space = page.locator("[data-space-line]");
    await expect(space).toHaveText(line);
    await expect(space.locator("svg.lucide-panel-right")).toHaveCount(1);
    const look = await space.evaluate((el) => {
      const style = getComputedStyle(el);
      const icon = el.querySelector("svg")!.getBoundingClientRect();
      return [style.fontSize, style.lineHeight, style.color, icon.width, icon.height];
    });
    expect(look).toEqual(["13px", "20px", "rgb(75, 94, 113)", 16, 16]);
    const box = (await space.boundingBox())!;
    expect([Math.round(box.x), Math.round(box.x + box.width)]).toEqual([COLUMN_9, COLUMN_12_END]);
    expect(Math.round(box.y)).toBe(Math.round((await page.locator(head).first().boundingBox())!.y));
    expect(await violations(page)).toEqual([]);

    const before = (await page.locator(work).boundingBox())!;
    const h1 = (await page.locator("main h1").boundingBox())!.x;
    const target = opener(page);
    await target.scrollIntoViewIfNeeded();
    const spot = (await target.boundingBox())!;
    await page.mouse.click(spot.x + spot.width / 2, spot.y + spot.height / 2);
    await expect(page.getByRole("dialog")).toBeVisible();
    await expect(space).toHaveCount(0);
    expect((await page.locator(work).boundingBox())!.x).toBe(before.x);
    expect((await page.locator("main h1").boundingBox())!.x).toBe(h1);
    await page.keyboard.press("Escape");
    await expect(page.getByRole("dialog")).toHaveCount(0);
    await expect(space).toBeVisible();
  });

  test(`the space line on ${name} shows neither at 1024 nor at 390 px, and axe finds nothing at 390 px`, async ({ page }) => {
    await open(page, 1024);
    await expect(page.locator("main h1")).toBeVisible();
    await expect(page.locator("[data-space-line]")).toBeHidden();
    await page.setViewportSize({ width: 390, height: 844 });
    await expect(page.locator("[data-space-line]")).toBeHidden();
    expect(await violations(page)).toEqual([]);
  });
}
