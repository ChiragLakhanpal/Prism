// The number tooltip's gate test (ticket 96; DESIGN.md section 5, Number tooltip): on the package workspace, the plan
// check, Home and a draft, one page load each, every number and every range chart dot whose tooltip has an action line
// opens what that line names, no number without an action line opens anything, and no two numbers in one sentence share
// a What sentence unless they share where they came from and what they open. Each later ticket that adds a click to a
// number adds its action line, and this test keeps it honest.
import type { Locator, Page } from "@playwright/test";
import { expect, mockApi, recorded, test, viewAnswers } from "./mocked";

type Answer = { status?: number; body: string };
type Seen = { label: string; what: string; from: string; act: string; opens: string | null; click: boolean; block: number };

const REF = "KE-NWWDA-541055-CW-RFB";
const PACKAGE_API = `/api/packages/${REF}`;
const PLAN = "/projects/P156634/procurement/northern-water-works-development-agency/2026-10-09";

async function serve(page: Page, answers: Record<string, Answer>, width = 1440) {
  await page.setViewportSize({ width, height: 900 });
  await mockApi(page, {
    ...(await viewAnswers()),
    "/api/me": { body: await recorded("me.json") },
    "/api/freshness": { body: await recorded("freshness.json") },
    "/api/drafts/existing": { body: '{"draft":null}' },
    "/api/evidence/opened": { body: '{"opened":[],"recorded":true}' },
    ...answers,
  });
}

// The numbers a reader can reach on the page: each one's tooltip read by keyboard focus, which opens it at once.
async function numbersOn(page: Page): Promise<{ number: Locator; seen: Seen }[]> {
  const found: { number: Locator; seen: Seen }[] = [];
  const all = page.locator("button[data-num]");
  const blocks = await all.evaluateAll((numbers) => {
    const owners: Element[] = [];
    return numbers.map((number) => {
      const owner = number.closest("p, li, td, th, dd, h1, h2, h3, [data-finding]") ?? number.parentElement!;
      if (!owners.includes(owner)) owners.push(owner);
      return number.getClientRects().length > 0 ? owners.indexOf(owner) : -1;
    });
  });
  for (const [index, block] of blocks.entries()) {
    if (block < 0) continue;
    const number = all.nth(index);
    await number.focus();
    const id = await number.getAttribute("aria-describedby");
    expect(id, `${await number.innerText()} has a tooltip as its description`).toBeTruthy();
    const tip = page.locator(`[id="${id}"]`);
    const part = async (name: string) => ((await tip.locator(`[data-num-${name}]`).count()) ? (await tip.locator(`[data-num-${name}]`).innerText()).trim() : "");
    await expect(tip.locator("[data-num-what]")).toBeVisible();
    found.push({
      number,
      seen: {
        label: (await number.innerText()).trim(),
        what: await part("what"),
        from: await part("from"),
        act: await part("act"),
        opens: await number.getAttribute("data-num-opens"),
        click: (await number.getAttribute("data-num-click")) !== null,
        block,
      },
    });
  }
  await page.keyboard.press("Escape");
  return found;
}

// Two numbers in one sentence never share a What sentence unless they come from the same place and open the same thing.
function sharedWhat(seen: Seen[]): string[] {
  const clashes: string[] = [];
  for (const [i, one] of seen.entries()) {
    for (const other of seen.slice(i + 1)) {
      if (one.block !== other.block || one.what !== other.what) continue;
      if (one.from !== other.from || one.act !== other.act || one.opens !== other.opens) clashes.push(`${one.label} and ${other.label}: ${one.what}`);
    }
  }
  return clashes;
}

// Every number shows where it came from, a number with an action line opens something, and one without opens nothing.
function promises(seen: Seen[]): string[] {
  return seen.flatMap((one) => [
    ...(one.from ? [] : [`${one.label} (${one.what}) says nowhere where it came from`]),
    ...(one.act && !(one.click && one.opens) ? [`${one.label} promises "${one.act}" but opens nothing`] : []),
    ...(!one.act && one.click ? [`${one.label} opens something its tooltip does not name`] : []),
  ]);
}

