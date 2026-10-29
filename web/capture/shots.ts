// What the capture command photographs (npm --prefix web run capture). Each shot is a page in
// one state, taken at 1440, 1024 and 390 px unless it names its own widths. Gallery shots
// open the design gallery; app shots open the production build with /api answered from the
// recordings in tests/fixtures/api, so design reviews are repeatable. To review a new screen,
// add its routes and states here.
import { readFileSync } from "node:fs";
import type { Page } from "@playwright/test";
import { galleryCopy } from "../src/gallery/copy";

export const WIDTHS = [1440, 1024, 390];

export type Shot = {
  name: string;
  path: string;
  server?: "gallery" | "app";
  // /api routes and the recorded file (in tests/fixtures/api) or body each one answers with.
  api?: Record<string, { recorded?: string; body?: string; status?: number }>;
  widths?: number[];
  // A real interaction before the photo, such as a hover or a keyboard focus. Shots with an
  // action photograph the window around the element; the others photograph the whole page.
  act?: (page: Page) => Promise<void>;
  // /api paths that never answer, for a page's loading state.
  pending?: string[];
  // Photograph the whole page even after an action, such as the plan check with its fold open.
  full?: boolean;
  // Ticket 47: the deck's data, a recorded file served at /deck/data.json in place of the build's own.
  deckData?: string;
};

const hover = (selector: string) => async (page: Page) => {
  const target = page.locator(selector).first();
  await target.scrollIntoViewIfNeeded();
  await target.hover();
  await page.waitForTimeout(250);
};

// Focus from the keyboard: Tab until the element has focus, so :focus-visible shows.
const focus = (selector: string) => async (page: Page) => {
  const target = page.locator(selector).first();
  await target.scrollIntoViewIfNeeded();
  for (let i = 0; i < 80; i += 1) {
    await page.keyboard.press("Tab");
    if (await target.evaluate((el) => el === document.activeElement || el.contains(document.activeElement))) break;
  }
  await page.waitForTimeout(250);
};

const click = (selector: string) => async (page: Page) => {
  const target = page.locator(selector).first();
  await target.scrollIntoViewIfNeeded();
  await target.click();
  await page.waitForTimeout(250);
};

const type = (selector: string, text: string) => async (page: Page) => {
  await page.locator(selector).first().fill(text);
  await page.waitForTimeout(250);
};

// Held down, as a pointer presses it, so the photo shows the pressed state (ticket 90: a button eases to 0.98).
const press = (selector: string) => async (page: Page) => {
  await hover(selector)(page);
  await page.mouse.down();
  await page.waitForTimeout(250);
};

const WIDE = [1440, 1024];
const NARROW = [390];

// The app's routes, as the 06 design brief lists them, and both not-found pages. All projects, a
// project's page and Check a plan have their own shots below (ticket 10), and so do the package
// workspace (ticket 12) and the Packages tab (ticket 15).
const ROUTES: [string, string][] = [
  ["lessons", "/lessons"],
  ["drafts", "/drafts"],
  ["not-found", "/nowhere"],
  ["not-a-project", "/projects/130164"],
];

// Ticket 30: section 3 of the package workspace, procurement risks and what helped, on the demo package. The
// table with rows is the server's answer with section 1's country set to India, whose comparables reach P130164's
// completion report (tests/record_risks_api.py); the fixture's Kenya comparables reach none. The other states are
// in the gallery (/gallery/risks), from the same answers.
const RISKS_PATH = "/packages/KE-NWWDA-541055-CW-RFB";
const RISKS_API = "/api/packages/KE-NWWDA-541055-CW-RFB";
function riskShot(name: string, risks: Answer | null, rest: Partial<Shot> = {}): Shot {
  // Section 1 answers with the same criteria section 3 was read with, so the page pairs India's comparables with
  // India's risks, as the app does, and Kenya's with Kenya's (ticket 60).
  const india = Boolean(risks?.recorded?.includes("-india"));
  const answers: Record<string, Answer> = {
    ...app(name, RISKS_PATH).api,
    [RISKS_API]: { recorded: "package-ke-nwwda-541055.json" },
    [`${RISKS_API}/comparables`]: { recorded: india ? "comparables-ke-nwwda-541055-india.json" : "comparables-ke-nwwda-541055.json" },
    [`${RISKS_API}/risk-selection`]: { recorded: "risks-selection-saved.json" },
    "/api/evidence": { recorded: "evidence-icr-p130164-54.json" },
    "/api/evidence/opened": { body: '{"opened":[],"recorded":true}' },
    ...rest.api,
  };
  if (risks) answers[`${RISKS_API}/risks`] = risks;
  return app(`risks--${name}`, RISKS_PATH, {}, { full: true, ...rest, api: answers, pending: risks ? rest.pending : [`${RISKS_API}/risks`] });
}
const INDIA: Answer = { recorded: "risks-ke-nwwda-541055-india.json" };
const toRisks = async (page: Page) => {
  await page.locator("section#risks").scrollIntoViewIfNeeded();
  await page.waitForTimeout(250);
};
const openPill = click("section#risks [data-risk-view]:visible [data-source-pill]");
const RISK_SHOTS: Shot[] = [
  riskShot("table", INDIA, { act: toRisks }),
  riskShot("selected", { recorded: "risks-ke-nwwda-541055-india-selected.json" }, { act: toRisks }),
  riskShot("no-reports", { recorded: "risks-ke-nwwda-541055.json" }, { act: toRisks }),
  riskShot("loading", null, { act: toRisks }),
  riskShot("error", { status: 503, body: '{"code":"data_service","trace_id":"0af7651916cd43dd8448eb211c80319c"}' }, { act: toRisks }),
  riskShot("drawer", INDIA, { act: openPill }),
  riskShot("count-reports", INDIA, { act: click("section#risks [data-risk-view]:visible [data-count] button") }),
  riskShot("hover-pill", INDIA, { full: false, widths: WIDE, act: hover("section#risks [data-risk-view]:visible [data-source-pill]") }),
  riskShot("focus-pill", INDIA, { full: false, act: focus("section#risks [data-risk-view]:visible [data-source-pill]") }),
  riskShot("focus-checkbox", INDIA, { full: false, act: focus("section#risks [data-risk-view]:visible input[type=checkbox]") }),
  riskShot("hover-count", INDIA, { full: false, widths: WIDE, act: hover("section#risks [data-risk-view]:visible [data-count] button") }),
  riskShot("320", INDIA, { widths: [320], act: toRisks }),
  // Ticket 105: a drawer's list lands on the row you came back to, marked with tint: a risk's reports, after one of
  // them was opened and "Back to the report" pressed.
  {
    ...riskShot("landed-row", INDIA, {
      full: false,
      widths: [1440, 390],
      act: async (page: Page) => {
        await click("section#risks [data-risk-view]:visible [data-count] button")(page);
        await click("[data-evidence-drawer] [data-report-entry]")(page);
        await click("[data-evidence-drawer] >> text=Back to the report")(page);
      },
    }),
    name: "evidence--landed-row",
  },
];

// Ticket 27: section 2 of the package workspace, the planned date for each STEP step. On the fixture every step
// abstains, so the dated states are the server's answers on the hand-made set (tests/record_steps_api.py) for its
// works package KE-HAND-900000-CW-RFB, and for a package from a sentence on the same set. The other states are in the
// gallery (/gallery/steps), from the same answers.
const STEPS_PATH = "/packages/KE-HAND-900000-CW-RFB";
const STEPS_API = "/api/packages/KE-HAND-900000-CW-RFB";
function stepShot(name: string, steps: Answer | null, rest: Partial<Shot> = {}): Shot {
  const answers: Record<string, Answer> = {
    ...app(name, STEPS_PATH).api,
    [STEPS_API]: { recorded: "package-ke-hand-900000.json" },
    [`${STEPS_API}/comparables`]: { recorded: "comparables-ke-hand-900000.json" },
    [`${STEPS_API}/risks`]: { recorded: "risks-ke-hand-900000.json" },
    [`${STEPS_API}/plan-dates`]: { recorded: "steps-plan-dates-saved.json" },
    "/api/evidence/opened": { body: '{"opened":[],"recorded":true}' },
    ...rest.api,
  };
  if (steps) answers[`${STEPS_API}/steps`] = steps;
  // Section 5 (ticket 31) has no recorded answer for the hand-made set, so its summary stays loading in these shots.
  const pending = [`${STEPS_API}/criteria`, ...(steps ? (rest.pending ?? []) : [`${STEPS_API}/steps`])];
  return app(`steps--${name}`, STEPS_PATH, {}, { full: true, ...rest, api: answers, pending });
}
const DATED_STEPS: Answer = { recorded: "steps-ke-hand-900000.json" };
const SECTION_2 = "section#planned-dates";
const toSteps = async (page: Page) => {
  await page.locator(SECTION_2).scrollIntoViewIfNeeded();
  await page.waitForTimeout(250);
};
const openSteps = async (page: Page) => {
  await page.locator(`${SECTION_2} [data-section-toggle]`).click();
  await toSteps(page);
};
const inOrder = (...acts: ((page: Page) => Promise<void>)[]) => async (page: Page) => {
  for (const act of acts) await act(page);
};
const STEP_SHOTS: Shot[] = [
  // Ticket 115: the tracker at the top of the workspace, five steps done and the completion late, and the keyboard's
  // tab stop on the late step. The fixture's showcase, with its late steps, is steps--fixture below.
  stepShot("tracker-done", { recorded: "steps-ke-hand-900000-done.json" }, { full: false, widths: [1440], act: focus("[data-step-tracker] li[tabindex='0']") }),
  stepShot("collapsed", DATED_STEPS, { act: toSteps }),
  stepShot("cautious", DATED_STEPS, { act: openSteps }),
  stepShot("middle", DATED_STEPS, { act: inOrder(openSteps, click(`${SECTION_2} [data-segment=middle]`)) }),
  // The demo package on the fixture, where every step abstains.
  app("steps--fixture", "/packages/KE-NWWDA-541055-CW-RFB", {}, {
    full: true,
    act: openSteps,
    api: {
      ...app("steps--fixture", "/packages/KE-NWWDA-541055-CW-RFB").api,
      "/api/packages/KE-NWWDA-541055-CW-RFB": { recorded: "package-ke-nwwda-541055.json" },
      "/api/packages/KE-NWWDA-541055-CW-RFB/comparables": { recorded: "comparables-ke-nwwda-541055.json" },
      "/api/packages/KE-NWWDA-541055-CW-RFB/risks": { recorded: "risks-ke-nwwda-541055.json" },
      "/api/packages/KE-NWWDA-541055-CW-RFB/steps": { recorded: "steps-ke-nwwda-541055.json" },
    },
  }),
  stepShot("abstain", { recorded: "steps-ke-hand-900000-few.json" }, { act: openSteps }),
  stepShot("loading", null, { act: toSteps }),
  stepShot("error", { status: 503, body: '{"code":"data_service","trace_id":"0af7651916cd43dd8448eb211c80319c"}' }, { act: toSteps }),
  stepShot("count-drawer", DATED_STEPS, { widths: WIDE, act: inOrder(openSteps, click(`${SECTION_2} [data-step-row=contract_signed] td:last-child button`)) }),
  stepShot("count-sheet", DATED_STEPS, { widths: NARROW, act: inOrder(openSteps, click(`${SECTION_2} [data-step-item=contract_signed] dd:last-child button`)) }),
  stepShot("longest-drawer", DATED_STEPS, { widths: WIDE, act: click(`${SECTION_2} [data-section-summary] button`) }),
  stepShot("hover-disclosure", DATED_STEPS, { full: false, widths: WIDE, act: hover(`${SECTION_2} [data-section-toggle]`) }),
  stepShot("focus-disclosure", DATED_STEPS, { full: false, act: focus(`${SECTION_2} [data-section-toggle]`) }),
  stepShot("focus-choice", DATED_STEPS, { full: false, act: inOrder(openSteps, focus(`${SECTION_2} input[type=radio]:checked`)) }),
  stepShot("hover-choice", DATED_STEPS, { full: false, widths: WIDE, act: inOrder(openSteps, hover(`${SECTION_2} [data-segment=middle]`)) }),
  // A step label's full STEP name on hover, on keyboard focus with no Enter, and pinned open by Enter (criterion 4).
  stepShot("term-open", DATED_STEPS, { full: false, widths: WIDE, act: inOrder(openSteps, hover(`${SECTION_2} [data-step-table] [data-term]`)) }),
  stepShot("term-focus", DATED_STEPS, { full: false, widths: WIDE, act: inOrder(openSteps, focus(`${SECTION_2} [data-step-table] [data-term]`)) }),
  stepShot("term-pinned", DATED_STEPS, { full: false, widths: WIDE, act: inOrder(openSteps, focus(`${SECTION_2} [data-step-table] [data-term]`), async (page) => page.keyboard.press("Enter")) }),
  stepShot("focus-date", DATED_STEPS, { full: false, widths: WIDE, act: inOrder(openSteps, focus(`${SECTION_2} [data-step-table] [data-num-lines]`)) }),
  stepShot("focus-count", DATED_STEPS, { full: false, widths: WIDE, act: inOrder(openSteps, focus(`${SECTION_2} [data-step-table] td:last-child button`)) }),
  stepShot("320", DATED_STEPS, { widths: [320], act: openSteps }),
  app("steps--sentence-undated", "/packages/pkg-000000000001", {}, {
    full: true,
    act: openSteps,
    api: {
      ...app("steps--sentence-undated", "/packages/pkg-000000000001").api,
      "/api/planned-packages/pkg-000000000001": { recorded: "planned-package-hand-made.json" },
      "/api/comparables": { recorded: "comparables-planned-hand-made.json" },
      "/api/planned-packages/pkg-000000000001/risks": { recorded: "risks-planned-hand-made.json" },
      "/api/planned-packages/pkg-000000000001/steps": { recorded: "steps-planned-hand-made.json" },
      "/api/planned-packages/pkg-000000000001/step-start": { recorded: "steps-planned-hand-made-dated.json" },
    },
    pending: ["/api/planned-packages/pkg-000000000001/criteria"],
  }),
  app("steps--sentence-dated", "/packages/pkg-000000000001", {}, {
    full: true,
    // 360 and 320 px too: the narrow list's longest values are this package's days captions.
    widths: [1440, 1024, 390, 360, 320],
    act: inOrder(openSteps, type(`${SECTION_2} input[type=date]`, "2021-03-01"), click(`${SECTION_2} [data-commit-start]`)),
    api: {
      ...app("steps--sentence-dated", "/packages/pkg-000000000001").api,
      "/api/planned-packages/pkg-000000000001": { recorded: "planned-package-hand-made.json" },
      "/api/comparables": { recorded: "comparables-planned-hand-made.json" },
      "/api/planned-packages/pkg-000000000001/risks": { recorded: "risks-planned-hand-made.json" },
      "/api/planned-packages/pkg-000000000001/steps": { recorded: "steps-planned-hand-made.json" },
      "/api/planned-packages/pkg-000000000001/step-start": { recorded: "steps-planned-hand-made-dated.json" },
    },
    pending: ["/api/planned-packages/pkg-000000000001/criteria"],
  }),
];

const SIGNED_OUT = '{"email":null,"name":null,"signed_in":false,"has_token":false}';
type Answer = { recorded?: string; body?: string; status?: number };

// An app shot: the page, with /api/me and /api/freshness answered from the recordings unless
// the shot says otherwise. A page under /lessons also gets who is viewing it and the Lessons page's one read, so the
// shell's shots there show the page and never a load error (ticket 102; ticket 60's routed note).
function app(name: string, path: string, answers: { me?: Answer; freshness?: Answer } = {}, rest: Partial<Shot> = {}): Shot {
  const lessons: Shot["api"] = path.startsWith("/lessons")
    ? { "/api/lessons/me": { recorded: "lessons-me-viewer.json" }, "/api/lessons/page": { recorded: "lessons-page.json" } }
    : {};
  return {
    name,
    path,
    server: "app",
    api: { "/api/me": answers.me ?? { recorded: "me.json" }, "/api/freshness": answers.freshness ?? { recorded: "freshness.json" }, ...lessons },
    ...rest,
  };
}

// Ticket 41: Home, from the server's answers on tests/home_story.py's story (tests/record_home_api.py): Ana's Home
// with her seeded examples, the first run, a quiet window, both drafts checked, the strip removed, and the agency
// preview. Under the function-first rule each is taken at 1440 px; the other widths wait for the design pass.
// Ticket 98 moves Home onto the workspace layout and adds the officer's and the public's Home and an answer asked from
// Home (home--answered, with the answer stream below).
const homeApi = (home: string, me = "me-home.json"): Record<string, Answer> => ({
  "/api/me": { recorded: me },
  "/api/me?view=piu": { recorded: "me-preview-piu.json" },
  "/api/me?view=public": { recorded: "me-preview-public.json" },
  "/api/freshness": { recorded: "freshness.json" },
  "/api/home": { recorded: home },
  "/api/home?view=piu": { recorded: "home-preview-piu.json" },
  "/api/home?view=public": { recorded: "home-preview-public.json" },
});
const HOME_SHOTS: Shot[] = [
  app("home--populated", "/", {}, { widths: [1440], full: true, api: homeApi("home.json") }),
  app("home--first-run", "/", {}, { widths: [1440], full: true, api: homeApi("home-first-run.json") }),
  app("home--quiet-week", "/", {}, { widths: [1440], full: true, api: homeApi("home-quiet.json") }),
  app("home--drafts-checked", "/", {}, { widths: [1440], full: true, api: homeApi("home-drafts-checked.json") }),
  app("home--officer", "/?view=piu", {}, { widths: [1440], full: true, api: homeApi("home.json") }),
  app("home--public", "/?view=public", {}, { widths: [1440], full: true, api: homeApi("home.json") }),
  app("home--loading", "/", {}, { widths: [1440], api: homeApi("home.json"), pending: ["/api/home"] }),
];

// Ticket 40: the view switch and the as-of date, with /api answered from the server's own answers
// (tests/record_views_api.py). Under the function-first rule each is taken at 1440 px only; the other widths wait for
// the design pass.
const VIEW_PLAN = "/projects/P156634/procurement/northern-water-works-development-agency/2026-10-09";
const viewApi = (rest: Record<string, Answer>): Record<string, Answer> => ({
  "/api/me": { recorded: "me.json" },
  "/api/me?view=piu": { recorded: "me-preview-piu.json" },
  "/api/me?view=public": { recorded: "me-preview-public.json" },
  "/api/me?asof=2016-08-26": { recorded: "me-asof.json" },
  "/api/freshness": { recorded: "freshness.json" },
  ...rest,
});
const VIEW_SHOTS: Shot[] = [
  { name: "views--popover-public-preview", path: "/gallery/navigation?pill=public&view=open", widths: [1440] },
  app("views--agency-preview-projects", "/projects?view=piu", {}, { widths: [1440], full: true,
    api: viewApi({ "/api/projects": { recorded: "projects.json" }, "/api/agency/projects": { recorded: "agency-projects-two.json" } }) }),
  app("views--public-preview-home", "/?view=public", {}, { widths: [1440],
    api: viewApi({ "/api/home?view=public": { recorded: "home-preview-public.json" } }) }),
  app("views--public-preview-packages-hidden", "/packages?view=public", {}, { widths: [1440], api: viewApi({}) }),
  app("views--public-preview-check-plan", `${VIEW_PLAN}?view=public`, {}, { widths: [1440], full: true,
    api: viewApi({ [`/api${VIEW_PLAN}`]: { recorded: "check-plan-p156634-nwwda-2026-10-09-public.json" },
      "/api/projects/P156634": { recorded: "project-p156634.json" } }) }),
  app("views--asof-timeline-p130164", "/projects/P130164/timeline?asof=2016-08-26", {}, { widths: [1440], full: true,
    api: viewApi({ "/api/projects/P130164": { recorded: "project-p130164-2016-08-26.json" },
      "/api/projects/P130164/follow": { recorded: "follow-off.json" },
      "/api/projects/P130164/timeline": { recorded: "timeline-p130164-2016-08-26.json" } }) }),
];

// Ticket 38: an implementing agency officer's Check my plan, an upload's check, a draft of planned dates, and what World
// Bank staff and another team get, with /api answered from the server's own answers (tests/record_uploads_api.py). Under
// the function-first rule each is taken at 1440 px only; the other widths wait for the design pass.
const OFFICER: Answer = { recorded: "me-officer.json" };
const UPLOAD_SHOTS: Shot[] = [
  app("uploads--check-my-plan", "/packages/check", { me: OFFICER }, { widths: [1440],
    api: { "/api/me": OFFICER, "/api/freshness": { recorded: "freshness.json" }, "/api/uploads/form": { recorded: "uploads-form-officer.json" } } }),
  app("uploads--check-my-plan-staff", "/packages/check", {}, { widths: [1440],
    api: { "/api/me": { recorded: "me.json" }, "/api/freshness": { recorded: "freshness.json" }, "/api/uploads/form": { recorded: "uploads-form-staff.json" } } }),
  app("uploads--check", "/packages/uploads/upl-000000000001", { me: OFFICER }, { widths: [1440], full: true,
    api: { "/api/me": OFFICER, "/api/freshness": { recorded: "freshness.json" },
      "/api/uploads/upl-000000000001": { recorded: "upload-check-nwwda.json" } } }),
  app("uploads--not-found", "/packages/uploads/upl-000000000001", {}, { widths: [1440],
    api: { "/api/me": { recorded: "me.json" }, "/api/freshness": { recorded: "freshness.json" },
      "/api/uploads/upl-000000000001": { status: 404, recorded: "upload-not-found.json" } } }),
  app("uploads--step-rows-draft", "/drafts/draft-0002", { me: OFFICER }, { widths: [1440], full: true,
    api: { "/api/me": OFFICER, "/api/freshness": { recorded: "freshness.json" }, "/api/drafts/draft-0002": { recorded: "drafts-step-rows-draft.json" },
      "/api/evidence/opened": { body: '{"recorded":true}' } } }),
];

// A Data tab shot (ticket 16): the page with the Data readiness answer it names, recorded from the
// server on the fixture, and the registry's datasets.
function data(name: string, path: string, readiness: Answer = { recorded: "data-readiness.json" }, rest: Partial<Shot> = {}, sources: Answer = { recorded: "data-sources.json" }): Shot {
  const shot = app(`data--${name}`, path, {}, rest);
  return { ...shot, api: { ...shot.api, "/api/data/readiness": readiness, "/api/data/sources": sources } };
}

const FILTERED = "/data?sources=awards,notices&from=find_comparables";
// Ticket 104: the hardest documents, the plan pages the parser couldn't read and the fixes are closed rows; a shot of
// what one holds presses its Show button first, as a reader does.
const openDataRow = (section: "shelf" | "failures" | "fixes") => async (page: Page) => {
  await page.locator(`[data-readiness] [data-section=${section}] [data-section-toggle][aria-expanded=false]`).click();
  await page.waitForTimeout(250);
};
const openDataRows = inOrder(openDataRow("shelf"), openDataRow("fixes"));

// Ticket 10's screens. A state the fixture cannot reach, such as a partial check, is the recorded
// plan check with one value changed, so it still shows real rows.
const PLAN = "/projects/P156634/procurement/northern-water-works-development-agency/2026-10-09";
const PLAN_API = `/api${PLAN}`;
const RECORDED = new URL("../../tests/fixtures/api/", import.meta.url);
const PLAN_FILE = "check-plan-p156634-nwwda-2026-10-09.json";

function derived(name: string, edit: (body: Record<string, any>) => void): string {
  const body = JSON.parse(readFileSync(new URL(name, RECORDED), "utf8"));
  edit(body);
  return JSON.stringify(body);
}

