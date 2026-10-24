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

const WIDE = [1440, 1024];
const NARROW = [390];

// The app's routes, as the 06 design brief lists them, and both not-found pages. All projects, a
// project's page and Check a plan have their own shots below (ticket 10), and so does the package
// workspace (ticket 12).
const ROUTES: [string, string][] = [
  ["home", "/"],
  ["packages", "/packages"],
  ["activity", "/projects/P130164/packages/IN-RRSMP-7431-CW-RFB"],
  ["lessons", "/lessons"],
  ["drafts", "/drafts"],
  ["not-found", "/nowhere"],
  ["not-a-project", "/projects/130164"],
];

const SIGNED_OUT = '{"email":null,"name":null,"signed_in":false,"has_token":false}';
type Answer = { recorded?: string; body?: string; status?: number };

// An app shot: the page, with /api/me and /api/freshness answered from the recordings unless
// the shot says otherwise.
function app(name: string, path: string, answers: { me?: Answer; freshness?: Answer } = {}, rest: Partial<Shot> = {}): Shot {
  return {
    name,
    path,
    server: "app",
    api: { "/api/me": answers.me ?? { recorded: "me.json" }, "/api/freshness": answers.freshness ?? { recorded: "freshness.json" } },
    ...rest,
  };
}

// A Data tab shot (ticket 16): the page with the Data readiness answer it names, recorded from the
// server on the fixture, and the registry's datasets.
function data(name: string, path: string, readiness: Answer = { recorded: "data-readiness.json" }, rest: Partial<Shot> = {}, sources: Answer = { recorded: "data-sources.json" }): Shot {
  const shot = app(`data--${name}`, path, {}, rest);
  return { ...shot, api: { ...shot.api, "/api/data/readiness": readiness, "/api/data/sources": sources } };
}

const FILTERED = "/data?sources=awards,notices&from=find_comparables";

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
  "/api/evidence": { recorded: "evidence-icr-p130164-54.json" },
  "/api/evidence/opened": { body: '{"opened":[],"recorded":true}' },
};
const hubShot = (name: string, path: string, rest: Partial<Shot> = {}, answers: Shot["api"] = {}): Shot =>
  app(name, path, {}, { ...rest, api: { ...app(name, path).api, ...HUB_API, [PLAN_API]: { recorded: PLAN_FILE }, ...answers } });