const evidenceShown = (page: Page) => new URL(page.url()).searchParams.get("evidence");

// Selects a number and finds what its action line names: the rows it counts, the record it comes from in the drawer
// (one its sentence cites, the one its tooltip names when the sentence cites more than one), or its window.
async function opensWhatItNames(page: Page, number: Locator, seen: Seen) {
  const cited = await number.evaluate((element) => [
    ...(element.closest("[data-sentence-text], li[data-line-kind], p")?.querySelectorAll("[data-citation-id]") ?? []),
  ].map((marker) => marker.getAttribute("data-citation-id")!));
  await number.click();
  const because = `${seen.label}: "${seen.act}"`;
  if (seen.opens === "rows") {
    // Focus moves to the rows it counts, which are on the page.
    await expect.poll(() => page.evaluate(() => document.activeElement?.closest("[data-comparables-table], [data-rebid-list], table, [role=table]") !== null), { message: because }).toBe(true);
    const all = /all (\d+)\./.exec(seen.act);
    if (all) await expect(page.locator("[data-comparables-table] caption, [data-comparables-table] [data-table-caption]").first(), because).toContainText(`All ${all[1]} `);
  } else if (seen.opens === "record") {
    const drawer = page.locator("[data-evidence-drawer]");
    await expect(drawer, because).toBeVisible();
    const shown = evidenceShown(page);
    expect(shown, because).toBeTruthy();
    if (cited.length > 0) expect(cited, because).toContain(shown);
    if (cited.length > 1) expect(seen.what, because).toContain(shown!.split(/[:/]/).pop());
    await page.keyboard.press("Escape");
    await expect(drawer).toHaveCount(0);
  } else {
    const window = page.getByRole("dialog").filter({ has: page.locator(":focus") });
    await expect(window, because).toBeVisible();
    // A count word's window lists what it counts.
    const counted = await number.evaluate((element) => element.closest("[data-count]")?.getAttribute("data-count") ?? null);
    if (counted) await expect(window.getByRole("listitem"), because).toHaveCount(Number(counted));
    await page.keyboard.press("Escape");
    await expect(window).toHaveCount(0);
  }
}

async function checkPage(page: Page) {
  const numbers = await numbersOn(page);
  const seen = numbers.map((one) => one.seen);
  expect(seen.length).toBeGreaterThan(0);
  expect(sharedWhat(seen)).toEqual([]);
  expect(promises(seen)).toEqual([]);
  for (const { number, seen: one } of numbers) if (one.act) await opensWhatItNames(page, number, one);
  return seen;
}

