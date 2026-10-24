// A package planned from a sentence (ticket 15) at seam 4: the one box's "Plan a package from this sentence",
// the reading page, the package workspace with its criterion chips and their editors, section 1's reruns, a
// comparable package in the evidence drawer, and the Packages tab. The answers are the ones the server wrote
// on the fixture (tests/record_packages_api.py), which tests/test_planned_packages.py checks the server
// still gives. The words below are the ticket's and the 15 design brief's, copied here so the test checks the
// copy file against an independent source.
import AxeBuilder from "@axe-core/playwright";
import type { Page, Request } from "@playwright/test";
import { expect, recorded, test } from "./mocked";

const SENTENCE = "rural roads, Kenya, about US$15 million";
const PACKAGE = "/packages/pkg-000000000001";
const WCAG_22_AA = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

type Answer = { status?: number; body: string; type?: string; delay?: number; hold?: boolean };

// Serve /api from recorded answers, by "METHOD /path", "METHOD /path?query" (find_comparables' criteria, sorted)
// or by path for any method. An /api call with no answer gets 404, and every request is listed for the test.
async function serve(page: Page, answers: Record<string, Answer>) {
  const asked: Request[] = [];
  const base: Record<string, Answer> = {
    "/api/me": { body: await recorded("me.json") },
    "/api/freshness": { body: await recorded("freshness.json") },
    "POST /api/evidence/opened": { body: '{"recorded":true}' },
    "/api/comparables?category=Works&country=KE&method=Request+for+Bids": { body: await recorded("comparables-planned-works-rfb-ke.json") },
    "/api/comparables?category=Works&country=KE&method=Request+for+Quotations": { body: await recorded("comparables-planned-works-rfq-ke.json") },
  };
  const all = { ...base, ...answers };
  await page.route("**/api/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    asked.push(request);
    const answer = all[`${request.method()} ${url.pathname}${url.search}`] ?? all[`${url.pathname}${url.search}`] ??
      all[`${request.method()} ${url.pathname}`] ?? all[url.pathname];
    if (!answer) return route.fulfill({ status: 404, json: { detail: "Not Found" } });
    if (answer.hold) return new Promise(() => {});
    if (answer.delay) await new Promise((resolve) => setTimeout(resolve, answer.delay));
    return route.fulfill({ status: answer.status ?? 200, contentType: answer.type ?? "application/json", body: answer.body });
  });
  return asked;
}

const stream = async (name: string): Promise<Answer> => ({ body: await recorded(name), type: "text/event-stream" });

const box = (page: Page) => page.locator("[data-box-band]").getByRole("combobox");
const options = (page: Page) => page.getByRole("listbox", { name: "What Enter will do" }).getByRole("option");
const card = (page: Page) => page.locator("[data-criteria-card]");
const group = (page: Page, name: string) => card(page).getByRole("group", { name });
const chip = (page: Page, key: string) => page.locator(`[data-chip="${key}"]`);
const live = (page: Page) => page.locator("[data-workspace-live]");

// From Home, the person types the ticket's sentence into the one box and chooses to plan a package from it.
async function planFromTheBox(page: Page, { width = 1440, height = 900, answers = {} }: { width?: number; height?: number; answers?: Record<string, Answer> } = {}) {
  await page.setViewportSize({ width, height });
  const asked = await serve(page, { "POST /api/planned-packages": await stream("package-plan-rural-roads.sse"), ...answers });
  await page.goto("/");
  await expect(page.locator("main h1")).toBeVisible();
  await page.keyboard.press("/");
  await page.keyboard.type(SENTENCE);
  await options(page).filter({ hasText: "Plan a package from this sentence" }).click();
  return asked;
}

// A saved package, opened by its address.
async function openPackage(page: Page, { width = 1440, height = 900, file = "planned-package-rural-roads.json", path = PACKAGE, answers = {} }:
  { width?: number; height?: number; file?: string; path?: string; answers?: Record<string, Answer> } = {}) {
  await page.setViewportSize({ width, height });
  const asked = await serve(page, { [`GET /api/planned-packages/${path.split("/").pop()!.split("?")[0]}`]: { body: await recorded(file) }, ...answers });
  await page.goto(path);
  await expect(page.locator("[data-planned-package]:not([data-planned-package=loading])")).toBeVisible();
  return asked;
}

const chipTexts = async (page: Page, name: string) =>
  (await group(page, name).locator("[data-chip]").allInnerTexts()).map((text) => text.replace(/\s+/g, " ").trim());

async function axe(page: Page) {
  await page.waitForFunction(() => document.getAnimations().every((animation) => animation.playState !== "running"));
  const results = await new AxeBuilder({ page }).withTags(WCAG_22_AA).analyze();
  return results.violations.map((v) => `${v.id}: ${v.nodes.map((node) => node.target.join(" ")).join(", ")}`);
}

// ── The box, the reading page and the chips ──────────────────────────────

