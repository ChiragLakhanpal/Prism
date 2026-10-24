// The Data tab at seam 4 (ticket 16; the 16 design brief): Data readiness, Sources and licenses and
// How Strata works, against the mocked API. The answers are the server's own on the fixture,
// recorded in tests/fixtures/api by tests/record_api.py, so every number the page shows is checked
// against the measure the server returned. Fixed words come from the brief and DESIGN.md section 8,
// copied here so the test checks the copy file against an independent source.
import AxeBuilder from "@axe-core/playwright";
import type { Page, Route } from "@playwright/test";
import { readFile } from "node:fs/promises";
import { expect, mockShell, recorded, test } from "./mocked";

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

const WCAG_22_AA = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];
async function violations(page: Page) {
  const results = await new AxeBuilder({ page }).withTags(WCAG_22_AA).analyze();
  return results.violations.map((v) => `${v.id}: ${v.nodes.map((node) => node.target.join(" ")).join(", ")}`);
}

// ── Data readiness ───────────────────────────────────────────────────────

test("the Data tab has one header, and its three sub-tabs are links in a nav that change the address", async ({ page }) => {
  await mockData(page, FULL);
  await open(page);

  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Data");
  await expect(page.locator("main h1 + p")).toHaveText(
    "How fit each source is to support answers, where each dataset comes from, and how I read them.",
  );
  await expect(page).toHaveTitle("Data readiness | Strata");
  const tabs = page.getByRole("navigation", { name: "Data pages" }).getByRole("link");
  await expect(tabs).toHaveText(["Data readiness", "Sources and licenses", "How Strata works"]);
  await expect(tabs.first()).toHaveAttribute("aria-current", "page");
  expect(await tabs.evaluateAll((links) => links.map((link) => Math.round(link.getBoundingClientRect().height)))).toEqual([44, 44, 44]);

  await tabs.nth(1).click();
  await expect(page).toHaveURL(/\/data\/sources$/);
  await expect(page).toHaveTitle("Sources and licenses | Strata");
  await expect(page.locator("main [data-lead]")).toBeFocused();
  await tabs.nth(2).click();
  await expect(page).toHaveTitle("How Strata works | Strata");
  await expect(page.locator("main [data-lead]")).toBeFocused();
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
      expect(shown, `${row.id} ${column}`).toContain(column === "coverage" ? count : `${count} of ${measure.denominator.toLocaleString("en-US")}`);
    }
  }
});

test("the headline is the server's sentence, and its caption says the measures' date and that no model wrote it", async ({ page }) => {
  const answer = await json("data-readiness.json");
  await mockData(page, FULL);
  await open(page);

  await expect(page.locator("[data-headline]")).toHaveText(answer.headline.text);
  await expect(page.locator("[data-lead] [data-headline] + p")).toHaveText(
    "I built this from the measures below, taken October 23, 2026. No model wrote it.",
  );
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
  await expect(cell(page, "plans:fresh")).toHaveText("Not measured yet");
  // CPIA and WGI scores are a source's own values; no score of Strata's rates a source.
  expect(await page.locator("main").textContent()).not.toMatch(/composite|\bscore\b|overall/i);
});

