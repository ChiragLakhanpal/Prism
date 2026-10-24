// Drafts at seam 4 (ticket 35): Check a plan's "Draft review notes (3 rows)", the writing page, a draft's
// page with its bar, and the Drafts tab, against the answers the server wrote on the fixture
// (tests/record_drafts_api.py), which tests/test_drafts.py checks the server still gives. The words below
// are the ticket's, DESIGN.md's and the 35 design brief's, copied here so the test checks the copy file
// against an independent source. The network is off: the shared fixture fails any test whose page asks
// for anything outside its own origin, so these tests also prove that exporting reaches nothing outside.
import AxeBuilder from "@axe-core/playwright";
import type { Page } from "@playwright/test";
import { draftBarSentence } from "./design-md";
import { expect, recorded, test } from "./mocked";

const PLAN = "/projects/P156634/procurement/northern-water-works-development-agency/2026-10-09";
const DRAFT = "/drafts/draft-0001";
const MARKED = ["KE-NWWDA-541055-CW-RFB", "KE-NWWDA-229129-CW-RFB", "KE-NWWDA-541062-CW-RFQ"];
const WCAG_22_AA = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];
const CONSEQUENCE = "Exporting sends nothing and is not a World Bank review, clearance or no-objection.";
const WORD = "review-notes-P156634-northern-water-works-development-agency-2026-10-09.docx";

type Answer = { status?: number; body: string; delay?: number };

// Serve /api from recorded answers, by "METHOD /path" or by path for any method. An /api call with no
// answer gets 404, and the test that made it can see it in the list this returns.
async function serve(page: Page, answers: Record<string, Answer>) {
  const asked: string[] = [];
  const base: Record<string, Answer> = {
    "/api/me": { body: await recorded("me.json") },
    "/api/freshness": { body: await recorded("freshness.json") },
    "POST /api/evidence/opened": { body: '{"recorded":true}' },
    "/api/drafts/existing": { body: '{"draft":null}' },
  };
  const all = { ...base, ...answers };
  await page.route("**/api/**", async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    asked.push(`${request.method()} ${path}`);
    const answer = all[`${request.method()} ${path}`] ?? all[path];
    if (!answer) return route.fulfill({ status: 404, json: { detail: "Not Found" } });
    if (answer.delay) await new Promise((resolve) => setTimeout(resolve, answer.delay));
    return route.fulfill({ status: answer.status ?? 200, contentType: "application/json", body: answer.body });
  });
  return asked;
}

async function openDraft(page: Page, { file = "drafts-review-notes-draft.json", path = DRAFT, width = 1440, height = 900, answers = {} }:
  { file?: string; path?: string; width?: number; height?: number; answers?: Record<string, Answer> } = {}) {
  await page.setViewportSize({ width, height });
  const asked = await serve(page, { [`GET /api${path.split("?")[0]}`]: { body: await recorded(file) }, ...answers });
  await page.goto(path);
  await expect(page.locator("[data-draft-page]:not([data-draft-page=loading])")).toBeVisible();
  return asked;
}

const bar = (page: Page) => page.getByRole("region", { name: "Check and export" });
const notes = (page: Page) => page.locator("[data-draft-notes] [data-view]:visible");

async function axe(page: Page) {
  await page.waitForFunction(() => document.getAnimations().every((animation) => animation.playState !== "running"));
  const results = await new AxeBuilder({ page }).withTags(WCAG_22_AA).analyze();
  return results.violations.map((v) => `${v.id}: ${v.nodes.map((node) => node.target.join(" ")).join(", ")}`);
}

// ── Check a plan: the action ─────────────────────────────────────────────

test("Check a plan offers to draft review notes on its three marked rows, and says the draft waits in Drafts", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await serve(page, { [`/api${PLAN}`]: { body: await recorded("check-plan-p156634-nwwda-2026-10-09.json") } });
  await page.goto(PLAN);

  const action = page.getByRole("button", { name: "Draft review notes (3 rows)" });
  await expect(action).toBeVisible();
  await expect(action).toHaveAttribute("data-button", "primary");
  // The button sits in the sticky header, to the right of the check pill, on the h1's first line.
  const header = page.locator("[data-plan-header]");
  await expect(header.locator("[data-draft-action]")).toBeVisible();
  const [pill, button] = [await header.locator("[data-check-pill]").boundingBox(), await action.boundingBox()];
  expect(button!.x).toBeGreaterThan(pill!.x + pill!.width);
  await expect(action).toHaveAccessibleDescription(
    "I write one note for each activity that needs a look or is worth watching. The draft waits in Drafts for you to check. I send nothing.",
  );
});

