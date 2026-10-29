// Check a plan (ticket 10) at seam 4: the NWWDA plan of October 9, 2026 for P156634, against the
// response recorded from check_plan in tests/fixtures/api, which the server tests check the server
// against. The words below are the ticket's, the blueprint wireframe's and the 10 design brief's,
// copied here so the test checks the copy file against an independent source.
//
// The plan lists nine activities. The wireframe draws eight and leaves out KE-NWWDA-207796-CS-INDV,
// which has no signals, so the screen shows six marked activities and folds three.
import { scan } from "./axe";
import type { Page } from "@playwright/test";
import { expect, mockApi, openSidebar, recorded, test, viewAnswers, windowBeside } from "./mocked";
import { recordTransitions, transitionsOn, type Moved } from "./reveals";
import { animationsDone } from "./settled";

const PLAN = "/projects/P156634/procurement/northern-water-works-development-agency/2026-10-09";
const API = `/api${PLAN}`;
const MARKED = [
  "KE-NWWDA-541055-CW-RFB",
  "KE-NWWDA-229129-CW-RFB",
  "KE-NWWDA-541062-CW-RFQ",
  "KE-NWWDA-503455-CW-RFQ",
  "KE-NWWDA-541061-CW-RFQ",
  "KE-NWWDA-199461-GO-RFB",
];
const FOLDED = ["KE-NWWDA-199471-GO-RFQ", "NWWDA-WSDP-03-2019-2020", "KE-NWWDA-207796-CS-INDV"];
const FINDING = "One activity needs a look and two are worth watching; three have data notes.";
// Ticket 111's narration, word for word: the step, how I check, and why it can take longer.
const NARRATION = {
  running: "I'm checking the plan.",
  how: "I'm comparing each activity with its own dates, its estimate and the project's closing date.",
  slow: "The database may be starting up, so this can take longer.",
};
// Columns 1 to 8 of the 12-column grid in a 1440 px page area: the window's 40 px margins leave 1360 px, all of it
// content, which may take 1440 px since ticket 110, so 8 columns of 84 px and 7 gutters of 32 px.
const EIGHT_COLUMNS = 896;
const widthOf = async (page: Page, selector: string) => Math.round((await page.locator(selector).boundingBox())!.width);

type Answer = { status?: number; body: string };

async function openPlan(page: Page, width = 1440, answer?: Answer, path = PLAN) {
  // width is the page area's: beside the sidebar (ticket 92) the window is that much wider.
  await openPlanAt(page, windowBeside(width), 900, answer, path);
}

// The plan check in a window of this size, as a person's screen is (ticket 100's landing sizes).
async function openPlanAt(page: Page, width: number, height: number, answer?: Answer, path = PLAN) {
  await page.setViewportSize({ width, height });
  await mockApi(page, {
    "/api/me": { body: await recorded("me.json") },
    "/api/freshness": { body: await recorded("freshness.json") },
    [`/api${path.split("#")[0]}`]: answer ?? { body: await recorded("check-plan-p156634-nwwda-2026-10-09.json") },
  });
  await page.goto(path);
  // The answer has drawn the page: a measure taken from here reads rows, cards or an alert, never
  // the skeleton or nothing.
  await expect(page.locator("[data-check-plan-page]:not([data-check-plan-page=loading])")).toBeVisible();
}

const view = (page: Page, name: "table" | "cards") => page.locator(`[data-view=${name}]`);
// The STEP references the view shows, top to bottom: each row header's or card heading's first line.
const refsIn = (page: Page, name: "table" | "cards") =>
  view(page, name).locator("[data-activity]").evaluateAll((elements) =>
    elements
      .filter((element) => element.getClientRects().length > 0)
      .map((element) => (element.firstElementChild ?? element).textContent?.trim()),
  );

// How many lines an element's text takes: the distinct tops of its text's line boxes.
const textLines = (element: Element) => {
  const range = document.createRange();
  range.selectNodeContents(element);
  return new Set(Array.from(range.getClientRects(), (rect) => Math.round(rect.top))).size;
};

async function axe(page: Page) {
  // Let the fold's fade-in finish, so contrast is measured on what stays on screen. The narration's turning icon
  // turns until the check arrives, so it never rests and is left out (ticket 111).
  await animationsDone(page);
  const results = await scan(page);
  return results.violations.map((v) => `${v.id}: ${v.nodes.map((node) => node.target.join(" ")).join(", ")}`);
}

test("the plan check finds every activity, states the finding, and folds the activities with no signals", async ({ page }) => {
  await openPlan(page);
  const main = page.getByRole("main");

  await expect(main.getByRole("heading", { level: 1 })).toHaveText("Northern Water Works Development Agency");
  await expect(main.getByText("Procurement Plan of October 9, 2026", { exact: true })).toBeVisible();
  await expect(main.locator("[data-check-pill]")).toHaveText("Nine activities checked");
  await expect(main.getByRole("heading", { level: 2, name: FINDING })).toBeVisible();
  await expect(main.locator("[data-count-line]")).toHaveText("Showing 6 of 9 activities.");
  await expect(view(page, "table")).toBeVisible();
  expect(await refsIn(page, "table")).toEqual(MARKED);
  const fold = view(page, "table").locator("[data-fold]:visible");
  await expect(fold).toContainText(
    "Three more activities have no signals: KE-NWWDA-199471-GO-RFQ, NWWDA-WSDP-03-2019-2020 and KE-NWWDA-207796-CS-INDV.",
  );

  // The visible badges of each kind equal the counts in the finding.
  const table = view(page, "table");
  await expect(table.locator("[data-badge=needs-a-look]:visible")).toHaveCount(1);
  await expect(table.locator("[data-badge=watch]:visible")).toHaveCount(2);
  await expect(table.locator("[data-badge=data-note]:visible")).toHaveCount(3);
  // The crumb names the project as its page header does, by the server's rule (the 21 critique, round 3).
  await expect(page.getByRole("link", { name: "Water and Sanitation Development (P156634)" }).first()).toHaveAttribute(
    "href",
    "/projects/P156634",
  );
});

// Ticket 100: the plan check belongs to the Packages section, though its address stays under /projects/, and in a view
// without Packages (the public view) it belongs to Projects (DESIGN.md section 5, Plan check table; plan 8.0).
const sidebar = (page: Page) => page.getByRole("navigation", { name: "Main" });
const crumbLinks = (page: Page) => page.getByRole("navigation", { name: "Breadcrumb" }).getByRole("link");

test("the plan check is lit as Packages, its breadcrumb starts at Packages, and it opens on its finding with the first marked row in the first screen", async ({ page }) => {
  await mockApi(page, {
    "/api/me": { body: await recorded("me.json") },
    "/api/freshness": { body: await recorded("freshness.json") },
    [API]: { body: await recorded("check-plan-p156634-nwwda-2026-10-09.json") },
  });
  for (const [width, height] of [[1440, 900], [1024, 768]]) {
    await page.setViewportSize({ width, height });
    await page.goto(PLAN);
    await expect(page.locator("[data-check-plan-page=ready]")).toBeVisible();
    await expect(sidebar(page).locator("[data-nav-item=packages]")).toHaveAttribute("aria-current", "true");
    await expect(sidebar(page).locator("[data-nav-item=projects]")).not.toHaveAttribute("aria-current", /./);
    await expect(crumbLinks(page)).toHaveText(["Packages", "Water and Sanitation Development (P156634)"]);
    await expect(crumbLinks(page).first()).toHaveAttribute("href", "/packages");
    // The finding is the page's largest type: Open Sans Light at 28 px (DESIGN.md section 3, finding).
    const finding = page.locator("[data-finding]");
    await expect(finding).toHaveText(FINDING);
    expect(await finding.evaluate((el) => [getComputedStyle(el).fontWeight, getComputedStyle(el).fontSize])).toEqual(["300", "28px"]);
    await page.evaluate(() => document.fonts.ready);
    const first = page.locator(`tr[id="${MARKED[0]}"]`);
    expect(await first.evaluate((el) => el.getBoundingClientRect().top), `the first marked row at ${width} by ${height}`).toBeLessThan(height);
  }
});

