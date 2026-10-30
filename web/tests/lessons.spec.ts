// The Lessons tab at seam 4 (ticket 29): the library, Waiting for review and one item's review page, against
// the answers the server wrote on the fixture (tests/record_lessons_api.py), which
// tests/test_lesson_review_routes.py checks the server still gives. The words below are the ticket's, DESIGN.md's
// and the 29 design brief's, copied here so the test checks the copy file against an independent source.
import { scan } from "./axe";
import type { Page } from "@playwright/test";
import { expect, openSidebar, recorded, test, windowBeside } from "./mocked";
import { EMAIL, people } from "./people";

const REBIDDING = "new-e903b07ad1";
const PERMITS = "new-64ec0401e3";
const RECHECK = "recheck-09bf32ecc3";
const CROSS_CHECK = "cross-e0d9a6a06a";
// DESIGN.md section 7, rule 19: words that read as a World Bank review decision, which no Lessons button uses.
const RULE_19 = /\b(approv\w*|clear(ance)?s?|no-objection|concur\w*|endorse\w*|validat\w*)\b/i;

type Answer = { status?: number; body: string };

async function file(name: string): Promise<Answer> {
  const text = await recorded(name);
  const parsed = JSON.parse(text);
  // A refusal is recorded with its status beside its body.
  return parsed.status && parsed.body ? { status: parsed.status, body: JSON.stringify(parsed.body) } : { body: text };
}

// Serve /api from recorded answers, by "METHOD /path" or by path for any method; the query is ignored.
async function serve(page: Page, answers: Record<string, Answer>) {
  const asked: { method: string; path: string; body: unknown }[] = [];
  const base: Record<string, Answer> = {
    "/api/me": { body: await recorded("me.json") },
    "/api/freshness": { body: await recorded("freshness.json") },
    "POST /api/evidence/opened": { body: '{"recorded":true}' },
    "/api/evidence": { body: await recorded("evidence-icr-p130164-54.json") },
  };
  const all = { ...base, ...answers };
  await page.route("**/api/**", async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    asked.push({ method: request.method(), path, body: request.postDataJSON?.() ?? null });
    const answer = all[`${request.method()} ${path}`] ?? all[path];
    if (!answer) return route.fulfill({ status: 404, json: { detail: "Not Found" } });
    return route.fulfill({ status: answer.status ?? 200, contentType: "application/json", body: answer.body });
  });
  return asked;
}

async function reviewer(page: Page, extra: Record<string, Answer> = {}) {
  return serve(page, { "/api/lessons/me": await file("lessons-me-reviewer.json"), ...extra });
}

async function viewer(page: Page, extra: Record<string, Answer> = {}) {
  return serve(page, { "/api/lessons/me": await file("lessons-me-viewer.json"), ...extra });
}

async function axe(page: Page) {
  await page.waitForFunction(() => document.getAnimations().every((animation) => animation.playState !== "running"));
  const results = await scan(page);
  return results.violations.map((v) => `${v.id}: ${v.nodes.map((node) => node.target.join(" ")).join(", ")}`);
}

// Ticket 102: the reviewer pages are the sidebar's items under Lessons (DESIGN.md section 5, Sidebar), so the page has
// no sub-tab row. The sub-items show in the open sidebar; the rail hides them.
const subTabs = (page: Page) => page.getByRole("navigation", { name: "Lesson pages" });
const lessonsItems = (page: Page) => page.getByRole("navigation", { name: "Main" }).locator("[data-sub-items=lessons] a");

// ── Who sees the queue ───────────────────────────────────────────────────

test("someone who is not a lesson reviewer sees no reviewer page under Lessons, and the queue's address shows the no-access card", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await openSidebar(page);
  await viewer(page, {
    // Ticket 39's page answers in one request (tests/record_lessons_page_api.py): here, Ana's first visit to an
    // empty library.
    "/api/lessons/page": await file("lessons-page-empty.json"),
    "/api/lessons/review": await file("lessons-queue-no-access.json"),
  });
  await page.goto("/lessons");
  await expect(page.locator("[data-library=empty]")).toBeVisible();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Lessons");
  await expect(subTabs(page)).toHaveCount(0);
  await expect(lessonsItems(page)).toHaveCount(0);
  await expect(page.getByRole("link", { name: /Waiting for review/ })).toHaveCount(0);
  // The empty library's row for anyone who is not a reviewer links where section 3's empty state does (ticket 114).
  await expect(page.locator("[data-library=empty]").getByRole("link")).toHaveText("See which completion reports I have read");

  await page.goto("/lessons/review");
  const card = page.locator("[data-empty-state]");
  await expect(card.getByRole("heading")).toHaveText("I show this page only to lesson reviewers.");
  await expect(card.getByRole("link", { name: "Go to Lessons" })).toHaveAttribute("href", "/lessons");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Lessons");
  await expect(subTabs(page)).toHaveCount(0);
  await expect(lessonsItems(page)).toHaveCount(0);
  await expect(page).toHaveTitle("Lessons | Strata");
});