test("with no activity marked, a preview or an as-of date, Check a plan offers no draft", async ({ page }) => {
  const result = JSON.parse(await recorded("check-plan-p156634-nwwda-2026-10-09.json"));
  for (const row of result.rows) row.marks = row.marks.filter((mark: { mark: string }) => mark.mark === "data_note");
  Object.assign(result.counts, { needs_a_look: 0, watch: 0, signal: 0 });
  await page.setViewportSize({ width: 1440, height: 900 });
  await serve(page, { [`/api${PLAN}`]: { body: JSON.stringify(result) } });
  await page.goto(PLAN);
  await expect(page.locator("[data-draft-slot=none]")).toHaveText(
    "No activity needs a look or is worth watching, so I have no review notes to draft.",
  );
  await expect(page.locator("[data-draft-action]")).toHaveCount(0);

  await page.goto(`${PLAN}?asof=2026-10-12`);
  await expect(page.locator("[data-draft-slot=asof]")).toHaveText("I draft review notes only from today's check, not from a past date.");
  await page.goto(`${PLAN}?view=piu`);
  await expect(page.locator("[data-check-plan-page=ready]")).toBeVisible();
  await expect(page.locator("[data-draft-slot], [data-draft-action]")).toHaveCount(0);
});

test("Check a plan names the review notes the team already started on the same plan, and still offers a new draft", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await serve(page, {
    [`/api${PLAN}`]: { body: await recorded("check-plan-p156634-nwwda-2026-10-09.json") },
    "/api/drafts/existing": { body: await recorded("drafts-existing.json") },
  });
  await page.goto(PLAN);

  await expect(page.locator("[data-existing-draft]")).toHaveText("Ana Example started review notes on this plan on October 23, 2026.");
  await expect(page.getByRole("link", { name: "Open the draft" })).toHaveAttribute("href", DRAFT);
  await expect(page.getByRole("button", { name: "Draft review notes (3 rows)" })).toBeVisible();
});

// ── Writing ──────────────────────────────────────────────────────────────

test("drafting shows the marked activities at once, then becomes the saved draft in place, and Back returns to the plan check", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  const asked = await serve(page, {
    [`/api${PLAN}`]: { body: await recorded("check-plan-p156634-nwwda-2026-10-09.json") },
    "POST /api/drafts": { body: await recorded("drafts-write-review-notes.sse"), delay: 600 },
    [`GET /api${DRAFT}`]: { body: await recorded("drafts-review-notes-draft.json") },
  });
  await page.goto(PLAN);
  await page.getByRole("button", { name: "Draft review notes (3 rows)" }).click();

  // The writing page: the activity cells from the plan check the page held, needs a look first, and the
  // note cells as skeletons.
  await expect(page).toHaveURL(/\/drafts\/new\?kind=review_notes&pid=P156634&agency=northern-water-works-development-agency&version=2026-10-09$/);
  await expect(page.locator("[data-draft-new=writing]")).toBeVisible();
  await expect(notes(page).locator("[data-activity-ref]")).toHaveText(MARKED);
  await expect(page.getByRole("heading", { level: 1 })).toBeFocused();
  // The saved draft, in place: the same address is replaced, so Back goes to the plan check.
  await expect(page).toHaveURL(DRAFT);
  await expect(page.locator("[data-draft-page=draft]")).toBeVisible();
  await expect(page.locator("[data-page-status]")).toHaveText("The draft is ready. I wrote three notes.");
  expect(asked.filter((call) => call === "POST /api/drafts")).toHaveLength(1);
  await page.goBack();
  await expect(page).toHaveURL(PLAN);
});

test("Stop writing goes back to the plan check, which says nothing was saved", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await serve(page, {
    [`/api${PLAN}`]: { body: await recorded("check-plan-p156634-nwwda-2026-10-09.json") },
    "POST /api/drafts": { body: await recorded("drafts-write-review-notes.sse"), delay: 60_000 },
  });
  await page.goto(PLAN);
  await page.getByRole("button", { name: "Draft review notes (3 rows)" }).click();
  await page.getByRole("button", { name: "Stop writing" }).click();

  await expect(page).toHaveURL(PLAN);
  await expect(page.getByText("I stopped writing the review notes and saved nothing.")).toBeVisible();
});

