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
  const existing = { body: await recorded("drafts-existing-yours.json"), delay: 150 };
  const me = { body: await recorded("me.json") };
  await serve(page, {
    [`/api${PLAN}`]: { body: await recorded("check-plan-p156634-nwwda-2026-10-09.json") },
    "/api/drafts/existing": existing,
    "/api/me": me,
  });
  await page.goto(PLAN);

  await expect(page.locator("[data-existing-draft]")).toHaveText("You started review notes on this plan on October 23, 2026.");
  await expect(page.getByRole("link", { name: "Open the draft" })).toHaveAttribute("href", DRAFT);
  await expect(page.getByRole("button", { name: "Draft review notes (3 rows)" })).toBeVisible();

  // Ben, Ana's teammate, sees her name.
  Object.assign(existing, { body: await recorded("drafts-existing.json") });
  me.body = await recorded("drafts-me-teammate.json");
  await page.reload();
  await expect(page.locator("[data-existing-draft]")).toHaveText("Ana Example started review notes on this plan on October 23, 2026.");
});

test("an open draft the lookup finds late is not put above a plan check already drawn", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await serve(page, {
    [`/api${PLAN}`]: { body: await recorded("check-plan-p156634-nwwda-2026-10-09.json") },
    "/api/drafts/existing": { body: await recorded("drafts-existing-yours.json"), delay: 900 },
  });
  await page.goto(PLAN);
  const action = page.getByRole("button", { name: "Draft review notes (3 rows)" });
  await expect(action).toBeVisible();
  const before = (await action.boundingBox())!.y;

  await page.waitForTimeout(1200);
  await expect(page.locator("[data-existing-draft]")).toHaveCount(0);
  expect((await action.boundingBox())!.y).toBe(before);
});

test("an open draft the lookup finds before a slow plan check is drawn is named, and the page does not move after", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await serve(page, {
    [`/api${PLAN}`]: { body: await recorded("check-plan-p156634-nwwda-2026-10-09.json"), delay: 1200 },
    "/api/drafts/existing": { body: await recorded("drafts-existing-yours.json"), delay: 500 },
  });
  await page.goto(PLAN);
  const action = page.getByRole("button", { name: "Draft review notes (3 rows)" });
  await expect(action).toBeVisible({ timeout: 5000 });
  await expect(page.locator("[data-existing-draft]")).toHaveText("You started review notes on this plan on October 23, 2026.");
  const before = (await action.boundingBox())!.y;
  await page.waitForTimeout(1000);
  expect((await action.boundingBox())!.y).toBe(before);
});

test("on the agency's latest plan, with no version in the address, the lookup starts at once and its notice shows above a slow check", async ({ page }) => {
  // The one box sends a STEP reference on an agency's latest plan here, so the lookup cannot wait for the
  // check to say which version it shows (the 35 review, round 3).
  const latest = PLAN.slice(0, PLAN.lastIndexOf("/"));
  await page.setViewportSize({ width: 1440, height: 900 });
  const asked: string[] = [];
  page.on("request", (request) => {
    if (request.url().includes("/api/drafts/existing")) asked.push(new URL(request.url()).search);
  });
  await serve(page, {
    [`/api${latest}`]: { body: await recorded("check-plan-p156634-nwwda-2026-10-09.json"), delay: 1200 },
    "/api/drafts/existing": { body: await recorded("drafts-existing-latest.json"), delay: 500 },
  });
  await page.goto(latest);
  const action = page.getByRole("button", { name: "Draft review notes (3 rows)" });
  await expect(action).toBeVisible({ timeout: 5000 });
  await expect(page.locator("[data-existing-draft]")).toHaveText("You started review notes on this plan on October 23, 2026.");
  expect(asked).toEqual(["?kind=review_notes&project_id=P156634&agency_id=northern-water-works-development-agency"]);
  const before = (await action.boundingBox())!.y;
  await page.waitForTimeout(1000);
  expect((await action.boundingBox())!.y).toBe(before);
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
  await expect(page).toHaveTitle("Review notes on the Northern Water Works Development Agency plan of Oct 9, 2026 | Strata");
  expect(asked.filter((call) => call === "POST /api/drafts")).toHaveLength(1);
  await page.goBack();
  await expect(page).toHaveURL(PLAN);
});

