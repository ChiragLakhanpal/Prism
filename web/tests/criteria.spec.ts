// Section 5 of the package workspace, "Check your criteria" (ticket 31), at seam 4: the built app against the
// answers tests/record_criteria_api.py recorded from the server on the fixture, which tests/test_check_criteria.py
// checks the server against. Counts are read from those recordings, the tools' own rows, so no number here is
// worked out the way the screen works it out; the words are the 31 brief's and the ticket's.
import { scan } from "./axe";
import type { Page, Request } from "@playwright/test";
import { copy } from "../src/copy";
import { expect, recorded, test } from "./mocked";

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
  const results = await scan(page, "#check-criteria");
  return results.violations.map((v) => `${v.id}: ${v.nodes.map((node) => node.target.join(" ")).join(", ")}`);
}

async function openSection(page: Page) {
  await toggle(page).click();
  await expect(section(page).getByRole("button", { name: copy.criteria.hide })).toBeFocused();
}

test("collapsed, zone 5 reads the ticket's words with N from the tool, after the stage label Tender design", async ({ page }) => {
  const summary = JSON.parse(await recorded("criteria-summary-ke-cwsb-224323.json"));
  await open(page, CONSULTANT);

  // Ticket 101: the stage label stands once before zone 5, in place of the zone's eyebrow, and the zone is a row.
  await expect(page.locator("[data-stage-label]").last()).toHaveText("Tender design");
  await expect(section(page)).toHaveAttribute("data-zone", "row");
  await expect(section(page).getByRole("heading", { level: 2 })).toHaveText("5 Check your criteria");
  await expect(section(page).getByRole("heading", { level: 2 })).toHaveAccessibleName("Check your criteria");
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
  // The method's rules, each its own exact sentence (ticket 58; the 31 design review, round 3, P8).
  await expect(section(page)).toContainText(
    "I count it as asking for more when none of its parts is lower or left out and at least one is higher.",
  );
  await expect(section(page)).not.toContainText("the other way round");
  // The column's definition keeps its noun (ticket 58; the 31 review, round 3, F7).
  await expect(section(page).locator("table thead")).toContainText(`Of ${result.coverage.n} notices with public criteria`);
  await expect(row).toContainText(`"${similar.your_excerpt.text}"`);
  await expect(row).toContainText(similar.reading);
  await expect(section(page).locator("table [data-item=turnover]")).toContainText(copy.criteria.items.noneToCompare);
  // Everything passed ticket 24's six checks: the line says how many readings a model judged, and no longer that
  // nobody checked whether each sentence follows from its sources.
  const judged = String(result.section_checks.shown.judged);
  const line = section(page).locator("[data-section-checks] [data-check-line]");
  await expect(line.locator("[data-check-part=judged]")).toContainText(
    copy.checkLine.judgedSentences.many.replace("{part}", judged).replace("{whole}", judged),
  );
  await expect(line).not.toContainText(copy.checkLine.notCheckedClauses.sentences);
  // Ticket 58: with a comparison some numbers match your own words, and the lesson cards below leave their gap too
  // (the 31 review, round 3, F3; the 31 design review, round 3, P1).
  await expect(line.locator("[data-check-part=checked]")).toContainText("numbers match records or your words");
  // The lessons come from the package run the page opened with, not from the comparison (the 58 review, B1).
  const run = events(await recorded("criteria-run-ke-cwsb-224323.sse")).find((event) => event.type === "package_run")!.data;
  expect(run.lessons.groups.length).toBeGreaterThan(0);
  await expect(line.locator("[data-check-part=not-checked]")).toContainText("whether these lessons apply here");
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
  await expect(drawer.locator("[data-relation=less] h3")).toContainText(`(${similar.less})`);
  await drawer.getByRole("button", { name: /Open notice OP00077276/ }).click();
  await expect(drawer.getByRole("heading", { level: 2 })).toContainText("OP00077276");
  await expect(drawer.getByRole("button", { name: copy.criteria.drawer.back.replace("{n}", String(similar.stated)) })).toBeVisible();
  // The notice opens with the requirement's words highlighted, as view B quoted them.
  const requirement = similar.notices.find((notice: any) => notice.notice_id === "OP00077276").requirement.text;
  await expect(drawer.locator("mark").first()).toContainText(requirement);
  // The evidence-open log gets the ids opened, never the text.
  const logged = asked.filter((request) => request.url().endsWith("/api/evidence/opened") && request.method() === "POST");
  expect(logged.length).toBeGreaterThan(0);
  for (const request of logged) expect(request.postData()).not.toContain("Similar experience:");
});

