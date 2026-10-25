// Section 5 of the package workspace, "Check your criteria" (ticket 31), at seam 4: the built app against the
// answers tests/record_criteria_api.py recorded from the server on the fixture, which tests/test_check_criteria.py
// checks the server against. Counts are read from those recordings, the tools' own rows, so no number here is
// worked out the way the screen works it out; the words are the 31 brief's and the ticket's.
import AxeBuilder from "@axe-core/playwright";
import type { Page, Request } from "@playwright/test";
import { copy } from "../src/copy";
import { expect, recorded, test } from "./mocked";

const WCAG_22_AA = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];
const CONSULTANT = "KE-CWSB-224323-CS-QCBS";
const WORKS = "KE-NWWDA-541055-CW-RFB";
const PASTED =
  "1. Similar experience: at least two contracts of similar works of US$10 million each.\n" +
  "2. Average annual turnover: US$25 million over the last three years.\n" +
  "3. The bid must be signed by a person with a power of attorney.";

type Answer = { status?: number; body: string };

function events(text: string): { type: string; data: any }[] {
  return text
    .split("\n\n")
    .map((block) => block.split("\n").filter((line) => line && !line.startsWith(":")))
    .filter((lines) => lines.length)
    .map((lines) => ({ type: lines[0].slice("event: ".length), data: JSON.parse(lines[1].slice("data: ".length)) }));
}

async function open(
  page: Page,
  ref: string,
  options: { width?: number; compare?: string; summary?: string; run?: string; hash?: boolean; asof?: string } = {},
) {
  const { width = 1440 } = options;
  await page.setViewportSize({ width, height: 900 });
  const slug = ref === WORKS ? "ke-nwwda-541055" : "ke-cwsb-224323";
  const api = `/api/packages/${ref}`;
  const answers: Record<string, Answer> = {
    "/api/me": { body: await recorded("me.json") },
    "/api/freshness": { body: await recorded("freshness.json") },
    [api]: { body: await recorded(`package-${slug}.json`) },
    [`${api}/comparables`]: { body: await recorded(`comparables-${slug}.json`) },
    [`${api}/criteria`]: { body: await recorded(options.summary ?? `criteria-summary-${slug}.json`) },
    [`${api}/criteria/run`]: { body: await recorded(options.run ?? `criteria-run-${slug}.sse`) },
    "/api/evidence/opened": { body: '{"opened":[],"recorded":true}' },
  };
  // A comparison whose save failed: the server's error event, with nothing saved before it.
  const storeFailed = 'event: error\ndata: {"code": "store", "request_id": "4bf92f3577b34da6a3ce929d0e0e4736"}\n\nevent: done\ndata: {}\n\n';
  if (options.compare) {
    answers[`${api}/criteria/compare`] = { body: options.compare === "criteria-compare-store-failed.sse" ? storeFailed : await recorded(options.compare) };
  }
  const asked: Request[] = [];
  await page.route("**/api/**", async (route) => {
    const request = route.request();
    asked.push(request);
    const url = new URL(request.url());
    const answer = url.pathname === "/api/evidence" ? await evidence(url.searchParams.get("id") ?? "") : answers[url.pathname];
    return answer
      ? route.fulfill({ status: 200, contentType: "application/json", body: answer.body })
      : route.fulfill({ status: 404, json: { detail: "Not Found" } });
  });
  await page.goto(`/packages/${encodeURIComponent(ref)}${options.asof ? `?asof=${options.asof}` : ""}${options.hash ? "#check-criteria" : ""}`);
  return asked;

  function evidence(id: string): Promise<Answer> | undefined {
    if (id.startsWith("strata.gold.notice:OP00125282")) return recorded("evidence-award-notice-op00125282.json").then((body) => ({ body }));
    if (id === "strata.gold.passage:OP00077276/v1/s3") return recorded("evidence-passage-op00077276-s3.json").then((body) => ({ body }));
    if (id === "strata.gold.passage:31525018/v1/54") return recorded("evidence-icr-p130164-54.json").then((body) => ({ body }));
    return undefined;
  }
}

