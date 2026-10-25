// Suggested PPSD risk rows and the Project Paper summary at seam 4 (ticket 36): the package workspace's "Suggest {n}
// PPSD risk rows", the draft page in the Short Form and the Long Form with its fill-in chips, the bar's export holds
// with a disagreement card's choices, Check a plan's "Drafts from this check" and the summary's page, against the
// answers the server wrote on the fixture (tests/record_ppsd_api.py), which tests/test_ppsd_rows.py checks the server
// still gives. The column names are the PPSD templates' (tests/ground_truth/values.toml, ppsd-short-* and
// ppsd-long-*), the footnote forms are the ticket's, and the words are the 36 brief's, copied here so the test checks
// the copy file against an independent source. A *-made-up-* answer is a state the fixture cannot reach, for layout
// and states only.
import { scan } from "./axe";
import type { Page } from "@playwright/test";
import { expect, recorded, test } from "./mocked";

const REF = "KE-NWWDA-541055-CW-RFB";
const PACKAGE = `/packages/${REF}`;
const API = `/api/packages/${REF}`;
const DRAFT = "/drafts/draft-0001";
const PAPER = "/drafts/draft-0002";
const CARD_DRAFT = "/drafts/draft-0090";
const PLAN = "/projects/P156634/procurement/northern-water-works-development-agency/2026-10-09";
const SHORT = ["Risk Description", "Description of mitigation", "Risk Owner"];
const LONG_ADDED = ["Likelihood Rating", "Impact Rating", "Overall Risk Score (A*B)", "Procurement Process Stage"];
const COST = "Cost estimates below market rates";
const PERMITS = "Land, forest and other permits not in place before award";

type Answer = { status?: number; body: string; delay?: number };

// Serve /api from recorded answers, by "METHOD /path" or by path for any method; anything else gets 404. Returns the
// calls made, with their bodies.
async function serve(page: Page, answers: Record<string, Answer>) {
  const asked: { call: string; body: unknown }[] = [];
  const all: Record<string, Answer> = {
    "/api/me": { body: await recorded("me.json") },
    "/api/freshness": { body: await recorded("freshness.json") },
    "POST /api/evidence/opened": { body: '{"recorded":true}' },
    "/api/evidence/opened": { body: '{"opened":[]}' },
    "/api/drafts/existing": { body: '{"draft":null}' },
    ...answers,
  };
  await page.route("**/api/**", async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    asked.push({ call: `${request.method()} ${path}`, body: request.postDataJSON?.() ?? null });
    const answer = all[`${request.method()} ${path}`] ?? all[path];
    if (!answer) return route.fulfill({ status: 404, json: { detail: "Not Found" } });
    if (answer.delay) await new Promise((resolve) => setTimeout(resolve, answer.delay));
    return route.fulfill({ status: answer.status ?? 200, contentType: "application/json", body: answer.body });
  });
  return asked;
}

async function openDraft(page: Page, file: string, { path = DRAFT, width = 1440, answers = {} }: { path?: string; width?: number; answers?: Record<string, Answer> } = {}) {
  await page.setViewportSize({ width, height: 900 });
  const asked = await serve(page, { [`GET /api${path}`]: { body: await recorded(file) }, ...answers });
  await page.goto(path);
  await expect(page.locator("[data-draft-page]:not([data-draft-page=loading])")).toBeVisible();
  return asked;
}

const bar = (page: Page) => page.getByRole("region", { name: "Check and export" });
const holdLine = (page: Page) => bar(page).locator("[data-hold-line]");

async function axe(page: Page) {
  await page.waitForFunction(() => document.getAnimations().every((animation) => animation.playState !== "running"));
  const results = await scan(page);
  return results.violations.map((v) => `${v.id}: ${v.nodes.map((node) => node.target.join(" ")).join(", ")}`);
}

// ── The package workspace's action ───────────────────────────────────────