test("a draft written in this visit, opened again from Drafts after it was checked, shows the state the server holds", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  const draft = { body: await recorded("drafts-review-notes-draft.json") };
  // The Drafts tab as the server lists it once Ana has checked draft-0001: under Checked, not yet exported.
  const list = JSON.parse(await recorded("drafts-list.json"));
  const entry = list.groups.exported.find((one: { draft_id: string }) => one.draft_id === "draft-0001");
  list.groups.exported = list.groups.exported.filter((one: { draft_id: string }) => one !== entry);
  list.groups.checked.unshift(Object.assign(entry, { state: "checked", exported: null }));
  const asked = await serve(page, {
    [`/api${PLAN}`]: { body: await recorded("check-plan-p156634-nwwda-2026-10-09.json") },
    "POST /api/drafts": { body: await recorded("drafts-write-review-notes.sse") },
    [`GET /api${DRAFT}`]: draft,
    "POST /api/drafts/draft-0001/check": { body: await recorded("drafts-review-notes-checked.json") },
    "/api/drafts": { body: JSON.stringify(list) },
  });
  await page.goto(PLAN);
  await page.getByRole("button", { name: "Draft review notes (3 rows)" }).click();
  await bar(page).getByRole("button", { name: "Mark as checked" }).click();
  await expect(page.locator("[aria-current=step]")).toHaveText("Checked by you");
  const reads = asked.filter((call) => call === `GET /api${DRAFT}`).length;

  draft.body = await recorded("drafts-review-notes-checked.json");
  await page.getByRole("navigation", { name: "Main" }).getByRole("link", { name: "Drafts" }).click();
  await page.locator(`[data-draft-group=checked] a[href="${DRAFT}"]`).click();

  await expect(page.locator("[aria-current=step]")).toHaveText("Checked by you");
  await expect(page.locator("[data-page-status]")).toHaveText("");
  expect(asked.filter((call) => call === `GET /api${DRAFT}`).length).toBeGreaterThan(reads);
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
  const heading = page.getByRole("heading", { name: "I couldn't write a note that passed my checks, so I saved no draft." });
  await expect(heading).toBeVisible();
  await expect(page.locator("[data-removed-lead]")).toHaveText("I removed all three sentences.");
  // No step is running, so the finished steps start at the heading's edge, with no empty icon rail.
  const step = await page.locator("[data-step=done] > span:last-child").first().boundingBox();
  expect(Math.round(step!.x)).toBe(Math.round((await heading.boundingBox())!.x));
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
  // The evidence pack writes the same check line, word for word (the server wrote it on the fixture).
  expect(await page.locator("[data-check-line]").evaluate((element) => (element as HTMLElement).innerText.replace(/\s+/g, " ").trim())).toBe(
    (await recorded("drafts-check-line.txt")).trim(),
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
  // Where the column sits on the page (not in the window, which scrolls to the marker), and how wide it is.
  const place = () =>
    page.locator("[data-document-column]").evaluate((element) => {
      const box = element.getBoundingClientRect();
      return [Math.round(box.x), Math.round(box.top + window.scrollY), Math.round(box.width)];
    });
  const before = await place();
  const headerHeight = () => page.locator("[data-draft-header]").evaluate((element) => element.getBoundingClientRect().height);
  const tall = await headerHeight();

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
  expect(await place()).toEqual(before);
  // The header keeps its height too, so nothing under it moves up.
  expect(await headerHeight()).toBe(tall);
});

