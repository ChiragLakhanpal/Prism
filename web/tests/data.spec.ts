// The Data tab at seam 4 (ticket 16; the 16 design brief): Data readiness and Sources and licenses,
// against the mocked API, and the old How Strata works address, which opens Data readiness (ticket 97).
// The answers are the server's own on the fixture,
// recorded in tests/fixtures/api by tests/record_api.py, so every number the page shows is checked
// against the measure the server returned. Fixed words come from the brief and DESIGN.md section 8,
// copied here so the test checks the copy file against an independent source.
import { scan } from "./axe";
import type { Page, Route } from "@playwright/test";
import { readFile } from "node:fs/promises";
import { dataReadinessHref } from "../src/routes";
import { expect, mockShell, openSidebar, recorded, test, windowBeside } from "./mocked";
import { placements, readRegistry, type SourceRegistry } from "./registries";
import { fontsLoaded } from "./settled";

type Answer = { status?: number; file: string };

// /api/data/readiness answers by its query: the full page, the filtered page, and so on.
async function mockData(page: Page, readiness: Answer | ((query: URLSearchParams) => Answer), sources: Answer = { file: "data-sources.json" }) {
  await mockShell(page);
  const answer = async (route: Route, chosen: Answer) =>
    route.fulfill({ status: chosen.status ?? 200, contentType: "application/json", body: await recorded(chosen.file) });
  await page.route("**/api/data/readiness*", async (route) => {
    const query = new URL(route.request().url()).searchParams;
    await answer(route, typeof readiness === "function" ? readiness(query) : readiness);
  });
  await page.route("**/api/data/sources", (route) => answer(route, sources));
}

const FULL: Answer = { file: "data-readiness.json" };
// How many rows the Sources table holds in all, from the server's recorded answer, so a source added to the registry
// in one entry (the change drill, docs/change-drill.md) changes the recording, not these tests.
const sourceRows = async (file: string): Promise<number> => {
  const answer = JSON.parse(await recorded(file)) as { filter?: { total: number }; headline_abstention?: { sources: number } };
  return answer.filter?.total ?? answer.headline_abstention?.sources ?? Number.NaN;
};
const byQuery = (query: URLSearchParams): Answer =>
  query.get("asof") === "2026-10-01"
    ? { file: "data-readiness-before-first.json" }
    : query.get("sources") === "awards,notices"
      ? { file: "data-readiness-filtered.json" }
      : query.get("sources")?.includes("not-a-source")
        ? { file: query.get("sources") === "not-a-source" ? "data-readiness-no-known-key.json" : "data-readiness-unknown-key.json" }
        : FULL;

async function open(page: Page, path = "/data", width = 1440) {
  await page.setViewportSize({ width, height: 900 });
  await page.goto(path);
  await expect(page.locator("[data-readiness], [data-sources-page], main h1").first()).toBeVisible();
}

const json = async (name: string) => JSON.parse(await recorded(name));
const table = (page: Page, id: string) => page.locator(`[data-readiness-table=${id}] [data-table-view=table]`);
const cell = (page: Page, key: string) => table(page, "sources").locator(`[data-cell="${key}"]`);
// The count line under a table's title, such as "Showing 2 of 14 sources."
const countLine = (page: Page, id: string) => page.locator(`[data-readiness-table=${id}] [data-table-lines]`);

// The hardest documents, the plan pages the parser couldn't read and the fixes start as closed rows (ticket 104): a
// test of what they hold opens each one first, with its Show button.
async function openRows(page: Page) {
  const closed = page.locator("[data-readiness] [data-section-toggle][aria-expanded=false]");
  await expect(page.locator("[data-readiness=ready], [data-readiness=filtered]")).toBeVisible();
  for (let left = await closed.count(); left > 0; left -= 1) await closed.first().click();
}

async function violations(page: Page) {
  const results = await scan(page);
  return results.violations.map((v) => `${v.id}: ${v.nodes.map((node) => node.target.join(" ")).join(", ")}`);
}

// ── Data readiness ───────────────────────────────────────────────────────

// Ticket 104: Data readiness and Sources and licenses are the sidebar's items under Data, as Following and All projects
// are under Projects (ticket 99), so the page has no sub-tab row of its own.
test("the sidebar lists Data readiness and Sources and licenses under Data, and the page has no sub-tab row", async ({ page }) => {
  await mockData(page, FULL);
  await openSidebar(page);
  await open(page);

  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Data");
  await expect(page.locator("main h1 + p")).toHaveText(
    "See how far each source can support an answer and where each dataset comes from.",
  );
  await expect(page).toHaveTitle("Data readiness | Strata");
  await expect(page.getByRole("navigation", { name: "Data pages" })).toHaveCount(0);
  await expect(page.locator("main nav")).toHaveCount(0);
  const sidebar = page.getByRole("navigation", { name: "Main" });
  const items = sidebar.locator("[data-sub-items=data] a");
  await expect(items).toHaveText(["Data readiness", "Sources and licenses"]);
  await expect(items.first()).toHaveAttribute("aria-current", "page");
  await expect(sidebar.getByRole("link", { name: "Data", exact: true })).toHaveAttribute("aria-current", "true");
  // No other section shows its pages while Data is current.
  await expect(sidebar.locator("[data-sub-items]")).toHaveCount(1);

  await items.nth(1).click();
  await expect(page).toHaveURL(/\/data\/sources$/);
  await expect(page).toHaveTitle("Sources and licenses | Strata");
  await expect(items.nth(1)).toHaveAttribute("aria-current", "page");
  await expect(items.first()).not.toHaveAttribute("aria-current");
  await expect(page.locator("main [data-lead]")).toBeFocused();
  await items.first().click();
  await expect(page).toHaveTitle("Data readiness | Strata");
  await expect(page.locator("main [data-lead]")).toBeFocused();
});

// Ticket 97: How Strata works is no longer a page (the deck at /present shows its figures). An old link to it lands on
// Data readiness, and the address is replaced, so Back goes to the page before it, never to the old address.
test("the old How Strata works address opens Data readiness and replaces the address", async ({ page }) => {
  await mockData(page, FULL);
  await open(page, "/data/sources");
  await page.goto("/data/how-strata-works#what-i-dont-do");

  await expect(page).toHaveURL(/\/data$/);
  await expect(page).toHaveTitle("Data readiness | Strata");
  await expect(page.locator("[data-readiness=ready]")).toBeVisible();
  await expect(page.locator("[data-sub-items=data] [data-sub-item=data]")).toHaveAttribute("aria-current", "page");
  await page.goBack();
  await expect(page).toHaveURL(/\/data\/sources$/);
});

test("every number in the Sources table is the measure the server returned for its cell", async ({ page }) => {
  const answer = await json("data-readiness.json");
  await mockData(page, FULL);
  await open(page);

  // Kenya's award rows and their STEP-reference link rate, which tests/ground_truth/values.toml
  // counts from the recorded award files: 632 rows; 528 of 603 contracts.
  await expect(cell(page, "awards:coverage").locator("[data-num]").first()).toHaveText("632");
  await expect(cell(page, "awards:linked").locator("[data-num]").first()).toHaveText("528 of 603, 88%");

  for (const row of answer.sources.filter((entry: { type: string }) => entry.type === "measured")) {
    for (const column of ["coverage", "linked", "read_well"]) {
      const given = row.cells[column];
      if (given.row === null || given.row === undefined) continue;
      const measure = answer.rows[given.row];
      const shown = await cell(page, `${row.id}:${column}`).locator("[data-num]").first().textContent();
      const count = measure.count.toLocaleString("en-US");
      const whole = column === "coverage" && measure.denominator === measure.count;
      expect(shown, `${row.id} ${column}`).toBe(whole ? count : `${count} of ${measure.denominator.toLocaleString("en-US")}${share(measure)}`);
    }
  }
});