async function openPackage(page: Page, { width = 1440, risks = "risks-ke-nwwda-541055-india-selected.json", me = "" } = {}) {
  await page.setViewportSize({ width, height: 900 });
  const asked = await serve(page, {
    // Suggested PPSD rows are a World Bank staff draft, so the workspace offers them to staff only.
    "/api/me": { body: me || (await recorded("me-staff.json")) },
    [API]: { body: await recorded("package-ke-nwwda-541055.json") },
    [`${API}/comparables`]: { body: await recorded("comparables-ke-nwwda-541055.json") },
    [`${API}/risks`]: { body: await recorded(risks) },
    [`${API}/steps`]: { body: await recorded("steps-ke-nwwda-541055.json") },
    [`${API}/risk-selection`]: { body: await recorded("risks-selection-saved.json") },
    "POST /api/drafts": { body: await recorded("drafts-write-ppsd.sse"), delay: 300 },
    [`GET /api${DRAFT}`]: { body: await recorded("drafts-ppsd-draft.json") },
  });
  await page.goto(PACKAGE);
  await expect(page.locator("section#risks [data-finding]").first()).toBeVisible();
  return asked;
}

test("the workspace's one solid button suggests a row for each risk you selected, and starts the writer for the package with no risk keys", async ({ page }) => {
  const asked = await openPackage(page);
  const action = page.locator("[data-ppsd-action][data-placement=header]");
  await expect(action.getByRole("button")).toHaveText("Suggest 1 PPSD risk row");
  await expect(action.getByRole("button")).toHaveAttribute("data-button", "primary");
  await expect(action).toContainText("The draft waits in Drafts for you to check. I send nothing.");
  // Only one copy is in the accessibility tree: the one under section 3 is for page areas below 768 px.
  await expect(page.locator("[data-ppsd-action][data-placement=inline]")).toBeHidden();

  // Selecting the second risk counts it at once.
  await page.locator("section#risks [data-risk-view]:visible").getByRole("checkbox", { name: new RegExp(PERMITS) }).check();
  await expect(action.getByRole("button")).toHaveText("Suggest 2 PPSD risk rows");

  await action.getByRole("button").click();
  await expect(page).toHaveURL(new RegExp(`/drafts/new\\?kind=ppsd_rows&package=${REF}$`));
  await expect(page).toHaveURL(DRAFT);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Suggested risk rows for the borrower's PPSD");
  const sent = asked.find((one) => one.call === "POST /api/drafts")!.body as Record<string, unknown>;
  expect(sent.kind).toBe("ppsd_rows");
  expect(sent.package).toBe(REF);
  expect(JSON.stringify(sent)).not.toContain("cost_estimates");
});

test("with no risk selected the action is held with its reason, and below 768 px it sits under section 3's last risk", async ({ page }) => {
  await openPackage(page, { risks: "risks-ke-nwwda-541055-india.json" });
  const held = page.locator("[data-ppsd-action][data-placement=header]").getByRole("button");
  await expect(held).toHaveText("Suggest PPSD risk rows");
  await expect(held).toHaveAttribute("aria-disabled", "true");
  await expect(held).toHaveAccessibleDescription("Select the risks you want in section 3 first.");

  await page.setViewportSize({ width: 390, height: 900 });
  const inline = page.locator("[data-ppsd-action][data-placement=inline]");
  await expect(inline).toBeVisible();
  await expect(page.locator("[data-ppsd-action][data-placement=header]")).toBeHidden();
  await expect(inline.getByRole("button")).toHaveAccessibleDescription("Select at least one risk above first.");
});

// A package from a sentence (tests/record_packages_api.py's pkg-000000000001), with section 3 serving the India rows
// and one of them selected: the workspace that "Plan a package from a sentence" opens offers the same action.
const PLANNED = "pkg-000000000001";
const PLANNED_API = `/api/planned-packages/${PLANNED}`;

