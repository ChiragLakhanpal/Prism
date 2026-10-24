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
// project's page and Check a plan have their own shots below (ticket 10).
const ROUTES: [string, string][] = [
  ["home", "/"],
  ["packages", "/packages"],
  ["package", "/packages/KE-NWWDA-541055-CW-RFB"],
  ["activity", "/projects/P130164/packages/IN-RRSMP-7431-CW-RFB"],
  ["document", "/projects/P130164/documents/icr?page=23&para=54"],
  ["lessons", "/lessons"],
  ["drafts", "/drafts"],
  ["data", "/data"],
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
const planShot = (name: string, answer: Answer, rest: Partial<Shot> = {}, path = PLAN): Shot =>
  app(name, path, {}, { ...rest, api: { ...app(name, path).api, [`/api${path.split("#")[0]}`]: answer } });
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
  planShot("check-plan--focus-breadcrumb", plan, { widths: [1440, 390], act: focus("[data-breadcrumb] a:visible") }),
  planShot("check-plan--deep-link", plan, {}, `${PLAN}#KE-NWWDA-207796-CS-INDV`),
  planShot("check-plan--320", plan, { widths: [320] }),
];

const PROJECT_SHOTS: Shot[] = [
  planShot("project", { recorded: "project-p156634.json" }, {}, "/projects/P156634"),
  planShot("project--loading", { recorded: "project-p156634.json" }, { pending: ["/api/projects/P156634"] }, "/projects/P156634"),
  planShot("project--no-plans", { recorded: "project-p130164.json" }, {}, "/projects/P130164/procurement"),
  planShot("project--error", { status: 503, body: SERVICE_DOWN }, {}, "/projects/P156634"),
  planShot("project--not-found", { status: 404, body: '{"code":"unknown_project"}' }, {}, "/projects/P999999"),
  planShot("project--focus-version", { recorded: "project-p156634.json" }, { widths: [1440, 390], act: focus("[data-agency] a:visible") }, "/projects/P156634"),
  planShot("projects", { recorded: "projects.json" }, {}, "/projects"),
  planShot("projects--loading", { recorded: "projects.json" }, { pending: ["/api/projects"] }, "/projects"),
  planShot("projects--more", { recorded: "projects.json" }, { act: click("[data-projects-page] button") }, "/projects"),
  planShot("projects--empty", { body: '{"as_of":"2026-10-23","total":0,"rows":[],"records_through":null}' }, {}, "/projects"),
  planShot("projects--error", { status: 503, body: SERVICE_DOWN }, {}, "/projects"),
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
  { name: "buttons--focus-disabled", path: "/gallery/buttons", act: focus("[data-state-section=disabled] button") },
  { name: "links--hover-link", path: "/gallery/links", act: hover("[data-state-section=text-link] a") },
  { name: "links--focus-link", path: "/gallery/links", act: focus("[data-state-section=text-link] a") },
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
  app("app--box-with-text", "/", {}, { act: type("[data-box-band] input", "P130164") }),
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

  // Ticket 10: Check a plan, a project's page and All projects, in every state the 10 brief
  // lists (section 10), with /api answered from the recordings.
  ...PLAN_SHOTS,
  ...PROJECT_SHOTS,
];