test("the sentence yields the wireframe's chips: four under What with one guess, Kenya, and How with two computed", async ({ page }) => {
  const asked = await planFromTheBox(page);

  await expect(page).toHaveURL(PACKAGE);
  await expect(page.locator("main h1")).toHaveText("Rural roads, Kenya");
  expect(await chipTexts(page, "What is being bought")).toEqual(["Works", "Rural roads", "About US$15 million", "2 lots · guess"]);
  expect(await chipTexts(page, "Where the package is")).toEqual(["Kenya"]);
  expect(await chipTexts(page, "How it will be procured")).toEqual([
    "Request for Bids (RFB)",
    "Open international · computed",
    "Single stage, one envelope",
    "Post-qualification",
    "Prior review · computed",
    "Add your plan",
  ]);
  await expect(card(page).locator("[data-you-wrote]")).toHaveText(`You wrote: "${SENTENCE}"`);
  await expect(card(page).locator("[data-instruction]")).toHaveText("Choose any part to change it. One guess to check.");
  // One POST planned the package; nothing else made one.
  expect(asked.filter((request) => request.method() === "POST" && new URL(request.url()).pathname === "/api/planned-packages")).toHaveLength(1);
});

test("free text lists Plan a package second, and Enter asks instead, so no package is made until the person chooses it", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  const asked = await serve(page, { "POST /api/ask": { hold: true, body: "" } });
  await page.goto("/");
  await page.keyboard.press("/");
  await page.keyboard.type(SENTENCE);

  await expect(options(page)).toHaveCount(2);
  await expect(options(page).nth(1)).toHaveAccessibleName(
    "Plan a package from this sentence I'll read the criteria from your sentence and open a new package. You can change any of them.",
  );
  await expect(options(page).nth(1)).toHaveAttribute("aria-selected", "false");
  await page.keyboard.press("Enter");

  await expect.poll(() => asked.filter((request) => new URL(request.url()).pathname === "/api/ask").length).toBe(1);
  expect(asked.filter((request) => new URL(request.url()).pathname.startsWith("/api/planned-packages"))).toEqual([]);
  await expect(page).toHaveURL("/");
});

test("while I read the sentence the page says each step, then becomes the saved package in place, and Back returns to where you typed", async ({ page }) => {
  let release: () => void = () => {};
  const held = new Promise<void>((resolve) => (release = resolve));
  await page.setViewportSize({ width: 1440, height: 900 });
  await serve(page, {});
  const body = await recorded("package-plan-rural-roads.sse");
  await page.route("**/api/planned-packages", async (route) => {
    await held;
    await route.fulfill({ contentType: "text/event-stream", body });
  });
  await page.goto("/");
  await page.keyboard.press("/");
  await page.keyboard.type(SENTENCE);
  await options(page).filter({ hasText: "Plan a package from this sentence" }).click();

  await expect(page).toHaveURL("/packages/new");
  await expect(page.locator("main h1")).toHaveText("New package");
  await expect(page.locator("main h1")).toBeFocused();
  await expect(page.locator("[data-saved-stamp]")).toHaveText("Not saved yet");
  await expect(card(page).locator("[data-you-wrote]")).toHaveText(`You wrote: "${SENTENCE}"`);
  // Only the step in progress is listed while nothing has come back, in the present tense.
  await expect(card(page).locator("[data-step]")).toHaveText(["Reading your sentence"]);
  await expect(card(page).locator("[data-step=running]")).toHaveCount(1);

  release();
  await expect(page).toHaveURL(PACKAGE);
  await expect(page.locator("main h1")).toHaveText("Rural roads, Kenya");
  // Focus stays on the h1, and the live region says what was read.
  await expect(page.locator("main h1")).toBeFocused();
  await expect(live(page)).toHaveText("I read five criteria from your sentence. One guess to check.");
  await page.goBack();
  await expect(page).toHaveURL("/");
});

test("a reload of the reading page goes to the Packages tab with the box in plan mode", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await serve(page, { "GET /api/planned-packages": { body: await recorded("planned-packages-empty.json") } });
  await page.goto("/packages/new");

  await expect(page).toHaveURL("/packages");
  await expect(box(page)).toBeFocused();
  await expect(page.locator("[data-box-band] [data-placeholder]")).toHaveText("Describe the package in one sentence");
  await expect(box(page)).toHaveAccessibleDescription(
    "Say what is being bought, where, and about how much. For example: rural roads, Kenya, about US$15 million.",
  );
});

test("a sentence with no package in it keeps the sentence, saves nothing, and offers to change it or set the criteria yourself", async ({ page }) => {
  await planFromTheBox(page, { answers: { "POST /api/planned-packages": await stream("package-plan-no-package.sse") } });

  await expect(page).toHaveURL("/packages/new");
  await expect(page.locator("[data-planned-package=no-package]")).toBeVisible();
  await expect(card(page)).toContainText("I couldn't find a package in that sentence.");
  await expect(card(page)).toContainText(`You wrote: "${SENTENCE}"`);
  await expect(page.locator("[data-past-range]")).toHaveCount(0);
  await page.getByRole("button", { name: "Change the sentence" }).click();
  await expect(box(page)).toBeFocused();
  await expect(box(page)).toHaveValue(SENTENCE);
});

