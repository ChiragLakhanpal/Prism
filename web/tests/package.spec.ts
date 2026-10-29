// The package workspace (ticket 12) at seam 4: KE-NWWDA-541055-CW-RFB's section 1, "How long it
// took", against find_comparables' answers recorded in tests/fixtures/api, which the server tests
// check the server against. The numbers below are tests/ground_truth/values.toml's [past_range],
// computed once with lifelines and checked with statsmodels, and the words are the 12 brief's, copied
// here so the test checks the screen against an independent source.
import { scan } from "./axe";
import type { Locator, Page } from "@playwright/test";
import { expect, mockApi, openSidebar, recorded, test, windowBeside } from "./mocked";
import { fontsLoaded } from "./settled";

const REF = "KE-NWWDA-541055-CW-RFB";
const PATH = `/packages/${REF}`;
const API = `/api/packages/${REF}`;
// values.toml [past_range]: 49 comparables, 45 signed and four still open; the middle half 3.3 to
// 7.9 months, the middle 4.4, 8 in 10 within 9.1; the plan's 1.5 months, and two signed within them.
const FINDING = "2 of 49 comparable packages, fewer than 1 in 10, were signed within the plan's 1.5 months.";
// Lane 2 (ticket 26): the demo package's estimated amount, US$1,230,000.00, lies outside what the fixture's model
// learned from (tests/fixtures/api/estimate-ke-nwwda-541055.json), so lane 2 says so in the first person.
// No colon joins the two halves (ticket 58; DESIGN.md section 7, rule 16).
const OUTSIDE_TRAINING = "I'm not giving a time estimate, because this package is larger than any package my model learned from.";

type Answer = { status?: number; body: string };
type Comparables = { rows: { step_reference: string; months: number; still_open: boolean }[]; [key: string]: unknown };

// A source the evidence drawer opens: ICR paragraph 54 of P130164, as the answer panel cites it.
const ICR_54 = "strata.gold.passage:31525018/v1/54";

async function openPackage(
  page: Page,
  options: {
    width?: number;
    height?: number;
    comparables?: Answer | null;
    pkg?: Answer | null;
    ref?: string;
    evidence?: boolean;
    estimate?: Answer | null;
    // The drawer answers with the package's own plan row (ticket 101), as the facts' marker opens it.
    planRow?: boolean;
    rebidding?: Answer;
    // The recording the drawer answers with, such as a comparable package's records.
    drawer?: string;
  } = {},
) {
  const { width = 1440, ref = REF } = options;
  await page.setViewportSize({ width, height: options.height ?? 900 });
  const api = `/api/packages/${ref}`;
  const pkgFile = ref === REF ? "package-ke-nwwda-541055.json" : "package-ke-nwwda-541062.json";
  const comparablesFile = ref === REF ? "comparables-ke-nwwda-541055.json" : "comparables-ke-nwwda-541062.json";
  const answers: Record<string, Answer> = {
    "/api/me": { body: await recorded("me.json") },
    "/api/freshness": { body: await recorded("freshness.json") },
  };
  if (options.pkg !== null) answers[api] = options.pkg ?? { body: await recorded(pkgFile) };
  if (options.comparables !== null) answers[`${api}/comparables`] = options.comparables ?? { body: await recorded(comparablesFile) };
  // Section 3, procurement risks and what helped (ticket 30): the fixture's Kenya comparables reach no completion report.
  answers[`${api}/risks`] = { body: await recorded("risks-ke-nwwda-541055.json") };
  // Section 2, the planned date for each step (ticket 27): on the fixture every step abstains.
  answers[`${api}/steps`] = { body: await recorded("steps-ke-nwwda-541055.json") };
  // Lane 2, the time estimate (ticket 26): the demo package lies outside what the fixture's model learned from, so
  // lane 2 says so in a sentence; another package's time estimate never answers, so its lane 2 stays loading.
  const estimate = options.estimate === undefined && ref === REF ? { body: await recorded("estimate-ke-nwwda-541055.json") } : options.estimate;
  if (estimate) answers[`${api}/estimate`] = estimate;
  if (estimate) answering.add(page);
  else answering.delete(page);
  if (options.evidence) {
    answers["/api/evidence"] = { body: await recorded("evidence-icr-p130164-54.json") };
    answers["/api/evidence/opened"] = { body: '{"opened":[],"recorded":true}' };
  }
  if (options.planRow) {
    answers["/api/evidence"] = { body: await recorded("evidence-plan-row-ke-nwwda-541055.json") };
    answers["/api/evidence/opened"] = { body: '{"opened":[],"recorded":true}' };
  }
  if (options.rebidding) answers[`${api}/rebidding`] = options.rebidding;
  if (options.drawer) {
    answers["/api/evidence"] = { body: await recorded(options.drawer) };
    answers["/api/evidence/opened"] = { body: '{"opened":[],"recorded":true}' };
  }
  await mockApi(page, answers);
  // A path left out never answers, so the page stays loading.
  if (options.pkg === null) await page.route(`**${api}`, () => new Promise(() => {}));
  if (options.comparables === null) await page.route(`**${api}/comparables`, () => new Promise(() => {}));
  if (!estimate) await page.route(`**${api}/estimate`, () => new Promise(() => {}));
  await page.goto(`/packages/${encodeURIComponent(ref)}${options.evidence ? `?evidence=${encodeURIComponent(ICR_54)}` : ""}`);
}

const section = (page: Page) => page.locator("[data-past-range]");
// A page whose time estimate answers: ready waits for lane 2 too, so nothing moves after a test measures the chart.
const answering = new WeakSet<Page>();
// Fonts too: a face that came late on a busy computer broke a date onto two lines after the measure (ticket 56).
const ready = async (page: Page) => {
  await expect(page.locator("[data-past-range]:not([data-past-range=loading])")).toBeVisible();
  if (answering.has(page)) await expect(page.locator("[data-lane2=loading]")).toHaveCount(0);
  await fontsLoaded(page);
};
const readout = (page: Page) => page.locator("[data-readout]");

// How many lines an element's text sits on: its text's boxes, by their tops (ticket 12's review, Standards).
const lineCount = (element: Locator) =>
  element.evaluate((el) => {
    const range = document.createRange();
    range.selectNodeContents(el);
    return new Set([...range.getClientRects()].map((r) => Math.round(r.top))).size;
  });

async function derived(name: string, edit: (body: Comparables) => void): Promise<Answer> {
  const body = JSON.parse(await recorded(name)) as Comparables;
  edit(body);
  return { body: JSON.stringify(body) };
}

// A plan row with no planned dates: no plan, so no share of it either.
const noPlan = (body: Comparables) => {
  body.plan = null;
  (body.frequencies as { plan: unknown }).plan = null;
};

async function signedWithin(months: number): Promise<number> {
  const body = JSON.parse(await recorded("comparables-ke-nwwda-541055.json")) as Comparables;
  return body.rows.filter((row) => !row.still_open && row.months <= months).length;
}

async function axe(page: Page) {
  const results = await scan(page);
  return results.violations.map((v) => `${v.id}: ${v.nodes.map((node) => node.target.join(" ")).join(", ")}`);
}

test("the workspace names the package, lists its facts in STEP's field names, and states the finding as the chart's title", async ({ page }) => {
  await openPackage(page);
  await ready(page);
  const main = page.getByRole("main");

  await expect(main.getByRole("heading", { level: 1 })).toContainText("Equipping of Exploratory");
  await expect(main.locator("[data-page-head]")).toContainText(REF);
  await expect(page).toHaveTitle(`Package ${REF} | Strata`);
  const crumbs = main.getByRole("navigation", { name: "Breadcrumb" });
  await expect(crumbs.getByRole("link", { name: "Packages" })).toHaveAttribute("href", "/packages");
  // The crumb names the project as Check a plan's crumb and the project's header do, by the server's display_name (the
  // 58 critique, rounds 1 to 3, "one project name").
  await expect(crumbs.getByRole("link", { name: "Water and Sanitation Development (P156634)" })).toHaveAttribute("href", "/projects/P156634");
  await expect(crumbs).not.toContainText("Development Project");
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

  await expect(page.locator("[data-stage-label]").first()).toHaveText("Planning");
  await expect(section(page).getByRole("heading", { level: 2 })).toHaveAccessibleName("How long it took");
  await expect(section(page).locator("[data-finding]")).toHaveText(FINDING);
  await expect(page.getByRole("figure", { name: FINDING })).toBeVisible();
  await expect(section(page).locator("[data-summary]")).toHaveText(
    "The middle half of these packages took 3.3 to 7.9 months, and the middle one took 4.4. 8 in 10 were signed within 9.1 months. " +
      "Four of the 49 are still open. I kept them in the range as not signed yet, so the range does not look shorter than it was. " +
      // Lane 2 (ticket 26): the demo package lies outside what the fixture's model learned from.
      "The past range above still shows every comparable package.",
  );
  await expect(section(page).locator("[data-coverage-line]")).toContainText(
    "Based on 49 of 65 matching packages; three lacked the STEP reference that links notice to contract, 10 had no specific procurement " +
      "notice in the records I hold and three were canceled before a contract was signed.",
  );
  await expect(section(page).locator("[data-coverage-line]").getByRole("link")).toHaveAttribute(
    "href",
    "/data?sources=notices,awards,documents,projects&from=find_comparables",
  );
  await expect(section(page).locator("[data-source]").first()).toContainText("Records run through October 13, 2026.");
});

test("the title states the plan's share in the words find_comparables returned with it", async ({ page }) => {
  // The tool decides the words (CLAUDE.md rule 4); here it says "about" 1 in 10 for the same 2 of 49.
  const about = await derived("comparables-ke-nwwda-541055.json", (body) => {
    body.frequencies = { q80: [8, 10], plan: { words: "about", states: [1, 10] } };
  });
  await openPackage(page, { comparables: about });
  await ready(page);
  await expect(section(page).locator("[data-finding]")).toHaveText(
    "2 of 49 comparable packages, about 1 in 10, were signed within the plan's 1.5 months.",
  );
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
    "Two lanes on one month axis from 0 to 18 months. " +
      "Dot chart of 49 comparable packages on a month axis from 0 to 18 months: 45 signed and four still open. The middle half took " +
      `3.3 to 7.9 months, the middle one took 4.4, and 8 in 10 were signed within 9.1. ${OUTSIDE_TRAINING} A line marks 1.5 months, ` +
      "and 2 of 49 were signed within it. I left out the three canceled packages, because a canceled package was never signed and is not still open.",
  );
  // The lane's key writes its counts as the alt text does, one to nine in words (ticket 58).
  await expect(chart).toContainText("45 signed");
  await expect(chart).toContainText("four still open");
  await expect(chart).not.toContainText("4 still open");
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
  // Twenty rows a page (ticket 101): the Yes cells on the three pages add up to the readout's count.
  let yes = 0;
  for (const rows of [20, 20, 9]) {
    await expect(table.locator("tbody tr")).toHaveCount(rows);
    yes += await table.locator("tbody td:last-child").filter({ hasText: /^Yes$/ }).count();
    if (rows === 20) await page.getByRole("button", { name: "Next 20" }).click();
  }
  expect(yes).toBe(await signedWithin(6.5));

  await page.getByRole("button", { name: "Use the plan's 1.5 months" }).click();
  await expect(input).toHaveValue("1.5");
  await expect(input).toBeFocused();
  await expect(readout(page)).toHaveText("2 of 49 signed within 1.5 months");
});

test("a drag gives the slider focus, so the arrow keys nudge the line you just moved", async ({ page }) => {
  await openPackage(page);
  await ready(page);
  const slider = page.getByRole("slider", { name: "Planned months" });
  // The two-lane chart (ticket 26) is 392 px tall, so bring it on screen before the mouse reaches for its knob.
  await page.locator("[data-range-chart]").scrollIntoViewIfNeeded();
  const box = (await page.locator("[data-range-chart]").boundingBox())!;
  const knob = (await slider.boundingBox())!;

  await page.mouse.move(knob.x + knob.width / 2, knob.y + knob.height / 2);
  await page.mouse.down();
  await page.mouse.move(box.x + 8 + ((box.width - 16) * 6) / 18, knob.y + knob.height / 2, { steps: 4 });
  await page.mouse.up();
  await expect(slider).toHaveAttribute("aria-valuenow", "6");
  await expect(slider).toBeFocused();

  await page.keyboard.press("ArrowRight");
  await expect(slider).toHaveAttribute("aria-valuenow", "6.5");
});

// Ticket 59 (the 12 review, round 11, P1): the chart's row B is measured in Open Sans, so the chart draws only once the
// fonts have loaded; until then its placeholder holds the chart's height, and the chart takes the same height.
test("while the fonts load the chart's place holds its height, and the chart draws once they are in", async ({ page }) => {
  let release!: () => void;
  const held = new Promise<void>((resolve) => (release = resolve));
  await page.route("**/*.woff2", async (route) => {
    await held;
    await route.fallback();
  });
  await openPackage(page, { width: 496 });
  await expect(page.locator("[data-chart-placeholder]")).toBeVisible();
  await expect(page.locator("[data-range-chart]")).toHaveCount(0);
  const placeholder = await page.locator("[data-chart-placeholder]").evaluate((element) => Math.round(element.getBoundingClientRect().height));
  release();
  await expect(page.locator("[data-range-chart]")).toBeVisible();
  await expect(page.locator("[data-chart-placeholder]")).toHaveCount(0);
  expect(await page.locator("[data-range-chart] svg").first().evaluate((svg) => Math.round(svg.getBoundingClientRect().height))).toBe(placeholder);
});

