// All projects and a project's page (ticket 10) at seam 4, against the responses recorded from the
// project routes in tests/fixtures/api, which the server tests check the server against. The values
// are the projects API's record for P156634 and P130164 and the documents API's list of P156634's
// Procurement Plans; the words are the 10 design brief's.
import { scan } from "./axe";
import type { Page } from "@playwright/test";
import { expect, mockApi, recorded, test, windowBeside } from "./mocked";

type Answer = { status?: number; body: string };

async function open(page: Page, path: string, api: Record<string, Answer>, width = 1440) {
  await page.setViewportSize({ width, height: 900 });
  const unrecorded = await mockApi(page, {
    "/api/me": { body: await recorded("me.json") },
    "/api/freshness": { body: await recorded("freshness.json") },
    ...api,
  });
  await page.goto(path);
  // The answer has drawn the page: a measure taken from here reads rows, cards or an alert, never
  // the skeleton or nothing.
  const pages = ["data-projects-page", "data-project-page", "data-check-plan-page"];
  await expect(page.locator(`:is(${pages.map((name) => `[${name}]`).join(", ")}):not(${pages.map((name) => `[${name}=loading]`).join(", ")})`)).toBeVisible();
  return unrecorded;
}

async function axe(page: Page) {
  const results = await scan(page);
  return results.violations.map((v) => `${v.id}: ${v.nodes.map((node) => node.target.join(" ")).join(", ")}`);
}

const projects = async () => ({ "/api/projects": { body: await recorded("projects.json") } });
// All projects' Task zone (ticket 99), the page's one zone: a section named by its h2. The table's own scroll region
// carries the same name, so the zone is found by its mark and its name is checked.
const listZone = (page: Page) => page.getByRole("main").locator("section[data-zone]").and(page.getByRole("region", { name: "All projects" }));
// Ticket 21: a project's address opens its Summary, and the Procurement tab lists its Packages too.
const p156634 = async () => ({
  "/api/projects/P156634": { body: await recorded("project-p156634.json") },
  "/api/projects/P156634/summary": { body: await recorded("summary-p156634.json") },
  "/api/projects/P156634/packages": { body: await recorded("packages-p156634.json") },
});

test("All projects shows 20 projects a page with the range it shows, sets project IDs in Roboto Mono as links, and pages by address", async ({ page }) => {
  const unrecorded = await open(page, "/projects", {
    ...(await projects()),
    "/api/projects?page=2": { body: await recorded("projects-page-2.json") },
  });
  const main = page.getByRole("main");

  await expect(main.getByRole("heading", { level: 1 })).toHaveText("Projects");
  await expect(
    main.getByText("Find a World Bank-financed project by name, project ID or country, then open it to see its plans and documents."),
  ).toBeVisible();
  // Ticket 99: one panel named "All projects" holds the search, the count line, the table, the pages and the source in
  // its foot strip, in that order (DESIGN.md section 5, Task zone and Foot strip).
  const panel = listZone(page);
  await expect(panel).toHaveAttribute("data-zone", "panel");
  const parts = await panel.evaluate((zone) =>
    ["[data-list-search]", "[data-page-lead]", "[data-table-view=table]", "[data-pagination]", "[data-foot-strip]"].map((selector) => {
      const part = zone.querySelector(selector);
      return part ? Math.round(part.getBoundingClientRect().top) : null;
    }),
  );
  expect(parts.every((top) => top !== null), "every part in the panel").toBe(true);
  expect([...parts].sort((a, b) => a! - b!), "in order").toEqual(parts);
  const table = panel.locator("[data-table-view=table] tbody tr");
  await expect(table).toHaveCount(20);
  await expect(panel.locator("[data-page-lead]")).toHaveText("Showing 1 to 20 of 93 projects");
  const first = panel.locator("[data-table-view=table]").getByRole("link", { name: "P176704" });
  await expect(first).toHaveAttribute("href", "/projects/P176704");
  expect(await first.evaluate((el) => [getComputedStyle(el).fontFamily.split(",")[0], getComputedStyle(el).fontWeight])).toEqual(['"Roboto Mono"', "500"]);
  // Each P-code link is a 24 px box (WCAG 2.5.8), as the prototype draws it.
  for (const link of await panel.locator("[data-table-view=table] [data-project-id]").all()) {
    expect(Math.round((await link.boundingBox())!.height)).toBe(24);
  }
  await expect(panel.locator("[data-foot-strip]")).toHaveText("Source: World Bank projects API, records through October 23, 2026.");
  const pages = panel.getByRole("navigation", { name: "Pages of the project list" });
  await expect(pages.getByText("Page 1 of 5")).toBeVisible();
  // On the first page, Previous page keeps its place but is not there to press.
  await expect(pages.getByRole("link", { name: "Previous page" })).toHaveCount(0);
  // For a viewer who is not World Bank staff, Projects opens All projects, the one page under it in the sidebar.
  const nav = page.getByRole("navigation", { name: "Main" });
  await expect(nav.locator("[data-nav-item=projects]")).toHaveAttribute("href", "/projects");
  await expect(nav.locator("[data-sub-items=projects] a")).toHaveText(["All projects"]);

  await pages.getByRole("link", { name: "Next page" }).click();

  await expect(page).toHaveURL(/\/projects\?page=2$/);
  const countLine = main.locator("[data-page-lead]");
  await expect(countLine).toHaveText("Showing 21 to 40 of 93 projects");
  await expect(countLine).toBeFocused();
  await expect(table.first().getByRole("link")).toHaveText("P167814");
  await page.goBack();
  await expect(countLine).toHaveText("Showing 1 to 20 of 93 projects");
  expect(unrecorded).toEqual([]);
});

