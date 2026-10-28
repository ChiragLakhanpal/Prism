// Following, the follow control and the mission brief (ticket 37) at seam 4, against the answers recorded from the
// server on the fixture in tests/fixtures/api (tests/record_following_api.py), which tests/test_following.py checks
// the server against. The states the fixture cannot reach are the following-made-up-*.json answers, made up from
// the real one and saying so; they are used for layout and states only, never as findings.
import { scan } from "./axe";
import type { Page } from "@playwright/test";
import { expect, recorded, test, viewAnswers, windowBeside } from "./mocked";

const FOLLOWING = "/projects/following";
// The current mark's fill (DESIGN.md section 2).
const TINT = "rgb(233, 247, 253)";
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
    ...(await viewAnswers()),
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
  const results = await scan(page);
  return results.violations.map((v) => `${v.id}: ${v.nodes.map((node) => node.target.join(" ")).join(", ")}`);
}

const view = (page: Page) => page.locator("[data-following-view]:visible");

test("P156634's row needs a look with the four signals of the Following wireframe, and the Status header says what that means", async ({ page }) => {
  await openFollowing(page);
  const table = page.locator("[data-following-view=table]");
  const row = table.locator("[data-project-row=P156634]");

  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Projects");
  await expect(page.locator("[data-sidebar] [data-sub-item=following]")).toHaveAttribute("aria-current", "page");
  await expect(page.getByRole("heading", { level: 2, name: "You follow two projects. One needs a look and one has closed." })).toBeVisible();
  await expect(row.locator("[data-badge=needs-a-look]")).toHaveText("Needs a look");
  await expect(row.locator("[data-signal-count]")).toHaveText("4 signals");
  const lines = row.getByRole("list", { name: "Signals for Water and Sanitation Development Project" }).locator("li");
  await expect(lines).toHaveCount(4);
  for (const [index, line] of LINES.entries()) await expect(lines.nth(index)).toContainText(line);
  await expect(row.locator("[data-meta]")).toHaveText("Kenya, P156634. It closes on Oct 31, 2026.");
  await expect(row.getByRole("link", { name: "Water and Sanitation Development Project" })).toHaveAttribute("href", "/projects/P156634");
  expect(await table.locator("thead th").first().evaluate((cell) => cell.textContent)).toBe(STATUS_HEADER);
  // "Status" opens the rules, one status a line.
  await table.locator("thead [data-term]").click();
  await expect(page.locator("[data-status-rules] dt")).toHaveText(["Needs a look: ", "Watch: ", "No signals: ", "Not checked: "]);
  await expect(page.locator("[data-status-rules] dd").first()).toHaveText("Three or more signals, or one strong signal.");
  await page.keyboard.press("Escape");
  // One action per row, secondary, and the page has no solid button.
  await expect(row.getByRole("button", { name: "Add to mission brief, Water and Sanitation Development Project" })).toBeVisible();
  await expect(page.locator("main [data-button=primary]")).toHaveCount(0);
  // The closed project folds away with a count, and opens in place.
  await expect(table.getByText("One project has closed.")).toBeVisible();
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
  const drawer = page.locator("[data-evidence-drawer]");
  await expect(drawer).toContainText("Pending Implementation");
  // The date the line states, as first published, is the field the drawer highlights.
  await expect(drawer.locator("[data-record] mark")).toHaveText(/Highlight starts\.\s*July 31, 2026\s*Highlight ends\./);
  await expect(drawer.locator("[data-record]")).toContainText("Planned completion first published in the plan of");
});

test("the closing date signal's marker names the latest move and opens that record", async ({ page }) => {
  await openFollowing(page);
  const marker = page.locator("[data-following-view=table] [data-signal=closing_moves] [data-citation]");

  await expect(marker).toHaveAccessibleName(/World Bank monthly loan history, reported November 30, 2025/);
  await marker.click();

  await expect(page).toHaveURL(/evidence=strata\.gold\.project_closing_date%3AP156634%2F2025-11-30/);
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
  // On a phone the seven checks are blocks, not a table that scrolls sideways, and the page never widens.
  for (const width of [390, 320]) {
    await openFollowing(page, { width, file: "following-made-up-track-record.json" });
    await page.getByRole("button", { name: "Show the seven checks" }).click();
    await expect(page.locator("[data-track-view=blocks]")).toBeVisible();
    await expect(page.locator("[data-track-view=table]")).toBeHidden();
    await expect(page.locator("[data-track-block=above_estimate]")).toContainText("Later extended their closing date");
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), `at ${width} px`).toBe(true);
  }
});

