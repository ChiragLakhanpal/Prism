// The project page as the hub (ticket 21) at seam 4: the header and tabs, the Summary, the Documents tab,
// the source view and the evidence drawer's link to it, against the responses the server wrote on the
// fixture (tests/record_api.py), which tests/test_project_hub.py checks the server against. The values are
// the projects API's and documents API's records for P130164 and the ICR of October 10, 2019, as
// tests/ground_truth/values.toml quotes them (project-p130164-*, pad-date, icr-date, icr-review-date,
// icr-review-reissue-date, icr-para-54 and icr-pdf-pages), copied here so the screen is checked against an
// independent source.
import AxeBuilder from "@axe-core/playwright";
import type { Page, Request } from "@playwright/test";
import { copy } from "../src/copy";
import { askFromTheBox, landed, marker, panel } from "./answer-page";
import { hubApi } from "./hub-api";
import { expect, mockApi, recorded, test } from "./mocked";

const WCAG_22_AA = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];
type Answer = { status?: number; body: string };

async function open(page: Page, path: string, width = 1440, extra: Record<string, Answer> = {}) {
  await page.setViewportSize({ width, height: 900 });
  const unrecorded = await mockApi(page, { ...(await hubApi()), ...extra });
  await page.goto(path);
  await expect(page.locator("main h1")).toBeVisible();
  return unrecorded;
}

async function axe(page: Page) {
  const results = await new AxeBuilder({ page }).withTags(WCAG_22_AA).analyze();
  return results.violations.map((v) => `${v.id}: ${v.nodes.map((node) => node.target.join(" ")).join(", ")}`);
}

const main = (page: Page) => page.getByRole("main");
const tabs = (page: Page) => main(page).getByRole("navigation", { name: "Project sections" }).getByRole("link");

// ── The header and the tabs ─────────────────────────────────────────────

test("P130164's header reads as the wireframe's one line with its implementing agency, and the tabs run in the wireframe's order", async ({ page }) => {
  const unrecorded = await open(page, "/projects/P130164");
  await expect(page.locator("[data-summary=ready]")).toBeVisible();

  const h1 = main(page).getByRole("heading", { level: 1 });
  await expect(h1).toHaveText("Rajasthan Road Sector Modernization · P130164 · India · closed");
  // The P-code is a ProjectId link in Roboto Mono 500, marked as this page on Summary.
  const pid = h1.getByRole("link", { name: "P130164" });
  await expect(pid).toHaveAttribute("href", "/projects/P130164");
  await expect(pid).toHaveAttribute("aria-current", "page");
  expect(await pid.evaluate((el) => [getComputedStyle(el).fontFamily.split(",")[0], getComputedStyle(el).fontWeight])).toEqual(['"Roboto Mono"', "500"]);
  await expect(main(page).locator("[data-agency-line]")).toHaveText("Implementing agency: Rajasthan State Public Works Department");
  // Tables keep the projects API's own word; the header lowercases it from the copy file.
  expect(copy.projectPage.statusInline.Closed).toBe("closed");

  // The built tabs, in the copy file's order, which is the wireframe's: Summary, Procurement, Timeline,
  // Documents, Connections. Timeline and Connections join when their tickets land.
  expect(Object.keys(copy.projectPage.tab)).toEqual(["summary", "procurement", "timeline", "documents", "connections"]);
  await expect(tabs(page)).toHaveText(["Summary", "Procurement", "Documents"]);
  await expect(tabs(page).first()).toHaveAttribute("aria-current", "page");
  await expect(page).toHaveTitle("Rajasthan Road Sector Modernization (P130164), Summary | Strata");
  // The current crumb names the project as the h1 does, with its ID in plain mono: the h1's P-code just
  // below it is the one link to this page, so Tab reaches it once.
  const crumb = page.getByRole("navigation", { name: "Breadcrumb" }).locator("[aria-current=page]");
  await expect(crumb).toHaveText("Rajasthan Road Sector Modernization (P130164)");
  await expect(crumb.getByRole("link")).toHaveCount(0);
  expect(unrecorded).toEqual([]);
});

test("switching tabs keeps the header in place and focus on the tab, says which tab shows, and names it in the page title", async ({ page }) => {
  await open(page, "/projects/P130164");
  await expect(page.locator("[data-summary=ready]")).toBeVisible();
  const h1 = main(page).getByRole("heading", { level: 1 });
  await h1.evaluate((el) => el.setAttribute("data-same-element", ""));

  await tabs(page).nth(2).focus();
  await page.keyboard.press("Enter");

  await expect(page).toHaveURL(/\/projects\/P130164\/documents$/);
  await expect(tabs(page).nth(2)).toBeFocused();
  await expect(tabs(page).nth(2)).toHaveAttribute("aria-current", "page");
  await expect(page.getByRole("status").filter({ hasText: "Showing Documents." })).toHaveCount(1);
  // The header did not redraw: it is the same element, and the project was read once.
  await expect(main(page).locator("h1[data-same-element]")).toHaveCount(1);
  await expect(page).toHaveTitle("Rajasthan Road Sector Modernization (P130164), Documents | Strata");

  await page.goBack();
  await expect(page).toHaveURL(/\/projects\/P130164$/);
  await expect(page.locator("[data-summary=ready]")).toBeVisible();
  // /projects/:pid/summary is the same page, and its address is rewritten to the shorter one.
  await page.goto("/projects/P130164/summary");
  await expect(page).toHaveURL(/\/projects\/P130164$/);
});

test("a project page viewed as of a date, or in a preview, passes ?asof= and ?view= on to every read it makes", async ({ page }) => {
  // The 21 review, round 2, item 10: each read answers with only what was public by the page's date.
  const asked: URL[] = [];
  page.on("request", (request) => {
    const url = new URL(request.url());
    if (url.pathname.startsWith("/api/projects/")) asked.push(url);
  });
  const params = "asof=2024-01-01&view=piu";
  await open(page, `/projects/P156634?${params}`, 1440, await p156634());
  await expect(page.locator("[data-summary=ready]")).toBeVisible();
  await page.goto(`/projects/P156634/procurement?${params}`);
  await expect(page.locator("[data-packages=ready]")).toBeVisible();
  await page.goto(`/projects/P156634/documents?${params}`);
  await expect(page.locator("main h1")).toBeVisible();
  await page.goto(`${NWWDA}/2026-10-09?${params}`);
  await expect(page.locator("[data-check-plan-page=ready]")).toBeVisible();
  await expect.poll(() => asked.some((url) => url.pathname.endsWith("/changes"))).toBe(true);

  const paths = ["/api/projects/P156634", "/summary", "/packages", "/documents", "/2026-10-09", "/changes"];
  for (const end of paths) {
    const reads = asked.filter((url) => url.pathname.endsWith(end));
    expect(reads.length, end).toBeGreaterThan(0);
    for (const url of reads) expect([url.searchParams.get("asof"), url.searchParams.get("view")], url.pathname).toEqual(["2024-01-01", "piu"]);
  }
});

test("arriving at a project page from All projects focuses its h1, as any route change does", async ({ page }) => {
  await open(page, "/projects?q=india", 1440, { "/api/projects?q=india": { body: await recorded("projects-india.json") } });
  await main(page).locator("[data-table-view=table]").getByRole("link", { name: "P130164" }).click();
  await expect(page.locator("[data-summary=ready]")).toBeVisible();
  await expect(main(page).getByRole("heading", { level: 1 })).toBeFocused();
});