// At 496 and 512 px the chart is just over 400 px wide, so the readout is one line only where one line
// fits beside a line in the middle of the plot.
test("at narrow widths the readout never crosses the knob, wherever the line sits", async ({ page }) => {
  const overlap = (a: { x: number; y: number; width: number; height: number }, b: typeof a) =>
    a.x < b.x + b.width && b.x < a.x + a.width && a.y < b.y + b.height && b.y < a.y + a.height;
  for (const width of [512, 496, 390, 320]) {
    await openPackage(page, { width });
    await ready(page);
    const input = page.getByRole("textbox", { name: "Planned months" });
    for (const months of ["1.5", "6", "9", "14"]) {
      await input.fill(months);
      await expect(page.getByRole("slider")).toHaveAttribute("aria-valuenow", String(Number(months)));
      // Ticket 59 (design-lead's call on ticket 12's round 11, P1): the chart keeps its height wherever the readout
      // takes two lines, at 496 and 512 px too, because row B's 16 px come out of lane 1. With lane 2 it is 392 px.
      const drawn = await page.locator("[data-range-chart] svg").first().evaluate((svg) => [Math.round(svg.getBoundingClientRect().height), svg.closest("[data-past-range]")!.getAttribute("data-lane2")]);
      // At 320 px the key takes a second line of row A, which DESIGN.md section 6 lets grow.
      if (width >= 390) expect(drawn[0], `${width} px, ${months} months: the chart's height`).toBe(drawn[1] ? 392 : 240);
      // Under 400 px wide, the readout is the copy's two lines wherever the line sits.
      if (width < 400) {
        const within = await signedWithin(Number(months));
        expect(await page.locator("[data-readout] text").allTextContents(), `${width} px, ${months} months`).toEqual([
          `${within} of 49 signed`,
          `within ${Number(months).toFixed(1)} months`,
        ]);
      }
      const knob = (await page.getByRole("slider").boundingBox())!;
      for (const label of await page.locator("[data-readout], [data-readout-plan]").all()) {
        const box = (await label.boundingBox())!;
        expect(overlap(box, knob), `${width} px, ${months} months: "${await label.textContent()}"`).toBe(false);
        // The letters stay inside the chart. Their 3 px surface halo may pass its edge where the readout
        // fits on neither side of the line, as at 320 px and 9 months: the halo's margin goes before the
        // gap to the knob's focus ring.
        const chart = (await page.locator("[data-range-chart]").boundingBox())!;
        const letters = await label.evaluate((text) => {
          const svg = (text as SVGGraphicsElement).ownerSVGElement!.getBoundingClientRect();
          const fill = (text as SVGGraphicsElement).getBBox();
          return { left: svg.left + fill.x, right: svg.left + fill.x + fill.width };
        });
        expect(letters.left, `${width} px, ${months} months`).toBeGreaterThanOrEqual(chart.x - 0.5);
        expect(letters.right, `${width} px, ${months} months`).toBeLessThanOrEqual(chart.x + chart.width + 0.5);
      }
    }
  }
});

test("the plan line never runs through a statistic's label: the label moves off it, or the line stops above it and resumes below", async ({ page }) => {
  for (const width of [1440, 390]) {
    await openPackage(page, { width });
    await ready(page);
    // 10 months sits just past the 8-in-10 point, where a reader drags the line to ask whether 10 would be enough; 4.4
    // and 5 sit on and just past the middle, where ticket 59 re-checked that the middle's label, moved off the line,
    // never stacks over the 8-in-10 label.
    for (const months of ["10", "6", "3.5", "4.4", "5"]) {
      await page.getByRole("textbox", { name: "Planned months" }).fill(months);
      await expect(page.getByRole("slider")).toHaveAttribute("aria-valuenow", String(Number(months)));
      const stacked = await page.evaluate(() => {
        const boxes = [...document.querySelectorAll("[data-chart-drawing] [data-row-c]")].map((label) => label.getBoundingClientRect());
        // Two rows of row C sit 16 px apart, so their letters' boxes may touch by a few pixels; over each other is more.
        return boxes.some((a, i) => boxes.some((b, j) => i < j && a.left < b.right && b.left < a.right && a.top < b.bottom - 6 && b.top < a.bottom - 6));
      });
      expect(stacked, `${width} px, ${months} months: two statistics' labels over each other`).toBe(false);
      // A label the line's x falls inside must sit on its knockout, drawn over the line and wider than the label.
      const through = await page.evaluate(() => {
        const svg = document.querySelector("[data-chart-drawing]")!;
        const x = svg.getBoundingClientRect().x + Number(svg.querySelector("[data-plan-line] line")!.getAttribute("x1"));
        const crossed: string[] = [];
        for (const label of svg.querySelectorAll("[data-row-c]")) {
          const box = label.getBoundingClientRect();
          if (x <= box.left - 1 || x >= box.right + 1) continue;
          const knockout = svg.querySelector(`[data-knockout="${label.getAttribute("data-row-c")}"]`);
          const cover = knockout?.getBoundingClientRect();
          const after = knockout ? svg.querySelector("[data-plan-line]")!.compareDocumentPosition(knockout) & Node.DOCUMENT_POSITION_FOLLOWING : 0;
          const covers = cover && after && cover.left <= box.left && cover.right >= box.right && cover.top <= box.top && cover.bottom >= box.bottom;
          if (!covers) crossed.push(label.textContent ?? "");
        }
        return crossed;
      });
      expect(through, `${width} px, ${months} months`).toEqual([]);
    }
  }
});

test("the statistics' labels and their knockouts stop above the axis, so the axis line runs whole under them", async ({ page }) => {
  for (const comparables of ["comparables-ke-nwwda-541055.json", "comparables-ke-nwwda-541055-any-category.json"]) {
    for (const width of [1440, 1024, 390]) {
      await openPackage(page, { width, comparables: { body: await recorded(comparables) } });
      await ready(page);
      // Both answers draw the middle's and the 8-in-10 point's knockouts, so the check below has two to read, and lane
      // 2's label has its own (ticket 26), which stops above the axis too.
      await expect(page.locator("[data-chart-drawing] :is([data-knockout=middle], [data-knockout=in10])"), `${comparables} at ${width} px`).toHaveCount(2);
      const overlaps = await page.evaluate(() => {
        // The axis is a 1 px line, so its stroke starts half a pixel above its y.
        const axis = document.querySelector("[data-chart-drawing] [data-axis]")!.getBoundingClientRect().top - 0.5;
        return [...document.querySelectorAll("[data-chart-drawing] [data-knockout]")]
          .map((knockout) => [knockout.getAttribute("data-knockout"), knockout.getBoundingClientRect().bottom - axis] as const)
          .filter(([, over]) => over > 0.01);
      });
      expect(overlaps, `${comparables} at ${width} px`).toEqual([]);
    }
  }
});

test("below 768 px the reset button takes the helper's place while the line is off the plan, so the chart sits about 16 px under the control", async ({ page }) => {
  for (const width of [390, 320]) {
    await openPackage(page, { width });
    await ready(page);
    const input = page.getByRole("textbox", { name: "Planned months" });
    const helper = page.getByText(/^The plan row puts the notice on/);
    const chartTop = () => page.locator("[data-range-chart]").evaluate((el) => el.getBoundingClientRect().top + window.scrollY);
    const pageBox = (locator: typeof helper) => locator.evaluate((el) => {
      const box = el.getBoundingClientRect();
      return { top: box.top + window.scrollY, bottom: box.bottom + window.scrollY };
    });
    const inputBox = await pageBox(input);
    const helperBox = await pageBox(helper);
    const before = await chartTop();

    // Ticket 59 (the 12 critique, round 11, item 3): the helper sits right under the input it explains, and the error's
    // held line sits under the helper, so the helper reads as the input's and an error appears between it and the chart.
    expect(helperBox.top - inputBox.bottom, `${width} px`).toBeLessThanOrEqual(8);
    const errorBox = await pageBox(page.locator("[data-plan-control] > p.text-error"));
    expect(errorBox.top, `${width} px: the error's line under the helper`).toBeGreaterThanOrEqual(helperBox.bottom);
    expect(before, `${width} px: and the chart under it`).toBeGreaterThanOrEqual(errorBox.bottom);
    expect(before - helperBox.bottom, `${width} px`).toBeLessThanOrEqual(48);

    await page.getByRole("slider").focus();
    await page.keyboard.press("ArrowRight");
    const reset = page.getByRole("button", { name: "Use the plan's 1.5 months" });
    await expect(reset).toBeVisible();
    await expect(helper).toBeHidden();
    const resetBox = await pageBox(reset);
    expect(Math.abs(resetBox.top - helperBox.top), `${width} px`).toBeLessThanOrEqual(1);
    expect(await chartTop(), `${width} px`).toBe(before);
    // Hidden, the helper still describes the input.
    await expect(input).toHaveAccessibleDescription(/The plan row puts the notice on/);
  }
});

test("from 768 px the reset button sits on the input's row with its focus ring 8 px clear of the word before it", async ({ page }) => {
  for (const width of [1440, 1024, 768]) {
    await openPackage(page, { width });
    await ready(page);
    await page.getByRole("slider").focus();
    await page.keyboard.press("ArrowRight");
    const reset = page.getByRole("button", { name: "Use the plan's 1.5 months" });
    await reset.focus();

    const { gap, ring, sameRow } = await page.evaluate(() => {
      const control = document.querySelector("[data-plan-control]")!;
      const unit = [...control.querySelectorAll("span")].find((span) => span.textContent === "months")!.getBoundingClientRect();
      const button = document.activeElement as HTMLElement;
      const style = getComputedStyle(button);
      const box = button.getBoundingClientRect();
      const input = control.querySelector("input")!.getBoundingClientRect();
      return {
        gap: box.left - unit.right,
        ring: parseFloat(style.outlineOffset) + parseFloat(style.outlineWidth),
        sameRow: box.top < input.bottom && box.bottom > input.top,
      };
    });
    expect(gap - ring, `${width} px`).toBeGreaterThanOrEqual(8);
    expect(sameRow, `${width} px`).toBe(true);
    await expect(page.getByText(/^The plan row puts the notice on/), `${width} px`).toBeVisible();
  }
});

// The readout sits beside the knob in row B, so it keeps clear of the knob's focus ring, on either side
// of the line: right of it at the plan's 1.5 months, and left of it at 14 months. At 320 px with the
// plan at 9 months the readout fits on neither side, so it takes the right, the side with more room,
// and gives up its halo's margin at the plot's edge before its gap to the ring.
test("the plan's readout keeps at least 3 px clear of the slider's focus ring, on either side of the line", async ({ page }) => {
  for (const [width, months, side] of [
    [1440, null, "right"],
    [1440, "14", "left"],
    [390, null, "right"],
    [390, "14", "left"],
    [320, "9", "right"],
  ] as const) {
    const where = `${width} px, ${months ?? "the plan's 1.5"} months`;
    await openPackage(page, { width });
    await ready(page);
    if (months) await page.getByRole("textbox", { name: "Planned months" }).fill(months);
    await page.getByRole("slider").focus();
    const gaps = await page.evaluate(() => {
      const knob = document.activeElement as HTMLElement;
      const style = getComputedStyle(knob);
      const ring = parseFloat(style.outlineOffset) + parseFloat(style.outlineWidth);
      const box = knob.getBoundingClientRect();
      return [...document.querySelectorAll("[data-chart-drawing] :is([data-readout], [data-readout-plan])")].map((text) => {
        const label = text.getBoundingClientRect();
        return [label.left >= box.right ? "right" : "left", label.left >= box.right ? label.left - (box.right + ring) : box.left - ring - label.right] as const;
      });
    });
    expect(gaps.length, where).toBeGreaterThan(0);
    expect(gaps.map(([found]) => found), where).toContain(side);
    for (const [, gap] of gaps) expect(gap, where).toBeGreaterThanOrEqual(3);
  }
});

test("moving the line or typing a bad number moves nothing else on the page", async ({ page }) => {
  for (const width of [320, 390, 1440]) {
    await openPackage(page, { width });
    await ready(page);
    // The chart's top on the page, wherever the page is scrolled.
    const top = () => page.locator("[data-range-chart]").evaluate((el) => el.getBoundingClientRect().top + window.scrollY);
    const before = await top();

    await page.getByRole("slider").focus();
    await page.keyboard.press("ArrowRight");
    await expect(page.getByRole("button", { name: "Use the plan's 1.5 months" })).toBeVisible();
    expect(await top(), `${width} px, after ArrowRight`).toBe(before);

    await page.getByRole("textbox", { name: "Planned months" }).fill("abc");
    await expect(page.getByRole("textbox", { name: "Planned months" })).toHaveAttribute("aria-invalid", "true");
    expect(await top(), `${width} px, after a bad number`).toBe(before);
  }
});

test("below 768 px the table's cards say what Months counts once, on the count line's row, not in every card", async ({ page }) => {
  const definition = "Months run from notice to signature, or so far if still open.";
  await openPackage(page, { width: 390 });
  await ready(page);
  await section(page).getByRole("button", { name: "Show the table" }).click();
  const cards = page.locator("[data-comparables-table] [data-table-view=cards]");

  // Twenty a page (ticket 101).
  await expect(cards.locator("li")).toHaveCount(20);
  await expect(cards).not.toContainText("so far if still open");
  await expect(page.locator("[data-comparables-table]").getByText(definition, { exact: true })).toBeVisible();
  // The definition is its own element beside the count, never run on into the count's sentence.
  await expect(page.locator("[data-comparables-table] p[data-numbers]").first()).toHaveText("Showing 1 to 20 of 49 packages.");

  // At 1024 px the zones take the whole frame beside the rail, so the table's frame has its 49rem and shows its rows.
  await page.setViewportSize({ width: 1024, height: 900 });
  await expect(page.locator("[data-comparables-table]").getByText(definition, { exact: true })).toBeHidden();
  await expect(page.locator("[data-comparables-table] thead")).toContainText("From notice to signature, or so far if still open");
});