test("a package planned from a sentence offers the same action, next to No STEP reference yet, and posts its id", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  const asked = await serve(page, {
    "/api/me": { body: await recorded("me-staff.json") },
    [PLANNED_API]: { body: await recorded("planned-package-rural-roads.json") },
    "/api/comparables": { body: await recorded("comparables-planned-works-rfb-ke.json") },
    [`${PLANNED_API}/risks`]: { body: await recorded("risks-ke-nwwda-541055-india-selected.json") },
    [`${PLANNED_API}/risk-selection`]: { body: await recorded("risks-selection-saved.json") },
    "POST /api/drafts": { body: await recorded("drafts-write-ppsd.sse"), delay: 300 },
    [`GET /api${DRAFT}`]: { body: await recorded("drafts-ppsd-draft.json") },
  });
  await page.goto(`/packages/${PLANNED}`);
  await expect(page.locator("section#risks [data-finding]").first()).toBeVisible();

  const header = page.locator("[data-package-header]");
  await expect(header).toContainText("No STEP reference yet");
  const action = header.locator("[data-ppsd-action][data-placement=header]");
  await expect(action.getByRole("button")).toHaveText("Suggest 1 PPSD risk row");
  await expect(action.getByRole("button")).toHaveAttribute("data-button", "primary");
  await expect(page.locator("[data-ppsd-action][data-placement=inline]")).toBeHidden();
  // While the action is live it is the screen's one solid button, so "Show the past range" turns secondary.
  await expect(page.locator("[data-plan-prompt]").getByRole("button", { name: "Show the past range" })).toHaveAttribute("data-button", "secondary");

  await action.getByRole("button").click();
  await expect(page).toHaveURL(new RegExp(`/drafts/new\\?kind=ppsd_rows&package=${PLANNED}$`));
  await expect(page).toHaveURL(DRAFT);
  const sent = asked.find((one) => one.call === "POST /api/drafts")!.body as Record<string, unknown>;
  expect({ kind: sent.kind, package: sent.package }).toEqual({ kind: "ppsd_rows", package: PLANNED });
  // The server reads the criteria from the saved package, and the selection from section 3's saves.
  expect(sent).not.toHaveProperty("criteria");
  expect(JSON.stringify(sent)).not.toContain("cost_estimates");
});

// ── The draft page ───────────────────────────────────────────────────────

test("the Short Form shows exactly the template's three columns, with the counts and passages as footnotes, and no Long Form below Table I", async ({ page }) => {
  await openDraft(page, "drafts-ppsd-draft.json");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Suggested risk rows for the borrower's PPSD");
  const table = page.locator("[data-ppsd-table] table");
  await expect(table.locator("thead th")).toHaveText(SHORT);
  await expect(table.locator("tbody tr")).toHaveCount(2);
  await expect(page.locator("[data-form-control]")).toHaveCount(0);
  await expect(page.locator("[data-form-caption]")).toContainText("I used the Short Form");
  // Strata never wrote an owner: each owner cell holds the plus chip.
  await expect(table.locator("[data-fill-chip=risk_owner]")).toHaveText(["Set the owner", "Set the owner"]);
  await expect(page.locator("[data-progress] [data-numbers]")).toHaveText("0 of 2 risk owners set.");
  // Each footnote's Word text, built once on the server, in the ticket's forms.
  const inWord = page.locator("[data-in-word]");
  await expect(inWord.first()).toHaveText(/^In Word: Seen in \d+ of \d+ comparable completion reports\.$/);
  await expect(inWord).toContainText(["In Word: ICR P130164 ¶54, page 23; ICR Review 10.b."]);
  // The bar says what is left before export, in one sentence, with a link to the first empty owner.
  await expect(holdLine(page)).toHaveText("Before you export them, mark the rows as checked and set two more risk owners.");
  expect(await axe(page)).toEqual([]);
});

