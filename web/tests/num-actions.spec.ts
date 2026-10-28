// The number tooltip's gate test (ticket 96; DESIGN.md section 5, Number tooltip): on the package workspace, the plan
// check, Home and a draft, one page load each, every number and every range chart dot whose tooltip has an action line
// opens what that line names, no number without an action line opens anything, and no two numbers in one sentence share
// a What sentence unless they share where they came from and what they open, and no tooltip names a number the page
// does not show, save a rounded amount's own value. Each later ticket that adds a click to a number adds its action
// line, and this test keeps it honest.
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

// The numbers a reader can reach on the page: each one's tooltip read by keyboard focus, which opens it at once. The
// page reads them all itself, in one round trip, as the dot walk below does.
async function numbersOn(page: Page): Promise<{ number: Locator; seen: Seen }[]> {
  const all = page.locator("button[data-num]");
  const read = await all.evaluateAll(async (numbers) => {
    const until = async (ok: () => boolean) => {
      const end = performance.now() + 5000;
      while (!ok() && performance.now() < end) await new Promise((done) => setTimeout(done, 1));
      return ok();
    };
    const owners: Element[] = [];
    const found: { index: number; seen: Seen | null; label: string }[] = [];
    for (const [index, number] of numbers.entries()) {
      const owner = number.closest("p, li, td, th, dd, h1, h2, h3, [data-finding]") ?? number.parentElement!;
      if (!owners.includes(owner)) owners.push(owner);
      if (number.getClientRects().length === 0) continue;
      (number as HTMLElement).focus();
      const tip = () => {
        const id = number.getAttribute("aria-describedby");
        return id ? document.getElementById(id) : null;
      };
      const label = (number as HTMLElement).innerText.trim();
      if (!(await until(() => tip()?.querySelector("[data-num-what]") != null))) {
        found.push({ index, seen: null, label });
        continue;
      }
      const part = (name: string) => (tip()!.querySelector<HTMLElement>(`[data-num-${name}]`)?.innerText ?? "").trim();
      found.push({
        index,
        label,
        seen: {
          label,
          what: part("what"),
          from: part("from"),
          act: part("act"),
          opens: number.getAttribute("data-num-opens"),
          click: number.hasAttribute("data-num-click"),
          block: owners.indexOf(owner),
        },
      });
    }
    return found;
  });
  await page.keyboard.press("Escape");
  expect(read.filter((one) => one.seen === null).map((one) => one.label), "numbers whose focus showed no tooltip").toEqual([]);
  return read.map((one) => ({ number: all.nth(one.index), seen: one.seen! }));
}

