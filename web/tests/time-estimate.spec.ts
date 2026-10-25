// The time estimate on screen (ticket 26) at seam 4: lane 2 of the range chart, "Compare with", the track record,
// the plan-date choice and section 4, against estimate_time's answers recorded in tests/fixtures/api
// (tests/record_estimate_api.py), which the server tests check the server against.
//
// On the fixture, KE-NWWDA-229129-CW-RFB, estimated at US$300,000, lies inside what the fixture's champion learned
// from, so its lane 2 draws in full; the demo package, KE-NWWDA-541055-CW-RFB, estimated at US$1,230,000.00, lies
// outside it and abstains; with review type Prior it has seven comparable packages (tests/ground_truth/values.toml).
// The fixture offers no comparison and holds no test year with 20 unseen packages, so the comparing, track-record
// and section 4 states are drawn from the recorded answer with the parts the test names changed, as the past
// range's tests derive theirs (web/tests/package.spec.ts). Every expected number is read from the answer served.
import type { Page, Request } from "@playwright/test";
import { scan } from "./axe";
import { expect, mockApi, recorded, test } from "./mocked";

const SIGNED = "KE-NWWDA-229129-CW-RFB";
const DEMO = "KE-NWWDA-541055-CW-RFB";
type Answer = { status?: number; body: string };
type Json = Record<string, unknown> & { [key: string]: any };

async function json(name: string): Promise<Json> {
  return JSON.parse(await recorded(name)) as Json;
}

async function openWorkspace(
  page: Page,
  options: { width?: number; ref?: string; estimate?: Answer; comparables?: Answer; reducedMotion?: boolean; rebidding?: Answer } = {},
) {
  const { width = 1440, ref = SIGNED } = options;
  await page.setViewportSize({ width, height: 900 });
  if (options.reducedMotion) await page.emulateMedia({ reducedMotion: "reduce" });
  const api = `/api/packages/${ref}`;
  const slug = ref === SIGNED ? "ke-nwwda-229129" : "ke-nwwda-541055";
  await mockApi(page, {
    "/api/me": { body: await recorded("me.json") },
    "/api/freshness": { body: await recorded("freshness.json") },
    [api]: { body: await recorded(`package-${slug}.json`) },
    [`${api}/comparables`]: options.comparables ?? { body: await recorded(`comparables-${slug}.json`) },
    [`${api}/risks`]: { body: await recorded(`risks-${slug}.json`) },
    [`${api}/plan-dates`]: { body: await recorded("plan-dates-saved.json") },
    [`${api}/estimate`]: options.estimate ?? { body: await recorded(`estimate-${slug}.json`) },
    ...(options.rebidding ? { [`${api}/rebidding`]: options.rebidding } : {}),
  });
  // Sections 2 and 5 and the rebidding block have their own tests; here they stay loading.
  for (const rest of ["steps", "criteria", ...(options.rebidding ? [] : ["rebidding"])]) {
    await page.route(`**${api}/${rest}`, () => new Promise(() => {}));
  }
  await page.goto(`/packages/${encodeURIComponent(ref)}`);
  await expect(page.locator("[data-past-range]:not([data-past-range=loading])")).toBeVisible();
  await expect(page.locator("[data-lane2=loading]")).toHaveCount(0);
}

// The recorded answer for KE-NWWDA-229129-CW-RFB, changed as a test needs.
async function derivedEstimate(edit: (body: Json, rows: string[]) => void): Promise<{ answer: Answer; body: Json }> {
  const body = await json("estimate-ke-nwwda-229129.json");
  const rows = ((await json("comparables-ke-nwwda-229129.json")).rows as { step_reference: string }[]).map((row) => row.step_reference);
  edit(body, rows);
  return { answer: { body: JSON.stringify(body) }, body };
}

const one = (value: number) => value.toFixed(1);
const plus = (points: Json, by: number) => ({ q25: points.q25 + by, q50: points.q50 + by, q75: points.q75 + by, q80: points.q80 + by, days: null });

