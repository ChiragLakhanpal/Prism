// The page an answer is asked on, for the screen tests of the answer panel and the evidence drawer
// (ticket 14): P130164's project page with /api answered from tests/fixtures/api, the one box, the
// panel, its markers and the drawer. answer.spec.ts runs these against the production build and
// dev.spec.ts against the development build.
import type { Page, Request } from "@playwright/test";
import { expect, mockApi, recorded, viewAnswers } from "./mocked";
import { animationsDone } from "./settled";

export const QUESTION = "Why were works contracts in P130164 advertised again?";
export const ICR_54 = "strata.gold.passage:31525018/v1/54";

export type Seen = { asked: Request[]; opened: Request[] };

export async function open(
  page: Page,
  { path = "/projects/P130164", stream = "ask-p130164-removed-number.sse", evidence = "evidence-icr-p130164-54.json", width = 1440, status = 200 } = {},
) {
  const seen: Seen = { asked: [], opened: [] };
  page.on("request", (request) => {
    const where = new URL(request.url()).pathname;
    if (where === "/api/ask") seen.asked.push(request);
    if (where === "/api/evidence/opened" && request.method() === "POST") seen.opened.push(request);
  });
  // Every change to the answer's status line, in order, as a screen reader would hear it.
  await page.addInitScript(() => {
    const said: string[] = [];
    (window as unknown as { said: string[] }).said = said;
    new MutationObserver(() => {
      const line = document.querySelector("[data-answer-status]")?.textContent ?? "";
      if (line && said[said.length - 1] !== line) said.push(line);
    }).observe(document, { subtree: true, childList: true, characterData: true });
  });
  await page.setViewportSize({ width, height: 900 });
  await mockApi(page, {
    ...(await viewAnswers()),
    "/api/me": { body: await recorded("me.json") },
    "/api/freshness": { body: await recorded("freshness.json") },
    "/api/projects/P130164": { body: await recorded("project-p130164.json") },
    // Ticket 21: /projects/P130164 is the project's Summary.
    "/api/projects/P130164/summary": { body: await recorded("summary-p130164.json") },
    "/api/ask": { status, body: status === 200 ? await recorded(stream) : '{"detail":"no"}' },
    "/api/evidence": { body: await recorded(evidence) },
    "/api/evidence/opened": { body: '{"opened":[],"recorded":true}' },
  });
  await page.goto(path);
  await expect(page.locator("main h1")).toBeVisible();
  return seen;
}

export const box = (page: Page) => page.locator("[data-box-slot]").getByRole("combobox");
export const panel = (page: Page) => page.getByRole("region", { name: "Answer" });
export const drawer = (page: Page) => page.getByRole("dialog");
export const marker = (page: Page, n: number) => panel(page).locator(`[data-citation="${n}"]`).first();

export async function askFromTheBox(page: Page, question = QUESTION) {
  await page.keyboard.press("/");
  await page.keyboard.type(question);
  await page.keyboard.press("Enter");
}

// The answer has landed and come to rest: its "Prism, in short" block rises 4 px as it fades in (ticket 111), so a
// test measures it, or scans it with axe, once that has ended.
export async function landed(page: Page) {
  await expect(panel(page).locator("[data-answer]:not([data-answer=streaming])")).toBeVisible();
  await animationsDone(page);
}
