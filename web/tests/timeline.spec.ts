// A project's timeline and the disagreement card (ticket 23) at seam 4: P130164's Timeline tab, the evidence drawer's
// views its marks open, and keeping the other report from an answer, against the answers the server wrote on the
// fixture (tests/record_timeline_api.py), which tests/test_timeline.py checks the server against. The dates and
// ratings are tests/ground_truth/values.toml's (pad-date, mid-term-review, isr-7-date, isr-7-rating,
// award-7431-signed, award-7431-reference, restructuring, isr-12-date, isr-12-rating, icr-date, icr-review-date,
// icr-review-reissue-date and icr-para-78), copied here so the screen is checked against an independent source.
// Its axe runs take most of its time, as the 10 and 21 screen tests' do.
import type { Page, Request } from "@playwright/test";
import { askFromTheBox, landed, open as openAnswer, panel } from "./answer-page";
import { scan } from "./axe";
import { hubApi } from "./hub-api";
import { expect, mockApi, recorded, test } from "./mocked";

const PDO = "disagreement:437378890475ef48";
const ICR_78 =
  "Indeed, it was clearly identified at the MTR that the achievement of part of the PDO was compromised by the major delays in implementing activities under Components 2 and 3 and lack of endorsement from relevant stakeholders.";

async function timelineApi() {
  const file = async (name: string) => ({ body: await recorded(name) });
  return {
    ...(await hubApi()),
    "/api/projects/P130164/timeline": await file("timeline-p130164.json"),
    "/api/projects/P130164/timeline?asof=2016-08-26": await file("timeline-p130164-2016-08-26.json"),
    "/api/projects/P130164/timeline?asof=2024-01-01": await file("timeline-p130164-2024-01-01.json"),
    [`/api/evidence?id=${PDO}`]: await file("evidence-disagreement-p130164-pdo.json"),
    "/api/evidence?id=doc:26733307": await file("evidence-doc-p130164-isr-7.json"),
    "/api/evidence?id=doc:31525018": await file("evidence-doc-p130164-icr.json"),
    "/api/evidence?id=ratings:P130164:pdo_progress:1-9": await file("evidence-ratings-p130164-1-9.json"),
    "/api/evidence?id=ratings:P130164:pdo_progress:1-9&asof=2024-01-01": await file("evidence-ratings-p130164-1-9-2024-01-01.json"),
    "/api/evidence?id=strata.gold.passage:31525018/v1/78": await file("evidence-icr-p130164-78.json"),
    "/api/evidence?id=strata.gold.passage:26733307/v1/s4": await file("evidence-isr-p130164-7-s4.json"),
  };
}

async function open(page: Page, path = "/projects/P130164/timeline", width = 1440, api: Record<string, { body: string }> = {}) {
  const requests: Request[] = [];
  page.on("request", (request) => requests.push(request));
  await page.setViewportSize({ width, height: 900 });
  const unrecorded = await mockApi(page, { ...(await timelineApi()), ...api });
  await page.goto(path);
  await expect(page.locator("[data-timeline=ready]")).toBeVisible();
  await page.evaluate(() => document.fonts.ready);
  return { requests, unrecorded };
}

async function axe(page: Page, within?: string) {
  const results = await scan(page, within);
  return results.violations.map((v) => `${v.id}: ${v.nodes.map((node) => node.target.join(" ")).join(", ")}`);
}

const chart = (page: Page) => page.locator("[data-evidence-trail]");
const items = (page: Page) => chart(page).getByRole("group").getByRole("link");
const item = (page: Page, id: string) => chart(page).locator(`[data-item="${id}"]`);
const drawer = (page: Page) => page.getByRole("dialog");