// Two comparisons, as the tool returns them: prequalification, which 22 comparable packages went with and which has
// a time estimate, and 1 lot, which only 12 went with, too few for one.
function addComparisons(body: Json, rows: string[]) {
  const n = body.comparables.n;
  body.comparisons = [
    { lever: "prequalification", value: "Y", own: "N", k: 22, rest: n - 22, n, matching_ids: rows.slice(0, 22), unrecorded_ids: rows.slice(40), estimate: plus(body.estimate, 1), abstention: null },
    { lever: "lots", value: 1, own: 3, k: 12, rest: n - 12, n, matching_ids: rows.slice(0, 12), unrecorded_ids: [], estimate: null, abstention: { reason: "too_few_in_subgroup", k: 12, n, min_subgroup: 20 } },
  ];
  body.axis_max_months = body.estimate.q80 + 1;
}

// Three approaches for section 4: the most common as described, with its time estimate, and two too few went with.
function addOptions(body: Json, rows: string[]) {
  const n = body.comparables.n;
  body.options = {
    approaches: [
      { market_approach: "Open - National", lots: 1, prequalification: "N", k: 25, matching_ids: rows.slice(0, 25), is_as_described: true, estimate: plus(body.estimate, 0), abstention: null },
      { market_approach: "Open - National", lots: 2, prequalification: "N", k: 12, matching_ids: rows.slice(25, 37), is_as_described: false, estimate: null, abstention: { reason: "too_few_in_subgroup", k: 12, n, min_subgroup: 20 } },
      { market_approach: "Open - National", lots: 1, prequalification: "Y", k: 6, matching_ids: rows.slice(37, 43), is_as_described: false, estimate: null, abstention: { reason: "too_few_in_subgroup", k: 6, n, min_subgroup: 20 } },
    ],
    count: 3,
    recorded: 43,
    ruled_out: 0,
    unrecorded: 5,
    n,
    review_type: "Post",
  };
}

// A track record from a test year with 120 packages the model had not seen, and the plan dates' counts from it.
function addTrackRecord(body: Json) {
  body.track_record = { year: 2025, n: 120, m: 95, expected: 96, ran_on: "2026-10-23", misses: 25, misses_early: null, misses_late: null, abstention: null };
  body.plan_dates = {
    middle: { months: body.estimate.q50, ran_longer: 61, total: 120, in10: 5 },
    eight_in_ten: { months: body.estimate.q80, ran_longer: 25, total: 120, in10: 2 },
    default: "eight_in_ten",
  };
}

async function comparing() {
  return derivedEstimate(addComparisons);
}

const section = (page: Page) => page.locator("[data-past-range]");
const summary = (page: Page) => section(page).locator("[data-summary]");
const compare = (page: Page) => page.getByRole("group", { name: "Compare with" });

test("lane 2 draws the stored time estimate as a navy middle-half bar, a white notch, a line to the 8-in-10 point and its end cap", async ({ page }) => {
  await openWorkspace(page);
  const estimate = (await json("estimate-ke-nwwda-229129.json")).estimate;

  const bar = section(page).locator("svg [data-lane2=estimate] [data-lane2-bar]");
  await expect(bar.locator("rect")).toHaveCount(4);
  await expect(bar.locator("rect").first()).toHaveClass(/fill-primary/);
  await expect(bar.locator("[data-lane2-notch]")).toHaveClass(/fill-surface/);
  await expect(bar.locator("[data-lane2-connector]")).toHaveCount(1);
  await expect(bar.locator("[data-lane2-cap]")).toHaveCount(1);
  await expect(page.locator("[data-chart-drawing]").getByText("Time estimate for this package", { exact: true })).toBeVisible();
  await expect(section(page).locator("[data-row-e=middle]")).toHaveText(`Middle half ${one(estimate.q25)} to ${one(estimate.q75)}, middle ${one(estimate.q50)}`);
  await expect(section(page).locator("[data-row-e=in10]")).toHaveText(`8 in 10 within ${one(estimate.q80)}`);
  await expect(summary(page)).toContainText(
    `For this package, I estimate ${one(estimate.q25)} to ${one(estimate.q75)} months for the middle half and ${one(estimate.q80)} months for 8 in 10.`,
  );
  // The chart's text alternative states lane 2's numbers too.
  await expect(page.locator("[data-chart-alt]")).toContainText(
    `Time estimate for this package: middle half ${one(estimate.q25)} to ${one(estimate.q75)} months, middle ${one(estimate.q50)}, 8 in 10 within ${one(estimate.q80)}.`,
  );
  if (process.env.STRATA_SHOT) await page.screenshot({ path: process.env.STRATA_SHOT, fullPage: true });
});

