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
    "/api/projects": await file("projects.json"),
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
    "/api/lessons": await file("lessons-library-reviewer.json"),
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

const ROUTES: [string, string][] = [
  ["/", "main h1"],
  ["/packages", "main h1"],
  ["/lessons", "[data-library=ready]"],
  ["/lessons/review", "[data-queue=ready]"],
  [`/lessons/review/${LESSON_ITEM}`, `[data-review-page="${LESSON_ITEM}"]`],
  ["/projects", "[data-projects-page=ready]"],
  ["/projects?q=india", "[data-projects-page=ready]"],
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

test("every P-code on every route is a link to its project page, with the drawer opened from a citation", async ({ page }) => {
  test.setTimeout(60_000);
  await page.setViewportSize({ width: 1440, height: 900 });
  await mockApi(page, await everyRecording());
  const found: string[] = [];
  for (const [path, ready] of ROUTES) {
    await page.goto(path);
    await expect(page.locator(ready).first()).toBeVisible();
    found.push(...(await offenders(page)).map((offender) => `${path}: ${offender}`));
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
});