const partial = derived(PLAN_FILE, (body) => {
  const row = body.rows.find((r: { activity_reference_no: string }) => r.activity_reference_no === "KE-NWWDA-541062-CW-RFQ");
  row.planned_completion_on = null;
  row.marks.push({ mark: "data_note", reasons: [{ code: "no_planned_date", mark: "data_note", step: "Contract Completion", evidence_ids: [row.evidence_id] }] });
  Object.assign(body.counts, { checked: 8, not_fully_checked: 1, data_note: 4 });
});
// With no closing date, check_plan runs no closing-date check: the Needs a look reason names no
// closing date, the activity pending near closing loses its Watch, and the fold grows to four.
const noClosingDate = derived(PLAN_FILE, (body) => {
  body.project.closing_date = null;
  body.project.days_to_close = null;
  body.checks_run = ["own_dates", "estimate"];
  for (const row of body.rows) {
    for (const mark of row.marks) for (const reason of mark.reasons) Object.assign(reason, { closing_date: null, days_to_close: null });
    row.marks = row.marks.filter((mark: { reasons: { code: string }[] }) => !mark.reasons.every((reason) => reason.code.startsWith("pending_")));
  }
  Object.assign(body.counts, { watch: 1, marked: 5, unmarked: 4 });
});
const noActivities = derived(PLAN_FILE, (body) => {
  body.rows = [];
  body.counts = null;
  body.abstention = { reason: "no_activities", plan_date: "2026-10-09" };
});
// A shot of one of ticket 10's pages, with its one /api read answered. The read's path is the
// page's own, under /api, unless the shot names it, as /projects/:pid/procurement must.
const planShot = (name: string, answer: Answer, rest: Partial<Shot> = {}, path = PLAN, read = `/api${path.split("#")[0]}`): Shot =>
  app(name, path, {}, { ...rest, api: { ...app(name, path).api, [read]: answer } });
const plan: Answer = { recorded: PLAN_FILE };
const SERVICE_DOWN = '{"code":"data_service","trace_id":"0af7651916cd43dd8448eb211c80319c"}';

const PLAN_SHOTS: Shot[] = [
  planShot("check-plan", plan),
  planShot("check-plan--loading", plan, { pending: [PLAN_API] }),
  planShot("check-plan--open", plan, { act: click("[data-fold] button:visible") }),
  planShot("check-plan--open-page", plan, { full: true, act: click("[data-fold] button:visible") }),
  planShot("check-plan--partial", { body: partial }),
  planShot("check-plan--no-closing-date", { body: noClosingDate }),
  planShot("check-plan--no-activities", { body: noActivities }),
  planShot("check-plan--agency-no-plan", { recorded: "check-plan-p156634-wajir-no-plan.json" }, {}, "/projects/P156634/procurement/wajir-water-and-sewerage-company"),
  planShot(
    "check-plan--version-not-found",
    { recorded: "check-plan-p156634-nwwda-2026-10-10-not-found.json" },
    {},
    "/projects/P156634/procurement/northern-water-works-development-agency/2026-10-10",
  ),
  planShot("check-plan--error", { status: 503, body: SERVICE_DOWN }),
  planShot("check-plan--permission", { status: 403, body: '{"code":"permission"}' }),
  planShot("check-plan--hover-show", plan, { widths: [1440, 390], act: hover("[data-fold] button:visible") }),
  planShot("check-plan--focus-show", plan, { widths: [1440, 390], act: focus("[data-fold] button:visible") }),
  planShot("check-plan--num-days-late", plan, { widths: [1440, 390], act: focus(":is([id='KE-NWWDA-229129-CW-RFB'], li:has([data-activity='KE-NWWDA-229129-CW-RFB'])) button[data-num]:visible") }),
  planShot("check-plan--definition", plan, { widths: [1440], act: click("[data-view=table] thead [data-term]") }),
  planShot("check-plan--definition-cards", plan, { widths: [390], act: click("[data-plan-check] [data-term]:visible") }),
  planShot("check-plan--focus-breadcrumb", plan, { widths: [1440, 390], act: focus("[data-breadcrumb] a:visible") }),
  planShot("check-plan--deep-link", plan, {}, `${PLAN}#KE-NWWDA-207796-CS-INDV`),
  planShot("check-plan--320", plan, { widths: [320] }),
  // Ticket 100: a row's reference opens its records in the drawer, and a count word marks the rows it counts.
  planShot("check-plan--row-records", plan, { widths: [1440], full: false, act: click("[data-view=table] [data-row-ref='KE-NWWDA-229129-CW-RFB']") }),
  planShot("check-plan--counted", plan, { widths: [1440], act: click("[data-finding] button[data-num-click]") }),
];

// Ticket 21's project hub, as the 21 brief's section 15 lists it: the project frame, Summary, Procurement,
// Check a plan's change list and baseline panel, Documents, the source view and All projects. Each state
// the fixture holds is the server's own answer; a state it cannot reach, such as a project with no ratings
// or a long version list, is a recorded answer with one value changed, so it still shows real rows.
const HUB_API: Shot["api"] = {
  "/api/projects/P130164": { recorded: "project-p130164.json" },
  "/api/projects/P130164/summary": { recorded: "summary-p130164.json" },
  "/api/projects/P130164/documents": { recorded: "documents-p130164.json" },
  "/api/projects/P156634": { recorded: "project-p156634.json" },
  "/api/projects/P156634/summary": { recorded: "summary-p156634.json" },
  "/api/projects/P156634/packages": { recorded: "packages-p156634.json" },
  "/api/projects/P156634/packages?page=2": { recorded: "packages-p156634-page-2.json" },
  "/api/projects/P156634/packages?q=boreholes": { recorded: "packages-p156634-boreholes.json" },
  "/api/projects/P156634/packages?q=atlantis": { recorded: "packages-p156634-no-match.json" },
  [`${PLAN_API}/changes`]: { recorded: "changes-nwwda-2026-10-09.json" },
  "/api/projects/P156634/procurement/northern-water-works-development-agency/2020-12-07/changes": { recorded: "changes-nwwda-2020-12-07.json" },
  "/api/projects/P156634/procurement/ministry-of-water-and-irrigation/2020-04-30": { recorded: "check-plan-p156634-ministry-2020-04-30.json" },
  "/api/projects/P156634/procurement/ministry-of-water-and-irrigation/2020-04-30/changes": { recorded: "changes-ministry-2020-04-30.json" },
  "/api/projects/P156634/procurement/northern-water-works-development-agency/2025-07-21": { recorded: "check-plan-p156634-nwwda-2025-07-21-baseline.json" },
  "/api/projects/P156634/procurement/northern-water-works-development-agency/2025-07-21/changes": { status: 404, body: '{"code":"unknown_plan"}' },
  "/api/projects/P130164/documents/icr-2019-10-10?page=23&para=54": { recorded: "source-icr-p130164-23-54.json" },
  "/api/projects/P130164/documents/icr-2019-10-10?page=23": { recorded: "source-icr-p130164-23.json" },
  "/api/projects/P130164/documents/icr-2019-10-10?page=22&para=54": { recorded: "source-icr-p130164-moved.json" },
  "/api/projects/P130164/documents/icr-2019-10-10?page=23&para=999": { recorded: "source-icr-p130164-no-para.json" },
  "/api/projects/P130164/documents/icr-2019-10-10?page=80": { recorded: "source-icr-p130164-page-range.json" },
  "/api/projects/P130164/documents/icr-2019-10-10?page=66": { recorded: "source-icr-p130164-page-range.json" },
  "/api/projects/P130164/documents/icr-2019-10-10?page=5": { recorded: "source-icr-p130164-page-unread.json" },
  "/api/projects/P130164/documents/icr-2019-10-10?page=49": { recorded: "source-icr-p130164-page-empty.json" },
  "/api/projects/P130164/documents/icr-2019-10-10?page=2": { recorded: "source-icr-p130164-front-matter.json" },
  "/api/projects/P130164/documents/icr-2019-10-10?page=23&asof=2019-10-01": { recorded: "source-icr-p130164-not-public.json" },
  "/api/projects/P130164/documents/icr-review-2023-05-04?page=1": { recorded: "source-icr-review-p130164-reissue.json" },
  "/api/projects/P130164/documents/isr": { recorded: "source-p130164-ambiguous.json" },
  "/api/projects/P130164/documents/not-a-document": { recorded: "source-p130164-not-found.json" },
  "/api/projects/P130164/documents/30152361": { recorded: "source-p130164-doc-unread.json" },
  "/api/projects/P130164/documents/pad-2013-10-01?page=65": { recorded: "source-pad-p130164-65.json" },
  "/api/projects/P161305/documents/procurement-plan-kenya-national-highways-authority-2026-09-24?page=3": { recorded: "source-plan-p161305-3.json" },
  "/api/evidence": { recorded: "evidence-icr-p130164-54.json" },
  "/api/evidence/opened": { body: '{"opened":[],"recorded":true}' },
};
const hubShot = (name: string, path: string, rest: Partial<Shot> = {}, answers: Shot["api"] = {}): Shot =>
  app(name, path, {}, { ...rest, api: { ...app(name, path).api, ...HUB_API, [PLAN_API]: { recorded: PLAN_FILE }, ...answers } });
const SOURCE = "/projects/P130164/documents/icr-2019-10-10";
const BASELINE_API = `${PLAN_API.replace(/\/2026-10-09$/, "")}/baseline`;
const JULY_2025 = PLAN.replace(/2026-10-09$/, "2025-07-21");
const JULY_2025_API = `/api${JULY_2025}`;
// A baseline write: the plan check answers as it reads after the write, then the button is clicked, so the
// shot shows the panel's message beside the reasons the new baseline gives.
const thenClick = (path: string, after: string, selector: string) => async (page: Page) => {
  const body = readFileSync(new URL(after, RECORDED), "utf8");
  await page.route(`**${path}`, (route) => route.fulfill({ status: 200, contentType: "application/json", body }));
  await click(selector)(page);
};
const summaryWithout = (edit: (body: Record<string, any>) => void) => ({ body: derived("summary-p130164.json", edit) });
const longVersions = derived("project-p156634-baseline.json", (body) => {
  const nwwda = body.agencies[0];
  for (const [index, date] of ["2019-06-14", "2019-01-10"].entries()) {
    nwwda.versions.push({ ...nwwda.versions[4], document_id: `older-${index}`, plan_date: date, disclosed_on: date, is_latest: false, is_baseline: false, shown: false });
  }
  Object.assign(nwwda, { version_count: 7, shown_count: 5 });
});

// Ticket 22: the activity page's contract trail and a project's Connections tab, in every state the 22 brief's
// section 14 lists, with /api answered from the server's own answers on the fixture (tests/record_api.py).
const KENYA_ACTIVITY = "/projects/P156634/packages/KE-NWWDA-229129-CW-RFB";
const SHOWCASE_ACTIVITY = "/projects/P130164/packages/IN-RRSMP-7431-CW-RFB";
const TRAIL_ICR_54 = "strata.gold.passage:31525018/v1/54";
const TRAIL_API: Shot["api"] = {
  "/api/projects/P130164": { recorded: "project-p130164.json" },
  "/api/projects/P156634": { recorded: "project-p156634.json" },
  "/api/projects/P127203": { recorded: "project-p130164.json" },
  [`/api${KENYA_ACTIVITY}`]: { recorded: "activity-ke-nwwda-229129.json" },
  [`/api${KENYA_ACTIVITY}?asof=2022-01-02`]: { recorded: "activity-ke-nwwda-229129-before-signing.json" },
  [`/api${SHOWCASE_ACTIVITY}`]: { recorded: "activity-in-rrsmp-7431.json" },
  "/api/projects/P156634/packages/KE-MAWASCO-501974-CS-INDV": { recorded: "activity-ke-mawasco-501974-indv.json" },
  "/api/projects/P156634/packages/KE-NWWDA-000000-CW-RFB": { status: 404, recorded: "activity-unknown.json" },
  "/api/projects/P156634/packages/KE-KIMAWASCO-372408-GO-RFQ": { recorded: "activity-ke-kimawasco-372408.json" },
  "/api/projects/P156634/packages/KE-NWWDA-503455-CW-RFQ": { recorded: "activity-ke-nwwda-503455.json" },
  "/api/projects/P156634/packages/KE-WASREB-235524-CS-QCBS": { recorded: "activity-ke-wasreb-235524.json" },
  "/api/projects/P156634/packages/KE-CWSB-102977-CS-QCBS": { recorded: "activity-ke-cwsb-102977.json" },
  "/api/projects/P130164/connections?asof=2017-06-14": { recorded: "connections-p130164-2017-06-14.json" },
  "/api/projects/P130164/connections": { recorded: "connections-p130164.json" },
  "/api/projects/P156634/connections": { recorded: "connections-p156634.json" },
  "/api/projects/P127203/connections": { recorded: "connections-p127203.json" },
  "/api/evidence": { recorded: "evidence-icr-p130164-54.json" },
  [`/api/evidence?id=${TRAIL_ICR_54}&step_ref=IN-RRSMP-7431-CW-RFB`]: { recorded: "evidence-icr-p130164-54-why.json" },
  "/api/evidence?id=strata.gold.notice:OP00164589": { recorded: "evidence-award-notice-op00164589.json" },
  "/api/evidence/opened": { body: '{"opened":[],"recorded":true}' },
};
const trailShot = (name: string, path: string, rest: Partial<Shot> = {}, answers: Shot["api"] = {}): Shot =>
  app(name, path, {}, { ...rest, api: { ...app(name, path).api, ...TRAIL_API, ...answers } });
const TRAIL_SHOTS: Shot[] = [
  trailShot("activity--loading", KENYA_ACTIVITY, { pending: [`/api${KENYA_ACTIVITY}`] }),
  trailShot("activity--full-trail", SHOWCASE_ACTIVITY),
  trailShot("activity--kenya", KENYA_ACTIVITY),
  trailShot("activity--individual-consultant", "/projects/P156634/packages/KE-MAWASCO-501974-CS-INDV"),
  trailShot("activity--before-signing", `${KENYA_ACTIVITY}?asof=2022-01-02`),
  trailShot("activity--public", `${KENYA_ACTIVITY}?view=public`),
  trailShot("activity--not-found", "/projects/P156634/packages/KE-NWWDA-000000-CW-RFB"),
  trailShot("activity--error", KENYA_ACTIVITY, {}, { [`/api${KENYA_ACTIVITY}`]: { status: 503, body: SERVICE_DOWN } }),
  trailShot("activity--permission", KENYA_ACTIVITY, {}, { [`/api${KENYA_ACTIVITY}`]: { status: 403, body: '{"code":"permission"}' } }),
  trailShot("activity--drawer-why", `${SHOWCASE_ACTIVITY}?evidence=${TRAIL_ICR_54}`, { full: false, act: async (page) => {
    await page.locator("[data-why]").waitFor();
  } }),
  trailShot("activity--drawer-why-score", `${SHOWCASE_ACTIVITY}?evidence=${TRAIL_ICR_54}`, { full: false, act: click("[data-why] button[aria-expanded]") }),
  trailShot("activity--drawer-award-notice", `${KENYA_ACTIVITY}?evidence=strata.gold.notice:OP00164589`, { full: false, act: async (page) => {
    await page.locator("[data-record]").first().waitFor();
  } }),
  trailShot("activity--focus-pill", KENYA_ACTIVITY, { widths: [1440, 390], act: focus("[data-stage=bids] [data-citation]") }),
  trailShot("activity--focus-crumb", KENYA_ACTIVITY, { widths: [1440, 390], act: focus("[data-breadcrumb] a:visible") }),
  trailShot("activity--320", KENYA_ACTIVITY, { widths: [320] }),
  // Round 2: two award notices and two contracts in one card each; the missing notice of a Limited market approach;
  // a consultant award notice with scores left out; one with a rejected firm whose price is blank; the showcase's
  // ICR group opened; and the plan row in the drawer, where no field is highlighted.
  trailShot("activity--several-notices", "/projects/P156634/packages/KE-KIMAWASCO-372408-GO-RFQ"),
  trailShot("activity--approach-no-notice", "/projects/P156634/packages/KE-NWWDA-503455-CW-RFQ"),
  trailShot("activity--proposals-no-scores", "/projects/P156634/packages/KE-WASREB-235524-CS-QCBS"),
  trailShot("activity--rejected-no-price", "/projects/P156634/packages/KE-CWSB-102977-CS-QCBS"),
  trailShot("activity--report-opened", SHOWCASE_ACTIVITY, { widths: [1440, 390], act: click("[data-report]:last-child button[aria-expanded]") }),
  trailShot("connections--loading", "/projects/P130164/connections", { pending: ["/api/projects/P130164/connections"] }),
  trailShot("connections--populated", "/projects/P130164/connections"),
  trailShot("connections--over-the-cap", "/projects/P156634/connections"),
  trailShot("connections--no-links", "/projects/P127203/connections"),
  trailShot("connections--empty", "/projects/P130164/connections", {}, {
    "/api/projects/P130164/connections": { body: derived("connections-p130164.json", (body) => Object.assign(body, { packages: [], documents: [], edges: [], more: [] })) },
  }),
  trailShot("connections--error", "/projects/P130164/connections", {}, { "/api/projects/P130164/connections": { status: 503, body: SERVICE_DOWN } }),
  trailShot("connections--permission", "/projects/P130164/connections", {}, { "/api/projects/P130164/connections": { status: 403, body: '{"code":"permission"}' } }),
  trailShot("connections--list", "/projects/P130164/connections", { widths: [1440], act: click("[data-list-toggle]"), full: true }),
  trailShot("connections--hover-package", "/projects/P130164/connections", { widths: [1440], act: hover("[data-package] a[data-node-link]") }),
  trailShot("connections--focus-package", "/projects/P130164/connections", { widths: [1440, 390], act: focus("[data-package] a[data-node-link]") }),
  trailShot("connections--hover-chip", "/projects/P130164/connections", { widths: [1440], act: hover("[data-node=document] [data-chip]") }),
  trailShot("connections--focus-toggle", "/projects/P130164/connections", { widths: [1440], act: focus("[data-list-toggle]") }),
  trailShot("connections--drawer", `/projects/P130164/connections?evidence=${TRAIL_ICR_54}`, { widths: [1440, 1024], full: false, act: async (page) => {
    await page.locator("[data-why]").waitFor();
  } }),
  trailShot("connections--320", "/projects/P130164/connections", { widths: [320] }),
  trailShot("connections--as-of", "/projects/P130164/connections?asof=2017-06-14"),
  trailShot("connections--hover-over-the-cap", "/projects/P156634/connections", { widths: [1440], act: hover("[data-package=KE-NWWDA-229129-CW-RFB] a[data-node-link]") }),
];

const PROJECT_SHOTS: Shot[] = [
  // Ticket 21: a project's address opens its Summary, so the plan versions are on /procurement.
  hubShot("project", "/projects/P156634/procurement"),
  hubShot("project--loading", "/projects/P156634/procurement", { pending: ["/api/projects/P156634"] }),
  hubShot("project--agencies-open", "/projects/P156634/procurement", { widths: [1440, 390], act: click("[data-agency-line] button") }),
  planShot("project--no-plans", { recorded: "project-p130164.json" }, {}, "/projects/P130164/procurement", "/api/projects/P130164"),
  planShot("project--error", { status: 503, body: SERVICE_DOWN }, {}, "/projects/P156634"),
  planShot("project--not-found", { status: 404, body: '{"code":"unknown_project"}' }, {}, "/projects/P999999"),
  hubShot("project--focus-version", "/projects/P156634/procurement", { widths: [1440, 390], act: focus("[data-agency] a:visible") }),
  planShot("projects", { recorded: "projects.json" }, {}, "/projects"),
  planShot("projects--loading", { recorded: "projects.json" }, { pending: ["/api/projects"] }, "/projects"),
  // Ticket 21: pages of 20, the list search, its answer and no match.
  planShot("projects--page-2", { recorded: "projects-page-2.json" }, {}, "/projects?page=2"),
  planShot("projects--india", { recorded: "projects-india.json" }, {}, "/projects?q=india"),
  planShot("projects--no-match", { recorded: "projects-no-match.json" }, {}, "/projects?q=atlantis"),
  // A search the server has not answered after 400 ms keeps the rows and says it is searching.
  planShot("projects--searching", { recorded: "projects.json" }, {
    act: async (page) => {
      await page.route((url) => url.pathname === "/api/projects" && url.searchParams.has("q"), () => undefined);
      await page.locator("[data-list-search] input").first().fill("kenya");
      await page.waitForTimeout(900);
    },
    full: true,
  }, "/projects"),
  planShot("projects--focus-search", { recorded: "projects.json" }, { widths: [1440, 390], act: focus("[data-list-search] input") }, "/projects"),
  planShot("projects--focus-next", { recorded: "projects.json" }, { widths: [1440, 390], act: focus("[data-pagination] a:visible >> nth=-1") }, "/projects"),
  planShot("projects--empty", { body: '{"as_of":"2026-10-23","total":0,"rows":[],"records_through":null}' }, {}, "/projects"),
  planShot("projects--error", { status: 503, body: SERVICE_DOWN }, {}, "/projects"),
];

