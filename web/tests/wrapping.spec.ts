// Ticket 59, criterion 5: no STEP reference, date, "page N" or "Not checked:" label breaks inside itself in the box
// list, the answer panel, the Summary's source cells, the hardest documents' "Open at page" links or the check line,
// at 320, 390, 1024 and 1440 px. Each test opens its page once and turns the window to each width. The answers are
// the server's own, recorded in tests/fixtures/api.
import type { Page } from "@playwright/test";
import { hubApi } from "./hub-api";
import { expect, mockApi, mockShell, recorded, test } from "./mocked";
import { fontsLoaded } from "./settled";
import { brokenInside, WHOLE } from "./unbroken";

const WIDTHS = [320, 390, 1024, 1440];
const PACKAGE = "KE-NWWDA-541055-CW-RFB";

// Each width in turn, with the fonts loaded and two frames drawn, so the lines are the ones a reader sees.
async function atEachWidth(page: Page, check: (width: number) => Promise<void>) {
  await fontsLoaded(page);
  for (const width of WIDTHS) {
    await page.setViewportSize({ width, height: 900 });
    await page.evaluate(() => new Promise((done) => requestAnimationFrame(() => requestAnimationFrame(done))));
    await check(width);
  }
}

test("the box list and the answer panel keep a STEP reference whole, and the check line keeps Not checked: whole", async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 900 });
  await mockApi(page, {
    "/api/me": { body: await recorded("me.json") },
    "/api/freshness": { body: await recorded("freshness.json") },
    [`/api/packages/${PACKAGE}`]: { body: await recorded("package-ke-nwwda-541055.json") },
    [`/api/packages/${PACKAGE}/comparables`]: { body: await recorded("comparables-ke-nwwda-541055.json") },
    "/api/ask": { body: await recorded("ask-ke-nwwda-541055-past-range.sse") },
  });
  await page.goto(`/packages/${PACKAGE}`);
  await expect(page.locator("main h1")).toBeVisible();

  // Free text on a package page offers "Ask this" within the package, its second line "Within KE-NWWDA-541055-CW-RFB".
  await page.keyboard.press("/");
  await page.keyboard.type("Which steps took longest");
  const list = page.getByRole("listbox", { name: "What Enter will do" });
  await expect(list.getByRole("option").first()).toContainText(PACKAGE);
  await atEachWidth(page, async (width) => {
    const { found, broken } = await brokenInside(page, "[data-box-popup] [role=option]", WHOLE.reference);
    expect(found, `${width} px: the references in the list`).toBeGreaterThan(0);
    expect(broken, `${width} px`).toEqual([]);
  });

  await page.keyboard.press("Enter");
  const panel = page.getByRole("region", { name: "Answer" });
  await expect(panel.locator("[data-answer]:not([data-answer=streaming])")).toBeVisible();
  await expect(panel.locator("[data-asked]")).toContainText(`Asked within ${PACKAGE}`);
  await atEachWidth(page, async (width) => {
    const asked = await brokenInside(page, "[data-answer-panel] [data-asked]", WHOLE.reference);
    expect(asked.found, `${width} px: the Asked line`).toBe(1);
    expect(asked.broken, `${width} px`).toEqual([]);
    const label = await brokenInside(page, "[data-answer-panel] [data-check-line]", WHOLE.notChecked);
    expect(label.found, `${width} px: the check line's label`).toBe(1);
    expect(label.broken, `${width} px`).toEqual([]);
  });
});

test("the Summary's source cells keep each date whole, in the fact tables and in the loan history's cards", async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 900 });
  await mockApi(page, {
    ...(await hubApi()),
    "/api/projects/P156634": { body: await recorded("project-p156634.json") },
    "/api/projects/P156634/summary": { body: await recorded("summary-p156634.json") },
  });
  await page.goto("/projects/P156634");
  await expect(page.locator("[data-closing-history=rows]")).toBeVisible();
  await atEachWidth(page, async (width) => {
    const facts = await brokenInside(page, "[data-fact-source]", WHOLE.date);
    expect(facts.found, `${width} px: the fact tables' dates`).toBeGreaterThan(3);
    expect(facts.broken, `${width} px`).toEqual([]);
    const history = await brokenInside(page, "[data-closing-history=rows] [data-table-view]", WHOLE.date);
    expect(history.found, `${width} px: the loan history's dates`).toBeGreaterThan(2);
    expect(history.broken, `${width} px`).toEqual([]);
  });
});

test("the hardest documents keep page and its number together in each Open at page link", async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 900 });
  await mockShell(page);
  await page.route("**/api/data/readiness*", async (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: await recorded("data-readiness.json") }),
  );
  await page.route("**/api/data/sources", async (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: await recorded("data-sources.json") }),
  );
  await page.goto("/data");
  const shelf = page.locator("[data-readiness-table=shelf]");
  await shelf.getByRole("button", { name: "Show the documents" }).click();
  await expect(shelf).toHaveAttribute("data-zone", "panel");
  await atEachWidth(page, async (width) => {
    const { found, broken } = await brokenInside(page, "[data-readiness-table=shelf] a", WHOLE.page);
    expect(found, `${width} px: the page links`).toBeGreaterThanOrEqual(5);
    expect(broken, `${width} px`).toEqual([]);
  });
});