test("the sentence on why the lanes differ uses the tool's difference and counts", async ({ page }) => {
  const { answer, body } = await derivedEstimate((body) => {
    body.difference = { middle_diff_months: body.difference.middle_diff_months, direction: "later", reasons: [{ code: "size_larger", k: body.comparables.n - 6, n: body.comparables.n }] };
  });
  await openWorkspace(page, { estimate: answer });
  const { middle_diff_months: diff, reasons } = body.difference;
  await expect(summary(page)).toContainText(
    `My time estimate's middle is ${one(diff)} months later than the past range's, mainly because this package is larger than ${reasons[0].k} of the ${reasons[0].n} comparable packages.`,
  );
});

test("pressing a Compare with segment lights the dots that went with it, counts them, and leaves the estimate as described as a ghost", async ({ page }) => {
  const { answer, body } = await comparing();
  // "Advertised again" (ticket 28) only needs an answer to show here; the demo package's recorded one stands in.
  await openWorkspace(page, { estimate: answer, rebidding: { body: await recorded("rebidding-ke-nwwda-541055.json") } });
  const [preq] = body.comparisons;
  const n = body.comparables.n;
  await expect(page.locator("[data-rebidding]")).toBeVisible();
  await expect(page.locator("[data-rebid-compare]")).toHaveCount(0);

  const segment = compare(page).getByRole("button", { name: "Prequalification" });
  await expect(segment).toHaveAttribute("aria-pressed", "false");
  expect((await segment.boundingBox())!.height).toBeGreaterThanOrEqual(32);
  await expect(page.locator("[data-lane2-ghost]")).toHaveCount(0);

  await segment.click();
  await expect(segment).toHaveAttribute("aria-pressed", "true");
  // The matching dots keep their look; every other dot turns grey and smaller. The browser decides no match.
  await expect(page.locator("[data-chart-drawing] [data-went-with=yes]")).toHaveCount(preq.k);
  await expect(page.locator("[data-chart-drawing] [data-went-with=no]")).toHaveCount(n - preq.k);
  await expect(section(page).locator("[data-key-a]")).toContainText(`${preq.k} went with prequalification`);
  await expect(section(page).locator("[data-key-a]")).toContainText(`${n - preq.k} others`);
  // The bar moves to the comparison, and the estimate as described stays as a dashed ghost.
  await expect(page.locator("[data-lane2-ghost]")).toHaveCount(1);
  await expect(section(page).locator("[data-row-e=middle]")).toHaveText(`Middle half ${one(preq.estimate.q25)} to ${one(preq.estimate.q75)}, middle ${one(preq.estimate.q50)}`);
  const e = body.estimate;
  await expect(summary(page)).toContainText(
    `${preq.k} of the ${n} comparable packages went with prequalification. With prequalification, I estimate ${one(preq.estimate.q25)} to ` +
      `${one(preq.estimate.q75)} months for the middle half and ${one(preq.estimate.q80)} months for 8 in 10, against ${one(e.q25)} to ${one(e.q75)} and ${one(e.q80)} months as described.`,
  );
  await expect(section(page)).not.toContainText(/\b(caused|split|splitting)\b/i);
  await expect(page.locator("[data-chart-alt]")).toContainText(`Compared with prequalification: ${preq.k} of ${n} comparable packages went with it`);
  await expect(page.locator("[data-chart-alt]")).toContainText(`A dashed outline shows the time estimate as described: middle half ${one(e.q25)} to ${one(e.q75)} months`);
  // "Advertised again" says the comparison leaves its count alone (the 28 brief, section 6.5).
  await expect(page.locator("[data-rebid-compare]")).toHaveText("The comparison above doesn't change this count. It is for this package's own criteria.");

  // Pressing it again stops comparing.
  await segment.click();
  await expect(segment).toHaveAttribute("aria-pressed", "false");
  await expect(page.locator("[data-lane2-ghost]")).toHaveCount(0);
  await expect(page.locator("[data-chart-drawing] [data-went-with]")).toHaveCount(0);
  await expect(section(page).locator("[data-row-e=middle]")).toHaveText(`Middle half ${one(e.q25)} to ${one(e.q75)}, middle ${one(e.q50)}`);
  await expect(page.locator("[data-rebid-compare]")).toHaveCount(0);
});

