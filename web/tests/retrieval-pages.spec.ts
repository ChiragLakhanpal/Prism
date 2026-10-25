// Lessons > Passage reports and Lessons > Judging (ticket 32) at seam 4, against the answers the server wrote on the
// fixture (tests/record_retrieval_api.py), which tests/test_retrieval_recordings.py checks the server still gives.
// The words are the ticket's and the 32 design brief's, copied here so the test checks the copy file.
import AxeBuilder from "@axe-core/playwright";
import type { Page } from "@playwright/test";
import { expect, recorded, recordingFor, test } from "./mocked";

const WCAG_22_AA = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];
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
  const results = await new AxeBuilder({ page }).withTags(WCAG_22_AA).analyze();
  return results.violations.map((v) => `${v.id}: ${v.nodes.map((node) => node.target.join(" ")).join(", ")}`);
}

const subTabs = (page: Page) => page.getByRole("navigation", { name: "Lesson pages" });

test("a passage reviewer sees Lessons and Passage reports, and a query judge Lessons and Judging", async ({ page }) => {
  await serve(page, {
    "/api/lessons/me": await file("retrieval-me-passage-reviewer.json"),
    "/api/lessons": await file("lessons-library-empty.json"),
    "/api/passage-reports": await file("passage-reports.json"),
  });
  await page.goto("/lessons/reports");
  await expect(subTabs(page).getByRole("link")).toHaveText(["Lessons", "Passage reports (0)"]);
  await expect(subTabs(page).getByRole("link", { name: "Passage reports (0)" })).toHaveAttribute("aria-current", "page");

  await page.unrouteAll();
  await serve(page, {
    "/api/lessons/me": await file("retrieval-me-judge.json"),
    "/api/judging/queries": await file("judging-queries.json"),
  });
  await page.goto("/lessons/judging");
  await expect(subTabs(page).getByRole("link")).toHaveText(["Lessons", "Judging (3)"]);
});

test("Passage reports lists the groups waiting, oldest first, and the decisions of the last 90 days", async ({ page }) => {
  await serve(page, {
    "/api/lessons/me": await file("retrieval-me-both.json"),
    "/api/passage-reports": await file("passage-reports-decided.json"),
  });
  await page.goto("/lessons/reports");
  await expect(page.locator("[data-reports-lead]")).toHaveText("Reports on one passage are waiting for you. The oldest came in on October 23, 2026.");
  await expect(page.getByText("Ranking a paragraph lower changes only questions like the ones in its reports. I never hide a paragraph, and I still show it when it is the only source.")).toBeVisible();
  const row = page.locator("[data-report-row]").first();
  await expect(row).toContainText("Wrong passage · needs your review");
  await expect(row.getByRole("heading", { level: 3 })).toHaveText("Rajasthan Road Sector Modernization Project, paragraph 55");
  await expect(page.getByRole("heading", { name: "Decided in the last 90 days" })).toBeVisible();
  await expect(page.locator("[data-reports-decided]")).toContainText("Ranked lower");
  expect(await axe(page)).toEqual([]);
});

test("one passage's reports name each sender by role, and Rank it lower needs a reason before it saves", async ({ page }) => {
  const sent = await serve(page, {
    "/api/passage-reports/grp-6fa04e510789": await file("passage-report.json"),
    "POST /api/passage-reports/grp-6fa04e510789/decide": await file("passage-report-saved.json"),
    "/api/lessons/me": await file("retrieval-me-passage-reviewer.json"),
  });
  await page.goto("/lessons/reports/grp-6fa04e510789");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Rajasthan Road Sector Modernization Project, paragraph 54");
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
    "/api/lessons/me": await file("retrieval-me-judge.json"),
    "/api/judging/queries": await file("judging-queries.json"),
  });
  await page.goto("/lessons/judging");
  await expect(page.locator("[data-judging-lead]")).toHaveText("You have judged 1 of 3 queries.");
  await expect(page.locator("[data-agreement=shown]")).toContainText("Where you have both finished, your grades matched on 20 of 25 passages. Cohen's kappa: 0.71.");
  await expect(page.getByRole("radiogroup", { name: "Show" }).getByRole("radio")).toHaveText(["To judge (2)", "Finished by you (1)", "Finished by both (1)"]);
  await expect(page.getByRole("radio", { name: "To judge (2)" })).toHaveAttribute("aria-checked", "true");
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
    }
  });
}