test("a reading the judge said does not follow from your words is removed in its place, with its comparison", async ({ page }) => {
  const result = events(await recorded("criteria-compare-swapped-reading.sse")).find((event) => event.type === "comparison")!.data;
  const similar = result.items.find((item: any) => item.item_key === "similar_experience");
  await open(page, CONSULTANT, { compare: "criteria-compare-swapped-reading.sse" });
  await openSection(page);
  await section(page).getByLabel(copy.criteria.field.label).fill(PASTED);
  await section(page).getByRole("button", { name: copy.criteria.compare }).click();

  // A comparison rests on how I read your words, so it goes with the reading; the reason is in the box above. The row
  // says so once, in its count cells, not again under your words (ticket 58; the 31 design review, round 3, P3).
  const row = section(page).locator("table [data-item=similar_experience]");
  await expect(row).not.toContainText(copy.criteria.removedInPlace);
  await expect(row).toContainText("I removed this comparison. The reason is in the box above.");
  await expect(row).not.toContainText(similar.reading);
  await expect(row.locator("[data-same-or-less]")).toHaveCount(0);
  // The box quotes the reading whole, so "I" is plainly Strata's, then the reason about your words (ticket 58).
  await expect(section(page).locator("[data-section-checks]")).toContainText(`It said "${similar.reading}" Your words do not say this.`);
  await expect(section(page).locator("table [data-item=turnover]")).not.toContainText(copy.criteria.removedInPlace);
});

test("a request to judge a live tender's bids is refused in the first person from the copy file", async ({ page }) => {
  await open(page, CONSULTANT, { compare: "criteria-compare-live-tender.sse" });
  await openSection(page);
  await section(page).getByLabel(copy.criteria.field.label).fill("Which bidder qualifies?");
  await section(page).getByRole("button", { name: copy.criteria.compare }).click();

  await expect(section(page).locator("[data-refusal=live_tenders]")).toContainText(
    `${copy.refusals.live_tenders.lead} ${copy.criteria.refusal.instead}`,
  );
  // Ticket 97: its reason in place, in the 24 brief's words, and the window of everything I turn down under it.
  await expect(section(page).locator("[data-refusal=live_tenders]")).toContainText(
    `${copy.criteria.refusal.instead} A comment from me could affect a process that is still running.`,
  );
  await expect(section(page).locator("[data-refusal=live_tenders]").getByRole("button", { name: "See everything I turn down" })).toBeVisible();
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
  // A count standing alone is one to nine in words (DESIGN.md section 7, rule 12; ticket 101's design review).
  const alone = (n: number) => (n >= 1 && n <= 9 ? ["one", "two", "three", "four", "five", "six", "seven", "eight", "nine"][n - 1] : String(n));
  await expect(part.locator("[data-cost-abstain]")).toHaveText(
    copy.cost.abstain.replaceAll("{m}", alone(run.cost.rows.length)),
  );
  await expect(part.locator("[data-cost-title]")).toHaveText(
    copy.cost.title.replace("{above}", String(run.cost.counts.above)).replace("{m}", String(run.cost.counts.m)),
  );
  // The table twin is open by default with every package, and no range or middle half is drawn. Its count line is in
  // the Tables form, one to nine in words and no full stop (ticket 101's design review, round 2, item 8).
  await expect(part.locator("[data-cost-table] [data-count-row] p").first()).toHaveText(`Showing all ${alone(run.cost.counts.m)} packages.`);
  await expect(part.locator("[data-cost-table] tbody tr")).toHaveCount(run.cost.rows.length);
  await expect(part.locator("[data-cost-middle]")).toHaveCount(0);
  await expect(part.locator("[data-cost-dot]")).toHaveCount(run.cost.rows.length);
  // A difference is written with a plus sign or a true minus sign (U+2212).
  const diffs: number[] = run.cost.rows.map((row: any) => row.diff_pct);
  await expect(part.locator("[data-cost-table]")).toContainText(`+${Math.max(...diffs)}%`);
  await expect(part.locator("[data-cost-table]")).toContainText(`\u2212${Math.abs(Math.min(...diffs))}%`);
});