// The points of each dashed line, every 2 px, that fall inside a mark label's box: none, so no line runs through a
// label (the 23 brief, section 4.5).
async function linesThroughLabels(page: Page): Promise<string[]> {
  return chart(page).evaluate((root) => {
    const found: string[] = [];
    const labels = [...root.querySelectorAll<SVGTextElement>("[data-mark-label]")].map((label) => ({ id: label.dataset.markLabel, box: label.getBBox() }));
    for (const path of root.querySelectorAll<SVGPathElement>("[data-disagreement-line]")) {
      const length = path.getTotalLength();
      for (let at = 0; at <= length; at += 2) {
        const point = path.getPointAtLength(at);
        for (const { id, box } of labels) {
          if (point.x > box.x + 1 && point.x < box.x + box.width - 1 && point.y > box.y + 1 && point.y < box.y + box.height - 1) found.push(`${id} at ${Math.round(point.x)},${Math.round(point.y)}`);
        }
      }
    }
    return [...new Set(found.map((one) => one.split(" at ")[0]))];
  });
}

// What covers the as-of label: each disagreement chip whose box meets the label's box, and each dashed line with a
// point inside it, sampled every 2 px as linesThroughLabels does. The label is the only place the tab shows its date.
async function overAsOf(page: Page): Promise<string[]> {
  return chart(page).evaluate((root) => {
    const label = root.querySelector<SVGTextElement>("[data-as-of] text");
    if (!label) return ["no as-of label"];
    const found = new Set<string>();
    const box = label.getBoundingClientRect();
    for (const chip of root.querySelectorAll<HTMLElement>("[data-item-kind=disagreement]")) {
      const at = chip.getBoundingClientRect();
      if (at.left < box.right && at.right > box.left && at.top < box.bottom && at.bottom > box.top) found.add(`chip ${chip.dataset.item}`);
    }
    const inner = label.getBBox();
    for (const path of root.querySelectorAll<SVGPathElement>("[data-disagreement-line]")) {
      const length = path.getTotalLength();
      for (let at = 0; at <= length; at += 2) {
        const point = path.getPointAtLength(at);
        if (point.x > inner.x + 1 && point.x < inner.x + inner.width - 1 && point.y > inner.y + 1 && point.y < inner.y + inner.height - 1) found.add("dashed line");
      }
    }
    return [...found];
  });
}

// The ticks whose year is not wholly inside the drawing.
async function ticksOutside(page: Page): Promise<string[]> {
  return chart(page).evaluate((root) => {
    const svg = root.querySelector<SVGSVGElement>("svg[role=img]")!.getBoundingClientRect();
    return [...root.querySelectorAll<SVGTextElement>("[data-tick]")]
      .filter((tick) => {
        const box = tick.getBoundingClientRect();
        return box.left < svg.left || box.right > svg.right;
      })
      .map((tick) => tick.textContent ?? "");
  });
}

// Two mark labels in one row that sit closer than 15 px, which reads as one phrase (design review, round 2, P7).
async function labelsTooClose(page: Page): Promise<string[]> {
  return chart(page).evaluate((root) => {
    const boxes = [...root.querySelectorAll<SVGTextElement>("[data-mark-label]")].map((label) => ({ id: label.dataset.markLabel, box: label.getBBox() }));
    const found: string[] = [];
    for (const [at, a] of boxes.entries()) {
      for (const b of boxes.slice(at + 1)) {
        const sameRow = a.box.y < b.box.y + b.box.height && b.box.y < a.box.y + a.box.height;
        const gap = Math.max(b.box.x - (a.box.x + a.box.width), a.box.x - (b.box.x + b.box.width));
        if (sameRow && gap < 15) found.push(`${a.id} and ${b.id}: ${Math.round(gap)} px`);
      }
    }
    return found;
  });
}

