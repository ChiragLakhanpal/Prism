// The package's steps as a tracker (ticket 115) at seam 4: the package workspace against the steps answers the server
// recorded (tests/record_steps_api.py), which tests/test_step_routes.py holds the server to. Every state, date and day
// count on the tracker is the server's; the browser counts nothing (CLAUDE.md rule 1).
//
// The literal values come from independent sources: the states and days late from tests/ground_truth/values.toml's
// [step_tracker], worked out by hand; the showcase's planned dates from its plan-541055 values (the Procurement Plan
// of October 9, 2026, page 3) and its signing from award-541055-signed (contract 1903781 in World Bank contract awards
// data); the hand-made set's dates from tests/step_set.py; and the step labels from the blueprint's "Step labels taken
// from STEP".
import { scan } from "./axe";
import type { Locator, Page } from "@playwright/test";
import { expect, recorded, test } from "./mocked";

type Answer = { status?: number; body: string };

async function serve(page: Page, answers: Record<string, Answer>) {
  await page.setViewportSize({ width: 1440, height: 900 });
  const all: Record<string, Answer> = {
    "/api/me": { body: await recorded("me.json") },
    "/api/freshness": { body: await recorded("freshness.json") },
    ...answers,
  };
  await page.route("**/api/**", (route) => {
    const answer = all[new URL(route.request().url()).pathname];
    if (!answer) return route.fulfill({ status: 404, json: { detail: "Not Found" } });
    return route.fulfill({ status: answer.status ?? 200, contentType: "application/json", body: answer.body });
  });
}

async function openStepRow(page: Page, ref: string, files: { pkg: string; comparables: string; steps: string }) {
  const api = `/api/packages/${ref}`;
  await serve(page, {
    [api]: { body: await recorded(files.pkg) },
    [`${api}/comparables`]: { body: await recorded(files.comparables) },
    [`${api}/steps`]: { body: await recorded(files.steps) },
  });
  await page.goto(`/packages/${ref}`);
  await expect(tracker(page).getByRole("listitem")).toHaveCount(6);
}

const tracker = (page: Page) => page.locator("[data-step-tracker]");
const items = (page: Page) => tracker(page).getByRole("listitem");
const words = async (locator: Locator) => (await locator.allInnerTexts()).map((text) => text.replace(/\s+/g, " ").trim());
const states = (page: Page) => items(page).evaluateAll((all) => all.map((item) => item.getAttribute("data-step-state")));

// What each state's node looks like, read from the page: a tick, a fill, an outline, the warning colour, or dots.
async function forms(page: Page) {
  return tracker(page)
    .locator("[data-step-node]")
    .evaluateAll((nodes) =>
      nodes.map((node) => {
        const style = getComputedStyle(node);
        const fill = node.querySelector("[data-node-fill]");
        return {
          tick: node.querySelector("[data-node-tick]") !== null,
          filled: style.backgroundColor === "rgb(56, 128, 4)" || (fill !== null && getComputedStyle(fill).backgroundColor === "rgb(0, 67, 112)"),
          border: style.borderTopStyle,
          warning: style.borderTopColor === "rgb(137, 96, 1)",
        };
      }),
    );
}

const FORM = {
  done: { tick: true, filled: true, border: "solid", warning: false },
  next: { tick: false, filled: true, border: "solid", warning: false },
  planned: { tick: false, filled: false, border: "solid", warning: false },
  late: { tick: false, filled: false, border: "solid", warning: true },
  unknown: { tick: false, filled: false, border: "dotted", warning: false },
};