test("Following has no WCAG 2.2 AA violations at 1440, 1024 and 390 px, with its made-up states and the fold open", async ({ page }) => {
  for (const width of [1440, 1024, 390]) {
    await openFollowing(page, { width, file: "following-made-up-states.json" });
    await view(page).getByRole("button", { name: /Show them|Show it/ }).click();
    await page.getByRole("button", { name: "Show the seven checks" }).click();
    expect(await axe(page), `at ${width} px`).toEqual([]);
    // The ghost buttons sit flush on the text's edge, as Button's flush rule sets.
    await expect(view(page).getByRole("button", { name: /Hide them|Hide it/ })).toHaveClass(/-ml-2/);
    await expect(page.getByRole("button", { name: "Hide the checks" })).toHaveClass(/-ml-2/);
  }
  await expect(page.locator("[data-following-view=list] [data-fold-sentence]")).toHaveText(
    "One project has no signals. One has closed, and one is in the pipeline. I couldn't run every check on one of the projects with no signals.");
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
    "When I replayed these checks on past dates, 9 of the 14 projects that needed a look later extended their closing date. " +
      "So did 11 of the 26 worth watching, and 7 of the 38 with no signals. Only 14 projects needed a look when I replayed the checks, " +
      "too few to say how much the status usually means.",
  );
  await expect(track).toContainText("These counts say what happened next, not why.");
  await expect(track).toContainText("June 30, 2023, June 30, 2024 and June 30, 2025");
  await track.getByRole("button", { name: "Show the seven checks" }).click();
  await expect(track.locator("[data-track-check=above_estimate]")).toContainText("4 of 9");
  await expect(track.locator("[data-track-check=above_estimate]")).toContainText("Too few projects to read as a rate.");
  // A check the replay never saw fire says so, and writes no count.
  await expect(track.locator("[data-track-check=disbursement]")).toContainText("I haven't seen this signal in my replay yet.");
  await expect(track.locator("[data-track-check=disbursement]")).not.toContainText("0 of 0");
  await expect(track.locator("tfoot")).toContainText("7 of 38");
});

test("Following refuses a viewer without the World Bank staff role, and a preview shows no list", async ({ page }) => {
  await openFollowing(page, { answers: { "/api/me": { body: await recorded("me-not-staff.json") }, "/api/following": { status: 403, body: await recorded("following-not-staff.json") } } });
  await expect(page.getByRole("heading", { level: 2, name: "I show Following only to World Bank staff." })).toBeVisible();
  // The sidebar offers no Following to a viewer without the role (ticket 99): All projects is the one page under Projects.
  await expect(page.locator("[data-sidebar] [data-sub-items=projects] a")).toHaveText(["All projects"]);
  // A viewer who cannot follow is not told to follow: the purpose is All projects'.
  await expect(page.locator("main")).not.toContainText("Follow the projects you work on");

  // No preview keeps Following (the roles file's [views], ticket 40): the page says so where its list would be.
  await serve(page, { "/api/following": { body: await recorded("following-p156634.json") } });
  await page.goto(`${FOLLOWING}?view=public`);
  await expect(page.locator("[data-not-in-view=following]")).toBeVisible();
  await expect(page.getByRole("heading", { level: 2, name: "The public view has no Following list." })).toBeVisible();
  // The page shows what the preview holds, so the shell never says it shows the staff view.
  await expect(page.getByText("I can't show the public preview yet")).toHaveCount(0);
});

test("as of a past date, the page says the date its checks ran as of, and the shell never says it shows today's data", async ({ page }) => {
  await openFollowing(page, { file: "following-asof-2024-06-30.json", path: `${FOLLOWING}?asof=2024-06-30` });

  await expect(page.getByText("I ran these seven checks as they would have run on June 30, 2024")).toBeVisible();
  await expect(page.getByText("so it shows today's data")).toHaveCount(0);
  await expect(page.locator("[data-coverage-line]")).toContainText(
    "I couldn't run every check on any project I checked. Each row says which records I lacked.");
});

test("a row's partial line names the plan window the thresholds file sets, never one the page types", async ({ page }) => {
  // Made up from the recorded as-of answer: the thresholds file set to a six-month plan window.
  const answer = JSON.parse(await recorded("following-asof-2024-06-30.json"));
  answer.thresholds.plan_months = 6;
  await openFollowing(page, { path: `${FOLLOWING}?asof=2024-06-30`, answers: { "/api/following": { body: JSON.stringify(answer) } } });

  await expect(view(page).locator("[data-project-row=P156634] [data-partial]")).toContainText(
    "no implementing agency has published a Procurement Plan for it in the last six months");
});