// The share a cell shows, from the columns the tool returned, never from a division in the browser
// (review B2): a percent from 50 rows, about N in 10 from 20, and the words for a part that rounds to
// an end of its scale.
function share(measure: { share_percent: number | null; share_bound: string | null; in_ten: number | null; in_ten_exact: boolean | null }) {
  if (measure.share_percent !== null) {
    return measure.share_bound === "under" ? ", <1%" : measure.share_bound === "over" ? ", >99%" : `, ${measure.share_percent}%`;
  }
  if (measure.in_ten !== null) {
    return measure.share_bound === "under"
      ? ", fewer than 1 in 10"
      : measure.share_bound === "over"
        ? ", more than 9 in 10"
        : measure.in_ten_exact
          ? `, ${measure.in_ten} in 10`
          : `, about ${measure.in_ten} in 10`;
  }
  return "";
}

test("the headline is the server's sentence, and its caption says the measures' date and that no model wrote it", async ({ page }) => {
  const answer = await json("data-readiness.json");
  await mockData(page, FULL);
  await open(page);

  await expect(page.locator("[data-headline]")).toHaveText(answer.headline.text);
  await expect(page.locator("[data-lead] [data-headline] + p")).toHaveText(
    "I built this from the measures below, taken October 23, 2026. No model wrote it.",
  );
});

// Ticket 104: the headline is the page's one finding (DESIGN.md section 1, principle 7), in the finding style: 28 / 36
// light, 24 / 32 below a 48rem window, at most 22.5em wide. A line that holds a number keeps the finding's pitch (ticket
// 91's review, routed to ticket 96: a number's button padding grew each line that held one).
for (const [width, size, pitch] of [[1440, 28, 36], [390, 24, 32]] as const) {
  test(`at ${width} px the headline is the page's one finding, ${size} px light, and a line that holds a number keeps its ${pitch} px pitch`, async ({ page }) => {
    await mockData(page, FULL);
    await page.setViewportSize({ width: windowBeside(width), height: 900 });
    await page.goto("/data");
    await expect(page.locator("[data-readiness=ready]")).toBeVisible();
    await fontsLoaded(page);
    await expect(page.locator("main [data-finding]")).toHaveCount(1);
    const headline = page.locator("[data-headline]");
    await expect(headline).toHaveAttribute("data-finding");
    await expect(headline.locator("button[data-num]").first()).toBeVisible();
    const look = await headline.evaluate((element) => {
      const style = getComputedStyle(element);
      return { size: style.fontSize, weight: style.fontWeight, height: element.getBoundingClientRect().height };
    });
    expect([look.size, look.weight]).toEqual([`${size}px`, "300"]);
    expect(look.height).toBeGreaterThan(pitch);
    expect(look.height % pitch, `${look.height} px is a whole number of ${pitch} px lines`).toBe(0);
  });
}

// Ticket 104 (plan 8.4, Data): What you can ask and Sources hold open work, so each is a panel; the hardest documents,
// the plan pages the parser couldn't read and the fixes are read by few, so each is a closed row with its one sentence,
// which opens in place with focus kept on its button. At 390 px the page is at least 30 percent shorter than the
// 11,205 px of the study's capture (current/data-390.png).
test("What you can ask and Sources are panels, and the last three sections are closed rows that open in place", async ({ page }) => {
  await mockData(page, FULL);
  await open(page, "/data", 390);
  await expect(page.locator("[data-readiness=ready]")).toBeVisible();
  await fontsLoaded(page);
  expect(await page.evaluate(() => document.documentElement.scrollHeight)).toBeLessThanOrEqual(Math.floor(11_205 * 0.7));
  await page.setViewportSize({ width: windowBeside(1440), height: 900 });

  const zone = (key: string) => page.locator(`[data-readiness] [data-section=${key}]`);
  for (const [key, name] of [["kinds", "What you can ask"], ["sources", "Sources"]]) {
    await expect(zone(key)).toHaveAttribute("data-zone", "panel");
    await expect(zone(key).getByRole("heading", { level: 2 })).toHaveText(name);
  }
  const rows = page.locator("[data-readiness] [data-zone=row]");
  // Ticket 58: the plan pages the layout parser couldn't read are part of the hardest documents' section, not a second
  // section about the parser right after it. The fixture's run read every plan page, so its sentence says so.
  await expect(rows.getByRole("heading", { level: 2 })).toHaveText(["The hardest documents I read", "Fixes that would unlock the most"]);
  await expect(rows.locator("[data-section-summary]")).toHaveText([
    "I use these documents as a stress test for my reading. The layout parser read every Procurement Plan page it tried.",
    "I rank each fix by how many projects it would add evidence to.",
  ]);
  await expect(zone("failures")).toHaveCount(0);
  await expect(page.locator("[data-readiness-table=shelf] [data-table-view], [data-fixes] li")).toHaveCount(0);

  for (const [key, show, hide, inside] of [
    ["shelf", "Show the documents", "Hide the documents", "[data-readiness-table=shelf] [data-table-view=table]"],
    ["fixes", "Show the fixes", "Hide the fixes", "[data-fixes] li"],
  ]) {
    const button = zone(key).getByRole("button", { name: show });
    await expect(button).toHaveAttribute("aria-expanded", "false");
    await button.press("Enter");
    await expect(zone(key)).toHaveAttribute("data-zone", "panel");
    await expect(page.locator(inside).first()).toBeVisible();
    const pressed = zone(key).getByRole("button", { name: hide });
    await expect(pressed).toBeFocused();
    await expect(pressed).toHaveAttribute("aria-expanded", "true");
    await pressed.press("Enter");
    await expect(zone(key)).toHaveAttribute("data-zone", "row");
    await expect(page.locator(inside)).toHaveCount(0);
    await expect(button).toBeFocused();
  }
});