test("P130164's timeline places each report, event and record at its date, names each band's rating, and reads as one chart", async ({ page }) => {
  const { requests, unrecorded } = await open(page);

  await expect(page.locator("[data-timeline-finding]")).toHaveText(
    "Two pairs of reports disagree, and ISR ratings of progress fell from Satisfactory to Moderately Unsatisfactory.",
  );
  // Every item, in arrow-key order, named with its date (values.toml).
  await expect(items(page)).toHaveCount(14);
  const names = await items(page).evaluateAll((links) => links.map((link) => link.getAttribute("aria-label")));
  for (const [at, expected] of [
    [0, "Project Appraisal Document, October 1, 2013. Why lane. Item 1 of 14."],
    [1, "ISRs 1 to 9 rated progress Satisfactory, from February 22, 2014 to July 26, 2017. How lane. Item 2 of 14."],
    [2, "Mid-term review, May 16, 2016. How lane. Item 3 of 14."],
    [3, "ISR 7, August 26, 2016, rated progress Satisfactory. Disagrees with the ICR. How lane. Item 4 of 14."],
    [4, "Contract IN-RRSMP-7431-CW-RFB signed, June 15, 2017. What lane. Item 5 of 14."],
    [6, "Restructuring, July 27, 2017. How lane. Item 7 of 14."],
    [7, "ISR 12, April 10, 2018, rated progress Moderately Unsatisfactory. How lane. Item 8 of 14."],
    [9, "Implementation Completion and Results Report, October 10, 2019. Disagrees with ISR 7 and the ICR Review. Why lane. Item 10 of 14."],
    [10, "2 reports disagree: ISR 7, August 26, 2016, and the ICR, October 10, 2019. I lean on the ICR. Item 11 of 14."],
    [11, "Implementation Completion Report Review, March 27, 2020, replaced by its re-issue of May 4, 2023. Why lane. Item 12 of 14."],
  ] as const) {
    expect(names[at]).toBe(expected);
  }
  expect(names[12]).toContain("Implementation Completion Report Review, May 4, 2023.");
  // The marks sit at their dates: left to right in date order on the one axis.
  const xs = await items(page).evaluateAll((links) =>
    links.filter((link) => link.getAttribute("data-item-kind") !== "disagreement" && link.getAttribute("data-item-kind") !== "band").map((link) => link.getBoundingClientRect().x),
  );
  expect(xs).toEqual([...xs].sort((a, b) => a - b));
  // The bands name their ratings in text, and the Note spells out each code.
  await expect(chart(page).locator("[data-band-label]").first()).toHaveText("Satisfactory, ISRs 1–9");
  await expect(page.locator("[data-timeline-note]")).toContainText("MS is Moderately Satisfactory. MU is Moderately Unsatisfactory.");
  // It spells out only the codes a band shows: the first band names Satisfactory in full.
  await expect(page.locator("[data-timeline-note]")).not.toContainText("S is Satisfactory.");
  // The ISR series is bands, never a dashed line: each line joins two reports of different kinds.
  await expect(chart(page).locator("[data-disagreement-line]")).toHaveCount(2);
  // role img with the alt text as its name; a time axis with no title and five ticks, on whole years.
  const drawing = chart(page).locator("svg[role=img]");
  await expect(drawing).toHaveAccessibleName(/^Timeline of P130164 from 2013 to 2023 in three lanes/);
  await expect(chart(page).locator("[data-tick]")).toHaveText(["2014", "2016", "2018", "2020", "2022"]);
  // Every mark keeps its label at the 1246 px chart, and no dashed line runs through one.
  await expect(chart(page).locator("[data-mark-label]")).toHaveCount(9);
  expect(await linesThroughLabels(page)).toEqual([]);
  expect(await axe(page)).toEqual([]);
  // No request to a route that calls a model.
  const models: { method: string; path: string }[] = JSON.parse(await recorded("model-routes.json")).routes;
  const called = requests.map((request) => ({ method: request.method(), path: new URL(request.url()).pathname }));
  expect(called.filter((one) => models.some((model) => model.method === one.method && model.path === one.path))).toEqual([]);
  expect(unrecorded).toEqual([]);
});