// ── The Summary ─────────────────────────────────────────────────────────

test("P130164's Summary renders from records with no request to a route that calls a model, and every value has a source line", async ({ page }) => {
  const requests: Request[] = [];
  page.on("request", (request) => requests.push(request));
  await open(page, "/projects/P130164");
  await expect(page.locator("[data-summary=ready]")).toBeVisible();

  // The routes the server tags as calling a model, recorded from the router (tests/test_project_hub.py
  // keeps the file in step with create_app's tags).
  const models: { method: string; path: string }[] = JSON.parse(await recorded("model-routes.json")).routes;
  expect(models.length).toBeGreaterThan(0);
  const called = requests.map((request) => ({ method: request.method(), path: new URL(request.url()).pathname }));
  expect(called.filter((request) => models.some((model) => model.method === request.method && model.path === request.path))).toEqual([]);
  // The Summary is one request.
  expect(called.filter((request) => request.path === "/api/projects/P130164/summary")).toHaveLength(1);

  const summary = page.locator("[data-summary=ready]");
  await expect(summary.locator("[data-summary-lead]")).toHaveText(
    "The project closed on December 31, 2018, its original closing date. The World Bank committed US$160.0 million to it. " +
      "Of that, US$121.6 million was disbursed and US$30.7 million was canceled.",
  );
  await expect(summary.locator("[data-made-by]")).toHaveText("I built this summary from World Bank records as of October 23, 2026. No model wrote it.");
  // Every value on the Summary has a source line, with a citation marker.
  const facts = summary.locator("[data-fact]");
  expect(await facts.count()).toBeGreaterThanOrEqual(12);
  for (const fact of await facts.all()) {
    await expect(fact.locator("[data-fact-source]")).not.toBeEmpty();
    await expect(fact.locator("[data-fact-source] [data-citation]")).toHaveCount(1);
  }
  await expect(summary.locator("[data-fact=approval_date]")).toContainText("Oct 29, 2013");
  await expect(summary.locator("[data-fact=closing_date]")).toContainText("Dec 31, 2018");
  await expect(summary.locator("[data-fact=closing_date] [data-fact-source]")).toHaveText(/^Projects API, Aug 1, 2023\u2060\[1\]$/);
  await expect(summary.locator("[data-closing-history=none]")).toContainText("The closing date did not change after approval.");
  // That sentence cites the monthly history it reads, as source 2.
  await expect(summary.locator("[data-closing-history=none] [data-source]")).toHaveText(/^Source: Loan history, Oct 2013\u2060\[2\]$/);
  // The lead's amounts are the Money table's cells, word for word.
  for (const [key, value] of [["commitment", "160.0"], ["disbursed", "121.6"], ["canceled", "30.7"]]) {
    await expect(summary.locator(`[data-fact=${key}] td`).first()).toHaveText(value);
  }
  await expect(summary.locator("[data-fact=ea_category]")).toContainText(
    "The project record has no risk rating under the Environmental and Social Framework (ESF), so I show its Environmental Assessment Category.",
  );
  await expect(summary.locator("[data-fact=sectors]")).toContainText("Rural and Inter-Urban Roads: 97%");
  // The ICR's own outcome rating sits before IEG's, cited to the ICR's paragraph 45, which its marker opens.
  const icr = summary.locator("[data-fact=icr_outcome]");
  await expect(icr.getByRole("rowheader")).toHaveText("Outcome, in the Implementation Completion and Results Report (ICR)");
  await expect(icr.getByRole("cell").first()).toHaveText("Moderately Unsatisfactory");
  await expect(icr.locator("[data-fact-source]")).toHaveText(/^ICR, Oct 10, 2019⁠\[\d\]$/);
  await expect(icr.locator("[data-citation]")).toHaveAccessibleName(/^Source \d: Implementation Completion and Results Report, October 10, 2019$/);
  const order = await summary.locator("[data-fact]").evaluateAll((rows) => rows.map((row) => row.getAttribute("data-fact")));
  expect(order.indexOf("icr_outcome")).toBe(order.indexOf("ieg_outcome") - 1);
  await icr.locator("[data-citation]").click();
  await expect(page.getByRole("dialog")).toContainText("the overall outcome is rated Moderately Unsatisfactory");
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
  // A source cited again keeps its number, like a footnote: every projects API fact is source 1.
  await expect(summary.locator("[data-fact=region] [data-citation]")).toHaveText("[1]");
  await expect(summary.locator("[data-fact=closing_date] [data-citation]")).toHaveAccessibleName("Source 1: World Bank projects API, record of August 1, 2023");

  // A marker on a record opens the drawer's record view at once, from the summary's own sources.
  await summary.locator("[data-fact=commitment] [data-citation]").click();
  const drawer = page.getByRole("dialog");
  await expect(drawer.getByRole("heading", { level: 2 })).toHaveText("Loan or credit IDA53100");
  await expect(drawer.locator("[data-record]")).toContainText("Original principal (US$)160,000,000.00");
  await expect(drawer).toContainText("Source: World Bank loans and credits data, as of September 30, 2026.");
});

test("P156634's Summary gives every value a marker and lists its agencies and sectors one per line, 4 px apart", async ({ page }) => {
  await open(page, "/projects/P156634", 1440, await p156634());
  const summary = page.locator("[data-summary=ready]");
  await expect(summary).toBeVisible();
  // ISR 19's ratings sit in a numbered section, and still cite the passage that prints them.
  for (const fact of await summary.locator("[data-fact]").all()) {
    await expect(fact.locator("[data-fact-source] [data-citation]")).toHaveCount(1);
  }
  await expect(summary.locator("[data-fact=pdo] [data-fact-source]")).toHaveText(/^ISR 19, Jun 30, 2026\u2060\[\d+\]$/);
  for (const key of ["agencies", "sectors"]) {
    const gaps = await summary.locator(`[data-fact=${key}] li`).evaluateAll((items) =>
      items.slice(1).map((item, index) => Math.round(item.getBoundingClientRect().top - items[index].getBoundingClientRect().bottom)),
    );
    expect(gaps.length, key).toBeGreaterThan(1);
    for (const gap of gaps) expect(gap, key).toBe(4);
  }
});

test("the Summary's record marker shows the value it cites, and the lead says how much was canceled however large", async ({ page }) => {
  // The route decides whether any was canceled (tests/test_project_hub.py), since "1,234.5" is not a number.
  const body = JSON.parse(await recorded("summary-p130164.json"));
  body.lead = { ...body.lead, canceled: "1,234.5", any_canceled: true };
  await open(page, "/projects/P130164", 1440, { "/api/projects/P130164/summary": { body: JSON.stringify(body) } });
  const summary = page.locator("[data-summary=ready]");
  await expect(summary.locator("[data-summary-lead]")).toContainText("US$1,234.5 million was canceled.");

  // The marker beside "B" opens the projects API's record, which holds that value and the sector shares.
  await summary.locator("[data-fact=ea_category] [data-citation]").click();
  const record = page.getByRole("dialog").locator("[data-record]");
  await expect(record).toContainText("Environmental Assessment CategoryB");
  await expect(record).toContainText("Sector, in Strata's taxonomyTransportation");
  await expect(record).toContainText("Sector and shareRural and Inter-Urban Roads: 97%");
  await page.keyboard.press("Escape");

  // Stacked below 768 px, the column heads are hidden, so a money value's units follow its label.
  await page.setViewportSize({ width: 390, height: 900 });
  await expect(summary.locator("[data-fact=commitment]").getByRole("rowheader")).toHaveText("Commitment (US$, millions)");
});