test("badges appear only on Partial and Gap cells, freshness reads like Oct 23 · daily, and nothing scores a source", async ({ page }) => {
  const answer = await json("data-readiness.json");
  await mockData(page, FULL);
  await open(page);

  const statuses = answer.sources.flatMap((row: { type: string; cells?: Record<string, { status?: string }> }) =>
    row.type === "gap" ? ["gap"] : Object.values(row.cells ?? {}).map((given) => given.status).filter(Boolean),
  );
  const badges = table(page, "sources").locator("[data-badge]");
  await expect(badges).toHaveCount(statuses.length);
  expect(new Set(await badges.evaluateAll((found) => found.map((badge) => badge.getAttribute("data-badge"))))).toEqual(new Set(["partial", "gap"]));
  await expect(cell(page, "awards:linked").locator("[data-badge=partial]")).toHaveText("Partial");
  await expect(cell(page, "awards:coverage").locator("[data-badge]")).toHaveCount(0);

  await expect(cell(page, "awards:fresh")).toContainText("Oct 23 · daily");
  await expect(cell(page, "awards_fy2001_2016:fresh")).toContainText("Jun 2016 · frozen");
  await expect(cell(page, "reports:fresh")).toContainText("Jun 30 · as published");
  await expect(cell(page, "awards:read_well")).toHaveText("Published as a table");
  // The registry gives the plans no freshness measure; their versions arrive as published.
  await expect(cell(page, "plans:fresh")).toHaveText("As published");
  // A limit the source declares sits on its own line, under what the number counts.
  await expect(cell(page, "cpia:coverage")).toContainText("264scores heldIDA countries onlyin 21 fiscal years");
  // A share breaks only after its comma: its count and its frequency each stay on one line.
  await expect(cell(page, "reports:read_well").locator("[data-num] .whitespace-nowrap")).toHaveText(["625 of 650,", "96%"]);
  // CPIA and WGI scores are a source's own values; no score of Strata's rates a source.
  expect(await page.locator("main").textContent()).not.toMatch(/composite|\bscore\b|overall/i);
});

// The places where a Sources row's cell text comes within 8 px of the next cell's on the same line.
async function tightCells(page: Page) {
  await expect(table(page, "sources")).toBeVisible();
  return table(page, "sources").evaluate((view) => {
    // The boxes of a cell's visible text, one for each line it runs.
    const boxes = (cell: Element) => {
      const found: DOMRect[] = [];
      const walker = document.createTreeWalker(cell, NodeFilter.SHOW_TEXT);
      for (let node = walker.nextNode(); node; node = walker.nextNode()) {
        if (!node.textContent?.trim()) continue;
        const range = document.createRange();
        range.selectNodeContents(node);
        found.push(...Array.from(range.getClientRects()).filter((box) => box.width > 1 && box.height > 1));
      }
      return found;
    };
    const close: string[] = [];
    for (const row of Array.from(view.querySelectorAll("tbody tr"))) {
      const cells = Array.from(row.children);
      cells.slice(1).forEach((right, index) => {
        const left = cells[index];
        for (const a of boxes(left))
          for (const b of boxes(right))
            if (a.top < b.bottom && b.top < a.bottom && b.left - a.right < 8)
              close.push(`${left.getAttribute("data-cell") ?? left.textContent} | ${right.getAttribute("data-cell")}: ${Math.round(b.left - a.right)} px`);
      });
    }
    return close;
  });
}

// Between 768 px, where the Sources table starts, and the widths a tablet holds in portrait, every
// cell's text keeps 8 px from its neighbour's on the same line: nothing spills into the next cell.
test("from 768 px no cell's text in the Sources table runs into the next cell's", async ({ page }) => {
  await mockData(page, FULL);
  for (const width of [768, 820, 900]) {
    await open(page, "/data", width);
    expect(await tightCells(page), `${width} px`).toEqual([]);
  }

  // Review r5 P2: a fresh measure can have no date. Its "Not measured yet" wraps like other text,
  // so it keeps clear of Read well too.
  const answer = await json("data-readiness.json");
  const reports = answer.sources.find((row: { id: string }) => row.id === "reports");
  answer.rows[reports.cells.fresh.row].as_of = null;
  await page.route("**/api/data/readiness*", (route) => route.fulfill({ contentType: "application/json", body: JSON.stringify(answer) }));
  await open(page, "/data", 768);
  const fresh = cell(page, "reports:fresh");
  await expect(fresh).toContainText("Not measured yet");
  expect(await tightCells(page), "768 px, with no date").toEqual([]);
  // Its text stays inside its own cell, so it never reaches the Read well cell's padding.
  const spill = await fresh.evaluate((box) => {
    const edge = box.getBoundingClientRect().left;
    const range = document.createRange();
    range.selectNodeContents(box);
    return Math.max(0, ...Array.from(range.getClientRects()).map((line) => Math.round(edge - line.left)));
  });
  expect(spill, "px the dateless Fresh cell's text runs past its own cell").toBe(0);
  // "Not measured yet" is not a value, so it is set as DESIGN.md section 5 sets it: regular, in
  // ink-muted (critique r6).
  const look = await fresh.getByText(/Not measured yet/).evaluate((element) => {
    const probe = document.createElement("span");
    probe.style.color = "var(--color-ink-muted)";
    document.body.append(probe);
    const muted = getComputedStyle(probe).color;
    probe.remove();
    return { muted: getComputedStyle(element).color === muted, weight: getComputedStyle(element).fontWeight };
  });
  expect(look).toEqual({ muted: true, weight: "400" });
});

// Critique r6: at 390 px the tables' source line broke its date ("taken Oct" then "23, 2026.").
test("at 390 px each table's source line keeps its date on one line", async ({ page }) => {
  await mockData(page, FULL);
  await open(page, "/data", 390);
  await openRows(page);

  const dates = page.locator("[data-readiness-table] [data-source] [data-num]");
  // Three tables: What you can ask, Sources, and the hardest documents (ticket 18), once opened.
  await expect(dates).toHaveCount(3);
  await expect(dates.first()).toHaveText("Oct 23, 2026");
  expect(await dates.evaluateAll((all) => all.map((date) => date.getClientRects().length))).toEqual([1, 1, 1]);
});

test("each column head holds its definition, and its label opens the full definition", async ({ page }) => {
  await mockData(page, FULL);
  await open(page);

  const heads = table(page, "sources").locator("thead th");
  await expect(heads).toHaveText([
    "Sourcewhere",
    "Coveragerows and fiscal years",
    "Linkedto projects and other records",
    "Read wellread without errors",
    "Freshlatest data, how often",
  ].map((text) => text.replace("Sourcewhere", "Source")));
  await heads.nth(2).getByRole("button", { name: "Linked" }).click();
  const definition = page.getByRole("dialog", { name: "Linked" });
  await expect(definition).toContainText(
    "How many of these rows I could join to the record they need: a project, a notice, a Procurement Plan, a sector or a borrower country. A row that doesn't join can't count in answers that need the join.",
  );
  await page.keyboard.press("Escape");
  await expect(definition).toBeHidden();
});

test("the fiscal 2017 to 2019 awards show as a Gap row with none published and the registry's note", async ({ page }) => {
  await mockData(page, FULL);
  await open(page);

  const row = table(page, "sources").locator("[data-row=fy2017_2019]");
  await expect(row.locator("th")).toHaveText("Contract awardsfiscal 2017–19");
  await expect(cell(page, "fy2017_2019:span")).toContainText("None published");
  await expect(cell(page, "fy2017_2019:span").locator("[data-badge=gap]")).toHaveText("Gap");
  await expect(cell(page, "fy2017_2019:span")).toContainText(
    "No World Bank dataset publishes contract awards for these years. Award notices cover most of them, in local currency.",
  );
  expect(await cell(page, "fy2017_2019:span").getAttribute("colspan")).toBe("4");
  // It sits directly under the source it belongs to.
  const order = await table(page, "sources").locator("tbody tr").evaluateAll((rows) => rows.map((tr) => tr.getAttribute("data-row")));
  expect(order.slice(0, 2)).toEqual(["awards", "fy2017_2019"]);
});