test("a number that is not between 0.5 and 60 months leaves the line where it was and says why", async ({ page }) => {
  await openPackage(page);
  await ready(page);
  const input = page.getByRole("textbox", { name: "Planned months" });

  await input.fill("90");

  await expect(input).toHaveAttribute("aria-invalid", "true");
  await expect(section(page).getByText("Type months from 0.5 to 60.", { exact: true })).toBeVisible();
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
  // Its name says what its tooltip shows (ticket 96): reference, months, its sentence with full dates, where it came
  // from and what Enter does.
  const from = "From Procurement Notices and Contract Awards, through October 13, 2026.";
  await expect(first).toHaveAccessibleName(
    "KE-MIGORI COUNTY-532367-CW-RFB, 0.4 months. Kenya. Its notice was published October 9, 2026, and the records I hold show no " +
      `signed contract. ${from} Select to see its records. Dot 1 of 49.`,
  );
  const tip = page.locator("[data-dot-tooltip]");
  await expect(tip).toContainText("KE-MIGORI COUNTY-532367-CW-RFB");

  await page.keyboard.press("ArrowRight");
  await page.keyboard.press("ArrowRight");
  await page.keyboard.press("ArrowRight");
  const fourth = group.getByRole("img").nth(3);
  await expect(fourth).toBeFocused();
  await expect(fourth).toHaveAccessibleName(
    "KE-WAJWASCO-372776-CW-RFB, 1.1 months. Kenya. Its notice was published September 2, 2023, and its contract was signed " +
      `October 6, 2023. ${from} Select to see its records. Dot 4 of 49.`,
  );
  // The country leads the line, so the notice is not read as published in Kenya.
  await expect(tip).toContainText("Kenya. Its notice was published September 2, 2023, and its contract was signed October 6, 2023.");

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

async function centre(page: Page, selector: string) {
  const box = (await page.locator(selector).boundingBox())!;
  return { x: box.x + box.width / 2, y: box.y + box.height / 2, top: box.y };
}

test("a tooltip opened first on the last dot keeps its own width and sits above the dot", async ({ page }) => {
  for (const width of [1440, 390]) {
    await openPackage(page, { width });
    await ready(page);
    await page.locator("[data-range-chart]").scrollIntoViewIfNeeded();
    const last = await centre(page, "[data-dot-target='48']");

    await page.mouse.move(last.x, last.y);

    const tip = page.locator("[data-dot-tooltip]");
    await expect(tip).toContainText("KE-");
    const box = (await tip.boundingBox())!;
    expect(box.width, `${width} px`).toBeGreaterThanOrEqual(200);
    expect(box.y + box.height, `${width} px`).toBeLessThanOrEqual(last.top);
  }
});

test("a dot's tooltip never covers another dot, so moving from dot to dot always shows the dot under the pointer", async ({ page }) => {
  await openPackage(page, { width: 390 });
  await ready(page);
  await page.locator("[data-range-chart]").scrollIntoViewIfNeeded();
  const name = async (index: number) =>
    (await page.locator(`[data-dot-target='${index}']`).getAttribute("aria-label"))!.split(",")[0];
  const tip = page.locator("[data-dot-tooltip]");
  // The centre of every dot the tooltip lies over: none, wherever the pointer opened it.
  const covered = () =>
    page.evaluate(() =>
      [...document.querySelectorAll("[data-dot-target]")].filter((dot) => {
        const r = dot.getBoundingClientRect();
        return document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2)?.closest("[data-dot-tooltip]") !== null;
      }).length,
    );

  for (let index = 0; index < 49; index += 3) {
    const here = await centre(page, `[data-dot-target='${index}']`);
    await page.mouse.move(here.x, here.y);
    await expect(tip).toContainText(await name(index));
    expect(await covered(), `dot ${index}`).toBe(0);
  }
  // Two dots stacked in one column at this width: the pointer moves straight up from one to the other.
  const pair = await page.evaluate(() => {
    const boxes = [...document.querySelectorAll("[data-dot-target]")].map((dot) => dot.getBoundingClientRect());
    for (let i = 0; i < boxes.length; i++)
      for (let j = 0; j < boxes.length; j++)
        if (Math.abs(boxes[i].x - boxes[j].x) < 4 && boxes[j].y < boxes[i].y - 4) return [i, j];
    return null;
  });
  expect(pair).not.toBeNull();
  const [from, to] = pair!;
  const a = await centre(page, `[data-dot-target='${from}']`);
  const b = await centre(page, `[data-dot-target='${to}']`);
  await page.mouse.move(a.x, a.y);
  await expect(tip).toContainText(await name(from));
  await page.mouse.move(b.x, b.y, { steps: 4 });
  await page.waitForTimeout(300);
  await expect(tip).toContainText(await name(to));
});

test("a dot's tooltip stays while the pointer moves onto it, so you can select its reference, and hides when the pointer leaves both", async ({ page }) => {
  for (const width of [1440, 390]) {
    await openPackage(page, { width });
    await ready(page);
    await page.locator("[data-range-chart]").scrollIntoViewIfNeeded();
    const last = await centre(page, "[data-dot-target='48']");
    const tip = page.locator("[data-dot-tooltip]");
    await page.mouse.move(last.x, last.y);
    await expect(tip).toContainText("KE-");

    // WCAG 2.2, 1.4.13: content shown on hover stays while the pointer moves over it.
    const box = (await tip.boundingBox())!;
    await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2, { steps: 8 });
    await page.waitForTimeout(500);
    await expect(tip, `${width} px`).toBeVisible();
    await page.mouse.move(box.x + box.width / 2 + 3, box.y + box.height / 2 + 2);
    await page.waitForTimeout(300);
    await expect(tip, `${width} px`).toBeVisible();
    expect(await tip.evaluate((el) => getComputedStyle(el).userSelect), `${width} px`).not.toBe("none");

    // Leaving the tooltip and the dot hides it.
    await page.mouse.move(box.x + box.width / 2, box.y - 60, { steps: 4 });
    await expect(tip, `${width} px`).toHaveCount(0);
  }
});

// Stops the page's clock once the chart is ready. A dot takes the tooltip once the pointer has rested on it for 100 ms
// (RangeChart.tsx), so a test that moves the pointer every 16 ms advances the page's clock 16 ms between two moves,
// with runFor, and a busy computer's pause between them never counts as a rest. With the time between moves left to
// the computer, these tests failed gates at load averages of 26 to 51 and passed alone (ticket 56). The clock must be
// installed before the page loads, so the page's timers are the clock's; clock.resume() lets a new page load.
async function stopTheClock(page: Page) {
  const now = await page.evaluate(() => Date.now());
  await page.clock.pauseAt(now + 1000);
}

// The dots of the tallest column at this width, top first: the column where a dot's tooltip sits
// furthest above it, past every dot stacked over it.
async function tallestColumn(page: Page): Promise<number[]> {
  return page.evaluate(() => {
    const columns = new Map<number, { index: number; y: number }[]>();
    document.querySelectorAll<HTMLElement>("[data-dot-target]").forEach((dot) => {
      const box = dot.getBoundingClientRect();
      const x = Math.round(box.x + box.width / 2);
      columns.set(x, [...(columns.get(x) ?? []), { index: Number(dot.dataset.dotTarget), y: box.y }]);
    });
    const tallest = [...columns.values()].sort((a, b) => b.length - a.length)[0];
    return tallest.sort((a, b) => a.y - b.y).map((dot) => dot.index);
  });
}

test("the pointer can cross the dots above a dot to reach its tooltip, and a dot it rests on takes the tooltip", async ({ page }) => {
  await page.clock.install();
  for (const width of [1440, 390]) {
    await page.clock.resume();
    await openPackage(page, { width });
    await ready(page);
    await page.locator("[data-range-chart]").scrollIntoViewIfNeeded();
    await stopTheClock(page);
    const column = await tallestColumn(page);
    expect(column.length, `${width} px`).toBeGreaterThanOrEqual(3);
    const bottom = column[column.length - 1];
    const name = async (index: number) =>
      (await page.locator(`[data-dot-target='${index}']`).getAttribute("aria-label"))!.split(",")[0];
    const tip = page.locator("[data-dot-tooltip]");

    // From the bottom dot straight to the nearest point of its tooltip, 2 px every 16 ms.
    const from = await centre(page, `[data-dot-target='${bottom}']`);
    await page.mouse.move(from.x, from.y);
    await expect(tip).toContainText(await name(bottom));
    const box = (await tip.boundingBox())!;
    const to = { x: Math.min(Math.max(from.x, box.x + 4), box.x + box.width - 4), y: box.y + box.height - 2 };
    const steps = Math.ceil(Math.hypot(to.x - from.x, to.y - from.y) / 2);
    for (let step = 1; step <= steps; step++) {
      await page.mouse.move(from.x + ((to.x - from.x) * step) / steps, from.y + ((to.y - from.y) * step) / steps);
      await page.clock.runFor(16);
    }
    await page.clock.runFor(400);
    await expect(tip, `${width} px, on arrival`).toContainText(await name(bottom));

    // From the same dot onto the dot above it, resting there: that dot takes the tooltip.
    await page.mouse.move(2, from.y, { steps: 4 });
    await page.clock.runFor(150);
    await expect(tip).toHaveCount(0);
    await page.mouse.move(from.x, from.y);
    await expect(tip).toContainText(await name(bottom));
    const above = await centre(page, `[data-dot-target='${column[column.length - 2]}']`);
    await page.mouse.move(above.x, above.y, { steps: 4 });
    await page.clock.runFor(150);
    await expect(tip, `${width} px, resting on the dot above`).toContainText(await name(column[column.length - 2]));

    // Escape pressed before that rest is over hides the tooltip, and no dot takes it after.
    await page.mouse.move(from.x, from.y, { steps: 4 });
    await expect(tip).toContainText(await name(bottom));
    await page.mouse.move(above.x, above.y, { steps: 4 });
    await page.keyboard.press("Escape");
    await page.clock.runFor(150);
    await expect(tip, `${width} px, after Escape`).toHaveCount(0);
  }
});

// Every dot's centre and reference in the viewport, and the lane's centre line, which the middle
// half's band is centred on.
async function swarmGeometry(page: Page) {
  return page.evaluate(() => {
    const band = document.querySelector("[data-band]")!.getBoundingClientRect();
    const dots = [...document.querySelectorAll<HTMLElement>("[data-dot-target]")].map((dot) => {
      const box = dot.getBoundingClientRect();
      return { x: box.x + box.width / 2, y: box.y + box.height / 2, name: dot.getAttribute("aria-label")!.split(",")[0] };
    });
    return { centre: band.y + band.height / 2, dots };
  });
}

// The dot a pointer at (x, y) answers to: the nearest one within 12 px of it (DESIGN.md section 5).
function within12(dots: { x: number; y: number; name: string }[], x: number, y: number) {
  let best: (typeof dots)[number] | null = null;
  let distance = 12;
  for (const dot of dots) {
    const d = Math.hypot(dot.x - x, dot.y - y);
    if (d <= distance) [best, distance] = [dot, d];
  }
  return best;
}

// A sweep from left of the swarm to right of it, 3 px every 16 ms, dy px from the lane's centre. The
// page notes the tooltip's header as each move arrives, so each move's reading is the tooltip 16 ms
// after the move before it, with no round trip between moves. While the pointer is within 12 px of a
// dot, it returns the longest run of readings in a row that named another dot.
async function sweep(page: Page, dy: number) {
  const { centre, dots } = await swarmGeometry(page);
  const start = Math.min(...dots.map((dot) => dot.x)) - 16;
  const end = Math.max(...dots.map((dot) => dot.x)) + 16;
  const y = centre + dy;
  await page.mouse.move(start, y);
  await expect(page.locator("[data-dot-tooltip]")).toHaveCount(0);
  await page.evaluate(() => {
    const seen: (string | null)[] = ((window as unknown as { seen: (string | null)[] }).seen = []);
    window.addEventListener("pointermove", () => seen.push(document.querySelector("[data-dot-tooltip] p")?.textContent ?? null), { capture: true });
  });
  const xs: number[] = [];
  let next = performance.now();
  for (let x = start; x <= end; x += 3) {
    await page.mouse.move(x, y);
    xs.push(x);
    next += 16;
    await new Promise((resolve) => setTimeout(resolve, Math.max(0, next - performance.now())));
  }
  await page.mouse.move(end + 3, y);
  const seen = await page.evaluate(() => (window as unknown as { seen: (string | null)[] }).seen);
  let wrong = 0;
  let longest = { steps: 0, at: "" };
  xs.forEach((x, index) => {
    const under = within12(dots, x, y);
    const shown = seen[index + 1];
    wrong = under === null || shown === under.name ? 0 : wrong + 1;
    if (wrong > longest.steps) longest = { steps: wrong, at: `on ${under!.name}, the tooltip named ${shown}` };
  });
  return longest;
}

for (const width of [1440, 390]) {
  for (const [side, dy] of [["above", -9], ["below", 9]] as const) {
    test(`at ${width} px, a pointer sweeping along the dots 9 px ${side} the lane's centre shows the dot under it within 48 ms`, async ({ page }) => {
      await openPackage(page, { width });
      await ready(page);
      await page.locator("[data-range-chart]").scrollIntoViewIfNeeded();
      const longest = await sweep(page, dy);
      // Three readings are 48 ms.
      expect(longest.steps, longest.at).toBeLessThanOrEqual(3);
    });
  }
}

test("a pointer that takes a dot from below its centre keeps it on the way up to its tooltip", async ({ page }) => {
  await page.clock.install();
  await openPackage(page, { width: 1024 });
  await ready(page);
  await page.locator("[data-range-chart]").scrollIntoViewIfNeeded();
  await stopTheClock(page);
  const { dots } = await swarmGeometry(page);
  const tip = page.locator("[data-dot-tooltip]");
  // Starts 3 px right of and 7 px below a dot, where the first 2 px up is nearer another dot.
  const starts = dots
    .map((dot) => ({ x: dot.x + 3, y: dot.y + 7 }))
    .filter((s) => {
      const first = within12(dots, s.x, s.y);
      const next = within12(dots, s.x, s.y - 2);
      return first !== null && next !== null && next !== first && first.y < s.y;
    });
  expect(starts.length).toBeGreaterThanOrEqual(1);

  for (const from of starts) {
    const taken = within12(dots, from.x, from.y)!.name;
    await page.mouse.move(2, from.y + 60);
    await page.clock.runFor(150);
    await expect(tip).toHaveCount(0);
    await page.mouse.move(from.x, from.y);
    await expect(tip).toContainText(taken);
    const box = (await tip.boundingBox())!;
    const to = { x: Math.min(Math.max(from.x, box.x + 4), box.x + box.width - 4), y: box.y + box.height - 2 };
    const steps = Math.ceil(Math.hypot(to.x - from.x, to.y - from.y) / 2);
    for (let step = 1; step <= steps; step++) {
      await page.mouse.move(from.x + ((to.x - from.x) * step) / steps, from.y + ((to.y - from.y) * step) / steps);
      await page.clock.runFor(16);
    }
    await page.clock.runFor(200);
    await expect(tip, `from below ${taken}`).toContainText(taken);
  }
});