test("in the public preview the plan check is lit as Projects, its breadcrumb starts at the project, and its head holds the pill alone and does not stick", async ({ page }) => {
  await page.setViewportSize({ width: windowBeside(1440), height: 900 });
  await mockApi(page, {
    ...(await viewAnswers()),
    "/api/me": { body: await recorded("me.json") },
    "/api/freshness": { body: await recorded("freshness.json") },
    [`${API}?view=public`]: { body: await recorded("check-plan-p156634-nwwda-2026-10-09-public.json") },
  });
  await page.goto(`${PLAN}?view=public`);
  await expect(page.locator("[data-check-plan-page=ready]")).toBeVisible();
  await expect(sidebar(page).locator("[data-nav-item]")).toHaveText(["Home", "Projects", "Lessons", "Data"]);
  await expect(sidebar(page).locator("[data-nav-item=projects]")).toHaveAttribute("aria-current", "true");
  await expect(crumbLinks(page)).toHaveText(["Water and Sanitation Development (P156634)"]);
  await expect(page.locator("[data-finding]")).toHaveText(
    "I don't show signals on active projects in this view, so a procurement still under way isn't prejudged; three have data notes.",
  );
  // The finding holds the signals back, so its byline says so (DESIGN.md section 5, Byline).
  await expect(page.locator("[data-finding-block] [data-byline]")).toHaveText("Strata held back");
  const head = page.locator("[data-plan-header]");
  await expect(head.locator("[data-check-pill]")).toHaveText("Nine activities checked");
  await expect(head.getByRole("button")).toHaveCount(0);
  await expect(head.locator("[data-draft-slot]")).toHaveCount(0);
  expect(await head.evaluate((el) => getComputedStyle(el).position)).toBe("static");
  // Only the data-note rows are marked; the public view saves no baseline.
  expect(await refsIn(page, "table")).toEqual(["KE-NWWDA-503455-CW-RFQ", "KE-NWWDA-541061-CW-RFQ", "KE-NWWDA-199461-GO-RFB"]);
  await expect(page.getByRole("region", { name: "Baseline for delay" })).toHaveCount(0);
});

test("the fold states check_plan's count of unmarked activities and never counts the rows itself", async ({ page }) => {
  // A response whose count differs from its rows shows which one the screen states.
  const result = JSON.parse(await recorded("check-plan-p156634-nwwda-2026-10-09.json"));
  result.counts.unmarked = 12;
  await openPlan(page, 1440, { body: JSON.stringify(result) });

  await expect(view(page, "table").locator("[data-fold]:visible")).toContainText("12 more activities have no signals.");
});

test("Show them opens the folded activities by mouse, and Hide them folds them again", async ({ page }) => {
  await openPlan(page);
  const show = view(page, "table").getByRole("button", { name: "Show them" });
  await expect(show).toHaveAttribute("aria-expanded", "false");
  // On the fold row's page background, the ghost button hovers to tint, so it answers the pointer.
  await show.hover();
  await expect.poll(() => show.evaluate((element) => getComputedStyle(element).backgroundColor)).toBe("rgb(233, 247, 253)");

  await show.click();

  const hide = view(page, "table").getByRole("button", { name: "Hide them" });
  await expect(hide).toHaveAttribute("aria-expanded", "true");
  await expect(hide).toBeFocused();
  expect(await refsIn(page, "table")).toEqual([...MARKED, ...FOLDED]);
  await expect(page.locator("[data-count-line]")).toHaveText("Showing all nine activities.");
  for (const ref of FOLDED) {
    await expect(view(page, "table").locator(`tr[id="${ref}"]`)).toContainText("No signals.");
  }

  await hide.click();
  expect(await refsIn(page, "table")).toEqual(MARKED);
});

test("Show them opens the folded activities from the keyboard, and focus stays on the button", async ({ page }) => {
  await openPlan(page);
  const button = view(page, "table").locator("[data-fold]:visible button");
  await button.focus();

  await page.keyboard.press("Enter");
  await expect(button).toHaveText("Hide them");
  await expect(button).toBeFocused();
  expect(await refsIn(page, "table")).toEqual([...MARKED, ...FOLDED]);

  await page.keyboard.press("Space");
  await expect(button).toHaveText("Show them");
  expect(await refsIn(page, "table")).toEqual(MARKED);
});

test("each reason is built from the copy file's sentence and the tool's values, and reads as the wireframe does", async ({ page }) => {
  await openPlan(page);
  const row = (ref: string) => view(page, "table").locator(`tr[id="${ref}"]`);

  await expect(row("KE-NWWDA-541055-CW-RFB")).toContainText(
    "Planned completion July 31, 2026 passed with no signed contract. The project closes October 31, 2026.",
  );
  // A date in a sentence never breaks across lines.
  const date = row("KE-NWWDA-541055-CW-RFB").locator("[data-num]").filter({ hasText: "October 31, 2026" });
  expect(await date.evaluate((element) => getComputedStyle(element).whiteSpace)).toBe("nowrap");
  await expect(row("KE-NWWDA-229129-CW-RFB")).toContainText(
    "Signed January 3, 2022, 186 days after its planned date, at US$1,245,092.76, about 4 times its estimate.",
  );
  await expect(row("KE-NWWDA-541062-CW-RFQ")).toContainText("Still pending, 9 days before the project closes.");
  await expect(row("KE-NWWDA-199461-GO-RFB")).toContainText(
    "The reference ends in RFB (Request for Bids), but the Method column says Request for Quotations. I use the Method column.",
  );
  await expect(row("KE-NWWDA-503455-CW-RFQ")).toContainText("Signed, but Actual Amount reads 0.00.");
  await expect(row("KE-NWWDA-541061-CW-RFQ")).toContainText("Completed, but Actual Amount reads 0.00.");
});

test("column names and values are STEP's, word for word", async ({ page }) => {
  await openPlan(page);
  const table = view(page, "table").locator("table");

  await expect(table.locator("thead th")).toHaveText([
    "Activity",
    "Method and market approach",
    "Review",
    "Estimated (US$)",
    "Process status",
    "What Strata found",
  ]);
  const cells = table.locator('tr[id="KE-NWWDA-541055-CW-RFB"] td');
  await expect(cells.nth(0)).toHaveText("Request for Bids · Open - National");
  await expect(cells.nth(1)).toHaveText("Post");
  await expect(cells.nth(2)).toHaveText("1,230,000.00");
  await expect(cells.nth(3)).toHaveText("Pending Implementation");
  await expect(table.locator('tr[id="KE-NWWDA-199461-GO-RFB"] td').nth(0)).toHaveText("Request for Quotations · Limited");
});

test("the table follows DESIGN.md: title sentence, count line, surface-2 header, units in the heads, numbers right-aligned in tabular numerals, a source line, and references in Roboto Mono", async ({ page }) => {
  await openPlan(page);
  const table = view(page, "table").locator("table");

  const header = await table.locator("thead").evaluate((el) => getComputedStyle(el).backgroundColor);
  expect(header).toBe("rgb(231, 237, 243)");
  // The header band sits 16 px under the panel's name and its count line, never touching them (the critique of
  // ticket 100, round 1).
  const bottom = (selector: string) => page.locator(selector).evaluate((el) => el.getBoundingClientRect().bottom);
  const nameFoot = Math.max(await bottom("[data-section=activities] [data-zone-name]"), await bottom("[data-section=activities] [data-zone-tag]"));
  expect(Math.round((await table.locator("thead").evaluate((el) => el.getBoundingClientRect().top)) - nameFoot)).toBeGreaterThanOrEqual(16);
  const amountHead = table.locator("thead th").nth(3);
  const amount = table.locator('tr[id="KE-NWWDA-541055-CW-RFB"] td').nth(2);
  for (const cell of [amountHead, amount]) {
    expect(await cell.evaluate((el) => getComputedStyle(el).textAlign)).toBe("right");
  }
  expect(await amount.evaluate((el) => getComputedStyle(el).fontVariantNumeric)).toContain("tabular-nums");
  const ref = table.locator('[data-activity="KE-NWWDA-541055-CW-RFB"] span').first();
  expect(await ref.evaluate((el) => getComputedStyle(el).fontFamily.split(",")[0])).toBe('"Roboto Mono"');

  const source = page.locator("[data-plan-check] [data-source]");
  await expect(source).toContainText(
    "Source: Procurement Plan, Northern Water Works Development Agency, P156634, version of October 9, 2026, disclosed October 9, 2026.",
  );
  // The marks are as of the date the page reads the records, not a date the checks ran.
  await expect(source).toContainText("Marks from Strata's fixed checks, as of October 22, 2026.");
  const [tableBox, sourceBox] = [await table.boundingBox(), await source.boundingBox()];
  expect(sourceBox!.y).toBeGreaterThan(tableBox!.y + tableBox!.height);
  await expect(page.getByRole("link", { name: "The plan on the World Bank's documents site (opens in a new tab)" })).toHaveAttribute(
    "target",
    "_blank",
  );
});

