// The Lessons tab at seam 4 (ticket 29): the library, Waiting for review and one item's review page, against
// the answers the server wrote on the fixture (tests/record_lessons_api.py), which
// tests/test_lesson_review_routes.py checks the server still gives. The words below are the ticket's, DESIGN.md's
// and the 29 design brief's, copied here so the test checks the copy file against an independent source.
import { scan } from "./axe";
import type { Page } from "@playwright/test";
import { expect, recorded, test } from "./mocked";

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

const subTabs = (page: Page) => page.getByRole("navigation", { name: "Lesson pages" });

// ── Who sees the queue ───────────────────────────────────────────────────

test("someone who is not a lesson reviewer sees no sub-tab row, and the queue's address shows the no-access card", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await viewer(page, {
    // Ticket 39's page answers in one request (tests/record_lessons_page_api.py): here, Ana's first visit to an
    // empty library.
    "/api/lessons/page": await file("lessons-page-empty.json"),
    "/api/lessons/review": await file("lessons-queue-no-access.json"),
  });
  await page.goto("/lessons");
  await expect(page.locator("[data-library], [data-empty-state]").first()).toBeVisible();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Lessons");
  await expect(subTabs(page)).toHaveCount(0);
  await expect(page.getByRole("link", { name: /Waiting for review/ })).toHaveCount(0);
  // Brief 06's empty card, unchanged, for anyone who is not a reviewer.
  await expect(page.locator("[data-empty-state] h2")).toHaveText("There are no lessons in the library yet.");

  await page.goto("/lessons/review");
  const card = page.locator("[data-empty-state]");
  await expect(card.getByRole("heading")).toHaveText("I show this page only to lesson reviewers.");
  await expect(card.getByRole("link", { name: "Go to Lessons" })).toHaveAttribute("href", "/lessons");
  await expect(subTabs(page)).toHaveCount(0);
  await expect(page).toHaveTitle("Lessons | Strata");
});

test("a lesson reviewer sees the Lessons sub-tabs with the count waiting in their region, and the queue grouped for them", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await reviewer(page, { "/api/lessons/review": await file("lessons-queue.json") });
  await page.goto("/lessons/review");
  await expect(page.locator("[data-queue=ready]")).toBeVisible();

  await expect(subTabs(page).getByRole("link")).toHaveText(["Lessons", "Waiting for review (3)"]);
  await expect(subTabs(page).getByRole("link", { name: "Waiting for review (3)" })).toHaveAttribute("aria-current", "page");
  await expect(page).toHaveTitle("Waiting for review, Lessons | Strata");
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
  const date = table.locator("tbody tr").first().locator("td").nth(1);
  await expect(date).toHaveText("Oct 27, 2026");
  const lines = await date.evaluate((cell) => Math.round(cell.querySelector("span")!.getBoundingClientRect().height / parseFloat(getComputedStyle(cell).lineHeight)));
  expect(lines).toBe(1);
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
  // The page reads top to bottom: evidence, tags, summary, history, then the form.
  const order = await page.locator("main h2").allTextContents();
  expect(order).toEqual(["The evidence", "How I tagged it", "My summary of the evidence", "What has happened so far", "Your recommendation"]);
  // The writer's summary passed the verifier; the sentence it removed is shown with its reason.
  await expect(page.locator("[data-summary=ready] [data-removed-box]")).toContainText("I removed one sentence.");
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
  await expect(page.locator("[data-history] li").last()).toContainText(
    "Asha Raman, accredited procurement specialist, recommended adding it. Reason: \"The ICR and IEG's review both say estimates below market rates led to rebidding.\"",
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
  await expect(stale).toContainText("While you had this lesson open, Asha Raman recommended it on October 27, 2026.");
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

// ── The library ──────────────────────────────────────────────────────────

test("the library lists lesson cards newest first, naming roles and never people, with each lesson's edition", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  // Ticket 39's page (tests/record_lessons_page_api.py): the library comes last, after what changed and what is new.
  await viewer(page, { "/api/lessons/page": await file("lessons-page.json") });
  await page.goto("/lessons");
  const cards = page.locator("[data-library] [data-lesson-card=full]");
  await expect(cards).toHaveCount(2);
  await expect(page.locator("[data-library] [data-lead]")).toHaveText("Showing all two current lessons, newest first.");
  const first = cards.first();
  await expect(first).toContainText("A lead procurement specialist decided version 2 on October 29, 2026, after an accredited procurement specialist recommended it.");
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

// ── The evidence drawer ──────────────────────────────────────────────────

test("an evidence card's marker opens the drawer at its source, and focus comes back to the marker", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await reviewer(page, { [`/api/lessons/review/${REBIDDING}`]: await file("lessons-item-recommend.json") });
  await page.goto(`/lessons/review/${REBIDDING}`);
  const marker = page.locator("[data-lesson-evidence] [data-citation]").first();
  // Measure the column once its item has drawn in the web fonts: under the whole gate's load the first box
  // could be taken while the text was still in the fallback font, and the swap made the column 34 px taller.
  await expect(marker).toBeVisible();
  await page.evaluate(() => document.fonts.ready);
  const column = await page.locator("[data-document-column]").boundingBox();
  await marker.click();
  const drawer = page.getByRole("dialog");
  await expect(drawer).toBeVisible();
  await expect(page).toHaveURL(/evidence=strata\.gold\.passage%3A31525018%2Fv1%2F54|evidence=strata.gold.passage:31525018\/v1\/54/);
  // The quote the card showed is highlighted in the whole paragraph.
  await expect(drawer.locator("mark")).toHaveText("Highlight starts. 108 of 328 cases had to go through rebidding. Highlight ends.");
  // The column keeps its place and width while the drawer is open.
  expect(await page.locator("[data-document-column]").boundingBox()).toEqual(column);
  await page.keyboard.press("Escape");
  await expect(drawer).toHaveCount(0);
  await expect(marker).toBeFocused();
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
  await expect(drawer).toContainText("What · lesson");
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
