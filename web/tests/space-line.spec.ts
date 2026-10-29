// Columns 9 to 12 of a workspace page, at seam 4. Ticket 110's space line said what those columns were for while no
// drawer was open (DESIGN.md section 5, Space line). Since ticket 101 the package page holds its side panel, "From the
// plan row", there, and since ticket 103 a draft's page holds "State of this draft", so no page has a space line. Each
// panel sits level with the page head and hides when the drawer opens in its place, while the work stays put.
import type { Page } from "@playwright/test";
import { scan } from "./axe";
import { expect, mockApi, recorded, test } from "./mocked";

const PACKAGE = "KE-NWWDA-541055-CW-RFB";
const MOWI = "KE-MOWI-47509-CW-RFB";
const DRAFT = "/drafts/draft-0001";

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

test("at 1440 px the package page holds its side panel in columns 9 to 12 level with the page head, and no space line", async ({ page }) => {
  await openPackage(page, 1440);
  await expect(page.locator("[data-space-line]")).toHaveCount(0);
  const side = page.getByRole("region", { name: "From the plan row" });
  const box = (await side.boundingBox())!;
  expect([Math.round(box.x), Math.round(box.x + box.width)]).toEqual([COLUMN_9, COLUMN_12_END]);
  expect(Math.round(box.y)).toBe(Math.round((await page.locator("[data-breadcrumb]").first().boundingBox())!.y));
  // A dot on the chart opens its package's records in the panel's place.
  const target = page.locator(`[data-dot-target][aria-label^="${MOWI},"]`);
  await target.scrollIntoViewIfNeeded();
  const spot = (await target.boundingBox())!;
  await page.mouse.click(spot.x + spot.width / 2, spot.y + spot.height / 2);
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(side).toBeHidden();
  expect(await page.locator("[data-space-line]").count()).toBe(0);
});

test("at 1440 px a draft holds State of this draft in columns 9 to 12 level with the page head, and no space line; the drawer opens in its place while the work stays put", async ({ page }) => {
  await openDraft(page, 1440);
  await expect(page.locator("[data-space-line]")).toHaveCount(0);
  const side = page.getByRole("region", { name: "State of this draft" });
  const box = (await side.boundingBox())!;
  expect([Math.round(box.x), Math.round(box.x + box.width)]).toEqual([COLUMN_9, COLUMN_12_END]);
  expect(Math.round(box.y)).toBe(Math.round((await page.locator("[data-breadcrumb]").first().boundingBox())!.y));
  expect(await violations(page)).toEqual([]);

  const work = page.locator("[data-document-column]");
  const before = (await work.boundingBox())!;
  const h1 = (await page.locator("main h1").boundingBox())!.x;
  const target = page.locator("[data-draft-notes] [data-view]:visible [data-citation='2']").first();
  await target.scrollIntoViewIfNeeded();
  const spot = (await target.boundingBox())!;
  await page.mouse.click(spot.x + spot.width / 2, spot.y + spot.height / 2);
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(side).toBeHidden();
  const after = (await work.boundingBox())!;
  expect([after.x, after.width]).toEqual([before.x, before.width]);
  expect((await page.locator("main h1").boundingBox())!.x).toBe(h1);
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(side).toBeVisible();
});
