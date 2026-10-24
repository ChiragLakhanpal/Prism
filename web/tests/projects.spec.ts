// All projects and a project's page (ticket 10) at seam 4, against the responses recorded from the
// project routes in tests/fixtures/api, which the server tests check the server against. The values
// are the projects API's record for P156634 and P130164 and the documents API's list of P156634's
// Procurement Plans; the words are the 10 design brief's.
import AxeBuilder from "@axe-core/playwright";
import type { Page } from "@playwright/test";
import { expect, mockApi, recorded, test } from "./mocked";

const WCAG_22_AA = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];
type Answer = { status?: number; body: string };

async function open(page: Page, path: string, api: Record<string, Answer>, width = 1440) {
  await page.setViewportSize({ width, height: 900 });
  const unrecorded = await mockApi(page, {
    "/api/me": { body: await recorded("me.json") },
    "/api/freshness": { body: await recorded("freshness.json") },
    ...api,
  });
  await page.goto(path);
  return unrecorded;
}

async function axe(page: Page) {
  const results = await new AxeBuilder({ page }).withTags(WCAG_22_AA).analyze();
  return results.violations.map((v) => `${v.id}: ${v.nodes.map((node) => node.target.join(" ")).join(", ")}`);
}

const projects = async () => ({ "/api/projects": { body: await recorded("projects.json") } });
const p156634 = async () => ({ "/api/projects/P156634": { body: await recorded("project-p156634.json") } });

test("All projects lists 50 projects whose IDs link to their pages, and Show 50 more adds the rest", async ({ page }) => {
  const unrecorded = await open(page, "/projects", await projects());
  const main = page.getByRole("main");

  await expect(main.getByRole("heading", { level: 1 })).toHaveText("Projects");
  await expect(main.getByText("These are the projects I have records for. Open a project ID to see its Procurement Plans.")).toBeVisible();
  await expect(main.getByRole("heading", { level: 2, name: "All projects" })).toBeVisible();
  const table = main.locator("[data-table-view=table] tbody tr");
  await expect(table).toHaveCount(50);
  await expect(main.getByText("Showing 1–50 of 92 projects")).toBeVisible();
  await expect(main.locator("[data-table-view=table]").getByRole("link", { name: "P156634" })).toHaveAttribute("href", "/projects/P156634");
  await expect(main.getByText("Source: World Bank projects API, records through October 23, 2026.")).toBeVisible();

  await main.getByRole("button", { name: "Show 50 more" }).click();

  await expect(table).toHaveCount(92);
  await expect(main.getByText("Showing all 92 projects")).toBeVisible();
  await expect(main.locator("[data-table-view=table] [data-row='50']")).toBeFocused();
  await expect(main.getByRole("button", { name: "Show 50 more" })).toHaveCount(0);
  expect(unrecorded).toEqual([]);
});

test("All projects' skeleton rows are as tall as its rows, so the page does not jump when they arrive", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await mockApi(page, { "/api/me": { body: await recorded("me.json") }, "/api/freshness": { body: await recorded("freshness.json") } });
  let release!: () => void;
  const held = new Promise<void>((resolve) => (release = resolve));
  await page.route("**/api/projects", async (route) => {
    await held;
    await route.fulfill({ status: 200, contentType: "application/json", body: await recorded("projects.json") });
  });
  await page.goto("/projects");
  await page.evaluate(() => document.fonts.ready);
  const firstRow = page.locator("[data-table-view=table] tbody tr").first();
  const height = () => firstRow.evaluate((row) => row.getBoundingClientRect().height);
  await expect(page.locator("[data-projects-page=loading]")).toBeVisible();
  const loading = await height();
  await page.setViewportSize({ width: 390, height: 900 });
  expect(await axe(page), "loading at 390 px").toEqual([]);
  await page.setViewportSize({ width: 1440, height: 900 });

  release();
  await expect(page.locator("[data-projects-page=ready]")).toBeVisible();

  expect(Math.abs((await height()) - loading)).toBeLessThanOrEqual(1);
});