test("when the reader does not answer, the error keeps the sentence and nothing is saved", async ({ page }) => {
  await planFromTheBox(page, { answers: { "POST /api/planned-packages": await stream("package-plan-reader-unavailable.sse") } });

  await expect(page.locator("[data-planned-package=failed]")).toBeVisible();
  await expect(page.getByRole("alert")).toContainText("I couldn't read your sentence just now. Nothing is saved yet.");
  await expect(page.getByRole("button", { name: "Try again" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Set the criteria yourself" })).toBeVisible();
  await expect(page.locator("[data-past-range]")).toHaveCount(0);
});

// ── The chips and their editors ──────────────────────────────────────────

// The change answers the server recorded from the first save, by the change the page sends.
async function changes(page: Page, delay = 0) {
  const answers: Record<string, string> = {
    "method:set:ICB": "planned-package-change-method-icb.json",
    "method:set:Request for Quotations": "planned-package-change-method-rfq.json",
    "lots:keep:": "planned-package-change-keep-lots.json",
    "estimated_amount_usd:set:5000000": "planned-package-change-amount.json",
    "review_type:set:Post": "planned-package-change-review-post.json",
    "description:set:Rural feeder roads": "planned-package-change-description.json",
    "plan_months:set:6": "planned-package-change-plan.json",
  };
  const sent: Record<string, unknown>[] = [];
  await page.route("**/api/planned-packages/pkg-000000000001", async (route) => {
    if (route.request().method() !== "POST") return route.fallback();
    const body = route.request().postDataJSON() as { field: string; action: string; value?: unknown };
    sent.push(body);
    const file = answers[`${body.field}:${body.action}:${body.value ?? ""}`];
    if (delay) await new Promise((resolve) => setTimeout(resolve, delay));
    if (!file) return route.fulfill({ status: 422, json: { code: "invalid_value", field: body.field } });
    return route.fulfill({ contentType: "application/json", body: await recorded(file) });
  });
  return sent;
}

test("each chip is a 32 px button that says its state in words, and opens its editor by keyboard, which Escape closes", async ({ page }) => {
  await openPackage(page);

  for (const key of ["category", "lots", "market_approach", "plan_months"]) {
    const box = (await chip(page, key).boundingBox())!;
    expect(box.height, key).toBeGreaterThanOrEqual(32);
  }
  await expect(chip(page, "lots")).toHaveAccessibleName("2 lots · guess");
  await expect(chip(page, "lots")).toHaveAccessibleDescription("Number of lots. My guess.");
  await expect(chip(page, "review_type")).toHaveAccessibleName("Prior review · computed");
  await expect(chip(page, "review_type")).toHaveAccessibleDescription("Review type. Computed from the thresholds.");
  await expect(chip(page, "method")).toHaveAccessibleDescription("Method. The default, since your sentence did not say.");

  await chip(page, "review_type").focus();
  await page.keyboard.press("Enter");
  const editor = page.getByRole("dialog", { name: "Review type" });
  await expect(editor).toBeVisible();
  await expect(chip(page, "review_type")).toHaveAttribute("aria-expanded", "true");
  await expect(editor).toContainText("I computed this from the thresholds.");
  await expect(editor).toContainText("In STEP: Review Type, Prior.");
  await expect(editor).toContainText("This doesn't change which packages I compare with.");
  await page.keyboard.press("Escape");
  await expect(editor).toHaveCount(0);
  await expect(chip(page, "review_type")).toBeFocused();
});

// The package form schema is the one place a chip is defined: the screen draws whatever fields the server hands
// it, in their group and order. tests/test_planned_packages.py proves the server hands over a field added to
// config/package_form.toml and drops one removed from it; here the screen draws exactly those.
test("a field added to the package form schema is a chip in its group, and a field removed from it is no chip", async ({ page }) => {
  const recordedPage = JSON.parse(await recorded("planned-package-rural-roads.json"));
  const added = structuredClone(recordedPage);
  added.form.fields.push({
    ...added.form.fields.find((field: { key: string }) => field.key === "procurement_process"),
    key: "high_sea_sh_risk",
    label: "SEA/SH risk",
    add_label: "Add the SEA/SH risk",
    step_field: "High SEA/SH Risk",
    default: null,
    options: [{ value: "Yes", label: "High SEA/SH risk" }, { value: "No", label: "Not high" }],
  });
  added.package.fields.push({ key: "high_sea_sh_risk", group: "how", value: null, provenance: null, computed: null });
  await openPackage(page, { answers: { "GET /api/planned-packages/pkg-000000000001": { body: JSON.stringify(added) } } });

  expect((await chipTexts(page, "How it will be procured")).at(-1)).toBe("Add the SEA/SH risk");
  await chip(page, "high_sea_sh_risk").click();
  await expect(page.getByRole("dialog", { name: "SEA/SH risk" })).toContainText("High SEA/SH risk");

  const removed = structuredClone(recordedPage);
  removed.form.fields = removed.form.fields.filter((field: { key: string }) => field.key !== "lots");
  removed.package.fields = removed.package.fields.filter((field: { key: string }) => field.key !== "lots");
  removed.package.guesses = 0;
  await page.unrouteAll({ behavior: "ignoreErrors" });
  await openPackage(page, { answers: { "GET /api/planned-packages/pkg-000000000001": { body: JSON.stringify(removed) } } });

  expect(await chipTexts(page, "What is being bought")).toEqual(["Works", "Rural roads", "About US$15 million"]);
  await expect(chip(page, "lots")).toHaveCount(0);
});

test("the computed note states the rules with the thresholds file's values and its source", async ({ page }) => {
  await openPackage(page);

  const note = page.locator("[data-computed-note]");
  await expect(note.locator("p[data-numbers]:not([data-source])")).toHaveText(
    "I computed review type and market approach from the thresholds. Works of US$10 million or more go to prior review. " +
      "In Kenya, plans send works of US$15 million or more to international bidding.",
  );
  await expect(note).toContainText("I assumed the implementing agency's procurement risk is High, because I don't know it yet.");
  await expect(note).toContainText("Source: The World Bank's procurement prior review thresholds for investment project financing, as of October 24, 2026.");
});

test("typing ICB into the method chip stores Request for Bids with an open international market approach", async ({ page }) => {
  await openPackage(page);
  const sent = await changes(page);

  await chip(page, "method").click();
  const editor = page.getByRole("dialog", { name: "Method" });
  await editor.getByRole("textbox", { name: "Method" }).fill("ICB");
  const first = editor.getByRole("radio").first();
  await expect(first).toHaveAccessibleName(/^Request for Bids \(RFB\)/);
  await expect(editor).toContainText('I read "ICB" as this, the name the Procurement Regulations use now.');
  await page.keyboard.press("Enter");

  await expect(editor).toHaveCount(0);
  await expect.poll(() => sent).toEqual([{ field: "method", action: "set", value: "ICB" }]);
  await expect(chip(page, "method")).toHaveText("Request for Bids (RFB)");
  await expect(chip(page, "market_approach")).toHaveText("Open international");
  await expect(chip(page, "method")).toBeFocused();
  await expect(page.locator("[data-saved-stamp]")).toHaveText("Saved October 23, 2026");
});

test("an old method name never reaches the copy file: the option's caption echoes what was typed", async ({ page }) => {
  await openPackage(page);
  await chip(page, "method").click();
  const editor = page.getByRole("dialog", { name: "Method" });
  await editor.getByRole("textbox", { name: "Method" }).fill("shopping");

  await expect(editor.getByRole("radio").first()).toHaveAccessibleName(/^Request for Quotations \(RFQ\)/);
  await expect(editor).toContainText('I read "shopping" as this');
});

test("changing a chip that picks the comparables reruns find_comparables and redraws section 1; other chips leave it alone", async ({ page }) => {
  const asked = await openPackage(page);
  await changes(page, 600);
  await expect(page.locator("[data-past-range]")).toHaveAttribute("data-past-range", "custom");
  const comparables = () => asked.filter((request) => new URL(request.url()).pathname === "/api/comparables").map((request) => new URL(request.url()).searchParams.get("method"));
  await expect.poll(comparables).toEqual(["Request for Bids"]);

  await chip(page, "description").click();
  await page.getByRole("dialog", { name: "Description" }).getByRole("textbox").fill("Rural feeder roads");
  await page.keyboard.press("Enter");
  await expect(chip(page, "description")).toHaveText("Rural feeder roads");
  await expect(live(page)).toHaveText("Description set to Rural feeder roads.");
  await expect(page.locator("[data-saved-stamp]")).toHaveText("Saved October 23, 2026");
  expect(comparables()).toEqual(["Request for Bids"]);

  await chip(page, "method").click();
  await page.getByRole("dialog", { name: "Method" }).locator("label", { hasText: "Request for Quotations (RFQ)" }).click();
  // The chip shows the new value at once, and the section says it is updating until the answer comes.
  await expect(chip(page, "method")).toHaveText("Request for Quotations (RFQ)");
  await expect(page.locator("[data-saved-stamp]")).toHaveText("Saving");
  await expect(page.locator("[data-section-status]")).toHaveText("Finding comparable packages for your new criteria.");
  await expect(page.locator("[data-past-range]")).toHaveAttribute("aria-busy", "true");
  await expect.poll(comparables).toEqual(["Request for Bids", "Request for Quotations"]);
  await expect(page.locator("[data-past-range]")).toHaveAttribute("data-past-range", "unmeasured");
  await expect(page.locator("[data-section-status]")).toHaveCount(0);
  await expect(page.locator("[data-criteria-line]")).toHaveText(/^Comparable packages: Works, Request for Quotations, Kenya/);
  await expect(page.locator("[data-past-range]")).toContainText("To compare with more packages, change a criterion above.");
  await expect(live(page)).toHaveText("Updated. 27 past packages matched this one, but I can't measure how long any of them took.");
});

test("with no plan yet, section 1 names its comparables and asks for the plan before it shows the range", async ({ page }) => {
  await openPackage(page);
  await changes(page);

  const prompt = page.locator("[data-plan-prompt]");
  await expect(page.locator("[data-criteria-line]")).toHaveText(
    "Comparable packages: Works, Request for Bids, Kenya, notices from 2019 to 2026.",
  );
  await expect(prompt).toContainText(
    "How many months does your plan allow from bid notice to signed contract? I ask before I show the past range, so the range doesn't set your plan.",
  );
  await expect(prompt).toContainText("I found 49 comparable packages for these criteria.");
  await expect(page.locator("[data-finding]")).toHaveCount(0);
  await expect(prompt.getByRole("button", { name: "Show the past range" })).toHaveAttribute("data-button", "primary");
  await prompt.getByRole("textbox", { name: "Your plan, in months" }).fill("6");
  await prompt.getByRole("button", { name: "Show the past range" }).click();

  await expect(chip(page, "plan_months")).toHaveText("Your plan: 6 months");
  await expect(page.locator("[data-finding]")).toBeVisible();
  await expect(prompt).toHaveCount(0);
});

test("a smaller amount recomputes review type and market approach, and the note says what changed and why", async ({ page }) => {
  await openPackage(page);
  await changes(page);

  await chip(page, "estimated_amount_usd").click();
  const editor = page.getByRole("dialog", { name: "Estimated amount" });
  await editor.getByRole("textbox").fill("5m");
  await expect(editor.locator("[data-read-back]")).toHaveText("I read this as US$5,000,000.");
  await editor.getByRole("button", { name: "Use this" }).click();

  await expect(chip(page, "review_type")).toHaveText("Post review · computed");
  await expect(chip(page, "market_approach")).toHaveText("Open national · computed");
  await expect(page.locator("[data-recomputed]")).toHaveText([
    "Market approach changed from Open international to Open national because the estimated amount changed.",
    "Review type changed from Prior review to Post review because the estimated amount changed.",
  ]);
  await expect(live(page)).toContainText("Review type changed from Prior review to Post review, computed from the thresholds.");
});

test("an amount the editor can't read says why and changes nothing", async ({ page }) => {
  await openPackage(page);
  const sent = await changes(page);

  await chip(page, "estimated_amount_usd").click();
  const editor = page.getByRole("dialog", { name: "Estimated amount" });
  await editor.getByRole("textbox").fill("lots of money");
  await page.keyboard.press("Enter");

  await expect(editor.locator("[data-editor-error]")).toHaveText("I couldn't read that amount. Type a number in US dollars, such as 15 million.");
  await expect(editor.getByRole("textbox")).toHaveAccessibleDescription("I couldn't read that amount. Type a number in US dollars, such as 15 million.");
  expect(sent).toEqual([]);
  await expect(chip(page, "estimated_amount_usd")).toHaveText("About US$15 million");
});

test("keeping the guess makes it a typed chip, and the guess count goes away", async ({ page }) => {
  await openPackage(page);
  await changes(page);

  await chip(page, "lots").click();
  await page.getByRole("dialog", { name: "Number of lots" }).getByRole("button", { name: "Keep 2 lots" }).click();

  await expect(chip(page, "lots")).toHaveText("2 lots");
  await expect(chip(page, "lots")).toHaveAttribute("data-look", "typed");
  await expect(card(page).locator("[data-instruction]")).toHaveText("Choose any part to change it.");
  await expect(live(page)).toHaveText("Number of lots kept as 2 lots. No guesses left to check.");
  await expect(chip(page, "lots")).toBeFocused();
});

test("a computed chip you set yourself turns typed, the note shows both values, and Use the computed value goes back", async ({ page }) => {
  await openPackage(page);
  await changes(page);

  await chip(page, "review_type").click();
  const editor = page.getByRole("dialog", { name: "Review type" });
  await editor.getByRole("button", { name: "Set it yourself" }).click();
  await editor.locator("label", { hasText: "Post review" }).click();

  await expect(chip(page, "review_type")).toHaveText("Post review");
  await expect(page.locator("[data-set-by-you]")).toHaveText("You set review type to Post review. The thresholds give Prior review.");
  await chip(page, "review_type").click();
  await expect(page.getByRole("dialog", { name: "Review type" })).toContainText("You set this. The thresholds give Prior review.");
  await expect(page.getByRole("dialog", { name: "Review type" }).getByRole("button", { name: "Use the computed value" })).toBeVisible();
});

// ── A comparable package in the evidence drawer ──────────────────────────

const MOWI = "KE-MOWI-47509-CW-RFB";

async function openChart(page: Page, width = 1440) {
  const asked = await openPackage(page, {
    width,
    answers: {
      "GET /api/evidence": { body: await recorded("evidence-package-ke-mowi-47509.json") },
      "GET /api/evidence/opened": { body: '{"opened":[]}' },
    },
  });
  await page.getByRole("button", { name: "Show it without a plan" }).click();
  await expect(page.locator("[data-finding]")).toBeVisible();
  return asked;
}

const dot = (page: Page, ref: string) => page.locator(`[data-dot-target][aria-label^="${ref},"]`);
const drawer = (page: Page) => page.getByRole("dialog", { name: `Records for comparable package ${MOWI}` });

test("a click on a dot opens its package's records in the evidence drawer, and closing it gives focus back to the dot", async ({ page }) => {
  const asked = await openChart(page);
  await page.locator("[data-range-chart]").scrollIntoViewIfNeeded();
  const column = (await page.locator("[data-planned-package]").boundingBox())!;

  const target = (await dot(page, MOWI).boundingBox())!;
  await page.mouse.click(target.x + target.width / 2, target.y + target.height / 2);

  await expect(drawer(page)).toBeVisible();
  await expect(page).toHaveURL(`${PACKAGE}?evidence=${encodeURIComponent(`strata.gold.package:${MOWI}`)}`);
  await expect(drawer(page).getByRole("heading").first()).toBeFocused();
  await expect(drawer(page)).toContainText("This package took 17.7 months from its notice on October 1, 2019 to its signed contract on March 23, 2021.");
  await expect(drawer(page).getByRole("heading", { name: "Specific procurement notice" })).toBeVisible();
  await expect(drawer(page).getByRole("heading", { name: "Contract award" })).toBeVisible();
  // The opened dot keeps its ring while its records show, and the column did not move.
  await expect(page.locator("[data-opened-ring]")).toHaveCount(1);
  expect((await page.locator("[data-planned-package]").boundingBox())!.x).toBe(column.x);
  await expect.poll(() => asked.filter((request) => request.method() === "POST" && new URL(request.url()).pathname === "/api/evidence/opened").length).toBe(1);

  await drawer(page).getByRole("button", { name: "Close the records" }).click();
  await expect(drawer(page)).toHaveCount(0);
  await expect(dot(page, MOWI)).toBeFocused();
  await expect(page.locator("[data-opened-ring]")).toHaveCount(0);
});

test("Enter on the focused dot opens its records, and Escape closes the drawer and gives focus back to the dot", async ({ page }) => {
  await openChart(page);
  const dots = page.locator("[data-dot-target]");
  const index = await dots.evaluateAll((all, ref) => all.findIndex((one) => one.getAttribute("aria-label")!.startsWith(`${ref},`)), MOWI);
  // The chart is one tab stop after the plan's input: with no plan, there is no line to stop at between them.
  await page.getByRole("textbox", { name: "Planned months" }).focus();
  await page.keyboard.press("Tab");
  await expect(dots.first()).toBeFocused();
  for (let step = 0; step < index; step += 1) await page.keyboard.press("ArrowRight");
  await expect(dot(page, MOWI)).toBeFocused();

  await page.keyboard.press("Enter");
  await expect(drawer(page)).toBeVisible();
  await expect(drawer(page).getByRole("heading").first()).toBeFocused();

  await page.keyboard.press("Escape");
  await expect(drawer(page)).toHaveCount(0);
  await expect(dot(page, MOWI)).toBeFocused();
});

test("when a rerun has redrawn the dot that opened the records away, closing them gives focus to section 1's heading", async ({ page }) => {
  await openChart(page);
  await changes(page);
  await dot(page, MOWI).focus();
  await page.keyboard.press("Enter");
  await expect(drawer(page)).toBeVisible();

  // Beside the drawer the page stays usable: a new method finds no packages it can measure, so the chart goes.
  await chip(page, "method").click();
  await page.getByRole("dialog", { name: "Method" }).locator("label", { hasText: "Request for Quotations (RFQ)" }).click();
  await expect(page.locator("[data-past-range]")).toHaveAttribute("data-past-range", "unmeasured");
  await expect(page.locator("[data-dot-target]")).toHaveCount(0);

  await drawer(page).getByRole("heading").first().focus();
  await page.keyboard.press("Escape");
  await expect(drawer(page)).toHaveCount(0);
  await expect(page.locator("[data-past-range] h2")).toBeFocused();
});

test("a row of the table twin opens the same records, and the row stays marked while they show", async ({ page }) => {
  await openChart(page);
  await page.getByRole("button", { name: "Show the table" }).click();
  const row = page.locator(`[data-open-row="${MOWI}"]:visible`);
  await expect(row).toHaveAccessibleName(`Open the records for ${MOWI}`);

  await row.click();
  await expect(drawer(page)).toBeVisible();
  await expect(page.locator(`[data-selected]:visible`)).toContainText(MOWI);
  await page.keyboard.press("Escape");
  await expect(row).toBeFocused();
});

// ── Reopening, and the Packages tab ──────────────────────────────────────

test("a saved package reopens with the same chips, and the Packages tab lists it with the person's checked plan", async ({ page }) => {
  await planFromTheBox(page, { answers: { "GET /api/planned-packages": { body: await recorded("planned-packages-list.json") },
                                          "GET /api/planned-packages/pkg-000000000001": { body: await recorded("planned-package-rural-roads.json") } } });
  await expect(page).toHaveURL(PACKAGE);
  const planned = {
    what: await chipTexts(page, "What is being bought"),
    where: await chipTexts(page, "Where the package is"),
    how: await chipTexts(page, "How it will be procured"),
  };

  await page.locator("nav").getByRole("link", { name: "Packages", exact: true }).first().click();
  await expect(page).toHaveURL("/packages");
  const table = page.locator("[data-packages-page=ready] table");
  await expect(page.getByText("You have three packages in progress and one checked plan.")).toBeVisible();
  await expect(table.locator("tbody tr")).toHaveCount(4);
  const plan = table.locator("tbody tr").nth(3);
  await expect(plan).toContainText("Northern Water Works Development Agency, plan of October 9, 2026");
  await expect(plan).toContainText("Nine activities checked.");
  await expect(plan).toContainText("Plan check");
  await expect(plan).toContainText("Kenya");
  const mine = table.locator("tbody tr").nth(2);
  await expect(mine).toContainText("No STEP reference yet. One guess to check.");
  await mine.getByRole("link", { name: "Rural roads, Kenya" }).click();

  await expect(page).toHaveURL(PACKAGE);
  await expect(page.locator("[data-planned-package=ready]")).toBeVisible();
  expect({
    what: await chipTexts(page, "What is being bought"),
    where: await chipTexts(page, "Where the package is"),
    how: await chipTexts(page, "How it will be procured"),
  }).toEqual(planned);
});

test("the Packages tab's buttons put the one box into plan mode or check mode and move focus there", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await serve(page, {
    "GET /api/planned-packages": { body: await recorded("planned-packages-empty.json") },
    "/api/projects/P156634": { body: await recorded("project-p156634.json") },
  });
  await page.goto("/packages");
  await expect(page.getByText("You have no packages or checked plans yet.")).toBeVisible();

  await page.getByRole("button", { name: "Plan a package" }).click();
  await expect(box(page)).toBeFocused();
  await expect(page.locator("[data-box-band] [data-placeholder]")).toHaveText("Describe the package in one sentence");
  await page.keyboard.type(SENTENCE);
  await expect(options(page).first()).toHaveAccessibleName(/^Plan a package from this sentence/);
  await expect(options(page).first()).toHaveAttribute("aria-selected", "true");
  await page.keyboard.press("Escape");
  await page.keyboard.press("Escape");

  await page.getByRole("button", { name: "Check a plan" }).click();
  await expect(box(page)).toBeFocused();
  await expect(page.locator("[data-box-band] [data-placeholder]")).toHaveText("Type a project ID, such as P156634");
  await page.keyboard.type("P156634");
  await expect(options(page).first()).toHaveAccessibleName(/^Check the Northern Water Works Development Agency plan of October 9, 2026/);
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL("/projects/P156634/procurement/northern-water-works-development-agency");
});

test("the Packages tab says when it could not load, and a preview holds its buttons with the reason", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await serve(page, { "GET /api/planned-packages": { status: 503, body: '{"code":"data_service","trace_id":"t-1"}' } });
  await page.goto("/packages");
  await expect(page.getByText("I couldn't load your packages and checked plans just now. Try again in a moment.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Try again" })).toBeVisible();

  await page.goto("/packages?view=piu");
  await expect(page.getByText("Checking and planning are off in a preview.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Check a plan" })).toHaveAttribute("aria-disabled", "true");
  await expect(page.getByRole("button", { name: "Plan a package" })).toHaveAttribute("aria-disabled", "true");
});

