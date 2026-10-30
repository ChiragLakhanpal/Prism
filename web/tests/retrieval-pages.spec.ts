// Lessons > Passage reports and Lessons > Judging (ticket 32) at seam 4, against the answers the server wrote on the
// fixture (tests/record_retrieval_api.py), which tests/test_retrieval_recordings.py checks the server still gives.
// The words are the ticket's and the 32 design brief's, copied here so the test checks the copy file.
import { scan } from "./axe";
import type { Page } from "@playwright/test";
import { expect, openSidebar, recorded, recordingFor, test, windowBeside } from "./mocked";
import { animationsDone } from "./settled";

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

// Ticket 102: the reviewer pages are the sidebar's items under Lessons, each only for its role and with its count in a
// badge hidden at zero, and the sub-tab row is gone. The sub-items show in the open sidebar; the rail hides them.
const subTabs = (page: Page) => page.getByRole("navigation", { name: "Lesson pages" });
const lessonsItems = (page: Page) => page.getByRole("navigation", { name: "Main" }).locator("[data-sub-items=lessons] a");

test("a passage reviewer finds Passage reports under Lessons, and a query judge Judging, each with its count in a badge hidden at zero", async ({ page }) => {
  await openSidebar(page);
  await serve(page, {
    "/api/lessons/me": await file("retrieval-me-passage-reviewer-waiting.json"),
    "/api/lessons/page": await file("lessons-page-empty.json"),
    "/api/passage-reports": await file("passage-reports.json"),
  });
  await page.goto("/lessons/reports");
  await expect(page.locator("[data-reports-lead]")).toContainText("Reports on two passages are waiting for you.");
  // On the wide Lessons pages each sentence keeps to the width of prose (DESIGN.md, Page layouts), so a lead never runs
  // the page's full width at 1440 px.
  expect((await page.locator("[data-reports-lead]").boundingBox())!.width).toBeLessThan(700);
  await expect(lessonsItems(page)).toHaveText(["Passage reports 2"]);
  await expect(lessonsItems(page)).toHaveAccessibleName("Passage reports, 2 passages");
  await expect(lessonsItems(page)).toHaveAttribute("aria-current", "page");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Passage reports");
  await expect(subTabs(page)).toHaveCount(0);

  await page.unrouteAll();
  await serve(page, {
    "/api/lessons/me": await file("retrieval-me-judge-after.json"),
    "/api/judging/queries": await file("judging-queries.json"),
  });
  await page.goto("/lessons/judging");
  await expect(page.getByRole("radio", { name: "To judge (2)" })).toBeVisible();
  expect((await page.locator("[data-judging-lead]").boundingBox())!.width).toBeLessThan(700);
  await expect(lessonsItems(page)).toHaveAccessibleName("Judging, 2 queries left");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Judging");
  await expect(subTabs(page)).toHaveCount(0);

  // A lead who reviews passage reports with none waiting: Waiting for review, then Passage reports with no badge.
  await page.unrouteAll();
  await serve(page, {
    "/api/lessons/me": await file("retrieval-me-both.json"),
    "/api/lessons/page": await file("lessons-page-reviewer.json"),
  });
  await page.goto("/lessons");
  await expect(page.locator("[data-lessons-page=ready]")).toBeVisible();
  await expect(lessonsItems(page)).toHaveText(["Waiting for review 3", "Passage reports"]);
  await expect(lessonsItems(page).nth(1)).toHaveAccessibleName("Passage reports");
  await expect(lessonsItems(page).nth(1).locator("[data-sub-count]")).toHaveCount(0);

  // With one passage waiting, its name counts one passage. Each badge's link reads its label, then its number, so its
  // name holds what it shows (WCAG 2.5.3, Label in Name).
  await page.unrouteAll();
  await serve(page, {
    "/api/lessons/me": await file("retrieval-me-both-waiting.json"),
    "/api/lessons/page": await file("lessons-page-reviewer.json"),
  });
  await page.goto("/lessons");
  await expect(lessonsItems(page)).toHaveText(["Waiting for review 3", "Passage reports 1"]);
  await expect(lessonsItems(page).nth(0)).toHaveAccessibleName("Waiting for review, 3 lessons");
  await expect(lessonsItems(page).nth(1)).toHaveAccessibleName("Passage reports, 1 passage");
  const sidebarScan = await scan(page, "[data-sub-items=lessons]");
  expect(sidebarScan.violations.map((violation) => violation.id)).toEqual([]);

  // The officer's preview hides the reviewer pages (config/roles.toml), whatever roles the viewer has.
  await page.unrouteAll();
  await serve(page, {
    "/api/me": await file("me-preview-piu.json"),
    "/api/lessons/me": await file("retrieval-me-both.json"),
    "/api/lessons/page": await file("lessons-page-preview.json"),
  });
  await page.goto("/lessons?view=piu");
  await expect(page.locator("[data-lessons-page=ready]")).toBeVisible();
  await expect(page.getByRole("navigation", { name: "Main" }).locator("[data-nav-item=lessons]")).toHaveAttribute("aria-current", "page");
  await expect(lessonsItems(page)).toHaveCount(0);
});

