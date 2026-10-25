// Lessons > Passage reports and Lessons > Judging (ticket 32) at seam 4, against the answers the server wrote on the
// fixture (tests/record_retrieval_api.py), which tests/test_retrieval_recordings.py checks the server still gives.
// The words are the ticket's and the 32 design brief's, copied here so the test checks the copy file.
import { scan } from "./axe";
import type { Page } from "@playwright/test";
import { expect, recorded, recordingFor, test } from "./mocked";

type Answer = { status?: number; body: string };

async function file(name: string): Promise<Answer> {
  const parsed = JSON.parse(await recorded(name));
  return parsed.status && parsed.body ? { status: parsed.status, body: JSON.stringify(parsed.body) } : { body: JSON.stringify(parsed) };
}

// Serve /api from recorded answers by "METHOD /path" or by path, and list what the page sent.
async function serve(page: Page, answers: Record<string, Answer>, width = 1440) {
  await page.setViewportSize({ width, height: 900 });
  const sent: { method: string; path: string; body: unknown }[] = [];
  const all: Record<string, Answer> = {
    "/api/me": { body: await recorded("me.json") },
    "/api/freshness": { body: await recorded("freshness.json") },
    ...answers,
  };
  await page.route("**/api/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    sent.push({ method: request.method(), path: url.pathname, body: request.postDataJSON?.() ?? null });
    const answer = all[`${request.method()} ${url.pathname}`] ?? recordingFor(all, url);
    if (!answer) return route.fulfill({ status: 404, json: { detail: "Not Found" } });
    return route.fulfill({ status: answer.status ?? 200, contentType: "application/json", body: answer.body });
  });
  return sent;
}

async function axe(page: Page) {
  await page.waitForFunction(() => document.getAnimations().every((a) => a.playState !== "running" || a.effect?.getTiming().iterations === Infinity));
  const results = await scan(page);
  return results.violations.map((v) => `${v.id}: ${v.nodes.map((node) => node.target.join(" ")).join(", ")}`);
}

const subTabs = (page: Page) => page.getByRole("navigation", { name: "Lesson pages" });

test("a passage reviewer sees Lessons and Passage reports, and a query judge Lessons and Judging, each with the page's own count", async ({ page }) => {
  await serve(page, {
    "/api/lessons/me": await file("retrieval-me-passage-reviewer-waiting.json"),
    "/api/lessons": await file("lessons-library-empty.json"),
    "/api/passage-reports": await file("passage-reports.json"),
  });
  await page.goto("/lessons/reports");
  await expect(subTabs(page).getByRole("link")).toHaveText(["Lessons", "Passage reports (2)"]);
  await expect(subTabs(page).getByRole("link", { name: "Passage reports (2)" })).toHaveAttribute("aria-current", "page");
  await expect(page.locator("[data-reports-lead]")).toContainText("Reports on two passages are waiting for you.");

  await page.unrouteAll();
  await serve(page, {
    "/api/lessons/me": await file("retrieval-me-judge-after.json"),
    "/api/judging/queries": await file("judging-queries.json"),
  });
  await page.goto("/lessons/judging");
  await expect(subTabs(page).getByRole("link")).toHaveText(["Lessons", "Judging (2)"]);
  await expect(page.getByRole("radio", { name: "To judge (2)" })).toBeVisible();
});