const SOURCE = "/projects/P130164/documents/icr-2019-10-10";
const summaryWithout = (edit: (body: Record<string, any>) => void) => ({ body: derived("summary-p130164.json", edit) });
const longVersions = derived("project-p156634-baseline.json", (body) => {
  const nwwda = body.agencies[0];
  for (const [index, date] of ["2019-06-14", "2019-01-10"].entries()) {
    nwwda.versions.push({ ...nwwda.versions[4], document_id: `older-${index}`, plan_date: date, disclosed_on: date, is_latest: false, is_baseline: false, shown: false });
  }
  Object.assign(nwwda, { version_count: 7, shown_count: 5 });
});

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
  hubShot("summary--history-unknown", "/projects/P130164", {}, { "/api/projects/P130164/summary": summaryWithout((body) => Object.assign(body, { history: { known: false, rows: [] }, lead: { ...body.lead, moves: null } })) }),
  hubShot("summary--no-ratings", "/projects/P130164", {}, { "/api/projects/P130164/summary": summaryWithout((body) => (body.ratings = [])) }),
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
  hubShot("check-plan--baseline-none", PLAN),
  hubShot("check-plan--baseline-another", PLAN, {}, { [PLAN_API]: { recorded: "check-plan-p156634-nwwda-2026-10-09-baseline.json" } }),
  hubShot("check-plan--baseline-this", "/projects/P156634/procurement/northern-water-works-development-agency/2025-07-21"),
  hubShot("check-plan--baseline-confirm", PLAN, { act: click("[data-baseline] button[data-button=secondary]") }, { [PLAN_API]: { recorded: "check-plan-p156634-nwwda-2026-10-09-baseline.json" } }),
  hubShot("check-plan--baseline-saving", PLAN, { act: click("[data-baseline] button") }, { [`${PLAN_API.replace(/\/2026-10-09$/, "")}/baseline`]: { status: 503, body: SERVICE_DOWN } }),
  hubShot("check-plan--baseline-piu", `${PLAN}?view=piu`, {}, { [`${PLAN_API}?view=piu`]: { body: derived("check-plan-p156634-nwwda-2026-10-09-baseline.json", (body) => (body.baseline.saved_by = null)) } }),
  hubShot("check-plan--baseline-delay-num", PLAN, { widths: [1440, 390], act: focus("[data-baseline-delay] button[data-num]:visible") }, { [PLAN_API]: { recorded: "check-plan-p156634-nwwda-2026-10-09-baseline.json" } }),
  // Documents.
  hubShot("documents", "/projects/P130164/documents"),
  hubShot("documents--loading", "/projects/P130164/documents", { pending: ["/api/projects/P130164/documents"] }),
  hubShot("documents--group-open", "/projects/P130164/documents", { full: true, act: click("[data-documents] button[aria-expanded=false]:visible") }),
  hubShot("documents--term-open", "/projects/P130164/documents", { widths: [1440], act: click("[data-documents] [data-term]") }),
  hubShot("documents--empty", "/projects/P130164/documents", {}, { "/api/projects/P130164/documents": { body: derived("documents-p130164.json", (body) => Object.assign(body, { groups: [], total: 0, shown_total: 0 })) } }),
  hubShot("documents--error", "/projects/P130164/documents", {}, { "/api/projects/P130164/documents": { status: 503, body: SERVICE_DOWN } }),
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

