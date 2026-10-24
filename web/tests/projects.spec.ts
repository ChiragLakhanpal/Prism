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

test("All projects says when it holds no records, and when the data service didn't answer", async ({ page }) => {
  await open(page, "/projects", { "/api/projects": { body: '{"as_of":"2026-10-23","total":0,"rows":[],"records_through":null}' } });
  await expect(page.locator("[data-empty-state]")).toContainText("I don't have any project records yet.");
  await expect(page.locator("[data-empty-state]").getByRole("link", { name: "Data readiness" })).toHaveAttribute("href", "/data");

  await open(page, "/projects", { "/api/projects": { status: 503, body: '{"code":"data_service","trace_id":"0af7651916cd43dd8448eb211c80319c"}' } });
  await expect(page.getByRole("alert")).toHaveText("I couldn't load the list of projects because the data service didn't answer.");
  await expect(page.getByRole("button", { name: "Try again" })).toBeVisible();
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
  await expect(main.locator("[data-agency=water-sector-trust-fund]")).toContainText("I don't have a Procurement Plan from this agency yet.");

  await nwwda.locator("[data-table-view=table]").getByRole("link", { name: "Plan of Oct 9, 2026" }).click();
  await expect(page).toHaveURL(/\/projects\/P156634\/procurement\/northern-water-works-development-agency\/2026-10-09$/);
});

test("a project with no plans says so, and a project with no record is not found", async ({ page }) => {
  await open(page, "/projects/P130164/procurement", { "/api/projects/P130164": { body: await recorded("project-p130164.json") } });
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Rajasthan Road Sector Modernization Project");
  await expect(page.locator("[data-empty-state]")).toContainText("I don't have a Procurement Plan for this project yet.");

  await open(page, "/projects/P999999", { "/api/projects/P999999": { status: 404, body: '{"code":"unknown_project"}' } });
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("I don't have a project with the ID P999999.");
  await expect(page.getByRole("main").getByRole("link", { name: "All projects" })).toHaveAttribute("href", "/projects");
});

test("axe finds no WCAG 2.2 AA violations on All projects and a project's page, which reflow at 320 px", async ({ page }) => {
  const cases: [string, Record<string, Answer>][] = [
    ["/projects", await projects()],
    ["/projects/P156634", await p156634()],
    ["/projects/P130164", { "/api/projects/P130164": { body: await recorded("project-p130164.json") } }],
    ["/projects/P999999", { "/api/projects/P999999": { status: 404, body: '{"code":"unknown_project"}' } }],
  ];
  for (const [path, api] of cases) {
    for (const width of [1440, 390]) {
      await open(page, path, api, width);
      await expect(page.locator("[data-projects-page=ready], [data-project-page=ready], [data-project-page=not-found]")).toBeVisible();
      expect(await axe(page), `${path} at ${width} px`).toEqual([]);
    }
    await page.setViewportSize({ width: 320, height: 900 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth), `${path} at 320 px`).toBeLessThanOrEqual(320);
  }
});