test("Passage reports lists the groups waiting, oldest first, and the decisions of the last 90 days", async ({ page }) => {
  await serve(page, {
    "/api/lessons/me": await file("retrieval-me-passage-reviewer-decided.json"),
    "/api/passage-reports": await file("passage-reports-decided.json"),
  });
  await page.goto("/lessons/reports");
  await expect(page.locator("[data-reports-lead]")).toHaveText("Reports on one passage are waiting for you. The oldest came in on October 23, 2026.");
  // The sub-tab counts what the lead says is waiting for you.
  await expect(subTabs(page).getByRole("link", { name: "Passage reports (1)" })).toBeVisible();
  await expect(page.getByText("Ranking a paragraph lower changes only questions like the ones in its reports. I never hide a paragraph, and I still show it when it is the only source.")).toBeVisible();
  const row = page.locator("[data-report-row]").first();
  await expect(row).toContainText("Wrong passage · needs your review");
  await expect(row.getByRole("heading", { level: 3 })).toHaveText("Rajasthan Road Sector Modernization, paragraph 55");
  await expect(page.getByRole("heading", { name: "Decided in the last 90 days" })).toBeVisible();
  await expect(page.locator("[data-reports-decided]")).toContainText("Ranked lower");
  await expect(page.locator("[data-reports-decided]")).toContainText("Showing 1 decision, newest first");
  expect(await axe(page)).toEqual([]);
});

test("one passage's reports name each sender by role, and Rank it lower needs a reason before it saves", async ({ page }) => {
  const sent = await serve(page, {
    "/api/passage-reports/grp-6fa04e510789": await file("passage-report.json"),
    "POST /api/passage-reports/grp-6fa04e510789/decide": await file("passage-report-saved.json"),
    "/api/lessons/me": await file("retrieval-me-passage-reviewer-waiting.json"),
  });
  await page.goto("/lessons/reports/grp-6fa04e510789");
  // The project is named as the evidence drawer's meta line names it, in the title and the passage block alike.
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Rajasthan Road Sector Modernization, paragraph 54");
  await expect(page.locator("[data-passage]").first()).toBeVisible();
  await expect(page.locator("[data-status]")).toHaveText("Wrong passage and not useful · needs your review");
  const reports = page.locator("[data-report-item]");
  await expect(reports).toHaveCount(2);
  await expect(reports.first()).toContainText("A World Bank staff member marked it as the wrong passage on October 23, 2026.");
  await expect(reports.nth(1)).toContainText("About their own project");
  await expect(reports.nth(1)).toContainText("They gave no reason.");
  expect(await axe(page)).toEqual([]);

  await page.getByRole("button", { name: "Rank it lower" }).click();
  await expect(page.getByText("Write your reason first. The people who sent these reports will see it.")).toBeVisible();
  await expect(page.getByRole("textbox", { name: "Your reason" })).toBeFocused();
  expect(sent.filter((call) => call.method === "POST")).toEqual([]);
  await page.getByRole("textbox", { name: "Your reason" }).fill("The paragraph is about estimates in general.");
  await page.getByRole("button", { name: "Rank it lower" }).click();
  const panel = page.locator("[data-outcome-panel]");
  await expect(panel).toBeFocused();
  await expect(panel).toContainText("You ranked this paragraph lower for questions about rebidding and bid prices.");
  expect(sent.filter((call) => call.method === "POST").map((call) => call.body)).toEqual([
    { expected_state: "none", outcome: "rank_lower", reason: "The paragraph is about estimates in general." },
  ]);
});

test("Judging shows your progress, your agreement with Cohen's kappa, and the queries to judge", async ({ page }) => {
  await serve(page, {
    "/api/lessons/me": await file("retrieval-me-judge-after.json"),
    "/api/judging/queries": await file("judging-queries.json"),
  });
  await page.goto("/lessons/judging");
  await expect(page.locator("[data-judging-lead]")).toHaveText("You have judged 1 of 3 queries.");
  // Each query names the award notice it was written from, as a link to that notice's record in the drawer.
  await expect(page.locator("[data-notice-link]").first()).toHaveAttribute("href", /\?evidence=strata\.gold\.notice%3AOP\d+$/);
  await expect(page.locator("[data-agreement=shown]")).toContainText("Where you have both finished, your grades matched on 20 of 25 passages. Cohen's kappa: 0.71.");
  await expect(page.getByRole("group", { name: "Show" }).locator("[data-segment]")).toHaveText(["To judge (2)", "Finished by you (1)", "Finished by both (1)"]);
  await expect(page.getByRole("radio", { name: "To judge (2)" })).toBeChecked();
  await expect(page.locator("[data-next-query]")).toHaveAttribute("href", "/lessons/judging/nq-rural-works-delays");
  expect(await axe(page)).toEqual([]);
});