test("marks are status badges with an icon and their name; Data note is neutral and dashed", async ({ page }) => {
  await openPlan(page);
  const badges = view(page, "table").locator("[data-badge]");

  for (const badge of await badges.all()) {
    await expect(badge.locator("svg[aria-hidden=true]")).toHaveCount(1);
    await expect(badge).toHaveText(/^(Needs a look|Watch|Data note)$/);
  }
  const note = view(page, "table").locator("[data-badge=data-note]").first();
  expect(await note.evaluate((el) => [getComputedStyle(el).borderStyle, getComputedStyle(el).backgroundColor])).toEqual([
    "dashed",
    "rgb(231, 237, 243)",
  ]);
});

test("the page says what Strata cannot see, as the wireframe does", async ({ page }) => {
  await openPlan(page);

  await expect(page.locator("[data-not-visible]")).toHaveText(
    // The first time the page names STEP, so it is spelled out here (DESIGN.md section 7 rule 10).
    "Not visible to Strata: the prior-review queue, complaints, contract amendments and contract management reports. " +
      "Those stay in Systematic Tracking of Exchanges in Procurement (STEP).",
  );
});

test("a number explains itself on focus, and What Strata found opens its definition", async ({ page }) => {
  await openPlan(page);
  const days = view(page, "table").locator('tr[id="KE-NWWDA-229129-CW-RFB"] button[data-num]').filter({ hasText: "186" });

  await days.focus();
  const tip = page.getByRole("tooltip");
  // What the number is, and where it came from (DESIGN.md, Number tooltip; ticket 96). The planned date it counts from
  // is not on the page, so the tooltip names it without its date; it opens nothing yet, so it has no action line.
  await expect(tip.locator("[data-num-what]")).toHaveText("Days between its planned signing date, as first published, and Contract signed.");
  await expect(tip.locator("[data-num-from]")).toHaveText("From my check of this plan, as of October 22, 2026.");
  await expect(tip.locator("[data-num-act]")).toHaveCount(0);
  await page.keyboard.press("Escape");
  await expect(tip).toHaveCount(0);
  await expect(days).toBeFocused();

  const term = view(page, "table").getByRole("button", { name: "What Strata found" });
  await term.click();
  const definition = page.getByRole("dialog", { name: "What Strata found" });
  await expect(definition).toContainText("A signal is a fixed check on public records. It gives a reason to look, never a finding.");
  await expect(definition).toContainText(
    "An activity needs a look when its planned completion passed with no signed contract. I mark it only when its estimate is US$1 million or more, or when the plan gives no estimate.",
  );
  await expect(definition).toContainText("It is also worth watching when it was signed at 2 times its estimate or more.");
  await page.keyboard.press("Escape");
  await expect(definition).toHaveCount(0);
  await expect(term).toBeFocused();
});

test("tabbing onto a number opens its tooltip, which stays open while it has focus", async ({ page }) => {
  await openPlan(page);
  // After the breadcrumb's last link, the project, the header's draft action (ticket 35), then the finding's first
  // count word.
  await page.getByRole("navigation", { name: "Breadcrumb" }).getByRole("link", { name: "Water and Sanitation Development (P156634)" }).focus();

  await page.keyboard.press("Tab");
  await expect(page.getByRole("button", { name: "Draft review notes (3 rows)" })).toBeFocused();
  await page.keyboard.press("Tab");

  await expect(page.getByRole("heading", { level: 2 }).getByRole("button", { name: "One" })).toBeFocused();
  await expect(page.getByRole("tooltip").locator("[data-num-what]")).toHaveText("The activity that needs a look: KE-NWWDA-541055-CW-RFB.");
});

test("a link whose hash names a folded activity opens the fold and focuses that activity", async ({ page }) => {
  await openPlan(page, 1440, undefined, `${PLAN}#KE-NWWDA-207796-CS-INDV`);

  const target = view(page, "table").locator('[data-activity="KE-NWWDA-207796-CS-INDV"]');
  await expect(target).toBeFocused();
  await expect(view(page, "table").getByRole("button", { name: "Hide them" })).toBeVisible();
  // The named row keeps the selected row's tint after focus moves on (DESIGN.md: tint, Selected row).
  await page.keyboard.press("Tab");
  expect(await view(page, "table").locator('tr[id="KE-NWWDA-207796-CS-INDV"]').evaluate((row) => getComputedStyle(row).backgroundColor)).toBe(
    "rgb(233, 247, 253)",
  );
});

test("below a table frame of 34rem a link whose hash names a folded activity opens the fold and focuses that activity's card", async ({ page }) => {
  await openPlan(page, 390, undefined, `${PLAN}#KE-NWWDA-207796-CS-INDV`);

  await expect(view(page, "cards").locator('[data-activity="KE-NWWDA-207796-CS-INDV"]')).toBeFocused();
  await expect(view(page, "cards").getByRole("button", { name: "Hide them" })).toBeVisible();
});

test("below a table frame of 34rem the cards open the What Strata found definition from their head, since they have no column heads", async ({ page }) => {
  await openPlan(page, 390);
  const term = page.getByRole("button", { name: "What Strata found" });
  await expect(term).toHaveCount(1);

  await term.click();

  await expect(page.getByRole("dialog", { name: "What Strata found" })).toContainText("It gives a reason to look, never a finding.");
  await page.keyboard.press("Escape");

  // At 320 px the two don't fit side by side, so the definition takes a line of its own and
  // neither breaks.
  await page.setViewportSize({ width: 320, height: 900 });
  expect(await page.locator("[data-count-line]").evaluate(textLines)).toBe(1);
  expect(await term.evaluate(textLines)).toBe(1);
});

test("the plan's date in the header keeps to one line, even at 320 px", async ({ page }) => {
  await openPlan(page, 320);
  const date = page.locator("[data-plan-header] p").getByText("October 9, 2026", { exact: true });
  await expect(date).toBeVisible();
  expect(await date.evaluate(textLines)).toBe(1);
});

test("below a table frame of 34rem the activities are cards, each headed by its marks and its reference", async ({ page }) => {
  for (const width of [540, 390]) {
    await openPlan(page, width);
    await expect(view(page, "cards")).toBeVisible();
    await expect(view(page, "table")).toBeHidden();
    expect(await refsIn(page, "cards"), `${width} px`).toEqual(MARKED);
  }
  await expect(page.getByRole("heading", { level: 3, name: "Needs a look KE-NWWDA-541055-CW-RFB" })).toBeVisible();
  await view(page, "cards").getByRole("button", { name: "Show them" }).click();
  expect(await refsIn(page, "cards")).toEqual([...MARKED, ...FOLDED]);
  // Below 768 px the breadcrumb shows only its parent, the project (ticket 100).
  await expect(page.getByRole("navigation", { name: "Breadcrumb" }).getByRole("link")).toHaveText("Water and Sanitation Development (P156634)");
});

test("a card's Process status takes its full width, as Method does, so STEP's Pending Implementation keeps to one line", async ({ page }) => {
  await openPlan(page, 540);
  const card = view(page, "cards").locator("li").filter({ has: page.locator("[data-activity=KE-NWWDA-541055-CW-RFB]") });
  const status = card.locator("dl > div").filter({ has: page.getByText("Process status", { exact: true }) }).locator("dd");
  for (const width of [540, 390]) {
    await page.setViewportSize({ width, height: 900 });
    await expect(status).toHaveText("Pending Implementation");
    expect(await status.evaluate(textLines), `${width} px`).toBe(1);
  }
});

test("from 1024 px the header sticks and focused rows stay 8 px clear of it; below 1024 px it scrolls away", async ({ page }) => {
  await openPlan(page, 1440);
  const header = page.locator("[data-plan-header]");
  await expect(page.locator("[data-plan-check]")).toBeVisible();

  expect(await header.evaluate((el) => getComputedStyle(el).position)).toBe("sticky");
  const height = await header.evaluate((el) => (el as HTMLElement).offsetHeight);
  // The header sticks under the navy bar, which sticks too from 1024 px, so the padding counts the bar (ticket 93).
  expect(await page.evaluate(() => getComputedStyle(document.documentElement).scrollPaddingTop)).toBe(`${56 + height + 8}px`);
  await page.evaluate(() => window.scrollTo(0, 800));
  await expect.poll(async () => Math.round((await header.boundingBox())!.y), "the header sticks under the bar").toBe(56);
  await page.evaluate(() => window.scrollTo(0, 0));

  await page.setViewportSize({ width: 390, height: 900 });
  await expect.poll(() => header.evaluate((el) => getComputedStyle(el).position)).toBe("static");
  await expect.poll(() => page.evaluate(() => document.documentElement.style.scrollPaddingTop)).toBe("");

  // Ticket 100: it sticks by the window, from 1024 px with the rail's 960 px page area too, and only in a window at
  // least 50rem tall, so a short window keeps its rows in view (ticket 93's design review, item 6).
  await page.setViewportSize({ width: 1024, height: 900 });
  await expect.poll(() => header.evaluate((el) => getComputedStyle(el).position)).toBe("sticky");
  await page.setViewportSize({ width: 1440, height: 700 });
  await expect.poll(() => header.evaluate((el) => getComputedStyle(el).position)).toBe("static");
});