test("setting an owner counts it at once, and once checked, export waits for the last owner and the bar says so", async ({ page }) => {
  await openDraft(page, "drafts-ppsd-draft.json", {
    answers: {
      [`PUT /api${DRAFT}/fields`]: { body: await recorded("drafts-ppsd-some-owners.json") },
      [`POST /api${DRAFT}/check`]: { body: await recorded("drafts-ppsd-checked-owners-left.json") },
    },
  });
  await page.getByRole("button", { name: `Set the owner for ${COST}` }).click();
  const editor = page.locator("[data-fill-editor-body=risk_owner]");
  await editor.getByLabel("Risk owner").fill("Implementing agency, procurement unit");
  await editor.getByRole("button", { name: "Set the owner", exact: true }).click();
  await expect(page.locator("[data-progress] [data-numbers]")).toHaveText("1 of 2 risk owners set.");
  await expect(holdLine(page)).toHaveText("Before you export them, mark the rows as checked and set one more risk owner.");

  await bar(page).getByRole("button", { name: "Mark as checked" }).click();
  const exportButton = bar(page).getByRole("button", { name: "Export to Word" });
  await expect(exportButton).toHaveAttribute("aria-disabled", "true");
  await expect(exportButton).toHaveAttribute("data-button", "primary");
  await expect(holdLine(page)).toHaveText("Before you export them, set one more risk owner.");
  // The clause links to the empty owner chip.
  await holdLine(page).getByRole("link").click();
  await expect(page.getByRole("button", { name: `Set the owner for ${PERMITS}` })).toBeFocused();
});

test("above Table I the Long Form toggle shows, and the four columns it adds are for people to fill", async ({ page }) => {
  await openDraft(page, "drafts-ppsd-made-up-long.json");
  await expect(page.locator("[data-form-control]")).toBeVisible();
  const permits = page.locator("[data-ppsd-row=permits_before_award] [data-band]");
  await expect(permits.locator(":scope span.text-caption")).toHaveText(["Risk Owner", ...LONG_ADDED].sort((a, b) =>
    ["Likelihood Rating", "Impact Rating", "Overall Risk Score (A*B)", "Risk Owner", "Procurement Process Stage"].indexOf(a) -
    ["Likelihood Rating", "Impact Rating", "Overall Risk Score (A*B)", "Risk Owner", "Procurement Process Stage"].indexOf(b)));
  // The row nobody rated: every field is empty, so Strata filled none.
  await expect(permits.locator("[data-fill-chip]")).toHaveText(["Set", "Set", "Set", "Set the owner", "Set"]);
  await expect(page.locator("[data-progress] [data-numbers]")).toHaveText("1 of 2 risk owners set. 1 of 2 rows rated.");
  await expect(holdLine(page)).toHaveText(
    "Before you export them, mark the rows as checked, set one more risk owner, and fill in the ratings for one more row.",
  );
  expect(await axe(page)).toEqual([]);
});

test("a warning disagreement holds export until you keep a report, and Keep with Strata's report saves at once", async ({ page }) => {
  let kept = false;
  await page.setViewportSize({ width: 1440, height: 900 });
  await serve(page, {
    "POST /api/disagreements/437378890475ef48/choices": { body: await recorded("disagreement-choice-lean.json") },
  });
  const first = await recorded("drafts-ppsd-made-up-disagreement.json");
  const after = await recorded("drafts-ppsd-made-up-disagreement-kept.json");
  await page.route(`**/api${CARD_DRAFT}`, (route) => route.fulfill({ contentType: "application/json", body: kept ? after : first }));
  await page.route("**/api/disagreements/437378890475ef48/choices", (route) => {
    kept = true;
    return route.fallback();
  });
  await page.goto(CARD_DRAFT);
  const card = page.locator("[data-draft-card='437378890475ef48'] [data-disagreement=warning]");
  await expect(card).toBeVisible();
  await expect(card).toContainText("Choose which report this draft keeps before you export it.");
  await expect(holdLine(page)).toHaveText(
    "Before you export them, mark the rows as checked, set two more risk owners, and choose which report to keep in one disagreement.",
  );
  await holdLine(page).getByRole("link", { name: "choose which report to keep in one disagreement" }).click();
  await expect(page.locator("[data-draft-card='437378890475ef48']")).toBeFocused();

  await card.locator("[data-keep-lean]").click();
  await expect(card.locator("[data-keep-line]")).toContainText(/^You kept .+ on .+\.$/);
  await expect(holdLine(page)).toHaveText("Before you export them, mark the rows as checked and set two more risk owners.");
  // Keeping the other report is still offered, with its reason form.
  await expect(card.locator("[data-keep-other]")).toBeVisible();
});