test("the chart is one tab stop with arrow keys between marks, and the dashed line opens both reports in the drawer", async ({ page }) => {
  await open(page);

  await page.locator("[data-timeline] h2").focus();
  // The title's count comes first, then the chart's one tab stop.
  await page.keyboard.press("Tab");
  await expect(page.locator("[data-timeline-finding]").getByRole("button", { name: "Two" })).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(items(page).first()).toBeFocused();
  await page.keyboard.press("ArrowRight");
  await expect(items(page).nth(1)).toBeFocused();
  await expect(page.locator("[data-trail-tooltip]")).toContainText("Satisfactory");
  await page.keyboard.press("End");
  await expect(items(page).last()).toBeFocused();
  await page.keyboard.press("Home");
  // Down from the PAD goes to the How lane's nearest item in time.
  await page.keyboard.press("ArrowDown");
  await expect(items(page).nth(1)).toBeFocused();
  // Tab leaves the chart: one tab stop.
  await page.keyboard.press("Tab");
  expect(await items(page).evaluateAll((links) => links.includes(document.activeElement as HTMLAnchorElement))).toBe(false);

  // The dashed line's chip, after the ICR in arrow-key order.
  await item(page, PDO).focus();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(new RegExp(`evidence=${encodeURIComponent(PDO)}`));
  const dialog = drawer(page);
  await expect(dialog.getByRole("heading", { level: 2 })).toHaveText("ISR 7 and ICR paragraph 78");
  await expect(dialog.getByRole("heading", { level: 2 })).toBeFocused();
  // The switcher opens on "Both reports"; a side's tab reads "ICR ¶78" and is named with "paragraph" spelled out.
  const tabs = dialog.getByRole("tablist", { name: "Reports in this disagreement" }).getByRole("tab");
  await expect(tabs).toHaveCount(3);
  for (const [at, name] of ["Both reports", "ISR 7", "ICR paragraph 78"].entries()) await expect(tabs.nth(at)).toHaveAccessibleName(name);
  await expect(tabs.first()).toHaveAttribute("aria-selected", "true");
  await expect(tabs.nth(2).locator("[aria-hidden=true]")).toHaveText("¶");
  const card = dialog.locator("[data-disagreement]");
  // The info variant: no answer or draft rests on it here.
  await expect(card).toHaveAttribute("data-disagreement", "info");
  await expect(card.locator("[data-badge]")).toHaveText("Sources differ");
  await expect(card.locator("[data-card-subject]")).toHaveText("Progress towards the project development objective (PDO) at the mid-term review");
  // ISR 7 first and ICR paragraph 78 second, in the order written, with equal weight; the tag on the ICR.
  const sides = card.locator("[data-side]");
  await expect(sides.nth(0)).toContainText("ISR 7");
  await expect(sides.nth(0)).toContainText("August 26, 2016. Written during the project.");
  await expect(sides.nth(0)).toContainText("Satisfactory");
  await expect(sides.nth(1)).toContainText("ICR, paragraph 78");
  await expect(sides.nth(1)).toContainText("October 10, 2019. Written after the project closed.");
  await expect(sides.nth(1).locator("[data-source-tag]")).toHaveText("Strata leans on this");
  await expect(sides.nth(0).locator("[data-source-tag]")).toHaveCount(0);
  await expect(sides.nth(1)).toContainText(`"${ICR_78}"`);
  const looks = await sides.evaluateAll((all) => all.map((side) => [getComputedStyle(side).borderColor, getComputedStyle(side).backgroundColor]));
  expect(looks[0]).toEqual(looks[1]);
  await expect(card).toContainText(
    "For a judgment of how a project went, I lean on the later, more independent report, here the ICR, and I keep ISR 7 as the record of the earlier view.",
  );
  await expect(card).toContainText('If you keep ISR 7 instead, I treat "Progress towards achievement of PDO" as Satisfactory.');
  await expect(card).toContainText("You can keep ISR 7 instead from an answer or draft that rests on these two reports.");
  // Never the error state.
  await expect(card.locator("[data-badge]")).not.toHaveClass(/error/);
  // A side's tab shows its passage.
  await dialog.getByRole("tab", { name: "ICR paragraph 78" }).click();
  await expect(dialog.locator("[data-passage]")).toContainText(ICR_78);
  expect(await axe(page)).toEqual([]);
  // Escape closes the drawer, and focus goes back to the chip.
  await page.keyboard.press("Escape");
  await expect(dialog).toHaveCount(0);
  await expect(item(page, PDO)).toBeFocused();
});