test("on the package workspace every number and every dot opens what its action line names", async ({ page }) => {
  await serve(page, {
    [PACKAGE_API]: { body: await recorded("package-ke-nwwda-541055.json") },
    [`${PACKAGE_API}/comparables`]: { body: await recorded("comparables-ke-nwwda-541055.json") },
    [`${PACKAGE_API}/risks`]: { body: await recorded("risks-ke-nwwda-541055.json") },
    [`${PACKAGE_API}/steps`]: { body: await recorded("steps-ke-nwwda-541055.json") },
    [`${PACKAGE_API}/estimate`]: { body: await recorded("estimate-ke-nwwda-541055.json") },
    [`${PACKAGE_API}/rebidding`]: { body: await recorded("rebidding-ke-nwwda-541055.json") },
    [`${PACKAGE_API}/criteria`]: { body: await recorded("criteria-summary-ke-nwwda-541055.json") },
  });
  await page.goto(`/packages/${REF}`);
  await expect(page.locator("[data-past-range]:not([data-past-range=loading])")).toBeVisible();
  await expect(page.locator("[data-lane2=loading]")).toHaveCount(0);
  await expect(page.locator("[data-rebid-count]")).toBeVisible();

  const seen = await checkPage(page);
  expect(seen.filter((one) => one.act).map((one) => one.label)).toEqual(expect.arrayContaining(["2", "49", "3.3", "7.9", "4.4", "9.1", "3", "52"]));

  // Every dot: its tooltip's action line, and Enter opens that package's records in the drawer. The drawer sits beside
  // the page, so focus goes back to the next dot while it is open, and that dot's Enter shows its own package instead;
  // Escape closes it at the end and leaves focus on the last dot. The page walks the 49 dots itself, in one round trip.
  const walked = await page.locator("[data-range-chart]").evaluate(async (chart) => {
    const until = async (ok: () => boolean) => {
      const end = performance.now() + 5000;
      while (!ok() && performance.now() < end) await new Promise((done) => setTimeout(done, 1));
      return ok();
    };
    const key = (target: Element, name: string) => target.dispatchEvent(new KeyboardEvent("keydown", { key: name, bubbles: true }));
    const drawer = () => document.querySelector("[data-evidence-drawer]");
    const evidence = () => new URL(location.href).searchParams.get("evidence");
    const wrong: string[] = [];
    const dots = [...chart.querySelectorAll<HTMLElement>("[data-dot-target]")];
    for (const dot of dots) {
      const ref = dot.getAttribute("aria-label")!.split(",")[0];
      dot.focus();
      const tip = () => document.querySelector("[data-dot-tooltip]");
      if (!(await until(() => tip()?.querySelector("p")?.textContent === ref))) wrong.push(`${ref}: no tooltip`);
      else if (tip()!.lastElementChild?.textContent !== "Select to see its records.") wrong.push(`${ref}: no action line`);
      key(dot, "Enter");
      if (!(await until(() => evidence() === `strata.gold.package:${ref}` && drawer() !== null))) wrong.push(`${ref}: its records did not open`);
    }
    const last = dots[dots.length - 1];
    last.focus();
    key(last, "Escape");
    if (!(await until(() => drawer() === null && document.activeElement === last))) wrong.push("Escape left the drawer open");
    return { count: dots.length, wrong };
  });
  expect(walked).toEqual({ count: 49, wrong: [] });
});

test("on the plan check every number says what it is and where it came from, and none opens what it does not name", async ({ page }) => {
  await serve(page, {
    [`/api${PLAN}`]: { body: await recorded("check-plan-p156634-nwwda-2026-10-09.json") },
    [`/api${PLAN}/changes`]: { body: await recorded("changes-nwwda-2026-10-09.json") },
  }, 1504);
  await page.goto(PLAN);
  await expect(page.locator("[data-check-plan-page]:not([data-check-plan-page=loading])")).toBeVisible();
  // The changes since the plan before it, and the activities with no signals, open too.
  for (const show of await page.locator("[data-plan-check] button[aria-expanded=false], [data-changes] button[aria-expanded=false]").all()) {
    if (await show.isVisible()) await show.click();
  }
  const seen = await checkPage(page);
  expect(seen.map((one) => one.label)).toEqual(expect.arrayContaining(["One", "two", "three", "186", "4", "9"]));
});

test("on Home every number opens what its action line names, and 1.23 gives the plan row's own 1,230,000.00", async ({ page }) => {
  await serve(page, { "/api/me": { body: await recorded("me-home.json") }, "/api/home": { body: await recorded("home.json") } });
  await page.goto("/");
  await expect(page.locator("[data-home=ready]")).toBeVisible();
  const seen = await checkPage(page);
  const millions = seen.find((one) => one.label === "1.23")!;
  expect(millions).toMatchObject({
    what: "The plan row's Estimated Amount (US$), 1,230,000.00, in millions.",
    from: "From the Northern Water Works Development Agency plan of October 9, 2026.",
    act: "Select to see the plan row.",
  });
  expect(seen.filter((one) => one.opens === "window").map((one) => one.label)).toEqual(["One", "One", "two", "One", "Two"]);
});

test("on a draft every number opens what its action line names", async ({ page }) => {
  await serve(page, { "/api/drafts/draft-0001": { body: await recorded("drafts-review-notes-draft.json") } });
  await page.goto("/drafts/draft-0001");
  await expect(page.locator("[data-draft-page]:not([data-draft-page=loading])")).toBeVisible();
  const seen = await checkPage(page);
  expect(seen.filter((one) => one.opens === "record").length).toBeGreaterThan(5);
});