test("a number's tooltip says what was counted and when, and a click opens its measure; Escape returns focus to it", async ({ page }) => {
  await mockData(page, FULL);
  await open(page);

  const number = cell(page, "awards:linked").locator("[data-num]").first();
  await number.focus();
  // The Number tooltip's Window variant (DESIGN.md section 5; ticket 96): what was counted, when I measured it, and
  // what a click opens.
  const tip = page.getByRole("tooltip");
  await expect(tip.locator("[data-num-what]")).toHaveText("528 of 603 contracts.");
  await expect(tip.locator("[data-num-from]")).toHaveText("From my measures on October 23, 2026.");
  await expect(tip.locator("[data-num-act]")).toHaveText("Select to see how I measured it.");
  await number.press("Enter");
  const window = page.getByRole("dialog", { name: "Linked" });
  await expect(window).toContainText("Counted528");
  await expect(window).toContainText("Out of603");
  await expect(window).toContainText("Counted instrata.gold.contract");
  await expect(window.getByRole("heading", { name: "Linked" })).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(window).toBeHidden();
  await expect(number).toBeFocused();
});

test("every number's tooltip names what it counts, and its window shows the number that opened it", async ({ page }) => {
  await mockData(page, FULL);
  await open(page);

  // Design review B1: no tooltip reads "2 . Measured". Focus opens each one; the open tooltip is the
  // one the number names as its description.
  await expect(page.locator("[data-readiness=ready]")).toBeVisible();
  await openRows(page);
  // The cards below 768 px repeat the table's numbers and are hidden at this width.
  const numbers = page.locator("main button[data-num]").filter({ visible: true });
  const count = await numbers.count();
  expect(count).toBeGreaterThan(40);
  for (let index = 0; index < count; index += 1) {
    const number = numbers.nth(index);
    await number.focus();
    await expect(number, `number ${index}`).toHaveAttribute("aria-describedby", /.+/);
    const tip = page.locator(`[id="${await number.getAttribute("aria-describedby")}"]`);
    const said = await tip.locator("[data-num-what]").textContent();
    // A bare number would read "2 ." or "2.": a noun always sits between them.
    expect(said, `number ${index}`).not.toMatch(/^[\d,]+ ?\./);
    // Where it came from keeps its date on one line in the 20rem tooltip (ticket 59).
    const dates = await tip.locator("[data-num-from] [data-num-date]").evaluateAll((elements) => elements.map((element) => element.getClientRects().length));
    expect(dates, `number ${index}'s date`).toEqual([1]);
  }

  // The headline's 75 is a shortfall: its tooltip names what the 75 lack, and its window shows it
  // above the measure's own numbers.
  const shortfall = page.locator("[data-headline] [data-num]", { hasText: /^75$/ });
  await shortfall.focus();
  await expect(page.getByRole("tooltip").locator("[data-num-what]")).toHaveText(
    "75 of 603 contracts lack a reference from Systematic Tracking of Exchanges in Procurement (STEP).",
  );
  // The reports' check names what its pages lack, so its tooltip says so, as its sentence does
  // (critique r6; ticket 18 made paragraph numbers a check of the reports' row).
  const unread = table(page, "kinds").locator("[data-cell='document_search:holds'] [data-num]", { hasText: /^70$/ });
  await unread.focus();
  // Ticket 58: a check of what I found says where I found none, and names the pages as a reader would.
  await expect(page.getByRole("tooltip").locator("[data-num-what]")).toHaveText(
    "I found no paragraph numbers on 70 of 264 pages of the reports' main text.",
  );
  await page.keyboard.press("Escape");

  await shortfall.click();
  const window = page.getByRole("dialog", { name: "Linked" });
  await expect(window).toContainText("Missing75");
  await expect(window).toContainText("Counted528");
  await page.keyboard.press("Escape");

  // A fix's project count opens only a window named for the measure that counted it (design r5 P1),
  // whose Counted is that count and which names its table, or none at all.
  const answer = await json("data-readiness.json");
  const inWords = ["one", "two", "three", "four", "five", "six", "seven", "eight", "nine"];
  const titles: Record<string, string> = {
    projects_with_contracts_lacking_step_reference: "Projects with contracts that lack a STEP reference",
    gap_years_projects_in_local_currency: "Projects with award-notice contracts in local currency",
  };
  for (const [index, fix] of answer.fixes.entries()) {
    const projects = page.locator("[data-fixes] li").nth(index).locator("p.text-small [data-num]");
    if (fix.projects_row === null) {
      await expect(projects).not.toHaveAttribute("aria-haspopup", "dialog");
      await page.evaluate(() => (document.activeElement as HTMLElement | null)?.blur());
      await projects.hover();
      const said = `${inWords[fix.projects - 1]} ${fix.projects === 1 ? "project" : "projects"}`;
      await expect(page.getByRole("tooltip").locator("[data-num-what]")).toHaveText(`The records behind this gap come from ${said}.`);
      // It opens nothing, so its tooltip promises nothing (ticket 59).
      await expect(page.getByRole("tooltip").locator("[data-num-act]")).toHaveCount(0);
    } else {
      const counted = answer.rows[fix.projects_row];
      await page.evaluate(() => (document.activeElement as HTMLElement | null)?.blur());
      await projects.hover();
      await expect(page.getByRole("tooltip").locator("[data-num-what]")).toHaveText(`${counted.count} of ${counted.denominator} projects.`);
      await projects.click();
      const opened = page.getByRole("dialog", { name: titles[counted.measure] });
      await expect(opened).toContainText(`Counted${fix.projects}`);
      await expect(opened).toContainText("Counted instrata.gold.contract");
      await expect(opened).not.toContainText("Fixes that would unlock the most");
      await page.keyboard.press("Escape");
      // Escape gives focus back to the number a frame later; wait for it, so the next number's hover is not raced by
      // this one's tooltip opening on that focus (a flake under the gate's load, seen in ticket 98's gates).
      await expect(opened).toHaveCount(0);
      await expect(projects).toBeFocused();
    }
    await page.keyboard.press("Escape");
  }
});

test("opened from the plan check, it shows only the rows the plan check reads, and every count is of those rows", async ({ page }) => {
  await mockData(page, { file: "data-readiness-plan-check.json" });
  await open(page, "/data?sources=documents,projects&from=check_plan");

  await expect(page.getByRole("main").locator("[data-alert=info]").first()).toContainText(
    "I'm showing only the two sources behind the plan check.",
  );
  await expect(page.locator("[data-headline]")).toContainText("Two sources are behind the plan check.");
  await expect(page.locator("[data-headline]")).not.toContainText("body pages");
  await expect(table(page, "sources").locator("tbody tr")).toHaveCount(2);
  const total = await sourceRows("data-readiness-plan-check.json");
  expect(total).toBeGreaterThanOrEqual(14);
  await expect(countLine(page, "sources")).toHaveText(`Showing 2 of ${total} sources.`);
  // The headline names no STEP gap here, so the first STEP, in What you can ask, is spelled out.
  await expect(table(page, "kinds").locator("[data-cell='plan_check:readyFor']")).toContainText(
    "rows in the format of Systematic Tracking of Exchanges in Procurement (STEP)",
  );
});

