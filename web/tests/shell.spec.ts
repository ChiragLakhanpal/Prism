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

  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");

  await expect(page.getByText("You are not signed in. Open Strata through its Databricks App to sign in.")).toBeVisible();
  // The view popover agrees: it does not suggest the viewer signed in with some account.
  await page.getByRole("button", { name: "View: World Bank staff" }).click();
  const view = page.getByRole("dialog", { name: "Your view" });
  await expect(view).toContainText("You are not signed in.");
  await expect(view).not.toContainText("I can't tell which account");
});

test("the shell says so in an error alert when it can't reach the server, and Try again asks again", async ({ page }) => {
  let calls = 0;
  await page.route("**/api/me", async (route) => {
    calls += 1;
    if (calls === 1) return route.fulfill({ status: 502, contentType: "application/json", body: JSON.stringify({ detail: "Bad Gateway" }) });
    return route.fulfill({ status: 200, contentType: "application/json", body: await recorded("me.json") });
  });

  await page.goto("/");

  const alert = page.getByRole("alert");
  await expect(alert).toHaveText(/^The server did not answer, so I can't tell who you are\.Try again$/);
  expect(await alert.evaluate((el) => getComputedStyle(el).backgroundColor)).toBe("rgb(253, 242, 242)");
  await alert.getByRole("button", { name: "Try again" }).click();
  await expect(page.getByText("You are signed in as Ana Example.")).toBeVisible();
  await expect(page.getByRole("alert")).toHaveCount(0);
});

test("the shell sits in the shared frame: the navy bar, the box band, a styled title and one left edge", async ({ page }) => {
  await mockApi(page, { "/api/me": { body: await recorded("me.json") } });
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");

  await expect(page.locator("[data-nav-bar]")).toBeVisible();
  await expect(page.getByRole("link", { name: "Strata", exact: true })).toHaveAttribute("aria-current", "page");
  await expect(page.locator("[data-box-band]").getByRole("textbox", { name: /Search a project/ })).toBeVisible();
  const title = page.getByRole("heading", { level: 1 });
  expect(await title.evaluate((el) => getComputedStyle(el).fontSize)).toBe("28px");
  // The title, the viewer line and the footer's text all start at the 72 px grid margin.
  const left = (selector: string) =>
    page.locator(selector).first().evaluate((el) => Math.round(el.getBoundingClientRect().x + parseFloat(getComputedStyle(el).paddingLeft)));
  expect([await left("h1"), await left("main p"), await left("footer p")]).toEqual([72, 72, 72]);
  // The skip link is out of sight until it has focus.
  const skip = page.getByRole("link", { name: "Skip to the main content" });
  expect((await skip.boundingBox())!.width).toBeLessThanOrEqual(1);
  await page.keyboard.press("Tab");
  await expect(skip).toBeFocused();
  expect((await skip.boundingBox())!.height).toBe(44);
});

test("axe finds no WCAG 2.2 AA violations in the shell, signed in or unable to reach the server", async ({ page }) => {
  const { default: AxeBuilder } = await import("@axe-core/playwright");
  const check = async () =>
    (await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"]).analyze()).violations.map(
      (v) => `${v.id}: ${v.nodes.map((node) => node.target.join(" ")).join(", ")}`,
    );
  for (const [width, response] of [
    [1440, { body: await recorded("me.json") }],
    [390, { status: 502, body: JSON.stringify({ detail: "Bad Gateway" }) }],
  ] as const) {
    await page.unrouteAll();
    await mockApi(page, { "/api/me": response });
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/");
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await expect(page.locator("main [role=status], main [role=alert]")).not.toHaveText("I'm checking who you are.");
    expect(await check(), `${width} px`).toEqual([]);
  }
});
