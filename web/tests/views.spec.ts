// The view switch and the as-of date (ticket 40) at seam 4: the built app against the answers tests/record_views_api.py
// and the earlier recorders wrote from the server on the fixture. The server applies each view's rules and the date
// (tests/test_views.py, tests/test_public_view.py, tests/test_as_of.py prove that); these tests prove the screens show
// what the server applied: the pill, the banners, the held acts with the server's own reason, the public view's tabs and
// pages, and the timeline as of a past date. Words are the 40 brief's, from the copy file.
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import type { Page } from "@playwright/test";
import { copyAt } from "../src/lib/view";
import { scan } from "./axe";
import { expect, mockApi, recorded, test, viewAnswers } from "./mocked";

type Answer = { status?: number; body: string };

const PLAN = "/projects/P156634/procurement/northern-water-works-development-agency/2026-10-09";
// A package whose comparables published their criteria, so "Check your criteria" offers the paste field (ticket 31).
const CONSULTANT = "KE-CWSB-224323-CS-QCBS";
const SHOWCASE = "IN-RRSMP-7431-CW-RFB";
const AGENCY_BANNER =
  "Preview of what an implementing agency officer at the Northern Water Works Development Agency (NWWDA) sees. You are still signed in as yourself.";

async function open(page: Page, path: string, answers: Record<string, Answer> = {}, width = 1440) {
  await page.setViewportSize({ width, height: 900 });
  await mockApi(page, {
    ...(await viewAnswers()),
    "/api/me": { body: await recorded("me.json") },
    "/api/freshness": { body: await recorded("freshness.json") },
    ...answers,
  });
  await page.goto(path);
  await expect(page.locator("main h1")).toBeVisible();
}

// The server's 403 for an act a preview refuses, as tests/record_views_api.py recorded it.
async function refusal(name: string): Promise<{ capability: string; copy_key: string }> {
  return JSON.parse(await recorded(name)).body;
}

async function violations(page: Page, within?: string) {
  const results = await scan(page, within);
  return results.violations.map((v) => `${v.id}: ${v.nodes.map((node) => node.target.join(" ")).join(", ")}`);
}

test("every reason a preview gives, in the roles file, is a sentence in the copy file", async () => {
  const path = fileURLToPath(new URL("../../config/roles.toml", import.meta.url));
  const read = spawnSync("python3", ["-c", "import json, sys, tomllib; print(json.dumps(tomllib.load(open(sys.argv[1], 'rb'))['views']))", path], { encoding: "utf8" });
  const views = JSON.parse(read.stdout) as { capabilities: Record<string, { kind: string; reason?: string }> };
  const acts = Object.entries(views.capabilities).filter(([, capability]) => ["record", "check", "export", "draft"].includes(capability.kind));
  expect(acts.length).toBeGreaterThan(10);
  for (const [key, capability] of acts) expect(copyAt(capability.reason!), key).toMatch(/\.$/);
});

test("in the agency preview, uploading and comparing criteria are held with the sentence the server's 403 names", async ({ page }) => {
  const upload = await refusal("refused-upload-preview.json");
  await open(page, "/packages/check?view=piu", { "/api/uploads/form?view=piu": { body: await recorded("uploads-form-preview.json") } });
  const submit = page.locator("[data-upload-submit]");
  await expect(submit).toHaveAttribute("aria-disabled", "true");
  const described = await submit.getAttribute("aria-describedby");
  await expect(page.locator(`[id="${described}"]`)).toHaveText(copyAt(upload.copy_key));
  expect(upload.capability).toBe("upload_and_check");

  const compare = await refusal("refused-compare-preview.json");
  const api = `/api/packages/${CONSULTANT}`;
  await open(page, `/packages/${CONSULTANT}?view=piu`, {
    [api]: { body: await recorded("package-ke-cwsb-224323.json") },
    [`${api}/comparables`]: { body: await recorded("comparables-ke-cwsb-224323.json") },
    [`${api}/criteria`]: { body: await recorded("criteria-summary-ke-cwsb-224323.json") },
    [`${api}/criteria/run`]: { body: await recorded("criteria-run-ke-cwsb-224323.sse") },
  });
  await page.locator("#check-criteria").getByRole("button", { name: /Show/ }).first().click();
  await expect(page.locator("[data-compare]")).toHaveAttribute("aria-disabled", "true");
  await expect(page.locator("[data-held-reason=compare_criteria]")).toHaveText(copyAt(compare.copy_key));
  expect(compare.capability).toBe("compare_criteria");
});

