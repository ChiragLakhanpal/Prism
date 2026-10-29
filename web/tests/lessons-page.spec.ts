// The Lessons page and the version notices at seam 4 (ticket 39), against the answers the server wrote from
// tests/lessons_page_story.py (tests/record_lessons_page_api.py), which tests/test_lessons_page.py checks the server
// still gives. The words are the ticket's and the 39 brief's, copied here so the test checks the copy file against an
// independent source; the lesson's words are the reviewers' in the story.
import { scan } from "./axe";
import type { Page } from "@playwright/test";
import { expect, recorded, test } from "./mocked";

type Answer = { status?: number; body: string };
const REBIDDING = "lesson-e903b07ad1";
const DRAFT_TITLE = "Suggested PPSD risk rows for Equipping of Exploratory Bo reholes Project-Lot 1- Sarma n - Tarbaj Water Supply";

async function serve(page: Page, answers: Record<string, Answer>) {
  const asked: { call: string; search: string; body: unknown }[] = [];
  const all: Record<string, Answer> = {
    "/api/me": { body: await recorded("me.json") },
    "/api/freshness": { body: await recorded("freshness.json") },
    "/api/lessons/me": { body: await recorded("lessons-me-viewer.json") },
    "POST /api/evidence/opened": { body: '{"recorded":true}' },
    "/api/evidence/opened": { body: '{"opened":[]}' },
    "/api/drafts/existing": { body: '{"draft":null}' },
    ...answers,
  };
  await page.route("**/api/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    asked.push({ call: `${request.method()} ${url.pathname}`, search: url.search, body: request.postDataJSON?.() ?? null });
    const answer = all[`${request.method()} ${url.pathname}`] ?? all[url.pathname];
    if (!answer) return route.fulfill({ status: 404, json: { detail: "Not Found" } });
    return route.fulfill({ status: answer.status ?? 200, contentType: "application/json", body: answer.body });
  });
  return asked;
}

async function file(name: string): Promise<Answer> {
  return { body: await recorded(name) };
}

async function openLessons(page: Page, name = "lessons-page.json", extra: Record<string, Answer> = {}, path = "/lessons") {
  await page.setViewportSize({ width: 1440, height: 900 });
  const asked = await serve(page, { "/api/lessons/page": await file(name), ...extra });
  await page.goto(path);
  await expect(page.locator("[data-lessons-page=ready]")).toBeVisible();
  return asked;
}

async function axe(page: Page) {
  await page.waitForFunction(() => document.getAnimations().every((animation) => animation.playState !== "running"));
  const results = await scan(page);
  return results.violations.map((v) => `${v.id}: ${v.nodes.map((node) => node.target.join(" ")).join(", ")}`);
}

// ── The page, in the wireframe's order ───────────────────────────────────

// Ticket 102 (DESIGN.md section 1, principle 6, and section 5, Lessons page): the digest is the page's finding, 28/36
// Light and 24/32 below 48rem, and a first visit's status sentence is lead, 18/28 400.
const typeOf = (element: ReturnType<Page["locator"]>) =>
  element.evaluate((found) => {
    const style = getComputedStyle(found);
    return `${style.fontSize}/${style.lineHeight} ${style.fontWeight}`;
  });

// Each zone of the page in order: its name, and whether it is a panel or a row.
const zones = (page: Page) =>
  page.locator("main section[data-zone]").evaluateAll((all) => all.map((zone) => [zone.querySelector("[data-zone-name]")?.textContent, zone.getAttribute("data-zone")]));

