// The number tooltip (ticket 96; DESIGN.md section 5, Number tooltip), at seam 4: what a number is, where it came from
// and what a click does, on the package workspace of KE-NWWDA-541055-CW-RFB against the answers the server recorded on
// the fixture. The words are the ticket's and the design plan's (plan.md 8.6), copied here so the test checks the copy
// file against an independent source; the numbers are tests/ground_truth/values.toml's [past_range].
//
// The timing tests stop the page's clock once the page is ready and move it with runFor, so a busy computer's pauses
// never count as a pointer resting (the way tests/package.spec.ts times a dot's rest).
import type { Locator, Page } from "@playwright/test";
import { scan } from "./axe";
import { expect, mockApi, recorded, test } from "./mocked";
import { fontsLoaded } from "./settled";

const REF = "KE-NWWDA-541055-CW-RFB";
const API = `/api/packages/${REF}`;
const RECORDS = "From Procurement Notices and Contract Awards, through October 13, 2026.";

async function openPackage(page: Page, width = 1440) {
  await page.setViewportSize({ width, height: 900 });
  await mockApi(page, {
    "/api/me": { body: await recorded("me.json") },
    "/api/freshness": { body: await recorded("freshness.json") },
    [API]: { body: await recorded("package-ke-nwwda-541055.json") },
    [`${API}/comparables`]: { body: await recorded("comparables-ke-nwwda-541055.json") },
    [`${API}/risks`]: { body: await recorded("risks-ke-nwwda-541055.json") },
    [`${API}/steps`]: { body: await recorded("steps-ke-nwwda-541055.json") },
    [`${API}/estimate`]: { body: await recorded("estimate-ke-nwwda-541055.json") },
    [`${API}/rebidding`]: { body: await recorded("rebidding-ke-nwwda-541055.json") },
    [`${API}/criteria`]: { body: await recorded("criteria-summary-ke-nwwda-541055.json") },
    "/api/drafts/existing": { body: '{"draft":null}' },
    "/api/evidence/opened": { body: '{"opened":[],"recorded":true}' },
  });
  await page.goto(`/packages/${REF}`);
  await expect(page.locator("[data-past-range]:not([data-past-range=loading])")).toBeVisible();
  await expect(page.locator("[data-lane2=loading]")).toHaveCount(0);
  await fontsLoaded(page);
}

// The finding's numbers: "2 of 49 comparable packages, fewer than 1 in 10, were signed within the plan's 1.5 months."
const finding = (page: Page) => page.locator("[data-past-range] [data-finding]");
const num = (scope: Locator, text: string) => scope.locator("button[data-num]").filter({ hasText: new RegExp(`^${text}$`) });
const tooltip = (page: Page) => page.getByRole("tooltip");

// Stops the page's clock where it is, so only runFor moves the page's timers on.
async function stopTheClock(page: Page) {
  const now = await page.evaluate(() => Date.now());
  await page.clock.pauseAt(now + 1000);
}

async function pointAt(page: Page, target: Locator) {
  const box = (await target.boundingBox())!;
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
}

