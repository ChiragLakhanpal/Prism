// What the capture command photographs (npm --prefix web run capture). Each shot is a page in
// one state, taken at 1440, 1024 and 390 px unless it names its own widths. Gallery shots
// open the design gallery; app shots open the production build with /api answered from the
// recordings in tests/fixtures/api, so design reviews are repeatable. To review a new screen,
// add its routes and states here.
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

// The app's routes, as the 06 design brief lists them, and both not-found pages.
const ROUTES: [string, string][] = [
  ["home", "/"],
  ["packages", "/packages"],
  ["package", "/packages/KE-NWWDA-541055-CW-RFB"],
  ["projects", "/projects"],
  ["project", "/projects/P130164"],
  ["activity", "/projects/P130164/packages/IN-RRSMP-7431-CW-RFB"],
  ["document", "/projects/P130164/documents/icr?page=23&para=54"],
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
  app("app--view-piu", "/projects?view=piu"),
  app("app--view-public", "/projects?view=public"),
  app("app--asof", "/projects?asof=2016-08-26"),
  app("app--asof-unreadable", "/projects?asof=last-tuesday"),
  app("app--box-with-text", "/", {}, { act: type("[data-box-band] input", "P130164") }),
  app("app--view-open", "/", {}, { widths: WIDE, act: click("[aria-haspopup=dialog]") }),
  app("app--view-error", "/", { me: { status: 502, body: '{"detail":"Bad Gateway"}' } }, { widths: WIDE, act: click("[aria-haspopup=dialog]") }),
  app("app--menu-open", "/projects/P130164", {}, { widths: NARROW, act: click("[aria-controls][aria-expanded]:not([aria-haspopup])") }),
  app("app--1024-with-scrollbar", "/projects", {}, {
    widths: [1024],
    act: async (page) => {
      await page.addStyleTag({ content: "body { margin-right: 15px; }" });
    },
  }),
  app("app--320", "/projects/P130164/packages/IN-RRSMP-7431-CW-RFB", {}, { widths: [320] }),
  app("app--hover-selected-tab", "/projects", {}, { widths: WIDE, act: hover("[data-nav-bar] [aria-current=page]") }),
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
];
