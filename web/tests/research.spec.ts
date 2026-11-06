// The Deep research tab (ticket 149) at seam 4: the brief GET /api/projects/{pid}/research returns, the run POST
// streams, the evidence drawer a marker opens, and the print view "Download as PDF" prints. The responses are ticket
// 148's routes' own, recorded in tests/fixtures/api (research-p156634.json, research-p156634-none.json,
// research-p156634.sse and evidence-research-item-p156634-star.json) by tests/record_research_api.py from the run
// ticket 147's seed keeps. Every count below is read from the recording, through the tab's own reader (briefFrom).
import type { Page, Route } from "@playwright/test";
import { copy } from "../src/copy";
import { briefFrom, itemFor, type Brief } from "../src/lib/research";
import { scan } from "./axe";
import { expect, mockApi, recorded, test, viewAnswers } from "./mocked";

type Answer = { status?: number; body: string };

const PATH = "/projects/P156634/research";
const ROUTE = "/api/projects/P156634/research";
const words = copy.research;

async function brief(): Promise<Brief> {
  const read = briefFrom(JSON.parse(await recorded("research-p156634.json")));
  if (read.status !== "ready") throw new Error("research-p156634.json holds no brief.");
  return read;
}

// The Sentinel-2 tiles are the one thing the brief loads from outside the app: each answers with a 1 px image here, so
// no test reaches the network. A page route wins over the context's route that refuses outside requests.
const PIXEL = Buffer.from("R0lGODlhAQABAIAAAP///wAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw==", "base64");

async function open(page: Page, { width = 1440, research, extra = {} }: { width?: number; research?: Answer; extra?: Record<string, Answer> } = {}) {
  await page.setViewportSize({ width, height: 900 });
  await page.route("https://tiles.maps.eox.at/**", (route) => route.fulfill({ status: 200, contentType: "image/gif", body: PIXEL }));
  const unrecorded = await mockApi(page, {
    ...(await viewAnswers()),
    "/api/me": { body: await recorded("me.json") },
    "/api/freshness": { body: await recorded("freshness.json") },
    "/api/projects/P156634": { body: await recorded("project-p156634.json") },
    [ROUTE]: research ?? { body: await recorded("research-p156634.json") },
    "/api/evidence": { body: await recorded("evidence-research-item-p156634-star.json") },
    "/api/evidence/opened": { body: '{"opened":[],"recorded":true}' },
    ...extra,
  });
  await page.goto(PATH);
  await expect(page.locator("main h1")).toBeVisible();
  return unrecorded;
}

const main = (page: Page) => page.getByRole("main");
const tab = (page: Page) => page.locator("[data-research]");

// The section titles on screen, in the sample's order.
const ORDER = [words.section.picture, words.section.bottomLine, words.section.developments, words.section.bySite, words.section.voices, words.section.questions, words.section.couldNotSee, words.section.sources];

