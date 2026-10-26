// Every route of docs/PLAN.md section 8 except the deck, the pages ticket 10 built and the Data
// tab, whose pages ticket 16 filled (tests/data.spec.ts) (seam 4, ticket 06): each states its title
// and its purpose, shows the empty state that says what will appear there, and sits in the frame
// with the footer. Unknown addresses show a not-found page in the same frame. The words are the
// 06 design brief's, copied here so the test checks the copy file against an independent source.
import { scan } from "./axe";
import type { Page } from "@playwright/test";
import { footerSentence } from "./design-md";
import { expect, mockApi, mockShell, recorded, test } from "./mocked";

type Route = {
  path: string;
  h1: string;
  purpose: string;
  tab?: string;
  empty?: { title: string; body: string; link?: [string, string] };
  link?: [string, string];
  // /api answers the page reads beyond the shell's, such as the Drafts tab's list (ticket 35).
  api?: Record<string, string>;
};

const DATA_LINK: [string, string] = ["Go to Data", "/data"];

export const ROUTES: Route[] = [
  // Home is built in ticket 41; web/tests/home.spec.ts tests it.
  // All projects and a project's page are built in ticket 10; web/tests/projects.spec.ts tests them.
  // The package workspace is built in ticket 12; web/tests/package.spec.ts tests it. The Packages tab and a
  // package planned from a sentence are built in ticket 15; web/tests/planned-package.spec.ts tests them. The
  // source view at /projects/:pid/documents/:doc is built in ticket 21; web/tests/hub.spec.ts tests it. The activity
  // page at /projects/:pid/packages/:stepRef is built in ticket 22; web/tests/trail.spec.ts tests it.
  {
    path: "/lessons",
    h1: "Lessons",
    tab: "Lessons",
    purpose:
      "Each lesson comes from a completion report or its review, quoted word for word with its page. A lead procurement specialist decides which lessons enter the library.",
    empty: {
      title: "There are no lessons in the library yet.",
      body: "A lesson appears here after I read a completion report and a lead procurement specialist decides it belongs.",
      link: DATA_LINK,
    },
    // Ticket 29: the library, empty, as anyone who is not a lesson reviewer reads it (tests/fixtures/api,
    // lessons-me-viewer.json), in ticket 39's page answer (lessons-page-empty.json).
    api: {
      "/api/lessons/me": '{"signed_in":true,"tabs":["library"],"acts":[],"regions":[],"role":null,"waiting":null}',
      "/api/lessons/page":
        '{"view":"staff","as_of":null,"visit":{"first_visit":true,"last_visit_on":null},' +
        '"digest":{"kind":"first","segments":[{"text":"This is your first visit to Lessons. The library has no lessons yet."}],' +
        '"counts":{"total":0,"proposed":0},"items":{},"strengthened":null},"notices":[],"new_lessons":null,' +
        '"feedback":{"never":true,"segments":null,"counts":null},"library":{"as_of":"2026-10-22","page":1,"pages":1,' +
        '"page_size":8,"total":0,"of":0,"from":0,"to":0,"status":"current","filters":{"stage":null,"method":null,' +
        '"sector":null,"status":null},"narrowed":false,"unknown_filter":false,"shown":null,"options":{"stage":[],' +
        '"method":[],"sector":[],"status":[]},"count":[],"can_recheck":false,"limits":{"reason_max_chars":500},' +
        '"waiting":null,"lessons":[]}}',
    },
  },
  {
    path: "/drafts",
    h1: "Drafts",
    tab: "Drafts",
    purpose:
      "I write drafts for you to check, such as review notes and suggested rows for the borrower's Project Procurement Strategy for Development (PPSD). Only you can mark a draft as checked or export it, and exporting sends nothing.",
    empty: {
      title: "You have no drafts to check.",
      body: "When you check a plan or plan a package, I can draft review notes or PPSD rows, and they wait here for you to check.",
      link: ["Go to Packages", "/packages"],
    },
    // Ticket 35 built the Drafts tab: with no drafts, it shows brief 06's empty-state card.
    api: { "/api/drafts": '{"groups":{"to_check":[],"checked":[],"exported":[]},"counts":{"to_check":0,"checked":0,"exported":0},"discarded":[],"discarded_count":0,"total":0}' },
  },
];

