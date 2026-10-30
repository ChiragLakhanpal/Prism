// Section 2 of the package workspace, "Planned date for each step" (ticket 27), at seam 4: the package workspace
// against the answers the server recorded (tests/record_steps_api.py), which tests/test_step_routes.py checks the
// server against. On the fixture every step abstains, so the dated states come from the hand-made set in
// tests/step_set.py, through the same routes.
//
// The literal values below come from independent sources: the step labels from the blueprint's "Step labels taken
// from STEP", the full STEP name from STEP's export (both copied in tests/test_step_registry.py), the counts and dates
// from tests/ground_truth/values.toml's [step_dates] (25 comparables, ran longest in 15 of 25, the cautious signing
// on August 1, 2021 and the middle one on July 11, 2021), and the sentences from the 27 brief.
import { scan } from "./axe";
import type { Locator, Page, Request } from "@playwright/test";
import { expect, recorded, test, windowBeside } from "./mocked";

const REF = "KE-HAND-900000-CW-RFB";
const API = `/api/packages/${REF}`;
const PLANNED = "/api/planned-packages/pkg-000000000001";
const GOODS = ["Bid invitation (SPN)", "Bidding document issued", "Bid opening", "Bid evaluation report", "Contract signed", "Contract completed"];

type Answer = { status?: number; body: string };

async function serve(page: Page, answers: Record<string, Answer>, width = 1440) {
  await page.setViewportSize({ width, height: 900 });
  const puts: Request[] = [];
  const all: Record<string, Answer> = {
    "/api/me": { body: await recorded("me.json") },
    "/api/freshness": { body: await recorded("freshness.json") },
    "/api/evidence/opened": { body: '{"opened":[],"recorded":true}' },
    ...answers,
  };
  await page.route("**/api/**", (route) => {
    const url = new URL(route.request().url());
    if (route.request().method() === "PUT") puts.push(route.request());
    const answer = all[`${route.request().method()} ${url.pathname}`] ?? all[url.pathname];
    if (!answer) return route.fulfill({ status: 404, json: { detail: "Not Found" } });
    return route.fulfill({ status: answer.status ?? 200, contentType: "application/json", body: answer.body });
  });
  return puts;
}

async function openPackage(page: Page, { width = 1440, steps = "steps-ke-hand-900000.json" }: { width?: number; steps?: string } = {}) {
  const puts = await serve(
    page,
    {
      [API]: { body: await recorded("package-ke-hand-900000.json") },
      [`${API}/comparables`]: { body: await recorded("comparables-ke-hand-900000.json") },
      [`${API}/risks`]: { body: await recorded("risks-ke-hand-900000.json") },
      [`${API}/steps`]: { body: await recorded(steps) },
      [`PUT ${API}/plan-dates`]: { body: await recorded("steps-plan-dates-saved.json") },
    },
    width,
  );
  await page.goto(`/packages/${REF}`);
  // Section 2 holds skeleton words while the steps load, so the summary has text before the answer lands: wait for the
  // zone to stop loading first (ticket 59, round 4 review, B1).
  await expect(section(page)).not.toHaveAttribute("data-zone-state", "loading");
  await expect(section(page).locator("[data-section-summary]")).not.toBeEmpty();
  return puts;
}

// The zone draws its table from 49rem of its own width (ticket 101's critique, round 2): at 1024 px there is no side
// panel, so the work column holds the four columns; beside the side panel at 1440 px the zone is a list.
const TABLE_WIDTH = 1024;

const section = (page: Page) => page.locator("section#planned-dates");
const disclosure = (page: Page) => section(page).locator("[data-section-toggle]");
const view = (page: Page) => section(page).locator("[data-step-table]:visible, [data-step-list]:visible").first();
const text = async (locator: Locator) => (await locator.innerText()).replace(/\s+/g, " ").trim();

async function axe(page: Page) {
  await page.waitForFunction(() => document.getAnimations().every((animation) => animation.playState !== "running"));
  const results = await scan(page, "section#planned-dates");
  return results.violations.map((v) => `${v.id}: ${v.nodes.map((node) => node.target.join(" ")).join(", ")}`);
}