// ── The Project Paper summary ────────────────────────────────────────────

test("Check a plan ends on Drafts from this check, which counts your team's checked PPSD rows and starts the summary", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  const asked = await serve(page, {
    [`/api${PLAN}`]: { body: await recorded("check-plan-p156634-nwwda-2026-10-09.json") },
    "/api/me": { body: await recorded("me-staff.json") },
    "/api/drafts/project-paper-inputs": { body: await recorded("drafts-pp-inputs.json") },
    "POST /api/drafts": { body: await recorded("drafts-write-pp.sse"), delay: 300 },
    [`GET /api${PAPER}`]: { body: await recorded("drafts-pp-draft.json") },
  });
  await page.goto(PLAN);
  const panel = page.locator("[data-pp-panel]");
  await expect(panel.getByRole("heading", { level: 2 })).toHaveText("Procurement summary for the Project Paper");
  await expect(panel.locator("[data-pp-body]")).toHaveText(
    "I draft it from this check, Northern Water Works Development Agency's track record with its past packages and the two PPSD rows your team checked for this project's packages.",
  );
  const action = panel.getByRole("button", { name: "Draft a Project Paper summary" });
  await expect(action).toHaveAttribute("data-button", "secondary");
  await action.click();
  await expect(page).toHaveURL(/\/drafts\/new\?kind=project_paper&pid=P156634&agency=northern-water-works-development-agency&version=2026-10-09$/);
  await expect(page).toHaveURL(PAPER);
  const sent = asked.find((one) => one.call === "POST /api/drafts")!.body as Record<string, unknown>;
  expect([sent.kind, sent.project_id, sent.agency_id, sent.plan_date]).toEqual(["project_paper", "P156634", "northern-water-works-development-agency", "2026-10-09"]);
});

test("the Project Paper summary for P156634 is a sheet in three parts, cites its counts, and never rates the agency", async ({ page }) => {
  await openDraft(page, "drafts-pp-draft.json", { path: PAPER });
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Procurement summary for the Project Paper");
  const sheet = page.locator("[data-paper-sheet]");
  await expect(sheet.locator("h3")).toHaveText(["The Procurement Plan", "The implementing agency's track record", "Procurement risks in the PPSD"]);
  // Every part's sentences carry a source marker, and every number sits in a cited sentence.
  for (const part of ["plan", "record", "ppsd"]) {
    await expect(sheet.locator(`[data-paper-part=${part}] [data-citation]`).first()).toBeVisible();
  }
  await expect(page.locator("main")).toContainText("I don't rate the agency's procurement risk.");
  // The ICR paragraph a checked PPSD row rests on is named as its marker and the Word footnote name it
  // (values.toml's icr-para-54: paragraph 54, PDF page 23).
  await expect(page.locator("[data-sources]")).toContainText("ICR P130164 paragraph 54, page 23");
  await expect(page.locator("[data-sources]")).toContainText(
    "Source: Implementation Completion and Results Report, P130164, October 10, 2019, paragraph 54, page 23.",
  );
  expect(await axe(page)).toEqual([]);
});

test("a viewer without the World Bank staff role gets no action to suggest PPSD rows", async ({ page }) => {
  await openPackage(page, { me: await recorded("me.json") });
  await expect(page.locator("[data-ppsd-action]")).toHaveCount(0);
});

test("the Drafts tab names each new kind and counts a rows draft's owners set, from the server's counts", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await serve(page, { "/api/drafts": { body: await recorded("drafts-list-ppsd.json") } });
  await page.goto("/drafts");
  const rows = page.locator("[data-draft-row=draft-0003]");
  await expect(rows.getByRole("link").first()).toHaveText(/^Suggested PPSD risk rows for /);
  await expect(rows.locator("[data-numbers]")).toContainText("0 of 2 risk owners set.");
  await expect(page.locator("[data-draft-row=draft-0005]").getByRole("link").first()).toHaveText(
    "Project Paper summary for the Northern Water Works Development Agency plan of Oct 9, 2026",
  );
});