test("a project's name wraps in full however long, and the list turns to cards below a page area of 34rem", async ({ page }) => {
  // P180287's name is the fixture's longest, 104 characters (the redesign plan, 7.10): never cut, clamped or scrolled.
  await open(page, "/projects?page=2", { "/api/projects?page=2": { body: await recorded("projects-page-2.json") } });
  const name = "Second Program for Strengthening Governance for Enabling Service Delivery and Public Investment in Kenya";
  expect(name).toHaveLength(104);
  for (const [width, view] of [[1440, "table"], [1024, "table"], [544, "table"], [543, "cards"], [390, "cards"]] as const) {
    await page.setViewportSize({ width, height: 900 });
    // Below 1024 px the window is the page area, since the sidebar is the Menu sheet there.
    await expect(page.locator(`[data-table-view=${view}]`), `${width} px`).toBeVisible();
    await expect(page.locator(`[data-table-view=${view === "table" ? "cards" : "table"}]`), `${width} px`).toBeHidden();
    const cell = page.locator(`[data-table-view=${view}] [data-project-name=P180287]`);
    await expect(cell, `${width} px`).toHaveText(name);
    const fits = await cell.evaluate((element) => {
      const style = getComputedStyle(element);
      return {
        whole: element.scrollWidth <= element.clientWidth && element.scrollHeight <= element.clientHeight,
        clamp: style.webkitLineClamp,
        overflow: style.textOverflow,
        lines: Math.round(element.getBoundingClientRect().height / parseFloat(style.lineHeight)),
      };
    });
    expect([fits.whole, fits.clamp, fits.overflow], `${width} px`).toEqual([true, "none", "clip"]);
    if (width <= 1024) expect(fits.lines, `${width} px`).toBeGreaterThan(1);
  }
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
});

test("the list search filters on the server as you type, by name, project ID or country, and says when nothing matches", async ({ page }) => {
  const asked: string[] = [];
  page.on("request", (request) => {
    const url = new URL(request.url());
    if (url.pathname === "/api/projects") asked.push(url.search);
  });
  await open(page, "/projects", {
    ...(await projects()),
    "/api/projects?q=india": { body: await recorded("projects-india.json") },
    "/api/projects?q=atlantis": { body: await recorded("projects-no-match.json") },
  });
  const main = page.getByRole("main");
  const field = main.getByRole("searchbox", { name: "Search projects" });
  await expect(field).toHaveAccessibleDescription("Type part of a project's name, its project ID or its country.");
  await expect(field).not.toHaveAttribute("placeholder");

  await field.pressSequentially("india");

  await expect(main.locator("[data-page-lead]")).toHaveText("Showing 1 project");
  await expect(main.locator("[data-table-view=table] tbody tr")).toHaveCount(1);
  await expect(main.locator("[data-table-view=table]").getByRole("link", { name: "P130164" })).toBeVisible();
  // One request for the word, sent once typing stopped, and the address keeps the search in place.
  expect(asked).toEqual(["", "?q=india"]);
  await expect(page).toHaveURL(/\/projects\?q=india$/);
  await expect(field).toBeFocused();
  await expect(main.getByRole("navigation", { name: "Pages of the project list" })).toHaveCount(0);

  await field.fill("atlantis");
  await expectNoMatch(page);
  await expect(page.getByRole("status").filter({ hasText: "I found no projects that match your search." })).toHaveCount(1);

  // Escape empties the field and shows every project again.
  await field.press("Escape");
  await expect(field).toHaveValue("");
  await expect(main.locator("[data-page-lead]")).toHaveText("Showing 1 to 20 of 93 projects");
  await expect(page).toHaveURL(/\/projects$/);
});