// What the visible table's cells look like at one width (ticket 100): any word broken inside itself, two letters or
// digits of one word on two lines; any Method line that starts with a dot or a dash; any reference that takes more
// than one line; any Estimated (US$) amount on more than one line; and any cell whose text runs past its content box.
// A break at a space or after a hyphen is no broken word, as DESIGN.md's Reference words allow.
function measureTable() {
  const visible = (element: Element) => element.getClientRects().length > 0;
  const linesOf = (cell: Element) => {
    const lines: { top: number; text: string }[] = [];
    const walker = document.createTreeWalker(cell, NodeFilter.SHOW_TEXT);
    for (let node = walker.nextNode() as Text | null; node; node = walker.nextNode() as Text | null) {
      for (let i = 0; i < node.length; i++) {
        const range = document.createRange();
        range.setStart(node, i);
        range.setEnd(node, i + 1);
        const rect = range.getClientRects()[0];
        if (!rect) continue;
        const last = lines[lines.length - 1];
        if (last && Math.abs(last.top - rect.top) < 4) last.text += node.data[i];
        else lines.push({ top: rect.top, text: node.data[i] });
      }
    }
    return lines.map((line) => line.text.trim()).filter(Boolean);
  };
  const word = /[\p{L}\p{N}]/u;
  const cells = Array.from(document.querySelectorAll("[data-view=table] thead th, [data-view=table] tbody tr[id] > *")).filter(visible);
  const brokenWords: string[] = [];
  const overflow: string[] = [];
  for (const cell of cells) {
    const box = cell.getBoundingClientRect();
    const style = getComputedStyle(cell);
    const right = box.right - parseFloat(style.paddingRight) + 0.5;
    const walker = document.createTreeWalker(cell, NodeFilter.SHOW_TEXT);
    for (let node = walker.nextNode() as Text | null; node; node = walker.nextNode() as Text | null) {
      let last: { top: number; char: string } | null = null;
      for (let i = 0; i < node.length; i++) {
        const char = node.data[i];
        // A line may break at a space, which then takes no room at the line's end.
        if (/\s/.test(char)) {
          last = null;
          continue;
        }
        const range = document.createRange();
        range.setStart(node, i);
        range.setEnd(node, i + 1);
        const rect = range.getClientRects()[0];
        if (!rect || rect.width === 0) continue;
        if (last && rect.top - last.top > 4 && word.test(char) && word.test(last.char)) brokenWords.push(node.data.trim());
        if (rect.right > right) overflow.push(`${(cell.closest("tr") as HTMLElement).id || "head"}: ${node.data.trim()}`);
        last = { top: rect.top, char };
      }
    }
  }
  const rows = Array.from(document.querySelectorAll("[data-view=table] tbody tr[id]")).filter(visible);
  const splitRefs: string[] = [];
  const lineStarts: string[] = [];
  const wrappedAmounts: string[] = [];
  for (const row of rows) {
    if (linesOf(row.querySelector("th [data-row-ref]")!).length !== 1) splitRefs.push(row.id);
    if (visible(row.children[1])) for (const line of linesOf(row.children[1])) if (/^[·-]/.test(line)) lineStarts.push(`${row.id}: ${line}`);
    if (linesOf(row.children[3]).length > 1) wrappedAmounts.push(row.children[3].textContent!);
  }
  return { brokenWords: [...new Set(brokenWords)], overflow, splitRefs, lineStarts, wrappedAmounts };
}

// The longest real value of each kind in the fixture (the shell redesign plan, 7.10), put into the NWWDA plan's rows to
// test the layout, not the facts: a 257-character Description and the reference it belongs to (packages-p156634-page-2.json),
// an all-capitals Description, an estimate of 232,524,000.00 with its Open - International and Prior
// (source-plan-p161305-3.json), a reference with spaces (timeline-p156634.json) and a 54-character agency
// (project-p120014.json).
const LONGEST = {
  ref: "KE-KIMAWASCO-76105-GO-RFB",
  description:
    "Supply and delivery of al l small customer meters(3,510 no.) to AMR enabled meter s(DN15mm-32mm) and majo r customer meters " +
    "(81 no-ult rasonic meters with integrate d radio module of size DN40, DN50-DN150mm),15nos.port able meter testing kit and 1n o. bench",
  capitals:
    "(PCKG 2) HORN OF AFRICA G ATEWAY DEVELOPMENT PROJ ECT (HoAGDP): PACKAGE 2 LOT 1: Wajir - Tarbaj road (A 13) (57km) LOT 2: " +
    "Tarbaj - Kotulo road ( A13) (64km) LOT 3: Kotulo - Kobo road (A13) (38km) LOT 4: Kobo - Elwak road (A13) (26km)",
  estimate: "232524000.00",
  spaced: "KE-WSTF-381008-CS-INDV-FIN MGT CONS",
  agency: "Rural Electrification and Renewable Energy Corporation",
};

async function longestCheck(): Promise<string> {
  const result = JSON.parse(await recorded("check-plan-p156634-nwwda-2026-10-09.json"));
  const row = (ref: string) => result.rows.find((found: { activity_reference_no: string }) => found.activity_reference_no === ref);
  Object.assign(row("KE-NWWDA-541055-CW-RFB"), { activity_reference_no: LONGEST.ref, description: LONGEST.description });
  Object.assign(row("KE-NWWDA-229129-CW-RFB"), {
    description: LONGEST.capitals,
    estimated_amount_usd: LONGEST.estimate,
    market_approach: "Open - International",
    review_type: "Prior",
  });
  Object.assign(row("KE-NWWDA-541062-CW-RFQ"), { activity_reference_no: LONGEST.spaced });
  result.plan.implementing_agency = LONGEST.agency;
  return JSON.stringify(result);
}

test("the table draws six columns at 1280 and 1440 px and three at 1024 px with the rail, and no word in a cell breaks inside itself in the real and the longest data", async ({ page }) => {
  for (const [data, body] of [["real", await recorded("check-plan-p156634-nwwda-2026-10-09.json")], ["longest", await longestCheck()]]) {
    await openPlan(page, 1440, { body });
    await view(page, "table").getByRole("button", { name: "Show them" }).click();
    await page.evaluate(() => document.fonts.ready);
    for (const [width, columns] of [[1024, 3], [1280, 6], [1440, 6]]) {
      await page.setViewportSize({ width, height: 900 });
      await expect(view(page, "table").locator("thead th:visible"), `${data} data at ${width} px`).toHaveCount(columns);
      const { splitRefs, ...rest } = await page.evaluate(measureTable);
      expect(rest, `${data} data at ${width} px`).toEqual({ brokenWords: [], overflow: [], lineStarts: [], wrappedAmounts: [] });
      // Every real reference keeps to one line; the longest, with spaces, may wrap at them.
      if (data === "real") expect(splitRefs, `${width} px`).toEqual([]);
    }
  }
});