test("a writer that does not answer, or notes that all fail the checks, save nothing and say so", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  const stream = { body: await recorded("drafts-write-agent-unavailable.sse") };
  await serve(page, { [`/api${PLAN}`]: { body: await recorded("check-plan-p156634-nwwda-2026-10-09.json") }, "POST /api/drafts": stream });
  await page.goto(PLAN);
  await page.getByRole("button", { name: "Draft review notes (3 rows)" }).click();
  await expect(page.getByRole("alert")).toContainText(
    "I couldn't write the review notes, because the model that writes my drafts did not respond. I saved nothing.",
  );
  await expect(page.locator("[data-write-reference]")).toHaveText("If it fails again, send the data team this reference: run-0006.");

  stream.body = await recorded("drafts-write-nothing-survived.sse");
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(page.getByRole("heading", { name: "I couldn't write a note that passed my checks, so I saved no draft." })).toBeVisible();
  await expect(page.locator("[data-removed-lead]")).toHaveText("I removed all three sentences.");
});

test("a reload of the writing page says I'm not writing, and links back to the plan check", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await serve(page, {});
  await page.goto("/drafts/new?kind=review_notes&pid=P156634&agency=northern-water-works-development-agency&version=2026-10-09");

  await expect(page.getByRole("heading", { name: "I'm not writing a draft right now." })).toBeVisible();
  await expect(page.getByRole("link", { name: "Back to the plan check" })).toHaveAttribute("href", PLAN);
});

// ── A draft's page ───────────────────────────────────────────────────────

test("the draft's notes cite their plan rows, and the bar says what exporting does and is not, with the opened count", async ({ page }) => {
  await openDraft(page);

  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Review notes");
  await expect(page.locator("[data-lede]")).toHaveText("I drafted a note on each of the three activities that need a look or are worth watching.");
  await expect(notes(page).locator("[data-activity-ref]")).toHaveText(MARKED);
  await expect(page.locator("[data-count-line]")).toHaveText("Showing all 3 activities with a signal");
  // The check line names what this draft's checks did not cover. Until ticket 24 adds the fourth check,
  // it also says whether each sentence follows from its sources was not checked.
  await expect(page.locator("[data-check-line]")).toContainText(
    "Not checked: whether each sentence follows from its sources, whether the plan's published records are complete, or whether these notes are what you would tell the borrower.",
  );
  await expect(page.locator("[data-removed-box]")).toHaveText("I removed no sentences.");
  // DESIGN.md section 5's sentence adapted to review notes, ending with the fixed consequence sentence;
  // then the opened count and the hold line.
  const sentence = await draftBarSentence();
  expect(sentence.endsWith(CONSEQUENCE)).toBe(true);
  await expect(bar(page).locator("[data-bar-lead]")).toHaveText(
    `${sentence} You opened 0 of 3 sources. Mark the notes as checked before you export them.`,
  );
  await expect(page.locator("[data-sources-caption]")).toHaveText("You opened 0 of 3. In the Word file, each of the 6 citations becomes a footnote.");
  await expect(page).toHaveTitle("Review notes on the Northern Water Works Development Agency plan of Oct 9, 2026 | Strata");
});

test("in Draft, Export to Word is held with its reason, Mark as checked is the one solid button, and Discard sits at the far left", async ({ page }) => {
  await openDraft(page);
  const exportButton = bar(page).getByRole("button", { name: "Export to Word" });
  const check = bar(page).getByRole("button", { name: "Mark as checked" });
  const discard = bar(page).getByRole("button", { name: "Discard" });

  await expect(exportButton).toHaveAttribute("aria-disabled", "true");
  await expect(exportButton).not.toHaveAttribute("disabled");
  await expect(exportButton).toHaveAccessibleDescription("Mark the notes as checked before you export them.");
  await expect(page.locator("main [data-button=primary]")).toHaveCount(1);
  await expect(check).toHaveAttribute("data-button", "primary");
  // DOM order matches the order on screen: Discard, Export to Word, Mark as checked.
  const [d, e, c] = [await discard.boundingBox(), await exportButton.boundingBox(), await check.boundingBox()];
  expect(d!.x + d!.width).toBeLessThan(e!.x - 100);
  expect(e!.x + e!.width).toBeLessThanOrEqual(c!.x);
  // Activating a held button does nothing.
  await exportButton.focus();
  await page.keyboard.press("Enter");
  await expect(page.locator("[data-draft-page=draft]")).toBeVisible();
});