test("the digest is the page's finding inside the first screen at 390 by 844 and 1024 by 768, then the zones in order, each a panel or a row by what it holds", async ({ page }) => {
  for (const [width, height, finding] of [[390, 844, "24px/32px 300"], [1024, 768, "28px/36px 300"]] as const) {
    await openLessons(page);
    await page.setViewportSize({ width, height });
    const digest = page.locator("main [data-finding]");
    await expect(digest).toHaveCount(1);
    await expect(digest).toHaveAttribute("id", "lessons-digest");
    expect(await typeOf(digest), `${width} px`).toBe(finding);
    const end = await digest.evaluate((found) => found.getBoundingClientRect().bottom + window.scrollY);
    expect(end, `${width} px`).toBeLessThanOrEqual(height);
    await expect(page.locator("main [data-status-lead]")).toHaveCount(0);
    await page.unrouteAll({ behavior: "ignoreErrors" });
  }
  await openLessons(page);
  const digest = page.locator("#lessons-digest");
  await expect(digest).toHaveText(
    "Since your last visit on October 22, 2026, two completion reports and two ICR Reviews came in. Two lessons are new and two changed.",
  );
  // 24 px after a finding (DESIGN.md section 4, space roles), then its sources note.
  const after = await digest.evaluate((found) => found.nextElementSibling!.getBoundingClientRect().top - found.getBoundingClientRect().bottom);
  expect(after).toBeCloseTo(24, 0);
  expect(await zones(page)).toEqual([
    ["Changed where you used it", "panel"],
    ["New", "panel"],
    ["Your reports", "row"],
    ["The library", "panel"],
  ]);

  // A count word opens the items it counts.
  await digest.getByRole("button", { name: "two" }).first().click();
  const reports = page.getByRole("dialog", { name: "Reports I read since October 22, 2026" });
  await expect(reports).toBeVisible();
  await expect(reports.locator("li")).toHaveCount(4);
  await page.keyboard.press("Escape");

  // The quiet line: a lesson you cite that only gained evidence, and no notice for it.
  await expect(page.locator("[data-strengthened]")).toContainText("One lesson you cite gained evidence since your last visit. Your drafts don't need to change.");

  expect(await axe(page)).toEqual([]);
});

test("a changed lesson shows was and now, the version's date, where it is used and the three actions", async ({ page }) => {
  await openLessons(page);
  const notice = page.locator("[data-version-notice=narrowed]");
  await expect(notice).toHaveCount(1);
  await expect(notice.locator("[data-badge=changed]")).toHaveText("Changed");
  await expect(notice.getByRole("heading", { level: 3 })).toHaveText("Base works estimates on market rates to avoid rebidding");
  const wasNow = notice.locator("[data-was-now]");
  await expect(wasNow).toContainText("Version 1, the one your draft cites.");
  await expect(wasNow).toContainText("Version 2, decided on October 29, 2026.");
  // The changed words are marked, and only those.
  await expect(wasNow.locator("[data-change-mark]").first()).toHaveText("Changed words start.costChanged words end.");
  await expect(notice.locator("[data-decided-line]")).toHaveText(
    'A lead procurement specialist made this change after an accredited procurement specialist recommended it. The lead\'s reason: "Current market rates is what the 2025 rules ask for."',
  );
  await expect(notice.locator("[data-use]")).toHaveCount(2);
  await expect(notice.locator("[data-use]").first()).toContainText(`Used in: ${DRAFT_TITLE} (cites version 1)`);
  await expect(notice.getByRole("link", { name: "See both versions" })).toBeVisible();
  await expect(notice.getByRole("button", { name: `Update the row in ${DRAFT_TITLE}` })).toHaveCount(2);
  await expect(notice.getByRole("button", { name: `Keep version 1, with a reason in ${DRAFT_TITLE}` })).toHaveCount(2);
  // The checked draft's feedforward says it goes back to Draft, before the click.
  await expect(notice.locator("[data-use]").nth(1).locator("[data-feedforward]")).toHaveText(
    "If you update the row, I rewrite it from version 2 and check it again. A draft you marked as checked goes back to Draft.",
  );
});

test("keeping version 1 needs a reason, sends the versions you saw and ends on the outcome", async ({ page }) => {
  const asked = await openLessons(page, "lessons-page.json", { "POST /api/drafts/draft-0001/rows/cost_estimates/lesson": await file("lessons-choice-kept.json") });
  const use = page.locator("[data-use=draft-0001]");
  await use.getByRole("button", { name: /^Keep version 1, with a reason/ }).click();
  const field = use.getByRole("textbox", { name: "Why keep version 1?" });
  await expect(field).toBeFocused();
  await use.getByRole("button", { name: "Keep version 1", exact: true }).click();
  await expect(use).toContainText("Write your reason first. It goes into the draft's evidence pack.");
  await field.fill("The borrower's estimates already use current rates.");
  await use.getByRole("button", { name: "Keep version 1", exact: true }).click();
  await expect(use.locator("[data-outcome]")).toBeFocused();
  await expect(use.locator("[data-outcome]")).toContainText("You kept version 1. I saved your reason with the draft, and it goes into the evidence pack.");
  const posted = asked.find((call) => call.call === "POST /api/drafts/draft-0001/rows/cost_estimates/lesson");
  expect(posted?.body).toMatchObject({ lesson_id: REBIDDING, action: "keep", expected_cited_version: 1, expected_current_version: 2, reason: "The borrower's estimates already use current rates." });
});

