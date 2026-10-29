// Section 3 of the package workspace, procurement risks and what helped (ticket 30), at seam 4: the package
// workspace against the risks answers the server recorded on the fixture (tests/record_risks_api.py), which
// tests/test_package_risks.py checks the server against.
//
// The fixture's only completion reports are P130164's, so the table with rows is the demo package's section with
// section 1's country set to India, whose comparables reach P130164's works package (the recorder's note). The
// literal values below are the ticket's and tests/ground_truth/values.toml's: the risk "Cost estimates below
// market rates", the lesson "Base works estimates on market rates to avoid rebidding", ICR P130164 paragraph 54
// (icr-para-54) and its restatement in the ICR Review's section 10.b (icr-review-2023-restates-para-54). The
// words are the 30 brief's, copied here so the test checks the screen against an independent source.
import { scan } from "./axe";
import type { Locator, Page, Request } from "@playwright/test";
import { expect, recorded, test } from "./mocked";

const REF = "KE-NWWDA-541055-CW-RFB";
const PATH = `/packages/${REF}`;
const API = `/api/packages/${REF}`;
const ICR_54 = "strata.gold.passage:31525018/v1/54";
const REVIEW_10B = "strata.gold.passage:34056616/v2/10.b";
const RISK = "Cost estimates below market rates";
const LESSON = "Base works estimates on market rates to avoid rebidding";

type Answer = { status?: number; body: string };

async function openPackage(page: Page, { width = 1440, risks = "risks-ke-nwwda-541055-india.json", save, evidence }: { width?: number; risks?: string; save?: Answer; evidence?: string } = {}) {
  await page.setViewportSize({ width, height: 900 });
  const puts: Request[] = [];
  const answers: Record<string, Answer> = {
    "/api/me": { body: await recorded("me.json") },
    "/api/freshness": { body: await recorded("freshness.json") },
    [API]: { body: await recorded("package-ke-nwwda-541055.json") },
    [`${API}/comparables`]: { body: await recorded("comparables-ke-nwwda-541055.json") },
    [`${API}/risks`]: { body: await recorded(risks) },
    [`${API}/steps`]: { body: await recorded("steps-ke-nwwda-541055.json") },
    [`${API}/risk-selection`]: save ?? { body: await recorded("risks-selection-saved.json") },
    "/api/evidence/opened": { body: '{"opened":[],"recorded":true}' },
  };
  const passages: Record<string, string> = {
    [ICR_54]: await recorded("evidence-icr-p130164-54.json"),
    [REVIEW_10B]: await recorded("evidence-icr-review-p130164-10b.json"),
  };
  await page.route("**/api/**", (route) => {
    const url = new URL(route.request().url());
    if (route.request().method() === "PUT") puts.push(route.request());
    if (url.pathname === "/api/evidence") {
      const body = passages[url.searchParams.get("id") ?? ""];
      return body ? route.fulfill({ contentType: "application/json", body }) : route.fulfill({ status: 404, json: { code: "unknown_evidence" } });
    }
    const answer = answers[url.pathname];
    if (!answer) return route.fulfill({ status: 404, json: { detail: "Not Found" } });
    return route.fulfill({ status: answer.status ?? 200, contentType: "application/json", body: answer.body });
  });
  await page.goto(evidence ? `${PATH}?evidence=${encodeURIComponent(evidence)}` : PATH);
  await expect(section(page).locator("[data-finding], [data-no-risks]").first()).toBeVisible();
  return puts;
}

const section = (page: Page) => page.locator("section#risks");
const view = (page: Page) => section(page).locator("[data-risk-view]:visible");
const row = (page: Page, key: string) => view(page).locator(`[data-risk-row='${key}']`);
const drawer = (page: Page) => page.getByRole("dialog");

async function axe(page: Page, scope = "section#risks") {
  await page.waitForFunction(() => document.getAnimations().every((animation) => animation.playState !== "running"));
  const results = await scan(page, scope);
  return results.violations.map((v) => `${v.id}: ${v.nodes.map((node) => node.target.join(" ")).join(", ")}`);
}

const text = async (locator: Locator) => (await locator.innerText()).replace(/\s+/g, " ").trim();
// What each element shows, leaving out the words only a screen reader hears.
const shown = (locator: Locator) =>
  locator.evaluateAll((elements) =>
    elements.map((element) => {
      const copy = element.cloneNode(true) as HTMLElement;
      copy.querySelectorAll(".sr-only").forEach((hidden) => hidden.remove());
      return (copy.textContent ?? "").replace(/\s+/g, " ").trim();
    }),
  );