const NOT_FOUND: Route[] = [
  {
    path: "/nowhere",
    h1: "Page not found",
    purpose: "I don't have a page at this address. Check the address, or go to Home.",
    link: ["Go to Home", "/"],
  },
  // The deck belongs to ticket 47. Until then its address is not found, and nothing links to it.
  {
    path: "/present",
    h1: "Page not found",
    purpose: "I don't have a page at this address. Check the address, or go to Home.",
    link: ["Go to Home", "/"],
  },
  {
    path: "/projects/130164",
    h1: "Page not found",
    purpose: "This address doesn't name a project. A project ID is the letter P followed by six digits.",
    link: ["Go to Projects", "/projects"],
  },
];

async function open(page: Page, path: string, width = 1440) {
  await mockShell(page);
  await page.setViewportSize({ width, height: 900 });
  await page.goto(path);
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
}

for (const route of [...ROUTES, ...NOT_FOUND]) {
  test(`${route.path} states its title and purpose, shows what will appear there, and carries the footer`, async ({ page }) => {
    const unrecorded = await mockApi(page, {
      "/api/me": { body: await recorded("me.json") },
      "/api/freshness": { body: await recorded("freshness.json") },
      ...Object.fromEntries(Object.entries(route.api ?? {}).map(([path, body]) => [path, { body }])),
    });
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto(route.path);

    const main = page.getByRole("main");
    await expect(main.getByRole("heading", { level: 1 })).toHaveText(route.h1);
    await expect(page).toHaveTitle(`${route.h1} | Strata`);
    await expect(main.getByText(route.purpose, { exact: true })).toBeVisible();
    const card = main.locator("[data-empty-state]");
    if (route.empty) {
      await expect(card).toHaveCount(1);
      await expect(card.getByRole("heading", { level: 2 })).toHaveText(route.empty.title);
      await expect(card.getByText(route.empty.body, { exact: true })).toBeVisible();
      await expect(card.getByRole("link")).toHaveCount(route.empty.link ? 1 : 0);
      if (route.empty.link) {
        await expect(card.getByRole("link", { name: route.empty.link[0], exact: true })).toHaveAttribute("href", route.empty.link[1]);
      }
    } else {
      await expect(card).toHaveCount(0);
      await expect(main.getByRole("link", { name: route.link![0], exact: true })).toHaveAttribute("href", route.link![1]);
    }
    await expect(page.getByRole("contentinfo")).toHaveText(await footerSentence());
    const selected = page.getByRole("navigation", { name: "Main" }).locator("[aria-current=page]");
    if (route.tab) await expect(selected).toHaveText(route.tab);
    else await expect(selected).toHaveCount(0);
    await expect(page.locator('a[href*="/present"]')).toHaveCount(0);
    expect(unrecorded).toEqual([]);
  });
}

test("IDs from the address render in Roboto Mono", async ({ page }) => {
  await open(page, "/projects/P130164/packages/IN-RRSMP-7431-CW-RFB");

  const id = page.getByRole("heading", { level: 1 }).getByText("IN-RRSMP-7431-CW-RFB");
  expect(await id.evaluate((el) => [getComputedStyle(el).fontFamily.split(",")[0], getComputedStyle(el).fontWeight])).toEqual([
    '"Roboto Mono"',
    "500",
  ]);
});

test("a lowercase p in a project ID is read as P, and the address is rewritten in place", async ({ page }) => {
  await open(page, "/projects/p130164/packages/IN-RRSMP-7431-CW-RFB");

  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Activity IN-RRSMP-7431-CW-RFB");
  expect(new URL(page.url()).pathname).toBe("/projects/P130164/packages/IN-RRSMP-7431-CW-RFB");
});