test("collapsed by default, the summary takes its step count and ran-longest count from the tool, and the keyboard opens and closes it", async ({ page }) => {
  await openPackage(page);

  await expect(section(page).getByRole("heading", { level: 2 })).toHaveAccessibleName("Planned date for each step");
  expect(await text(section(page).locator("[data-section-summary]"))).toBe(
    "Six steps, from the bid invitation to the contract's completion. Bid evaluation ran longest in 15 of 25 comparable packages. " +
      "I have too few comparable packages to date one of the six.",
  );
  await expect(disclosure(page)).toHaveAttribute("aria-expanded", "false");
  await expect(section(page).locator("[data-section-body]")).toBeHidden();

  await disclosure(page).focus();
  await page.keyboard.press("Enter");
  await expect(disclosure(page)).toHaveAttribute("aria-expanded", "true");
  await expect(disclosure(page)).toHaveText("Hide the steps");
  await expect(disclosure(page)).toBeFocused();
  await expect(view(page)).toBeVisible();
  // The opened zone ends its evidence in its foot strip, as zones 1 and 3 do: provenance has one place (ticket 101's
  // design review, item 6).
  await expect(section(page).locator("[data-foot-strip] [data-step-notes]")).toBeVisible();
  await expect(section(page).locator("[data-section-body] [data-step-notes]")).toHaveCount(0);
  await page.keyboard.press("Space");
  await expect(disclosure(page)).toHaveAttribute("aria-expanded", "false");
  await expect(disclosure(page)).toHaveText("Show the steps");
});

// Ticket 60 (ticket 27's design review, R7): a load that fails leaves nothing stale in the zone's live region, where
// "Loading the planned dates." stayed after the error alert had spoken.
test("when the planned dates fail to load after the zone was opened, its live region no longer says it is loading", async ({ page }) => {
  let fail!: () => void;
  const failed = new Promise<void>((resolve) => (fail = resolve));
  await serve(page, {
    [API]: { body: await recorded("package-ke-hand-900000.json") },
    [`${API}/comparables`]: { body: await recorded("comparables-ke-hand-900000.json") },
    [`${API}/risks`]: { body: await recorded("risks-ke-hand-900000.json") },
  });
  await page.route(`**${API}/steps*`, async (route) => {
    await failed;
    await route.fulfill({ status: 503, json: { code: "data_service", trace_id: "0af7651916cd43dd8448eb211c80319c" } });
  });
  await page.goto(`/packages/${REF}`);
  const live = section(page).getByRole("status");
  await disclosure(page).click();
  await expect(live).toHaveText("Loading the planned dates.");

  fail();

  await expect(section(page).getByRole("alert")).toBeVisible();
  await expect(live).toHaveText("");
});

const FULL_NAME = 'STEP calls this step "Bid Evaluation Report and Recommendation for Award".';

test("the steps carry the blueprint's labels for goods, works and non-consulting services, with STEP's full name on hover and on focus", async ({ page }) => {
  await openPackage(page, { width: TABLE_WIDTH });
  await disclosure(page).focus();
  await page.keyboard.press("Enter");

  await expect(view(page).getByRole("rowheader").locator("[data-term]")).toHaveText(GOODS);
  const report = view(page).getByRole("button", { name: "Bid evaluation report", exact: true });
  const name = page.getByRole("dialog", { name: "Bid evaluation report" });
  await expect(report).toHaveAccessibleDescription("In STEP: Bid Evaluation Report and Recommendation for Award");

  // Hover alone shows the full name, and it goes when the pointer leaves.
  await report.hover();
  await expect(name).toContainText(FULL_NAME);
  await page.mouse.move(0, 0);
  await expect(name).toBeHidden();

  // So does Tab, with no Enter: focus stays on the label, and Escape closes the window there.
  for (let tabs = 0; tabs < 30 && !(await report.evaluate((element) => element === document.activeElement)); tabs++) await page.keyboard.press("Tab");
  await expect(report).toBeFocused();
  await expect(name).toContainText(FULL_NAME);
  await page.keyboard.press("Escape");
  await expect(name).toBeHidden();
  await expect(report).toBeFocused();

  // Enter pins it open with focus on its title, and Escape gives focus back to the label without opening it again.
  await page.keyboard.press("Enter");
  await expect(name.getByRole("heading")).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(report).toBeFocused();
  await expect(name).toBeHidden();
});

const row = (page: Page, key: string) => view(page).locator(`[data-step-row='${key}']`);