const HUB_SHOTS: Shot[] = [
  // The frame and the Summary.
  hubShot("summary", "/projects/P130164"),
  hubShot("summary--loading", "/projects/P130164", { pending: ["/api/projects/P130164/summary"] }),
  hubShot("summary--frame-loading", "/projects/P130164", { pending: ["/api/projects/P130164"] }),
  hubShot("summary--active", "/projects/P156634"),
  // Ticket 99: at 1280 px beside the rail the Summary is under 75rem, so its fact tables take one column; at 1440 px two.
  hubShot("summary--1280", "/projects/P130164", { widths: [1280] }),
  hubShot("summary--active-1280", "/projects/P156634", { widths: [1280] }),
  hubShot("summary--history-unknown", "/projects/P130164", {}, { "/api/projects/P130164/summary": summaryWithout((body) => Object.assign(body, { history: { known: false, rows: [] }, lead: { ...body.lead, moves: null } })) }),
  hubShot("summary--no-ratings", "/projects/P130164", {}, { "/api/projects/P130164/summary": summaryWithout((body) => (body.ratings = [])) }),
  // A project whose record has a risk rating under the ESF shows it in place of its EA category.
  hubShot("summary--esf", "/projects/P130164", {}, { "/api/projects/P130164/summary": summaryWithout((body) => (body.ratings = body.ratings.map((fact: Record<string, any>) => (fact.key === "ea_category" ? { ...fact, key: "esf_rating", value: "Substantial" } : fact)))) }),
  hubShot("summary--value-missing", "/projects/P130164", {}, { "/api/projects/P130164/summary": summaryWithout((body) => (body.dates[0].value = null)) }),
  hubShot("summary--error", "/projects/P130164", {}, { "/api/projects/P130164/summary": { status: 503, body: SERVICE_DOWN } }),
  hubShot("summary--permission", "/projects/P130164", {}, { "/api/projects/P130164/summary": { status: 403, body: '{"code":"permission"}' } }),
  hubShot("summary--header-error", "/projects/P130164", {}, { "/api/projects/P130164": { status: 503, body: SERVICE_DOWN } }),
  hubShot("summary--focus-tab", "/projects/P130164", { widths: [1440, 390], act: focus("nav[aria-label='Project sections'] a >> nth=1") }),
  hubShot("summary--hover-tab", "/projects/P130164", { widths: [1440], act: hover("nav[aria-label='Project sections'] a >> nth=2") }),
  hubShot("summary--marker-focused", "/projects/P130164", { widths: [1440], act: focus("[data-fact=closing_date] [data-citation]") }),
  hubShot("summary--drawer-record", "/projects/P130164", { widths: [1440], full: false, act: click("[data-fact=commitment] [data-citation]") }),
  hubShot("summary--320", "/projects/P130164", { widths: [320] }),
  // Procurement.
  hubShot("procurement", "/projects/P156634/procurement"),
  hubShot("procurement--baseline-mark", "/projects/P156634/procurement", {}, { "/api/projects/P156634": { recorded: "project-p156634-baseline.json" } }),
  hubShot("procurement--versions-folded", "/projects/P156634/procurement", { widths: [1440, 390] }, { "/api/projects/P156634": { body: longVersions } }),
  hubShot("procurement--versions-open", "/projects/P156634/procurement", { widths: [1440, 390], full: true, act: click("[data-agency] button[aria-expanded=false]") }, { "/api/projects/P156634": { body: longVersions } }),
  hubShot("procurement--loading", "/projects/P156634/procurement", { pending: ["/api/projects/P156634"] }),
  hubShot("procurement--packages-searched", "/projects/P156634/procurement?packages_q=boreholes"),
  hubShot("procurement--packages-no-match", "/projects/P156634/procurement?packages_q=atlantis"),
  hubShot("procurement--packages-page-2", "/projects/P156634/procurement?packages_page=2"),
  hubShot("procurement--packages-error", "/projects/P156634/procurement", {}, { "/api/projects/P156634/packages": { status: 503, body: SERVICE_DOWN } }),
  hubShot("procurement--packages-loading", "/projects/P156634/procurement", { pending: ["/api/projects/P156634/packages"] }),
  // Check a plan: the change line, the change list and the baseline panel.
  hubShot("check-plan--change-list", `${PLAN}#changes`),
  hubShot("check-plan--added-redated", "/projects/P156634/procurement/ministry-of-water-and-irrigation/2020-04-30#changes"),
  hubShot("check-plan--earliest", "/projects/P156634/procurement/northern-water-works-development-agency/2020-12-07", {}, {
    "/api/projects/P156634/procurement/northern-water-works-development-agency/2020-12-07": { body: derived(PLAN_FILE, (body) => (body.plan.plan_date = "2020-12-07")) },
  }),
  // Only the comparison fails: the change line says so, and the section keeps its heading over the alert.
  hubShot("check-plan--changes-error", PLAN, {}, { [`${PLAN_API}/changes`]: { status: 503, body: SERVICE_DOWN } }),
  hubShot("check-plan--baseline-none", PLAN),
  hubShot("check-plan--baseline-another", PLAN, {}, { [PLAN_API]: { recorded: "check-plan-p156634-nwwda-2026-10-09-baseline.json" } }),
  hubShot("check-plan--baseline-this", "/projects/P156634/procurement/northern-water-works-development-agency/2025-07-21"),
  hubShot("check-plan--baseline-confirm", PLAN, { act: click("[data-baseline] button[data-button=secondary]") }, { [PLAN_API]: { recorded: "check-plan-p156634-nwwda-2026-10-09-baseline.json" } }),
  hubShot("check-plan--baseline-saving", PLAN, { pending: [BASELINE_API], act: click("[data-baseline] button") }),
  hubShot("check-plan--baseline-saved", JULY_2025, { act: thenClick(JULY_2025_API, "check-plan-p156634-nwwda-2025-07-21-baseline.json", "[data-baseline] button") }, {
    [JULY_2025_API]: { recorded: "check-plan-p156634-nwwda-2025-07-21.json" },
    [BASELINE_API]: { recorded: "baseline-saved.json" },
  }),
  hubShot("check-plan--baseline-removed", JULY_2025, { act: thenClick(JULY_2025_API, "check-plan-p156634-nwwda-2025-07-21.json", "[data-baseline] button") }, {
    [BASELINE_API]: { body: '{"baseline":null}' },
  }),
  hubShot("check-plan--baseline-error", PLAN, { act: click("[data-baseline] button") }, { [BASELINE_API]: { status: 503, body: SERVICE_DOWN } }),
  hubShot("check-plan--baseline-permission", PLAN, { act: click("[data-baseline] button") }, { [BASELINE_API]: { status: 403, body: '{"code":"permission"}' } }),
  hubShot("check-plan--baseline-piu", `${PLAN}?view=piu`, {}, { [`${PLAN_API}?view=piu`]: { body: derived("check-plan-p156634-nwwda-2026-10-09-baseline.json", (body) => (body.baseline.saved_by = null)) } }),
  hubShot("check-plan--baseline-delay-num", PLAN, { widths: [1440, 390], act: focus("[data-baseline-delay] button[data-num]:visible") }, { [PLAN_API]: { recorded: "check-plan-p156634-nwwda-2026-10-09-baseline.json" } }),
  // Documents.
  hubShot("documents", "/projects/P130164/documents"),
  hubShot("documents--loading", "/projects/P130164/documents", { pending: ["/api/projects/P130164/documents"] }),
  hubShot("documents--group-open", "/projects/P130164/documents", { full: true, act: click("[data-documents] button[aria-expanded=false]:visible") }),
  hubShot("documents--term-open", "/projects/P130164/documents", { widths: [1440], act: click("[data-documents] [data-term]") }),
  // A project the slice selects whose documents are still to come, and one outside the slice.
  hubShot("documents--empty", "/projects/P117635/documents", {}, {
    "/api/projects/P117635": { recorded: "project-p117635.json" },
    "/api/projects/P117635/documents": { recorded: "documents-p117635-none-yet.json" },
  }),
  hubShot("documents--outside", "/projects/P120014/documents", {}, {
    "/api/projects/P120014": { recorded: "project-p120014.json" },
    "/api/projects/P120014/documents": { recorded: "documents-p120014-outside.json" },
  }),
  hubShot("documents--error", "/projects/P130164/documents", {}, { "/api/projects/P130164/documents": { status: 503, body: SERVICE_DOWN } }),
  // A listed document whose type the documents API leaves blank is named by its date.
  hubShot("documents--untyped", "/projects/P130164/documents", {}, {
    "/api/projects/P130164/documents": { body: derived("documents-p130164.json", (body) => (body.groups.find((group: { type: string }) => group.type === "other").documents[0].document_type = "")) },
  }),
  // The source view.
  hubShot("source", `${SOURCE}?page=23&para=54`),
  hubShot("source--loading", `${SOURCE}?page=23&para=54`, { pending: [`/api${SOURCE}`] }),
  hubShot("source--no-para-asked", `${SOURCE}?page=23`),
  hubShot("source--moved", `${SOURCE}?page=22&para=54`),
  hubShot("source--no-para", `${SOURCE}?page=23&para=999`),
  hubShot("source--page-range", `${SOURCE}?page=80`),
  hubShot("source--page-unread", `${SOURCE}?page=5`),
  hubShot("source--page-empty", `${SOURCE}?page=49`),
  hubShot("source--front-matter", `${SOURCE}?page=2`),
  hubShot("source--doc-unread", "/projects/P130164/documents/30152361"),
  hubShot("source--not-found", "/projects/P130164/documents/not-a-document"),
  hubShot("source--ambiguous", "/projects/P130164/documents/isr"),
  hubShot("source--as-of", `${SOURCE}?page=23&asof=2019-10-01`),
  hubShot("source--reissue", "/projects/P130164/documents/icr-review-2023-05-04?page=1"),
  // A page with a table read into rows, and a plan's page of STEP rows: below 768 px each scrolls in a frame
  // that takes focus.
  // At 1024 px the table shows in its frame (ticket 60).
  hubShot("source--table", "/projects/P130164/documents/pad-2013-10-01?page=65", { widths: [1440, 1024, 390, 320] }),
  hubShot("source--plan-rows", "/projects/P161305/documents/procurement-plan-kenya-national-highways-authority-2026-09-24?page=3", { widths: [1440, 1024, 390, 320] }),
  hubShot("source--error", `${SOURCE}?page=23&para=54`, {}, { [`/api${SOURCE}?page=23&para=54`]: { status: 503, body: SERVICE_DOWN } }),
  hubShot("source--focus-page-bar", `${SOURCE}?page=23&para=54`, { widths: [1440, 390], act: focus("[data-page-bar] a:visible >> nth=-1") }),
  hubShot("source--hover-page-bar", `${SOURCE}?page=23&para=54`, { widths: [1440], act: hover("[data-page-bar] a:visible >> nth=-1") }),
  hubShot("source--320", `${SOURCE}?page=23&para=54`, { widths: [320] }),
  // The drawer's link to the source view, focused, then where it lands.
  hubShot("drawer--open-at-page", `/projects/P130164?evidence=${encodeURIComponent("strata.gold.passage:31525018/v1/54")}`, { widths: [1440, 390], full: false, act: focus("[data-open-at-page]") }),
  hubShot("drawer--landed", `/projects/P130164?evidence=${encodeURIComponent("strata.gold.passage:31525018/v1/54")}`, { widths: [1440, 390], act: click("[data-open-at-page]") }),
];

// Ticket 14: the one box, the answer panel and the evidence drawer, as the 14 brief's section 11 lists
// them. The answers are the streams ticket 13's server writes, recorded in tests/fixtures/api.
const QUESTION = "Why were works contracts in P130164 advertised again?";
const ICR_54 = "strata.gold.passage:31525018/v1/54";
const ISR_S4 = "strata.gold.passage:19095337/v1/s4";

const typeInBox = (text: string) => async (page: Page) => {
  await page.keyboard.press("/");
  await page.keyboard.type(text);
  await page.waitForTimeout(400);
};

const askInBox = (text = QUESTION, wait = true) => async (page: Page) => {
  await typeInBox(text)(page);
  await page.keyboard.press("Enter");
  if (wait) await page.locator("[data-answer-panel] [data-answer]:not([data-answer=streaming])").waitFor();
  await page.waitForTimeout(300);
};

const then = (...acts: ((page: Page) => Promise<void>)[]) => async (page: Page) => {
  for (const act of acts) await act(page);
};

const BOX_API: Shot["api"] = {
  "/api/projects/P130164": { recorded: "project-p130164.json" },
  "/api/projects/P156634": { recorded: "project-p156634.json" },
  "/api/projects/P130164/summary": { recorded: "summary-p130164.json" },
  "/api/projects/P156634/summary": { recorded: "summary-p156634.json" },
  "/api/lookup/loan": { recorded: "lookup-loan-ida-60290.json" },
  "/api/lookup/activity": { recorded: "lookup-activity-ke-nwwda-541055-cw-rfb.json" },
  "/api/evidence": { recorded: "evidence-icr-p130164-54.json" },
  "/api/evidence/opened": { body: '{"opened":[],"recorded":true}' },
};

// A shot of the box or the answer on P130164's page, with the stream it answers with.
const answerShot = (name: string, stream: string, rest: Partial<Shot> = {}, path = "/projects/P130164"): Shot =>
  app(name, path, {}, { full: true, ...rest, api: { ...app(name, path).api, ...BOX_API, "/api/ask": { recorded: stream }, ...rest.api } });

const ANSWER = "ask-p130164-removed-number.sse";
const marker = "[data-answer-panel] [data-citation='1']";

// Ticket 98: an answer asked from Home, in the work's columns above the head, with the briefing folded to one line.
const HOME_ANSWERED: Shot = app("home--answered", "/", {}, {
  widths: [1440],
  full: true,
  api: { ...homeApi("home.json"), ...BOX_API, "/api/ask": { recorded: "ask-p130164-rebidding.sse" } },
  act: askInBox("Why were works contracts advertised again?"),
});

const ANSWER_SHOTS: Shot[] = [
  HOME_ANSWERED,
  answerShot("box--hint", ANSWER, { full: false, act: (page) => page.keyboard.press("/") }, "/"),
  answerShot("box--project", ANSWER, { full: false, act: typeInBox("P130164") }, "/"),
  ...["IDA60290", "IDA-60290", "60290", "IDA / 60290"].map((loan, index) =>
    answerShot(`box--loan-${index + 1}`, ANSWER, { full: false, widths: index ? [1440] : WIDTHS, act: typeInBox(loan) }, "/"),
  ),
  answerShot("box--step-reference", ANSWER, { full: false, act: typeInBox("KE-NWWDA-541055-CW-RFB") }, "/"),
  answerShot("box--free-text", ANSWER, { full: false, act: typeInBox("Why were works contracts advertised again?") }, "/"),
  answerShot("box--free-text-with-id", ANSWER, { full: false, act: typeInBox(QUESTION) }, "/"),
  answerShot("box--lookup-pending", ANSWER, { full: false, pending: ["/api/lookup/activity"], act: typeInBox("KE-NWWDA-541055-CW-RFB") }, "/"),
  answerShot("box--not-found", ANSWER, { full: false, api: { "/api/projects/P999999": { status: 404, body: '{"code":"unknown_project"}' } }, act: typeInBox("P999999") }, "/"),
  answerShot("box--lookup-failed", ANSWER, { full: false, api: { "/api/lookup/activity": { status: 503, body: '{"code":"data_service"}' } }, act: typeInBox("KE-NWWDA-541055-CW-RFB") }, "/"),
  answerShot("box--scoped", ANSWER, { full: false, act: typeInBox("Why?") }),
  answerShot("box--scope-removed", ANSWER, { full: false, act: click("[data-scope-chip] button") }),
  answerShot("box--step-landing", ANSWER, { full: false, act: then(typeInBox("KE-NWWDA-541055-CW-RFB"), async (page) => {
    await page.keyboard.press("Enter");
    await page.waitForTimeout(600);
  }), api: { "/api/projects/P156634/procurement/northern-water-works-development-agency": { recorded: PLAN_FILE } } }, "/"),
  answerShot("answer--streaming", ANSWER, { pending: ["/api/ask"], act: askInBox(QUESTION, false) }),
  answerShot("answer--ready", ANSWER, { act: askInBox() }),
  answerShot("answer--all-checks-passed", "ask-p130164-rebidding.sse", { act: askInBox() }),
  answerShot("answer--hover-marker", ANSWER, { full: false, widths: WIDE, act: then(askInBox(), hover(marker)) }),
  answerShot("answer--focus-marker", ANSWER, { full: false, act: then(askInBox(), focus(marker)) }),
  // A number's and a date's Number tooltip in an answer: what each matched, and where that came from (ticket 96).
  answerShot("answer--num-hover", ANSWER, { full: false, widths: WIDE, act: then(askInBox(), hover("[data-answer-panel] [data-sentence-text='0'] [data-num]")) }),
  answerShot("answer--date-hover", ANSWER, { full: false, widths: WIDE, act: then(askInBox(), hover("[data-answer-panel] [data-sentence-text='2'] [data-num]")) }),
  answerShot("answer--drawer", ANSWER, { full: false, act: then(askInBox(), click(marker)) }),
  answerShot("answer--drawer-visited", ANSWER, { full: false, act: then(askInBox(), click(marker), async (page) => {
    await page.keyboard.press("Escape");
    await page.waitForTimeout(250);
  }) }),
  answerShot("answer--drawer-from-link", ANSWER, { full: false }, `/projects/P130164?evidence=${encodeURIComponent(ICR_54)}`),
  answerShot("answer--drawer-loading", ANSWER, { full: false, pending: ["/api/evidence"] }, `/projects/P130164?evidence=${encodeURIComponent(ICR_54)}`),
  answerShot("answer--drawer-failed", ANSWER, { full: false, api: { "/api/evidence": { status: 503, body: SERVICE_DOWN } } }, `/projects/P130164?evidence=${encodeURIComponent(ICR_54)}`),
  answerShot("answer--drawer-unknown", ANSWER, { full: false, api: { "/api/evidence": { status: 404, body: '{"code":"unknown_evidence"}' } } }, "/projects/P130164?evidence=strata.gold.passage%3Anothing"),
  // The ICR of October 10, 2019, linked as of a date before it was public.
  answerShot("answer--drawer-unknown-as-of", ANSWER, { full: false, api: { "/api/evidence": { status: 404, body: '{"code":"unknown_evidence"}' } } }, `/projects/P130164?asof=2016-08-26&evidence=${encodeURIComponent(ICR_54)}`),
  answerShot("answer--drawer-preview", ANSWER, { full: false }, `/projects/P130164?view=public&evidence=${encodeURIComponent(ICR_54)}`),
  // An ISR section has no paragraph number: the drawer names the section, and its long name wraps.
  answerShot("answer--drawer-section", ANSWER, { full: false, widths: [...WIDTHS, 320], api: { "/api/evidence": { recorded: "evidence-isr-p130164-s4.json" } } }, `/projects/P130164?evidence=${encodeURIComponent(ISR_S4)}`),
  // An answer whose fourth sentence quotes the table in an ISR section and also cites the ICR's Annex 1.A.
  answerShot("answer--isr-card", "ask-p130164-isr-section.sse", { full: false, widths: WIDE, act: then(askInBox(), hover("[data-answer-panel] [data-sentence-text='3'] [data-citation='3']")) }),
  // Ticket 18's kinds of passage in the drawer, opened from a link, and the removed box's table-summary reason.
  ...([
    ["scanned", "strata.gold.passage:18381488/v1/23", "evidence-pad-p130164-scanned.json"],
    ["table-row", "strata.gold.passage:18381488/v1/table65.2", "evidence-pad-p130164-risk-row.json"],
    ["table-summary", "strata.gold.passage:18381488/v1/table65", "evidence-pad-p130164-risk-summary.json"],
    ["notice", "strata.gold.passage:OP00118817/v1/s5", "evidence-notice-op00118817-qualifications.json"],
    ["notice-contacts", "strata.gold.passage:OP00118817/v1/s8", "evidence-notice-op00118817.json"],
    ["french", "strata.gold.passage:33407968/v1/1", "evidence-icr-p127203-fr.json"],
  ] as const).map(([kind, id, file]) =>
    answerShot(`answer--drawer-${kind}`, ANSWER, { full: false, widths: [1440, 390], api: { "/api/evidence": { recorded: file } } }, `/projects/P130164?evidence=${encodeURIComponent(id)}`),
  ),
  answerShot("answer--removed-table-summary", "ask-p130164-table-summary.sse", { full: false, act: askInBox() }),
  // A sentence quoting a table row's rating: the drawer highlights the rating's cell (design review r2 P1).
  answerShot("answer--drawer-table-row-quoted", "ask-p130164-table-row.sse", { full: false, widths: [1440, 390], act: then(askInBox(), click("[data-answer-panel] [data-sentence-text='3'] [data-citation]")) }),
  answerShot("answer--isr-drawer", "ask-p130164-isr-section.sse", { full: false, widths: [...WIDTHS, 320], act: then(askInBox(), click("[data-answer-panel] [data-sentence-text='3'] [data-citation='3']")) }),
  answerShot("answer--error", "ask-agent-unavailable.sse", { act: askInBox() }),
  answerShot("answer--no-agent", "ask-no-agent.sse", { act: askInBox() }),
  answerShot("answer--refused", "ask-content-filter.sse", { act: askInBox() }),
  answerShot("answer--empty-scoped", "ask-p130164-nothing-found.sse", { act: askInBox("Which firms built the bridges in P130164?") }),
  answerShot("answer--empty-unscoped", "ask-p130164-nothing-found.sse", { act: askInBox("Which firms built the bridges?") }, "/"),
  answerShot("answer--unsupported", "ask-p130164-before-the-icr.sse", { act: askInBox() }),
  answerShot("answer--as-of", ANSWER, { act: askInBox() }, "/projects/P130164?asof=2026-10-01"),
  answerShot("answer--preview", ANSWER, { act: askInBox() }, "/projects/P130164?view=public"),
  answerShot("answer--320", ANSWER, { widths: [320], act: askInBox() }),
  // The plan check beside an open drawer: at 1024 px the page area is 614 px wide, so its table
  // becomes activity cards (the 14 brief, section 2.5).
  app("check-plan--drawer", `${PLAN}?evidence=${encodeURIComponent(ICR_54)}`, {}, {
    widths: [1440, 1024],
    api: { ...app("x", PLAN).api, [PLAN_API]: plan, "/api/evidence": { recorded: "evidence-icr-p130164-54.json" }, "/api/evidence/opened": { body: '{"opened":[]}' } },
  }),
];

// Ticket 35: Check a plan's draft action, the writing page, a draft's page and the Drafts tab, in the
// states the 35 brief's section 12 lists. The answers are the server's own, recorded on the fixture by
// tests/record_drafts_api.py; a state no recording holds is a recording with one value changed.
const DRAFT = "/drafts/draft-0001";
const DRAFT_API = "/api/drafts/draft-0001";
const DRAFT_FILE = "drafts-review-notes-draft.json";
const draftWith = (edit: (body: Record<string, any>) => void, name = DRAFT_FILE) => derived(name, edit);
const OPENED: Answer = { body: '{"recorded":true}' };
// The open draft the plan check names: your own, and a teammate's as Ben sees Ana's.
const EXISTING: Answer = { recorded: "drafts-existing-yours.json" };
const EXISTING_TEAMMATE: Answer = { recorded: "drafts-existing.json" };
// Ben, Ana's teammate, signed in: the screens that show him Ana's draft.
const AS_TEAMMATE: Shot["api"] = { "/api/me": { recorded: "drafts-me-teammate.json" } };
const NO_EXISTING: Answer = { body: '{"draft":null}' };
// The read a draft page makes: /api/drafts/:draftId for /drafts/:draftId.
const draftRead = (path: string) => `/api${path.split("?")[0]}`;
const draftShot = (name: string, answer: Answer, rest: Partial<Shot> = {}, path = DRAFT): Shot =>
  app(name, path, {}, { ...rest, api: { ...app(name, path).api, [draftRead(path)]: answer, "/api/evidence/opened": OPENED, ...rest.api } });
// Check a plan with the existing-draft lookup answered.
const planWithDraft = (name: string, existing: Answer, rest: Partial<Shot> = {}, body: Answer = plan, path = PLAN): Shot =>
  app(name, path, {}, { ...rest, api: { ...app(name, PLAN).api, [PLAN_API]: body, "/api/drafts/existing": existing, ...rest.api } });
// The writing page, reached from Check a plan's button, with the stream it answers with.
const writingShot = (name: string, stream: Answer, rest: Partial<Shot> = {}): Shot =>
  planWithDraft(name, NO_EXISTING, {
    full: true,
    ...rest,
    api: { "/api/drafts": stream, [DRAFT_API]: { recorded: DRAFT_FILE }, "/api/evidence/opened": OPENED, ...rest.api },
    act: async (page) => {
      await page.locator("[data-draft-action]:visible").first().click();
      await page.waitForTimeout(rest.pending ? 300 : 900);
    },
  });
const noSignals = derived(PLAN_FILE, (body) => {
  for (const row of body.rows) row.marks = row.marks.filter((mark: { mark: string }) => mark.mark === "data_note");
  Object.assign(body.counts, { needs_a_look: 0, watch: 0, signal: 0, marked: 3, unmarked: 6 });
});
const filesMissing = draftWith((body) => {
  body.export.files = [];
  body.export.files_available = false;
}, "drafts-review-notes-exported.json");
const failingAct: Shot["api"] = { "/api/drafts/draft-0001/check": { status: 503, body: SERVICE_DOWN } };
const MARKER = "[data-draft-notes] [data-view]:visible [data-citation='1']";
const LAST_MARKER = "[data-draft-notes] [data-view]:visible [data-citation='3']";

// Ticket 37: Following, the follow control and the mission brief, with /api answered from the server's answers on
// the fixture (tests/record_following_api.py). The states the fixture cannot reach are the following-made-up-*.json
// answers, made up from the real one and saying so.
const STAFF = { recorded: "me-staff.json" };
const following = (name: string, file: string | null, rest: Partial<Shot> = {}, path = "/projects/following"): Shot =>
  app(`following--${name}`, path, { me: STAFF }, {
    ...rest,
    api: { ...app(name, path, { me: STAFF }).api, ...(file ? { "/api/following": { recorded: file } } : {}), "/api/evidence/opened": { body: '{"recorded":true}' }, ...rest.api },
  });
const BRIEF_DRAFT = { "/api/drafts/draft-0001": { recorded: "drafts-mission-brief-draft.json" } };
const projectWithFollow = (name: string, follow: Answer, rest: Partial<Shot> = {}): Shot =>
  app(`following--${name}`, "/projects/P156634", { me: STAFF }, {
    ...rest,
    api: {
      ...app(name, "/projects/P156634", { me: STAFF }).api,
      "/api/projects/P156634": { recorded: "project-p156634.json" },
      "/api/projects/P156634/summary": { recorded: "summary-p156634.json" },
      "/api/projects/P156634/follow": follow,
      ...rest.api,
    },
  });

