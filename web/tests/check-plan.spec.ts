// Check a plan (ticket 10) at seam 4: the NWWDA plan of October 9, 2026 for P156634, against the
// response recorded from check_plan in tests/fixtures/api, which the server tests check the server
// against. The words below are the ticket's, the blueprint wireframe's and the 10 design brief's,
// copied here so the test checks the copy file against an independent source.
//
// The plan lists nine activities. The wireframe draws eight and leaves out KE-NWWDA-207796-CS-INDV,
// which has no signals, so the screen shows six marked activities and folds three.
import AxeBuilder from "@axe-core/playwright";
import type { Page } from "@playwright/test";
import { expect, mockApi, recorded, test } from "./mocked";

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
const FINDING = "One needs a look and two are worth watching; three have data notes.";
const WCAG_22_AA = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];
// At 1440 px, columns 1 to 8 of the 12-column grid: 8 columns of 78.67 px and 7 gutters of 32 px.
const EIGHT_COLUMNS = 853;
const widthOf = async (page: Page, selector: string) => Math.round((await page.locator(selector).boundingBox())!.width);

type Answer = { status?: number; body: string };

async function openPlan(page: Page, width = 1440, answer?: Answer, path = PLAN) {
  await page.setViewportSize({ width, height: 900 });
  await mockApi(page, {
    "/api/me": { body: await recorded("me.json") },
    "/api/freshness": { body: await recorded("freshness.json") },
    [`/api${path.split("#")[0]}`]: answer ?? { body: await recorded("check-plan-p156634-nwwda-2026-10-09.json") },
  });
  await page.goto(path);
}

const view = (page: Page, name: "table" | "cards") => page.locator(`[data-view=${name}]`);
// The STEP references the view shows, top to bottom: each row header's or card heading's first line.
const refsIn = (page: Page, name: "table" | "cards") =>
  view(page, name).locator("[data-activity]").evaluateAll((elements) =>
    elements
      .filter((element) => element.getClientRects().length > 0)
      .map((element) => (element.firstElementChild ?? element).textContent?.trim()),
  );

async function axe(page: Page) {
  // Let the fold's fade-in finish, so contrast is measured on what stays on screen.
  await page.waitForFunction(() => document.getAnimations().every((animation) => animation.playState !== "running"));
  const results = await new AxeBuilder({ page }).withTags(WCAG_22_AA).analyze();
  return results.violations.map((v) => `${v.id}: ${v.nodes.map((node) => node.target.join(" ")).join(", ")}`);
}

test("the plan check finds every activity, states the finding, and folds the activities with no signals", async ({ page }) => {
  await openPlan(page);
  const main = page.getByRole("main");

  await expect(main.getByRole("heading", { level: 1 })).toHaveText("Northern Water Works Development Agency");
  await expect(main.getByText("Procurement Plan of October 9, 2026", { exact: true })).toBeVisible();
  await expect(main.locator("[data-check-pill]")).toHaveText("9 activities checked");
  await expect(main.getByRole("heading", { level: 2, name: FINDING })).toBeVisible();
  await expect(main.locator("[data-count-line]")).toHaveText("Showing 6 of 9 activities");
  await expect(view(page, "table")).toBeVisible();
  expect(await refsIn(page, "table")).toEqual(MARKED);
  const fold = view(page, "table").locator("[data-fold]");
  await expect(fold).toContainText(
    "Three more activities have no signals: KE-NWWDA-199471-GO-RFQ, NWWDA-WSDP-03-2019-2020 and KE-NWWDA-207796-CS-INDV.",
  );

  // The visible badges of each kind equal the counts in the finding.
  const table = view(page, "table");
  await expect(table.locator("[data-badge=needs-a-look]:visible")).toHaveCount(1);
  await expect(table.locator("[data-badge=watch]:visible")).toHaveCount(2);
  await expect(table.locator("[data-badge=data-note]:visible")).toHaveCount(3);
  await expect(page.getByRole("link", { name: "Water and Sanitation Development Project (P156634)" }).first()).toHaveAttribute(
    "href",
    "/projects/P156634",
  );
});

