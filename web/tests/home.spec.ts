// Home (ticket 41; the 41 design brief), against the answers the server gave on tests/home_story.py's story
// (tests/record_home_api.py): Ana's Home with the examples the seed command set up for her, Ben's first run, a quiet
// window, the agency and public previews, and Home once both drafts are checked. The expected words come from the
// ticket, the wireframe and tests/ground_truth/values.toml, never from the copy file.
import type { Page } from "@playwright/test";
import { scan } from "./axe";
import { hubApi } from "./hub-api";
import { trailApi } from "./trail-api";
import { expect, mockApi, recorded, test, viewAnswers } from "./mocked";

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

async function open(page: Page, path = "/", extra: Record<string, Answer> = {}, width = 1440) {
  await page.setViewportSize({ width, height: 900 });
  const unrecorded = await mockApi(page, await homeApi(extra));
  await page.goto(path);
  await expect(page.locator("[data-home=ready]")).toBeVisible();
  return unrecorded;
}

const line = (page: Page, n: number) => page.locator("li[data-line-kind]").nth(n);

test("the briefing's counts equal the lines below it, kind by kind, and Home asks no model while it renders", async ({ page }) => {
  const models: { method: string; path: string }[] = JSON.parse(await recorded("model-routes.json")).routes;
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
  await expect(page.getByRole("heading", { name: "Worth knowing · fixed checks, no model" })).toBeVisible();

  // Home's one read, beside the shell's: nothing that calls a model.
  const routes = models.map(({ method, path }) => new RegExp(`^${method} ${path.replace(/\{[^}]+\}/g, "[^/]+")}$`));
  expect(asked.filter((request) => routes.some((route) => route.test(request)))).toEqual([]);
  expect(asked.filter((request) => request.includes("/api/home"))).toEqual(["GET /api/home"]);
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
    return route.fulfill({ status: 200, contentType: "application/json", body: await recorded("start-here-removed.json") });
  });

  await page.getByRole("button", { name: "Remove the Start here examples" }).click();

  expect(asked).toEqual({ visible: false, view: "staff" });
  await expect(page.locator("[data-start-here=shown]")).toHaveCount(0);
  await expect(page.getByText("You removed the examples Strata set up.")).toBeFocused();
  await expect(page.getByRole("button", { name: "Show the examples again" })).toBeVisible();

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
  await expect(rows.nth(1)).toContainText("You opened 0 of 3 sources.");
  await expect(waiting).not.toContainText("approve");

  await open(page, "/", { "/api/home": await file("home-drafts-checked.json") });
  await expect(page.locator("[data-waiting] [data-draft-row]")).toHaveCount(0);
  await expect(page.locator("[data-waiting-empty]")).toContainText("No draft is waiting for you to check.");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("No draft is waiting for you to check.");
});

test("the agency preview and the public preview show the Home their column of the roles table describes", async ({ page }) => {
  await open(page, "/?view=piu");
  const h1 = page.getByRole("heading", { level: 1 });
  await expect(h1).toContainText("I checked your team's latest Procurement Plan, the plan of October 9, 2026 for the Water and Sanitation Development Project (P156634).");
  await expect(h1).toContainText("Two of its activities are behind their planned dates.");
  await expect(page.locator("li[data-line-kind]")).toHaveCount(2);
  await expect(page.locator("[data-waiting]")).toContainText("In a preview I don't show an implementing agency's drafts");
  await expect(page.locator("[data-start-here]")).toHaveCount(0);
  await expect(page.locator("[data-check-my-plan]")).toHaveCount(0);

  // An officer's own Home: "Check my plan" in the strip's place.
  const own = JSON.parse(await recorded("home-preview-piu.json"));
  own.preview = false;
  own.waiting = { rows: [], total: 0, more: false, reason: null };
  await open(page, "/", { "/api/home": { body: JSON.stringify(own) } });
  await expect(page.getByRole("link", { name: "Check my plan before you submit an update" })).toHaveAttribute("href", "/packages/check");
  await expect(page.locator("[data-start-here]")).toHaveCount(0);

  await open(page, "/?view=public");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("I hold records for 93 World Bank-financed projects.");
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
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Nothing changed in the plans of the one project you follow in the past 15 days.");
  // The block below words the window as the server did: the page picks no count word.
  await expect(page.locator("[data-worth=staff]")).toContainText(
    "No plan changed and no new signal came up in the past 15 days for the projects you follow.",
  );
});