test("a package someone else saved, or that does not exist, says so and links to the Packages tab", async ({ page }) => {
  await openPackage(page, { path: "/packages/pkg-00000000000a", answers: { "GET /api/planned-packages/pkg-00000000000a": { status: 404, body: await recorded("planned-package-not-found.json") } } });

  await expect(page.locator("[data-planned-package=not-found]")).toBeVisible();
  await expect(page.getByText("I can't find this package. It may have been removed, or it was saved by someone else.")).toBeVisible();
  await expect(page.getByRole("link", { name: "Go to Packages" })).toHaveAttribute("href", "/packages");
});

test("in the public view the workspace and the Packages tab are not offered", async ({ page }) => {
  await openPackage(page, { path: `${PACKAGE}?view=public` });

  await expect(page.locator("[data-planned-package=public]")).toBeVisible();
  await expect(page.getByText("Packages are not part of the public view.")).toBeVisible();
  await expect(page.getByRole("link", { name: "Go to Projects" })).toHaveAttribute("href", "/projects");
});

test("in an implementing agency preview the chips open read-only editors and nothing is saved", async ({ page }) => {
  await openPackage(page, { path: `${PACKAGE}?view=piu` });
  const sent = await changes(page);

  await expect(page.locator("[data-saved-stamp]")).toHaveText("Changes are off in a preview");
  await chip(page, "method").click();
  const editor = page.getByRole("dialog", { name: "Method" });
  await expect(editor).toContainText("Changes are off in a preview.");
  await expect(editor.getByRole("radio")).toHaveCount(0);
  await page.keyboard.press("Escape");
  await expect(page.locator("[data-plan-prompt]").getByRole("textbox")).toBeDisabled();
  expect(sent).toEqual([]);
});