test("the Summary's skeleton has as many rows in each table as P130164's populated Summary", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await mockApi(page, await hubApi());
  let release!: () => void;
  const held = new Promise<void>((resolve) => (release = resolve));
  await page.route("**/api/projects/P130164/summary", async (route) => {
    await held;
    await route.fulfill({ status: 200, contentType: "application/json", body: await recorded("summary-p130164.json") });
  });
  await page.goto("/projects/P130164");
  const rows = () => page.locator("[data-fact-table]").evaluateAll((tables) => tables.map((table) => table.querySelectorAll("tbody tr").length));
  await expect(page.locator("[data-summary=loading]")).toBeVisible();
  const loading = await rows();

  release();
  await expect(page.locator("[data-summary=ready]")).toBeVisible();

  expect(loading).toEqual(await rows());
  await expect(page.locator("[data-summary=loading] h4, [data-summary=ready] h4").first()).toHaveText("Closing date history");
});

test("a project with a risk rating under the ESF shows it in the Ratings table, in place of its Environmental Assessment Category", async ({ page }) => {
  // No recorded project has an ESF rating, so P130164's recorded Summary gets one by hand, as the server
  // gives it (tests/test_project_hub.py: esf_rating in place of ea_category, cited to the project record).
  const body = JSON.parse(await recorded("summary-p130164.json"));
  body.ratings = body.ratings.map((fact: { key: string }) => (fact.key === "ea_category" ? { ...fact, key: "esf_rating", value: "Substantial" } : fact));
  await open(page, "/projects/P130164", 1440, { "/api/projects/P130164/summary": { body: JSON.stringify(body) } });

  const row = page.locator("[data-summary=ready] [data-fact=esf_rating]");
  await expect(row.getByRole("rowheader")).toHaveText("Environmental and social risk");
  await expect(row.getByRole("cell").first()).toHaveText("Substantial");
  await expect(row.locator("[data-fact-source]")).toHaveText(/^Projects API, Aug 1, 2023⁠\[1\]$/);
  await expect(page.locator("[data-summary=ready] [data-fact=ea_category]")).toHaveCount(0);
  await expect(page.locator("[data-summary=ready]")).not.toContainText("Environmental Assessment Category");
});

// ── Documents ───────────────────────────────────────────────────────────

test("P130164's Documents list the PAD, the ISRs, the ICR and the ICR Review re-issue with the ground truth's dates", async ({ page }) => {
  await open(page, "/projects/P130164/documents");
  const list = page.locator("[data-documents=ready] [data-view=table]");
  await expect(list).toBeVisible();

  await expect(list.locator("tbody[data-group] > tr:first-child th")).toHaveText([
    "Project Appraisal Document (PAD)1 document",
    "Implementation Status and Results Reports (ISRs)13 documents",
    "Procurement Plans15 documents",
    "Implementation Completion and Results Report (ICR)1 document",
    "ICR Reviews by the Independent Evaluation Group (IEG)1 document",
    "Other documents30 documents",
  ].map((text) => new RegExp(`^${text.replace(/[()]/g, "\\$&").replace(/(\d+ documents?)$/, "\\s*$1")}$`)));
  const pad = list.locator("[data-document=pad-2013-10-01]");
  await expect(pad.locator("th")).toHaveText("Project Appraisal Document");
  await expect(pad.locator("td").first()).toHaveText("Oct 1, 2013");
  await expect(pad.locator("td").nth(1)).toHaveText("Nov 6, 2013");
  // Pages read puts the number first, with a Partial badge only when pages were missed.
  await expect(pad.locator("td").nth(2)).toContainText("86 of 100");
  await expect(pad.locator("td").nth(2)).toContainText("Partial");
  await expect(pad.getByRole("link", { name: "Project Appraisal Document", exact: true })).toHaveAttribute("href", "/projects/P130164/documents/pad-2013-10-01");
  const icr = list.locator("[data-document=icr-2019-10-10]");
  await expect(icr.locator("td").first()).toHaveText("Oct 10, 2019");
  await expect(icr.locator("td").nth(1)).toHaveText("Nov 2, 2019");
  await expect(icr.locator("td").nth(2)).toContainText("59 of 66");
  // The re-issued ICR Review is one row: its original date, then the re-issue's.
  const review = list.locator("[data-document=icr-review-2023-05-04]");
  await expect(review.locator("td").first()).toHaveText("Mar 27, 2020Re-issued May 4, 2023");
  await expect(review.locator("th")).toContainText("The re-issue replaces the version of March 27, 2020.");
  await expect(review.getByRole("link", { name: "Open the version of Mar 27, 2020" })).toHaveAttribute("href", "/projects/P130164/documents/icr-review-2020-03-27");
  await expect(list.locator("[data-group=isr] tr[data-document]")).toHaveCount(5);
  await expect(list.locator("[data-group=isr] tr[data-document]").first().locator("th")).toHaveText("ISR 13");
  // A document I haven't read is plain text and says so; the PDF link names its document.
  const plan = list.locator("[data-document='30152361']");
  await expect(plan.getByRole("link", { name: /^Procurement Plan of Jun 20, 2018$/ })).toHaveCount(0);
  await expect(plan.locator("td").nth(2)).toHaveText("Not read");
  await expect(icr.getByRole("link", { name: "Open the PDF of Implementation Completion and Results Report, October 10, 2019, on the World Bank's site (opens in a new tab)" })).toHaveAttribute("target", "_blank");
  await expect(page.locator("[data-documents-count]")).toHaveText("Showing 18 of 61 documents");

  // A group's fold opens in place and keeps focus on its button.
  const more = list.getByRole("button", { name: "Show all 13" });
  await more.click();
  await expect(list.locator("[data-group=isr] tr[data-document]")).toHaveCount(13);
  await expect(list.getByRole("button", { name: "Show fewer" })).toBeFocused();
  await expect(page.locator("[data-documents-count]")).toHaveText("Showing 26 of 61 documents");
});

