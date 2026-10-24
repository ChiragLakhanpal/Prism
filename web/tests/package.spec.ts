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

test("the chart draws each comparable as a dot on a month axis, hollow if still open, with the middle half as a band and the middle as a tick", async ({ page }) => {
  await openPackage(page);
  await ready(page);
  const chart = page.locator("[data-chart-drawing]");

  await expect(chart).toHaveAttribute("role", "img");
  await expect(chart.locator("[data-dot=filled]")).toHaveCount(45);
  await expect(chart.locator("[data-dot=hollow]")).toHaveCount(4);
  const hollow = await chart.locator("[data-dot=hollow] circle").nth(1).evaluate((el) => [getComputedStyle(el).fill, getComputedStyle(el).stroke]);
  expect(hollow).toEqual(["rgb(255, 255, 255)", "rgb(16, 108, 161)"]);
  const filled = await chart.locator("[data-dot=filled] circle").nth(1).evaluate((el) => getComputedStyle(el).fill);
  expect(filled).toBe("rgb(16, 108, 161)");
  // DESIGN.md section 6: a grey200 band with line-strong edges, and a 2.5 px grey500 middle tick.
  const band = await chart.locator("[data-band]").evaluate((el) => [getComputedStyle(el).fill, getComputedStyle(el).stroke]);
  expect(band).toEqual(["rgb(206, 212, 222)", "rgb(88, 110, 132)"]);
  const middle = await chart.locator("[data-middle]").evaluate((el) => [getComputedStyle(el).stroke, el.getAttribute("stroke-width")]);
  expect(middle).toEqual(["rgb(17, 17, 17)", "2.5"]);
  await expect(chart.locator("[data-in10]")).toHaveCount(1);
  // The axis runs in months from 0, with about five ticks.
  await expect(chart.locator("text").filter({ hasText: /^(0|6|12|18 months)$/ })).toHaveCount(4);
  // The text alternative states the same numbers, and says what happened to the canceled packages.
  await expect(page.locator("[data-chart-alt]")).toHaveText(
    "Dot chart of 49 comparable packages on a month axis from 0 to 18 months: 45 signed and 4 still open. The middle half took " +
      "3.3 to 7.9 months, the middle one took 4.4, and 8 in 10 were signed within 9.1. A line marks 1.5 months, and 2 of 49 were " +
      "signed within it. I left out the 3 canceled packages, because they are not still open.",
  );
});

test("dragging the plan line, pressing arrow keys on it or typing months updates the readout from the returned rows, and the table agrees", async ({ page }) => {
  await openPackage(page);
  await ready(page);
  const slider = page.getByRole("slider", { name: "Planned months" });
  await expect(readout(page)).toHaveText("2 of 49 signed within 1.5 months");
  await expect(slider).toHaveAttribute("aria-valuetext", "1.5 months, the plan's own figure. 2 of 49 were signed within 1.5 months.");

  // Keyboard: Right adds half a month, Page Up three.
  await slider.focus();
  await page.keyboard.press("ArrowRight");
  await expect(readout(page)).toHaveText(`${await signedWithin(2)} of 49 signed within 2.0 months`);
  await page.keyboard.press("PageUp");
  await expect(slider).toHaveAttribute("aria-valuenow", "5");
  await expect(readout(page)).toHaveText(`${await signedWithin(5)} of 49 signed within 5.0 months`);

  // Mouse: drag the knob to the middle of the axis, which runs to 18 months.
  const box = (await page.locator("[data-range-chart]").boundingBox())!;
  const knob = (await slider.boundingBox())!;
  await page.mouse.move(knob.x + knob.width / 2, knob.y + knob.height / 2);
  await page.mouse.down();
  await page.mouse.move(box.x + 8 + (box.width - 16) / 2, knob.y + knob.height / 2, { steps: 4 });
  await page.mouse.up();
  await expect(slider).toHaveAttribute("aria-valuenow", "9");
  await expect(readout(page)).toHaveText(`${await signedWithin(9)} of 49 signed within 9.0 months`);
  await expect(page.locator("[data-live]")).toHaveText(`${await signedWithin(9)} of 49 were signed within 9.0 months.`);

  // Typing: the line follows the number, and the reset button brings back the plan's months.
  const input = page.getByRole("textbox", { name: "Planned months" });
  await input.fill("6,5");
  await expect(readout(page)).toHaveText(`${await signedWithin(6.5)} of 49 signed within 6.5 months`);
  await expect(slider).toHaveAttribute("aria-valuenow", "6.5");

  // The table's last column follows the line, so the readout can be checked row by row.
  await section(page).getByRole("button", { name: "Show the table" }).click();
  const table = page.locator("[data-comparables-table] table");
  await expect(table.locator("thead")).toContainText("Signed within 6.5 months");
  await expect(table.locator("tbody tr")).toHaveCount(49);
  await expect(table.locator("tbody td:last-child").filter({ hasText: /^Yes$/ })).toHaveCount(await signedWithin(6.5));

  await page.getByRole("button", { name: "Use the plan's 1.5 months" }).click();
  await expect(input).toHaveValue("1.5");
  await expect(input).toBeFocused();
  await expect(readout(page)).toHaveText("2 of 49 signed within 1.5 months");
});

