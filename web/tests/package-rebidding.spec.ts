// Section 1's "Advertised again" block (ticket 28), at seam 4: the package workspace against the rebidding answers
// the server recorded on the fixture (tests/record_rebidding_api.py), which tests/test_package_routes.py checks the
// server against, and two mocks for the states the fixture cannot hold (rebidding-mock-*.json, each labeled a mock).
//
// The literal values below are tests/ground_truth/values.toml's [rebidding] entry, counted by hand from the recorded
// files: three of the 52 comparable packages were advertised again, 49 in the past range, and the one reason in
// words is OP00083890's "The Request for Bids has been cancelled.", in an Invitation for Bids, not an award notice.
// The words are the 28 brief's, copied here so the test checks the screen against an independent source.
import { copy } from "../src/copy";
import { scan } from "./axe";
import type { Page } from "@playwright/test";
import { expect, recorded, test } from "./mocked";

const REF = "KE-NWWDA-541055-CW-RFB";
const API = `/api/packages/${REF}`;
const QUOTE = "The Request for Bids has been cancelled.";
const NOTICE = "strata.silver.notices:OP00083890";
const PLAN_ROW = "strata.silver.plan_rows:40001676/KE-KIMAWASCO-157517-CW-RFB";
const WHY = "No field in the records says a package was advertised again, so I worked this out from notices and plan rows, and I may have missed or miscounted some.";

type Answer = { status?: number; body: string };

async function openPackage(page: Page, { width = 1440, rebidding = "rebidding-ke-nwwda-541055.json", comparables = "comparables-ke-nwwda-541055.json", answer }: {
  width?: number; rebidding?: string; comparables?: string; answer?: Answer;
} = {}) {
  await page.setViewportSize({ width, height: 900 });
  const answers: Record<string, Answer> = {
    "/api/me": { body: await recorded("me.json") },
    "/api/freshness": { body: await recorded("freshness.json") },
    [API]: { body: await recorded("package-ke-nwwda-541055.json") },
    [`${API}/comparables`]: { body: await recorded(comparables) },
    [`${API}/rebidding`]: answer ?? { body: await recorded(rebidding) },
    [`${API}/risks`]: { body: await recorded("risks-ke-nwwda-541055.json") },
    "/api/evidence/opened": { body: '{"opened":[],"recorded":true}' },
  };
  const records: Record<string, string> = {
    [NOTICE]: await recorded("evidence-notice-op00083890.json"),
    [PLAN_ROW]: await recorded("evidence-plan-row-ke-kimawasco-157517.json"),
    "strata.gold.package:KE-KIMAWASCO-149448-CW-RFB": await recorded("evidence-package-ke-kimawasco-149448.json"),
    "strata.silver.notices:OP90000006": await recorded("evidence-mock-award-notice-op90000006.json"),
    "strata.silver.notices:OP90000011": await recorded("evidence-mock-notice-op90000011.json"),
    "strata.silver.notices:OP90000012": await recorded("evidence-mock-notice-op90000012.json"),
  };
  await page.route("**/api/**", (route) => {
    const url = new URL(route.request().url());
    if (url.pathname === "/api/evidence") {
      const body = records[url.searchParams.get("id") ?? ""];
      return body ? route.fulfill({ contentType: "application/json", body }) : route.fulfill({ status: 404, json: { code: "unknown_evidence" } });
    }
    const found = answers[url.pathname];
    if (!found) return route.fulfill({ status: 404, json: { detail: "Not Found" } });
    return route.fulfill({ status: found.status ?? 200, contentType: "application/json", body: found.body });
  });
  await page.goto(`/packages/${REF}`);
}

const block = (page: Page) => page.locator("[data-rebidding]");
const ready = async (page: Page) => expect(page.locator("[data-rebidding=found], [data-rebidding=none]")).toBeVisible();
const text = async (page: Page, selector: string) => ((await block(page).locator(selector).innerText()) ?? "").replace(/\s+/g, " ").trim();
const disclosure = (page: Page) => block(page).locator("[data-rebid-disclosure]");
// Why the count needs care, and why my model gives no estimate, are in the Experimental badge's window since ticket 126
// (T17; DESIGN.md section 7, rule 32). A click pins it open; its text, spaces folded.
const badgeWindow = async (page: Page) => {
  await block(page).getByRole("button", { name: "Experimental" }).click();
  return page.getByRole("dialog", { name: "Experimental" });
};
const inBadgeWindow = async (page: Page, selector: string) =>
  ((await (await badgeWindow(page)).locator(selector).innerText()) ?? "").replace(/\s+/g, " ").trim();

