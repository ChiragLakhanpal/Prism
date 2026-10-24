// The package workspace (ticket 12) at seam 4: KE-NWWDA-541055-CW-RFB's section 1, "How long it
// took", against find_comparables' answers recorded in tests/fixtures/api, which the server tests
// check the server against. The numbers below are tests/ground_truth/values.toml's [past_range],
// computed once with lifelines and checked with statsmodels, and the words are the 12 brief's, copied
// here so the test checks the screen against an independent source.
import AxeBuilder from "@axe-core/playwright";
import type { Page } from "@playwright/test";
import { expect, mockApi, recorded, test } from "./mocked";

const REF = "KE-NWWDA-541055-CW-RFB";
const PATH = `/packages/${REF}`;
const API = `/api/packages/${REF}`;
const WCAG_22_AA = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];
// values.toml [past_range]: 49 comparables, 45 signed and four still open; the middle half 3.3 to
// 7.9 months, the middle 4.4, 8 in 10 within 9.1; the plan's 1.5 months, and two signed within them.
const FINDING = "2 of 49 comparable packages, fewer than 1 in 10, were signed within the plan's 1.5 months.";

type Answer = { status?: number; body: string };
type Comparables = { rows: { step_reference: string; months: number; still_open: boolean }[]; [key: string]: unknown };

async function openPackage(page: Page, options: { width?: number; comparables?: Answer | null; pkg?: Answer | null; ref?: string } = {}) {
  const { width = 1440, ref = REF } = options;
  await page.setViewportSize({ width, height: 900 });
  const api = `/api/packages/${ref}`;
  const pkgFile = ref === REF ? "package-ke-nwwda-541055.json" : "package-ke-nwwda-541062.json";
  const comparablesFile = ref === REF ? "comparables-ke-nwwda-541055.json" : "comparables-ke-nwwda-541062.json";
  const answers: Record<string, Answer> = {
    "/api/me": { body: await recorded("me.json") },
    "/api/freshness": { body: await recorded("freshness.json") },
  };
  if (options.pkg !== null) answers[api] = options.pkg ?? { body: await recorded(pkgFile) };
  if (options.comparables !== null) answers[`${api}/comparables`] = options.comparables ?? { body: await recorded(comparablesFile) };
  await mockApi(page, answers);
  // A path left out never answers, so the page stays loading.
  if (options.pkg === null) await page.route(`**${api}`, () => new Promise(() => {}));
  if (options.comparables === null) await page.route(`**${api}/comparables`, () => new Promise(() => {}));
  await page.goto(`/packages/${encodeURIComponent(ref)}`);
}

const section = (page: Page) => page.locator("[data-past-range]");
const ready = async (page: Page) => expect(page.locator("[data-past-range]:not([data-past-range=loading])")).toBeVisible();
const readout = (page: Page) => page.locator("[data-readout]");

async function derived(name: string, edit: (body: Comparables) => void): Promise<Answer> {
  const body = JSON.parse(await recorded(name)) as Comparables;
  edit(body);
  return { body: JSON.stringify(body) };
}

async function signedWithin(months: number): Promise<number> {
  const body = JSON.parse(await recorded("comparables-ke-nwwda-541055.json")) as Comparables;
  return body.rows.filter((row) => !row.still_open && row.months <= months).length;
}

async function axe(page: Page) {
  const results = await new AxeBuilder({ page }).withTags(WCAG_22_AA).analyze();
  return results.violations.map((v) => `${v.id}: ${v.nodes.map((node) => node.target.join(" ")).join(", ")}`);
}

test("the workspace names the package, lists its facts in STEP's field names, and states the finding as the chart's title", async ({ page }) => {
  await openPackage(page);
  await ready(page);
  const main = page.getByRole("main");

  await expect(main.getByRole("heading", { level: 1 })).toContainText("Equipping of Exploratory");
  await expect(main.locator("[data-package-header]")).toContainText(REF);
  await expect(page).toHaveTitle(`Package ${REF} | Strata`);
  const crumbs = main.getByRole("navigation", { name: "Breadcrumb" });
  await expect(crumbs.getByRole("link", { name: "Packages" })).toHaveAttribute("href", "/packages");
  await expect(crumbs.getByRole("link", { name: "Water and Sanitation Development Project (P156634)" })).toHaveAttribute("href", "/projects/P156634");
  const facts = main.locator("[data-package-facts]");
  for (const [label, value] of [
    ["Method", "Request for Bids"],
    ["Market Approach", "Open - National"],
    ["Review Type", "Post"],
    ["Estimated Amount (US$)", "1,230,000.00"],
    ["Process Status", "Pending Implementation"],
  ]) {
    await expect(facts.locator("div", { has: page.getByText(label, { exact: true }) })).toContainText(value);
  }
  await expect(facts.getByRole("link", { name: "Northern Water Works Development Agency plan of October 9, 2026" })).toHaveAttribute(
    "href",
    `/projects/P156634/procurement/northern-water-works-development-agency/2026-10-09#${REF}`,
  );

  await expect(section(page).getByText("Planning", { exact: true })).toBeVisible();
  await expect(section(page).getByRole("heading", { level: 2 })).toHaveAccessibleName("How long it took");
  await expect(section(page).getByRole("heading", { level: 3 })).toHaveText(FINDING);
  await expect(page.getByRole("figure", { name: FINDING })).toBeVisible();
  await expect(section(page).locator("[data-summary]")).toHaveText(
    "The middle half of these packages took 3.3 to 7.9 months, and the middle one took 4.4. 8 in 10 were signed within 9.1 months. " +
      "Four of the 49 are still open. I kept them in the range as not signed yet, so the range does not look shorter than it was.",
  );
  await expect(section(page).locator("[data-coverage-line]")).toContainText(
    "Based on 49 of 65 matching packages; 3 lacked the STEP reference that links notice to contract, 10 had no specific procurement notice " +
      "in the records I hold and 3 were canceled before a contract was signed.",
  );
  await expect(section(page).locator("[data-coverage-line]").getByRole("link")).toHaveAttribute(
    "href",
    "/data?sources=notices,awards,documents,projects&from=find_comparables",
  );
  await expect(section(page).locator("[data-source]").first()).toContainText("Records run through October 13, 2026.");
});