test("hovering 49 shows nothing at 60 ms and its three parts by 260 ms, and 2 then shows its own sentence at once", async ({ page }) => {
  await page.clock.install();
  await openPackage(page);
  const all = num(finding(page), "49");
  await all.scrollIntoViewIfNeeded();
  await stopTheClock(page);

  await pointAt(page, all);
  await page.clock.runFor(60);
  await expect(tooltip(page)).toHaveCount(0);
  await page.clock.runFor(200);
  await expect(tooltip(page)).toHaveText(
    "All comparable packages in the past range, including the four still open." + RECORDS + "Select to see all 49.",
  );
  await expect(tooltip(page).locator("[data-num-what]")).toHaveText("All comparable packages in the past range, including the four still open.");
  await expect(tooltip(page).locator("[data-num-from]")).toHaveText(RECORDS);
  await expect(tooltip(page).locator("[data-num-act]")).toHaveText("Select to see all 49.");
  // The tooltip is the number's description, never its name.
  await expect(all).toHaveAccessibleName("49");
  await expect(all).toHaveAccessibleDescription(/^All comparable packages in the past range/);

  // Along the sentence to "2": its own sentence, at once, with no movement.
  await pointAt(page, num(finding(page), "2"));
  await expect(tooltip(page).locator("[data-num-what]")).toHaveText("Comparable packages signed within 1.5 months of their notice.");
  await expect(tooltip(page)).toHaveAttribute("data-instant", "");

  // Off the numbers: it hides 100 ms after the pointer leaves, and a number reached within 300 ms opens at once.
  await page.mouse.move(4, 4);
  await page.clock.runFor(90);
  await expect(tooltip(page)).toHaveCount(1);
  await page.clock.runFor(20);
  await expect(tooltip(page)).toHaveCount(0);
  await page.clock.runFor(150);
  await pointAt(page, all);
  await expect(tooltip(page).locator("[data-num-what]")).toHaveText(/^All comparable packages/);
  await expect(tooltip(page)).toHaveAttribute("data-instant", "");
});

test("keyboard focus shows a tooltip at once, Escape hides it until the focus leaves, and under reduced motion nothing moves", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.clock.install();
  await openPackage(page);
  await stopTheClock(page);
  const two = num(finding(page), "2");
  const all = num(finding(page), "49");

  await two.focus();
  await expect(tooltip(page).locator("[data-num-what]")).toHaveText("Comparable packages signed within 1.5 months of their notice.");
  await page.keyboard.press("Escape");
  await expect(tooltip(page)).toHaveCount(0);
  await expect(two).toBeFocused();
  // Hidden until the focus leaves: a pointer resting on it opens nothing.
  await pointAt(page, two);
  await page.clock.runFor(400);
  await expect(tooltip(page)).toHaveCount(0);
  await page.mouse.move(4, 4);
  await page.keyboard.press("Tab");
  await expect(all).toBeFocused();
  await expect(tooltip(page).locator("[data-num-what]")).toHaveText(/^All comparable packages/);
  await page.keyboard.press("Shift+Tab");
  await expect(tooltip(page).locator("[data-num-what]")).toHaveText("Comparable packages signed within 1.5 months of their notice.");

  // Under reduced motion the tooltip opened by a resting pointer, with no other open before it, moves nothing.
  await page.locator("body").evaluate((body) => (document.activeElement as HTMLElement | null)?.blur());
  await page.clock.runFor(400);
  await pointAt(page, all);
  await page.clock.runFor(200);
  await expect(tooltip(page)).not.toHaveAttribute("data-instant");
  expect(await tooltip(page).evaluate((tip) => [getComputedStyle(tip).transitionDuration, tip.getAnimations().length])).toEqual(["0s", 0]);
});

test("a number inside the finding opens its tooltip under the whole finding, left aligned with it, at 1440 and 390 px", async ({ page }) => {
  for (const width of [1440, 390]) {
    await openPackage(page, width);
    const whole = finding(page);
    await whole.evaluate((element) => element.scrollIntoView({ block: "start" }));
    for (const text of ["2", "49"]) {
      const number = num(whole, text);
      await number.hover();
      await expect(tooltip(page).locator("[data-num-what]")).toBeVisible();
      await expect(tooltip(page)).toHaveAttribute("data-side", "bottom");
      const [tip, sentence, own] = [(await tooltip(page).boundingBox())!, (await whole.boundingBox())!, (await number.boundingBox())!];
      expect(Math.round(tip.y - (sentence.y + sentence.height)), `${text} at ${width} px: 8 px under the finding`).toBe(8);
      // Left aligned with the number, or as far left as keeps it 16 px inside the window's right edge.
      const aligned = Math.abs(tip.x - own.x) < 1 || (tip.x < own.x && Math.abs(tip.x + tip.width - (width - 16)) < 1);
      expect(aligned, `${text} at ${width} px: left aligned with the number (${tip.x}, ${own.x})`).toBe(true);
      await page.mouse.move(2, 2);
      await expect(tooltip(page)).toHaveCount(0);
    }
  }
});