test("a lesson reviewer finds Waiting for review under Lessons in the sidebar with its count in a badge, and the queue grouped for them", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await openSidebar(page);
  await reviewer(page, {
    "/api/lessons/page": await file("lessons-page-reviewer.json"),
    "/api/lessons/review": await file("lessons-queue.json"),
    [`/api/lessons/review/${REBIDDING}`]: await file("lessons-item-recommend.json"),
  });
  await page.goto("/lessons");
  await expect(page.locator("[data-lessons-page=ready]")).toBeVisible();
  const nav = page.getByRole("navigation", { name: "Main" });
  const lessons = nav.locator("[data-nav-item=lessons]");
  const queue = lessonsItems(page);
  // One page for this role, Waiting for review, with the count waiting in the reviewer's region in its badge.
  await expect(queue).toHaveCount(1);
  await expect(queue).toHaveAttribute("href", "/lessons/review");
  await expect(queue).toHaveAccessibleName("Waiting for review, 3 lessons");
  await expect(queue.locator("[data-sub-count]")).toHaveText("3");
  await expect(lessons).toHaveAttribute("aria-current", "page");
  // No sub-tab row on the page.
  await expect(subTabs(page)).toHaveCount(0);
  await expect(page.locator("main nav")).toHaveCount(0);

  // A sub-item is a route link: the page names itself in its h1, which takes focus, and the mark moves to it.
  await queue.click();
  await expect(page).toHaveURL(/\/lessons\/review$/);
  await expect(page.locator("[data-queue=ready]")).toBeVisible();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Waiting for review");
  await expect(page.getByRole("heading", { level: 1 })).toBeFocused();
  await expect(queue).toHaveAttribute("aria-current", "page");
  await expect(lessons).toHaveAttribute("aria-current", "true");
  // As the current item, in its heavier weight, the label and its badge still keep to one line, so the sidebar stays put.
  expect((await queue.boundingBox())!.height).toBeLessThanOrEqual(32);
  await expect(subTabs(page)).toHaveCount(0);
  await expect(page).toHaveTitle("Waiting for review, Lessons | Strata");

  // An item's review page sits inside Waiting for review, so its item keeps the mark.
  await page.locator(`[data-queue-row=${REBIDDING}] h3 a`).click();
  await expect(page.locator(`[data-review-page=${REBIDDING}]`)).toBeVisible();
  await expect(queue).toHaveAttribute("aria-current", "true");
  await page.goBack();
  await expect(page.locator("[data-queue-lead]")).toHaveText(
    "Three lessons are waiting for you. The oldest has used three of its 10 business days.",
  );
  await expect(page.locator("[data-quote-check]")).toContainText(
    "In the last 30 days I dropped one proposed lesson whose quote was not on its cited page.",
  );
  await expect(page.locator("[data-quote-check] a")).toHaveAttribute("href", "/data?sources=documents&from=get_lessons");
  const group = page.locator("[data-queue-group=you]");
  await expect(group.getByRole("heading", { level: 2 })).toHaveText("Waiting for you");
  await expect(page.locator("[data-queue-group=others]")).toHaveCount(0);
  const row = page.locator(`[data-queue-row=${REBIDDING}]`);
  await expect(row.locator("p").first()).toHaveText("New lesson · needs your recommendation");
  await expect(row.getByRole("heading", { level: 3 })).toHaveText("Base works estimates on market rates to avoid rebidding");
  await expect(row.getByRole("link", { name: "Base works estimates on market rates to avoid rebidding" })).toHaveAttribute(
    "href",
    `/lessons/review/${REBIDDING}`,
  );
  await expect(row).toContainText("From the ICR for Rajasthan Road Sector Modernization Project (P130164), paragraph 54, page 23. South Asia.");
  await expect(row.locator("[data-badge=restated]")).toHaveText("Restated by IEG");
  await expect(row).toContainText("Day 3 of 10 business days, due November 5, 2026.");

  // Three digits keep the current item on one line too (design round 2, item A), so Drafts below it stays put.
  const me = JSON.parse(await recorded("lessons-me-reviewer.json"));
  await page.route("**/api/lessons/me", (route) => route.fulfill({ contentType: "application/json", body: JSON.stringify({ ...me, waiting: 100 }) }));
  await page.reload();
  await expect(queue.locator("[data-sub-count]")).toHaveText("100");
  await expect(queue).toHaveAccessibleName("Waiting for review, 100 lessons");
  await expect(queue).toHaveAttribute("aria-current", "page");
  expect((await queue.boundingBox())!.height).toBeLessThanOrEqual(32);
});

