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

async function serve(page: Page, answers: Record<string, Answer>, size = { width: 1440, height: 900 }) {
  await page.setViewportSize(size);
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

async function openStepRow(
  page: Page,
  ref: string,
  files: { pkg: string; comparables: string; steps: string },
  size?: { width: number; height: number },
  count = 6,
) {
  const api = `/api/packages/${ref}`;
  await serve(
    page,
    {
      [api]: { body: await recorded(files.pkg) },
      [`${api}/comparables`]: { body: await recorded(files.comparables) },
      [`${api}/steps`]: { body: await recorded(files.steps) },
    },
    size,
  );
  await page.goto(`/packages/${ref}`);
  await expect(tracker(page).getByRole("listitem")).toHaveCount(count);
}

const tracker = (page: Page) => page.locator("[data-step-tracker]");
const items = (page: Page) => tracker(page).getByRole("listitem");
const words = async (locator: Locator) => (await locator.allInnerTexts()).map((text) => text.replace(/\s+/g, " ").trim());
const states = (page: Page) => items(page).evaluateAll((all) => all.map((item) => item.getAttribute("data-step-state")));
const tops = (page: Page) => items(page).evaluateAll((all) => all.map((item) => Math.round(item.getBoundingClientRect().top)));
const lefts = (page: Page) => items(page).evaluateAll((all) => all.map((item) => Math.round(item.getBoundingClientRect().left)));

// Each line of text inside a step, as the browser laid it out, that leaves its step's box (the design review's R2-B1).
const spills = (page: Page) =>
  items(page).evaluateAll((all) =>
    all.flatMap((item, index) => {
      const box = item.getBoundingClientRect();
      const walker = document.createTreeWalker(item, NodeFilter.SHOW_TEXT);
      const out: string[] = [];
      for (let node = walker.nextNode(); node; node = walker.nextNode()) {
        const range = document.createRange();
        range.selectNodeContents(node);
        for (const rect of Array.from(range.getClientRects())) {
          if (rect.left < box.left - 0.5 || rect.right > box.right + 0.5) out.push(`step ${index + 1}: ${node.textContent}`);
        }
      }
      return out;
    }),
  );

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
    "Bid invitation (SPN) No date The plan gave no actual date",
    "Bidding document issued No date Not in the plan",
    "Bid opening No date The plan gave no actual date",
    "Bid evaluation report No date The plan gave no actual date",
    "Contract signed Done Jun 22, 2026",
    "Contract completed Late by 89 days Planned for Jul 31, 2026",
  ]);
  expect(await states(page)).toEqual(["unknown", "unknown", "unknown", "unknown", "done", "late"]);
  expect(await forms(page)).toEqual([FORM.unknown, FORM.unknown, FORM.unknown, FORM.unknown, FORM.done, FORM.late]);
  await expect(tracker(page).locator("[data-source]")).toHaveText(
    "Source: The Procurement Plan of October 9, 2026 and World Bank contract awards data. I count days late to October 28, 2026.",
  );
  // The source line ends the card in its foot strip, across the card inside its 1 px edge, as each block of evidence
  // ends (ticket 101's critique, round 2).
  await expect(tracker(page).locator("[data-foot-strip] [data-source]")).toHaveCount(1);
  const [card, strip] = [(await tracker(page).boundingBox())!, (await tracker(page).locator("[data-foot-strip]").boundingBox())!];
  expect([Math.round(strip.x - card.x), Math.round(card.x + card.width - strip.x - strip.width)]).toEqual([1, 1]);
  expect(Math.round(card.y + card.height - strip.y - strip.height)).toBe(1);
  await expect(tracker(page).locator("[data-tracker-status]")).toHaveCount(0);
  // At 1440 px the tracker is a list in the side column (ticket 130). At 1024 px it moves after zone 1, where the page
  // area still holds the six steps in a row, and no step's words reach into the next.
  expect(new Set(await lefts(page)).size).toBe(1);
  await page.setViewportSize({ width: 1024, height: 768 });
  await expect(page.locator("[data-zones] [data-step-tracker]")).toHaveCount(1);
  expect(await spills(page)).toEqual([]);
  expect(new Set(await lefts(page)).size).toBe(6);
  await page.setViewportSize({ width: 1440, height: 900 });
  await expect(page.locator("[data-side-slot] [data-step-tracker]")).toHaveCount(1);
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
    "Bid invitation (SPN) Done Mar 10, 2021",
    "Bidding document issued Done Mar 30, 2021",
    "Bid opening Done Apr 20, 2021",
    "Bid evaluation report Done May 20, 2021",
    "Contract signed Done Jul 20, 2021",
    "Contract completed Late by 21 days Planned for Jun 10, 2022",
  ]);
  await expect(tracker(page).locator("[data-source]")).toHaveText("Source: The Procurement Plan of December 1, 2021. I count days late to July 1, 2022.");
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
    "Bid invitation (SPN) Next Planned for Mar 1, 2021",
    "Bidding document issued Planned for Mar 8, 2021",
    "Bid opening Planned for Apr 7, 2021",
    "Bid evaluation report Planned for Apr 30, 2021",
    "Contract signed Planned for Jun 10, 2021",
    "Contract completed Planned for Jun 10, 2022",
  ]);
  // With no step late, the source line gives the date the states hold on, not a count to it.
  await expect(tracker(page).locator("[data-source]")).toHaveText("Source: The Procurement Plan of December 15, 2020. Dates as of January 15, 2021.");
  expect(await forms(page)).toEqual([FORM.next, ...Array(5).fill(FORM.planned)]);
  const fill = tracker(page).locator("[data-node-fill]");
  expect(await fill.evaluate((el) => getComputedStyle(el).transitionDuration)).toContain("0.16s");

  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.reload();
  await expect(fill).toBeVisible();
  expect(await fill.evaluate((el) => getComputedStyle(el).transitionDuration.split(",").every((part) => parseFloat(part) === 0))).toBe(true);
  expect(await page.evaluate(() => document.getAnimations().length)).toBe(0);
});