// ── Accessibility at each width ──────────────────────────────────────────

const noSideScroll = (page: Page) => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth);

for (const width of [1440, 1024, 390]) {
  test(`at ${width} px axe finds no WCAG 2.2 AA violations on the workspace, a chip's editor, the drawer and the Packages tab`, async ({ page }) => {
    await openChart(page, width);
    expect(await axe(page), "the chart").toEqual([]);
    expect(await noSideScroll(page)).toBe(true);

    await chip(page, "method").click();
    const editor = page.getByRole("dialog", { name: "Method" });
    await expect(editor).toBeVisible();
    // Below 768 px the editor is a bottom sheet over a scrim, with a 44 px close button.
    await expect(editor).toHaveAttribute("data-chip-editor", width < 768 ? "sheet" : "popover");
    if (width < 768) {
      expect(Math.round((await editor.getByRole("button", { name: "Close" }).boundingBox())!.height)).toBeGreaterThanOrEqual(44);
      await expect(editor).toHaveAttribute("aria-modal", "true");
    }
    expect(await axe(page), "the method editor").toEqual([]);
    await page.keyboard.press("Escape");
    await expect(editor).toHaveCount(0);
    await expect(chip(page, "method")).toBeFocused();

    await page.getByRole("button", { name: "Show the table" }).click();
    await page.locator(`[data-open-row="${MOWI}"]:visible`).click();
    await expect(drawer(page)).toBeVisible();
    await expect(drawer(page)).toHaveAttribute("data-evidence-drawer", width < 768 ? "sheet" : "drawer");
    expect(await axe(page), "the drawer").toEqual([]);
    await page.keyboard.press("Escape");

    await serve(page, { "GET /api/planned-packages": { body: await recorded("planned-packages-list.json") } });
    await page.goto("/packages");
    await expect(page.locator("[data-packages-page=ready]")).toBeVisible();
    expect(await axe(page), "the Packages tab").toEqual([]);
    expect(await noSideScroll(page)).toBe(true);
  });
}