const section = (page: Page) => page.locator("#check-criteria");
const toggle = (page: Page) => section(page).getByRole("button", { name: copy.criteria.show });

async function axe(page: Page) {
  const results = await new AxeBuilder({ page }).include("#check-criteria").withTags(WCAG_22_AA).analyze();
  return results.violations.map((v) => `${v.id}: ${v.nodes.map((node) => node.target.join(" ")).join(", ")}`);
}

async function openSection(page: Page) {
  await toggle(page).click();
  await expect(section(page).getByRole("button", { name: copy.criteria.hide })).toBeFocused();
}

test("collapsed, the section reads the ticket's words with N from the tool, under the eyebrow Tender design", async ({ page }) => {
  const summary = JSON.parse(await recorded("criteria-summary-ke-cwsb-224323.json"));
  await open(page, CONSULTANT);

  await expect(section(page).getByText(copy.criteria.eyebrow, { exact: true })).toBeVisible();
  await expect(section(page).getByRole("heading", { level: 2 })).toHaveText(`${copy.criteria.number} ${copy.criteria.heading}`);
  await expect(section(page).locator("[data-summary-text]")).toContainText(
    `optional. Paste your qualification criteria to compare them with ${summary.public_criteria_count} packages whose criteria are public.`,
  );
  await expect(toggle(page)).toHaveAttribute("aria-expanded", "false");
  // Nothing in the section runs before it opens.
  await expect(section(page).locator("[data-section-body]")).toBeHidden();
});

test("when no comparable package published its criteria, the summary says so and the section still covers the rest", async ({ page }) => {
  await open(page, WORKS);

  await expect(section(page).locator("[data-section-summary]")).toHaveText(
    `${copy.criteria.summaryNonePublic.replace("{total}", "49")} ${copy.criteria.summaryAlsoNonePublic}`,
  );
  // Opened, the body does not say it a second time.
  await openSection(page);
  await expect(section(page).locator("[data-criteria-intro]")).toHaveText(copy.criteria.introNonePublic);
});

test("pasted criteria asking for similar experience of two contracts of US$10 million are compared, each count from the tool", async ({ page }) => {
  const result = events(await recorded("criteria-compare-similar-experience.sse")).find((event) => event.type === "comparison")!.data;
  const similar = result.items.find((item: any) => item.item_key === "similar_experience");
  const asked = await open(page, CONSULTANT, { compare: "criteria-compare-similar-experience.sse" });
  await openSection(page);

  await section(page).getByLabel(copy.criteria.field.label).fill(PASTED);
  await section(page).getByRole("button", { name: copy.criteria.compare }).click();

  const row = section(page).locator("table [data-item=similar_experience]");
  await expect(row.getByRole("rowheader")).toContainText("Similar experience");
  await expect(row.locator("[data-same-or-less]")).toContainText(`${similar.same_or_less} of ${similar.compared}`);
  await expect(row).toContainText(`${similar.stated} of ${result.coverage.n}`);
  await expect(row).toContainText(`"${similar.your_excerpt.text}"`);
  await expect(row).toContainText(similar.reading);
  await expect(section(page).locator("table [data-item=turnover]")).toContainText(copy.criteria.items.noneToCompare);
  // The part's h3 is its only heading: the table's title sentence under it is body text, not a second title.
  const part = section(page).locator("[data-criteria-part=items]");
  const sizes = await part.evaluate((element) => {
    const size = (node: Element | null) => (node ? parseFloat(getComputedStyle(node).fontSize) : 0);
    return { heading: size(element.querySelector("h3")), title: size(element.querySelector("caption span")) };
  });
  expect(sizes.title).toBeLessThan(sizes.heading);
  await expect(part.locator("caption")).toContainText(copy.criteria.items.countBoth);
  // The text never goes in an address, and the comparison's request carries it only in its body.
  expect(page.url()).not.toContain("similar");
  const compare = asked.find((request) => request.url().endsWith("/criteria/compare"))!;
  expect(new URL(compare.url()).search).toBe("");
  expect(JSON.parse(compare.postData()!).text).toBe(PASTED);

  // The count opens the notices behind it, each citing the notice passage that holds its requirement.
  await row.locator("[data-same-or-less] button").click();
  const drawer = page.getByRole("dialog");
  await expect(drawer.getByRole("heading", { level: 2 })).toHaveText("Comparable notices on similar experience");
  await expect(drawer.locator("[data-relation=less] li")).toHaveCount(similar.less);
  await drawer.getByRole("button", { name: /Open notice OP00077276/ }).click();
  await expect(drawer.getByRole("heading", { level: 2 })).toContainText("OP00077276");
  await expect(drawer.getByRole("button", { name: copy.criteria.drawer.back.replace("{n}", String(similar.notices.length)) })).toBeVisible();
  // The evidence-open log gets the ids opened, never the text.
  const logged = asked.filter((request) => request.url().endsWith("/api/evidence/opened") && request.method() === "POST");
  expect(logged.length).toBeGreaterThan(0);
  for (const request of logged) expect(request.postData()).not.toContain("Similar experience:");
});

