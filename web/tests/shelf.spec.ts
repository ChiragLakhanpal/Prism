// The hardest documents I read, the evidence drawer's new kinds of passage, and the removed box's
// table-summary reason (ticket 18; the 18 design brief), at seam 4 against the mocked API. Every answer
// is the server's own on the fixture, recorded in tests/fixtures/api by tests/record_api.py and
// tests/test_answer_stream.py, so each number the page shows is checked against the row the server
// returned. Fixed words come from the brief, copied here so the test checks the copy file against an
// independent source.
import AxeBuilder from "@axe-core/playwright";
import type { Page, Route } from "@playwright/test";
import { askFromTheBox, drawer, landed, open as openAnswerPage, panel } from "./answer-page";
import { expect, mockShell, recorded, test } from "./mocked";

const WCAG_22_AA = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];
async function violations(page: Page) {
  // The drawer fades in; contrast is checked once it has settled.
  await page.waitForFunction(() => document.getAnimations().every((a) => a.playState !== "running" || a.effect?.getTiming().iterations === Infinity));
  const results = await new AxeBuilder({ page }).withTags(WCAG_22_AA).analyze();
  return results.violations.map((v) => `${v.id}: ${v.nodes.map((node) => node.target.join(" ")).join(", ")}`);
}

type Answer = { file?: string; body?: string; status?: number; pending?: boolean };

async function openData(page: Page, readiness: Answer, { path = "/data", width = 1440 } = {}) {
  await mockShell(page);
  const fulfil = async (route: Route, answer: Answer) =>
    route.fulfill({ status: answer.status ?? 200, contentType: "application/json", body: answer.body ?? (await recorded(answer.file!)) });
  await page.route("**/api/data/readiness*", async (route) => (readiness.pending ? undefined : fulfil(route, readiness)));
  await page.route("**/api/data/sources", (route) => fulfil(route, { file: "data-sources.json" }));
  await page.setViewportSize({ width, height: 900 });
  await page.goto(path);
}

const json = async (name: string) => JSON.parse(await recorded(name));
const shelf = (page: Page) => page.locator("[data-readiness-table=shelf]");
const visible = (page: Page, width: number) => shelf(page).locator(`[data-table-view=${width < 768 ? "cards" : "table"}]`);
const row = (page: Page, width: number, key: string) => visible(page, width).locator(width < 768 ? `[data-card="${key}"]` : `[data-row="${key}"]`);
const TITLE = "The hardest documents I read";
const KEYS = ["p130164_pad", "longest_pad", "long_plan", "french_report", "over_parser_limit"];