test("a number that is not between 0.5 and 60 months leaves the line where it was and says why", async ({ page }) => {
  await openPackage(page);
  await ready(page);
  const input = page.getByRole("textbox", { name: "Planned months" });

  await input.fill("90");

  await expect(input).toHaveAttribute("aria-invalid", "true");
  await expect(section(page).getByText("Type a number of months from 0.5 to 60.", { exact: true })).toBeVisible();
  await expect(page.getByRole("slider")).toHaveAttribute("aria-valuenow", "1.5");
});

test("the dots are one tab stop with arrow keys between them, each names its package, and Escape hides its details", async ({ page }) => {
  await openPackage(page);
  await ready(page);
  await page.getByRole("slider").focus();

  await page.keyboard.press("Tab");
  const group = page.getByRole("group", { name: "49 comparable packages, one dot each" });
  const first = group.getByRole("img").first();
  await expect(first).toBeFocused();
  // The shortest is KE-MIGORI COUNTY-532367-CW-RFB, still open after 13 days (0.4 months).
  await expect(first).toHaveAccessibleName("KE-MIGORI COUNTY-532367-CW-RFB, Kenya. Still open after 0.4 months. Dot 1 of 49.");
  const tip = page.locator("[data-dot-tooltip]");
  await expect(tip).toContainText("KE-MIGORI COUNTY-532367-CW-RFB");

  await page.keyboard.press("ArrowRight");
  await page.keyboard.press("ArrowRight");
  await page.keyboard.press("ArrowRight");
  const fourth = group.getByRole("img").nth(3);
  await expect(fourth).toBeFocused();
  await expect(fourth).toHaveAccessibleName(
    "KE-WAJWASCO-372776-CW-RFB, Kenya. Signed after 1.1 months, on October 6, 2023. Dot 4 of 49.",
  );
  await expect(tip).toContainText("Signed Oct 6, 2023. Notice published Sep 2, 2023. Kenya.");

  await page.keyboard.press("Escape");
  await expect(tip).toHaveCount(0);
  await expect(fourth).toBeFocused();

  // One tab stop: the next Tab leaves the chart.
  await page.keyboard.press("Tab");
  expect(await page.evaluate(() => document.activeElement?.getAttribute("role"))).not.toBe("img");
  // Coming back lands on the dot visited last.
  await page.keyboard.press("Shift+Tab");
  await expect(fourth).toBeFocused();
});

test("a dot shows its package on hover and Escape hides it, and a click on the axis row moves the plan line there", async ({ page }) => {
  await openPackage(page);
  await ready(page);
  const tip = page.locator("[data-dot-tooltip]");
  await page.locator("[data-range-chart]").scrollIntoViewIfNeeded();
  const dot = (await page.locator("[data-dot-target='3']").boundingBox())!;

  await page.mouse.move(dot.x + dot.width / 2, dot.y + dot.height / 2);
  await expect(tip).toContainText("KE-WAJWASCO-372776-CW-RFB");
  await expect(tip).toHaveAttribute("aria-hidden", "true");
  await page.keyboard.press("Escape");
  await expect(tip).toHaveCount(0);

  // The axis row runs from 0 to 18 months across the plot, 8 px in from each side.
  const box = (await page.locator("[data-range-chart]").boundingBox())!;
  await page.mouse.click(box.x + 8 + ((box.width - 16) * 12) / 18, box.y + box.height - 12);
  await expect(page.getByRole("slider")).toHaveAttribute("aria-valuenow", "12");
  await expect(readout(page)).toHaveText(`${await signedWithin(12)} of 49 signed within 12.0 months`);
});

test("above 60 comparables the lane draws 20 quantile dots, and the table still lists every package 20 at a time", async ({ page }) => {
  await openPackage(page, { comparables: { body: await recorded("comparables-ke-nwwda-541055-any-category.json") } });
  await ready(page);

  await expect(page.locator("[data-chart-drawing] [data-dot]")).toHaveCount(20);
  await expect(page.getByRole("group", { name: /^20 dots, each 1 in 20 of the 103 comparable packages$/ })).toBeVisible();
  await section(page).getByRole("button", { name: "Show the table" }).click();
  await expect(page.locator("[data-comparables-table] table tbody tr")).toHaveCount(20);
  await expect(page.locator("[data-comparables-table]")).toContainText("Showing 1–20 of 103 packages");
  await page.getByRole("button", { name: "Next 20" }).click();
  await expect(page.locator("[data-comparables-table]")).toContainText("Showing 21–40 of 103 packages");
});