// Ticket 130, the design lead's Option W2 of October 29, 2026: from a frame of 75rem the right column holds the plan
// row's facts and then the tracker, which reads its own width there (under its 36rem row), so it is a list, and which
// sticks 24 px under the 56 px bar while you read the zones. Below that frame the page is one column and the tracker
// follows zone 1, a row at 1024 px as ticket 115 drew it.
const SHOWCASE = { pkg: "package-ke-nwwda-541055.json", comparables: "comparables-ke-nwwda-541055.json", steps: "steps-ke-nwwda-541055.json" };

test("at 1440 and 1280 px the tracker is a list in the right column under the plan row's facts, in view under the bar while you read the zones; at 1024 and 390 px it follows zone 1", async ({ page }) => {
  for (const [width, height] of [
    [1440, 900],
    [1280, 800],
  ] as const) {
    await openStepRow(page, "KE-NWWDA-541055-CW-RFB", SHOWCASE, { width, height });
    const side = page.locator("[data-side-slot]");
    await expect(side.locator("[data-step-tracker]"), `${width} px`).toHaveCount(1);
    await expect(page.locator("[data-zones] [data-step-tracker]")).toHaveCount(0);
    const facts = (await side.getByRole("region", { name: "From the plan row" }).boundingBox())!;
    const card = (await tracker(page).boundingBox())!;
    const zones = (await page.locator("[data-zones]").boundingBox())!;
    // Under the facts, 16 px down, in the facts' column, right of the zones.
    expect(Math.round(card.y - facts.y - facts.height), `${width} px`).toBe(16);
    expect([Math.round(card.x), Math.round(card.width)]).toEqual([Math.round(facts.x), Math.round(facts.width)]);
    expect(card.x).toBeGreaterThan(zones.x + zones.width);
    // A list: every step at one left edge, each under the one before.
    expect(new Set(await lefts(page)).size, `${width} px`).toBe(1);
    const down = await tops(page);
    expect(down.every((top, index) => index === 0 || top > down[index - 1]), `${width} px`).toBe(true);
    expect(await spills(page)).toEqual([]);
    // Scrolled a screen and more down, to zone 3 under the bar, the tracker is still whole on screen, 24 px under it.
    await page.locator("[data-zones] > [data-zone]").nth(2).evaluate((zone) => zone.scrollIntoView({ block: "start" }));
    expect(await page.evaluate(() => window.scrollY), `${width} px`).toBeGreaterThan(height);
    await expect(tracker(page)).toBeInViewport({ ratio: 1 });
    expect(Math.round((await tracker(page).boundingBox())!.y), `${width} px`).toBe(56 + 24);
    // The whole page passes axe with the tracker beside the zones (package.spec.ts scans 1440, 1024 and 390 px).
    if (width === 1280) {
      await page.waitForFunction(() => document.getAnimations().every((animation) => animation.playState !== "running"));
      const results = await scan(page);
      expect(results.violations.map((v) => `${v.id}: ${v.nodes.map((node) => node.target.join(" ")).join(", ")}`)).toEqual([]);
    }
    await page.unrouteAll();
  }
  for (const [width, height] of [
    [1024, 768],
    [390, 844],
  ] as const) {
    await openStepRow(page, "KE-NWWDA-541055-CW-RFB", SHOWCASE, { width, height });
    // One column: the tracker follows zone 1, inside the work, and the facts are the head's line.
    await expect(page.locator("[data-side-slot] [data-step-tracker]"), `${width} px`).toHaveCount(0);
    const order = await page
      .locator("[data-zones] > *")
      .evaluateAll((all) => all.map((el) => (el.hasAttribute("data-zone") ? el.querySelector("h2")?.textContent : el.querySelector("[data-step-tracker]") ? "tracker" : null)));
    const named = order.filter(Boolean);
    expect(named.slice(0, 3), `${width} px`).toEqual([expect.stringContaining("How long it took"), "tracker", expect.stringContaining("Planned date for each step")]);
    // A row of six at 1024 px, as ticket 115 drew it; a list at 390.
    expect(new Set(await lefts(page)).size, `${width} px`).toBe(width === 1024 ? 6 : 1);
    await page.unrouteAll();
  }
});