test("Compare with is one tab stop the arrow keys move through without pressing, and Space presses; too few gives the ghost alone", async ({ page }) => {
  const { answer, body } = await comparing();
  await openWorkspace(page, { estimate: answer });
  const [preq, lots] = body.comparisons;
  const first = compare(page).getByRole("button", { name: "Prequalification" });
  const second = compare(page).getByRole("button", { name: "1 lot" });
  await expect(first).toHaveAttribute("tabindex", "0");
  await expect(second).toHaveAttribute("tabindex", "-1");

  await first.focus();
  await page.keyboard.press("ArrowRight");
  await expect(second).toBeFocused();
  await expect(second).toHaveAttribute("aria-pressed", "false");
  await page.keyboard.press("ArrowRight");
  await expect(first).toBeFocused();
  await page.keyboard.press("End");
  await expect(second).toBeFocused();
  await page.keyboard.press("Space");
  await expect(second).toHaveAttribute("aria-pressed", "true");
  await expect(first).toHaveAttribute("aria-pressed", "false");

  // Too few went with 1 lot: lane 1 lights its dots, lane 2 keeps only the ghost and says why.
  await expect(page.locator("[data-chart-drawing] [data-went-with=yes]")).toHaveCount(lots.k);
  await expect(page.locator("[data-lane2-bar]")).toHaveCount(0);
  await expect(page.locator("[data-lane2-ghost]")).toHaveCount(1);
  await expect(section(page).locator("[data-lane2-note]")).toHaveText(`Only ${lots.k} went with 1 lot, too few for a time estimate.`);
  await expect(summary(page)).toContainText(`Only ${lots.k} of the ${lots.n} comparable packages went with 1 lot, so I'm not giving a time estimate for it.`);

  // Enter moves the one comparison to the other segment.
  await page.keyboard.press("Home");
  await page.keyboard.press("Enter");
  await expect(first).toHaveAttribute("aria-pressed", "true");
  await expect(second).toHaveAttribute("aria-pressed", "false");
  await expect(page.locator("[data-chart-drawing] [data-went-with=yes]")).toHaveCount(preq.k);
});

test("under reduced motion lane 2's bar and the dots change at once, with no transition", async ({ page }) => {
  const { answer } = await comparing();
  await openWorkspace(page, { estimate: answer, reducedMotion: true });
  await compare(page).getByRole("button", { name: "Prequalification" }).click();
  const durations = await page.locator("[data-lane2-move], [data-dot-mark]").evaluateAll((elements) =>
    elements.map((element) => getComputedStyle(element).transitionDuration),
  );
  expect(durations.length).toBeGreaterThan(0);
  expect(durations.filter((duration) => duration.split(",").some((part) => parseFloat(part) > 0))).toEqual([]);
});

test("the track record states the backtest's counts, and the plan-date choice starts on the cautious date and saves a change", async ({ page }) => {
  const { answer, body } = await derivedEstimate(addTrackRecord);
  await openWorkspace(page, { estimate: answer });
  const track = body.track_record;
  await expect(section(page).locator("[data-track-record]")).toHaveText(
    `Track record: of ${track.n} packages from ${track.year} that I had not seen, ${track.m} finished inside my 8-in-10 range, where a well-sized range catches about ${track.expected}.`,
  );

  const choice = page.getByRole("group", { name: "Dates I draft for this package" });
  const cautious = choice.getByRole("radio", { name: `${one(body.estimate.q80)} months: about 2 in 10 ran longer` });
  const middle = choice.getByRole("radio", { name: `${one(body.estimate.q50)} months: about half ran longer` });
  await expect(cautious).toBeChecked();
  await expect(middle).not.toBeChecked();

  const saved = page.waitForRequest((request: Request) => request.method() === "PUT" && request.url().endsWith(`/api/packages/${SIGNED}/plan-dates`));
  // The radios are inside their segments' labels, as section 2's are, so the label takes the click.
  await choice.locator("label", { hasText: "about half ran longer" }).click();
  expect((await saved).postDataJSON()).toMatchObject({ choice: "middle" });
  await expect(middle).toBeChecked();
});

test("for a viewer who can't read the backtest results, the track record says so, never that there are none", async ({ page }) => {
  // The tool's answer when strata.ops refuses this viewer (tests/test_estimate_time.py's NoOpsGrant).
  const { answer } = await derivedEstimate((body) => {
    body.track_record = { year: null, abstention: { reason: "not_readable" } };
    body.test_years = [];
  });
  await openWorkspace(page, { estimate: answer });
  const track = section(page).locator("[data-track-record]");
  await expect(track).toHaveText("I couldn't read my backtest results, so I can't give a track record.");
  await expect(track).not.toContainText("no backtest results yet");
});

