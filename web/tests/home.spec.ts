// Home (ticket 41; the 41 design brief), against the answers the server gave on tests/home_story.py's story
// (tests/record_home_api.py): Ana's Home with the examples the seed command set up for her, Ben's first run, a quiet
// window, the agency and public previews, and Home once both drafts are checked. The expected words come from the
// ticket, the wireframe and tests/ground_truth/values.toml, never from the copy file.
import type { Locator, Page } from "@playwright/test";
import { scan } from "./axe";
import { hubApi } from "./hub-api";
import { trailApi } from "./trail-api";
import { expect, mockApi, modelRoutes, recorded, test, viewAnswers } from "./mocked";

type Answer = { status?: number; body: string };
const NWWDA = "/projects/P156634/procurement/northern-water-works-development-agency";

async function file(name: string): Promise<Answer> {
  return { body: await recorded(name) };
}

async function homeApi(extra: Record<string, Answer> = {}): Promise<Record<string, Answer>> {
  return {
    ...(await viewAnswers()),
    "/api/me": await file("me-home.json"),
    "/api/freshness": await file("freshness.json"),
    "/api/home": await file("home.json"),
    ...extra,
  };
}

async function open(page: Page, path = "/", extra: Record<string, Answer> = {}, width = 1440, height = 900) {
  await page.setViewportSize({ width, height });
  const unrecorded = await mockApi(page, await homeApi(extra));
  await page.goto(path);
  await expect(page.locator("[data-home=ready]")).toBeVisible();
  return unrecorded;
}

const line = (page: Page, n: number) => page.locator("li[data-line-kind]").nth(n);

test("the briefing's counts equal the lines below it, kind by kind, and Home asks no model while it renders", async ({ page }) => {
  const { callsAModel } = await modelRoutes();
  const asked: string[] = [];
  page.on("request", (request) => {
    const url = new URL(request.url());
    if (url.pathname.startsWith("/api/")) asked.push(`${request.method()} ${url.pathname}`);
  });
  await open(page);

  const h1 = page.getByRole("heading", { level: 1 });
  await expect(h1).toContainText("Your briefing for Wednesday, October 28");
  await expect(h1).toContainText(
    "One plan changed in the past 15 days. One of its activities needs a look and two are worth watching. " +
      "One lesson cited in your drafts changed. Two drafts are waiting for you to check.",
  );
  const counted = async (kind: string) => Number(await page.locator(`[data-count-kind=${kind}]`).getAttribute("data-count"));
  expect(await counted("look")).toBe(await page.locator("li[data-line-kind=activity][data-line-status=needs_a_look]").count());
  expect(await counted("watch")).toBe(await page.locator("li[data-line-kind=activity][data-line-status=watch]").count());
  expect(await counted("lessonsChanged")).toBe(await page.locator("li[data-line-kind=lesson][data-line-status=changed]").count());
  expect(await counted("drafts")).toBe(await page.locator("[data-waiting] [data-draft-row]").count());
  expect([await counted("look"), await counted("watch"), await counted("lessonsChanged"), await counted("drafts")]).toEqual([1, 2, 1, 2]);
  await expect(page.getByRole("heading", { name: "Worth knowing", exact: true })).toBeVisible();

  // Home's one read, beside the shell's: nothing that calls a model.
  expect(asked.filter((request) => callsAModel(request.split(" ")[0], request.split(" ")[1]))).toEqual([]);
  expect(asked.filter((request) => request.includes("/api/home"))).toEqual(["GET /api/home"]);
});

// Ticket 98 (DESIGN.md section 3's type scale and section 1, principle 6): the date line in label (13/16, 600), the
// briefing's sentences in the finding style (28/36 Light, 24/32 below 48rem), and a first run's sentences, which report
// a state, in lead (18/28, 400).
const typeOf = (element: Locator) =>
  element.evaluate((found) => {
    const style = getComputedStyle(found);
    return `${style.fontSize}/${style.lineHeight} ${style.fontWeight}`;
  });

// The bottom of the element, from the top of the page, and the top of the box floating at the window's foot.
const bottomOf = (element: Locator) => element.evaluate((found) => found.getBoundingClientRect().bottom + window.scrollY);
const boxTop = (page: Page) => page.locator("[data-box-slot] form").evaluate((form) => form.getBoundingClientRect().top + window.scrollY);

