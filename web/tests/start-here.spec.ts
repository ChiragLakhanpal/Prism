// Start here goes with you (ticket 114): once Home has loaded for World Bank staff in their own view, the sidebar on
// every page shows "Start here", how many of the six examples the person followed, and the next one as a link. An
// example is done once the person follows it from Home's strip or from the sidebar; the browser keeps that, so a
// reload keeps it. The expected words come from the ticket, never from the copy file.
import type { Page } from "@playwright/test";
import { scan } from "./axe";
import { expect, mockApi, openSidebar, recorded, test, viewAnswers } from "./mocked";

type Answer = { status?: number; body: string };
const PLAN = "/projects/P156634/procurement/northern-water-works-development-agency/2026-10-09";

async function file(name: string): Promise<Answer> {
  return { body: await recorded(name) };
}

// Ana's Home with the examples the seed command set up for her (tests/record_home_api.py), and the pages her examples
// open that these tests land on.
async function startHereApi(extra: Record<string, Answer> = {}): Promise<Record<string, Answer>> {
  return {
    ...(await viewAnswers()),
    "/api/me": await file("me-home.json"),
    "/api/freshness": await file("freshness.json"),
    "/api/home": await file("home.json"),
    "/api/data/readiness": await file("data-readiness.json"),
    "/api/planned-packages": await file("planned-packages-list.json"),
    "/api/examples/rural_roads_kenya": await file("example-rural-roads-kenya.json"),
    [`/api${PLAN}`]: await file("check-plan-p156634-nwwda-2026-10-09.json"),
    [`/api${PLAN}/changes`]: await file("changes-nwwda-2026-10-09.json"),
    "/api/drafts/existing": await file("drafts-existing-example-review-notes.json"),
    ...extra,
  };
}

const sidebarItem = (page: Page) => page.getByRole("navigation", { name: "Main" }).locator("[data-start-here-item]");

test("once Home has loaded, the open sidebar shows Start here, the count and the next example as a link", async ({ page }) => {
  await openSidebar(page);
  await page.setViewportSize({ width: 1440, height: 900 });
  await mockApi(page, await startHereApi());

  // A browser that has not opened Home yet shows no item.
  await page.goto("/data");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Data");
  await expect(sidebarItem(page)).toHaveCount(0);

  await page.goto("/");
  await expect(page.locator("[data-home=ready]")).toBeVisible();
  const item = sidebarItem(page);
  await expect(item).toContainText("Start here");
  await expect(item).toContainText("0 of 6 done");
  await expect(item).toContainText("Next: Check a published plan (P156634)");
  await expect(item).toHaveAttribute("href", PLAN);

  // Following an example from the strip ticks it: the sidebar moves on at once, with no reload.
  const strip = page.locator("[data-start-here=shown]");
  await strip.getByRole("link", { name: "Check the data" }).click();
  await expect(page).toHaveURL("/data");
  await expect(item).toContainText("1 of 6 done");
  await expect(item).toContainText("Next: Check a published plan (P156634)");

  // Back on Home, the strip shows the tick and the count; only a done link's name ends with "done".
  await page.getByRole("navigation", { name: "Main" }).getByRole("link", { name: "Home", exact: true }).click();
  await expect(page.locator("[data-home=ready]")).toBeVisible();
  await expect(strip).toHaveAccessibleName("Start here 1 of 6 done");
  const links = strip.getByRole("listitem").getByRole("link");
  await expect(links).toHaveCount(6);
  await expect(strip.locator("[data-start-link=checkData]")).toHaveAccessibleName(/^Check the data ?, done$/);
  await expect(strip.locator("[data-start-link=checkData] [data-start-tick=done]")).toBeVisible();
  for (const key of ["checkPlan", "planPackage", "wholeStory", "lessonChange", "publicView"]) {
    await expect(strip.locator(`[data-start-link=${key}] [data-start-tick=open]`), key).toBeVisible();
    await expect(strip.locator(`[data-start-link=${key}]`), key).not.toHaveAccessibleName(/done$/);
  }

  // Following the next one from the sidebar ticks it too, and goes straight there.
  await item.click();
  await expect(page).toHaveURL(PLAN);
  await expect(item).toContainText("2 of 6 done");
  await expect(item).toContainText("Next: Plan a package from a sentence");
  await expect(item).toHaveAttribute("href", "/packages?box=plan&example=rural_roads_kenya");

  // A reload on another page keeps both.
  await page.goto("/data");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Data");
  await expect(item).toContainText("2 of 6 done");
  await expect(item).toContainText("Next: Plan a package from a sentence");
});