// Two numbers in one sentence never share a What sentence unless they come from the same place and open the same thing.
// Two that open nothing open no same thing, so they never share one ("7", "49" and "42" in a coverage line).
function sharedWhat(seen: Seen[]): string[] {
  const clashes: string[] = [];
  for (const [i, one] of seen.entries()) {
    for (const other of seen.slice(i + 1)) {
      if (one.block !== other.block || one.what !== other.what) continue;
      if (!one.opens || one.from !== other.from || one.act !== other.act || one.opens !== other.opens) clashes.push(`${one.label} and ${other.label}: ${one.what}`);
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

// The numbers and dates in a text. A date is one token, written in full or short: "July 1, 2021" and "Jul 1, 2021"
// are 2021-07-01, "Jul 2021" is 2021-07, and "Oct 9", which a page writes without the year in the current year, is
// --10-09. So "July 1, 2021" never passes on a 1 and a 2021 found apart on the page.
const MONTH = /\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s(?:(\d{1,2})(?:,\s(\d{4}))?|(\d{4}))\b/g;
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
function tokens(text: string): string[] {
  const dates: string[] = [];
  const two = (n: number | string) => String(n).padStart(2, "0");
  const rest = text.replace(MONTH, (_, name: string, day?: string, year?: string, monthYear?: string) => {
    const month = two(MONTHS.indexOf(name) + 1);
    dates.push(monthYear ? `${monthYear}-${month}` : `${year ?? "-"}-${month}-${two(day!)}`);
    return " ";
  });
  return [...dates, ...(rest.match(/\d[\d,]*(\.\d+)?/g) ?? [])];
}

// The numbers a tooltip names that the page does not show. DESIGN.md's one exception, a rounded amount's own unrounded
// value from its record (the Signal line), is the only one a test may expect here. A date the page writes without its
// year shows that day of the current year.
async function unshown(page: Page, said: { label: string; text: string }[]): Promise<string[]> {
  const shown = new Set(tokens(await page.locator("main").innerText()));
  const isShown = (token: string) => shown.has(token) || (/^\d{4}-\d{2}-\d{2}$/.test(token) && shown.has(`-${token.slice(4)}`));
  return said.flatMap((one) => tokens(one.text).filter((token) => !isShown(token)).map((token) => `${one.label}: ${token}`));
}

async function checkPage(page: Page, unrounded: string[] = []) {
  const numbers = await numbersOn(page);
  const seen = numbers.map((one) => one.seen);
  expect(seen.length).toBeGreaterThan(0);
  expect(sharedWhat(seen)).toEqual([]);
  expect(promises(seen)).toEqual([]);
  const said = seen.map((one) => ({ label: one.label, text: `${one.what} ${one.from}` }));
  expect(await unshown(page, said), "numbers a tooltip names that the page does not show").toEqual(unrounded);
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
  // Sections 2 to 5 rest closed. Open each, so the numbers inside them are read and opened too.
  for (const show of await page.locator("main [data-zone] button[aria-expanded=false]").all()) {
    if (await show.isVisible()) await show.click();
  }
  await expect(page.locator("section#planned-dates [data-step-caption]").first()).toBeVisible();

  const seen = await checkPage(page);
  expect(seen.filter((one) => one.act).map((one) => one.label)).toEqual(expect.arrayContaining(["2", "49", "3.3", "7.9", "4.4", "9.1", "3", "52"]));
  // Section 2's step counts, inside a zone that rests closed, were read and opened too: one for each step a comparable
  // package's plan recorded.
  const steps = seen.filter((one) => one.what.startsWith("Comparable packages whose published plans recorded"));
  expect(steps.map((one) => [one.label, one.act])).toEqual(Array.from({ length: 5 }, () => ["7", "Select to list them."]));
  // Advertised again counts plan rows canceled in the Procurement Plan too, so its From line names all three record sets.
  for (const count of await page.locator("[data-rebid-count] button[data-num]").all()) {
    await count.focus();
    await expect(page.locator(`[id="${await count.getAttribute("aria-describedby")}"] [data-num-from]`)).toHaveText(
      "From Procurement Notices, Contract Awards and Documents & Reports, through October 13, 2026.",
    );
  }

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
    const said: { label: string; text: string }[] = [];
    const dots = [...chart.querySelectorAll<HTMLElement>("[data-dot-target]")];
    for (const dot of dots) {
      const ref = dot.getAttribute("aria-label")!.split(",")[0];
      dot.focus();
      const tip = () => document.querySelector<HTMLElement>("[data-dot-tooltip]");
      if (!(await until(() => tip()?.querySelector("p")?.textContent === ref))) wrong.push(`${ref}: no tooltip`);
      else if (tip()!.lastElementChild?.textContent !== "Select to see its records.") wrong.push(`${ref}: no action line`);
      // What the tooltip says after the dot's reference, for the check that it names no number the page leaves out.
      else said.push({ label: ref, text: [...tip()!.children].slice(1).map((part) => (part as HTMLElement).innerText).join(" ") });
      key(dot, "Enter");
      if (!(await until(() => evidence() === `strata.gold.package:${ref}` && drawer() !== null))) wrong.push(`${ref}: its records did not open`);
    }
    const last = dots[dots.length - 1];
    last.focus();
    key(last, "Escape");
    if (!(await until(() => drawer() === null && document.activeElement === last))) wrong.push("Escape left the drawer open");
    return { count: dots.length, wrong, said };
  });
  expect({ count: walked.count, wrong: walked.wrong }).toEqual({ count: 49, wrong: [] });
  expect(await unshown(page, walked.said), "numbers a dot's tooltip names that the page does not show").toEqual([]);
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
  // The one number a tooltip names that Home does not show: the plan row's own Estimated Amount behind "1.23".
  const seen = await checkPage(page, ["1.23: 1,230,000.00"]);
  const millions = seen.find((one) => one.label === "1.23")!;
  expect(millions).toMatchObject({
    what: "The plan row's Estimated Amount (US$) is 1,230,000.00. This line gives it in millions.",
    from: "From the Northern Water Works Development Agency plan of October 9, 2026.",
    act: "Select to see the plan row.",
  });
  expect(seen.filter((one) => one.opens === "window").map((one) => one.label)).toEqual(["One", "One", "two", "One", "Two"]);
  // The days to closing come from the project's closing date, which the plan row does not hold, so they open nothing.
  expect(seen.find((one) => one.what === "Days from my check to the project's closing date.")).toMatchObject({ act: "", opens: null });
});

test("on a draft every number opens what its action line names", async ({ page }) => {
  await serve(page, { "/api/drafts/draft-0001": { body: await recorded("drafts-review-notes-draft.json") } });
  await page.goto("/drafts/draft-0001");
  await expect(page.locator("[data-draft-page]:not([data-draft-page=loading])")).toBeVisible();
  const seen = await checkPage(page);
  expect(seen.filter((one) => one.opens === "record").length).toBeGreaterThan(5);
});