// Design r5 B1: the first-listing check fills no column, so its window names the check itself and
// never borrows Coverage's title and definition.
test("the plan check's first-listing number opens a window named for that check, not for Coverage", async ({ page }) => {
  await mockData(page, { file: "data-readiness-plan-check.json" });
  await open(page, "/data?sources=documents,projects&from=check_plan");

  const number = page.locator("[data-headline] [data-num]", { hasText: /^258$/ });
  await number.focus();
  await number.press("Enter");
  const window = page.getByRole("dialog", { name: "First listing confirmed" });
  await expect(window).toContainText("trace back to the plan version that first listed them");
  await expect(window).toContainText("Missing258");
  await expect(window).not.toContainText("Coverage");
  await expect(window).not.toContainText("fiscal years");
});

// Review r7 B1: the document search's Ready for number counts passages, which fill no column, so
// its window names them and the table they were counted in, not Coverage and its fiscal years.
test("the document search's Ready for number opens a window named for the passages you can search, with their table", async ({ page }) => {
  await mockData(page, FULL);
  await open(page);

  await table(page, "kinds").locator("[data-cell='document_search:readyFor'] [data-num]").click();
  const window = page.getByRole("dialog", { name: "Passages you can search" });
  // Ticket 58 (the 16 review, round 8, P1): what the count is, and when a replaced version is found.
  await expect(window).toContainText(
    "How many of the passages I read are in the search index. I count them out of every passage I read. A search finds an older version of a report only as of a date before the newer one came out.",
  );
  await expect(window).not.toContainText("fiscal years");
  await expect(window.locator(".font-mono")).toHaveText("strata.gold.passage");
});

// Ticket 58 (the 16 design review, round 8, P1): STEP's "Activity Reference No." ends with a period, so a shortfall's
// tooltip that names it ends with one period, not two.
test("a shortfall whose records lack a field name ending in a period ends its tooltip once", async ({ page }) => {
  const answer = JSON.parse(await recorded("data-readiness.json"));
  const lack = "an Activity Reference\u00a0No.";
  for (const segment of answer.headline.segments) if (segment.role === "missing") segment.lack = lack;
  await mockData(page, FULL);
  await page.route("**/api/data/readiness*", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(answer) }));
  await open(page);

  await page.locator("[data-headline] [data-num]", { hasText: /^75$/ }).focus();
  const said = page.getByRole("tooltip").locator("[data-num-what]");
  await expect(said).toHaveText("75 of 603 contracts lack an Activity Reference No.");
  expect(await said.textContent()).not.toContain("..");
});

// The Read well measures the registry splits by route (read_well_by_route), whose window has its own definition.
const byRoute = new Set(
  Object.values(readRegistry<SourceRegistry>("sources.toml").sources).flatMap((source) =>
    (source.readiness ?? [])
      .filter((row) => (row as { read_well_by_route?: boolean }).read_well_by_route)
      .map((row) => (row as { read_well?: { measure: string } }).read_well?.measure ?? ""),
  ),
);

// Review r7: three rounds each found a number whose window named another measure. This opens every
// number's window on each view and checks it against the registries, not the page's own choice: a
// measure a column of its row shows opens that column's window, any other opens its own words, and
// every window names the table the registry says the measure was counted in.
const SWEPT: [string, string, Answer][] = [
  ["the full page", "/data", FULL],
  ["the plan check's view", "/data?sources=documents,projects&from=check_plan", { file: "data-readiness-plan-check.json" }],
  ["the past range's view", "/data?sources=awards,notices&from=find_comparables", { file: "data-readiness-filtered.json" }],
];
for (const [name, path, answer] of SWEPT) {
  test(`on ${name}, every number's window is named for the measure it counted, with its definition and its table`, async ({ page }) => {
    const { copy } = await import("../src/copy.ts");
    const words = copy.dataReadiness;
    const { placed } = placements();
    await mockData(page, answer);
    await open(page, path);
    await openRows(page);

    // The cards below 768 px repeat the table's numbers and are hidden at this width.
    const numbers = page.locator("main button[data-num][aria-haspopup=dialog]").filter({ visible: true });
    const count = await numbers.count();
    expect(count).toBeGreaterThan(10);
    for (let index = 0; index < count; index += 1) {
      const number = numbers.nth(index);
      const key = `${await number.getAttribute("data-measure-source")}/${await number.getAttribute("data-measure")}`;
      // The hardest documents' numbers come from the shelf's outcomes, not a registry; web/tests/shelf.spec.ts
      // checks their windows.
      if (key.startsWith("documents/stress_shelf_")) continue;
      const placement = placed.get(key);
      expect(placement, `number ${index} counts ${key}, which no registry places`).toBeTruthy();
      const measure = key.slice(key.indexOf("/") + 1);
      // A document collection's Read well counts pages across both routes, so its window says what counts on each
      // (ticket 58): the registry marks that row read_well_by_route.
      const want = byRoute.has(measure) && placement?.column === "read_well"
        ? { title: words.sources.columns.read_well.label, definition: words.sources.readWellDocuments }
        : placement?.column
          ? { title: words.sources.columns[placement.column].label, definition: words.sources.definitions[placement.column] }
          : words.measureWindows[measure];
      expect(want, `number ${index} counts ${key}, which fills no column and has no window words`).toBeTruthy();
      await number.click();
      const window = page.getByRole("dialog");
      await expect(window.getByRole("heading"), `number ${index}, ${key}`).toHaveText(want!.title);
      await expect(window, `number ${index}, ${key}`).toContainText(want!.definition);
      await expect(window.locator(".font-mono"), `number ${index}, ${key}`).toHaveText(placement?.table ?? "");
      await page.keyboard.press("Escape");
      await expect(window).toBeHidden();
    }
  });
}

// Design r6 P4: the table name is what a reader copies or searches for, so at 320 px it breaks
// only after a dot ("strata.silver." then "plan_listings"), never inside a word.
test("at 320 px a window's table name breaks only after a dot", async ({ page }) => {
  await mockData(page, { file: "data-readiness-plan-check.json" });
  await open(page, "/data?sources=documents,projects&from=check_plan", 320);

  await page.locator("[data-headline] [data-num]", { hasText: /^258$/ }).click();
  const name = page.getByRole("dialog", { name: "First listing confirmed" }).locator(".font-mono");
  await expect(name).toHaveText("strata.silver.plan_listings");
  // The last character of every line but the last, from the top of each character's box.
  const lineEnds = await name.evaluate((element) => {
    const boxes: { char: string; top: number }[] = [];
    const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT);
    for (let node = walker.nextNode(); node; node = walker.nextNode()) {
      const text = node.textContent ?? "";
      for (let i = 0; i < text.length; i++) {
        const range = document.createRange();
        range.setStart(node, i);
        range.setEnd(node, i + 1);
        boxes.push({ char: text[i], top: Math.round(range.getBoundingClientRect().top) });
      }
    }
    return boxes.filter((box, i) => i + 1 < boxes.length && boxes[i + 1].top > box.top).map((box) => box.char);
  });
  expect(lineEnds.length, "the name is wider than the window's cell at 320 px").toBeGreaterThan(0);
  expect(lineEnds).toEqual(lineEnds.map(() => "."));
});