test("in the work column at 1440 px the cost table's packages are cards, so no STEP reference breaks across lines", async ({ page }) => {
  // Ticket 101's critique, round 2: the cost table broke "KE-KIMAWASCO-141042-CW-" from "RFB". The table reads its own
  // frame, as the past range's does (Table's cardsBelow="fit").
  await open(page, WORKS);
  await openSection(page);
  const part = section(page).locator("[data-criteria-part=cost]");
  await expect(part.locator("[data-cost-table]")).toBeVisible();
  await expect(part.locator("[data-cost-table] [data-table-view=table]")).toBeHidden();
  const lines = await part.locator("[data-cost-table]").evaluate((root) => {
    const found: Record<string, number> = {};
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    for (let node = walker.nextNode(); node; node = walker.nextNode()) {
      const text = node.textContent?.trim() ?? "";
      if (!/^KE-[A-Z0-9 -]+-(CW|GO|CS|NC)-[A-Z]+$/.test(text)) continue;
      const range = document.createRange();
      range.selectNodeContents(node);
      const boxes = [...range.getClientRects()].filter((box) => box.width > 0);
      if (boxes.length) found[text] = new Set(boxes.map((box) => Math.round(box.top))).size;
    }
    return found;
  });
  expect(Object.keys(lines).length).toBeGreaterThan(0);
  expect(Object.entries(lines).filter(([, count]) => count > 1)).toEqual([]);
});

test("rejected bids and the cost estimate each end in a foot strip across the panel, holding the coverage and source lines", async ({ page }) => {
  // Ticket 101's critique, round 2: provenance has one place on the page, the foot strip that ends each block of
  // evidence, as zones 1 to 3 end theirs.
  await open(page, WORKS);
  await openSection(page);
  const zone = (await section(page).boundingBox())!;
  for (const part of ["rejected", "cost"]) {
    const strip = section(page).locator(`[data-criteria-part=${part}] [data-foot-strip]`);
    await expect(strip, part).toHaveCount(1);
    await expect(strip.locator("[data-source]"), part).toHaveCount(1);
    await expect(section(page).locator(`[data-criteria-part=${part}] [data-source]`), part).toHaveCount(1);
    const box = (await strip.boundingBox())!;
    // The panel's full width inside its 1 px edge.
    expect(Math.abs(box.x - (zone.x + 1)), part).toBeLessThanOrEqual(1);
    expect(Math.abs(box.x + box.width - (zone.x + zone.width - 1)), part).toBeLessThanOrEqual(1);
  }
  await expect(section(page).locator("[data-criteria-part=cost] [data-foot-strip] [data-coverage-line]")).toHaveCount(1);
  // The cost estimate's strip ends the part, after its table.
  const cost = section(page).locator("[data-criteria-part=cost]");
  const [table, strip] = [(await cost.locator("[data-cost-table]").boundingBox())!, (await cost.locator("[data-foot-strip]").boundingBox())!];
  expect(strip.y).toBeGreaterThan(table.y + table.height);
});