test("after a press scrolls the page, a number scrolled under the resting pointer opens nothing until the pointer moves", async ({ page }) => {
  await page.clock.install();
  await openPackage(page);
  await stopTheClock(page);
  const all = num(finding(page), "49");
  await all.evaluate((element) => element.scrollIntoView({ block: "center" }));
  const box = (await all.boundingBox())!;
  const pointer = { x: box.x + box.width / 2, y: box.y + box.height / 2 };
  await page.mouse.move(pointer.x, pointer.y);
  await page.clock.runFor(200);
  await expect(tooltip(page)).toHaveCount(1);
  // The press opens the table and moves focus to its caption, which scrolls the page.
  await page.mouse.down();
  await page.mouse.up();
  await page.clock.runFor(50);
  await expect(page.locator("[data-comparables-table]")).toBeVisible();
  await expect(tooltip(page)).toHaveCount(0);
  // The pointer rests on no number, straight above or below a number of the summary; then the page scrolls that number
  // under it, as a press that lands on rows does.
  const median = num(page.locator("[data-summary]"), "4.4");
  const x = await median.evaluate((element) => element.getBoundingClientRect().left + element.getBoundingClientRect().width / 2);
  const y = await page.evaluate((x) => [450, 300, 600, 200, 700].find((y) => !document.elementFromPoint(x, y)?.closest("[data-num]"))!, x);
  await page.mouse.move(x, y);
  await page.clock.runFor(400);
  await expect(tooltip(page)).toHaveCount(0);
  await median.evaluate((element, y) => window.scrollBy(0, element.getBoundingClientRect().top + element.getBoundingClientRect().height / 2 - y), y);
  // The browser has told the page the number is under the pointer.
  await expect.poll(() => median.evaluate((element) => element.matches(":hover"))).toBe(true);
  await page.clock.runFor(400);
  const at = (await median.boundingBox())!;
  expect(Math.abs(at.y + at.height / 2 - y)).toBeLessThan(2);
  await expect(tooltip(page)).toHaveCount(0);
  // Once the pointer moves over it, it opens as a resting pointer's tooltip does.
  await page.mouse.move(x + 1, y + 1);
  await page.clock.runFor(200);
  await expect(tooltip(page).locator("[data-num-what]")).toHaveText(/^The middle package's months\./);
});

test("a dot's tooltip gives its reference, months, a sentence with full dates, the From line and its action, above or below every dot, hidden from screen readers", async ({ page }) => {
  await openPackage(page);
  const group = page.getByRole("group", { name: "49 comparable packages, one dot each" });
  // KE-NWWDA-229129-CW-RFB: its notice of September 17, 2021, signed January 3, 2022, after 3.5 months.
  const dot = group.getByRole("img", { name: /^KE-NWWDA-229129-CW-RFB,/ });
  const tip = page.locator("[data-dot-tooltip]");
  const sentence = "Kenya. Its notice was published September 17, 2021, and its contract was signed January 3, 2022.";
  await dot.focus();
  await expect(tip.locator("p")).toHaveText(["KE-NWWDA-229129-CW-RFB", "3.5 months", sentence, RECORDS, "Select to see its records."]);
  await expect(tip).toHaveAttribute("aria-hidden", "true");
  // The dot's name says the same as its hidden tooltip.
  await expect(dot).toHaveAccessibleName(`KE-NWWDA-229129-CW-RFB, 3.5 months. ${sentence} ${RECORDS} Select to see its records. Dot 20 of 49.`);
  // A package still open says the records show no signed contract.
  await group.getByRole("img").first().focus();
  await expect(tip.locator("p").nth(2)).toHaveText("Kenya. Its notice was published October 9, 2026, and the records I hold show no signed contract.");

  // Above every dot in the lane, or below them all, on any dot.
  const lane = await page.locator("[data-dot-target]").evaluateAll((dots) => {
    const boxes = dots.map((one) => one.getBoundingClientRect());
    return { top: Math.min(...boxes.map((box) => box.top)), bottom: Math.max(...boxes.map((box) => box.bottom)) };
  });
  for (const index of [0, 22, 48]) {
    await page.locator(`[data-dot-target='${index}']`).focus();
    const box = (await tip.boundingBox())!;
    expect(box.y + box.height <= lane.top || box.y >= lane.bottom, `dot ${index + 1}`).toBe(true);
  }
});

test("a dot's tooltip hides when its click opens the drawer, and after Escape the dot the pointer moves to shows its own", async ({ page }) => {
  await openPackage(page);
  const tip = page.locator("[data-dot-tooltip]");
  const dot = (index: number) => page.locator(`[data-dot-target='${index}']`);
  const ref = async (index: number) => (await dot(index).getAttribute("aria-label"))!.split(",")[0];

  // Ticket 60: a click opens the package's records beside the page, and the tooltip under the resting pointer goes, so
  // it no longer covers the key while the drawer shows the same package.
  await page.locator("[data-range-chart]").evaluate((chart) => chart.scrollIntoView({ block: "center" }));
  await pointAt(page, dot(30));
  await expect(tip.locator("p").first()).toHaveText(await ref(30));
  await page.mouse.down();
  await page.mouse.up();
  await expect(page.locator("[data-evidence-drawer]")).toBeVisible();
  await expect(tip).toHaveCount(0);
  await page.keyboard.press("Escape");
  await expect(page.locator("[data-evidence-drawer]")).toHaveCount(0);

  // Ticket 60: Escape hides a focused dot's tooltip; the pointer then moving onto another dot shows that dot's, never
  // the focused one's again.
  await page.mouse.move(2, 2);
  await dot(5).focus();
  await expect(tip.locator("p").first()).toHaveText(await ref(5));
  await page.keyboard.press("Escape");
  await expect(tip).toHaveCount(0);
  await pointAt(page, dot(40));
  await expect(tip.locator("p").first()).toHaveText(await ref(40));
});

// The violations axe finds on the page as it is now.
async function violations(page: Page) {
  const results = await scan(page);
  return results.violations.map((v) => `${v.id}: ${v.nodes.map((node) => node.target.join(" ")).join(", ")}`);
}

for (const width of [1440, 390]) {
  test(`with a number's tooltip open, and then a dot's, axe finds no WCAG 2.2 AA violation at ${width} px`, async ({ page }) => {
    await openPackage(page, width);
    await num(finding(page), "49").focus();
    await expect(tooltip(page).locator("[data-num-act]")).toHaveText("Select to see all 49.");
    expect(await violations(page), "a number's tooltip").toEqual([]);
    await page.locator("[data-dot-target='20']").focus();
    await expect(page.locator("[data-dot-tooltip]")).toBeVisible();
    expect(await violations(page), "a dot's tooltip").toEqual([]);
  });
}

test("a tooltip opened by a resting pointer grows from the side that touches its number over 160 ms", async ({ page }) => {
  await page.clock.install();
  await openPackage(page);
  const all = num(finding(page), "49");
  await all.evaluate((element) => element.scrollIntoView({ block: "center" }));
  await stopTheClock(page);
  await pointAt(page, all);
  await page.clock.runFor(200);
  const motion = await tooltip(page).evaluate((tip) => {
    const style = getComputedStyle(tip);
    return { duration: style.transitionDuration, property: style.transitionProperty, origin: style.transformOrigin };
  });
  expect(motion).toEqual({ duration: "0.16s, 0.16s", property: "opacity, scale", origin: "0px 0px" });
  // It grows from its top left: under the finding, left aligned with the number.
  await expect(tooltip(page)).toHaveAttribute("data-side", "bottom");
});
