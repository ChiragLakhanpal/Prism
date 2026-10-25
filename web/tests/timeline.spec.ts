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
    [`/api/evidence?id=${PDO}`]: await file("evidence-disagreement-p130164-pdo.json"),
    "/api/evidence?id=doc:26733307": await file("evidence-doc-p130164-isr-7.json"),
    "/api/evidence?id=doc:31525018": await file("evidence-doc-p130164-icr.json"),
    "/api/evidence?id=ratings:P130164:pdo_progress:1-9": await file("evidence-ratings-p130164-1-9.json"),
    "/api/evidence?id=strata.gold.passage:31525018/v1/78": await file("evidence-icr-p130164-78.json"),
    "/api/evidence?id=strata.gold.passage:26733307/v1/s4": await file("evidence-isr-p130164-7-s4.json"),
  };
}

async function open(page: Page, path = "/projects/P130164/timeline", width = 1440) {
  const requests: Request[] = [];
  page.on("request", (request) => requests.push(request));
  await page.setViewportSize({ width, height: 900 });
  const unrecorded = await mockApi(page, await timelineApi());
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
    [9, "Implementation Completion and Results Report, October 10, 2019. Disagrees with ISR 7, the ICR Review. Why lane. Item 10 of 14."],
    [10, "2 reports disagree: ISR 7, August 26, 2016, and the ICR, October 10, 2019. Strata leans on the ICR. Item 11 of 14."],
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
  // The ISR series is bands, never a dashed line: each line joins two reports of different kinds.
  await expect(chart(page).locator("[data-disagreement-line]")).toHaveCount(2);
  // role img with the alt text as its name; a time axis with no title and five ticks, on whole years.
  const drawing = chart(page).locator("svg[role=img]");
  await expect(drawing).toHaveAccessibleName(/^Timeline of P130164 from 2013 to 2023 in three lanes/);
  await expect(chart(page).locator("[data-tick]")).toHaveText(["2014", "2016", "2018", "2020", "2022"]);
  // Every mark keeps its label at the 1246 px chart.
  await expect(chart(page).locator("[data-mark-label]")).toHaveCount(9);
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
  await expect(card).toContainText("For a judgment of how a project went, I lean on the later, more independent report, here ICR paragraph 78. I keep ISR 7 beside it.");
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
  expect(Math.round((await chart(page).boundingBox())!.width)).toBe(524);
  await expect(chart(page).locator("[data-mark-label]")).toHaveCount(9);

  await item(page, "doc:26733307").click();
  await expect(dialog.getByRole("heading", { level: 2 })).toHaveText("ISR 7, August 26, 2016");
  await expect(dialog.locator("[data-document-fields]")).toContainText("Disclosed");
  await expect(dialog.locator("[data-claim-line]")).toContainText("ISR 7 and the ICR disagree about progress towards the project development objective (PDO) at the mid-term review.");
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
  await expect(chart(page).locator("[data-disagreement-line]")).toHaveCount(0);
});

test("Show the table lists every item in arrow-key order, under its caption", async ({ page }) => {
  await open(page);
  const toggle = page.getByRole("button", { name: "Show the table" });
  await toggle.click();
  await expect(page.getByRole("button", { name: "Hide the table" })).toHaveAttribute("aria-expanded", "true");
  const table = page.locator("[data-timeline-table]");
  await expect(table).toContainText("Everything on the timeline of Rajasthan Road Sector Modernization, in date order.");
  await expect(table).toContainText("Showing all 14 items.");
  await expect(table.locator("tbody tr")).toHaveCount(14);
  await expect(table.locator("tbody tr").nth(3)).toContainText("Disagrees with the ICR.");
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
    },
  ]);
  expect(await axe(page, "[data-answer-panel]")).toEqual([]);
});