test("each step's planned date is the cautious one by default, names its comparables and abstains below 20, and the middle dates show at once", async ({ page }) => {
  const puts = await openPackage(page, { width: TABLE_WIDTH });
  await disclosure(page).click();

  await expect(view(page).locator("[data-choice-header]")).toContainText("Planned date, cautious");
  await expect(section(page).getByRole("radio", { name: "Cautious dates: 2 in 10 ran later" })).toBeChecked();
  expect(await text(row(page, "contract_signed").locator("[data-planned]"))).toBe("Aug 1, 2021 52 days after the plan's date");
  await expect(row(page, "contract_signed").locator("td").last()).toHaveText("25");
  await expect(row(page, "contract_completed").locator("[data-abstains]")).toHaveText("No comparable package recorded this step, so I can't date it.");
  await expect(section(page).locator("[data-step-caption]:visible")).toHaveText("Cautious dates put the signed contract on August 1, 2021.");

  await section(page).getByText("Middle dates: half ran later").click();
  expect(await text(row(page, "contract_signed").locator("[data-planned]"))).toBe("Jul 11, 2021 31 days after the plan's date");
  await expect(view(page).locator("[data-choice-header]")).toContainText("Planned date, middle");
  // The live region says the choice and the new caption, not every cell.
  await expect(section(page).getByRole("status")).toHaveText("Showing middle dates. Middle dates put the signed contract on July 11, 2021.");
  await expect.poll(() => puts.map((put) => put.postDataJSON())).toEqual([{ choice: "middle" }]);
});

// Ticket 59 (the 27 critique, round 2, follow-ups 5 and 6): in the narrowest table, a 900 px window, the planned date's
// column keeps "52 days after the plan's date" on one line; in the list at 390 px each label sits on its value's first
// line.
test("the table keeps each planned date's sentence on one line, and the list sets each label on its value's first line", async ({ page }) => {
  await openPackage(page, { width: TABLE_WIDTH });
  await disclosure(page).click();
  // The narrowest window that still draws the table, where its planned date's column is narrowest.
  let narrowest = TABLE_WIDTH;
  for (let width = TABLE_WIDTH - 16; width >= 880; width -= 16) {
    await page.setViewportSize({ width, height: 900 });
    if ((await section(page).locator("[data-step-table]:visible").count()) === 0) break;
    narrowest = width;
  }
  await page.setViewportSize({ width: narrowest, height: 900 });
  await expect(section(page).locator("[data-step-table]:visible")).toHaveCount(1);
  // The lines a planned date's sentence takes: the distinct line tops of the text after its date.
  const sentenceLines = (cell: Element) => {
    const range = document.createRange();
    const walker = document.createTreeWalker(cell, NodeFilter.SHOW_TEXT);
    const tops = new Set<number>();
    for (let node = walker.nextNode(); node; node = walker.nextNode()) {
      if (!/after the plan/.test(node.textContent ?? "") && !node.parentElement?.closest("[data-after]")) continue;
      range.selectNodeContents(node);
      for (const box of range.getClientRects()) if (box.width > 0) tops.add(Math.round(box.top));
    }
    return tops.size;
  };
  const lines = await view(page).locator("[data-planned]").evaluateAll((cells, count) => cells.map((cell) => new Function("cell", `return (${count})(cell)`)(cell)), sentenceLines.toString());
  expect(lines.filter((count) => count > 0).length, "dated rows").toBeGreaterThan(2);
  expect(lines.filter((count) => count > 1), "sentences on two lines").toEqual([]);

  await page.setViewportSize({ width: 390, height: 900 });
  await expect(section(page).locator("[data-step-list]:visible")).toHaveCount(1);
  const gaps = await view(page).locator("li[data-step-item] dl").first().evaluate((list) => {
    // The bottom of an element's first line of text, from its text's own boxes.
    const firstLine = (element: Element) => {
      const range = document.createRange();
      const boxes: DOMRect[] = [];
      const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT);
      for (let node = walker.nextNode(); node; node = walker.nextNode()) {
        range.selectNodeContents(node);
        boxes.push(...[...range.getClientRects()].filter((box) => box.width > 0));
      }
      const top = Math.min(...boxes.map((box) => box.top));
      return Math.max(...boxes.filter((box) => box.top - top < 4).map((box) => box.bottom));
    };
    // A value beside its label, not a sentence that takes the item's full width under it.
    return [...list.querySelectorAll("dt")]
      .filter((label) => label.nextElementSibling!.getBoundingClientRect().left > label.getBoundingClientRect().right)
      .map((label) => Math.round(Math.abs(firstLine(label) - firstLine(label.nextElementSibling!))));
  });
  expect(gaps.length, "labels beside their values").toBeGreaterThan(1);
  for (const gap of gaps) expect(gap, "a label's first line against its value's").toBeLessThanOrEqual(3);
});