test("Deep research is the sixth tab, at /projects/P156634/research, and shows the stored brief's sections in the sample's order", async ({ page }) => {
  const unrecorded = await open(page);
  const data = await brief();
  const tabs = main(page).getByRole("navigation", { name: "Project sections" }).getByRole("link");
  await expect(tabs).toHaveCount(6);
  await expect(tabs.nth(5)).toHaveText(copy.projectPage.tab.research);
  await expect(tabs.nth(5)).toHaveAttribute("href", PATH);
  await expect(tabs.nth(5)).toHaveAttribute("aria-current", "page");
  await expect(tab(page)).toHaveAttribute("data-research", "ready");
  await expect(page).toHaveTitle(/Water and Sanitation Development \(P156634\), Deep research/);

  // The sections, as h2s and h3s in the tab, in the sample's order.
  await expect(tab(page).locator("[data-research-section] > h2, [data-research-section] > h3")).toHaveText(ORDER);
  // The headline and every sentence of every section are on screen, word for word.
  await expect(tab(page).locator("[data-research-headline]")).toContainText(data.sections.headline!.text);
  const sentences = [
    ...data.sections.picture,
    ...data.sections.bottom_line,
    ...data.sections.developments.flatMap((row) => row.sentences),
    ...data.sections.by_site.flatMap((group) => [group.title, ...group.sentences]),
    ...data.sections.voices,
    ...data.sections.questions.flatMap((question) => question.sentences),
    ...data.sections.could_not_see,
  ];
  for (const sentence of sentences) await expect(tab(page)).toContainText(sentence.text);
  // Each development, newest first as the writer gave them, one row each; an undated one says so.
  await expect(tab(page).locator("[data-development]")).toHaveCount(data.sections.developments.length);
  await expect(tab(page).locator("[data-development] [data-development-date]").filter({ hasText: words.undated })).toHaveCount(
    data.sections.developments.filter((row) => row.date === null).length,
  );
  // One group per site, with the Sentinel-2 grids side by side: two years of nine tiles each.
  await expect(tab(page).locator("[data-site]")).toHaveCount(data.sections.by_site.length);
  const grids = tab(page).locator("[data-site] [data-s2-grid]");
  await expect(grids).toHaveCount(2);
  const [left, right] = [(await grids.nth(0).boundingBox())!, (await grids.nth(1).boundingBox())!];
  expect(Math.abs(left.y - right.y), "the two years side by side").toBeLessThan(2);
  await expect(grids.nth(0).locator("img")).toHaveCount(9);
  // The voices, the questions with their bold leads, and the sources with "Open the source" in a new tab.
  await expect(tab(page).locator("[data-voice]")).toHaveCount(data.sections.voices.length);
  await expect(tab(page).locator("[data-question] b")).toHaveText(data.sections.questions.map((question) => question.lead));
  // Every sentence carries its markers; every cited source is numbered, and each item has its link. The run's summary
  // record, which a sentence cites for a count, is numbered with Prism's words and no outside link.
  const cited = new Set([data.sections.headline!, ...sentences].flatMap((sentence) => sentence.evidence_ids));
  await expect(tab(page).locator("[data-research-sources] li")).toHaveCount(cited.size);
  const links = tab(page).locator("[data-research-sources] li").getByRole("link", { name: new RegExp(words.openSource) });
  await expect(links).toHaveCount([...cited].filter((id) => itemFor(data, id)).length);
  await expect(links.first()).toHaveAttribute("target", "_blank");
  await expect(tab(page).locator("[data-research-sources] li").filter({ hasText: words.summarySource })).toHaveCount(
    [...cited].filter((id) => !itemFor(data, id)).length,
  );
  // A removed sentence shows under the brief with its reason, as answers do; with none removed there is no box.
  // The box reports it ("It said the project's agencies ..."), so its first letter may be lowercased.
  if (data.removed.length > 0) {
    const removed = data.removed[0].sentence.replace(/\.$/, "").replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    await expect(tab(page).locator("[data-removed-box]")).toContainText(new RegExp(removed, "i"));
  } else {
    await expect(tab(page).locator("[data-removed-box]")).toHaveCount(0);
  }
  expect(unrecorded).toEqual([]);
});

const drawer = (page: Page) => page.getByRole("dialog");
const escaped = (text: string) => text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