test("Documents keeps each date and count on one line, starts Pages read at a card's left edge, and names a document with no type", async ({ page }) => {
  // P156634 lists a document whose type the documents API leaves blank (document 40098345); P130164's
  // first other document gets that blank by hand.
  const body = JSON.parse(await recorded("documents-p130164.json"));
  const other = body.groups.find((group: { type: string }) => group.type === "other");
  other.documents[0].document_type = "";
  await open(page, "/projects/P130164/documents", 1440, { "/api/projects/P130164/documents": { body: JSON.stringify(body) } });
  const list = page.locator("[data-documents=ready] [data-view=table]");
  await expect(list.locator("[data-document='32604339'] th")).toHaveText("Document of Nov 1, 2020");
  await expect(list.locator("[data-document='32604339']").getByRole("link", { name: /^Open the PDF of Document of Nov 1, 2020, November 1, 2020,/ })).toHaveCount(1);

  // One line box each, however narrow the column: an inline element has one client rect per line.
  const lines = (locator: import("@playwright/test").Locator) => locator.evaluate((element) => element.getClientRects().length);
  const review = list.locator("[data-document=icr-review-2023-05-04]");
  for (const width of [1440, 1024]) {
    await page.setViewportSize({ width, height: 900 });
    await expect(review.locator("td").first().locator("[data-day]")).toHaveCount(2);
    for (const day of await review.locator("[data-day]").all()) expect(await lines(day), `a date at ${width} px`).toBe(1);
    expect(await lines(review.getByRole("link", { name: "Open the version of Mar 27, 2020" }).locator("[data-day]")), `the link's date at ${width} px`).toBe(1);
  }

  await page.setViewportSize({ width: 390, height: 900 });
  const cards = page.locator("[data-documents=ready] [data-view=cards]");
  const pad = cards.locator("[data-group=pad]");
  expect(await lines(pad.locator("h3 [data-group-count]"))).toBe(1);
  const pages = pad.locator("li dl > div").nth(2);
  const [label, value] = await Promise.all([pages.locator("dt"), pages.locator("dd [data-pages-read]")].map((part) => part.evaluate((element) => Math.round(element.getBoundingClientRect().left))));
  expect(value).toBe(label);
});

test("Documents says when a project's documents are still to come, and when the project is outside the set I fetch documents for", async ({ page }) => {
  const file = async (name: string) => ({ body: await recorded(name) });
  // P117635 is a Kenya water project the slice selects, with no list of its documents yet; P120014 is an
  // energy project, outside the slice (tests/test_project_hub.py checks both against the server).
  await open(page, "/projects/P117635/documents", 1440, {
    "/api/projects/P117635": await file("project-p117635.json"),
    "/api/projects/P117635/documents": await file("documents-p117635-none-yet.json"),
    "/api/projects/P120014": await file("project-p120014.json"),
    "/api/projects/P120014/documents": await file("documents-p120014-outside.json"),
  });
  const card = page.locator("[data-documents=ready] [data-empty-state]");
  await expect(card.getByRole("heading")).toHaveText("I don't have any documents for this project yet.");
  await expect(page.locator("[data-documents-count]")).toHaveCount(0);

  await page.goto("/projects/P120014/documents");
  await expect(card.getByRole("heading")).toHaveText("I don't list documents for this project.");
  await expect(card).toContainText("I fetch and read documents only for a set of projects chosen for this demo, and this project isn't one of them.");
  await expect(card.getByRole("link", { name: "Data readiness" })).toHaveAttribute("href", "/data?sources=documents");
  await expect(page.locator("[data-documents-count]")).toHaveCount(0);
});

// ── The source view and the drawer's link ───────────────────────────────

test("the source view opens the ICR at page 23 with paragraph 54 highlighted and focused, and links the World Bank's PDF at that page", async ({ page }) => {
  await open(page, "/projects/P130164/documents/icr-2019-10-10?page=23&para=54");
  const view = page.locator("[data-source-page=read]");
  await expect(view).toBeVisible();

  await expect(main(page).getByRole("heading", { level: 1 })).toHaveText("Implementation Completion and Results Report");
  const block = page.locator("[data-highlighted]");
  await expect(block).toContainText("54. Another lesson to be highlighted is that the works contract estimates should have been based on the market rate");
  await expect(block).toBeFocused();
  await expect(block).toHaveAccessibleDescription("You opened this page at paragraph 54.");
  // The highlight token, #fff1b8, once it has settled in.
  await expect.poll(() => block.evaluate((el) => getComputedStyle(el).backgroundColor)).toBe("rgb(255, 241, 184)");
  // Only paragraph 54 is highlighted, and it sits under its section's caption.
  await expect(page.locator("[data-highlighted]")).toHaveCount(1);
  await expect(view.getByText("Section III.B")).toBeVisible();
  await expect(page.locator("#para-54")).toBeVisible();
  await expect(main(page).getByRole("navigation", { name: "Pages of this document" }).first()).toContainText("Page 23 of 66");
  await expect(main(page).getByRole("link", { name: "Open page 23 in the World Bank's PDF, opens in a new tab" })).toHaveAttribute(
    "href",
    "https://documents.worldbank.org/curated/en/258481572631321132/pdf/India-Rajasthan-Road-Sector-Modernization-Project.pdf#page=23",
  );
  await expect(page).toHaveTitle("ICR of Oct 10, 2019, page 23 | Strata");
  // The project crumb is a link, so its P-code is plain mono inside it, never a link inside a link.
  await expect(page.locator("a a")).toHaveCount(0);
  await expect(page.getByRole("navigation", { name: "Breadcrumb" }).getByRole("link", { name: "Rajasthan Road Sector Modernization (P130164)" })).toHaveAttribute("href", "/projects/P130164");
});

test("while a page of the source view loads, its page bar gives the page from the address and no total, and keeps Next page's place", async ({ page }) => {
  // The 21 design review, round 2, B2: no tool has returned the page count yet (CLAUDE.md rule 1).
  await page.setViewportSize({ width: 1440, height: 900 });
  await mockApi(page, await hubApi());
  let release!: () => void;
  const held = new Promise<void>((resolve) => (release = resolve));
  await page.route((url) => url.pathname === "/api/projects/P130164/documents/icr-2019-10-10", async (route) => {
    await held;
    await route.fulfill({ status: 200, contentType: "application/json", body: await recorded("source-icr-p130164-23-54.json") });
  });
  await page.goto("/projects/P130164/documents/icr-2019-10-10?page=23&para=54");
  const bar = main(page).getByRole("navigation", { name: "Pages of this document" });
  await expect(bar.locator("[data-page-lead]")).toHaveText("Page 23");
  await expect(bar).not.toContainText(" of ");
  // Unseen, so it is out of the accessibility tree, but it holds its place in the bar.
  await expect(bar.getByRole("link", { name: "Next page", includeHidden: true })).toHaveCSS("visibility", "hidden");
  await expect(bar.getByRole("spinbutton", { name: "Go to page" })).not.toHaveAttribute("max");

  release();

  await expect(page.locator("[data-source-page=read]")).toBeVisible();
  await expect(bar.first().locator("[data-page-lead]")).toHaveText("Page 23 of 66");
  await expect(bar.first().getByRole("link", { name: "Next page" })).toHaveCSS("visibility", "visible");
});

test("the drawer's Open at page 23 lands on the source view with paragraph 54 highlighted, and Back returns to the drawer", async ({ page }) => {
  await open(page, `/projects/P130164?evidence=${encodeURIComponent("strata.gold.passage:31525018/v1/54")}`);
  const drawer = page.getByRole("dialog");
  const link = drawer.getByRole("link", { name: "Open at page 23", exact: true });
  await expect(link).toBeVisible();
  // It opens in the same tab, with no external icon.
  await expect(link).not.toHaveAttribute("target");

  await link.click();

  await expect(page).toHaveURL(/\/projects\/P130164\/documents\/icr-2019-10-10\?page=23&para=54$/);
  const block = page.locator("[data-highlighted]");
  await expect(block).toContainText("54. Another lesson");
  await expect(block).toBeFocused();

  await page.goBack();
  await expect(page.getByRole("dialog").getByRole("heading", { level: 2 })).toHaveText("Rajasthan Road Sector Modernization, paragraph 54");
});