test("the h1 is the date line in label over the briefing in the finding style, inside the first screen at 390 by 844 and 1024 by 768, and a first run's sentences are in lead", async ({ page }) => {
  for (const [width, height, finding] of [[390, 844, "24px/32px 300"], [1024, 768, "28px/36px 300"]] as const) {
    await open(page, "/", {}, width, height);
    const h1 = page.locator("main h1");
    const at = `${width} by ${height}`;
    await expect(h1.locator("[data-date-line]"), at).toHaveText("Your briefing for Wednesday, October 28");
    expect(await typeOf(h1.locator("[data-date-line]")), at).toBe("13px/16px 600");
    expect(await typeOf(h1.locator("[data-finding]")), at).toBe(finding);
    await expect(h1.locator("[data-status-lead]"), at).toHaveCount(0);
    const end = await bottomOf(h1);
    expect(end, at).toBeLessThanOrEqual(height);
    expect(end, `${at}: the box at the window's foot covers none of it`).toBeLessThanOrEqual(await boxTop(page));
  }
  // Each count word still opens its window.
  await page.locator("[data-count-kind=watch] button").click();
  await expect(page.getByRole("dialog", { name: "Activities worth watching" }).getByRole("link")).toHaveText(["KE-NWWDA-229129-CW-RFB", "KE-NWWDA-541062-CW-RFQ"]);

  await open(page, "/", { "/api/home": await file("home-first-run.json") });
  const lead = page.locator("main h1 [data-status-lead]");
  await expect(lead).toHaveText("You don't follow any projects yet, so I have no plans to brief you on. No draft is waiting for you to check.");
  expect(await typeOf(lead)).toBe("18px/28px 400");
  await expect(page.locator("main h1 [data-finding]")).toHaveCount(0);
});

// What a person reaches with Tab in the page, in order: each stop's tag and its words.
const tabStops = (page: Page) =>
  page.locator("main").evaluate((main) =>
    Array.from(main.querySelectorAll<HTMLElement>("a[href], button:not([disabled]), [tabindex='0']"))
      .filter((stop) => stop.getClientRects().length > 0)
      .map((stop) => `${stop.tagName.toLowerCase()} ${(stop.getAttribute("aria-label") ?? stop.innerText).trim()}`),
  );
const box = async (element: Locator) => (await element.boundingBox())!;

test("Worth knowing is a panel with its tag, each line's verb at its first row's right; Start here's tag sits under its name; Waiting for you is the side panel from a frame of 75rem and follows Worth knowing, in one Tab order at every width", async ({ page }) => {
  await open(page);
  const worth = page.getByRole("region", { name: "Worth knowing", exact: true });
  await expect(worth).toHaveAttribute("data-zone", "panel");
  await expect(worth.locator("[data-zone-tag]")).toHaveText("Fixed checks, no model");
  await expect(worth.getByRole("heading", { level: 2 })).toHaveText("Worth knowing");
  await expect(page.locator("main")).not.toContainText("·");

  // Each line: its badge, its one verb at the first row's right, then its sentence, which ends in its marker.
  const lines = worth.locator("li[data-line-kind]");
  await expect(lines).toHaveCount(4);
  for (const line of await lines.all()) {
    const [badge, verb, row] = [await box(line.locator("[data-badge]")), await box(line.locator("[data-line-action]")), await box(line)];
    expect(Math.abs(verb.y + verb.height / 2 - (badge.y + badge.height / 2))).toBeLessThanOrEqual(4);
    expect(Math.abs(verb.x + verb.width - (row.x + row.width))).toBeLessThanOrEqual(2);
    expect(await line.locator("p").first().evaluate((p) => {
      let last: Element | null = p;
      while (last?.lastElementChild) last = last.lastElementChild;
      return last?.closest("[data-citation]") !== null && p.textContent!.trim().endsWith(last!.closest("[data-citation]")!.textContent!.trim());
    })).toBe(true);
  }

  const name = page.locator("[data-start-here=shown] [data-zone-name]");
  const tag = page.locator("[data-start-here=shown] [data-zone-tag]");
  await expect(tag).toHaveText("Examples Strata set up for you");
  const waiting = page.getByRole("region", { name: "Waiting for you", exact: true });
  await expect(waiting).toHaveAttribute("data-side-panel", "panel");
  // Each zone's and the side panel's name is an h2 in h2 type, 18/24 600 (routed from ticket 91's critique).
  for (const heading of [name, worth.getByRole("heading", { level: 2 }), waiting.getByRole("heading", { level: 2 })]) {
    expect(await typeOf(heading)).toBe("18px/24px 600");
  }

  let order: string[] | null = null;
  for (const width of [1440, 1280, 1024, 390]) {
    await page.setViewportSize({ width, height: 900 });
    const [w, s] = [await box(worth), await box(waiting)];
    if (width >= 1280) {
      // Beside the work, from the top of the page's head.
      expect(s.x, `${width} px`).toBeGreaterThan(w.x + w.width);
      expect(s.y, `${width} px`).toBeLessThan(w.y);
    } else {
      expect(s.y, `${width} px`).toBeGreaterThan(w.y + w.height);
      expect(Math.round(s.x), `${width} px`).toBe(Math.round(w.x));
    }
    if (width === 1440 || width === 390) {
      const [n, t] = [await box(name), await box(tag)];
      expect(t.y, `${width} px: the tag under the name`).toBeGreaterThanOrEqual(n.y + n.height - 1);
      expect(Math.round(t.x), `${width} px`).toBe(Math.round(n.x));
    }
    const stops = await tabStops(page);
    if (order === null) order = stops;
    else expect(stops, `${width} px`).toEqual(order);
  }
  // Tab from Worth knowing's last stop goes to Waiting for you's first.
  await page.setViewportSize({ width: 1440, height: 900 });
  await worth.locator("a[href], button").last().focus();
  await page.keyboard.press("Tab");
  await expect(waiting.getByRole("link").first()).toBeFocused();
});