test("while the queue loads, its purpose is already in place and names every one of the reviewer's regions", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const me = JSON.parse(await recorded("lessons-me-reviewer.json"));
  await serve(page, { "/api/lessons/me": { body: JSON.stringify({ ...me, regions: ["South Asia", "East Asia and Pacific", "Eastern and Southern Africa"] }) } });
  await page.route("**/api/lessons/review?page=1", () => undefined); // the queue never answers
  await page.goto("/lessons/review");
  const purpose = page.locator("[data-queue=loading] [data-queue-purpose]");
  await expect(purpose).toContainText("within 10 business days.");
  await expect(purpose).toContainText("This page lists lessons for South Asia, East Asia and Pacific and Eastern and Southern Africa,");
});

test("the decided table keeps each date on one line, and each day count says what it counts from", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await reviewer(page, { "/api/lessons/review": await file("lessons-queue-decided.json") });
  await page.goto("/lessons/review");
  const table = page.locator("[data-queue-decided=table]");
  // Every decision shows, and the count line stays because it is where the list says its order (ticket 126).
  await expect(table.locator("[data-count-row] p[data-numbers]")).toHaveText("Showing all three decisions, newest first.");
  const date = table.locator("tbody tr").first().locator("td").nth(1);
  await expect(date).toHaveText("Oct 27, 2026");
  const lines = await date.evaluate((cell) => Math.round(cell.querySelector("span")!.getBoundingClientRect().height / parseFloat(getComputedStyle(cell).lineHeight)));
  expect(lines).toBe(1);
  // Ticket 59 (the 29 critique, round 3, follow-up 4): the statement's first line is level with the Outcome's and
  // Decided's first lines.
  const firstLines = await table.locator("tbody tr").first().evaluate((row) =>
    [...row.children].slice(0, 3).map((cell) => {
      const range = document.createRange();
      const walker = document.createTreeWalker(cell, NodeFilter.SHOW_TEXT);
      const text = walker.nextNode()!;
      range.selectNodeContents(text);
      return Math.round(range.getClientRects()[0].top);
    }),
  );
  expect(Math.max(...firstLines) - Math.min(...firstLines), `first lines at ${firstLines.join(", ")}`).toBeLessThanOrEqual(1);
  await table.locator("tbody button[data-num]").first().focus();
  await expect(page.getByRole("tooltip")).toHaveText("Days from November 2, 2019, when the report became public, to the decision on October 27, 2026.");
});

// ── Reviewers' verbs ─────────────────────────────────────────────────────

test("a reviewer recommends, a lead adds or rejects, and no button uses a word that reads as a World Bank decision", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await reviewer(page, {
    [`/api/lessons/review/${REBIDDING}`]: await file("lessons-item-recommend.json"),
    [`/api/lessons/review/${PERMITS}`]: await file("lessons-item-decide-repeats.json"),
    [`/api/lessons/review/${RECHECK}`]: await file("lessons-item-recheck-decide.json"),
  });
  await page.goto(`/lessons/review/${REBIDDING}`);
  const form = page.locator("[data-decision-form]");
  await expect(form.getByRole("heading", { level: 2 })).toHaveText("Your recommendation");
  await expect(form.getByRole("button", { name: "Recommend adding it" })).toBeVisible();
  await expect(form.getByRole("button", { name: "Recommend rejecting it" })).toBeVisible();

  await page.goto(`/lessons/review/${PERMITS}`);
  await expect(form.getByRole("heading", { level: 2 })).toHaveText("Your decision");
  await expect(form.getByRole("group", { name: "Is this a new lesson?" }).getByRole("radio")).toHaveCount(2);
  await expect(form.getByRole("button", { name: "Add to the library" })).toBeVisible();
  await expect(form.getByRole("button", { name: "Reject, with a reason" })).toBeVisible();

  await page.goto(`/lessons/review/${RECHECK}`);
  await expect(form.getByRole("button", { name: "Save this decision" })).toBeVisible();
  for (const button of await page.getByRole("button").all()) expect(await button.innerText()).not.toMatch(RULE_19);
});

test("the quote is the one highlighted thing on the review page, checked on its page, with the evidence before the decision", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await reviewer(page, { [`/api/lessons/review/${REBIDDING}`]: await file("lessons-item-recommend.json") });
  await page.goto(`/lessons/review/${REBIDDING}`);

  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Base works estimates on market rates to avoid rebidding");
  await expect(page).toHaveTitle("Base works estimates on market rates to avoid rebidding, Waiting for review | Strata");
  const cards = page.locator("[data-lesson-evidence]");
  await expect(cards).toHaveCount(2);
  await expect(cards.first().locator("mark")).toHaveText("Highlight starts. 108 of 328 cases had to go through rebidding. Highlight ends.");
  await expect(cards.first().locator("[data-check-line]")).toHaveText(
    "Checked: I found this quote word for word on page 23. Not checked: whether the lesson follows from it.",
  );
  await expect(cards.nth(1)).toContainText("IEG's review of this ICR restated the lesson.");
  // The work reads top to bottom: evidence, tags, summary, then the form; the history is the side panel, which
  // follows the work in one column (ticket 102).
  const order = await page.locator("main h2").allTextContents();
  expect(order).toEqual(["The evidence", "How I tagged it", "My summary of the evidence", "Your recommendation", "What has happened so far"]);
  // The writer's summary passed the verifier; the sentence it removed is shown with its reason.
  await expect(page.locator("[data-summary=ready] [data-removed-box]")).toContainText("I removed one sentence.");
});