test("at 320 px the workspace and the Packages tab reflow with no sideways scroll, and the header scrolls with the page", async ({ page }) => {
  await openPackage(page, { width: 320 });
  expect(await noSideScroll(page)).toBe(true);
  expect(await page.locator("[data-package-header]").evaluate((element) => getComputedStyle(element).position)).toBe("static");
  for (const key of ["procurement_process", "market_approach"]) {
    const [box, column] = [(await chip(page, key).boundingBox())!, (await card(page).boundingBox())!];
    expect(box.x + box.width, key).toBeLessThanOrEqual(column.x + column.width);
  }
  await page.goto("/packages");
  await serve(page, { "GET /api/planned-packages": { body: await recorded("planned-packages-list.json") } });
  await page.reload();
  await expect(page.locator("[data-packages-page=ready]")).toBeVisible();
  expect(await noSideScroll(page)).toBe(true);
});

test("in a preview the box lists the plan option disabled with its reason, and the public view does not offer it", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  const asked = await serve(page, {});
  await page.goto("/?view=piu");
  await page.keyboard.press("/");
  await page.keyboard.type(SENTENCE);

  const plan = options(page).nth(1);
  await expect(plan).toHaveAccessibleName("Plan a package from this sentence Planning a package is off in a preview.");
  await expect(plan).toHaveAttribute("aria-disabled", "true");
  await plan.click({ force: true });
  await page.keyboard.press("ArrowDown");
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL("/?view=piu");
  expect(asked.filter((request) => new URL(request.url()).pathname.startsWith("/api/planned-packages"))).toEqual([]);

  await page.goto("/?view=public");
  await page.keyboard.press("/");
  await page.keyboard.type(SENTENCE);
  await expect(options(page)).toHaveCount(1);
  await expect(options(page).first()).toHaveAccessibleName(/^Ask this/);
});

test("in a list of choices the arrow keys move between options without choosing, and Enter or Space chooses", async ({ page }) => {
  await openPackage(page);
  const sent = await changes(page);

  await chip(page, "method").focus();
  await page.keyboard.press("Enter");
  const editor = page.getByRole("dialog", { name: "Method" });
  await editor.getByRole("radio", { name: "Request for Bids (RFB)" }).focus();
  await page.keyboard.press("ArrowDown");

  await expect(editor.getByRole("radio", { name: "Request for Quotations (RFQ)" })).toBeFocused();
  await expect(editor).toBeVisible();
  expect(sent).toEqual([]);
  await page.keyboard.press("Enter");
  await expect(editor).toHaveCount(0);
  await expect.poll(() => sent).toEqual([{ field: "method", action: "set", value: "Request for Quotations" }]);
  await expect(chip(page, "method")).toBeFocused();
});