for (const width of [1440, 1024, 390]) {
  test(`at ${width} px the hardest documents are five rows after Sources and before the fixes, each with its outcome and a link to its page`, async ({ page }) => {
    const answer = await json("data-readiness.json");
    await openData(page, { file: "data-readiness.json" }, { width });
    await expect(shelf(page)).toBeVisible();

    // A region named by its title, in the slice file's order, between the Sources table and the fixes.
    await expect(page.getByRole("region", { name: TITLE }).getByRole("heading", { level: 2 })).toHaveText(TITLE);
    await expect(shelf(page).locator("h2 + p")).toHaveText(
      "I use these documents as a stress test for my reading. Each row says what makes the document hard, what I recovered, and the page where you can compare the two.",
    );
    const top = async (selector: string) => (await page.locator(selector).boundingBox())!.y;
    expect(await top("[data-readiness-table=sources]")).toBeLessThan(await top("[data-readiness-table=shelf]"));
    expect(await top("[data-readiness-table=shelf]")).toBeLessThan(await top("[data-fixes]"));
    const keys = await visible(page, width).locator(width < 768 ? "[data-card]" : "[data-row]").evaluateAll((rows) =>
      rows.map((element) => element.getAttribute("data-card") ?? element.getAttribute("data-row")),
    );
    expect(keys).toEqual(KEYS);

    // Every number is the server's row, "{count} of {total}" with no percentage, or the count alone when
    // there is nothing to check it against.
    for (const entry of answer.stress_shelf.filter((found: { state: string }) => found.state === "read")) {
      const outcome = answer.rows[entry.outcome_row];
      const parser = answer.rows[entry.parser_row];
      const cells = row(page, width, entry.key);
      // The document's date is a Num too; the measures are the numbers alone.
      await expect(cells.locator("[data-num]").filter({ hasText: /^[\d,]+( of [\d,]+)?$/ })).toHaveText([
        `${parser.count} of ${parser.denominator}`,
        outcome.denominator === null
          ? outcome.count.toLocaleString("en-US")
          : `${outcome.count.toLocaleString("en-US")} of ${outcome.denominator.toLocaleString("en-US")}`,
      ]);
      // The link opens the in-app source view at the hard part's page, in the same tab (ticket 21), named
      // for its document. The source view links the World Bank's PDF at the same page.
      const link = cells.getByRole("link", { name: /^Open at page/ });
      await expect(link).toHaveAttribute("href", `/projects/${entry.document.project_id}/documents/${entry.document.document_id}?page=${entry.hard_page}`);
      await expect(link).not.toHaveAttribute("target");
      // The name starts with the words on screen (WCAG 2.2 SC 2.5.3) and names the document.
      await expect(link).toHaveAccessibleName(
        `Open at page ${entry.hard_page} of the ${entry.document.document_type} for ${entry.document.project_id}`,
      );
    }
    // The fixture's outcomes all reach the read-well threshold, so no row has a badge.
    await expect(visible(page, width).getByText(/^(Partial|Gap)$/)).toHaveCount(0);
    // No person has counted the annex's risks, so the row says what it recovered and has nothing to
    // check it against; and it says it checks the risks and ratings, not the text beside them.
    await expect(row(page, width, "p130164_pad")).toContainText(
      "A scanned document whose risk annex is set in two columns. I check its risks and ratings, not the text beside them.",
    );
    await expect(row(page, width, "p130164_pad")).toContainText("rated risks recovered");
    await expect(row(page, width, "p130164_pad")).toContainText("I have no count of the annex's risks to check this against.");
    await expect(row(page, width, "p130164_pad")).not.toContainText("counted by hand");
    await expect(row(page, width, "p130164_pad")).toContainText("where the risk annex starts");
    await expect(row(page, width, "french_report")).toContainText("passages marked as French");
    await expect(row(page, width, "over_parser_limit")).toContainText(
      "No document I read has more than 500 pages, so none needed dividing. The longest has 103 pages.",
    );
    await expect(row(page, width, "over_parser_limit").getByRole("link")).toHaveCount(0);
    // DESIGN.md section 7: the screen never says "stress shelf", and spells the PAD out.
    await expect(shelf(page)).not.toContainText(/stress shelf|\bPAD\b/i);
    await expect(shelf(page)).toContainText(
      "Strata's reading records, taken Oct 23, 2026. Documents from the World Bank's Documents and Reports.",
    );
    // Nothing scrolls sideways.
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    expect(await violations(page)).toEqual([]);
  });
}