async function axe(page: Page) {
  await page.waitForFunction(() => document.getAnimations().every((animation) => animation.playState !== "running"));
  const results = await scan(page, "[data-past-range]");
  return results.violations.map((v) => `${v.id}: ${v.nodes.map((node) => node.target.join(" ")).join(", ")}`);
}

test("the block ends section 1's card after a divider, labeled experimental with why, and counts 3 of the 52", async ({ page }) => {
  await openPackage(page);
  await ready(page);

  // Zone 1's second block, after everything else in it but its own foot strip, which holds its source (ticket 101), with
  // a 1px line above it.
  expect(
    await block(page).evaluate(
      (element) =>
        element.closest("[data-past-range]") !== null &&
        element.nextElementSibling?.hasAttribute("data-foot-strip") === true &&
        element.nextElementSibling.nextElementSibling === null,
    ),
  ).toBe(true);
  await expect(page.locator("[data-past-range] > [data-foot-strip]").last()).toContainText("Records run through");
  expect(await block(page).evaluate((element) => getComputedStyle(element).borderTopWidth)).toBe("1px");
  await expect(block(page).getByRole("heading", { level: 3 })).toHaveText("Advertised again");
  await expect(block(page).locator("[data-badge=experimental]")).toHaveText("Experimental");
  expect(await text(page, "[data-rebid-count]")).toBe("3 of the 52 comparable packages were advertised again.");
  // Why 52 and not the past range's 49 is in the 52's tooltip since ticket 126 (T18; rule 15 keeps it one step away).
  await block(page).locator("[data-rebid-count] [data-num]").nth(1).focus();
  await expect(page.getByRole("tooltip")).toContainText(
    "I counted 52 packages here and 49 in the past range, because the past range leaves out canceled packages, and a canceled package counts here.",
  );
  await page.keyboard.press("Escape");
  expect(await block(page).innerText()).not.toMatch(/%|percent| in 10/);
  // No model results on the fixture: only the counts, and the badge's window says why, after why the count needs care.
  const why = await badgeWindow(page);
  await expect(why.locator("[data-rebid-why]")).toHaveText(WHY);
  await expect(why.locator("[data-rebid-model-off]")).toHaveText("I'm not giving an estimate, because my model has no test results yet.");
  await page.keyboard.press("Escape");
  await expect(disclosure(page)).toHaveAttribute("aria-expanded", "false");
  await expect(block(page).locator("[data-rebid-list]")).toBeHidden();
});

test("the reasons open grouped, most packages first, each quoted or described and cited, with markers numbered on the page", async ({ page }) => {
  await openPackage(page);
  await ready(page);

  await disclosure(page).click();
  await expect(disclosure(page)).toHaveAttribute("aria-expanded", "true");
  await expect(disclosure(page)).toBeFocused();
  const headings = block(page).getByRole("heading", { level: 4 });
  await expect(headings.first()).toHaveAccessibleName("Canceled in the Procurement Plan, 2 of the 3 packages");
  await expect(headings.nth(1)).toHaveAccessibleName("The process was canceled, 1 of the 3 packages");
  await expect(headings).toHaveCount(2);
  const quoted = block(page).locator("[data-rebid-row='KE-KIMAWASCO-149448-CW-RFB']");
  await expect(quoted.locator("[data-rebid-line=quote]")).toContainText(`"${QUOTE}"`);
  await expect(quoted.locator("[data-rebid-sources]")).toHaveText("Notice OP00083890, published Feb 4, 2020.");
  const canceled = block(page).locator("[data-rebid-row='KE-KIMAWASCO-157517-CW-RFB'] [data-rebid-line=canceled_row]");
  await expect(canceled).toContainText('The Procurement Plan of March 19, 2025 gave its Process Status as "Canceled".');
  const markers = block(page).locator("[data-citation]");
  await expect(markers).toHaveText(["[1]", "[2]", "[3]"]);
  await expect(markers.nth(2)).toHaveAccessibleName("Source 3: Notice OP00083890, February 4, 2020");
  await expect(block(page).getByRole("button", { name: "Open the records for KE-KIMAWASCO-149448-CW-RFB" })).toBeVisible();
});

test("selecting a count opens the list and moves focus to its first group", async ({ page }) => {
  await openPackage(page);
  await ready(page);

  await block(page).locator("[data-rebid-count] button").first().click();

  await expect(block(page).locator("[data-rebid-list]")).toBeVisible();
  await expect(block(page).getByRole("heading", { level: 4 }).first()).toBeFocused();
});