test("opening a source, by click or by Enter, or switching to another, keeps the window still and the note in view above the bar", async ({ page }) => {
  const scrollY = () => page.evaluate(() => window.scrollY);
  for (const [width, height] of [[1440, 900], [1024, 768]]) {
    for (const how of ["click", "Enter"]) {
      const where = `${how} at ${width} by ${height}`;
      await openDraft(page, { width, height });
      const marker = notes(page).locator("[data-citation='2']").first();
      // Put the second note's marker 450 px down the window.
      const top = (await marker.boundingBox())!.y;
      await page.evaluate((by) => window.scrollBy(0, by), top - 450);
      await expect.poll(async () => Math.abs((await marker.boundingBox())!.y - 450)).toBeLessThanOrEqual(2);
      const before = await scrollY();

      if (how === "click") await marker.click();
      else {
        await marker.focus();
        await page.keyboard.press("Enter");
      }
      await expect(page.getByRole("dialog")).toBeVisible();
      await expect(page.getByRole("dialog").getByRole("heading").first()).toBeFocused();
      // The marker shown now (in the cards, if the notes turned into cards) sits in the window above the bar.
      const clear = async () => {
        const [box, edge] = [await notes(page).locator("[data-citation='2']").first().boundingBox(), await bar(page).boundingBox()];
        return box!.y >= 0 && box!.y + box!.height <= edge!.y;
      };
      await expect.poll(clear, { message: where }).toBe(true);
      // From 1200 px the notes keep their place. At 1024 px the narrower column turns the notes into cards,
      // which moves the note, so the page scrolls only the few pixels that keep its marker clear of the bar.
      expect(Math.abs((await scrollY()) - before), where).toBeLessThanOrEqual(width >= 1200 ? 8 : 40);
    }
  }

  // With the drawer open, the next note's source opens in it without moving the window either.
  const next = notes(page).locator("[data-citation='3']").first();
  await page.evaluate((by) => window.scrollBy(0, by), (await next.boundingBox())!.y - 400);
  await expect.poll(async () => Math.abs((await next.boundingBox())!.y - 400)).toBeLessThanOrEqual(2);
  const before = await scrollY();
  await next.click();
  await expect(page.getByRole("dialog")).toContainText("KE-NWWDA-541062-CW-RFQ");
  expect(Math.abs((await scrollY()) - before)).toBeLessThanOrEqual(8);

  // A source opened from the Sources list keeps the window still too.
  await openDraft(page, { width: 1440, height: 900 });
  const listed = page.locator("[data-sources] [data-citation='1']");
  await page.evaluate((by) => window.scrollBy(0, by), (await listed.boundingBox())!.y - 450);
  await expect.poll(async () => Math.abs((await listed.boundingBox())!.y - 450)).toBeLessThanOrEqual(2);
  const still = await scrollY();
  await listed.click();
  await expect(page.getByRole("dialog").getByRole("heading").first()).toBeFocused();
  expect(Math.abs((await scrollY()) - still)).toBeLessThanOrEqual(8);
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
  await expect(page.locator("[data-export-success]")).toContainText(
    "The evidence pack lists all 3 sources and whether you opened each one. Your browser downloaded the Word file, and the " +
      "evidence pack's files are below. I keep all three with this draft for your team. I sent nothing to anyone.",
  );
  await expect(page.getByRole("link", { name: `${WORD}, Word file, 6 footnotes` })).toHaveAttribute("download", WORD);
  await expect(page.getByRole("link", { name: /evidence-pack\.pdf, Evidence pack, PDF$/ })).toBeVisible();
  await expect(page.getByRole("link", { name: /evidence-pack\.csv, Evidence pack, CSV$/ })).toBeVisible();
  await expect(page.locator("[aria-current=step]")).toHaveText("Exported");
  await expect(bar(page)).toHaveCount(0);
  // No mail, share or send control anywhere on the page.
  await expect(page.getByRole("button", { name: /email|share|send/i })).toHaveCount(0);
});

test("an export whose files are gone says so, and does not offer them", async ({ page }) => {
  const exported = JSON.parse(await recorded("drafts-review-notes-exported.json"));
  Object.assign(exported.export, { files_available: false, files: [] });
  await openDraft(page, { answers: { "GET /api/drafts/draft-0001": { body: JSON.stringify(exported) } } });

  const panel = page.locator("[data-export-success]");
  await expect(panel.locator("p")).toHaveText([
    "I sent nothing to anyone.",
    "I can't find the files from this export. I kept the record of the export, so the data team can restore the files from Draft ID draft-0001.",
  ]);
  await expect(panel.getByRole("link")).toHaveCount(0);
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
  await expect(sentence).toHaveText("You discarded these review notes, so your team no longer sees them in Drafts.");
  await expect(sentence).toBeFocused();
  await expect(page.getByText("Discarded on October 23, 2026")).toBeVisible();
  // Stuck to the window's bottom edge, the notice ends the scrolling notes as the bar did: a 1px rule above
  // it, with 12 px of the page's background on each side of the alert.
  const frame = await page.locator("[data-discarded-notice]").evaluate((element) => {
    const style = getComputedStyle(element);
    return [style.position, style.borderTopWidth, style.borderTopStyle, style.paddingTop, style.paddingBottom];
  });
  expect(frame).toEqual(["sticky", "1px", "solid", "12px", "12px"]);
  await page.getByRole("button", { name: "Restore the draft" }).click();
  await expect(bar(page).getByRole("button", { name: "Mark as checked" })).toBeFocused();
  await expect(bar(page).locator("[data-bar-status]")).toHaveText("You restored the draft.");
});

