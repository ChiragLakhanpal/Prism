// Following, the follow control and the mission brief (ticket 37) at seam 4, against the answers recorded from the
// server on the fixture in tests/fixtures/api (tests/record_following_api.py), which tests/test_following.py checks
// the server against. The states the fixture cannot reach are the following-made-up-*.json answers, made up from
// the real one and saying so; they are used for layout and states only, never as findings.
import AxeBuilder from "@axe-core/playwright";
import type { Page } from "@playwright/test";
import { expect, recorded, test } from "./mocked";

const WCAG_22_AA = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];
const FOLLOWING = "/projects/following";
// The ticket's four lines, word for word (criterion 1).
const LINES = [
  "KE-NWWDA-541055-CW-RFB passed its planned completion (July 31, 2026) with no signed contract.",
  "KE-NWWDA-229129-CW-RFB was signed at about 4 times its estimate.",
  "KE-CWSB-567630-CW-DIR, a US$2.6 million direct-selection works activity, first appears in the August 17, 2026 plan.",
  "The closing date has moved three times since 2022.",
];
// Criterion 2: the Status column header's text.
const STATUS_HEADER = "Status: needs a look means three signals or one strong one; a signal is a reason to look, not a finding";

type Answer = { status?: number; body: string; delay?: number };

async function serve(page: Page, answers: Record<string, Answer>) {
  const asked: string[] = [];
  const all: Record<string, Answer> = {
    "/api/me": { body: await recorded("me-staff.json") },
    "/api/freshness": { body: await recorded("freshness.json") },
    "POST /api/evidence/opened": { body: '{"recorded":true}' },
    ...answers,
  };
  await page.route("**/api/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    asked.push(`${request.method()} ${url.pathname}${url.search}`);
    const answer = all[`${request.method()} ${url.pathname}${url.search}`] ?? all[`${request.method()} ${url.pathname}`] ?? all[url.pathname];
    if (!answer) return route.fulfill({ status: 404, json: { detail: "Not Found" } });
    if (answer.delay) await new Promise((resolve) => setTimeout(resolve, answer.delay));
    return route.fulfill({ status: answer.status ?? 200, contentType: "application/json", body: answer.body });
  });
  return asked;
}

async function openFollowing(page: Page, { file = "following-p156634.json", width = 1440, path = FOLLOWING, answers = {} }:
  { file?: string; width?: number; path?: string; answers?: Record<string, Answer> } = {}) {
  await page.setViewportSize({ width, height: 900 });
  const asked = await serve(page, { "/api/following": { body: await recorded(file) }, ...answers });
  await page.goto(path);
  await expect(page.locator("[data-following-page]:not([data-following-page=loading])")).toBeVisible();
  return asked;
}

async function axe(page: Page) {
  const results = await new AxeBuilder({ page }).withTags(WCAG_22_AA).analyze();
  return results.violations.map((v) => `${v.id}: ${v.nodes.map((node) => node.target.join(" ")).join(", ")}`);
}

const view = (page: Page) => page.locator("[data-following-view]:visible");