test("zone 3 carries its PPSD tag and lists the cost estimates risk, what helped, its count and its sources", async ({ page }) => {
  // The table's form, with its column heads, shows where the zone gives it 49rem: at 1024 px.
  await openPackage(page, { width: 1024 });

  await expect(section(page).locator("[data-zone-tag]")).toHaveText("PPSD section 3");
  // Ticket 101: with risks to select, zone 3 is a panel.
  await expect(section(page)).toHaveAttribute("data-zone", "panel");
  await expect(section(page).getByRole("heading", { level: 2 })).toHaveAccessibleName("Procurement risks and what helped");
  const cost = row(page, "cost_estimates");
  await expect(cost.getByRole("rowheader")).toHaveText(RISK);
  await expect(cost.locator("[data-helped]")).toHaveText(LESSON);
  // The count names its reference class in its cell and its column head, as a count of the one denominator.
  expect(await text(cost.locator("[data-count]"))).toBe("1 of 1 completion reports");
  await expect(view(page).locator("thead")).toContainText("In completion reports for projects with comparable packages");
  const pills = cost.getByRole("list", { name: "Sources" }).getByRole("link");
  expect(await shown(pills)).toEqual(["ICR P130164 ¶54", "ICR Review 10.b"]);
  await expect(pills.first()).toHaveAccessibleName(/^ICR P130164 paragraph 54 ?, Implementation Completion and Results Report, October 10, 2019$/);
  // Counts only: no percentage and no "in 10" anywhere in the section.
  const all = await text(section(page));
  expect(all).not.toMatch(/%|percent| in 10/);
  await expect(section(page).locator("[data-check-line]")).toContainText("Not checked:");
  // The rows restate their records' names and lessons, which are not quotes from a page (ticket 30's review F3).
  await expect(section(page).locator("[data-check-line] [data-check-part=checked]")).toHaveText(
    "Checked: 4 of 4 numbers match records; 4 of 4 names and lessons match their records.",
  );
  await expect(section(page).locator("[data-check-line]")).not.toContainText("on their pages");
  await expect(section(page).locator("[data-removed-box]")).toHaveText("I removed no risks.");
});

test("a source click opens the drawer at its paragraph with the row's claim, the switcher and IEG's badge", async ({ page }) => {
  await openPackage(page);
  const pill = row(page, "cost_estimates").locator(`[data-source-pill='${ICR_54}']`);

  await pill.click();

  await expect(page).toHaveURL(new RegExp(`evidence=${encodeURIComponent(ICR_54).replace(/\./g, "\\.")}`));
  await expect(drawer(page).getByRole("heading", { level: 2 })).toHaveText(/, paragraph 54$/);
  await expect(drawer(page).locator("[data-row-claim]")).toContainText(`From this page${RISK}What helped: ${LESSON}`);
  await expect(drawer(page).locator("[data-badge='ieg-restates']")).toHaveText("IEG's review restates this lesson");
  const tabs = drawer(page).getByRole("tablist", { name: "Sources for this risk" }).getByRole("tab");
  expect(await shown(tabs)).toEqual(["ICR ¶54", "ICR Review 10.b"]);
  await expect(tabs.first()).toHaveAccessibleName("ICR paragraph 54");
  await expect(tabs.first()).toHaveAttribute("aria-selected", "true");
  await expect(row(page, "cost_estimates")).toHaveAttribute("data-open", "true");

  await tabs.nth(1).click();
  await expect(page).toHaveURL(/evidence=strata\.gold\.passage%3A34056616/);
  await expect(drawer(page).locator("[data-ieg-line='restated']")).toBeVisible();

  await page.keyboard.press("Escape");
  await expect(drawer(page)).toHaveCount(0);
  await expect(pill).toBeFocused();
});

test("a drawer opened from the address restores the row's claim once the row shows", async ({ page }) => {
  await openPackage(page, { evidence: ICR_54 });

  await expect(drawer(page).locator("[data-row-claim]")).toContainText(RISK);
  await expect(drawer(page).getByRole("tablist", { name: "Sources for this risk" })).toBeVisible();
});

test("a row's count opens the completion reports that raised its risk, and each opens its paragraph", async ({ page }) => {
  await openPackage(page);

  await row(page, "cost_estimates").locator("[data-count] button").click();

  await expect(drawer(page).getByRole("heading", { level: 2 })).toHaveText("Completion reports that raised this risk");
  await expect(drawer(page)).toContainText(`1 of the 1 completion reports for projects with comparable packages raised "${RISK}".`);
  await drawer(page).locator(`[data-report-entry='${ICR_54}']`).click();
  await expect(drawer(page).getByRole("heading", { level: 2 })).toHaveText(/, paragraph 54$/);
  await drawer(page).getByRole("button", { name: "Back to the report" }).click();
  await expect(drawer(page).locator(`[data-report-entry='${ICR_54}']`)).toBeFocused();
  // The list lands on the report you came back from, marked with tint (ticket 105).
  await expect(drawer(page).locator("[data-landed]")).toHaveAttribute("data-report-entry", ICR_54);
});