test("What you can ask shows each kind of question with what it is ready for and what holds it back", async ({ page }) => {
  await mockData(page, FULL);
  await open(page);

  const kinds = table(page, "kinds");
  await expect(kinds.locator("tbody th")).toHaveText([
    "Checking a plan against its own dates",
    "What project documents say",
    "Lessons from completion reports",
    "How long comparable packages took",
  ]);
  await expect(kinds.locator("[data-cell='plan_check:holds']")).toContainText(
    "None of the 258 activity entries in the latest plan versions has a first listing I could confirm.",
  );
  await expect(kinds.locator("[data-cell='plan_check:readyFor'] [data-badge=partial]")).toHaveText("Partial");
  // The headline above already spells STEP out, so the count words it as the Procurement Plans row does.
  await expect(kinds.locator("[data-cell='plan_check:readyFor']")).toContainText(
    "activity entries in the latest plan versions with rows in STEP's format",
  );
  await expect(kinds.locator("[data-cell='plan_check:readyFor']")).not.toContainText("Systematic Tracking");
});

test("the fixes end the page, ranked by the projects each would add evidence to", async ({ page }) => {
  const answer = await json("data-readiness.json");
  await mockData(page, FULL);
  await open(page);

  const zones = page.locator("[data-readiness] [data-zone]");
  await expect(zones.last()).toHaveAttribute("data-fixes", "");
  await expect(page.locator("[data-fixes] [data-section-summary]")).toHaveText("I rank each fix by how many projects it would add evidence to.");
  await openRows(page);
  const fixes = page.locator("[data-fixes] li");
  await expect(fixes).toHaveCount(answer.fixes.length);
  await expect(fixes.first()).toContainText("Would add evidence to three projects.");
});

// Design r4 P4: a source can fall short with no fix in the registry, so the card never says that
// nothing needs one; it says nothing falls short only when no gap is in view.
test("with no fix to rank, the fixes card says nothing falls short only when nothing does", async ({ page }) => {
  const answer = await json("data-readiness-filtered.json");
  await mockShell(page);
  let body = { ...answer, fixes: [] };
  await page.route("**/api/data/readiness*", (route) => route.fulfill({ contentType: "application/json", body: JSON.stringify(body) }));
  await open(page, "/data?sources=awards,notices&from=find_comparables");
  expect(answer.gaps.length).toBeGreaterThan(0);
  await expect(page.locator("[data-fixes] [data-section-summary]")).toHaveText("I don't have a fix to suggest for these sources.");

  // Design r5 P3: with one source in view, as the alert and the headline say, the card says "this source".
  body = { ...answer, fixes: [], filter: { ...answer.filter, shown: 1 } };
  await page.reload();
  await expect(page.locator("[data-fixes] [data-section-summary]")).toHaveText("I don't have a fix to suggest for this source.");

  body = { ...answer, fixes: [], gaps: [] };
  await page.reload();
  await expect(page.locator("[data-fixes] [data-section-summary]")).toHaveText("Nothing I measured falls short, so there are no fixes to rank.");
});

test("opened from a coverage line, it shows only the sources behind it; Show all sources restores the table and Back returns", async ({ page }) => {
  await mockData(page, byQuery);
  await open(page, "/data?sources=awards,notices&from=find_comparables");

  await expect(page.getByRole("main").locator("[data-alert=info]").first()).toContainText(
    "I'm showing only the two sources behind the past range.",
  );
  await expect(page.locator("[data-headline]")).toContainText("Two sources are behind the past range.");
  // The awards' fiscal 2017 to 2019 gap ended before the past range's period, so its row is left out (ticket 63).
  const rows = table(page, "sources").locator("tbody tr");
  await expect(rows).toHaveCount(2);
  const total = await sourceRows("data-readiness-filtered.json");
  expect(total).toBeGreaterThanOrEqual(14);
  await expect(countLine(page, "sources")).toHaveText(`Showing 2 of ${total} sources.`);

  await page.getByRole("link", { name: "Show all sources" }).click();
  await expect(page).toHaveURL(/\/data$/);
  await expect(page.locator("[data-readiness=ready]")).toBeVisible();
  await expect(page.locator("main [data-lead]")).toBeFocused();
  await expect(rows).toHaveCount((await json("data-readiness.json")).sources.length);
  await page.goBack();
  await expect(rows).toHaveCount(2);
});

test("a coverage line's link, built by dataReadinessHref, opens the page filtered to the sources behind it", async ({ page }) => {
  const href = dataReadinessHref(["awards", "notices"], "find_comparables");
  expect(href).toBe("/data?sources=awards,notices&from=find_comparables");
  await mockData(page, byQuery);
  await open(page, href);

  await expect(page.locator("[data-readiness=filtered]")).toBeVisible();
});

test("a link's own words never reach the page, and keys the registry lacks are only counted", async ({ page }) => {
  await mockData(page, byQuery);
  await open(page, "/data?sources=awards,not-a-source&from=find_comparables");

  await expect(page.getByRole("main").locator("[data-alert=info]").first()).toContainText(
    "I'm showing only the source behind the past range. I didn't recognize one of the sources in this link.",
  );
  expect(await page.locator("main").textContent()).not.toContain("not-a-source");

  await open(page, "/data?sources=not-a-source");
  await expect(page.locator("[data-readiness=no-known-source]")).toContainText(
    "I couldn't find the sources this link names. They may have been renamed since the link was made.",
  );
  await expect(page.locator("[data-readiness-table]")).toHaveCount(0);
});

test("while the measures load, skeletons hold each table's rows, and after three seconds one line says why", async ({ page }) => {
  await mockShell(page);
  await page.route("**/api/data/sources", async (route) =>
    route.fulfill({ contentType: "application/json", body: await recorded("data-sources.json") }),
  );
  let release: () => void = () => {};
  const held = new Promise<void>((done) => (release = done));
  await page.route("**/api/data/readiness*", async (route) => {
    await held;
    await route.fulfill({ contentType: "application/json", body: await recorded("data-readiness.json") });
  });
  await page.clock.install();
  await open(page);

  const loading = page.locator("[data-readiness=loading]");
  await expect(loading).toHaveAttribute("aria-busy", "true");
  const registry = await json("data-sources.json");
  await expect(table(page, "sources").locator("tbody tr")).toHaveCount(registry.readiness_rows + registry.known_gaps);
  // The page's own status line, in main: the band holds the box's status line too (ticket 14).
  await expect(page.getByRole("main").getByRole("status")).toHaveText("");
  await page.clock.runFor(3100);
  await expect(page.getByRole("main").getByRole("status")).toHaveText(
    "I'm still loading the measures. The database may be starting up, which can take up to a minute.",
  );
  release();
  await expect(page.locator("[data-readiness=ready]")).toBeVisible();
});

for (const width of [1440, 1024, 390]) {
  test(`in a ${width} px page area the section titles land within 16 px of where the skeleton put them`, async ({ page }) => {
    await mockShell(page);
    await page.route("**/api/data/sources", async (route) => route.fulfill({ contentType: "application/json", body: await recorded("data-sources.json") }));
    let release: () => void = () => {};
    const held = new Promise<void>((done) => (release = done));
    await page.route("**/api/data/readiness*", async (route) => {
      await held;
      await route.fulfill({ contentType: "application/json", body: await recorded("data-readiness.json") });
    });
    await page.setViewportSize({ width: windowBeside(width), height: 900 });
    await page.goto("/data");
    await expect(table(page, "sources").or(page.locator("[data-readiness-table=sources] [data-table-view=cards]")).locator("[aria-hidden=true]").first()).toBeAttached();
    const titles = () =>
      page.locator("[data-readiness] h2").evaluateAll((found) => found.map((h) => [h.textContent, Math.round(h.getBoundingClientRect().top + window.scrollY)]));
    await expect.poll(async () => (await titles()).length).toBeGreaterThanOrEqual(3);
    // Until a face arrives, the fallback face can wrap a line more at 390 px (ticket 94's 16 px margins), so both
    // measures wait for every face. On a busy computer the skeleton's own faces came after its measure (ticket 56).
    await fontsLoaded(page);
    const before = Object.fromEntries(await titles());
    release();
    await expect(page.locator("[data-readiness=ready]")).toBeVisible();
    await fontsLoaded(page);
    const after = Object.fromEntries(await titles());
    expect(Object.keys(after)).toEqual(Object.keys(before));
    for (const title of Object.keys(after)) {
      expect(Math.abs(after[title] - before[title]), `${title} at ${width} px`).toBeLessThanOrEqual(16);
    }
  });
}