// Ticket 99: Following and All projects are the sidebar's items under Projects for World Bank staff (DESIGN.md section 5,
// Sidebar), and the sub-tab row is gone. The sub-items show in the open sidebar; the rail hides them, so there Projects
// itself carries the current mark.
test("for World Bank staff, Following and All projects are sidebar items under Projects, which opens Following", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await serve(page, { "/api/projects": { body: await recorded("projects.json") }, "/api/following": { body: await recorded("following-p156634.json") } });
  await page.goto("/projects");
  await expect(page.locator("[data-projects-page=ready]")).toBeVisible();
  const nav = page.getByRole("navigation", { name: "Main" });
  const projects = nav.locator("[data-nav-item=projects]");
  const subs = nav.locator("[data-sub-items=projects] a");
  const look = (link: typeof projects) =>
    link.evaluate((element) => ({
      weight: getComputedStyle(element).fontWeight,
      fill: getComputedStyle(element).backgroundColor,
      bar: getComputedStyle(element, "::before").width,
    }));

  // The sidebar rests as the rail, which hides the sub-items, so Projects itself carries the tint and the bar
  // (DESIGN.md section 2, one current mark).
  await expect(subs.first()).toBeHidden();
  expect(await look(projects)).toEqual({ weight: "600", fill: TINT, bar: "3px" });

  // Opened, the sidebar shows them under Projects.
  await page.getByRole("button", { name: "Expand the sidebar" }).click();
  await expect(projects).toHaveAttribute("href", FOLLOWING);
  await expect(subs).toHaveText(["Following", "All projects"]);
  await expect(subs.nth(0)).toHaveAttribute("href", FOLLOWING);
  await expect(subs.nth(1)).toHaveAttribute("href", "/projects");
  // The page's own item carries the mark (tint and a 3 px primary bar); Projects is "true", in 600, with no tint.
  await expect(subs.nth(1)).toHaveAttribute("aria-current", "page");
  await expect(projects).toHaveAttribute("aria-current", "true");
  expect(await look(subs.nth(1))).toEqual({ weight: "600", fill: TINT, bar: "3px" });
  expect((await look(projects)).weight).toBe("600");
  expect((await look(projects)).fill).not.toBe(TINT);
  // No sub-tab row on the page.
  await expect(page.getByRole("navigation", { name: "Projects pages" })).toHaveCount(0);
  await expect(page.locator("main [data-projects-tabs]")).toHaveCount(0);

  // A sub-item is a route link: Following opens with its h1 focused, and the mark moves to it.
  await subs.nth(0).click();
  await expect(page).toHaveURL(new RegExp(`${FOLLOWING}$`));
  await expect(page.locator("[data-following-page=ready]")).toBeVisible();
  await expect(page.getByRole("heading", { level: 1 })).toBeFocused();
  await expect(subs.nth(0)).toHaveAttribute("aria-current", "page");
  await expect(subs.nth(1)).not.toHaveAttribute("aria-current");
  await expect(page.getByRole("navigation", { name: "Projects pages" })).toHaveCount(0);
});

test("in the officer's and the public previews, Projects opens All projects and holds it alone, with no Following", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await serve(page, { "/api/projects": { body: await recorded("projects.json") }, "/api/agency/projects": { body: await recorded("agency-projects-two.json") } });
  for (const view of ["piu", "public"]) {
    await page.goto(`/projects?view=${view}`);
    await expect(page.locator("[data-projects-page=ready]")).toBeVisible();
    const nav = page.getByRole("navigation", { name: "Main" });
    await expect(nav.locator("[data-nav-item=projects]"), view).toHaveAttribute("href", `/projects?view=${view}`);
    await expect(nav.locator("[data-sub-items=projects] a"), view).toHaveText(["All projects"]);
    await expect(nav.locator("[data-sub-item=following]"), view).toHaveCount(0);
  }
});

test("when reading whether you follow a project fails, the control says so and offers Try again, not a state", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await serve(page, {
    "/api/projects/P156634": { body: await recorded("project-p156634.json") },
    "/api/projects/P156634/summary": { body: await recorded("summary-p156634.json") },
    "GET /api/projects/P156634/follow": { status: 503, body: '{"code":"data_service"}' },
  });
  await page.goto("/projects/P156634");
  const follow = page.locator("[data-follow]");

  await expect(follow.locator("[data-follow-unread]")).toHaveText("I couldn't check whether you follow this project just now.");
  await expect(follow.getByRole("button", { name: "Follow this project" })).toHaveCount(0);
  await page.route("**/api/projects/P156634/follow", async (route) => route.fulfill({ contentType: "application/json", body: await recorded("follow-on.json") }));
  await follow.getByRole("button", { name: "Try again" }).click();
  await expect(follow.getByText("You follow this project.")).toBeVisible();
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
  await expect(awards).toContainText("Two contracts were signed after the ISR dated June 30, 2026, for US$2.5 million together.");
  await expect(awards.locator("[data-brief-view=table] tbody tr")).toHaveCount(2);
  await expect(awards.locator("[data-brief-view=table] tbody tr").first()).toContainText("2,432,125.50");
  await expect(page.locator("[data-check-line]")).toContainText(
    "Not checked: whether the project's published records are complete, or whether this brief covers what your mission needs.");
  expect(await axe(page)).toEqual([]);
});