const FOLLOWING_SHOTS: Shot[] = [
  following("loading", null, { pending: ["/api/following"] }),
  following("populated", "following-p156634.json"),
  following("fold-open", "following-p156634.json", { full: true, act: click("[data-following-view]:visible [data-fold]") }),
  following("states", "following-made-up-states.json"),
  following("many-quiet", "following-made-up-many-quiet.json", { full: true, act: click("[data-following-view]:visible [data-fold]") }),
  following("all-quiet", "following-made-up-all-quiet.json"),
  following("one", "following-made-up-one.json"),
  following("track-record", "following-made-up-track-record.json", { full: true, act: click("[data-track-record] button[aria-expanded]") }),
  following("asof", "following-asof-2024-06-30.json", {}, "/projects/following?asof=2024-06-30"),
  following("empty", "following-empty.json"),
  following("error", null, { api: { "/api/following": { status: 503, body: '{"code":"data_service","trace_id":"4bf92f3577b34da6a3ce929d0e0e4736"}' } } }),
  following("permission", null, { api: { "/api/following": { status: 403, body: '{"code":"permission"}' } } }),
  following("not-staff", null, { api: { "/api/me": { recorded: "me-not-staff.json" }, "/api/following": { status: 403, recorded: "following-not-staff.json" } } }),
  following("preview-piu", null, {}, "/projects/following?view=piu"),
  following("preview-public", null, {}, "/projects/following?view=public"),
  // The visible Status term: the table's header from 1,200 px, the definitions above the list below it.
  following("status-term", "following-p156634.json", { widths: WIDE, act: click("[data-term]:visible >> nth=0") }),
  following("ratio-num", "following-p156634.json", { widths: WIDE, act: click("[data-following-view]:visible [data-signal=above_estimate] [data-num]") }),
  following("hover-add", "following-p156634.json", { widths: WIDE, act: hover("[data-following-view]:visible [data-add-brief]") }),
  following("focus-add", "following-p156634.json", { act: focus("[data-following-view]:visible [data-add-brief]") }),
  following("focus-marker", "following-p156634.json", { act: focus("[data-following-view]:visible [data-citation]") }),
  following("drawer", "following-p156634.json", { act: click("[data-following-view]:visible [data-signal=completion_passed] [data-citation]") }),
  following("all-projects", null, { api: { "/api/projects": { recorded: "projects.json" } } }, "/projects"),
  // Ticket 99: Following and All projects as the sidebar's items under Projects, with the sidebar opened.
  following("sidebar-items", "following-p156634.json", { widths: [1440], full: true, act: click("[data-sidebar-toggle]") }),
  following("all-projects-sidebar-items", null, { widths: [1440], full: true, act: click("[data-sidebar-toggle]"), api: { "/api/projects": { recorded: "projects.json" } } }, "/projects"),
  projectWithFollow("project-not-following", { recorded: "follow-off.json" }),
  projectWithFollow("project-following", { recorded: "follow-on.json" }),
  // Only the PUT is held, so the control first reads that you don't follow and then shows Saving.
  projectWithFollow("project-saving", { recorded: "follow-off.json" }, {
    act: async (page) => {
      await page.route("**/api/projects/P156634/follow", (route) => (route.request().method() === "PUT" ? undefined : route.fallback()));
      await page.locator("[data-follow] button").first().click();
      await page.waitForTimeout(200);
    },
  }),
  projectWithFollow("project-loading", { recorded: "follow-off.json" }, { pending: ["/api/projects/P156634/follow"] }),
  projectWithFollow("project-hover-follow", { recorded: "follow-off.json" }, { widths: WIDE, act: hover("[data-follow] button") }),
  following("brief-writing", "following-p156634.json", {
    full: true,
    pending: ["/api/drafts"],
    api: BRIEF_DRAFT,
    act: async (page) => {
      await page.locator("[data-following-view]:visible [data-add-brief]").first().click();
      await page.waitForTimeout(300);
    },
  }),
  app("following--brief-draft", "/drafts/draft-0001", { me: STAFF }, { api: { ...app("b", "/").api, ...BRIEF_DRAFT, "/api/evidence/opened": { body: '{"recorded":true}' } } }),
  app("following--brief-checked", "/drafts/draft-0001", { me: STAFF }, {
    api: { ...app("b", "/").api, "/api/drafts/draft-0001": { recorded: "drafts-mission-brief-checked.json" }, "/api/evidence/opened": { body: '{"recorded":true}' } },
  }),
  app("following--brief-exported", "/drafts/draft-0001", { me: STAFF }, {
    api: { ...app("b", "/").api, "/api/drafts/draft-0001": { recorded: "drafts-mission-brief-exported.json" }, "/api/evidence/opened": { body: '{"recorded":true}' } },
  }),
];

const DRAFT_SHOTS: Shot[] = [
  planWithDraft("draft--plan-action", NO_EXISTING),
  planWithDraft("draft--plan-none", NO_EXISTING, {}, { body: noSignals }),
  planWithDraft("draft--plan-existing", EXISTING),
  planWithDraft("draft--plan-existing-teammate", EXISTING_TEAMMATE, { api: AS_TEAMMATE }),
  planWithDraft("draft--plan-asof", NO_EXISTING, {}, plan, `${PLAN}?asof=2026-10-01`),
  writingShot("draft--writing", { recorded: "drafts-write-review-notes.sse" }, { pending: ["/api/drafts"] }),
  writingShot("draft--writing-error", { recorded: "drafts-write-agent-unavailable.sse" }),
  writingShot("draft--writing-nothing", { recorded: "drafts-write-nothing-survived.sse" }),
  draftShot("draft--writing-reload", { recorded: DRAFT_FILE }, { full: true }, "/drafts/new?kind=review_notes&pid=P156634&agency=northern-water-works-development-agency&version=2026-10-09"),
  draftShot("draft--loading", { recorded: DRAFT_FILE }, { pending: [DRAFT_API] }),
  draftShot("draft", { recorded: DRAFT_FILE }),
  // The first screen at 900 px tall, with the bar stuck to the window's bottom, and the page scrolled
  // with the header stuck to its top.
  draftShot("draft--first-screen", { recorded: DRAFT_FILE }, { full: false }),
  draftShot("draft--scrolled", { recorded: DRAFT_FILE }, { full: false, act: (page) => page.evaluate(() => window.scrollTo(0, 700)) }),
  draftShot("draft--saving", { recorded: DRAFT_FILE }, { pending: ["/api/drafts/draft-0001/check"], full: true, act: click("[data-draft-bar] [data-button=primary]") }),
  draftShot("draft--checked", { recorded: "drafts-review-notes-checked.json" }),
  // Ticket 103: just after Mark as checked, the bar's decided line, Export to Word solid with focus, and the side panel's
  // Checked line (or, at 390 px, the stepper in the head).
  draftShot("draft--marked-checked", { recorded: DRAFT_FILE }, {
    widths: [1440, 1024, 390],
    api: { "/api/drafts/draft-0001/check": { recorded: "drafts-review-notes-checked.json" } },
    act: async (page) => {
      await page.locator("[data-draft-bar] [data-button=primary]").first().click();
      await page.locator("[data-decided-line]").waitFor();
    },
  }),
  draftShot("draft--exporting", { recorded: "drafts-review-notes-checked.json" }, { pending: ["/api/drafts/draft-0001/export"], full: true, act: click("[data-draft-bar] [data-button=primary]") }),
  draftShot("draft--exported", { recorded: "drafts-review-notes-checked.json" }, {
    full: true,
    api: { "/api/drafts/draft-0001/export": { recorded: "drafts-review-notes-exported.json" } },
    act: click("[data-draft-bar] [data-button=primary]"),
  }),
  draftShot("draft--exported-revisit", { recorded: "drafts-review-notes-exported.json" }),
  draftShot("draft--exported-files-missing", { body: filesMissing }),
  draftShot("draft--partial", { recorded: "drafts-review-notes-partial.json" }, {}, "/drafts/draft-0002"),
  // Ticket 105: How I checked this draft, which opens on the two sentences I removed.
  draftShot("checks--how-window-draft", { recorded: "drafts-review-notes-partial.json" }, { widths: [1440, 390], act: click("[data-how-checked]") }, "/drafts/draft-0002"),
  draftShot("draft--refused", { recorded: "drafts-review-notes-refused.json" }, {}, "/drafts/draft-0003"),
  draftShot("draft--teammate", { recorded: "drafts-review-notes-teammate.json" }, { api: AS_TEAMMATE }),
  draftShot("draft--discarded", { recorded: "drafts-review-notes-discarded.json" }, {}, "/drafts/draft-0004"),
  draftShot("draft--action-failed", { recorded: DRAFT_FILE }, { full: true, api: failingAct, act: click("[data-draft-bar] [data-button=primary]") }),
  draftShot("draft--conflict", { recorded: "drafts-review-notes-checked.json" }, {
    full: true,
    api: { "/api/drafts/draft-0001/check": { status: 409, body: '{"code":"stale","error":"stale","state":"checked"}' } },
    act: async (page) => {
      // The page loaded the draft as it was, then another tab checked it.
      await page.route("**/api/drafts/draft-0001", (route) => route.fulfill({ contentType: "application/json", body: readFileSync(new URL(DRAFT_FILE, RECORDED), "utf8") }), { times: 1 });
      await page.reload();
      await page.locator("[data-draft-bar] [data-button=primary]").first().click();
      await page.waitForTimeout(400);
    },
  }),
  // Ticket 60: another tab exported the draft, so the export panel says so at its top.
  draftShot("draft--conflict-exported", { recorded: "drafts-review-notes-exported.json" }, {
    full: true,
    api: { "/api/drafts/draft-0001/check": { status: 409, body: '{"code":"stale","error":"stale","state":"exported"}' } },
    act: async (page) => {
      // The page loaded the draft as it was, then another tab exported it.
      await page.route("**/api/drafts/draft-0001", (route) => route.fulfill({ contentType: "application/json", body: readFileSync(new URL(DRAFT_FILE, RECORDED), "utf8") }), { times: 1 });
      await page.reload();
      await page.locator("[data-draft-bar] [data-button=primary]").first().click();
      await page.waitForTimeout(400);
    },
  }),
  draftShot("draft--not-found", { status: 404, body: '{"code":"unknown_draft"}' }, {}, "/drafts/draft-9999"),
  draftShot("draft--error", { status: 503, body: SERVICE_DOWN }),
  draftShot("draft--preview-piu", { recorded: DRAFT_FILE }, {}, `${DRAFT}?view=piu`),
  draftShot("draft--preview-public", { recorded: DRAFT_FILE }, {}, `${DRAFT}?view=public`),
  draftShot("draft--hover-check", { recorded: DRAFT_FILE }, { widths: [1440, 390], act: hover("[data-draft-bar] [data-button=primary]") }),
  draftShot("draft--focus-check", { recorded: DRAFT_FILE }, { widths: [1440, 390], act: focus("[data-draft-bar] [data-button=primary]") }),
  draftShot("draft--focus-held-export", { recorded: DRAFT_FILE }, { widths: [1440, 390], act: focus("[data-draft-bar] [data-held]") }),
  draftShot("draft--focus-discard", { recorded: DRAFT_FILE }, { widths: [1440, 390], act: focus("[data-draft-bar] [data-button=ghost]") }),
  draftShot("draft--focus-last-marker", { recorded: DRAFT_FILE }, { widths: [1440, 390], act: focus(LAST_MARKER) }),
  draftShot("draft--drawer", { recorded: DRAFT_FILE }, { widths: [1440, 1024, 800], act: click(MARKER) }),
  draftShot("draft--lede-num", { recorded: DRAFT_FILE }, { widths: [1440, 390], act: hover("[data-lede] [data-num]") }),
  draftShot("draft--focus-restore", { recorded: "drafts-review-notes-discarded.json" }, { widths: [1440, 390], act: focus("[data-discarded-notice] button") }, "/drafts/draft-0004"),
  draftShot("draft--focus-file", { recorded: "drafts-review-notes-exported.json" }, { widths: [1440, 390], act: focus("[data-export-success] a") }),
  draftShot("draft--320", { recorded: DRAFT_FILE }, { widths: [320] }),
  draftShot("drafts-tab", { recorded: "drafts-list.json" }, { api: { "/api/drafts": { recorded: "drafts-list.json" } } }, "/drafts"),
  draftShot("drafts-tab--teammate", { recorded: "drafts-list-teammate.json" }, { api: { ...AS_TEAMMATE, "/api/drafts": { recorded: "drafts-list-teammate.json" } } }, "/drafts"),
  draftShot("drafts-tab--loading", { recorded: "drafts-list.json" }, { pending: ["/api/drafts"] }, "/drafts"),
  draftShot("drafts-tab--empty", { recorded: "drafts-list-empty.json" }, { api: { "/api/drafts": { recorded: "drafts-list-empty.json" } } }, "/drafts"),
  draftShot("drafts-tab--discarded-open", { recorded: "drafts-list.json" }, { full: true, api: { "/api/drafts": { recorded: "drafts-list.json" } }, act: click("[data-discarded-fold] button") }, "/drafts"),
  draftShot("drafts-tab--error", { recorded: "drafts-list.json" }, { api: { "/api/drafts": { status: 503, body: SERVICE_DOWN } } }, "/drafts"),
  draftShot("drafts-tab--preview-piu", { recorded: "drafts-list.json" }, {}, "/drafts?view=piu"),
  draftShot("drafts-tab--preview-public", { recorded: "drafts-list.json" }, {}, "/drafts?view=public"),
];


// Ticket 29: the Lessons tab, Waiting for review and the review page, in the states the 29 brief's section 12
// lists. The answers are the server's own, recorded on the fixture by tests/record_lessons_api.py; a state no
// recording holds is a recording with one value changed. A refusal is recorded with its status beside its body.
const REVIEWER: Answer = { recorded: "lessons-me-reviewer.json" };
const NOT_A_REVIEWER: Answer = { recorded: "lessons-me-viewer.json" };
function refusal(name: string): Answer {
  const { status, body } = JSON.parse(readFileSync(new URL(name, RECORDED), "utf8"));
  return { status, body: JSON.stringify(body) };
}
const lessonsWith = (name: string, edit: (body: Record<string, any>) => void): Answer => ({ body: derived(name, edit) });
const lessonShot = (name: string, path: string, answers: Shot["api"], rest: Partial<Shot> = {}, me: Answer = REVIEWER): Shot =>
  app(`lessons--${name}`, path, {}, {
    ...rest,
    api: { ...app(name, path).api, "/api/lessons/me": me, "/api/evidence": { recorded: "evidence-icr-p130164-54.json" }, "/api/evidence/opened": { body: '{"recorded":true}' }, ...answers },
  });
// Ticket 39: the Lessons tab answers in one request (tests/record_lessons_page_api.py), with the library inside it.
const LIBRARY = { "/api/lessons/page": { recorded: "lessons-page-reviewer.json" } };
const libraryWith = (name: string, edit: (library: Record<string, any>) => void): Answer => lessonsWith(name, (body) => edit(body.library));
const QUEUE = (file: string) => ({ "/api/lessons/review": { recorded: file } });
const REB = "new-e903b07ad1";
const PERM = "new-64ec0401e3";
const IEG = "new-cfdf000a46";
const RECHECK_ITEM = "recheck-09bf32ecc3";
const CROSS_ITEM = "cross-e0d9a6a06a";
const itemPath = (id: string) => `/lessons/review/${id}`;
const itemApi = (id: string) => `/api/lessons/review/${id}`;
const item = (id: string, answer: Answer, rest: Partial<Shot> = {}, extra: Shot["api"] = {}, me: Answer = REVIEWER, name = "") =>
  lessonShot(name, itemPath(id), { [itemApi(id)]: answer, ...extra }, rest, me);
const review = (name: string, id: string, file: string, rest: Partial<Shot> = {}, extra: Shot["api"] = {}) =>
  item(id, { recorded: file }, rest, extra, REVIEWER, `review--${name}`);
const reviewWith = (name: string, id: string, file: string, edit: (body: Record<string, any>) => void, rest: Partial<Shot> = {}) =>
  item(id, lessonsWith(file, edit), rest, {}, REVIEWER, `review--${name}`);
const fillReason = (text: string, button: string) => async (page: Page) => {
  await page.locator("[data-decision-form] textarea").last().fill(text);
  await page.locator(`[data-decision-form] button:has-text("${button}")`).first().click();
  await page.waitForTimeout(400);
};
const choose = (label: string) => async (page: Page) => {
  await page.getByRole("radio", { name: label }).first().check();
  await page.waitForTimeout(250);
};
const manySources = (library: Record<string, any>) => {
  const card = library.lessons[0];
  const more = Array.from({ length: 6 }, (_, n) => ({ ...card.evidence[0], evidence_id: `${card.evidence[0].evidence_id}-${n}`, locator: { kind: "paragraph", text: String(60 + n) } }));
  card.evidence = [...card.evidence, ...more];
  // The server folds the sources past chips_max behind "Show {n} more sources", so the shot's card does too.
  card.folded = Math.max(0, card.evidence.length - card.chips_max);
};
const pageTwo = (body: Record<string, any>) => Object.assign(body, { page: 2, pages: 3, total: 18, from: 9, to: 10 });
const decidedAs = (outcome: string, version: number | null) => (body: Record<string, any>) => {
  // A change or a retirement leaves the version before it on record, as the server's outcome says.
  body.outcome = { ...body.outcome, outcome, version, previous_version: version && version > 1 ? version - 1 : null };
  const decided = body.history.findLast((event: { event: string }) => event.event === "decided");
  if (decided) {
    decided.outcome = { added: "add", merged: "repeat", rejected: "reject", changed: "change", retired_wrong: "retire_wrong", retired_outdated: "retire_outdated" }[outcome];
    // The history names the version the outcome names, so the record agrees with itself (ticket 60).
    if (version !== null) decided.version = version;
  }
};
const summaryAs = (status: string) => (body: Record<string, any>) => {
  body.summary = status === "nothing_survived"
    ? { ...body.summary, status, sentences: [], removed: [...body.summary.removed, ...body.summary.sentences.map((s: { index: number; text: string }) => ({ index: s.index, sentence: s.text, reason: "id_not_returned", reasons: [{ check: 2, code: "id_not_returned", text: null }] }))] }
    : { status };
};
const barred = (code: string, values: Record<string, string>) => (body: Record<string, any>) => {
  body.can = { act: null, reason_code: code, values };
  body.read_only = true;
};