test("row selections save at once and persist when the package is reopened", async ({ page }) => {
  const puts = await openPackage(page);
  await expect(section(page).locator("[data-selection-status]")).toHaveText("You haven't selected a risk for the PPSD yet.");

  await view(page).getByRole("checkbox", { name: `Select ${RISK} for the PPSD` }).check();

  await expect(section(page).locator("[data-selection-status]")).toHaveText("You selected 1 of the 2 risks for the PPSD.");
  await expect.poll(() => puts.length).toBe(1);
  expect(puts[0].postDataJSON()).toEqual({ changes: { cost_estimates: true } });

  await page.unrouteAll({ behavior: "ignoreErrors" });
  await openPackage(page, { risks: "risks-ke-nwwda-541055-india-selected.json" });
  await expect(view(page).getByRole("checkbox", { name: `Select ${RISK} for the PPSD` })).toBeChecked();
  await expect(section(page).locator("[data-selection-status]")).toHaveText("You selected 1 of the 2 risks for the PPSD.");
});

test("a failed save keeps the selection on the page and offers Try again", async ({ page }) => {
  await openPackage(page, { save: { status: 503, body: '{"code":"not_saved","trace_id":"0af7651916cd43dd8448eb211c80319c"}' } });

  await view(page).getByRole("checkbox", { name: `Select ${RISK} for the PPSD` }).check();

  await expect(section(page).locator("[data-save-failed]")).toContainText("I couldn't save your selection. It still applies on this page.");
  await expect(section(page).locator("[data-risks-live]")).toHaveText("I couldn't save your selection.");
  await expect(view(page).getByRole("checkbox", { name: `Select ${RISK} for the PPSD` })).toBeChecked();
});

test("on the fixture's Kenya comparables the section says no completion report could be read", async ({ page }) => {
  await openPackage(page, { risks: "risks-ke-nwwda-541055.json" });

  // Ticket 101: holding only its sentence and one link, zone 3 is a row.
  await expect(section(page)).toHaveAttribute("data-zone", "row");
  await expect(section(page).locator("[data-no-risks] [data-no-risks-title]")).toHaveText("None of the three projects with comparable packages has a completion report I could read.");
  await expect(section(page).getByRole("link", { name: "See which completion reports I have read" })).toHaveAttribute(
    "href",
    "/data?sources=notices,awards,documents,projects&from=package_risks",
  );
});

// A package from a sentence: the rural roads package (tests/record_packages_api.py's pkg-000000000001).
async function openPlanned(page: Page, risks: Answer, save: Answer = { body: '{"selected":["cost_estimates"]}' }) {
  await page.setViewportSize({ width: 1440, height: 900 });
  const puts: Request[] = [];
  const answers: Record<string, Answer> = {
    "/api/me": { body: await recorded("me.json") },
    "/api/freshness": { body: await recorded("freshness.json") },
    "/api/planned-packages/pkg-000000000001": { body: await recorded("planned-package-rural-roads.json") },
    "/api/comparables": { body: await recorded("comparables-planned-works-rfb-ke.json") },
    "/api/planned-packages/pkg-000000000001/risks": risks,
    "/api/planned-packages/pkg-000000000001/risk-selection": save,
  };
  await page.route("**/api/**", (route) => {
    const url = new URL(route.request().url());
    if (route.request().method() === "PUT") puts.push(route.request());
    const answer = answers[url.pathname];
    if (!answer) return route.fulfill({ status: 404, json: { detail: "Not Found" } });
    return route.fulfill({ status: answer.status ?? 200, contentType: "application/json", body: answer.body });
  });
  await page.goto("/packages/pkg-000000000001");
  await expect(section(page).locator("[data-finding], [data-no-risks]").first()).toBeVisible();
  return puts;
}

test("the rural roads package from a sentence reaches no completion report on the fixture, and says so", async ({ page }) => {
  await openPlanned(page, { body: await recorded("risks-planned-rural-roads.json") });

  await expect(section(page).locator("[data-zone-tag]")).toHaveText("PPSD section 3");
  await expect(section(page).locator("[data-no-risks] [data-no-risks-title]")).toHaveText("None of the three projects with comparable packages has a completion report I could read.");
});