// As a rail (at rest from 1024 px, ticket 110) the item shows its icon over the short count, and its tooltip says the
// rest. Below 1024 px it sits under Home in the Menu sheet, as the open sidebar draws it. Its name is its words.
for (const width of [1440, 390]) {
  test(`at ${width} px the item shows the count and the next example, and axe finds no violation in it or the strip`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await mockApi(page, await startHereApi());
    await page.goto("/");
    await expect(page.locator("[data-home=ready]")).toBeVisible();
    const strip = page.locator("[data-start-here=shown]");
    await expect(strip.locator("[data-start-count]")).toHaveText("0 of 6 done");
    const name = "Start here 0 of 6 done Next: Check a published plan (P156634)";

    if (width === 1440) {
      const item = sidebarItem(page);
      await expect(item).toHaveAccessibleName(name);
      // The rail shows the short count under the icon; the item's words stay in its name and its tooltip.
      await expect(item.getByText("0 of 6", { exact: true })).toBeVisible();
      expect((await item.getByText("Start here", { exact: true }).boundingBox())!.width).toBeLessThanOrEqual(1);
      await item.hover();
      const tip = page.locator("[data-rail-tip]");
      await expect(tip).toHaveText("Start here: 0 of 6 done. Next: Check a published plan (P156634).");
      expect((await scan(page, "[data-sidebar-column], [data-start-here]")).violations).toEqual([]);
      return;
    }

    expect((await scan(page, "[data-start-here]")).violations).toEqual([]);
    await page.getByRole("button", { name: "Menu", exact: true }).click();
    const sheet = page.getByRole("dialog", { name: "Menu" });
    const item = sheet.locator("[data-start-here-item]");
    await expect(item).toHaveAccessibleName(name);
    for (const words of ["Start here", "0 of 6 done", "Next: Check a published plan (P156634)"]) {
      await expect(item.getByText(words, { exact: true })).toBeVisible();
    }
    expect((await scan(page, "[data-sidebar]")).violations).toEqual([]);

    // Following it from the sheet closes the sheet, and the sheet then shows the next one.
    await item.click();
    await expect(page).toHaveURL(PLAN);
    await page.getByRole("button", { name: "Menu", exact: true }).click();
    await expect(sheet.locator("[data-start-here-item]")).toHaveAccessibleName("Start here 1 of 6 done Next: Plan a package from a sentence");
  });
}

test("with all six done the item says so and leads to the strip, and after Remove it is gone from every page", async ({ page }) => {
  await openSidebar(page);
  await page.setViewportSize({ width: 1440, height: 900 });
  await mockApi(page, await startHereApi());
  await page.goto("/");
  await expect(page.locator("[data-home=ready]")).toBeVisible();
  const strip = page.locator("[data-start-here=shown]");
  for (const name of ["Check a published plan", "Plan a package from a sentence", "See a project's whole story", "See a lesson change", "Check the data", "See the public view"]) {
    await strip.getByRole("link", { name: new RegExp(`^${name}`) }).click();
    await expect(page).not.toHaveURL(/\/$/);
    await page.goBack();
    await expect(page.locator("[data-home=ready]")).toBeVisible();
  }
  await expect(strip).toHaveAccessibleName("Start here 6 of 6 done");
  await expect(strip.locator("[data-start-tick=done]")).toHaveCount(6);

  const item = sidebarItem(page);
  await expect(item).toHaveAccessibleName("Start here All six done");
  await expect(item).toHaveAttribute("href", "/#start-here");
  await page.getByRole("navigation", { name: "Main" }).getByRole("link", { name: "Data", exact: true }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Data");
  await item.click();
  await expect(page).toHaveURL("/#start-here");
  await expect(page.getByRole("heading", { name: "Start here", exact: true })).toBeFocused();

  // Remove takes the item off this page and every other at once.
  await page.route("**/api/home/start-here", async (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: await recorded("start-here-removed.json") }),
  );
  await page.getByRole("button", { name: "Remove the Start here examples" }).click();
  await expect(page.getByText("You removed the examples Prism set up.")).toBeFocused();
  await expect(item).toHaveCount(0);
  await page.getByRole("navigation", { name: "Main" }).getByRole("link", { name: "Data", exact: true }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Data");
  await expect(item).toHaveCount(0);
});

test("in a preview, as of a date and in the officer's own view no item shows, though this browser kept the list", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await mockApi(page, await startHereApi());
  await page.goto("/");
  await expect(sidebarItem(page)).toHaveCount(1);

  for (const path of ["/?view=piu", "/?view=public", "/?asof=2016-08-26"]) {
    await page.goto(path);
    await expect(page.locator("[data-home=ready]"), path).toBeVisible();
    await expect(page.getByRole("navigation", { name: "Main" }).getByRole("link", { name: "Home", exact: true }), path).toBeVisible();
    await expect(sidebarItem(page), path).toHaveCount(0);
  }

  // An implementing agency officer's own Home, in the same browser.
  const own = JSON.parse(await recorded("home-preview-piu.json"));
  own.preview = false;
  await page.unrouteAll({ behavior: "ignoreErrors" });
  await mockApi(page, await startHereApi({ "/api/me": await file("me-officer.json"), "/api/home": { body: JSON.stringify(own) } }));
  await page.goto("/");
  await expect(page.locator("[data-check-my-plan]")).toBeVisible();
  await expect(sidebarItem(page)).toHaveCount(0);
});

test("with local storage blocked Home and other pages still render, and no item shows", async ({ page }) => {
  await page.addInitScript(() => {
    Object.defineProperty(window, "localStorage", {
      get() {
        throw new DOMException("The storage is blocked.", "SecurityError");
      },
    });
  });
  await page.setViewportSize({ width: 1440, height: 900 });
  await mockApi(page, await startHereApi());
  await page.goto("/");
  await expect(page.locator("[data-home=ready]")).toBeVisible();
  const strip = page.locator("[data-start-here=shown]");
  await expect(strip.locator("[data-start-link]")).toHaveCount(6);
  await expect(sidebarItem(page)).toHaveCount(0);
  await strip.getByRole("link", { name: "Check the data" }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Data");
  await expect(sidebarItem(page)).toHaveCount(0);
});