const LESSON_SHOTS: Shot[] = [
  // The frame and the library.
  lessonShot("library", "/lessons", LIBRARY),
  lessonShot("library-viewer", "/lessons", { "/api/lessons/page": { recorded: "lessons-page.json" } }, {}, NOT_A_REVIEWER),
  lessonShot("library-loading", "/lessons", LIBRARY, { pending: ["/api/lessons/page"] }),
  lessonShot("library-empty-viewer", "/lessons", { "/api/lessons/page": { recorded: "lessons-page-empty.json" } }, {}, NOT_A_REVIEWER),
  lessonShot("library-empty-reviewer", "/lessons", { "/api/lessons/page": { recorded: "lessons-page-empty.json" } }),
  lessonShot("library-page-2", "/lessons?page=2", { "/api/lessons/page": libraryWith("lessons-page-reviewer.json", pageTwo) }),
  lessonShot("library-error", "/lessons", { "/api/lessons/page": { status: 503, body: SERVICE_DOWN } }),
  lessonShot("library-rechecking", "/lessons", { "/api/lessons/page": libraryWith("lessons-page-reviewer.json", (library) => Object.assign(library.lessons[0], { state: "rechecking", rechecking_since: "2026-10-28" })) }),
  lessonShot("card-many-sources", "/lessons", { "/api/lessons/page": libraryWith("lessons-page-reviewer.json", manySources) }),
  lessonShot("card-many-sources-open", "/lessons", { "/api/lessons/page": libraryWith("lessons-page-reviewer.json", manySources) }, { full: true, act: click("[data-library] [data-source-chips] button") }),
  // Ticket 39's states, at 1440 px until the design pass (the user's rule of October 25, 2026): the whole page, a
  // first visit, nothing new, a lesson retired as wrong, and a draft row's notice with the bar's hold. Ticket 102: the
  // whole page and a first visit at 1440, 1024 and 390 px, with the digest as the finding and the zones in order.
  lessonShot("page", "/lessons", { "/api/lessons/page": { recorded: "lessons-page.json" } }, {}, NOT_A_REVIEWER),
  lessonShot("page-first-visit", "/lessons", { "/api/lessons/page": { recorded: "lessons-page-first.json" } }, {}, NOT_A_REVIEWER),
  lessonShot("page-nothing-new", "/lessons", { "/api/lessons/page": { recorded: "lessons-page-nothing.json" } }, { widths: [1440] }, NOT_A_REVIEWER),
  lessonShot("page-retired", "/lessons", { "/api/lessons/page": { recorded: "lessons-page-retired.json" } }, { widths: [1440] }, NOT_A_REVIEWER),
  lessonShot("draft-notice", "/drafts/draft-0001", { "/api/drafts/draft-0001": { recorded: "drafts-lesson-retired.json" }, "/api/drafts/existing": { body: '{"draft":null}' } }, { widths: [1440] }, NOT_A_REVIEWER),
  lessonShot("recheck-open", "/lessons", LIBRARY, { full: true, act: click("[data-recheck=closed] button") }),
  lessonShot("recheck-empty", "/lessons", LIBRARY, { full: true, act: async (page) => {
    await click("[data-recheck=closed] button")(page);
    await click("[data-recheck=open] button[type=submit]")(page);
  } }),
  lessonShot("recheck-saving", "/lessons", LIBRARY, { full: true, pending: ["/api/lessons/lesson-e903b07ad1/recheck"], act: async (page) => {
    await click("#lesson-lesson-e903b07ad1 [data-recheck=closed] button")(page);
    await type("#lesson-lesson-e903b07ad1 textarea", "The 2025 Procurement Regulations changed how cost estimates are prepared.")(page);
    await click("#lesson-lesson-e903b07ad1 button[type=submit]")(page);
  } }),
  lessonShot("recheck-saved", "/lessons", { ...LIBRARY, "/api/lessons/lesson-e903b07ad1/recheck": { recorded: "lessons-act-recheck.json" } }, { full: true, act: async (page) => {
    await click("#lesson-lesson-e903b07ad1 [data-recheck=closed] button")(page);
    await type("#lesson-lesson-e903b07ad1 textarea", "The 2025 Procurement Regulations changed how cost estimates are prepared.")(page);
    await click("#lesson-lesson-e903b07ad1 button[type=submit]")(page);
  } }),
  lessonShot("recheck-already", "/lessons", { ...LIBRARY, "/api/lessons/lesson-e903b07ad1/recheck": refusal("lessons-act-recheck-open.json") }, { full: true, act: async (page) => {
    await click("#lesson-lesson-e903b07ad1 [data-recheck=closed] button")(page);
    await type("#lesson-lesson-e903b07ad1 textarea", "Check it against the new rules.")(page);
    await click("#lesson-lesson-e903b07ad1 button[type=submit]")(page);
  } }),
  lessonShot("drawer-from-chip", "/lessons", LIBRARY, { widths: WIDE, act: click("#lesson-lesson-e903b07ad1 [data-source-chip] >> nth=0") }),
  // Ticket 102: the reviewer pages are the sidebar's items under Lessons, with the count in a badge, shown with the
  // sidebar opened, and an item's focus and hover; below 1024 px they sit in the Menu sheet.
  lessonShot("sidebar-items", "/lessons", LIBRARY, { widths: WIDE, full: true, act: click("[data-sidebar-toggle]") }),
  lessonShot("focus-sidebar-item", "/lessons", LIBRARY, { widths: WIDE, act: then(click("[data-sidebar-toggle]"), focus("[data-sub-item=lessonsQueue]")) }),
  lessonShot("hover-sidebar-item", "/lessons", LIBRARY, { widths: WIDE, act: then(click("[data-sidebar-toggle]"), hover("[data-sub-item=lessonsQueue]")) }),
  lessonShot("menu-sidebar-items", "/lessons", LIBRARY, { widths: NARROW, act: click("[aria-controls][aria-expanded]:not([aria-haspopup])") }),
  lessonShot("focus-chip", "/lessons", LIBRARY, { act: focus("[data-source-chip]") }),
  lessonShot("library-320", "/lessons", LIBRARY, { widths: [320] }),

  // Waiting for review.
  lessonShot("queue", "/lessons/review", QUEUE("lessons-queue.json")),
  lessonShot("queue-lead", "/lessons/review", QUEUE("lessons-queue-lead.json")),
  lessonShot("queue-own-project", "/lessons/review", QUEUE("lessons-queue-own-project.json")),
  lessonShot("queue-same-person", "/lessons/review", QUEUE("lessons-queue-same-person.json")),
  lessonShot("queue-recheck", "/lessons/review", QUEUE("lessons-queue-recheck.json")),
  lessonShot("queue-overdue", "/lessons/review", QUEUE("lessons-queue-overdue.json")),
  lessonShot("queue-cross-check", "/lessons/review", QUEUE("lessons-queue-cross-check.json"), {}, { recorded: "lessons-me-wanjiru.json" }),
  lessonShot("queue-empty-with-decisions", "/lessons/review", QUEUE("lessons-queue-decided.json")),
  lessonShot("queue-loading", "/lessons/review", QUEUE("lessons-queue.json"), { pending: ["/api/lessons/review?page=1"] }),
  lessonShot("queue-error", "/lessons/review", { "/api/lessons/review": { status: 503, body: SERVICE_DOWN } }),
  lessonShot("queue-no-access", "/lessons/review", { "/api/lessons/review": refusal("lessons-queue-no-access.json") }, {}, NOT_A_REVIEWER),
  lessonShot("queue-decided-drawer-1024", "/lessons/review", QUEUE("lessons-queue-decided.json"), { widths: [1024], act: async (page) => {
    await page.goto(`${process.env.STRATA_CAPTURE_APP_URL}/lessons/review?evidence=strata.gold.passage:31525018/v1/54`);
    await page.waitForTimeout(600);
  } }),
  lessonShot("queue-hover-row", "/lessons/review", QUEUE("lessons-queue.json"), { widths: WIDE, act: hover("[data-queue-row] h3 a") }),
  lessonShot("queue-focus-row", "/lessons/review", QUEUE("lessons-queue.json"), { act: focus("[data-queue-row] h3 a") }),
  lessonShot("queue-num-tooltip", "/lessons/review", QUEUE("lessons-queue.json"), { act: focus("[data-queue-row] [data-num]") }),
  lessonShot("queue-320", "/lessons/review", QUEUE("lessons-queue-overdue.json"), { widths: [320] }),

  // The review page, a new lesson.
  review("recommend", REB, "lessons-item-recommend.json"),
  review("recommend-repeats", PERM, "lessons-item-recommend-repeats.json"),
  review("recommend-repeat-chosen", PERM, "lessons-item-recommend-repeats.json", { full: true, act: choose("No, it repeats") }),
  review("decide", REB, "lessons-item-decide.json"),
  review("decide-editor", REB, "lessons-item-decide.json", { full: true, act: click("[data-decision-form] button[aria-expanded]") }),
  review("decide-editor-errors", REB, "lessons-item-decide.json", { full: true, act: async (page) => {
    await click("[data-decision-form] button[aria-expanded]")(page);
    await page.locator("[data-lesson-editor] textarea").fill("");
    await click("[data-decision-form] button:has-text('Add to the library')")(page);
  } }),
  review("decide-repeats", PERM, "lessons-item-decide-repeats.json"),
  review("ieg-lesson", IEG, "lessons-item-ieg-lesson.json"),
  review("errors", REB, "lessons-item-recommend.json", { full: true, act: click("[data-decision-form] button:has-text('Recommend adding it')") }),
  review("repeats-no-choice", PERM, "lessons-item-recommend-repeats.json", { full: true, act: fillReason("It gives the same advice.", "Recommend adding it") }),
  review("saving", REB, "lessons-item-recommend.json", { full: true, pending: [`${itemApi(REB)}/recommend`], act: fillReason("The ICR and IEG's review both say it.", "Recommend adding it") }),
  review("recommended", REB, "lessons-item-recommend.json", { full: true, act: fillReason("The ICR and IEG's review both say it.", "Recommend adding it") }, { [`${itemApi(REB)}/recommend`]: { recorded: "lessons-act-recommended.json" } }),
  review("added", REB, "lessons-item-decide.json", { full: true, act: fillReason("Two reports state it.", "Add to the library") }, { [`${itemApi(REB)}/decide`]: { recorded: "lessons-act-added.json" } }),
  review("merged", PERM, "lessons-item-decide-repeats.json", { full: true, act: async (page) => {
    await choose("No, it repeats")(page);
    await fillReason("More evidence for IEG's lesson.", "Add to the library")(page);
  } }, { [`${itemApi(PERM)}/decide`]: { recorded: "lessons-act-merged.json" } }),
  review("rejected", REB, "lessons-item-decide.json", { full: true, act: fillReason("Too general to act on.", "Reject, with a reason") }, {
    [`${itemApi(REB)}/decide`]: { body: derived("lessons-act-added.json", (body) => decidedAs("rejected", null)(body.item)) },
  }),
  review("stale", REB, "lessons-item-recommend.json", { full: true, act: fillReason("Too general to act on.", "Recommend rejecting it") }, { [`${itemApi(REB)}/recommend`]: refusal("lessons-act-stale.json") }),
  review("refused", REB, "lessons-item-decide.json", { full: true, act: fillReason("It reads well.", "Add to the library") }, { [`${itemApi(REB)}/decide`]: refusal("lessons-act-refused-own-project.json") }),
  review("failed", REB, "lessons-item-recommend.json", { full: true, act: fillReason("The ICR and IEG's review both say it.", "Recommend adding it") }, { [`${itemApi(REB)}/recommend`]: { status: 503, body: SERVICE_DOWN } }),
  review("lost-role", REB, "lessons-item-recommend.json", { full: true, act: fillReason("The ICR and IEG's review both say it.", "Recommend adding it") }, { [`${itemApi(REB)}/recommend`]: { status: 403, body: '{"code":"not_a_reviewer","values":{}}' } }),
  // Why you can't act: all six reasons.
  review("same-person", PERM, "lessons-item-same-person.json"),
  review("own-project", REB, "lessons-item-own-project.json"),
  review("same-region", CROSS_ITEM, "lessons-item-same-region.json"),
  reviewWith("other-region", REB, "lessons-item-own-project.json", barred("other_region", { region: "South Asia" })),
  reviewWith("not-a-lead", REB, "lessons-item-decide.json", barred("not_a_lead", {})),
  reviewWith("no-lead-free", REB, "lessons-item-decide.json", barred("no_lead_free", { region: "South Asia", project_name: "Rajasthan Road Sector Modernization Project", pid: "P130164" })),
  // The evidence badges and the IEG notes.
  reviewWith("badge-awaiting", REB, "lessons-item-recommend.json", (body) => {
    body.ieg_status = "awaiting";
    body.ieg_note = { kind: "awaiting" };
    body.evidence = body.evidence.slice(0, 1);
  }),
  // The summary in each of its states.
  review("summary-writing", RECHECK_ITEM, "lessons-item-recheck-recommend.json"),
  reviewWith("summary-nothing", REB, "lessons-item-recommend.json", summaryAs("nothing_to_add")),
  reviewWith("summary-none-survived", REB, "lessons-item-recommend.json", summaryAs("nothing_survived")),
  reviewWith("summary-failed", REB, "lessons-item-recommend.json", summaryAs("failed")),
  reviewWith("summary-rewriting", REB, "lessons-item-recommend.json", summaryAs("failed"), { full: true, pending: [`${itemApi(REB)}/summary`], act: click("[data-summary=failed] button") }),
  // Re-checks and cross-checks.
  review("recheck-recommend", RECHECK_ITEM, "lessons-item-recheck-recommend.json"),
  review("recheck-change", RECHECK_ITEM, "lessons-item-recheck-recommend.json", { full: true, act: choose("Change its wording or tags") }),
  review("recheck-decide", RECHECK_ITEM, "lessons-item-recheck-decide.json"),
  review("recheck-decide-keep", RECHECK_ITEM, "lessons-item-recheck-decide.json", { full: true, act: choose("Keep it as it is") }),
  review("recheck-decide-change", RECHECK_ITEM, "lessons-item-recheck-decide.json", { full: true, act: choose("Change its wording or tags") }),
  review("recheck-decide-retire", RECHECK_ITEM, "lessons-item-recheck-decide.json", { full: true, act: choose("Retire it, because it was wrong") }),
  review("cross-check", CROSS_ITEM, "lessons-item-cross-check.json"),
  review("cross-check-disagree-error", CROSS_ITEM, "lessons-item-cross-check.json", { full: true, act: async (page) => {
    await choose("No, I disagree")(page);
    await click("[data-decision-form] button:has-text('Save the cross-check')")(page);
  } }),
  // Decided records.
  review("decided-added", REB, "lessons-item-decided-added.json"),
  review("decided-merged", PERM, "lessons-item-decided-merged.json"),
  // A re-check that kept the lesson as it was: its record names the version it stayed at.
  review("decided-kept", RECHECK_ITEM, "lessons-item-decided-kept.json"),
  reviewWith("decided-rejected", REB, "lessons-item-decided-added.json", decidedAs("rejected", null)),
  // A change or a retirement is decided on a lesson that already has a version: the kept re-check's record (ticket 60).
  reviewWith("decided-changed", RECHECK_ITEM, "lessons-item-decided-kept.json", decidedAs("changed", 2)),
  reviewWith("decided-retired", RECHECK_ITEM, "lessons-item-decided-kept.json", decidedAs("retired_wrong", 2)),
  // Loading, not found, errors and no access.
  review("loading", REB, "lessons-item-recommend.json", { pending: [itemApi(REB)] }),
  item("new-0000000000", refusal("lessons-item-not-found.json"), {}, {}, REVIEWER, "review--not-found"),
  item(REB, { status: 503, body: SERVICE_DOWN }, {}, {}, REVIEWER, "review--error"),
  item(REB, refusal("lessons-item-no-access.json"), {}, {}, NOT_A_REVIEWER, "review--no-access"),
  // The drawer from an evidence card's marker, and focus.
  review("drawer", REB, "lessons-item-recommend.json", { act: click("[data-lesson-evidence] [data-citation] >> nth=0") }),
  // The writer's sentence under a likely repeat cites the library lesson: the drawer names it by its statement.
  review("repeats-lesson-drawer", PERM, "lessons-item-recommend-repeats.json", { act: click("[data-repeats] [data-citation] >> nth=0") }),
  review("focus-marker", REB, "lessons-item-recommend.json", { act: focus("[data-lesson-evidence] [data-citation]") }),
  review("focus-radio", PERM, "lessons-item-recommend-repeats.json", { act: focus("[data-decision-form] input[type=radio]") }),
  review("hover-primary", REB, "lessons-item-recommend.json", { widths: WIDE, act: hover("[data-decision-form] [data-button=primary]") }),
  review("320", REB, "lessons-item-decide.json", { widths: [320] }),
];

// Ticket 12: the package workspace for KE-NWWDA-541055-CW-RFB, in every state the 12 brief lists, with
// its two /api reads answered from the recordings. A state the fixture cannot reach, such as a plan row
// with no planned dates, is the recorded answer with one value changed, so it still shows real rows.
const PACKAGE = "/packages/KE-NWWDA-541055-CW-RFB";
const PACKAGE_API = "/api/packages/KE-NWWDA-541055-CW-RFB";
const COMPARABLES_API = `${PACKAGE_API}/comparables`;
const COMPARABLES = "comparables-ke-nwwda-541055.json";
const comparables = (name: string): Answer => ({ recorded: name });
const noPlanDates = derived(COMPARABLES, (body) => {
  body.plan = null;
  body.frequencies.plan = null;
  body.package.planned_notice_on = null;
  body.package.planned_signing_on = null;
});
function packageShot(name: string, answer: Answer | null, rest: Partial<Shot> = {}, pkg: Answer | null = { recorded: "package-ke-nwwda-541055.json" }, path = PACKAGE): Shot {
  const api = `/api${path}`;
  const answers: Record<string, Answer> = { ...app(name, path).api, ...(rest.api ?? {}) };
  if (pkg) answers[api] = pkg;
  if (answer) answers[`${api}/comparables`] = answer;
  // Section 3 (ticket 30): the fixture's Kenya comparables reach no completion report.
  answers[`${api}/risks`] = { recorded: "risks-ke-nwwda-541055.json" };
  // Section 2 (ticket 27): on the fixture every step abstains.
  answers[`${api}/steps`] = { recorded: "steps-ke-nwwda-541055.json" };
  // Lane 2 (ticket 26): the demo package lies outside what the fixture's model learned from, so lane 2 says so.
  if (path === PACKAGE) answers[`${api}/estimate`] = { recorded: "estimate-ke-nwwda-541055.json" };
  // Section 5, "Check your criteria" (ticket 31), collapsed under section 1, as the server answered on the fixture.
  if (path === PACKAGE) {
    answers[`${api}/criteria`] = { recorded: "criteria-summary-ke-nwwda-541055.json" };
    answers[`${api}/criteria/run`] = { recorded: "criteria-run-ke-nwwda-541055.sse" };
  }
  const pending = [...(pkg ? [] : [api]), ...(answer ? [] : [`${api}/comparables`]), ...(rest.pending ?? [])];
  return app(name, path, {}, { ...rest, api: answers, pending });
}
const wideAndNarrow = [1440, 390];
// The chart's dots answer the pointer by distance, so the mouse goes to the dot's centre.
const hoverDot = (index: number) => async (page: Page) => {
  const dot = page.locator(`[data-dot-target='${index}']`);
  await dot.scrollIntoViewIfNeeded();
  const box = (await dot.boundingBox())!;
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
  await page.waitForTimeout(250);
};

// The bottom dot of the tallest column at this width, hovered, then the pointer moved straight up onto
// its tooltip, 2 px every 16 ms, over the dots stacked above it.
const crossToTip = async (page: Page) => {
  await page.locator("[data-range-chart]").scrollIntoViewIfNeeded();
  const from = await page.evaluate(() => {
    const columns = new Map<number, DOMRect[]>();
    document.querySelectorAll<HTMLElement>("[data-dot-target]").forEach((dot) => {
      const box = dot.getBoundingClientRect();
      const x = Math.round(box.x + box.width / 2);
      columns.set(x, [...(columns.get(x) ?? []), box]);
    });
    const bottom = [...columns.values()].sort((a, b) => b.length - a.length)[0].sort((a, b) => b.y - a.y)[0];
    return { x: bottom.x + bottom.width / 2, y: bottom.y + bottom.height / 2 };
  });
  await page.mouse.move(from.x, from.y);
  await page.waitForTimeout(100);
  const box = (await page.locator("[data-dot-tooltip]").boundingBox())!;
  const to = { x: Math.min(Math.max(from.x, box.x + 4), box.x + box.width - 4), y: box.y + box.height - 2 };
  const steps = Math.ceil(Math.hypot(to.x - from.x, to.y - from.y) / 2);
  for (let step = 1; step <= steps; step += 1) {
    await page.mouse.move(from.x + ((to.x - from.x) * step) / steps, from.y + ((to.y - from.y) * step) / steps);
    await page.waitForTimeout(16);
  }
  await page.waitForTimeout(400);
};
const focusReset = async (page: Page) => {
  await page.locator("[data-plan-control] input").fill("6");
  await page.locator("[data-plan-reset] button:visible").focus();
  await page.waitForTimeout(250);
};

// Ticket 31: section 5 of the package workspace, "Check your criteria", on a works package whose comparables
// published no qualification criteria (KE-NWWDA-541055-CW-RFB) and on a consultant services package whose
// comparables did (KE-CWSB-224323-CS-QCBS), each answered as the server answered on the fixture
// (tests/record_criteria_api.py). The section's other states are on the gallery's check-criteria page.
const CONSULTANT = "/packages/KE-CWSB-224323-CS-QCBS";
const CONSULTANT_API = "/api/packages/KE-CWSB-224323-CS-QCBS";
const PASTED =
  "1. Similar experience: at least two contracts of similar works of US$10 million each.\n" +
  "2. Average annual turnover: US$25 million over the last three years.\n" +
  "3. The bid must be signed by a person with a power of attorney.";
function criteriaShot(name: string, rest: Partial<Shot> = {}, compare = "criteria-compare-similar-experience.sse", path = CONSULTANT): Shot {
  const api = `/api${path}`;
  const slug = path === CONSULTANT ? "ke-cwsb-224323" : "ke-nwwda-541055";
  // Section 3 (ticket 30) sits above section 5: the works package's risks as recorded; the consultant package has
  // no recorded risks, so its section 3 stays loading rather than showing an error the server never gave.
  const risks = path === CONSULTANT ? [`${api}/risks`] : [];
  return app(`criteria--${name}`, path, {}, {
    ...rest,
    pending: [...risks, ...(rest.pending ?? [])],
    api: {
      ...(path === CONSULTANT ? {} : { [`${api}/risks`]: { recorded: "risks-ke-nwwda-541055.json" } }),
      ...app(name, path).api,
      [api]: { recorded: `package-${slug}.json` },
      [`${api}/comparables`]: { recorded: `comparables-${slug}.json` },
      [`${api}/criteria`]: { recorded: `criteria-summary-${slug}.json` },
      [`${api}/criteria/run`]: { recorded: `criteria-run-${slug}.sse` },
      [`${api}/criteria/compare`]: { recorded: compare },
      "/api/evidence/opened": OPENED,
      "/api/evidence": { recorded: "evidence-award-notice-op00125282.json" },
      ...rest.api,
    },
  });
}
const openCheck = click("#check-criteria [data-section-toggle]");
const compareCriteria = then(openCheck, async (page) => {
  await page.locator("#check-criteria textarea").fill(PASTED);
  await page.locator("#check-criteria [data-compare]").click();
  await page.locator("#check-criteria :is([data-criteria-notes], [data-refusal], [data-none-found])").first().waitFor();
});
const CRITERIA_SHOTS: Shot[] = [
  criteriaShot("collapsed"),
  criteriaShot("collapsed-none-public", {}, undefined, PACKAGE),
  criteriaShot("collapsed-loading", { pending: [`${CONSULTANT_API}/criteria`] }),
  criteriaShot("works-open", { full: true, act: openCheck }, undefined, PACKAGE),
  criteriaShot("open-before-comparing", { full: true, act: openCheck }),
  criteriaShot("run-in-progress", { full: true, act: openCheck, pending: [`${CONSULTANT_API}/criteria/run`] }),
  criteriaShot("compared", { full: true, act: compareCriteria }),
  criteriaShot("live-tender-refused", { full: true, act: compareCriteria }, "criteria-compare-live-tender.sse"),
  criteriaShot("partial-refusal", { full: true, act: compareCriteria }, "criteria-compare-partial-refusal.sse"),
  criteriaShot("none-found", { full: true, act: compareCriteria }, "criteria-compare-none-found.sse"),
  criteriaShot("empty-on-press", { act: then(openCheck, click("#check-criteria [data-compare]")) }),
  criteriaShot("focus-toggle", { act: focus("#check-criteria [data-section-toggle]") }),
  criteriaShot("focus-textarea", { act: then(openCheck, focus("#check-criteria textarea")) }),
  criteriaShot("hover-count", { widths: WIDE, act: then(compareCriteria, hover("#check-criteria [data-same-or-less] [data-num]:visible")) }),
  criteriaShot("drawer-item", { act: then(compareCriteria, click("#check-criteria [data-same-or-less] [data-num]:visible")) }),
  criteriaShot("drawer-public", { act: then(openCheck, click("#check-criteria [data-summary-text] [data-num]")) }),
  criteriaShot("hover-cost-dot", { widths: WIDE, act: then(openCheck, hover("[data-cost-dot] >> nth=0")) }, undefined, PACKAGE),
  criteriaShot("focus-cost-dot", { act: then(openCheck, focus("[data-cost-dot] >> nth=0")) }, undefined, PACKAGE),
  criteriaShot("drawer-cost", { act: then(openCheck, click("[data-cost-row]:visible >> nth=0")) }, undefined, PACKAGE),
  criteriaShot("drawer-award-notice", { act: then(openCheck, click("[data-rejected-row] [data-citation] >> nth=0")) }, undefined, PACKAGE),
  criteriaShot("focus-marker", { act: then(openCheck, focus("[data-lesson-card] [data-citation]")) }, undefined, PACKAGE),
  criteriaShot("320", { widths: [320], full: true, act: compareCriteria }),
  criteriaShot("works-320", { widths: [320], full: true, act: openCheck }, undefined, PACKAGE),
  criteriaShot("review-decisions-refused", { full: true, act: compareCriteria }, "criteria-compare-review-decisions.sse"),
  criteriaShot("focus-intro-count", { act: then(openCheck, focus("#check-criteria [data-criteria-intro] [data-num]")) }),
  // A reading check 4's judge said does not follow: removed in its place, its reason in the box above.
  criteriaShot("reading-removed", { full: true, act: compareCriteria }, "criteria-compare-swapped-reading.sse"),
  // Ticket 60: the judge did not respond, so the removed box says the cause once and offers Try again.
  criteriaShot("readings-unjudged", { full: true, act: compareCriteria }, "criteria-compare-swapped-reading-no-judge.sse"),
  // View C with the requirement highlighted, and view F with the lesson's words highlighted and its IEG line.
  criteriaShot("drawer-notice", {
    api: { "/api/evidence": { recorded: "evidence-passage-op00077276-s3.json" } },
    act: then(compareCriteria, click("#check-criteria [data-same-or-less] [data-num]:visible"), click("[role=dialog] [data-entry='strata.gold.passage:OP00077276/v1/s3']")),
  }),
  criteriaShot("drawer-lesson", {
    api: { "/api/evidence": { recorded: "evidence-icr-p130164-54.json" } },
    act: then(openCheck, click("[data-lesson-card] [data-citation]")),
  }, undefined, PACKAGE),
];

// Ticket 28: section 1's "Advertised again" block on the demo package. The fixture's answers are the server's
// (tests/record_rebidding_api.py): three of the 52 comparable packages, and with review type Prior, none of 7. The
// model shown and the model that did no better are mocks (rebidding-mock-*.json), labeled as such. The other states
// are in the gallery (/gallery/rebidding).
function rebidShot(name: string, rebidding: Answer | null, rest: Partial<Shot> = {}, comparables = "comparables-ke-nwwda-541055.json"): Shot {
  const answers: Record<string, Answer> = {
    ...app(name, RISKS_PATH).api,
    [RISKS_API]: { recorded: "package-ke-nwwda-541055.json" },
    [`${RISKS_API}/comparables`]: { recorded: comparables },
    [`${RISKS_API}/risks`]: { recorded: "risks-ke-nwwda-541055.json" },
    [`${RISKS_API}/criteria`]: { recorded: "criteria-summary-ke-nwwda-541055.json" },
    "/api/evidence": { recorded: "evidence-notice-op00083890.json" },
    "/api/evidence/opened": { body: '{"opened":[],"recorded":true}' },
    ...rest.api,
  };
  if (rebidding) answers[`${RISKS_API}/rebidding`] = rebidding;
  return app(`rebidding--${name}`, RISKS_PATH, {}, { full: true, ...rest, api: answers, pending: rebidding ? rest.pending : [`${RISKS_API}/rebidding`] });
}
const REBID: Answer = { recorded: "rebidding-ke-nwwda-541055.json" };
const REBID_SHOWN: Answer = { recorded: "rebidding-mock-model-shown.json" };
const toRebid = async (page: Page) => {
  await page.locator("[data-rebidding]").scrollIntoViewIfNeeded();
  await page.waitForTimeout(250);
};
const openReasons = click("[data-rebid-disclosure]");
const REBID_SHOTS: Shot[] = [
  rebidShot("fixture", REBID, { act: toRebid }),
  rebidShot("fixture-open", REBID, { act: openReasons }),
  rebidShot("under-20", { recorded: "rebidding-ke-nwwda-541055-prior.json" }, { act: toRebid }, "comparables-ke-nwwda-541055-prior.json"),
  rebidShot("model-shown", REBID_SHOWN, { act: openReasons }),
  rebidShot("not-better", { recorded: "rebidding-mock-not-better.json" }, { act: toRebid }),
  rebidShot("loading", null, { act: toRebid }),
  rebidShot("error", { status: 503, body: '{"code":"data_service","trace_id":"0af7651916cd43dd8448eb211c80319c"}' }, { act: toRebid }),
  rebidShot("drawer-notice", REBID, { act: then(openReasons, click("[data-rebidding] [data-citation-id='strata.silver.notices:OP00083890']")) }),
  rebidShot("drawer-plan-row", REBID, {
    api: { "/api/evidence": { recorded: "evidence-plan-row-ke-kimawasco-157517.json" } },
    act: then(openReasons, click("[data-rebidding] [data-citation] >> nth=0")),
  }),
  rebidShot("drawer-two-notices", REBID_SHOWN, {
    api: { "/api/evidence": { recorded: "evidence-mock-notice-op90000011.json" } },
    act: then(openReasons, click("[data-rebidding] [data-citation-id='strata.silver.notices:OP90000011']")),
  }),
  rebidShot("drawer-award-notice", REBID_SHOWN, {
    api: { "/api/evidence": { recorded: "evidence-mock-award-notice-op90000006.json" } },
    act: then(openReasons, click("[data-rebidding] [data-citation] >> nth=0")),
  }),
  rebidShot("show-more", REBID_SHOWN, { act: then(openReasons, click("[data-rebid-group=all_bids_rejected] [data-button=ghost]")) }),
  rebidShot("hover-marker", REBID, { full: false, widths: WIDE, act: then(openReasons, hover("[data-rebidding] [data-citation]")) }),
  rebidShot("focus-marker", REBID, { full: false, act: then(openReasons, focus("[data-rebidding] [data-citation]")) }),
  rebidShot("focus-disclosure", REBID, { full: false, act: focus("[data-rebid-disclosure]") }),
  rebidShot("focus-step-ref", REBID, { full: false, act: then(openReasons, focus("[data-rebidding] [data-step-ref]")) }),
  rebidShot("hover-count", REBID, { full: false, widths: WIDE, act: hover("[data-rebid-count] button") }),
  rebidShot("focus-count", REBID, { full: false, act: focus("[data-rebid-count] button") }),
  rebidShot("320", REBID_SHOWN, { widths: [320], act: openReasons }),
];