// Ticket 98 (fairshare's strip, the redesign plan's section 9, pattern 6): an answer asked from Home opens in columns 1
// to 7 above the head, beside Waiting for you, and the briefing folds to its date line and first sentence in body.
test("with an answer open on Home the briefing shows only its date line and first sentence, Show the briefing unfolds the rest in place, and closing the answer unfolds it", async ({ page }) => {
  await open(page, "/", { "/api/ask": await file("ask-p130164-rebidding.sse"), "/api/evidence/opened": { body: '{"opened":[],"recorded":true}' } });
  const h1 = page.locator("main h1");
  const all =
    "One plan changed in the past 15 days. One of its activities needs a look and two are worth watching. " +
    "One lesson cited in your drafts changed. Two drafts are waiting for you to check.";
  await page.keyboard.press("/");
  await page.keyboard.type("Why were works contracts advertised again?");
  await page.keyboard.press("Enter");
  const answer = page.getByRole("region", { name: "Answer" });
  await expect(answer.locator("[data-answer]:not([data-answer=streaming])")).toBeVisible();

  // The answer takes the work's columns above the head, and Waiting for you stays beside it.
  const [panel, head, worth, waiting] = [await box(answer), await box(h1), await box(page.locator("[data-worth]")), await box(page.locator("[data-waiting]"))];
  expect(panel.y + panel.height).toBeLessThan(head.y);
  expect(Math.round(panel.x)).toBe(Math.round(worth.x));
  expect(Math.round(panel.width)).toBe(Math.round(worth.width));
  expect(waiting.x).toBeGreaterThan(panel.x + panel.width);
  expect(waiting.y).toBeLessThan(panel.y + panel.height);

  await expect(h1).toHaveText("Your briefing for Wednesday, October 28. One plan changed in the past 15 days.");
  expect(await typeOf(h1.locator("[data-sentences]"))).toBe("16px/24px 400");
  const show = page.getByRole("button", { name: "Show the briefing" });
  await expect(show).toHaveAttribute("aria-expanded", "false");
  await show.click();
  await expect(h1).toHaveText(`Your briefing for Wednesday, October 28. ${all}`);
  const hide = page.getByRole("button", { name: "Hide the briefing" });
  await expect(hide).toHaveAttribute("aria-expanded", "true");
  await expect(hide).toBeFocused();
  // The count words in the unfolded sentences still open their windows.
  await h1.locator("[data-count-kind=drafts] button").click();
  await expect(page.getByRole("dialog", { name: "Drafts waiting for you to check" }).getByRole("link")).toHaveCount(2);
  await page.keyboard.press("Escape");
  await hide.click();
  await expect(h1).toHaveText("Your briefing for Wednesday, October 28. One plan changed in the past 15 days.");
  expect((await scan(page, "[data-page-head]")).violations).toEqual([]);

  // Closing the answer unfolds the briefing, in the finding style again.
  await answer.getByRole("button", { name: "Close the answer" }).first().click();
  await expect(answer).toHaveCount(0);
  await expect(h1).toHaveText(`Your briefing for Wednesday, October 28. ${all}`);
  expect(await typeOf(h1.locator("[data-finding]"))).toBe("28px/36px 300");
  await expect(page.getByRole("button", { name: /the briefing$/ })).toHaveCount(0);
});