test("All projects says when it holds no records, and when the data service didn't answer", async ({ page }) => {
  await open(page, "/projects", { "/api/projects": { body: '{"as_of":"2026-10-23","total":0,"rows":[],"records_through":null}' } });
  await expect(page.locator("[data-empty-state]")).toContainText("I don't have any project records yet.");
  await expect(page.locator("[data-empty-state]").getByRole("link", { name: "Data readiness" })).toHaveAttribute("href", "/data");
  expect(Math.round((await page.locator("[data-empty-state]").boundingBox())!.width)).toBe(853);
  await page.setViewportSize({ width: 390, height: 900 });
  expect(await axe(page), "empty at 390 px").toEqual([]);

  await open(page, "/projects", { "/api/projects": { status: 503, body: '{"code":"data_service","trace_id":"0af7651916cd43dd8448eb211c80319c"}' } });
  await expect(page.getByRole("alert")).toHaveText("I couldn't load the list of projects because the data service didn't answer.");
  await expect(page.getByRole("button", { name: "Try again" })).toBeVisible();
  // At 1440 px the alert holds columns 1 to 8, as on every other page.
  expect(Math.round((await page.getByRole("alert").boundingBox())!.width)).toBe(853);
  await page.setViewportSize({ width: 390, height: 900 });
  expect(await axe(page), "error at 390 px").toEqual([]);
});

test("a project's page shows its header, one Procurement tab, and each agency's plan versions newest first", async ({ page }) => {
  await open(page, "/projects/P156634", await p156634());
  const main = page.getByRole("main");

  await expect(main.getByRole("heading", { level: 1 })).toHaveText("Water and Sanitation Development Project");
  const header = main.locator("dl").first();
  await expect(header).toContainText("Project IDP156634");
  await expect(header).toContainText("CountryKenya");
  await expect(header).toContainText("StatusActive");
  await expect(header).toContainText("Implementing agencies");
  await expect(header).toContainText("Ministry of Water, Sanitation and Irrigation; Mombasa Water and Sanitation Services Company");
  const tabs = main.getByRole("navigation", { name: "Project sections" }).getByRole("link");
  await expect(tabs).toHaveText(["Procurement"]);
  await expect(tabs.first()).toHaveAttribute("aria-current", "page");
  await expect(page.getByRole("navigation", { name: "Main" }).locator("[aria-current=page]")).toHaveText("Projects");

  const nwwda = main.locator("[data-agency=northern-water-works-development-agency]");
  await expect(nwwda.getByRole("heading", { level: 3 })).toHaveText("Northern Water Works Development Agency");
  await expect(nwwda.getByText("Showing all 5 versions")).toBeVisible();
  await expect(nwwda.locator("[data-table-view=table] tbody th")).toHaveText([
    "Plan of Oct 9, 2026 Latest",
    "Plan of Mar 5, 2026",
    "Plan of Jul 21, 2025",
    "Plan of Apr 21, 2021",
    "Plan of Dec 7, 2020",
  ]);
  await expect(nwwda.locator("[data-table-view=table] tbody tr").first().locator("td")).toHaveText(["Oct 9, 2026", "9"]);
  await expect(main.locator("[data-agency=kilifi-mariakani-water-and-sewerage-company-ltd]").getByText("Showing 1 version")).toBeVisible();
  // The agencies with no plan share one block after the ones with plans, rather than ten alike.
  const others = main.locator("[data-other-agencies]");
  await expect(others.getByRole("heading", { level: 3 })).toHaveText("Other implementing agencies");
  await expect(others).toContainText("I don't have a Procurement Plan from these agencies yet:");
  await expect(others.getByRole("listitem")).toHaveCount(10);
  await expect(others.getByRole("listitem").filter({ hasText: "Water Sector Trust Fund" })).toHaveCount(1);
  await expect(main.getByRole("heading", { level: 3 })).toHaveCount(5);

  await nwwda.locator("[data-table-view=table]").getByRole("link", { name: "Plan of Oct 9, 2026" }).click();
  await expect(page).toHaveURL(/\/projects\/P156634\/procurement\/northern-water-works-development-agency\/2026-10-09$/);
});

// Opens a project's page with its read held until release() is called.
async function holdProject(page: Page, pid: string, file: string) {
  await page.setViewportSize({ width: 1440, height: 900 });
  await mockApi(page, { "/api/me": { body: await recorded("me.json") }, "/api/freshness": { body: await recorded("freshness.json") } });
  let release!: () => void;
  const held = new Promise<void>((resolve) => (release = resolve));
  await page.route(`**/api/projects/${pid}`, async (route) => {
    await held;
    await route.fulfill({ status: 200, contentType: "application/json", body: await recorded(file) });
  });
  await page.goto(`/projects/${pid}`);
  await expect(page.locator("[data-project-page=loading]")).toBeVisible();
  await page.evaluate(() => document.fonts.ready);
  return release;
}

// The section tabs' top at each width, measured on the page as it stands.
async function tabTops(page: Page, widths: number[]) {
  const tabs = page.getByRole("navigation", { name: "Project sections" });
  const tops: Record<number, number> = {};
  for (const width of widths) {
    await page.setViewportSize({ width, height: 900 });
    tops[width] = await tabs.evaluate((element) => element.getBoundingClientRect().top + window.scrollY);
  }
  return tops;
}