test("Back from the source view restores the page with its answer and the drawer, with focus on the drawer's heading", async ({ page }) => {
  await open(page, "/projects/P130164", 1440, { "/api/ask": { body: await recorded("ask-p130164-removed-number.sse") } });
  await expect(page.locator("[data-summary=ready]")).toBeVisible();
  await askFromTheBox(page);
  await landed(page);
  await marker(page, 1).click();
  await page.getByRole("dialog").getByRole("link", { name: "Open at page 23", exact: true }).click();
  await expect(page.locator("[data-highlighted]")).toBeFocused();
  await expect(panel(page)).toHaveCount(0);
  // A question asked on the source view does not take the first page's answer away.
  await askFromTheBox(page);
  await landed(page);

  await page.goBack();

  await expect(panel(page)).toBeVisible();
  await expect(page.getByRole("dialog").getByRole("heading", { level: 2 })).toBeFocused();
});

test("the source view corrects a short address, a paragraph on another page, a missing paragraph and a page past the last, with a note", async ({ page }) => {
  // A bare type opens the one ICR, and the address becomes its key, in place.
  await open(page, "/projects/P130164/documents/icr?page=23&para=54");
  await expect(page).toHaveURL(/\/projects\/P130164\/documents\/icr-2019-10-10\?page=23&para=54$/);
  await expect(page.locator("[data-highlighted]")).toContainText("54.");

  await page.goto("/projects/P130164/documents/icr-2019-10-10?page=22&para=54");
  await expect(page.getByRole("status").filter({ hasText: "Paragraph 54 is on page 23, so I opened that page." })).toBeVisible();
  await expect(page).toHaveURL(/page=23&para=54$/);
  await expect(page.locator("[data-highlighted]")).toContainText("54.");

  await page.goto("/projects/P130164/documents/icr-2019-10-10?page=23&para=999");
  await expect(page.getByRole("status").filter({ hasText: "I don't have a paragraph 999 in this document, so I opened page 23 without a highlight." })).toBeVisible();
  await expect(page.locator("[data-highlighted]")).toHaveCount(0);

  await page.goto("/projects/P130164/documents/icr-2019-10-10?page=80");
  await expect(page.getByRole("status").filter({ hasText: "This document has 66 pages, so I opened page 66." })).toBeVisible();
  await expect(page).toHaveURL(/page=66$/);
  // A section that names itself an annex is captioned by its own name, never "Section Annex 8".
  await expect(page.locator("[data-source-page=read]").getByText("Annex 8", { exact: true })).toBeVisible();
  await expect(page.locator("[data-source-page=read]")).not.toContainText("Section Annex");
});

test("the source view says when a page or a document is not read, a link names no document, or names more than one", async ({ page }) => {
  await open(page, "/projects/P130164/documents/icr-2019-10-10?page=5");
  await expect(page.locator("[data-empty-state]")).toContainText("I couldn't read page 5.");
  await expect(page.locator("[data-empty-state]").getByRole("link")).toHaveText("Open page 5 in the World Bank's PDF");

  await page.goto("/projects/P130164/documents/30152361");
  await expect(page.locator("[data-source-page=doc_unread] [data-empty-state]")).toContainText("I haven't read this document.");

  await page.goto("/projects/P130164/documents/isr");
  await expect(page.locator("[data-empty-state]")).toContainText("This project has 13 ISRs, so the link doesn't say which one to open.");

  await page.goto("/projects/P130164/documents/not-a-document");
  await expect(page.locator("[data-empty-state]")).toContainText("I don't have this document for this project.");
  // The page never repeats text taken from the address.
  await expect(main(page)).not.toContainText("not-a-document");
});

test("the source view of a re-issued report says which version it replaces and links it", async ({ page }) => {
  await open(page, "/projects/P130164/documents/icr-review-2023-05-04?page=1");
  await expect(page.locator("[data-source-page=read]")).toBeVisible();
  await expect(main(page)).toContainText("This is the re-issue of May 4, 2023. It replaces the version of March 27, 2020.");
  await expect(main(page).getByRole("link", { name: "Open the version of Mar 27, 2020" })).toHaveAttribute("href", "/projects/P130164/documents/icr-review-2020-03-27?page=1");
});

test("axe finds no WCAG 2.2 AA violations on Summary, Documents and the source view at 1440, 1024 and 390 px, and they reflow at 320 px", async ({ page }) => {
  for (const [path, ready] of [
    ["/projects/P130164", "[data-summary=ready]"],
    ["/projects/P130164/documents", "[data-documents=ready]"],
    ["/projects/P130164/documents/icr-2019-10-10?page=23&para=54", "[data-source-page=read]"],
  ]) {
    await page.unrouteAll({ behavior: "ignoreErrors" });
    await open(page, path);
    await expect(page.locator(ready)).toBeVisible();
    for (const width of [1440, 1024, 390]) {
      await page.setViewportSize({ width, height: 900 });
      expect(await axe(page), `${path} at ${width} px`).toEqual([]);
    }
    await page.setViewportSize({ width: 320, height: 900 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth), `${path} at 320 px`).toBeLessThanOrEqual(320);
  }
});

// ── Procurement: what changed, the fold and Packages ────────────────────

const NWWDA = "/projects/P156634/procurement/northern-water-works-development-agency";

async function p156634(): Promise<Record<string, Answer>> {
  const file = async (name: string) => ({ body: await recorded(name) });
  return {
    "/api/projects/P156634": await file("project-p156634.json"),
    "/api/projects/P156634/summary": await file("summary-p156634.json"),
    "/api/projects/P156634/packages": await file("packages-p156634.json"),
    "/api/projects/P156634/packages?page=2": await file("packages-p156634-page-2.json"),
    "/api/projects/P156634/packages?q=boreholes": await file("packages-p156634-boreholes.json"),
    "/api/projects/P156634/packages?q=atlantis": await file("packages-p156634-no-match.json"),
    [`/api${NWWDA}/2026-10-09`]: await file("check-plan-p156634-nwwda-2026-10-09.json"),
    [`/api${NWWDA}/2026-10-09/changes`]: await file("changes-nwwda-2026-10-09.json"),
    [`/api${NWWDA}/2020-12-07/changes`]: await file("changes-nwwda-2020-12-07.json"),
    "/api/projects/P156634/procurement/ministry-of-water-and-irrigation/2020-04-30": await file("check-plan-p156634-ministry-2020-04-30.json"),
    "/api/projects/P156634/procurement/ministry-of-water-and-irrigation/2020-04-30/changes": await file("changes-ministry-2020-04-30.json"),
  };
}