test("opening a source counts it in the bar and the Sources list at once, and the evidence drawer opens beside the notes", async ({ page }) => {
  const asked = await openDraft(page);

  await notes(page).locator("[data-citation='2']").first().click();

  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(bar(page).locator("[data-opened-link]")).toHaveText("You opened 1 of 3 sources");
  await expect(page.locator("[data-source-item$='KE-NWWDA-229129-CW-RFB'] [data-opened]")).toHaveText("You opened this.");
  expect(asked).toContain("POST /api/evidence/opened");
  // From 1200 px the column keeps to columns 1 to 7, so the drawer opens into the free space: the notes
  // do not move.
  const column = await page.locator("[data-document-column]").boundingBox();
  const drawer = await page.getByRole("dialog").boundingBox();
  expect(column!.x + column!.width).toBeLessThanOrEqual(drawer!.x);
});

test("Mark as checked saves, moves the state on and makes Export to Word the solid button, with focus on it", async ({ page }) => {
  await openDraft(page, { answers: { "POST /api/drafts/draft-0001/check": { body: await recorded("drafts-review-notes-checked.json"), delay: 300 } } });
  const check = bar(page).getByRole("button", { name: "Mark as checked" });

  await check.click();
  await expect(bar(page)).toHaveAttribute("aria-busy", "true");
  await expect(bar(page).getByRole("button", { name: "Saving" })).toBeVisible();

  const exportButton = bar(page).getByRole("button", { name: "Export to Word" });
  await expect(exportButton).toBeFocused();
  await expect(exportButton).toHaveAttribute("data-button", "primary");
  await expect(exportButton).not.toHaveAttribute("aria-disabled");
  await expect(page.locator("[aria-current=step]")).toHaveText("Checked by you");
  await expect(bar(page).locator("[data-hold-line]")).toHaveCount(0);
  await expect(bar(page).locator("[data-bar-status]")).toHaveText("You marked these notes as checked. You can export them now.");
});

test("Export downloads the Word file, ends on a success that names it and its footnotes, and reaches nothing outside Strata", async ({ page }) => {
  await openDraft(page, {
    file: "drafts-review-notes-checked.json",
    answers: {
      "POST /api/drafts/draft-0001/export": { body: await recorded("drafts-review-notes-exported.json") },
      [`/api/drafts/draft-0001/files/${WORD}`]: { body: "word" },
    },
  });
  const downloaded = page.waitForEvent("download");

  await bar(page).getByRole("button", { name: "Export to Word" }).click();

  expect((await downloaded).suggestedFilename()).toBe(WORD);
  const heading = page.getByRole("heading", { name: "Exported. I made a Word file with 6 footnotes and an evidence pack." });
  await expect(heading).toBeFocused();
  await expect(page.locator("[data-export-success]")).toContainText("The files went only to your browser's downloads. I sent nothing to anyone.");
  await expect(page.getByRole("link", { name: `${WORD}, Word file, 6 footnotes` })).toHaveAttribute("download", WORD);
  await expect(page.getByRole("link", { name: /evidence-pack\.pdf, Evidence pack, PDF$/ })).toBeVisible();
  await expect(page.getByRole("link", { name: /evidence-pack\.csv, Evidence pack, CSV$/ })).toBeVisible();
  await expect(page.locator("[aria-current=step]")).toHaveText("Exported");
  await expect(bar(page)).toHaveCount(0);
  // No mail, share or send control anywhere on the page.
  await expect(page.getByRole("button", { name: /email|share|send/i })).toHaveCount(0);
});

test("Discard is undone by Restore the draft, which puts the bar back in the state it was in", async ({ page }) => {
  const discarded = JSON.parse(await recorded("drafts-review-notes-discarded.json"));
  Object.assign(discarded, { draft_id: "draft-0001" });
  await openDraft(page, {
    answers: {
      "POST /api/drafts/draft-0001/discard": { body: JSON.stringify(discarded) },
      "POST /api/drafts/draft-0001/restore": { body: await recorded("drafts-review-notes-draft.json") },
    },
  });

  await bar(page).getByRole("button", { name: "Discard" }).click();

  const sentence = page.locator("[data-discarded-sentence]");
  await expect(sentence).toHaveText("I discarded these review notes, and your team no longer sees them in Drafts.");
  await expect(sentence).toBeFocused();
  await expect(page.getByText("Discarded on October 23, 2026")).toBeVisible();
  await page.getByRole("button", { name: "Restore the draft" }).click();
  await expect(bar(page).getByRole("button", { name: "Mark as checked" })).toBeFocused();
  await expect(bar(page).locator("[data-bar-status]")).toHaveText("I restored the draft.");
});

