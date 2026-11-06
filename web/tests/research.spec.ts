// The Deep research tab (ticket 149) at seam 4: the brief GET /api/projects/{pid}/research returns, the run POST
// streams, the evidence drawer a marker opens, and the print view "Download as PDF" prints. The responses are ticket
// 148's routes' own, recorded in tests/fixtures/api (research-p156634.json, research-p156634-none.json,
// research-p156634.sse and evidence-research-item-p156634-star.json) by tests/record_research_api.py from the run
// ticket 147's seed keeps. Every count below is read from the recording, through the tab's own reader (briefFrom).
// Ticket 158 adds the pictures: the tiles through Prism's route, the PDF that waits for them, a frame that fails saying
// why, and P161305's print (research-p161305.json, the App's answer of November 6, 2026 at 07:25 UTC, and
// field-photos-p161305.json, the seed's photos through the route's own listing).
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import type { Page, Route } from "@playwright/test";
import { copy } from "../src/copy";
import { fill } from "../src/routes";
import { briefFrom, briefNumbers, developmentSheets, itemFor, notReachedIn, satelliteFor, sourceSheets, tileYear, type Brief } from "../src/lib/research";
import { scan } from "./axe";
import { expect, mockApi, recorded, test, viewAnswers } from "./mocked";

type Answer = { status?: number; body: string };

const PATH = "/projects/P156634/research";
const ROUTE = "/api/projects/P156634/research";
const words = copy.research;

// How many items the brief cites, each once: the sources sheets list them eighteen to a sheet.
function citedCount(data: Brief): number {
  const { sections } = data;
  const all = [sections.headline!, ...sections.picture, ...sections.bottom_line, ...sections.developments.flatMap((row) => row.sentences),
    ...sections.by_site.flatMap((group) => [group.title, ...group.sentences]), ...sections.voices,
    ...sections.questions.flatMap((question) => question.sentences), ...sections.could_not_see];
  return new Set(all.flatMap((sentence) => sentence.evidence_ids)).size;
}

async function brief(): Promise<Brief> {
  const read = briefFrom(JSON.parse(await recorded("research-p156634.json")));
  if (read.status !== "ready") throw new Error("research-p156634.json holds no brief.");
  return read;
}

// The Sentinel-2 tiles come through Prism's own route (ticket 158; src/strata/server/research_tiles.py): each answers
// with a 1 px image here, so no test reaches the network, and every address the page asks is kept, EOX's included.
// A page route wins over the context's route that refuses outside requests, and over mockApi's, registered before it.
const PIXEL = Buffer.from("R0lGODlhAQABAIAAAP///wAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw==", "base64");
const TILES = "**/api/research/tiles/**";
type Tiles = (route: Route) => Promise<void> | void;
const pixel: Tiles = (route) => route.fulfill({ status: 200, contentType: "image/gif", body: PIXEL });