test("the Procurement tab says what changed in each agency's latest plan and links the full list on that plan's check", async ({ page }) => {
  await open(page, "/projects/P156634/procurement", 1440, await p156634());
  const nwwda = page.locator("[data-agency=northern-water-works-development-agency]");
  const sentence = nwwda.locator("[data-changes-sentence]");
  await expect(sentence).toHaveText("The latest plan is the plan of October 9, 2026. Compared with the plan of March 5, 2026, it re-estimated two activities. See what changed");
  await expect(sentence.getByRole("link", { name: "See what changed" })).toHaveAttribute("href", `${NWWDA}/2026-10-09#changes`);
  // Source lines on a project's own pages leave its ID out (DESIGN.md section 5, ProjectId).
  await expect(nwwda.locator("[data-source]")).toHaveText(/^Source: World Bank documents and reports API, Procurement Plans listed for this project, through [A-Z][a-z]+ \d{1,2}, \d{4}\.$/);
  await expect(page.locator("[data-agency=ministry-of-water-and-irrigation] [data-changes-sentence]")).toHaveText(
    "The latest plan is the plan of April 30, 2020. Compared with the plan of November 8, 2019, it added one activity and re-dated one. See what changed",
  );
  // An agency with one plan says it has nothing to compare it with, and links nowhere.
  const kilifi = page.locator("[data-agency=kilifi-mariakani-water-and-sewerage-company-ltd] [data-changes-sentence]");
  await expect(kilifi).toHaveText("The only plan I have from this agency is the plan of March 19, 2025, so I can't compare it with an earlier version.");
  await expect(kilifi.getByRole("link")).toHaveCount(0);

  await sentence.getByRole("link", { name: "See what changed" }).click();

  // The plan's check opens at its change list, whose heading takes focus.
  const heading = page.getByRole("heading", { level: 2, name: "What changed since the plan of March 5, 2026" });
  await expect(heading).toBeFocused();
});

test("an agency's version list shows the five newest and the baseline, and folds the rest behind Show all", async ({ page }) => {
  const body = JSON.parse(await recorded("project-p156634-baseline.json"));
  const nwwda = body.agencies[0];
  // Two older versions than the fixture holds, folded: the route marks which versions show.
  for (const [index, date] of ["2019-06-14", "2019-01-10"].entries()) {
    nwwda.versions.push({ ...nwwda.versions[4], document_id: `older-${index}`, plan_date: date, disclosed_on: date, is_latest: false, is_baseline: false, shown: false });
  }
  nwwda.version_count = 7;
  nwwda.shown_count = 5;
  await open(page, "/projects/P156634/procurement", 1440, { ...(await p156634()), "/api/projects/P156634": { body: JSON.stringify(body) } });
  const block = page.locator("[data-agency=northern-water-works-development-agency]");
  await expect(block.getByText("Showing 5 of 7 versions")).toBeVisible();
  await expect(block.locator("[data-table-view=table] tbody th").nth(2)).toHaveText("Plan of Jul 21, 2025 Baseline");
  const more = block.getByRole("button", { name: "Show all 7 versions" });
  await expect(more).toHaveAttribute("aria-expanded", "false");

  await more.click();

  await expect(block.locator("[data-table-view=table] tbody tr")).toHaveCount(7);
  await expect(block.getByText("Showing all 7 versions")).toBeVisible();
  const fewer = block.getByRole("button", { name: "Show fewer versions" });
  await expect(fewer).toBeFocused();
  await expect(fewer).toHaveAttribute("aria-expanded", "true");
});

test("Packages lists every activity in each agency's latest plan by STEP reference, 20 a page, and searches past the PDF's wrap spaces", async ({ page }) => {
  const unrecorded = await open(page, "/projects/P156634/procurement", 1440, await p156634());
  const packages = page.locator("[data-packages=ready]");
  await expect(packages.getByRole("heading", { level: 2, name: "Packages" })).toBeVisible();
  await expect(packages.locator("[data-page-lead]")).toHaveText("Showing 1–20 of 46 packages");
  const first = packages.locator("[data-table-view=table] tbody tr").first();
  await expect(first.getByRole("link", { name: "KE-NWWDA-229129-CW-RFB" })).toHaveAttribute("href", `${NWWDA}/2026-10-09#KE-NWWDA-229129-CW-RFB`);
  await expect(first.locator("td")).toHaveText(["Northern Water Works Development Agency", "Request for Bids · Open - National", "300,000.00", "Signed"]);
  await expect(packages.getByRole("navigation", { name: "Pages of the package list" })).toContainText("Page 1 of 3");

  await packages.getByRole("link", { name: "Next page" }).click();
  await expect(page).toHaveURL(/packages_page=2$/);
  await expect(page.locator("[data-packages] [data-page-lead]")).toHaveText("Showing 21–40 of 46 packages");

  // The description reads "Exploratory Bo reholes" in the PDF, and the search still finds "boreholes".
  const field = page.getByRole("searchbox", { name: "Search packages" });
  await field.fill("boreholes");
  await expect(page).toHaveURL(/packages_q=boreholes$/);
  const found = page.locator("[data-packages=ready] [data-table-view=table] tbody tr");
  await expect(found).toHaveCount(5);
  await expect(found.nth(2)).toContainText("Equipping of Exploratory Bo reholes Project-Lot 1");
  await field.fill("atlantis");
  await expect(page.locator("[data-packages] [data-empty-state]")).toContainText("I found no packages that match your search.");
  expect(unrecorded).toEqual([]);
});

// ── Check a plan: what changed and the baseline ─────────────────────────

test("the NWWDA plan of October 9, 2026 lists what changed since the plan of March 5, 2026, as the two versions' rows differ", async ({ page }) => {
  await open(page, `${NWWDA}/2026-10-09`, 1440, await p156634());
  await expect(page.locator("[data-check-plan-page=ready]")).toBeVisible();
  // The two versions differ only in two estimates (tests/ground_truth/values.toml, plan-541055-estimated
  // and plan-541062-estimated, and their plan-of-March-5 entries): nothing was added, dropped or re-dated.
  await expect(page.locator("[data-change-line]")).toHaveText("Compared with the plan of March 5, 2026, this version re-estimated two activities. See what changed");
  const changes = page.locator("[data-changes]");
  await expect(changes.getByRole("heading", { level: 2 })).toHaveText("What changed since the plan of March 5, 2026");
  await expect(changes).toContainText("This version re-estimated two activities. No activity was added, dropped or re-dated.");
  await expect(changes.locator("[data-change-kind]")).toHaveCount(1);
  const table = changes.locator("[data-change-kind=reestimated]");
  await expect(table.getByRole("heading", { level: 3 })).toHaveText("Two activities were re-estimated.");
  await expect(table.locator("[data-view=table] tbody tr")).toHaveText([
    /^KE-NWWDA-541055-CW-RFB.*1,200,000\.001,230,000\.0030,000\.00 more$/,
    /^KE-NWWDA-541062-CW-RFQ.*280,000\.00295,000\.0015,000\.00 more$/,
  ]);
  // The changed rows say so in their Activity cell, as text.
  await expect(page.locator("[data-view=table] [data-changed]")).toHaveCount(2);
  await expect(page.locator("#KE-NWWDA-541055-CW-RFB [data-changed]")).toHaveText("Re-estimated in this version");
  await expect(changes.locator("[data-source]")).toContainText("Procurement Plans of Northern Water Works Development Agency, versions of March 5, 2026 and October 9, 2026");
});