test("a marker opens the evidence drawer at its item, and the item's source link opens in a new tab", async ({ page }) => {
  const unrecorded = await open(page);
  const data = await brief();
  const first = data.sections.headline!.evidence_ids[0];
  const item = itemFor(data, first)!;
  const marker = tab(page).locator("[data-research-headline]").locator(`[data-citation-id="${first}"]`);
  await expect(marker).toHaveAttribute("data-citation", "1");
  await marker.click();
  await expect(drawer(page)).toBeVisible();
  await expect(page).toHaveURL(new RegExp(`evidence=${escaped(encodeURIComponent(first))}`));
  await expect(drawer(page).getByRole("heading", { level: 2 })).toHaveText(item.title);
  await expect(marker).toHaveAttribute("aria-expanded", "true");
  const link = drawer(page).getByRole("link", { name: new RegExp(`^${words.openSource}`) });
  await expect(link).toHaveAttribute("href", item.url);
  await expect(link).toHaveAttribute("target", "_blank");
  await expect(link).toHaveAttribute("rel", /noopener/);
  await expect(drawer(page).locator("[data-research-item]")).toBeVisible();
  // Closing gives focus back to the marker.
  await page.keyboard.press("Escape");
  await expect(drawer(page)).toHaveCount(0);
  await expect(marker).toBeFocused();
  expect(unrecorded).toEqual([]);
});

test("an item opened from a link is read from the server, with its source link", async ({ page }) => {
  const star = JSON.parse(await recorded("evidence-research-item-p156634-star.json"));
  await page.setViewportSize({ width: 1440, height: 900 });
  const unrecorded = await mockApi(page, {
    ...(await viewAnswers()),
    "/api/me": { body: await recorded("me.json") },
    "/api/freshness": { body: await recorded("freshness.json") },
    "/api/projects/P156634": { body: await recorded("project-p156634.json") },
    "/api/projects/P156634/summary": { body: await recorded("summary-p156634.json") },
    "/api/evidence": { body: JSON.stringify(star) },
    "/api/evidence/opened": { body: '{"opened":[],"recorded":true}' },
  });
  await page.goto(`/projects/P156634?evidence=${encodeURIComponent(star.id)}`);
  await expect(drawer(page).getByRole("heading", { level: 2 })).toHaveText(star.row.title);
  await expect(drawer(page).getByRole("link", { name: new RegExp(`^${words.openSource}`) })).toHaveAttribute("href", star.row.url);
  expect(unrecorded).toEqual([]);
});

// ── The run ─────────────────────────────────────────────────────────────

type StreamStep = { id: string; kind: string; status: string; items?: number; note?: string | null; removed?: number };

// The steps the stream sent, each as it last stood; check 4's judge runs inside checking, so it has no line of its own.
function streamSteps(sse: string): StreamStep[] {
  const steps = new Map<string, StreamStep>();
  for (const block of sse.split("\n\n")) {
    const [kind, data] = block.split("\n");
    if (kind === "event: step") {
      const step = JSON.parse(data.replace(/^data: /, ""));
      if (step.kind === "judge" || step.kind === "disagreement") continue;
      steps.set(step.id, { ...steps.get(step.id), ...step });
    }
  }
  return [...steps.values()];
}

