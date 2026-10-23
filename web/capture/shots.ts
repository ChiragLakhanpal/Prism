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

const WIDE = [1440, 1024];
const NARROW = [390];

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

  // The production app's shell against the mocked API: signed in, signed out and unreachable.
  { name: "app--signed-in", path: "/", server: "app", api: { "/api/me": { recorded: "me.json" } } },
  {
    name: "app--signed-out",
    path: "/",
    server: "app",
    api: { "/api/me": { body: '{"email":null,"name":null,"signed_in":false,"has_token":false}' } },
  },
  { name: "app--unreachable", path: "/", server: "app", api: { "/api/me": { status: 502, body: '{"detail":"Bad Gateway"}' } } },
  {
    name: "app--focus-retry",
    path: "/",
    server: "app",
    api: { "/api/me": { status: 502, body: '{"detail":"Bad Gateway"}' } },
    act: focus("[role=alert] button"),
  },
  { name: "app--focus-skip-link", path: "/", server: "app", api: { "/api/me": { recorded: "me.json" } }, act: (page) => page.keyboard.press("Tab") },
];
