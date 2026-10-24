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

// A source the evidence drawer opens: ICR paragraph 54 of P130164, as the answer panel cites it.
const ICR_54 = "strata.gold.passage:31525018/v1/54";

async function openPackage(
  page: Page,
  options: { width?: number; comparables?: Answer | null; pkg?: Answer | null; ref?: string; evidence?: boolean } = {},
) {
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
  if (options.evidence) {
    answers["/api/evidence"] = { body: await recorded("evidence-icr-p130164-54.json") };
    answers["/api/evidence/opened"] = { body: '{"opened":[],"recorded":true}' };
  }
  await mockApi(page, answers);
  // A path left out never answers, so the page stays loading.
  if (options.pkg === null) await page.route(`**${api}`, () => new Promise(() => {}));
  if (options.comparables === null) await page.route(`**${api}/comparables`, () => new Promise(() => {}));
  await page.goto(`/packages/${encodeURIComponent(ref)}${options.evidence ? `?evidence=${encodeURIComponent(ICR_54)}` : ""}`);
}

const section = (page: Page) => page.locator("[data-past-range]");
const ready = async (page: Page) => expect(page.locator("[data-past-range]:not([data-past-range=loading])")).toBeVisible();
const readout = (page: Page) => page.locator("[data-readout]");

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
  await expect(section(page).getByRole("heading", { level: 3 })).toHaveText(
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
    "Dot chart of 49 comparable packages on a month axis from 0 to 18 months: 45 signed and four still open. The middle half took " +
      "3.3 to 7.9 months, the middle one took 4.4, and 8 in 10 were signed within 9.1. A line marks 1.5 months, and 2 of 49 were " +
      "signed within it. I left out the three canceled packages, because a canceled package was never signed and is not still open.",
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

test("a drag gives the slider focus, so the arrow keys nudge the line you just moved", async ({ page }) => {
  await openPackage(page);
  await ready(page);
  const slider = page.getByRole("slider", { name: "Planned months" });
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

test("at phone widths the readout never crosses the knob, wherever the line sits", async ({ page }) => {
  const overlap = (a: { x: number; y: number; width: number; height: number }, b: typeof a) =>
    a.x < b.x + b.width && b.x < a.x + a.width && a.y < b.y + b.height && b.y < a.y + a.height;
  for (const width of [390, 320]) {
    await openPackage(page, { width });
    await ready(page);
    const input = page.getByRole("textbox", { name: "Planned months" });
    for (const months of ["1.5", "6", "9", "14"]) {
      await input.fill(months);
      await expect(page.getByRole("slider")).toHaveAttribute("aria-valuenow", String(Number(months)));
      const knob = (await page.getByRole("slider").boundingBox())!;
      for (const label of await page.locator("[data-readout], [data-readout-plan]").all()) {
        const box = (await label.boundingBox())!;
        expect(overlap(box, knob), `${width} px, ${months} months: "${await label.textContent()}"`).toBe(false);
        const chart = (await page.locator("[data-range-chart]").boundingBox())!;
        expect(box.x, `${width} px, ${months} months`).toBeGreaterThanOrEqual(chart.x - 0.5);
        expect(box.x + box.width, `${width} px, ${months} months`).toBeLessThanOrEqual(chart.x + chart.width + 0.5);
      }
    }
  }
});

test("the plan line never runs through a statistic's label: the label moves off it, or the line stops above it and resumes below", async ({ page }) => {
  for (const width of [1440, 390]) {
    await openPackage(page, { width });
    await ready(page);
    // 10 months sits just past the 8-in-10 point, where a reader drags the line to ask whether 10 would be enough.
    for (const months of ["10", "6", "3.5"]) {
      await page.getByRole("textbox", { name: "Planned months" }).fill(months);
      await expect(page.getByRole("slider")).toHaveAttribute("aria-valuenow", String(Number(months)));
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

    expect(helperBox.top - inputBox.bottom, `${width} px`).toBeLessThanOrEqual(28);
    // The chart follows the helper with no empty row between: 16 px, or a few more where the held
    // button is taller than the helper's lines.
    expect(before - helperBox.bottom, `${width} px`).toBeLessThanOrEqual(24);

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

  await expect(cards.locator("li")).toHaveCount(49);
  await expect(cards).not.toContainText("so far if still open");
  await expect(page.locator("[data-comparables-table]").getByText(definition, { exact: true })).toBeVisible();
  // The definition is its own element beside the count, never run on into the count's sentence.
  await expect(page.locator("[data-comparables-table] p[data-numbers]").first()).toHaveText("Showing all 49 packages");

  await page.setViewportSize({ width: 1440, height: 900 });
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
  // The country leads the line, as it follows the reference in the dot's name, so the notice is not
  // read as published in Kenya.
  await expect(tip).toContainText("Kenya. Signed Oct 6, 2023. Its notice was published Sep 2, 2023.");

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
  for (const width of [1440, 390]) {
    await openPackage(page, { width });
    await ready(page);
    await page.locator("[data-range-chart]").scrollIntoViewIfNeeded();
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
      await page.waitForTimeout(16);
    }
    await page.waitForTimeout(400);
    await expect(tip, `${width} px, on arrival`).toContainText(await name(bottom));

    // From the same dot onto the dot above it, resting there: that dot takes the tooltip.
    await page.mouse.move(2, from.y, { steps: 4 });
    await expect(tip).toHaveCount(0);
    await page.mouse.move(from.x, from.y);
    await expect(tip).toContainText(await name(bottom));
    const above = await centre(page, `[data-dot-target='${column[column.length - 2]}']`);
    await page.mouse.move(above.x, above.y, { steps: 4 });
    await page.waitForTimeout(150);
    await expect(tip, `${width} px, resting on the dot above`).toContainText(await name(column[column.length - 2]));

    // Escape pressed before that rest is over hides the tooltip, and no dot takes it after.
    await page.mouse.move(from.x, from.y, { steps: 4 });
    await expect(tip).toContainText(await name(bottom));
    await page.mouse.move(above.x, above.y, { steps: 4 });
    await page.keyboard.press("Escape");
    await page.waitForTimeout(150);
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
  await openPackage(page, { width: 1024 });
  await ready(page);
  await page.locator("[data-range-chart]").scrollIntoViewIfNeeded();
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
    await expect(tip).toHaveCount(0);
    await page.mouse.move(from.x, from.y);
    await expect(tip).toContainText(taken);
    const box = (await tip.boundingBox())!;
    const to = { x: Math.min(Math.max(from.x, box.x + 4), box.x + box.width - 4), y: box.y + box.height - 2 };
    const steps = Math.ceil(Math.hypot(to.x - from.x, to.y - from.y) / 2);
    for (let step = 1; step <= steps; step++) {
      await page.mouse.move(from.x + ((to.x - from.x) * step) / steps, from.y + ((to.y - from.y) * step) / steps);
      await page.waitForTimeout(16);
    }
    await page.waitForTimeout(200);
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
  await expect(chart).toContainText("Each dot is 1 in 20 of the 103 packages.");
  await expect(chart).toContainText("Eight still open.");
  await expect(chart.locator(":scope > circle")).toHaveCount(0);
  await section(page).getByRole("button", { name: "Show the table" }).click();
  await expect(page.locator("[data-comparables-table] table tbody tr")).toHaveCount(20);
  await expect(page.locator("[data-comparables-table]")).toContainText("Showing 1–20 of 103 packages");
  await page.getByRole("button", { name: "Next 20" }).click();
  await expect(page.locator("[data-comparables-table]")).toContainText("Showing 21–40 of 103 packages");
});

test("a quantile dot the curve never reached is pinned at the plot's edge, so the axis stays readable", async ({ page }) => {
  for (const width of [1440, 390]) {
    await openPackage(page, { width, comparables: { body: await recorded("comparables-ke-nwwda-541055-any-category.json") } });
    await ready(page);
    const chart = page.locator("[data-chart-drawing]");

    // The 20th dot is past its last follow-up, so it sits at the edge with a chevron and keeps its months in its name.
    await expect(chart.locator("[data-beyond]")).toHaveCount(1);
    await expect(page.locator("[data-dot-target='19']")).toHaveAccessibleName(/sits past \d+\.\d months\.$/);
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
  // With none still open, the text alternative names only the signed ones.
  await expect(page.locator("[data-chart-alt]")).toHaveText(
    "Dot chart of seven comparable packages on a month axis from 0 to 12 months: seven signed. I'm not giving a range for so few. " +
      "A line marks 1.5 months, and 0 of 7 were signed within it.",
  );
});

test("when packages matched but none could be measured, the reasons say how many of them, with no count of none used", async ({ page }) => {
  await openPackage(page, { comparables: { body: await recorded("comparables-ke-nwwda-541055-non-consulting.json") } });
  await ready(page);

  await expect(section(page).getByRole("heading", { level: 3 })).toHaveText(
    "Six past packages matched this one, but I can't measure how long any of them took.",
  );
  await expect(section(page).locator("[data-coverage-line]")).toContainText(
    "Of the six, two lacked the STEP reference that links notice to contract and four had no specific procurement notice in the records I hold.",
  );
  await expect(section(page)).not.toContainText("Based on");
  await expect(section(page).getByRole("link", { name: /^See data readiness/ })).toBeVisible();
  // Each count can be checked, with the same tooltip as the populated coverage line.
  const line = section(page).locator("[data-coverage-line]");
  await expect(line.getByRole("button")).toHaveText(["six", "two", "four"]);
  await line.getByRole("button", { name: "two" }).hover();
  await expect(page.getByText("Counted from the records behind this section. Data readiness lists them by source.")).toBeVisible();
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

  await expect(page.locator("[data-package-header]")).toHaveText(REF);
});

test("a reference no plan lists stays whole in the not-found sentence at phone width", async ({ page }) => {
  await openPackage(page, { width: 390, pkg: { status: 404, body: '{"code":"unknown_package"}' } });
  const reference = page.locator("main p", { hasText: "No package in Strata has the reference" }).locator(".font-mono");

  await expect(reference).toHaveText(REF);
  // The lines its text sits on: one.
  const lines = await reference.evaluate((el) => {
    const range = document.createRange();
    range.selectNodeContents(el);
    return new Set([...range.getClientRects()].map((r) => Math.round(r.top))).size;
  });
  expect(lines).toBe(1);
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
  const tops = await county.evaluate((p) =>
    [...p.querySelectorAll(".font-mono")].map((part) => [part.textContent, Math.round(part.getBoundingClientRect().top)]),
  );
  expect(tops).toHaveLength(2);
  expect(tops[1][1]).toBeGreaterThan(tops[0][1] as number);
  expect((await county.locator(".font-mono").nth(1).evaluate((el) => el.getClientRects().length))).toBe(1);
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

    await page.goto(PATH);
    await ready(page);
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
// evidence drawer narrows it. At 1024 px the drawer takes 410 px and leaves a 614 px page area, so
// the workspace shows what a 614 px window shows: a header that does not stick, facts in two
// columns, the sentence before the chart, the reset button in the helper's place and the table as cards.
test("at 1024 px with the evidence drawer open, the workspace lays out as its page area is wide, not the window", async ({ page }) => {
  await openPackage(page, { width: 1024, evidence: true });
  await ready(page);
  await expect(page.getByRole("dialog")).toBeVisible();
  expect(Math.round((await page.locator("[data-page-column]").boundingBox())!.width)).toBe(614);

  const layout = await page.evaluate(() => {
    const summary = document.querySelector("[data-summary]")!;
    const chart = document.querySelector("[data-chart-figure]")!;
    return {
      summaryFirst: Boolean(summary.compareDocumentPosition(chart) & Node.DOCUMENT_POSITION_FOLLOWING),
      header: getComputedStyle(document.querySelector("[data-package-header]")!).position,
      factColumns: getComputedStyle(document.querySelector("[data-package-facts]")!).gridTemplateColumns.split(" ").length,
      scrollPadding: document.documentElement.style.scrollPaddingTop,
      resets: [...document.querySelectorAll("[data-plan-reset]")].map((el) => getComputedStyle(el).display),
      scrollWidth: document.documentElement.scrollWidth,
    };
  });
  expect(layout.summaryFirst).toBe(true);
  expect(layout.header).not.toBe("sticky");
  expect(layout.scrollPadding).toBe("");
  expect(layout.factColumns).toBe(2);
  // The input row's button is display: none; the helper's place keeps the other.
  expect(layout.resets).toEqual(["none", "block"]);
  expect(layout.scrollWidth).toBeLessThanOrEqual(1024);

  await section(page).getByRole("button", { name: "Show the table" }).click();
  await expect(section(page).locator("[data-table-view=cards]")).toBeVisible();
  await expect(section(page).locator("[data-table-view=table]")).toBeHidden();
});

// At a browser zoom such as 110 percent, the page area beside the drawer can be a fraction of a pixel
// under 768 px. The sentence's place reads the same exact width the container queries read.
test("a page area a fraction of a pixel under 768 px puts the sentence first, as the header and facts lay out narrow", async ({ page }) => {
  await openPackage(page);
  await ready(page);
  await page.locator("[data-page-column]").evaluate((column) => {
    column.style.flex = "none";
    column.style.width = "767.6px";
  });
  await expect(page.locator("[data-package-header]")).not.toHaveCSS("position", "sticky");
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
// about 1415 px than at 1024 px. So it reads its own width: its rows when its frame has 49rem, and cards
// below that. At 1440 px the drawer leaves an 864 px page area, and at 1920 px a 1320 px one; an 834 px
// window is an iPad held upright.
test("the past range's table shows its rows where its frame has 49rem, every cell's text inside its cell, and cards where it has less", async ({ page }) => {
  const body = JSON.parse(await recorded("comparables-ke-nwwda-541055.json")) as Comparables;
  const withoutSpace = body.rows.filter((row) => !row.step_reference.includes(" ")).length;
  for (const [width, evidence, view] of [
    [1024, false, "table"],
    [1440, false, "table"],
    [1600, false, "table"],
    [1200, false, "cards"],
    [1280, false, "cards"],
    [1366, false, "cards"],
    [1920, true, "cards"],
    [1440, true, "cards"],
    [834, false, "cards"],
  ] as const) {
    const where = `${width} px${evidence ? " beside the drawer" : ""}`;
    await openPackage(page, { width, evidence });
    await ready(page);
    await section(page).getByRole("button", { name: "Show the table" }).click();
    const table = section(page).locator("[data-table-view=table]");
    const cards = section(page).locator("[data-table-view=cards]");
    await expect(view === "table" ? table : cards, where).toBeVisible();
    await expect(view === "table" ? cards : table, where).toBeHidden();
    if (view === "cards") continue;

    // No cell's text runs past its cell, and the frame does not scroll sideways.
    const spill = await table.evaluate((frame) => ({
      scroll: frame.scrollWidth - frame.clientWidth,
      cells: [...frame.querySelectorAll("tbody td, tbody th")]
        .filter((cell) => {
          const range = document.createRange();
          range.selectNodeContents(cell);
          return Math.max(...[...range.getClientRects()].map((r) => r.right)) > cell.getBoundingClientRect().right + 0.5;
        })
        .map((cell) => cell.textContent),
    }));
    expect(spill, where).toEqual({ scroll: 0, cells: [] });

    // Each row's reference and the lines its text sits on, counted by their tops. A reference without a
    // space keeps to one line.
    const references = await table.locator("tbody th").evaluateAll((cells) =>
      cells.map((cell) => {
        const range = document.createRange();
        range.selectNodeContents(cell);
        const tops = [...range.getClientRects()].filter((r) => r.width > 0).map((r) => Math.round(r.top));
        return [cell.textContent!, new Set(tops).size] as const;
      }),
    );
    const spaceless = references.filter(([reference]) => !reference.includes(" "));
    expect(spaceless, where).toHaveLength(withoutSpace);
    expect(spaceless.filter(([, lines]) => lines !== 1), where).toEqual([]);
  }
});

// DESIGN.md section 5, Reference words: a reference with a county's name breaks at its spaces first,
// as the scope chip and the not-found sentence break it. Each Roboto Mono part keeps to one line.
async function countyParts(page: Page, selector: string) {
  return page.locator(selector).evaluateAll((elements) =>
    elements
      .filter((element) => element.textContent!.includes("COUNTY"))
      .map((element) => {
        const mono = element.matches(".font-mono") ? [element] : [...element.querySelectorAll(".font-mono")];
        const parts = mono.map((part) => {
          const range = document.createRange();
          range.selectNodeContents(part);
          const tops = [...range.getClientRects()].filter((r) => r.width > 0).map((r) => Math.round(r.top));
          return [part.textContent!, new Set(tops).size] as const;
        });
        return { reference: element.textContent!.trim(), parts };
      }),
  );
}

test("a reference with a county's name breaks only at its spaces, in a dot's details, the table and the cards", async ({ page }) => {
  const whole = (found: Awaited<ReturnType<typeof countyParts>>, where: string) => {
    expect(found.length, where).toBeGreaterThan(0);
    for (const { reference, parts } of found) {
      expect(parts.map(([part]) => part).join(" "), where).toBe(reference);
      expect(parts.filter(([, lines]) => lines !== 1), `${where}: ${reference}`).toEqual([]);
    }
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
    [1440, "table", "tbody th"],
    [320, "cards", "li > :first-child"],
  ] as const) {
    await openPackage(page, { width });
    await ready(page);
    await section(page).getByRole("button", { name: "Show the table" }).click();
    await expect(section(page).locator(`[data-table-view=${view}]`)).toBeVisible();
    const found = await countyParts(page, `[data-past-range] [data-table-view=${view}] ${selector}`);
    expect(found.map(({ reference }) => reference), `${width} px`).toEqual([
      "KE-MIGORI COUNTY-532367-CW-RFB",
      "KE-UASIN GISHU COUNTY-571338-CW-RFB",
      "KE-KAJIADO COUNTY-567787-CW-RFB",
    ]);
    whole(found, `${width} px, the ${view}`);
  }
});

test("a plan row with no planned dates has no plan line until you type months", async ({ page }) => {
  await openPackage(page, { comparables: await derived("comparables-ke-nwwda-541055.json", noPlan) });
  await ready(page);

  await expect(section(page).getByRole("heading", { level: 3 })).toHaveText(
    "The middle half of the 49 comparable packages took 3.3 to 7.9 months from notice to signature.",
  );
  // The title already gives the middle half, so the summary starts with the middle one.
  await expect(section(page).locator("[data-summary]")).toHaveText(
    "The middle one took 4.4 months. 8 in 10 were signed within 9.1 months. Four of the 49 are still open. I kept them in the range " +
      "as not signed yet, so the range does not look shorter than it was.",
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