test("a marker opens the drawer at the notice with its words highlighted under the row's claim, and Escape gives focus back", async ({ page }) => {
  await openPackage(page);
  await ready(page);
  await disclosure(page).click();
  const marker = block(page).locator(`[data-citation-id='${NOTICE}']`);

  await marker.click();

  const drawer = page.getByRole("dialog");
  await expect(page).toHaveURL(/evidence=strata\.silver\.notices%3AOP00083890/);
  await expect(drawer.getByRole("heading", { level: 2 })).toHaveText("Notice OP00083890");
  const claim = drawer.locator("[data-rebid-claim]");
  await expect(claim.locator("p").first()).toHaveText("From this page");
  await expect(claim.locator("p").nth(1)).toContainText(`"${QUOTE}"`);
  await expect(claim.locator("p").nth(1).locator("[aria-hidden=true]").last()).toHaveText("3");
  await expect(drawer.locator("mark")).toContainText(QUOTE);
  // The way out to the source: the notice's own page (ticket 28's design review, F1).
  await expect(drawer.getByRole("link", { name: new RegExp(`^${copy.evidence.openNotice}`) })).toHaveAttribute(
    "href",
    "https://projects.worldbank.org/en/projects-operations/procurement-detail/OP00083890",
  );
  await expect(block(page).locator("[data-rebid-row='KE-KIMAWASCO-149448-CW-RFB']")).toHaveAttribute("data-open", "true");

  await page.keyboard.press("Escape");
  await expect(drawer).toHaveCount(0);
  await expect(marker).toBeFocused();
});

test("a canceled plan row opens with its Process Status highlighted, and a STEP reference opens the package's records", async ({ page }) => {
  await openPackage(page);
  await ready(page);
  await disclosure(page).click();

  // The marker names the row as the drawer heads it, an activity (ticket 58; the 28 design review, F2).
  await expect(block(page).locator(`[data-citation-id='${PLAN_ROW}']`).first()).toHaveAccessibleName(/^Source \d+: Activity KE-KIMAWASCO-157517-CW-RFB, /);
  await block(page).locator(`[data-citation-id='${PLAN_ROW}']`).click();
  const drawer = page.getByRole("dialog");
  await expect(drawer.getByRole("heading", { level: 2 })).toHaveText("Activity KE-KIMAWASCO-157517-CW-RFB");
  // A plan row records a plan, so its caption names the plan, as the plan check's drawer does (the 58 design review,
  // follow-up 12).
  await expect(drawer.locator("[data-drawer-caption]")).toHaveText("Activity in the Kilifi - Mariakani Water and Sewerage Company Ltd plan of March 19, 2025");
  await expect(drawer.locator("mark")).toContainText("Canceled");
  // Its place in Check a plan, on the plan version that canceled it (ticket 28's design review, F1).
  await expect(drawer.getByRole("link", { name: copy.trail.plan.showInPlan })).toHaveAttribute(
    "href",
    "/projects/P156634/procurement/kilifi-mariakani-water-and-sewerage-company-ltd/2025-03-19#KE-KIMAWASCO-157517-CW-RFB",
  );

  await block(page).getByRole("button", { name: "Open the records for KE-KIMAWASCO-149448-CW-RFB" }).click();
  await expect(page).toHaveURL(/evidence=strata\.gold\.package%3AKE-KIMAWASCO-149448-CW-RFB/);
  // A canceled package is left out of the past range, so the drawer never says it is in it (ticket 101's review, B1).
  await expect(drawer.locator("[data-comparable=canceled]")).toBeVisible();
  await expect(drawer.locator("[data-drawer-caption]")).toHaveCount(0);
});

// Ticket 58 (ticket 28's review, follow-up 3): a package planned from a sentence is in no plan, so the nightly job never
// scores it, and the block says so rather than "not yet". The fixture registers no model, so the server's reason
// (tests/test_rebidding_backtest.py proves it) is set in memory.
test("a package planned from a sentence says my model scores only packages listed in a plan", async ({ page }) => {
  const planned = JSON.parse(await recorded("rebidding-planned-works-rfb-ke.json"));
  planned.model = { ...planned.model, not_shown_reason: "not_in_plan" };
  await openPackage(page, { answer: { body: JSON.stringify(planned) } });
  await ready(page);

  expect(await inBadgeWindow(page, "[data-rebid-model-off]")).toBe(
    "I'm not giving an estimate. My model scores only packages listed in a Procurement Plan, and this one is not in a plan yet.",
  );
});