test("section 4 opens on demand to at most three approaches, each counted out of the same comparable packages as lane 1", async ({ page }) => {
  const { answer, body } = await derivedEstimate(addOptions);
  await openWorkspace(page, { estimate: answer });
  const options = page.locator("[data-approach-options]");
  const n = body.comparables.n;
  await expect(options).toContainText("Procurement approach options");
  await expect(options).toContainText(`Comparable packages went with three approaches. The most common was open national, 1 lot, post-qualification, with 25 of ${n}.`);
  const button = options.getByRole("button", { name: "Show the options" });
  await expect(button).toHaveAttribute("aria-expanded", "false");
  await expect(options.locator("[data-approach-table]")).toHaveCount(0);

  await button.click();
  await expect(options.getByRole("button", { name: "Hide the options" })).toHaveAttribute("aria-expanded", "true");
  const rows = options.locator("[data-approach-table] table tbody tr");
  await expect(rows).toHaveCount(3);
  await expect(rows.nth(0)).toContainText(`25 of ${n}`);
  await expect(rows.nth(0)).toContainText("As described above");
  await expect(rows.nth(1)).toContainText(`12 of ${n}`);
  await expect(rows.nth(1)).toContainText("No time estimate: only 12 went with it");
  // With no approach ruled out, the table's caption may call the first approach the most common of all.
  await expect(options.locator("[data-approach-table] caption")).toContainText(
    `25 of the ${n} comparable packages went with open national, 1 lot, post-qualification, the most common approach.`,
  );
  // n is lane 1's total: the same comparable packages find_comparables returned.
  const lane1 = (await json("comparables-ke-nwwda-229129.json")).counts.comparables;
  expect(n).toBe(lane1);
  await expect(options).toContainText("Review type stays Post for every approach");
  await expect(options).not.toContainText(/\b(caused|split|splitting)\b/i);
  // The count of those that record no whole approach is the tool's, not worked out in the browser.
  await expect(options).toContainText(`Five of the ${n} comparable packages don't record their market approach, lots and qualification`);
  await expect(options).not.toContainText("the thresholds rule out");
});

test("section 4 says when the thresholds rule out the whole approaches comparable packages recorded, never that none recorded one", async ({ page }) => {
  // Ana's rural roads package, about US$15 million: the three comparable packages that record their whole approach
  // went national, which the thresholds rule out for a Kenya works package that large (its recorded answer).
  const planned = (await json("estimate-planned-rural-roads.json")).options;
  expect([planned.approaches.length, planned.recorded, planned.ruled_out]).toEqual([0, 3, 3]);
  const { answer } = await derivedEstimate((body) => {
    body.options = planned;
  });
  await openWorkspace(page, { estimate: answer });
  const options = page.locator("[data-approach-options]");
  await expect(options).toContainText(
    "The three comparable packages that record their market approach, lots and qualification went with approaches the thresholds rule out for this package, so I can't list approach options.",
  );
  await expect(options).not.toContainText("None of the");
});

test("with one approach left, section 4 counts the comparable packages whose approach the thresholds rule out apart from those that record none", async ({ page }) => {
  const { answer, body } = await derivedEstimate((body, rows) => {
    const n = body.comparables.n;
    body.options = {
      approaches: [{ market_approach: "Open - National", lots: 1, prequalification: "N", k: 2, matching_ids: rows.slice(0, 2), is_as_described: true, estimate: plus(body.estimate, 0), abstention: null }],
      count: 1,
      recorded: 3,
      ruled_out: 1,
      unrecorded: n - 3,
      n,
      review_type: "Post",
    };
  });
  await openWorkspace(page, { estimate: answer });
  const options = page.locator("[data-approach-options]");
  await expect(options).toContainText(
    `Two of the ${body.comparables.n} comparable packages went with open national, 1 lot, post-qualification. One went with an approach the thresholds rule out for this package, so I have no other approach to compare.`,
  );
  await expect(options).not.toContainText("The rest don't record");
});