test("updating the row on the checked draft ends on its outcome, which says the draft is back in Draft", async ({ page }) => {
  const asked = await openLessons(page, "lessons-page.json", { "POST /api/drafts/draft-0002/rows/cost_estimates/lesson": await file("lessons-choice-updated.json") });
  const use = page.locator("[data-use=draft-0002]");
  await use.getByRole("button", { name: /^Update the row/ }).click();
  await expect(use.locator("[data-outcome=updated]")).toContainText(
    "You updated the row to version 2. I checked the new text, and the draft is back in Draft so you can check it.",
  );
  expect(asked.find((call) => call.call.startsWith("POST /api/drafts/draft-0002"))?.body).toMatchObject({ action: "update", expected_cited_version: 1, expected_current_version: 2 });
});

test("when none of the rewrite's sentences pass, the notice says the row is unchanged and shows what I removed and why", async ({ page }) => {
  await openLessons(page, "lessons-page.json", { "POST /api/drafts/draft-0002/rows/cost_estimates/lesson": await file("lessons-choice-nothing-passed.json") });
  const use = page.locator("[data-use=draft-0002]");
  await use.getByRole("button", { name: /^Update the row/ }).click();
  await expect(use.getByRole("alert")).toContainText("none of my sentences passed my checks, so I left the row as it was. It still cites version 1.");
  const box = use.locator("[data-removed-box]");
  await expect(box.locator("[data-removed-lead]")).toHaveText("I removed the one sentence I wrote.");
  await expect(box.getByRole("listitem")).toHaveText(
    '"Base the works cost estimates on market rates before the contracts go to bid." It cited a source other than this risk\'s records.',
  );
});

test("a use whose draft kind cannot rewrite the row offers only Keep, and says nothing about removing it", async ({ page }) => {
  // The recorded page, with draft-0001 standing in for a kind that has no writer for one row.
  const answer = JSON.parse(await recorded("lessons-page.json"));
  answer.notices[0].uses[0].can_update = false;
  await openLessons(page, "lessons-page.json", { "/api/lessons/page": { body: JSON.stringify(answer) } });
  const use = page.locator("[data-use=draft-0001]");
  await expect(use.getByRole("button", { name: /^Keep version 1, with a reason/ })).toBeVisible();
  await expect(use.getByRole("button", { name: /^(Update|Remove) the row/ })).toHaveCount(0);
  await expect(use.locator("[data-feedforward]")).toHaveCount(0);
  await expect(use).not.toContainText("If you remove the row");
  // The Keep button names no description that is not on the page.
  await expect(use.getByRole("button", { name: /^Keep version 1/ })).not.toHaveAttribute("aria-describedby", /.*/);
});

test("a lesson retired as wrong comes first and says it holds the export, with Remove the row and Keep the row", async ({ page }) => {
  await openLessons(page, "lessons-page-retired.json");
  const first = page.locator("[data-version-notice]").first();
  await expect(first).toHaveAttribute("data-version-notice", "retired_wrong");
  await expect(first.locator("[data-badge=retired-wrong]")).toHaveText("Retired as wrong");
  await expect(first.locator("[data-was-now]")).toContainText("Retired as wrong on October 29, 2026.");
  await expect(first.locator("[data-decided-line]")).toContainText("The lead's reason: \"IEG's own review later said the permits were not the cause.\"");
  await expect(first.locator("[data-hold-sentence]").first()).toHaveText("You can't export this draft until you choose what to do with this row.");
  await expect(first.getByRole("button", { name: /^Remove the row/ })).toHaveCount(2);
  await expect(first.getByRole("button", { name: /^Keep the row, with a reason/ })).toHaveCount(2);
  await expect(first.getByRole("link", { name: "Read the retired lesson" })).toBeVisible();
  expect(await axe(page)).toEqual([]);
});