test("at 1024 px the chart redraws beside the drawer at 524 px and keeps every label; a band and a report open their views", async ({ page }) => {
  await open(page, "/projects/P130164/timeline", 1024);
  await expect(chart(page).locator("[data-mark-label]")).toHaveCount(9);

  await item(page, "ratings:P130164:pdo_progress:1-9").click();
  const dialog = drawer(page);
  await expect(dialog.getByRole("heading", { level: 2 })).toHaveText("ISRs 1–9, rated Satisfactory");
  await expect(dialog).toContainText("I show them as a trajectory, not a disagreement.");
  await expect(dialog.locator("tbody tr")).toHaveCount(9);
  // The 410 px drawer is too narrow for the three columns, so each ISR is a card.
  await expect(dialog.getByRole("table")).toBeHidden();
  expect(Math.round((await chart(page).boundingBox())!.width)).toBe(524);
  await expect(chart(page).locator("[data-mark-label]")).toHaveCount(9);
  expect(await linesThroughLabels(page)).toEqual([]);
  // The narrowest band, beside the drawer, still names its rating by its code.
  await expect(chart(page).locator("[data-band-label]")).toHaveCount(3);

  await item(page, "doc:26733307").click();
  await expect(dialog.getByRole("heading", { level: 2 })).toHaveText("ISR 7, August 26, 2016");
  await expect(dialog.locator("[data-document-fields]")).toContainText("Disclosed");
  await expect(dialog.locator("[data-claim-line]")).toContainText("ISR 7 and the ICR disagree about progress towards the project development objective (PDO) at the mid-term review.");
  await item(page, "doc:31525018").click();
  // A sentence that starts with a report's short name starts with a capital.
  await expect(dialog.locator("[data-claim-line]").first()).toContainText("The ICR and ISR 7 disagree about");
  await item(page, "doc:26733307").click();
  await dialog.getByRole("button", { name: "Show both reports" }).click();
  await expect(dialog.getByRole("heading", { level: 2 })).toHaveText("ISR 7 and ICR paragraph 78");
  expect(await axe(page)).toEqual([]);
});