// The round 1 review's B1 and B2: the card sticks only while the window shows all of it, so its Source line is never
// held out of view, and a step the arrow keys move to is brought into view when it is not.
const CONSULTING = { pkg: "package-ke-cwsb-224323.json", comparables: "comparables-ke-cwsb-224323.json", steps: "steps-ke-cwsb-224323.json" };
const sticking = (page: Page) => page.locator("[data-side-sticky]").evaluate((part) => getComputedStyle(part).position);
// A screen and a half down, inside zone 1, whose comparables run to about 3,000 px for this package: the card sticks
// there when it fits, clear of the work's end, which pushes a stuck card up with the page.
const midway = (page: Page) => page.evaluate(() => window.scrollTo(0, Math.round(window.innerHeight * 1.5)));
async function tabToTracker(page: Page) {
  for (let tabs = 0; tabs < 40 && !(await page.evaluate(() => document.activeElement?.hasAttribute("data-step-state"))); tabs++) await page.keyboard.press("Tab");
}

test("in the right column the tracker sticks only while the window shows all of it, and the arrow keys bring a step below the window into view", async ({ page }) => {
  // Six steps at 1280 by 800, at the page's top: the card is in the page's flow and its last steps are below the window.
  await openStepRow(page, "KE-HAND-900000-CW-RFB", { pkg: "package-ke-hand-900000.json", comparables: "comparables-ke-hand-900000.json", steps: "steps-ke-hand-900000.json" }, { width: 1280, height: 800 });
  await tabToTracker(page);
  await expect(items(page).nth(0)).toBeFocused();
  await page.keyboard.press("End");
  await expect(items(page).nth(5)).toBeFocused();
  await expect(items(page).nth(5)).toBeInViewport({ ratio: 1 });
  await page.unrouteAll();

  // A consulting firm's nine steps: taller than a 1280 by 800 window less the bar, so the card scrolls with the page,
  // and the arrow keys still bring its last step into view.
  await openStepRow(page, "KE-CWSB-224323-CS-QCBS", CONSULTING, { width: 1280, height: 800 }, 9);
  await midway(page);
  expect(await sticking(page)).toBe("static");
  await page.evaluate(() => window.scrollTo(0, 0));
  await tabToTracker(page);
  await page.keyboard.press("End");
  await expect(items(page).nth(8)).toBeFocused();
  await expect(items(page).nth(8)).toBeInViewport({ ratio: 1 });

  // In a 1440 by 900 window the nine steps fit under the bar, so the card sticks, whole on screen.
  await page.setViewportSize({ width: 1440, height: 900 });
  await midway(page);
  await expect.poll(() => sticking(page)).toBe("sticky");
  await expect(tracker(page)).toBeInViewport({ ratio: 1 });
  expect(Math.round((await tracker(page).boundingBox())!.y)).toBe(56 + 24);
});