// ── New, and the evidence badges ─────────────────────────────────────────

test("new lessons show their evidence badge: Restated by IEG for the ICR's lesson IEG's review restated", async ({ page }) => {
  await openLessons(page);
  const cards = page.locator("[data-new] [data-lesson-card]");
  await expect(cards).toHaveCount(2);
  await expect(page.locator(`#new-lesson-${REBIDDING} [data-badge=restated]`)).toHaveText("Restated by IEG");
  await expect(page.locator("[data-new] [data-badge=ieg-lesson]")).toHaveText("IEG's lesson");
  await expect(page.locator(`#new-lesson-${REBIDDING}`)).toContainText("Request for Bids (RFB)");
});

test("a new lesson resting on an ICR whose ICR Review is not out yet shows Awaiting IEG review", async ({ page }) => {
  // The fixture holds no such lesson (every recorded ICR's project has its ICR Review), so this answer is the
  // recorded one with one card's ieg_status set as the server sets it then (brief 29, section 4.4).
  const answer = JSON.parse(await recorded("lessons-page.json"));
  answer.new_lessons.cards[1].ieg_status = "awaiting";
  await openLessons(page, "lessons-page.json", { "/api/lessons/page": { body: JSON.stringify(answer) } });
  await expect(page.locator("[data-new] [data-badge=awaiting]")).toHaveText("Awaiting IEG review");
});

// ── Your reports ─────────────────────────────────────────────────────────

test("your reports read the retrieval loop's counts, with words for one to nine", async ({ page }) => {
  await openLessons(page);
  await expect(page.locator("[data-feedback-line]")).toHaveText(
    "You marked two passages as wrong; one is fixed, and 14 answers now cite the right paragraph.",
  );
});

// ── The library ──────────────────────────────────────────────────────────

test("the library's filters change the list at once, keep the address, and the count line compares like with like", async ({ page }) => {
  const asked = await openLessons(page, "lessons-page.json", { "/api/lessons/library": await file("lessons-library-method-rfq.json") });
  const library = page.locator("[data-library=ready]");
  await expect(library.locator("[data-lead]")).toHaveText("Showing all two current lessons, newest first.");
  // The four filters sit in one row at 1440 px, each as wide as its words, and stack on a phone.
  const boxes = () => library.locator("[data-filter]").evaluateAll((all) => all.map((select) => select.getBoundingClientRect()).map(({ top, width }) => ({ top: Math.round(top), width })));
  const wide = await boxes();
  expect(wide).toHaveLength(4);
  expect(new Set(wide.map((box) => box.top)).size).toBe(1);
  expect(Math.max(...wide.map((box) => box.width))).toBeLessThan(400);
  await page.setViewportSize({ width: 390, height: 844 });
  expect(new Set((await boxes()).map((box) => box.top)).size).toBe(4);
  await page.setViewportSize({ width: 1440, height: 900 });
  await library.getByLabel("Method").selectOption("Request for Quotations");
  await expect(library.locator("[data-lead]")).toHaveText("Showing one of two current lessons, newest first.");
  await expect(page).toHaveURL(/\/lessons\?method=Request\+for\+Quotations$/);
  await expect(library.locator("#method-caption")).toHaveText("Lessons that name no method are included, because they apply to every method.");
  await expect(library.locator("[data-lesson-card]")).toHaveCount(1);
  expect(asked.some((call) => call.call === "GET /api/lessons/library" && call.search === "?method=Request+for+Quotations")).toBe(true);

  // Going back to the starting filters asks again, so the list, the select and the address all follow.
  const unfiltered = await recorded("lessons-library.json");
  const again: string[] = [];
  await page.route("**/api/lessons/library**", (route) => {
    again.push(new URL(route.request().url()).search);
    return route.fulfill({ contentType: "application/json", body: unfiltered });
  });
  await library.getByRole("button", { name: "Reset the filters" }).click();
  await expect(library.locator("[data-lead]")).toHaveText("Showing all two current lessons, newest first.");
  await expect(page).toHaveURL(/\/lessons$/);
  await expect(library.getByLabel("Method")).toHaveValue("");
  await expect(library.locator("[data-lesson-card]")).toHaveCount(2);
  expect(again).toEqual([""]);
});