test("a failed load puts the error alert in the alert slot with Home as the h1, and Try again brings the briefing with focus on it", async ({ page }) => {
  let fail = true;
  await page.setViewportSize({ width: 1440, height: 900 });
  await mockApi(page, await homeApi());
  await page.route("**/api/home", async (route) =>
    fail
      ? route.fulfill({ status: 503, contentType: "application/json", body: '{"code":"data_service","trace_id":"0af7651916cd43dd8448eb211c80319c"}' })
      : route.fallback(),
  );
  await page.goto("/");
  await expect(page.locator("[data-alert-slot]")).toContainText("I couldn't load your briefing because the data service didn't answer.");
  await expect(page.locator("main h1")).toHaveText("Home");
  await expect(page.locator("main [data-zone], main [data-side-slot]")).toHaveCount(0);

  fail = false;
  await page.locator("[data-alert-slot]").getByRole("button", { name: "Try again" }).click();
  await expect(page.locator("[data-home=ready]")).toBeVisible();
  await expect(page.locator("main h1")).toBeFocused();
  await expect(page.locator("main h1 [data-date-line]")).toHaveText("Your briefing for Wednesday, October 28");
  await expect(page.locator("[data-alert-slot]")).not.toContainText("I couldn't load your briefing");
});

test("a count word opens what it counts, each a link to its line", async ({ page }) => {
  await open(page);
  await page.locator("[data-count-kind=watch] button").click();
  const window = page.getByRole("dialog", { name: "Activities worth watching" });

  await expect(window.getByRole("link")).toHaveText(["KE-NWWDA-229129-CW-RFB", "KE-NWWDA-541062-CW-RFQ"]);
  await expect(window.getByRole("link").first()).toHaveAttribute("href", "#line-activity-KE-NWWDA-229129-CW-RFB");
});

test("the first two lines are the wireframe's real lines from the NWWDA plan, and Open the activity lands on the activity's page", async ({ page }) => {
  await open(page, "/", { ...(await trailApi()) });

  await expect(line(page, 0)).toContainText(
    "KE-NWWDA-541055-CW-RFB, US$1.23 million of works in the Water and Sanitation Development Project (P156634), passed " +
      "its planned completion date of July 31, 2026 with no signed contract in the plan. The project closes October 31, 2026.",
  );
  await expect(line(page, 1)).toContainText(
    "In the same plan, KE-NWWDA-229129-CW-RFB was signed at US$1,245,092.76 against an estimate of US$300,000.",
  );
  await expect(line(page, 0).locator("[data-badge]")).toHaveText("Needs a look");
  await expect(line(page, 1).locator("[data-badge]")).toHaveText("Watch");
  const first = line(page, 0).getByRole("link", { name: "Open the activity KE-NWWDA-541055-CW-RFB" });
  await expect(first).toHaveAttribute("href", "/projects/P156634/packages/KE-NWWDA-541055-CW-RFB");

  await line(page, 1).getByRole("link", { name: "Open the activity KE-NWWDA-229129-CW-RFB" }).click();
  await expect(page).toHaveURL("/projects/P156634/packages/KE-NWWDA-229129-CW-RFB");
  await expect(page.locator("[data-activity-page=ready]")).toBeVisible();
  await expect(page.getByRole("main")).toContainText("KE-NWWDA-229129-CW-RFB");
});