test("with no measures yet, the page shows DESIGN.md's empty-state card, which points to Sources and licenses", async ({ page }) => {
  await mockData(page, { file: "data-readiness-empty.json" });
  await open(page);

  const card = page.locator("[data-readiness=empty] [data-empty-state]");
  await expect(card.getByRole("heading")).toHaveText("I haven't measured any sources yet.");
  await expect(card).toContainText("The measures appear here after the first data run.");
  await expect(card.getByRole("link", { name: "See the datasets I'm set up to read" })).toHaveAttribute("href", "/data/sources");
  await expect(page.locator("[data-readiness-table]")).toHaveCount(0);
});

test("a source with no measures leaves the headline out, and its row says it is not measured yet", async ({ page }) => {
  await mockData(page, { file: "data-readiness-unmeasured.json" });
  await open(page);

  const total = await sourceRows("data-readiness-unmeasured.json");
  expect(total).toBeGreaterThanOrEqual(14);
  await expect(page.locator("[data-headline]")).toHaveText(
    // One to nine in words, as in any sentence (DESIGN.md section 7, rule 12; design r5 P4).
    // No colon joins the two sentences (ticket 58; DESIGN.md section 7, rule 16).
    `I'm not giving a headline. One of the ${total} sources below has no measures yet. Its row says so.`,
  );
  // With no headline, the caption says when the measures were taken, with no "this" to point at nothing.
  await expect(page.locator("[data-lead] [data-headline] + p")).toHaveText("I took the measures below on October 23, 2026.");
  await expect(cell(page, "wgi:span")).toHaveText("Not measured yet. The next data run measures it.");

  // Review r6 P2: a filtered view abstains out of the sources in view, so the total is small too,
  // and is written in words, as is a view in which no source, or the only one, has measures.
  const answer = await json("data-readiness-unmeasured.json");
  const abstaining = (unmeasured: number, sources: number) => ({
    ...answer,
    filter: { ...answer.filter, shown: sources },
    headline_abstention: { reason: "unmeasured", unmeasured, sources },
  });
  let body = abstaining(1, 2);
  await page.route("**/api/data/readiness*", (route) => route.fulfill({ contentType: "application/json", body: JSON.stringify(body) }));
  await page.reload();
  await expect(page.locator("[data-headline]")).toHaveText(
    "I'm not giving a headline. One of the two sources below has no measures yet. Its row says so.",
  );
  body = abstaining(2, 2);
  await page.reload();
  await expect(page.locator("[data-headline]")).toHaveText("I'm not giving a headline, because none of the sources below has measures yet. Their rows say so.");
  body = abstaining(1, 1);
  await page.reload();
  await expect(page.locator("[data-headline]")).toHaveText("I'm not giving a headline, because the source below has no measures yet. Its row says so.");
});

test("a date before the first measure says when the measures start and links to today's", async ({ page }) => {
  await mockData(page, byQuery);
  await open(page, "/data?asof=2026-10-01");

  await expect(page.locator("[data-readiness=before-first]")).toContainText(
    "I have no measures taken on or before October 1, 2026. I took my first measures on October 23, 2026.",
  );
  await expect(page.getByRole("link", { name: "Show today's measures" })).toHaveAttribute("href", "/data");
  // The page applies the date itself, so the frame does not say it shows today's data.
  await expect(page.getByText("so you are seeing today's data")).toHaveCount(0);
});

for (const [name, file, status, text, retry] of [
  ["a timeout", "data-readiness-timeout.json", 504, "I couldn't load the measures, because the database didn't answer within 30 seconds. Try again in a minute.", true],
  ["no access", "data-readiness-no-access.json", 403, "I couldn't load the measures, because your account doesn't have access to them. Ask the person who runs Strata to give your account access.", false],
  ["a server error", "data-readiness-error.json", 502, "I couldn't load the measures, because the server returned an error. Try again. If it fails again, tell the person who runs Strata.", true],
] as const) {
  test(`after ${name}, an error alert takes the headline's place and no table shows`, async ({ page }) => {
    await mockData(page, { file, status });
    await open(page);

    await expect(page.getByRole("main").getByRole("alert")).toHaveText(text + (retry ? "Try again" : ""));
    await expect(page.getByRole("button", { name: "Try again" })).toHaveCount(retry ? 1 : 0);
    await expect(page.locator("[data-readiness-table]")).toHaveCount(0);
  });
}

test("Try again moves focus to the busy lead at once, and it stays there when the headline arrives", async ({ page }) => {
  let calls = 0;
  let release: () => void = () => {};
  const held = new Promise<void>((done) => (release = done));
  await mockShell(page);
  await page.route("**/api/data/sources", async (route) => route.fulfill({ contentType: "application/json", body: await recorded("data-sources.json") }));
  await page.route("**/api/data/readiness*", async (route) => {
    if (++calls === 1) return route.fulfill({ status: 502, contentType: "application/json", body: await recorded("data-readiness-error.json") });
    await held;
    await route.fulfill({ contentType: "application/json", body: await recorded("data-readiness.json") });
  });
  await open(page);

  await page.getByRole("button", { name: "Try again" }).press("Enter");
  await expect(page.locator("[data-readiness=loading]")).toBeVisible();
  await expect(page.locator("main [data-lead]")).toBeFocused();
  await expect(page.locator("main [data-lead]")).toHaveAttribute("aria-busy", "true");
  release();
  await expect(page.locator("[data-readiness=ready]")).toBeVisible();
  await expect(page.locator("main [data-lead]")).toBeFocused();
});