for (const width of [1440, 390]) {
  test(`at ${width} px a judge grades a passage with A, the next ungraded passage takes its place, and a held key grades nothing more`, async ({ page }) => {
    const sent = await serve(page, { "/api/judging/queries/nq-rural-works-delays": await file("judging-query.json") }, width);
    // Every grade gets the server's recorded answer to a grade, whichever passage Mei's order put first.
    const saved = await file("judging-grade-saved.json");
    await page.route("**/api/judging/queries/nq-rural-works-delays/passages/**", (route) => {
      sent.push({ method: route.request().method(), path: new URL(route.request().url()).pathname, body: route.request().postDataJSON() });
      return route.fulfill({ contentType: "application/json", body: saved.body });
    });
    await page.goto("/lessons/judging/nq-rural-works-delays");
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("What held up the award of rural road works contracts, and how did the project respond?");
    const panel = page.locator("[data-judging-panel]");
    await expect(panel.getByRole("heading", { level: 2 })).toHaveText("Passage 1 of 40");
    // Blind judging: no rank or score on the page.
    await expect(page.getByText(/\bscore\b|\brank\b/i)).toHaveCount(0);
    expect(await axe(page)).toEqual([]);

    await panel.click({ position: { x: 4, y: 4 } });
    // A held key: the first press grades passage 1, and the repeats it sends while held grade nothing more.
    await page.keyboard.down("a");
    await page.keyboard.down("a");
    await page.keyboard.up("a");
    await expect(panel.getByRole("heading", { level: 2 })).toHaveText("Passage 2 of 40");
    await expect(panel.getByRole("heading", { level: 2 })).toBeFocused();
    await expect(page.locator("[data-progress]")).toContainText("1 of 40 passages graded.");
    await expect.poll(() => sent.filter((call) => call.method === "PUT").length).toBe(1);
    expect(sent.find((call) => call.method === "PUT")!.body).toEqual({ grade: "answers" });
    if (width === 1440) {
      expect(await page.locator("[data-grade-bar]").evaluate((el) => getComputedStyle(el).position)).toBe("sticky");
    } else {
      expect(await page.locator("[data-grade-bar]").evaluate((el) => getComputedStyle(el).position)).toBe("static");
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
      // Below 1024 px the grade buttons come right after the passage, before the definitions, and the page scrolled
      // so the next passage's heading is at the top of the window.
      expect(await panel.evaluate((el) => [...el.querySelectorAll("[data-grade-bar], dl")].map((node) => node.tagName))).toEqual(["DIV", "DL"]);
      expect((await panel.getByRole("heading", { level: 2 }).boundingBox())!.y).toBeLessThan(8);
    }
  });
}

test("a grade that fails to save says so on the grade bar, and Try again saves it and counts it again", async ({ page }) => {
  await serve(page, { "/api/judging/queries/nq-rural-works-delays": await file("judging-query.json") });
  const saved = await file("judging-grade-saved.json");
  let tries = 0;
  await page.route("**/api/judging/queries/nq-rural-works-delays/passages/**", (route) => {
    tries += 1;
    return tries === 1
      ? route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ code: "data_service" }) })
      : route.fulfill({ contentType: "application/json", body: saved.body });
  });
  await page.goto("/lessons/judging/nq-rural-works-delays");
  await page.locator("[data-judging-panel]").click({ position: { x: 4, y: 4 } });
  await page.keyboard.press("a");
  const bar = page.locator("[data-grade-bar]");
  await expect(bar.getByRole("alert")).toContainText("I couldn't save your grade for passage 1. Your other grades are saved.");
  await expect(page.locator("[data-progress]")).toContainText("0 of 40 passages graded.");
  await bar.getByRole("button", { name: "Try again" }).click();
  await expect(page.locator("[data-progress]")).toContainText("1 of 40 passages graded.");
  await expect(bar.getByRole("alert")).toHaveCount(0);
});

