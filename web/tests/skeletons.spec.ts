// Ticket 59, criterion 3: each skeleton the ticket names stands where its section will be drawn. A test holds the
// section's one /api answer, notes where the skeleton sits at 320, 390, 450, 496, 640, 767, 768, 1024 and 1440 px,
// releases the answer and notes where the drawn section sits at the same widths (held.ts). The drawn section's top is
// within 24 px of the skeleton's, and its end within 48 px. A section that lists rows ends, for this measure, at its
// first row's end, since a skeleton cannot know how many rows will come; one that holds a fixed set of parts ends at its
// end.
import { hubApi } from "./hub-api";
import { jumps, skeletonShift } from "./held";
import { expect, mockApi, recorded, test } from "./mocked";

type Answer = { status?: number; body: string };
const shell = async (): Promise<Record<string, Answer>> => ({
  "/api/me": { body: await recorded("me.json") },
  "/api/freshness": { body: await recorded("freshness.json") },
});

const PLAN = "/projects/P156634/procurement/northern-water-works-development-agency/2026-10-09";

// The plan check answers with two requests: the check, and what changed since the version before (/changes), whose
// line sits under the method sentence. Both are answered from their recordings, so the test measures the page a person
// sees: the section runs from the head's top to the activities panel's name, under the finding and the change line.
const planAnswers = async (): Promise<Record<string, Answer>> => ({
  ...(await shell()),
  [`/api${PLAN}`]: { body: await recorded("check-plan-p156634-nwwda-2026-10-09.json") },
  [`/api${PLAN}/changes`]: { body: await recorded("changes-nwwda-2026-10-09.json") },
});
const toActivities = { from: "[data-plan-header]", to: "[data-section=activities] [data-zone-name]" };

test("the plan check's head and narration hold the head, the finding and the change line's place", async ({ page }) => {
  await mockApi(page, await planAnswers());
  const shifts = await skeletonShift(page, {
    path: PLAN,
    hold: `**/api${PLAN}`,
    answer: { body: await recorded("check-plan-p156634-nwwda-2026-10-09.json") },
    skeleton: toActivities,
    drawn: toActivities,
    loaded: "[data-plan-check]",
  });
  expect(jumps(shifts)).toEqual([]);
});

// The critique of round 1: when the comparison is the slower answer, the skeleton holds its line's place too.
test("while what changed is still loading, the plan check's skeleton holds the change line's place", async ({ page }) => {
  await mockApi(page, await planAnswers());
  const shifts = await skeletonShift(page, {
    path: PLAN,
    hold: `**/api${PLAN}/changes`,
    answer: { body: await recorded("changes-nwwda-2026-10-09.json") },
    skeleton: toActivities,
    drawn: toActivities,
    loaded: "[data-plan-check]",
  });
  expect(jumps(shifts)).toEqual([]);
});

const PACKAGE = "/api/packages/KE-NWWDA-541055-CW-RFB";
const packageAnswers = async (): Promise<Record<string, Answer>> => ({
  ...(await shell()),
  [PACKAGE]: { body: await recorded("package-ke-nwwda-541055.json") },
  [`${PACKAGE}/comparables`]: { body: await recorded("comparables-ke-nwwda-541055.json") },
  [`${PACKAGE}/estimate`]: { body: await recorded("estimate-ke-nwwda-541055.json") },
  [`${PACKAGE}/risks`]: { body: await recorded("risks-ke-nwwda-541055.json") },
  [`${PACKAGE}/steps`]: { body: await recorded("steps-ke-nwwda-541055.json") },
  [`${PACKAGE}/rebidding`]: { body: await recorded("rebidding-ke-nwwda-541055.json") },
});

test("the past range's skeleton puts the chart where it will start and ends the block where it will end", async ({ page }) => {
  await mockApi(page, await packageAnswers());
  const shifts = await skeletonShift(page, {
    path: "/packages/KE-NWWDA-541055-CW-RFB",
    hold: `**${PACKAGE}/comparables`,
    answer: { body: await recorded("comparables-ke-nwwda-541055.json") },
    // From the chart's top to the end of the block's foot strip, before "Advertised again".
    skeleton: { from: "[data-chart-skeleton]", to: "[data-past-range] [data-block=took] + [data-foot-strip]" },
    drawn: { from: "[data-range-chart]", to: "[data-past-range] [data-block=took] + [data-foot-strip]" },
  });
  expect(jumps(shifts)).toEqual([]);
});

// Item 55 and the critique of round 1: the card that holds both blocks, the past range and "Advertised again", ends
// within 48 px of where its skeleton ended, so "Where the steps stand" and sections 2 to 5 stay put when the comparables
// arrive. On the first load "Advertised again" holds its own skeleton under the past range's.
test("section 1's card ends where its skeleton ended, with Advertised again's skeleton under the past range's", async ({ page }) => {
  await mockApi(page, await packageAnswers());
  const shifts = await skeletonShift(page, {
    path: "/packages/KE-NWWDA-541055-CW-RFB",
    hold: `**${PACKAGE}/comparables`,
    answer: { body: await recorded("comparables-ke-nwwda-541055.json") },
    skeleton: { from: "[data-section=took]", to: "[data-section=took]" },
    drawn: { from: "[data-section=took]", to: "[data-section=took]" },
    loaded: "[data-range-chart]",
    ready: (page) => expect(page.locator("[data-rebidding=found]")).toBeVisible(),
  });
  expect(jumps(shifts)).toEqual([]);
});

