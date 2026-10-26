// The app's frame on every page (seam 4, ticket 06): the navy bar with the World Bank logo, the
// band with the box and the data-freshness stamp in its five states, the page alerts, and the
// footer, against the mocked API. The words are the 06 design brief's.
import { createHash } from "node:crypto";
import type { Page } from "@playwright/test";
import { expect, mockShell, recorded, test } from "./mocked";

// web/src/assets/world-bank-logo.md: the official file's hash when it was downloaded.
const LOGO_SHA256 = "c11d30bf69ad0f6f224b350e93ea976bbac438ff18c82786d1c11454a0317aff";

// The stamp writes "Oct 21" in the current year, so the tests fix today.
const TODAY = new Date("2026-10-24T12:00:00Z");

// The Packages tab lists the viewer's packages and checked plans (ticket 15). An empty list keeps the tab's
// own alert, for a list it could not load, out of the page's alerts that these tests count.
async function noPlannedPackages(page: Page) {
  await page.route("**/api/planned-packages", async (route) =>
    route.fulfill({ contentType: "application/json", body: await recorded("planned-packages-empty.json") }),
  );
}

test("the navy bar carries the official World Bank Group logo, unaltered, 24 px tall with clear space of half its height", async ({ page }) => {
  await mockShell(page);
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");

  // worldbank.org's white mark is the World Bank Group logo, so its text alternative names the Group.
  const logo = page.getByRole("img", { name: "World Bank Group logo" });
  await expect(logo).toBeVisible();
  const file = await page.request.get(await logo.evaluate((img) => (img as HTMLImageElement).currentSrc));
  const body = await file.body();
  expect(createHash("sha256").update(body).digest("hex")).toBe(LOGO_SHA256);
  // White artwork, the file for dark backgrounds, so it reads on the navy bar.
  expect(new Set(body.toString().match(/fill="[^"]*"/g))).toEqual(new Set(['fill="#fff"', 'fill="none"']));
  // The logo is not a link.
  await expect(page.locator("a").filter({ has: logo })).toHaveCount(0);

  const bar = (await page.locator("[data-nav-bar]").boundingBox())!;
  const box = (await logo.boundingBox())!;
  const wordmark = (await page.getByRole("link", { name: "Strata", exact: true }).boundingBox())!;
  expect([box.width, box.height]).toEqual([120, 24]);
  expect(box.y - bar.y).toBeGreaterThanOrEqual(12);
  expect(bar.y + bar.height - (box.y + box.height)).toBeGreaterThanOrEqual(12);
  expect(Math.round(box.x)).toBe(72);
  // 24 px to the wordmark, so the logo and "Strata" never read as one co-branded name.
  expect(wordmark.x - (box.x + box.width)).toBeGreaterThanOrEqual(24);
});

test("one banner holds the Main navigation, the search landmark around the box and the stamp", async ({ page }) => {
  await mockShell(page);
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");

  const banner = page.getByRole("banner");
  await expect(banner).toHaveCount(1);
  await expect(banner.getByRole("navigation", { name: "Main" })).toHaveCount(1);
  await expect(banner.getByRole("search")).toHaveCount(1);
  await expect(banner.locator("[data-stamp]").getByRole("link")).toBeVisible();
  // The stamp's description is read once, through aria-describedby, and never as page text.
  await expect(page.getByText("Open the Data page.")).toBeHidden();
});

test("the first paint holds the bar, the band and the logo where the app puts them, before any script runs", async ({ browser, page }) => {
  const boxes = (selectors: string[]) =>
    selectors.map((selector) => {
      const box = document.querySelector(selector)!.getBoundingClientRect();
      return [Math.round(box.x), Math.round(box.y), Math.round(box.width), Math.round(box.height)];
    });
  await mockShell(page);
  for (const width of [1440, 800, 390]) {
    const first = await browser.newContext({ javaScriptEnabled: false, viewport: { width, height: 900 } });
    const before = await first.newPage();
    await before.goto(test.info().project.use.baseURL!);
    const painted = await before.evaluate(boxes, ["[data-boot-bar]", "[data-boot-band]", "[data-boot-bar] img"]);
    await first.close();

    await page.setViewportSize({ width, height: 900 });
    await page.goto("/");
    await expect(page.locator("[data-stamp]").getByRole("link")).toBeVisible();
    const mounted = await page.evaluate(boxes, ["[data-nav-bar]", "[data-box-band]", "[data-nav-bar] img"]);

    expect(painted, `${width} px`).toEqual(mounted);
  }
});

test("the stamp shows the day the server returns, and links to the Data page", async ({ page }) => {
  await page.clock.setFixedTime(TODAY);
  await mockShell(page);
  await page.goto("/");

  const stamp = page.locator("[data-stamp]").getByRole("link");
  await expect(stamp).toHaveText("Data through Oct 23");
  await expect(stamp).toHaveAttribute("href", "/data");
  await expect(stamp).toHaveAccessibleDescription("Open the Data page.");
  await expect(page.locator("[data-stamp]")).not.toHaveAttribute("aria-busy");
});

test("a data date from another year shows its year", async ({ page }) => {
  await page.clock.setFixedTime(TODAY);
  await mockShell(page, { freshness: { body: '{"data_through": "2025-12-30"}' } });
  await page.goto("/");

  await expect(page.locator("[data-stamp]").getByRole("link")).toHaveText("Data through Dec 30, 2025");
});

test("before any daily source has loaded, the stamp says no data are loaded and still links to the Data page", async ({ page }) => {
  await mockShell(page, { freshness: { body: await recorded("freshness-empty.json") } });
  await page.goto("/");

  await expect(page.locator("[data-stamp]").getByRole("link")).toHaveText("No data loaded yet");
  await expect(page.locator("[data-stamp]").getByRole("link")).toHaveAttribute("href", "/data");
});

test("while it loads, the stamp holds a static bar for the first second and then says it is reading the date", async ({ page }) => {
  await mockShell(page);
  let answer: () => void = () => {};
  const answered = new Promise<void>((resolve) => (answer = resolve));
  await page.route("**/api/freshness", async (route) => {
    await answered;
    await route.fulfill({ status: 200, contentType: "application/json", body: await recorded("freshness.json") });
  });
  await page.goto("/");

  const stamp = page.locator("[data-stamp]");
  await expect(stamp).toHaveAttribute("aria-busy", "true");
  await expect(stamp.locator("[data-skeleton]")).toHaveCount(1);
  await expect(stamp).toHaveText("Reading the data date", { timeout: 3000 });
  answer();
  await expect(stamp.getByRole("link")).toHaveText(/^Data through /);
});

test("when the server fails, the stamp says it can't read the date, and tries again on a later page at most once a minute", async ({ page }) => {
  await page.clock.install({ time: TODAY });
  await mockShell(page);
  let reads = 0;
  await page.route("**/api/freshness", async (route) => {
    reads += 1;
    if (reads === 1) return route.fulfill({ status: 502, contentType: "application/json", body: '{"code": "unreadable"}' });
    return route.fulfill({ status: 200, contentType: "application/json", body: await recorded("freshness.json") });
  });
  await page.goto("/");

  const stamp = page.locator("[data-stamp]");
  await expect(stamp).toHaveText("I can't read the data date.");
  await expect(stamp.getByRole("link")).toHaveCount(0);
  await expect(stamp.locator("svg.lucide-circle-x")).toHaveCount(1);

  const tabs = page.getByRole("navigation", { name: "Main" });
  await tabs.getByRole("link", { name: "Packages" }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Packages");
  expect(reads).toBe(1);

  await page.clock.fastForward("01:01");
  await tabs.getByRole("link", { name: "Projects" }).click();
  await expect(stamp.getByRole("link")).toHaveText("Data through Oct 23");
  expect(reads).toBe(2);
});

test("an account the warehouse refuses gets one error alert that says how to get access", async ({ page }) => {
  await mockShell(page, { freshness: { status: 403, body: await recorded("freshness-no-access.json") } });
  await noPlannedPackages(page);
  await page.goto("/packages");

  await expect(page.getByRole("alert")).toHaveText(
    "Your account can't read the data I hold yet; ask the person who shared Strata with you for access.",
  );
  await expect(page.locator("[data-stamp]")).toHaveText("I can't read the data date.");
});

test("while the stamp tries again, the access alert stays where it is, so it is not announced twice", async ({ page }) => {
  await page.clock.install({ time: TODAY });
  await mockShell(page);
  // The Packages tab lists the viewer's packages (ticket 15); an empty list keeps its own alert out of the count.
  await page.route("**/api/planned-packages", async (route) =>
    route.fulfill({ contentType: "application/json", body: await recorded("planned-packages-empty.json") }),
  );
  let reads = 0;
  let answer: () => void = () => {};
  const answered = new Promise<void>((resolve) => (answer = resolve));
  await page.route("**/api/freshness", async (route) => {
    reads += 1;
    if (reads > 1) await answered;
    await route.fulfill({ status: 403, contentType: "application/json", body: await recorded("freshness-no-access.json") });
  });
  await page.goto("/");
  const alert = page.getByRole("alert");
  await expect(alert).toHaveCount(1);

  await page.clock.fastForward("01:01");
  await page.getByRole("navigation", { name: "Main" }).getByRole("link", { name: "Packages" }).click();

  await expect(page.locator("[data-stamp]")).toHaveText("Reading the data date");
  await expect(alert).toHaveCount(1);
  answer();
  await expect(page.locator("[data-stamp]")).toHaveText("I can't read the data date.");
  await expect(alert).toHaveCount(1);
  expect(reads).toBe(2);
});

test("with no forwarded identity, one error alert says to open Strata from its link in the workspace", async ({ page }) => {
  await mockShell(page, {
    me: { body: '{"email": null, "name": null, "signed_in": false, "has_token": false}' },
    freshness: { status: 401, body: await recorded("freshness-no-identity.json") },
  });
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");

  await expect(page.getByRole("alert")).toHaveText(
    "I can't tell who you are, so I can't read any data; open Strata from its link in the workspace.",
  );
  await page.getByRole("button", { name: "View: World Bank staff" }).click();
  await expect(page.getByRole("dialog", { name: "Your view" })).toContainText("You are not signed in.");
});

test("the view popover says who is signed in and offers each view as a link, with yours current", async ({ page }) => {
  await mockShell(page);
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");

  await page.getByRole("button", { name: "View: World Bank staff" }).click();

  // Who is viewing comes first, then the views as link rows and the past date (ticket 40), then the language of answers
  // and drafts (ticket 42).
  const dialog = page.getByRole("dialog", { name: "Your view" });
  await expect(dialog.locator("[data-view-popover] p").first()).toHaveText("Signed in as ana.example@worldbank.org");
  await expect(dialog.locator("[data-view-row]")).toHaveText([
    "World Bank staffYour own view, with everything I show.",
    "Implementing agency officerA preview of what an officer at the Northern Water Works Development Agency (NWWDA) sees.",
    "The publicA preview of what a member of the public sees. It has projects, lessons and data only.",
  ]);
  const own = dialog.getByRole("link", { name: "World Bank staff" });
  await expect(own).toHaveAttribute("aria-current", "true");
  await expect(own).toBeFocused();
  await expect(dialog.getByRole("link", { name: "The public" })).toHaveAttribute("href", "/?view=public");
  await expect(dialog.getByRole("group")).toHaveAccessibleName("Language of answers and drafts");
});

test("Tab in the view popover closes it and moves on to the box; Shift+Tab closes it and returns to the pill", async ({ page }) => {
  await mockShell(page);
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  const pill = page.getByRole("button", { name: "View: World Bank staff" });

  await pill.click();
  await expect(page.getByRole("dialog", { name: "Your view" })).toBeVisible();
  // Tab moves through the view rows, the past date and the language group (tickets 40 and 42); past the last control
  // it leaves the popover for the box.
  await expect(page.getByRole("link", { name: "World Bank staff" })).toBeFocused();
  for (let press = 0; press < 12 && (await page.getByRole("dialog").count()) > 0; press += 1) await page.keyboard.press("Tab");

  await expect(page.locator("[data-box-band]").getByRole("combobox")).toBeFocused();
  await expect(page.getByRole("dialog")).toHaveCount(0);

  await pill.click();
  await expect(page.getByRole("dialog", { name: "Your view" })).toBeVisible();
  await page.keyboard.press("Shift+Tab");

  await expect(pill).toBeFocused();
  await expect(page.getByRole("dialog")).toHaveCount(0);
});

// The view switch's banners and the alerts for what the server could not apply (ticket 40; the 40 brief, 6.2 and 6.3).
const ADDRESS_ALERTS: [string, string][] = [
  ["?view=piu", "Preview of what an implementing agency officer at the Northern Water Works Development Agency (NWWDA) sees. You are still signed in as yourself."],
  ["?view=public", "Preview of what the public sees. You are still signed in as yourself."],
  ["?view=board", "I don't know the view in this link, so you are seeing the World Bank staff view."],
  ["?asof=2016-08-26", "I'm showing this page as of August 26, 2016. I use only what was disclosed by that date."],
  ["?asof=last-tuesday", "I can't read the date in this link, so you are seeing today's data."],
];

for (const [query, sentence] of ADDRESS_ALERTS) {
  test(`a link with ${query} says so above the title`, async ({ page }) => {
    await mockShell(page);
    await page.goto(`/${query}`);

    const alert = page.locator("[data-alert=info]");
    await expect(alert.locator("p").first()).toHaveText(sentence);
    const [alertBox, title] = [await alert.boundingBox(), await page.getByRole("heading", { level: 1 }).boundingBox()];
    expect(alertBox!.y).toBeLessThan(title!.y);
  });
}

test("a link with ?view=staff, ?lang= or ?evidence= shows no alert", async ({ page }) => {
  await mockShell(page);
  await noPlannedPackages(page);
  await page.goto("/packages?view=staff&lang=fr&evidence=ev-1");

  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Packages");
  // The page's alert slot stays empty; the evidence drawer beside the page answers ?evidence= itself.
  await expect(page.getByRole("main").locator("[data-alert]")).toHaveCount(0);
});

test("error alerts come before the address's info alerts", async ({ page }) => {
  await mockShell(page, { freshness: { status: 403, body: await recorded("freshness-no-access.json") } });
  await page.goto("/?view=public&asof=2016-08-26");

  await expect(page.locator("[data-alert]")).toHaveCount(3);
  await expect(page.locator("[data-alert]").first()).toHaveAttribute("data-alert", "error");
});

test("a Menu row's focus ring ends 2 px inside the panel, so the panel edge never clips it", async ({ page }) => {
  await mockShell(page);
  await page.setViewportSize({ width: 390, height: 900 });
  await page.goto("/packages");
  await page.getByRole("button", { name: "Menu" }).click();
  await page.keyboard.press("Tab");

  const row = page.getByRole("navigation", { name: "Main" }).getByRole("link", { name: "Packages" });
  await expect(row).toBeFocused();
  const ring = await row.evaluate((el) => {
    const style = getComputedStyle(el);
    const box = el.getBoundingClientRect();
    const reach = parseFloat(style.outlineOffset) + parseFloat(style.outlineWidth);
    return { left: box.left - reach, right: box.right + reach, style: style.outlineStyle };
  });
  expect(ring.style).toBe("solid");
  expect(ring.left).toBe(2);
  expect(ring.right).toBe(388);
  // The row's text still starts on the grid margin, 28 px in at 390 px.
  const text = await row.evaluate((el) => el.getBoundingClientRect().left + parseFloat(getComputedStyle(el).paddingLeft));
  expect(text).toBe(28);
});

// An element's last line of text: how wide it is, as a share of the widest line, and how many words it holds.
const lastLine = (el: Element) => {
  const lines = new Map<number, { left: number; right: number; words: number }>();
  const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
  for (let node = walker.nextNode(); node; node = walker.nextNode()) {
    for (const word of node.textContent!.matchAll(/\S+/g)) {
      const range = document.createRange();
      range.setStart(node, word.index!);
      range.setEnd(node, word.index! + word[0].length);
      const box = range.getClientRects()[0];
      const top = Math.round(box.top);
      const line = lines.get(top) ?? { left: box.left, right: box.right, words: 0 };
      lines.set(top, { left: Math.min(line.left, box.left), right: Math.max(line.right, box.right), words: line.words + 1 });
    }
  }
  const sorted = [...lines.entries()].sort(([a], [b]) => a - b).map(([, line]) => line);
  const last = sorted[sorted.length - 1];
  const widest = Math.max(...sorted.map((line) => line.right - line.left));
  return { share: (last.right - last.left) / widest, words: last.words };
};

for (const width of [390, 320]) {
  test(`at ${width} px the Home card's title wraps into even lines, and the Menu's view line never ends on one word`, async ({ page }) => {
    // Home's first run (ticket 41): its empty-state card, as a viewer who follows nothing sees it.
    await mockShell(page, { home: { body: await recorded("home-first-run.json") } });
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/");

    const title = page.locator("[data-empty-state]").getByRole("heading");
    await expect(title).toHaveText("I brief you on the projects you follow.");
    expect((await title.evaluate(lastLine)).share).toBeGreaterThan(0.5);

    // The Menu's view rows wrap with text-pretty, so no description ends on one word (ticket 40).
    await page.getByRole("button", { name: "Menu" }).click();
    const view = page.locator("[data-menu-panel]").getByText("A preview of what a member of the public sees. It has projects, lessons and data only.");
    await expect(view).toBeVisible();
    expect((await view.evaluate(lastLine)).words).toBeGreaterThan(1);
  });
}

test("/ closes an open Menu and focuses the box", async ({ page }) => {
  await mockShell(page);
  await page.setViewportSize({ width: 390, height: 900 });
  await page.goto("/");
  await page.getByRole("button", { name: "Menu" }).click();
  await page.getByRole("heading", { level: 1 }).click();

  await page.keyboard.press("/");

  await expect(page.getByRole("button", { name: "Menu" })).toHaveAttribute("aria-expanded", "false");
  await expect(page.locator("[data-box-band]").getByRole("combobox")).toBeFocused();
});