test("a tab opens its page without reloading, moves focus to the new title and updates the page title", async ({ page }) => {
  await open(page, "/");
  await page.evaluate(() => ((window as unknown as { stillHere: boolean }).stillHere = true));
  await page.evaluate(() => window.scrollTo(0, 400));

  await page.getByRole("navigation", { name: "Main" }).getByRole("link", { name: "Lessons" }).click();

  const title = page.getByRole("heading", { level: 1 });
  await expect(title).toHaveText("Lessons");
  await expect(title).toBeFocused();
  await expect(page).toHaveTitle("Lessons | Strata");
  expect(new URL(page.url()).pathname).toBe("/lessons");
  expect(await page.evaluate(() => (window as unknown as { stillHere?: boolean }).stillHere)).toBe(true);
  expect(await page.evaluate(() => window.scrollY)).toBe(0);
  await expect(page.getByRole("navigation", { name: "Main" }).locator("[aria-current=page]")).toHaveText("Lessons");

  await page.goBack();
  await expect(title).toContainText("Your briefing for");
  await expect(page.getByRole("link", { name: "Strata", exact: true })).toHaveAttribute("aria-current", "page");
});

test("the stamp is read once per page load and kept across route changes", async ({ page }) => {
  let reads = 0;
  await mockShell(page);
  await page.route("**/api/freshness", async (route) => {
    reads += 1;
    await route.fulfill({ status: 200, contentType: "application/json", body: '{"data_through": "2026-10-21"}' });
  });
  await page.goto("/");
  await expect(page.locator("[data-stamp]")).toContainText("Data through");

  for (const tab of ["Packages", "Projects", "Data"]) {
    await page.getByRole("navigation", { name: "Main" }).getByRole("link", { name: tab }).click();
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(tab);
  }

  expect(reads).toBe(1);
});

test("below 768 px a labeled Menu holds the tabs; a row opens its page, closes the Menu and focuses the title", async ({ page }) => {
  await open(page, "/", 390);
  const menu = page.getByRole("button", { name: "Menu" });
  await expect(page.getByRole("navigation", { name: "Main" })).toHaveCount(0);

  await menu.click();
  const nav = page.getByRole("navigation", { name: "Main" });
  await expect(nav.getByRole("link")).toHaveText(["Packages", "Projects", "Lessons", "Drafts", "Data"]);
  await nav.getByRole("link", { name: "Drafts" }).click();

  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Drafts");
  await expect(page.getByRole("heading", { level: 1 })).toBeFocused();
  await expect(menu).toHaveAttribute("aria-expanded", "false");
  await menu.click();
  await expect(page.getByRole("navigation", { name: "Main" }).locator("[aria-current=page]")).toHaveText("Drafts");
});

test("at 1024 px with a 15 px scrollbar the navy bar fits on one line", async ({ page }) => {
  // Playwright's Chromium hides scrollbars. A classic scrollbar takes 15 px from the page while
  // the breakpoints still see the whole 1024 px window, which a 15 px right margin on the body
  // reproduces.
  await open(page, "/projects", 1024);
  await page.addStyleTag({ content: "body { margin-right: 15px; }" });
  expect(await page.evaluate(() => document.body.getBoundingClientRect().width)).toBe(1009);

  const bar = page.locator("[data-nav-bar] > .layout");
  expect(await bar.evaluate((el) => el.scrollWidth <= el.clientWidth)).toBe(true);
  expect((await page.locator("[data-nav-bar]").boundingBox())!.height).toBe(56);
  const heights = await page.getByRole("navigation", { name: "Main" }).getByRole("link").evaluateAll((links) =>
    links.map((link) => link.getBoundingClientRect().height),
  );
  expect(heights).toEqual([40, 40, 40, 40, 40]);
  await expect(page.getByRole("button", { name: "View: World Bank staff" })).toBeVisible();
});

for (const route of [...ROUTES, ...NOT_FOUND]) {
  test(`${route.path}: a skip link leads, it reflows at 320 px, and axe finds no WCAG 2.2 AA violations`, async ({ page }) => {
    await open(page, route.path, 1440);
    await page.keyboard.press("Tab");
    const skip = page.getByRole("link", { name: "Skip to main content", exact: true });
    await expect(skip).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(page.getByRole("main")).toBeFocused();

    const check = async () =>
      (await scan(page)).violations.map(
        (v) => `${v.id}: ${v.nodes.map((node) => node.target.join(" ")).join(", ")}`,
      );
    expect(await check(), "1440 px").toEqual([]);
    await page.setViewportSize({ width: 390, height: 900 });
    expect(await check(), "390 px").toEqual([]);
    await page.setViewportSize({ width: 320, height: 900 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(320);
  });
}