// Lane 2 drawn in full (ticket 26): KE-NWWDA-229129-CW-RFB, estimated at US$300,000, lies inside what the fixture's
// model learned from (tests/record_estimate_api.py). The fixture offers no comparison and no track record, so the
// comparing shot adds one comparison to the recorded answer, over the first 22 of its comparable packages.
const SIGNED_PACKAGE = "/packages/KE-NWWDA-229129-CW-RFB";
const comparingEstimate = (() => {
  const rows = JSON.parse(readFileSync(new URL("comparables-ke-nwwda-229129.json", RECORDED), "utf8")).rows as { step_reference: string }[];
  return derived("estimate-ke-nwwda-229129.json", (body) => {
    const e = body.estimate;
    const n = body.comparables.n;
    const matching = rows.slice(0, 22).map((row) => row.step_reference);
    const shifted = { q25: e.q25 + 1, q50: e.q50 + 1, q75: e.q75 + 1, q80: e.q80 + 1 };
    body.comparisons = [{ lever: "prequalification", value: "Y", own: "N", k: 22, rest: n - 22, n, matching_ids: matching, unrecorded_ids: [], estimate: { ...shifted, days: null }, abstention: null }];
    body.axis_max_months = shifted.q80;
  });
})();
function timeEstimateShot(name: string, estimate: Answer, rest: Partial<Shot> = {}): Shot {
  const api = `/api${SIGNED_PACKAGE}`;
  return app(`package--${name}`, SIGNED_PACKAGE, {}, {
    widths: [1440],
    ...rest,
    api: {
      ...app(name, SIGNED_PACKAGE).api,
      [api]: { recorded: "package-ke-nwwda-229129.json" },
      [`${api}/comparables`]: { recorded: "comparables-ke-nwwda-229129.json" },
      [`${api}/risks`]: { recorded: "risks-ke-nwwda-229129.json" },
      [`${api}/estimate`]: estimate,
    },
    pending: [`${api}/steps`, `${api}/criteria`, `${api}/rebidding`],
  });
}

const PACKAGE_SHOTS: Shot[] = [
  timeEstimateShot("time-estimate", { recorded: "estimate-ke-nwwda-229129.json" }),
  timeEstimateShot("time-estimate-comparing", { body: comparingEstimate }, { full: true, act: click("[data-segmented=toggle] button >> nth=0") }),
  packageShot("package", comparables(COMPARABLES)),
  packageShot("package--loading", null, {}, null),
  packageShot("package--section-loading", null),
  // Ticket 59, round 3: the time estimate held alone. Section 1 draws no Compare with row, and the held-back estimate's
  // sentences keep their places, unseen, under the chart and at the end of the summary.
  packageShot("package--estimate-loading", comparables(COMPARABLES), { pending: [`/api${PACKAGE}/estimate`] }),
  packageShot("package--no-plan-dates", { body: noPlanDates }),
  packageShot("package--quantile-dots", comparables("comparables-ke-nwwda-541055-any-category.json")),
  packageShot("package--abstention", comparables("comparables-ke-nwwda-541055-prior.json")),
  packageShot("package--no-match", comparables("comparables-ke-nwwda-541055-india.json")),
  packageShot("package--none-measurable", comparables("comparables-ke-nwwda-541055-non-consulting.json")),
  packageShot(
    "package--not-measurable",
    comparables("comparables-ke-nwwda-541062.json"),
    {},
    { recorded: "package-ke-nwwda-541062.json" },
    "/packages/KE-NWWDA-541062-CW-RFQ",
  ),
  packageShot("package--section-error", { status: 503, body: SERVICE_DOWN }),
  // Ticket 101: the past range failed while "Advertised again" answered, which stays under the error; the plan row's
  // record in the drawer, from the side panel's marker, in the side panel's place; and "2" pressed, with the table
  // filtered to the two packages it counts.
  packageShot("package--section-error-again", { status: 503, body: SERVICE_DOWN }, {
    api: { "/api/packages/KE-NWWDA-541055-CW-RFB/rebidding": { recorded: "rebidding-ke-nwwda-541055.json" } },
  }),
  packageShot("package--drawer-plan-row", comparables(COMPARABLES), {
    widths: [1440, 1280, 1024],
    // The side panel's marker from a frame of 75rem, the facts line's "Show the plan row" below it.
    act: async (page: Page) => {
      await page.locator("[data-side-panel] [data-citation], [data-facts-line] button").filter({ visible: true }).first().click();
      await page.waitForTimeout(250);
    },
    api: { "/api/evidence": { recorded: "evidence-plan-row-ke-nwwda-541055.json" }, "/api/evidence/opened": { body: '{"opened":[],"recorded":true}' } },
  }),
  // At 1024 px too, where the filtered rows are a table (ticket 101's design review: the filtered state at three widths).
  packageShot("package--pressed-within", comparables(COMPARABLES), { widths: [1440, 1024, 390], act: click("[data-finding] button[data-num]") }),
  packageShot("package--error", null, {}, { status: 503, body: SERVICE_DOWN }),
  packageShot("package--not-found", null, {}, { status: 404, body: '{"code":"unknown_package"}' }, "/packages/KE-NWWDA-000000-CW-RFB"),
  packageShot("package--moved", comparables(COMPARABLES), { widths: wideAndNarrow, act: type("[data-plan-control] input", "6") }),
  packageShot("package--hover-dot", comparables(COMPARABLES), { widths: wideAndNarrow, act: hoverDot(20) }),
  packageShot("package--focus-dot", comparables(COMPARABLES), { widths: wideAndNarrow, act: focus("[data-dot-target='0']") }),
  // The Number tooltip of "49" in the finding, under the whole finding and left aligned with the number (ticket 96).
  packageShot("package--hover-num-finding", comparables(COMPARABLES), {
    widths: wideAndNarrow,
    act: then(
      (page) => page.locator("[data-past-range] [data-finding]").evaluate((finding) => finding.scrollIntoView({ block: "center" })),
      hover("[data-past-range] [data-finding] button[data-num] >> nth=1"),
    ),
  }),
  packageShot("package--focus-slider", comparables(COMPARABLES), { widths: wideAndNarrow, act: focus("[role=slider]") }),
  packageShot("package--invalid", comparables(COMPARABLES), { widths: wideAndNarrow, act: type("[data-plan-control] input", "90") }),
  // 1280 px is a page area where the workspace keeps to columns 1 to 8 and the table's frame is under
  // 49rem, so the table shows as cards there (DESIGN.md section 5, Tables).
  packageShot("package--table-open", comparables(COMPARABLES), { widths: [1440, 1280, 390], full: true, act: click("[data-past-range] button[aria-controls][aria-expanded]") }),
  packageShot("package--320", comparables(COMPARABLES), { widths: [320] }),
  // Round 1's fixes: months typed into a row with no plan dates, the last dot's tooltip opened first,
  // and the quantile dot past the axis, pinned at the plot's edge.
  packageShot("package--no-plan-typed", { body: noPlanDates }, { widths: wideAndNarrow, act: type("[data-plan-control] input", "6") }),
  packageShot("package--hover-last-dot", comparables(COMPARABLES), { widths: wideAndNarrow, act: hoverDot(48) }),
  packageShot("package--quantile-last-dot", comparables("comparables-ke-nwwda-541055-any-category.json"), { widths: wideAndNarrow, act: hoverDot(19) }),
  packageShot("package--moved-320", comparables(COMPARABLES), { widths: [320], act: type("[data-plan-control] input", "9") }),
  // Round 2's fixes: the plan just past the 8-in-10 point, where its label moves or sits on its knockout,
  // and a bad number at 320 px, whose one-line error moves nothing.
  packageShot("package--plan-10", comparables(COMPARABLES), { widths: [1440, 390, 320], act: type("[data-plan-control] input", "10") }),
  packageShot("package--invalid-320", comparables(COMPARABLES), { widths: [320], act: type("[data-plan-control] input", "abc") }),
  // Round 3's fixes: the pointer on a buried dot's tooltip after crossing the dots above it, the reset
  // button's focus ring clear of "months" in the input's row, and a long reference on the not-found page.
  packageShot("package--crossed-to-tip", comparables(COMPARABLES), { widths: [1440, 1024, 390, 320], act: crossToTip }),
  packageShot("package--focus-reset", comparables(COMPARABLES), { widths: [1440, 1024, 390], act: focusReset }),
  packageShot("package--not-found-long", null, { widths: [320] }, { status: 404, body: '{"code":"unknown_package"}' }, "/packages/KE-NWWDA-541055-CW-RFB-LOT-0001-2026-ABC"),
  // Round 10's fix: the plan mid-axis on a chart just over 400 px wide, where one line of the readout
  // does not fit beside it, so the readout takes the copy's two lines.
  packageShot("package--moved-496", comparables(COMPARABLES), {
    widths: [496],
    act: async (page) => {
      await type("[data-plan-control] input", "9")(page);
      await page.locator("[data-range-chart]").scrollIntoViewIfNeeded();
    },
  }),
];

// Ticket 15: a package planned from a sentence, in the states the 15 brief's section 12 lists. The answers are
// the server's own on the fixture (tests/record_packages_api.py). A saved package after a change is the change's
// recorded answer with the schema beside it, which is what the package's page reads. The capture answers by
// path for any method, so a change posted to the package's address gets the same package back; a shot that
// needs another answer to a change sets it up in its action. Section 1's abstention and none-found states
// answer with ticket 12's recordings, since no recorded planned package has fewer than 20 comparables.
const SENTENCE = "rural roads, Kenya, about US$15 million";
const PLANNED = "/packages/pkg-000000000001";
const PLANNED_API = "/api/planned-packages/pkg-000000000001";
const PLANNED_FILE = "planned-package-rural-roads.json";
const MOWI = "strata.gold.package:KE-MOWI-47509-CW-RFB";
const ICTA = "strata.gold.package:KE-ICTA-571738-CW-RFB";
const KIMAWASCO = "strata.gold.package:KE-KIMAWASCO-149448-CW-RFB";
const read = (name: string) => JSON.parse(readFileSync(new URL(name, RECORDED), "utf8"));
// A change's recorded package as the package's page reads it, with the schema.
const changed = (name: string): Answer => ({ body: JSON.stringify({ ...read(PLANNED_FILE), package: read(name).package }) });
const PLANNED_ANSWERS: Shot["api"] = {
  "/api/comparables": { recorded: "comparables-planned-works-rfb-ke.json" },
  // Section 5 of the first planned package (ticket 31).
  [`${PLANNED_API}/criteria`]: { recorded: "criteria-summary-planned-rural-roads.json" },
  [`${PLANNED_API}/criteria/run`]: { recorded: "criteria-run-planned-rural-roads.sse" },
  "/api/evidence": { recorded: "evidence-package-ke-mowi-47509.json" },
  "/api/evidence/opened": OPENED,
  "/api/planned-packages": { recorded: "planned-packages-list.json" },
  "/api/projects/P156634": { recorded: "project-p156634.json" },
  // Section 3 (ticket 30): the rural roads package's Kenya comparables reach no completion report. The package set up
  // yourself lacks the criteria that pick comparables, and the dividing one has the rural roads package's criteria
  // (ticket 60).
  "/api/planned-packages/pkg-000000000001/risks": { recorded: "risks-planned-rural-roads.json" },
  "/api/planned-packages/pkg-000000000002/risks": { recorded: "risks-planned-yourself.json" },
  "/api/planned-packages/pkg-000000000003/risks": { recorded: "risks-planned-rural-roads.json" },
  // Section 2 (ticket 27): the rural roads package asks for its first step's date.
  "/api/planned-packages/pkg-000000000001/steps": { recorded: "steps-planned-rural-roads.json" },
};
const plannedShot = (name: string, pkg: Answer = { recorded: PLANNED_FILE }, rest: Partial<Shot> = {}, path = PLANNED, read = PLANNED_API): Shot =>
  app(name, path, {}, { ...rest, api: { ...app(name, path).api, ...PLANNED_ANSWERS, [read]: pkg, ...rest.api } });
// The Packages tab, with its list answered.
const tabShot = (name: string, list: Answer, rest: Partial<Shot> = {}, path = "/packages"): Shot =>
  app(name, path, {}, { ...rest, api: { ...app(name, path).api, ...PLANNED_ANSWERS, "/api/planned-packages": list, ...rest.api } });
// From Home, the sentence typed into the box and "Plan a package from this sentence" chosen, with the stream
// the reading page answers with.
const planFromBox = (name: string, stream: Answer | null, rest: Partial<Shot> = {}): Shot =>
  app(name, "/", {}, {
    full: true,
    ...rest,
    api: { ...app(name, "/").api, ...PLANNED_ANSWERS, [PLANNED_API]: { recorded: PLANNED_FILE }, ...(stream ? { "/api/planned-packages": stream } : {}), ...rest.api },
    pending: stream ? rest.pending : ["/api/planned-packages", ...(rest.pending ?? [])],
    act: async (page) => {
      await typeInBox(SENTENCE)(page);
      await page.locator("[data-box-option=plan]").click();
      await page.waitForTimeout(stream ? 900 : 300);
    },
  });
const openChip = (key: string, ...after: ((page: Page) => Promise<void>)[]) =>
  then(click(`[data-chip='${key}']`), ...after);
const typeInEditor = (text: string, enter = false) => async (page: Page) => {
  await page.locator("[data-chip-editor] input:not([type=radio])").first().fill(text);
  if (enter) await page.keyboard.press("Enter");
  await page.waitForTimeout(250);
};
// A change whose save the server refuses: the chip keeps its new value and the stamp says it was not saved.
const saveFails = async (page: Page) => {
  await page.route(`**${PLANNED_API}`, (route) =>
    route.request().method() === "POST" ? route.fulfill({ status: 503, contentType: "application/json", body: SERVICE_DOWN }) : route.fallback());
  await openChip("lots", typeInEditor("3", true))(page);
  await page.waitForTimeout(400);
};
// A chip that picks the comparables changed, with find_comparables still running.
const rerunning = async (page: Page) => {
  await page.route(`**${PLANNED_API}`, (route) =>
    route.request().method() === "POST"
      ? route.fulfill({ contentType: "application/json", body: readFileSync(new URL("planned-package-change-method-rfq.json", RECORDED), "utf8") })
      : route.fallback());
  await page.route("**/api/comparables**", () => undefined);
  await openChip("method", click("[data-chip-editor] label:has-text('Request for Quotations (RFQ)')"))(page);
  await page.waitForTimeout(600);
};
const withoutPlan = click("[data-plan-prompt] [data-button=ghost]");
const evidenceAt = (id: string) => `${PLANNED}?evidence=${encodeURIComponent(id)}`;
// More than 60 comparables, so 20 quantile dots: no planned package's criteria match that many on the fixture,
// so section 1 answers with ticket 12's comparables with the category left open, without its plan row's plan.
const DOTS: Answer = (() => {
  const body = read("comparables-ke-nwwda-541055-any-category.json");
  return { body: JSON.stringify({ ...body, package: null, plan: null, frequencies: { ...body.frequencies, plan: null } }) };
})();

const PLANNED_SHOTS: Shot[] = [
  // The box: free text lists the plan option second, the Packages tab's buttons put it in plan or check mode,
  // and a preview holds the option with its reason.
  plannedShot("box--plan-option", undefined, { full: false, act: typeInBox(SENTENCE) }, "/"),
  tabShot("box--plan-mode", { recorded: "planned-packages-list.json" }, { act: click("main [data-button=secondary]") }),
  tabShot("box--plan-mode-typed", { recorded: "planned-packages-list.json" }, { act: then(click("main [data-button=secondary]"), async (page) => {
    await page.keyboard.type(SENTENCE);
    await page.waitForTimeout(300);
  }) }),
  tabShot("box--check-mode", { recorded: "planned-packages-list.json" }, { act: then(click("main [data-button=primary]"), async (page) => {
    await page.keyboard.type("P156634");
    await page.waitForTimeout(400);
  }) }),
  plannedShot("box--plan-option-preview", undefined, { full: false, act: typeInBox(SENTENCE) }, "/?view=piu"),
  // The reading page, and the reading's three ends that save nothing.
  planFromBox("planned--reading", null),
  planFromBox("planned--no-package", { recorded: "package-plan-no-package.sse" }),
  planFromBox("planned--read-failed", { recorded: "package-plan-reader-unavailable.sse" }),
  planFromBox("planned--arrived", { recorded: "package-plan-rural-roads.sse" }),
  // The workspace: one guess, with the plan prompt; the guess kept; a computed chip set by you; the note after
  // a recompute; the dividing refusal; set yourself, with the criteria that pick comparables missing.
  plannedShot("planned"),
  plannedShot("planned--loading", undefined, { pending: [PLANNED_API] }),
  plannedShot("planned--guess-kept", changed("planned-package-change-keep-lots.json")),
  plannedShot("planned--set-by-you", changed("planned-package-change-review-post.json")),
  plannedShot("planned--recomputed", changed("planned-package-change-amount.json")),
  // Goods in Kenya: no market approach threshold, so the chip asks for one and the note says why it emptied.
  plannedShot("planned--emptied", changed("planned-package-change-category-goods.json"), { full: false }),
  plannedShot("planned--dividing", { recorded: "planned-package-dividing.json" }, {}, "/packages/pkg-000000000003", "/api/planned-packages/pkg-000000000003"),
  plannedShot("planned--missing", { recorded: "planned-package-yourself.json" }, {}, "/packages/pkg-000000000002", "/api/planned-packages/pkg-000000000002"),
  // Section 1: the chart with a plan and without one, updating, abstention, none found, none measurable, error.
  plannedShot("planned--with-plan", changed("planned-package-change-plan.json")),
  plannedShot("planned--without-plan", undefined, { full: true, act: withoutPlan }),
  plannedShot("planned--updating", undefined, { full: true, act: rerunning }),
  plannedShot("planned--abstention", changed("planned-package-change-plan.json"), { api: { "/api/comparables": { recorded: "comparables-ke-nwwda-541055-prior.json" } } }),
  plannedShot("planned--none-found", undefined, { api: { "/api/comparables": { recorded: "comparables-ke-nwwda-541055-india.json" } } }),
  plannedShot("planned--none-measurable", changed("planned-package-change-method-rfq.json"), { api: { "/api/comparables": { recorded: "comparables-planned-works-rfq-ke.json" } } }),
  plannedShot("planned--section-error", undefined, { api: { "/api/comparables": { status: 503, body: SERVICE_DOWN } } }),
  plannedShot("planned--save-failed", undefined, { full: true, act: saveFails }),
  // Each kind of chip editor: a popover from 768 px, a bottom sheet below.
  plannedShot("planned--editor-computed", undefined, { full: false, act: openChip("review_type") }),
  // By its words: below 768 px the sheet's close is the first ghost button.
  plannedShot("planned--editor-set-it-yourself", undefined, { full: false, act: openChip("review_type", click("[data-chip-editor] button:has-text('Set it yourself')")) }),
  plannedShot("planned--editor-method-old-name", undefined, { full: false, act: openChip("method", typeInEditor("ICB")) }),
  plannedShot("planned--editor-amount", undefined, { full: false, act: openChip("estimated_amount_usd", typeInEditor("12m")) }),
  plannedShot("planned--editor-amount-error", undefined, { full: false, act: openChip("estimated_amount_usd", typeInEditor("about fifteen", true)) }),
  plannedShot("planned--editor-country", undefined, { full: false, act: openChip("country", typeInEditor("ken")) }),
  plannedShot("planned--editor-guess", undefined, { full: false, act: openChip("lots") }),
  plannedShot("planned--editor-months", changed("planned-package-change-plan.json"), { full: false, act: openChip("plan_months") }),
  plannedShot("planned--editor-preview", undefined, { full: false, act: openChip("method") }, `${PLANNED}?view=piu`),
  // Hover and keyboard focus on a chip and a mark.
  plannedShot("planned--hover-chip", undefined, { widths: WIDE, act: hover("[data-chip='lots']") }),
  plannedShot("planned--focus-chip", undefined, { act: focus("[data-chip='market_approach']") }),
  plannedShot("planned--focus-dot", changed("planned-package-change-plan.json"), { widths: wideAndNarrow, act: focus("[data-dot-target='0']") }),
  plannedShot("planned--hover-dot", changed("planned-package-change-plan.json"), { widths: wideAndNarrow, act: hoverDot(20) }),
  // A comparable package's records in the evidence drawer: signed, still open, loading, failed, and its close
  // button focused. At 390 px it is the full-screen sheet.
  plannedShot("planned--drawer-signed", changed("planned-package-change-plan.json"), { full: false }, evidenceAt(MOWI)),
  plannedShot("planned--drawer-still-open", changed("planned-package-change-plan.json"), { full: false, api: { "/api/evidence": { recorded: "evidence-package-ke-icta-571738.json" } } }, evidenceAt(ICTA)),
  plannedShot("planned--drawer-canceled", changed("planned-package-change-plan.json"), { full: false, api: { "/api/evidence": { recorded: "evidence-package-ke-kimawasco-149448.json" } } }, evidenceAt(KIMAWASCO)),
  // The drawer reads /api/evidence?id=..., which a route for the bare path does not match.
  plannedShot("planned--drawer-loading", changed("planned-package-change-plan.json"), { full: false, pending: ["/api/evidence?id=**"] }, evidenceAt(MOWI)),
  plannedShot("planned--drawer-error", changed("planned-package-change-plan.json"), { full: false, api: { "/api/evidence": { status: 503, body: SERVICE_DOWN } } }, evidenceAt(MOWI)),
  plannedShot("planned--drawer-from-dot", changed("planned-package-change-plan.json"), { full: false, widths: WIDE, act: then(focus("[data-dot-target='0']"), async (page) => {
    await page.keyboard.press("Enter");
    await page.waitForTimeout(500);
  }) }),
  plannedShot("planned--focus-drawer-close", changed("planned-package-change-plan.json"), { full: false, act: focus("[data-evidence-drawer] [data-drawer-header] button") }, evidenceAt(MOWI)),
  // A quantile dot's packages in the drawer: the last dot, which stands for the last signed package and four
  // still open, then the signed one opened from that list, with the way back above its title.
  plannedShot("planned--drawer-dot-list", changed("planned-package-change-plan.json"), { full: false, api: { "/api/comparables": DOTS } }, evidenceAt("comparables-dot:20")),
  plannedShot("planned--drawer-dot-package", changed("planned-package-change-plan.json"), {
    full: false,
    api: { "/api/comparables": DOTS },
    act: async (page) => {
      await page.locator("[data-dot-entry='KE-MOWI-47509-CW-RFB']").click();
      await page.waitForTimeout(500);
    },
  }, evidenceAt("comparables-dot:20")),
  // The page's other states.
  plannedShot("planned--not-found", { status: 404, recorded: "planned-package-not-found.json" }, {}, "/packages/pkg-00000000000a", "/api/planned-packages/pkg-00000000000a"),
  plannedShot("planned--error", { status: 503, body: SERVICE_DOWN }),
  plannedShot("planned--preview", undefined, {}, `${PLANNED}?view=piu`),
  plannedShot("planned--public", undefined, {}, `${PLANNED}?view=public`),
  plannedShot("planned--320", undefined, { widths: [320] }),
  // The Packages tab.
  tabShot("packages-tab", { recorded: "planned-packages-list.json" }),
  tabShot("packages-tab--loading", { recorded: "planned-packages-list.json" }, { pending: ["/api/planned-packages"] }),
  tabShot("packages-tab--empty", { recorded: "planned-packages-empty.json" }),
  tabShot("packages-tab--error", { status: 503, body: SERVICE_DOWN }),
  tabShot("packages-tab--preview", { recorded: "planned-packages-list.json" }, {}, "/packages?view=piu"),
  tabShot("packages-tab--public", { recorded: "planned-packages-list.json" }, {}, "/packages?view=public"),
  tabShot("packages-tab--focus-row", { recorded: "planned-packages-list.json" }, { act: focus("main [data-table] a:visible") }),
  tabShot("packages-tab--320", { recorded: "planned-packages-list.json" }, { widths: [320] }),
];