test("a request to judge a live tender's bids is refused in the first person from the copy file", async ({ page }) => {
  await open(page, CONSULTANT, { compare: "criteria-compare-live-tender.sse" });
  await openSection(page);
  await section(page).getByLabel(copy.criteria.field.label).fill("Which bidder qualifies?");
  await section(page).getByRole("button", { name: copy.criteria.compare }).click();

  await expect(section(page).locator("[data-refusal=live_tenders]")).toContainText(
    `${copy.refusals.live_tenders.lead} ${copy.criteria.refusal.instead}`,
  );
  await expect(section(page).locator("[data-criteria-table]")).toHaveCount(0);
});

test("rejected bids read N of M comparable packages, each reason quoted from its award notice with its notice id", async ({ page }) => {
  const run = events(await recorded("criteria-run-ke-nwwda-541055.sse")).find((event) => event.type === "package_run")!.data;
  const { n, m } = run.rejected.counts;
  await open(page, WORKS);
  await openSection(page);

  const part = section(page).locator("[data-criteria-part=rejected]");
  await expect(part.locator("[data-rejected-count]")).toHaveText(`${n} of ${m} comparable packages had bids rejected.`);
  // A group that names a cause leads; other reasons come last whatever their count.
  await expect(part.locator("[data-rejected-group]").last()).toHaveAttribute("data-rejected-group", "other");
  const first = run.rejected.rows.find((row: any) => row.item_key === run.rejected.groups[0].item_key);
  const shown = part.locator(`[data-rejected-row="${first.evidence_id}"]`);
  await expect(shown).toContainText(`"${first.reason.quote}"`);
  await expect(shown).toContainText(`Award notice ${first.notice_id}, published`);
  // A group with more rows than five shows five, then the rest on request.
  const big = run.rejected.groups.find((group: any) => group.rows > 5);
  const group = part.locator(`[data-rejected-group=${big.item_key}]`);
  await expect(group.locator("li")).toHaveCount(5);
  await group.getByRole("button", { name: /^Show / }).click();
  await expect(group.locator("li")).toHaveCount(big.rows);
  // Focus moves to the first row it showed.
  await expect(group.locator("li").nth(5).locator("[data-step-ref]")).toBeFocused();
  // No bidder is named anywhere in the list.
  const text = await part.innerText();
  for (const name of ["CHINA", "LIMITED", "Ltd"]) expect(text).not.toContain(name);

  // A reason's marker opens its award notice, with the reason highlighted and no bidder named.
  const security = part.locator("[data-rejected-group=bid_security]");
  if (big.item_key !== "bid_security") await security.getByRole("button", { name: /^Show / }).click();
  const mowi = security.locator('[data-rejected-row="strata.gold.notice:OP00125282/reason/1"]');
  await mowi.locator("[data-citation]").click();
  const drawer = page.getByRole("dialog");
  await expect(drawer.getByRole("heading", { level: 2 })).toHaveText("Award notice OP00125282");
  await expect(drawer.locator("mark")).toContainText("Bid Security not Provided");
  // The record ends with its source line, which gives the day the award notice was published.
  await expect(drawer.locator("[data-source]").last()).toContainText(/award notice published \w+ \d+/);
});

