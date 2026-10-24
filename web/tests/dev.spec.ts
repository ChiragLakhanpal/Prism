// The evidence drawer in the development build (ticket 14's design review, round 1). scripts/dev serves
// the app through Vite's dev server, where React's StrictMode mounts each component, unmounts it and
// mounts it again, so every effect runs twice. The panel asks for live code changes on scripts/dev, so
// the drawer must behave there as it does in production: focus moves to its heading and stays, the
// evidence card closes, the opening is recorded once, and closing goes back one history entry.
//
// This file runs in the "dev" project of playwright.config.ts, against `vite` rather than `vite
// preview`. It holds only what StrictMode can break; answer.spec.ts covers the rest.
import { askFromTheBox, drawer, ICR_54, landed, marker, open } from "./answer-page";
import { expect, test } from "./mocked";

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
