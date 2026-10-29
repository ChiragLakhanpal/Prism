// The ProjectId rule (ticket 21; the 21 brief, section 9): every P-code anywhere in the app is a link to
// its project page. This sweep opens every route with the responses recorded from the server on the
// fixture, at 1440 px, asks a question once and opens the evidence drawer from its citation, and finds
// every P and six digits in the page's text. Each must sit inside a link whose path is /projects/{that
// ID} or under it, unless it is in one of the places PROJECT_ID_EXEMPT names: text a person typed, the one
// box's scope chip, and visually hidden text that repeats a link on screen. The page's <title> is outside
// the body. The test lists every offender with its route.
import type { Page } from "@playwright/test";
import { PROJECT_ID_EXEMPT } from "../src/lib/projectId";
import { askFromTheBox, landed, marker } from "./answer-page";
import { hubApi } from "./hub-api";
import { trailApi } from "./trail-api";
import { expect, mockApi, recorded, test } from "./mocked";
import { labelProblems } from "./designed-not-built";
import { readRegistry, type DesignedNotBuiltRegistry } from "./registries";

type Answer = { status?: number; body: string };

const NWWDA = "/projects/P156634/procurement/northern-water-works-development-agency";
const PACKAGE = "/packages/KE-NWWDA-541055-CW-RFB";
const LESSON_ITEM = "new-e903b07ad1";

async function everyRecording(): Promise<Record<string, Answer>> {
  const file = async (name: string) => ({ body: await recorded(name) });
  return {
    ...(await trailApi()),
    ...(await hubApi()),
    "/api/ask": await file("ask-p130164-removed-number.sse"),
    // Ticket 41: Home with Ana's examples, whose Start here links name P-codes inside their own words.
    "/api/home": await file("home.json"),
    "/api/projects": await file("projects.json"),
    "/api/following": await file("following-p156634.json"),
    "/api/projects?q=india": await file("projects-india.json"),
    "/api/projects/P156634": await file("project-p156634-baseline.json"),
    "/api/projects/P156634/summary": await file("summary-p156634.json"),
    "/api/projects/P156634/packages": await file("packages-p156634.json"),
    [`/api${NWWDA}/2026-10-09`]: await file("check-plan-p156634-nwwda-2026-10-09-baseline.json"),
    [`/api${NWWDA}/2026-10-09/changes`]: await file("changes-nwwda-2026-10-09.json"),
    "/api/drafts/existing": { body: '{"draft":null}' },
    "/api/drafts": await file("drafts-list.json"),
    "/api/drafts/draft-0001": await file("drafts-review-notes-draft.json"),
    [`/api${PACKAGE}`]: await file("package-ke-nwwda-541055.json"),
    [`/api${PACKAGE}/comparables`]: await file("comparables-ke-nwwda-541055.json"),
    "/api/data/readiness": await file("data-readiness.json"),
    "/api/data/sources": await file("data-sources.json"),
    "/api/lessons/me": await file("lessons-me-reviewer.json"),
    "/api/lessons/page": await file("lessons-page-reviewer.json"),
    "/api/lessons/review": await file("lessons-queue.json"),
    [`/api/lessons/review/${LESSON_ITEM}`]: await file("lessons-item-recommend.json"),
  };
}

// Every P-code in the page's text that is not a link to its project page, outside the exempt places.
async function offenders(page: Page): Promise<string[]> {
  return page.evaluate((exempt) => {
    const found: string[] = [];
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    for (let node = walker.nextNode(); node; node = walker.nextNode()) {
      const text = node.textContent ?? "";
      const ids = text.match(/\bP\d{6}\b/g);
      const parent = node.parentElement;
      if (!ids || !parent || parent.closest(exempt.join(", "))) continue;
      // Only text a reader can see: not in a closed fold, a hidden view or an unopened popover.
      if (parent.getClientRects().length === 0 || getComputedStyle(parent).visibility === "hidden") continue;
      const link = parent.closest("a");
      const path = link ? new URL(link.href).pathname : "";
      for (const id of ids) {
        if (path !== `/projects/${id}` && !path.startsWith(`/projects/${id}/`)) found.push(`${id} in "${text.trim().slice(0, 70)}"`);
      }
    }
    return found;
  }, PROJECT_ID_EXEMPT);
}