test.describe("on a touch screen", () => {
  test.use({ hasTouch: true });

  test("a tapped dot keeps its details until you tap somewhere else", async ({ page }) => {
    await openPackage(page, { width: 390 });
    await ready(page);
    await page.locator("[data-range-chart]").scrollIntoViewIfNeeded();
    const dot = await centre(page, "[data-dot-target='3']");

    await page.touchscreen.tap(dot.x, dot.y);
    await page.waitForTimeout(500);
    await expect(page.locator("[data-dot-tooltip]")).toContainText("KE-WAJWASCO-372776-CW-RFB");

    const heading = await centre(page, "[data-finding]");
    await page.touchscreen.tap(heading.x, heading.y);
    await expect(page.locator("[data-dot-tooltip]")).toHaveCount(0);
  });
});

test("above 60 comparables the lane draws 20 quantile dots, and the table still lists every package 20 at a time", async ({ page }) => {
  await openPackage(page, { comparables: { body: await recorded("comparables-ke-nwwda-541055-any-category.json") } });
  await ready(page);

  await expect(page.locator("[data-chart-drawing] [data-dot]")).toHaveCount(20);
  await expect(page.getByRole("group", { name: /^20 dots, each 1 in 20 of the 103 comparable packages$/ })).toBeVisible();
  // Open packages are not drawn one by one here, so the key states their count in words, with no hollow glyph.
  const chart = page.locator("[data-chart-drawing]");
  // The subtitle says what a dot is, once: the key under the lane does not repeat it (ticket 58).
  await expect(section(page)).toContainText("Each dot is 1 in 20 of the 103 packages, placed by the months");
  await expect(chart).not.toContainText("Each dot is 1 in 20");
  await expect(chart).toContainText("Eight still open.");
  await expect(chart.locator(":scope > circle")).toHaveCount(0);
  await section(page).getByRole("button", { name: "Show the table" }).click();
  await expect(page.locator("[data-comparables-table] table tbody tr")).toHaveCount(20);
  await expect(page.locator("[data-comparables-table]")).toContainText("Showing 1 to 20 of 103 packages");
  await page.getByRole("button", { name: "Next 20" }).click();
  await expect(page.locator("[data-comparables-table]")).toContainText("Showing 21 to 40 of 103 packages");
});

test("a quantile dot the curve never reached is pinned at the plot's edge, so the axis stays readable", async ({ page }) => {
  for (const width of [1440, 390]) {
    await openPackage(page, { width, comparables: { body: await recorded("comparables-ke-nwwda-541055-any-category.json") } });
    await ready(page);
    const chart = page.locator("[data-chart-drawing]");

    // The 20th dot is past its last follow-up, so it sits at the edge with a chevron and keeps its months in its name.
    await expect(chart.locator("[data-beyond]")).toHaveCount(1);
    // Its name ends as its tooltip does (ticket 96): where it came from, and what Enter does.
    await expect(page.locator("[data-dot-target='19']")).toHaveAccessibleName(
      /sits past \d+\.\d months\. From Procurement Notices and Contract Awards, through \w+ \d+, \d{4}\. Select to list the packages it stands for\.$/,
    );
    const labels = await chart.locator("[data-tick-label]").evaluateAll((elements) =>
      elements.filter((el) => el.getAttribute("opacity") !== "0").map((el) => el.getBoundingClientRect()).map((r) => [r.left, r.right]),
    );
    expect(labels.length, `${width} px`).toBeLessThanOrEqual(width < 768 ? 5 : 6);
    for (let i = 1; i < labels.length; i++) expect(labels[i][0], `${width} px, label ${i}`).toBeGreaterThan(labels[i - 1][1]);
    const band = (await chart.locator("[data-band]").boundingBox())!;
    expect(band.width, `${width} px`).toBeGreaterThanOrEqual(40);
    // The key never runs past the chart's right edge.
    const box = (await page.locator("[data-range-chart]").boundingBox())!;
    for (const text of await chart.locator("text").all()) {
      const r = (await text.boundingBox())!;
      if (r.width > 0) expect(r.x + r.width, `${width} px: ${await text.textContent()}`).toBeLessThanOrEqual(box.x + box.width + 0.5);
    }
  }
});

// Ticket 111: Strata's own words open with its byline, and a record's words end with their source. On this page the
// byline sits over section 1's finding alone: "Strata found", or "Strata held back" over its abstention, 8 px above
// the words, outside the finding's own heading.
test("section 1's finding opens with Strata's byline, its abstention with Strata held back, and nothing else on the page has one", async ({ page }) => {
  await openPackage(page);
  await ready(page);
  const bylines = page.locator("[data-byline]");
  await expect(bylines).toHaveText(["Strata found"]);
  await expect(section(page).locator("[data-finding]")).toHaveText(FINDING);
  const [over, under] = [(await bylines.boundingBox())!, (await section(page).locator("[data-finding]").boundingBox())!];
  expect(Math.round(under.y - (over.y + over.height))).toBe(8);

  await openPackage(page, {
    comparables: { body: await recorded("comparables-ke-nwwda-541055-prior.json") },
    estimate: { body: await recorded("estimate-ke-nwwda-541055-prior.json") },
  });
  await ready(page);
  await expect(section(page).locator("[data-finding]")).toHaveText("I'm not giving a range from only seven comparable packages. Here are all seven.");
  await expect(bylines).toHaveText(["Strata held back"]);
});

// Ticket 59, item 59, as the design review of round 1 settled it: on the 0 to 12 axis under 400 px wide, where the label
// "9" would come within 8 px of "12 months", every second tick from 0 is labeled instead (0, 6, 12 months), and every
// tick and gridline stays, so no gridline is left with a lone missing label. At 390 px all five labels fit today.
for (const [width, labels] of [
  [390, ["0", "3", "6", "9", "12 months"]],
  [320, ["0", "6", "12 months"]],
] as const) {
  test(`at ${width} px the 0 to 12 axis labels ${labels.length === 5 ? "every tick" : "every second tick from 0"} and keeps every tick`, async ({ page }) => {
    await openPackage(page, {
      width,
      comparables: { body: await recorded("comparables-ke-nwwda-541055-prior.json") },
      estimate: { body: await recorded("estimate-ke-nwwda-541055-prior.json") },
    });
    await ready(page);
    const chart = page.locator("[data-chart-drawing]");
    const shown = await chart.locator("[data-tick-label]").evaluateAll((elements) =>
      elements.filter((el) => el.getAttribute("opacity") !== "0").map((el) => el.textContent),
    );
    expect(shown).toEqual(labels);
    await expect(chart.locator("[data-tick-label]")).toHaveCount(5);
  });
}

test("below 20 comparables there is no range and no share: the copy file's sentence, every package, and the table open", async ({ page }) => {
  await openPackage(page, {
    comparables: { body: await recorded("comparables-ke-nwwda-541055-prior.json") },
    estimate: { body: await recorded("estimate-ke-nwwda-541055-prior.json") },
  });
  await ready(page);

  // The finding: the first-person sentence that holds back (ticket 101).
  await expect(section(page).locator("[data-finding]")).toHaveText(
    "I'm not giving a range from only seven comparable packages. Here are all seven.",
  );
  await expect(page.locator("[data-chart-drawing] [data-dot]")).toHaveCount(7);
  await expect(page.locator("[data-chart-drawing] :is([data-band], [data-middle], [data-in10])")).toHaveCount(0);
  await expect(section(page)).not.toContainText(/in 10|percent|%/);
  await expect(readout(page)).toHaveText("0 of 7 signed within 1.5 months");
  await expect(section(page).getByRole("button", { name: "Hide the table" })).toHaveAttribute("aria-expanded", "true");
  await expect(page.locator("[data-comparables-table] table tbody tr")).toHaveCount(7);
  // DESIGN.md section 7, rule 12: one to nine in words, in the caption as in the title.
  await expect(page.locator("[data-comparables-table] [data-table-caption]")).toHaveText("All seven comparable packages, shortest first.");
  // With none still open, the text alternative names only the signed ones.
  await expect(page.locator("[data-chart-alt]")).toHaveText(
    "Two lanes on one month axis from 0 to 12 months. " +
      "Dot chart of seven comparable packages on a month axis from 0 to 12 months: seven signed. I'm not giving a range for so few. " +
      "I'm not giving a time estimate for so few. A line marks 1.5 months, and 0 of 7 were signed within it.",
  );
});

test("when packages matched but none could be measured, the reasons say how many of them, with no count of none used", async ({ page }) => {
  await openPackage(page, { comparables: { body: await recorded("comparables-ke-nwwda-541055-non-consulting.json") } });
  await ready(page);

  await expect(section(page).getByRole("heading", { level: 3 }).first()).toHaveText(
    "Six past packages matched this one, but I can't measure how long any of them took.",
  );
  await expect(section(page).locator("[data-coverage-line]")).toContainText(
    "Of the six, two lacked the STEP reference that links notice to contract and four had no specific procurement notice in the records I hold.",
  );
  await expect(section(page)).not.toContainText("Based on");
  await expect(section(page).getByRole("link", { name: /^See Data readiness/ })).toBeVisible();
  // The count of matching packages can be checked; the counts of what they lacked are plain words, since the sentence
  // says what each one counts and a shared tooltip would say the same of all three (ticket 96).
  const line = section(page).locator("[data-coverage-line]");
  await expect(line.getByRole("button")).toHaveText(["six"]);
  await line.getByRole("button", { name: "six" }).hover();
  await expect(page.getByRole("tooltip").locator("[data-num-what]")).toHaveText("Past packages that matched the criteria.");
});

test("a package with no public notice quotes its Market Approach and offers the way back to the plan check", async ({ page }) => {
  await openPackage(page, { ref: "KE-NWWDA-541062-CW-RFQ" });
  await ready(page);

  await expect(section(page)).toContainText(
    'I measure it from the specific procurement notice to the signed contract. Packages with the Market Approach "Limited - National" had ' +
      "no public notice to start from.",
  );
  await expect(section(page).getByRole("link", { name: "Back to the plan check" })).toHaveAttribute(
    "href",
    "/projects/P156634/procurement/northern-water-works-development-agency/2026-10-09#KE-NWWDA-541062-CW-RFQ",
  );
});

test("when the whole page fails, the reference is the heading and is not repeated under it", async ({ page }) => {
  await openPackage(page, { pkg: { status: 503, body: SERVICE_DOWN } });
  await expect(page.locator("main h1")).toHaveText(REF);

  // The head has no ID line under the h1, and its alert slot holds the page's error with Try again (ticket 101).
  await expect(page.locator("[data-page-head] [data-id-line]")).toHaveCount(0);
  await expect(page.locator("[data-page-head] [data-head-alert]")).toContainText("I couldn't load this package.");
  await expect(page.locator("[data-page-head] [data-head-alert]").getByRole("button", { name: "Try again" })).toBeVisible();
});

// Ticket 58 (the 12 critique, round 11): the no-match state's link and the coverage line's name Data readiness the same
// way, so one screen never calls the page two names. No recording matches nothing, so the past range's answer is
// emptied in memory.
test("with no comparable package the link names Data readiness as the coverage line does", async ({ page }) => {
  const none = JSON.parse(await recorded("comparables-ke-nwwda-541055.json"));
  none.rows = [];
  none.abstention = { reason: "no_comparables" };
  await openPackage(page, { comparables: { body: JSON.stringify(none) } });

  await expect(section(page)).toContainText("No past package matched this one, so I have nothing to compare it with.");
  await expect(section(page).getByRole("link", { name: "See Data readiness for these sources" })).toBeVisible();
  await expect(section(page)).not.toContainText("Open Data readiness");
});

test("a reference no plan lists stays whole in the not-found sentence at phone width", async ({ page }) => {
  await openPackage(page, { width: 390, pkg: { status: 404, body: '{"code":"unknown_package"}' } });
  const reference = page.locator("main p", { hasText: "No package in Strata has the reference" }).locator(".font-mono");

  await expect(reference).toHaveText(REF);
  // The lines its text sits on: one.
  expect(await lineCount(reference)).toBe(1);
  // The next step is the box, which opens a project by its ID or name (ticket 58).
  await expect(page.locator("main p", { hasText: "No package in Strata has the reference" })).toContainText(
    "Check the reference in STEP, or find its project in the box at the bottom of the page.",
  );
});

test("a reference too long for the line breaks after a hyphen, so the not-found page never scrolls sideways at 320 px", async ({ page }) => {
  const long = "KE-NWWDA-541055-CW-RFB-LOT-0001-2026-ABC";
  expect(long).toHaveLength(40);
  for (const width of [320, 390]) {
    await openPackage(page, { width, ref: long, pkg: { status: 404, body: '{"code":"unknown_package"}' } });
    const sentence = page.locator("main p", { hasText: "No package in Strata has the reference" });
    await expect(sentence.locator(".font-mono").first()).toHaveText(long);

    await page.evaluate(() => document.fonts.ready);
    expect(await page.evaluate(() => document.documentElement.scrollWidth), `${width} px`).toBeLessThanOrEqual(width);
    // The sentence's lines as the reader sees them, one string per line. A character's top depends on
    // its font, so the full stop in Open Sans and a mono digit on one line can sit a pixel apart: a
    // character joins the line whose top is within 6 px of its own.
    const lines = await sentence.evaluate((p) => {
      const rows = new Map<number, string>();
      const walker = document.createTreeWalker(p, NodeFilter.SHOW_TEXT);
      for (let node = walker.nextNode(); node; node = walker.nextNode()) {
        for (let i = 0; i < node.textContent!.length; i++) {
          const range = document.createRange();
          range.setStart(node, i);
          range.setEnd(node, i + 1);
          const rect = range.getBoundingClientRect();
          if (rect.width === 0) continue;
          const top = [...rows.keys()].find((line) => Math.abs(line - rect.top) < 6) ?? rect.top;
          rows.set(top, (rows.get(top) ?? "") + range.toString());
        }
      }
      return [...rows.entries()].sort((a, b) => a[0] - b[0]).map(([, text]) => text.trim());
    });
    // It breaks after a hyphen: no line starts with one, no line ends inside a run of digits, and the
    // full stop stays with the reference's last part.
    for (const [index, line] of lines.entries()) {
      expect(line.startsWith("-"), `${width} px, line ${index + 1}: ${line}`).toBe(false);
      if (index > 0) expect(/\d$/.test(lines[index - 1]) && /^\d/.test(line), `${width} px: ${lines[index - 1]} | ${line}`).toBe(false);
    }
    expect(lines.some((line) => line.includes("ABC.")), `${width} px: ${lines.join(" | ")}`).toBe(true);
    // A copy of the sentence holds the reference as written.
    await expect(sentence).toContainText(`reference ${long}. Check`);
  }

  // A reference with a county's name breaks at its space first.
  await openPackage(page, { width: 320, ref: "KE-MIGORI COUNTY-532367-CW-RFB", pkg: { status: 404, body: '{"code":"unknown_package"}' } });
  const county = page.locator("main p", { hasText: "No package in Strata has the reference" });
  await expect(county).toContainText("reference KE-MIGORI COUNTY-532367-CW-RFB. Check");
  // The reference's two parts, leaving out the Roboto Mono space between them.
  const parts = county.locator(".font-mono", { hasText: /\S/ });
  const tops = await parts.evaluateAll((elements) =>
    elements.map((part) => [part.textContent, Math.round(part.getBoundingClientRect().top)]),
  );
  expect(tops).toHaveLength(2);
  expect(tops[1][1]).toBeGreaterThan(tops[0][1] as number);
  expect(await parts.nth(1).evaluate((el) => el.getClientRects().length)).toBe(1);
});