test("each Start here link lands where it says", async ({ page }) => {
  const landings = {
    ...(await hubApi()),
    ...(await homeApi()),
    "/api/projects/P156634": await file("project-p156634.json"),
    [`/api${NWWDA}/2026-10-09`]: await file("check-plan-p156634-nwwda-2026-10-09.json"),
    [`/api${NWWDA}/2026-10-09/changes`]: await file("changes-nwwda-2026-10-09.json"),
    // The review notes the seed command set up for Ana on this plan, as the server names them to her.
    "/api/drafts/existing": await file("drafts-existing-example-review-notes.json"),
    "/api/planned-packages": await file("planned-packages-list.json"),
    "/api/examples/rural_roads_kenya": await file("example-rural-roads-kenya.json"),
    "/api/projects/P130164/timeline": await file("timeline-p130164.json"),
    "/api/lessons/me": await file("lessons-me-viewer.json"),
    "/api/lessons/page": await file("lessons-page.json"),
    "/api/data/readiness": await file("data-readiness.json"),
  };
  const strip = page.locator("[data-start-here=shown]");
  const follow = async (name: string) => {
    await page.goto("/");
    await expect(page.locator("[data-home=ready]")).toBeVisible();
    await strip.getByRole("link", { name }).click();
  };
  await page.setViewportSize({ width: 1440, height: 900 });
  await mockApi(page, landings);

  await follow("Check a published plan (P156634)");
  await expect(page).toHaveURL(`${NWWDA}/2026-10-09`);
  await expect(page.locator("[data-check-plan-page=ready]")).toBeVisible();
  // The notice names the seeded draft as Strata's example, never as one Ana started (the 41 brief, 5.12).
  const notice = page.locator("[data-existing-draft]");
  await expect(notice).toHaveText("I set up review notes on this plan for you as an example on October 28, 2026.");
  await expect(page.locator("[data-existing-draft-example] [data-tag]")).toHaveText("Example");

  await follow("Plan a package from a sentence");
  await expect(page).toHaveURL("/packages?box=plan&example=rural_roads_kenya");
  const box = page.getByRole("combobox");
  await expect(box).toHaveValue("rural roads, Kenya, about US$15 million");
  await expect(box).toBeFocused();

  await follow("See a project's whole story (P130164)");
  await expect(page).toHaveURL("/projects/P130164/timeline");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Rajasthan Road Sector Modernization");
  await expect(page.locator("[data-timeline=ready]")).toBeVisible();

  await follow("See a lesson change");
  await expect(page).toHaveURL("/lessons#notice-lesson-e903b07ad1-v1");
  await expect(page.locator("#notice-lesson-e903b07ad1-v1 h3")).toBeFocused();

  await follow("Check the data");
  await expect(page).toHaveURL("/data");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Data");

  await follow("See the public view");
  await expect(page).toHaveURL("/?view=public");
  await expect(page.locator("[data-worth=public]")).toBeVisible();
  await expect(page.locator("[data-start-here]")).toHaveCount(0);
});

test("Remove hides the strip with an undo row, and a later visit ends Home with the way to show it again", async ({ page }) => {
  let asked: unknown = null;
  await open(page);
  await page.route("**/api/home/start-here", async (route) => {
    asked = route.request().postDataJSON();
    const visible = (asked as { visible: boolean }).visible;
    return route.fulfill({ status: 200, contentType: "application/json", body: await recorded(visible ? "start-here-shown.json" : "start-here-removed.json") });
  });
  // Ticket 98: a Task zone row under the briefing, with Remove at the row's right.
  const strip = page.locator("[data-start-here=shown]");
  await expect(strip).toHaveAttribute("data-zone", "row");
  const remove = page.getByRole("button", { name: "Remove the Start here examples" });
  const [row, button] = [await box(strip), await box(remove)];
  expect(row.x + row.width - (button.x + button.width)).toBeLessThanOrEqual(24);
  expect(button.y - row.y).toBeLessThanOrEqual(16);

  await remove.click();

  expect(asked).toEqual({ visible: false, view: "staff" });
  await expect(strip).toHaveCount(0);
  await expect(page.getByText("You removed the examples Strata set up.")).toBeFocused();
  // The undo row brings the strip back in place, with focus on its name.
  await page.getByRole("button", { name: "Show the examples again" }).click();
  expect(asked).toEqual({ visible: true, view: "staff" });
  await expect(strip).toBeVisible();
  await expect(page.getByRole("heading", { name: "Start here", exact: true })).toBeFocused();

  // A later visit: the server says the strip stays hidden for this viewer.
  const home = JSON.parse(await recorded("home.json"));
  home.start_here.visible = false;
  const me = JSON.parse(await recorded("me-home.json"));
  me.start_here_visible = false;
  await open(page, "/", { "/api/home": { body: JSON.stringify(home) }, "/api/me": { body: JSON.stringify(me) } });
  await expect(page.locator("[data-start-here]")).toHaveCount(0);
  await expect(page.locator("[data-restore-line]")).toContainText("You removed the examples Strata set up.");

  // A viewer who is not World Bank staff never had the strip: the server sends no links, and Home never says they
  // removed it.
  home.start_here = { visible: false, links: [] };
  await open(page, "/", { "/api/home": { body: JSON.stringify(home) }, "/api/me": { body: JSON.stringify(me) } });
  await expect(page.locator("[data-start-here]")).toHaveCount(0);
  await expect(page.locator("[data-restore-line]")).toHaveCount(0);
});