test("a refused act shows its failure in the bar and keeps the state; a change made elsewhere reloads the draft", async ({ page }) => {
  const checked = await recorded("drafts-review-notes-checked.json");
  let reads = 0;
  await page.setViewportSize({ width: 1440, height: 900 });
  await serve(page, { "POST /api/drafts/draft-0001/check": { status: 409, body: '{"code":"stale","error":"stale","state":"checked"}' } });
  await page.route("**/api/drafts/draft-0001", async (route) => {
    reads += 1;
    return route.fulfill({ contentType: "application/json", body: reads === 1 ? await recorded("drafts-review-notes-draft.json") : checked });
  });
  await page.goto(DRAFT);
  await bar(page).getByRole("button", { name: "Mark as checked" }).click();

  await expect(page.getByText("This draft changed in another tab or window, so I reloaded it.")).toBeVisible();
  await expect(page.locator("[aria-current=step]")).toHaveText("Checked by you");

  await page.unroute("**/api/drafts/draft-0001");
  await openDraft(page, { answers: { "POST /api/drafts/draft-0001/check": { status: 503, body: '{"code":"data_service"}' } } });
  await bar(page).getByRole("button", { name: "Mark as checked" }).click();
  await expect(bar(page).getByRole("alert")).toHaveText("I couldn't save your check just now. The notes are still a draft.");
  await expect(bar(page).getByRole("button", { name: "Mark as checked" })).toBeFocused();
});

test("a teammate reads the draft, with the author's name in the bar and the stepper, and cannot act on it", async ({ page }) => {
  await openDraft(page, { file: "drafts-review-notes-teammate.json" });

  await expect(bar(page).locator("[data-bar-lead]")).toContainText(
    `A working draft of Ana Example's review notes on the borrower's Procurement Plan. ${CONSEQUENCE}`,
  );
  await expect(bar(page).locator("[data-read-only]")).toHaveText("Only Ana Example can mark these notes as checked or export them.");
  await expect(bar(page).getByRole("button")).toHaveCount(0);
  await expect(page.getByText("I drafted these notes for Ana Example on October 23, 2026.")).toBeVisible();
});

test("an activity whose sentences all failed, and a refused one, keep their rows with a sentence that says so", async ({ page }) => {
  await openDraft(page, { file: "drafts-review-notes-partial.json", path: "/drafts/draft-0002" });
  await expect(page.locator("[data-lede]")).toHaveText("I drafted notes on two of the three activities that need a look or are worth watching.");
  await expect(notes(page).locator("tbody tr").nth(2)).toContainText(
    "I couldn't write a note on this activity that passed my checks. The sentences I removed are listed above, with the reason for each.",
  );
  await expect(page.locator("[data-removed-lead]")).toHaveText("I removed two sentences.");

  await openDraft(page, { file: "drafts-review-notes-refused.json", path: "/drafts/draft-0003" });
  await expect(notes(page).locator("tbody tr").nth(2)).toContainText("I didn't write a note on this activity");
});

test("a draft another team made, a failed read and the previews each say so in the first person", async ({ page }) => {
  await openDraft(page, { path: "/drafts/draft-9999", answers: { "GET /api/drafts/draft-9999": { status: 404, body: '{"code":"unknown_draft"}' } } });
  await expect(page.getByRole("heading", { name: "I can't find this draft." })).toBeVisible();

  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto(`${DRAFT}?view=piu`);
  await expect(page.getByRole("heading", { name: "I don't show review notes in this preview, because they are a World Bank staff draft." })).toBeVisible();
  await page.goto(`${DRAFT}?view=public`);
  await expect(page.getByRole("heading", { name: "The public view has no drafts." })).toBeVisible();
});