test("with fewer than 20 comparable packages and none advertised again, only the counts appear, then where to look next", async ({ page }) => {
  await openPackage(page, { rebidding: "rebidding-ke-nwwda-541055-prior.json", comparables: "comparables-ke-nwwda-541055-prior.json" });
  await expect(block(page)).toHaveAttribute("data-rebidding", "none");

  expect(await text(page, "[data-rebid-count]")).toBe("I found no sign that any of the seven comparable packages were advertised again.");
  // None was advertised again, so the count says what it counted and opens nothing (ticket 58; the 28 design review, F4).
  const seven = block(page).locator("[data-rebid-count] [data-num]");
  await seven.focus();
  await expect(page.getByRole("tooltip").locator("[data-num-what]")).toHaveText("The comparable packages I checked for this count.");
  await expect(page.getByRole("tooltip")).not.toContainText("Select to see");
  expect(await inBadgeWindow(page, "[data-rebid-model-off]")).toBe("I'm not giving an estimate, because I give one only from 20 or more comparable packages.");
  expect(await block(page).innerText()).not.toMatch(/%|percent| in 10/);
  await expect(disclosure(page)).toHaveCount(0);
  await expect(block(page).getByRole("link", { name: "See how complete the notices are" })).toHaveAttribute("href", "/data?sources=notices&from=rebidding_risk");
});

test("my model's estimate shows as about k in 10 with its track record, a long group shows five rows then the rest, and a quote keeps its language (mock)", async ({ page }) => {
  await openPackage(page, { rebidding: "rebidding-mock-model-shown.json" });
  await ready(page);

  expect(await text(page, "[data-rebid-model]")).toBe("My model estimates that about 3 in 10 packages like this one are advertised again.");
  expect(await text(page, "[data-rebid-track]")).toBe(
    "Track record: I tested my model on 61 packages from 2025 that it had not seen. It matched what happened better than the rate among their comparable packages did.",
  );
  await disclosure(page).click();
  const group = block(page).locator("[data-rebid-group=all_bids_rejected]");
  await expect(group.locator("[data-rebid-row]")).toHaveCount(5);
  await expect(block(page).locator("[data-rebid-row='SN-SAMPLE-310004-CW-RFB'] [data-rebid-line]")).toHaveAttribute("lang", "fr");
  await expect(block(page).locator("[data-rebid-row='SN-SAMPLE-310004-CW-RFB']")).toContainText("In French, as the award notice gives it.");
  // The hidden row's marker kept its number: the activity advertised twice cites 7 and 8.
  await expect(block(page).locator("[data-rebid-row='KE-SAMPLE-320001-CW-RFB'] [data-citation]")).toHaveText(["[7]", "[8]"]);

  await group.getByRole("button", { name: "Show one more" }).click();
  await expect(group.locator("[data-rebid-row]")).toHaveCount(6);
  await expect(group.getByRole("button", { name: "Open the records for KE-SAMPLE-310001-CW-RFB" })).toBeFocused();
});

// Ticket 60 (ticket 28's review, follow-up 9): a denominator reason the copy file has no words for says no reason,
// never a raw code. Since ticket 126 the reason is in the count's tooltip, so the tooltip is where it would show.
test("a denominator reason with no words in the copy file says no reason in the count's tooltip", async ({ page }) => {
  const body = JSON.parse(await recorded("rebidding-ke-nwwda-541055.json"));
  await openPackage(page, { answer: { body: JSON.stringify({ ...body, denominator_reason: "a_reason_with_no_words" }) } });
  await ready(page);
  await expect(block(page).locator("[data-rebid-count]")).toBeVisible();
  await block(page).locator("[data-rebid-count] [data-num]").nth(1).focus();
  await expect(page.getByRole("tooltip").locator("[data-num-what]")).toBeVisible();
  await expect(page.getByRole("tooltip")).not.toContainText("a_reason_with_no_words");
  await expect(page.getByRole("tooltip")).not.toContainText("I counted 52 packages here");
  await expect(block(page)).not.toContainText("a_reason_with_no_words");
});