test("the preview banner reads as the blueprint's, never collapses, is reached by keyboard, and the view survives navigation", async ({ page }) => {
  await open(page, "/?view=piu");
  const banner = page.getByRole("region", { name: "Preview" });
  await expect(banner.locator("[data-alert] p").first()).toHaveText(AGENCY_BANNER);
  await expect(page.getByRole("button", { name: "Preview: Agency officer" })).toBeVisible();
  // It has no close button, and Escape leaves it in place.
  await expect(banner.getByRole("button")).toHaveCount(0);
  await page.keyboard.press("Escape");
  await expect(banner).toBeVisible();

  // Its way out is a tab stop, reached from the top of the page by keyboard.
  const leave = banner.getByRole("link", { name: "Leave the preview" });
  for (let press = 0; press < 30 && !(await leave.evaluate((element) => element === document.activeElement)); press += 1) {
    await page.keyboard.press("Tab");
  }
  await expect(leave).toBeFocused();

  // A tab keeps the view, and so does the page it opens.
  await page.getByRole("navigation", { name: "Main" }).getByRole("link", { name: "Lessons" }).click();
  await expect(page).toHaveURL(/\/lessons\?view=piu$/);
  await expect(page.getByRole("region", { name: "Preview" })).toBeVisible();

  // Leaving the preview drops ?view=, the banner goes, the h1 takes focus and the change is said.
  await page.getByRole("link", { name: "Leave the preview" }).click();
  await expect(page).toHaveURL(/\/lessons$/);
  await expect(page.getByRole("region", { name: "Preview" })).toHaveCount(0);
  await expect(page.locator("[data-mode-status]")).toHaveText("You left the preview. You are seeing the World Bank staff view.");
  expect(await violations(page)).toEqual([]);
});

test("choosing a view in the popover opens the preview, with the filled pill and the banner focused", async ({ page }) => {
  await open(page, "/");
  await page.getByRole("button", { name: "View: World Bank staff" }).click();
  expect(await violations(page, "[role=dialog]")).toEqual([]);
  await page.getByRole("dialog").getByRole("link", { name: "The public" }).click();

  await expect(page).toHaveURL(/\/\?view=public$/);
  const pill = page.getByRole("button", { name: "Preview: Public" });
  await expect(pill).toHaveAttribute("data-preview", "public");
  await expect(page.getByRole("region", { name: "Preview" })).toBeFocused();
  // The public view has only Projects, Lessons and Data, and its Home until ticket 41.
  await expect(page.getByRole("navigation", { name: "Main" }).getByRole("link")).toHaveText(["Projects", "Lessons", "Data"]);
  await expect(page.locator("main h1")).toHaveText("Start from a project");
  await expect(page).toHaveTitle("Start from a project (public preview) | Strata");
  expect(await violations(page)).toEqual([]);
});

test("in the public view a page it hides says why, and P156634's plan shows data notes and no signal", async ({ page }) => {
  await open(page, "/packages?view=public");
  await expect(page.locator("main h1")).toHaveText("Packages");
  await expect(page.locator("[data-not-in-view=packages]")).toContainText("Packages are not part of the public view.");

  await open(page, `${PLAN}?view=public`, {
    [`/api${PLAN}`]: { body: await recorded("check-plan-p156634-nwwda-2026-10-09-public.json") },
    "/api/projects/P156634": { body: await recorded("project-p156634.json") },
  });
  const check = page.locator("[data-plan-check]");
  await expect(check.getByRole("heading", { level: 2 })).toHaveText(
    "I don't show signals on active projects in this view, so a procurement still under way isn't prejudged; three have data notes.",
  );
  await expect(page.locator("[data-badge=needs-a-look], [data-badge=watch]")).toHaveCount(0);
  await expect(page.locator("[data-badge=data-note]").first()).toBeVisible();
  // The activities folded away may still have a signal this view holds back, so I don't say they have none.
  const recordedCheck = JSON.parse(await recorded("check-plan-p156634-nwwda-2026-10-09-public.json")) as { counts: { unmarked: number } };
  expect(recordedCheck.counts.unmarked).toBe(6);
  await expect(check).toContainText("Six more activities have no data notes.");
  await expect(check).not.toContainText("no signals");
});

test("in the public view P130164, a closed project, shows its contract trail with no past range", async ({ page }) => {
  await open(page, `/projects/P130164/packages/${SHOWCASE}?view=public`, {
    "/api/projects/P130164": { body: await recorded("project-p130164.json") },
    [`/api/projects/P130164/packages/${SHOWCASE}`]: { body: await recorded("activity-in-rrsmp-7431.json") },
  });
  await expect(page.locator("[data-activity-page=ready]")).toBeVisible();
  await expect(page.locator("[data-past-range-link]")).toHaveCount(0);
  await expect(page.getByRole("region", { name: "Preview" })).toBeVisible();
});

test("in the public view P130164's timeline, a closed project's, shows its marks and its disagreements as staff see them", async ({ page }) => {
  const staff = JSON.parse(await recorded("timeline-p130164.json")) as { items: unknown[]; disagreements: { count: number } };
  await open(page, "/projects/P130164/timeline?view=public", {
    "/api/projects/P130164": { body: await recorded("project-p130164.json") },
    "/api/projects/P130164/timeline?view=public": { body: await recorded("timeline-p130164-public.json") },
  });
  await expect(page.locator("[data-timeline=ready]")).toBeVisible();
  await expect(page.getByRole("region", { name: "Preview" })).toBeVisible();
  const trail = page.locator("[data-evidence-trail]");
  await expect(trail.getByRole("group").getByRole("link")).toHaveCount(staff.items.length);
  await expect(trail.locator("[data-disagreement-line]")).toHaveCount(staff.disagreements.count);
  expect(staff.disagreements.count).toBeGreaterThan(0);
});