test("a page past the end of the library says so and links to the first page, not that nothing matches", async ({ page }) => {
  const answer = JSON.parse(await recorded("lessons-page.json"));
  answer.library = JSON.parse(await recorded("lessons-library-past-end.json"));
  await openLessons(page, "lessons-page.json", { "/api/lessons/page": { body: JSON.stringify(answer) } }, "/lessons?page=99");
  const library = page.locator("[data-library=ready]");
  await expect(library.locator("[data-empty-state] h3")).toHaveText("There is no page 99 in the library.");
  await expect(library.getByRole("link", { name: "Go to the first page" })).toHaveAttribute("href", "/lessons");
});

// ── The first visit and nothing new ──────────────────────────────────────

test("a first visit's status sentence is lead, not the finding, and a visit with nothing new is the finding, with no new or gained-evidence lines", async ({ page }) => {
  await openLessons(page, "lessons-page-first.json");
  const status = page.locator("main [data-status-lead]");
  await expect(status).toHaveText("This is your first visit to Lessons. The library holds two current lessons.");
  expect(await typeOf(status)).toBe("18px/28px 400");
  await expect(page.locator("main [data-finding]")).toHaveCount(0);
  // Its caption, then the sources note, then the zones: the reader's reports and the library.
  await expect(page.locator("[data-digest=first] p")).toHaveText([
    "This is your first visit to Lessons. The library holds two current lessons.",
    "From your next visit, I start this page with what came in since this one.",
    "Lessons come from Implementation Completion and Results Reports (ICRs), and from ICR Reviews and Project Performance Assessment Reports (PPARs) by the Independent Evaluation Group (IEG).",
  ]);
  expect(await zones(page)).toEqual([
    ["Your reports", "row"],
    ["The library", "panel"],
  ]);
  // The count word in the status sentence still opens what it counts.
  await status.getByRole("button", { name: "two" }).click();
  await expect(page.getByRole("dialog", { name: "The library" })).toBeVisible();
  await page.keyboard.press("Escape");
  expect(await axe(page)).toEqual([]);

  await page.unrouteAll({ behavior: "ignoreErrors" });
  await openLessons(page, "lessons-page-nothing.json");
  await expect(page.locator("main [data-finding]")).toHaveText("Nothing came in since your last visit on October 30, 2026, and no lesson changed.");
  await expect(page.locator("[data-new], [data-strengthened]")).toHaveCount(0);
  // The notice stays until the author chooses, whatever happened to the last visit, and its zone says the change came
  // before that visit, so "no lesson changed" above it still reads true.
  await expect(page.locator("[data-version-notice=narrowed]")).toHaveCount(1);
  await expect(page.locator("[data-changed] [data-zone-caption]")).toHaveText(
    "This change came before your last visit. Your drafts still cite the version you used, and nothing in a draft changes until you choose.",
  );
  expect(await axe(page)).toEqual([]);
});

test("when the page's one read fails, its error alert is in the alert slot with Try again, the h1 names the page and nothing else draws", async ({ page }) => {
  let fail = true;
  await page.setViewportSize({ width: 1440, height: 900 });
  await serve(page, {
    "/api/lessons/page": { status: 503, body: '{"code":"data_service","trace_id":"0af7651916cd43dd8448eb211c80319c"}' },
  });
  const ready = await file("lessons-page.json");
  await page.route("**/api/lessons/page", (route) => (fail ? route.fallback() : route.fulfill({ contentType: "application/json", body: ready.body })));
  await page.goto("/lessons");
  const slot = page.locator("[data-alert-slot]");
  await expect(slot.locator("[role=alert]")).toHaveText("I couldn't load the lessons because the data service didn't answer.");
  await expect(page.locator("main h1")).toHaveText("Lessons");
  await expect(page.locator("main [data-zone], main [data-finding], main [data-status-lead]")).toHaveCount(0);
  await expect(page.locator("main")).not.toContainText("These are lessons quoted from completion reports");
  fail = false;
  await slot.getByRole("button", { name: "Try again" }).click();
  await expect(page.locator("[data-lessons-page=ready]")).toBeVisible();
  await expect(slot).not.toContainText("I couldn't load the lessons");
});