// Every link, menu item or button on the page whose address or action names /present.
async function deckLinks(page: Page): Promise<string[]> {
  return page.evaluate(() =>
    [...document.querySelectorAll("a[href], [role=menuitem], [data-href], form[action]")]
      .map((element) => element.getAttribute("href") ?? element.getAttribute("data-href") ?? element.getAttribute("action") ?? "")
      .filter((href) => /(^|\/)present(\/|$|[?#])/.test(new URL(href, location.origin).pathname + "/")),
  );
}

const ROUTES: [string, string][] = [
  ["/", "[data-home=ready]"],
  ["/packages", "main h1"],
  ["/lessons", "[data-library=ready]"],
  ["/lessons/review", "[data-queue=ready]"],
  [`/lessons/review/${LESSON_ITEM}`, `[data-review-page="${LESSON_ITEM}"]`],
  ["/projects", "[data-projects-page=ready]"],
  ["/projects?q=india", "[data-projects-page=ready]"],
  // Ticket 37: Following, whose rows' meta lines set the P-code in plain mono beside the heading's link.
  ["/projects/following", "[data-following-page=ready]"],
  ["/projects/P130164", "[data-summary=ready]"],
  ["/projects/P130164/procurement", "[data-procurement-tab=ready]"],
  ["/projects/P130164/documents", "[data-documents=ready]"],
  ["/projects/P130164/documents/icr-2019-10-10?page=23&para=54", "[data-source-page=read]"],
  ["/projects/P130164/documents/icr-review-2023-05-04?page=1", "[data-source-page=read]"],
  ["/projects/P156634", "[data-summary=ready]"],
  ["/projects/P156634/procurement", "[data-packages=ready]"],
  [`${NWWDA}/2026-10-09`, "[data-changes]"],
  // Ticket 22: the activity page and the Connections tab.
  ["/projects/P130164/packages/IN-RRSMP-7431-CW-RFB", "[data-activity-page=ready]"],
  ["/projects/P156634/packages/KE-NWWDA-229129-CW-RFB", "[data-activity-page=ready]"],
  ["/projects/P130164/connections", "[data-connections=ready]"],
  ["/projects/P156634/connections", "[data-connections=ready]"],
  [PACKAGE, "[data-past-range]:not([data-past-range=loading])"],
  ["/drafts", "main h1"],
  ["/drafts/draft-0001", "[data-draft-page]:not([data-draft-page=loading])"],
  ["/data", "main h1"],
  ["/data/sources", "main h1"],
  ["/projects/130164", "main h1"],
];

// Ticket 47: the app's other pages, which the P-code and label checks above do not cover, opened only to show that
// none of them links to the deck either. Each opens with the recordings and the ready marker its own spec uses, so
// the page is the one that spec checks: the Timeline tab (timeline.spec.ts), Passage reports and Judging
// (retrieval-pages.spec.ts), Check my plan and an upload's check (uploads.spec.ts), a package planned from a sentence
// (planned-package.spec.ts), a reload of the writing page (drafts.spec.ts) and the not-found page (routes.spec.ts).
const PLANNED = "pkg-000000000001";
const PASSAGE_GROUP = "grp-6fa04e510789";
const JUDGING_QUERY = "nq-rural-works-delays";
const PLANNED_COMPARABLES = "/api/comparables?category=Works&country=KE&method=Request+for+";

async function deckOnlyRoutes(): Promise<[string, string, Record<string, Answer>][]> {
  const file = async (name: string) => ({ body: await recorded(name) });
  const reviewer = { "/api/lessons/me": await file("retrieval-me-passage-reviewer-waiting.json") };
  const judge = { "/api/lessons/me": await file("retrieval-me-judge-after.json") };
  const officer = { "/api/me": await file("me-officer.json") };
  return [
    ["/projects/P130164/timeline", "[data-timeline=ready]", { "/api/projects/P130164/timeline": await file("timeline-p130164.json") }],
    ["/lessons/reports", "[data-reports-lead]", { ...reviewer, "/api/lessons/page": await file("lessons-page-empty.json"), "/api/passage-reports": await file("passage-reports.json") }],
    [`/lessons/reports/${PASSAGE_GROUP}`, `[data-report-page="${PASSAGE_GROUP}"]`, { ...reviewer, [`/api/passage-reports/${PASSAGE_GROUP}`]: await file("passage-report.json") }],
    ["/lessons/judging", "[data-judging=ready]", { ...judge, "/api/judging/queries": await file("judging-queries.json") }],
    [`/lessons/judging/${JUDGING_QUERY}`, `[data-judging-query="${JUDGING_QUERY}"]`, { ...judge, [`/api/judging/queries/${JUDGING_QUERY}`]: await file("judging-query.json") }],
    ["/packages/check", "[data-upload-card]", { ...officer, "/api/uploads/form": await file("uploads-form-officer.json") }],
    ["/packages/uploads/upl-000000000001", "[data-upload-check-page=ready]", { ...officer, "/api/uploads/upl-000000000001": await file("upload-check-nwwda.json") }],
    // A reload of the reading page goes to the Packages tab.
    // Plan mode's placeholder has a short form below 768 px (ticket 58), so the one that shows is the wide one here.
    ["/packages/new", "[data-box-slot] [data-placeholder]:not(.md\\:hidden)", { "/api/planned-packages": await file("planned-packages-empty.json") }],
    [`/packages/${PLANNED}`, "[data-planned-package]:not([data-planned-package=loading])", {
      [`/api/planned-packages/${PLANNED}`]: await file("planned-package-rural-roads.json"),
      [`/api/planned-packages/${PLANNED}/risks`]: await file("risks-planned-rural-roads.json"),
      [`/api/planned-packages/${PLANNED}/steps`]: await file("steps-planned-rural-roads.json"),
      [`${PLANNED_COMPARABLES}Bids`]: await file("comparables-planned-works-rfb-ke.json"),
      [`${PLANNED_COMPARABLES}Quotations`]: await file("comparables-planned-works-rfq-ke.json"),
    }],
    [`/drafts/new?kind=review_notes&pid=P156634&agency=northern-water-works-development-agency&version=2026-10-09`, "[data-draft-new=none]", {}],
    ["/not-a-page", "main h1", {}],
  ];
}

test("every P-code on every route is a link to its project page, with the drawer opened from a citation", async ({ page }) => {
  test.setTimeout(60_000);
  await page.setViewportSize({ width: 1440, height: 900 });
  await mockApi(page, await everyRecording());
  const found: string[] = [];
  const labels: { route: string; key: string }[] = [];
  // Ticket 47: nothing in the app links to the deck at /present, on any route, in any link or menu item.
  const toDeck: string[] = [];
  for (const [path, ready] of ROUTES) {
    await page.goto(path);
    await expect(page.locator(ready).first()).toBeVisible();
    found.push(...(await offenders(page)).map((offender) => `${path}: ${offender}`));
    toDeck.push(...(await deckLinks(page)).map((link) => `${path}: ${link}`));
    for (const key of await page.locator("[data-dnb]").evaluateAll((els) => els.map((el) => el.getAttribute("data-dnb") ?? ""))) {
      labels.push({ route: path, key });
    }
  }
  // An answer, and the drawer opened from its first citation, on a project's page.
  await page.goto("/projects/P130164");
  await expect(page.locator("[data-summary=ready]")).toBeVisible();
  await askFromTheBox(page);
  await landed(page);
  await marker(page, 1).click();
  await expect(page.getByRole("dialog").getByRole("heading", { level: 2 })).toBeVisible();
  found.push(...(await offenders(page)).map((offender) => `answer and drawer: ${offender}`));
  // A Summary record in the drawer, opened from its marker.
  await page.goto("/projects/P130164");
  await page.locator("[data-fact=closing_date] [data-citation]").click();
  await expect(page.getByRole("dialog").getByRole("heading", { level: 2 })).toBeVisible();
  found.push(...(await offenders(page)).map((offender) => `record drawer: ${offender}`));

  expect(found).toEqual([]);

  // Below 1024 px the tabs move into the Menu (DESIGN.md section 4): its items link nowhere near the deck either.
  await page.setViewportSize({ width: 1000, height: 900 });
  await page.goto("/");
  await page.getByRole("button", { name: "Menu", exact: true }).click();
  await expect(page.getByRole("button", { name: "Menu", exact: true })).toHaveAttribute("aria-expanded", "true");
  toDeck.push(...(await deckLinks(page)).map((link) => `Menu: ${link}`));

  // The pages the P-code sweep does not open, each with its own recordings: no link to the deck there either.
  await page.setViewportSize({ width: 1440, height: 900 });
  const recordings = await everyRecording();
  for (const [path, ready, answers] of await deckOnlyRoutes()) {
    await page.unrouteAll();
    await mockApi(page, { ...recordings, ...answers });
    await page.goto(path);
    await expect(page.locator(ready).first(), path).toBeVisible();
    toDeck.push(...(await deckLinks(page)).map((link) => `${path}: ${link}`));
  }
  expect(toDeck).toEqual([]);

  const items = readRegistry<DesignedNotBuiltRegistry>("designed_not_built.toml").items ?? [];
  expect(labelProblems(labels, items, ROUTES.map(([path]) => path))).toEqual([]);
});

test("the label check fails on a label with no entry, an entry with no label at its route, and a route the sweep skips", () => {
  const items = [
    { key: "hazard_model", route: "/projects/P156634" },
    { key: "word_add_in", route: "/drafts/new" },
  ];
  const labels = [
    { route: "/projects/P156634", key: "hazard_model" },
    { route: "/data", key: "teams_channel" },
  ];
  expect(labelProblems(labels, items, ["/projects/P156634", "/data"])).toEqual([
    'teams_channel is labeled "Designed, not built" in Strata at /data but is missing from the proposal\'s list.',
    "word_add_in is in the proposal's list at /drafts/new, which web/tests/sweep.spec.ts does not open. Add the route to ROUTES there.",
  ]);
  expect(labelProblems([], [items[0]], ["/projects/P156634"])).toEqual([
    "hazard_model is in the proposal's list, but Strata shows no label at /projects/P156634.",
  ]);
  expect(labelProblems(labels.slice(0, 1), items.slice(0, 1), ["/projects/P156634"])).toEqual([]);
});