// No match (ticket 99; the redesign plan, 7.10): the panel keeps its name, the search keeps the query, and the no-match
// sentence, its body and "Show all projects" take the list's place, with no count line, table or pages.
async function expectNoMatch(page: Page) {
  const panel = listZone(page);
  await expect(panel.getByRole("searchbox", { name: "Search projects" })).toHaveValue("atlantis");
  const none = panel.locator("[data-empty-state]");
  await expect(none.getByRole("heading")).toHaveText("I found no projects that match your search.");
  await expect(none).toContainText(
    "I search project names, project IDs and country names. Check the spelling, or search for the country by the name the World Bank uses, such as Türkiye.",
  );
  await expect(none.getByRole("link", { name: "Show all projects" })).toHaveAttribute("href", "/projects");
  await expect(panel.locator("[data-table], [data-page-lead], [data-pagination]")).toHaveCount(0);
  await expect(panel.locator("[data-foot-strip]")).toHaveText("Source: World Bank projects API, records through October 23, 2026.");
}

test("All projects opened on a search with no match keeps the query in the field and says what I search", async ({ page }) => {
  await open(page, "/projects?q=atlantis", { "/api/projects?q=atlantis": { body: await recorded("projects-no-match.json") } });
  await expectNoMatch(page);
  await page.getByRole("link", { name: "Show all projects" }).click();
  await expect(page).toHaveURL(/\/projects$/);
});

test("while a search waits on the server, the list keeps its rows at full contrast and says it is searching, with no axe violations", async ({ page }) => {
  // The 21 design review, round 2, B1: a fade to 60 percent dropped muted text under 4.5:1, so the
  // count line and aria-busy alone say the list is updating. Packages uses the same Table.
  const cases: [string, Record<string, Answer>, string, string, string][] = [
    ["/projects", await projects(), "/api/projects", "Search projects", "Searching projects."],
    ["/projects/P156634/procurement", await p156634(), "/api/projects/P156634/packages", "Search packages", "Searching packages."],
  ];
  for (const [path, api, list, name, searching] of cases) {
    await page.unrouteAll({ behavior: "ignoreErrors" });
    await open(page, path, api);
    // The search is never answered, so the list stays in its searching state.
    await page.route((url) => url.pathname === list && url.searchParams.has("q"), () => undefined);
    await page.getByRole("searchbox", { name }).fill("kenya");
    const table = page.locator("[aria-busy=true]").filter({ has: page.locator("[data-table-view=table]") });
    await expect(table).toBeVisible();
    await expect(table.getByText(searching)).toBeVisible();
    for (const width of [1440, 390]) {
      await page.setViewportSize({ width, height: 900 });
      for (const view of await page.locator("[data-table-view]").all()) {
        expect(await view.evaluate((element) => getComputedStyle(element).opacity), `${path} at ${width} px`).toBe("1");
      }
      expect(await axe(page), `${path} searching at ${width} px`).toEqual([]);
    }
  }
});

test("All projects' skeleton rows and cards are as tall as its rows and cards, so the page does not jump when they arrive", async ({ page }) => {
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
  // The first row from 768 px, the first card below it: its top on the page and its height. Most
  // project names take two lines below 1200 px and one from it.
  const widths = [1440, 1024, 390];
  const measure = async () => {
    const sizes: Record<number, { top: number; height: number }> = {};
    for (const width of widths) {
      await page.setViewportSize({ width, height: 900 });
      const first = page.locator(width < 768 ? "[data-table-view=cards] > li" : "[data-table-view=table] tbody tr").first();
      sizes[width] = await first.evaluate((element) => {
        const box = element.getBoundingClientRect();
        return { top: Math.round(box.top + window.scrollY), height: Math.round(box.height) };
      });
    }
    return sizes;
  };
  await expect(page.locator("[data-projects-page=loading]")).toBeVisible();
  const loading = await measure();
  expect(await axe(page), "loading at 390 px").toEqual([]);

  release();
  await expect(page.locator("[data-projects-page=ready]")).toBeVisible();

  const ready = await measure();
  for (const width of widths) {
    expect(Math.abs(ready[width].top - loading[width].top), `top at ${width} px`).toBeLessThanOrEqual(1);
    expect(Math.abs(ready[width].height - loading[width].height), `height at ${width} px`).toBeLessThanOrEqual(1);
  }
});