test("Waiting for you lists the drafts to check with their progress, and shows its empty state once none remain", async ({ page }) => {
  await open(page);
  const waiting = page.locator("[data-waiting]");
  const rows = waiting.locator("[data-draft-row]");

  await expect(rows).toHaveCount(2);
  await expect(rows.nth(0)).toContainText("0 of 2 risk owners set.");
  await expect(rows.nth(0)).toContainText("Example");
  await expect(rows.nth(1)).toContainText("You opened 0 of 4 sources.");
  await expect(waiting).not.toContainText("approve");

  await open(page, "/", { "/api/home": await file("home-drafts-checked.json") });
  await expect(page.locator("[data-waiting] [data-draft-row]")).toHaveCount(0);
  await expect(page.locator("[data-waiting-empty]")).toContainText("No draft is waiting for you to check.");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("No draft is waiting for you to check.");
});

test("the agency preview and the public preview show the Home their column of the roles table describes", async ({ page }) => {
  await open(page, "/?view=piu");
  const h1 = page.getByRole("heading", { level: 1 });
  // The same shape as staff's Home (ticket 98): the date line, then the team's plan sentence in the finding style.
  await expect(h1.locator("[data-date-line]")).toHaveText("Your briefing for Wednesday, October 28");
  const finding = h1.locator("[data-finding]");
  await expect(finding).toContainText("I checked your team's latest Procurement Plan, the plan of October 9, 2026 for the Water and Sanitation Development Project (P156634).");
  await expect(finding).toContainText("Two of its activities are behind their planned dates.");
  expect(await typeOf(finding)).toBe("28px/36px 300");
  await page.locator("[data-count-kind=behind] button").click();
  await expect(page.getByRole("dialog", { name: "Activities behind their planned dates" }).getByRole("link")).toHaveText(["KE-NWWDA-541055-CW-RFB", "KE-NWWDA-541062-CW-RFQ"]);
  await page.keyboard.press("Escape");
  const worth = page.getByRole("region", { name: "Worth knowing", exact: true });
  await expect(worth.locator("[data-zone-tag]")).toHaveText("Fixed checks, no model");
  await expect(worth.locator("li[data-line-kind]")).toHaveCount(2);
  await expect(worth).toContainText("Your team's published Procurement Plans and project records from World Bank APIs");
  // Waiting for you holds only a sentence in a preview, so it is a row in the side column, after Worth knowing.
  const waiting = page.getByRole("region", { name: "Waiting for you", exact: true });
  await expect(waiting).toHaveAttribute("data-side-panel", "row");
  await expect(waiting).toContainText("In a preview I don't show an implementing agency's drafts");
  await expect(page.locator("[data-start-here]")).toHaveCount(0);
  await expect(page.locator("[data-check-my-plan]")).toHaveCount(0);

  // An officer's own Home: "Check my plan" in the strip's place.
  const own = JSON.parse(await recorded("home-preview-piu.json"));
  own.preview = false;
  own.waiting = { rows: [], total: 0, more: false, reason: null };
  await open(page, "/", { "/api/home": { body: JSON.stringify(own) } });
  await expect(page.getByRole("link", { name: "Check my plan before you submit an update" })).toHaveAttribute("href", "/packages/check");
  await expect(page.locator("[data-start-here]")).toHaveCount(0);

  // The public view (ticket 98): "Home" as the h1, its one sentence in lead, and "Closed projects" with its tag, no
  // middle dot and no side panel.
  await open(page, "/?view=public");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Home");
  const lead = page.locator("main [data-status-lead]");
  await expect(lead).toHaveCount(1);
  await expect(lead).toHaveText(
    "I hold records for 93 World Bank-financed projects. Search for one by name, project ID or country in the search box, " +
      "or start from the closed project below, the latest to close among those whose contracts I hold.",
  );
  expect(await typeOf(lead)).toBe("18px/28px 400");
  const projects = page.getByRole("region", { name: "Closed projects", exact: true });
  await expect(projects.getByRole("heading", { level: 2 })).toHaveText("Closed projects");
  await expect(projects.locator("[data-zone-tag]")).toHaveText("Contracts traced from public records");
  await expect(page.locator("main")).not.toContainText("·");
  await expect(page.locator("main [data-side-slot]")).toHaveCount(0);
  await expect(projects.getByRole("link", { name: "Find more projects" })).toHaveAttribute("href", "/projects");
  // The fixture's one closed project with contracts, P130164 (values.toml, counts.p130164_trail).
  const closed = page.locator("li[data-line-kind=public]");
  await expect(closed).toHaveCount(1);
  await expect(closed).toContainText(
    "The Rajasthan Road Sector Modernization Project (P130164) in India closed on December 31, 2018. I traced 1 of its 8 " +
      "contracts from notice to signature.",
  );
  await expect(closed.getByRole("link", { name: "See its contracts Rajasthan Road Sector Modernization Project" })).toHaveAttribute(
    "href",
    "/projects/P130164/procurement#packages",
  );
  await expect(page.locator("[data-waiting]")).toHaveCount(0);
  await expect(page.locator("[data-start-here]")).toHaveCount(0);
  await expect(page).toHaveTitle("Home (public preview) | Strata");
});