// Ticket 102 (DESIGN.md section 4, Page layouts, Workspace): from a frame of 75rem the work takes columns 1 to 7 and the
// history is the side panel in columns 9 to 12; below it the page is one column and the history follows the work. The
// widths are windows beside the rail, which the sidebar rests as.
test("a review page is a workspace at 1440 and 1280 px, with its history in the side panel, and one column at 1024 and 390 px", async ({ page }) => {
  await reviewer(page, { [`/api/lessons/review/${REBIDDING}`]: await file("lessons-item-recommend.json") });
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto(`/lessons/review/${REBIDDING}`);
  const work = page.locator("[data-review-page] [data-workspace-work][data-zones]");
  const side = page.locator("[data-review-page] [data-side-slot]");
  await expect(side.getByRole("heading", { level: 2 })).toHaveText("What has happened so far");
  await expect(side.locator("[data-history] li").first()).toBeVisible();
  for (const width of [1440, 1280, 1024, 390]) {
    await page.setViewportSize({ width, height: 900 });
    await page.evaluate(() => document.fonts.ready);
    const [w, s, column] = [(await work.boundingBox())!, (await side.boundingBox())!, (await page.locator("[data-page-column]").boundingBox())!];
    if (width >= 1280) {
      // Beside the work, to its right, and the work a little more than half the page column.
      expect(s.x, `${width} px`).toBeGreaterThan(w.x + w.width);
      expect(s.y, `${width} px`).toBeLessThan(w.y + w.height);
      expect(w.width / column.width, `${width} px`).toBeLessThan(0.65);
    } else {
      // One column: the history after the work, as wide as it.
      expect(s.y, `${width} px`).toBeGreaterThanOrEqual(w.y + w.height);
      expect(Math.abs(s.width - w.width), `${width} px`).toBeLessThan(2);
    }
  }

  // The decision form keeps its focus rules in the workspace: a recommendation with no reason sends focus to the field.
  await page.setViewportSize({ width: 1440, height: 900 });
  const form = page.locator("[data-decision-form]");
  await form.getByRole("button", { name: "Recommend adding it" }).click();
  await expect(form.getByRole("textbox", { name: "Your reason" })).toBeFocused();
});

// Round 1 of ticket 102: a review page whose one read fails puts its alert in the alert slot, and its h1 names one item
// under the breadcrumb that ends at the queue, so the page never reads as the queue itself.
test("when a review page's one read fails, its alert is in the alert slot and its h1 names one lesson, not the queue", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await reviewer(page, { [`/api/lessons/review/${REBIDDING}`]: { status: 503, body: '{"code":"data_service","trace_id":"0af7651916cd43dd8448eb211c80319c"}' } });
  await page.goto(`/lessons/review/${REBIDDING}`);
  await expect(page.locator("[data-alert-slot] [role=alert]")).toBeVisible();
  await expect(page.locator("main nav[aria-label] a").last()).toHaveText("Waiting for review");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("A lesson waiting for review");
  await expect(page).toHaveTitle("Waiting for review, Lessons | Strata");
});

test("a recommendation needs a reason, sends the stage the reviewer saw, and ends on the outcome panel", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  const asked = await reviewer(page, {
    [`/api/lessons/review/${REBIDDING}`]: await file("lessons-item-recommend.json"),
    [`POST /api/lessons/review/${REBIDDING}/recommend`]: await file("lessons-act-recommended.json"),
  });
  await page.goto(`/lessons/review/${REBIDDING}`);
  const form = page.locator("[data-decision-form]");
  await form.getByRole("button", { name: "Recommend adding it" }).click();
  const reason = form.getByRole("textbox", { name: "Your reason" });
  await expect(reason).toBeFocused();
  await expect(reason).toHaveAttribute("aria-invalid", "true");
  await expect(form).toContainText("Write your reason first. The lead reads it before deciding.");
  expect(asked.filter((call) => call.method === "POST")).toEqual([]);

  await reason.fill("The ICR and IEG's review both say estimates below market rates led to rebidding.");
  await form.getByRole("button", { name: "Recommend adding it" }).click();
  const panel = page.locator("[data-outcome-panel]");
  await expect(panel).toBeFocused();
  await expect(panel).toContainText("You recommended adding this lesson.");
  await expect(panel).toContainText("A different lead procurement specialist decides next, by November 5, 2026.");
  const post = asked.find((call) => call.method === "POST");
  expect(post?.body).toMatchObject({ expected_stage: "recommendation", outcome: "add" });
  // Your own act is yours in the history too, never your name (ticket 140).
  await expect(page.locator("[data-history] li").last()).toContainText(
    "You recommended adding it. Reason: \"The ICR and IEG's review both say estimates below market rates led to rebidding.\"",
  );
});

