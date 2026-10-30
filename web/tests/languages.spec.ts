// Other languages at seam 4 (ticket 42): an answer and a draft written in French, the evidence drawer and the source
// view of the French completion report, the language of answers and drafts in the view popover, and a ?lang= I can't
// use. The page stays lang="en": who wrote a piece of text decides its language (DESIGN.md section 10; the 42 design
// brief, section 2). Every answer comes from the server on the fixture (tests/record_*.py and strata.agent.scripted),
// which the Python tests check the server still gives. The words below are the ticket's and the 42 brief's.
import type { Page } from "@playwright/test";
import { scan } from "./axe";
import { askFromTheBox, drawer, landed, marker, panel } from "./answer-page";
import { expect, recorded, test } from "./mocked";

type Answer = { status?: number; body: string };

// Serve /api from recorded answers, by "METHOD /path" or by path for any method, and list what was asked.
async function serve(page: Page, answers: Record<string, Answer>) {
  const asked: { method: string; path: string; search: string; body: string | null }[] = [];
  const all: Record<string, Answer> = {
    "/api/me": { body: await recorded("me.json") },
    "/api/freshness": { body: await recorded("freshness.json") },
    "POST /api/evidence/opened": { body: '{"opened":[],"recorded":true}' },
    "/api/projects/P130164": { body: await recorded("project-p130164.json") },
    "/api/projects/P130164/summary": { body: await recorded("summary-p130164.json") },
    ...answers,
  };
  await page.route("**/api/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    asked.push({ method: request.method(), path: url.pathname, search: url.search, body: request.postData() });
    const answer = all[`${request.method()} ${url.pathname}`] ?? all[url.pathname];
    if (!answer) return route.fulfill({ status: 404, json: { detail: "Not Found" } });
    return route.fulfill({ status: answer.status ?? 200, contentType: "application/json", body: answer.body });
  });
  return asked;
}

async function axe(page: Page, within?: string) {
  await page.waitForFunction(() => document.getAnimations().every((animation) => animation.playState !== "running"));
  const results = await scan(page, within);
  return results.violations.map((v) => `${v.id}: ${v.nodes.map((node) => node.target.join(" ")).join(", ")}`);
}

// The language an element is read in: its own lang or the nearest one around it.
const readIn = (page: Page, selector: string) =>
  page.locator(selector).first().evaluate((element) => element.closest("[lang]")?.getAttribute("lang") ?? null);

async function askInFrench(page: Page, me = "me-lang-fr.json") {
  await page.setViewportSize({ width: 1440, height: 900 });
  const asked = await serve(page, { "/api/me": { body: await recorded(me) }, "/api/ask": { body: await recorded("ask-p127203-fr.sse") } });
  await page.goto("/projects/P130164?lang=fr");
  await expect(page.locator("main h1")).toBeVisible();
  await askFromTheBox(page, "Why were procurement processes delayed in P127203?");
  await landed(page);
  return asked;
}

test("with lang=fr the answer is written in French, its markers read in English, and the page stays English", async ({ page }) => {
  const asked = await askInFrench(page);

  // The question went out for an answer in French, and the screens' own words stayed English.
  const ask = asked.find((request) => request.path === "/api/ask");
  expect(JSON.parse(ask!.body!).lang).toBe("fr");
  expect(await page.evaluate(() => document.documentElement.lang)).toBe("en");
  await expect(panel(page).locator("[data-asked]")).toHaveText("Asked within P130164, for an answer in French.");
  expect(await readIn(page, "[data-sentence-text='0']")).toBe("fr");
  await expect(panel(page).locator("[data-sentence-text='0']")).toContainText(
    "des retards ont eu lieu dans la préparation des documents d’appels d’offres",
  );
  // A citation marker is the copy file's words, so a screen reader reads it in English.
  expect(await marker(page, 1).evaluate((element) => element.closest("[lang]")?.getAttribute("lang"))).toBe("en");
  // The answer is in the language you chose, so there is nothing to ask again.
  await expect(panel(page).getByRole("button", { name: /^Ask again in/ })).toHaveCount(0);
  expect(await axe(page, "[data-answer-panel]")).toEqual([]);
});

test("with French in effect, the box's Ask this line names the language of the answer before you press Enter", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await serve(page, { "/api/me": { body: await recorded("me-lang-fr.json") } });
  await page.goto("/projects/P130164?lang=fr");
  await expect(page.locator("main h1")).toBeVisible();
  await page.keyboard.press("/");
  await page.keyboard.type("Why were works contracts advertised again?");

  await expect(page.getByRole("option", { name: /^Ask this/ })).toContainText("Within P130164, for an answer in French");
});