test("below 20 comparables there is no range and no share: the copy file's sentence, every package, and the table open", async ({ page }) => {
  await openPackage(page, { comparables: { body: await recorded("comparables-ke-nwwda-541055-prior.json") } });
  await ready(page);

  await expect(section(page).getByRole("heading", { level: 3 })).toHaveText(
    "I'm not giving a range: only seven comparable packages. Here are all seven.",
  );
  await expect(page.locator("[data-chart-drawing] [data-dot]")).toHaveCount(7);
  await expect(page.locator("[data-chart-drawing] :is([data-band], [data-middle], [data-in10])")).toHaveCount(0);
  await expect(section(page)).not.toContainText(/in 10|percent|%/);
  await expect(readout(page)).toHaveText("0 of 7 signed within 1.5 months");
  await expect(section(page).getByRole("button", { name: "Hide the table" })).toHaveAttribute("aria-expanded", "true");
  await expect(page.locator("[data-comparables-table] table tbody tr")).toHaveCount(7);
});

// The states the 12 brief lists, each checked with axe at the three widths the review captures.
const SERVICE_DOWN = '{"code":"data_service","trace_id":"0af7651916cd43dd8448eb211c80319c"}';
const STATES: [string, () => Promise<Parameters<typeof openPackage>[1]>][] = [
  ["populated", async () => ({})],
  ["no plan dates", async () => ({ comparables: await derived("comparables-ke-nwwda-541055.json", (body) => (body.plan = null)) })],
  ["quantile dots", async () => ({ comparables: { body: await recorded("comparables-ke-nwwda-541055-any-category.json") } })],
  ["abstention", async () => ({ comparables: { body: await recorded("comparables-ke-nwwda-541055-prior.json") } })],
  ["no match", async () => ({ comparables: { body: await recorded("comparables-ke-nwwda-541055-india.json") } })],
  ["none measurable", async () => ({ comparables: { body: await recorded("comparables-ke-nwwda-541055-non-consulting.json") } })],
  ["not measurable", async () => ({ ref: "KE-NWWDA-541062-CW-RFQ" })],
  ["section error", async () => ({ comparables: { status: 503, body: SERVICE_DOWN } })],
  ["page error", async () => ({ pkg: { status: 503, body: SERVICE_DOWN } })],
  ["loading", async () => ({ comparables: null })],
  ["not found", async () => ({ pkg: { status: 404, body: '{"code":"unknown_package"}' } })],
];
const SETTLED = new Set(["populated", "no plan dates", "quantile dots", "abstention", "no match", "none measurable", "not measurable", "section error"]);

for (const [name, options] of STATES) {
  test(`the ${name} state passes axe at 1440, 1024 and 390 px`, async ({ page }) => {
    for (const width of [1440, 1024, 390]) {
      await openPackage(page, { ...(await options()), width });
      await expect(page.locator("main h1")).toBeVisible();
      if (SETTLED.has(name)) await ready(page);
      expect(await axe(page), `${width} px`).toEqual([]);
    }
  });
}

test("below 768 px the section's sentence leads the chart in the page's order, so focus never jumps", async ({ page }) => {
  await openPackage(page, { width: 390 });
  await ready(page);
  const order = await page.evaluate(() => {
    const summary = document.querySelector("[data-summary]")!;
    const chart = document.querySelector("[data-chart-figure]")!;
    return summary.compareDocumentPosition(chart) & Node.DOCUMENT_POSITION_FOLLOWING;
  });
  expect(order).toBeTruthy();
});

test("a plan row with no planned dates has no plan line until you type months", async ({ page }) => {
  await openPackage(page, { comparables: await derived("comparables-ke-nwwda-541055.json", (body) => (body.plan = null)) });
  await ready(page);

  await expect(section(page).getByRole("heading", { level: 3 })).toHaveText(
    "The middle half of the 49 comparable packages took 3.3 to 7.9 months from notice to signature.",
  );
  await expect(page.getByRole("slider")).toHaveCount(0);
  await expect(section(page).getByText(/^The plan row has no planned notice date or signing date/)).toBeVisible();

  await page.getByRole("textbox", { name: "Planned months" }).fill("4");
  await expect(page.getByRole("slider")).toHaveAttribute("aria-valuenow", "4");
  await expect(readout(page)).toHaveText(`${await signedWithin(4)} of 49 signed within 4.0 months`);
});

test("each Check a plan row links to its package's past range, named with its reference", async ({ page }) => {
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: 900 });
    await mockApi(page, {
      "/api/me": { body: await recorded("me.json") },
      "/api/freshness": { body: await recorded("freshness.json") },
      "/api/projects/P156634/procurement/northern-water-works-development-agency/2026-10-09": {
        body: await recorded("check-plan-p156634-nwwda-2026-10-09.json"),
      },
    });
    await page.goto("/projects/P156634/procurement/northern-water-works-development-agency/2026-10-09");
    const link = page.getByRole("link", { name: `See the past range for ${REF}` }).filter({ visible: true });
    await expect(link).toHaveAttribute("href", PATH);
    await expect(link).toHaveText("See the past range");
  }
});