test("a plan that changed with no activity marked never reads as no plan changed below the briefing", async ({ page }) => {
  await open(page, "/?asof=2025-03-25", { "/api/home": await file("home-nothing-marked.json") });

  await expect(page.getByRole("heading", { level: 1 })).toContainText("One plan changed in the 15 days to March 25, 2025.");
  const worth = page.locator("[data-worth=staff]");
  await expect(worth).not.toContainText("No plan changed");
  await expect(worth).toContainText("None of the activities in the plans that changed needs a look or is worth watching");
});

test("past eight lines the rest fold behind Show them, and the briefing's counts include the folded lines", async ({ page }) => {
  const home = JSON.parse(await recorded("home.json"));
  const watched = home.worth.lines.find((found: { status: string }) => found.status === "watch");
  const extra = Array.from({ length: 7 }, (_, index) => ({ ...watched, id: `${watched.id}-${index}`, key: `${watched.key}-${index}` }));
  home.worth.lines.splice(3, 0, ...extra);
  const count = home.briefing.sentences.flat().find((segment: { kind?: string }) => segment.kind === "watch");
  count.count = 9;
  count.word = "nine";
  count.ids = home.worth.lines.filter((found: { status: string }) => found.status === "watch").map((found: { id: string }) => found.id);
  await open(page, "/", { "/api/home": { body: JSON.stringify(home) } });

  const lines = page.locator("li[data-line-kind]");
  await expect(lines).toHaveCount(11);
  await expect(page.locator("li[data-line-kind]:visible")).toHaveCount(8);
  expect(Number(await page.locator("[data-count-kind=watch]").getAttribute("data-count"))).toBe(
    await page.locator("li[data-line-kind=activity][data-line-status=watch]").count(),
  );
  await page.getByRole("button", { name: "Show them" }).click();
  await expect(page.locator("li[data-line-kind]:visible")).toHaveCount(11);
});

test("each example the seed command set up is labeled Example where it is listed", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await mockApi(page, await homeApi({
    "/api/me": await file("me-staff.json"),
    "/api/following": await file("following-examples.json"),
    "/api/planned-packages": await file("planned-packages-examples.json"),
  }));
  await page.goto("/projects/following");
  await expect(page.locator("[data-following-view]:visible [data-tag]")).toHaveText(["Example", "Example"]);

  await page.goto("/packages");
  await expect(page.locator("[data-packages-page] [data-tag]:visible")).toHaveText(["Example"]);
});