test("the same person can't decide what they recommended, and nobody acts on their own project: each says why", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await reviewer(page, {
    [`/api/lessons/review/${PERMITS}`]: await file("lessons-item-same-person.json"),
    [`/api/lessons/review/${REBIDDING}`]: await file("lessons-item-own-project.json"),
  });
  await page.goto(`/lessons/review/${PERMITS}`);
  await expect(page.locator("[data-review-action] [data-alert=neutral]")).toHaveText(
    "You recommended this lesson, so a different lead procurement specialist decides it.",
  );
  await expect(page.locator("[data-decision-form]")).toHaveCount(0);
  await page.goto(`/lessons/review/${REBIDDING}`);
  await expect(page.locator("[data-review-action] [data-alert=neutral]")).toHaveText(
    "You work on Rajasthan Road Sector Modernization Project (P130164), so you can't recommend or decide on this lesson.",
  );
});

test("a refused decision says why at the top, then the note takes the form's place", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await reviewer(page, {
    [`/api/lessons/review/${REBIDDING}`]: await file("lessons-item-decide.json"),
    [`POST /api/lessons/review/${REBIDDING}/decide`]: await file("lessons-act-refused-own-project.json"),
  });
  await page.goto(`/lessons/review/${REBIDDING}`);
  const form = page.locator("[data-decision-form]");
  await form.getByRole("textbox", { name: "Your reason" }).fill("It reads well.");
  await form.getByRole("button", { name: "Add to the library" }).click();
  const refused = page.locator("[data-gave-way=refused]");
  await expect(refused).toBeFocused();
  // The error says what failed, and the note under it says why, so no sentence shows twice.
  await expect(refused.locator("[data-alert=error]")).toHaveText("I couldn't save your decision.");
  await expect(refused.locator("[data-alert=neutral]")).toContainText("so you can't recommend or decide on this lesson.");
});

test("an act on an item that moved on keeps the reviewer's unsent reason", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await reviewer(page, {
    [`/api/lessons/review/${REBIDDING}`]: await file("lessons-item-recommend.json"),
    [`POST /api/lessons/review/${REBIDDING}/recommend`]: await file("lessons-act-stale.json"),
  });
  await page.goto(`/lessons/review/${REBIDDING}`);
  const form = page.locator("[data-decision-form]");
  await form.getByRole("textbox", { name: "Your reason" }).fill("Too general to act on.");
  await form.getByRole("button", { name: "Recommend rejecting it" }).click();
  const stale = page.locator("[data-gave-way=stale]");
  await expect(stale).toBeFocused();
  await expect(stale).toContainText(
    "While you had this lesson open, an accredited procurement specialist for South Asia recommended it on October 27, 2026.",
  );
  await expect(stale).toContainText("I didn't send your reason. You can copy it from the box below.");
  await expect(stale.getByRole("textbox")).toHaveValue("Too general to act on.");
});

test("a decided record shows the outcome where the form was, with days from publication to the decision", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await reviewer(page, { [`/api/lessons/review/${PERMITS}`]: await file("lessons-item-decided-merged.json") });
  await page.goto(`/lessons/review/${PERMITS}`);
  await expect(page.locator("[data-status]")).toHaveText("New lesson · decided");
  await expect(page.locator("main")).toContainText("Decided on October 27, 2026, 2,551 days after the report became public.");
  await expect(page.locator("[data-outcome-panel]")).toContainText(
    'Added as evidence to "Put forest and other permits in place before awarding contracts" on October 27, 2026.',
  );
  await expect(page.locator("[data-history]")).toContainText("Was: Rested on one quote from one report.");
  await expect(page.locator("[data-history]")).toContainText("Now: Rests on two quotes from two reports.");
});

// Ticket 58 (the 29 critique, round 3, follow-up 2): a decided record whose summary was never written says so, and
// never that I'm still writing it so you can decide.
test("a decided record whose summary was never written says I didn't write one before the decision", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  const item = JSON.parse((await file("lessons-item-decided-merged.json")).body);
  item.summary = { ...item.summary, status: "writing", sentences: [], evidence: {}, removed: [] };
  await reviewer(page, { [`/api/lessons/review/${PERMITS}`]: { body: JSON.stringify(item) } });
  await page.goto(`/lessons/review/${PERMITS}`);

  await expect(page.locator("main")).toContainText("I didn't write a summary of this evidence before the decision.");
  await expect(page.locator("main")).not.toContainText("I'm still writing my summary");
});