test("All projects says when it holds no records, and when the data service didn't answer", async ({ page }) => {
  // A 1440 px page area: beside the rail (tickets 92 and 110) the window is wider.
  // With no records at all, the zone holds only a sentence and one link, so it is a row on the page grey (DESIGN.md
  // section 1, principle 7), and there is nothing to search.
  await open(page, "/projects", { "/api/projects": { body: '{"as_of":"2026-10-23","total":0,"rows":[],"records_through":null}' } }, windowBeside(1440));
  const zone = listZone(page);
  await expect(zone).toHaveAttribute("data-zone", "row");
  await expect(zone).toContainText("I don't have any project records yet.");
  await expect(zone.getByRole("link", { name: "Data readiness" })).toHaveAttribute("href", "/data");
  await expect(zone.getByRole("searchbox")).toHaveCount(0);
  await page.setViewportSize({ width: 390, height: 900 });
  expect(await axe(page), "empty at 390 px").toEqual([]);

  // A failed load keeps the panel's name and its search, and the error alert takes the list's place.
  await open(page, "/projects", { "/api/projects": { status: 503, body: '{"code":"data_service","trace_id":"0af7651916cd43dd8448eb211c80319c"}' } }, windowBeside(1440));
  const panel = listZone(page);
  await expect(panel).toHaveAttribute("data-zone", "panel");
  await expect(panel.getByRole("searchbox", { name: "Search projects" })).toBeVisible();
  await expect(panel.getByRole("alert")).toHaveText("I couldn't load the list of projects because the data service didn't answer.");
  await expect(panel.getByRole("button", { name: "Try again" })).toBeVisible();
  await expect(panel.locator("[data-table], [data-page-lead], [data-pagination], [data-foot-strip]")).toHaveCount(0);
  await page.setViewportSize({ width: 390, height: 900 });
  expect(await axe(page), "error at 390 px").toEqual([]);
});