// Ticket 24: the six checks and the refusals, as the 24 brief's section 12 lists them, each answer the stream
// its scripted case gives (tests/fixtures/agent/cases.toml). Every state is taken at 1440, 1024 and 390 px. A
// question about another project or package than P130164 is asked from the home page, with no scope chip, so the
// panel never reads "Asked within P130164." over it.
const steps = "[data-answer-panel] [aria-expanded][aria-controls]:not([data-citation])";
const cardMarker = "[data-answer-panel] [data-disagreement] [data-citation='2']";
// Each answer is asked with its scripted case's own question, from the gallery's copy of them.
const { questions: CASE_QUESTIONS, refusalQuestions: REFUSED } = galleryCopy.sixChecks;
const PAST_RANGE = CASE_QUESTIONS.pastRange;
const SUMMARIES = CASE_QUESTIONS.summaries;
const ISR_7 = CASE_QUESTIONS.isr7;
const BOTH_SIDES = CASE_QUESTIONS.bothSides;
const NOT_YET_PUBLIC = CASE_QUESTIONS.planNotYetPublic;
const PARTIAL = REFUSED.partial;
// Ticket 23: a project's Timeline tab, as the 23 brief's section 13 lists it, against the answers the server wrote on
// the fixture (tests/record_timeline_api.py): loading, populated, the drawer on the disagreement and on a mark and a
// band (at 1440 and 1024 the chart redraws at 718 and 524 px beside it), the table open, as of August 26, 2016, the
// public view of an active project, an error, hover and focus on a mark and the chip, and at 390 px the list and the
// sheet. The card's states and the drawer's views are also in the gallery (/gallery/timeline); the card under an
// answer is above (checks--disagreement-*), with its keep form and a kept choice here.
const PDO_DISAGREEMENT = "disagreement:437378890475ef48";
const TIMELINE = "/projects/P130164/timeline";
const TIMELINE_API: Shot["api"] = {
  ...HUB_API,
  "/api/projects/P130164/timeline": { recorded: "timeline-p130164.json" },
  "/api/projects/P130164/timeline?asof=2016-08-26": { recorded: "timeline-p130164-2016-08-26.json" },
  "/api/projects/P130164/timeline?asof=2024-01-01": { recorded: "timeline-p130164-2024-01-01.json" },
  "/api/projects/P156634/timeline": { recorded: "timeline-p156634.json" },
  "/api/projects/P156634/timeline?view=public": { recorded: "timeline-p156634-public.json" },
  [`/api/evidence?id=${PDO_DISAGREEMENT}`]: { recorded: "evidence-disagreement-p130164-pdo.json" },
  "/api/evidence?id=doc:26733307": { recorded: "evidence-doc-p130164-isr-7.json" },
  "/api/evidence?id=doc:31525018": { recorded: "evidence-doc-p130164-icr.json" },
  "/api/evidence?id=ratings:P130164:pdo_progress:1-9": { recorded: "evidence-ratings-p130164-1-9.json" },
  "/api/evidence?id=strata.gold.passage:31525018/v1/78": { recorded: "evidence-icr-p130164-78.json" },
  "/api/evidence?id=strata.gold.passage:26733307/v1/s4": { recorded: "evidence-isr-p130164-7-s4.json" },
};
const timelineShot = (name: string, path: string, rest: Partial<Shot> = {}): Shot => hubShot(name, path, rest, TIMELINE_API);
const mark = (id: string) => `[data-evidence-trail] [data-item="${id}"]`;
const KEPT_CHOICE = JSON.stringify({
  recorded: true,
  choice: {
    choice_id: "choice-0000000000000001",
    kept_assertion_id: "strata.gold.passage:26733307/v1/s4#P130164/pdo_progress",
    leaned_assertion_id: "strata.gold.passage:31525018/v1/78#P130164/pdo_progress",
    reason: galleryCopy.timelineReason,
    run_id: "run-0001",
    draft_id: null,
    made_at: "2026-10-23T15:00:00+00:00",
    kept_other: true,
  },
});
const TIMELINE_SHOTS: Shot[] = [
  timelineShot("project-timeline", TIMELINE),
  timelineShot("project-timeline--loading", TIMELINE, { pending: ["/api/projects/P130164/timeline"] }),
  // hubShot takes the answers as its last argument: an api in the shot's options would be replaced by them.
  hubShot("project-timeline--error", TIMELINE, {}, {
    ...TIMELINE_API,
    "/api/projects/P130164/timeline": { status: 503, body: '{"code":"data_service","trace_id":"0af7651916cd43dd8448eb211c80319c"}' },
  }),
  timelineShot("project-timeline--drawer-disagreement", `${TIMELINE}?evidence=${PDO_DISAGREEMENT}`),
  timelineShot("project-timeline--drawer-side", `${TIMELINE}?evidence=${PDO_DISAGREEMENT}`, { act: click("[role=tab]:has-text('78')"), full: true }),
  timelineShot("project-timeline--drawer-document", `${TIMELINE}?evidence=doc:26733307`),
  timelineShot("project-timeline--drawer-band", `${TIMELINE}?evidence=ratings:P130164:pdo_progress:1-9`, { widths: WIDE }),
  timelineShot("project-timeline--table", TIMELINE, { widths: WIDE, act: click("[data-timeline-card] button[aria-controls]"), full: true }),
  timelineShot("project-timeline--as-of", `${TIMELINE}?asof=2016-08-26`),
  // After the ICR Review's re-issue: the second dashed line ends near the as-of date's label (round 2's B1).
  timelineShot("project-timeline--as-of-late", `${TIMELINE}?asof=2024-01-01`, { widths: WIDE }),
  // get_disagreements did not answer: the server's own recorded answer (tests/record_timeline_api.py, FAILED).
  hubShot("project-timeline--disagreements-failed", TIMELINE, { widths: WIDE }, { ...TIMELINE_API, "/api/projects/P130164/timeline": { recorded: "timeline-p130164-failed.json" } }),
  timelineShot("project-timeline--public-active", "/projects/P156634/timeline?view=public", { widths: WIDE }),
  timelineShot("project-timeline--crowded", "/projects/P156634/timeline", { widths: WIDE }),
  timelineShot("project-timeline--hover-mark", TIMELINE, { widths: WIDE, act: hover(mark("doc:26733307")) }),
  timelineShot("project-timeline--focus-mark", TIMELINE, { widths: WIDE, act: focus(mark("doc:18381488")) }),
  timelineShot("project-timeline--hover-band", TIMELINE, { widths: WIDE, act: hover(mark("ratings:P130164:pdo_progress:1-9")) }),
  timelineShot("project-timeline--hover-chip", TIMELINE, { widths: WIDE, act: hover(mark(PDO_DISAGREEMENT)) }),
  timelineShot("project-timeline--focus-list-item", TIMELINE, { widths: NARROW, act: focus("[data-timeline-list] a") }),
  timelineShot("project-timeline--320", TIMELINE, { widths: [320] }),
  answerShot("checks--disagreement-keep-form", "ask-p130164-isr-7-rating.sse", {
    widths: WIDE,
    act: then(askInBox(ISR_7), click("[data-answer-panel] [data-disagreement] [data-keep] button")),
  }),
  answerShot("checks--disagreement-kept", "ask-p130164-isr-7-rating.sse", {
    widths: WIDE,
    api: { "/api/disagreements/437378890475ef48/choices": { body: KEPT_CHOICE } },
    act: askInBox(ISR_7),
  }),
];

const CHECK_SHOTS: Shot[] = [
  answerShot("checks--ticket-form", "ask-ke-nwwda-541055-past-range.sse", { act: askInBox(PAST_RANGE) }, "/"),
  // Ticket 105: How I checked this answer, opened from "How was that checked?" after the check line.
  answerShot("checks--how-window", "ask-ke-nwwda-541055-past-range.sse", { widths: [1440, 390], act: then(askInBox(PAST_RANGE), click("[data-how-checked]")) }, "/"),
  answerShot("checks--judged", "ask-ke-nwwda-541055-advice.sse", { act: askInBox(PAST_RANGE) }, "/"),
  answerShot("checks--every-sentence-judged", "ask-p130164-summaries.sse", { act: askInBox(SUMMARIES) }),
  answerShot("checks--six-checks-judged", "ask-ke-nwwda-541055-advice.sse", { act: then(askInBox(PAST_RANGE), click(steps)) }, "/"),
  answerShot("checks--six-checks-not-judged", "ask-ke-nwwda-541055-past-range.sse", { act: then(askInBox(PAST_RANGE), click(steps)) }, "/"),
  answerShot("checks--six-checks-attached", "ask-p130164-isr-7-rating.sse", { act: then(askInBox(ISR_7), click(steps)) }),
  answerShot("checks--removed-check-4", "ask-p130164-unsupported.sse", { act: askInBox() }),
  answerShot("checks--removed-check-5", "ask-p130164-advice-without-lesson.sse", { act: askInBox() }),
  answerShot("checks--removed-check-6", "ask-p130164-disagreements-unavailable.sse", { act: askInBox() }),
  answerShot("checks--removed-several", "ask-p130164-several-removed.sse", { act: askInBox() }),
  // Ticket 58: an answer whose kept sentence cites nothing, with its steps open; the same with a sentence check 4
  // removed for saying more than a tool reported; and check 2's removal of a sentence that cites nothing.
  answerShot("checks--none-cited", "ask-p156634-plan-not-yet-public.sse", { act: then(askInBox(NOT_YET_PUBLIC), click(steps)) }),
  answerShot("checks--removed-beyond-abstention", "ask-p156634-uncited-blame.sse", { act: then(askInBox(NOT_YET_PUBLIC), click(steps)) }),
  answerShot("checks--removed-no-source", "ask-p130164-uncited-summary.sse", { act: then(askInBox(), click(steps)) }),
  answerShot("checks--judge-silent", "ask-p130164-judge-no-response.sse", { act: askInBox() }),
  answerShot("checks--judge-silent-nothing-kept", "ask-p130164-judge-no-response-none-kept.sse", { act: askInBox(SUMMARIES) }),
  // Ticket 60: the outage states and a partial refusal whose other sentences lost check 6's service, each from its
  // scripted case's recorded stream, at 1440, 1024 and 390 px (check 2's removal is checks--removed-no-source above).
  answerShot("checks--judge-silent-some-failed", "ask-p130164-judge-no-response-some-failed.sse", { act: askInBox(SUMMARIES) }),
  answerShot("checks--removed-check-6-some-kept", "ask-ke-nwwda-541055-disagreements-unavailable-some-kept.sse", { act: askInBox(PAST_RANGE) }, "/"),
  answerShot("checks--removed-check-6-mixed", "ask-ke-nwwda-541055-disagreements-unavailable-mixed.sse", { act: askInBox(PAST_RANGE) }, "/"),
  answerShot("checks--partial-refusal-unchecked", "ask-refuses-part-supplier-scores-disagreements-unavailable.sse", { act: askInBox(PARTIAL) }),
  answerShot("checks--focus-try-again", "ask-p130164-judge-no-response.sse", { full: false, act: then(askInBox(), focus("[data-removed-box] [data-button]")) }),
  answerShot("checks--disagreement-warning", "ask-p130164-isr-7-rating.sse", { act: askInBox(ISR_7) }),
  answerShot("checks--disagreement-info", "ask-p130164-both-sides.sse", { act: askInBox(BOTH_SIDES) }),
  answerShot("checks--disagreement-focus-marker", "ask-p130164-isr-7-rating.sse", { full: false, act: then(askInBox(ISR_7), focus(cardMarker)) }),
  answerShot("checks--disagreement-hover-marker", "ask-p130164-isr-7-rating.sse", { full: false, widths: WIDE, act: then(askInBox(ISR_7), hover(cardMarker)) }),
  answerShot("checks--disagreement-drawer", "ask-p130164-isr-7-rating.sse", { full: false, widths: [1440], act: then(askInBox(ISR_7), click(cardMarker)) }),
  answerShot("checks--320", "ask-p130164-isr-7-rating.sse", { widths: [320], act: askInBox(ISR_7) }),
  answerShot("refusal--supplier-scores", "ask-refuses-supplier-scores.sse", { act: askInBox(REFUSED.supplier_scores) }, "/"),
  answerShot("refusal--fraud-and-redactions", "ask-refuses-fraud-and-redactions.sse", { act: askInBox(REFUSED.fraud_and_redactions) }),
  answerShot("refusal--live-tenders", "ask-refuses-live-tenders.sse", { act: askInBox(REFUSED.live_tenders) }, "/"),
  answerShot("refusal--review-decisions", "ask-refuses-review-decisions.sse", { act: askInBox(REFUSED.review_decisions) }, "/"),
  answerShot("refusal--estimates-for-decisions", "ask-refuses-estimates-for-decisions.sse", { act: askInBox(REFUSED.estimates_for_decisions) }, "/"),
  answerShot("refusal--dividing-packages", "ask-refuses-dividing-packages.sse", { act: askInBox(REFUSED.dividing_packages) }, "/"),
  answerShot("refusal--rule-breach-findings", "ask-refuses-rule-breach-findings.sse", { act: askInBox(REFUSED.rule_breach_findings) }, "/"),
  answerShot("refusal--personal-details", "ask-refuses-personal-details.sse", { act: askInBox(REFUSED.personal_details) }, "/"),
  answerShot("refusal--wrong-edition", "ask-refuses-wrong-edition.sse", { act: askInBox(REFUSED.wrong_edition) }),
  answerShot("refusal--private-uploads", "ask-refuses-private-uploads.sse", { act: askInBox(REFUSED.private_uploads) }, "/"),
  answerShot("refusal--partial", "ask-refuses-part-supplier-scores.sse", { act: askInBox(PARTIAL) }),
  // Ticket 97: "See everything I turn down" under the refusal, focused, and the refusal window it opens.
  answerShot("refusal--focus-link", "ask-refuses-supplier-scores.sse", { full: false, act: then(askInBox(REFUSED.supplier_scores), focus("[data-answer-panel] [data-answer=refused] [data-refusal-all]")) }, "/"),
  answerShot("refusal--why", "ask-refuses-supplier-scores.sse", { full: false, act: then(askInBox(REFUSED.supplier_scores), click("[data-answer-panel] [data-answer=refused] [data-refusal-all]")) }, "/"),
];

const pages: Shot[] = Object.keys(galleryCopy.pages).map((slug) => ({ name: slug, path: `/gallery/${slug}` }));

// Ticket 95's zone parts (/gallery/zones). An action photographs the window around its element, so each state's shot
// brings its zone into view first.
const inView = (selector: string) => async (page: Page) => {
  await page.locator(selector).first().evaluate((el) => el.scrollIntoView({ block: "center" }));
  await page.waitForTimeout(250);
};
const ZONES = "/gallery/zones";
const WORKSPACE = `${ZONES}?sample=workspace`;
const ZONE_STATES = ["open", "closed", "loading", "error", "empty"] as const;
const ZONE_SHOTS: Shot[] = [
  ...ZONE_STATES.map((state) => ({
    name: `zones--state-${state}`,
    path: ZONES,
    widths: state === "open" || state === "closed" ? WIDTHS : [1440, 390],
    act: inView(`[data-section=state-${state}]`),
  })),
  { name: "zones--opened-row", path: ZONES, act: click("[data-section=steps] [data-section-toggle]") },
  { name: "zones--failed-block", path: ZONES, act: inView("[data-state-section=failed] [data-zone]") },
  { name: "zones--tag-under", path: ZONES, act: inView("[data-section=start-here]") },
  { name: "zones--side-panel", path: ZONES, act: inView("[data-state-section=side]") },
  { name: "zones--focus-toggle", path: ZONES, act: focus("[data-section=steps] [data-section-toggle]") },
  { name: "zones--hover-toggle", path: ZONES, widths: WIDE, act: hover("[data-section=steps] [data-section-toggle]") },
  { name: "zones--workspace-open", path: `${WORKSPACE}&sidebar=open`, widths: [1440, 1200] },
  { name: "zones--workspace-rail", path: `${WORKSPACE}&sidebar=rail`, widths: [1280, 1024, 390] },
  { name: "zones--workspace-drawer-open", path: `${WORKSPACE}&sidebar=open&drawer=open`, widths: [1440] },
  { name: "zones--workspace-drawer-rail", path: `${WORKSPACE}&sidebar=rail&drawer=open`, widths: [1280] },
];

// Ticket 32: the evidence drawer's feedback row, opened from the showcase answer's first marker, in the states the 32
// brief's section 12 lists, and Lessons > Passage reports and Lessons > Judging. The answers are the server's own,
// recorded on the fixture by tests/record_retrieval_api.py. Each page is served with the frame's counts from the
// same moment of that story (retrieval-me-*.json), so the sub-tab's count and the page's lead agree. The other states
// are in the gallery (/gallery/retrieval and /gallery/judging), from the same answers.
const FEEDBACK_API: Shot["api"] = {
  "/api/feedback": { recorded: "feedback-sent.json" },
};
const openRow = then(askInBox(QUESTION), click(marker), async (page) => {
  await page.locator("[data-feedback-row]").scrollIntoViewIfNeeded();
  await page.waitForTimeout(250);
});
const rowShot = (name: string, act: (page: Page) => Promise<void>, rest: Partial<Shot> = {}) =>
  answerShot(`feedback--${name}`, "ask-p130164-rebidding.sse", { full: false, ...rest, act, api: { ...FEEDBACK_API, ...rest.api } });
const retrievalShot = (name: string, path: string, me: string, answers: Shot["api"], rest: Partial<Shot> = {}) =>
  app(`retrieval--${name}`, path, {}, { full: true, ...rest, api: { ...app(name, path).api, "/api/lessons/me": { recorded: me }, ...answers } });
const GROUP = "/lessons/reports/grp-6fa04e510789";
const QUERY_PATH = "/lessons/judging/nq-rural-works-delays";
const RETRIEVAL_SHOTS: Shot[] = [
  rowShot("idle", openRow),
  rowShot("chosen", then(openRow, click("[data-feedback-row] [data-report-kind=wrong_passage]"))),
  rowShot("typed", then(openRow, click("[data-feedback-row] [data-report-kind=not_useful]"), type("[data-feedback-row] textarea", "It is about estimates in general."))),
  rowShot("sent", then(openRow, click("[data-feedback-row] [data-report-kind=wrong_passage]"), type("[data-feedback-row] textarea", "It is about estimates in general."), click("[data-send-report]"))),
  rowShot("hover-kind", then(openRow, hover("[data-feedback-row] [data-report-kind=wrong_passage]")), { widths: WIDE }),
  rowShot("focus-kind", then(openRow, focus("[data-feedback-row] [data-report-kind=not_useful]"))),
  rowShot("preview", openRow, { path: "/projects/P130164?view=piu" }),
  retrievalShot("frame-reviewer", "/lessons/reports", "retrieval-me-passage-reviewer.json", { "/api/passage-reports": { recorded: "passage-reports-empty.json" } }),
  retrievalShot("frame-judge", "/lessons/judging", "retrieval-me-judge.json", { "/api/judging/queries": { recorded: "judging-queries-start.json" } }),
  retrievalShot("reports", "/lessons/reports", "retrieval-me-both-waiting.json", { "/api/passage-reports": { recorded: "passage-reports-own-report.json" } }),
  retrievalShot("reports-decided", "/lessons/reports", "retrieval-me-passage-reviewer-decided.json", { "/api/passage-reports": { recorded: "passage-reports-decided.json" } }),
  retrievalShot("reports-audit", "/lessons/reports", "retrieval-me-passage-reviewer-audit.json", { "/api/passage-reports": { recorded: "passage-reports-audit.json" } }),
  retrievalShot("reports-loading", "/lessons/reports", "retrieval-me-passage-reviewer-waiting.json", {}, { pending: ["/api/passage-reports"] }),
  retrievalShot("reports-no-access", "/lessons/reports", "lessons-me-viewer.json", { "/api/passage-reports": refusal("passage-reports-no-access.json") }),
  retrievalShot("report", GROUP, "retrieval-me-passage-reviewer-waiting.json", { "/api/passage-reports/grp-6fa04e510789": { recorded: "passage-report.json" } }),
  retrievalShot("report-decided", GROUP, "retrieval-me-passage-reviewer-decided.json", { [`/api/passage-reports/grp-6fa04e510789`]: { recorded: "passage-report-decided.json" } }),
  retrievalShot("report-audit", GROUP, "retrieval-me-passage-reviewer-audit.json", { [`/api/passage-reports/grp-6fa04e510789`]: { recorded: "passage-report-audit.json" } }),
  retrievalShot("report-not-found", "/lessons/reports/grp-000000000000", "retrieval-me-passage-reviewer-waiting.json", { "/api/passage-reports/grp-000000000000": refusal("passage-report-not-found.json") }),
  retrievalShot("judging", "/lessons/judging", "retrieval-me-judge-after.json", { "/api/judging/queries": { recorded: "judging-queries.json" } }),
  retrievalShot("judging-both", "/lessons/judging?show=finished_by_both", "retrieval-me-judge-after.json", { "/api/judging/queries": { recorded: "judging-queries-both.json" } }),
  retrievalShot("judging-no-access", "/lessons/judging", "lessons-me-viewer.json", { "/api/judging/queries": refusal("judging-no-access.json") }),
  retrievalShot("query", QUERY_PATH, "retrieval-me-judge.json", { "/api/judging/queries/nq-rural-works-delays": { recorded: "judging-query.json" } }, { full: false }),
  retrievalShot("query-progress", QUERY_PATH, "retrieval-me-judge-after.json", { "/api/judging/queries/nq-rural-works-delays": { recorded: "judging-query-progress.json" } }, { full: false, act: click("[data-passage-map] button") }),
  retrievalShot("query-locked", "/lessons/judging/nq-water-works-readiness", "retrieval-me-judge-after.json", { "/api/judging/queries/nq-water-works-readiness": { recorded: "judging-query-locked.json" } }),
  retrievalShot("query-not-found", "/lessons/judging/nq-nothing", "retrieval-me-judge-after.json", { "/api/judging/queries/nq-nothing": refusal("judging-query-not-found.json") }),
  retrievalShot("query-focus-grade", QUERY_PATH, "retrieval-me-judge.json", { "/api/judging/queries/nq-rural-works-delays": { recorded: "judging-query.json" } }, { full: false, act: focus("[data-grade-bar] [data-grade=partly]") }),
  retrievalShot("query-320", QUERY_PATH, "retrieval-me-judge.json", { "/api/judging/queries/nq-rural-works-delays": { recorded: "judging-query.json" } }, { widths: [320] }),
];