async function open(
  page: Page,
  { width = 1440, research, extra = {}, tiles = pixel, asked = [] }: { width?: number; research?: Answer; extra?: Record<string, Answer>; tiles?: Tiles; asked?: string[] } = {},
) {
  await page.setViewportSize({ width, height: 900 });
  page.on("request", (request) => {
    if (/tiles\.maps\.eox\.at|\/api\/research\/tiles\//.test(request.url())) asked.push(request.url());
  });
  await page.route("https://tiles.maps.eox.at/**", (route) => route.fulfill({ status: 200, contentType: "image/gif", body: PIXEL }));
  const unrecorded = await mockApi(page, {
    ...(await viewAnswers()),
    "/api/me": { body: await recorded("me.json") },
    "/api/freshness": { body: await recorded("freshness.json") },
    "/api/projects/P156634": { body: await recorded("project-p156634.json") },
    [ROUTE]: research ?? { body: await recorded("research-p156634.json") },
    // The team's field photos under the brief (ticket 150; web/tests/field-photos.spec.ts): none yet.
    "/api/projects/P156634/field-photos": { body: await recorded("field-photos-p156634-none.json") },
    "/api/evidence": { body: await recorded("evidence-research-item-p156634-star.json") },
    "/api/evidence/opened": { body: '{"opened":[],"recorded":true}' },
    ...extra,
  });
  await page.route(TILES, tiles);
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

// The run's stream as blocks, each event with its type and data, and the plan it sent.
type Block = { text: string; type: string; data: Record<string, unknown> };
function blocksOf(sse: string): Block[] {
  return sse
    .split("\n\n")
    .filter((text) => text.startsWith("event: "))
    .map((text) => {
      const [kind, data] = text.split("\n");
      return { text: `${text}\n\n`, type: kind.replace(/^event: /, ""), data: JSON.parse(data.replace(/^data: /, "")) };
    });
}
type Plan = { steps: { id: string; kind: string; label: string }[]; usual_seconds: [number, number] };
const planOf = (blocks: Block[]) => blocks.find((block) => block.type === "plan")!.data as unknown as Plan;

// The research POST answers with a stream the test writes block by block, so each step can be read as it comes; every
// change to the rail's live region is kept in order, as a screen reader would hear it.
async function heldStream(page: Page) {
  await page.addInitScript((route) => {
    const open = window.fetch.bind(window);
    const encoder = new TextEncoder();
    let writer: ReadableStreamDefaultController<Uint8Array> | null = null;
    const said: string[] = [];
    const shared = window as unknown as { research: { send: (text: string) => void; end: () => void }; said: string[] };
    shared.said = said;
    shared.research = { send: (text) => writer?.enqueue(encoder.encode(text)), end: () => writer?.close() };
    window.fetch = (input, init) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
      if (init?.method !== "POST" || new URL(url, location.href).pathname !== route) return open(input, init);
      const body = new ReadableStream<Uint8Array>({ start: (controller) => void (writer = controller) });
      return Promise.resolve(new Response(body, { status: 200, headers: { "Content-Type": "text/event-stream" } }));
    };
    new MutationObserver(() => {
      const line = document.querySelector("[data-research-progress] [aria-live]")?.textContent ?? "";
      if (line && said[said.length - 1] !== line) said.push(line);
    }).observe(document, { subtree: true, childList: true, characterData: true });
  }, ROUTE);
  return {
    send: (blocks: Block[]) => page.evaluate((text) => (window as unknown as { research: { send: (text: string) => void } }).research.send(text), blocks.map((block) => block.text).join("")),
    end: () => page.evaluate(() => (window as unknown as { research: { end: () => void } }).research.end()),
    said: () => page.evaluate(() => (window as unknown as { said: string[] }).said),
  };
}

const rail = (page: Page) => tab(page).locator("[data-research-progress]");
const row = (page: Page, id: string) => rail(page).locator(`[data-progress-id="${id}"]`);

// The present-tense sentence the live region says when a step starts, in the ask box's words.
function runningSentence(step: { id: string; kind: string; label: string }): string {
  if (step.kind === "facts") return words.steps.facts.running;
  if (step.kind === "writing") return words.steps.write.running;
  if (step.kind === "checking") return words.steps.check.running;
  return words.steps.source.running(words.source[step.id.replace(/^source-/, "")] ?? step.label);
}

test("a run lists every planned step at once, fills its meter step by step, counts the checked sentences and says each step once", async ({ page }) => {
  const blocks = blocksOf(await recorded("research-p156634.sse"));
  const plan = planOf(blocks);
  const stream = await heldStream(page);
  // The page's clock moves only when the test moves it, so the elapsed line can be read exactly.
  await page.clock.install({ time: new Date("2026-11-05T10:30:00Z") });
  await open(page, { research: { body: await recorded("research-p156634-none.json") } });
  await tab(page).getByRole("button", { name: words.run }).click();
  await expect(tab(page)).toHaveAttribute("data-research", "running");

  const steps = (id: string, status?: string) => blocks.filter((block) => block.type === "step" && block.data.id === id && (!status || block.data.status === status));
  // The facts, then the plan: every planned row is on screen at once, the ones to come marked "to do".
  await stream.send(steps("facts", "running"));
  await expect(row(page, "facts")).toHaveAttribute("data-progress-step", "running");
  await stream.send(steps("facts", "done"));
  await stream.send(blocks.filter((block) => block.type === "plan"));
  const rows = rail(page).locator("[data-progress-id]");
  await expect(rows).toHaveCount(plan.steps.length);
  await expect(rows.locator("[data-progress-title]")).toHaveText(plan.steps.map((step) => new RegExp(`^${escaped(words.progress.label[step.kind] ?? step.label)}`)));
  await expect(row(page, "facts")).toHaveAttribute("data-progress-step", "done");
  for (const step of plan.steps.slice(1)) {
    await expect(row(page, step.id)).toHaveAttribute("data-progress-step", "todo");
    await expect(row(page, step.id)).toContainText(words.progress.state.todo);
  }
  const meter = rail(page).getByRole("progressbar", { name: words.progress.meter });
  await expect(meter).toHaveAttribute("aria-valuemin", "0");
  await expect(meter).toHaveAttribute("aria-valuemax", String(plan.steps.length));
  await expect(meter).toHaveAttribute("aria-valuenow", "1");
  // The step count, the elapsed clock and the usual range, in whole minutes.
  const [low, high] = plan.usual_seconds.map((seconds) => String(Math.round(seconds / 60)));
  await page.clock.runFor(27_000);
  await expect(rail(page).locator("[data-progress-line]")).toHaveText(
    `${fill(words.progress.step, { n: "2", total: String(plan.steps.length) })} · ${fill(words.progress.elapsed, { clock: "0:27" })} · ${words.progress.usual(low, high)}`,
  );

  // The sources one by one: the meter rises with each, and a source not reached says so with its note.
  const sources = plan.steps.filter((step) => step.kind === "source");
  let done = 1;
  for (const source of sources) {
    await stream.send(steps(source.id, "running"));
    await expect(row(page, source.id)).toHaveAttribute("data-progress-step", "running");
    await expect(row(page, source.id)).toContainText(words.progress.state.running);
    await stream.send(blocks.filter((block) => block.type === "step" && block.data.id === source.id && block.data.status !== "running"));
    done += 1;
    await expect(meter).toHaveAttribute("aria-valuenow", String(done));
  }
  const missed = blocks.filter((block) => block.type === "step" && block.data.status === "not_reached");
  expect(missed.length, "the recording has a source not reached").toBeGreaterThan(0);
  for (const block of missed) {
    await expect(row(page, String(block.data.id))).toHaveAttribute("data-progress-step", "not_reached");
    await expect(row(page, String(block.data.id)).locator("[data-progress-result]")).toHaveText(words.progress.result.notReached);
    await expect(rail(page).locator(`[data-progress-note="${String(block.data.id)}"]`)).toContainText(String(block.data.note));
  }
  const reached = blocks.find((block) => block.type === "step" && block.data.kind === "source" && block.data.status === "done" && Number(block.data.items) > 1)!;
  await expect(row(page, String(reached.data.id)).locator("[data-progress-result]")).toHaveText(words.progress.kept.several(String(reached.data.items)));

  // Writing, then checking: three sentences checked of those the writer wrote.
  await stream.send(steps("writing", "running"));
  await expect(row(page, "writing").locator("[data-progress-result]")).toHaveText(words.progress.writing.running);
  await stream.send(steps("writing", "done"));
  const written = String(steps("writing", "done")[0].data.sentences);
  await expect(row(page, "writing").locator("[data-progress-result]")).toHaveText(words.progress.writing.several(written));
  await stream.send(steps("checking", "running"));
  await stream.send(blocks.filter((block) => block.type === "sentence").slice(0, 3));
  await expect(row(page, "checking").locator("[data-progress-result]")).toHaveText(words.progress.checked("3", written));
  await expect(meter).toHaveAttribute("aria-valuenow", String(plan.steps.length - 1));
  await expect(rail(page)).toContainText(words.progress.keepOpen);

  // Past the usual high end the line says so; with no event for 30 seconds, the running step says it is still working.
  await expect(row(page, "checking")).not.toContainText(copy.steps.stillWorking);
  await page.clock.runFor(plan.usual_seconds[1] * 1000);
  await expect(rail(page).locator("[data-progress-line]")).toContainText(`elapsed · ${words.progress.longer}`);
  await expect(rail(page).locator("[data-progress-line]")).not.toContainText(words.progress.usual(low, high));
  await expect(row(page, "checking")).toContainText(copy.steps.stillWorking);

  // One sentence per step, in the plan's order, said once each.
  expect(await stream.said()).toEqual(plan.steps.map(runningSentence));
  await scan(page, "[data-research-progress]");
  await stream.end();
});

// Ticket 159: every part of the rail a person reads, measured as the stream goes on. The meter's fill and the running
// icon change inside their own boxes, so they are not measured; the boxes are.
const RAIL_PARTS = [
  "[data-progress-heading]",
  "[data-progress-line]",
  "[data-progress-read]",
  "[data-research-progress] [role=progressbar]",
  "[data-progress-id]",
  "[data-progress-id] [data-progress-icon]",
  "[data-progress-keep]",
  "[data-research-progress] [data-disclosure]",
].join(", ");
type Box = { part: string; top: number; left: number; height: number };

// Sends one block of the stream, waits two frames so React has drawn it, and returns where each part of the rail sits.
async function sendAndMeasure(page: Page, text: string): Promise<Box[]> {
  return page.evaluate(
    async ({ text, parts }) => {
      if (text) (window as unknown as { research: { send: (text: string) => void } }).research.send(text);
      await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
      return [...document.querySelectorAll<HTMLElement>(parts)].map((element, index) => {
        const box = element.getBoundingClientRect();
        const part = element.dataset.progressId ?? Object.keys(element.dataset)[0] ?? element.getAttribute("role") ?? String(index);
        return { part: `${index} ${part}`, top: box.top + window.scrollY, left: box.left, height: box.height };
      });
    },
    { text, parts: RAIL_PARTS },
  );
}

test("from the plan to the last check nothing in the rail moves: each row is one line with its result, the read date is said once, and the notes wait behind a disclosure", async ({ page }) => {
  const blocks = blocksOf(await recorded("research-p156634.sse"));
  const plan = planOf(blocks);
  const stream = await heldStream(page);
  await page.clock.install({ time: new Date("2026-11-05T10:30:00Z") });
  // The App's setting: the run writes from the sources read ahead of time (ticket 152).
  await open(page, { research: { body: demoSetting(await recorded("research-p156634-none.json")) } });
  await tab(page).getByRole("button", { name: words.run }).click();
  const planAt = blocks.findIndex((block) => block.type === "plan");
  await stream.send(blocks.slice(0, planAt + 1));
  const rows = rail(page).locator("[data-progress-id]");
  await expect(rows).toHaveCount(plan.steps.length);

  // Where each part sits once the plan has come; every later event, one at a time, must leave it there. The clock
  // passes 0:59 halfway, so "0:59" and "1:00" are measured too.
  const before = await sendAndMeasure(page, "");
  expect(before.length, "six parts, and each row with its icon box").toBe(6 + 2 * plan.steps.length);
  const later = blocks.slice(planAt + 1).filter((block) => block.type !== "done");
  const moved: string[] = [];
  const sources = plan.steps.filter((step) => step.kind === "source");
  let measured = 0;
  for (const [index, block] of later.entries()) {
    if (index === Math.floor(later.length / 4)) {
      await page.clock.runFor(59_000);
      await expect(rail(page).locator("[data-progress-clock]")).toHaveText(/^0:59|^1:0\d/);
    }
    const now = await sendAndMeasure(page, block.text);
    measured += 1;
    for (const [at, box] of now.entries()) {
      const was = before[at];
      if (!was || was.part !== box.part || was.top !== box.top || was.left !== box.left || was.height !== box.height) {
        moved.push(`${block.type} ${String(block.data.id ?? "")}: ${JSON.stringify(was)} -> ${JSON.stringify(box)}`);
      }
    }
    if (now.length !== before.length) moved.push(`${block.type}: ${before.length} parts became ${now.length}`);
    // Mid-run, as a person sees it on the App: saved for the ticket's report when asked.
    if (block.type === "step" && block.data.id === sources[5].id && block.data.status === "running" && process.env.RESEARCH_PROGRESS_SHOT) {
      await tab(page).screenshot({ path: process.env.RESEARCH_PROGRESS_SHOT });
    }
  }
  console.log(`Rail layout: ${before.length} parts measured after each of ${measured} events; ${moved.length} moved.`);
  expect(moved).toEqual([]);
  await expect(rail(page).locator("[data-progress-clock]")).toHaveText(/^1:\d\d$/);

  // Each row is one line: its label, then only its result. The label never wraps, and carries its full text in title.
  const lines = await rows.evaluateAll((items) =>
    items.map((item) => {
      const label = item.querySelector<HTMLElement>("[data-progress-title]")!;
      return { wraps: item.scrollHeight > item.clientHeight || label.scrollHeight > label.clientHeight, height: item.getBoundingClientRect().height, title: label.title };
    }),
  );
  expect(lines.filter((line) => line.wraps)).toEqual([]);
  expect(new Set(lines.map((line) => line.height)).size, "every row has the same height").toBe(1);
  expect(lines.map((line) => line.title)).toEqual(plan.steps.map((step) => words.progress.label[step.kind] ?? step.label));
  const result = (id: string) => row(page, id).locator("[data-progress-result]");
  await expect(result("facts")).toHaveText(words.progress.result.facts);
  const done = (id: string) => blocks.find((block) => block.type === "step" && block.data.id === id && block.data.status !== "running")!.data;
  for (const source of sources) {
    const sent = done(source.id);
    const items = Number(sent.items ?? 0);
    await expect(result(source.id)).toHaveText(
      sent.status === "not_reached" ? words.progress.result.notReached : items === 0 ? words.progress.kept.none : items === 1 ? words.progress.kept.one : words.progress.kept.several(String(items)),
    );
  }
  await expect(result("writing")).toHaveText(words.progress.writing.several(String(done("writing").sentences)));
  await expect(result("checking")).toHaveText(words.progress.removed.none);

  // No row carries a date; the sentence under the step count says the day the sources were read, once on screen.
  for (const text of await rows.allInnerTexts()) expect(text).not.toMatch(/November|2026/);
  await expect(rail(page).locator("[data-progress-read]")).toHaveText(words.readOnStored("November 5, 2026"));
  expect((await rail(page).innerText()).split("November 5, 2026").length - 1).toBe(1);

  // The notes wait behind one disclosure, closed, named for the source not reached; opened, it lists each source's note
  // and moves nothing above it.
  const notes = rail(page).locator("[data-disclosure]");
  await expect(notes).toHaveAttribute("data-disclosure", "closed");
  const button = notes.getByRole("button", { name: words.progress.notes.missed });
  await expect(button).toHaveAttribute("aria-expanded", "false");
  await button.click();
  await expect(notes).toHaveAttribute("data-disclosure", "open");
  for (const source of sources) {
    const sent = done(source.id);
    await expect(notes.locator(`[data-progress-note="${source.id}"]`)).toContainText(String(sent.note));
  }
  const opened = await sendAndMeasure(page, "");
  expect(opened.map(({ part, top, left }) => ({ part, top, left }))).toEqual(before.map(({ part, top, left }) => ({ part, top, left })));
  await scan(page, "[data-research-progress]");
  await stream.end();
});

test("a rail with every source reached names its notes About these sources, and under reduced motion only the words change", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  const blocks = blocksOf(await recorded("research-p156634.sse")).filter((block) => block.data.status !== "not_reached");
  const stream = await heldStream(page);
  await open(page, { research: { body: demoSetting(await recorded("research-p156634-none.json")) } });
  await tab(page).getByRole("button", { name: words.run }).click();
  const at = blocks.findIndex((block) => block.type === "step" && block.data.id === "source-outlet_feeds" && block.data.status === "running");
  await stream.send(blocks.slice(0, at + 1));
  await expect(row(page, "source-outlet_feeds")).toHaveAttribute("data-progress-step", "running");
  await expect(rail(page).getByRole("button", { name: words.progress.notes.all })).toBeVisible();
  // The spinner stands still and the meter's fill does not ease.
  const motion = await rail(page).evaluate((element) => ({
    spin: getComputedStyle(element.querySelector("[data-progress-step=running] [data-progress-icon] svg")!).animationName,
    meter: getComputedStyle(element.querySelector("[role=progressbar] > div")!).transitionDuration,
  }));
  expect(motion).toEqual({ spin: "none", meter: "0s" });
  await stream.end();
});

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

  // Every planned step, done, in its order; a source not reached is its own row with its note.
  const steps = streamSteps(sse);
  const plan = planOf(blocksOf(sse));
  const rows = rail(page).locator("[data-progress-id]");
  await expect(rows).toHaveCount(plan.steps.length);
  await expect(rows.first()).toHaveAttribute("data-progress-step", "done");
  const missed = steps.filter((step) => step.status === "not_reached");
  expect(missed.length, "the recording has a source not reached").toBeGreaterThan(0);
  for (const step of missed) {
    await expect(row(page, step.id)).toHaveAttribute("data-progress-step", "not_reached");
    await expect(rail(page).locator(`[data-progress-note="${step.id}"]`)).toContainText(step.note!);
  }
  const removed = steps.find((step) => step.kind === "checking")!.removed ?? 0;
  await expect(rows.last().locator("[data-progress-result]")).toHaveText(removed === 0 ? words.progress.removed.none : removed === 1 ? words.progress.removed.one : words.progress.removed.several(String(removed)));
  await expect(rail(page).getByRole("progressbar")).toHaveAttribute("aria-valuenow", String(plan.steps.length));
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