test("grading the last passage moves focus to the panel that says you graded them all", async ({ page }) => {
  // The recorded query with every passage but the first in Mei's order already graded.
  const query = JSON.parse((await file("judging-query.json")).body);
  query.passages = query.passages.map((passage: { my_grade: string | null }, index: number) => ({ ...passage, my_grade: index === 0 ? null : "partly" }));
  await serve(page, { "/api/judging/queries/nq-rural-works-delays": { body: JSON.stringify(query) } });
  const saved = await file("judging-grade-saved.json");
  await page.route("**/api/judging/queries/nq-rural-works-delays/passages/**", (route) => route.fulfill({ contentType: "application/json", body: saved.body }));
  await page.goto("/lessons/judging/nq-rural-works-delays");
  await page.locator("[data-judging-panel]").click({ position: { x: 4, y: 4 } });
  await page.keyboard.press("n");
  const finished = page.locator("[data-judging-finished=mine] [data-outcome-panel]");
  await expect(finished).toBeFocused();
  await expect(finished).toContainText("You graded all 40 passages for this query.");
});

test("when the other judge finishes while the query is open, the refused grade says the grades are locked, with no retry", async ({ page }) => {
  const start = await file("judging-query.json");
  const locked = await file("judging-query-locked.json");
  const refused = await file("judging-grade-locked.json");
  await serve(page, {});
  let reads = 0;
  await page.route("**/api/judging/queries/nq-rural-works-delays", (route) => {
    reads += 1;
    return route.fulfill({ contentType: "application/json", body: reads === 1 ? start.body : locked.body });
  });
  await page.route("**/api/judging/queries/nq-rural-works-delays/passages/**", (route) =>
    route.fulfill({ status: refused.status ?? 409, contentType: "application/json", body: refused.body }),
  );
  await page.goto("/lessons/judging/nq-rural-works-delays");
  await page.locator("[data-judging-panel]").click({ position: { x: 4, y: 4 } });
  await page.keyboard.press("a");
  const notice = page.locator("[data-locked-while-open]");
  await expect(notice).toBeFocused();
  await expect(notice).toHaveText("The other judge finished this query while you had it open, so I locked your grades for it.");
  await expect(page.getByRole("button", { name: "Try again" })).toHaveCount(0);
});

test("choosing another filter with the arrow keys keeps focus on the filter while its queries load", async ({ page }) => {
  await serve(page, {
    "/api/lessons/me": await file("retrieval-me-judge-after.json"),
    "/api/judging/queries": await file("judging-queries.json"),
    "/api/judging/queries?show=finished_by_both": await file("judging-queries-both.json"),
  });
  await page.goto("/lessons/judging");
  await page.getByRole("radio", { name: "To judge (2)" }).focus();
  await page.keyboard.press("ArrowRight");
  await page.keyboard.press("ArrowRight");
  await expect(page).toHaveURL(/show=finished_by_both/);
  await expect(page.locator("[data-judging=ready] [aria-busy]")).toHaveCount(0);
  await expect(page.getByRole("radio", { name: "Finished by both (1)" })).toBeFocused();
});

// The focused heading clears the stuck header: its top is at or below the header's bottom (DESIGN.md section 10).
async function clearsHeader(page: Page) {
  const heading = page.locator("[data-judging-panel] h2");
  await expect(heading).toBeFocused();
  const header = (await page.locator("[data-judging-header]").boundingBox())!;
  const top = (await heading.boundingBox())!.y;
  expect(top).toBeGreaterThanOrEqual(Math.max(header.y + header.height, 0));
  expect(top).toBeLessThan(900);
}