// Ticket 114: the empty library's sentences answer whose lessons these are, who decides, what happens to the proposed
// ones and where the lessons show up anyway, and link where section 3's own empty state links: Data readiness for the
// sources the package page's risks draw on (the server's answer for section 3, risks-ke-nwwda-541055.json). Ticket 102:
// they sit in the library's zone as a row, under its name, and never repeat the digest above them. One page load serves
// both widths.
test("at 1440 and 390 px the empty library is a row that says whose lessons they are, who decides, and where they show up on a package's page", async ({ page }) => {
  await openLessons(page, "lessons-page-empty.json");
  await expect(page.locator("main [data-status-lead]")).toHaveText("This is your first visit to Lessons. The library has no lessons yet.");
  expect(await zones(page)).toEqual([
    ["Your reports", "row"],
    ["The library", "row"],
  ]);
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: 900 });
    const card = page.locator("[data-library=empty]");
    await expect(card.getByRole("heading", { level: 2 })).toHaveText("The library");
    await expect(card).not.toContainText("no lessons yet");
    await expect(card).not.toContainText("No lesson has entered the library yet.");
    await expect(card.locator("[data-library-empty] p")).toHaveText([
      "I propose each lesson, and a lead procurement specialist decides whether it enters the library. Proposed lessons " +
        "wait for that decision, and only lesson reviewers can read them.",
      "On a package's page, in section 3, Procurement risks and what helped, I show the lessons from projects with " +
        "comparable packages.",
      "See which completion reports I have read",
    ]);
    // The purpose above says whose lessons they are, so the row does not say it again.
    await expect(page.locator("main [data-page-head]")).toContainText("quoted from completion reports");
    const section3 = JSON.parse(await recorded("risks-ke-nwwda-541055.json"));
    expect(section3.empty_reason).toBe("no_reports");
    const link = card.getByRole("link", { name: "See which completion reports I have read" });
    await expect(link).toHaveAttribute("href", `/data?sources=${section3.coverage.sources.join(",")}&from=package_risks`);
    await expect(link).toHaveAttribute("href", "/data?sources=notices,awards,documents,projects&from=package_risks");
    // The page's caption spells IEG out above the card; the opening sentence still counts what came in.
    await expect(page.locator("main")).toContainText("by the Independent Evaluation Group (IEG)");
    await expect(page.locator("#lessons-digest")).toHaveText("This is your first visit to Lessons. The library has no lessons yet.");
    await expect(card).not.toContainText(/approv/i);
    expect((await scan(page, "[data-library=empty]")).violations, `${width} px`).toEqual([]);
  }
});

// Round 1 of ticket 102: as of a past date the page shows only what was disclosed by then (the server's own answer,
// tests/record_lessons_page_api.py), and says so once, in the alert slot; the library's own sentence is a status line.
test("as of a past date the page says so once, and the library holds only what was public then", async ({ page }) => {
  await openLessons(page, "lessons-page-asof.json", { "/api/me": await file("me-asof.json") }, "/lessons?asof=2016-08-26");
  await expect(page.locator("[data-alert-slot] [data-alert=info]")).toContainText("August 26, 2016");
  await expect(page.locator("[data-alert]")).toHaveCount(1);
  await expect(page.locator("main [data-status-lead]")).toHaveText(
    "You are seeing the library as of August 26, 2016, with each lesson at the version that was current then.",
  );
  expect(await zones(page)).toEqual([["The library", "row"]]);
  await expect(page.locator("main")).not.toContainText(/2019|2023|2026/);
});

test("a preview leaves out the reader's drafts, reports and the proposed count", async ({ page }) => {
  await openLessons(page, "lessons-page-preview.json", {}, "/lessons?view=piu");
  await expect(page.locator("[data-changed], [data-reports], [data-strengthened]")).toHaveCount(0);
  await expect(page.locator("main")).toContainText("This is a preview, so I leave out what is about you");
});

// ── Two versions of a lesson ─────────────────────────────────────────────

test("See both versions opens the evidence drawer on the two versions, with the changed words marked", async ({ page }) => {
  await openLessons(page, "lessons-page.json", { "/api/evidence": await file("lessons-versions.json") });
  await page.locator("[data-version-notice=narrowed]").getByRole("link", { name: "See both versions" }).click();
  const drawer = page.locator("[data-evidence-drawer]");
  await expect(drawer.getByRole("heading", { level: 2 })).toHaveText("Versions 1 and 2 of a lesson");
  await expect(drawer.locator("[data-version-block]")).toHaveCount(2);
  await expect(drawer.locator("[data-version-block='2'] [data-change-mark]")).toHaveCount(2);
});