test("Mark as checked, Discard and Restore the draft move focus into the sticky bar without scrolling the notes", async ({ page }) => {
  const discarded = JSON.parse(await recorded("drafts-review-notes-discarded.json"));
  Object.assign(discarded, { draft_id: "draft-0001" });
  const scrollY = () => page.evaluate(() => window.scrollY);
  const from300 = async () => {
    await page.evaluate(() => window.scrollTo(0, 300));
    await expect.poll(scrollY).toBe(300);
  };
  // A click where the button is, as a person makes it: Playwright's own click first scrolls the button out
  // of the page's scroll padding, which would hide what the page does.
  const press = async (name: string) => {
    const box = (await page.getByRole("button", { name, exact: true }).boundingBox())!;
    await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
  };

  await openDraft(page, { answers: { "POST /api/drafts/draft-0001/check": { body: await recorded("drafts-review-notes-checked.json") } } });
  await from300();
  await press("Mark as checked");
  await expect(bar(page).getByRole("button", { name: "Export to Word" })).toBeFocused();
  expect(Math.abs((await scrollY()) - 300), "Mark as checked").toBeLessThanOrEqual(2);

  await openDraft(page, {
    answers: {
      "POST /api/drafts/draft-0001/discard": { body: JSON.stringify(discarded) },
      "POST /api/drafts/draft-0001/restore": { body: await recorded("drafts-review-notes-draft.json") },
    },
  });
  await from300();
  await press("Discard");
  await expect(page.locator("[data-discarded-sentence]")).toBeFocused();
  expect(Math.abs((await scrollY()) - 300), "Discard").toBeLessThanOrEqual(2);
  await press("Restore the draft");
  await expect(bar(page).getByRole("button", { name: "Mark as checked" })).toBeFocused();
  expect(Math.abs((await scrollY()) - 300), "Restore the draft").toBeLessThanOrEqual(2);
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

  // The draft reloads in its state now, says so beside the buttons and above the page, and focus goes to
  // that state's next step.
  await expect(page.locator("[aria-current=step]")).toHaveText("Checked by you");
  await expect(bar(page).locator("[data-bar-notice]")).toHaveText("This draft changed in another tab or window, so I reloaded it.");
  await expect(page.locator("main [role=status]").filter({ hasText: "This draft changed" }).first()).toBeVisible();
  await expect(bar(page).getByRole("button", { name: "Export to Word" })).toBeFocused();

  await page.unroute("**/api/drafts/draft-0001");
  await openDraft(page, { answers: { "POST /api/drafts/draft-0001/check": { status: 503, body: '{"code":"data_service"}' } } });
  await bar(page).getByRole("button", { name: "Mark as checked" }).click();
  await expect(bar(page).getByRole("alert")).toHaveText("I couldn't save your check just now. The notes are still a draft.");
  await expect(bar(page).getByRole("button", { name: "Mark as checked" })).toBeFocused();
});