async function openBrief(page: Page, width: number, draft?: object) {
  await page.setViewportSize({ width, height: 900 });
  await serve(page, { "GET /api/drafts/draft-0001": { body: draft ? JSON.stringify(draft) : await recorded("drafts-mission-brief-draft.json") } });
  await page.goto("/drafts/draft-0001");
  await expect(page.locator("[data-brief-parts=draft]")).toBeVisible();
}

test("each source of the brief says which record it is, and the disbursement table says why it reads more than committed", async ({ page }) => {
  // A 1440 px page area: beside the open sidebar (ticket 92) the window is wider.
  await openBrief(page, windowBeside(1440));
  const titles = page.locator("[data-source-title]");

  await expect(titles.nth(0)).toHaveText("Latest plan of Northern Water Works Development Agency");
  await expect(titles.nth(3)).toHaveText("Totals for P156634");
  await expect(titles.nth(5)).toHaveText("ISR 19, Progress towards achievement of PDO");
  await expect(titles.nth(7)).toHaveText("ISR 19, Overall Implementation Progress (IP)");
  await expect(page.locator("[data-sources] [data-source-item]").nth(3)).toContainText("Strata's totals of this project's records, as of");
  await expect(page.locator("[data-brief-part=disbursement]")).toContainText(
    "The loans and credits data reports more disbursed and canceled than committed for this project.");
  await expect(page.getByText("I wrote each part from public records through October 23, 2026")).toBeVisible();
  // "US$" stays on the line of its amount.
  await expect(page.locator("[data-brief-part=awards] [data-note] .whitespace-nowrap").filter({ hasText: "US$" }).first()).toHaveText("US$2.5");
  // Each latest plan links to that version's plan check.
  await expect(page.locator("[data-brief-part=plans] [data-brief-view=table]").getByRole("link", { name: "Plan of Oct 9, 2026" })).toHaveAttribute(
    "href", "/projects/P156634/procurement/northern-water-works-development-agency/2026-10-09");
});

test("on a phone, each block of the mission brief keeps its labels clear of their values", async ({ page }) => {
  for (const width of [390, 320]) {
    await openBrief(page, width);
    const overlaps = await page.locator("[data-brief-view=blocks]:visible").evaluateAll((lists) =>
      lists.flatMap((list) =>
        [...list.querySelectorAll("dt")].flatMap((term) => {
          const value = term.nextElementSibling as HTMLElement;
          const range = document.createRange();
          range.selectNodeContents(term);
          const text = [...range.getClientRects()];
          const valueRange = document.createRange();
          valueRange.selectNodeContents(value);
          const valueText = [...valueRange.getClientRects()];
          const right = Math.max(...text.map((rect) => rect.right));
          const left = Math.min(...valueText.map((rect) => rect.left));
          const wide = term.getBoundingClientRect().width > 0;
          return wide && (valueText.length === 0 || right <= left + 0.5) ? [] : [`${term.textContent} at ${right} past ${left}`];
        }),
      ),
    );
    expect(overlaps, `at ${width} px`).toEqual([]);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), `at ${width} px`).toBe(true);
  }
});

test("when every project you follow is quiet, the finding counts them in words", async ({ page }) => {
  await openFollowing(page, { file: "following-made-up-all-quiet.json" });

  await expect(page.getByRole("heading", { level: 2, name: "You follow three projects, and none has a signal." })).toBeVisible();
});

test("a part the writer refused says so, and never says I removed sentences", async ({ page }) => {
  // Made up from the recorded draft: the writer refused the disbursement part (tests/fixtures/agent/writers.toml,
  // mission-brief-a-refused-part, which tests/test_mission_brief.py runs through the server).
  const draft = JSON.parse(await recorded("drafts-mission-brief-draft.json"));
  const part = draft.notes.find((note: { key: string }) => note.key === "disbursement");
  Object.assign(part, { state: "refused", refusal: "out_of_scope", sentences: [] });
  await openBrief(page, 1440, draft);
  const disbursement = page.locator("[data-brief-part=disbursement]");

  await expect(disbursement).toContainText("I didn't write this part, because it would need more than the project's records show.");
  await expect(disbursement).not.toContainText("I removed every sentence");
  await expect(disbursement.locator("[data-brief-view=table] tbody tr")).toHaveCount(2);
});