// Ticket 58 (the 29 design review, round 3, F5): the decided table's cards say what days from publication count.
test("below 768 px the decided table's note says what days from publication count", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await reviewer(page, { "/api/lessons/review": await file("lessons-queue-decided.json") });
  await page.goto("/lessons/review");
  await expect(page.locator("main")).toContainText(
    "Days from publication count from the day the report became public to the day of the decision.",
  );
});

// ── The library ──────────────────────────────────────────────────────────

test("the library lists lesson cards newest first, naming roles and never people, with each lesson's edition", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  // Ticket 39's page (tests/record_lessons_page_api.py): the library comes last, after what changed and what is new.
  await viewer(page, { "/api/lessons/page": await file("lessons-page.json") });
  await page.goto("/lessons");
  const cards = page.locator("[data-library] [data-lesson-card=full]");
  await expect(cards).toHaveCount(2);
  await expect(page.locator("[data-library] [data-lead]")).toHaveText("Showing both current lessons, newest first.");
  const first = cards.first();
  // Who decided, by role, is in the version's window beside the badges since ticket 126 (T30), and each by its region
  // since ticket 140.
  await first.getByRole("button", { name: "Version 2" }).click();
  await expect(page.getByRole("dialog", { name: "Version 2" })).toContainText(
    "A lead procurement specialist for South Asia decided version 2 on October 29, 2026, after an accredited procurement specialist for South Asia recommended it.",
  );
  await page.keyboard.press("Escape");
  await expect(first).toContainText("Its projects followed the World Bank's Procurement Guidelines of January 2011.");
  await expect(page.locator("main")).not.toContainText("Asha Raman");
  await expect(page.locator("main")).not.toContainText("Omar Haddad");
  await expect(page.getByRole("button", { name: "Ask for a re-check" })).toHaveCount(0);
  // A chip shows the document's short name and the item; its name then says what it opens.
  await expect(first.locator("[data-source-chip]").first()).toHaveText(/^ICR ¶54, opens the source: /);
});

test("a lesson reviewer can ask for a re-check from a card, with a reason", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  const lesson = JSON.parse(await recorded("lessons-page-reviewer.json")).library.lessons[1].lesson_id;
  const asked = await reviewer(page, {
    "/api/lessons/page": await file("lessons-page-reviewer.json"),
    [`POST /api/lessons/${lesson}/recheck`]: await file("lessons-act-recheck.json"),
  });
  await page.goto("/lessons");
  const card = page.locator(`#lesson-${lesson}`);
  await card.getByRole("button", { name: "Ask for a re-check" }).click();
  const field = card.getByRole("textbox", { name: "Why should reviewers re-check this lesson?" });
  await expect(field).toBeFocused();
  await card.getByRole("button", { name: "Ask for a re-check" }).click();
  await expect(card).toContainText("Write a reason, so the reviewers know what to look at.");
  await field.fill("The 2025 Procurement Regulations changed how cost estimates are prepared.");
  await card.getByRole("button", { name: "Ask for a re-check" }).click();
  await expect(card.locator("[data-recheck=saved]")).toBeFocused();
  await expect(card.locator("[data-badge=rechecking]")).toHaveText("Being re-checked");
  // The sub-tab's count is asked for again after the save.
  await expect.poll(() => asked.filter((call) => call.path === "/api/lessons/me").length).toBe(2);
});

// ── Who an act names (ticket 140) ────────────────────────────────────────
//
// One rule names the person behind an act: "You" to that person, their role and region to everyone else the roles file
// lists, and "A reviewer" for anyone it no longer lists. No page under /lessons prints a person's name or email.

async function namesNoPerson(page: Page) {
  const text = (await page.locator("main").innerText()).toLowerCase();
  expect((await people()).filter((word) => text.includes(word.toLowerCase()))).toEqual([]);
  expect(text).not.toMatch(EMAIL);
}