test("Passage reports lists the groups waiting, oldest first, and the decisions of the last 90 days", async ({ page }) => {
  await serve(page, {
    "/api/lessons/me": await file("retrieval-me-passage-reviewer-decided.json"),
    "/api/passage-reports": await file("passage-reports-decided.json"),
  });
  await page.goto("/lessons/reports");
  await expect(page.locator("[data-reports-lead]")).toHaveText("Reports on one passage are waiting for you. The oldest came in on October 23, 2026.");
  // The sidebar's badge counts what the lead says is waiting for you.
  await expect(page.locator("[data-sub-item=lessonsReports] [data-sub-count]")).toHaveText("1");
  // The decision form's feedforward says what ranking lower changes, where it matters; the page's caption went in
  // ticket 126 (R51).
  await expect(page.getByText("Ranking a paragraph lower changes only questions like the ones in its reports.")).toHaveCount(0);
  const row = page.locator("[data-report-row]").first();
  await expect(row).toContainText("Wrong passage · needs your review");
  await expect(row.getByRole("heading", { level: 3 })).toHaveText("Rajasthan Road Sector Modernization, paragraph 55");
  await expect(page.getByRole("heading", { name: "Decided in the last 90 days" })).toBeVisible();
  await expect(page.locator("[data-reports-decided]")).toContainText("Ranked lower");
  // Every row shows, and the count line stays because it says the list's order (ticket 126; DESIGN.md section 5, Tables).
  await expect(page.locator("[data-reports-decided] [data-count-row] p[data-numbers]")).toHaveText("Showing the one decision, newest first.");
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

// An account that can't read Strata's tables reads what to ask for once: the alert says what failed, and the line under
// it what to ask (the 58 critique, round 3, "Seen outside this ticket's code").
test("Judging without read access says once what to ask the workspace admin for", async ({ page }) => {
  await serve(page, {
    "/api/lessons/me": await file("retrieval-me-judge-after.json"),
    "/api/judging/queries": { status: 403, body: '{"code":"permission"}' },
  });
  await page.goto("/lessons/judging");
  const failed = page.locator("[data-load-error=permission]");
  await expect(failed.getByRole("alert")).toHaveText("Your account can't read Strata's tables, so I can't show the queries.");
  expect((await failed.textContent())!.split("Ask your workspace admin").length - 1).toBe(1);
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

// Ticket 59 (the 32 critique, round 3, follow-ups 3 and 4): where neither judge has finished a query, no agreement
// block shows, and the filter sits 32 px under "Judge the next query", as the 32 brief's 2.10 sets it; an open disclosure
// points its chevron up.
test("with no query finished by both, Show sits 32 px under Judge the next query, and an open passage list points up", async ({ page }) => {
  await serve(page, {
    "/api/lessons/me": await file("retrieval-me-judge-after.json"),
    "/api/judging/queries": await file("judging-queries-start.json"),
    "/api/judging/queries/nq-rural-works-delays": await file("judging-query.json"),
  });
  await page.goto("/lessons/judging");
  await expect(page.locator("[data-next-query]")).toBeVisible();
  await expect(page.locator("[data-agreement]")).toHaveCount(0);
  const [next, show] = await page.evaluate(() =>
    [document.querySelector("[data-next-query]")!, document.querySelector("[data-judging=ready] fieldset, [data-judging=ready] [role=group]")!].map((part) =>
      part.getBoundingClientRect().toJSON(),
    ),
  );
  expect(Math.round(show.top - next.bottom)).toBe(32);

  await page.goto("/lessons/judging/nq-rural-works-delays");
  const map = page.locator("[data-passage-map]").getByRole("button").first();
  await expect(map.locator("svg")).toHaveClass(/lucide-chevron-down/);
  await map.click();
  await expect(map).toHaveAttribute("aria-expanded", "true");
  await expect(map.locator("svg")).toHaveClass(/lucide-chevron-up/);
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
      // Ticket 113: at the page's end the grade bar has let go of the window's foot, and the box still floats 16 px
      // above it.
      const gap = await page.evaluate(
        () =>
          new Promise<number>((done) => {
            window.scrollTo(0, document.documentElement.scrollHeight);
            requestAnimationFrame(() =>
              requestAnimationFrame(() => {
                const box = document.querySelector("[data-box-slot] form > [data-focus-ring]")!.getBoundingClientRect();
                done(Math.round(document.querySelector("[data-grade-bar]")!.getBoundingClientRect().top - box.bottom));
              }),
            );
          }),
      );
      expect(gap, "the box 16 px above the grade bar at the page's end").toBe(16);
    } else {
      expect(await page.locator("[data-grade-bar]").evaluate((el) => getComputedStyle(el).position)).toBe("static");
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
      // Below 1024 px the grade buttons come right after the passage, before the definitions, and the page scrolled
      // so the next passage's heading is at the top of the window.
      expect(await panel.evaluate((el) => [...el.querySelectorAll("[data-grade-bar], dl")].map((node) => node.tagName))).toEqual(["DIV", "DL"]);
      // Ticket 59 (the 32 critique, round 3, follow-up 2): 16 px from the window's top, its scroll margin.
      const y = (await panel.getByRole("heading", { level: 2 }).boundingBox())!.y;
      expect(y).toBeGreaterThanOrEqual(12);
      expect(y).toBeLessThanOrEqual(20);
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

// Ticket 102: a review page keeps to the workspace's work columns from a frame of 75rem (1440 and 1280 px beside the
// rail) and is one column below it, and its single-key grades work only inside its own panel (WCAG 2.2, 2.1.4).
test("a query's page keeps to the work columns at 1440 and 1280 px and is one column at 1024 and 390 px, and A grades only inside its panel", async ({ page }) => {
  const sent = await serve(page, { "/api/judging/queries/nq-rural-works-delays": await file("judging-query.json") });
  await page.goto("/lessons/judging/nq-rural-works-delays");
  const panel = page.locator("[data-judging-panel]");
  await expect(panel.getByRole("heading", { level: 2 })).toHaveText("Passage 1 of 40");
  for (const width of [1440, 1280, 1024, 390]) {
    await page.setViewportSize({ width, height: 900 });
    const [work, column] = [(await page.locator("[data-document-column]").boundingBox())!, (await page.locator("[data-page-column]").boundingBox())!];
    if (width >= 1280) expect(work.width / column.width, `${width} px`).toBeLessThan(0.65);
    else expect(work.width / column.width, `${width} px`).toBeGreaterThan(0.85);
  }
  await page.setViewportSize({ width: 1440, height: 900 });
  // Outside the panel, on the page's h1, the key grades nothing; inside it, the same key grades.
  // One PUT after both presses proves the first sent nothing and the second graded.
  await page.getByRole("heading", { level: 1 }).focus();
  await page.keyboard.press("a");
  await expect(panel.getByRole("heading", { level: 2 })).toHaveText("Passage 1 of 40");
  await panel.focus();
  await page.keyboard.press("a");
  await expect.poll(() => sent.filter((call) => call.method === "PUT").length).toBe(1);
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
  // Every passage is graded, so the bar no longer promises to open the next one (ticket 58; the 32 design review, F2).
  await expect(page.locator("[data-grade-bar]")).toContainText("Choosing a grade saves the change.");
  await expect(page.locator("[data-grade-bar]")).not.toContainText("opens the next passage");
});

// Ticket 58 (the 32 design review, round 3, F4): one finished query is "the one query", never "1 queries".
test("the agreement's tooltip says the one query you both finished", async ({ page }) => {
  await serve(page, {
    "/api/lessons/me": await file("retrieval-me-judge-after.json"),
    "/api/judging/queries": await file("judging-queries.json"),
  });
  await page.goto("/lessons/judging");
  const agree = page.locator("[data-agreement=shown] [data-num]").first();
  await agree.focus();
  await expect(page.getByRole("tooltip")).toContainText("Passages you both graded, on the one query you both finished.");
  await expect(page.getByRole("tooltip")).not.toContainText("1 queries");
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
  });
  // Each other filter's queries wait until the test lets them through, so the check mark is read while they load.
  let release!: () => void;
  const held = new Promise<void>((resolve) => (release = resolve));
  const both = await file("judging-queries-both.json");
  const mine = await file("judging-queries.json");
  await page.route("**/api/judging/queries?show=*", async (route) => {
    const show = new URL(route.request().url()).searchParams.get("show");
    if (show === "to_judge") return route.fulfill({ contentType: "application/json", body: mine.body });
    await held;
    await route.fulfill({ contentType: "application/json", body: show === "finished_by_both" ? both.body : mine.body });
  });
  await page.goto("/lessons/judging");
  await page.getByRole("radio", { name: "To judge (2)" }).focus();
  await page.keyboard.press("ArrowRight");
  await page.keyboard.press("ArrowRight");
  await expect(page).toHaveURL(/show=finished_by_both/);
  // While its queries load, the check mark is on the filter you chose, where focus is (ticket 60).
  await expect(page.locator("[data-judging=ready] [aria-busy]")).toHaveCount(1);
  await expect(page.getByRole("radio", { name: /^Finished by both/ })).toBeFocused();
  await expect(page.getByRole("radio", { name: /^Finished by both/ })).toBeChecked();
  release();
  await expect(page.locator("[data-judging=ready] [aria-busy]")).toHaveCount(0);
  await expect(page.getByRole("radio", { name: "Finished by both (1)" })).toBeFocused();
  await expect(page.getByRole("radio", { name: "Finished by both (1)" })).toBeChecked();
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
  test(`in a ${width} px page area the next passage's heading lands below the stuck header, after a grade by pointer or by key`, async ({ page }) => {
    await serve(page, { "/api/judging/queries/nq-rural-works-delays": await file("judging-query.json") }, windowBeside(width));
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

// Ticket 60 (ticket 32's critique, round 3): after a click grades a passage, the next passage's buttons all look
// unpressed alike until the pointer moves; the button under the resting pointer takes no hover fill.
test("after a click on a grade, the next passage's three buttons share one background until the pointer moves", async ({ page }) => {
  await serve(page, { "/api/judging/queries/nq-rural-works-delays": await file("judging-query.json") });
  const saved = await file("judging-grade-saved.json");
  await page.route("**/api/judging/queries/nq-rural-works-delays/passages/**", (route) => route.fulfill({ contentType: "application/json", body: saved.body }));
  await page.goto("/lessons/judging/nq-rural-works-delays");
  const bar = page.locator("[data-grade-bar=ready]");
  await bar.getByRole("button", { name: /Not relevant/ }).click();
  await expect(page.locator("[data-judging-panel] h2")).toHaveText("Passage 2 of 40");
  await animationsDone(page);

  const buttons = bar.locator("[data-grade]");
  await expect(buttons).toHaveCount(3);
  for (const pressed of await buttons.evaluateAll((all) => all.map((button) => button.getAttribute("aria-pressed")))) expect(pressed).toBe("false");
  const fills = await buttons.evaluateAll((all) => all.map((button) => getComputedStyle(button).backgroundColor));
  expect(new Set(fills).size).toBe(1);

  // A move of the pointer brings the hover fill back.
  const box = (await bar.getByRole("button", { name: /Not relevant/ }).boundingBox())!;
  await page.mouse.move(box.x + box.width / 2 + 2, box.y + box.height / 2);
  await expect.poll(() => buttons.evaluateAll((all) => new Set(all.map((button) => getComputedStyle(button).backgroundColor)).size)).toBe(2);
});

// Ticket 60 (ticket 32's design review, round 3, F1; WCAG 3.2.2): a grade changed after you finished keeps the
// finished panel in place while it saves, and focus and the scroll stay where you are.
for (const width of [1440, 390]) {
  test(`at ${width} px changing a grade after you finish keeps focus on the grade and the page where it was`, async ({ page }) => {
    const query = JSON.parse((await file("judging-query.json")).body);
    query.passages = query.passages.map((passage: { my_grade: string | null }) => ({ ...passage, my_grade: "partly" }));
    await serve(page, { "/api/judging/queries/nq-rural-works-delays": { body: JSON.stringify(query) } }, width);
    const saved = await file("judging-grade-saved.json");
    await page.route("**/api/judging/queries/nq-rural-works-delays/passages/**", async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 300));
      await route.fulfill({ contentType: "application/json", body: saved.body });
    });
    await page.goto("/lessons/judging/nq-rural-works-delays");
    const finished = page.locator("[data-judging-finished=mine]");
    await expect(finished).toBeVisible();
    const button = page.locator("[data-grade-bar]").getByRole("button", { name: /Not relevant/ });
    await button.scrollIntoViewIfNeeded();
    const before = await page.evaluate(() => window.scrollY);

    await button.click();

    // While the change saves (300 ms), the finished panel stays: nothing blinks.
    await expect(button).toHaveAttribute("aria-pressed", "true");
    expect(await finished.count()).toBe(1);
    await page.waitForTimeout(500);
    await expect(button).toBeFocused();
    await expect(finished).toBeVisible();
    expect(await page.evaluate(() => window.scrollY)).toBe(before);
  });
}

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
  // In a 700 px window the link starts below the window, so focusing it scrolls it in, and the gap below proves the
  // scroll padding (ticket 60's review, item 4).
  await page.setViewportSize({ width: page.viewportSize()!.width, height: 700 });
  await page.evaluate(() => window.scrollTo(0, 0));
  expect(await next.evaluate((link) => link.getBoundingClientRect().top > window.innerHeight)).toBe(true);
  await next.focus();
  const box = (await next.boundingBox())!;
  const bar = (await page.locator("[data-grade-bar=locked]").boundingBox())!;
  expect(box.y + box.height <= bar.y || box.y >= bar.y + bar.height).toBe(true);
  // Ticket 60 (ticket 32's critique, round 3, follow-up 5): with nothing of the page stuck at the foot, the focused link
  // still sits at least 8 px clear of the Ask bar at the window's foot, never flush on it.
  const ask = (await page.locator("[data-box-slot]").boundingBox())!;
  expect(box.y + box.height).toBeLessThanOrEqual(ask.y - 8 + 0.5);
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
