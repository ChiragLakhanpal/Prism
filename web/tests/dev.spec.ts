// The evidence drawer in the development build (ticket 14's design review, round 1). scripts/dev serves
// the app through Vite's dev server, where React's StrictMode mounts each component, unmounts it and
// mounts it again, so every effect runs twice. The panel asks for live code changes on scripts/dev, so
// the drawer must behave there as it does in production: focus moves to its heading and stays, the
// evidence card closes, the opening is recorded once, and closing goes back one history entry.
//
// This file runs in the "dev" project of playwright.config.ts, against `vite` rather than `vite
// preview`. It holds only what StrictMode can break; answer.spec.ts covers the rest.
import { askFromTheBox, drawer, ICR_54, landed, marker, open } from "./answer-page";
import { expect, mockApi, recorded, test } from "./mocked";

test("in the development build, a marker's click moves focus into the drawer and keeps it there, and records the opening once", async ({ page }) => {
  const seen = await open(page);
  await askFromTheBox(page);
  await landed(page);

  await marker(page, 1).click();

  const heading = drawer(page).getByRole("heading", { level: 2 });
  await expect(heading).toBeFocused();
  // StrictMode's second mount has run, and a frame has passed for anything it scheduled.
  await page.evaluate(() => new Promise((done) => requestAnimationFrame(() => requestAnimationFrame(done))));
  await expect(heading).toBeFocused();
  await expect(page.getByRole("tooltip")).toHaveCount(0);
  expect(seen.opened.map((request) => request.postDataJSON().evidence_id)).toEqual([ICR_54]);

  await page.keyboard.press("Escape");

  await expect(drawer(page)).toHaveCount(0);
  await expect(marker(page, 1)).toBeFocused();
  // Closing went back the entry that opening added, so Forward opens the drawer again.
  await page.goForward();
  await expect(drawer(page)).toBeVisible();
});

test("in the development build, a saved package opened by its address shows section 1's plan prompt", async ({ page }) => {
  // Ticket 15's critique, round 2: StrictMode's cleanup aborted the first read of the comparables, and the
  // second mount never asked again, so section 1 stayed a skeleton on every reopened package.
  await page.setViewportSize({ width: 1440, height: 900 });
  const unrecorded = await mockApi(page, {
    "/api/me": { body: await recorded("me.json") },
    "/api/freshness": { body: await recorded("freshness.json") },
    "/api/planned-packages/pkg-000000000001": { body: await recorded("planned-package-rural-roads.json") },
    "/api/comparables": { body: await recorded("comparables-planned-works-rfb-ke.json") },
    "/api/planned-packages/pkg-000000000001/risks": { body: await recorded("risks-planned-rural-roads.json") },
    "/api/planned-packages/pkg-000000000001/steps": { body: await recorded("steps-planned-rural-roads.json") },
    // Section 5, "Check your criteria" (ticket 31), reads its collapsed summary with the page.
    "/api/planned-packages/pkg-000000000001/criteria": { body: await recorded("criteria-summary-planned-rural-roads.json") },
    // Ticket 36: the page asks whether your team has suggested PPSD rows open on this package.
    "/api/drafts/existing": { body: '{"draft":null}' },
  });

  await page.goto("/packages/pkg-000000000001");

  await expect(page.locator("[data-plan-prompt]")).toBeVisible();
  await expect(page.locator("[data-past-range]")).not.toHaveAttribute("aria-busy", "true");
  // Section 3 (ticket 30) reads its risks once StrictMode's second mount asks again, too.
  await expect(page.locator("section#risks")).toHaveAttribute("data-risks", "no_reports");
  // Section 2 (ticket 27) reads its steps the same way: loaded, it is a collapsed section with its summary.
  await expect(page.locator("section#planned-dates")).toHaveAttribute("data-collapsed-section", "collapsed");
  expect(unrecorded).toEqual([]);
});