test("an activity advertised twice opens the drawer with a tab for each notice (mock)", async ({ page }) => {
  await openPackage(page, { rebidding: "rebidding-mock-model-shown.json" });
  await ready(page);
  await disclosure(page).click();

  await block(page).locator("[data-citation-id='strata.silver.notices:OP90000011']").click();

  const tabs = page.getByRole("dialog").getByRole("tablist", { name: "Sources for this sentence" }).getByRole("tab");
  await expect(tabs).toHaveText(["Notice OP90000011", "Notice OP90000012"]);
  await expect(tabs.first()).toHaveAttribute("aria-selected", "true");
  // Ticket 60 (ticket 28's critique, follow-up 5): the line is dated by the second notice, so the claim ends with both
  // records' numbers, whichever tab is open.
  await expect(page.getByRole("dialog").locator("[data-rebid-claim] [data-claim-numbers]")).toHaveText("78");
  await tabs.nth(1).click();
  await expect(page).toHaveURL(/evidence=strata\.silver\.notices%3AOP90000012/);
  await expect(page.getByRole("dialog").getByRole("heading", { level: 2 })).toHaveText("Notice OP90000012");
});

test("a model that did no better than its baseline gives no estimate, and says so (mock)", async ({ page }) => {
  await openPackage(page, { rebidding: "rebidding-mock-not-better.json" });
  await ready(page);

  // The tests' count opens nothing inside the window, so the window says where it came from (CLAUDE.md rule 2).
  expect(await inBadgeWindow(page, "[data-rebid-model-off]")).toBe(
    "I'm not giving an estimate. In tests on 44 packages from 2025 that my model had not seen, it did no better than the rate among their comparable packages. From my model's saved test results of October 20, 2026.",
  );
  expect(await block(page).innerText()).not.toMatch(/ in 10/);
});

test("too few comparable packages for my model names the settings its smallest count came from (mock)", async ({ page }) => {
  const prior = JSON.parse(await recorded("rebidding-ke-nwwda-541055-prior.json"));
  prior.model.score_date = "2026-10-20";
  await openPackage(page, { answer: { body: JSON.stringify(prior) }, comparables: "comparables-ke-nwwda-541055-prior.json" });
  await expect(block(page)).toHaveAttribute("data-rebidding", "none");

  expect(await inBadgeWindow(page, "[data-rebid-model-off]")).toBe(
    "I'm not giving an estimate, because I give one only from 20 or more comparable packages. From the settings I used on October 20, 2026.",
  );
});

test("a failed load says so with Try again and the code, and a route the server lacks hides the block", async ({ page }) => {
  let calls = 0;
  await openPackage(page, { answer: { status: 503, body: '{"code":"data_service","trace_id":"0af7651916cd43dd8448eb211c80319c"}' } });
  await expect(block(page)).toHaveAttribute("data-rebidding", "error");
  await expect(block(page).locator("[data-alert=error]")).toHaveText("I couldn't load the count of packages advertised again.");
  await expect(block(page)).toContainText("If it fails again, quote this code: 0af7651916cd43dd8448eb211c80319c.");
  await expect(block(page).locator("[data-rebid-why]")).toHaveCount(0);
  // Zone 1 has one polite live region, and the block's failure is said there, not in a second region of its own
  // (the 28 brief; ticket 60).
  const zone = page.locator("section[data-section=took]");
  await expect(zone.getByRole("status")).toHaveCount(1);
  await expect(zone.getByRole("status")).toHaveText("I couldn't load the count of packages advertised again.");
  await expect(block(page).getByRole("status")).toHaveCount(0);

  let release = () => {};
  const held = new Promise<void>((resolve) => (release = resolve));
  await page.route(`**${API}/rebidding`, async (route) => {
    calls += 1;
    await held;
    await route.fulfill({ contentType: "application/json", body: await recorded("rebidding-ke-nwwda-541055.json") });
  });
  await block(page).getByRole("button", { name: "Try again" }).click();
  // The region empties while the retry runs, so a second failure would be heard again (ticket 60's review, item 5).
  await expect(zone.getByRole("status")).toHaveText("");
  release();
  await expect(block(page)).toHaveAttribute("data-rebidding", "found");
  await expect(block(page).getByRole("heading", { level: 3 })).toBeFocused();
  expect(calls).toBe(1);

  const other = await page.context().newPage();
  await openPackage(other, { answer: { status: 404, body: '{"detail":"Not Found"}' } });
  await expect(other.locator("[data-past-range=range], [data-past-range=dots]")).toBeVisible();
  await expect(other.locator("[data-rebidding]")).toHaveCount(0);
});