// ── The draft page ───────────────────────────────────────────────────────

test("on the draft, the changed lesson's row shows was and now under it with the same choices", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await serve(page, { "GET /api/drafts/draft-0001": await file("drafts-lesson-notice.json") });
  await page.goto("/drafts/draft-0001");
  const notice = page.locator("[data-row-notice=narrowed]");
  await expect(notice).toHaveCount(1);
  await expect(notice).toContainText("This row cites version 1 of a lesson that changed.");
  await expect(notice.locator("[data-was-now]")).toContainText("Version 1, the one this row cites.");
  await expect(notice.getByRole("button", { name: /^Update the row/ })).toBeVisible();
  await expect(notice.getByRole("button", { name: /^Keep version 1, with a reason/ })).toBeVisible();
  // A changed lesson holds nothing: the bar's hold line names only the check and the owners.
  await expect(page.locator("[data-hold-line]")).not.toContainText("retired as wrong");
  expect(await axe(page)).toEqual([]);
});

test("a lesson retired as wrong holds the draft's export, and the hold line links to the row's notice", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await serve(page, { "GET /api/drafts/draft-0001": await file("drafts-lesson-retired.json") });
  await page.goto("/drafts/draft-0001");
  await expect(page.locator("[data-row-notice=retired_wrong]")).toContainText("This row cites a lesson that a lead procurement specialist retired as wrong.");
  const hold = page.locator("[data-hold-line]");
  await expect(hold).toContainText("remove or keep, with a reason, one row that cites a lesson retired as wrong");
  await expect(hold.locator("[data-hold-link=lessonRetiredWrong]")).toHaveAttribute("href", "#notice-permits_before_award");
});

test("a part that cites two changed lessons shows both notices, the one that holds the export first, and the hold links to it", async ({ page }) => {
  // The recorded summary, with a narrowed notice for a second lesson listed before the retired one.
  const draft = JSON.parse(await recorded("drafts-paper-lesson-retired.json"));
  const [retired] = draft.lesson_notices;
  const narrowed = { ...retired, lesson_id: "lesson-0000000002", tier: "narrowed", holds_export: false, anchor: "notice-ppsd", retired_on: null, retired_as: null, a: 1, b: 2, between: [], actions: ["keep"] };
  draft.lesson_notices = [narrowed, retired];
  await page.setViewportSize({ width: 1440, height: 900 });
  await serve(page, { "GET /api/drafts/draft-0003": { body: JSON.stringify(draft) } });
  await page.goto("/drafts/draft-0003");
  const notices = page.locator("[data-paper-part=ppsd] [data-row-notice]");
  await expect(notices).toHaveCount(2);
  await expect(notices.nth(0)).toHaveAttribute("data-row-notice", "retired_wrong");
  await expect(notices.nth(0)).toHaveAttribute("id", "notice-ppsd");
  await expect(notices.nth(1)).toHaveAttribute("data-row-notice", "narrowed");
  await expect(notices.nth(1)).toHaveAttribute("id", "notice-ppsd-lesson-0000000002-v1");
  await expect(page.locator("[data-hold-link=lessonRetiredWrong]")).toHaveAttribute("href", "#notice-ppsd");
});

test("on a Project Paper summary, the PPSD part that cites a lesson retired as wrong shows its notice, and the hold links to it", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await serve(page, { "GET /api/drafts/draft-0003": await file("drafts-paper-lesson-retired.json") });
  await page.goto("/drafts/draft-0003");
  const part = page.locator("[data-paper-part=ppsd]");
  await expect(part.locator("#notice-ppsd[data-row-notice=retired_wrong]")).toContainText("retired as wrong");
  await expect(part.getByRole("button", { name: /^Remove the row/ })).toBeVisible();
  const hold = page.locator("[data-hold-line]");
  await expect(hold.locator("[data-hold-link=lessonRetiredWrong]")).toHaveAttribute("href", "#notice-ppsd");
});