test("a version that added and re-dated activities lists each in its own table, with a step that lost its date as No date", async ({ page }) => {
  await open(page, "/projects/P156634/procurement/ministry-of-water-and-irrigation/2020-04-30", 1440, await p156634());
  const changes = page.locator("[data-changes]");
  await expect(changes.locator("[data-change-kind]")).toHaveCount(2);
  await expect(changes.locator("[data-change-kind=added] h3")).toHaveText("One activity was added.");
  await expect(changes.locator("[data-change-kind=added] [data-view=table] tbody tr")).toContainText("MWSI-WSDP-04-2019-2020");
  const redated = changes.locator("[data-change-kind=redated] [data-view=table] tbody");
  await expect(redated.locator("th[scope=rowgroup]")).toContainText("MOWS-WSDP-01-2017-2018");
  // With no new date there is nothing to measure, so Moved shows nothing and tells a screen reader why.
  await expect(redated.locator("td")).toHaveText(["Expression of Interest Notice", "Jun 11, 2018", "No date", "Not measured"]);
  await expect(redated.locator("td").last().locator(".sr-only")).toHaveText("Not measured");
  await page.setViewportSize({ width: 390, height: 900 });
  await expect(changes.locator("[data-change-kind=redated] li dd").first()).toHaveText("Was Jun 11, 2018. Now no date.");
});

test("when only the comparison fails, the change line says so and links the section, which keeps its heading over the alert", async ({ page }) => {
  await open(page, `${NWWDA}/2026-10-09`, 1440, {
    ...(await p156634()),
    [`/api${NWWDA}/2026-10-09/changes`]: { status: 503, body: '{"code":"data_service","trace_id":"0af7651916cd43dd8448eb211c80319c"}' },
  });
  await expect(page.locator("[data-check-plan-page=ready]")).toBeVisible();
  const line = page.locator("[data-change-line]");
  await expect(line).toHaveText("I couldn't load what changed in this plan. Go to that section");
  await expect(line.getByRole("link", { name: "Go to that section" })).toHaveAttribute("href", "#changes");
  const section = page.locator("[data-changes=error]");
  await expect(section.getByRole("heading", { level: 2 })).toHaveText("What changed in this plan");
  await expect(section.getByRole("alert")).toHaveText("I couldn't load what changed in this plan because the data service didn't answer.");
  // Try again sits 16 px under the alert, as on every other load error.
  const [alert, retry] = await Promise.all([section.getByRole("alert").boundingBox(), section.getByRole("button", { name: "Try again" }).boundingBox()]);
  expect(Math.round(retry!.y - (alert!.y + alert!.height))).toBe(16);
});

test("the earliest version has no change list, and its change line says why", async ({ page }) => {
  await open(page, `${NWWDA}/2020-12-07`, 1440, {
    ...(await p156634()),
    [`/api${NWWDA}/2020-12-07`]: { body: JSON.stringify({ ...JSON.parse(await recorded("check-plan-p156634-nwwda-2026-10-09.json")), plan: { ...JSON.parse(await recorded("check-plan-p156634-nwwda-2026-10-09.json")).plan, plan_date: "2020-12-07" } }) },
  });
  await expect(page.locator("[data-change-line]")).toHaveText("This is the earliest plan I have from this agency, so I have no earlier version to compare it with.");
  await expect(page.locator("[data-changes]")).toHaveCount(0);
});

test("after Save as the baseline, a check reports delay against the baseline and against the first published planned date, each labeled", async ({ page }) => {
  const check = `/api${NWWDA}/2025-07-21`;
  let saved = false;
  const writes: { method: string; body: unknown }[] = [];
  await open(page, `${NWWDA}/2025-07-21`, 1440, {
    ...(await p156634()),
    [`/api${NWWDA}/2025-07-21/changes`]: { status: 404, body: '{"code":"unknown_plan"}' },
  });
  await page.route(`**${check}`, async (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: await recorded(saved ? "check-plan-p156634-nwwda-2025-07-21-baseline.json" : "check-plan-p156634-nwwda-2025-07-21.json") }),
  );
  await page.route(`**/api${NWWDA}/baseline`, async (route) => {
    writes.push({ method: route.request().method(), body: route.request().postDataJSON() });
    saved = route.request().method() === "PUT";
    await route.fulfill({ status: 200, contentType: "application/json", body: saved ? await recorded("baseline-saved.json") : '{"baseline":null}' });
  });
  await page.reload();
  const panel = page.getByRole("region", { name: "Baseline for delay" });
  await expect(panel).toContainText("No plan from this agency is saved as the baseline yet. If this is the plan agreed at negotiations, save it as the baseline.");
  const signed = page.locator("#KE-NWWDA-229129-CW-RFB");
  // Without a baseline, ticket 10's reason stays word for word.
  await expect(signed).toContainText("Signed January 3, 2022, 186 days after its planned date, at US$1,245,092.76, about 4 times its estimate.");

  await panel.getByRole("button", { name: "Save as the baseline" }).click();

  expect(writes).toEqual([{ method: "PUT", body: { plan_date: "2025-07-21" } }]);
  await expect(panel.getByRole("status")).toHaveText("I saved the plan of July 21, 2025 as the baseline. The reasons below now also give delay against it.");
  await expect(panel.getByRole("status")).toBeFocused();
  // The reasons now name both measures, each labeled: the first published planned date and the baseline.
  await expect(signed).toContainText("Signed January 3, 2022, 186 days after its first published planned date, at US$1,245,092.76, about 4 times its estimate.");
  await expect(signed.locator("[data-baseline-delay=late]")).toHaveText("That was 186 days after its baseline date of July 1, 2021.");
  await expect(page.locator("[data-method]")).toContainText(
    "I measure delay two ways: from the first published planned date, because each plan update can move the planned dates, and from the baseline, the plan of July 21, 2025.",
  );

  // Undo puts things back as they were, with no dialog.
  await panel.getByRole("button", { name: "Undo" }).click();
  await expect(panel.getByRole("status")).toHaveText("I undid that change. No plan from this agency is saved as the baseline.");
  expect(writes.map((write) => write.method)).toEqual(["PUT", "DELETE"]);
  await expect(signed.locator("[data-baseline-delay]")).toHaveCount(0);
});

test("a later plan's check names the saved baseline and who saved it, gives both delays, and asks in place before replacing it", async ({ page }) => {
  await open(page, `${NWWDA}/2026-10-09`, 1440, {
    ...(await p156634()),
    [`/api${NWWDA}/2026-10-09`]: { body: await recorded("check-plan-p156634-nwwda-2026-10-09-baseline.json") },
  });
  const panel = page.getByRole("region", { name: "Baseline for delay" });
  await expect(panel.getByRole("status")).toHaveText(
    "The baseline is the plan of July 21, 2025, saved by Ana Example on October 23, 2026. I measure delay from its dates as well as from the first published planned dates.",
  );
  await expect(panel.getByRole("link", { name: "Plan of Jul 21, 2025" })).toHaveAttribute("href", `${NWWDA}/2025-07-21`);
  await expect(page.locator("#KE-NWWDA-229129-CW-RFB [data-baseline-delay=late]")).toHaveText("That was 186 days after its baseline date of July 1, 2021.");
  await expect(page.locator("#KE-NWWDA-541055-CW-RFB [data-baseline-delay=not_in_baseline]")).toHaveText(
    "It was not in the baseline plan, so I measure its delay only from its first published planned date.",
  );
  // The baseline's days explain themselves, as the first delay's do.
  await page.locator("#KE-NWWDA-229129-CW-RFB [data-baseline-delay] button[data-num]").focus();
  await expect(page.getByRole("tooltip")).toContainText("Planned date in the baseline, the plan of July 21, 2025");

  await panel.getByRole("button", { name: "Make this plan the baseline" }).click();
  const confirm = panel.locator("[data-baseline-confirm]");
  await expect(confirm).toHaveText("This replaces the plan of July 21, 2025 as the baseline for everyone who checks Northern Water Works Development Agency's plans.");
  await expect(confirm).toBeFocused();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  // Stacked at 390 px, the ghost "Keep" button sits flush, its label on the sentence's left edge.
  await page.setViewportSize({ width: 390, height: 900 });
  const keep = panel.getByRole("button", { name: "Keep the plan of Jul 21, 2025" });
  const left = (locator: import("@playwright/test").Locator) => locator.evaluate((element) => Math.round(element.getBoundingClientRect().left));
  expect(Math.abs((await left(keep.locator("span").first())) - (await left(confirm)))).toBeLessThanOrEqual(1);
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.keyboard.press("Escape");
  await expect(panel.getByRole("button", { name: "Make this plan the baseline" })).toBeFocused();
});