for (const width of [1440, 1024, 390]) {
  test(`at ${width} px the block passes axe with its reasons open, on the fixture, with fewer than 20 and with the model shown`, async ({ page }) => {
    for (const [rebidding, comparables] of [
      ["rebidding-ke-nwwda-541055.json", "comparables-ke-nwwda-541055.json"],
      ["rebidding-ke-nwwda-541055-prior.json", "comparables-ke-nwwda-541055-prior.json"],
      ["rebidding-mock-model-shown.json", "comparables-ke-nwwda-541055.json"],
    ]) {
      await openPackage(page, { width, rebidding, comparables });
      await ready(page);
      if ((await disclosure(page).count()) > 0) await disclosure(page).click();
      expect(await axe(page), rebidding).toEqual([]);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), rebidding).toBe(true);
    }
  });
}

test("at 320 px nothing scrolls sideways with the reasons open", async ({ page }) => {
  await openPackage(page, { width: 320, rebidding: "rebidding-mock-model-shown.json" });
  await ready(page);
  await disclosure(page).click();

  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});

// The last line of an element's text: the characters that sit lowest.
function lastLine(element: Element) {
  const range = document.createRange();
  const chars: { top: number; text: string }[] = [];
  const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT);
  for (let node = walker.nextNode() as Text | null; node; node = walker.nextNode() as Text | null) {
    for (let i = 0; i < node.length; i++) {
      range.setStart(node, i);
      range.setEnd(node, i + 1);
      const rect = range.getClientRects()[0];
      if (rect) chars.push({ top: Math.round(rect.top), text: node.data[i] });
    }
  }
  const bottom = Math.max(...chars.map((char) => char.top));
  return chars
    .filter((char) => Math.abs(char.top - bottom) < 4)
    .map((char) => char.text)
    .join("")
    .trim();
}

// Ticket 59 (the 28 design review, F6 and F9; the 28 critique, follow-ups 1 to 4): the group counts keep to the
// prose width beside their labels, and below 480 px of the group's width they sit under them as captions; the count
// sentence never leaves one word on its last line; and a failed load's code wraps inside the card at 320 px.
test("the group counts sit by their labels within the prose width, as captions under them below 480 px, and a failed load's code stays in the card", async ({ page }) => {
  await openPackage(page);
  await ready(page);
  await disclosure(page).click();
  const heading = block(page).getByRole("heading", { level: 4 }).first();
  const count = heading.locator("span[aria-hidden]").nth(1);
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: 900 });
    // The group lays out again by its own width once the window has drawn at this size.
    await page.evaluate(() => new Promise((done) => requestAnimationFrame(() => requestAnimationFrame(done))));
    await expect.poll(() => count.evaluate((element) => getComputedStyle(element).fontSize)).toBe(width === 390 ? "13px" : "14px");
    // The three boxes in one read, so a scroll between two reads cannot move one against the other.
    const [label, number, prose] = await block(page).evaluate((element) => {
      const parts = element.querySelectorAll("h4")[0].querySelectorAll("span[aria-hidden]");
      return [parts[0], parts[1], element.querySelector("[data-rebid-count]")!].map((part) => {
        const box = part.getBoundingClientRect();
        return { x: box.x, y: box.y, width: box.width, height: box.height };
      });
    });
    expect(number.x + number.width, `${width} px: the count keeps to the prose width`).toBeLessThanOrEqual(prose.x + prose.width + 1);
    const style = await count.evaluate((element) => [getComputedStyle(element).fontSize, getComputedStyle(element).fontWeight]);
    if (width === 390) {
      expect(number.y, "the count under its label").toBeGreaterThanOrEqual(label.y + label.height - 1);
      expect(style, "a caption").toEqual(["13px", "400"]);
    } else {
      expect(Math.abs(number.y + number.height / 2 - (label.y + label.height / 2)), "the count beside its label").toBeLessThanOrEqual(3);
      expect(style).toEqual(["14px", "600"]);
    }
    expect((await block(page).locator("[data-rebid-count]").evaluate(lastLine)).split(" ").length, `${width} px: the count sentence's last line`).toBeGreaterThan(1);
  }

  await page.unrouteAll({ behavior: "ignoreErrors" });
  await openPackage(page, { width: 320, answer: { status: 503, body: '{"code":"data_service","trace_id":"0af7651916cd43dd8448eb211c80319c"}' } });
  await expect(block(page)).toHaveAttribute("data-rebidding", "error");
  const code = block(page).getByText("0af7651916cd43dd8448eb211c80319c");
  const [inner, outer] = [(await code.boundingBox())!, (await block(page).boundingBox())!];
  expect(inner.x + inner.width, "the code inside the card").toBeLessThanOrEqual(outer.x + outer.width);
});
