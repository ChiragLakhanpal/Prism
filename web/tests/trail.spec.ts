// The activity page's contract trail, a project's Connections tab and "Why this source" (ticket 22) at seam 4,
// against the answers the server wrote on the fixture (tests/record_api.py), which tests/test_project_hub.py
// checks the server against. The values are the records' own, as tests/ground_truth/values.toml quotes them
// (plan-229129-estimated, notice-229129-invitation, award-229129-signed, award-229129-amount,
// award-notice-229129-published, [award_notice_bids], award-7431-signed, icr-date and icr-months-after-7431),
// copied here so the screens are checked against an independent source.
import AxeBuilder from "@axe-core/playwright";
import type { Page, Request } from "@playwright/test";
import { expect, mockApi, recorded, test } from "./mocked";
import { ICR_54, KENYA, SHOWCASE, trailApi } from "./trail-api";

const WCAG_22_AA = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];
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
  const results = await new AxeBuilder({ page }).withTags(WCAG_22_AA).analyze();
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
    "The award notice listed 11 bids. In the project's reports, 23 paragraphs appeared together with the contract.",
  );
  const trail = page.getByRole("list", { name: `Contract trail for ${KENYA}` });
  await expect(trail.locator(":scope > li")).toHaveCount(5);
  await expect(trail.getByRole("heading", { level: 2 })).toHaveText([
    "In the Procurement Plan", "Notice", "Bids", "Contract", "Paragraphs that appeared together with the contract",
  ]);
  await expect(stage(page, "plan")).toContainText("Estimated Amount (US$)300,000.00");
  await expect(stage(page, "notice")).toContainText("Published Sep 17, 2021");
  await expect(stage(page, "notice").locator("[data-source]")).toContainText("Procurement notice OP00146683, published Sep 17, 2021.");
  // The bids, in the award notice's order, with their prices as it writes them and their results.
  const rows = stage(page, "bids").locator("tbody tr");
  await expect(rows).toHaveCount(11);
  await expect(rows.first().locator("th, td")).toHaveText(["OSB AFRICA LIMITED", "61503269.60", "61503269.60", "Awarded"]);
  await expect(rows.nth(3).locator("th, td")).toHaveText(["HYDRO WATER WELL (K) LIMITED", "69346168.80", "Not in the notice", "Not awarded"]);
  await expect(rows.nth(10).locator("th, td")).toHaveText(["BITAT LIMITED", "54770811.00", "54770811.00", 'Rejected. The award notice gives the reason "Non Responsive".']);
  await expect(stage(page, "bids")).toContainText("Award notice published Feb 2, 2022");
  await expect(stage(page, "contract")).toContainText("Signed Jan 3, 2022");
  await expect(stage(page, "contract")).toContainText("Signed amount (US$)1,245,092.76");
  for (const name of ["plan", "notice", "bids", "contract"]) await expect(stage(page, name).locator("[data-source]").first()).toBeVisible();
  await expect(page.locator("[data-paragraph-card] [data-source]")).toHaveCount(10);

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

  await expect(bids.locator("thead th")).toHaveText(["Bidder", "Bid price at opening (KES)", "Evaluated bid price (KES)", "Result"]);
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
  await expect(why.getByRole("link", { name: `Open the activity ${SHOWCASE}` })).toHaveAttribute("href", SHOWCASE_PATH);
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
  await expect(tabs).toHaveText(["Summary", "Procurement", "Documents", "Connections"]);
  await expect(tabs.last()).toHaveAttribute("aria-current", "page");

  await expect(page.locator("#connections-finding")).toHaveText("In this project, one contract appeared together with 53 paragraphs from 11 of its reports.");
  await expect(page.locator("[data-connections]")).toContainText("Showing 20 of 65 packages and documents");
  const nodes = page.locator("[data-node]");
  expect(await nodes.count()).toBeLessThanOrEqual(20);
  await expect(page.locator("[data-diagram]").getByRole("link", { name: "and 15 more Procurement Plans" })).toHaveAttribute("href", "/projects/P130164/documents");
  await expect(page.locator("[data-diagram]").getByRole("link", { name: "and 30 more documents" })).toBeVisible();
  // One dashed line for each link the tool returned between a shown package and a shown chip, and two solid lines.
  const edges = JSON.parse(await recorded("connections-p130164.json")).edges.length;
  await expect(page.locator("[data-diagram] > svg path[stroke-dasharray]")).toHaveCount(edges);
  await expect(page.locator("[data-diagram] > svg path:not([stroke-dasharray])")).toHaveCount(2);
  expect(await axe(page)).toEqual([]);
  expect(unrecorded).toEqual([]);
});

test("every node and chip is reachable by keyboard and opens its page or the drawer", async ({ page }) => {
  await open(page, "/projects/P130164/connections");
  const links = page.locator("[data-diagram] [data-node-link], [data-diagram] [data-node=project] a, [data-diagram] [data-node=document] [data-chip]");
  const count = await links.count();
  expect(count).toBeGreaterThan(10);
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
  await expect(page.getByRole("button", { name: "Show as a diagram" })).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByRole("status").filter({ hasText: "Showing the list." })).toHaveCount(1);
  await expect(page.locator("[data-diagram=list]")).toBeVisible();
});

test("Connections caps a large project at 20 nodes and counts its packages, and shows its no-links, empty and error states", async ({ page }) => {
  await open(page, "/projects/P156634/connections", 1024);
  await expect(page.locator("[data-connections]")).toContainText("Showing 20 of 628 packages and documents");
  await expect(page.getByRole("link", { name: "and 265 more packages" })).toHaveAttribute("href", "/projects/P156634/procurement");
  expect(await page.locator("[data-node]").count()).toBeLessThanOrEqual(20);
  expect(await axe(page)).toEqual([]);

  await page.goto("/projects/P127203/connections");
  await expect(page.locator("#connections-finding")).toHaveText("In this project, no contract appeared together with a paragraph from its reports.");
  await expect(page.locator("[data-connections]")).toContainText("I keep a link only when its score reaches 0.50.");

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