test("Strata writes no actual date into a step: every date on screen is a planned date or the plan's own", async ({ page }) => {
  const result = JSON.parse(await recorded("steps-ke-hand-900000.json"));
  const withActuals = JSON.stringify({ ...result, step_dates: { ...result.step_dates, actual_steps_count: 5 } });
  await serve(page, {
    [API]: { body: await recorded("package-ke-hand-900000.json") },
    [`${API}/comparables`]: { body: await recorded("comparables-ke-hand-900000.json") },
    [`${API}/risks`]: { body: await recorded("risks-ke-hand-900000.json") },
    [`${API}/steps`]: { body: withActuals },
  }, TABLE_WIDTH);
  await page.goto(`/packages/${REF}`);
  await disclosure(page).click();

  const short = new Intl.DateTimeFormat("en-US", { timeZone: "UTC", month: "short", day: "numeric", year: "numeric" });
  const long = new Intl.DateTimeFormat("en-US", { timeZone: "UTC", month: "long", day: "numeric", year: "numeric" });
  const planned = new Set<string>();
  for (const step of result.step_dates.steps) {
    for (const iso of [step.middle?.planned_date, step.cautious?.planned_date, step.plan_first_date, step.plan_latest_date, step.plan_first_version_date]) {
      if (iso) for (const style of [short, long]) planned.add(style.format(new Date(`${iso}T00:00:00Z`)));
    }
  }
  planned.add(long.format(new Date(`${result.records_through}T00:00:00Z`)));
  const shown = (await text(section(page))).match(/[A-Z][a-z]+ \d{1,2}, \d{4}/g) ?? [];
  expect(shown.length).toBeGreaterThan(0);
  expect(shown.filter((date) => !planned.has(date))).toEqual([]);
  await expect(view(page).locator("thead")).not.toContainText("Actual");
  await expect(section(page).locator("[data-actuals]")).toHaveText(
    "STEP records actual dates for five of these steps. I suggest planned dates only and leave actual dates to STEP.",
  );
});

test("a count opens the evidence drawer at the step's comparable packages, and Escape gives focus back to it", async ({ page }) => {
  // A 1440 px page area: the zone is a list beside the side panel, and the drawer takes the side panel's place, so it
  // stays a list (ticket 101). The open sidebar (ticket 92) widens the window.
  await openPackage(page, { width: windowBeside(1440) });
  await disclosure(page).click();

  const item = section(page).locator("[data-step-item='contract_signed']");
  const count = item.getByRole("button", { name: "25 comparable packages for Contract signed" });
  await expect(count).toHaveAccessibleName("25 comparable packages for Contract signed");
  await count.click();
  const drawer = page.getByRole("dialog");
  await expect(drawer.getByRole("heading", { level: 2 })).toHaveText("Comparable packages for the signed contract");
  await expect(drawer.locator("[data-step-entry]")).toHaveCount(25);
  await expect(item).toHaveClass(/bg-tint/);
  await page.keyboard.press("Escape");
  await expect(count).toBeFocused();
});

test("under 20 comparable packages in all, the section gives the steps and their counts with no dates and no controls", async ({ page }) => {
  await openPackage(page, { width: TABLE_WIDTH, steps: "steps-ke-hand-900000-few.json" });

  await expect(section(page).locator("[data-section-summary]")).toContainText(
    "I'm not giving planned dates, because I found only 12 comparable packages.",
  );
  await disclosure(page).click();
  // The summary above says it, so the intro does not say it again.
  await expect(section(page).locator("[data-step-intro]")).not.toContainText("I'm not giving planned dates");
  await expect(section(page).locator("[data-choice]")).toHaveCount(0);
  await expect(view(page).locator("[data-choice-header]")).toHaveCount(0);
  await expect(row(page, "contract_signed").locator("td").last()).toHaveText("12");
});

