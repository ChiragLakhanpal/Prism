// Ticket 137: section 1's period of notices never ends before it starts. On October 29, 2026 the walkthrough's capture
// of IN-RRSMP-7516-CW-RFB (P130164, plan of June 20, 2018) read "They had to be in India and have notices from July 1,
// 2019 to June 20, 2018". find_comparables now runs a plan older than the awards data to the as-of date and says so in
// criteria.period, and when the period still ends before it starts, the section says why no package can match.
//
// The first test builds the period's words for every plan date the fixture holds, from find_comparables' periods
// recorded in tests/fixtures/api/notice-periods.json (tests/record_comparables_api.py, which
// tests/test_comparables_period.py checks against the tool). The others open P130164's package on answers recorded
// from a copy of the fixture that holds its plan row. The sentences are the ticket's, copied here.
import { expect as plainExpect, test as plainTest } from "@playwright/test";
import type { ComparablesPeriod } from "../src/lib/api";
import { formatDate } from "../src/lib/format";
import { periodWords, type PeriodForm } from "../src/lib/period";
import { expect, mockApi, recorded, test } from "./mocked";

type Period = { plan_date: string; as_of: string; notice_from: string; notice_to: string; period: ComparablesPeriod };

const DATE = /(?:January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2}, \d{4}/g;

// The words as the screen writes them: each slot's date in the sentence style Num gives it.
function written(entry: Period, form: PeriodForm) {
  const words = periodWords(entry, form, entry.as_of);
  return words.template.replace(/\{(\w+)\}/g, (_, slot: "from" | "to" | "asOf") => formatDate(words.slots[slot] ?? ""));
}

plainTest("for every plan date in the fixture, section 1 never names a period that ends before it starts", async () => {
  const { periods } = JSON.parse(await recorded("notice-periods.json")) as { periods: Period[] };
  plainExpect(periods.length).toBeGreaterThan(300);
  for (const entry of periods) {
    for (const form of ["note", "empty"] as const) {
      const text = written(entry, form);
      plainExpect(text, `${entry.plan_date} as of ${entry.as_of}`).not.toMatch(/[{}]/);
      // Two dates in one sentence are a period from the first to the second, which never runs backwards.
      const [from, to, ...more] = text.match(DATE) ?? [];
      if (/ to /.test(text)) {
        plainExpect([from, to, more.length], text).toEqual([expect.any(String), expect.any(String), 0]);
        plainExpect(Date.parse(from!) <= Date.parse(to!), `${entry.plan_date} as of ${entry.as_of}: ${text}`).toBe(true);
      }
    }
  }
  const p130164 = (asOf: string) => periods.find((entry) => entry.plan_date === "2018-06-20" && entry.as_of === asOf)!;
  plainExpect(written(p130164("2026-10-30"), "note")).toBe(
    "The plan is older than the awards data I hold, so I compared packages with notices from July 1, 2019 to October 30, 2026.",
  );
  plainExpect(written(p130164("2018-06-20"), "empty")).toBe(
    "The awards data I hold starts on July 1, 2019, after the as-of date of June 20, 2018, so no past package can match.",
  );
});

const REF = "IN-RRSMP-7516-CW-RFB";
const API = `/api/packages/${REF}`;

async function openIndia(page: import("@playwright/test").Page, comparables: string) {
  await page.setViewportSize({ width: 1440, height: 900 });
  await mockApi(page, {
    "/api/me": { body: await recorded("me.json") },
    "/api/freshness": { body: await recorded("freshness.json") },
    [API]: { body: await recorded("package-in-rrsmp-7516.json") },
    [`${API}/comparables`]: { body: await recorded(comparables) },
  });
  // The other zones never answer, so they stay loading and the test reads section 1 alone.
  for (const path of ["estimate", "risks", "steps", "rebidding", "criteria"]) await page.route(`**${API}/${path}**`, () => new Promise(() => {}));
  await page.goto(`/packages/${encodeURIComponent(REF)}`);
  const section = page.locator("[data-past-range]:not([data-past-range=loading])");
  await expect(section).toBeVisible();
  return section;
}

test("P130164's package of a plan older than the awards data looks from the data's start to the as-of date and says why", async ({ page }) => {
  const section = await openIndia(page, "comparables-in-rrsmp-7516.json");

  await expect(section).toContainText("No past package matched this one, so I have nothing to compare it with.");
  await expect(section).toContainText("They had to be in India.");
  await expect(section).toContainText(
    "The plan is older than the awards data I hold, so I looked for packages with notices from July 1, 2019 to October 30, 2026.",
  );
  await expect(section).not.toContainText("to June 20, 2018");
});

test("as of a date before the awards data, the section says why no package can match instead of naming a period", async ({ page }) => {
  const section = await openIndia(page, "comparables-in-rrsmp-7516-2018-12-01.json");

  await expect(section).toContainText("They had to be in India.");
  await expect(section).toContainText("The awards data I hold starts on July 1, 2019, after the as-of date of December 1, 2018, so no past package can match.");
  await expect(section).not.toContainText("notices from");
});

test("with comparables, the note says the plan is older than the awards data and gives the period it used", async ({ page }) => {
  // The demo package's 49 comparables, with the period a plan older than the awards data gives it.
  const body = JSON.parse(await recorded("comparables-ke-nwwda-541055.json"));
  body.criteria = { ...body.criteria, notice_to: "2026-10-30", period: "plan_before_data" };
  await page.setViewportSize({ width: 1440, height: 900 });
  await mockApi(page, {
    "/api/me": { body: await recorded("me.json") },
    "/api/freshness": { body: await recorded("freshness.json") },
    "/api/packages/KE-NWWDA-541055-CW-RFB": { body: await recorded("package-ke-nwwda-541055.json") },
    "/api/packages/KE-NWWDA-541055-CW-RFB/comparables": { body: JSON.stringify(body) },
  });
  await page.goto("/packages/KE-NWWDA-541055-CW-RFB");

  const note = page.locator("[data-chart-note]");
  await expect(note).toContainText("They were in Kenya.");
  await expect(note).toContainText("The plan is older than the awards data I hold, so I compared packages with notices from July 1, 2019 to October 30, 2026.");
});