// A coverage line's link names the sources behind it and the tool, and never sends an empty value.
// Data readiness now reads an empty value as left out (ticket 16's V1), but the link does not rely on that.
test("each coverage line's link names the sources behind it and find_comparables, and never sends an empty parameter", async ({ page }) => {
  const answers: [string, Answer][] = [
    ["populated", { body: await recorded("comparables-ke-nwwda-541055.json") }],
    ["quantile dots", { body: await recorded("comparables-ke-nwwda-541055-any-category.json") }],
    ["abstention", { body: await recorded("comparables-ke-nwwda-541055-prior.json") }],
    ["none measurable", { body: await recorded("comparables-ke-nwwda-541055-non-consulting.json") }],
    ["no match", { body: await recorded("comparables-ke-nwwda-541055-india.json") }],
    ["no sources", await derived("comparables-ke-nwwda-541055.json", (body) => (body.sources = []))],
  ];
  for (const [name, comparables] of answers) {
    await openPackage(page, { comparables });
    await ready(page);
    const sources = (JSON.parse(comparables.body) as { sources: { key: string }[] }).sources.map((source) => source.key);
    const links = await section(page).locator("a[href^='/data']").evaluateAll((all) => all.map((a) => a.getAttribute("href")!));
    expect(links.length, name).toBeGreaterThanOrEqual(1);
    for (const href of links) {
      const query = new URL(href, "http://strata.test").searchParams;
      expect([...query.entries()].filter(([, value]) => value === ""), `${name}: ${href}`).toEqual([]);
      expect(query.get("from"), `${name}: ${href}`).toBe("find_comparables");
      expect(query.get("sources")?.split(",") ?? [], `${name}: ${href}`).toEqual(sources);
    }
  }
});

// The states the 12 brief lists, each checked with axe at the three widths the review captures.
const SERVICE_DOWN = '{"code":"data_service","trace_id":"0af7651916cd43dd8448eb211c80319c"}';
const STATES: [string, () => Promise<Parameters<typeof openPackage>[1]>][] = [
  ["populated", async () => ({})],
  ["no plan dates", async () => ({ comparables: await derived("comparables-ke-nwwda-541055.json", noPlan) })],
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

test("the page barely moves when the package and then its comparables arrive, at every width", async ({ page }) => {
  // Every layout shift from the first paint, as the browser scores it (CLS).
  await page.addInitScript(() => {
    const seen = ((window as unknown as { shifts: number[] }).shifts = [] as number[]);
    new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) seen.push((entry as unknown as { value: number }).value);
    }).observe({ type: "layout-shift", buffered: true });
  });
  const later = (ms: number, name: string) => async (route: import("@playwright/test").Route) => {
    await new Promise((resolve) => setTimeout(resolve, ms));
    await route.fulfill({ contentType: "application/json", body: await recorded(name) });
  };
  // 600 and 700 sit where the chart's type sizes and the page's 768 px break disagree.
  for (const width of [320, 390, 600, 700, 1024, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    await mockApi(page, { "/api/me": { body: await recorded("me.json") }, "/api/freshness": { body: await recorded("freshness.json") } });
    await page.route(`**${API}`, later(400, "package-ke-nwwda-541055.json"));
    await page.route(`**${API}/comparables`, later(800, "comparables-ke-nwwda-541055.json"));
    // The tracker at the top of the page (ticket 115) holds its place until section 2's steps arrive.
    await page.route(`**${API}/steps`, later(800, "steps-ke-nwwda-541055.json"));

    await page.goto(PATH);
    await ready(page);
    await expect(page.locator("[data-step-tracker] li")).toHaveCount(6);
    await page.waitForTimeout(200);

    const shift = await page.evaluate(() => (window as unknown as { shifts: number[] }).shifts.reduce((a, b) => a + b, 0));
    expect(shift, `${width} px`).toBeLessThan(0.1);
    await page.unrouteAll();
  }
});

test("from 768 px the heading's skeleton holds the Description's two lines, so the page under it stays put when the package arrives", async ({ page }) => {
  for (const width of [1024, 1440]) {
    let answer: () => void = () => {};
    const arrived = new Promise<void>((resolve) => (answer = resolve));
    await openPackage(page, { width, pkg: null, comparables: null });
    await page.unroute(`**${API}`);
    await page.route(`**${API}`, async (route) => {
      await arrived;
      await route.fulfill({ contentType: "application/json", body: await recorded("package-ke-nwwda-541055.json") });
    });
    await page.reload();
    const purpose = page.getByText(/^This page shows how comparable packages went/);
    const held = (await purpose.boundingBox())!.y;

    answer();
    await expect(page.locator("main h1")).toContainText("Equipping of Exploratory");

    expect(Math.abs((await purpose.boundingBox())!.y - held), `${width} px`).toBeLessThanOrEqual(8);
  }
});

// Below 768 px the head holds the demo package's three h1 lines and its facts line's two lines over the 44 px row of
// "Show the plan row", so zone 1 stays put when the package arrives (DESIGN.md section 1, principle 5; ticket 101's
// design review, item 3).
test("below 768 px the head's skeleton holds the package's h1 and facts line, so zone 1 stays put when the package arrives", async ({ page }) => {
  for (const width of [390, 320]) {
    let answer: () => void = () => {};
    const arrived = new Promise<void>((resolve) => (answer = resolve));
    await openPackage(page, { width, height: 844, pkg: null });
    await page.unroute(`**${API}`);
    await page.route(`**${API}`, async (route) => {
      await arrived;
      await route.fulfill({ contentType: "application/json", body: await recorded("package-ke-nwwda-541055.json") });
    });
    await page.reload();
    const top = () => page.locator("[data-zones]").evaluate((el) => el.getBoundingClientRect().top + window.scrollY);
    await expect(page.locator("[data-page-head] [data-facts-line]")).toBeAttached();
    const held = await top();

    answer();
    await expect(page.locator("main h1")).toContainText("Equipping of Exploratory");
    await expect(page.locator("[data-page-head] [data-facts-line] button")).toBeVisible();
    // At 320 px the link back to the project wraps to two lines where the loading head's "Packages" took one, so the
    // loading head holds two below a 20rem page area (ticket 101's design review, round 2, item 13).
    expect(Math.abs((await top()) - held), `${width} px`).toBeLessThanOrEqual(8);
  }
});

test("the section's skeleton holds the chart where the chart arrives, with the summary first below 768 px", async ({ page }) => {
  for (const width of [390, 1440]) {
    let answer: () => void = () => {};
    const arrived = new Promise<void>((resolve) => (answer = resolve));
    await openPackage(page, { width, comparables: null });
    await page.unroute(`**${API}/comparables`);
    await page.route(`**${API}/comparables`, async (route) => {
      await arrived;
      await route.fulfill({ contentType: "application/json", body: await recorded("comparables-ke-nwwda-541055.json") });
    });
    await page.reload();
    const top = (selector: string) => page.locator(selector).evaluate((el) => el.getBoundingClientRect().top + window.scrollY);
    const held = await top("[data-chart-skeleton]");

    answer();
    await ready(page);

    expect(Math.abs((await top("[data-range-chart]")) - held), `${width} px`).toBeLessThanOrEqual(16);
  }
});

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

// DESIGN.md section 4: under the band a page lays out by the page area's width, because the
// evidence drawer narrows it. At 1024 px the rail takes 64 px (ticket 92) and the drawer 40 percent of the window,
// 410 px (ticket 94), which leaves a 550 px page area, so the workspace shows what a 550 px window shows: a head that
// does not stick, the facts in one line (ticket 101), the sentence before the chart, the reset button in the helper's
// place and the table as cards.
test("at 1024 px with the evidence drawer open, the workspace lays out as its page area is wide, not the window", async ({ page }) => {
  await openPackage(page, { width: 1024, evidence: true });
  await ready(page);
  await expect(page.getByRole("dialog")).toBeVisible();
  expect(Math.round((await page.locator("[data-page-column]").boundingBox())!.width)).toBe(550);

  const layout = await page.evaluate(() => {
    const summary = document.querySelector("[data-summary]")!;
    const chart = document.querySelector("[data-chart-figure]")!;
    return {
      summaryFirst: Boolean(summary.compareDocumentPosition(chart) & Node.DOCUMENT_POSITION_FOLLOWING),
      header: getComputedStyle(document.querySelector("[data-page-head]")!).position,
      factsLine: getComputedStyle(document.querySelector("[data-facts-line]")!).display,
      scrollPadding: document.documentElement.style.scrollPaddingTop,
      resets: [...document.querySelectorAll("[data-plan-reset]")].map((el) => getComputedStyle(el).display),
      scrollWidth: document.documentElement.scrollWidth,
    };
  });
  expect(layout.summaryFirst).toBe(true);
  expect(layout.header).not.toBe("sticky");
  // Only the bar sticks, so focus lands 8 px under its 56 px (ticket 94's one hook in the frame).
  expect(layout.scrollPadding).toBe("64px");
  expect(layout.factsLine).toBe("flex");
  // The input row's button is display: none; the helper's place keeps the other.
  expect(layout.resets).toEqual(["none", "block"]);
  expect(layout.scrollWidth).toBeLessThanOrEqual(1024);

  await section(page).getByRole("button", { name: "Show the table" }).click();
  await expect(section(page).locator("[data-table-view=cards]")).toBeVisible();
  await expect(section(page).locator("[data-table-view=table]")).toBeHidden();
});

// At a browser zoom such as 110 percent, the page area beside the drawer can be a fraction of a pixel
// under 768 px. The sentence's place reads the same exact width the container queries read. At 1024 px the
// frame is under 75rem, where the zones take the page area's width (from a frame of 75rem they keep theirs, and
// the summary keeps its place: the drawer test at 1440 and 1280 px).
test("a page area a fraction of a pixel under 768 px puts the sentence first, as the header and facts lay out narrow", async ({ page }) => {
  await openPackage(page, { width: 1024 });
  await ready(page);
  await page.locator("[data-page-column]").evaluate((column) => {
    column.style.flex = "none";
    column.style.width = "767.6px";
  });
  await expect(page.locator("[data-page-head]")).not.toHaveCSS("position", "sticky");
  await expect
    .poll(() =>
      page.evaluate(() => {
        const summary = document.querySelector("[data-summary]")!;
        return Boolean(summary.compareDocumentPosition(document.querySelector("[data-chart-figure]")!) & Node.DOCUMENT_POSITION_FOLLOWING);
      }),
    )
    .toBe(true);
});

// DESIGN.md section 5, Tables: the past range's table needs about 776 px with one line per cell. From a
// page area of 1200 px the workspace keeps to columns 1 to 8, so the table has less room from 1200 to
// about 1411 px than at 1024 px. So it reads its own width: its rows when its frame has 49rem, and cards
// below that. 1416 px is about the narrowest window that shows the table. At 1440 px the drawer leaves an
// 864 px page area, and at 1920 px a 1320 px one; an 834 px window is an iPad held upright.
//
// WCAG 1.4.12, Text Spacing: with a reader's letter spacing of 0.12em, word spacing of 0.16em, line
// height of 1.5 and paragraph spacing of 2em, a cell's text may wrap but must not run into the next
// column.
const TEXT_SPACING =
  "* { letter-spacing: 0.12em !important; word-spacing: 0.16em !important; line-height: 1.5 !important; } p { margin-bottom: 2em !important; }";

// The cells in a table frame whose text runs past their own right edge, and how far the frame scrolls
// sideways.
async function spillOf(frame: Locator) {
  return frame.evaluate((element) => ({
    scroll: element.scrollWidth - element.clientWidth,
    cells: [...element.querySelectorAll("tbody td, tbody th")]
      .filter((cell) => {
        const range = document.createRange();
        range.selectNodeContents(cell);
        return Math.max(...[...range.getClientRects()].map((r) => r.right)) > cell.getBoundingClientRect().right + 0.5;
      })
      .map((cell) => cell.textContent),
  }));
}