test("a teammate reads the draft, with the author's name in the bar and the stepper, and cannot act on it", async ({ page }) => {
  await openDraft(page, { file: "drafts-review-notes-teammate.json", answers: { "/api/me": { body: await recorded("drafts-me-teammate.json") } } });

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

test("the header and the bar stick in a window at least 768 px wide and 640 px tall, and a focused marker stays clear of the bar", async ({ page }) => {
  await openDraft(page, { width: 1440, height: 900 });
  const header = page.locator("[data-draft-header]");
  // At the top of the page the bar already sits on the bottom edge of the window, over the notes.
  await page.evaluate(() => window.scrollTo(0, 0));
  expect(await bar(page).evaluate((element) => Math.round(element.getBoundingClientRect().bottom))).toBe(900);
  // Scrolled, the header stays at the top of the window with the stepper in it.
  await page.evaluate(() => window.scrollTo(0, 900));
  expect(await header.evaluate((element) => Math.round(element.getBoundingClientRect().top))).toBe(0);
  await expect(header.locator("[aria-current=step]")).toBeInViewport();
  // Focus the last note's marker from the top of the page: scroll padding keeps it above the bar (WCAG 2.4.11).
  await page.evaluate(() => window.scrollTo(0, 0));
  const last = notes(page).locator("[data-citation='3']").last();
  await last.focus();
  const [marker, edge] = [await last.boundingBox(), await bar(page).boundingBox()];
  expect(marker!.y + marker!.height).toBeLessThanOrEqual(edge!.y);
  expect(edge!.y + edge!.height).toBeLessThanOrEqual(900);

  // A short or narrow window: the bar sits at the end of the document.
  for (const [width, height] of [[1440, 600], [390, 844]]) {
    await page.setViewportSize({ width, height });
    await page.evaluate(() => window.scrollTo(0, 0));
    const top = await bar(page).evaluate((element) => element.getBoundingClientRect().top);
    expect(top, `${width} by ${height}`).toBeGreaterThan(height);
  }
});

test("a double click on Mark as checked never exports the draft", async ({ page }) => {
  const asked = await openDraft(page, { answers: {
    "POST /api/drafts/draft-0001/check": { body: await recorded("drafts-review-notes-checked.json"), delay: 60 },
    "POST /api/drafts/draft-0001/export": { body: await recorded("drafts-review-notes-exported.json") },
  } });
  const check = bar(page).getByRole("button", { name: "Mark as checked" });
  const box = (await check.boundingBox())!;

  await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
  await page.waitForTimeout(150);
  await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2, { clickCount: 2 });

  await expect(page.locator("[data-draft-page=checked]")).toBeVisible();
  await page.waitForTimeout(500);
  await expect(page.locator("[data-draft-page=checked]")).toBeVisible();
  expect(asked).not.toContain("POST /api/drafts/draft-0001/export");
});

test("Discard's label starts on the bar text's left edge", async ({ page }) => {
  await openDraft(page);
  const text = await bar(page).locator("[data-bar-lead]").evaluate((element) => {
    const range = document.createRange();
    range.setStart(element.firstChild!, 0);
    range.setEnd(element.firstChild!, 1);
    return range.getBoundingClientRect().x;
  });
  const label = await bar(page).getByRole("button", { name: "Discard" }).locator("span span").first().evaluate((element) => {
    const range = document.createRange();
    range.selectNodeContents(element);
    return range.getBoundingClientRect().x;
  });
  expect(Math.abs(label - text)).toBeLessThanOrEqual(1);
});

test("the loading skeleton puts the notes and the bar where the loaded draft puts them, with the bar's sentence", async ({ page }) => {
  const body = await recorded("drafts-review-notes-draft.json");
  await serve(page, {});
  for (const [width, height, notesView] of [[1440, 900, "table"], [390, 844, "ul"]] as const) {
    await page.setViewportSize({ width, height });
    let release = () => {};
    const held = new Promise<void>((resolve) => (release = resolve));
    await page.route("**/api/drafts/draft-0001", async (route) => {
      await held;
      await route.fulfill({ contentType: "application/json", body });
    });
    await page.goto(DRAFT);
    const box = (selector: string) =>
      page.locator(selector).evaluate((element) => {
        const rect = element.getBoundingClientRect();
        return { top: rect.top + window.scrollY, inWindow: rect.top, height: rect.height };
      });
    const where = `${width} by ${height}`;
    const skeleton = page.locator("[data-draft-page=loading]");
    // The bar's consequence sentence is true before the draft loads, so it is there as text.
    await expect(bar(page)).toContainText(CONSEQUENCE);
    const [notesBefore, barBefore] = [await box(`[data-draft-page=loading] ${notesView}:visible`), await box("[data-draft-page=loading] section")];
    await expect(skeleton).toBeVisible();
    release();
    await expect(page.locator("[data-draft-page=draft]")).toBeVisible();
    const notesAfter = await box(`[data-draft-notes] [data-view]:visible`);
    const barAfter = await box("[data-draft-bar]");
    expect(Math.abs(notesAfter.top - notesBefore.top), where).toBeLessThanOrEqual(12);
    expect(Math.abs(barAfter.height - barBefore.height), where).toBeLessThanOrEqual(12);
    // Where the bar sticks, the skeleton's bar already sits on the window's bottom edge.
    if (width >= 768) expect(Math.round(barBefore.inWindow + barBefore.height), where).toBe(height);
    await page.unroute("**/api/drafts/draft-0001");
  }
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
  // In the bar beside the drawer, the consequence sentence's key word and the opened count each stay on one line.
  const lines = (words: string) =>
    bar(page).locator("[data-bar-lead]").evaluate((lead, words) => {
      const walker = document.createTreeWalker(lead, NodeFilter.SHOW_TEXT);
      for (let node = walker.nextNode(); node; node = walker.nextNode()) {
        const at = node.textContent!.indexOf(words);
        if (at < 0) continue;
        const range = document.createRange();
        range.setStart(node, at);
        range.setEnd(node, at + words.length);
        return new Set([...range.getClientRects()].map((rect) => Math.round(rect.top))).size;
      }
      return 0;
    }, words);
  expect(await lines("no-objection")).toBe(1);
  await expect(bar(page).locator("[data-opened-link]")).toHaveText("You opened 1 of 3 sources");
  expect(await lines("You opened 1 of 3 sources")).toBe(1);
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
