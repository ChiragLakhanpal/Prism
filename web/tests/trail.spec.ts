// The activity page's contract trail, a project's Connections tab and "Why this source" (ticket 22) at seam 4,
// against the answers the server wrote on the fixture (tests/record_api.py), which tests/test_project_hub.py
// checks the server against. The values are the records' own, as tests/ground_truth/values.toml quotes them
// (plan-229129-estimated, notice-229129-invitation, award-229129-signed, award-229129-amount,
// award-notice-229129-published, [award_notice_bids], award-7431-signed, icr-date and icr-months-after-7431),
// copied here so the screens are checked against an independent source.
import type { Page, Request } from "@playwright/test";
import { scan } from "./axe";
import { expect, mockApi, recorded, test } from "./mocked";
import { ICR_54, KENYA, SHOWCASE, trailApi } from "./trail-api";

type Answer = { status?: number; body: string };
const KENYA_PATH = `/projects/P156634/packages/${KENYA}`;
const SHOWCASE_PATH = `/projects/P130164/packages/${SHOWCASE}`;
const SERVICE_DOWN = '{"code":"data_service","trace_id":"0af7651916cd43dd8448eb211c80319c"}';

async function open(page: Page, path: string, width = 1440, extra: Record<string, Answer> = {}) {
  await page.setViewportSize({ width, height: 900 });
  const unrecorded = await mockApi(page, { ...(await trailApi()), ...extra });
  await page.goto(path);
  await expect(page.locator("main h1")).toBeVisible();
  return unrecorded;
}

async function axe(page: Page) {
  const results = await scan(page);
  return results.violations.map((v) => `${v.id}: ${v.nodes.map((node) => node.target.join(" ")).join(", ")}`);
}

const stage = (page: Page, name: string) => page.locator(`[data-stage=${name}]`);
const sideways = (page: Page) => page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);

// ── The activity page ────────────────────────────────────────────────────

test("KE-NWWDA-229129-CW-RFB's trail shows its plan row, notice, bids and contract, each with a source line, and calls no model", async ({ page }) => {
  const requests: Request[] = [];
  page.on("request", (request) => requests.push(request));
  const unrecorded = await open(page, KENYA_PATH);
  await expect(page.locator("[data-activity-page=ready]")).toBeVisible();

  await expect(page.locator("[data-lead] p").first()).toHaveText(
    "This activity was estimated at US$300,000 in the plan, advertised on September 17, 2021 and signed on January 3, 2022, for US$1,245,092.76.",
  );
  await expect(page.locator("[data-lead] p").nth(1)).toHaveText(
    "The award notice listed 11 bids. In the project's reports, 21 paragraphs appeared together with the contract.",
  );
  // The notice names the activity as STEP typed it, since the newer plans split words in its cell.
  await expect(page.locator("main h1")).toHaveText("Drilling of 4 Number Exploratory Boreholes In Wajir County");
  const trail = page.getByRole("list", { name: `Contract trail for ${KENYA}` });
  await expect(trail.locator(":scope > li")).toHaveCount(5);
  await expect(trail.getByRole("heading", { level: 2 })).toHaveText([
    "In the Procurement Plan", "Notice", "Bids", "Contract", "Paragraphs that appeared together with the contract",
  ]);
  await expect(stage(page, "plan")).toContainText("Estimated Amount (US$)300,000.00");
  await expect(stage(page, "notice")).toContainText("Published Sep 17, 2021");
  await expect(stage(page, "notice").locator("[data-source]")).toContainText("Procurement notice OP00146683, published Sep 17, 2021.");
  // The bids, in the award notice's order, with their prices in STEP's form with their cents, and their results.
  const rows = stage(page, "bids").locator("tbody tr");
  await expect(rows).toHaveCount(11);
  await expect(stage(page, "bids")).toContainText("Showing all 11 bids");
  await expect(rows.first().locator("th, td")).toHaveText(["OSB AFRICA LIMITED", "61,503,269.60", "61,503,269.60", "Awarded"]);
  await expect(rows.nth(3).locator("th, td")).toHaveText(["HYDRO WATER WELL (K) LIMITED", "69,346,168.80", "Not in the notice", "Not awarded"]);
  await expect(rows.nth(10).locator("th, td")).toHaveText(["BITAT LIMITED", "54,770,811.00", "54,770,811.00", 'Rejected. The award notice gives the reason "Non Responsive".']);
  await expect(stage(page, "bids")).toContainText("Award notice published Feb 2, 2022");
  await expect(stage(page, "contract")).toContainText("Signed Jan 3, 2022");
  await expect(stage(page, "contract")).toContainText("Signed amount (US$)1,245,092.76");
  for (const name of ["plan", "notice", "bids", "contract"]) await expect(stage(page, name).locator("[data-source]").first()).toBeVisible();
  // The paragraphs come grouped by report: the PAD's first three of its six, then each ISR's.
  await expect(page.locator("[data-report]")).toHaveCount(13);
  await expect(page.locator("[data-report]").first().getByRole("heading", { level: 3 })).toHaveText("Project Appraisal Document, Apr 5, 2017");
  await expect(page.locator("[data-report]").first()).toContainText("Six paragraphs");
  await expect(page.locator("[data-paragraph-card] [data-source]")).toHaveCount(18);

  const models: { method: string; path: string }[] = JSON.parse(await recorded("model-routes.json")).routes;
  const called = requests.map((request) => ({ method: request.method(), path: new URL(request.url()).pathname }));
  expect(called.filter((request) => models.some((model) => model.method === request.method && model.path === request.path))).toEqual([]);
  expect(await axe(page)).toEqual([]);
  expect(unrecorded).toEqual([]);
});