test("each column head holds its definition, and its label opens the full definition", async ({ page }) => {
  await mockData(page, FULL);
  await open(page);

  const heads = table(page, "sources").locator("thead th");
  await expect(heads).toHaveText([
    "Sourcewhere",
    "Coveragerows and fiscal years",
    "Linkedto projects and notices",
    "Read wellread without errors",
    "Freshlatest data, how often",
  ].map((text) => text.replace("Sourcewhere", "Source")));
  await heads.nth(2).getByRole("button", { name: "Linked" }).click();
  const definition = page.getByRole("dialog", { name: "Linked" });
  await expect(definition).toContainText(
    "How many of these rows I could join to a project, a notice or a Procurement Plan. A row that doesn't join can't count in answers that need the join.",
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
  await expect(page.getByRole("tooltip")).toHaveText("528 of 603 contracts. Measured Oct 23, 2026.");
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

test("What you can ask shows each kind of question with what it is ready for and what holds it back", async ({ page }) => {
  await mockData(page, FULL);
  await open(page);

  const kinds = table(page, "kinds");
  await expect(kinds.locator("tbody th")).toHaveText(["Checking a plan against its own dates", "What project documents say"]);
  await expect(kinds.locator("[data-cell='plan_check:holds']")).toContainText(
    "The 46 of 46 activity entries in the latest plan versions that lack a confirmed first listing I read.",
  );
  await expect(kinds.locator("[data-cell='plan_check:readyFor'] [data-badge=partial]")).toHaveText("Partial");
});

test("the fixes end the page, ranked by the projects each would add evidence to", async ({ page }) => {
  const answer = await json("data-readiness.json");
  await mockData(page, FULL);
  await open(page);

  const fixes = page.locator("[data-fixes] li");
  await expect(fixes).toHaveCount(answer.fixes.length);
  await expect(page.locator("[data-fixes] > p").first()).toHaveText("Ranked by how many projects each fix would add evidence to.");
  await expect(fixes.first()).toContainText("Would add evidence to two projects.");
});

test("opened from a coverage line, it shows only the sources behind it; Show all sources restores the table and Back returns", async ({ page }) => {
  await mockData(page, byQuery);
  await open(page, "/data?sources=awards,notices&from=find_comparables");

  await expect(page.getByRole("main").locator("[data-alert=info]").first()).toContainText(
    "I'm showing only the two sources behind the past range.",
  );
  await expect(page.locator("[data-headline]")).toContainText("Two sources are behind the past range.");
  const rows = table(page, "sources").locator("tbody tr");
  await expect(rows).toHaveCount(3);
  await expect(page.locator("[data-readiness-table=sources] > p").first()).toHaveText("Showing two of 13 sources.");

  await page.getByRole("link", { name: "Show all sources" }).click();
  await expect(page).toHaveURL(/\/data$/);
  await expect(page.locator("[data-readiness=ready]")).toBeVisible();
  await expect(page.locator("main [data-lead]")).toBeFocused();
  await expect(rows).toHaveCount((await json("data-readiness.json")).sources.length);
  await page.goBack();
  await expect(rows).toHaveCount(3);
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
  await expect(table(page, "sources").locator("tbody tr")).toHaveCount((await json("data-sources.json")).readiness_rows);
  await expect(page.getByRole("status")).toHaveText("");
  await page.clock.runFor(3100);
  await expect(page.getByRole("main").getByRole("status")).toHaveText(
    "I'm still loading the measures. The database may be starting up, which can take up to a minute.",
  );
  release();
  await expect(page.locator("[data-readiness=ready]")).toBeVisible();
});

test("with no measures yet, the page says so and points to Sources and licenses", async ({ page }) => {
  await mockData(page, { file: "data-readiness-empty.json" });
  await open(page);

  await expect(page.locator("[data-readiness=empty]")).toContainText(
    "I haven't measured any sources yet. The measures appear here after the first data run.",
  );
  await expect(page.getByRole("main").getByRole("link", { name: "Sources and licenses" }).last()).toHaveAttribute("href", "/data/sources");
  await expect(page.locator("[data-readiness-table]")).toHaveCount(0);
});

test("a source with no measures leaves the headline out, and its row says it is not measured yet", async ({ page }) => {
  await mockData(page, { file: "data-readiness-unmeasured.json" });
  await open(page);

  await expect(page.locator("[data-headline]")).toHaveText(
    "I'm not giving a headline: one of the 13 sources below have no measures yet. Their rows say so.",
  );
  await expect(cell(page, "wgi:span")).toHaveText("Not measured yet. The next data run measures it.");
});

test("a date before the first measure says when the measures start and links to today's", async ({ page }) => {
  await mockData(page, byQuery);
  await open(page, "/data?asof=2026-10-01");

  await expect(page.locator("[data-readiness=before-first]")).toContainText(
    "I have no measures from on or before October 1, 2026. My first measures were taken October 23, 2026.",
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

test("Try again keeps focus on the button while loading, then moves it to the headline", async ({ page }) => {
  let calls = 0;
  await mockData(page, () => (++calls === 1 ? { file: "data-readiness-error.json", status: 502 } : FULL));
  await open(page);

  await page.getByRole("button", { name: "Try again" }).click();
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
  await page.setViewportSize({ width: 320, height: 900 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(320);
});

// ── Sources and licenses, and How Strata works ──────────────────────────

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

test("How Strata works states its purpose and links to the other two pages, and nothing links to /present", async ({ page }) => {
  await mockData(page, FULL);
  await open(page, "/data/how-strata-works");

  await expect(page.locator("main [data-lead]")).toHaveText(
    "This page is for the figures that show how I turn World Bank records and documents into cited answers. They are not drawn yet.",
  );
  await expect(page.locator("main a[href='/present']")).toHaveCount(0);
});

// ── Accessibility in every state ─────────────────────────────────────────

const STATES: [string, string, Answer | ((query: URLSearchParams) => Answer)][] = [
  ["populated", "/data", FULL],
  ["filtered", "/data?sources=awards,notices&from=find_comparables", byQuery],
  ["filtered with an unknown key", "/data?sources=awards,not-a-source&from=find_comparables", byQuery],
  ["empty", "/data", { file: "data-readiness-empty.json" }],
  ["abstention", "/data", { file: "data-readiness-unmeasured.json" }],
  ["before the first measure", "/data?asof=2026-10-01", byQuery],
  ["error", "/data", { file: "data-readiness-error.json", status: 502 }],
  ["sources and licenses", "/data/sources", FULL],
  ["how strata works", "/data/how-strata-works", FULL],
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