test("the drawer keeps the wireframe's blocks for a French passage, in French, with its highlight's spoken words in English", async ({ page }) => {
  await askInFrench(page);
  await marker(page, 1).click();
  const sheet = drawer(page);
  await expect(sheet).toBeVisible();

  // Eyebrow, heading, the claim, the passage with its meta line, the line under it, the link: one order in every language.
  const order = await sheet.evaluate((root) =>
    ["[data-claim]", "[data-meta-line]", "[data-passage]", "[data-open-at-page]"].map((selector) => {
      const found = root.querySelector(selector);
      return found ? [...root.querySelectorAll("*")].indexOf(found) : -1;
    }),
  );
  expect(order.every((place, index) => place >= 0 && (index === 0 || place > order[index - 1]))).toBe(true);
  await expect(sheet.locator("[data-claim] p[lang='fr']")).toContainText("Selon le rapport d’achèvement");
  await expect(sheet.locator("[data-passage]")).toHaveAttribute("lang", "fr");
  await expect(sheet.locator("[data-meta-line]")).toContainText("In French");
  expect(await sheet.locator("[data-passage] mark .sr-only").first().evaluate((element) => element.closest("[lang]")?.getAttribute("lang"))).toBe("en");
  // Your language of answers and drafts is French, as the passage is, so the line under it says nothing more.
  await expect(sheet).not.toContainText("I quote sources only in the language they were written in.");
  expect(await axe(page, "[role=dialog]")).toEqual([]);
});

test("in English, the French answer offers to ask again in English and the drawer says why it shows no translation", async ({ page }) => {
  await askInFrench(page, "me.json");

  await expect(panel(page).locator("[data-asked]")).toHaveText("Asked within P130164, for an answer in French.");
  await expect(panel(page).getByRole("button", { name: "Ask again in English" })).toBeVisible();
  await marker(page, 1).click();
  // The drawer says why it shows no translation; "The whole paragraph, word for word." went in ticket 126.
  await expect(drawer(page)).toContainText("I quote sources only in the language they were written in.");
  await expect(drawer(page)).not.toContainText("word for word");
});

test("the source view of the French completion report marks every paragraph as French and names its language", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  const asked = await serve(page, {
    "/api/projects/P127203/documents/icr-2021-07-29": { body: await recorded("source-icr-p127203-fr-13.json") },
  });
  await page.goto("/projects/P127203/documents/icr-2021-07-29?page=13&para=1");
  await expect(page.locator("[data-source-page=read]")).toBeVisible();

  const paragraphs = page.locator("[data-passage-id]");
  expect(await paragraphs.count()).toBeGreaterThan(0);
  expect(await paragraphs.evaluateAll((all) => all.every((element) => element.getAttribute("lang") === "fr"))).toBe(true);
  await expect(page.locator("main")).toContainText("French");
  expect(await page.evaluate(() => document.documentElement.lang)).toBe("en");
  expect(asked.filter((request) => request.method === "GET" && request.path.startsWith("/api/projects/P127203/"))).toHaveLength(1);
  expect(await axe(page)).toEqual([]);
});

test("a ?lang= I can't use shows the info alert, never its value, and the page goes on in English", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await serve(page, { "/api/me": { body: await recorded("me-lang-unknown.json") } });
  await page.goto("/projects/P130164?lang=xx");
  await expect(page.locator("main h1")).toBeVisible();

  await expect(page.getByText("I can't write answers and drafts in the language this link asks for, so I'm using English.")).toBeVisible();
  await expect(page.locator("main")).not.toContainText("xx");
  expect(await page.evaluate(() => document.documentElement.lang)).toBe("en");
});