test("as of August 26, 2016, P130164's timeline ends at the date; ISR 7's drawer opens it, and Back to today clears it", async ({ page }) => {
  const api = {
    "/api/projects/P130164": { body: await recorded("project-p130164.json") },
    "/api/projects/P130164/timeline": { body: await recorded("timeline-p130164.json") },
    "/api/projects/P130164?asof=2016-08-26": { body: await recorded("project-p130164-2016-08-26.json") },
    "/api/projects/P130164/timeline?asof=2016-08-26": { body: await recorded("timeline-p130164-2016-08-26.json") },
    "/api/evidence?id=doc:26733307": { body: await recorded("evidence-doc-p130164-isr-7.json") },
  };
  await open(page, "/projects/P130164/timeline", api);
  await expect(page.locator("[data-timeline=ready]")).toBeVisible();
  await page.locator('[data-item="doc:26733307"]').first().click();
  const action = page.getByRole("dialog").locator("[data-asof-action]");
  await expect(action.getByRole("link", { name: "See Strata as of this date" })).toHaveAccessibleDescription(
    "It opens this project as it was on August 26, 2016, the day the World Bank disclosed this report.",
  );
  await action.getByRole("link").click();

  await expect(page).toHaveURL(/\/projects\/P130164\/timeline\?asof=2016-08-26$/);
  await expect(page.getByRole("dialog")).toHaveCount(0);
  const banner = page.getByRole("region", { name: "Past date" });
  await expect(banner).toBeFocused();
  await expect(banner.locator("[data-alert] p").first()).toHaveText("I'm showing this page as of August 26, 2016. I use only what was disclosed by that date.");
  // Nothing after the date is drawn: every mark the server sent is dated on or before it.
  const recorded2016 = JSON.parse(await recorded("timeline-p130164-2016-08-26.json")) as { items: { date?: string }[] };
  expect(recorded2016.items.every((item) => !item.date || item.date <= "2016-08-26")).toBe(true);
  await expect(page.locator("[data-evidence-trail] [data-as-of]")).toContainText("Aug 26, 2016");
  // ISR 7 is still on the timeline, and its drawer no longer offers the date it already shows.
  await page.locator('[data-item="doc:26733307"]').first().click();
  await expect(page.getByRole("dialog").locator("[data-asof-action]")).toHaveCount(0);
  await page.keyboard.press("Escape");

  await page.getByRole("link", { name: "Back to today" }).click();
  await expect(page).toHaveURL(/\/projects\/P130164\/timeline$/);
  await expect(page.getByRole("region", { name: "Past date" })).toHaveCount(0);
  await expect(page.locator("[data-mode-status]")).toHaveText("You are seeing today's data again.");
});

test("as of a past date, the pages that keep today's state say so under the date", async ({ page }) => {
  await open(page, "/packages?asof=2016-08-26", {
    "/api/planned-packages": { body: await recorded("planned-packages-empty.json") },
    "/api/uploads": { body: await recorded("uploads-list-nwwda.json") },
  });
  const banner = page.getByRole("region", { name: "Past date" }).locator("[data-alert] p").first();
  await expect(banner).toHaveText(
    "I'm showing this page as of August 26, 2016. I use only what was disclosed by that date. I show your packages and checked plans as they are today, whatever the as-of date.",
  );
  for (const [path, line] of [
    ["/lessons/review", "I show the lessons waiting for review as they are today, whatever the as-of date."],
    ["/lessons/reports", "I show passage reports as they are today, whatever the as-of date."],
    ["/lessons/judging", "I show the queries to judge as they are today, whatever the as-of date."],
  ]) {
    await page.goto(`${path}?asof=2016-08-26`);
    await expect(banner).toContainText(line);
  }
});

test("Your agency's projects lists each disclosed plan with its check, in the agency preview", async ({ page }) => {
  await open(page, "/projects?view=piu", {
    "/api/projects": { body: await recorded("projects.json") },
    "/api/agency/projects": { body: await recorded("agency-projects-two.json") },
  });
  const section = page.locator("[data-agency-projects]");
  await expect(section.getByRole("heading", { level: 2 })).toHaveText("Your agency's projects");
  await expect(section).toContainText(
    "These are the projects where the Northern Water Works Development Agency (NWWDA) has a disclosed Procurement Plan. I checked the latest plan for each one.",
  );
  // The link keeps the preview, so it holds it opened in a new tab too.
  await expect(section.getByRole("link", { name: "Procurement Plan of October 9, 2026" })).toHaveAttribute("href", `${PLAN}?view=piu`);
  await expect(section.locator("[data-agency-project=P156634]")).toContainText("One needs a look and two are worth watching; three have data notes.");
  await expect(section.locator("[data-agency-project]")).toHaveCount(2);
});