test("with approaches to list, section 4 names those the thresholds allow and counts the comparable packages that went with one they rule out", async ({ page }) => {
  const { answer, body } = await derivedEstimate((body, rows) => {
    addOptions(body, rows);
    Object.assign(body.options, { recorded: 45, ruled_out: 2, unrecorded: 3 });
  });
  await openWorkspace(page, { estimate: answer });
  const options = page.locator("[data-approach-options]");
  const n = body.comparables.n;
  await expect(options).toContainText(
    `Comparable packages went with three approaches the thresholds allow for this package. The most common was open national, 1 lot, post-qualification, with 25 of ${n}.`,
  );
  await options.getByRole("button", { name: "Show the options" }).click();
  // The tool doesn't count each ruled-out approach, so the caption claims only the most common one the thresholds allow.
  const caption = options.locator("[data-approach-table] caption");
  await expect(caption).toContainText(
    `25 of the ${n} comparable packages went with open national, 1 lot, post-qualification, the most common approach the thresholds allow for this package.`,
  );
  await expect(caption).not.toContainText("the most common approach.");
  await expect(options).toContainText(`Two of the ${n} comparable packages went with approaches the thresholds rule out for this package, so I left those approaches out.`);
  await expect(options).toContainText(`Three of the ${n} comparable packages don't record their market approach, lots and qualification`);
});

test("with fewer than 20 comparable packages lane 2 says so in the first person, with no bar, no comparison and no plan dates", async ({ page }) => {
  await openWorkspace(page, {
    ref: DEMO,
    comparables: { body: await recorded("comparables-ke-nwwda-541055-prior.json") },
    estimate: { body: await recorded("estimate-ke-nwwda-541055-prior.json") },
  });
  const count = (await json("estimate-ke-nwwda-541055-prior.json")).abstention.count;
  expect(count).toBeLessThan(20);
  await expect(section(page).locator("[data-lane2-message=abstain]")).toHaveText(`I'm not giving a time estimate: only ${count === 7 ? "seven" : count} comparable packages.`);
  await expect(page.locator("[data-lane2-bar]")).toHaveCount(0);
  await expect(compare(page)).toHaveCount(0);
  await expect(page.locator("[data-track-record]")).toHaveCount(0);
  await expect(page.getByRole("group", { name: "Dates I draft for this package" })).toHaveCount(0);
  await expect(page.locator("[data-approach-options]")).toContainText(`I'm not listing approach options: only ${count === 7 ? "seven" : count} comparable packages.`);
});

// Lane 2 has no time estimate for a reason other than too few comparable packages: an as-of date before the end of
// the model's training data, as recorded, or no model scored yet, which every package answers until the live
// backtest keeps a champion. Section 4 then gives that reason, never the count, which is well above 20.
for (const [when, abstention] of [
  ["for an as-of date before the model's training data", null],
  ["before any model is scored", { reason: "no_model" }],
] as const) {
  test(`with no time estimate ${when}, section 4 says it has no time estimate and never that it has too few comparable packages`, async ({ page }) => {
    const body = await json("estimate-ke-nwwda-229129-before-training.json");
    expect(body.abstention.reason).toBe("asof_before_training");
    expect(body.comparables.n).toBeGreaterThanOrEqual(body.thresholds.min_comparables);
    if (abstention) body.abstention = abstention;
    await openWorkspace(page, { estimate: { body: JSON.stringify(body) } });
    const options = page.locator("[data-approach-options]");
    await expect(options).toContainText("I'm not listing approach options, because I have no time estimate for this package.");
    await expect(options).not.toContainText(`only ${body.comparables.n}`);
    await expect(options).not.toContainText("comparable packages.");
  });
}

test("at 1440 px axe finds no WCAG 2.2 AA violations while comparing, with section 4 and the table twin open", async ({ page }) => {
  const { answer } = await derivedEstimate((body, rows) => {
    addComparisons(body, rows);
    addOptions(body, rows);
    addTrackRecord(body);
  });
  await openWorkspace(page, { estimate: answer });
  await compare(page).getByRole("button", { name: "Prequalification" }).click();
  await page.locator("[data-approach-options]").getByRole("button", { name: "Show the options" }).click();
  await section(page).getByRole("button", { name: "Show the table" }).click();
  await expect(page.locator("[data-time-estimate-table]")).toBeVisible();
  const results = await scan(page);
  expect(results.violations.map((v) => `${v.id}: ${v.nodes.map((node) => node.target.join(" ")).join(", ")}`)).toEqual([]);
});