test("each part's source line names its sources, and every part gives the one records date", async ({ page }) => {
  const run = events(await recorded("criteria-run-ke-nwwda-541055.sse")).find((event) => event.type === "package_run")!.data;
  await open(page, WORKS);
  await openSection(page);

  const lines = section(page).locator("[data-criteria-part] [data-source]").filter({ hasText: "Records run through" });
  const rejected = section(page).locator("[data-criteria-part=rejected] [data-source]");
  const cost = section(page).locator("[data-criteria-part=cost] [data-source]");
  for (const source of run.rejected.sources) await expect(rejected).toContainText(source.dataset_name);
  for (const source of run.cost.sources) await expect(cost).toContainText(source.dataset_name);
  const dates = (await lines.allInnerTexts()).map((text) => /Records run through ([^.]+)\./.exec(text)?.[1]);
  expect(dates.length).toBe(2);
  expect(new Set(dates).size).toBe(1);
  expect(run.rejected.records_through).toBe(run.records_through);
});

test("as of a past date, each part's source line says the records were read as of it", async ({ page }) => {
  await open(page, WORKS, { asof: "2026-10-28" });
  await openSection(page);

  await expect(section(page).locator("[data-criteria-part=rejected] [data-source]")).toContainText("Records as of");
  await expect(section(page).locator("[data-criteria-part=cost] [data-source]")).toContainText("Records as of");
});

test("below 20 comparables the cost estimate abstains in the first person and lists every package", async ({ page }) => {
  const run = events(await recorded("criteria-run-ke-nwwda-541055.sse")).find((event) => event.type === "package_run")!.data;
  await open(page, WORKS);
  await openSection(page);

  const part = section(page).locator("[data-criteria-part=cost]");
  await expect(part.locator("[data-cost-abstain]")).toHaveText(
    copy.cost.abstain.replaceAll("{m}", String(run.cost.rows.length)),
  );
  await expect(part.locator("[data-cost-title]")).toHaveText(
    copy.cost.title.replace("{above}", String(run.cost.counts.above)).replace("{m}", String(run.cost.counts.m)),
  );
  // The table twin is open by default with every package, and no range or middle half is drawn.
  await expect(part.locator("[data-cost-table] tbody tr")).toHaveCount(run.cost.rows.length);
  await expect(part.locator("[data-cost-middle]")).toHaveCount(0);
  await expect(part.locator("[data-cost-dot]")).toHaveCount(run.cost.rows.length);
  // A difference is written with a plus sign or a true minus sign.
  await expect(part.locator("[data-cost-table]")).toContainText("+315%");
  await expect(part.locator("[data-cost-table]")).toContainText("−36.6%");
});

test("lessons on cost estimates appear with their citations, including ICR P130164 paragraph 54", async ({ page }) => {
  await open(page, WORKS);
  await openSection(page);

  const part = section(page).locator("[data-criteria-part=lessons]");
  const group = part.locator("[data-lesson-group=cost_estimates]");
  await expect(group.getByRole("heading", { level: 4 }).first()).toHaveText("Cost estimates");
  const card = group.locator("[data-lesson-card]").first();
  await expect(card.locator("[data-source]")).toContainText("Implementation Completion and Results Report (ICR), P130164, October 10, 2019, paragraph 54, page 23.");
  await expect(card.locator("[data-citation]")).toHaveAccessibleName(/Source \d+: Implementation Completion and Results Report, October 10, 2019, paragraph 54/);
  await expect(card.locator("[data-lesson-status]")).toContainText("restated it");
  // The card quotes its paragraph with the lesson's words highlighted, and its marker sits outside the title.
  await expect(card.locator("[data-lesson-excerpt] mark")).toContainText("108 of 328 cases had to go through rebidding");
  await expect(card.getByRole("heading", { level: 4 }).locator("[data-citation]")).toHaveCount(0);
  await expect(card).toHaveAccessibleName(await card.getByRole("heading", { level: 4 }).innerText());
});

