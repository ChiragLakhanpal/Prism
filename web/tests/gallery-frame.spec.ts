// The gallery's navigation, box band and footer match the blueprint's Home wireframe and
// DESIGN.md sections 5 and 8 (criteria 3 and 4 of ticket 02).
import { expect, test } from "./mocked";
import { footerSentence } from "./design-md";
import { galleryPaths } from "./gallery-pages";

const NAVY = "rgb(0, 34, 68)";
const WHITE = "rgb(255, 255, 255)";

test("the navy bar is 56 px tall with the logo slot, the wordmark, five tabs in order and the view pill", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/gallery/navigation");

  const bar = page.locator("[data-nav-bar]");
  const box = (await bar.boundingBox())!;
  expect(box.height).toBe(56);
  expect(await bar.evaluate((el) => getComputedStyle(el).backgroundColor)).toBe(NAVY);

  const main = page.getByRole("navigation", { name: "Main" });
  await expect(main.getByRole("link")).toHaveText(["Packages", "Projects", "Lessons", "Drafts", "Data"]);
  await expect(main.getByRole("link", { name: "Projects" })).toHaveAttribute("aria-current", "page");

  // Logo at least 24 px tall, with clear space of half its height on every side.
  const logo = (await page.locator("[data-logo]").boundingBox())!;
  const wordmark = (await page.getByRole("link", { name: "Strata", exact: true }).boundingBox())!;
  expect(logo.height).toBeGreaterThanOrEqual(24);
  const clear = logo.height / 2;
  expect(logo.y - box.y).toBeGreaterThanOrEqual(clear);
  expect(box.y + box.height - (logo.y + logo.height)).toBeGreaterThanOrEqual(clear);
  expect(logo.x).toBeGreaterThanOrEqual(clear);
  expect(wordmark.x - (logo.x + logo.width)).toBeGreaterThanOrEqual(clear);

  // Left to right: logo, wordmark, tabs, then the pill at the right edge of the grid (72 px margin).
  const tabs = await main.getByRole("link").evaluateAll((links) => links.map((link) => link.getBoundingClientRect().x));
  const pill = page.getByRole("button", { name: "View: World Bank staff" });
  const pillBox = (await pill.boundingBox())!;
  expect(wordmark.x).toBeGreaterThan(logo.x);
  expect(tabs[0]).toBeGreaterThan(wordmark.x + wordmark.width);
  expect(tabs).toEqual([...tabs].sort((a, b) => a - b));
  expect(pillBox.x).toBeGreaterThan(tabs[4]);
  expect(Math.round(1440 - (pillBox.x + pillBox.width))).toBe(72);
  await expect(pill.locator("svg.lucide-chevron-down")).toHaveCount(1);
});

test("the selected tab on the navy bar has a 3 px white underline, and the others none", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/gallery/navigation");
  const main = page.getByRole("navigation", { name: "Main" });

  const underline = (name: string) =>
    main.getByRole("link", { name }).evaluate((link) => {
      const after = getComputedStyle(link, "::after");
      return { height: after.height, color: after.backgroundColor };
    });
  expect(await underline("Projects")).toEqual({ height: "3px", color: WHITE });
  expect((await underline("Lessons")).color).toBe("rgba(0, 0, 0, 0)");
});

test("the band holds the box over columns 1 to 8 and the stamp at the right, and / focuses the box", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/gallery/navigation");

  const band = (await page.locator("[data-box-band]").boundingBox())!;
  expect(band.height).toBeGreaterThanOrEqual(69);
  const box = (await page.locator("[data-box-band] [data-focus-ring]").boundingBox())!;
  const stamp = (await page.locator("[data-box-band] [data-stamp] a").boundingBox())!;
  // Content is 1296 px wide: 12 columns and 11 gutters of 32 px. The box ends after column 8.
  const column = (1296 - 11 * 32) / 12;
  expect(Math.round(box.x)).toBe(72);
  expect(Math.round(box.x + box.width)).toBe(Math.round(72 + 8 * column + 7 * 32));
  expect(Math.round(stamp.x + stamp.width)).toBe(1440 - 72);
  await expect(page.locator("[data-box-band] [data-stamp] a")).toHaveText("Data through Oct 21");

  await page.locator("h1").click();
  await page.keyboard.press("/");
  await expect(page.locator("[data-box-band]").getByRole("textbox", { name: /Search a project/ })).toBeFocused();
});

test("below 1024 px a labelled Menu holds the tabs and the view lines, and Escape closes it", async ({ page }) => {
  await page.setViewportSize({ width: 1023, height: 900 });
  await page.goto("/gallery/navigation");
  await expect(page.getByRole("button", { name: "View: World Bank staff" })).toBeHidden();

  const menu = page.getByRole("button", { name: "Menu" });
  await expect(menu).toHaveAttribute("aria-expanded", "false");
  await menu.click();
  await expect(menu).toHaveAttribute("aria-expanded", "true");
  const main = page.getByRole("navigation", { name: "Main" });
  await expect(main.getByRole("link")).toHaveText(["Packages", "Projects", "Lessons", "Drafts", "Data"]);
  await expect(page.getByText("You are seeing the World Bank staff view.")).toBeVisible();

  await main.getByRole("link", { name: "Lessons" }).focus();
  await page.keyboard.press("Escape");
  await expect(menu).toHaveAttribute("aria-expanded", "false");
  await expect(menu).toBeFocused();

  await page.setViewportSize({ width: 1024, height: 900 });
  await expect(page.getByRole("button", { name: "View: World Bank staff" })).toBeVisible();
  await expect(menu).toBeHidden();
});

test("at 1024 px the whole bar fits on one line, with no overflow", async ({ page }) => {
  await page.setViewportSize({ width: 1024, height: 900 });
  await page.goto("/gallery/navigation");
  const bar = page.locator("[data-nav-bar] > .layout");
  expect(await bar.evaluate((el) => el.scrollWidth <= el.clientWidth)).toBe(true);
  expect((await page.locator("[data-nav-bar]").boundingBox())!.height).toBe(56);
});

test("the view pill opens who is signed in and which view this is", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/gallery/navigation");
  await page.getByRole("button", { name: "View: World Bank staff" }).click();
  const dialog = page.getByRole("dialog", { name: "Your view" });
  await expect(dialog).toContainText("Signed in as ana.example@worldbank.org");
  await expect(dialog).toContainText("You are seeing the World Bank staff view.");
  await page.keyboard.press("Escape");
  await expect(dialog).toBeHidden();
  await expect(page.getByRole("button", { name: "View: World Bank staff" })).toBeFocused();
});

test("the footer reads DESIGN.md section 8's disclaimer word for word on every page the gallery renders", async ({ page }) => {
  const footer = await footerSentence();
  const paths = await galleryPaths(page);
  expect(paths.length).toBeGreaterThan(10);
  for (const path of paths) {
    await page.goto(path);
    await expect(page.getByRole("contentinfo"), path).toHaveText(footer);
  }
});