test("the bar sticks only in a window at least 768 px wide and 640 px tall, and a focused marker in the last row stays clear of it", async ({ page }) => {
  await openDraft(page, { width: 1440, height: 900 });
  await expect(bar(page)).toHaveCSS("position", "sticky");
  // Tab to the last note's marker: scroll padding keeps it above the bar (WCAG 2.4.11).
  const last = notes(page).locator("[data-citation='3']").last();
  await last.focus();
  const [marker, edge] = [await last.boundingBox(), await bar(page).boundingBox()];
  expect(marker!.y + marker!.height).toBeLessThanOrEqual(edge!.y);

  await page.setViewportSize({ width: 1440, height: 600 });
  await expect(bar(page)).toHaveCSS("position", "static");
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(bar(page)).toHaveCSS("position", "static");
});

test("the notes are a table on a wide column, and cards below 560 px of column, as at 390 px or beside the drawer at 1024 px", async ({ page }) => {
  await openDraft(page, { width: 390, height: 844 });
  await expect(page.locator("[data-draft-notes] [data-view=cards]")).toBeVisible();
  await expect(page.locator("[data-draft-notes] [data-view=table]")).toBeHidden();
  // Below 768 px the breadcrumb is a link back to Drafts.
  await expect(page.locator("[data-breadcrumb] p a")).toHaveText("Drafts");
  // Nothing scrolls sideways at 320 px.
  await page.setViewportSize({ width: 320, height: 800 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(320);

  await openDraft(page, { width: 1024, height: 900, path: `${DRAFT}?evidence=${encodeURIComponent("strata.silver.plan_rows:40132287/KE-NWWDA-541055-CW-RFB")}` });
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(page.locator("[data-draft-notes] [data-view=cards]")).toBeVisible();
});

test("the draft pages have no WCAG 2.2 AA violations at 1440, 1024 and 390 px", async ({ page }) => {
  test.setTimeout(60_000);
  for (const width of [1440, 1024, 390]) {
    for (const [file, path] of [
      ["drafts-review-notes-draft.json", DRAFT],
      ["drafts-review-notes-exported.json", DRAFT],
      ["drafts-review-notes-teammate.json", DRAFT],
      ["drafts-review-notes-discarded.json", "/drafts/draft-0004"],
    ]) {
      await openDraft(page, { file, path, width, height: 900 });
      expect(await axe(page), `${file} at ${width} px`).toEqual([]);
    }
  }
});

// ── The Drafts tab ───────────────────────────────────────────────────────

test("the Drafts tab lists the team's drafts under To check, Checked and Exported, with the author's opened count", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await serve(page, { "/api/drafts": { body: await recorded("drafts-list.json") } });
  await page.goto("/drafts");

  const groups = page.locator("[data-draft-group]");
  await expect(groups.getByRole("heading", { level: 2 })).toHaveText(["To check", "Checked", "Exported"]);
  const toCheck = page.locator("[data-draft-group=to_check]");
  await expect(toCheck).toContainText("One draft.");
  await expect(toCheck.getByRole("link")).toHaveText("Review notes on the Northern Water Works Development Agency plan of Oct 9, 2026");
  await expect(toCheck).toContainText("Water and Sanitation Development Project (P156634). Two notes. Drafted by you on October 23, 2026.");
  await expect(toCheck).toContainText("You opened 0 of 2 sources.");
  await expect(page.locator("[data-draft-group=exported]")).toContainText("Three notes. Exported by you on October 23, 2026.");
  // Only the author's own discarded drafts, folded.
  const fold = page.locator("[data-discarded-fold]");
  await expect(fold).toContainText("You discarded one draft.");
  await fold.getByRole("button", { name: "Show it" }).click();
  await expect(fold.getByRole("link")).toHaveAttribute("href", "/drafts/draft-0004");
  expect(await axe(page)).toEqual([]);
});

test("a teammate's Drafts tab names the author and has no opened count or discarded fold; an empty one shows its card", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const list = { body: await recorded("drafts-list-teammate.json") };
  await serve(page, { "/api/drafts": list });
  await page.goto("/drafts");
  await expect(page.locator("[data-draft-group=checked]")).toContainText("Checked by Ana Example on October 23, 2026.");
  await expect(page.getByText(/You opened/)).toHaveCount(0);
  await expect(page.locator("[data-discarded-fold]")).toHaveCount(0);
  expect(await axe(page)).toEqual([]);

  list.body = await recorded("drafts-list-empty.json");
  await page.reload();
  await expect(page.getByRole("heading", { name: "You have no drafts to check." })).toBeVisible();
});