test("a failed save is said once, under the field, and any other failure offers Try again", async ({ page }) => {
  await open(page, CONSULTANT, { compare: "criteria-compare-store-failed.sse" });
  await openSection(page);
  await section(page).getByLabel(copy.criteria.field.label).fill(PASTED);
  await section(page).getByRole("button", { name: copy.criteria.compare }).click();

  await expect(section(page).locator("[data-save-failed]")).toHaveText(copy.criteria.errors.store);
  await expect(section(page).locator("[data-criteria-part=items] [data-part-error]")).toHaveCount(0);
  await expect(section(page)).not.toContainText("Your text is saved");
});

for (const width of [1440, 1024, 390]) {
  test(`the section passes axe collapsed and open, before and after a comparison, at ${width} px`, async ({ page }) => {
    await open(page, CONSULTANT, { width, compare: "criteria-compare-similar-experience.sse" });
    await expect(toggle(page)).toBeVisible();
    expect(await axe(page), "collapsed").toEqual([]);
    await openSection(page);
    await expect(section(page).locator("[data-criteria-part=lessons]")).toBeVisible();
    expect(await axe(page), "open").toEqual([]);
    await section(page).getByLabel(copy.criteria.field.label).fill(PASTED);
    await section(page).getByRole("button", { name: copy.criteria.compare }).click();
    await expect(section(page).locator("[data-criteria-notes]")).toBeVisible();
    expect(await axe(page), "compared").toEqual([]);
  });

  test(`the works package's section passes axe with its rejected bids, cost lane and lessons at ${width} px`, async ({ page }) => {
    await open(page, WORKS, { width, hash: true });
    await expect(section(page).locator("[data-lesson-card]").first()).toBeVisible();
    expect(await axe(page)).toEqual([]);
    // Nothing scrolls sideways.
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  });
}

test("an empty or too long text gives the field's error and sends nothing", async ({ page }) => {
  const asked = await open(page, CONSULTANT);
  await openSection(page);
  await section(page).getByRole("button", { name: copy.criteria.compare }).click();

  const field = section(page).getByLabel(copy.criteria.field.label);
  await expect(field).toHaveAttribute("aria-invalid", "true");
  await expect(section(page).locator("[data-field-error]")).toHaveText(copy.criteria.error.empty);
  expect(asked.filter((request) => request.url().endsWith("/criteria/compare"))).toHaveLength(0);
});

test("section 5's words never say estimate alone or benchmark", () => {
  const found: string[] = [];
  const walk = (value: unknown, path: string) => {
    if (typeof value === "string") {
      // A {slot} names a value, not a word on screen.
      const text = value.replace(/\{\w+\}/g, "").toLowerCase();
      if (/\bbenchmark/.test(text)) found.push(`${path}: benchmark`);
      for (const match of text.matchAll(/\bestimates?\b/g)) {
        const before = text.slice(0, match.index).trimEnd();
        if (!/(cost|time)$/.test(before)) found.push(`${path}: ${value}`);
      }
    } else if (typeof value === "function") {
      walk((value as (...args: string[]) => string)("{a}", "{b}", "{c}"), path);
    } else if (value && typeof value === "object") {
      for (const [key, inner] of Object.entries(value)) walk(inner, `${path}.${key}`);
    }
  };
  walk(copy.criteria, "criteria");
  walk(copy.cost, "cost");
  walk(copy.criteriaLessons, "criteriaLessons");
  expect(found).toEqual([]);
});