// ── The demo's setting (ticket 152): research.live_sources false, briefs written only from stored runs ──────────

const demoSetting = (body: string) => JSON.stringify({ ...JSON.parse(body), live_sources: false });

test("with the demo's setting, the tab says no brief has been prepared, the rail says once the day the sources were read, and the buttons keep their live names", async ({ page }) => {
  const sse = await recorded("research-p156634.sse");
  const stored = demoSetting(await recorded("research-p156634.json"));
  let release = () => {};
  const held = new Promise<void>((resolve) => (release = resolve));
  await open(page, { research: { body: demoSetting(await recorded("research-p156634-none.json")) } });
  await expect(tab(page)).toHaveAttribute("data-research", "none");
  await expect(tab(page)).toContainText(words.notPrepared);
  await expect(tab(page)).not.toContainText(words.none);
  await page.route(`**${ROUTE}`, async (route: Route) => {
    if (route.request().method() === "POST") return route.fulfill({ status: 200, contentType: "text/event-stream", body: sse });
    await held;
    return route.fulfill({ status: 200, contentType: "application/json", body: stored });
  });
  await tab(page).getByRole("button", { name: words.run }).click();

  // The rail says once the day the stored run read the sources; each source it reached says what it kept, with no date.
  const reached = streamSteps(sse).filter((step) => step.kind === "source" && step.status === "done");
  expect(reached.length, "the recording has sources from the stored run").toBeGreaterThan(0);
  await expect(rail(page).locator("[data-progress-read]")).toHaveText(words.readOnStored("November 5, 2026"));
  const results = rail(page).locator("[data-progress-id] [data-progress-result]");
  await expect(results.filter({ hasText: /^kept / })).toHaveCount(reached.length);
  await expect(results.filter({ hasText: /2026/ })).toHaveCount(0);

  release();
  await expect(tab(page)).toHaveAttribute("data-research", "ready");
  await expect(tab(page).getByRole("button", { name: words.again })).toBeVisible();
  await expect(tab(page)).toContainText(words.readOnStored("November 5, 2026"));
});