test("the past range's table shows its rows where its frame has 49rem, every cell's text inside its cell, and cards where it has less", async ({ page }) => {
  const body = JSON.parse(await recorded("comparables-ke-nwwda-541055.json")) as Comparables;
  // The first page of twenty rows (ticket 101).
  const first = body.rows.slice(0, 20);
  const withoutSpace = first.filter((row) => !row.step_reference.includes(" ")).length;
  // Ticket 101: below a frame of 75rem zone 1 takes the page area's width, so the table's frame has its 49rem from a
  // page area of about 870 px; from that frame the zones keep to the work's columns, under 49rem, so the rows are cards.
  for (const [width, evidence, view] of [
    [1024, false, "table"],
    [1100, false, "table"],
    [960, false, "table"],
    [1200, false, "cards"],
    [1440, false, "cards"],
    [1920, true, "cards"],
    [834, false, "cards"],
  ] as const) {
    const where = `${width} px${evidence ? " beside the drawer" : ""}`;
    // A page area of each width: beside the sidebar (ticket 92) the window is wider.
    await openPackage(page, { width: windowBeside(width), evidence });
    await ready(page);
    await section(page).getByRole("button", { name: "Show the table" }).click();
    const table = section(page).locator("[data-table-view=table]");
    const cards = section(page).locator("[data-table-view=cards]");
    await expect(view === "table" ? table : cards, where).toBeVisible();
    await expect(view === "table" ? cards : table, where).toBeHidden();
    // The zone's foot strip holds the one source line, so the table repeats none of its own (ticket 101's critique).
    await expect(section(page).locator("[data-comparables-table] [data-source]"), where).toHaveCount(0);
    await expect(section(page).locator("[data-foot-strip] [data-source]"), where).toHaveCount(1);
    if (view === "cards") {
      // Inside zone 1's panel the cards are rows divided by a 1 px line, not boxes (DESIGN.md section 5, Tables). The
      // line runs on the text's edges, 12 px in from the row's tint (ticket 101's design review, round 2, item 10).
      const form = await cards.locator(":scope > li").evaluateAll((items) =>
        items.map((item) => {
          const style = getComputedStyle(item);
          const line = getComputedStyle(item, "::before");
          return [style.borderTopLeftRadius, style.borderLeftWidth, style.borderTopWidth, line.height, line.left, line.right].join(" ");
        }),
      );
      expect(form.slice(1).every((f) => f === "0px 0px 0px 1px 12px 12px"), where).toBe(true);
      continue;
    }

    // No cell's text runs past its cell, and the frame does not scroll sideways.
    expect(await spillOf(table), where).toEqual({ scroll: 0, cells: [] });

    // Each cell's text and the lines it sits on, counted by the tops of its text, so a button around a
    // reference (ticket 15's row button, whose padding starts above its text) does not count as a line.
    const lines = (selector: string) =>
      table.locator(selector).evaluateAll((cells) =>
        cells.map((cell) => {
          const tops: number[] = [];
          const walker = document.createTreeWalker(cell, NodeFilter.SHOW_TEXT);
          for (let node = walker.nextNode(); node; node = walker.nextNode()) {
            const range = document.createRange();
            range.selectNodeContents(node);
            tops.push(...[...range.getClientRects()].filter((r) => r.width > 0).map((r) => Math.round(r.top)));
          }
          return [cell.textContent!, new Set(tops).size] as const;
        }),
      );
    // A reference without a space keeps to one line.
    const spaceless = (await lines("tbody th")).filter(([reference]) => !reference.includes(" "));
    expect(spaceless, where).toHaveLength(withoutSpace);
    expect(spaceless.filter(([, count]) => count !== 1), where).toEqual([]);
    // So does each date, in the Notice and Signed columns.
    const dates = await lines("tbody td:nth-child(3), tbody td:nth-child(4)");
    expect(dates.length, where).toBe(2 * first.length);
    expect(dates.filter(([, count]) => count !== 1), `${where}: dates on more than one line`).toEqual([]);

    // With WCAG 1.4.12's text spacing, a cell's text may wrap, but none runs into the next column.
    const spacing = await page.addStyleTag({ content: TEXT_SPACING });
    expect(await spillOf(table), `${where}, with text spacing`).toEqual({ scroll: 0, cells: [] });
    await spacing.evaluate((style) => (style as HTMLStyleElement).remove());
  }
});

// The chart's labels that run past the chart, and the pairs that sit over each other.
async function chartLabels(page: Page) {
  return page.locator("[data-chart-drawing]").evaluate((svg) => {
    const chart = svg.getBoundingClientRect();
    const shown = [...svg.querySelectorAll("text")].filter((text) => text.textContent!.trim() !== "" && getComputedStyle(text).opacity !== "0");
    const boxes = shown.map((text) => ({ text: text.textContent!, box: text.getBoundingClientRect() }));
    return {
      outside: boxes.filter(({ box }) => box.left < chart.left - 0.5 || box.right > chart.right + 0.5).map(({ text }) => text),
      over: boxes.flatMap((a, i) =>
        boxes.slice(i + 1).flatMap((b) => {
          const w = Math.min(a.box.right, b.box.right) - Math.max(a.box.left, b.box.left);
          const h = Math.min(a.box.bottom, b.box.bottom) - Math.max(a.box.top, b.box.top);
          // A 12 px label's font box is 17 px tall, and the key's lines sit 14 px apart, so stacked lines
          // share up to 3 px of their boxes. Labels collide when they share more than 4.
          return w > 0.5 && h > 4 ? [`${a.text} / ${b.text}`] : [];
        }),
      ),
    };
  });
}

// WCAG 1.4.12 at 320 px, the narrowest width the page lays out for (WCAG 1.4.10). A reader's extension
// sets the spacing before the page draws, so the chart measures its labels with it. Each fact's text
// stays inside its column, and each chart label inside the chart, clear of every other label: a label
// wider than the chart takes a second line (DESIGN.md section 6, the range chart).
test("with WCAG 1.4.12's text spacing at 320 px, every fact stays in its column and every chart label inside the chart", async ({ page }) => {
  await page.addInitScript((css) => {
    document.addEventListener("DOMContentLoaded", () => {
      const style = document.createElement("style");
      style.textContent = css;
      document.head.append(style);
    });
  }, TEXT_SPACING);
  for (const [state, comparables] of [
    ["the populated state", "comparables-ke-nwwda-541055.json"],
    ["the quantile state", "comparables-ke-nwwda-541055-any-category.json"],
  ] as const) {
    await openPackage(page, { width: 320, comparables: { body: await recorded(comparables) } });
    await ready(page);
    await page.evaluate(() => document.fonts.ready);
    const facts = await page.locator("[data-package-facts] dd").evaluateAll((values) =>
      values.flatMap((value) => {
        const range = document.createRange();
        range.selectNodeContents(value);
        const box = value.getBoundingClientRect();
        return [...range.getClientRects()].some((r) => r.width > 0 && (r.right > box.right + 0.5 || r.left < box.left - 0.5)) ? [value.textContent] : [];
      }),
    );
    expect(facts, `${state}: facts past their column`).toEqual([]);

    expect(await chartLabels(page), state).toEqual({ outside: [], over: [] });
  }
});

// WCAG 1.4.12 switched on after the chart is drawn, as WCAG's own bookmarklet or an extension turned on
// with the page open does. The chart measures its labels again when their size changes, so every label,
// the axis's included, stays inside the chart and clear of the others.
test("with WCAG 1.4.12's text spacing switched on after the chart is drawn, every chart label still fits inside the chart", async ({ page }) => {
  for (const width of [320, 360]) {
    for (const [state, comparables] of [
      ["the populated state", "comparables-ke-nwwda-541055.json"],
      ["the quantile state", "comparables-ke-nwwda-541055-any-category.json"],
    ] as const) {
      await openPackage(page, { width, comparables: { body: await recorded(comparables) } });
      await ready(page);
      await page.evaluate(() => document.fonts.ready);
      expect(await chartLabels(page), `${width} px, ${state}, before`).toEqual({ outside: [], over: [] });
      await page.addStyleTag({ content: TEXT_SPACING });
      await expect.poll(() => chartLabels(page), { message: `${width} px, ${state}, after`, timeout: 2_000 }).toEqual({ outside: [], over: [] });
    }
  }
});

// WCAG 1.4.12 with the plan line anywhere on the axis. The readout's lines are chosen once for the
// chart's width (DESIGN.md section 6, the range chart), so at every half month its letters stay 3 px
// clear of the knob's focus ring, never span the line and stay inside the chart, and the chart keeps its
// height. One answer is derived with the plan row's own months mid-axis, where "Plan" adds a line above
// the readout; it serves this geometry check only, and no count is read from it.
test("with WCAG 1.4.12's text spacing, the readout keeps clear of the knob at every half month, and the chart keeps its height", async ({ page }) => {
  await page.addInitScript((css) => {
    document.addEventListener("DOMContentLoaded", () => {
      const style = document.createElement("style");
      style.textContent = css;
      document.head.append(style);
    });
  }, TEXT_SPACING);
  const midAxis = await derived("comparables-ke-nwwda-541055.json", (body) => {
    (body.plan as { months: number }).months = 9;
  });
  const prior = { body: await recorded("comparables-ke-nwwda-541055-prior.json") };
  const quantile = { body: await recorded("comparables-ke-nwwda-541055-any-category.json") };
  for (const [where, options] of [
    ["320 px", { width: 320 }],
    ["360 px", { width: 360 }],
    ["560 px", { width: 560 }],
    ["1024 px beside the drawer", { width: 1024, evidence: true }],
    ["320 px in the abstention state", { width: 320, comparables: prior }],
    ["320 px in the quantile state", { width: 320, comparables: quantile }],
    ["320 px with the plan row's months mid-axis", { width: 320, comparables: midAxis }],
  ] as const) {
    await openPackage(page, options);
    await ready(page);
    await page.evaluate(() => document.fonts.ready);
    const problems = await page.locator("[data-range-chart]").evaluate(async (chart) => {
      const knob = chart.querySelector<HTMLElement>("[data-plan-knob]")!;
      knob.focus();
      const ring = parseFloat(getComputedStyle(knob).outlineOffset) + parseFloat(getComputedStyle(knob).outlineWidth);
      const press = async (key: string) => {
        knob.dispatchEvent(new KeyboardEvent("keydown", { key, bubbles: true }));
        await new Promise((resolve) => setTimeout(resolve, 0));
      };
      await press("Home");
      const height = chart.getBoundingClientRect().height;
      const found: string[] = [];
      for (;;) {
        const months = knob.getAttribute("aria-valuenow");
        const svg = chart.querySelector("[data-chart-drawing]")!.getBoundingClientRect();
        const box = knob.getBoundingClientRect();
        const lineX = svg.left + Number(chart.querySelector("[data-plan-line] line")!.getAttribute("x1"));
        for (const text of chart.querySelectorAll<SVGTextElement>("text[data-readout], [data-readout] text, [data-readout-plan]")) {
          const fill = text.getBBox();
          const left = svg.left + fill.x;
          const right = left + fill.width;
          const top = svg.top + fill.y;
          const bottom = top + fill.height;
          const clear = left >= box.right + ring + 3 || right <= box.left - ring - 3 || top >= box.bottom + ring + 3 || bottom <= box.top - ring - 3;
          if (!clear) found.push(`${months} months: "${text.textContent}" within 3 px of the knob's ring`);
          if (left < lineX && right > lineX) found.push(`${months} months: "${text.textContent}" across the line`);
          if (left < svg.left - 0.5 || right > svg.right + 0.5) found.push(`${months} months: "${text.textContent}" outside the chart`);
        }
        // A readout that wraps keeps its words together: no line holds one word alone.
        const lines = [...chart.querySelectorAll("[data-readout] text")].map((text) => text.textContent!);
        if (lines.length > 2 && lines.some((line) => !line.includes(" "))) found.push(`${months} months: a word alone in ${JSON.stringify(lines)}`);
        if (Math.abs(chart.getBoundingClientRect().height - height) > 0.5) found.push(`${months} months: the chart's height changed`);
        if (Number(months) >= Number(knob.getAttribute("aria-valuemax"))) break;
        await press("ArrowRight");
      }
      return found;
    });
    expect.soft(problems, where).toEqual([]);
  }
});

// DESIGN.md section 5, Reference words: a reference with a county's name breaks at its spaces first,
// as the scope chip and the not-found sentence break it. Each Roboto Mono part keeps to one line, and
// the space between two parts on one line is a Roboto Mono space too, one character wide.
async function countyParts(page: Page, selector: string) {
  return page.locator(selector).evaluateAll((elements) =>
    elements
      .filter((element) => element.textContent!.includes("COUNTY"))
      .map((element) => {
        const mono = element.matches(".font-mono")
          ? [element]
          : [...element.querySelectorAll(".font-mono")].filter((part) => part.textContent!.trim() !== "");
        const parts = mono.map((part) => {
          const range = document.createRange();
          range.selectNodeContents(part);
          const boxes = [...range.getClientRects()].filter((r) => r.width > 0);
          const tops = boxes.map((r) => Math.round(r.top));
          const width = boxes.reduce((sum, r) => sum + r.width, 0);
          return {
            text: part.textContent!,
            lines: new Set(tops).size,
            top: tops[0],
            left: boxes[0].left,
            right: boxes[boxes.length - 1].right,
            // One Roboto Mono character, from the part's own width.
            character: width / part.textContent!.length,
          };
        });
        // The space between each two parts that share a line, beside one character of the part before it.
        const spaces = parts.slice(1).flatMap((part, index) =>
          parts[index].top === part.top ? [{ space: part.left - parts[index].right, character: parts[index].character }] : [],
        );
        return { reference: element.textContent!.trim(), parts: parts.map(({ text, lines }) => [text, lines] as const), spaces };
      }),
  );
}

test("a reference with a county's name breaks only at its spaces, in a dot's details, the table and the cards", async ({ page }) => {
  const whole = (found: Awaited<ReturnType<typeof countyParts>>, where: string) => {
    expect(found.length, where).toBeGreaterThan(0);
    for (const { reference, parts, spaces } of found) {
      expect(parts.map(([part]) => part).join(" "), where).toBe(reference);
      expect(parts.filter(([, lines]) => lines !== 1), `${where}: ${reference}`).toEqual([]);
      for (const { space, character } of spaces) expect(Math.abs(space - character), `${where}: ${reference}, a space of ${space} px`).toBeLessThanOrEqual(0.5);
    }
    return found.flatMap(({ spaces }) => spaces).length;
  };

  // The shortest comparable, the first dot, is KE-MIGORI COUNTY-532367-CW-RFB.
  await openPackage(page);
  await ready(page);
  await page.getByRole("slider").focus();
  await page.keyboard.press("Tab");
  await expect(page.locator("[data-dot-tooltip]")).toContainText("KE-MIGORI COUNTY-532367-CW-RFB");
  whole(await countyParts(page, "[data-dot-tooltip] p:first-child"), "the dot's details");

  for (const [width, view, selector] of [
    [1024, "table", "tbody th"],
    // In the work's columns from a frame of 75rem the rows are cards (ticket 101).
    [1440, "cards", "li > :first-child"],
    [390, "cards", "li > :first-child"],
    [320, "cards", "li > :first-child"],
  ] as const) {
    await openPackage(page, { width: windowBeside(width) });
    await ready(page);
    await section(page).getByRole("button", { name: "Show the table" }).click();
    await expect(section(page).locator(`[data-table-view=${view}]`)).toBeVisible();
    const found = await countyParts(page, `[data-past-range] [data-table-view=${view}] ${selector}`);
    expect(found.map(({ reference }) => reference), `${width} px`).toEqual([
      "KE-MIGORI COUNTY-532367-CW-RFB",
      "KE-UASIN GISHU COUNTY-571338-CW-RFB",
      "KE-KAJIADO COUNTY-567787-CW-RFB",
    ]);
    const spaces = whole(found, `${width} px, the ${view}`);
    // At 390 px a card's heading holds a shorter county reference on one line, so a space is measured there.
    if (width === 390) expect(spaces, "390 px, the cards").toBeGreaterThan(0);
  }
});