test("while a project loads, its h1 and last crumb name it, and its section tabs stay where they are when it arrives", async ({ page }) => {
  const widths = [1440, 1024, 390];
  const release = await holdProject(page, "P156634", "project-p156634.json");
  // A route change focuses the h1, so it names the project while the bars stand in for its name.
  await expect(page.getByRole("main").getByRole("heading", { level: 1 })).toHaveText("Project P156634");
  await expect(page.getByRole("navigation", { name: "Breadcrumb" }).locator("[aria-current=page]")).toHaveText("Project P156634");
  const loading = await tabTops(page, widths);
  expect(await axe(page), "loading at 390 px").toEqual([]);

  release();
  await expect(page.locator("[data-project-page=ready]")).toBeVisible();

  const ready = await tabTops(page, widths);
  for (const width of widths) expect(Math.abs(ready[width] - loading[width]), `${width} px`).toBeLessThanOrEqual(1);
});

test("a project whose agencies fit on one line moves its tabs up when it arrives, never down", async ({ page }) => {
  // The skeleton keeps the place of two lines of agencies and "Show all agencies", which a project
  // with one agency does not need (DESIGN.md section 5, Project header).
  const widths = [1440, 390];
  const release = await holdProject(page, "P130164", "project-p130164.json");
  const loading = await tabTops(page, widths);

  release();
  await expect(page.locator("[data-project-page=ready]")).toBeVisible();

  const ready = await tabTops(page, widths);
  for (const width of widths) expect(ready[width], `${width} px`).toBeLessThanOrEqual(loading[width] + 1);
});

test("a long list of implementing agencies keeps to two lines until you show them all", async ({ page }) => {
  await open(page, "/projects/P156634", await p156634());
  const show = page.getByRole("button", { name: "Show all agencies" });
  await expect(show).toHaveAttribute("aria-expanded", "false");
  // On the page background a ghost button hovers to tint, as "Show them" does, so it answers the pointer.
  await show.hover();
  await expect.poll(() => show.evaluate((element) => getComputedStyle(element).backgroundColor)).toBe("rgb(233, 247, 253)");
  const agencies = page.locator(`[id="${await show.getAttribute("aria-controls")}"]`);
  await expect(agencies).toContainText("Ministry of Water, Sanitation and Irrigation; Mombasa Water and Sanitation Services Company");
  const lineHeight = await agencies.evaluate((element) => parseFloat(getComputedStyle(element).lineHeight));
  expect(await agencies.evaluate((element) => element.clientHeight)).toBeLessThanOrEqual(2 * lineHeight + 1);

  await show.click();

  const fewer = page.getByRole("button", { name: "Show fewer agencies" });
  await expect(fewer).toHaveAttribute("aria-expanded", "true");
  await expect(fewer).toBeFocused();
  expect(await agencies.evaluate((element) => element.clientHeight)).toBeGreaterThan(2 * lineHeight + 1);

  // One agency fits on a line, so there is nothing to show.
  await open(page, "/projects/P130164", { "/api/projects/P130164": { body: await recorded("project-p130164.json") } });
  await expect(page.locator("[data-project-page=ready]")).toBeVisible();
  await expect(page.getByRole("button", { name: "Show all agencies" })).toHaveCount(0);
});

test("a project's page says when the data service didn't answer, and when your account can't read Strata's tables", async ({ page }) => {
  const api = (answer: Answer) => ({ "/api/projects/P156634": answer });
  await open(page, "/projects/P156634", api({ status: 503, body: '{"code":"data_service","trace_id":"0af7651916cd43dd8448eb211c80319c"}' }), 1100);
  await expect(page.getByRole("alert")).toHaveText("I couldn't load this project's Procurement Plans because the data service didn't answer.");
  await expect(page.getByRole("button", { name: "Try again" })).toBeVisible();
  // From 1024 px the alert holds columns 1 to 8, as on every other page: at 1100 px, 8 columns of
  // 50.33 px and 7 gutters of 32 px.
  expect(Math.round((await page.getByRole("alert").boundingBox())!.width)).toBe(627);
  await page.setViewportSize({ width: 390, height: 900 });
  expect(await axe(page), "error at 390 px").toEqual([]);

  await page.unrouteAll({ behavior: "ignoreErrors" });
  await open(page, "/projects/P156634", api({ status: 403, body: '{"code":"permission"}' }), 390);
  await expect(page.getByRole("alert")).toHaveText("Your account can't read Strata's tables, so I can't show this project.");
  await expect(page.getByText("Ask your workspace admin for read access to the strata catalog.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Try again" })).toHaveCount(0);
  expect(await axe(page), "permission at 390 px").toEqual([]);
});