test("with the demo's setting, a writer that fails keeps the stored brief with one line, and no error", async ({ page }) => {
  const stored = demoSetting(await recorded("research-p156634.json"));
  await open(page, { research: { body: stored } });
  const kept = 'event: step\ndata: {"id": "facts", "kind": "facts", "status": "done"}\n\nevent: step\ndata: {"id": "writing", "kind": "writing", "status": "running"}\n\nevent: step\ndata: {"id": "writing", "kind": "writing", "status": "done", "kept_from": "2026-11-05", "label": "Writing: kept the brief of November 5, 2026"}\n\nevent: done\ndata: {"run_id": "research-0002", "status": "kept"}\n\n';
  let release = () => {};
  const held = new Promise<void>((resolve) => (release = resolve));
  await page.route(`**${ROUTE}`, async (route: Route) => {
    if (route.request().method() === "POST") return route.fulfill({ status: 200, contentType: "text/event-stream", body: kept });
    await held;
    return route.fulfill({ status: 200, contentType: "application/json", body: stored });
  });
  await tab(page).getByRole("button", { name: words.again }).click();
  await expect(rail(page).locator("[data-progress-id]").last().locator("[data-progress-result]")).toHaveText(words.progress.result.keptBrief);
  release();
  await expect(tab(page)).toHaveAttribute("data-research", "ready");
  await expect(tab(page).locator("[data-alert=error]")).toHaveCount(0);
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

test("Download as PDF prints the brief: the cover, then one Letter sheet per section with its header, a navy rule under its title and its page number", async ({ page }) => {
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
  await expect.poll(() => page.evaluate(() => (window as unknown as { printed: number }).printed)).toBe(1);

  // On screen the print view is never shown.
  await expect(page.locator("[data-research-print]")).toBeHidden();
  await page.emulateMedia({ media: "print" });
  const view = page.locator("[data-research-print]");
  await expect(view).toBeVisible();
  // The app's chrome is hidden: the bar, the sidebar, the page with its head and tabs.
  await expect(page.getByRole("main")).toBeHidden();
  await expect(page.getByRole("navigation", { name: "Project sections" })).toBeHidden();

  // The sections in the sample's order, the developments eleven to a sheet and each site on its own.
  const devSheets = developmentSheets(data.sections.developments, notReachedIn(data, "developments").length).length;
  const labels = [
    words.section.picture,
    ...Array.from({ length: devSheets }, (_, index) => (index === 0 ? words.section.developments : words.section.developmentsMore)),
    ...data.sections.by_site.map((site) => (site as { location?: { name: string } }).location?.name ?? words.section.bySite),
    words.section.voices,
    words.section.questions,
    words.section.couldNotSee,
    ...Array.from({ length: sourceSheets(data, [...briefNumbers(data.sections).keys()]).length }, (_, index) => (index === 0 ? words.section.sources : words.section.sourcesMore)),
  ];
  const sheets = view.locator(".research-sheet");
  await expect(sheets).toHaveCount(labels.length + 1);
  // The cover first, navy, with no running header or footer.
  const cover = sheets.first();
  await expect(cover).toHaveAttribute("data-sheet", "cover");
  await expect(cover).toContainText("What is happening on the ground: Water and Sanitation Development Project");
  // The cover keeps the project line and the closing date, and says nothing about the run or the sample (ticket 156).
  await expect(cover).toContainText("closing date October 31, 2026");
  await expect(cover).not.toContainText("Read on");
  await expect(cover).not.toContainText(words.disclaimer);
  await expect(cover.locator("[data-sheet-header], [data-sheet-footer]")).toHaveCount(0);
  // The Prism wordmark is no taller than the World Bank logo beside it.
  const [logoHeight, brandHeight] = await cover.evaluate((el) => [el.querySelector(".cover-top img")!.getBoundingClientRect().height, el.querySelector(".brand > div")!.getBoundingClientRect().height]);
  expect(brandHeight).toBeLessThanOrEqual(logoHeight);
  expect(await cover.evaluate((el) => getComputedStyle(el).backgroundColor)).toBe("rgb(0, 34, 68)");

  // Every other sheet: the running header (the project and the section), its section's title over a navy rule, a footer
  // that is its page number alone, US Letter wide, and a page break after it. The disclaimer sits once, on the last.
  const rest = view.locator(".research-sheet:not([data-sheet=cover])");
  await expect(rest.locator("[data-sheet-label]")).toHaveText(labels);
  await expect(rest.locator("[data-sheet-header] > span:first-child")).toHaveText(labels.map(() => "Deep research · Water and Sanitation Development Project (P156634)"));
  await expect(rest.locator("[data-sheet-footer]")).toHaveText(labels.map((_, index) => String(index + 1)));
  await expect(rest.locator("[data-sheet-number]")).toHaveText(labels.map((_, index) => String(index + 1)));
  await expect(view.locator("[data-disclaimer]")).toHaveCount(1);
  await expect(sheets.last().locator("[data-disclaimer]")).toHaveText(words.disclaimer);
  const rules = await rest.evaluateAll((all) =>
    all.map((sheet) => {
      const titles = sheet.querySelectorAll(".body > h1.section");
      return titles.length === 1 ? getComputedStyle(titles[0]).borderBottomColor : `${titles.length} titles`;
    }),
  );
  expect(rules).toEqual(labels.map(() => "rgb(0, 34, 68)"));
  // The picture as short paragraphs, as the writer grouped it; developments, sites and questions one sentence a bullet.
  const paragraphs = new Set(data.sections.picture.map((sentence) => sentence.paragraph)).size;
  await expect(view.locator("[data-picture-paragraph]")).toHaveCount(paragraphs);
  expect(paragraphs).toBeGreaterThan(1);
  await expect(view.locator("table.dev ul.bullets > li")).toHaveCount(data.sections.developments.flatMap((row) => row.sentences).length);
  await expect(view.locator("ol.questions ul.bullets > li")).toHaveCount(data.sections.questions.flatMap((question) => question.sentences).length);
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
  await expect(sheets.nth(1).locator(".lead .cite").first()).toHaveText("1");
  const cited = new Set(
    [data.sections.headline!, ...data.sections.picture, ...data.sections.bottom_line, ...data.sections.developments.flatMap((row) => row.sentences),
      ...data.sections.by_site.flatMap((group) => [group.title, ...group.sentences]), ...data.sections.voices,
      ...data.sections.questions.flatMap((question) => question.sentences), ...data.sections.could_not_see].flatMap((sentence) => sentence.evidence_ids),
  );
  await expect(view.locator("ol.sources li")).toHaveCount(cited.size);
  expect(citedCount(data)).toBe(cited.size);
  // A source not reached keeps its one line on paper too.
  for (const entry of data.coverage.filter((one) => !one.reached)) {
    await expect(rest.locator(`[data-not-reached="${entry.source}"]`)).toContainText(entry.note!);
  }
});

test("the print shows each of the team's field photos under the site whose words name its place, with its caption", async ({ page }) => {
  await open(page, { extra: { "/api/projects/P156634/field-photos": { body: await recorded("field-photos-p156634.json") } } });
  await page.emulateMedia({ media: "print" });
  const view = page.locator("[data-research-print]");
  const photo = view.locator('[data-print-photo="fph-000000000001"]');
  await expect(photo).toHaveCount(1);
  await expect(photo).toContainText("The new intake pipe");
  await expect(view.locator(".research-sheet", { has: page.locator(`[data-print-photo="fph-000000000001"]`) }).locator("h2")).toContainText("Baricho");
});

// ── The pictures (ticket 158): served by Prism, waited for, and explained when they fail ──────────

const JPEG = (name: string) => readFile(fileURLToPath(new URL(`../../data/fixture/field_photos/${name}`, import.meta.url)));
const print = (page: Page) => page.locator("[data-research-print]");

async function countPrints(page: Page) {
  await page.evaluate(() => {
    const counted = window as unknown as { printed: number };
    counted.printed = 0;
    window.print = () => {
      counted.printed += 1;
    };
  });
}
const printed = (page: Page) => page.evaluate(() => (window as unknown as { printed: number }).printed);

test("the grids ask Prism's tile route, never EOX, on the tab and in the print view", async ({ page }) => {
  const asked: string[] = [];
  await open(page, { asked });
  const tiles = tab(page).locator("[data-s2-grid] img");
  await expect(tiles).toHaveCount(18);
  for (const src of await tiles.evaluateAll((all) => all.map((img) => img.getAttribute("src")))) expect(src).toMatch(/^\/api\/research\/tiles\/\d{4}\/15\/\d+\/\d+\.jpg$/);
  await expect(print(page).locator(".tiles img")).toHaveCount(18);
  await expect.poll(() => asked.length).toBeGreaterThanOrEqual(18);
  expect(asked.filter((url) => url.includes("tiles.maps.eox.at"))).toEqual([]);
});

test("a tile that fails leaves its cell in surface-2 and the caption says how many did not load, in the tab and on paper", async ({ page }) => {
  // The tile server answers none of the first year's tiles and one of the last year's, once.
  const data = await brief();
  const item = data.sections.by_site.flatMap((site) => satelliteFor(data, site))[0];
  const [first, last] = [tileYear(item.image_urls[0])!, tileYear(item.image_urls[item.image_urls.length - 1])!];
  let one = true;
  await open(page, {
    tiles: (route) => {
      const year = /tiles\/(\d{4})\//.exec(route.request().url())![1];
      if (year === first || (year === last && one)) {
        if (year === last) one = false;
        return route.fulfill({ status: 502, contentType: "application/json", body: '{"code":"tile_server"}' });
      }
      return route.fulfill({ status: 200, contentType: "image/gif", body: PIXEL });
    },
  });
  const caption = tab(page).locator("[data-s2-figure] figcaption");
  await expect(caption).toContainText(words.tilesNone("9", first));
  await expect(caption).toContainText(new RegExp(`\\d of the 9 tiles for ${last} did not load from the tile server\\.`));
  await expect(tab(page).locator("[data-s2-grid] [data-tile-failed]").first()).toBeVisible();
  await page.emulateMedia({ media: "print" });
  const paper = print(page).locator("[data-print-satellite] .caption");
  await expect(paper).toContainText(words.tilesNone("9", first));
  expect(await print(page).locator("[data-tile-failed]").first().evaluate((cell) => getComputedStyle(cell).backgroundColor)).toBe("rgb(231, 237, 243)");
});

test("a photo that fails says so in its frame, on the tab and on paper, in a 4:3 frame", async ({ page }) => {
  await open(page, {
    extra: {
      "/api/projects/P156634/field-photos": { body: await recorded("field-photos-p156634.json") },
      "/api/projects/P156634/field-photos/fph-000000000001": { status: 503, body: '{"code":"photo_store"}' },
    },
  });
  await expect(page.locator('[data-field-photo="fph-000000000001"]')).toContainText(copy.research.photos.notLoaded);
  await page.emulateMedia({ media: "print" });
  const figure = print(page).locator('[data-print-photo="fph-000000000001"]');
  await expect(figure.locator("[data-photo-frame=failed]")).toHaveText(copy.research.photos.notLoaded);
  await expect(figure).toContainText("The new intake pipe");
  const box = await figure.locator("[data-photo-frame]").boundingBox();
  expect(Math.abs(box!.width / box!.height - 4 / 3)).toBeLessThan(0.02);
});

test("Download as PDF waits for every image with a visible count, then prints", async ({ page }) => {
  const held: Route[] = [];
  await open(page, { tiles: (route) => void held.push(route) });
  await countPrints(page);
  await tab(page).getByRole("button", { name: words.print }).click();
  const button = tab(page).locator("[data-research-pdf]");
  await expect(button).toHaveText(words.pdf.preparing);
  const total = await print(page).locator("img").count();
  expect(total).toBeGreaterThan(18);
  await expect(tab(page).locator("[data-research-pdf-count]")).toHaveText(new RegExp(`^\\d+ of ${total} images loaded$`));
  expect(await printed(page)).toBe(0);
  for (const route of held.splice(0)) await route.fulfill({ status: 200, contentType: "image/gif", body: PIXEL });
  await expect.poll(() => printed(page)).toBe(1);
  await expect(button).toHaveText(words.print);
  await expect(tab(page).locator("[data-research-pdf-count]")).toHaveText("");
});

test("every image in the print view carries its width and height, and every figure keeps together on its page", async ({ page }) => {
  await open(page, { extra: { "/api/projects/P156634/field-photos": { body: await recorded("field-photos-p156634.json") } } });
  await page.emulateMedia({ media: "print" });
  await expect(print(page).locator("[data-print-photo]")).toHaveCount(1);
  const sizes = await print(page).locator("img").evaluateAll((all) => all.map((img) => [img.getAttribute("width"), img.getAttribute("height")]));
  expect(sizes.length).toBeGreaterThan(18);
  for (const [width, height] of sizes) {
    expect(Number(width)).toBeGreaterThan(0);
    expect(Number(height)).toBeGreaterThan(0);
  }
  const breaks = await print(page).locator(".figure, .photo").evaluateAll((all) => all.map((figure) => getComputedStyle(figure).breakInside));
  expect(new Set(breaks)).toEqual(new Set(["avoid"]));
});

test("P161305's print puts a site's photos on a sheet of their own after the site's satellite pair", async ({ page }) => {
  const project = JSON.parse(await recorded("project-p156634.json"));
  // P161305's header: the fixture's P156634 header with P161305's subject, as the brief names it.
  const subject = JSON.parse(await recorded("research-p161305.json")).subject;
  project.project = { ...project.project, project_id: "P161305", project_name: subject.project_name, display_name: subject.project_name, implementing_agencies: [] };
  project.agencies = [];
  const photos = JSON.parse(await recorded("field-photos-p161305.json"));
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.route("https://tiles.maps.eox.at/**", (route) => route.fulfill({ status: 200, contentType: "image/gif", body: PIXEL }));
  await mockApi(page, {
    ...(await viewAnswers()),
    "/api/me": { body: await recorded("me.json") },
    "/api/freshness": { body: await recorded("freshness.json") },
    "/api/projects/P161305": { body: JSON.stringify(project) },
    "/api/projects/P161305/research": { body: await recorded("research-p161305.json") },
    "/api/projects/P161305/field-photos": { body: JSON.stringify(photos) },
  });
  await page.route(TILES, pixel);
  for (const [index, photo] of (photos.photos as { url: string }[]).entries()) {
    const body = await JPEG(`P161305-${index + 1}.jpg`);
    await page.route(`**${photo.url}`, (route) => route.fulfill({ status: 200, contentType: "image/jpeg", body }));
  }
  await page.goto("/projects/P161305/research");
  await expect(tab(page)).toHaveAttribute("data-research", "ready");
  await page.emulateMedia({ media: "print" });
  const near = fill(words.photosNear, { site: "Wajir" });
  const wajir = print(page).locator(".research-sheet", { has: page.locator(`[data-print-photo="${photos.photos[0].photo_id}"]`) });
  await expect(wajir).toHaveCount(1);
  await expect(wajir.locator("h2")).toHaveText(near);
  await expect(wajir.locator("[data-sheet-label]")).toHaveText(near);
  await expect(wajir.locator("h1.section")).toHaveText(words.section.bySiteMore);
  // No sheet holds both a satellite pair and a photo, and every photo frame shows its picture.
  const mixed = await print(page).locator(".research-sheet").evaluateAll((all) => all.filter((sheet) => sheet.querySelector("[data-print-satellite]") && sheet.querySelector("[data-print-photo]")).length);
  expect(mixed).toBe(0);
  await expect(print(page).locator("[data-photo-frame=shown] img")).toHaveCount(photos.photos.length);
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