test("the package workspace names the PPSD rows the seed command set up as an example", async ({ page }) => {
  const api = "/api/packages/KE-NWWDA-541055-CW-RFB";
  await page.setViewportSize({ width: 1440, height: 900 });
  await mockApi(page, await homeApi({
    "/api/me": await file("me-staff.json"),
    [api]: await file("package-ke-nwwda-541055.json"),
    [`${api}/comparables`]: await file("comparables-ke-nwwda-541055.json"),
    [`${api}/risks`]: await file("risks-ke-nwwda-541055-india-selected.json"),
    [`${api}/steps`]: await file("steps-ke-nwwda-541055.json"),
    [`${api}/risk-selection`]: await file("risks-selection-saved.json"),
    "/api/drafts/existing": await file("drafts-existing-example-ppsd-rows.json"),
  }));
  await page.goto("/packages/KE-NWWDA-541055-CW-RFB");

  await expect(page.locator("[data-existing-ppsd]")).toHaveText(
    "I set up suggested PPSD rows for this package for you as an example on October 28, 2026.",
  );
  await expect(page.locator("[data-existing-draft-example] [data-tag]")).toHaveText("Example");
});

// ── The budget on a throttled 3G profile ─────────────────────────────────

const FAST_3G = { latency: 562.5, download: (1.44 * 1024 * 1024) / 8, upload: (675 * 1024) / 8 };

async function throttle(page: Page, api: Record<string, Answer>) {
  const session = await page.context().newCDPSession(page);
  await session.send("Network.enable");
  await session.send("Network.emulateNetworkConditions", {
    offline: false,
    latency: FAST_3G.latency,
    downloadThroughput: FAST_3G.download,
    uploadThroughput: FAST_3G.upload,
  });
  await page.route("**/api/**", async (route) => {
    const answer = api[new URL(route.request().url()).pathname];
    if (!answer) return route.fallback();
    await new Promise((resolve) => setTimeout(resolve, FAST_3G.latency + (answer.body.length / FAST_3G.download) * 1000));
    return route.fulfill({ status: 200, contentType: "application/json", body: answer.body });
  });
}

test.describe(() => {
  test.use({ extraHTTPHeaders: {} });

  test("Home is one request of at most 15 KB, populated within 5 s cold and 2 s from another page on the throttled 3G profile", async ({ page }) => {
    expect(Buffer.byteLength(await recorded("home.json"))).toBeLessThanOrEqual(15 * 1024);
    const api = await homeApi({ "/api/data/readiness": await file("data-readiness.json") });

    // From another page: Data, then the logo back to Home.
    await mockApi(page, api);
    await page.goto("/data");
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("Data");
    await throttle(page, api);
    const started = Date.now();
    await page.getByRole("link", { name: "Strata", exact: true }).click();
    await expect(page.locator("[data-home=ready]")).toBeVisible({ timeout: 10_000 });
    const warm = Date.now() - started;
    expect(warm, "from another page, in ms").toBeLessThanOrEqual(2000);

    const cold = await page.context().newPage();
    await mockApi(cold, api);
    await throttle(cold, api);
    const coldStart = Date.now();
    await cold.goto("/");
    await expect(cold.locator("[data-home=ready]")).toBeVisible({ timeout: 15_000 });
    const coldTime = Date.now() - coldStart;
    test.info().annotations.push({ type: "timing", description: `from another page ${warm} ms, cold ${coldTime} ms` });
    expect(coldTime, "cold, in ms").toBeLessThanOrEqual(5000);
  });
});

test("axe finds no WCAG 2.2 AA violations on Home populated, on its first run and in a quiet window", async ({ page }) => {
  for (const home of ["home.json", "home-first-run.json", "home-quiet.json"]) {
    await open(page, "/", { "/api/home": await file(home) });
    expect((await scan(page)).violations, home).toEqual([]);
  }
  // A quiet window reports a state, so it takes lead too (ticket 98).
  await expect(page.locator("main h1 [data-status-lead]")).toContainText("Nothing changed in the plans of the one project you follow in the past 15 days.");
  // The block below words the window as the server did: the page picks no count word.
  await expect(page.locator("[data-worth=staff]")).toContainText(
    "No plan changed and no new signal came up in the past 15 days for the projects you follow.",
  );
});