async function openSentencePackage(page: Page, width = 1440, address = "/packages/pkg-000000000001") {
  const puts = await serve(
    page,
    {
      [PLANNED]: { body: await recorded("planned-package-hand-made.json") },
      "/api/comparables": { body: await recorded("comparables-planned-hand-made.json") },
      [`${PLANNED}/risks`]: { body: await recorded("risks-planned-hand-made.json") },
      [`${PLANNED}/steps`]: { body: await recorded("steps-planned-hand-made.json") },
      [`PUT ${PLANNED}/step-start`]: { body: await recorded("steps-planned-hand-made-dated.json") },
    },
    width,
  );
  await page.goto(address);
  await disclosure(page).click();
  return puts;
}

test("a package from a sentence asks for its first step's date, then dates every later step from it, as of the page's date", async ({ page }) => {
  const puts = await openSentencePackage(page, 1440, "/packages/pkg-000000000001?asof=2021-01-15");

  // Before a start date, no step is dated, so the intro says how I date them, in the present (ticket 58).
  await expect(section(page).locator("[data-step-intro]")).toContainText("I date each step from how long it took in comparable packages");
  await expect(section(page).locator("[data-step-caption]:visible")).toHaveText("How many days each step took in comparable packages.");
  await expect(section(page).locator("[data-planned='undated']:visible").first()).toContainText("Not dated yet");
  await section(page).getByRole("button", { name: "Date the steps" }).click();
  await expect(section(page).getByText("Choose a date for the bid invitation.")).toBeVisible();
  await section(page).getByLabel("Date of the bid invitation").fill("2021-03-01");
  await section(page).getByRole("button", { name: "Date the steps" }).click();
  await expect(section(page).locator("[data-step-caption]:visible")).toHaveText("Cautious dates put the signed contract on July 17, 2021.");
  await expect(section(page).getByRole("status")).toHaveText("Cautious dates put the signed contract on July 17, 2021.");
  expect(new URL(puts[0].url()).searchParams.get("asof")).toBe("2021-01-15");
  // The summary counts the one step the tool could not date, the contract's completion.
  await expect(section(page).locator("[data-section-summary]")).toContainText("I can't date one of the six steps.");

  // Every comparable package took 30 days or less from the bidding documents to the bid opening, so the date's tooltip
  // and its drawer say "In all 25", never "0 of 25, about 0 in 10" (ticket 58).
  const opening = section(page).locator("[data-step-row='bid_opening'] [data-planned] [data-num], [data-step-item='bid_opening'] [data-planned] [data-num]").filter({ visible: true }).first();
  await opening.focus();
  await expect(page.getByRole("tooltip")).toContainText("In all 25 comparable packages, the bid opening came no more than 30 days after");
  await expect(page.getByRole("tooltip")).not.toContainText("0 of 25");
  await opening.click();
  await expect(page.getByRole("dialog")).toContainText("In all 25 packages, the bid opening came no more than 30 days after");
  await expect(page.getByRole("dialog")).not.toContainText("about 0 in 10");
  // Every sentence says what the step came after, so none ends on "after." (the 58 review, P4).
  await expect(page.getByRole("dialog")).not.toContainText(/days after\./);
});

// Ticket 58 (the 27 design review, round 2, R1): a step the comparable packages had not reached names the date the
// source line names, the records' own when the page has no as-of date, and its drawer never says they recorded it.
test("a step comparable packages had not reached names the source line's date, and its drawer says they had not reached it", async ({ page }) => {
  await openSentencePackage(page);

  await expect(section(page).locator("[data-step-notes]")).toContainText("Records run through August 3, 2020.");
  const completion = section(page).locator("[data-step-row='contract_completed'], [data-step-item='contract_completed']").filter({ visible: true });
  await expect(completion).toContainText("None of the 25 comparable packages had reached this step by August 3, 2020, so I can't date it yet.");
  // The count's tooltip says the packages were checked for the step, never that they recorded it (the 58 design
  // review, round 3, follow-up 1).
  const count = completion.getByRole("button", { name: /comparable packages for/ });
  await count.focus();
  await expect(page.getByRole("tooltip")).toContainText("The comparable packages I checked for the contract's completion.");
  await expect(page.getByRole("tooltip")).not.toContainText("recorded");
  await count.click();
  await expect(page.getByRole("dialog")).toContainText("None of the 25 comparable packages had reached the contract's completion by August 3, 2020. Here are all 25.");
  await expect(page.getByRole("dialog")).not.toContainText("recorded the contract's completion");
});