test("below 768 px the chart is a list in date order, and as of August 26, 2016 it shows only what was public then", async ({ page }) => {
  await open(page, "/projects/P130164/timeline", 390);
  const list = page.locator("[data-timeline-list] > li > a");
  await expect(list).toHaveCount(14);
  await expect(list.first()).toContainText("Oct 1, 2013");
  await expect(list.first()).toContainText("Project Appraisal Document (PAD)");
  // The list writes each run's rating in words, so its Note does not describe grey bands.
  await expect(page.locator("[data-timeline-note]")).not.toContainText("grey bands");
  await expect(page.locator("[data-evidence-trail]")).toHaveCount(0);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  expect(await axe(page)).toEqual([]);
  await page.setViewportSize({ width: 320, height: 800 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);

  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/projects/P130164/timeline?asof=2016-08-26");
  await expect(page.locator("[data-timeline=ready]")).toBeVisible();
  await expect(items(page)).toHaveCount(4);
  await expect(item(page, "doc:26733307")).toHaveAccessibleName(/^ISR 7, August 26, 2016/);
  await expect(chart(page).locator("[data-as-of]")).toContainText("Aug 26, 2016");
  // The tab applies the date itself, so no alert says it shows today's data.
  await expect(page.locator("main [data-alert]")).toHaveCount(0);
  await expect(chart(page).locator("[data-disagreement-line]")).toHaveCount(0);
});

test("as of a date after the ICR Review's re-issue, no dashed line or chip covers the as-of date, beside the drawer too", async ({ page }) => {
  for (const width of [1440, 1024]) {
    await open(page, "/projects/P130164/timeline?asof=2024-01-01", width);
    await expect(chart(page).locator("[data-as-of]")).toContainText("Jan 1, 2024");
    // Both disagreements are public by then, so the second line ends near the chart's right edge.
    await expect(chart(page).locator("[data-disagreement-line]")).toHaveCount(2);
    expect(await overAsOf(page)).toEqual([]);
    // The 2024 tick falls on the as-of date, at the chart's right edge, and stays whole there.
    expect(await ticksOutside(page)).toEqual([]);
    await item(page, "ratings:P130164:pdo_progress:1-9").click();
    await expect(drawer(page).getByRole("heading", { level: 2 })).toHaveText("ISRs 1–9, rated Satisfactory");
    expect(await overAsOf(page)).toEqual([]);
    expect(await ticksOutside(page)).toEqual([]);
  }
});

test("the skeleton title is sized to the title, so the chart does not move when the timeline arrives", async ({ page }) => {
  for (const width of [1440, 1024, 390]) {
    let release = () => {};
    const held = new Promise<void>((resolve) => (release = resolve));
    await page.setViewportSize({ width, height: 900 });
    await mockApi(page, await timelineApi());
    await page.route("**/api/projects/P130164/timeline", async (route) => {
      await held;
      await route.fulfill({ contentType: "application/json", body: await recorded("timeline-p130164.json") });
    });
    await page.goto("/projects/P130164/timeline");
    await expect(page.locator("[data-timeline=loading]")).toBeVisible();
    await page.evaluate(() => document.fonts.ready);
    const before = (await page.locator("[data-timeline-subtitle]").boundingBox())!.y;
    release();
    await expect(page.locator("[data-timeline=ready]")).toBeVisible();
    const after = (await page.locator("[data-timeline-subtitle]").boundingBox())!.y;
    expect(Math.abs(after - before), `at ${width} px`).toBeLessThanOrEqual(2);
    await page.unrouteAll({ behavior: "ignoreErrors" });
  }
});

test("two labels in one row keep 16 px apart at every chart width, beside the drawer too, and none is dropped", async ({ page }) => {
  // 1246 and 830 px with the drawer closed; 718 and 524 px beside it.
  for (const [width, evidence] of [[1440, ""], [1024, ""], [1440, "?evidence=ratings:P130164:pdo_progress:1-9"], [1024, "?evidence=ratings:P130164:pdo_progress:1-9"]] as const) {
    await open(page, `/projects/P130164/timeline${evidence}`, width);
    // In the 576 px drawer at 1440 px the band's nine ISRs are one table of three columns, not nine tall cards.
    if (evidence) await expect(drawer(page).getByRole("table")).toBeVisible({ visible: width === 1440 });
    // And it fits the drawer: a table never scrolls sideways inside its frame (DESIGN.md section 5, Tables).
    if (evidence && width === 1440) expect(await drawer(page).getByRole("table").evaluate((table) => table.parentElement!.scrollWidth <= table.parentElement!.clientWidth)).toBe(true);
    await expect(chart(page).locator("[data-mark-label]")).toHaveCount(9);
    expect(await labelsTooClose(page), `at ${Math.round((await chart(page).boundingBox())!.width)} px`).toEqual([]);
    expect(await linesThroughLabels(page)).toEqual([]);
  }
});

test("Show the table lists every item in arrow-key order, under its caption", async ({ page }) => {
  // At 1024 px the finding takes two lines; the count's tooltip opens above it, so it never hides the second.
  await open(page, "/projects/P130164/timeline", 1024);
  await page.locator("[data-timeline-finding]").getByRole("button", { name: "Two" }).focus();
  const tip = page.getByRole("tooltip");
  await expect(tip).toContainText("Counted by the disagreement check for this project.");
  const [finding, shown] = [(await page.locator("[data-timeline-finding]").boundingBox())!, (await tip.boundingBox())!];
  expect(shown.y + shown.height <= finding.y || shown.y >= finding.y + finding.height).toBe(true);

  await page.setViewportSize({ width: 1440, height: 900 });
  // The count in the title opens the table and takes you to it.
  await page.locator("[data-timeline-finding]").getByRole("button", { name: "Two" }).click();
  await expect(page.locator("[data-timeline-table]")).toBeVisible();
  await expect(page.locator("[data-timeline-table] [tabindex='0']").first()).toBeFocused();
  await page.getByRole("button", { name: "Hide the table" }).click();
  const toggle = page.getByRole("button", { name: "Show the table" });
  await toggle.click();
  await expect(page.getByRole("button", { name: "Hide the table" })).toHaveAttribute("aria-expanded", "true");
  const table = page.locator("[data-timeline-table]");
  await expect(table).toContainText("Everything on the timeline of Rajasthan Road Sector Modernization, in date order.");
  await expect(table).toContainText("Showing all 14 items.");
  await expect(table.locator("tbody tr")).toHaveCount(14);
  await expect(table.locator("tbody tr").nth(3)).toContainText("Disagrees with the ICR.");
  await expect(table.locator("tbody tr").nth(9)).toContainText("Disagrees with ISR 7 and the ICR Review.");
  await expect(table.locator("tbody tr").nth(10)).toContainText("I lean on the ICR.");
  // The source line says "Source:" once.
  await expect(table.getByText("Source:", { exact: true })).toHaveCount(1);
});

test("keeping ISR 7 under an answer that rests on it asks for a reason and stores it with the answer", async ({ page }) => {
  const posted: unknown[] = [];
  await openAnswer(page, { stream: "ask-p130164-isr-7-rating.sse" });
  await page.route("**/api/disagreements/*/choices**", (route) => {
    if (route.request().method() === "POST") {
      posted.push(route.request().postDataJSON());
      return route.fulfill({
        json: {
          recorded: true,
          choice: { kept_assertion_id: "x", leaned_assertion_id: "y", reason: "The mission saw the works on site.", made_at: "2026-10-23T15:00:00+00:00", kept_other: true },
        },
      });
    }
    return route.fulfill({ json: { choice: null } });
  });
  await askFromTheBox(page);
  await landed(page);

  const card = panel(page).getByRole("group", { name: "Two reports disagree: ISR 7 and ICR paragraph 78" });
  await expect(card).toHaveAttribute("data-disagreement", "warning");
  await card.getByRole("button", { name: "Keep ISR 7 instead" }).click();
  const reason = card.getByRole("textbox", { name: "Why do you keep ISR 7?" });
  await expect(reason).toBeFocused();
  // The row keeps your account's id, not your name.
  await expect(card).toContainText("I save your reason with your account and this answer, and it goes into the evidence pack.");
  await card.getByRole("button", { name: "Keep ISR 7" }).click();
  await expect(reason).toHaveAttribute("aria-invalid", "true");
  await expect(card).toContainText("Write a reason, so the evidence pack says why you kept ISR 7.");
  expect(posted).toEqual([]);

  await reason.fill("The mission saw the works on site.");
  await card.getByRole("button", { name: "Keep ISR 7" }).click();
  await expect(card.locator("[data-kept-line]")).toHaveText('You kept ISR 7 on October 23, 2026. Your reason: "The mission saw the works on site."');
  await expect(card.locator("[data-side=other] [data-source-tag]")).toHaveText("You kept this");
  await expect(card.locator("[data-side=leaned] [data-source-tag]")).toHaveText("Strata leans on this");
  expect(posted).toEqual([
    {
      kept_assertion_id: "strata.gold.passage:26733307/v1/s4#P130164/pdo_progress",
      reason: "The mission saw the works on site.",
      run_id: "run-0001",
      view: "staff",
    },
  ]);
  expect(await axe(page, "[data-answer-panel]")).toEqual([]);

  // Going back to Strata's choice that fails to save keeps the choice and says so to a screen reader too.
  await page.route("**/api/disagreements/*/choices**", (route) =>
    route.request().method() === "POST" ? route.fulfill({ status: 503, json: { code: "not_recorded" } }) : route.fulfill({ json: { choice: null } }),
  );
  await card.getByRole("button", { name: "Go back to Strata's choice" }).click();
  await expect(card.locator("[aria-live=polite]")).toHaveText("I couldn't save that just now, so you still keep ISR 7.");
  await expect(card.locator("[data-kept-line]")).toBeVisible();
});

test("the drawer says two reports disagree about each sentence the disagreement changes, not only the one its card follows", async ({ page }) => {
  await openAnswer(page, { stream: "ask-p130164-isr-7-rating.sse", evidence: "evidence-isr-p130164-7-s4.json" });
  // The recorded answer has one sentence. This one repeats it as a second sentence that the disagreement also
  // changes, as a longer answer could.
  const recordedStream = await recorded("ask-p130164-isr-7-rating.sse");
  const block = recordedStream.split("\n\n").find((one) => one.startsWith("event: sentence"))!;
  const stream = recordedStream
    .replace(block, `${block}\n\n${block.replace('"index": 0', '"index": 1')}`)
    .replace('"changes_sentence_ids": [0], "changes_count": 1', '"changes_sentence_ids": [0, 1], "changes_count": 2');
  await page.route("**/api/ask", (route) => route.fulfill({ contentType: "text/event-stream", body: stream }));
  await askFromTheBox(page);
  await landed(page);

  for (const sentence of [0, 1]) {
    await panel(page).locator(`[data-citation][data-sentence="${sentence}"]`).first().click();
    await expect(drawer(page).locator("[data-claim-line]")).toContainText("ISR 7 and ICR paragraph 78 disagree about this.");
    await page.keyboard.press("Escape");
  }
  await expect(panel(page).getByRole("group", { name: /^Two reports disagree/ })).toContainText("That changes two sentences in this answer.");
});

test("when get_disagreements fails, the chart says it couldn't read the ratings, and the newest ISR keeps its mark", async ({ page }) => {
  // The server's own answer with get_disagreements failing (tests/record_timeline_api.py, FAILED).
  await open(page, "/projects/P130164/timeline", 1440, { "/api/projects/P130164/timeline": { body: await recorded("timeline-p130164-failed.json") } });

  await expect(page.locator("[data-timeline-finding]")).toHaveText("I couldn't read this project's ISR ratings or check its reports for disagreements just now.");
  // The title says what failed; the alert says only what is missing until then, and fits the list as well as the chart.
  await expect(page.locator("[data-timeline-card] [data-alert]")).toHaveText(/^Until I can read the ratings, the timeline shows no rating bands and no dashed lines\./);
  // No dashed line is drawn, so the legend does not describe one.
  await expect(page.locator("[data-timeline-subtitle]")).toHaveText("Each mark is a report, an event or a record.");
  await expect(chart(page).locator("[data-band-row]")).toHaveText("I couldn't read this project's ISR ratings just now.");
  await expect(chart(page).locator("svg[role=img]")).not.toHaveAccessibleName(/I have no ISR ratings/);
  await expect(chart(page).locator("[data-disagreement-line]")).toHaveCount(0);
  // ISR 13, December 28, 2018 (values.toml, isr-13-date): named without a rating it could not read.
  await expect(chart(page).getByRole("link", { name: /^ISR 13, December 28, 2018\. How lane\./ })).toHaveCount(1);
  // Try again in the alert brings the chart back and takes you to it (the 23 brief, section 8.4).
  await page.route("**/api/projects/P130164/timeline", async (route) => route.fulfill({ contentType: "application/json", body: await recorded("timeline-p130164.json") }));
  await page.locator("[data-timeline-card] [data-alert]").getByRole("button", { name: "Try again" }).click();
  await expect(chart(page).locator("[data-disagreement-line]")).toHaveCount(2);
  await expect(page.locator("[data-timeline-card]")).toBeFocused();
});

test("the public preview of a project still under way hides its disagreements, and no alert says the page shows the staff view", async ({ page }) => {
  await open(page, "/projects/P156634/timeline?view=public", 1440, {
    "/api/projects/P156634": { body: await recorded("project-p156634.json") },
    "/api/projects/P156634/timeline?view=public": { body: await recorded("timeline-p156634-public.json") },
  });

  await expect(page.locator("[data-timeline-card]")).toContainText("I don't show disagreements on active projects in the public view");
  await expect(page.locator("[data-timeline-subtitle]")).toHaveText("Each mark is a report, an event or a record.");
  await expect(page.locator("main [data-alert]")).toHaveCount(0);
});
