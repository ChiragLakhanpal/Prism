// Field photos on the Deep research tab (ticket 150) at seam 4: a World Bank staff viewer adds a geo-tagged photo and
// sees it listed with its date and place, labelled Official Use Only and visible to the team, with "Uploading never
// submits anything" beside the control. The answers are the routes' own, recorded by tests/record_field_photos_api.py:
// the list before (field-photos-p156634-none.json) and after (field-photos-p156634.json) Ana adds the Baricho photo
// tests/test_field_photos.py makes, and the POST's answer (field-photo-added-p156634.json).
import type { Page, Route } from "@playwright/test";
import { copy } from "../src/copy";
import { formatDate } from "../src/lib/format";
import { scan } from "./axe";
import { expect, mockApi, recorded, test, viewAnswers } from "./mocked";

const PATH = "/projects/P156634/research";
const PHOTOS = "/api/projects/P156634/field-photos";
const words = copy.research.photos;
const PIXEL = Buffer.from("R0lGODlhAQABAIAAAP///wAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw==", "base64");

async function open(page: Page, list: string) {
  await page.setViewportSize({ width: 1440, height: 900 });
  const unrecorded = await mockApi(page, {
    ...(await viewAnswers()),
    "/api/me": { body: await recorded("me.json") },
    "/api/freshness": { body: await recorded("freshness.json") },
    "/api/projects/P156634": { body: await recorded("project-p156634.json") },
    "/api/projects/P156634/research": { body: await recorded("research-p156634-none.json") },
    [PHOTOS]: { body: await recorded(list) },
  });
  // Each listed photo shows the photo itself (ticket 156), which the photo route answers with a 1 px image here.
  await page.route(/\/api\/projects\/P156634\/field-photos\/fph-[0-9a-f]{12}$/, (route) => route.fulfill({ status: 200, contentType: "image/gif", body: PIXEL }));
  await page.goto(PATH);
  await expect(page.locator("main h1")).toBeVisible();
  return unrecorded;
}

const section = (page: Page) => page.locator("[data-field-photos]");

test("a staff viewer adds a geo-tagged photo and sees it listed with its date and place, for their team only", async ({ page }) => {
  const unrecorded = await open(page, "field-photos-p156634-none.json");
  await expect(section(page)).toHaveAttribute("data-field-photos", "ready");
  await expect(section(page).getByRole("heading", { level: 2 })).toHaveText(words.heading);
  await expect(section(page).locator("[data-access-label]")).toContainText(copy.upload.access.lead);
  await expect(section(page).locator("[data-access-label]")).toContainText(copy.upload.access.rest);
  await expect(section(page).locator("[data-never-submits]")).toHaveText(words.neverSubmits);
  await expect(section(page)).toContainText(words.none);

  // The POST answers with the route's own answer, and the list read after it with the photo listed.
  const after = await recorded("field-photos-p156634.json");
  const sent: { method: string; name: string | null; caption: string | null }[] = [];
  await page.route(`**${PHOTOS}*`, async (route: Route) => {
    const request = route.request();
    if (request.method() === "POST") {
      sent.push({ method: "POST", name: request.headers()["x-strata-file-name"] ?? null, caption: request.headers()["x-strata-caption"] ?? null });
      return route.fulfill({ status: 200, contentType: "application/json", body: await recorded("field-photo-added-p156634.json") });
    }
    return route.fulfill({ status: 200, contentType: "application/json", body: after });
  });
  const photo = JSON.parse(after).photos[0];
  await section(page).getByLabel(words.fileLabel).setInputFiles({ name: "intake.jpg", mimeType: "image/jpeg", buffer: Buffer.from([0xff, 0xd8, 0xff, 0xd9]) });
  await section(page).getByLabel(words.captionLabel).fill(photo.caption);
  await section(page).getByRole("button", { name: words.add }).click();

  await expect(section(page).locator("[data-field-photo-added]")).toHaveText(words.added);
  const listed = section(page).locator(`[data-field-photo="${photo.photo_id}"]`);
  await expect(listed).toContainText(photo.caption);
  await expect(listed.locator("[data-field-photo-date]")).toHaveText(words.taken(formatDate(photo.taken_on)));
  await expect(listed.locator("[data-field-photo-place]")).toHaveText(words.near(photo.place));
  await expect(listed.getByRole("link", { name: new RegExp(`^${words.open}`) })).toHaveAttribute("href", photo.url);
  expect(sent).toEqual([{ method: "POST", name: "intake.jpg", caption: encodeURIComponent(photo.caption) }]);
  await scan(page);
  expect(unrecorded).toEqual([]);
});

test("a photo the server refuses for its size says so, and nothing is listed", async ({ page }) => {
  const unrecorded = await open(page, "field-photos-p156634-none.json");
  await page.route(`**${PHOTOS}*`, async (route: Route) => {
    if (route.request().method() !== "POST") return route.fallback();
    return route.fulfill({ status: 422, contentType: "application/json", body: JSON.stringify({ code: "size", kept: false }) });
  });
  await section(page).getByLabel(words.fileLabel).setInputFiles({ name: "big.jpg", mimeType: "image/jpeg", buffer: Buffer.from([0xff, 0xd8]) });
  await section(page).getByLabel(words.captionLabel).fill("The pump house.");
  await section(page).getByRole("button", { name: words.add }).click();
  await expect(section(page).getByRole("alert")).toHaveText(words.errors.size("10"));
  await expect(section(page).locator("[data-field-photo]")).toHaveCount(0);
  expect(unrecorded).toEqual([]);
});
