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

type Answer = { status?: number; body: string; type?: string };
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
    return route.fulfill({ status: answer.status ?? 200, contentType: answer.type ?? "application/json", body: answer.body });
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
  const sent = page.waitForRequest((request) => request.method() === "POST" && new URL(request.url()).pathname === "/api/uploads");
  await page.getByRole("button", { name: "Upload and check" }).click();

  await expect(page).toHaveURL(UPLOAD);
  expect(asked).toContain("POST /api/uploads");
  // The file's name travels in a header, never in the address a proxy's log may keep.
  const request = await sent;
  expect(request.url()).not.toContain("nwwda-plan");
  expect(request.headers()["x-strata-file-name"]).toBe("nwwda-plan-2026-10-09.csv");
  await expect(page.locator("[data-check-pill]")).toHaveText("9 activities checked");
  expect(await shownText(page, "[data-upload-check-page] [data-access-label]")).toBe(ACCESS);
  await expect(page.getByRole("button", { name: "Draft planned dates (9 activities)" })).toBeVisible();
  await expect(page.locator("[data-reading-line]")).toContainText(
    "I read nine activities from nwwda-plan-2026-10-09.csv for Water and Sanitation Development (P156634).");
  await expect(page.locator("[data-view=table] th[data-activity='KE-NWWDA-541055-CW-RFB']")).toBeVisible();
  expect(await violations(page)).toEqual([]);
});

// Ticket 100's review, F1 and F3: a row whose only mark is an upload's reading note still lists what I checked, and a
// planned date that came from the upload itself, since no published plan lists the activity, says so.
test("An upload row's records list what I checked for a reading note, and name your upload as the plan a planned date came from", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  const check = JSON.parse(await recorded("upload-check-nwwda.json"));
  const late = check.rows.find((row: { position: number }) => row.position === 1);
  Object.assign(late.marks[0].reasons[0], { planned_signing_plan_date: "2026-10-22" });
  late.listed = false;
  const unread = check.rows.find((row: { position: number }) => row.position === 7);
  unread.marks = [{ mark: "data_note", reasons: [{ code: "unread_date", mark: "data_note", column: "Signed Contract", value: "31/02/2021", evidence_ids: [unread.evidence_id] }] }];
  await serve(page, { "GET /api/uploads/upl-000000000001": { body: JSON.stringify(check) } });
  await page.goto(UPLOAD);
  const pairs = (kind: string) =>
    page.getByRole("dialog").locator(`[data-records=${kind}] > div`).evaluateAll((lines) => lines.map((line) => [line.querySelector("dt")!.textContent, line.querySelector("dd")!.textContent]));

  await page.locator("[data-view=table]").getByRole("button", { name: "KE-NWWDA-199471-GO-RFQ", exact: true }).click();
  await expect(page.getByRole("dialog").getByRole("heading", { level: 3 })).toHaveText(["What I checked", "From the plan row"]);
  expect(await pairs("checked")).toEqual([
    ["Process Status", "Completed"],
    ["Planned completion", "May 7, 2021"],
    ["Contract signed", "Mar 19, 2021"],
    ["Checked as of", "Oct 22, 2026"],
  ]);
  await page.keyboard.press("Escape");

  await page.locator("[data-view=table]").getByRole("button", { name: "KE-NWWDA-229129-CW-RFB", exact: true }).click();
  expect((await pairs("checked")).slice(0, 2)).toEqual([
    ["Planned signing", "Jul 1, 2021"],
    ["In the plan of", "your upload of Oct 22, 2026"],
  ]);
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

test("A count of comparable packages on a draft of planned dates opens its list, and the bar counts it as opened", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  const asked = await serve(page, { "GET /api/drafts/draft-0002": { body: await recorded("drafts-step-rows-draft.json") } });
  await page.goto("/drafts/draft-0002");
  const bar = page.getByRole("region", { name: "Check and export" });
  await expect(bar).toContainText("You opened 0 of 5 lists of comparable packages");

  // The hand-made set's 25 comparable packages, C01 to C25 (tests/step_set.py), behind the bid invitation's count.
  await page.locator("#activity-1 [data-step='bid_invitation']").getByRole("button", { name: /^25 comparable packages/ }).click();

  const drawer = page.getByRole("dialog");
  await expect(drawer.locator("[data-step-entry]")).toHaveCount(25);
  await expect(drawer.locator("[data-step-entry='KE-HAND-900001-CW-RFB']")).toBeVisible();
  await expect(bar).toContainText("You opened 1 of 5 lists of comparable packages");
  expect(asked).toContain("POST /api/evidence/opened");
});

test("When my verifier removes a step's dates on a draft of planned dates, the page shows the removed box and the cell says why", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  // The server's answer when the draft stated a cautious date estimate_time did not return (tests/record_uploads_api.py).
  await serve(page, { "GET /api/drafts/draft-0003": { body: await recorded("drafts-step-rows-removed.json") } });
  await page.goto("/drafts/draft-0003");

  const box = page.locator("[data-removed-box]");
  await expect(box).toContainText("I removed one sentence.");
  await expect(box).toContainText("bid evaluation report: middle date 2021-05-31; cautious date 2021-06-30; 25 comparable packages, and no record supports that date.");
  const step = page.locator("#activity-1 [data-step='bid_evaluation_report']");
  await expect(step).toContainText("I removed this date, because it didn't match my delay model's results.");
  // The count went with the dates it was stated with.
  await expect(step.locator("td").last()).toHaveText("");
  const bar = page.getByRole("region", { name: "Check and export" });
  await expect(bar).toContainText("You opened 0 of 4 lists of comparable packages");
  // The signed contract's date in the overview opens its 25 comparable packages, as it does in the Step table.
  await page.locator("[data-overview-row]").first().getByRole("button", { name: /Aug 1, 2021/ }).click();
  await expect(page.getByRole("dialog").locator("[data-step-entry]")).toHaveCount(25);
  await expect(bar).toContainText("You opened 1 of 4 lists of comparable packages");
});

test("When my verifier removes every date I worked out, the writing page shows what it removed and why, and never blames too few packages", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  // The server's stream when the draft stated a cautious date estimate_time did not return on all five steps it dates,
  // each with 25 comparable packages (tests/record_uploads_api.py): nothing is left dated, so nothing is saved.
  await serve(page, {
    "GET /api/uploads/upl-000000000001": { body: await recorded("upload-check-nwwda.json") },
    "POST /api/drafts": { body: await recorded("drafts-step-rows-nothing-removed.sse"), type: "text/event-stream" },
  });
  await page.goto(UPLOAD);
  await page.getByRole("button", { name: "Draft planned dates (9 activities)" }).click();

  const nothing = page.locator("[data-nothing-dated]");
  await expect(nothing.getByRole("heading", { name: "I couldn't date any step of your plan, so I saved no draft." })).toBeVisible();
  await expect(nothing).toContainText("My checks removed what I worked out for five steps, because it didn't match my delay model's results, and no other step had a date.");
  await expect(nothing).not.toContainText("fewer than");
  const box = nothing.locator("[data-removed-box]");
  await expect(box).toContainText("I removed five sentences.");
  await expect(box).toContainText("bid invitation (SPN): middle date 2021-03-09; cautious date 2021-03-25; 25 comparable packages");
  await expect(box).toContainText("no record supports that date");
  expect(await shownText(page, "[data-draft-new] [data-access-label]")).toBe(ACCESS);
  expect(await violations(page)).toEqual([]);
});