test("a plan row with no planned dates has no plan line until you type months", async ({ page }) => {
  await openPackage(page, { comparables: await derived("comparables-ke-nwwda-541055.json", noPlan) });
  await ready(page);

  await expect(section(page).locator("[data-finding]")).toHaveText(
    "The middle half of the 49 comparable packages took 3.3 to 7.9 months from notice to signature.",
  );
  // The title already gives the middle half, so the summary starts with the middle one.
  await expect(section(page).locator("[data-summary]")).toHaveText(
    "The middle one took 4.4 months. 8 in 10 were signed within 9.1 months. Four of the 49 are still open. I kept them in the range " +
      "as not signed yet, so the range does not look shorter than it was. The past range above still shows every comparable package.",
  );
  await expect(page.getByRole("slider")).toHaveCount(0);
  await expect(section(page).getByText(/^The plan row has no planned notice date or signing date, so there is no plan line yet/)).toBeVisible();

  await page.getByRole("textbox", { name: "Planned months" }).fill("4");
  await expect(page.getByRole("slider")).toHaveAttribute("aria-valuenow", "4");
  await expect(readout(page)).toHaveText(`${await signedWithin(4)} of 49 signed within 4.0 months`);
  await expect(section(page).getByText(
    "The plan row has no planned notice date or signing date, so the line shows the months you typed.", { exact: true },
  )).toBeVisible();
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

// ── Ticket 101: the package workspace as numbered task zones, with its facts in a side panel ──────────

// The facts line below a frame of 75rem: STEP's values for the package's plan row in tests/fixtures/api/package-ke-nwwda-541055.json,
// with its Estimated Amount (US$) of 1,230,000.00 in STEP's form with its cents, as the plan's section 7.6 says facts keep
// it (ticket 101's review, follow-up 1: the tool's rounding, CLAUDE.md rule 1).
const FACTS_LINE = "Request for Bids, Open - National, US$1,230,000.00, Pending Implementation";

test("with the sidebar open, a side panel label that wraps keeps its value on the row's line", async ({ page }) => {
  await openSidebar(page);
  await openPackage(page);
  await ready(page);
  const side = page.getByRole("region", { name: "From the plan row" });
  const value = (label: string) => side.locator("[data-side-fact]", { has: page.getByText(label, { exact: true }) }).locator("dd");
  const post = (await value("Review Type").boundingBox())!;
  const amount = (await value("Estimated Amount (US$)").boundingBox())!;
  // The two share a row of the panel's two columns, so their values line up.
  expect(amount.x).toBeGreaterThan(post.x);
  expect(Math.round(amount.y)).toBe(Math.round(post.y));
});

test("from a frame of 75rem the facts are the side panel From the plan row, whose marker opens the plan row in the drawer in its place while the zones keep their place", async ({ page }) => {
  await openPackage(page, { planRow: true });
  await ready(page);
  const side = page.getByRole("region", { name: "From the plan row" });
  await expect(side).toBeVisible();
  for (const [label, value] of [
    ["Method", "Request for Bids"],
    ["Market Approach", "Open - National"],
    ["Review Type", "Post"],
    ["Estimated Amount (US$)", "1,230,000.00"],
    ["Process Status", "Pending Implementation"],
    ["In the plan", "Northern Water Works Development Agency plan of October 9, 2026"],
  ]) {
    await expect(side.locator("[data-side-fact]", { has: page.getByText(label, { exact: true }) }).locator("dd")).toHaveText(value);
  }
  // The facts line stands in for the panel only below that frame.
  await expect(page.locator("[data-facts-line]")).toBeHidden();
  const zones = page.locator("[data-zones]");
  const before = (await zones.boundingBox())!;

  const marker = side.getByRole("link", { name: /^Source 1: / });
  await marker.click();
  const drawer = page.getByRole("dialog");
  await expect(drawer.getByRole("heading", { level: 2 })).toContainText(REF);
  await expect(drawer).toContainText("Pending Implementation");
  await expect(side).toBeHidden();
  const after = (await zones.boundingBox())!;
  expect([after.x, after.width]).toEqual([before.x, before.width]);
  await page.keyboard.press("Escape");
  await expect(marker).toBeFocused();
  await expect(side).toBeVisible();
});

test("below a frame of 75rem the facts fold into one line whose Show the plan row opens the same record", async ({ page }) => {
  await openPackage(page, { width: 1024, planRow: true });
  await ready(page);
  await expect(page.getByRole("region", { name: "From the plan row" })).toBeHidden();
  const line = page.locator("[data-facts-line]");
  await expect(line.locator("p")).toHaveText(FACTS_LINE);
  // Each STEP value moves to the next line whole, never as "Pending" / "Implementation" (ticket 101's design review,
  // round 2, item 12).
  const values = await line.locator("p > span").evaluateAll((spans) => spans.map((span) => [span.textContent, getComputedStyle(span).whiteSpace]));
  expect(values.map(([text]) => text).join(", ")).toBe(FACTS_LINE);
  expect(values.filter(([, space]) => space !== "nowrap")).toEqual([]);
  const show = line.getByRole("button", { name: "Show the plan row" });
  await expect(show).toHaveAttribute("aria-expanded", "false");
  await show.click();
  const drawer = page.getByRole("dialog");
  await expect(drawer.getByRole("heading", { level: 2 })).toContainText(REF);
  await expect(show).toHaveAttribute("aria-expanded", "true");
});

// values.toml [past_range]: the two packages signed within the plan's 1.5 months, shortest first.
const WITHIN_PLAN = ["KE-WAJWASCO-372776-CW-RFB", "KE-WAJWASCO-356671-CW-RFB"];

for (const [width, height] of [
  [1440, 900],
  [390, 844],
] as const) {
  test(`at ${width} by ${height} pressing 2 lands on the two packages signed within the plan, under a count line that repeats it, and Show all 49 brings back the first 20`, async ({ page }) => {
    await openPackage(page, { width, height });
    await ready(page);
    const finding = section(page).locator("[data-finding]");
    const two = finding.getByRole("button", { name: "2", exact: true });
    await two.hover();
    await expect(page.getByRole("tooltip").locator("[data-num-act]")).toHaveText("Select to see the two packages.");
    await two.click();

    const table = section(page).locator("[data-comparables-table]");
    const view = table.locator("[data-table-view]:visible");
    const count = table.locator("[data-count-row] p").first();
    await expect(count).toHaveText("Showing the 2 of 49 packages signed within 1.5 months.");
    await expect(count).toBeFocused();
    const all = table.getByRole("button", { name: "Show all 49" });
    await expect(all).toBeVisible();
    // The button follows the count line in the reading order.
    expect(await count.evaluate((line, button) => Boolean(line.compareDocumentPosition(button!) & Node.DOCUMENT_POSITION_FOLLOWING), await all.elementHandle())).toBe(true);
    // The rows are cards wherever the table's own frame is under 49rem, as in the work's columns at 1440 px.
    const refs = view.locator("tbody th, li > :first-child");
    await expect(refs).toHaveText(WITHIN_PLAN);
    await expect(refs.first()).toBeInViewport({ ratio: 1 });
    // While filtered the title claims no "All 49": the count line says which rows show (ticket 101's critique, 7a).
    const title = table.locator("[data-table-caption]").last();
    await expect(title).toHaveText("Comparable packages, shortest first.");

    await all.click();
    await expect(title).toHaveText("All 49 comparable packages, shortest first.");
    await expect(count).toHaveText("Showing 1 to 20 of 49 packages.");
    await expect(count).toBeFocused();
    await expect(refs).toHaveCount(20);
    await expect(table.getByRole("button", { name: "Show all 49" })).toHaveCount(0);
  });
}

// A keyboard press carries focus down to the count line, so the line shows the focus ring every control shows; a
// pointer's press shows none (ticket 101's design review, item 4).
test("a number pressed from the keyboard lands on a count line that shows its focus ring, and a click shows none", async ({ page }) => {
  await openPackage(page);
  await ready(page);
  const two = section(page).locator("[data-finding]").getByRole("button", { name: "2", exact: true });
  const count = section(page).locator("[data-comparables-table] [data-count-row] p").first();
  const ring = () => count.evaluate((el) => getComputedStyle(el).outlineStyle);
  await two.focus();
  await page.keyboard.press("Enter");
  await expect(count).toBeFocused();
  expect(await ring()).not.toBe("none");

  await section(page).getByRole("button", { name: "Show all 49" }).click();
  await section(page).getByRole("button", { name: "Hide the table" }).click();
  await two.click();
  await expect(count).toBeFocused();
  expect(await ring()).toBe("none");
});

test("only a pressed number filters the table: hidden and shown again, it lists every package", async ({ page }) => {
  await openPackage(page);
  await ready(page);
  await section(page).locator("[data-finding]").getByRole("button", { name: "2", exact: true }).click();
  const count = section(page).locator("[data-comparables-table] [data-count-row] p").first();
  await expect(count).toHaveText("Showing the 2 of 49 packages signed within 1.5 months.");
  await section(page).getByRole("button", { name: "Hide the table" }).click();
  await section(page).getByRole("button", { name: "Show the table" }).click();
  await expect(count).toHaveText("Showing 1 to 20 of 49 packages.");
});

test("each number in the finding and the summary says what a click lands on, and every count line states only the number pressed", async ({ page }) => {
  await openPackage(page);
  await ready(page);
  const tool = JSON.parse(await recorded("comparables-ke-nwwda-541055.json")) as {
    past_range: { q25: number; q50: number; q75: number; q80: number };
    plan: { months: number; within: number };
    counts: { comparables: number };
  };
  // The numbers find_comparables returned, as the screen writes them.
  const returned = new Set(
    [tool.past_range.q25, tool.past_range.q50, tool.past_range.q75, tool.past_range.q80, tool.plan.months]
      .map((n) => n.toFixed(1))
      .concat([tool.plan.within, tool.counts.comparables].map(String)),
  );
  const summary = section(page).locator("[data-summary]");
  for (const [where, name, act, line] of [
    ["finding", "49", "Select to see all 49.", "Showing 1 to 20 of 49 packages."],
    ["summary", "3.3", "Select to see the packages in the middle half.", "Showing the packages in the middle half, from 3.3 to 7.9 months."],
    ["summary", "4.4", "Select to see the middle package.", "Showing the middle package, at 4.4 months."],
    ["summary", "9.1", "Select to see the packages signed within 9.1 months.", "Showing the packages signed within 9.1 months."],
  ] as const) {
    const scope = where === "finding" ? section(page).locator("[data-finding]") : summary;
    const number = scope.getByRole("button", { name, exact: true }).first();
    await number.hover();
    await expect(page.getByRole("tooltip").locator("[data-num-act]")).toHaveText(act);
    await number.click();
    const count = section(page).locator("[data-comparables-table] [data-count-row] p").first();
    await expect(count).toHaveText(line);
    await expect(count).toBeFocused();
    // The table's own range, "1–20", is the rows on this page; every other figure is one the tool returned.
    const figures = (await count.innerText()).replace("Showing 1 to 20 of", "Showing of").match(/\d+(\.\d+)?/g) ?? [];
    for (const figure of figures) expect(returned.has(figure), `${figure} in "${line}"`).toBe(true);
    await page.mouse.move(0, 0);
  }
  // The middle package's row is the one at the middle's months.
  await summary.getByRole("button", { name: "4.4", exact: true }).click();
  await expect(section(page).locator("[data-comparables-table] [data-table-view]:visible").locator("tbody th, li > :first-child")).toHaveText(["KE-TAVEVO-151330-CW-RFB"]);
});

// The quartiles are Kaplan-Meier days on which a package was signed, and a package still open is censored (ticket 15),
// so the middle half and the middle count only signed packages; and two packages at the middle's months are not "the
// middle package", so its number opens every row (ticket 101's review, follow-up 2). A derived answer puts a still-open
// package inside the middle half and a second signed package at the middle's months.
test("the middle half and the middle list only signed packages, and a middle two packages share opens every row", async ({ page }) => {
  const body = JSON.parse(await recorded("comparables-ke-nwwda-541055.json")) as Comparables & { past_range: { q25: number; q50: number; q75: number } };
  const { q25, q50, q75 } = body.past_range;
  const open = body.rows.find((row) => row.still_open)!;
  open.months = 5;
  body.rows.find((row) => !row.still_open && row.months > q25 && row.months < q50)!.months = q50;
  await openPackage(page, { comparables: { body: JSON.stringify(body) } });
  await ready(page);
  const summary = section(page).locator("[data-summary]");
  const refs = section(page).locator("[data-comparables-table] [data-table-view]:visible").locator("tbody th, li > :first-child");

  await summary.getByRole("button", { name: "3.3", exact: true }).first().click();
  const middle = body.rows.filter((row) => !row.still_open && row.months >= q25 && row.months <= q75).map((row) => row.step_reference);
  await expect(refs).toHaveText(middle.slice(0, 20));
  expect(middle).not.toContain(open.step_reference);

  await page.mouse.move(0, 0);
  const median = summary.getByRole("button", { name: "4.4", exact: true });
  await median.hover();
  await expect(page.getByRole("tooltip").locator("[data-num-act]")).toHaveText("Select to see all 49.");
  await median.click();
  await expect(section(page).locator("[data-comparables-table] [data-count-row] p").first()).toHaveText("Showing 1 to 20 of 49 packages.");
});

test("the plan's months in the finding open the plan row in the drawer", async ({ page }) => {
  await openPackage(page, { planRow: true });
  await ready(page);
  const months = section(page).locator("[data-finding]").getByRole("button", { name: "1.5", exact: true });
  await months.hover();
  await expect(page.getByRole("tooltip").locator("[data-num-act]")).toHaveText("Select to see the plan row.");
  await months.click();
  await expect(page.getByRole("dialog").getByRole("heading", { level: 2 })).toContainText(REF);
});

test("the five sections are Task zones numbered 1 to 5 in two stages, with the PPSD sections as tags and no eyebrow or middle-dot heading at 1440, 1024 and 390 px", async ({ page }) => {
  for (const width of [1440, 1024, 390]) {
    await openPackage(page, { width });
    await ready(page);
    await expect(page.locator("[data-step-tracker] li")).toHaveCount(6);
    const zones = page.locator("[data-zones] > [data-zone], [data-zones] > [data-stage-label]");
    // The page's order: the stage, zones 1 to 4, the next stage and zone 5, each zone with its number and its name.
    const order = await zones.evaluateAll((all) =>
      all.map((el) =>
        el.hasAttribute("data-stage-label")
          ? `stage: ${el.textContent}`
          : `${el.getAttribute("data-zone")}: ${el.querySelector("[data-zone-number]")?.textContent?.trim()} ${el.querySelector("[data-zone-name]")?.lastChild?.textContent}` +
            (el.querySelector("[data-zone-tag]") ? ` [${el.querySelector("[data-zone-tag]")!.textContent}]` : ""),
      ),
    );
    expect(order, `${width} px`).toEqual([
      "stage: Planning",
      "panel: 1 How long it took",
      "row: 2 Planned date for each step",
      "row: 3 Procurement risks and what helped [PPSD section 3]",
      "row: 4 Procurement approach options [PPSD section 6]",
      "stage: Tender design",
      "row: 5 Check your criteria",
    ]);
    // Each zone is a section named by its h2, whose number screen readers do not hear.
    const names = ["How long it took", "Planned date for each step", "Procurement risks and what helped", "Procurement approach options", "Check your criteria"];
    for (const [index, name] of names.entries()) {
      await expect(page.locator("[data-zones] > [data-zone]").nth(index)).toHaveAccessibleName(name);
    }
    // No eyebrow in capitals and no middle dot in a heading, a label or a tag of the page's work.
    const marks = await page.locator("[data-zones], [data-page-head], [data-side-slot]").evaluateAll((roots) =>
      roots.flatMap((root) =>
        [...root.querySelectorAll<HTMLElement>("h1, h2, h3, [data-stage-label], [data-zone-tag], .text-label")]
          .filter((el) => el.offsetParent !== null && !el.closest("[data-range-chart]"))
          .filter((el) => el.textContent!.includes("·") || getComputedStyle(el).textTransform === "uppercase")
          .map((el) => el.textContent),
      ),
    );
    expect(marks, `${width} px`).toEqual([]);
  }
});

test("zone 1 opens on its finding in the finding style, inside the first screen at 390 by 844 and 1024 by 768", async ({ page }) => {
  for (const [width, height] of [
    [390, 844],
    [1024, 768],
  ] as const) {
    await openPackage(page, { width, height });
    await ready(page);
    const finding = section(page).locator("[data-finding]");
    await expect(finding).toHaveText(FINDING);
    // The finding style (DESIGN.md section 3): Open Sans Light, 28/36, 24/32 below 48rem, heading ink.
    const style = await finding.evaluate((el) => {
      const css = getComputedStyle(el);
      return [css.fontWeight, css.fontSize, css.lineHeight, css.color];
    });
    expect(style).toEqual(["300", width < 768 ? "24px" : "28px", width < 768 ? "32px" : "36px", "rgb(1, 39, 64)"]);
    const top = (await finding.boundingBox())!.y;
    expect(top, `${width} by ${height}`).toBeLessThan(height);
    // It is the largest type on the page.
    const largest = await page.locator("main").evaluate((main) =>
      Math.max(...[...main.querySelectorAll<HTMLElement>("*")].filter((el) => el.offsetParent !== null && el.childNodes.length && [...el.childNodes].some((node) => node.nodeType === 3 && node.textContent!.trim())).map((el) => parseFloat(getComputedStyle(el).fontSize))),
    );
    expect(largest).toBe(width < 768 ? 24 : 28);
    // The foot strip's three lines share one style, caption in ink-muted (DESIGN.md, Foot strip), the coverage line's
    // 24 px line box aside, which holds its numbers' buttons (ticket 101's design review).
    const strip = section(page).locator("[data-foot-strip]").first();
    const look = (selector: string) => strip.locator(selector).first().evaluate((el) => [getComputedStyle(el).fontSize, getComputedStyle(el).color]);
    expect(await look("[data-coverage-line]"), `${width} px`).toEqual(await look("[data-source]"));
    // The Note and its label too, not the chart's colours (ticket 101's design review, round 2, item 9).
    expect(await look("[data-chart-note]"), `${width} px`).toEqual(await look("[data-source]"));
    expect(await look("[data-chart-note] > span"), `${width} px`).toEqual(await look("[data-source]"));
  }
});

test("below 20 comparables the sentence that holds back is zone 1's finding, the count follows in body, the chart has dots and no range, and the table is open", async ({ page }) => {
  await openPackage(page, {
    comparables: { body: await recorded("comparables-ke-nwwda-541055-prior.json") },
    estimate: { body: await recorded("estimate-ke-nwwda-541055-prior.json") },
  });
  await ready(page);
  const finding = section(page).locator("[data-finding]");
  await expect(finding).toHaveText("I'm not giving a range from only seven comparable packages. Here are all seven.");
  expect(await finding.evaluate((el) => [getComputedStyle(el).fontWeight, getComputedStyle(el).fontSize])).toEqual(["300", "28px"]);
  const count = section(page).locator("[data-few-count]");
  await expect(count).toHaveText("None of the seven comparable packages were signed within the plan's 1.5 months.");
  expect(await count.evaluate((el) => getComputedStyle(el).fontSize)).toBe("16px");
  await expect(page.locator("[data-chart-drawing] [data-dot]")).toHaveCount(7);
  await expect(page.locator("[data-chart-drawing] :is([data-band], [data-middle], [data-in10])")).toHaveCount(0);
  await expect(section(page).getByRole("button", { name: "Hide the table" })).toHaveAttribute("aria-expanded", "true");
  await expect(section(page).locator("[data-comparables-table] [data-table-view]:visible").locator("tbody tr, li")).toHaveCount(7);
  // One to nine in words, as the finding writes the count (DESIGN.md section 7, rule 12; ticket 101's design review).
  await expect(section(page).locator("[data-comparables-table] [data-count-row] p").first()).toHaveText("Showing all seven packages.");
});

// How far apart, in pixels, the tops of a phrase's characters sit inside an element, with a no-break space read as a
// space: 0 when the phrase keeps to one line, a line's height or more when it breaks.
const phraseSpread = (element: Locator, phrase: string) =>
  element.evaluate((el, phrase) => {
    const chars: { node: Text; at: number; ch: string }[] = [];
    const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    for (let node = walker.nextNode() as Text | null; node; node = walker.nextNode() as Text | null) {
      for (let at = 0; at < node.data.length; at++) chars.push({ node, at, ch: node.data[at] });
    }
    const start = chars.map((c) => (c.ch === "\u00a0" ? " " : c.ch)).join("").indexOf(phrase);
    if (start < 0) return -1;
    const tops = chars.slice(start, start + phrase.length).filter((c) => c.ch.trim() !== "").map((c) => {
      const range = document.createRange();
      range.setStart(c.node, c.at);
      range.setEnd(c.node, c.at + 1);
      return range.getBoundingClientRect().top;
    });
    return Math.round(Math.max(...tops) - Math.min(...tops));
  }, phrase);

// Block 9 of the redesign's DESIGN.md text: a number and its "months" never break apart, a share of 10 stays whole, and
// no line starts with the full stop after a number you can press (ticket 101's design review and critique, round 1).
test("a number keeps its months, a share of 10 keeps its words, and a full stop stays with the number before it", async ({ page }) => {
  for (const width of [1440, 1280, 1024, 390]) {
    await openPackage(page, { width });
    await ready(page);
    const finding = section(page).locator("[data-finding]");
    const summary = section(page).locator("[data-summary]");
    expect(await phraseSpread(finding, "1 in 10,"), `${width} px`).toBeLessThan(8);
    expect(await phraseSpread(finding, "1.5 months."), `${width} px`).toBeLessThan(8);
    expect(await phraseSpread(summary, "4.4."), `${width} px`).toBeLessThan(8);
    expect(await phraseSpread(summary, "9.1 months."), `${width} px`).toBeLessThan(8);
  }
  for (const width of [1440, 1024, 390]) {
    await openPackage(page, {
      width,
      comparables: { body: await recorded("comparables-ke-nwwda-541055-prior.json") },
      estimate: { body: await recorded("estimate-ke-nwwda-541055-prior.json") },
    });
    await ready(page);
    expect(await phraseSpread(section(page).locator("[data-few-count]"), "1.5 months."), `${width} px`).toBeLessThan(8);
  }
});

test("when the past range fails, zone 1 shows the error alert under its header and Advertised again still shows", async ({ page }) => {
  await openPackage(page, {
    comparables: { status: 503, body: SERVICE_DOWN },
    rebidding: { body: await recorded("rebidding-ke-nwwda-541055.json") },
  });
  const zone = section(page);
  await expect(zone).toHaveAttribute("data-past-range", "error");
  await expect(zone.getByRole("heading", { level: 2 })).toHaveAccessibleName("How long it took");
  const alert = zone.locator("[data-block=took]").getByText("I couldn't load the comparable packages for this section.");
  await expect(alert).toBeVisible();
  await expect(zone.getByRole("button", { name: "Try again" })).toBeVisible();
  // The alert sits under the zone's header, and Advertised again after it, in the same zone.
  const [head, error, again] = [
    (await zone.locator("[data-zone-head]").boundingBox())!,
    (await alert.boundingBox())!,
    (await zone.getByRole("heading", { level: 3, name: "Advertised again" }).boundingBox())!,
  ];
  expect(head.y + head.height).toBeLessThanOrEqual(error.y);
  expect(error.y).toBeLessThan(again.y);
  await expect(zone.locator("[data-rebid-count]")).toHaveText("3 of the 52 comparable packages were advertised again.");
  // Zone 4 waits on the same request, so it says so in one sentence, and zone 1's alert is the one place to try again
  // (ticket 101's design review, item 8).
  const options = page.locator("[data-approach-options]");
  await expect(options).toHaveAttribute("data-zone", "row");
  await expect(options.locator("[data-section-summary]")).toHaveText(
    "I'll list approach options when the comparable packages in section 1 load. Use Try again in section 1.",
  );
  await expect(options.getByRole("button")).toHaveCount(0);
  await expect(page.getByRole("alert")).toHaveCount(1);
});

for (const [width, open, least] of [
  [1440, true, 560],
  [1280, false, 560],
  [1024, false, 800],
] as const) {
  test(`the chart is at least ${least} px wide at ${width} px with the sidebar ${open ? "open" : "as a rail"}`, async ({ page }) => {
    if (open) await openSidebar(page);
    await openPackage(page, { width });
    await ready(page);
    // With no stored choice the sidebar rests as the rail (ticket 110).
    if (open) await expect(page.locator("html")).toHaveAttribute("data-sidebar-rest", "open");
    else await expect(page.locator("html")).not.toHaveAttribute("data-sidebar-rest", "open");
    const chart = (await page.locator("[data-range-chart]").boundingBox())!;
    expect(chart.width).toBeGreaterThanOrEqual(least);
  });
}

test("at 1440 and 1280 px a dot's drawer takes the side panel's place, the zones keep their left edge and width, and the opened dot keeps its ring", async ({ page }) => {
  for (const width of [1440, 1280]) {
    await openPackage(page, { width, drawer: "evidence-package-ke-mowi-47509.json" });
    await ready(page);
    const zones = page.locator("[data-zones]");
    const before = (await zones.boundingBox())!;
    const zone1 = section(page);
    const zone1Height = (await zone1.boundingBox())!.height;
    const tracker = page.locator("[data-step-tracker]");
    await expect(tracker.locator("[data-step-state]").first()).toBeVisible();
    const trackerHeight = (await tracker.boundingBox())!.height;
    await expect(page.getByRole("region", { name: "From the plan row" })).toBeVisible();
    const dot = page.locator('[data-dot-target][aria-label^="KE-MOWI-47509-CW-RFB,"]');
    await dot.scrollIntoViewIfNeeded();
    const spot = (await dot.boundingBox())!;
    await page.mouse.click(spot.x + spot.width / 2, spot.y + spot.height / 2);
    const drawer = page.getByRole("dialog");
    await expect(drawer).toBeVisible();
    await expect(drawer.locator("[data-drawer-caption]")).toHaveText("Comparable package in the past range");
    await expect(page.getByRole("region", { name: "From the plan row" })).toBeHidden();
    const after = (await zones.boundingBox())!;
    expect([after.x, after.width], `${width} px`).toEqual([before.x, before.width]);
    // Nothing in zone 1 moves either (principle 5): the summary keeps its place under the chart, so the dot you
    // clicked stays where it was, beside its records (ticket 101's critique, round 1).
    expect(Math.round((await dot.boundingBox())!.y), `${width} px`).toBe(Math.round(spot.y));
    expect((await zone1.boundingBox())!.height, `${width} px`).toBeCloseTo(zone1Height, 0);
    // The step tracker reads its own width, so it keeps its row of six too (ticket 101's critique, round 2).
    expect((await tracker.boundingBox())!.height, `${width} px`).toBeCloseTo(trackerHeight, 0);
    // The drawer sits where the side panel was, beside the zones.
    expect((await drawer.boundingBox())!.x).toBeGreaterThan(after.x + after.width);
    // The opened dot keeps its 2 px info-icon ring while the drawer shows it.
    const ring = page.locator("[data-opened-ring]");
    await expect(ring).toBeAttached();
    expect(await ring.evaluate((el) => [getComputedStyle(el).stroke, getComputedStyle(el).strokeWidth])).toEqual(["rgb(0, 113, 188)", "2px"]);
  }
});