// Ticket 100: a row's reference opens the row's records in the evidence drawer, beside the page. The values are the
// recorded check's for KE-NWWDA-229129-CW-RFB, which tests/ground_truth/values.toml quotes from the plan's page 3.
test("a row's reference opens its records in the drawer, the row keeps the current mark, Escape returns focus, and a count word marks the rows it counts", async ({ page }) => {
  await openSidebar(page);
  await page.setViewportSize({ width: 1440, height: 900 });
  await mockApi(page, {
    "/api/me": { body: await recorded("me.json") },
    "/api/freshness": { body: await recorded("freshness.json") },
    [API]: { body: await recorded("check-plan-p156634-nwwda-2026-10-09.json") },
    "/api/evidence/opened": { body: '{"opened":[],"recorded":true}' },
  });
  await page.goto(PLAN);
  const ref = "KE-NWWDA-229129-CW-RFB";
  const reference = view(page, "table").getByRole("button", { name: ref, exact: true });
  const row = view(page, "table").locator(`tr[id="${ref}"]`);
  await expect(reference).toHaveAttribute("aria-expanded", "false");
  // The reference reads as the text link it is: every part of it is underlined (DESIGN.md section 10).
  for (const part of await reference.locator("span.inline-block").all()) await expect(part).toHaveCSS("text-decoration-line", "underline");
  const opened = page.waitForRequest((request) => request.method() === "POST" && new URL(request.url()).pathname === "/api/evidence/opened");

  await reference.click();

  const drawer = page.getByRole("dialog", { name: ref });
  await expect(drawer.getByRole("heading", { level: 2 })).toBeFocused();
  await expect(drawer.locator("[data-drawer-caption]")).toHaveText("Activity in the Northern Water Works Development Agency plan of October 9, 2026");
  await expect(drawer.locator("[data-badge=watch]")).toBeVisible();
  await expect(drawer.locator("[data-row-found]")).toContainText(
    "Signed January 3, 2022, 186 days after its planned date, at US$1,245,092.76, about 4 times its estimate.",
  );
  const pairs = (kind: string) =>
    drawer.locator(`[data-records=${kind}] > div`).evaluateAll((lines) => lines.map((line) => [line.querySelector("dt")!.textContent, line.querySelector("dd")!.textContent]));
  await expect(drawer.getByRole("heading", { level: 3 })).toHaveText(["What I checked", "From the plan row"]);
  // A group of facts in the drawer is an h3, 16 px 600 (DESIGN.md section 3).
  await expect(drawer.getByRole("heading", { level: 3 }).first()).toHaveCSS("font-size", "16px");
  // The planned date names the plan it came from, the one that first listed the activity (check_plan's reason).
  expect(await pairs("checked")).toEqual([
    ["Planned signing", "Jul 1, 2021"],
    ["In the plan of", "Apr 21, 2021"],
    ["Contract signed", "Jan 3, 2022"],
    ["Days late", "186"],
    ["Actual Amount (US$)", "1,245,092.76"],
    ["Estimated Amount (US$)", "300,000.00"],
    ["Actual divided by estimated", "about 4"],
  ]);
  expect(await pairs("plan")).toEqual([
    ["Description", "Drilling of 4 Number Explor atory Boreholes In Wajir Cou nty"],
    ["Method", "Request for Bids"],
    ["Market Approach", "Open - National"],
    ["Review Type", "Post"],
    ["Estimated Amount (US$)", "300,000.00"],
    ["Process Status", "Signed"],
  ]);
  await expect(drawer.locator("[data-source]")).toContainText(
    "Procurement Plan, Northern Water Works Development Agency, P156634, version of October 9, 2026, disclosed October 9, 2026.",
  );
  await expect(drawer.getByRole("link", { name: `Open the activity ${ref}` })).toHaveAttribute("href", `/projects/P156634/packages/${ref}`);
  await expect(drawer.getByRole("link", { name: `See the past range for ${ref}` })).toHaveAttribute("href", `/packages/${ref}`);
  // Opening the records records the plan row as opened, under its own evidence id.
  expect((await opened).postDataJSON()).toMatchObject({ evidence_id: `strata.silver.plan_rows:40132287/${ref}` });
  // The row keeps the current mark while its records show: tint and a 3 px primary bar at its left edge.
  await expect(reference).toHaveAttribute("aria-expanded", "true");
  await expect(row).toHaveCSS("background-color", "rgb(233, 247, 253)");
  await expect(row.locator("th")).toHaveCSS("box-shadow", "rgb(0, 67, 112) 3px 0px 0px 0px inset");
  // At 1440 px with the sidebar open, the table keeps three columns beside the drawer.
  await expect(view(page, "table").locator("thead th:visible")).toHaveCount(3);
  // There a 22-character reference keeps to one line (ticket 100's design review, item 12).
  expect(await reference.locator("span.inline-block").evaluate((part) => part.getClientRects().length === 1 && part.getBoundingClientRect().height < 30)).toBe(true);

  await page.keyboard.press("Escape");
  await expect(drawer).toHaveCount(0);
  await expect(reference).toBeFocused();
  await expect(row).not.toHaveAttribute("data-row-mark", /./);
  await expect(view(page, "table").locator("thead th:visible")).toHaveCount(6);

  // "two" in the finding marks the two Watch rows and moves focus to the first one's reference.
  const two = page.locator("[data-finding]").getByRole("button", { name: "two" });
  await two.focus();
  await expect(page.getByRole("tooltip").locator("[data-num-act]")).toHaveText("Select to mark them below.");
  await page.keyboard.press("Enter");
  await expect(reference).toBeFocused();
  await expect(view(page, "table").locator("tbody tr[data-row-mark=counted]")).toHaveCount(2);
  expect(await view(page, "table").locator("tbody tr[data-row-mark=counted]").evaluateAll((rows) => rows.map((row) => row.id))).toEqual([
    "KE-NWWDA-229129-CW-RFB",
    "KE-NWWDA-541062-CW-RFQ",
  ]);
  // A counted row takes tint alone; only the row whose records are open keeps the bar, so the two never look alike.
  await expect(row).toHaveCSS("background-color", "rgb(233, 247, 253)");
  await expect(row.locator("th")).toHaveCSS("box-shadow", "none");
});

// Ticket 100 (ticket 59's landing item, with the bar's offset): a link that lands on any row brings it into view with
// nothing cut under the parts that stick, the bar from 1024 px and the head from a 1024 px window 50rem tall, and the
// row above it either in view whole or out of view whole. One page load at each size; the hash changes in place.
const ROWS = [...MARKED, ...FOLDED];
function landing(ref: string) {
  const target = Array.from(document.querySelectorAll<HTMLElement>("[data-activity]")).find(
    (element) => element.dataset.activity === ref && element.getClientRects().length > 0,
  )!;
  const block = target.closest("tr, li")!;
  const sticky = [document.querySelector("[data-nav-bar]")?.closest("header"), document.querySelector("[data-plan-header]")].filter(
    (part): part is HTMLElement => Boolean(part) && getComputedStyle(part!).position === "sticky",
  );
  const edge = Math.max(0, ...sticky.map((part) => part.getBoundingClientRect().bottom));
  let before = block.previousElementSibling;
  while (before && before.getClientRects().length === 0) before = before.previousElementSibling;
  const box = block.getBoundingClientRect();
  const above = before?.getBoundingClientRect();
  return {
    focused: document.activeElement === target,
    rowCut: box.top < edge - 0.5,
    aboveCut: above ? above.top < edge - 0.5 && above.bottom > edge + 0.5 : false,
    sticky: sticky.length,
  };
}

test("a link that lands on any row leaves no row cut under the bar and the head at 1440 by 900, 1440 by 700, 1024 by 768 and 320 by 568", async ({ page }) => {
  const sizes: [number, number, number][] = [
    // Width, height, and how many parts stick: the bar and the head, the bar alone in a window under 50rem tall,
    // and nothing below 1024 px.
    [1440, 900, 2],
    [1440, 700, 1],
    [1024, 768, 1],
    [320, 568, 0],
  ];
  for (const [width, height, sticking] of sizes) {
    await page.setViewportSize({ width, height });
    await openPlanAt(page, width, height);
    for (const ref of ROWS) {
      await page.evaluate((hash) => (window.location.hash = hash), ref);
      await expect.poll(() => page.evaluate(landing, ref), `${ref} at ${width} by ${height}`).toEqual({
        focused: true,
        rowCut: false,
        aboveCut: false,
        sticky: sticking,
      });
    }
  }
});

test("with a 54-character agency and a 232,524,000.00 estimate nothing scrolls sideways at 320 px, and the head's name wraps in full", async ({ page }) => {
  await openPlan(page, 320, { body: await longestCheck() });
  await expect(page.locator("main h1")).toHaveText(LONGEST.agency);
  await page.evaluate(() => document.fonts.ready);
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(320);
  await expect(view(page, "cards").getByText("232,524,000.00", { exact: true })).toBeVisible();
});

// The check line, as every page shows it (DESIGN.md section 5, Check line), starts on its panel's text edge with no
// indent: that is checks.spec.ts's, on the answer panel.

// The head of a plan with a signal to draft from holds the pill and the action on one row, their centres level, beside
// the title at 1440 and 1024 px (ticket 100, from ticket 94's critique).
test("the head keeps the check pill and Draft review notes on one row, their centres level, at 1440 and 1024 px", async ({ page }) => {
  await openPlan(page, 1440);
  const centre = async (locator: import("@playwright/test").Locator) => {
    const box = (await locator.boundingBox())!;
    return box.y + box.height / 2;
  };
  for (const width of [1440, 1024]) {
    await page.setViewportSize({ width, height: 900 });
    const pill = page.locator("[data-plan-header] [data-check-pill]");
    const action = page.getByRole("button", { name: "Draft review notes (3 rows)" });
    expect(Math.abs((await centre(pill)) - (await centre(action))), `${width} px`).toBeLessThanOrEqual(2);
  }
});