test("the trail shows no supplier score, rank or profile: bids keep the notice's order and a bidder is plain text", async ({ page }) => {
  await open(page, KENYA_PATH);
  const bids = stage(page, "bids");
  await expect(bids.locator("tbody tr")).toHaveCount(11);

  // The price columns carry the award notice's own names.
  await expect(bids.locator("thead th")).toHaveText(["Bidder", "Bid Price at Opening (KES)", "Evaluated Bid Price (KES)", "Result"]);
  await expect(bids.getByRole("button")).toHaveCount(0);
  await expect(bids.locator("tbody th a, [data-stage=contract] dd a")).toHaveCount(0);
  await expect(page.locator("main")).not.toContainText(/score|rank|profile/i);
});

test("an individual consultant is never named on the trail", async ({ page }) => {
  await open(page, "/projects/P156634/packages/KE-MAWASCO-501974-CS-INDV");
  await expect(stage(page, "bids")).toHaveText(/This activity hired an individual consultant\. I don't name individuals, and no bids were listed\./);
  await expect(stage(page, "contract")).toContainText("SupplierIndividual consultant");
});

test("the showcase trail states its two missing stages, takes its contract from the award notice, and explains ICR paragraph 54", async ({ page }) => {
  await open(page, SHOWCASE_PATH);
  await expect(stage(page, "plan")).toContainText(
    "I haven't read a Procurement Plan that lists this activity. The award notice names it by its STEP reference.",
  );
  await expect(stage(page, "notice")).toContainText("I found no notice with this STEP reference in the records through October 23, 2026.");
  await expect(stage(page, "contract")).toContainText(
    "The World Bank's contract awards data skip fiscal 2017 to 2019. This contract comes from its award notice, in Indian rupees.",
  );
  await expect(stage(page, "contract")).toContainText("Signed amount (INR)69,826,127.64");
  await expect(stage(page, "contract").locator("[data-source]")).toContainText("Award notice OP00044090, published Jul 19, 2017.");
  // The dashed segment runs only into the paragraphs.
  await expect(page.locator("[data-trail] [data-join]")).toHaveCount(4);
  await expect(page.locator("[data-trail] [data-join=together]")).toHaveCount(1);

  // "Why this source" for ICR paragraph 54, from a link with the drawer open on the activity page.
  await page.goto(`${SHOWCASE_PATH}?evidence=${ICR_54}`);
  const why = page.getByRole("dialog").locator("[data-why]");
  await expect(why.locator("[data-why-sentence]")).toHaveText(
    "This paragraph appeared together with award notice IN-RRSMP-7431-CW-RFB, signed June 15, 2017. Both concern works contracts and roads, in a project that has closed. The ICR is dated October 10, 2019, 28 months after the signing.",
  );
  await expect(why).toContainText("A link means only that they appeared together.");
  // On the activity page it names, the block does not link to the page you are on.
  await expect(why.getByRole("link", { name: `Open the activity ${SHOWCASE}` })).toHaveCount(0);
  await expect(page.getByRole("dialog").locator("[data-passage] mark, [data-passage] [data-highlight]").first()).toContainText("works contract");
  const score = why.getByRole("button", { name: "How I scored this link" });
  await expect(why.locator("[data-why-score]")).toBeHidden();
  await score.click();
  await expect(why.getByRole("button", { name: "Hide how I scored this link" })).toBeFocused();
  await expect(why.locator("[data-why-score] tbody th")).toHaveText(["Project", "Sector", "Time", "Wording", "Mentions"]);
  await expect(why).toContainText("Link score: 0.53. I keep a link when it scores 0.50 or more.");
  expect(await axe(page)).toEqual([]);
});

test("as of the day before the contract was signed, the trail holds no contract and no links", async ({ page }) => {
  await open(page, `${KENYA_PATH}?asof=2022-01-02`);
  // The page is all as of the date, so no alert says it shows today's data (the 22 critique, States).
  await expect(page.locator("[data-contract-trail], [data-trail]").first()).toBeVisible();
  await expect(page.getByText(/as of January 2, 2022 yet/)).toHaveCount(0);
  await expect(stage(page, "contract")).toContainText("No contract for this activity was public as of January 2, 2022.");
  await expect(stage(page, "paragraphs")).toContainText("I link paragraphs to signed contracts. As of January 2, 2022, this activity had none.");
  await expect(page.locator("[data-paragraph-card]")).toHaveCount(0);
  await expect(page.locator("main")).not.toContainText("1686165");
});

test("an activity no record holds says so, and one opened under another project moves to its own", async ({ page }) => {
  await open(page, "/projects/P156634/packages/KE-NWWDA-000000-CW-RFB");
  await expect(page.locator("[data-empty-state]")).toContainText("I have no activity KE-NWWDA-000000-CW-RFB in P156634.");
  await expect(page.locator("[data-empty-state]").getByRole("link", { name: "Procurement Plans for P156634" })).toHaveAttribute("href", "/projects/P156634/procurement");

  await page.goto(`/projects/P130164/packages/${KENYA}`);
  await expect(page).toHaveURL(new RegExp(`/projects/P156634/packages/${KENYA}$`));
});

test("the activity page's loading, service error and permission states", async ({ page }) => {
  await page.setViewportSize({ width: 1024, height: 900 });
  await mockApi(page, { ...(await trailApi()), [`/api${KENYA_PATH}`]: { status: 503, body: SERVICE_DOWN } });
  await page.goto(KENYA_PATH);
  await expect(page.getByRole("alert")).toHaveText("I couldn't load this activity. The data service didn't answer.");
  await expect(page.getByRole("button", { name: "Try again" })).toBeVisible();
  expect(await axe(page)).toEqual([]);

  await mockApi(page, { ...(await trailApi()), [`/api${KENYA_PATH}`]: { status: 403, body: '{"code":"permission"}' } });
  await page.goto(KENYA_PATH);
  await expect(page.getByRole("alert")).toHaveText("Your account can't read Strata's tables, so I can't show this activity.");
  await expect(page.getByRole("button", { name: "Try again" })).toHaveCount(0);

  await page.route(`**/api${KENYA_PATH}`, () => undefined);
  await page.goto(KENYA_PATH);
  await expect(page.getByRole("status").filter({ hasText: "Loading this activity." })).toHaveCount(1);
  expect(await axe(page)).toEqual([]);
});

test("at 390 and 320 px the trail reflows with no sideways scroll, the bids become cards, and it passes axe", async ({ page }) => {
  await open(page, KENYA_PATH, 390);
  await expect(stage(page, "bids").locator("[data-bid-card]")).toHaveCount(11);
  await expect(stage(page, "bids").locator("table")).toBeHidden();
  expect(await sideways(page)).toBeLessThanOrEqual(0);
  expect(await axe(page)).toEqual([]);
  await page.setViewportSize({ width: 320, height: 900 });
  expect(await sideways(page)).toBeLessThanOrEqual(0);
});

// ── The Connections tab ─────────────────────────────────────────────────

test("Connections draws at most 20 nodes, counts the rest by kind, and joins packages to paragraph chips with dashed lines", async ({ page }) => {
  const unrecorded = await open(page, "/projects/P130164/connections");
  await expect(page.locator("[data-connections=ready]")).toBeVisible();
  const tabs = page.getByRole("navigation", { name: "Project sections" }).getByRole("link");
  await expect(tabs).toHaveText(["Summary", "Procurement", "Timeline", "Documents", "Connections"]);
  await expect(tabs.last()).toHaveAttribute("aria-current", "page");

  // The finding counts every linked contract, those with no STEP reference too, and each paragraph once.
  await expect(page.locator("#connections-finding")).toHaveText("In this project, seven contracts appeared together with 89 paragraphs from 12 of its reports.");
  await expect(page.locator("[data-connections]")).toContainText("Showing 19 of 64 packages and documents");
  const nodes = page.locator("[data-node]");
  expect(await nodes.count()).toBeLessThanOrEqual(20);
  await expect(page.locator("[data-diagram]").getByRole("link", { name: "and 15 more Procurement Plans I haven't read" })).toHaveAttribute("href", "/projects/P130164/documents");
  await expect(page.locator("[data-diagram]").getByRole("link", { name: "and 30 more documents I haven't read" })).toBeVisible();
  // One dashed curve for each package and document that appeared together, and two solid lines.
  const lines = JSON.parse(await recorded("connections-p130164.json")).lines.length;
  await expect(page.locator("[data-diagram] > svg path[stroke-dasharray]")).toHaveCount(lines);
  await expect(page.locator("[data-diagram] > svg path:not([stroke-dasharray])")).toHaveCount(2);
  await expect(page.getByText("Hover over or focus a package to see its links.")).toHaveCount(0);
  // Each curve ends at a document card's left edge, so no part of a line runs under a card.
  const ends = await page.locator("[data-diagram] > svg path[stroke-dasharray]").evaluateAll((paths) =>
    paths.map((path) => (path.getAttribute("d") ?? "").trim().split(/[\s,]+/).slice(-2).map(Number)),
  );
  const cards = await page.locator("[data-node=document]").evaluateAll((items) => {
    const frame = document.querySelector("[data-diagram]")!.getBoundingClientRect();
    return items.map((item) => item.getBoundingClientRect().left - frame.left);
  });
  for (const [x] of ends) expect(cards.some((left) => Math.abs(left - x) < 1)).toBe(true);
  // The rest of a document's paragraphs open in its source view.
  await expect(page.locator("[data-node=document] [data-more-chips]").first()).toHaveAttribute("href", /^\/projects\/P130164\/documents\//);
  expect(await axe(page)).toEqual([]);
  expect(unrecorded).toEqual([]);
});

test("every node and chip is reachable by keyboard and opens its page or the drawer", async ({ page }) => {
  await open(page, "/projects/P130164/connections");
  const links = page.locator("[data-diagram] [data-node-link], [data-diagram] [data-node=project] a, [data-diagram] [data-node=document] [data-chip]");
  // The diagram draws after the page's h1, once its answer is in and its frame measured, so wait for its links
  // rather than count them at once (ticket 56).
  await expect(page.locator("[data-connections=ready]")).toBeVisible();
  await expect.poll(() => links.count()).toBeGreaterThan(10);
  const count = await links.count();
  for (let index = 0; index < count; index += 1) {
    const link = links.nth(index);
    if (!(await link.isVisible())) continue;
    await link.focus();
    await expect(link).toBeFocused();
    expect(await link.getAttribute("href")).toMatch(/^\/projects\/P130164|\?evidence=/);
  }
  // A chip opens the drawer at its paragraph, and Escape gives focus back to it.
  const chip = page.locator("[data-node=document] [data-chip]").first();
  await chip.focus();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(chip).toBeFocused();
  // A package node goes to its activity page.
  await expect(page.locator(`[data-package="${SHOWCASE}"] a[data-node-link]`)).toHaveAttribute("href", SHOWCASE_PATH);
});

test("below 768 px Connections is a list, and from 768 px a toggle shows the list", async ({ page }) => {
  await open(page, "/projects/P130164/connections", 390);
  await expect(page.locator("[data-diagram] > svg")).toBeHidden();
  await expect(page.getByRole("button", { name: "Show as a list" })).toBeHidden();
  await expect(page.locator(`[data-package="${SHOWCASE}"]`)).toContainText("Appeared together with");
  expect(await sideways(page)).toBeLessThanOrEqual(0);
  expect(await axe(page)).toEqual([]);

  await page.setViewportSize({ width: 1440, height: 900 });
  const toggle = page.getByRole("button", { name: "Show as a list" });
  await toggle.click();
  // The label says what a press does, so the button is not also a pressed toggle.
  await expect(page.getByRole("button", { name: "Show as a diagram" })).not.toHaveAttribute("aria-pressed");
  await expect(page.getByRole("status").filter({ hasText: "Showing the list." })).toHaveCount(1);
  await expect(page.locator("[data-diagram=list]")).toBeVisible();
});

test("Connections caps a large project at 20 nodes and counts its packages, and shows its no-links, empty and error states", async ({ page }) => {
  await open(page, "/projects/P156634/connections", 1024);
  await expect(page.locator("[data-connections]")).toContainText("Showing 19 of 627 packages and documents");
  await expect(page.getByRole("link", { name: "and 265 more packages" })).toHaveAttribute("href", "/projects/P156634/procurement");
  expect(await page.locator("[data-node]").count()).toBeLessThanOrEqual(20);
  // Past 12 curves, only the first linked package's are drawn at rest, and a caption says how to see the rest.
  const atRest = JSON.parse(await recorded("connections-p156634.json")).lines.filter((line: { at_rest: boolean }) => line.at_rest).length;
  await expect(page.locator("[data-diagram] > svg path[stroke-dasharray]")).toHaveCount(atRest);
  await expect(page.getByText("Hover over or focus a package to see its links.")).toBeVisible();
  await page.locator("[data-package=KE-NWWDA-229129-CW-RFB] a[data-node-link]").hover();
  expect(await page.locator("[data-diagram] > svg path.stroke-primary").count()).toBeGreaterThan(0);
  // A paragraph read in parts is one chip, and no two chips on one document have the same name.
  for (const card of await page.locator("[data-node=document]").all()) {
    const names = await card.locator("[data-chip] .clip-visually").allTextContents();
    expect(new Set(names).size).toBe(names.length);
  }
  expect(await axe(page)).toEqual([]);

  await page.goto("/projects/P127203/connections");
  await expect(page.locator("#connections-finding")).toHaveText("In this project, no contract appeared together with a paragraph from its reports.");
  await expect(page.locator("[data-connections]")).toContainText("I keep a link only when its score reaches 0.50.");
  // The empty column says why it is empty, and the rows say the documents they count are unread, not hidden.
  await expect(page.locator("[data-diagram]")).toContainText("I haven't read a Procurement Plan for P127203 yet.");
  await expect(page.getByRole("link", { name: "and 12 more ISRs I haven't read" })).toBeVisible();

  const empty = JSON.parse(await recorded("connections-p130164.json"));
  Object.assign(empty, { packages: [], documents: [], edges: [], more: [] });
  await mockApi(page, { ...(await trailApi()), "/api/projects/P130164/connections": { body: JSON.stringify(empty) } });
  await page.goto("/projects/P130164/connections");
  await expect(page.locator("[data-empty-state]")).toContainText("I have no packages or documents for P130164 yet.");

  await mockApi(page, { ...(await trailApi()), "/api/projects/P130164/connections": { status: 503, body: SERVICE_DOWN } });
  await page.goto("/projects/P130164/connections");
  await expect(page.getByRole("alert")).toHaveText("I couldn't load this project's connections. The data service didn't answer.");
  expect(await axe(page)).toEqual([]);
});

// ── Round 2 ──────────────────────────────────────────────────────────────

test("the showcase's paragraphs are grouped by report, so the ICR's group shows, and Show all opens the rest", async ({ page }) => {
  await open(page, SHOWCASE_PATH);
  const reports = page.locator("[data-report]");
  await expect(reports).toHaveCount(11);
  const icr = reports.last();
  await expect(icr.getByRole("heading", { level: 3 })).toHaveText("Implementation Completion and Results Report, Oct 10, 2019");
  await expect(icr).toContainText("29 paragraphs");
  await expect(icr.locator("[data-paragraph-card]")).toHaveCount(3);
  // The PAD numbers its annexes' paragraphs again, so two of its cards name their sections.
  await expect(reports.first().locator("[data-paragraph-card] h4").first()).toHaveText(/^Paragraph \d+$/);
  // A passage with no paragraph number is titled by its section's name, as the ISR names it.
  await expect(reports.nth(1).locator("[data-paragraph-card] h4")).toHaveText("Overall Ratings");
  const more = icr.getByRole("button", { name: "Show all 29 paragraphs from the Implementation Completion and Results Report of Oct 10, 2019" });
  await more.click();
  await expect(icr.locator("[data-paragraph-card]")).toHaveCount(29);
  await expect(icr.locator("[data-paragraph-card] a").nth(3)).toBeFocused();
  await expect(icr.locator(`[data-paragraph-card="31525018/v1/54"]`)).toBeVisible();
  await expect(icr.getByRole("button", { name: /^Show fewer paragraphs from the Implementation Completion/ })).toHaveAttribute("aria-expanded", "true");
  expect(await axe(page)).toEqual([]);
});

test("with two award notices and two contracts, the lead counts each notice's bids and one card holds both", async ({ page }) => {
  await open(page, "/projects/P156634/packages/KE-KIMAWASCO-372408-GO-RFQ");
  await expect(page.locator("[data-lead] p").nth(1)).toHaveText(
    "The award notices listed five and four bids. In the project's reports, one paragraph appeared together with its contracts.",
  );
  await expect(stage(page, "bids").locator("[data-stage-card]")).toHaveCount(1);
  await expect(stage(page, "bids").getByRole("heading", { level: 3 })).toHaveText(["Award notice OP00266922", "Award notice OP00266923"]);
  await expect(stage(page, "bids")).toContainText("Showing all five bids");
  // A Limited market approach invites firms directly, so its notice is never listed as missing.
  await expect(stage(page, "notice")).toContainText("This activity had no public notice. Its Market Approach,");
  expect(await axe(page)).toEqual([]);
});

test("a Limited market approach never lists the notice as missing, in the trail or the lead", async ({ page }) => {
  await open(page, "/projects/P156634/packages/KE-NWWDA-503455-CW-RFQ");
  await expect(stage(page, "notice")).toContainText("This activity had no public notice. Its Market Approach, Limited - National, invites firms directly.");
  await expect(page.locator("[data-lead]")).not.toContainText("no notice");
  await expect(stage(page, "bids")).toContainText("Showing the one bid");
});

test("a consultant award notice keeps a rejected firm's reason when its price is blank, and leaves its scores out", async ({ page }) => {
  await open(page, "/projects/P156634/packages/KE-CWSB-102977-CS-QCBS");
  const bids = stage(page, "bids");
  await expect(bids.getByRole("heading", { level: 2 })).toHaveText("Proposals");
  await expect(bids.locator("thead th").nth(2)).toHaveText("Final Evaluation Price (KES)");
  const rejected = bids.locator("tbody tr").filter({ hasText: "NICHOLAS O'DWYER" });
  await expect(rejected.locator("td").nth(1)).toHaveText("Not in the notice");
  await expect(rejected.locator("td").nth(2)).toHaveText('Rejected. The award notice gives the reason "Non Responsive".');
  await expect(bids).toContainText("The award notice also lists evaluation scores. I don't show scores or ranks for suppliers.");
  await expect(page.locator("main")).not.toContainText("Reason for Rejection");
});

test("the Connections tab and its header are as of the date the banner names, and the activity page has no other alert", async ({ page }) => {
  await open(page, "/projects/P130164/connections?asof=2017-06-14");
  // Every read on the page carries the date (ticket 40), so one banner speaks for the whole page.
  await expect(page.locator("[data-view-banner=asof]")).toContainText("I'm showing this page as of June 14, 2017.");
  await expect(page.locator("[data-diagram] > svg path[stroke-dasharray]")).toHaveCount(0);
  // The project node is one link, with its P-code and name inside it.
  await expect(page.locator("[data-node=project] a")).toHaveCount(1);

  await page.goto(`${KENYA_PATH}?asof=2022-01-02&view=public`);
  await expect(page.locator("[data-activity-page=ready]")).toBeVisible();
  await expect(page.getByText(/I can't show the public preview yet/)).toHaveCount(0);
  await expect(page.getByText(/I can't show this page as of/)).toHaveCount(0);
});