test("a Gap is the one row that stands out, and What holds it back links down to it", async ({ page }) => {
  await openData(page, { file: "data-readiness-shelf-gap.json" });
  await expect(shelf(page)).toBeVisible();

  await expect(row(page, 1440, "p130164_pad").locator("[data-cell='p130164_pad:outcome']")).toContainText("0 of 8rated risks recoveredGap");
  await expect(row(page, 1440, "longest_pad").locator("[data-cell='longest_pad:outcome']")).toContainText("Partial");
  await expect(visible(page, 1440).getByText(/^(Partial|Gap)$/)).toHaveCount(2);

  // The document search reads the PAD's source, so its cell gains one sentence after its top gap.
  const holds = page.locator("[data-readiness-table=kinds] [data-table-view=table] [data-cell='document_search:holds'] p");
  await expect(holds.last()).toHaveText(
    "I couldn't read the risk annex in the Project Appraisal Document for P130164, one of the hardest documents I read.",
  );
  await expect(holds.last().locator(".font-mono")).toHaveText("P130164");
  await expect(page.locator("[data-cell='plan_check:holds']").first()).not.toContainText("hardest documents");
  await expect(page.locator("[data-headline]")).not.toContainText("hardest documents");

  await holds.last().getByRole("link", { name: "the hardest documents I read" }).click();
  await expect(page.getByRole("heading", { level: 2, name: TITLE })).toBeFocused();
  await expect(page).toHaveURL(/\/data#hardest-documents$/);
  expect(await violations(page)).toEqual([]);
});

test("with two hard documents unread, the sentence counts them and names one", async ({ page }) => {
  await openData(page, { file: "data-readiness-shelf-two-gaps.json" });

  await expect(page.locator("[data-readiness-table=kinds] [data-table-view=table] [data-cell='document_search:holds'] p").last()).toHaveText(
    "I couldn't read parts of two of the hardest documents I read, such as the risk annex in the Project Appraisal Document for P130164.",
  );
});

test("a row with nothing to show spans one note across its last three cells, with no badge and no link", async ({ page }) => {
  await openData(page, { file: "data-readiness-shelf-abstentions.json" });
  await expect(shelf(page)).toBeVisible();
  const span = (key: string) => visible(page, 1440).locator(`[data-cell='${key}:span']`);

  // No hand count: the number alone, and what it lacks.
  await expect(row(page, 1440, "p130164_pad").locator("[data-cell='p130164_pad:outcome']")).toContainText(
    "8rated risks recoveredI have no count of the annex's risks to check this against.",
  );
  // A rule that found no document says what I looked for, and nothing that contradicts it (critique r2).
  await expect(span("longest_pad")).toHaveText("I found no Project Appraisal Document of the pilot projects among the documents I read.");
  await expect(row(page, 1440, "longest_pad").locator("th")).toHaveText("The longest Project Appraisal Document");
  await expect(row(page, 1440, "longest_pad").locator("[data-cell='longest_pad:hard']")).toHaveText(
    "I looked for the longest Project Appraisal Document of the pilot projects.",
  );
  // The read pages and the page count are one number, and the cap says it covers the whole run.
  await expect(span("long_plan")).toHaveText(
    "6 of 14 pages read so farI stopped at today's limit of 30 pages, which covers every document in the run. The next run reads the rest.",
  );
  await expect(span("long_plan").locator("[data-num]")).toHaveText(["6 of 14", "30"]);
  await span("long_plan").locator("[data-num]").nth(1).focus();
  await expect(page.getByRole("tooltip").filter({ hasText: "The most pages I send the layout parser in one day. It is my own setting, not a measure." })).toBeVisible();
  await expect(span("french_report")).toHaveText("Not read yet. The next document run reads it.");
  for (const key of ["longest_pad", "long_plan", "french_report"]) {
    await expect(span(key)).toHaveAttribute("colspan", "3");
    await expect(row(page, 1440, key).getByRole("link", { name: /^Open at page/ })).toHaveCount(0);
  }
  await expect(visible(page, 1440).getByText(/^(Partial|Gap)$/)).toHaveCount(0);
  expect(await violations(page)).toEqual([]);
});

test("before the first document run every row says it is not read yet, and the section keeps its shape", async ({ page }) => {
  await openData(page, { file: "data-readiness-shelf-empty.json" });

  await expect(visible(page, 1440).locator("[data-row]")).toHaveCount(5);
  await expect(visible(page, 1440).locator("td[colspan='3']")).toHaveText(Array(5).fill("Not read yet. The next document run reads it."));
  // Before any reading, a rule's row never says I read the document (critique r2).
  await expect(row(page, 1440, "longest_pad").locator("th")).toHaveText("The longest Project Appraisal DocumentI choose it when I read the documents.");
  await expect(row(page, 1440, "longest_pad").locator("[data-cell='longest_pad:hard']")).toHaveText(
    "The longest Project Appraisal Document of the pilot projects.",
  );
});

test("a filtered view shows only the rows on its sources, and leaves the section out when none are", async ({ page }) => {
  await openData(page, { file: "data-readiness-filtered.json" }, { path: "/data?sources=awards,notices&from=find_comparables" });
  await expect(page.locator("[data-readiness=filtered]")).toBeVisible();
  await expect(page.getByRole("heading", { name: TITLE })).toHaveCount(0);

  await page.unrouteAll({ behavior: "ignoreErrors" });
  await openData(page, { file: "data-readiness-plan-check.json" }, { path: "/data?sources=documents,projects&from=check_plan" });
  await expect(visible(page, 1440).locator("[data-row]")).toHaveCount(1);
  await expect(row(page, 1440, "long_plan").locator("th")).toContainText("Procurement Plan");
});

test("while the measures load, the section shows its title and one skeleton row for each document the slice file names", async ({ page }) => {
  await openData(page, { pending: true });

  await expect(page.getByRole("heading", { level: 2, name: TITLE })).toBeVisible();
  await expect(shelf(page).locator("[data-table-view=table] tbody tr[aria-hidden=true]")).toHaveCount(5);
  await expect(page.locator("[data-readiness=loading]")).toHaveAttribute("aria-busy", "true");
});

test("an outcome's number says what it counts and opens a window with what it checks, the parser and the table", async ({ page }) => {
  await openData(page, { file: "data-readiness.json" });
  const number = row(page, 1440, "p130164_pad").locator("[data-cell='p130164_pad:outcome'] [data-num]");

  await number.focus();
  await expect(page.getByRole("tooltip").filter({ hasText: "8 rated risks. Measured Oct 23, 2026." })).toBeVisible();
  await number.click();
  const window = page.getByRole("dialog", { name: "Outcome" });
  // The annex's outcome says it checks names and ratings, not the text the scan runs together (design r2 B2).
  await expect(window).toContainText(
    "A risk counts when I read its name and its rating from the risk table. I don't check the description and mitigation text beside them, which the scan sets in two columns. Open the page to compare.",
  );
  await expect(window).not.toContainText("Counted against");
  await expect(window.locator(".font-mono")).toHaveText(["recorded words (pdftotext -bbox)", "strata.ops.stress_shelf"]);
  await page.keyboard.press("Escape");
  await expect(number).toBeFocused();

  // The headers' full definitions open from their labels.
  await shelf(page).locator("[data-table-view=table] thead").getByRole("button", { name: "Layout parser" }).click();
  await expect(page.getByRole("dialog", { name: "Layout parser" })).toContainText(
    "I send scanned pages, tables and figures to a layout parser instead, because the published text loses their rows and columns.",
  );
});

test("with a hand count, the outcome's window says what it was counted against", async ({ page }) => {
  await openData(page, { file: "data-readiness-shelf-gap.json" });
  await row(page, 1440, "p130164_pad").locator("[data-cell='p130164_pad:outcome'] [data-num]").click();

  await expect(page.getByRole("dialog", { name: "Outcome" })).toContainText(
    "Counted against8 rated risks in the annex, counted by hand from the PDF on Oct 20, 2026",
  );
});

test("the project reports' row counts the projects its documents belong to, then the pilot projects read, and its Read well window splits the share by route", async ({ page }) => {
  const answer = await json("data-readiness.json");
  const reports = answer.sources.find((found: { id: string }) => found.id === "reports");
  const cell = (column: string) => page.locator(`[data-readiness-table=sources] [data-table-view=table] [data-cell='reports:${column}']`);
  await openData(page, { file: "data-readiness.json" });

  // Both numbers on the line count the same documents (design review r2 B1): the projects are the
  // documents' own, and the pilot projects read are a line of their own.
  const documents = answer.rows[reports.cells.coverage.row];
  const projects = answer.rows[reports.cells.coverage.projects_row];
  const pilot = answer.rows[reports.cells.coverage.slice_row];
  expect(projects.count).toBe(documents.subjects.length);
  expect([pilot.count, pilot.denominator]).toEqual([1, 17]);
  expect(projects.count).toBe(3);
  await expect(cell("coverage")).toContainText("documents for three projects");
  await expect(cell("coverage")).toContainText("1 of 17 pilot projects");
  await cell("coverage").locator("[data-num]").nth(1).click();
  await expect(page.getByRole("dialog", { name: "Projects with documents read" })).toContainText("strata.silver.documents");
  await page.keyboard.press("Escape");
  await cell("coverage").locator("[data-num]").nth(2).click();
  await expect(page.getByRole("dialog", { name: "Pilot projects read" })).toContainText("strata.silver.documents");
  await page.keyboard.press("Escape");
  await expect(page.locator("[data-readiness-table=sources] [data-row=reports] th")).toContainText(
    "Water and transport projects in Kenya, Bangladesh, Vietnam and Pakistan, fiscal 2012 to 2025, and the projects of the hardest documents below",
  );
  const [text, parser] = reports.cells.read_well.routes.map((route: { row: number }) => answer.rows[route.row]);
  await cell("read_well").locator("[data-num]").click();
  const window = page.getByRole("dialog", { name: "Read well" });
  await expect(window).toContainText(`Published text${text.count} of ${text.denominator} pages read well`);
  await expect(window).toContainText(`Layout parser${parser.count} of ${parser.denominator} pages read well`);
  await page.keyboard.press("Escape");
  await expect(page.locator("[data-readiness-table=sources] [data-table-view=table] [data-cell='notice_text:read_well']")).toHaveText("Published as text");
});

// Critique r2: from 768 to about 1100 px a wrapped head label sat on the left over right-aligned numbers,
// and "100 of 100" broke after "of". Each number column's head and numbers keep to its right edge, and a
// "{n} of {d}" pair stays on one line.
for (const width of [768, 1024]) {
  test(`at ${width} px the number columns' heads and numbers line up on the right, and no pair breaks`, async ({ page }) => {
    await openData(page, { file: "data-readiness-shelf-gap.json" }, { width });
    const table = visible(page, width);
    await expect(table).toBeVisible();
    const columns = ["parser", "outcome"];
    const heads = table.locator("thead th");
    for (const [index, column] of columns.entries()) {
      const head = heads.nth(index + 2);
      const label = head.locator("[data-term]");
      const [h, l] = [(await head.boundingBox())!, (await label.boundingBox())!];
      expect(Math.abs(h.x + h.width - 16 - (l.x + l.width)), `the ${column} head's label`).toBeLessThanOrEqual(1.5);
      const cells = table.locator(`td[data-cell$=':${column}']`);
      for (let i = 0; i < (await cells.count()); i += 1) {
        const number = cells.nth(i).locator("[data-num]");
        if ((await number.count()) === 0) continue;
        const [c, n] = [(await cells.nth(i).boundingBox())!, (await number.first().boundingBox())!];
        expect(n.x + n.width, `${column} row ${i} keeps to the right`).toBeGreaterThanOrEqual(c.x + c.width - 16 - 1.5);
        expect(n.x + n.width, `${column} row ${i} stays in its cell`).toBeLessThanOrEqual(c.x + c.width);
        expect(n.height, `${column} row ${i} is one line`).toBeLessThan(32);
      }
    }
  });
}

// Review r2 P12: every number on the shelf opens a window with its own title, counted in the shelf's table.
test("every number on the shelf opens its own window, counted in the shelf's table", async ({ page }) => {
  const { copy } = await import("../src/copy.ts");
  const windows = copy.dataReadiness.shelf.windows;
  const titles: Record<string, string> = {
    parser_row: windows.parser.title,
    outcome_row: windows.outcome.title,
    read_pages_row: windows.read.title,
    longest_row: windows.longest.title,
  };
  for (const file of ["data-readiness.json", "data-readiness-shelf-abstentions.json"]) {
    const answer = await json(file);
    await page.unrouteAll({ behavior: "ignoreErrors" });
    await openData(page, { file });
    await expect(shelf(page)).toBeVisible();
    for (const entry of answer.stress_shelf) {
      for (const [field, title] of Object.entries(titles)) {
        const index = entry[field];
        if (index === null) continue;
        const measure = answer.rows[index].measure;
        const number = row(page, 1440, entry.key).locator(`[data-num][data-measure='${measure}']`);
        await number.click();
        const window = page.getByRole("dialog", { name: title });
        await expect(window, `${file} ${entry.key} ${field}`).toBeVisible();
        await expect(window.locator(".font-mono").last()).toHaveText("strata.ops.stress_shelf");
        await page.keyboard.press("Escape");
        await expect(window).toBeHidden();
      }
    }
  }
});

test("in a card, the Page field's label is for screen readers, so the link stands on its own line", async ({ page }) => {
  await openData(page, { file: "data-readiness.json" }, { width: 390 });
  const card = row(page, 390, "p130164_pad");

  await expect(card.locator("dt.clip-visually")).toHaveText("Page where the hard part starts");
  await expect(card.locator("dt:not(.clip-visually)", { hasText: /^Page/ })).toHaveCount(0);
});

test("at 320 px the hardest documents reflow as cards with no sideways scroll", async ({ page }) => {
  await openData(page, { file: "data-readiness-shelf-gap.json" }, { width: 320 });
  await expect(shelf(page).locator("[data-table-view=cards] [data-card]")).toHaveCount(5);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await expect(row(page, 320, "p130164_pad").getByRole("heading", { level: 3 })).toHaveText("Project Appraisal Document");
  expect(await violations(page)).toEqual([]);
});

// ── The evidence drawer's new kinds of passage (the 18 brief, section 7) ──

const KINDS = [
  {
    name: "a paragraph the layout parser read from a scanned page",
    id: "strata.gold.passage:18381488/v1/23",
    file: "evidence-pad-p130164-scanned.json",
    heading: "Rajasthan Road Sector Modernization, paragraph 23",
    note: "The whole paragraph, as the layout parser read it from a scanned page. The PDF page has the exact words.",
    link: /^Open at page 20$/,
  },
  {
    name: "a row of a table",
    id: "strata.gold.passage:18381488/v1/table65.2",
    file: "evidence-pad-p130164-risk-row.json",
    heading: "Rajasthan Road Sector Modernization, Annex 4 - Operational Risk Assessment Framework (ORAF)",
    note: "This row as the layout parser read it from the table. The PDF page has the original.",
    link: /^Open at page 65$/,
  },
  {
    name: "a table's summary",
    id: "strata.gold.passage:18381488/v1/table65",
    file: "evidence-pad-p130164-risk-summary.json",
    heading: "Rajasthan Road Sector Modernization, summary of Annex 4 - Operational Risk Assessment Framework (ORAF)",
    note: "I wrote this summary of the table on PDF pages 65 to 70. It is not the document's own words, and I never use it to back a number.",
    link: /^Open at page 65$/,
  },
  {
    name: "a section of a notice's text",
    id: "strata.gold.passage:OP00118817/v1/s5",
    file: "evidence-notice-op00118817-qualifications.json",
    heading: "Notice OP00118817",
    note: "The whole section, word for word, without contact details.",
    link: /^Open this notice on the World Bank's site/,
  },
];

for (const kind of KINDS) {
  for (const width of [1440, 390]) {
    test(`the drawer at ${width} px opens ${kind.name} from a link and says what the text is`, async ({ page }) => {
      await openAnswerPage(page, { path: `/projects/P130164?evidence=${encodeURIComponent(kind.id)}`, evidence: kind.file, width });

      await expect(drawer(page).getByRole("heading", { level: 2 })).toHaveText(kind.heading);
      await expect(drawer(page)).toContainText(kind.note);
      await expect(drawer(page).getByRole("link", { name: kind.link })).toHaveCount(1);
      expect(await violations(page)).toEqual([]);
    });
  }
}

test("a table row shows its cells as column heads and values, and its meta line names its table and row", async ({ page }) => {
  await openAnswerPage(page, { path: `/projects/P130164?evidence=${encodeURIComponent(KINDS[1].id)}`, evidence: KINDS[1].file });

  const cells = drawer(page).locator("[data-row-cells] tbody tr");
  await expect(cells.first().locator("th")).toHaveText("Risk");
  await expect(cells.first().locator("td")).toHaveText("Capacity");
  await expect(cells.nth(1)).toHaveText("RatingLow");
  await expect(drawer(page).locator("[data-meta-line]")).toContainText("Row 2");
  await expect(drawer(page).locator("[data-meta-line]")).toContainText("PDF page 65 of 100");
});

test("a table row quoted by a sentence highlights the cell it matched", async ({ page }) => {
  await openAnswerPage(page, { stream: "ask-p130164-table-row.sse" });
  await askFromTheBox(page);
  await landed(page);
  await panel(page).locator("[data-sentence-text='3'] [data-citation]").click();

  const rating = drawer(page).locator("[data-row-cells] tbody tr").nth(1);
  await expect(rating.locator("th")).toHaveText("Rating");
  await expect(rating.locator("td mark")).toHaveText("Highlight starts. Low Highlight ends.");
  await expect(drawer(page).locator("[data-row-cells] mark")).toHaveCount(1);
  await expect(drawer(page)).not.toContainText("so no words are highlighted");
  expect(await violations(page)).toEqual([]);
});

test("a table's summary names every page of its table in its meta line", async ({ page }) => {
  await openAnswerPage(page, { path: `/projects/P130164?evidence=${encodeURIComponent(KINDS[2].id)}`, evidence: KINDS[2].file });

  await expect(drawer(page).locator("[data-meta-line]")).toContainText("PDF pages 65 to 70 of 100");
  await expect(drawer(page).locator("[data-passage]")).toContainText(
    "The table on PDF pages 65 to 70 of the Project Appraisal Document is titled Annex 4 - Operational Risk Assessment Framework (ORAF).",
  );
});

test("a notice's text shows where contact details were removed and never the raw marker", async ({ page }) => {
  const id = "strata.gold.passage:OP00118817/v1/s8";
  await openAnswerPage(page, { path: `/projects/P130164?evidence=${encodeURIComponent(id)}`, evidence: "evidence-notice-op00118817.json" });

  await expect(drawer(page).locator("[data-passage]")).toContainText("Telephone: (contact details removed), Email address: (contact details removed)");
  await expect(drawer(page)).not.toContainText("[contact removed]");
  await expect(drawer(page).locator("p.text-label")).toHaveText("What · notice");
  await expect(drawer(page).locator("[data-meta-line]")).toHaveText(
    /^Request for Expression of Interest\s·\sWater and Sanitation Development\s\(P156634\)\s·\sFebruary 26, 2021\s·\sAddress referred above$/,
  );
  await expect(drawer(page).getByRole("link", { name: /^Open this notice/ })).toHaveAttribute("href", "https://projects.worldbank.org/en/projects-operations/procurement-detail/OP00118817");
});

test("a passage in French carries its language, and its meta line says so", async ({ page }) => {
  await openAnswerPage(page, { path: `/projects/P130164?evidence=${encodeURIComponent("strata.gold.passage:33407968/v1/1")}`, evidence: "evidence-icr-p127203-fr.json" });

  await expect(drawer(page).locator("[data-passage]")).toHaveAttribute("lang", "fr");
  await expect(drawer(page).locator("[data-passage]")).toContainText("Au lendemain du tremblement de terre de janvier 2010");
  await expect(drawer(page).locator("[data-meta-line]")).toContainText("In French");
  expect(await violations(page)).toEqual([]);
});

test("a number that only a table's summary backs is removed, and the removed box says why", async ({ page }) => {
  await openAnswerPage(page, { stream: "ask-p130164-table-summary.sse" });
  await askFromTheBox(page);
  await landed(page);

  await expect(panel(page).locator("[data-removed-box]")).toHaveText(
    "I removed one sentence. It said the appraisal document's risk annex rated 8 risks, and that number came only from my summary of a table, not from the table's rows.",
  );
});