test("while the check loads, skeletons hold its places and a status says so", async ({ page }) => {
  await page.setViewportSize({ width: windowBeside(1440), height: 900 });
  await mockApi(page, { "/api/me": { body: await recorded("me.json") }, "/api/freshness": { body: await recorded("freshness.json") } });
  let release!: () => void;
  const held = new Promise<void>((resolve) => (release = resolve));
  await page.route(`**${API}`, async (route) => {
    await held;
    await route.fulfill({ status: 200, contentType: "application/json", body: await recorded("check-plan-p156634-nwwda-2026-10-09.json") });
  });
  // The page's clock runs fast through the two seconds before the database line.
  await page.clock.install();
  await page.goto(PLAN);

  await expect(page.locator("[data-plan-skeleton]")).toBeVisible();
  // Ticket 111: the status says the step the narration shows, once.
  await expect(page.getByRole("status").filter({ hasText: NARRATION.running })).toHaveCount(1);
  // The h1's bar stands for the agency's name: 60% of the header's row, at most 560 px (the 10
  // brief, section 6), not the width of the date's bar under it.
  const nameBar = page.locator("[data-plan-header] h1 [data-skeleton]").filter({ visible: true });
  expect(Math.round((await nameBar.boundingBox())!.width)).toBeGreaterThanOrEqual(480);
  // A heading holds only phrasing content, so the bars inside it are spans, never a div.
  await expect(page.locator("[data-plan-header] h1 div")).toHaveCount(0);
  await expect(page.locator("[data-plan-skeleton] thead th")).toHaveText([
    "Activity",
    "Method and market approach",
    "Review",
    "Estimated (US$)",
    "Process status",
    "What Strata found",
  ]);
  await page.clock.fastForward(2000);
  await expect(page.getByText(NARRATION.slow)).toBeVisible();
  // The header's skeleton has the populated header's shape, with the pill's bar on the right, and the narration
  // holds the byline's, the finding's and the method's places, its database line included, so the table under
  // them does not move when the rows arrive (the 10 brief, section 7; ticket 111).
  await page.evaluate(() => document.fonts.ready);
  const top = (selector: string) => page.locator(selector).evaluate((element) => element.getBoundingClientRect().top + window.scrollY);
  const header = { loading: await top("[data-plan-header]"), table: await top("[data-plan-skeleton] thead") };
  release();
  await expect(page.getByRole("status").filter({ hasText: "Checked nine activities." })).toHaveCount(1);
  expect(Math.abs((await top("[data-plan-header]")) - header.loading)).toBeLessThanOrEqual(1);
  expect(Math.abs(header.table - (await top("[data-view=table] thead")))).toBeLessThanOrEqual(1);
});

// Ticket 111: while its one request runs, the plan check says what I'm doing in the finding's place with the answer
// panel's own steps, one running step and how I check under it, and after two seconds why it can take longer, with
// no timer. The page's clock runs fast through those two seconds.
for (const width of [1440, 390]) {
  test(`at ${width} px, while the check runs, the finding's place says what I'm doing, and the finding replaces it`, async ({ page }) => {
    await page.setViewportSize({ width: windowBeside(width), height: 900 });
    await mockApi(page, { "/api/me": { body: await recorded("me.json") }, "/api/freshness": { body: await recorded("freshness.json") } });
    let release!: () => void;
    const held = new Promise<void>((resolve) => (release = resolve));
    await page.route(`**${API}`, async (route) => {
      await held;
      await route.fulfill({ status: 200, contentType: "application/json", body: await recorded("check-plan-p156634-nwwda-2026-10-09.json") });
    });
    // When the page's h1 and the narration first drew, and each line the page's status said, in order.
    await page.addInitScript(() => {
      const seen = { h1: -1, narration: -1, said: [] as string[] };
      (window as unknown as { seen: typeof seen }).seen = seen;
      new MutationObserver(() => {
        const now = performance.now();
        if (seen.h1 < 0 && document.querySelector("main h1")) seen.h1 = now;
        if (seen.narration < 0 && document.querySelector("[data-plan-narration]")) seen.narration = now;
        const line = document.querySelector("[data-check-plan-page] > [role=status]")?.textContent ?? "";
        if (line && seen.said.at(-1) !== line) seen.said.push(line);
      }).observe(document, { subtree: true, childList: true, characterData: true });
    });
    const seen = () => page.evaluate(() => (window as unknown as { seen: { h1: number; narration: number; said: string[] } }).seen);
    await recordTransitions(page);
    await page.clock.install();
    await page.goto(PLAN);

    const narration = page.locator("[data-plan-narration]");
    const running = narration.locator("[data-steps] li[data-step=running]");
    await expect(running).toContainText(NARRATION.running);
    await expect(running.locator("svg.animate-spin")).toBeVisible();
    await expect(running.locator("[data-step-items] li")).toHaveText([NARRATION.how]);
    // The narration draws with the page's first frame, never after a delay.
    const first = await seen();
    expect(first.narration - first.h1).toBeLessThanOrEqual(100);
    // It sits above today's table skeleton: the skeleton table's head from 1024 px, its first card below.
    await page.evaluate(() => document.fonts.ready);
    const box = async (selector: string) => {
      const found = (await page.locator(selector).filter({ visible: true }).first().boundingBox())!;
      return { top: found.y, bottom: found.y + found.height, height: found.height };
    };
    const rows = width < 1024 ? "[data-skeleton-cards] > li" : "[data-plan-skeleton] thead";
    const told = await box("[data-plan-narration]");
    expect(told.bottom).toBeLessThanOrEqual((await box(rows)).top);
    // The steps announce nothing themselves: the page's one polite status says the step.
    await expect(narration.locator("[aria-live]")).toHaveCount(0);
    await expect(page.getByRole("status").filter({ hasText: NARRATION.running })).toHaveCount(1);

    await page.clock.fastForward(2000);
    await expect(running.locator("[data-step-items] li")).toHaveText([NARRATION.how, NARRATION.slow]);
    await expect(page.getByText("Still checking this plan.")).toHaveCount(0);
    // The database line keeps to the narration's reserved height.
    expect(Math.abs((await box("[data-plan-narration]")).height - told.height)).toBeLessThanOrEqual(1);

    release();
    await expect(page.getByRole("heading", { level: 2, name: FINDING })).toBeVisible();
    await expect(narration).toHaveCount(0);
    // The finding takes the narration's place, its byline on the narration's top line, and no other part of the page,
    // its rows and source line included, has a byline.
    await expect(page.locator("[data-byline]")).toHaveText(["Strata found"]);
    await expect(page.locator("[data-plan-check] [data-byline] + h2")).toHaveText(FINDING);
    // The status said the step once, then how many activities were checked.
    await expect.poll(async () => (await seen()).said).toEqual([NARRATION.running, "Checked nine activities."]);
    // The narration showed for more than 400 ms, so the finding entered: opacity and a 4 px rise over 200 ms.
    await animationsDone(page);
    expect(byProperty(await transitionsOn(page, "findingBlock"))).toEqual(ENTERED);
    expect(Math.abs((await box("[data-plan-check] [data-byline]")).top - told.top)).toBeLessThanOrEqual(1);
  });
}

// What the finding's entrance runs, in the order byProperty sorts it (DESIGN.md section 4, Motion; ticket 111).
const ENTERED = [
  { property: "opacity", from: "0", duration: 200, delay: 0 },
  { property: "translate", from: "0px 4px", duration: 200, delay: 0 },
];
const byProperty = (moved: Omit<Moved, "on">[]) => [...moved].sort((a, b) => a.property.localeCompare(b.property));

test("a check that arrives before its narration has shown for 400 ms puts the finding up at once", async ({ page }) => {
  await recordTransitions(page);
  // When the narration came and went, as the page drew it.
  await page.addInitScript(() => {
    const shown = { from: -1, to: -1 };
    (window as unknown as { shown: typeof shown }).shown = shown;
    new MutationObserver(() => {
      const here = document.querySelector("[data-plan-narration]") !== null;
      if (here && shown.from < 0) shown.from = performance.now();
      if (!here && shown.from >= 0 && shown.to < 0) shown.to = performance.now();
    }).observe(document, { subtree: true, childList: true });
  });
  await openPlan(page);
  await expect(page.getByRole("heading", { level: 2, name: FINDING })).toBeVisible();
  await animationsDone(page);
  const shown = await page.evaluate(() => (window as unknown as { shown: { from: number; to: number } }).shown);
  const showed = shown.to - shown.from;
  // The recorded check answers at once. On a busy computer it can still take 400 ms or more, and then the finding
  // enters, as after any wait that long; a few milliseconds either side of 400 prove nothing, so they are left out.
  if (showed < 350) expect(await transitionsOn(page, "findingBlock")).toEqual([]);
  else if (showed > 450) expect(byProperty(await transitionsOn(page, "findingBlock"))).toEqual(ENTERED);
});

