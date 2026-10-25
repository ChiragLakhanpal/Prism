// An implementing agency officer's upload at seam 4 (ticket 38): Check my plan with its access label, the upload of the
// fixture plan and its check, a file the server refuses, the not-found card another team gets, World Bank staff's empty
// state, a draft of planned dates with its STEP rows export, and the officer's pill. /api answers from the server's own
// answers on the fixture and on ticket 27's hand-made set (tests/record_uploads_api.py), which tests/test_step_rows.py
// checks the server still gives. The words below are the ticket's and the 38 brief's, copied here so the test checks
// the copy file against an independent source.
import { fileURLToPath } from "node:url";
import { scan } from "./axe";
import type { Page } from "@playwright/test";
import { expect, recorded, test } from "./mocked";

type Answer = { status?: number; body: string };
const UPLOAD = "/packages/uploads/upl-000000000001";
const ACCESS = "Official Use Only · visible to your team";

async function serve(page: Page, answers: Record<string, Answer>, me = "me-officer.json") {
  const base: Record<string, Answer> = {
    "GET /api/me": { body: await recorded(me) },
    "GET /api/freshness": { body: await recorded("freshness.json") },
    "POST /api/evidence/opened": { body: '{"recorded":true}' },
  };
  const all = { ...base, ...answers };
  const asked: string[] = [];
  await page.route("**/api/**", (route) => {
    const request = route.request();
    const key = `${request.method()} ${new URL(request.url()).pathname}`;
    asked.push(key);
    const answer = all[key];
    if (!answer) return route.fulfill({ status: 404, json: { detail: "Not Found" } });
    return route.fulfill({ status: answer.status ?? 200, contentType: "application/json", body: answer.body });
  });
  return asked;
}

// The label's words as a sighted reader sees them: the comma a screen reader hears is visually hidden.
async function shownText(page: Page, selector: string): Promise<string> {
  return page.locator(selector).first().evaluate((element) => {
    const copy = element.cloneNode(true) as HTMLElement;
    copy.querySelectorAll(".sr-only").forEach((hidden) => hidden.remove());
    return (copy.textContent ?? "").replace(/\s+/g, " ").trim();
  });
}

async function violations(page: Page) {
  const results = await scan(page);
  return results.violations.map((v) => `${v.id}: ${v.nodes.map((node) => node.target.join(" ")).join(", ")}`);
}

test("Check my plan shows the access label and the privacy sentences above the file field, and says uploading submits nothing", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await serve(page, { "GET /api/uploads/form": { body: await recorded("uploads-form-officer.json") } });
  await page.goto("/packages/check");

  const card = page.locator("[data-upload-card]");
  await expect(card.getByRole("heading", { name: "Upload your plan" })).toBeVisible();
  expect(await shownText(page, "[data-upload-card] [data-access-label]")).toBe(ACCESS);
  await expect(card.locator("[data-access-label]")).toHaveText(/Official Use Only\s*·?\s*,?\s*visible to your team/);
  // The label and the privacy sentence come before the file field.
  const [label, field] = [await card.locator("[data-access-label]").boundingBox(), await card.locator("[data-file-field]").boundingBox()];
  expect(label!.y).toBeLessThan(field!.y);
  await expect(card).toContainText("only to your team at Northern Water Works Development Agency");
  await expect(card).toContainText("I keep the activities I read from your file, not the file itself.");
  await expect(page.getByRole("button", { name: "Upload and check" })).toHaveAccessibleDescription(
    "Uploading doesn't submit your plan. I send nothing to the World Bank or to STEP.");
  await expect(page.getByLabel("Procurement Plan file")).toHaveAttribute("accept", ".xlsx,.csv");
  // The columns listed are STEP's, from the server's registry.
  await page.getByRole("button", { name: "Show the columns I read" }).click();
  await expect(page.locator("[data-column-lists]")).toContainText("Activity Reference No. / Description");
  await expect(page.getByRole("link", { name: "Procurement Plan of October 9, 2026" })).toHaveAttribute(
    "href", "/projects/P156634/procurement/northern-water-works-development-agency/2026-10-09");
  await expect(page.locator("[data-view-pill]")).toHaveText("View: Agency officer");
  expect(await violations(page)).toEqual([]);
});