test("the implementing agency view reads the baseline without its saver and offers no control, and the public view shows no panel", async ({ page }) => {
  const body = JSON.parse(await recorded("check-plan-p156634-nwwda-2026-10-09-baseline.json"));
  body.baseline.saved_by = null;
  await open(page, `${NWWDA}/2026-10-09?view=piu`, 1440, { ...(await p156634()), [`/api${NWWDA}/2026-10-09?view=piu`]: { body: JSON.stringify(body) } });
  const panel = page.getByRole("region", { name: "Baseline for delay" });
  await expect(panel).toHaveText("The baseline is the plan of July 21, 2025, saved on October 23, 2026 as the plan agreed at negotiations. Only World Bank staff can change it.");
  await expect(panel.getByRole("button")).toHaveCount(0);

  const open_ = JSON.parse(await recorded("check-plan-p156634-nwwda-2026-10-09.json"));
  await page.unrouteAll({ behavior: "ignoreErrors" });
  await open(page, `${NWWDA}/2026-10-09?view=public`, 1440, { ...(await p156634()), [`/api${NWWDA}/2026-10-09?view=public`]: { body: JSON.stringify(open_) } });
  await expect(page.locator("[data-check-plan-page=ready]")).toBeVisible();
  await expect(page.getByRole("region", { name: "Baseline for delay" })).toHaveCount(0);
});

// ── The Summary's budget on a throttled 3G profile ──────────────────────

// The throttled profile the screen tests use: Chrome's Fast 3G, 562.5 ms of latency, 1.44 Mbps down and
// 675 kbps up. The app's own files go through the browser's network emulation; the recorded /api answers
// are served by the test, so each waits the profile's latency and its size at the profile's speed.
const FAST_3G = { latency: 562.5, download: (1.44 * 1024 * 1024) / 8, upload: (675 * 1024) / 8 };

async function throttle(page: Page) {
  const session = await page.context().newCDPSession(page);
  await session.send("Network.enable");
  await session.send("Network.emulateNetworkConditions", {
    offline: false,
    latency: FAST_3G.latency,
    downloadThroughput: FAST_3G.download,
    uploadThroughput: FAST_3G.upload,
  });
  const api = await hubApi();
  await page.route("**/api/**", async (route) => {
    const url = new URL(route.request().url());
    const answer = api[url.pathname];
    if (!answer) return route.fallback();
    await new Promise((resolve) => setTimeout(resolve, FAST_3G.latency + (answer.body.length / FAST_3G.download) * 1000));
    return route.fulfill({ status: 200, contentType: "application/json", body: answer.body });
  });
}

test("the Summary is one request of at most 15 KB, populated within 2 s from another tab and 5 s cold on the throttled 3G profile", async ({ page }) => {
  // One request, small enough for a slow link.
  expect(Buffer.byteLength(await recorded("summary-p130164.json"))).toBeLessThanOrEqual(15 * 1024);

  await open(page, "/projects/P130164/procurement");
  await expect(page.locator("[data-procurement-tab=ready]")).toBeVisible();
  await throttle(page);
  const started = Date.now();
  await tabs(page).first().click();
  await expect(page.locator("[data-summary=ready]")).toBeVisible({ timeout: 10_000 });
  const fromTab = Date.now() - started;
  expect(fromTab, "from another tab, in ms").toBeLessThanOrEqual(2000);

  // Cold: a new page, with nothing cached.
  const cold = await page.context().newPage();
  await mockApi(cold, await hubApi());
  await throttle(cold);
  const coldStart = Date.now();
  await cold.goto("/projects/P130164");
  await expect(cold.locator("[data-summary=ready]")).toBeVisible({ timeout: 15_000 });
  const coldTime = Date.now() - coldStart;
  test.info().annotations.push({ type: "timing", description: `from another tab ${fromTab} ms, cold ${coldTime} ms` });
  expect(coldTime, "cold, in ms").toBeLessThanOrEqual(5000);
});

test("axe finds no WCAG 2.2 AA violations on Check a plan's change list and baseline panel, and in the hub's loading and error states", async ({ page }) => {
  // Check a plan with the Ministry's change list (added and re-dated) and the baseline panel, at three widths.
  await open(page, "/projects/P156634/procurement/ministry-of-water-and-irrigation/2020-04-30", 1440, await p156634());
  await expect(page.locator("[data-changes]")).toBeVisible();
  for (const width of [1440, 1024, 390]) {
    await page.setViewportSize({ width, height: 900 });
    expect(await axe(page), `change list at ${width} px`).toEqual([]);
  }
  await page.setViewportSize({ width: 320, height: 900 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth), "change list at 320 px").toBeLessThanOrEqual(320);

  // The baseline panel with another plan saved, and its replace confirm.
  await page.unrouteAll({ behavior: "ignoreErrors" });
  await open(page, `${NWWDA}/2026-10-09`, 390, { ...(await p156634()), [`/api${NWWDA}/2026-10-09`]: { body: await recorded("check-plan-p156634-nwwda-2026-10-09-baseline.json") } });
  await page.getByRole("button", { name: "Make this plan the baseline" }).click();
  expect(await axe(page), "baseline confirm at 390 px").toEqual([]);

  // The Summary, Documents and source view while they load and when the data service doesn't answer.
  const down = { status: 503, body: '{"code":"data_service","trace_id":"0af7651916cd43dd8448eb211c80319c"}' };
  for (const [path, api, ready] of [
    ["/projects/P130164", "/api/projects/P130164/summary", "[data-summary=error]"],
    ["/projects/P130164/documents", "/api/projects/P130164/documents", "[data-documents=error]"],
    ["/projects/P130164/documents/icr-2019-10-10?page=23", "/api/projects/P130164/documents/icr-2019-10-10?page=23", "[data-source-page=error]"],
  ] as const) {
    await page.unrouteAll({ behavior: "ignoreErrors" });
    await open(page, path, 390, { [api]: down });
    await expect(page.locator(ready)).toBeVisible();
    await expect(page.getByRole("alert")).toBeVisible();
    expect(await axe(page), `${path} error at 390 px`).toEqual([]);
    await page.unrouteAll({ behavior: "ignoreErrors" });
    await mockApi(page, await hubApi());
    await page.route(`**${api.split("?")[0]}*`, () => new Promise(() => {}));
    await page.goto(path);
    await expect(page.locator(ready.replace("error", "loading"))).toBeVisible();
    expect(await axe(page), `${path} loading at 390 px`).toEqual([]);
  }
});