test("the fold states check_plan's count of unmarked activities and never counts the rows itself", async ({ page }) => {
  // A response whose count differs from its rows shows which one the screen states.
  const result = JSON.parse(await recorded("check-plan-p156634-nwwda-2026-10-09.json"));
  result.counts.unmarked = 12;
  await openPlan(page, 1440, { body: JSON.stringify(result) });

  await expect(view(page, "table").locator("[data-fold]")).toContainText("12 more activities have no signals.");
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
  await expect(page.locator("[data-count-line]")).toHaveText("Showing all 9 activities");
  for (const ref of FOLDED) {
    await expect(view(page, "table").locator(`tr[id="${ref}"]`)).toContainText("No signals.");
  }

  await hide.click();
  expect(await refsIn(page, "table")).toEqual(MARKED);
});

test("Show them opens the folded activities from the keyboard, and focus stays on the button", async ({ page }) => {
  await openPlan(page);
  const button = view(page, "table").locator("[data-fold] button");
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
    "Method · market approach",
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
    "Not visible to Strata: the prior-review queue, complaints, contract amendments and contract management reports. Those stay in STEP.",
  );
});

test("a number explains itself on focus, and What Strata found opens its definition", async ({ page }) => {
  await openPlan(page);
  const days = view(page, "table").locator('tr[id="KE-NWWDA-229129-CW-RFB"] button[data-num]').filter({ hasText: "186" });

  await days.focus();
  const tip = page.getByRole("tooltip");
  await expect(tip).toContainText("Planned signing date, as first published");
  await expect(tip).toContainText("July 1, 2021, in the plan of April 21, 2021");
  await expect(tip).toContainText("Days between them186");
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
  // After the breadcrumb's last link, the next tab stop is the finding's first count word.
  await page.getByRole("navigation", { name: "Breadcrumb" }).getByRole("link", { name: "Procurement" }).focus();

  await page.keyboard.press("Tab");

  await expect(page.getByRole("heading", { level: 2 }).getByRole("button", { name: "One" })).toBeFocused();
  await expect(page.getByRole("tooltip")).toContainText("The activities I counted:KE-NWWDA-541055-CW-RFB");
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

test("below 1024 px a link whose hash names a folded activity opens the fold and focuses that activity's card", async ({ page }) => {
  await openPlan(page, 390, undefined, `${PLAN}#KE-NWWDA-207796-CS-INDV`);

  await expect(view(page, "cards").locator('[data-activity="KE-NWWDA-207796-CS-INDV"]')).toBeFocused();
  await expect(view(page, "cards").getByRole("button", { name: "Hide them" })).toBeVisible();
});

test("below 1024 px the count line's row opens the What Strata found definition, since the cards have no column heads", async ({ page }) => {
  await openPlan(page, 390);
  const term = page.getByRole("button", { name: "What Strata found" });
  await expect(term).toHaveCount(1);

  await term.click();

  await expect(page.getByRole("dialog", { name: "What Strata found" })).toContainText("It gives a reason to look, never a finding.");
  await page.keyboard.press("Escape");

  // At 320 px the two don't fit side by side, so the definition takes a line of its own and
  // neither breaks.
  await page.setViewportSize({ width: 320, height: 900 });
  const lines = (element: Element) => {
    const range = document.createRange();
    range.selectNodeContents(element);
    return new Set(Array.from(range.getClientRects(), (rect) => Math.round(rect.top))).size;
  };
  expect(await page.locator("[data-count-line]").evaluate(lines)).toBe(1);
  expect(await term.evaluate(lines)).toBe(1);
});

test("below 1024 px the activities are cards, each headed by its marks and its reference", async ({ page }) => {
  for (const width of [1023, 768, 390]) {
    await openPlan(page, width);
    await expect(view(page, "table")).toBeHidden();
    expect(await refsIn(page, "cards"), `${width} px`).toEqual(MARKED);
  }
  await expect(page.getByRole("heading", { level: 3, name: "Needs a look KE-NWWDA-541055-CW-RFB" })).toBeVisible();
  await view(page, "cards").getByRole("button", { name: "Show them" }).click();
  expect(await refsIn(page, "cards")).toEqual([...MARKED, ...FOLDED]);
  // Below 768 px the breadcrumb shows only its parent.
  await expect(page.getByRole("navigation", { name: "Breadcrumb" }).getByRole("link")).toHaveText("Procurement");
});

test("from 1024 px the header sticks and focused rows stay 8 px clear of it; below 1024 px it scrolls away", async ({ page }) => {
  await openPlan(page, 1440);
  const header = page.locator("[data-plan-header]");
  await expect(page.locator("[data-plan-check]")).toBeVisible();

  expect(await header.evaluate((el) => getComputedStyle(el).position)).toBe("sticky");
  const height = await header.evaluate((el) => (el as HTMLElement).offsetHeight);
  expect(await page.evaluate(() => document.documentElement.style.scrollPaddingTop)).toBe(`${height + 8}px`);

  await page.setViewportSize({ width: 390, height: 900 });
  await expect.poll(() => header.evaluate((el) => getComputedStyle(el).position)).toBe("static");
  await expect.poll(() => page.evaluate(() => document.documentElement.style.scrollPaddingTop)).toBe("");
});

// What the table's cells look like at one width: each line of a Method cell, whether each
// reference and each Market Approach sits on one line, and any cell whose text runs past its
// content box.
function measureTable() {
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
  const rows = Array.from(document.querySelectorAll("[data-view=table] tbody tr[id]"));
  const splitRefs: string[] = [];
  const splitApproaches: string[] = [];
  const lineStarts: string[] = [];
  const overflow: string[] = [];
  for (const row of rows) {
    const ref = row.querySelector("th span")!;
    if (linesOf(ref).length !== 1) splitRefs.push(row.id);
    const approach = row.children[1].querySelector("span");
    if (approach && linesOf(approach).length !== 1) splitApproaches.push(approach.textContent!);
    for (const line of linesOf(row.children[1])) if (/^[·-]/.test(line)) lineStarts.push(`${row.id}: ${line}`);
  }
  for (const cell of document.querySelectorAll("[data-view=table] thead th, [data-view=table] tbody tr[id] > *")) {
    const box = cell.getBoundingClientRect();
    const style = getComputedStyle(cell);
    const right = box.right - parseFloat(style.paddingRight) + 0.5;
    const walker = document.createTreeWalker(cell, NodeFilter.SHOW_TEXT);
    for (let node = walker.nextNode(); node; node = walker.nextNode()) {
      const range = document.createRange();
      range.selectNodeContents(node);
      for (const rect of range.getClientRects()) {
        if (rect.right > right) overflow.push(`${(cell.closest("tr") as HTMLElement).id || "head"}: ${node.textContent}`);
      }
    }
  }
  return { splitRefs, splitApproaches, lineStarts, overflow };
}

test("from 1024 to 1440 px each column fits its values: references and Market Approaches stay whole, and no Method line starts with a dot or a dash", async ({ page }) => {
  await openPlan(page, 1440);
  await view(page, "table").getByRole("button", { name: "Show them" }).click();
  await page.evaluate(() => document.fonts.ready);
  for (const width of [1024, 1100, 1200, 1280, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    await expect(view(page, "table")).toBeVisible();
    const { splitApproaches, ...rest } = await page.evaluate(measureTable);
    expect(rest, `${width} px`).toEqual({ splitRefs: [], lineStarts: [], overflow: [] });
    // Only below 1100 px may the longest Market Approach in the plan take two lines.
    expect(splitApproaches.filter((text) => width >= 1100 || text !== "Open - International"), `${width} px`).toEqual([]);
  }
});

test("at 1024 px the plan check is a table", async ({ page }) => {
  await openPlan(page, 1024);

  await expect(view(page, "cards")).toBeHidden();
  expect(await refsIn(page, "table")).toEqual(MARKED);
});

test("while the check loads, skeletons hold its places and a status says so", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await mockApi(page, { "/api/me": { body: await recorded("me.json") }, "/api/freshness": { body: await recorded("freshness.json") } });
  let release!: () => void;
  const held = new Promise<void>((resolve) => (release = resolve));
  await page.route(`**${API}`, async (route) => {
    await held;
    await route.fulfill({ status: 200, contentType: "application/json", body: await recorded("check-plan-p156634-nwwda-2026-10-09.json") });
  });
  // The page's clock runs fast through the two seconds before "Still checking this plan.".
  await page.clock.install();
  await page.goto(PLAN);

  await expect(page.locator("[data-plan-skeleton]")).toBeVisible();
  await expect(page.getByRole("status").filter({ hasText: "Checking this plan." })).toHaveCount(1);
  await expect(page.locator("[data-plan-skeleton] thead th")).toHaveText([
    "Activity",
    "Method · market approach",
    "Review",
    "Estimated (US$)",
    "Process status",
    "What Strata found",
  ]);
  await page.clock.fastForward(2000);
  await expect(page.getByText("Still checking this plan.")).toBeVisible();
  // The header's skeleton has the populated header's shape, with the pill's bar on the right, so
  // the table under it does not move when the rows arrive (the 10 brief, section 7).
  await page.evaluate(() => document.fonts.ready);
  const top = (selector: string) => page.locator(selector).evaluate((element) => element.getBoundingClientRect().top + window.scrollY);
  const header = { loading: await top("[data-plan-header]"), table: await top("[data-plan-skeleton] thead") };
  // "Still checking this plan." and its 4 px margin go when the rows arrive; nothing else moves.
  const still = await page.getByText("Still checking this plan.").evaluate((element) => element.getBoundingClientRect().height + 4);
  release();
  await expect(page.getByRole("status").filter({ hasText: "Checked nine activities." })).toHaveCount(1);
  expect(Math.abs((await top("[data-plan-header]")) - header.loading)).toBeLessThanOrEqual(1);
  expect(Math.abs(header.table - still - (await top("[data-view=table] thead")))).toBeLessThanOrEqual(1);
});

test("opening a plan from the Procurement tab keeps focus on the page's h1 while the check loads and after it arrives", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await mockApi(page, {
    "/api/me": { body: await recorded("me.json") },
    "/api/freshness": { body: await recorded("freshness.json") },
    "/api/projects/P156634": { body: await recorded("project-p156634.json") },
  });
  let release!: () => void;
  const held = new Promise<void>((resolve) => (release = resolve));
  await page.route(`**${API}`, async (route) => {
    await held;
    await route.fulfill({ status: 200, contentType: "application/json", body: await recorded("check-plan-p156634-nwwda-2026-10-09.json") });
  });
  await page.goto("/projects/P156634");
  await page.locator("[data-agency=northern-water-works-development-agency] [data-table-view=table]").getByRole("link", { name: "Plan of Oct 9, 2026" }).click();
  const h1 = page.getByRole("main").getByRole("heading", { level: 1 });
  await expect(h1).toBeFocused();

  release();

  await expect(h1).toHaveText("Northern Water Works Development Agency");
  await expect(h1).toBeFocused();
});

test("below 1024 px the skeleton cards are as tall as the activity cards they stand for", async ({ page }) => {
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
  const heights = (selector: string) =>
    page.locator(selector).evaluateAll((cards) => cards.filter((card) => card.getClientRects().length > 0).map((card) => card.getBoundingClientRect().height));
  await expect(page.locator("[data-plan-skeleton]")).toBeVisible();
  const skeleton = await heights("[data-plan-skeleton] li");

  release();
  await expect(page.locator("[data-plan-check]")).toBeVisible();

  const real = await heights("[data-view=cards] ul:first-child > li:not([data-fold])");
  for (const card of skeleton) {
    expect(card).toBeGreaterThanOrEqual(Math.min(...real) - 1);
    expect(card).toBeLessThanOrEqual(Math.max(...real) + 1);
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
  await page.setViewportSize({ width: 1440, height: 900 });
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
  // The h1 keeps what the address says, the plan's date, and says "Procurement Plan" once. The
  // status no longer says it is checking.
  await expect(page.getByRole("main").getByRole("heading", { level: 1 })).toHaveText("Procurement Plan of October 9, 2026");
  await expect(page.getByRole("main").getByText("Procurement Plan", { exact: false })).toHaveCount(1);
  await expect(page.getByRole("status").filter({ hasText: "Checking this plan." })).toHaveCount(0);
  expect(await widthOf(page, "[role=alert]")).toBe(EIGHT_COLUMNS);
  await page.getByRole("button", { name: "Try again" }).click();

  await expect(page.getByRole("heading", { level: 2, name: FINDING })).toBeFocused();
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

test("axe finds no violations in the loading, empty and error states at 1440, 1024 and 390 px", async ({ page }) => {
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
    await axeAtEveryWidth(page, name, () => expect(ready).toBeVisible());
  }
});