test("below 768 px each table becomes cards, each with the source's name as a heading and its measures as terms", async ({ page }) => {
  await mockData(page, FULL);
  await open(page, "/data", 390);

  await expect(table(page, "sources")).toBeHidden();
  const cards = page.locator("[data-readiness-table=sources] [data-table-view=cards] > li");
  await expect(cards.first().getByRole("heading", { level: 3 })).toHaveText("Contract awards");
  await expect(cards.first().locator("dt").first()).toHaveText("Coveragerows and fiscal years");
  await expect(cards.first().locator("dd").nth(1)).toContainText("528 of 603, 88%");
  // Each column's short definition shows once over the cards, not in every card (DESIGN.md section 5, Tables; ticket
  // 104); a screen reader still hears it with each label.
  const note = page.locator("[data-readiness-table=sources] [data-cards-note]");
  await expect(note.locator("dt")).toHaveText(["Coverage", "Linked", "Read well", "Fresh"]);
  await expect(note.locator("dd").first()).toHaveText("rows and fiscal years");
  expect(await cards.first().getByText("rows and fiscal years").evaluate((about) => about.getBoundingClientRect().width)).toBeLessThanOrEqual(1);
  await page.setViewportSize({ width: 1440, height: 900 });
  await expect(note).toBeHidden();
  await page.setViewportSize({ width: 390, height: 900 });
  // Each label opens its full definition on a phone too.
  await cards.first().locator("dt").nth(1).getByRole("button", { name: "Linked" }).click();
  await expect(page.getByRole("dialog", { name: "Linked" })).toContainText("a sector or a borrower country");
  await page.keyboard.press("Escape");
  // A kind's card has one number, so its Ready for runs the card's full width.
  const kind = page.locator("[data-readiness-table=kinds] [data-table-view=cards] > li").first();
  const [card, value] = await Promise.all([kind.locator("dl").boundingBox(), kind.locator("dl > div").first().boundingBox()]);
  expect(Math.round(value!.width)).toBe(Math.round(card!.width));
  await page.setViewportSize({ width: 320, height: 900 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(320);
});

// ── Laid out by the page area (ticket 104) ───────────────────────────────

// DESIGN.md section 4, Breakpoints: under the bar a page lays out by the page area (@md/page: and the rest), because the
// evidence drawer narrows it. A window variant (md:, xl:) in these files would lay a table out for a window the page
// does not have.
test("Data readiness and its tables use no window breakpoint, only the page area's", async () => {
  const files = ["../src/pages/data/DataReadiness.tsx", "../src/components/ReadinessTable.tsx", "../src/pages/data/HardestDocuments.tsx"];
  for (const file of files) {
    const text = await readFile(new URL(file, import.meta.url), "utf8");
    const found = text.match(/(?<=^|[\s"'`{(])(?:max-)?(?:sm|md|lg|xl|2xl):[\w[-]/gm) ?? [];
    expect(found, file).toEqual([]);
  }
});

// What each Data readiness table shows: its table or its cards, and how many columns a card's measures take.
const tableLayout = (page: Page) =>
  page.locator("[data-readiness-table]").evaluateAll((tables) =>
    tables.map((table) => {
      const shown = Array.from(table.querySelectorAll<HTMLElement>("[data-table-view]")).filter((view) => getComputedStyle(view).display !== "none");
      const card = table.querySelector("[data-table-view=cards] > li dl");
      return {
        id: table.getAttribute("data-readiness-table"),
        views: shown.map((view) => view.dataset.tableView),
        cardColumns: card ? getComputedStyle(card).gridTemplateColumns.split(" ").length : 0,
      };
    }),
  );

// At 1024 px the rail takes 64 px and the drawer 410 px, which leaves a 550 px page area (ticket 94): the tables read
// it as cards, as they would in a 550 px window, and nothing scrolls sideways.
test("beside the evidence drawer at 1024 px, the tables are laid out as in a 550 px page area", async ({ page }) => {
  const ICR_54 = "strata.gold.passage:31525018/v1/54";
  await mockData(page, FULL);
  await page.route("**/api/evidence*", async (route) =>
    route.fulfill({ contentType: "application/json", body: await recorded("evidence-icr-p130164-54.json") }),
  );
  await page.route("**/api/evidence/opened*", (route) => route.fulfill({ contentType: "application/json", body: '{"opened":[],"recorded":true}' }));
  await open(page, "/data", 550);
  await openRows(page);
  const narrow = await tableLayout(page);
  expect(narrow.map((table) => table.id)).toEqual(["kinds", "sources", "shelf"]);
  expect(narrow.map((table) => table.views)).toEqual(narrow.map(() => ["cards"]));

  await open(page, `/data?evidence=${encodeURIComponent(ICR_54)}`, 1024);
  await openRows(page);
  await expect(page.locator("[data-evidence-drawer]")).toBeVisible();
  expect(Math.round((await page.locator("[data-page-column]").boundingBox())!.width)).toBe(550);
  expect(await tableLayout(page)).toEqual(narrow);
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(1024);
});

// ── Sources and licenses ─────────────────────────────────────────────────

test("Sources and licenses credits every dataset in the World Bank's format, with DESIGN.md section 8's sentences word for word", async ({ page }) => {
  const sources = await json("data-sources.json");
  const design = await readFile(new URL("../../DESIGN.md", import.meta.url), "utf8");
  const fixed = (start: string) => new RegExp(`"(${start}[^"]*)"`).exec(design)![1];
  await mockData(page, FULL);
  await open(page, "/data/sources");

  const lines = page.locator("[data-dataset]");
  await expect(lines).toHaveText(
    sources.datasets.map(
      (dataset: { dataset_name: string; data_source: string }) =>
        `The World Bank: ${dataset.dataset_name}: ${dataset.data_source}. License: CC BY 4.0.`,
    ),
  );
  await expect(lines.first().getByRole("link")).toHaveAttribute("href", sources.datasets[0].catalog_url);
  await expect(page.locator("[data-terms]")).toHaveText(fixed("Terms of use: "));
  await expect(page.locator("[data-terms] a")).toHaveAttribute("href", "https://www.worldbank.org/ext/en/legal/terms-conditions/datasets");
  await expect(page.locator("[data-changes]")).toHaveText(fixed("Strata joined these records"));
  await expect(page.locator("[data-caveat]")).toHaveText(fixed("The World Bank does not guarantee"));
  await expect(page.getByText(fixed("The World Bank Group authorizes the use of this material"))).toBeVisible();
});

test("Sources and licenses works while the warehouse is down, because it reads only the registry", async ({ page }) => {
  await mockData(page, { file: "data-readiness-error.json", status: 502 });
  await open(page, "/data/sources");

  await expect(page.locator("[data-dataset]")).toHaveCount((await json("data-sources.json")).datasets.length);
});

// ── Accessibility in every state ─────────────────────────────────────────

const STATES: [string, string, Answer | ((query: URLSearchParams) => Answer)][] = [
  ["populated", "/data", FULL],
  ["filtered", "/data?sources=awards,notices&from=find_comparables", byQuery],
  ["filtered from the plan check", "/data?sources=documents,projects&from=check_plan", { file: "data-readiness-plan-check.json" }],
  ["filtered with an unknown key", "/data?sources=awards,not-a-source&from=find_comparables", byQuery],
  ["empty", "/data", { file: "data-readiness-empty.json" }],
  ["abstention", "/data", { file: "data-readiness-unmeasured.json" }],
  ["before the first measure", "/data?asof=2026-10-01", byQuery],
  ["error", "/data", { file: "data-readiness-error.json", status: 502 }],
  ["sources and licenses", "/data/sources", FULL],
];

for (const [name, path, answer] of STATES) {
  test(`${name}: axe finds no WCAG 2.2 AA violations at 1440, 1024 and 390 px, and it reflows at 320 px`, async ({ page }) => {
    await mockData(page, answer);
    for (const width of [1440, 1024, 390]) {
      await open(page, path, width);
      await page.waitForFunction(() => !document.querySelector("[data-readiness=loading], [data-sources-page=loading]"));
      expect(await violations(page), `${width} px`).toEqual([]);
    }
    await page.setViewportSize({ width: 320, height: 900 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(320);
  });
}