test("under reduced motion the finding replaces a long narration with no transition", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.setViewportSize({ width: windowBeside(1440), height: 900 });
  await mockApi(page, { "/api/me": { body: await recorded("me.json") }, "/api/freshness": { body: await recorded("freshness.json") } });
  let release!: () => void;
  const held = new Promise<void>((resolve) => (release = resolve));
  await page.route(`**${API}`, async (route) => {
    await held;
    await route.fulfill({ status: 200, contentType: "application/json", body: await recorded("check-plan-p156634-nwwda-2026-10-09.json") });
  });
  await recordTransitions(page);
  await page.clock.install();
  await page.goto(PLAN);
  await expect(page.locator("[data-plan-narration]")).toBeVisible();
  await page.clock.fastForward(2000);
  release();
  await expect(page.getByRole("heading", { level: 2, name: FINDING })).toBeVisible();
  expect(await transitionsOn(page, "findingBlock")).toEqual([]);
});

test("at 1024 and 390 px the skeleton is as tall as the header, finding and method above the rows, so the rows stay put", async ({ page }) => {
  await page.setViewportSize({ width: 1024, height: 900 });
  await mockApi(page, { "/api/me": { body: await recorded("me.json") }, "/api/freshness": { body: await recorded("freshness.json") } });
  let release!: () => void;
  const held = new Promise<void>((resolve) => (release = resolve));
  await page.route(`**${API}`, async (route) => {
    await held;
    await route.fulfill({ status: 200, contentType: "application/json", body: await recorded("check-plan-p156634-nwwda-2026-10-09.json") });
  });
  await page.goto(PLAN);
  await expect(page.locator("[data-plan-skeleton]")).toBeVisible();
  await page.evaluate(() => document.fonts.ready);
  // The rows' top: the table's head from 1024 px, the first card below it.
  const rowsTop = async (table: string, cards: string) => {
    const tops: Record<number, number> = {};
    for (const width of [1024, 390]) {
      await page.setViewportSize({ width, height: 900 });
      const first = page.locator(width < 1024 ? `${cards} li` : `${table} thead`).first();
      tops[width] = await first.evaluate((element) => element.getBoundingClientRect().top + window.scrollY);
    }
    return tops;
  };
  // The skeleton's cards, not the narration's steps above them, which are a list too (ticket 111).
  const loading = await rowsTop("[data-plan-skeleton]", "[data-skeleton-cards]");

  release();
  await expect(page.locator("[data-plan-check]")).toBeVisible();

  const ready = await rowsTop("[data-view=table]", "[data-view=cards]");
  for (const width of [1024, 390]) expect(Math.abs(ready[width] - loading[width]), `${width} px`).toBeLessThanOrEqual(2);
});

test("opening a plan from the Procurement tab keeps focus on the page's h1 while the check loads and after it arrives", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await mockApi(page, {
    "/api/me": { body: await recorded("me.json") },
    "/api/freshness": { body: await recorded("freshness.json") },
    "/api/projects/P156634": { body: await recorded("project-p156634.json") },
    "/api/projects/P156634/packages": { body: await recorded("packages-p156634.json") },
  });
  let release!: () => void;
  const held = new Promise<void>((resolve) => (release = resolve));
  await page.route(`**${API}`, async (route) => {
    await held;
    await route.fulfill({ status: 200, contentType: "application/json", body: await recorded("check-plan-p156634-nwwda-2026-10-09.json") });
  });
  await page.goto("/projects/P156634/procurement");
  await page.locator("[data-agency=northern-water-works-development-agency] [data-table-view=table]").getByRole("link", { name: "Plan of Oct 9, 2026" }).click();
  const h1 = page.getByRole("main").getByRole("heading", { level: 1 });
  await expect(h1).toBeFocused();

  release();

  await expect(h1).toHaveText("Northern Water Works Development Agency");
  await expect(h1).toBeFocused();
});

// Ticket 100 (routed from ticket 94's review, F1): when the page's one read fails after an in-app link, the head is the
// same element it was while the check loaded, so focus stays on the h1 and never drops to the body.
test("a check that fails after an in-app link keeps focus on the page's h1, which names the page", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await mockApi(page, {
    "/api/me": { body: await recorded("me.json") },
    "/api/freshness": { body: await recorded("freshness.json") },
    "/api/projects/P156634": { body: await recorded("project-p156634.json") },
    "/api/projects/P156634/packages": { body: await recorded("packages-p156634.json") },
  });
  let release!: () => void;
  const held = new Promise<void>((resolve) => (release = resolve));
  await page.route(`**${API}`, async (route) => {
    await held;
    await route.fulfill({ status: 503, contentType: "application/json", body: '{"code": "data_service", "trace_id": "0af7651916cd43dd8448eb211c80319c"}' });
  });
  await page.goto("/projects/P156634/procurement");
  await page.locator("[data-agency=northern-water-works-development-agency] [data-table-view=table]").getByRole("link", { name: "Plan of Oct 9, 2026" }).click();
  const h1 = page.locator("main h1");
  await expect(h1).toBeFocused();

  release();

  await expect(page.getByRole("alert")).toContainText("I couldn't load this plan's check because the data service didn't answer.");
  await expect(h1).toHaveText("Procurement Plan");
  await expect(h1).toBeFocused();
});

test("below a table frame of 34rem the skeleton cards are as tall as the activity cards they stand for", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 900 });
  await mockApi(page, { "/api/me": { body: await recorded("me.json") }, "/api/freshness": { body: await recorded("freshness.json") } });
  let release!: () => void;
  const held = new Promise<void>((resolve) => (release = resolve));
  await page.route(`**${API}`, async (route) => {
    await held;
    await route.fulfill({ status: 200, contentType: "application/json", body: await recorded("check-plan-p156634-nwwda-2026-10-09.json") });
  });
  await page.goto(PLAN);
  await page.evaluate(() => document.fonts.ready);
  // The cards' heights at 390 px, where the four STEP fields take three rows, and at 540 px, where
  // Review and the amount share a row with room to spare.
  const widths = [390, 540];
  const heights = async (selector: string) => {
    const sizes: Record<number, number[]> = {};
    for (const width of widths) {
      await page.setViewportSize({ width, height: 900 });
      sizes[width] = await page
        .locator(selector)
        .evaluateAll((cards) => cards.filter((card) => card.getClientRects().length > 0).map((card) => card.getBoundingClientRect().height));
    }
    return sizes;
  };
  await expect(page.locator("[data-plan-skeleton]")).toBeVisible();
  const skeleton = await heights("[data-skeleton-cards] > li");

  release();
  await expect(page.locator("[data-plan-check]")).toBeVisible();

  const real = await heights("[data-view=cards] > ul:first-of-type > li:not([data-fold])");
  for (const width of widths) {
    for (const card of skeleton[width]) {
      expect(card, `${width} px`).toBeGreaterThanOrEqual(Math.min(...real[width]) - 1);
      expect(card, `${width} px`).toBeLessThanOrEqual(Math.max(...real[width]) + 1);
    }
  }
});

test("an agency with no plan says so and links to the project's plans", async ({ page }) => {
  await openPlan(page, 1440, { body: await recorded("check-plan-p156634-wajir-no-plan.json") }, "/projects/P156634/procurement/wajir-water-and-sewerage-company");

  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Wajir Water and Sewerage Company");
  const card = page.locator("[data-empty-state]");
  await expect(card.getByRole("heading", { level: 2 })).toHaveText("I don't have a Procurement Plan from Wajir Water and Sewerage Company yet.");
  await expect(card).toContainText("I can check a plan only after the World Bank discloses it and I have read it.");
  await expect(card.getByRole("link", { name: "All Procurement Plans for this project" })).toHaveAttribute("href", "/projects/P156634/procurement");
  await expect(page.locator("[data-check-pill]")).toHaveCount(0);
  // Empty states and alerts hold columns 1 to 8, as on every other page.
  expect(await widthOf(page, "[data-empty-state]")).toBe(EIGHT_COLUMNS);
});

test("a version the agency never published names the latest one", async ({ page }) => {
  const path = "/projects/P156634/procurement/northern-water-works-development-agency/2026-10-10";
  await openPlan(page, 1440, { body: await recorded("check-plan-p156634-nwwda-2026-10-10-not-found.json") }, path);

  const card = page.locator("[data-empty-state]");
  await expect(card.getByRole("heading", { level: 2 })).toHaveText("I don't have a plan from this agency dated October 10, 2026.");
  await expect(card).toContainText("The latest plan I have from this agency is dated October 9, 2026.");
  await expect(card.getByRole("link", { name: "Plan of Oct 9, 2026" })).toHaveAttribute("href", PLAN);
});