test("Advertised again's skeleton holds the block's place under section 1", async ({ page }) => {
  await mockApi(page, await packageAnswers());
  const shifts = await skeletonShift(page, {
    path: "/packages/KE-NWWDA-541055-CW-RFB",
    hold: `**${PACKAGE}/rebidding`,
    answer: { body: await recorded("rebidding-ke-nwwda-541055.json") },
    skeleton: "[data-rebidding]",
    drawn: "[data-rebidding]",
    loaded: "[data-rebidding=found]",
  });
  expect(jumps(shifts)).toEqual([]);
});

test("a project's head holds the name's lines and one agency line", async ({ page }) => {
  await mockApi(page, await hubApi());
  const shifts = await skeletonShift(page, {
    path: "/projects/P130164",
    hold: "**/api/projects/P130164",
    answer: { body: await recorded("project-p130164.json") },
    skeleton: "[data-project-head]",
    drawn: "[data-project-head]",
    loaded: "[data-project-page=ready]",
  });
  expect(jumps(shifts)).toEqual([]);
});

// Data readiness's tables (ticket 104) hold as many skeleton rows as the tables will have, so each is measured whole.
for (const [id, open] of [["sources", false], ["shelf", true]] as const) {
  test(`Data readiness's ${id === "sources" ? "Sources" : "hardest documents"} skeleton rows are as tall as the rows that replace them`, async ({ page }) => {
    await mockApi(page, { ...(await shell()), "/api/data/sources": { body: await recorded("data-sources.json") } });
    const table = `[data-readiness-table=${id}] [data-table-view]`;
    const shifts = await skeletonShift(page, {
      path: "/data",
      hold: "**/api/data/readiness*",
      answer: { body: await recorded("data-readiness.json") },
      // The hardest documents start as a closed row, which opens in place while the page loads too.
      prepare: open ? (page) => page.locator(`[data-readiness-table=${id}]`).getByRole("button", { name: "Show the documents" }).click() : undefined,
      skeleton: { from: "[data-readiness=loading] [data-lead]", to: `[data-readiness=loading] ${table}` },
      drawn: { from: "[data-readiness=ready] [data-lead]", to: `[data-readiness=ready] ${table}` },
    });
    expect(jumps(shifts)).toEqual([]);
  });
}

const reviewer = async (): Promise<Record<string, Answer>> => ({ ...(await shell()), "/api/lessons/me": { body: await recorded("lessons-me-reviewer.json") } });

test("the review queue's skeleton holds the lead, the quote check's caption and a first row", async ({ page }) => {
  await mockApi(page, await reviewer());
  const shifts = await skeletonShift(page, {
    path: "/lessons/review",
    hold: "**/api/lessons/review?*",
    answer: { body: await recorded("lessons-queue.json") },
    skeleton: { from: "[data-queue=loading]", to: "[data-queue=loading] [data-skeleton-row]" },
    drawn: { from: "[data-queue=ready]", to: "[data-queue=ready] [data-queue-row]" },
  });
  expect(jumps(shifts)).toEqual([]);
});

test("a review page's skeleton holds the head, the evidence title and its first card", async ({ page }) => {
  await mockApi(page, await reviewer());
  const shifts = await skeletonShift(page, {
    path: "/lessons/review/new-e903b07ad1",
    hold: "**/api/lessons/review/new-e903b07ad1",
    answer: { body: await recorded("lessons-item-recommend.json") },
    skeleton: { from: "main [data-breadcrumb]", to: "[data-review-page=loading] [data-skeleton-card]" },
    drawn: { from: "main [data-breadcrumb]", to: "[data-review-work] section:first-of-type > div > :first-child" },
    loaded: "[data-review-work]",
  });
  expect(jumps(shifts)).toEqual([]);
});

// The draft in a window 640 px tall, as ticket 59 asks, so the draft bar does not stick on a phone.
test("a draft's skeleton holds its head, its lede, its check line and its first note", async ({ page }) => {
  await mockApi(page, { ...(await shell()), "/api/drafts/existing": { body: '{"draft":null}' } });
  const shifts = await skeletonShift(page, {
    path: "/drafts/draft-0001",
    hold: "**/api/drafts/draft-0001",
    answer: { body: await recorded("drafts-review-notes-draft.json") },
    height: 640,
    skeleton: { from: "[data-draft-page=loading]", to: "[data-draft-page=loading] table tbody tr, [data-draft-page=loading] ul > li" },
    drawn: { from: "[data-draft-page]:not([data-draft-page=loading])", to: "[data-draft-notes] tbody tr, [data-draft-notes] li" },
  });
  expect(jumps(shifts)).toEqual([]);
});

test("the Packages list's skeleton holds its title, its count line and a first row with its caption", async ({ page }) => {
  await mockApi(page, { ...(await shell()), "/api/uploads": { body: await recorded("uploads-list-nwwda.json") } });
  const firstRow = (zone: string) => ({ from: zone, to: `${zone} [data-table-view] tbody tr, ${zone} [data-table-view] > li` });
  const shifts = await skeletonShift(page, {
    path: "/packages",
    hold: "**/api/planned-packages",
    answer: { body: await recorded("planned-packages-list.json") },
    skeleton: firstRow("[data-zone][aria-busy=true]"),
    drawn: firstRow("[data-zone]:has([data-count-line])"),
  });
  expect(jumps(shifts)).toEqual([]);
});