// The 58 review, P6: on a page with an as-of date, the row and the drawer it opens name the same date.
test("on a page as of a date, a step not reached and its drawer name the same date", async ({ page }) => {
  await openSentencePackage(page, 1440, "/packages/pkg-000000000001?asof=2021-01-15");

  const completion = section(page).locator("[data-step-row='contract_completed'], [data-step-item='contract_completed']").filter({ visible: true });
  await expect(completion).toContainText("had reached this step by January 15, 2021");
  await completion.getByRole("button", { name: /comparable packages for/ }).click();
  await expect(page.getByRole("dialog")).toContainText("had reached the contract's completion by January 15, 2021.");
  // The source line keeps the records' own date apart from the page's: it reads "as of" the page's date, as the
  // section's line does, and never says the records run through a date no tool returned (the 58 review, round 2, B1).
  await expect(page.getByRole("dialog").locator("[data-source]")).toHaveText(/Records as of January 15, 2021\.$/);
  await expect(page.getByRole("dialog")).not.toContainText("Records run through January 15, 2021");
});

// Every list item's labels and values, as text boxes: none of a label's boxes may touch its value's.
async function labelsOverValues(page: Page): Promise<string[]> {
  return section(page)
    .locator("[data-step-list]")
    .evaluate((list) => {
      const boxes = (element: Element) => {
        const range = document.createRange();
        range.selectNodeContents(element);
        return [...range.getClientRects()].filter((box) => box.width > 0 && box.height > 0);
      };
      const touch = (a: DOMRect, b: DOMRect) => a.left < b.right - 0.5 && b.left < a.right - 0.5 && a.top < b.bottom - 0.5 && b.top < a.bottom - 0.5;
      const found: string[] = [];
      for (const label of list.querySelectorAll("dt")) {
        const value = label.nextElementSibling;
        if (!value) continue;
        if (boxes(label).some((a) => boxes(value).some((b) => touch(a, b)))) {
          found.push(`${label.closest("[data-step-item]")?.getAttribute("data-step-item")}: ${label.textContent}`);
        }
      }
      return found;
    });
}

test("below a 768 px page area no label prints over its value, for a dated package from a sentence and a step a later plan moved", async ({ page }) => {
  await openSentencePackage(page);
  await section(page).getByLabel("Date of the bid invitation").fill("2021-03-01");
  await section(page).getByRole("button", { name: "Date the steps" }).click();
  await expect(section(page).locator("[data-step-caption]:visible")).toHaveText("Cautious dates put the signed contract on July 17, 2021.");
  for (const width of [390, 360, 320]) {
    await page.setViewportSize({ width, height: 900 });
    await expect(section(page).locator("[data-step-list]")).toBeVisible();
    expect(await labelsOverValues(page), `at ${width} px`).toEqual([]);
    await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), { message: `at ${width} px` }).toBe(true);
  }

  // A made-up later plan re-dates the signed contract, as no recorded plan does: its "Moved to" line is the longest value.
  const result = JSON.parse(await recorded("steps-ke-hand-900000.json"));
  const steps = result.step_dates.steps.map((step: { step_key: string }) =>
    step.step_key === "contract_signed" ? { ...step, plan_latest_date: "2021-07-01", plan_latest_version_date: "2021-01-10" } : step,
  );
  await page.unrouteAll();
  await serve(
    page,
    {
      [API]: { body: await recorded("package-ke-hand-900000.json") },
      [`${API}/comparables`]: { body: await recorded("comparables-ke-hand-900000.json") },
      [`${API}/risks`]: { body: await recorded("risks-ke-hand-900000.json") },
      [`${API}/steps`]: { body: JSON.stringify({ ...result, step_dates: { ...result.step_dates, steps } }) },
    },
    390,
  );
  await page.goto(`/packages/${REF}`);
  await disclosure(page).click();
  await expect(section(page).locator("[data-plan-moved]:visible")).toHaveText("Moved to Jul 1, 2021 in the plan of Jan 10, 2021");
  for (const width of [390, 360, 320]) {
    await page.setViewportSize({ width, height: 900 });
    expect(await labelsOverValues(page), `at ${width} px`).toEqual([]);
  }
});