test("an agency's count line states the route's count of its versions", async ({ page }) => {
  const body = JSON.parse(await recorded("project-p156634.json"));
  body.agencies[0].version_count = 7;
  await open(page, "/projects/P156634", { "/api/projects/P156634": { body: JSON.stringify(body) } });

  await expect(page.locator("[data-agency=northern-water-works-development-agency]").getByText("Showing all 7 versions")).toBeVisible();
});

test("a project with no plans says so, and a project with no record is not found", async ({ page }) => {
  await open(page, "/projects/P130164/procurement", { "/api/projects/P130164": { body: await recorded("project-p130164.json") } });
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Rajasthan Road Sector Modernization Project");
  await expect(page.locator("[data-empty-state]")).toContainText("I don't have a Procurement Plan for this project yet.");
  await page.setViewportSize({ width: 390, height: 900 });
  expect(await axe(page), "no plans at 390 px").toEqual([]);

  await open(page, "/projects/P999999", { "/api/projects/P999999": { status: 404, body: '{"code":"unknown_project"}' } });
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("I don't have a project with the ID P999999.");
  await expect(page.getByRole("main").getByRole("link", { name: "All projects" })).toHaveAttribute("href", "/projects");
  // You are not on Projects, so the trail links to it and names the ID you asked for.
  const trail = page.getByRole("navigation", { name: "Breadcrumb" });
  await expect(trail.getByRole("link", { name: "Projects" })).toHaveAttribute("href", "/projects");
  await expect(trail.locator("[aria-current=page]")).toHaveText("Project P999999");
  await page.setViewportSize({ width: 390, height: 900 });
  expect(await axe(page), "not found at 390 px").toEqual([]);
});

// The tables a reader can see that scroll sideways inside their frame, which hides a column.
const scrollingTables = (page: Page) =>
  page.locator("[data-table-view=table], [data-view=table]").evaluateAll((frames) =>
    frames
      .filter((frame) => frame.getClientRects().length > 0 && frame.scrollWidth > frame.clientWidth)
      .map((frame) => frame.closest("[data-agency]")?.getAttribute("data-agency") ?? frame.getAttribute("data-view") ?? "table"),
  );

test("from 1024 to 1200 px every table fits its frame, so no column hides behind a sideways scroll", async ({ page }) => {
  const cases: [string, Record<string, Answer>][] = [
    ["/projects", await projects()],
    ["/projects/P156634", await p156634()],
    ["/projects/P156634/procurement/northern-water-works-development-agency/2026-10-09", {
      "/api/projects/P156634/procurement/northern-water-works-development-agency/2026-10-09": { body: await recorded("check-plan-p156634-nwwda-2026-10-09.json") },
    }],
  ];
  for (const [path, api] of cases) {
    await page.unrouteAll({ behavior: "ignoreErrors" });
    await open(page, path, api, 1024);
    await expect(page.locator("[data-projects-page=ready], [data-project-page=ready], [data-check-plan-page=ready]")).toBeVisible();
    for (const width of [1024, 1100, 1199, 1200]) {
      await page.setViewportSize({ width, height: 900 });
      expect(await scrollingTables(page), `${path} at ${width} px`).toEqual([]);
    }
  }
});

test("axe finds no WCAG 2.2 AA violations on All projects and a project's page at 1440 and 390 px, and they reflow at 320 px", async ({ page }) => {
  // The populated pages hold every component these pages use. The tests above run axe at 390 px on
  // each other state: loading, empty, no plans, not found, the service error and the permission error.
  const cases: [string, Record<string, Answer>][] = [
    ["/projects", await projects()],
    ["/projects/P156634", await p156634()],
  ];
  // Each page loads once and is resized through the widths, which keeps the axe runs quick.
  for (const [path, api] of cases) {
    await page.unrouteAll({ behavior: "ignoreErrors" });
    await open(page, path, api);
    for (const width of [1440, 390]) {
      await page.setViewportSize({ width, height: 900 });
      await expect(page.locator("[data-projects-page=ready], [data-project-page=ready], [data-project-page=not-found]")).toBeVisible();
      expect(await axe(page), `${path} at ${width} px`).toEqual([]);
    }
    await page.setViewportSize({ width: 320, height: 900 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth), `${path} at 320 px`).toBeLessThanOrEqual(320);
  }
});