test("P156634's row needs a look with the four signals of the Following wireframe, and the Status header says what that means", async ({ page }) => {
  await openFollowing(page);
  const table = page.locator("[data-following-view=table]");
  const row = table.locator("[data-project-row=P156634]");

  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Projects");
  await expect(page.getByRole("navigation", { name: "Projects pages" }).getByRole("link", { name: "Following (2)" })).toHaveAttribute("aria-current", "page");
  await expect(page.getByRole("heading", { level: 2, name: "You follow two projects. One needs a look and one has closed." })).toBeVisible();
  await expect(row.locator("[data-badge=needs-a-look]")).toHaveText("Needs a look");
  await expect(row.locator("[data-signal-count]")).toHaveText("4 signals");
  const lines = row.getByRole("list", { name: "Signals for Water and Sanitation Development Project" }).locator("li");
  await expect(lines).toHaveCount(4);
  for (const [index, line] of LINES.entries()) await expect(lines.nth(index)).toContainText(line);
  await expect(row.locator("[data-meta]")).toHaveText("Kenya, P156634. It closes on Oct 31, 2026.");
  await expect(row.getByRole("link", { name: "Water and Sanitation Development Project" })).toHaveAttribute("href", "/projects/P156634");
  expect(await table.locator("thead th").first().evaluate((cell) => cell.textContent)).toBe(STATUS_HEADER);
  // One action per row, secondary, and the page has no solid button.
  await expect(row.getByRole("button", { name: "Add to mission brief, Water and Sanitation Development Project" })).toBeVisible();
  await expect(page.locator("main [data-button=primary]")).toHaveCount(0);
  // The closed project folds away with a count, and opens in place.
  await expect(table.getByText("One project has closed or is in the pipeline.")).toBeVisible();
  await expect(table.locator("[data-project-row=P130164]")).toBeHidden();
  await table.getByRole("button", { name: "Show it" }).click();
  await expect(table.locator("[data-project-row=P130164]")).toContainText("Closed");
  await expect(page.locator("[data-count-line]:visible")).toHaveText("Showing 2 of 2 projects you follow");
  // Never replayed yet on the fixture: the track record says so, and types no number.
  await expect(page.locator("[data-track-record=none]")).toContainText("I haven't replayed these checks on past dates yet");
});

test("a signal's marker opens the plan row behind it in the evidence drawer", async ({ page }) => {
  await openFollowing(page);
  const marker = page.locator("[data-following-view=table] [data-signal=completion_passed] [data-citation]");

  await marker.click();

  await expect(page).toHaveURL(/evidence=strata\.silver\.plan_rows%3A40132287%2FKE-NWWDA-541055-CW-RFB/);
  await expect(page.locator("[data-evidence-drawer]")).toContainText("Pending Implementation");
});

test("below a 1,200 px page area each row is a block, with the Status and Next definitions above the list", async ({ page }) => {
  for (const width of [1024, 390]) {
    await openFollowing(page, { width });
    await expect(view(page)).toHaveAttribute("data-following-view", "list");
    await expect(page.locator("[data-list-definitions]")).toContainText(`${STATUS_HEADER}.`);
    const lines = page.locator("[data-following-view=list] [data-project-row=P156634] [data-signal]");
    for (const [index, line] of LINES.entries()) await expect(lines.nth(index)).toContainText(line);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  }
});

test("Following has no WCAG 2.2 AA violations at 1440, 1024 and 390 px, with its made-up states and the fold open", async ({ page }) => {
  for (const width of [1440, 1024, 390]) {
    await openFollowing(page, { width, file: "following-made-up-states.json" });
    await view(page).getByRole("button", { name: /Show them|Show it/ }).click();
    await page.getByRole("button", { name: "Show the seven checks" }).click();
    expect(await axe(page), `at ${width} px`).toEqual([]);
  }
  await expect(page.locator("[data-following-view=list] [data-badge=not-checked]")).toHaveText("Not checked");
  await expect(page.locator("[data-following-view=list] [data-partial]")).toContainText("I couldn't run two of the seven checks, because I haven't read an ISR for it.");
  await expect(page.locator("[data-coverage-line]")).toBeVisible();
  await expect(page.locator("[data-following-view=list] [data-existing-brief]")).toContainText("You started one on Oct 23, 2026. Open the draft");
  await expect(page.locator("[data-following-view=list] [data-tag]").first()).toHaveText("Strong signal");
});

test("the track record states the stored counts, says when they are too few to read as a rate, and never computes one", async ({ page }) => {
  await openFollowing(page, { file: "following-made-up-track-record.json" });
  const track = page.locator("[data-track-record=stored]");

  await expect(track.locator("[data-track-status]")).toHaveText(
    "When I replayed these checks on past dates, nine of the 14 projects that needed a look later extended their closing date. " +
      "So did 11 of the 26 worth watching, and seven of the 38 with no signals. Only 14 projects needed a look when I replayed the checks, " +
      "too few to say how much the status usually means.",
  );
  await expect(track).toContainText("These counts say what happened next, not why.");
  await track.getByRole("button", { name: "Show the seven checks" }).click();
  await expect(track.locator("[data-track-check=above_estimate]")).toContainText("four of nine");
  await expect(track.locator("[data-track-check=above_estimate]")).toContainText("Too few projects to read as a rate.");
  await expect(track.locator("tfoot")).toContainText("seven of 38");
});