const ANSWER_SHOTS: Shot[] = [
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
  draftShot("draft--exporting", { recorded: "drafts-review-notes-checked.json" }, { pending: ["/api/drafts/draft-0001/export"], full: true, act: click("[data-draft-bar] [data-button=primary]") }),
  draftShot("draft--exported", { recorded: "drafts-review-notes-checked.json" }, {
    full: true,
    api: { "/api/drafts/draft-0001/export": { recorded: "drafts-review-notes-exported.json" } },
    act: click("[data-draft-bar] [data-button=primary]"),
  }),
  draftShot("draft--exported-revisit", { recorded: "drafts-review-notes-exported.json" }),
  draftShot("draft--exported-files-missing", { body: filesMissing }),
  draftShot("draft--partial", { recorded: "drafts-review-notes-partial.json" }, {}, "/drafts/draft-0002"),
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
  const answers: Record<string, Answer> = { ...app(name, path).api };
  if (pkg) answers[api] = pkg;
  if (answer) answers[`${api}/comparables`] = answer;
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

const PACKAGE_SHOTS: Shot[] = [
  packageShot("package", comparables(COMPARABLES)),
  packageShot("package--loading", null, {}, null),
  packageShot("package--section-loading", null),
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
  packageShot("package--error", null, {}, { status: 503, body: SERVICE_DOWN }),
  packageShot("package--not-found", null, {}, { status: 404, body: '{"code":"unknown_package"}' }, "/packages/KE-NWWDA-000000-CW-RFB"),
  packageShot("package--moved", comparables(COMPARABLES), { widths: wideAndNarrow, act: type("[data-plan-control] input", "6") }),
  packageShot("package--hover-dot", comparables(COMPARABLES), { widths: wideAndNarrow, act: hoverDot(20) }),
  packageShot("package--focus-dot", comparables(COMPARABLES), { widths: wideAndNarrow, act: focus("[data-dot-target='0']") }),
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

const pages: Shot[] = Object.keys(galleryCopy.pages).map((slug) => ({ name: slug, path: `/gallery/${slug}` }));

export const SHOTS: Shot[] = [
  { name: "index", path: "/gallery" },
  ...pages,

  // The frame: bar, band and footer.
  { name: "navigation--hover-tab", path: "/gallery/navigation", widths: WIDE, act: hover("[data-nav-bar] [data-nav-tab=lessons]") },
  { name: "navigation--focus-tab", path: "/gallery/navigation", widths: WIDE, act: focus("[data-nav-bar] [data-nav-tab=projects]") },
  { name: "navigation--focus-wordmark", path: "/gallery/navigation", act: focus("[data-nav-bar] a[href='/']") },
  { name: "navigation--focus-skip-link", path: "/gallery/navigation", act: (page) => page.keyboard.press("Tab") },
  { name: "navigation--hover-pill", path: "/gallery/navigation", widths: WIDE, act: hover("[aria-haspopup=dialog]") },
  { name: "navigation--focus-pill", path: "/gallery/navigation", widths: WIDE, act: focus("[aria-haspopup=dialog]") },
  { name: "navigation--view-open", path: "/gallery/navigation?view=open", widths: WIDE },
  { name: "navigation--view-loading", path: "/gallery/navigation?view=open&viewer=loading", widths: WIDE },
  { name: "navigation--view-signed-out", path: "/gallery/navigation?view=open&viewer=signed-out", widths: WIDE },
  { name: "navigation--view-error", path: "/gallery/navigation?view=open&viewer=error", widths: WIDE },
  { name: "navigation--hover-menu", path: "/gallery/navigation", widths: NARROW, act: hover("[aria-controls][aria-expanded]:not([aria-haspopup])") },
  { name: "navigation--focus-menu", path: "/gallery/navigation", widths: NARROW, act: focus("[aria-controls][aria-expanded]:not([aria-haspopup])") },
  { name: "navigation--menu-open", path: "/gallery/navigation?menu=open", widths: NARROW },
  { name: "navigation--menu-row-focus", path: "/gallery/navigation?menu=open", widths: NARROW, act: focus("[data-menu-panel] [data-nav-tab=lessons]") },
  { name: "navigation--menu-row-hover", path: "/gallery/navigation?menu=open", widths: NARROW, act: hover("[data-menu-panel] [data-nav-tab=drafts]") },
  { name: "navigation--focus-box", path: "/gallery/navigation", act: focus("[data-box-band] input") },
  { name: "navigation--hover-box", path: "/gallery/navigation", act: hover("[data-box-band] [data-focus-ring]") },
  { name: "navigation--focus-stamp", path: "/gallery/navigation", act: focus("[data-box-band] [data-stamp] a") },
  { name: "navigation--hover-stamp", path: "/gallery/navigation", act: hover("[data-box-band] [data-stamp] a") },
  { name: "navigation--320", path: "/gallery/navigation?menu=open", widths: [320] },

  // Buttons, links and tabs.
  { name: "buttons--hover-primary", path: "/gallery/buttons", act: hover("[data-button=primary]") },
  { name: "buttons--hover-secondary", path: "/gallery/buttons", act: hover("[data-button=secondary]") },
  { name: "buttons--hover-ghost", path: "/gallery/buttons", act: hover("[data-button=ghost]") },
  { name: "buttons--focus-primary", path: "/gallery/buttons", act: focus("[data-button=primary]") },
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
  app("app--view-piu", "/lessons?view=piu"),
  app("app--view-public", "/lessons?view=public"),
  app("app--asof", "/lessons?asof=2016-08-26"),
  app("app--asof-unreadable", "/lessons?asof=last-tuesday"),
  app("app--box-with-text", "/", { }, { act: type("[data-box-band] input", "P130164"), api: { ...app("x", "/").api, ...BOX_API } }),
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
  app("app--hover-selected-tab", "/lessons", {}, { widths: WIDE, act: hover("[data-nav-bar] [aria-current=page]") }),
  app("app--focus-wordmark", "/", {}, { act: focus("[data-nav-bar] a[href='/']") }),
  app("app--focus-empty-link", "/", {}, { act: focus("[data-empty-state] a") }),
  app("app--hover-empty-link", "/", {}, { act: hover("[data-empty-state] a") }),
  app("app--focus-skip-link", "/", {}, { act: (page) => page.keyboard.press("Tab") }),

  // The Data tab (ticket 16): every state of Data readiness, Sources and licenses and How Strata
  // works, and its focus and hover states. The loading states are the gallery's readiness page.
  data("readiness", "/data"),
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
  data("how", "/data/how-strata-works"),
  data("focus-subtab", "/data", undefined, { act: focus("[aria-label='Data pages'] a[href='/data/sources']") }),
  data("hover-subtab", "/data", undefined, { widths: WIDE, act: hover("[aria-label='Data pages'] a[href='/data/sources']") }),
  data("focus-show-all", FILTERED, { recorded: "data-readiness-filtered.json" }, { act: focus("main [data-alert=info] a") }),
  data("term-open", "/data", undefined, { widths: WIDE, act: click("[data-readiness-table=sources] thead [data-term] >> nth=1") }),
  data("focus-num", "/data", undefined, { act: focus("[data-headline] [data-num] >> nth=2") }),
  data("num-window", "/data", undefined, { act: click("[data-headline] [data-num] >> nth=2") }),
  data("hover-num", "/data", undefined, { widths: WIDE, act: hover("[data-cell='awards:linked'] [data-num]") }),
  data("fix-projects-window", "/data", undefined, { widths: WIDE, act: click("[data-fixes] li >> nth=0 >> p.text-small [data-num]") }),
  data("hover-link", "/data", { recorded: "data-readiness-empty.json" }, { act: hover("[data-readiness=empty] a") }),
  data("cards-320", "/data", undefined, { widths: [320] }),
  // Ticket 18: the hardest documents I read, after Sources. The states the fixture does not reach are
  // the server's answers on the fixture with its shelf outcomes changed (tests/record_api.py).
  data("shelf-gap", "/data", { recorded: "data-readiness-shelf-gap.json" }),
  data("shelf-two-gaps", "/data", { recorded: "data-readiness-shelf-two-gaps.json" }),
  data("shelf-abstentions", "/data", { recorded: "data-readiness-shelf-abstentions.json" }),
  data("shelf-empty", "/data", { recorded: "data-readiness-shelf-empty.json" }),
  data("shelf-loading", "/data", undefined, { pending: ["/api/data/readiness"] }),
  data("shelf-focus-link", "/data", undefined, { act: focus("[data-readiness-table=shelf] a:visible") }),
  data("shelf-hover-link", "/data", undefined, { widths: WIDE, act: hover("[data-readiness-table=shelf] [data-table-view=table] a") }),
  data("shelf-term-open", "/data", undefined, { widths: WIDE, act: click("[data-readiness-table=shelf] thead [data-term] >> nth=0") }),
  data("shelf-focus-num", "/data", undefined, { act: focus("[data-readiness-table=shelf] [data-num]:visible") }),
  data("shelf-num-window", "/data", undefined, { act: click(":is([data-cell='p130164_pad:outcome'], [data-card='p130164_pad']) [data-num]:visible >> nth=-1") }),
  data("shelf-holds-link", "/data", { recorded: "data-readiness-shelf-gap.json" }, { act: click("[data-readiness-table=kinds] a[href='#hardest-documents']:visible") }),
  data("read-well-window", "/data", undefined, { widths: WIDE, act: click("[data-cell='reports:read_well'] [data-num]") }),
  data("shelf-cards-320", "/data", { recorded: "data-readiness-shelf-gap.json" }, { widths: [320] }),

  // Ticket 10: Check a plan, a project's page and All projects, in every state the 10 brief
  // lists (section 10), with /api answered from the recordings.
  ...PLAN_SHOTS,
  ...PROJECT_SHOTS,
  ...HUB_SHOTS,
  ...ANSWER_SHOTS,
  ...DRAFT_SHOTS,
  ...PACKAGE_SHOTS,
];