test("on a package from a sentence, a selection saves with the package under the saved stamp", async ({ page }) => {
  const rows = { body: await recorded("risks-ke-nwwda-541055-india.json") };
  const puts = await openPlanned(page, rows);

  await view(page).getByRole("checkbox", { name: `Select ${RISK} for the PPSD` }).check();

  await expect(page.locator("[data-saved-stamp]")).toHaveText("Saved just now");
  expect(puts.map((request) => request.postDataJSON())).toEqual([{ changes: { cost_estimates: true } }]);
});

// Ticket 59 (the 30 design review, F2 to F4 and F13; the 30 critique, follow-ups 2, 3, 9 and 10). At 1024 px the
// table's pills keep to one line and How often's head no longer breaks a word or two a line, so the head is shorter;
// at 390 px a one-line risk name sits 4 px over its count and a two-line name keeps small's 20 px leading; a failed
// save keeps its icon on the sentence's first line; and the foot strip's lines keep to 65 characters.
test("the table's pills keep one line, a risk's name sits on its count, a failed save keeps its icon with its words, and the notes keep to the prose width", async ({ page }) => {
  await openPackage(page, { width: 1024, save: { status: 503, body: '{"code":"not_saved","trace_id":"0af7651916cd43dd8448eb211c80319c"}' } });
  await expect(view(page)).toHaveAttribute("data-risk-view", "table");
  const table = view(page);
  const pills = await table.locator("[data-source-pill]").evaluateAll((all) => all.map((pill) => Math.round(pill.getBoundingClientRect().height)));
  expect(pills.length).toBeGreaterThan(2);
  for (const height of pills) expect(height, "one line").toBeLessThanOrEqual(24);
  const often = await table.locator("thead th").nth(2).evaluate((cell) => Math.round(cell.getBoundingClientRect().width));
  expect(often, "How often's column").toBeGreaterThanOrEqual(140);
  // The notes, the coverage line and the source line, each at most 65 characters a line.
  const widths = await section(page).locator("[data-risk-notes] > *").evaluateAll((lines) => lines.map((line) => Math.round(line.getBoundingClientRect().width)));
  const prose = await section(page).locator("[data-risk-notes] > p").first().evaluate((line) => parseFloat(getComputedStyle(line).maxWidth));
  for (const width of widths) expect(width, "a foot strip line").toBeLessThanOrEqual(Math.ceil(prose));

  await page.setViewportSize({ width: 390, height: 900 });
  await expect(view(page)).toHaveAttribute("data-risk-view", "list");
  const items = await view(page).locator("li[data-risk-row]").evaluateAll((all) =>
    all.map((item) => {
      const name = item.querySelector("label span.block")!;
      const label = item.querySelector("label")!.getBoundingClientRect();
      const count = item.querySelector("[data-count]")!.getBoundingClientRect();
      const lines = Math.round(name.getBoundingClientRect().height / parseFloat(getComputedStyle(name).lineHeight));
      return { lines, leading: getComputedStyle(name).lineHeight, gap: Math.round(count.top - label.bottom) };
    }),
  );
  expect(items.some((item) => item.lines === 1)).toBe(true);
  for (const item of items) expect(item, "the name over its count").toMatchObject({ leading: "20px", gap: 4 });

  await view(page).getByRole("checkbox", { name: `Select ${RISK} for the PPSD` }).check();
  const failed = section(page).locator("[data-save-failed]");
  await expect(failed).toContainText("I couldn't save your selection.");
  // Both boxes in one read, so a scroll between two reads cannot move one against the other.
  const [icon, words] = await failed.evaluate((line) => [line.querySelector("svg")!, line.querySelector("span > span")!].map((part) => part.getBoundingClientRect().toJSON()));
  expect(Math.abs(icon.y + icon.height / 2 - (words.y + 10)), "the icon on the sentence's first line").toBeLessThanOrEqual(2);
});

// The table shows where the zone gives it 49rem, as the past range's does (DESIGN.md section 5, Tables): at 1024 px. At
// 1440 px the zones keep to the work's seven columns beside the side panel, so the risks are a list there, as at 390
// px, and no column head runs to six lines (ticket 101's design review and critique).
for (const [width, form] of [[1440, "list"], [1024, "table"], [390, "list"]] as const) {
  test(`the section is a ${form} at ${width} px, and axe finds no WCAG 2.2 AA violation`, async ({ page }) => {
    await openPackage(page, { width });

    await expect(view(page)).toHaveAttribute("data-risk-view", form);
    expect(await axe(page)).toEqual([]);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  });
}