test("the language of answers and drafts is one tab stop in the view popover; arrows choose, and the choice is saved for next time", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  const asked = await serve(page, { "PUT /api/me/working-language": { status: 204, body: "" } });
  await page.goto("/");
  await page.getByRole("button", { name: "View: World Bank staff" }).click();
  const popover = page.getByRole("dialog", { name: "Your view" });
  const group = popover.getByRole("group", { name: "Language of answers and drafts" });
  await expect(group).toHaveAccessibleDescription("The screens stay in English. Quotes stay in the language their source was written in.");
  // Each language: its English name, and its own name in its own language.
  await expect(group.locator("[data-language=fr] [lang=fr]")).toHaveText("Français");
  expect(await axe(page, "[role=dialog]")).toEqual([]);

  // The popover opens on the current view's row (ticket 40, which keeps brief 40's focus rule over brief 42's); Tab
  // moves through the rows and the past date to the language group, one tab stop on its chosen language.
  const english = group.getByRole("radio", { name: /^English/ });
  for (let press = 0; press < 10 && !(await english.evaluate((element) => element === document.activeElement)); press += 1) {
    await page.keyboard.press("Tab");
  }
  await expect(english).toBeFocused();
  await page.keyboard.press("ArrowDown");
  await page.keyboard.press("ArrowDown");
  await expect(group.getByRole("radio", { name: "Spanish Español" })).toBeChecked();

  await expect(popover.locator("[data-language-status]")).toHaveText(
    "From now on, I write answers and drafts in Spanish. Answers and drafts already written keep their language.",
  );
  const saves = asked.filter((request) => request.method === "PUT");
  expect(saves.map((request) => JSON.parse(request.body!))).toEqual([{ code: "es" }]);
  expect(new URL(page.url()).searchParams.get("lang")).toBeNull();
});

test("when the choice can't be saved it holds in the page's address instead, and the status line says so", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await serve(page, { "PUT /api/me/working-language": { status: 503, body: '{"code":"data_service"}' } });
  await page.goto("/");
  await page.getByRole("button", { name: "View: World Bank staff" }).click();
  await page.getByRole("dialog", { name: "Your view" }).locator("[data-language=pt]").click();

  await expect(page.getByRole("dialog", { name: "Your view" }).locator("[data-language-status]")).toHaveText(
    "I couldn't save your choice for next time, so I kept it in this page's link instead.",
  );
  await expect.poll(() => new URL(page.url()).searchParams.get("lang")).toBe("pt");
});

test("review notes written in French say so under their method, and every note is marked French", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await serve(page, {
    "/api/drafts/draft-0005": { body: await recorded("drafts-review-notes-fr.json") },
    "/api/drafts/existing": { body: '{"draft":null}' },
  });
  await page.goto("/drafts/draft-0005");
  await expect(page.locator("[data-draft-page]:not([data-draft-page=loading])")).toBeVisible();

  await expect(page.locator("[data-draft-language]")).toHaveText("I wrote this draft in French. Quotes stay in the language of their source.");
  const notes = page.locator("[data-note]:visible");
  expect(await notes.count()).toBeGreaterThan(0);
  expect(await notes.evaluateAll((all) => all.every((element) => element.getAttribute("lang") === "fr"))).toBe(true);
  // STEP's field names and values stay in English, word for word, inside the French sentences.
  await expect(notes.first()).toContainText("Pending Implementation");
  expect(await page.evaluate(() => document.documentElement.lang)).toBe("en");
  expect(await axe(page)).toEqual([]);
});

test("Sources and licenses lists the Procurement Plan template in French under its French title, in French", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await serve(page, { "/api/data/sources": { body: await recorded("data-sources.json") } });
  await page.goto("/data/sources");

  const title = page.locator("main li [lang=fr]");
  await expect(title).toHaveText("Plan de passation de marchés (Partie Textuelle)");
  await expect(page.locator("main li").filter({ has: page.locator("[lang=fr]") })).toHaveText(
    "Plan de passation de marchés (Partie Textuelle), published by the World Bank, as the Procurement Plan template in French, from the World Bank's Documents & Reports.",
  );
});

test("an English answer keeps the French words it quotes in French, and its check line says a model judged across languages", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await serve(page, { "/api/ask": { body: await recorded("ask-p127203-en-cites-french.sse") } });
  await page.goto("/projects/P130164");
  await expect(page.locator("main h1")).toBeVisible();
  await askFromTheBox(page, "What delayed procurement in P127203, according to its completion report?");
  await landed(page);

  await expect(panel(page).locator("[data-asked]")).toHaveText("Asked within P130164.");
  const quoted = panel(page).locator("[data-sentence-text] [lang=fr]");
  await expect(quoted).toHaveText("des retards ont eu lieu dans la préparation des documents d’appels d’offres et des processus de passations des marchés");
  expect(await readIn(page, "[data-sentence-text='0']")).toBe("en");
  // The sentences that needed no model are the fourth check in "How was that checked?" since ticket 126 (T28).
  await expect(panel(page).locator("[data-check-part=judged]")).toHaveText(
    "Judged by a model: 1 of 1 sentence follows from its sources. It cites a source written in another language.",
  );
  expect(await axe(page, "[data-answer-panel]")).toEqual([]);
});