test("a project's Procurement tab shows each agency's plan versions newest first, under the header's one line", async ({ page }) => {
  await open(page, "/projects/P156634/procurement", await p156634());
  const main = page.getByRole("main");

  // Ticket 21: the header is the wireframe's one line, then the implementing agency line.
  await expect(main.getByRole("heading", { level: 1 })).toHaveText("Water and Sanitation Development · P156634 · Kenya · active");
  const agencies = main.locator("[data-agency-line]");
  await expect(agencies).toContainText("Implementing agencies: ");
  await expect(agencies).toContainText("Ministry of Water, Sanitation and Irrigation; Mombasa Water and Sanitation Services Company");
  const tabs = main.getByRole("navigation", { name: "Project sections" }).getByRole("link");
  await expect(tabs).toHaveText(["Summary", "Procurement", "Timeline", "Documents", "Connections"]);
  await expect(tabs.nth(1)).toHaveAttribute("aria-current", "page");
  await expect(page.getByRole("navigation", { name: "Main" }).locator("[aria-current]")).toHaveText("Projects");

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
  await expect(main.locator("[data-procurement-tab]").getByRole("heading", { level: 3 })).toHaveCount(5);

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
    // A page area of each width: beside the sidebar (ticket 92) the window is wider.
    await page.setViewportSize({ width: windowBeside(width), height: 900 });
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
  // A heading holds only phrasing content, so the bars inside it are spans, never a div.
  await expect(page.getByRole("main").locator("h1 div")).toHaveCount(0);
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

test("a long list of implementing agencies keeps to one line until you show them all", async ({ page }) => {
  // Ticket 99: one line, with "Show all agencies" after it on that line (DESIGN.md section 5, Project header).
  await open(page, "/projects/P156634", await p156634());
  const show = page.getByRole("button", { name: "Show all agencies" });
  await expect(show).toHaveAttribute("aria-expanded", "false");
  // On the page background a ghost button hovers to tint, as "Show them" does, so it answers the pointer.
  await show.hover();
  await expect.poll(() => show.evaluate((element) => getComputedStyle(element).backgroundColor)).toBe("rgb(233, 247, 253)");
  const agencies = page.locator(`[id="${await show.getAttribute("aria-controls")}"]`);
  await expect(agencies).toContainText("Ministry of Water, Sanitation and Irrigation; Mombasa Water and Sanitation Services Company");
  const lineHeight = await agencies.evaluate((element) => parseFloat(getComputedStyle(element).lineHeight));
  expect(await agencies.evaluate((element) => element.clientHeight)).toBeLessThanOrEqual(lineHeight + 1);

  await show.click();

  const fewer = page.getByRole("button", { name: "Show fewer agencies" });
  await expect(fewer).toHaveAttribute("aria-expanded", "true");
  await expect(fewer).toBeFocused();
  // Opened, every name shows, wrapping in full, and the button follows them.
  expect(await agencies.evaluate((element) => element.clientHeight)).toBeGreaterThan(2 * lineHeight + 1);
  expect(await agencies.evaluate((element) => element.scrollWidth <= element.clientWidth)).toBe(true);
  expect((await fewer.boundingBox())!.y).toBeGreaterThanOrEqual((await agencies.boundingBox())!.y + (await agencies.boundingBox())!.height - 1);

  // One agency fits on a line, so there is nothing to show.
  await open(page, "/projects/P130164", { "/api/projects/P130164": { body: await recorded("project-p130164.json") } });
  await expect(page.locator("[data-project-page=ready]")).toBeVisible();
  await expect(page.getByRole("button", { name: "Show all agencies" })).toHaveCount(0);
});

test("a project's page says when the data service didn't answer, and when your account can't read Strata's tables", async ({ page }) => {
  const api = (answer: Answer) => ({ "/api/projects/P156634": answer });
  await open(page, "/projects/P156634", api({ status: 503, body: '{"code":"data_service","trace_id":"0af7651916cd43dd8448eb211c80319c"}' }), windowBeside(1100));
  await expect(page.getByRole("alert")).toHaveText("I couldn't load this project because the data service didn't answer.");
  await expect(page.getByRole("button", { name: "Try again" })).toBeVisible();
  // From a 1024 px page area the alert holds columns 1 to 8, as on every other page: in a 1100 px page area (the
  // window less the rail, ticket 92) with the 1164 px window's 32 px margins (ticket 94), 8 columns of 57 px and 7
  // gutters of 32 px.
  expect(Math.round((await page.getByRole("alert").boundingBox())!.width)).toBe(680);
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
  body.agencies[0].shown_count = 7;
  await open(page, "/projects/P156634/procurement", { ...(await p156634()), "/api/projects/P156634": { body: JSON.stringify(body) } });

  await expect(page.locator("[data-agency=northern-water-works-development-agency]").getByText("Showing all 7 versions")).toBeVisible();
});

test("a project with no plans says so, and a project with no record is not found", async ({ page }) => {
  await open(page, "/projects/P130164/procurement", { "/api/projects/P130164": { body: await recorded("project-p130164.json") } });
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Rajasthan Road Sector Modernization · P130164 · India · closed");
  // With no plans there are no packages to list, so Packages says so in one sentence.
  await expect(page.locator("[data-packages=none]")).toContainText("I haven't read a Procurement Plan for this project yet, so I can't list its packages.");
  // P130164's Documents tab lists 15 Procurement Plans I haven't read, so the title says I haven't read one,
  // as the Packages line does, rather than that I have none (the 21 critique, round 3, item 7).
  await expect(page.locator("[data-empty-state] h3")).toHaveText("I haven't read a Procurement Plan for this project yet.");
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
    ["/projects/P156634/procurement", await p156634()],
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

test("below 768 px a card's short values sit side by side: a version's Disclosed and Activities, a project's Country and Status", async ({ page }) => {
  // The tops of the visible first card's fields, which share a row when they sit side by side.
  const fieldTops = async (selector: string) => {
    const card = page.locator(selector).first();
    await expect(card).toBeVisible();
    return card.locator("dl > div").evaluateAll((fields) => fields.map((field) => Math.round(field.getBoundingClientRect().top)));
  };
  await open(page, "/projects/P156634/procurement", await p156634(), 390);
  await expect(page.locator("[data-project-page=ready]")).toBeVisible();
  const disclosedAndActivities = await fieldTops("[data-agency=northern-water-works-development-agency] [data-table-view=cards] > li");
  expect(disclosedAndActivities).toHaveLength(2);
  expect(new Set(disclosedAndActivities).size).toBe(1);

  await page.unrouteAll({ behavior: "ignoreErrors" });
  await open(page, "/projects", await projects(), 390);
  await expect(page.locator("[data-projects-page=ready]")).toBeVisible();
  const countryAndStatus = await fieldTops("[data-table-view=cards] > li");
  expect(countryAndStatus).toHaveLength(2);
  expect(new Set(countryAndStatus).size).toBe(1);
});

test("axe finds no WCAG 2.2 AA violations on All projects and a project's page at 1440 and 390 px, and they reflow at 320 px", async ({ page }) => {
  // The populated pages hold every component these pages use. The tests above run axe at 390 px on
  // each other state: loading, empty, no plans, not found, the service error and the permission error.
  const cases: [string, Record<string, Answer>][] = [
    ["/projects", await projects()],
    ["/projects/P156634/procurement", await p156634()],
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