test("when no step can be dated, as on the fixture's demo package, the section offers no choice of dates and says why", async ({ page }) => {
  const DEMO = "/api/packages/KE-NWWDA-541055-CW-RFB";
  await serve(page, {
    [DEMO]: { body: await recorded("package-ke-nwwda-541055.json") },
    [`${DEMO}/comparables`]: { body: await recorded("comparables-ke-nwwda-541055.json") },
    [`${DEMO}/risks`]: { body: await recorded("risks-ke-nwwda-541055.json") },
    [`${DEMO}/steps`]: { body: await recorded("steps-ke-nwwda-541055.json") },
  });
  await page.goto("/packages/KE-NWWDA-541055-CW-RFB");
  await disclosure(page).click();

  await expect(section(page).locator("[data-step-intro]")).toHaveText(
    "I date a step only when 20 or more comparable packages recorded it.",
  );
  await expect(section(page).locator("[data-choice]")).toHaveCount(0);
  // The caption says what the table holds, since the intro above names the steps and the summary says none could be
  // dated (ticket 58; the 58 critique, follow-up 7).
  await expect(section(page).locator("[data-step-caption]:visible")).toHaveText("Each step, and how many comparable packages recorded it.");
  // The count line in the Tables form: one to nine in words and a full stop, as every count line (ticket 58).
  await expect(section(page).locator("[data-step-count]:visible")).toHaveText("Showing all six steps.");
  await expect(section(page).locator("[data-section-summary]")).toContainText("I have too few comparable packages to date any of the six.");
  // The date column says what dating takes, not how often packages ran later over six refusals (ticket 58): in the
  // list here, each step's label, and in the table, the column head with its note.
  await expect(section(page).locator("[data-step-list]")).toBeVisible();
  const labels = section(page).locator("[data-step-list] dt").filter({ hasText: /^Planned date/ });
  await expect(labels).toHaveCount(6);
  await expect(labels.first()).toHaveText("Planned date");
  await expect(section(page).locator("[data-step-table] [data-choice-header]")).toHaveText("Planned dateDated only when 20 or more comparable packages recorded the step.");
  await expect(section(page)).not.toContainText("Planned date, cautious");
});

test("beside the side panel at 1440 px the steps are a list sized by the zone's own width, so no planned-date sentence runs past two lines", async ({ page }) => {
  // Ticket 101's critique, round 2: the four-column table squeezed into the 657 px work column put one sentence on
  // five lines in each of six cells. The zone switches to the list below 49rem of its own width, as zone 3 does.
  const DEMO = "/api/packages/KE-NWWDA-541055-CW-RFB";
  await serve(page, {
    [DEMO]: { body: await recorded("package-ke-nwwda-541055.json") },
    [`${DEMO}/comparables`]: { body: await recorded("comparables-ke-nwwda-541055.json") },
    [`${DEMO}/risks`]: { body: await recorded("risks-ke-nwwda-541055.json") },
    [`${DEMO}/steps`]: { body: await recorded("steps-ke-nwwda-541055.json") },
  });
  await page.goto("/packages/KE-NWWDA-541055-CW-RFB");
  await disclosure(page).click();
  await expect(section(page).locator("[data-step-list]")).toBeVisible();
  await expect(section(page).locator("[data-step-table]")).toBeHidden();
  const sentences = section(page).locator("[data-abstains]:visible");
  await expect(sentences).toHaveCount(6);
  const heights = await sentences.evaluateAll((all) => all.map((one) => one.getBoundingClientRect().height));
  expect(heights.filter((height) => height > 48)).toEqual([]);
});

test("axe finds no WCAG 2.2 AA violations collapsed and open, and at 390 px the steps are a list with STEP's full names printed", async ({ page }) => {
  await openPackage(page);
  expect(await axe(page)).toEqual([]);
  await disclosure(page).click();
  expect(await axe(page)).toEqual([]);

  await page.setViewportSize({ width: 390, height: 900 });
  await expect(section(page).locator("[data-step-list]")).toBeVisible();
  await expect(section(page).locator("[data-step-item='bid_evaluation_report']")).toContainText(
    "In STEP: Bid Evaluation Report and Recommendation for Award",
  );
  expect(await axe(page)).toEqual([]);
  await page.setViewportSize({ width: 320, height: 900 });
  // Section 1's chart measures its new width a frame after the resize, so wait for the page to settle.
  await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});