test("on the fixture's showcase package the signing is done on the contract awards' date, the completion is late by the days the server counted, the steps before the signing have no date, and a package from a sentence has none", async ({ page }) => {
  await openStepRow(page, "KE-NWWDA-541055-CW-RFB", {
    pkg: "package-ke-nwwda-541055.json",
    comparables: "comparables-ke-nwwda-541055.json",
    steps: "steps-ke-nwwda-541055.json",
  });

  await expect(tracker(page).getByRole("heading", { level: 2 })).toHaveText("Where the steps stand");
  expect(await words(items(page))).toEqual([
    "Bid invitation (SPN) No date The plan gives no actual date",
    "Bidding document issued No date Not in the plan",
    "Bid opening No date The plan gives no actual date",
    "Bid evaluation report No date The plan gives no actual date",
    "Contract signed Done June 22, 2026",
    "Contract completed Late by 89 days Planned for July 31, 2026",
  ]);
  expect(await states(page)).toEqual(["unknown", "unknown", "unknown", "unknown", "done", "late"]);
  expect(await forms(page)).toEqual([FORM.unknown, FORM.unknown, FORM.unknown, FORM.unknown, FORM.done, FORM.late]);
  await expect(tracker(page).locator("[data-source]")).toHaveText(
    "Source: The Procurement Plan of October 9, 2026 and World Bank contract awards data. I count days late to October 28, 2026.",
  );
  await expect(tracker(page).locator("[data-tracker-status]")).toHaveCount(0);
  // Section 2's list stays where it was, under "Show the steps".
  await expect(page.locator("section#planned-dates [data-section-toggle]")).toHaveText("Show the steps");
  await page.waitForFunction(() => document.getAnimations().every((animation) => animation.playState !== "running"));
  const results = await scan(page, "[data-step-tracker]");
  expect(results.violations.map((v) => `${v.id}: ${v.nodes.map((node) => node.target.join(" ")).join(", ")}`)).toEqual([]);

  // A package from a sentence has no plan, so none of its steps has a date.
  await page.unrouteAll();
  await serve(page, {
    "/api/planned-packages/pkg-000000000001": { body: await recorded("planned-package-rural-roads.json") },
    "/api/planned-packages/pkg-000000000001/steps": { body: await recorded("steps-planned-rural-roads.json") },
  });
  await page.goto("/packages/pkg-000000000001");
  await expect(items(page)).toHaveCount(6);
  expect(await states(page)).toEqual(Array(6).fill("unknown"));
  expect(await forms(page)).toEqual(Array(6).fill(FORM.unknown));
  // Each step reads its label and "No date" once; the note under the list says why, once.
  expect(await words(items(page))).toEqual(
    ["Bid invitation (SPN)", "Bidding document issued", "Bid opening", "Bid evaluation report", "Contract signed", "Contract completed"].map(
      (label) => `${label} No date`,
    ),
  );
  await expect(tracker(page).locator("[data-source]")).toHaveCount(0);
  await expect(tracker(page).locator("[data-tracker-note]")).toHaveText("No Procurement Plan gives dates for these steps yet.");
});

test("done steps carry a tick and their actual dates, the next step is filled, and the tracker is a list whose nodes take focus in turn; nothing moves under reduced motion", async ({ page }) => {
  const hand = { pkg: "package-ke-hand-900000.json", comparables: "comparables-ke-hand-900000.json" };
  await openStepRow(page, "KE-HAND-900000-CW-RFB", { ...hand, steps: "steps-ke-hand-900000-done.json" });

  expect(await words(items(page))).toEqual([
    "Bid invitation (SPN) Done March 10, 2021",
    "Bidding document issued Done March 30, 2021",
    "Bid opening Done April 20, 2021",
    "Bid evaluation report Done May 20, 2021",
    "Contract signed Done July 20, 2021",
    "Contract completed Late by 21 days Planned for June 10, 2022",
  ]);
  expect(await forms(page)).toEqual([FORM.done, FORM.done, FORM.done, FORM.done, FORM.done, FORM.late]);

  // A list for screen readers, named by its heading; Tab lands on the step that needs a look, and the arrow keys,
  // Home and End move along the nodes.
  const list = page.getByRole("list", { name: "Where the steps stand" });
  await expect(list.getByRole("listitem")).toHaveCount(6);
  for (let tabs = 0; tabs < 40 && !(await items(page).nth(5).evaluate((el) => el === document.activeElement)); tabs++) await page.keyboard.press("Tab");
  await expect(items(page).nth(5)).toBeFocused();
  await page.keyboard.press("ArrowLeft");
  await expect(items(page).nth(4)).toBeFocused();
  await page.keyboard.press("Home");
  await expect(items(page).nth(0)).toBeFocused();
  await page.keyboard.press("ArrowRight");
  await expect(items(page).nth(1)).toBeFocused();
  await page.keyboard.press("End");
  await expect(items(page).nth(5)).toBeFocused();

  // Before any step happened: the first step is next, and its fill enters in 160 ms.
  await page.unrouteAll();
  await openStepRow(page, "KE-HAND-900000-CW-RFB", { ...hand, steps: "steps-ke-hand-900000.json" });
  expect(await words(items(page))).toEqual([
    "Bid invitation (SPN) Next Planned for March 1, 2021",
    "Bidding document issued Planned for March 8, 2021",
    "Bid opening Planned for April 7, 2021",
    "Bid evaluation report Planned for April 30, 2021",
    "Contract signed Planned for June 10, 2021",
    "Contract completed Planned for June 10, 2022",
  ]);
  expect(await forms(page)).toEqual([FORM.next, ...Array(5).fill(FORM.planned)]);
  const fill = tracker(page).locator("[data-node-fill]");
  expect(await fill.evaluate((el) => getComputedStyle(el).transitionDuration)).toContain("0.16s");

  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.reload();
  await expect(fill).toBeVisible();
  expect(await fill.evaluate((el) => getComputedStyle(el).transitionDuration.split(",").every((part) => parseFloat(part) === 0))).toBe(true);
  expect(await page.evaluate(() => document.getAnimations().length)).toBe(0);
});