test("Research this project streams the run's steps; a source not reached is one line, not an error, and the brief follows", async ({ page }) => {
  const sse = await recorded("research-p156634.sse");
  const stored = await recorded("research-p156634.json");
  let release = () => {};
  const held = new Promise<void>((resolve) => (release = resolve));
  const asked: string[] = [];
  const unrecorded = await open(page, { research: { body: await recorded("research-p156634-none.json") } });
  await expect(tab(page)).toHaveAttribute("data-research", "none");
  await expect(tab(page)).toContainText(words.none);
  // From here the run answers the POST with its stream, and the read after it waits until the test lets it go, so the
  // steps can be read while the brief is on its way.
  await page.route(`**${ROUTE}`, async (route: Route) => {
    asked.push(route.request().method());
    if (route.request().method() === "POST") return route.fulfill({ status: 200, contentType: "text/event-stream", body: sse });
    await held;
    return route.fulfill({ status: 200, contentType: "application/json", body: stored });
  });
  await tab(page).getByRole("button", { name: words.run }).click();
  await expect(tab(page)).toHaveAttribute("data-research", "running");

  // Every step the stream sent, done, in its order, in the ask box's words.
  const steps = streamSteps(sse);
  const lines = tab(page).locator("[data-steps] li[data-step]");
  await expect(lines).toHaveCount(steps.length);
  await expect(lines.first()).toHaveText(words.steps.facts.done);
  const missed = steps.filter((step) => step.status === "not_reached");
  expect(missed.length, "the recording has a source not reached").toBeGreaterThan(0);
  for (const step of missed) {
    await expect(lines.filter({ hasText: step.note! })).toHaveCount(1);
    await expect(lines.filter({ hasText: step.note! })).toContainText("was not reached for this brief.");
  }
  const removed = steps.find((step) => step.kind === "checking")!.removed ?? 0;
  await expect(lines.last()).toHaveText(removed === 0 ? words.steps.check.none : removed === 1 ? words.steps.check.one : words.steps.check.several(String(removed)));
  await expect(tab(page).locator("[data-alert=error]")).toHaveCount(0);

  release();
  await expect(tab(page)).toHaveAttribute("data-research", "ready");
  // The source not reached is one line under the section it feeds, from the run's coverage; nothing is an error.
  const data = await brief();
  for (const entry of data.coverage.filter((one) => !one.reached)) {
    const line = tab(page).locator(`[data-not-reached="${entry.source}"]`);
    await expect(line).toHaveCount(1);
    await expect(line).toContainText(entry.note!);
  }
  await expect(tab(page).locator("[data-alert=error]")).toHaveCount(0);
  expect(asked).toEqual(["POST", "GET"]);
  expect(unrecorded).toEqual([]);
});

test("a run that stops with an error code says why in the code's words, with Try again", async ({ page }) => {
  await open(page, { research: { body: await recorded("research-p156634-none.json") } });
  const stopped = 'event: step\ndata: {"id": "facts", "kind": "facts", "status": "running"}\n\nevent: error\ndata: {"code": "writer_unavailable"}\n\nevent: done\ndata: {"run_id": "research-0001", "status": "stopped"}\n\n';
  await page.route(`**${ROUTE}`, (route: Route) =>
    route.request().method() === "POST"
      ? route.fulfill({ status: 200, contentType: "text/event-stream", body: stopped })
      : route.fulfill({ status: 200, contentType: "application/json", body: '{"status":"none"}' }),
  );
  await tab(page).getByRole("button", { name: words.run }).click();
  await expect(tab(page).locator("[data-alert=error]")).toContainText(words.errors.writer_unavailable);
  await expect(tab(page).getByRole("button", { name: copy.answer.tryAgain })).toBeVisible();
});

test("a run the service didn't answer says so with Try again, and keeps the page", async ({ page }) => {
  await open(page, { research: { body: await recorded("research-p156634-none.json") } });
  await page.route(`**${ROUTE}`, (route: Route) =>
    route.request().method() === "POST"
      ? route.fulfill({ status: 503, contentType: "application/json", body: '{"detail":"no"}' })
      : route.fulfill({ status: 200, contentType: "application/json", body: '{"status":"none"}' }),
  );
  await tab(page).getByRole("button", { name: words.run }).click();
  await expect(tab(page).locator("[data-alert=error]")).toContainText(words.runError);
  await expect(tab(page).getByRole("button", { name: copy.answer.tryAgain })).toBeVisible();
  await expect(tab(page).getByRole("button", { name: words.run })).toBeVisible();
});

// ── The read's states ───────────────────────────────────────────────────

test("a read the service didn't answer offers Try again, and an account that can't read Prism's tables is told so", async ({ page }) => {
  await open(page, { research: { status: 500, body: '{"detail":"no"}' } });
  await expect(tab(page)).toHaveAttribute("data-research", "error");
  await expect(tab(page).locator("[data-load-error=service]")).toContainText(words.error);
  await expect(tab(page).getByRole("button", { name: copy.answer.tryAgain })).toBeVisible();

  await open(page, { research: { status: 403, body: '{"detail":"forbidden"}' } });
  await expect(tab(page).locator("[data-load-error=permission]")).toContainText(words.permission);
  await expect(tab(page).getByRole("button", { name: copy.answer.tryAgain })).toHaveCount(0);
});