for (const width of [1440, 1024]) {
  test(`at ${width} px the next passage's heading lands below the stuck header, after a grade by pointer or by key`, async ({ page }) => {
    await serve(page, { "/api/judging/queries/nq-rural-works-delays": await file("judging-query.json") }, width);
    const saved = await file("judging-grade-saved.json");
    await page.route("**/api/judging/queries/nq-rural-works-delays/passages/**", (route) => route.fulfill({ contentType: "application/json", body: saved.body }));
    await page.goto("/lessons/judging/nq-rural-works-delays");
    const panel = page.locator("[data-judging-panel]");
    await expect(panel.getByRole("heading", { level: 2 })).toHaveText("Passage 1 of 40");

    await page.locator("[data-grade-bar]").getByRole("button", { name: /Not relevant/ }).click();
    await expect(panel.getByRole("heading", { level: 2 })).toHaveText("Passage 2 of 40");
    await clearsHeader(page);

    await page.evaluate(() => window.scrollBy(0, 350));
    await page.waitForTimeout(350);
    await page.keyboard.press("p");
    await expect(panel.getByRole("heading", { level: 2 })).toHaveText("Passage 3 of 40");
    await clearsHeader(page);
    // Stuck, the header keeps 12 px of the page above its caption.
    await expect(page.locator("[data-judging-header]")).toHaveAttribute("data-stuck", "true");
    expect((await page.locator("[data-judging-header] p").first().boundingBox())!.y).toBeGreaterThanOrEqual(12);
  });
}

test("once you finish a query, the grade bar stays so you can change a grade until the other judge finishes", async ({ page }) => {
  const query = JSON.parse((await file("judging-query.json")).body);
  query.passages = query.passages.map((passage: { my_grade: string | null }, index: number) => ({ ...passage, my_grade: index === 0 ? null : "partly" }));
  const sent = await serve(page, { "/api/judging/queries/nq-rural-works-delays": { body: JSON.stringify(query) } });
  const saved = await file("judging-grade-saved.json");
  await page.route("**/api/judging/queries/nq-rural-works-delays/passages/**", (route) => {
    sent.push({ method: route.request().method(), path: new URL(route.request().url()).pathname, body: route.request().postDataJSON() });
    return route.fulfill({ contentType: "application/json", body: saved.body });
  });
  await page.goto("/lessons/judging/nq-rural-works-delays");
  await page.locator("[data-judging-panel]").click({ position: { x: 4, y: 4 } });
  await page.keyboard.press("n");
  await expect(page.locator("[data-judging-finished=mine] [data-outcome-panel]")).toBeFocused();

  const bar = page.locator("[data-grade-bar=ready]");
  await expect(bar.getByRole("button", { name: /Not relevant/ })).toHaveAttribute("aria-pressed", "true");
  await bar.getByRole("button", { name: /Partly/ }).click();
  await expect(bar.getByRole("button", { name: /Partly/ })).toHaveAttribute("aria-pressed", "true");
  await expect.poll(() => sent.filter((call) => call.method === "PUT").map((call) => call.body)).toEqual([{ grade: "not_relevant" }, { grade: "partly" }]);
});

test("on a query both judges finished, the two grades sit in the page, not in a bar stuck to the window", async ({ page }) => {
  await serve(page, { "/api/judging/queries/nq-water-works-readiness": await file("judging-query-locked.json") });
  await page.goto("/lessons/judging/nq-water-works-readiness");
  await expect(page.locator("[data-grade-bar=locked]")).toBeVisible();
  expect(await page.locator("[data-grade-bar=locked]").evaluate((el) => getComputedStyle(el).position)).toBe("static");
  // The keys grade nothing on a locked query, so the line that names them is gone.
  await expect(page.getByText("While you are in this panel, the keys A, P and N choose a grade.")).toHaveCount(0);
  // "Judge the next query" is never under a stuck bar.
  await page.locator("[data-judging-finished=both]").getByRole("button", { name: /Show where you differed/ }).click();
  const next = page.locator("[data-judging-finished=both]").getByRole("link", { name: "Judge the next query" });
  await next.focus();
  const box = (await next.boundingBox())!;
  const bar = (await page.locator("[data-grade-bar=locked]").boundingBox())!;
  expect(box.y + box.height <= bar.y || box.y >= bar.y + bar.height).toBe(true);
});