test("the queue names your own recommendation as yours and anyone else's act by role and region, never by name", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  // Omar recommended adding paragraph 55 as evidence to IEG's lesson, so a different lead decides it.
  await reviewer(page, { "/api/lessons/review": await file("lessons-queue-same-person.json") });
  await page.goto("/lessons/review");
  const own = page.locator(`[data-queue-row=${PERMITS}]`);
  await expect(own).toContainText("You recommended adding it as evidence to another lesson on October 27, 2026.");
  await expect(own).toContainText("You recommended it, so a different lead decides.");
  await namesNoPerson(page);

  // A lead's queue: Asha, an accredited procurement specialist, recommended the rebidding lesson.
  await reviewer(page, { "/api/lessons/review": await file("lessons-queue-lead.json") });
  await page.goto("/lessons/review");
  await expect(page.locator(`[data-queue-row=${REBIDDING}]`)).toContainText(
    "An accredited procurement specialist for South Asia recommended adding it on October 27, 2026.",
  );
  await namesNoPerson(page);

  // Wanjiru, a lead in Eastern and Southern Africa, asked for the re-check: her region, not the lesson's.
  await reviewer(page, { "/api/lessons/review": await file("lessons-queue-recheck.json") });
  await page.goto("/lessons/review");
  await expect(page.locator(`[data-queue-row=${RECHECK}]`)).toContainText(
    "A lead procurement specialist for Eastern and Southern Africa asked for a re-check on October 28, 2026.",
  );
  await namesNoPerson(page);
});

test("an item's history names each act by the same rule, yours as yours", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await reviewer(page, {
    [`/api/lessons/review/${RECHECK}`]: await file("lessons-item-recheck-decide.json"),
    [`/api/lessons/review/${REBIDDING}`]: await file("lessons-item-decided-added.json"),
  });
  await page.goto(`/lessons/review/${RECHECK}`);
  const history = page.locator("[data-history]");
  await expect(history).toContainText("A lead procurement specialist for Eastern and Southern Africa asked for a re-check.");
  await expect(history).toContainText("An accredited procurement specialist for South Asia recommended changing it.");
  await namesNoPerson(page);

  // Asha reads the record of the lesson she recommended and Omar added.
  await page.goto(`/lessons/review/${REBIDDING}`);
  await expect(history).toContainText("You recommended adding it.");
  await expect(history).toContainText("A lead procurement specialist for South Asia added it to the library as version 1.");
  await namesNoPerson(page);
});

test("a library card names who decided its version and who recommended it, yours as yours", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  // Asha recommended the change that became version 2 of the rebidding lesson, and reads the library.
  await reviewer(page, { "/api/lessons/page": await file("lessons-page-reviewer.json") });
  await page.goto("/lessons");
  const first = page.locator("[data-library] [data-lesson-card=full]").first();
  await first.getByRole("button", { name: "Version 2" }).click();
  await expect(page.getByRole("dialog", { name: "Version 2" })).toContainText(
    "A lead procurement specialist for South Asia decided version 2 on October 29, 2026, after you recommended it.",
  );
  await namesNoPerson(page);

  // A retired lesson's card names who retired it by the same rule.
  const retired = JSON.parse(await recorded("lessons-page.json"));
  retired.library = JSON.parse(await recorded("lessons-library-retired.json"));
  await viewer(page, { "/api/lessons/page": { body: JSON.stringify(retired) } });
  await page.goto("/lessons?status=retired");
  await expect(page.locator("[data-library] [data-lesson-card=full]").first()).toContainText(
    "A lead procurement specialist for South Asia retired it on October 29, 2026. The lead's reason: \"IEG's own review later said the permits were not the cause.\"",
  );
  await namesNoPerson(page);
});

// ── The evidence drawer ──────────────────────────────────────────────────

test("an evidence card's marker opens the drawer at its source, and focus comes back to the marker", async ({ page }) => {
  // A 1440 px page area: beside the open sidebar (ticket 92) the window is wider.
  await page.setViewportSize({ width: windowBeside(1440), height: 900 });
  await reviewer(page, { [`/api/lessons/review/${REBIDDING}`]: await file("lessons-item-recommend.json") });
  await page.goto(`/lessons/review/${REBIDDING}`);
  const marker = page.locator("[data-lesson-evidence] [data-citation]").first();
  // Measure the column once its item has drawn in the web fonts: under the whole gate's load the first box
  // could be taken while the text was still in the fallback font, and the swap made the column 34 px taller.
  await expect(marker).toBeVisible();
  await page.evaluate(() => document.fonts.ready);
  // The workspace's work (ticket 102): the side panel hides while the drawer is open, and the work stays put.
  const work = page.locator("[data-review-page] [data-workspace-work][data-zones]");
  const column = await work.boundingBox();
  await marker.click();
  const drawer = page.getByRole("dialog");
  await expect(drawer).toBeVisible();
  await expect(page).toHaveURL(/evidence=strata\.gold\.passage%3A31525018%2Fv1%2F54|evidence=strata.gold.passage:31525018\/v1\/54/);
  // The quote the card showed is highlighted in the whole paragraph.
  await expect(drawer.locator("mark")).toHaveText("Highlight starts. 108 of 328 cases had to go through rebidding. Highlight ends.");
  // The column keeps its place and width while the drawer is open, and the history's side panel steps aside for it.
  expect(await work.boundingBox()).toEqual(column);
  await expect(page.locator("[data-review-page] [data-side-slot]")).toBeHidden();
  await page.keyboard.press("Escape");
  await expect(drawer).toHaveCount(0);
  await expect(marker).toBeFocused();

  // At 1280 px too, where the drawer leaves the page area narrower than the work's own breakpoints: the work lays out by
  // its own column, so the marker you pressed does not move when the drawer opens.
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.evaluate(() => document.fonts.ready);
  const before = await marker.boundingBox();
  await marker.click();
  await expect(drawer).toBeVisible();
  await page.waitForFunction(() => document.getAnimations().every((animation) => animation.playState !== "running"));
  expect(await marker.boundingBox()).toEqual(before);
});