test("Uploading the fixture plan opens its check: nine activities with the label, and the action that drafts planned dates", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  const asked = await serve(page, {
    "GET /api/uploads/form": { body: await recorded("uploads-form-officer.json") },
    "POST /api/uploads": { body: await recorded("upload-kept.json") },
    "GET /api/uploads/upl-000000000001": { body: await recorded("upload-check-nwwda.json") },
  });
  await page.goto("/packages/check");
  await page.getByLabel("Procurement Plan file").setInputFiles(fileURLToPath(new URL("../../tests/fixtures/uploads/nwwda-plan-2026-10-09.csv", import.meta.url)));
  await expect(page.locator("[data-file-status]")).toContainText("nwwda-plan-2026-10-09.csv");
  await page.getByRole("button", { name: "Upload and check" }).click();

  await expect(page).toHaveURL(UPLOAD);
  expect(asked).toContain("POST /api/uploads");
  await expect(page.locator("[data-check-pill]")).toHaveText("9 activities checked");
  expect(await shownText(page, "[data-upload-check-page] [data-access-label]")).toBe(ACCESS);
  await expect(page.getByRole("button", { name: "Draft planned dates (9 activities)" })).toBeVisible();
  await expect(page.locator("[data-reading-line]")).toContainText(
    "I read nine activities from nwwda-plan-2026-10-09.csv for Water and Sanitation Development (P156634).");
  await expect(page.locator("[data-view=table] th[data-activity='KE-NWWDA-541055-CW-RFB']")).toBeVisible();
  expect(await violations(page)).toEqual([]);
});

test("A file with no Method column is refused with its name, I kept nothing, and the columns I read", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await serve(page, {
    "GET /api/uploads/form": { body: await recorded("uploads-form-officer.json") },
    "POST /api/uploads": { status: 422, body: await recorded("upload-missing-columns.json") },
  });
  await page.goto("/packages/check");
  await page.getByLabel("Procurement Plan file").setInputFiles({ name: "draft-plan.csv", mimeType: "text/csv",
    buffer: Buffer.from("Activity Reference No. / Description,Review Type\r\n / New works,Post\r\n") });
  await page.getByRole("button", { name: "Upload and check" }).click();

  await expect(page.getByRole("alert")).toHaveText(
    'I couldn\'t check draft-plan.csv, because it has no "Method" column. I kept nothing.');
  await expect(page.getByRole("heading", { name: "The columns I read" })).toBeVisible();
  await expect(page).toHaveURL("/packages/check");
});

test("Another team's upload, or one that does not exist, gets the same card; World Bank staff get the empty state", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await serve(page, { "GET /api/uploads/upl-000000000001": { status: 404, body: await recorded("upload-not-found.json") },
    "GET /api/uploads/form": { body: await recorded("uploads-form-staff.json") } }, "me.json");
  await page.goto(UPLOAD);
  await expect(page.getByRole("heading", { name: "I can't find this upload." })).toBeVisible();
  await expect(page.locator("[data-access-label]")).toHaveCount(0);

  await page.goto("/packages/check");
  await expect(page.getByRole("heading", { name: "I check uploads only for implementing agency teams, and your account isn't on one." })).toBeVisible();
  await expect(page.locator("[data-upload-card]")).toHaveCount(0);
});

test("A draft of planned dates shows each activity's dates in the file's order, with the label, and exports STEP rows", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await serve(page, { "GET /api/drafts/draft-0002": { body: await recorded("drafts-step-rows-draft.json") } });
  await page.goto("/drafts/draft-0002");

  await expect(page.getByRole("heading", { level: 1, name: "Planned dates" })).toBeVisible();
  expect(await shownText(page, "[data-draft-page] [data-access-label]")).toBe(ACCESS);
  const rows = page.locator("[data-overview-row]");
  await expect(rows).toHaveCount(2);
  await expect(rows.first()).toContainText("KE-HAND-900000-CW-RFB");
  // The cautious date for the signed contract, from tests/ground_truth/values.toml's [step_dates].
  await expect(rows.first()).toContainText("Aug 1, 2021");
  await expect(rows.nth(1)).toContainText("No reference yet. STEP assigns one.");
  await expect(page.locator("[data-left-to-people]")).toContainText("Activity Reference No.");
  const bar = page.getByRole("region", { name: "Check and export" });
  await expect(bar.getByRole("button", { name: "Export STEP rows" })).toBeVisible();
  await expect(bar).toContainText("You opened 0 of 5 lists of comparable packages");
  expect(await violations(page)).toEqual([]);
});