// Ticket 36: the package workspace's "Suggest {n} PPSD risk rows", suggested PPSD rows in the Short Form and the Long
// Form, a warning disagreement card on a draft, Check a plan's "Drafts from this check" and the Project Paper summary,
// with /api answered from the server's answers on the fixture (tests/record_ppsd_api.py). A *-made-up-* answer is a
// state the fixture cannot reach. Function first (October 25, 2026): 1440 px only until the design pass.
const PPSD_WIDTHS = [1440];
const PPSD_SHOTS: Shot[] = [
  {
    ...packageShot("ppsd--package-action", comparables(COMPARABLES)),
    widths: PPSD_WIDTHS,
    api: {
      ...packageShot("ppsd--package-action", comparables(COMPARABLES)).api,
      [`/api${PACKAGE}/risks`]: { recorded: "risks-ke-nwwda-541055-india-selected.json" },
      "/api/me": { recorded: "me-staff.json" },
      "/api/drafts/existing": { body: '{"draft":null}' },
    },
  },
  draftShot("ppsd--draft", { recorded: "drafts-ppsd-draft.json" }, { widths: PPSD_WIDTHS }),
  draftShot("ppsd--some-owners", { recorded: "drafts-ppsd-some-owners.json" }, { widths: PPSD_WIDTHS }),
  draftShot("ppsd--checked-owners-left", { recorded: "drafts-ppsd-checked-owners-left.json" }, { widths: PPSD_WIDTHS }),
  draftShot("ppsd--exported", { recorded: "drafts-ppsd-exported.json" }, { widths: PPSD_WIDTHS }),
  draftShot("ppsd--long-form", { recorded: "drafts-ppsd-made-up-long.json" }, { widths: PPSD_WIDTHS }),
  draftShot("ppsd--one-cell", { recorded: "drafts-ppsd-one-cell.json" }, { widths: PPSD_WIDTHS }),
  draftShot("ppsd--disagreement", { recorded: "drafts-ppsd-made-up-disagreement.json" }, { widths: PPSD_WIDTHS }, "/drafts/draft-0090"),
  planWithDraft("ppsd--plan-panel", NO_EXISTING, {
    widths: PPSD_WIDTHS,
    full: true,
    api: { "/api/me": { recorded: "me-staff.json" }, "/api/drafts/project-paper-inputs": { recorded: "drafts-pp-inputs.json" } },
  }),
  draftShot("paper--draft", { recorded: "drafts-pp-draft.json" }, { widths: PPSD_WIDTHS }, "/drafts/draft-0002"),
  draftShot("paper--no-ppsd", { recorded: "drafts-pp-no-ppsd.json" }, { widths: PPSD_WIDTHS }, "/drafts/draft-0002"),
  draftShot("paper--no-record", { recorded: "drafts-pp-made-up-no-record.json" }, { widths: PPSD_WIDTHS }, "/drafts/draft-0002"),
];

// Other languages (ticket 42), at 1440 px only until the design pass: an answer and its drawer written in French, the
// French completion report's source view, the language choice in the view popover, and review notes in French.
const FRENCH = "Why were procurement processes delayed in P127203?";
const LANGUAGE_SHOTS: Shot[] = [
  answerShot("languages--answer-in-french", "ask-p127203-fr.sse", { widths: [1440], act: askInBox(FRENCH),
    api: { "/api/me": { recorded: "me-lang-fr.json" } } }, "/projects/P130164?lang=fr"),
  answerShot("languages--drawer-french-passage", "ask-p127203-fr.sse", { widths: [1440], full: false,
    act: then(askInBox(FRENCH), click(marker)), api: { "/api/me": { recorded: "me-lang-fr.json" } } }, "/projects/P130164?lang=fr"),
  app("languages--source-view-french", "/projects/P127203/documents/icr-2021-07-29?page=13&para=1", {}, { widths: [1440],
    api: { ...app("x", "/").api, "/api/projects/P127203/documents/icr-2021-07-29": { recorded: "source-icr-p127203-fr-13.json" } } }),
  app("languages--choice-in-popover", "/", {}, { widths: [1440], full: false, act: click("[data-view-pill]") }),
  app("languages--review-notes-in-french", "/drafts/draft-0005", {}, { widths: [1440], api: { ...app("x", "/").api,
    "/api/drafts/draft-0005": { recorded: "drafts-review-notes-fr.json" }, "/api/drafts/existing": { body: '{"draft":null}' } } }),
];

// Ticket 47: the deck at /present, from the fixture's deck data. Under the function-first rule each is taken at 1440 px
// only; the other widths, hover and focus wait for the design pass.
const deck = (name: string, path: string, rest: Partial<Shot> = {}): Shot => ({
  name: `deck--${name}`,
  path,
  server: "app",
  deckData: "deck-data.json",
  widths: [1440],
  ...rest,
});
const DECK_SHOTS: Shot[] = [
  deck("title", "/present/1", { full: false }),
  deck("opener", "/present/7", { full: false }),
  deck("award-gap", "/present/16", { full: false }),
  deck("reading-view", "/present/page"),
  deck("speaker-notes", "/present/notes"),
];

export const SHOTS: Shot[] = [
  { name: "index", path: "/gallery" },
  ...pages,

  // The frame: the bar with the box, the sidebar and the footer. Ticket 92: the sidebar open and as the rail, a rail
  // item's tooltip, an item's focus and hover, a section's own pages, the public view's sidebar, and the Menu sheet below
  // 1024 px.
  { name: "navigation--hover-item", path: "/gallery/navigation", widths: WIDE, act: hover("[data-sidebar] [data-nav-item=lessons]") },
  { name: "navigation--focus-item", path: "/gallery/navigation", widths: WIDE, act: focus("[data-sidebar] [data-nav-item=projects]") },
  { name: "navigation--rail", path: "/gallery/navigation?sidebar=rail", widths: [1440] },
  { name: "navigation--rail-tip", path: "/gallery/navigation?sidebar=rail", widths: [1440], act: hover("[data-sidebar] [data-nav-item=lessons]") },
  { name: "navigation--sub-items", path: "/gallery/navigation?sub=1", widths: [1440] },
  // Ticket 59: the sidebar before GET /api/me answers, its bars where Home, the sections and Data will be.
  { name: "navigation--sidebar-loading", path: "/gallery/navigation?pill=loading&sidebar=open", widths: [1440] },
  { name: "navigation--menu-loading", path: "/gallery/navigation?pill=loading&menu=open", widths: [390] },
  { name: "navigation--public", path: "/gallery/navigation?pill=public", widths: WIDE },
  { name: "navigation--focus-wordmark", path: "/gallery/navigation", act: focus("[data-nav-bar] a[href='/']") },
  { name: "navigation--focus-skip-link", path: "/gallery/navigation", act: (page) => page.keyboard.press("Tab") },
  // From 768 px the view switch sits in the bar, so its shots take 800 px too (ticket 60).
  { name: "navigation--hover-pill", path: "/gallery/navigation", widths: [1440, 1024, 800], act: hover("[aria-haspopup=dialog]") },
  { name: "navigation--focus-pill", path: "/gallery/navigation", widths: [1440, 1024, 800], act: focus("[aria-haspopup=dialog]") },
  { name: "navigation--view-open", path: "/gallery/navigation?view=open", widths: [1440, 1024, 800] },
  { name: "navigation--view-loading", path: "/gallery/navigation?view=open&viewer=loading", widths: WIDE },
  { name: "navigation--view-signed-out", path: "/gallery/navigation?view=open&viewer=signed-out", widths: WIDE },
  { name: "navigation--view-error", path: "/gallery/navigation?view=open&viewer=error", widths: WIDE },
  { name: "navigation--hover-menu", path: "/gallery/navigation", widths: NARROW, act: hover("[data-menu-button]") },
  { name: "navigation--focus-menu", path: "/gallery/navigation", widths: NARROW, act: focus("[data-menu-button]") },
  { name: "navigation--menu-open", path: "/gallery/navigation?menu=open", widths: NARROW },
  // Ticket 59: the sheet's view button pressed, its popover with the view lines and language choice above it.
  { name: "navigation--menu-view-open", path: "/gallery/navigation?menu=open&menuview=open", widths: [390] },
  { name: "navigation--menu-row-focus", path: "/gallery/navigation?menu=open", widths: NARROW, act: focus("[data-sidebar] [data-nav-item=lessons]") },
  { name: "navigation--menu-row-hover", path: "/gallery/navigation?menu=open", widths: NARROW, act: hover("[data-sidebar] [data-nav-item=drafts]") },
  // Ticket 93: the box in the bar, the stamp at the sidebar's foot (the Menu sheet's below 1024 px), and the fixture's
  // longest reference in the box's chip at 390 px.
  { name: "navigation--focus-box", path: "/gallery/navigation", act: focus("[data-box-slot] input") },
  { name: "navigation--hover-box", path: "/gallery/navigation", act: hover("[data-box-slot] [data-focus-ring]") },
  { name: "navigation--focus-stamp", path: "/gallery/navigation?sidebar=open", widths: WIDE, act: focus("[data-sidebar] [data-stamp] a") },
  { name: "navigation--hover-stamp", path: "/gallery/navigation?sidebar=open", widths: WIDE, act: hover("[data-sidebar] [data-stamp] a") },
  { name: "navigation--long-chip", path: "/gallery/navigation?scope=KE-UASIN%20GISHU%20COUNTY-571338-CW-RFB", widths: [390] },
  { name: "navigation--320", path: "/gallery/navigation?menu=open", widths: [320] },

  // Ticket 95: the Task zone in each state, at 1440 and 390 px, and open and closed at 1024 px too; a row opened in
  // place; the Show button's focus and hover; and the workspace sample, closed and beside the drawer, at 1440 px with
  // the sidebar open and 1280 px as a rail, and as one column at 1200 px open, 1024 px as a rail and 390 px.
  ...ZONE_SHOTS,

  // Buttons, links and tabs.
  // The variants' own buttons: the frame's view popover holds a secondary button too, out of sight until it opens.
  { name: "buttons--hover-primary", path: "/gallery/buttons", act: hover("[data-state-section=variants] [data-button=primary]") },
  { name: "buttons--hover-secondary", path: "/gallery/buttons", act: hover("[data-state-section=variants] [data-button=secondary]") },
  { name: "buttons--hover-ghost", path: "/gallery/buttons", act: hover("[data-state-section=variants] [data-button=ghost]") },
  { name: "buttons--focus-primary", path: "/gallery/buttons", act: focus("[data-state-section=variants] [data-button=primary]") },
  { name: "buttons--pressed-primary", path: "/gallery/buttons", act: press("[data-state-section=variants] [data-button=primary]") },
  { name: "buttons--pressed-secondary", path: "/gallery/buttons", act: press("[data-state-section=variants] [data-button=secondary]") },
  { name: "buttons--hover-flush", path: "/gallery/buttons", act: hover("[data-state-section=flush] button") },
  { name: "buttons--focus-flush", path: "/gallery/buttons", act: focus("[data-state-section=flush] button") },
  { name: "buttons--hover-on-page", path: "/gallery/buttons", act: hover("[data-state-section=on-page] button") },
  { name: "buttons--focus-disabled", path: "/gallery/buttons", act: focus("[data-state-section=disabled] button") },
  { name: "links--hover-link", path: "/gallery/links", act: hover("[data-state-section=text-link] a") },
  { name: "links--focus-link", path: "/gallery/links", act: focus("[data-state-section=text-link] a") },
  { name: "links--hover-external-link", path: "/gallery/links", act: hover("[data-state-section=external-link] a") },
  { name: "links--focus-external-link", path: "/gallery/links", act: focus("[data-state-section=external-link] a") },
  { name: "links--hover-tab", path: "/gallery/links", act: hover("[data-state-section=tabs] a:not([aria-current])") },
  { name: "links--focus-tab", path: "/gallery/links", act: focus("[data-state-section=tabs] a[aria-current]") },
  { name: "cards--focus-link", path: "/gallery/cards", act: focus("[data-empty-state] a") },
  { name: "cards--hover-link", path: "/gallery/cards", act: hover("[data-empty-state] a") },

  // Numbers, terms and citations.
  { name: "numbers--focus-num", path: "/gallery/numbers", act: focus("[data-state-section=checkable] button") },
  { name: "numbers--hover-num", path: "/gallery/numbers", act: hover("[data-state-section=checkable] button") },
  { name: "numbers--term-open", path: "/gallery/numbers", act: click("[data-term]") },
  { name: "numbers--measure-open", path: "/gallery/numbers", act: click("[data-state-section=terms] [data-term] >> nth=1") },
  { name: "citations--hover-marker", path: "/gallery/citations", act: hover("[data-state-section=markers] p [data-citation]") },
  { name: "citations--focus-marker", path: "/gallery/citations", act: focus("[data-state-section=markers] p [data-citation]") },
  { name: "citations--focus-coverage-link", path: "/gallery/citations", act: focus("[data-coverage-line] a") },

  // The answer, the document and the table.
  { name: "answer--steps-open", path: "/gallery/answer", act: click("[data-state-section=ready] [aria-expanded]") },
  { name: "answer--hover-steps", path: "/gallery/answer", act: hover("[data-state-section=ready] [aria-expanded]") },
  { name: "answer--focus-steps", path: "/gallery/answer", act: focus("[data-state-section=ready] [aria-expanded]") },
  { name: "answer--focus-retry", path: "/gallery/answer", act: focus("[data-state-section=error] button") },
  { name: "document--focus-pdf-link", path: "/gallery/document", act: focus("[data-document=ready] a") },
  { name: "table--focus-region", path: "/gallery/table", widths: WIDE, act: focus("[data-table] [role=region]") },
  // Between 768 and 1023 px the two breakpoints differ: the default table and the lg one's cards.
  { name: "table--cards-below-lg", path: "/gallery/table", widths: [900] },

  // The production app against the mocked API (ticket 06): every route, both not-found pages,
  // the stamp's states, the page alerts, the box, the view popover, the Menu and the frame's
  // hover and focus states.
  ...ROUTES.map(([name, path]) => app(`app--${name}`, path)),
  app("app--stamp-past-year", "/", { freshness: { body: '{"data_through":"2025-12-30"}' } }),
  app("app--stamp-empty", "/", { freshness: { recorded: "freshness-empty.json" } }),
  app("app--stamp-error", "/", { freshness: { status: 502, body: '{"code":"unreadable"}' } }),
  app("app--no-access", "/", { freshness: { status: 403, recorded: "freshness-no-access.json" } }),
  app("app--no-identity", "/", { me: { body: SIGNED_OUT }, freshness: { status: 401, recorded: "freshness-no-identity.json" } }),
  // A preview's and a past date's Lessons page, from the server's answers (ticket 102): the preview leaves out what is
  // about you, and as of a date the page says it shows the library as it was. The past date's answer is the server's
  // own for August 26, 2016 (tests/record_lessons_page_api.py), when no lesson, notice or report was public yet.
  app("app--view-piu", "/lessons?view=piu", {}, { api: { ...app("x", "/lessons").api, "/api/me": { recorded: "me-preview-piu.json" }, "/api/lessons/page": { recorded: "lessons-page-preview.json" } } }),
  app("app--view-public", "/lessons?view=public", {}, { api: { ...app("x", "/lessons").api, "/api/me": { recorded: "me-preview-public.json" }, "/api/lessons/page": { recorded: "lessons-page-preview.json" } } }),
  app("app--asof", "/lessons?asof=2016-08-26", {}, {
    api: { ...app("x", "/lessons").api, "/api/me": { recorded: "me-asof.json" }, "/api/lessons/page": { recorded: "lessons-page-asof.json" } },
  }),
  app("app--asof-unreadable", "/lessons?asof=last-tuesday"),
  app("app--box-with-text", "/", { }, { act: type("[data-box-slot] input", "P130164"), api: { ...app("x", "/").api, ...BOX_API } }),
  app("app--view-open", "/", {}, { widths: WIDE, act: click("[aria-haspopup=dialog]") }),
  app("app--view-error", "/", { me: { status: 502, body: '{"detail":"Bad Gateway"}' } }, { widths: WIDE, act: click("[aria-haspopup=dialog]") }),
  app("app--menu-open", "/lessons", {}, { widths: NARROW, act: click("[aria-controls][aria-expanded]:not([aria-haspopup])") }),
  app("app--1024-with-scrollbar", "/lessons", {}, {
    widths: [1024],
    act: async (page) => {
      await page.addStyleTag({ content: "body { margin-right: 15px; }" });
    },
  }),
  app("app--320", "/projects/P130164/packages/IN-RRSMP-7431-CW-RFB", {}, { widths: [320] }),
  app("app--hover-current-item", "/lessons", {}, { widths: WIDE, act: hover("[data-sidebar] [aria-current=page]") }),
  app("app--focus-wordmark", "/", {}, { act: focus("[data-nav-bar] a[href='/']") }),
  app("app--focus-empty-link", "/", {}, { act: focus("[data-empty-state] a") }),
  app("app--hover-empty-link", "/", {}, { act: hover("[data-empty-state] a") }),
  app("app--focus-skip-link", "/", {}, { act: (page) => page.keyboard.press("Tab") }),

  // The Data tab (ticket 16): every state of Data readiness and Sources and licenses, and its focus
  // and hover states. The loading states are the gallery's readiness page. How Strata works left the
  // tab in ticket 97, and its two pages became the sidebar's items under Data in ticket 104.
  data("readiness", "/data"),
  // Ticket 104: the finding, the two panels and the three closed rows, then the rows opened in place, and the page
  // beside the evidence drawer at 1024 px, where its tables read a 550 px page area and turn to cards.
  data("rows-open", "/data", undefined, { act: openDataRows, full: true }),
  data("beside-drawer", `/data?evidence=${encodeURIComponent("strata.gold.passage:31525018/v1/54")}`, undefined, {
    widths: [1024],
    full: true,
    api: {
      "/api/me": { recorded: "me.json" },
      "/api/freshness": { recorded: "freshness.json" },
      "/api/evidence": { recorded: "evidence-icr-p130164-54.json" },
      "/api/evidence/opened": { body: '{"opened":[],"recorded":true}' },
    },
  }),
  data("filtered", FILTERED, { recorded: "data-readiness-filtered.json" }),
  data("filtered-plan-check", "/data?sources=documents,projects&from=check_plan", { recorded: "data-readiness-plan-check.json" }),
  data("filtered-unknown-key", "/data?sources=awards,not-a-source&from=find_comparables", { recorded: "data-readiness-unknown-key.json" }),
  data("no-known-key", "/data?sources=not-a-source", { recorded: "data-readiness-no-known-key.json" }),
  data("empty", "/data", { recorded: "data-readiness-empty.json" }),
  data("unmeasured", "/data", { recorded: "data-readiness-unmeasured.json" }),
  data("before-first", "/data?asof=2026-10-01", { recorded: "data-readiness-before-first.json" }),
  data("timeout", "/data", { status: 504, recorded: "data-readiness-timeout.json" }),
  data("no-access", "/data", { status: 403, recorded: "data-readiness-no-access.json" }),
  data("error", "/data", { status: 502, recorded: "data-readiness-error.json" }),
  data("sources", "/data/sources"),
  data("sources-empty", "/data/sources", undefined, {}, { body: '{"datasets":[],"collections":[],"readiness_rows":0,"known_gaps":0,"kinds":0,"fixes":0}' }),
  data("focus-show-all", FILTERED, { recorded: "data-readiness-filtered.json" }, { act: focus("main [data-alert=info] a") }),
  data("term-open", "/data", undefined, { widths: WIDE, act: click("[data-readiness-table=sources] thead [data-term] >> nth=1") }),
  data("focus-num", "/data", undefined, { act: focus("[data-headline] [data-num] >> nth=2") }),
  data("num-window", "/data", undefined, { act: click("[data-headline] [data-num] >> nth=2") }),
  data("hover-num", "/data", undefined, { widths: WIDE, act: hover("[data-cell='awards:linked'] [data-num]") }),
  data("fix-projects-window", "/data", undefined, { widths: WIDE, act: inOrder(openDataRow("fixes"), click("[data-fixes] li >> nth=0 >> p.text-small [data-num]")) }),
  data("hover-link", "/data", { recorded: "data-readiness-empty.json" }, { act: hover("[data-readiness=empty] a") }),
  data("cards-320", "/data", undefined, { widths: [320] }),
  // Ticket 18: the hardest documents I read, after Sources. The states the fixture does not reach are
  // the server's answers on the fixture with its shelf outcomes changed (tests/record_api.py).
  data("shelf-gap", "/data", { recorded: "data-readiness-shelf-gap.json" }, { act: openDataRow("shelf"), full: true }),
  data("shelf-two-gaps", "/data", { recorded: "data-readiness-shelf-two-gaps.json" }, { act: openDataRow("shelf"), full: true }),
  data("shelf-abstentions", "/data", { recorded: "data-readiness-shelf-abstentions.json" }, { act: openDataRow("shelf"), full: true }),
  data("shelf-empty", "/data", { recorded: "data-readiness-shelf-empty.json" }, { act: openDataRow("shelf"), full: true }),
  data("shelf-loading", "/data", undefined, { pending: ["/api/data/readiness"], act: openDataRow("shelf"), full: true }),
  data("shelf-focus-link", "/data", undefined, { act: inOrder(openDataRow("shelf"), focus("[data-readiness-table=shelf] a:visible")) }),
  data("shelf-hover-link", "/data", undefined, { widths: WIDE, act: inOrder(openDataRow("shelf"), hover("[data-readiness-table=shelf] [data-table-view=table] a")) }),
  data("shelf-term-open", "/data", undefined, { widths: WIDE, act: inOrder(openDataRow("shelf"), click("[data-readiness-table=shelf] thead [data-term] >> nth=0")) }),
  data("shelf-focus-num", "/data", undefined, { act: inOrder(openDataRow("shelf"), focus("[data-readiness-table=shelf] [data-num]:visible")) }),
  data("shelf-num-window", "/data", undefined, { act: inOrder(openDataRow("shelf"), click(":is([data-cell='p130164_pad:outcome'], [data-card='p130164_pad']) [data-num]:visible >> nth=-1")) }),
  data("shelf-holds-link", "/data", { recorded: "data-readiness-shelf-gap.json" }, { act: click("[data-readiness-table=kinds] a[href='#hardest-documents']:visible") }),
  data("read-well-window", "/data", undefined, { widths: WIDE, act: click("[data-cell='reports:read_well'] [data-num]") }),
  data("shelf-cards-320", "/data", { recorded: "data-readiness-shelf-gap.json" }, { widths: [320], act: openDataRow("shelf"), full: true }),

  // Ticket 10: Check a plan, a project's page and All projects, in every state the 10 brief
  // lists (section 10), with /api answered from the recordings.
  ...PLAN_SHOTS,
  ...PROJECT_SHOTS,
  ...HUB_SHOTS,
  ...ANSWER_SHOTS,
  ...CHECK_SHOTS,
  ...DRAFT_SHOTS,
  ...FOLLOWING_SHOTS,
  ...LESSON_SHOTS,
  ...PACKAGE_SHOTS,
  ...PLANNED_SHOTS,
  ...STEP_SHOTS,
  ...RISK_SHOTS,
  ...RETRIEVAL_SHOTS,
  ...REBID_SHOTS,
  ...CRITERIA_SHOTS,
  ...TIMELINE_SHOTS,
  ...TRAIL_SHOTS,
  ...PPSD_SHOTS,
  ...UPLOAD_SHOTS,
  ...LANGUAGE_SHOTS,
  ...VIEW_SHOTS,
  ...DECK_SHOTS,
  ...HOME_SHOTS,
];