test("Following refuses a viewer without the World Bank staff role, and a preview shows no list", async ({ page }) => {
  await openFollowing(page, { answers: { "/api/me": { body: await recorded("me-not-staff.json") }, "/api/following": { status: 403, body: await recorded("following-not-staff.json") } } });
  await expect(page.getByRole("heading", { level: 2, name: "I show Following only to World Bank staff." })).toBeVisible();
  await expect(page.getByRole("navigation", { name: "Projects pages" })).toHaveCount(0);

  await openFollowing(page, { path: `${FOLLOWING}?view=public` });
  await expect(page.getByRole("heading", { level: 2, name: "The public view has no Following list." })).toBeVisible();
});

test("the Projects tab opens Following for World Bank staff, and All projects shows the sub-tabs", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await serve(page, { "/api/projects": { body: await recorded("projects.json") } });
  await page.goto("/projects");
  await expect(page.locator("[data-projects-page=ready]")).toBeVisible();

  await expect(page.locator("[data-nav-bar] [data-nav-tab=projects]")).toHaveAttribute("href", FOLLOWING);
  await expect(page.getByRole("navigation", { name: "Projects pages" }).getByRole("link", { name: "All projects" })).toHaveAttribute("aria-current", "page");
});

test("Follow this project waits for the server, then says you follow it and offers Unfollow", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await serve(page, {
    "/api/projects/P156634": { body: await recorded("project-p156634.json") },
    "/api/projects/P156634/summary": { body: await recorded("summary-p156634.json") },
    "GET /api/projects/P156634/follow": { body: await recorded("follow-off.json") },
    "PUT /api/projects/P156634/follow": { body: await recorded("follow-on.json"), delay: 300 },
  });
  await page.goto("/projects/P156634");
  const follow = page.getByRole("group", { name: "Follow" });

  await follow.getByRole("button", { name: "Follow this project" }).click();
  await expect(follow).toHaveAttribute("aria-busy", "true");
  await expect(follow.getByText("You follow this project.")).toBeVisible();
  await expect(follow.getByRole("button", { name: "Unfollow" })).toBeFocused();
  expect(await axe(page)).toEqual([]);
});

test("Add to mission brief writes the five parts, then becomes the draft in place, with numbers from tools and citations", async ({ page }) => {
  await openFollowing(page, {
    answers: {
      "POST /api/drafts": { body: await recorded("drafts-write-mission-brief.sse"), delay: 300 },
      "GET /api/drafts/draft-0001": { body: await recorded("drafts-mission-brief-draft.json") },
    },
  });
  await page.locator("[data-following-view=table]").getByRole("button", { name: /Add to mission brief/ }).click();

  await expect(page).toHaveURL(/\/drafts\/new\?kind=mission_brief&pid=P156634$/);
  await expect(page.locator("[data-brief-parts=writing] h3")).toHaveText(
    ["Latest Procurement Plans", "Awards since the last ISR", "Rating history", "Disbursement", "Closing check"]);
  await expect(page).toHaveURL("/drafts/draft-0001");
  const parts = page.locator("[data-brief-parts=draft] [data-brief-part]");
  await expect(parts).toHaveCount(5);
  await expect(page.getByRole("heading", { level: 2, name: "I drafted all five parts of the mission brief." })).toBeVisible();
  const awards = page.locator("[data-brief-part=awards]");
  await expect(awards).toContainText("Two contracts were signed after the ISR dated June 30, 2026, for US$2,544,201.48 together.");
  await expect(awards.locator("[data-brief-view=table] tbody tr")).toHaveCount(2);
  await expect(awards.locator("[data-brief-view=table] tbody tr").first()).toContainText("2,432,125.50");
  await expect(page.locator("[data-check-line]")).toContainText(
    "Not checked: whether the project's published records are complete, or whether this brief covers what your mission needs.");
  expect(await axe(page)).toEqual([]);
});