test("a service that didn't answer gives Try again and a reference; Try again that works moves focus to the finding", async ({ page }) => {
  await page.setViewportSize({ width: windowBeside(1440), height: 900 });
  await mockApi(page, { "/api/me": { body: await recorded("me.json") }, "/api/freshness": { body: await recorded("freshness.json") } });
  const good = await recorded("check-plan-p156634-nwwda-2026-10-09.json");
  let calls = 0;
  await page.route(`**${API}`, (route) => {
    calls += 1;
    return calls === 1
      ? route.fulfill({ status: 503, contentType: "application/json", body: '{"code": "data_service", "trace_id": "0af7651916cd43dd8448eb211c80319c"}' })
      : route.fulfill({ status: 200, contentType: "application/json", body: good });
  });
  await page.goto(PLAN);

  await expect(page.getByRole("alert")).toHaveText("I couldn't load this plan's check because the data service didn't answer.");
  await expect(page.getByText("If it fails again, send the data team this reference: 0af7651916cd43dd8448eb211c80319c.")).toBeVisible();
  // The h1 names the page, "Procurement Plan", and nothing else draws under it (ticket 100; plan 8.5). The status no
  // longer says it is checking.
  await expect(page.getByRole("main").getByRole("heading", { level: 1 })).toHaveText("Procurement Plan");
  await expect(page.getByRole("main").getByText("Procurement Plan", { exact: false })).toHaveCount(1);
  await expect(page.locator("[data-plan-header]")).toHaveCSS("border-bottom-width", "0px");
  // With nothing to act on, the head does not stick (DESIGN.md section 5, Plan check table).
  await expect(page.locator("[data-plan-header]")).toHaveCSS("position", "static");
  await expect(page.getByRole("status").filter({ hasText: "Checking this plan." })).toHaveCount(0);
  expect(await widthOf(page, "[role=alert]")).toBe(EIGHT_COLUMNS);
  // Ticket 94 (plan 8.5): the page's one read failed, so the alert sits in the page's alert slot, above the
  // breadcrumb and the h1, which names the page.
  await expect(page.locator("[data-alert-slot] [role=alert]")).toHaveCount(1);
  const [alert, crumbs] = [(await page.getByRole("alert").boundingBox())!, (await page.locator("[data-breadcrumb]").boundingBox())!];
  expect(alert.y + alert.height).toBeLessThan(crumbs.y);
  await page.getByRole("button", { name: "Try again" }).click();

  await expect(page.getByRole("heading", { level: 2, name: FINDING })).toBeFocused();
});

// Ticket 100's review, F2: a row's records come only from the check on the page, so a link to them on a check that
// failed says the drawer found nothing, never "Loading" for ever.
test("a link to a row's records on a check that failed says I found nothing, and stops loading", async ({ page }) => {
  await openPlan(page, 1440, { status: 503, body: '{"code": "data_service", "trace_id": "0af7651916cd43dd8448eb211c80319c"}' },
    `${PLAN}?evidence=${encodeURIComponent("plan-row-check:strata.silver.plan_rows:40132287/KE-NWWDA-229129-CW-RFB")}`);
  await expect(page.locator("[data-alert-slot] [role=alert]")).toBeVisible();
  const drawer = page.getByRole("dialog");
  await expect(drawer).toContainText("I have no source with this ID. The link may be incomplete.");
  await expect(drawer.locator("[data-skeleton]")).toHaveCount(0);
});

test("an account that can't read Strata's tables is told what to ask for, with no retry", async ({ page }) => {
  await openPlan(page, 1440, { status: 403, body: '{"code": "permission"}' });

  await expect(page.getByRole("alert")).toHaveText("Your account can't read Strata's tables, so I can't show this plan.");
  await expect(page.getByText("Ask your workspace admin for read access to the strata catalog.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Try again" })).toHaveCount(0);
});

// Each state loads once and is resized through the three widths, which keeps the axe runs quick.
async function axeAtEveryWidth(page: Page, label: string, ready: () => Promise<void>, widths = [1440, 1024, 390]) {
  for (const width of widths) {
    await page.setViewportSize({ width, height: 900 });
    await ready();
    expect(await axe(page), `${label} at ${width} px`).toEqual([]);
  }
}

test("axe finds no WCAG 2.2 AA violations at 1440, 1024 and 390 px with the fold closed and at 1440 and 390 px with it open, and the page reflows at 320 px", async ({ page }) => {
  await openPlan(page);
  const check = page.locator("[data-plan-check]");
  await axeAtEveryWidth(page, "folded", () => expect(check).toBeVisible());
  // The open fold adds rows of the same shape, so two widths cover it: the table and the cards.
  await page.locator("[data-fold] button:visible").click();
  await axeAtEveryWidth(page, "open", () => expect(check).toBeVisible(), [1440, 390]);
  await page.setViewportSize({ width: 320, height: 900 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(320);
});

test("axe finds no violations in the loading state at 1440, 1024 and 390 px, and in the empty and error states at 1440 and 390 px", async ({ page }) => {
  // Loading: the check never arrives.
  await mockApi(page, { "/api/me": { body: await recorded("me.json") }, "/api/freshness": { body: await recorded("freshness.json") } });
  await page.route(`**${API}`, () => new Promise(() => {}));
  await page.goto(PLAN);
  // The project's crumb is a link before its name arrives, so it reads the project's ID.
  await expect(page.getByRole("navigation", { name: "Breadcrumb" }).getByRole("link", { name: "Project P156634" })).toHaveAttribute("href", "/projects/P156634");
  await axeAtEveryWidth(page, "loading", () => expect(page.locator("[data-check-plan-page=loading]")).toBeVisible());

  // The permission error is the service error's frame without its button, so the service error covers it.
  const states: [string, Answer, string?][] = [
    ["empty", { body: await recorded("check-plan-p156634-wajir-no-plan.json") }, "/projects/P156634/procurement/wajir-water-and-sewerage-company"],
    ["error", { status: 503, body: '{"code": "data_service", "trace_id": "0af7651916cd43dd8448eb211c80319c"}' }],
  ];
  for (const [name, answer, path] of states) {
    await page.unrouteAll({ behavior: "ignoreErrors" });
    await openPlan(page, 1440, answer, path);
    const ready = page.locator(`[data-check-plan-page=${name === "empty" ? "ready" : "error"}]`);
    // At 1024 px these states draw the same card or alert in columns 1 to 8 as at 1440 px.
    await axeAtEveryWidth(page, name, () => expect(ready).toBeVisible(), [1440, 390]);
  }
});

// The 14 brief, section 2.5: the page lays out by the page area's width, so the evidence drawer
// narrows Check a plan without breaking it. At 1024 px the rail takes 64 px (ticket 92) and the drawer 40 percent of
// the window, 410 px (ticket 94),
// which leaves a 550 px page area that shows the activity cards, as a 550 px window would.
test("at 1024 px with the evidence drawer open, the plan check shows its cards and nothing scrolls sideways", async ({ page }) => {
  const ICR_54 = "strata.gold.passage:31525018/v1/54";
  await page.setViewportSize({ width: 1024, height: 900 });
  await mockApi(page, {
    "/api/me": { body: await recorded("me.json") },
    "/api/freshness": { body: await recorded("freshness.json") },
    [API]: { body: await recorded("check-plan-p156634-nwwda-2026-10-09.json") },
    "/api/evidence": { body: await recorded("evidence-icr-p130164-54.json") },
    "/api/evidence/opened": { body: '{"opened":[],"recorded":true}' },
  });
  await page.goto(`${PLAN}?evidence=${encodeURIComponent(ICR_54)}`);
  await expect(page.locator("[data-check-plan-page]:not([data-check-plan-page=loading])")).toBeVisible();
  await expect(page.getByRole("dialog")).toBeVisible();

  expect(await widthOf(page, "[data-page-column]")).toBe(550);
  await expect(view(page, "cards")).toBeVisible();
  await expect(view(page, "table")).toBeHidden();
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(1024);
  // One text edge runs through the panel's name, the definition over the cards and the cards (ticket 100's design
  // review, item 13), and the card list is named by its panel, not by the finding (item 15).
  const zone = page.locator("[data-section=activities]");
  const left = (locator: import("@playwright/test").Locator) => locator.evaluate((element) => Math.round(element.getBoundingClientRect().left));
  const edge = await left(zone.getByRole("heading", { level: 2 }));
  expect(await left(view(page, "cards").locator("p").first())).toBe(edge);
  expect(await left(view(page, "cards").locator("ul > li").first())).toBe(edge);
  await expect(view(page, "cards").getByRole("list").first()).toHaveAccessibleName("Activities in this plan");
});
