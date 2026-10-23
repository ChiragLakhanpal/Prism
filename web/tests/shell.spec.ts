// Smoke test of the web shell (seam 4): the built app against the mocked API.
import { expect, mockApi, recorded, test } from "./mocked";

// DESIGN.md section 8, word for word.
const FOOTER =
  "Strata is an independent demo built on World Bank open data. It is not a World Bank product, " +
  "and the World Bank has not reviewed or endorsed it.";

test("the shell renders, names the signed-in viewer and carries the footer", async ({ page, outsideRequests }) => {
  const unrecorded = await mockApi(page, { "/api/me": { body: await recorded("me.json") } });

  await page.goto("/");

  await expect(page.getByRole("heading", { level: 1, name: "Strata" })).toBeVisible();
  await expect(page.getByText("You are signed in as Ana Example.")).toBeVisible();
  await expect(page.getByRole("contentinfo")).toHaveText(FOOTER);
  await expect(page.getByRole("link", { name: "Skip to the main content" })).toHaveAttribute("href", "#main");
  expect(unrecorded).toEqual([]);
  expect(outsideRequests).toEqual([]);
});

test("nothing in the shell links to the deck", async ({ page }) => {
  await mockApi(page, { "/api/me": { body: await recorded("me.json") } });

  await page.goto("/");
  await expect(page.getByText("You are signed in as Ana Example.")).toBeVisible();

  await expect(page.locator('a[href*="/present"]')).toHaveCount(0);
});

test("the shell says so when no one is signed in", async ({ page }) => {
  await mockApi(page, {
    "/api/me": { body: JSON.stringify({ email: null, name: null, signed_in: false, has_token: false }) },
  });

  await page.goto("/");

  await expect(page.getByText("You are not signed in. Open Strata through its Databricks App to sign in.")).toBeVisible();
});

test("the shell says so when it can't reach the server", async ({ page }) => {
  await mockApi(page, { "/api/me": { status: 502, body: JSON.stringify({ detail: "Bad Gateway" }) } });

  await page.goto("/");

  await expect(page.getByText("I can't reach Strata's server. Try again in a minute.")).toBeVisible();
});
