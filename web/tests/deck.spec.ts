// The deck at /present, second draft (ticket 47; .notes/deck2/brief.md): five topics between the bookends, outside the
// app's frame. Every slide carries the World Bank logo where DESIGN.md section 9 puts it and the section 8 footer; a
// press brings in one point or figure step at a time; the speaker notes window follows the deck press by press; axe
// finds no WCAG 2.2 AA violation; and the number check (src/strata/proposal/numbers.py) passes over every slide, its
// notes and the reading view. The deck reads tests/fixtures/api/deck-data.json, built from the fixture database and the
// made-up month (tests/record_deck_api.py), where the built app reads /deck/data.json.
import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { closeSync, mkdtempSync, openSync, readFileSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import type { Locator, Page } from "@playwright/test";
import { copyChecker } from "../lint/copy";
import { deckCopy, figureCopy } from "../src/deck/copy";
import type { DeckData } from "../src/deck/data";
import { TOPIC_ORDER } from "../src/deck/talk";
import { formatDate } from "../src/lib/format";
import { scan } from "./axe";
import { footerSentence } from "./design-md";
import { expect, recorded, test } from "./mocked";

const REPO = fileURLToPath(new URL("../../", import.meta.url));
// web/src/assets/world-bank-logo.md: each file's hash when it was downloaded, the light one from data.worldbank.org and
// the white one from worldbank.org's footer.
const LIGHT_LOGO_SHA256 = "15a18185cbdc72239c7b052225e47d533c3128adc6df99e699ba3018ae3b6c9a";
const WHITE_LOGO_SHA256 = "c11d30bf69ad0f6f224b350e93ea976bbac438ff18c82786d1c11454a0317aff";
// The brief's talk, by each slide's id: the bookends, then the five topics, each opened by its navy opener.
const OPENERS = ["work", "built", "answers", "grows"];

async function serveDeck(page: Page, file = "deck-data.json", status = 200) {
  const body = await recorded(file);
  await page.route("**/deck/data.json", (route) => route.fulfill({ status, contentType: "application/json", body }));
}

const serveData = (page: Page, data: DeckData) =>
  page.route("**/deck/data.json", (route) => route.fulfill({ contentType: "application/json", body: JSON.stringify(data) }));

async function present(page: Page, n = 1, size = { width: 1440, height: 900 }) {
  await serveDeck(page);
  await page.setViewportSize(size);
  await page.goto(`/present/${n}`);
  await expect(page.locator("[data-deck=present]")).toBeVisible();
}

const slideById = (page: Page, id: string) => page.locator(`section[data-slide-id='${id}']`);

// Opens the deck at a slide and waits until it shows, so a key pressed next reaches the deck.
async function openAt(page: Page, n: number) {
  await page.goto(`/present/${n}`);
  await expect(page.locator(`section[data-slide='${n}']`)).toBeVisible();
}
const numberOf = async (page: Page, id: string) => Number(await slideById(page, id).getAttribute("data-slide"));
const total = (page: Page) => page.locator("section[aria-roledescription=slide]").count();

// The number check over named pieces of HTML: what it found, as the check's own sentence parts. The pieces go in as a
// file, not a pipe, and the run has a time limit, so a slow Python start never holds the worker (the 47 verify notes,
// finding 1).
function numberCheck(pieces: Record<string, string>): { where: string; number: string; excerpt: string }[] {
  const dir = mkdtempSync(join(tmpdir(), "deck-numbers-"));
  const file = join(dir, "pieces.json");
  writeFileSync(file, JSON.stringify(pieces));
  const input = openSync(file, "r");
  try {
    const done = spawnSync("python3", ["-m", "strata.proposal.numbers"], {
      cwd: REPO,
      env: { ...process.env, PYTHONPATH: `${REPO}src` },
      stdio: [input, "pipe", "pipe"],
      encoding: "utf8",
      timeout: 30_000,
    });
    if (done.error) throw done.error;
    if (done.status !== 0 && done.status !== 1) throw new Error(done.stderr);
    return JSON.parse(done.stdout);
  } finally {
    closeSync(input);
    rmSync(dir, { recursive: true, force: true });
  }
}

// The figure parts a slide shows now: those its step has reached.
const shownParts = (slide: Locator) => slide.locator("[data-motion-item]:not([data-unreached])");

test("/present serves the talk outside the app's frame: the bookends, five topics, an opener for each topic after the first, and a slide number out of range goes to the last slide", async ({ page }) => {
  await present(page, 999);
  const count = await total(page);
  await expect(page.locator("section[data-slide]:not([hidden])")).toHaveCount(1);
  await expect(page.locator(`section[data-slide='${count}']`)).toBeVisible();
  expect(new URL(page.url()).pathname).toBe(`/present/${count}`);
  await expect(page).toHaveTitle(`Slide ${count} of ${count} | Strata deck`);
  const ids = await page.locator("section[data-slide]").evaluateAll((sections) => sections.map((section) => section.getAttribute("data-slide-id")));
  expect(ids[0]).toBe("welcome");
  expect(ids[1]).toBe("agenda");
  expect(ids.at(-1)).toBe("thanks");
  for (const opener of OPENERS) expect(ids, opener).toContain(opener);
  // The openers come in the topics' order.
  expect(OPENERS.map((opener) => ids.indexOf(opener))).toEqual([...OPENERS.map((opener) => ids.indexOf(opener))].sort((a, b) => a - b));
  // Each navy slide draws its own hairline figure, which loads with the deck, never the core sample in its place.
  const drawn = await page.locator("section[data-slide] [data-deck-hairline]").evaluateAll((boxes) => boxes.map((box) => box.getAttribute("data-deck-hairline")));
  expect(drawn).toEqual(["core-sample", "plan-rows", "passages", "filter", "sediment", "sediment"]);
  // No navy bar, no box: the deck is not an app page.
  await expect(page.locator("[data-nav-bar], [data-box-band]")).toHaveCount(0);
});

test("every slide carries one World Bank logo, unaltered, at 24 px or more with clear space, the light file on light slides and the white one on navy slides, and the footer sentence word for word", async ({ page }) => {
  test.setTimeout(90_000);
  await present(page, 1);
  const footer = await footerSentence();
  const count = await total(page);
  for (let n = 1; n <= count; n += 1) {
    if (n > 1) await page.goto(`/present/${n}`);
    const slide = page.locator(`section[data-slide='${n}']`);
    await expect(slide).toBeVisible();
    const logos = slide.getByRole("img", { name: deckCopy.logo });
    await expect(logos, `slide ${n}`).toHaveCount(1);
    const navy = (await slide.getAttribute("class"))!.includes("bg-navy");
    await expect(logos).toHaveAttribute("data-deck-logo", navy ? "white" : "light");
    const box = (await logos.boundingBox())!;
    const header = (await slide.locator("[data-frame=header]").boundingBox())!;
    const stage = (await page.locator("[data-stage]").boundingBox())!;
    expect(box.height, `slide ${n}`).toBeGreaterThanOrEqual(24);
    // Clear space of half its height above it, below it and from the slide's edge.
    expect(box.y - header.y).toBeGreaterThanOrEqual(box.height / 2 - 0.5);
    expect(header.y + header.height - (box.y + box.height)).toBeGreaterThanOrEqual(box.height / 2 - 0.5);
    expect(box.x - stage.x).toBeGreaterThanOrEqual(box.height / 2 - 0.5);
    await expect(slide.locator("[data-slide-footer]"), `slide ${n}`).toHaveText(footer);
  }
  for (const [n, sha] of [
    [1, WHITE_LOGO_SHA256],
    [2, LIGHT_LOGO_SHA256],
  ] as const) {
    await page.goto(`/present/${n}`);
    const logo = page.locator(`section[data-slide='${n}']`).getByRole("img", { name: deckCopy.logo });
    // src, not currentSrc: currentSrc stays empty until the browser picks the source, and an empty address fetches the
    // page itself. The logo has no srcset, so src is the file.
    const file = await page.request.get(await logo.evaluate((img) => (img as HTMLImageElement).src));
    expect(createHash("sha256").update(await file.body()).digest("hex")).toBe(sha);
  }
  // No drawing holds a logo: the frame draws the one logo.
  await expect(page.locator("svg image, svg img")).toHaveCount(0);
});

test("a press brings in one figure step or one point at a time, a press after the last moves on, a press back steps back, and going back onto a slide shows it whole", async ({ page }) => {
  await present(page, 1);
  const layers = await numberOf(page, "layers");
  await openAt(page, layers - 1);
  await page.keyboard.press("ArrowRight");
  const slide = slideById(page, "layers");
  const steps = Number(await slide.getAttribute("data-step-count"));
  expect(steps).toBe(figureCopy.layers.steps.length);
  // Arriving forward, the figure shows its structure and none of its parts.
  await expect(slide).toBeVisible();
  await expect(slide).toHaveAttribute("data-step-current", "0");
  await expect(shownParts(slide)).toHaveCount(0);
  await expect(page.locator("[data-deck-status]")).toHaveText(new RegExp(`^Slide ${layers} of \\d+: `));
  for (let step = 1; step <= steps; step += 1) {
    await page.keyboard.press("ArrowRight");
    await expect(slide).toHaveAttribute("data-step-current", String(step));
    // Every part shown is at this step or before it, and this step's parts are shown.
    const reached = await shownParts(slide).evaluateAll((parts) => parts.map((part) => Number(part.getAttribute("data-step"))));
    expect(Math.max(...reached)).toBe(step);
    await expect(page.locator("[data-deck-status]")).toHaveText(figureCopy.layers.steps[step - 1]);
  }
  expect(new URL(page.url()).pathname).toBe(`/present/${layers}`);
  // A press after the last step moves on to the next slide, at its start.
  await page.keyboard.press("ArrowRight");
  const next = page.locator(`section[data-slide='${layers + 1}']`);
  await expect(next).toBeVisible();
  await expect(next).toHaveAttribute("data-step-current", "0");
  expect(new URL(page.url()).pathname).toBe(`/present/${layers + 1}`);
  // Back onto the slide shows it whole, and back again takes one step away.
  await page.keyboard.press("ArrowLeft");
  await expect(slide).toHaveAttribute("data-step-current", String(steps));
  await page.keyboard.press("PageUp");
  await expect(slide).toHaveAttribute("data-step-current", String(steps - 1));

  // A text slide: the title on arrival, then a point a press; the newest leads and the ones before it recede.
  const cost = await numberOf(page, "cost");
  await openAt(page, cost - 1);
  await page.keyboard.press("PageDown");
  const points = slideById(page, "cost").locator("[data-step]");
  await expect(points.first()).toHaveAttribute("aria-hidden", "true");
  await page.keyboard.press("ArrowRight");
  await expect(points.nth(0)).toHaveAttribute("data-current", "");
  await expect(points.nth(1)).toHaveAttribute("aria-hidden", "true");
  await page.keyboard.press("ArrowRight");
  await expect(points.nth(0)).toHaveAttribute("data-receded", "");
  await expect(points.nth(1)).toHaveAttribute("data-current", "");
  await expect(page.locator("[data-deck-status]")).toHaveText(deckCopy.slides.cost.lines[1]);

  // Home and End, and no single-letter shortcut.
  await page.keyboard.press("Home");
  await expect(page.locator("section[data-slide='1']")).toBeVisible();
  await page.keyboard.press("End");
  const count = await total(page);
  await expect(page.locator(`section[data-slide='${count}']`)).toBeVisible();
  await page.keyboard.press("n");
  await expect(page.locator(`section[data-slide='${count}']`)).toBeVisible();
});

test("the live region reads each press's own words: the slide's point after its figure's steps, never a figure part, with each block ended as a sentence", async ({ page }) => {
  await present(page, 1);
  const status = page.locator("[data-deck-status]");
  // The reading slide: its figure's steps, then the slide's own sentence about the passages it counted.
  const reading = await numberOf(page, "reading");
  await openAt(page, reading - 1);
  await page.keyboard.press("ArrowRight");
  const slide = slideById(page, "reading");
  const steps = Number(await slide.getAttribute("data-step-count"));
  for (let step = 1; step <= steps; step += 1) await page.keyboard.press("ArrowRight");
  await expect(slide).toHaveAttribute("data-step-current", String(steps));
  for (const words of deckCopy.slides.reading.passages.split(/\{\w+\}/).map((part) => part.trim()).filter(Boolean)) {
    await expect(status).toContainText(words);
  }
  await expect(status).toContainText(deckCopy.slides.reading.pages.split("{ratio}")[1].trim());
  // The agenda: a topic's name and its line are two sentences, not one run of words, and its number is not read.
  // A slide opened by its address shows whole, so the walk starts on the slide before it.
  await openAt(page, (await numberOf(page, "agenda")) - 1);
  await page.keyboard.press("ArrowRight");
  await page.keyboard.press("ArrowRight");
  await expect(status).toHaveText(`${deckCopy.topics.strata.name}. ${deckCopy.topics.strata.line}`);
});

test("the tracker lights the slide's topic, with a segment per slide of each topic, and the title, the agenda and the close show none", async ({ page }) => {
  await present(page, 1);
  const parts = await page.locator("section[data-slide]").evaluateAll((sections) =>
    sections.map((section) => section.querySelector("[data-topic-name][aria-current]")?.closest("[data-topic]")?.getAttribute("data-topic") ?? null),
  );
  for (const id of ["welcome", "agenda", "thanks"]) await expect(slideById(page, id).locator("[data-tracker]"), id).toHaveCount(0);
  const reading = await numberOf(page, "reading");
  await page.goto(`/present/${reading}`);
  const slide = slideById(page, "reading");
  await expect(slide.locator("[data-topic=built] [data-topic-name]")).toHaveAttribute("aria-current", "step");
  // Each topic has as many segments as it has slides, and this slide's own is the current one.
  for (const topic of TOPIC_ORDER) {
    const slides = parts.filter((part) => part === topic).length;
    await expect(slide.locator(`[data-topic=${topic}] [data-segment]`), topic).toHaveCount(slides);
  }
  const built = slide.locator("[data-topic=built] [data-segment]");
  const index = parts.slice(0, reading - 1).filter((part) => part === "built").length;
  await expect(built.nth(index)).toHaveAttribute("data-segment", "current");
  await expect(slide.locator("[data-topic=strata] [data-segment]").first()).toHaveAttribute("data-segment", "passed");
  await expect(slide.locator("[data-topic=grows] [data-segment]").first()).toHaveAttribute("data-segment", "later");
  // An opener names its topic and numbers it in the deck's chrome.
  const opener = slideById(page, "built");
  await page.goto(`/present/${await numberOf(page, "built")}`);
  await expect(opener.getByRole("heading", { level: 1 })).toHaveText(deckCopy.topics.built.name);
  await expect(opener.locator("[data-topic-number]")).toHaveText(String(TOPIC_ORDER.indexOf("built") + 1));
});

test("axe finds no WCAG 2.2 AA violation on any slide", async ({ page }) => {
  test.setTimeout(120_000);
  await present(page, 1);
  const count = await total(page);
  for (let n = 1; n <= count; n += 1) {
    if (n > 1) await page.goto(`/present/${n}`);
    await expect(page.locator(`section[data-slide='${n}']`)).toBeVisible();
    expect((await scan(page)).violations.map((found) => `slide ${n}: ${found.id}`)).toEqual([]);
  }
});

test("the speaker notes open in their own window, follow the deck press by press with the figure step's words, and a press there moves the deck", async ({ page, context }) => {
  await present(page, 1);
  const layers = await numberOf(page, "layers");
  await openAt(page, layers);
  const notesLink = page.getByRole("link", { name: deckCopy.bar.notesName });
  await context.route("**/deck/data.json", async (route) => route.fulfill({ contentType: "application/json", body: await recorded("deck-data.json") }));
  const [notes] = await Promise.all([context.waitForEvent("page"), notesLink.click()]);
  await expect(notes.locator("[data-deck=notes]")).toBeVisible();
  await expect(notes.locator(`[data-notes-view='${layers}']`)).toBeVisible();
  await page.bringToFront();
  await page.keyboard.press("ArrowRight");
  await expect(notes.locator(`[data-notes-view='${layers + 1}']`)).toBeVisible();
  await page.keyboard.press("ArrowRight");
  await expect(notes.locator("[data-notes-press]")).toHaveText(deckCopy.pressOf("1", String(figureCopy.pipeline.steps.length)));
  await expect(notes.locator("[data-notes-step]")).toHaveText(figureCopy.pipeline.steps[0]);
  expect((await scan(notes)).violations.map((found) => found.id)).toEqual([]);
  // The notes' forward press moves the deck, and its outline jumps to a slide.
  await notes.getByRole("button", { name: deckCopy.notesView.nextButton }).click();
  await expect(slideById(page, "pipeline")).toHaveAttribute("data-step-current", "2");
  await notes.locator("[data-notes-outline] button").first().click();
  await expect(page.locator("section[data-slide='1']")).toBeVisible();
});

// Every slide whole, its reading view and its notes, as /present/page and presentation mode draw them.
async function allPieces(page: Page): Promise<Record<string, string>> {
  await page.goto("/present/page");
  // count() does not wait, and the loading frame shows until the deck's data arrive, so wait for the reading view first.
  await expect(page.locator("[data-reading-slide]").first()).toBeVisible();
  const count = await page.locator("[data-reading-slide]").count();
  expect(count).toBeGreaterThan(20);
  const pieces: Record<string, string> = {};
  for (let n = 1; n <= count; n += 1) {
    const section = page.locator(`[data-reading-slide='${n}']`);
    pieces[`Slide ${n}, reading view`] = await section.evaluate((element) => {
      const copy = element.cloneNode(true) as HTMLElement;
      copy.querySelectorAll("[data-notes]").forEach((notes) => notes.remove());
      return copy.outerHTML;
    });
    pieces[`Slide ${n}, notes`] = await section.locator("[data-notes]").evaluate((element) => element.outerHTML);
  }
  await page.goto("/present/1");
  for (let n = 1; n <= count; n += 1) {
    pieces[`Slide ${n}`] = await page.locator(`section[data-slide='${n}']`).evaluate((element) => element.outerHTML);
  }
  return pieces;
}

// Every key a number is bound to in these pieces of HTML. A chart that draws two answers names both, with a space.
const sourceKeys = (pieces: Record<string, string>) => [
  ...new Set(Object.values(pieces).flatMap((html) => [...html.matchAll(/data-source-key="([^"]*)"/g)].flatMap((found) => found[1].split(/\s+/)))),
];

// The keys the deck's data does not hold: a result the snapshot does not carry, a setting, a dimension of the rubric
// or a tool that is not one of the demo package's two recorded answers.
function unknownKeys(keys: string[], data: DeckData): string[] {
  const dimensions = new Set(data.rubric.dimensions.map((dimension) => dimension.key));
  const known = (key: string) => {
    const [kind, name] = [key.slice(0, key.indexOf(":")), key.slice(key.indexOf(":") + 1)];
    if (kind === "r") return name in data.results;
    if (kind === "s") return name in data.settings;
    if (kind === "rubric") return dimensions.has(name);
    return key === "tool:find_comparables" || key === "tool:estimate_time";
  };
  return keys.filter((key) => !known(key));
}

test("the number check passes on every slide whole, its reading view and its speaker notes, every key it reads is in the deck's data, and it fails a number planted in one", async ({ page }) => {
  test.setTimeout(90_000);
  await serveDeck(page);
  await page.setViewportSize({ width: 1440, height: 900 });
  const pieces = await allPieces(page);
  expect(numberCheck(pieces)).toEqual([]);
  const keys = sourceKeys(pieces);
  const data = JSON.parse(await recorded("deck-data.json")) as DeckData;
  expect(keys).toEqual(expect.arrayContaining(["r:benchmark-passed", "s:check-count", "s:fewest-comparables", "rubric:architecture"]));
  expect(unknownKeys(keys, data)).toEqual([]);
  expect(unknownKeys(["r:not-a-result", "s:check-count", "tool:find_everything"], data)).toEqual(["r:not-a-result", "tool:find_everything"]);
  const planted = { ...pieces, "Slide 4": pieces["Slide 4"].replace("</h1>", " across 12 countries</h1>") };
  expect(numberCheck(planted).map((found) => [found.where, found.number])).toEqual([["Slide 4", "12"]]);
});

test("the deck the App serves says on each slide what is not measured yet, and passes the number check", async ({ page }) => {
  // web/public/deck/data.json, built from the committed snapshot: until the workspace pull, no result is measured and
  // the demo package's answers are not recorded. Each slide that reads one says so in its own words.
  const committed = readFileSync(new URL("../public/deck/data.json", import.meta.url), "utf8");
  const data = JSON.parse(committed) as DeckData;
  await serveData(page, data);
  await page.setViewportSize({ width: 1440, height: 900 });
  const pieces = await allPieces(page);
  const s = deckCopy.slides;
  const text = (id: string) => page.locator(`section[data-slide-id='${id}']`);
  const unmeasured: [boolean, string, string][] = [
    // With the pages not measured either, one sentence says both.
    [!data.results.passages.measured, "reading", data.results["pages-read-well"].measured ? s.reading.passagesNone : s.reading.bothNone],
    [!data.results["award-rows-by-year"].measured, "gap", s.gap.noneLine],
    [!data.results["benchmark-passed"].measured || !data.results["must-refuse"].measured, "checks", s.checks.none.split("{checks}")[0]],
    [!data.results["hindsight-caught"].measured, "hindsight", s.hindsight.titleNone],
    [!data.results["azure-spend"].measured, "spend", s.spend.noSpend],
  ];
  for (const [, id, sentence] of unmeasured.filter(([missing]) => missing)) await expect(text(id), id).toContainText(sentence);
  // A test that has not run is described as planned, never in the past tense as if it had run.
  if (!data.results["hindsight-caught"].measured) {
    await expect(text("hindsight")).not.toContainText(s.hindsight.method.split("{coders}")[0]);
    await expect(text("hindsight")).toContainText(s.hindsight.methodPlanned.split("{coders}")[0]);
  }
  expect(numberCheck(pieces)).toEqual([]);
  expect(unknownKeys(sourceKeys(pieces), data)).toEqual([]);
});

test("the award gap chart sits whole inside its card, clear of the points beside it, and its key names only the years it draws", async ({ page }) => {
  await present(page, 1);
  const gap = await numberOf(page, "gap");
  await page.goto(`/present/${gap}`);
  const slide = slideById(page, "gap");
  const card = (await slide.locator("figure[data-chart]").boundingBox())!;
  const chart = (await slide.locator("[data-award-chart]").boundingBox())!;
  expect(chart.x).toBeGreaterThanOrEqual(card.x);
  expect(chart.x + chart.width).toBeLessThanOrEqual(card.x + card.width);
  expect(chart.y + chart.height).toBeLessThanOrEqual(card.y + card.height);
  // The points and the link beside the chart start right of the card.
  for (const box of await slide.locator("[data-step], a").evaluateAll((items) => items.map((item) => item.getBoundingClientRect().left))) {
    expect(box).toBeGreaterThanOrEqual(card.x + card.width);
  }
  // The key's names hold no fiscal years the chart does not draw.
  const data = JSON.parse(await recorded("deck-data.json")) as DeckData;
  const drawn = (data.results["award-rows-by-year"].series ?? []).map((row) => Number(row.fiscal_year));
  const named = [...(await slide.locator("[data-chart-key]").innerText()).matchAll(/FY(\d{2,4})/g)].map((found) => Number(found[1]));
  for (const year of named) expect(drawn.some((one) => one % 100 === year % 100), `FY${year}`).toBe(true);
});

test("the demo slides open Strata's own screens from the examples registry in a new tab, and the answer demo copies its question", async ({ page, context }) => {
  await context.grantPermissions(["clipboard-read", "clipboard-write"]);
  const data = JSON.parse(await recorded("deck-data.json")) as DeckData;
  await present(page, 1);
  const links = { "demo-plan": data.demo.links!.checkPlan!, "demo-package": data.demo.links!.planPackage!, "demo-answer": `/projects/${data.showcase.project_id}` };
  for (const [id, href] of Object.entries(links)) {
    await page.goto(`/present/${await numberOf(page, id)}`);
    const link = slideById(page, id).locator("[data-demo-link]");
    await expect(link, id).toHaveAttribute("href", href);
    await expect(link).toHaveAttribute("target", "_blank");
  }
  // No link on any slide replaces the deck mid-talk: each opens a new tab and says so.
  const slideLinks = await page.locator("section[data-slide] a").evaluateAll((anchors) =>
    anchors.map((anchor) => ({ href: anchor.getAttribute("href"), target: anchor.getAttribute("target"), text: anchor.textContent ?? "" })),
  );
  expect(slideLinks.length).toBeGreaterThan(5);
  for (const link of slideLinks) {
    expect(link.target, link.href ?? "").toBe("_blank");
    expect(link.text, link.href ?? "").toContain(deckCopy.demo.opens);
  }
  await expect(slideById(page, "demo-package").locator("[data-demo-box]")).toContainText(data.demo.sentence!);
  const answer = slideById(page, "demo-answer");
  await answer.locator("[data-copy-question]").click();
  await expect(answer.locator("[data-copy-question]")).toHaveText(deckCopy.demo.copied);
  expect(await page.evaluate(() => navigator.clipboard.readText())).toBe(data.demo.question);
});

test("the package demo's recorded answer: no button without a recording; with one, a press draws the app's range chart from it with its date, coverage line and source line, passes the number check and axe, and the next press moves on", async ({ page }) => {
  const data = JSON.parse(await recorded("deck-data.json")) as DeckData;
  const comparables = data.demo.comparables!;
  await page.setViewportSize({ width: 1440, height: 900 });
  // Without the recorded answers the slide is as it was.
  await serveData(page, { ...data, demo: { ...data.demo, comparables: null, estimate: null } });
  await page.goto("/present/1");
  await expect(page.locator("[data-deck=present]")).toBeVisible();
  const n = await numberOf(page, "demo-package");
  await openAt(page, n);
  const slide = slideById(page, "demo-package");
  await expect(slide.locator("[data-demo-box]")).toBeVisible();
  await expect(slide.locator("[data-recorded-toggle]")).toHaveCount(0);
  // With them, the slide is reached by a press, from the slide before it.
  await page.unroute("**/deck/data.json");
  await serveDeck(page);
  await openAt(page, n - 1);
  await page.keyboard.press("ArrowRight");
  await expect(slide).toHaveAttribute("data-step-current", "0");
  const toggle = slide.locator("[data-recorded-toggle]");
  await expect(toggle).toHaveText(deckCopy.demo.showRecorded);
  await toggle.click();
  // The answer takes the box's and the points' place, with the slide's last press in, and focus on the button that
  // hides it.
  const answer = slide.locator("[data-recorded-answer]");
  await expect(answer.locator("svg[data-chart-drawing]")).toBeVisible();
  await expect(slide.locator("[data-demo-box]")).toHaveCount(0);
  await expect(slide).toHaveAttribute("data-step-current", String(deckCopy.slides.demoPackage.lines.length));
  await expect(toggle).toBeFocused();
  await expect(toggle).toHaveText(deckCopy.demo.hideRecorded);
  // Every number is the recording's: the plan line's readout, the coverage line's counts and the dates.
  const plan = comparables.plan!;
  await expect(answer.locator("svg[data-chart-drawing]")).toContainText(`${plan.within} of ${comparables.rows.length}`);
  await expect(answer.locator("[data-recorded-on]")).toContainText(formatDate(comparables.as_of));
  await expect(answer.locator("[data-recorded-on]")).toContainText(data.demo.step_reference);
  await expect(answer.locator("[data-coverage-line]")).toContainText(`${comparables.coverage.used} of ${comparables.coverage.matched}`);
  await expect(answer.locator("[data-source]")).toContainText(formatDate(comparables.records_through!));
  expect(numberCheck({ "The recorded answer": await slide.evaluate((element) => element.outerHTML) })).toEqual([]);
  expect((await scan(page)).violations.map((found) => found.id)).toEqual([]);
  // A press back closes it and shows the points from that press; opened again, the next press moves on, and coming
  // back shows the slide whole, with its box.
  await page.keyboard.press("ArrowLeft");
  await expect(slide.locator("[data-demo-box]")).toBeVisible();
  await expect(slide).toHaveAttribute("data-step-current", String(deckCopy.slides.demoPackage.lines.length - 1));
  await expect(toggle).toBeFocused();
  await toggle.click();
  await expect(answer).toBeVisible();
  await page.keyboard.press("ArrowRight");
  await expect(page).toHaveURL(new RegExp(`/present/${n + 1}$`));
  await page.keyboard.press("ArrowLeft");
  await expect(slide.locator("[data-demo-box]")).toBeVisible();
  await expect(answer).toHaveCount(0);
  // In the reading view the same button opens it under the points.
  await page.goto("/present/page");
  const reading = page.locator(`[data-reading-slide='${n}']`);
  await reading.locator("[data-recorded-toggle]").click();
  await expect(reading.locator("[data-recorded-toggle]")).toHaveAttribute("aria-expanded", "true");
  await expect(reading.locator("[data-recorded-answer] svg[data-chart-drawing]")).toBeVisible();
  expect(numberCheck({ "The recorded answer, reading view": await reading.evaluate((element) => element.outerHTML) })).toEqual([]);
});

test("below the size of the canvas the deck is a page that reflows, with every slide whole, its figure text and its notes, and the footer once", async ({ page }) => {
  await serveDeck(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/present/4");
  await expect(page.locator("[data-deck=read]")).toBeVisible();
  await expect(page.getByRole("contentinfo")).toHaveText(await footerSentence());
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(deckCopy.slides.welcome.statement);
  // Nothing waits for a press here: no item is hidden or receded.
  await expect(page.locator("[data-reading-slide] [data-step][aria-hidden=true]")).toHaveCount(0);
  await expect(page.locator("[data-reading-slide] [data-receded]")).toHaveCount(0);
  // A drawing wider than the column scrolls in its own region, and its text version is open.
  const slide = page.locator("[data-reading-slide]").filter({ has: page.locator("[data-figure=layers]") });
  await expect(slide.getByRole("region", { name: deckCopy.reading.scrolls(figureCopy.layers.title) })).toBeVisible();
  await expect(slide.locator("[data-figure-text=layers]")).toBeVisible();
  // A drawing cut at the column's edge says that it scrolls, and so does the award chart.
  await expect(slide.getByText(deckCopy.reading.scrollHint)).toBeVisible();
  const gap = page.locator("[data-reading-slide]").filter({ has: page.locator("[data-award-chart]") });
  await expect(gap.getByText(deckCopy.reading.scrollHint)).toBeVisible();
  // The close keeps what the navy close shows: the question to the room and the way into Strata.
  const close = page.locator("[data-reading-slide]").last();
  await expect(close).toContainText(deckCopy.slides.thanks.ask);
  await expect(close.getByRole("link", { name: deckCopy.slides.thanks.links.app })).toHaveAttribute("href", "/");
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  expect((await scan(page)).violations.map((found) => found.id)).toEqual([]);
});

// The literal values a test may assert, by id, each with its source document and page (tests/ground_truth/values.toml).
type Fact = { value: string; paragraph?: number; pdf_page?: number; date: string };
function groundTruth(): Record<string, Fact> {
  const read = spawnSync(
    "python3",
    [
      "-c",
      "import json, sys, tomllib; v = tomllib.load(open(sys.argv[1], 'rb'))['value']; print(json.dumps({x['id']: x for x in v}, default=str))",
      `${REPO}tests/ground_truth/values.toml`,
    ],
    { encoding: "utf8", timeout: 30_000 },
  );
  return JSON.parse(read.stdout) as Record<string, Fact>;
}

test("the ladder slide's showcase is the ground truth's: ISR 7's date and rating, and the ICR's date, paragraph and PDF page", async ({ page }) => {
  const facts = groundTruth();
  await present(page, 1);
  await page.goto(`/present/${await numberOf(page, "ladder")}`);
  const slide = slideById(page, "ladder");
  const text = (await slide.innerText()).replace(/\s+/g, " ");
  expect(text).toContain(`Report 7, P130164, ${formatDate(facts["isr-7-date"].value)};`);
  expect(text).toContain(`rated progress toward the objective ${facts["isr-7-rating"].value} in August 2016`);
  expect(text).toContain(`Report, P130164, ${formatDate(facts["icr-date"].value)}, paragraph ${facts["icr-para-78"].paragraph}, page ${facts["icr-para-78"].pdf_page}.`);
});

// The recorded answer to the answer demo's question (the smoke question), as the agent streamed it: its sentences, the
// evidence they cite and the verifier's counts.
async function recordedAnswer() {
  const events = (await recorded("ask-p130164-rebidding.sse"))
    .split("\n\n")
    .map((block) => ({ event: /^event: (.*)$/m.exec(block)?.[1], data: /^data: (.*)$/m.exec(block)?.[1] }))
    .filter((found) => found.event && found.data)
    .map((found) => ({ event: found.event!, data: JSON.parse(found.data!) }));
  const of = (name: string) => events.filter((found) => found.event === name).map((found) => found.data);
  type Source = { document_type: string; paragraph: string; pdf_page: number; document_date: string };
  return {
    evidence: of("evidence").map((found) => found.row.source as Source),
    checks: of("checks")[0] as { sentences: { removed: number }; quotes: { total: number; found: number } },
  };
}

test("the answer demo claims only what the recorded answer shows: the paragraph it cites, on its page, and quotes the verifier found; its source line is the ground truth's", async ({ page }) => {
  const facts = groundTruth();
  const answer = await recordedAnswer();
  await present(page, 1);
  await page.goto(`/present/${await numberOf(page, "demo-answer")}`);
  const slide = slideById(page, "demo-answer");
  const text = (await slide.innerText()).replace(/\s+/g, " ");
  // The source line: the completion report's date, and paragraph 54 on its PDF page, as values.toml records them.
  const para = facts["icr-para-54"];
  expect(text).toContain(`Report, P130164, ${formatDate(facts["icr-date"].value)}, paragraph ${para.paragraph}, page ${para.pdf_page}.`);
  // The paragraph the slide says one click opens is the one the recorded answer cites first, on the same page.
  expect(answer.evidence[0]).toMatchObject({ paragraph: String(para.paragraph), pdf_page: para.pdf_page });
  expect(text).toContain(`paragraph ${answer.evidence[0].paragraph}, on page ${answer.evidence[0].pdf_page}`);
  // The verifier found every quote on its page and removed no sentence, which the slide's last line says.
  expect(answer.checks.quotes.total).toBeGreaterThan(0);
  expect(answer.checks.quotes.found).toBe(answer.checks.quotes.total);
  expect(answer.checks.sentences.removed).toBe(0);
  // The slide names no document the recorded answer does not cite: every source it cites is the completion report.
  expect(new Set(answer.evidence.map((source) => source.document_type))).toEqual(new Set(["Implementation Completion and Results Report"]));
  expect(text).not.toContain("Independent Evaluation Group");
});

test("a deck that cannot load says so on the stage with a way to try again", async ({ page }) => {
  await page.route("**/deck/data.json", (route) => route.fulfill({ status: 502, body: "" }));
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/present");
  await expect(page.getByRole("alert")).toContainText(deckCopy.states.loadError);
  await expect(page.getByRole("button", { name: deckCopy.states.reload })).toBeVisible();
});

test("each figure's steps are its text version's, in order, its words pass the copy lint and the number check, and each hairline figure's meaning passes the copy lint", () => {
  const check = copyChecker(fileURLToPath(new URL("../../DESIGN.md", import.meta.url)));
  const folder = fileURLToPath(new URL("../src/figures/", import.meta.url));
  const problems: string[] = [];
  const pieces: Record<string, string> = {};
  const svgs = readdirSync(folder).filter((name) => name.endsWith(".svg"));
  expect(svgs.length).toBe(Object.keys(figureCopy).length - 1);
  for (const name of svgs) {
    const svg = readFileSync(folder + name, "utf8").replace(/<style>[\s\S]*?<\/style>/g, "");
    const id = name.replace(/\.svg$/, "") as keyof typeof figureCopy;
    const words = [...svg.matchAll(/<(title|desc|text|tspan)\b[^>]*>([^<]*)<\/\1>/g)].map((found) => found[2].replace(/&#x27;/g, "'").replace(/&amp;/g, "&"));
    expect(words[0], `${name}'s title is the copy file's`).toBe(figureCopy[id].title);
    const steps = Math.max(...[...svg.matchAll(/data-step="(\d+)"/g)].map((found) => Number(found[1])));
    expect(steps, `${name}'s presses match its text version`).toBe(figureCopy[id].steps.length);
    for (const text of words) for (const problem of check(text)) problems.push(`${name}: "${text}" ${problem}`);
    pieces[name] = `<p>${words.join("</p><p>")}</p>`;
  }
  expect(numberCheck(pieces)).toEqual([]);
  const hairlines = fileURLToPath(new URL("../src/figures/hairline/", import.meta.url));
  for (const file of readdirSync(hairlines).filter((name) => name.endsWith(".js") && name !== "kernel.js")) {
    const means = /means:\s*"([^"]+)"/.exec(readFileSync(hairlines + file, "utf8"))?.[1] ?? "";
    expect(means.length, file).toBeGreaterThan(20);
    if (/\d/.test(means)) problems.push(`${file}: "${means}" holds a digit`);
    for (const problem of check(means)) problems.push(`${file}: "${means}" ${problem}`);
  }
  expect(problems).toEqual([]);
});