test("closing the award notice's record puts focus back on its link", async ({ page }) => {
  await serve(page, {
    "/api/judging/queries/nq-rural-works-delays": await file("judging-query.json"),
    "/api/evidence": await file("evidence-award-notice-op00125282.json"),
  });
  await page.goto("/lessons/judging/nq-rural-works-delays");
  const link = page.locator("[data-judging-header] [data-notice-link]");
  await link.click();
  await expect(page.locator("[data-evidence-drawer]")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.locator("[data-evidence-drawer]")).toHaveCount(0);
  await expect(link).toBeFocused();
});

test("at 390 px a grade that fails to save says so in view, above the next passage", async ({ page }) => {
  await serve(page, { "/api/judging/queries/nq-rural-works-delays": await file("judging-query.json") }, 390);
  await page.route("**/api/judging/queries/nq-rural-works-delays/passages/**", (route) =>
    route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ code: "data_service" }) }),
  );
  await page.goto("/lessons/judging/nq-rural-works-delays");
  await page.locator("[data-judging-panel]").click({ position: { x: 4, y: 4 } });
  await page.keyboard.press("a");
  const alert = page.locator("[data-judging-panel]").getByRole("alert");
  await expect(alert).toContainText("I couldn't save your grade for passage 1.");
  const box = (await alert.boundingBox())!;
  expect(box.y).toBeGreaterThanOrEqual(0);
  expect(box.y + box.height).toBeLessThanOrEqual(900);
  // Between the panel's heading and the passage.
  expect(await page.locator("[data-judging-panel]").evaluate((panel) => {
    const kids = [...panel.children];
    const at = kids.findIndex((kid) => kid.querySelector("[role=alert]") || kid.getAttribute("role") === "alert");
    return [kids[at - 1]?.tagName, at > 0];
  })).toEqual(["H2", true]);
});

for (const width of [1024, 390]) {
  test(`at ${width} px a query that isn't there keeps the footer below the fold`, async ({ page }) => {
    await serve(page, { "/api/judging/queries/nq-nothing": await file("judging-query-not-found.json") }, width);
    await page.goto("/lessons/judging/nq-nothing");
    await expect(page.getByText("nq-nothing")).toBeVisible();
    expect((await page.locator("footer").boundingBox())!.y).toBeGreaterThanOrEqual(900);
  });
}

test("a judge with one query and no grades reads that one is waiting", async ({ page }) => {
  const list = JSON.parse((await file("judging-queries.json")).body);
  Object.assign(list, { total: 1, mine_done: 0, other_done: 0, queries: list.queries.slice(0, 1) });
  list.agreement = { ...list.agreement, both_done: 0 };
  await serve(page, { "/api/lessons/me": await file("retrieval-me-judge-after.json"), "/api/judging/queries": { body: JSON.stringify(list) } });
  await page.goto("/lessons/judging");
  await expect(page.locator("[data-judging-lead]")).toHaveText("You haven't judged any queries yet, and one is waiting for you.");
});

test("at 390 px a notice reference moves to the next line whole rather than breaking at a hyphen", async ({ page }) => {
  await serve(page, { "/api/lessons/me": await file("retrieval-me-judge-after.json"), "/api/judging/queries": await file("judging-queries.json") }, 390);
  await page.goto("/lessons/judging");
  const links = page.locator("[data-notice-link]").filter({ visible: true });
  await expect(links.first()).toBeVisible();
  // The lines the reference's own text runs over: one, wherever the link starts.
  const lines = await links.evaluateAll((all) =>
    all.map((el) => {
      const range = document.createRange();
      range.selectNodeContents(el);
      return new Set([...range.getClientRects()].map((rect) => Math.round(rect.top))).size;
    }),
  );
  expect(lines.length).toBeGreaterThan(0);
  for (const count of lines) expect(count).toBe(1);
});