// ── The PDF ─────────────────────────────────────────────────────────────

test("Download as PDF prints the brief: the cover, then one Letter sheet per section with the sample's header and footer", async ({ page }) => {
  await open(page);
  const data = await brief();
  await page.evaluate(() => {
    const counted = window as unknown as { printed: number };
    counted.printed = 0;
    window.print = () => {
      counted.printed += 1;
    };
  });
  await tab(page).getByRole("button", { name: words.print }).click();
  expect(await page.evaluate(() => (window as unknown as { printed: number }).printed)).toBe(1);

  // On screen the print view is never shown.
  await expect(page.locator("[data-research-print]")).toBeHidden();
  await page.emulateMedia({ media: "print" });
  const view = page.locator("[data-research-print]");
  await expect(view).toBeVisible();
  // The app's chrome is hidden: the bar, the sidebar, the page with its head and tabs.
  await expect(page.getByRole("main")).toBeHidden();
  await expect(page.getByRole("navigation", { name: "Project sections" })).toBeHidden();

  // The sections in the sample's order, the developments eleven to a sheet and each site on its own.
  const developmentSheets = Math.ceil(data.sections.developments.length / 11);
  const labels = [
    words.section.picture,
    ...Array.from({ length: developmentSheets }, (_, index) => (index === 0 ? words.section.developments : words.section.developmentsMore)),
    ...data.sections.by_site.map((site) => (site as { location?: { name: string } }).location?.name ?? words.section.bySite),
    words.section.voices,
    words.section.questions,
    words.section.sources,
  ];
  const sheets = view.locator(".research-sheet");
  await expect(sheets).toHaveCount(labels.length + 1);
  // The cover first, navy, with no running header or footer.
  const cover = sheets.first();
  await expect(cover).toHaveAttribute("data-sheet", "cover");
  await expect(cover).toContainText("What is happening on the ground: Water and Sanitation Development Project");
  await expect(cover.locator("[data-sheet-header], [data-sheet-footer]")).toHaveCount(0);
  expect(await cover.evaluate((el) => getComputedStyle(el).backgroundColor)).toBe("rgb(0, 34, 68)");

  // Every other sheet: the running header (the project and the section), the footer (Prism, the read date, the one-line
  // disclaimer and the number), US Letter wide, and a page break after it.
  const rest = view.locator(".research-sheet:not([data-sheet=cover])");
  await expect(rest.locator("[data-sheet-label]")).toHaveText(labels);
  await expect(rest.locator("[data-sheet-header] > span:first-child")).toHaveText(labels.map(() => "Deep research · Water and Sanitation Development Project (P156634)"));
  await expect(rest.locator("[data-sheet-footer] > span:first-child")).toHaveText(
    labels.map(() => "Prism · read on November 5, 2026 · an independent demo built on World Bank open data, not a World Bank product"),
  );
  await expect(rest.locator("[data-sheet-number]")).toHaveText(labels.map((_, index) => String(index + 1)));
  const shapes = await sheets.evaluateAll((all) =>
    all.map((sheet) => {
      const style = getComputedStyle(sheet);
      return { width: Math.round(sheet.getBoundingClientRect().width), breakAfter: style.breakAfter, page: style.page };
    }),
  );
  // 215.9 mm is 816 CSS pixels; the last sheet breaks nowhere.
  expect(shapes.map((shape) => shape.width)).toEqual(shapes.map(() => 816));
  expect(shapes.slice(0, -1).map((shape) => shape.breakAfter)).toEqual(shapes.slice(0, -1).map(() => "page"));
  expect(shapes.map((shape) => shape.page)).toEqual(shapes.map(() => "research"));
  // Each sheet carries its markers as the sample's small numbered pills, and the sources sheet lists every cited item.
  await expect(sheets.nth(1).locator("h1 .cite").first()).toHaveText("1");
  const cited = new Set(
    [data.sections.headline!, ...data.sections.picture, ...data.sections.bottom_line, ...data.sections.developments.flatMap((row) => row.sentences),
      ...data.sections.by_site.flatMap((group) => [group.title, ...group.sentences]), ...data.sections.voices,
      ...data.sections.questions.flatMap((question) => question.sentences), ...data.sections.could_not_see].flatMap((sentence) => sentence.evidence_ids),
  );
  await expect(sheets.last().locator("ol.sources li")).toHaveCount(cited.size);
  // A source not reached keeps its one line on paper too.
  for (const entry of data.coverage.filter((one) => !one.reached)) {
    await expect(rest.locator(`[data-not-reached="${entry.source}"]`)).toContainText(entry.note!);
  }
});