test("a likely repeat's citation of a library lesson opens the drawer at the lesson, named by its statement", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await reviewer(page, { [`/api/lessons/review/${PERMITS}`]: await file("lessons-item-recommend-repeats.json") });
  await page.goto(`/lessons/review/${PERMITS}`);
  const statement = "Put forest and other permits in place before awarding contracts";
  const marker = page.locator("[data-repeats] [data-citation]").first();
  await expect(marker).toHaveAccessibleName(`Source 2: Lesson, version 1, ${statement}`);
  await marker.click();
  const drawer = page.getByRole("dialog");
  await expect(drawer.getByRole("heading", { level: 2 })).toHaveText(statement);
  // The drawer's head is its title, with no eyebrow and no middle dot (ticket 94).
  await expect(drawer.locator("[data-drawer-header]")).not.toContainText("·");
  const source = drawer.locator("[data-source]");
  await expect(source).toHaveText("Source: Strata's lesson library, version 1, decided on October 27, 2026.");
  await expect(source).not.toContainText(", ,");
  await expect(source).not.toContainText("lesson-");
});

// ── Accessibility at three widths ────────────────────────────────────────

const PAGES: { name: string; path: string; me: "reviewer" | "viewer"; answers: Record<string, string> }[] = [
  { name: "the library", path: "/lessons", me: "reviewer", answers: { "/api/lessons/page": "lessons-page-reviewer.json" } },
  // Ticket 39: the whole page with a notice, what is new and the reader's reports, and the page with a lesson retired
  // as wrong, at the three widths.
  { name: "the Lessons page", path: "/lessons", me: "viewer", answers: { "/api/lessons/page": "lessons-page.json" } },
  { name: "the Lessons page with a lesson retired as wrong", path: "/lessons", me: "viewer", answers: { "/api/lessons/page": "lessons-page-retired.json" } },
  { name: "the queue", path: "/lessons/review", me: "reviewer", answers: { "/api/lessons/review": "lessons-queue-overdue.json" } },
  { name: "the decided table", path: "/lessons/review", me: "reviewer", answers: { "/api/lessons/review": "lessons-queue-decided.json" } },
  { name: "a recommendation with likely repeats", path: `/lessons/review/${PERMITS}`, me: "reviewer", answers: { [`/api/lessons/review/${PERMITS}`]: "lessons-item-recommend-repeats.json" } },
  { name: "a decision", path: `/lessons/review/${REBIDDING}`, me: "reviewer", answers: { [`/api/lessons/review/${REBIDDING}`]: "lessons-item-decide.json" } },
  { name: "a re-check", path: `/lessons/review/${RECHECK}`, me: "reviewer", answers: { [`/api/lessons/review/${RECHECK}`]: "lessons-item-recheck-recommend.json" } },
  { name: "a cross-check", path: `/lessons/review/${CROSS_CHECK}`, me: "reviewer", answers: { [`/api/lessons/review/${CROSS_CHECK}`]: "lessons-item-cross-check.json" } },
  { name: "a decided record", path: `/lessons/review/${PERMITS}`, me: "reviewer", answers: { [`/api/lessons/review/${PERMITS}`]: "lessons-item-decided-merged.json" } },
  { name: "no access", path: "/lessons/review", me: "viewer", answers: { "/api/lessons/review": "lessons-queue-no-access.json" } },
];

for (const shown of PAGES) {
  test(`${shown.name}: axe finds no WCAG 2.2 AA violations at 1440, 1024 and 390 px, and it reflows at 320 px`, async ({ page }) => {
    const answers: Record<string, Answer> = {};
    for (const [path, name] of Object.entries(shown.answers)) answers[path] = await file(name);
    await (shown.me === "reviewer" ? reviewer : viewer)(page, answers);
    for (const width of [1440, 1024, 390]) {
      await page.setViewportSize({ width, height: 900 });
      await page.goto(shown.path);
      await expect(page.locator("[data-library=ready], [data-queue=ready], [data-review-page]:not([data-review-page=loading]), [data-empty-state]").first()).toBeVisible();
      expect(await axe(page), `${shown.name} at ${width} px`).toEqual([]);
    }
    await page.setViewportSize({ width: 320, height: 800 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(320);
  });
}