// Ticket 139: section 1's plan line and the tracker read the plan's dates the same way, so section 1 draws its line
// whenever the tracker shows a planned bid invitation and a planned signing, and names the date the tracker shows when
// it cannot draw one. The hand-made set's plan of December 15, 2020 plans the bid invitation for March 1, 2021 and the
// signing for June 10, 2021 (tests/step_set.py, TARGET_PLANNED).
const HAND = "KE-HAND-900000-CW-RFB";
const HAND_FILES = { pkg: "package-ke-hand-900000.json", comparables: "comparables-ke-hand-900000.json", steps: "steps-ke-hand-900000.json" };
const planSentence = (page: Page) => page.locator("[data-past-range] [data-plan-control] p").first();

test("section 1 draws the plan line from the planned bid invitation and the planned signing the tracker shows, and says where its dates come from", async ({ page }) => {
  await openStepRow(page, HAND, HAND_FILES);

  const shown = await words(items(page));
  expect([shown[0], shown[4]]).toEqual(["Bid invitation (SPN) Next Planned for Mar 1, 2021", "Contract signed Planned for Jun 10, 2021"]);
  await expect(page.getByRole("slider")).toHaveAttribute("aria-valuenow", "3.3");
  await page.locator("[data-past-range] [data-finding] [data-num]").filter({ hasText: "3.3" }).first().focus();
  await expect(page.getByRole("tooltip")).toContainText("From the plan's step dates: bid invitation March 1, 2021, contract signed June 10, 2021.");
});

test("a plan that dates the signing but not the bid invitation has no plan line, and section 1 names the date the tracker shows", async ({ page }) => {
  // What the server answers for such a plan, as the walkthrough's KE-SDOR-KIHBT-563865-CW-RFB read on the workspace
  // (tests/test_plan_line.py): the tracker has no date for the bid invitation, so the bidding document is next, and
  // find_comparables has no plan.
  const steps = JSON.parse(await recorded(HAND_FILES.steps));
  const [invitation, bidding] = steps.step_dates.steps;
  Object.assign(invitation, {
    plan_first_date: null,
    plan_first_version_date: null,
    plan_latest_date: null,
    plan_latest_version_date: null,
    abstain_reason: "not_in_plan",
    state: "unknown",
    middle: { planned_date: null, days: null, days_relation: null, longer: null, in10: null },
    cautious: { planned_date: null, days: null, days_relation: null, longer: null, in10: null },
  });
  bidding.state = "next";
  const comparables = JSON.parse(await recorded(HAND_FILES.comparables));
  Object.assign(comparables, { plan: null, frequencies: { ...comparables.frequencies, plan: null } });
  comparables.package.planned_notice_on = null;
  const api = `/api/packages/${HAND}`;
  await serve(page, {
    [api]: { body: await recorded(HAND_FILES.pkg) },
    [`${api}/comparables`]: { body: JSON.stringify(comparables) },
    [`${api}/steps`]: { body: JSON.stringify(steps) },
  });
  await page.goto(`/packages/${HAND}`);
  await expect(items(page)).toHaveCount(6);

  const shown = await words(items(page));
  expect([shown[0], shown[4]]).toEqual(["Bid invitation (SPN) No date Not in the plan", "Contract signed Planned for Jun 10, 2021"]);
  await expect(page.getByRole("slider")).toHaveCount(0);
  await expect(planSentence(page)).toHaveText(
    "The plan's step dates put the signed contract on June 10, 2021 but give no planned notice date, so there is no plan line yet. Type a number of months to compare.",
  );
  await page.getByRole("textbox", { name: "Planned months" }).fill("4");
  await expect(page.getByRole("slider")).toHaveAttribute("aria-valuenow", "4");
  await expect(planSentence(page)).toHaveText("The plan's step dates give no planned notice date, so the line shows the months you typed.");
});