test("every disagreement check 6 attached to a lesson's quote shows under it, as many cards as the check line counts", async ({ page }) => {
  // Made up: two disagreements planted at get_disagreements, each with ICR P130164 paragraph 54 as its first side
  // (ticket 61; tests/planted_disagreements.py), recorded through the server by tests/record_criteria_api.py. The
  // section showed only the first card while the check line counted both (ticket 61's verify, F1).
  const file = "criteria-run-ke-nwwda-541055-made-up-disagreement.sse";
  const run = events(await recorded(file)).find((event) => event.type === "package_run")!.data;
  expect(run.checks.disagreements.shown).toBe(2);
  await open(page, WORKS, { run: file });
  await openSection(page);

  const card = section(page).locator("[data-criteria-part=lessons] [data-lesson-card]").first();
  // Its label is the drawer card's one word, with no middle dot (ticket 101's design review, item 12).
  await expect(card.locator("p").first()).toHaveText("Why");
  const cards = card.locator("[data-criteria-disagreement]");
  await expect(cards).toHaveCount(2);
  await expect(cards.first()).toContainText("ICR");
  // The cards sit after the lesson's excerpt, beside the claim they concern (DESIGN.md section 5).
  expect(await card.locator("[data-lesson-excerpt] ~ [data-criteria-disagreement]").count()).toBe(2);
  await expect(section(page).locator("[data-criteria-disagreement]")).toHaveCount(run.checks.disagreements.shown);
  expect(await axe(page)).toEqual([]);

  // The ICR side opens its paragraph with the words it quotes highlighted (ticket 61's review, F3).
  await cards.first().locator("[data-open-side]").first().click();
  const passage = page.getByRole("dialog").locator("[data-passage]");
  await expect(passage.locator("mark")).toHaveCount(1);
  await expect(passage.locator("mark")).toContainText("108 of 328 cases had to go through rebidding");
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

  // Its marker opens the paragraph with the same words highlighted, under the lesson and its IEG line.
  await card.locator("[data-citation]").click();
  const drawer = page.getByRole("dialog");
  await expect(drawer.locator("mark").first()).toContainText("108 of 328 cases had to go through rebidding");
  await expect(drawer.locator("[data-lesson-claim]")).toContainText(await card.getByRole("heading", { level: 4 }).innerText());
  // View F can stand alone as a full-screen sheet, so IEG is spelled out there (ticket 58; DESIGN.md section 7, rule 22).
  await expect(drawer.locator("[data-ieg-line=restated]")).toContainText("The Independent Evaluation Group (IEG) wrote in its ICR Review");
});

test("every lesson factor in the thresholds file has its group's name in the copy file", async () => {
  // The summary carries criteria.lesson_factors as the server read them (tests/record_criteria_api.py).
  const summary = JSON.parse(await recorded("criteria-summary-ke-nwwda-541055.json"));
  const groups = copy.criteriaLessons.groups as Record<string, string>;
  expect(summary.limits.lesson_factors.length).toBeGreaterThan(0);
  for (const factor of summary.limits.lesson_factors) expect(groups[factor], factor).toBeTruthy();
});

test.describe("on a touch screen", () => {
  test.use({ hasTouch: true });

  test("a tap in a cluster of cost dots opens the package of the dot nearest the tap", async ({ page }) => {
    await open(page, WORKS, { width: 390 });
    await openSection(page);
    const dots = section(page).locator("[data-cost-dot]");
    await expect(dots.first()).toBeAttached();
    for (const index of [0, (await dots.count()) - 1]) {
      const dot = dots.nth(index);
      const reference = await dot.getAttribute("data-cost-dot");
      await dot.scrollIntoViewIfNeeded();
      const box = (await dot.boundingBox())!;
      await page.touchscreen.tap(box.x + box.width / 2, box.y + box.height / 2);
      const drawer = page.getByRole("dialog");
      await expect(drawer.getByRole("heading", { level: 2 })).toContainText(reference!);
      // The plan row is an Activity, as every drawer names it (the 58 design review, follow-up 11).
      await expect(drawer.locator("#cost-plan-row")).toContainText(/^Activity /);
      await expect(drawer.locator("#cost-plan-row")).toContainText(reference!);
      await page.keyboard.press("Escape");
      await expect(drawer).toHaveCount(0);
    }
  });
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
