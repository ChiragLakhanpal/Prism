// The deck at /present (ticket 47; the 47 brief): sixteen slides outside the app's frame, the logo where DESIGN.md
// section 9 puts it, the section 8 footer on every slide, keyboard moves, the speaker notes window, axe at WCAG 2.2
// AA, and the number check (src/strata/proposal/numbers.py) over every slide and its notes. The deck reads
// tests/fixtures/api/deck-data.json, built from the fixture database and the made-up month (tests/record_deck_api.py),
// where the built app reads /deck/data.json.
import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { readFileSync, readdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import type { Page } from "@playwright/test";
import { copyChecker } from "../lint/copy";
import { deckCopy, figureCopy } from "../src/deck/copy";
import { scan } from "./axe";
import { footerSentence } from "./design-md";
import { expect, recorded, test } from "./mocked";

const REPO = fileURLToPath(new URL("../../", import.meta.url));
// web/src/assets/world-bank-logo.md: the light file's hash when it was downloaded from data.worldbank.org.
const LIGHT_LOGO_SHA256 = "15a18185cbdc72239c7b052225e47d533c3128adc6df99e699ba3018ae3b6c9a";
const TOTAL = 16;
const CORE_SAMPLE_SOURCE = readFileSync(new URL("../src/figures/hairline/core-sample.js", import.meta.url), "utf8");

async function serveDeck(page: Page, file = "deck-data.json", status = 200) {
  const body = await recorded(file);
  await page.route("**/deck/data.json", (route) => route.fulfill({ status, contentType: "application/json", body }));
}

async function present(page: Page, n = 1, size = { width: 1440, height: 900 }) {
  await serveDeck(page);
  await page.setViewportSize(size);
  await page.goto(`/present/${n}`);
  await expect(page.locator("[data-deck=present]")).toBeVisible();
}

// The number check over named pieces of HTML: what it found, as the check's own sentence parts.
function numberCheck(pieces: Record<string, string>): { where: string; number: string; excerpt: string }[] {
  const done = spawnSync("python3", ["-m", "strata.proposal.numbers"], {
    cwd: REPO,
    env: { ...process.env, PYTHONPATH: `${REPO}src` },
    input: JSON.stringify(pieces),
    encoding: "utf8",
  });
  if (done.status !== 0 && done.status !== 1) throw new Error(done.stderr);
  return JSON.parse(done.stdout);
}

test("/present serves sixteen slides outside the app's frame, and a slide number out of range goes to the nearest slide", async ({ page }) => {
  await present(page, 99);
  await expect(page.locator("section[aria-roledescription=slide]")).toHaveCount(TOTAL);
  await expect(page.locator("section[data-slide]:not([hidden])")).toHaveCount(1);
  await expect(page.locator("section[data-slide='16']")).toBeVisible();
  expect(new URL(page.url()).pathname).toBe("/present/16");
  await expect(page).toHaveTitle("Slide 16 of 16 | Strata deck");
  // No navy bar, no box: the deck is not an app page.
  await expect(page.locator("[data-nav-bar], [data-box-band]")).toHaveCount(0);
});

test("the title slide shows the World Bank's light logo unaltered at 24 px or more with clear space, every figure carries it, and every slide the footer", async ({ page }) => {
  await present(page, 1);
  const footer = await footerSentence();
  const slide = page.locator("section[data-slide='1']");
  const logo = slide.getByRole("img", { name: deckCopy.logo });
  await expect(logo).toBeVisible();
  const file = await page.request.get(await logo.evaluate((img) => (img as HTMLImageElement).currentSrc));
  expect(createHash("sha256").update(await file.body()).digest("hex")).toBe(LIGHT_LOGO_SHA256);
  const box = (await logo.boundingBox())!;
  expect(box.height).toBeGreaterThanOrEqual(24);
  // Clear space of half its height: from the drawing above it, from the footer rule below and from the slide's edge.
  const drawing = (await slide.locator("[data-figure-frame=hairline] > div").first().boundingBox())!;
  const rule = (await slide.locator("[data-slide-footer]").boundingBox())!;
  const stage = (await page.locator("[data-stage]").boundingBox())!;
  expect(box.y - (drawing.y + drawing.height)).toBeGreaterThanOrEqual(box.height / 2 - 0.5);
  expect(rule.y - (box.y + box.height)).toBeGreaterThanOrEqual(box.height / 2 - 0.5);
  expect(stage.x + stage.width - (box.x + box.width)).toBeGreaterThanOrEqual(box.height / 2 - 0.5);

  for (let n = 1; n <= TOTAL; n += 1) {
    const section = page.locator(`section[data-slide='${n}']`);
    await expect(section.locator("[data-slide-footer]"), `slide ${n}`).toHaveText(footer);
    const frames = section.locator("[data-figure-frame]");
    for (let i = 0; i < (await frames.count()); i += 1) {
      await expect(frames.nth(i).locator("[data-credit-row] img[data-deck-logo]"), `slide ${n}, frame ${i + 1}`).toHaveCount(1);
    }
  }
  // Eight figures and two charts carry the logo, and no SVG holds it.
  await expect(page.locator("[data-figure-frame] img[data-deck-logo]")).toHaveCount(10);
  await expect(page.locator("svg image, svg img")).toHaveCount(0);
});

test("arrow keys, Page Up and Down, Home and End move the slides, the address follows, and axe finds no WCAG 2.2 AA violation on any slide", async ({ page }) => {
  test.setTimeout(60_000);
  await present(page, 1);
  const status = page.locator("[data-deck-status]");
  for (let n = 1; n <= TOTAL; n += 1) {
    await expect(page.locator(`section[data-slide='${n}']`)).toBeVisible();
    expect(new URL(page.url()).pathname).toBe(`/present/${n}`);
    expect((await scan(page)).violations.map((found) => `slide ${n}: ${found.id}`)).toEqual([]);
    if (n < TOTAL) await page.keyboard.press("ArrowRight");
  }
  await expect(status).toHaveText(new RegExp(`^Slide ${TOTAL} of ${TOTAL}: `));
  await page.keyboard.press("PageUp");
  await expect(page.locator("section[data-slide='15']")).toBeVisible();
  await page.keyboard.press("Home");
  await expect(page.locator("section[data-slide='1']")).toBeVisible();
  await page.keyboard.press("End");
  await expect(page.locator("section[data-slide='16']")).toBeVisible();
  await page.keyboard.press("ArrowLeft");
  await page.keyboard.press("ArrowUp");
  await expect(page.locator("section[data-slide='14']")).toBeVisible();
  // No single-letter shortcut: n does nothing.
  await page.keyboard.press("n");
  await expect(page.locator("section[data-slide='14']")).toBeVisible();
});

test("the speaker notes open in their own window and follow the deck, and the table twin swaps in on a chart slide", async ({ page, context }) => {
  await present(page, 7);
  await page.locator("[data-table-toggle]").click();
  await expect(page.locator("section[data-slide='7'] [data-chart=table] table")).toBeVisible();
  await expect(page.locator("[data-table-toggle]")).toHaveText(deckCopy.bar.showChart);

  const notesLink = page.getByRole("link", { name: deckCopy.bar.notesName });
  await context.route("**/deck/data.json", async (route) => route.fulfill({ contentType: "application/json", body: await recorded("deck-data.json") }));
  const [notes] = await Promise.all([context.waitForEvent("page"), notesLink.click()]);
  await expect(notes.locator("[data-deck=notes]")).toBeVisible();
  await expect(notes.locator("[data-notes-view='7']")).toBeVisible();
  await page.bringToFront();
  await page.keyboard.press("ArrowRight");
  await expect(notes.locator("[data-notes-view='8']")).toBeVisible();
  await expect(notes).toHaveTitle("Speaker notes, slide 8 of 16 | Strata deck");
  expect((await scan(notes)).violations.map((found) => found.id)).toEqual([]);
  // The notes' Next moves the deck too.
  await notes.getByRole("button", { name: deckCopy.notesView.nextButton }).click();
  await expect(page.locator("section[data-slide='9']")).toBeVisible();
});

test("the number check passes on every slide and its speaker notes, and fails a number planted in one", async ({ page }) => {
  await serveDeck(page);
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/present/page");
  await expect(page.locator("[data-reading-slide]")).toHaveCount(TOTAL);
  const pieces: Record<string, string> = {};
  for (let n = 1; n <= TOTAL; n += 1) {
    const section = page.locator(`[data-reading-slide='${n}']`);
    pieces[`Slide ${n}`] = await section.evaluate((element) => {
      const copy = element.cloneNode(true) as HTMLElement;
      copy.querySelectorAll("[data-notes]").forEach((notes) => notes.remove());
      return copy.outerHTML;
    });
    pieces[`Slide ${n}, notes`] = await section.locator("[data-notes]").evaluate((element) => element.outerHTML);
  }
  // Presentation mode draws the same slides on the canvas, the footer's counter included.
  await page.goto("/present/1");
  for (let n = 1; n <= TOTAL; n += 1) {
    pieces[`Slide ${n}, presented`] = await page.locator(`section[data-slide='${n}']`).evaluate((element) => element.outerHTML);
  }
  expect(numberCheck(pieces)).toEqual([]);
  const planted = { ...pieces, "Slide 5": pieces["Slide 5"].replace("</h2>", " across 12 countries</h2>") };
  expect(numberCheck(planted).map((found) => [found.where, found.number])).toEqual([["Slide 5", "12"]]);
});

test("below the size of the canvas the deck is a page that reflows, with each slide's notes and figure text, and the footer once", async ({ page }) => {
  await serveDeck(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/present/4");
  await expect(page.locator("[data-deck=read]")).toBeVisible();
  await expect(page.locator("[data-reading-slide]")).toHaveCount(TOTAL);
  await expect(page.getByRole("contentinfo")).toHaveText(await footerSentence());
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(deckCopy.slides.s1.statement);
  // A drawing wider than the column scrolls in its own region, and its text version is open.
  const slide = page.locator("[data-reading-slide='4']");
  await expect(slide.getByRole("region", { name: deckCopy.reading.scrolls(figureCopy.pipeline.title) })).toBeVisible();
  await expect(slide.locator("[data-figure-text=pipeline]")).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  expect((await scan(page)).violations.map((found) => found.id)).toEqual([]);
});

test("a deck that cannot load says so on the stage with a way to try again", async ({ page }) => {
  await page.route("**/deck/data.json", (route) => route.fulfill({ status: 502, body: "" }));
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/present");
  await expect(page.getByRole("alert")).toContainText(deckCopy.states.loadError);
  await expect(page.getByRole("button", { name: deckCopy.states.reload })).toBeVisible();
});

test("the figures hold no digits, and their titles, descriptions, labels and the hairline figure's meaning pass the copy lint", () => {
  const check = copyChecker(fileURLToPath(new URL("../../DESIGN.md", import.meta.url)));
  const folder = fileURLToPath(new URL("../src/figures/", import.meta.url));
  const problems: string[] = [];
  const svgs = readdirSync(folder).filter((name) => name.endsWith(".svg"));
  expect(svgs.length).toBe(7);
  for (const name of svgs) {
    const svg = readFileSync(folder + name, "utf8").replace(/<style>[\s\S]*?<\/style>/g, "");
    const words = [...svg.matchAll(/<(title|desc|text)\b[^>]*>([^<]*)<\/\1>/g)].map((found) => found[2].replace(/&#x27;/g, "'").replace(/&amp;/g, "&"));
    expect(words.length, name).toBeGreaterThan(3);
    for (const text of words) {
      if (/\d/.test(text)) problems.push(`${name}: "${text}" holds a digit`);
      for (const problem of check(text)) problems.push(`${name}: "${text}" ${problem}`);
    }
    const id = name.replace(/\.svg$/, "") as keyof typeof figureCopy;
    expect(words[0], `${name}'s title is the copy file's`).toBe(figureCopy[id].title);
  }
  const means = /means:\s*"([^"]+)"/.exec(CORE_SAMPLE_SOURCE)?.[1] ?? "";
  expect(means.length).toBeGreaterThan(20);
  if (/\d/.test(means)) problems.push(`core-sample.js: "${means}" holds a digit`);
  for (const problem of check(means)) problems.push(`core-sample.js: "${means}" ${problem}`);
  expect(problems).toEqual([]);
});