// ── Accessibility, keyboard and reflow ─────────────────────────────────

test("the brief passes axe at WCAG 2.2 AA, and Tab reaches Download as PDF, Research again and the markers", async ({ page }) => {
  await open(page);
  await expect(tab(page)).toHaveAttribute("data-research", "ready");
  const results = await scan(page);
  expect(results.violations.map((violation) => `${violation.id}: ${violation.nodes.map((node) => node.target.join(" ")).join(", ")}`)).toEqual([]);

  // From the tab row, Tab reaches the tab's two buttons and then the headline's first marker.
  await main(page).getByRole("navigation", { name: "Project sections" }).getByRole("link", { name: copy.projectPage.tab.research }).focus();
  const reached: string[] = [];
  for (let press = 0; press < 12 && !reached.includes("marker"); press += 1) {
    await page.keyboard.press("Tab");
    reached.push(
      await page.evaluate(() => {
        const at = document.activeElement as HTMLElement | null;
        if (!at) return "";
        if (at.dataset.citation) return "marker";
        return at.textContent?.trim() ?? "";
      }),
    );
  }
  expect(reached).toContain(words.print);
  expect(reached).toContain(words.again);
  expect(reached.indexOf(words.print)).toBeLessThan(reached.indexOf("marker"));
  // Enter on the marker opens the drawer.
  await page.keyboard.press("Enter");
  await expect(drawer(page)).toBeVisible();
});

test("with no brief yet, Tab reaches Research this project, and the state passes axe", async ({ page }) => {
  await open(page, { research: { body: await recorded("research-p156634-none.json") } });
  await expect(tab(page)).toHaveAttribute("data-research", "none");
  const results = await scan(page);
  expect(results.violations.map((violation) => violation.id)).toEqual([]);
  const button = tab(page).getByRole("button", { name: words.run });
  await main(page).getByRole("navigation", { name: "Project sections" }).getByRole("link", { name: copy.projectPage.tab.research }).focus();
  for (let press = 0; press < 6; press += 1) {
    await page.keyboard.press("Tab");
    if (await button.evaluate((el) => el === document.activeElement)) break;
  }
  await expect(button).toBeFocused();
});

test("at 320 px the brief reflows with no sideways scroll and passes axe", async ({ page }) => {
  await open(page, { width: 320 });
  await expect(tab(page)).toHaveAttribute("data-research", "ready");
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(320);
  // The two Sentinel-2 years stay side by side, inside the column.
  const grids = tab(page).locator("[data-s2-grid]");
  const [left, right] = [(await grids.nth(0).boundingBox())!, (await grids.nth(1).boundingBox())!];
  expect(Math.abs(left.y - right.y)).toBeLessThan(2);
  expect(right.x + right.width).toBeLessThanOrEqual(320);
  const results = await scan(page);
  expect(results.violations.map((violation) => `${violation.id}: ${violation.nodes.map((node) => node.target.join(" ")).join(", ")}`)).toEqual([]);
});
