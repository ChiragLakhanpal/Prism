// The gallery's components behave as DESIGN.md section 5 says (criteria 5, 6 and 7 of ticket
// 02): badges carry their state in an icon shape and a word, the citation marker names its
// source, the check line is neutral, Num never turns a small count into a percentage, and the
// open states (Menu, view popover, tooltip, DefinitionWindow) pass axe and close on Escape.
import { readFile } from "node:fs/promises";
import { scan } from "./axe";
import type { Locator, Page } from "@playwright/test";
import { expect, test } from "./mocked";


async function axe(page: Page) {
  await page.waitForFunction(() =>
    document.getAnimations().every((a) => a.playState !== "running" || a.effect?.getTiming().iterations === Infinity),
  );
  const results = await scan(page);
  return results.violations.map((v) => `${v.id}: ${v.nodes.map((node) => node.target.join(" ")).join(", ")}`);
}

// Moved from web/tests/routes.spec.ts when the package workspace replaced the last placeholder page
// whose empty state named a STEP reference; the gallery's page header sample keeps that empty state.
test("an empty state's title keeps a STEP reference on one line whenever it fits", async ({ page }) => {
  await page.goto("/gallery/pages");
  for (const width of [390, 768, 1024, 1279]) {
    await page.setViewportSize({ width, height: 900 });
    const id = page.locator("[data-state-section=header] [data-empty-state] h3").getByText("KE-SAMPLE-000001-CW-RFB");
    expect(await id.evaluate((el) => el.getClientRects().length), `${width} px`).toBe(1);
  }
});

const badge = (page: Page, text: string) => page.locator("[data-badge]", { hasText: new RegExp(`^${text}$`) });

test("the status badge shows Needs a look, Watch and No signals, each with its own icon shape and its word", async ({ page }) => {
  await page.goto("/gallery/badges");
  const shapes: Record<string, string> = { "Needs a look": "triangle-alert", Watch: "info", "No signals": "circle" };
  for (const [text, icon] of Object.entries(shapes)) {
    const found = badge(page, text);
    await expect(found).toHaveText(text);
    await expect(found.locator(`svg.lucide-${icon}`)).toHaveCount(1);
    await expect(found.locator("svg")).toHaveAttribute("aria-hidden", "true");
  }
  expect(new Set(Object.values(shapes)).size).toBe(3);
});

test("Partial uses the warning state with triangle-alert, and Gap the neutral state with circle-dashed and a dashed border", async ({
  page,
}) => {
  await page.goto("/gallery/badges");
  const look = (text: string) =>
    badge(page, text).evaluate((el) => {
      const style = getComputedStyle(el);
      return { background: style.backgroundColor, border: style.borderTopStyle, icon: el.querySelector("svg")!.classList.contains("lucide-triangle-alert") ? "triangle-alert" : el.querySelector("svg")!.getAttribute("class") };
    });
  expect(await look("Partial")).toEqual({ background: "rgb(254, 243, 215)", border: "solid", icon: "triangle-alert" });
  const gap = await look("Gap");
  expect(gap.background).toBe("rgb(231, 237, 243)");
  expect(gap.border).toBe("dashed");
  expect(gap.icon).toContain("lucide-circle-dashed");
});

// Ticket 46 (the 46 brief, section 12.2): a part that is designed but not built carries a neutral badge with its own
// icon, drafting-compass, and no visible border, followed at once by one sentence saying what Strata does instead.
test("Designed, not built is a quiet neutral badge with drafting-compass, followed at once by what Strata does instead", async ({
  page,
}) => {
  await page.goto("/gallery/badges");
  const found = badge(page, "Designed, not built").first();
  await expect(found.locator("svg.lucide-drafting-compass")).toHaveCount(1);
  await expect(found.locator("svg")).toHaveAttribute("aria-hidden", "true");
  const look = await found.evaluate((el) => {
    const style = getComputedStyle(el);
    return { background: style.backgroundColor, border: style.borderTopColor };
  });
  expect(look).toEqual({ background: "rgb(231, 237, 243)", border: "rgba(0, 0, 0, 0)" });
  const label = page.locator("[data-dnb=sample]");
  await expect(label.locator("[data-badge=designed-not-built]")).toHaveText("Designed, not built");
  await expect(label.locator("[data-dnb-instead]")).toHaveText("I don't run this model yet, so these signals come from fixed checks.");
  const instead = await label.locator("[data-dnb-instead]").getAttribute("id");
  expect(instead).toBeTruthy();
  await expect(label.locator("[data-badge=designed-not-built]")).toHaveAttribute("aria-describedby", instead!);
});

test("the citation marker's accessible name names the source, and a copy of it reads [1]", async ({ page }) => {
  await page.goto("/gallery/citations");
  const marker = page.getByRole("link", { name: "Source 1: Implementation Completion and Results Report, June 30, 2021, paragraph 54" }).first();
  await expect(marker).toBeVisible();
  expect(await marker.textContent()).toBe("[1]");
  await expect(
    page.getByRole("link", { name: "Source 2: Implementation Status and Results Report, March 4, 2020, paragraph 12, opened" }).first(),
  ).toBeVisible();
});

// CLAUDE.md rule 2: the marker shows which claim a source backs. A marker that wraps to the
// next line sits at the head of the next sentence and points at the wrong claim. Answers come
// from a model, so their line ends move; the marker must hold to its sentence at any width.
//
// For each marker that follows a sentence, this lists the markers that sit on a different
// line from the last character of that sentence.
function markersApart(page: Page) {
  return page.locator("[data-citation]").evaluateAll((markers) =>
    markers.flatMap((marker) => {
      // The word joiner sits in the marker's no-wrap span, so it always shares the marker's
      // line. Measure the last character a reader sees instead.
      const visible = (text: string) => text.replace(/[\s\u2060]+$/u, "");
      // Only markers that follow a sentence: in a paragraph, or in an answer's "In short".
      const block = marker.closest("p, [data-answer] > div");
      if (!block) return [];
      let last: Text | null = null;
      const walker = document.createTreeWalker(block, NodeFilter.SHOW_TEXT);
      while (walker.nextNode()) {
        const node = walker.currentNode as Text;
        if (marker.contains(node) || marker.compareDocumentPosition(node) & Node.DOCUMENT_POSITION_FOLLOWING) break;
        if (visible(node.data)) last = node;
      }
      if (!last) return [];
      // The last character of that text, and the line it sits on.
      const end = visible(last.data).length;
      const range = document.createRange();
      range.setStart(last, end - 1);
      range.setEnd(last, end);
      const char = range.getBoundingClientRect();
      const box = marker.getBoundingClientRect();
      const middle = box.top + box.height / 2;
      return middle > char.top && middle < char.bottom ? [] : [`marker ${marker.textContent} after "${visible(last.data).slice(-20)}"`];
    }),
  );
}

test("a citation marker stays on the line of the sentence it cites, at every width", async ({ page }) => {
  for (const path of ["/gallery/citations", "/gallery/answer"]) {
    for (const width of [1440, 1280, 1024, 768, 390, 360, 320]) {
      await page.setViewportSize({ width, height: 900 });
      await page.goto(path);
      await expect(page.locator("[data-citation]").first()).toBeVisible();
      expect(await markersApart(page), `${path} at ${width} px`).toEqual([]);
    }
  }
});

// The guard above must be able to fail. A line break forced in front of marker 1 moves the
// marker, with its no-wrap span, to the head of the next line, and the measure must see it.
test("the marker measure catches a marker pushed to the start of the next line", async ({ page }) => {
  for (const path of ["/gallery/citations", "/gallery/answer"]) {
    await page.setViewportSize({ width: 1024, height: 900 });
    await page.goto(path);
    const first = page.locator("p [data-citation], [data-answer] > div [data-citation]").first();
    await expect(first).toBeVisible();
    await first.evaluate((marker) => marker.parentElement!.before(document.createElement("br")));
    expect(await markersApart(page), path).toEqual([expect.stringMatching(/^marker \[1\] after /)]);
  }
});

test("hovering or focusing a marker shows its evidence card, and Escape closes it", async ({ page }) => {
  await page.goto("/gallery/citations");
  const marker = page.locator("p").getByRole("link", { name: /^Source 1:/ });
  await marker.focus();
  const card = page.getByRole("tooltip");
  await expect(card).toContainText("The works contracts were advertised again in 2017");
  expect(await axe(page)).toEqual([]);
  await page.keyboard.press("Escape");
  await expect(card).toBeHidden();
  await expect(marker).toBeFocused();
});

test("hovering a marker opens its card after a short delay, and the pointer can move onto the card", async ({ page }) => {
  await page.goto("/gallery/citations");
  const marker = page.locator("p").getByRole("link", { name: /^Source 1:/ });
  await marker.hover();
  const card = page.getByRole("tooltip");
  await expect(card).toBeVisible();
  await expect(marker).toHaveAttribute("aria-describedby", (await card.getAttribute("id"))!);
  await card.hover();
  await page.waitForTimeout(400);
  await expect(card).toBeVisible();
  await page.mouse.move(5, 600);
  await expect(card).toBeHidden();
});

test("the check line uses the neutral state, never success green", async ({ page }) => {
  await page.goto("/gallery/citations");
  const lines = page.locator("[data-check-line]");
  await expect(lines.first()).toHaveText(
    "Checked: 23 of 23 numbers match records; 14 of 14 quotes are on their pages. Not checked: whether these are the right comparables.",
  );
  for (const line of await lines.all()) {
    const style = await line.evaluate((el) => ({ background: getComputedStyle(el).backgroundColor, color: getComputedStyle(el).color }));
    expect(style).toEqual({ background: "rgb(231, 237, 243)", color: "rgb(61, 76, 92)" });
  }
  expect(await page.locator("[data-check-line] svg").count()).toBe(0);
});

test("Num shows 6 of 12 as a count and 31 of 37 beside about 8 in 10, on screen", async ({ page }) => {
  await page.goto("/gallery/numbers");
  const nums = page.locator("[data-state-section=ratios] table [data-num]");
  await expect(nums).toHaveText([
    "6 of 12",
    "31 of 37, about 8 in 10",
    "42 of 50, 84 percent",
    "93 of 118, 79%",
    "1 of 300, less than 1 percent",
  ]);
  await expect(page.locator("[data-state-section=formats] table [data-num]")).toHaveText([
    "1,234", "12.5K", "296K", "1.3M", "2.5B", "0.46", "45.7", "457", "2,450,000.00",
  ]);
  await expect(page.locator("[data-state-section=counts] table [data-num]")).toHaveText([
    "seven", "14", "2024", "March 4, 2024", "Mar 4, 2024",
  ]);
  expect(await nums.first().evaluate((el) => getComputedStyle(el).fontVariantNumeric)).toBe("tabular-nums");
});

test("each Num reference row shows the value the tool sent beside what Num shows", async ({ page }) => {
  await page.goto("/gallery/numbers");
  const first = page.locator("[data-state-section=formats] table tbody tr").first();
  await expect(first.locator("th, td")).toHaveText(["1234", "Below 10,000, Num writes comma thousands.", "1,234"]);
  await expect(page.locator("[data-state-section=formats] table thead th")).toHaveText(["Value the tool sent", "Rule", "Num shows"]);
});

test("the coverage line ends its first sentence with the gap, or with a period when nothing was missing", async ({ page }) => {
  await page.goto("/gallery/citations");
  await expect(page.locator("[data-coverage-line]")).toHaveText([
    "Based on 37 of 52 matching packages; 15 lacked the STEP reference that links notice to contract. See data readiness for these sources",
    "Based on 52 of 52 matching packages. See data readiness for these sources",
  ]);
});

test("a table shows its title, count and source lines only with its rows", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/gallery/table");
  const ready = page.locator("[data-state-section=ready] [data-table]");
  await expect(ready.getByRole("heading")).toHaveText("Three of the four sample activities were signed after their planned date.");
  await expect(ready).toContainText("Showing all 4 activities");
  await expect(ready).toContainText("Source: Sample rows made for the gallery, in STEP's columns.");

  for (const state of ["loading", "empty", "error"]) {
    const section = page.locator(`[data-state-section=${state}]`);
    await expect(section, state).not.toContainText("Three of the four");
    await expect(section, state).not.toContainText("Showing");
    await expect(section, state).not.toContainText("Source:");
  }
  await expect(page.locator("[data-state-section=empty] h3")).toHaveText("I have no activities for this plan yet.");
  await expect(page.locator("[data-state-section=error]").getByRole("alert")).toContainText("I couldn't load the activities in this plan.");
});

test("nothing in a table moves when its rows arrive: columns, rows and cards keep their places", async ({ page }) => {
  const edges = (state: string) =>
    page.locator(`[data-state-section=${state}] table thead th`).evaluateAll((cells) => cells.map((cell) => Math.round(cell.getBoundingClientRect().x)));
  const box = async (state: string, selector: string) => {
    const found = (await page.locator(`[data-state-section=${state}] ${selector}`).first().boundingBox())!;
    return { width: Math.round(found.width), height: Math.round(found.height) };
  };

  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/gallery/table");
  // The gallery loads through a dynamic import and evaluateAll does not wait, so wait for both
  // tables before measuring them.
  await expect(page.locator("[data-state-section=ready] table thead th")).toHaveCount(4);
  await expect(page.locator("[data-state-section=loading] table thead th")).toHaveCount(4);
  expect(await edges("loading")).toEqual(await edges("ready"));
  expect(await box("loading", "table tbody tr")).toEqual(await box("ready", "table tbody tr"));
  expect(await box("loading", "[data-table]")).toEqual(await box("ready", "[data-table]"));

  await page.setViewportSize({ width: 390, height: 900 });
  expect(await box("loading", "ul > li")).toEqual(await box("ready", "ul > li"));
});

test("below 768 px every value in a table's cards starts at one left edge, with each head above its value", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 900 });
  await page.goto("/gallery/numbers");
  const cards = page.locator("[data-table=ready] ul > li");
  await expect(cards).toHaveCount(5 + 9 + 5);
  const measured = await cards.evaluateAll((items) =>
    items.map((item) => {
      const left = (el: Element) => Math.round(el.getBoundingClientRect().x);
      const field = (kind: string) =>
        [...item.querySelectorAll(`[data-card-field=${kind}]`)].map((el) => ({
          head: el.querySelector("dt")!.getBoundingClientRect(),
          value: el.querySelector("dd")!.getBoundingClientRect(),
        }));
      return {
        heading: left(item.querySelector("h4, h5")!),
        text: field("text").map(({ value }) => Math.round(value.x)),
        numbers: field("number").map(({ value }) => Math.round(value.x)),
        // Each head sits above its value, so a value never starts beside its head.
        stacked: [...field("text"), ...field("number")].every(({ head, value }) => value.top >= head.bottom - 1),
      };
    }),
  );
  const heading = measured[0].heading;
  for (const card of measured) {
    expect(card.heading).toBe(heading);
    expect(new Set(card.text)).toEqual(new Set([heading]));
    expect(card.stacked).toBe(true);
  }
  // Numbers share the grid's columns, so across all 18 cards they start at two edges at most,
  // and the first is the text's.
  const numberEdges = new Set(measured.flatMap((card) => card.numbers));
  expect(numberEdges.size).toBeLessThanOrEqual(2);
  expect(Math.min(...numberEdges)).toBe(heading);

  // "Estimated Amount (US$)" wraps to two lines beside "Days late", and both values still
  // share one line.
  await page.goto("/gallery/table");
  const tableCards = page.locator("[data-state-section=ready] [data-table=ready] ul > li");
  await expect(tableCards).toHaveCount(4);
  const tops = await tableCards.evaluateAll((items) =>
    items.map((item) => [...item.querySelectorAll("[data-card-field=number] dd")].map((dd) => Math.round(dd.getBoundingClientRect().top))),
  );
  for (const card of tops) {
    expect(card).toHaveLength(2);
    expect(new Set(card).size).toBe(1);
  }
});

// Ticket 10's plan check needs 880 px for its columns, so it turns into cards below 1024 px,
// while every other table keeps DESIGN.md's 768 px. Exactly one view shows at each width.
test("a table turns into cards below 768 px, or below 1024 px with cardsBelow lg", async ({ page }) => {
  await page.goto("/gallery/table");
  const shown = (section: string) =>
    page.locator(`[data-state-section=${section}] [data-table-view]`).evaluateAll((views) =>
      views.filter((view) => getComputedStyle(view).display !== "none").map((view) => (view as HTMLElement).dataset.tableView),
    );
  const expected: [number, string, string][] = [
    [390, "cards", "cards"],
    [767, "cards", "cards"],
    [768, "table", "cards"],
    [900, "table", "cards"],
    [1023, "table", "cards"],
    [1024, "table", "table"],
    [1440, "table", "table"],
  ];
  await expect(page.locator("[data-state-section=cards-below-lg] [data-table=ready]")).toBeVisible();
  for (const [width, md, lg] of expected) {
    await page.setViewportSize({ width, height: 900 });
    expect(await shown("ready"), `default at ${width} px`).toEqual([md]);
    expect(await shown("cards-below-lg"), `lg at ${width} px`).toEqual([lg]);
  }
});

// The past range's table keeps to columns 1 to 8 from 1200 px, where its frame is narrower than at
// 1024 px, so it reads its own width: cards while its frame is under 49rem (784 px), whatever the page area.
test("with cardsBelow fit a table turns into cards while its own frame is under 49rem", async ({ page }) => {
  await page.goto("/gallery/table");
  const section = page.locator("[data-state-section=cards-below-fit]");
  await expect(section.locator("[data-table=ready]")).toBeVisible();
  const seen = new Set<string>();
  for (const width of [390, 1024, 1180, 1280, 1440, 1920]) {
    await page.setViewportSize({ width, height: 900 });
    const { frame, shown } = await section.locator("[data-table=ready]").evaluate((table) => ({
      frame: table.getBoundingClientRect().width,
      shown: [...table.querySelectorAll<HTMLElement>("[data-table-view]")]
        .filter((view) => getComputedStyle(view).display !== "none")
        .map((view) => view.dataset.tableView),
    }));
    expect(shown, `${width} px, a frame of ${frame} px`).toEqual([frame >= 784 ? "table" : "cards"]);
    seen.add(shown[0]!);
  }
  expect([...seen].sort()).toEqual(["cards", "table"]);
});

test("the steps toggle lines up with the answer's text, and its fill and focus ring stay inside the card", async ({ page }) => {
  for (const width of [390, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/gallery/answer");
    for (const state of ["ready", "abstained", "empty", "refused"]) {
      const answer = page.locator(`[data-answer=${state}]`);
      const card = (await answer.locator("xpath=..").boundingBox())!;
      const toggle = answer.getByRole("button", { name: /I took$/ });
      // DESIGN.md section 10's focus ring: a 2 px outline at a 2 px offset.
      const ring = 4;
      const button = (await toggle.boundingBox())!;
      const icon = (await toggle.locator("svg").boundingBox())!;
      const text = (await answer.locator("h3, p").first().boundingBox())!;
      // The card's 1 px border stays clear of the fill and the ring.
      expect(button.x - ring, `${state} at ${width}`).toBeGreaterThan(card.x + 1);
      // The icon box starts on the text's edge: a flush button has no side border to push it in.
      expect(Math.abs(icon.x - text.x), `${state} at ${width}`).toBeLessThan(0.5);
    }
  }
});

test("the steps list starts its text under the toggle's text, on one inner edge", async ({ page }) => {
  for (const width of [390, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/gallery/answer");
    for (const state of ["ready", "abstained"]) {
      const answer = page.locator(`[data-answer=${state}]`);
      // Found by place, not by name: its name changes to "Hide the steps" once it opens.
      const toggle = answer.locator(":scope > div > button[aria-expanded]");
      await toggle.click();
      await expect(toggle).toHaveAttribute("aria-expanded", "true");
      const label = (await toggle.locator("span").boundingBox())!;
      const step = (await answer.locator("[data-steps] li > span:last-child").first().boundingBox())!;
      expect(Math.abs(step.x - label.x), `${state} at ${width}`).toBeLessThan(0.5);
    }
  }
});

// The count test further down checks that each answer sample's counts agree, whatever they
// are. This one stays beside it because it also pins the abstention's exact words, which a
// count alone would not catch if they changed.
test("the abstention's sentence, table and check line count the same 12 packages", async ({ page }) => {
  await page.goto("/gallery/answer");
  const answer = page.locator("[data-answer=abstained]");
  await expect(answer).toContainText("only 12 comparable packages. Here are all 12.");
  await expect(answer.locator("[data-table-view=table] tbody tr")).toHaveCount(12);
  await expect(answer.locator("[data-table]")).toContainText("Showing all 12 comparable packages");
  await expect(answer.locator("[data-check-line]")).toContainText("Checked: 12 of 12 numbers match records.");
  await answer.getByRole("button", { name: "Show the three steps I took" }).click();
  await expect(answer.locator("[data-steps]")).toContainText("I found 12 comparable packages.");
  await expect(answer.locator("[data-steps]")).toContainText("I checked the 12 numbers in the table against the records.");
});

// DESIGN.md section 5: "Check line ... Sits under 'In short', with the removed box open below
// it." In an abstention the rows come after both, so the proof stays beside the sentence.
test("in every answer with checks, the check line and the removed box come right under In short, before the rows", async ({
  page,
}) => {
  await page.goto("/gallery/answer");
  for (const state of ["ready", "abstained"]) {
    const order = await page.locator(`[data-answer=${state}]`).evaluate((root) =>
      [...root.querySelectorAll("[data-in-short], [data-check-line], [data-removed-lead], [data-table], [data-steps]")].map(
        (el) =>
          el.matches("[data-in-short]") ? "in short"
          : el.matches("[data-check-line]") ? "check line"
          : el.matches("[data-removed-lead]") ? "removed box"
          : el.matches("[data-table]") ? "rows"
          : "steps",
      ),
    );
    expect(order.slice(0, 3), state).toEqual(["in short", "check line", "removed box"]);
  }
  const held = page.locator("[data-answer=abstained]");
  const checkLine = (await held.locator("[data-check-line]").boundingBox())!;
  const rows = (await held.locator("[data-table]").boundingBox())!;
  expect(checkLine.y + checkLine.height).toBeLessThan(rows.y);
});

// Every mark of something you can check or look up is the same 1 px dotted line: a Term, a
// measure's name, a checkable number and the data date.
// Waits for the marks first: the data date shows a skeleton for its first second.
const underlines = async (marks: Locator, count: number) => {
  await expect(marks).toHaveCount(count);
  return marks.evaluateAll((els) =>
    els.map((el) => {
      const style = getComputedStyle(el);
      return [style.textDecorationLine, style.textDecorationStyle, style.textDecorationThickness, style.textDecorationColor].join(" ");
    }),
  );
};

test("a term, a measure, a checkable number and the data date share one dotted underline", async ({ page }) => {
  await page.goto("/gallery/numbers");
  const marks = [
    ...(await underlines(page.locator("[data-state-section=terms] [data-term]"), 2)),
    ...(await underlines(page.locator("[data-state-section=checkable] button[data-num]"), 1)),
  ];
  await page.goto("/gallery/navigation");
  marks.push(...(await underlines(page.locator("[data-stamp] a").first(), 1)));
  expect(marks).toHaveLength(4);
  expect(new Set(marks), marks.join("\n")).toEqual(new Set([marks[0]]));
  expect(marks[0]).toMatch(/^underline dotted 1px /);
});

test("a checkable number shows where it came from on focus, and Escape closes it", async ({ page }) => {
  await page.goto("/gallery/numbers");
  const num = page.locator("[data-state-section=checkable] button[data-num]");
  expect(await num.evaluate((el) => getComputedStyle(el).textDecorationStyle)).toBe("dotted");
  await num.focus();
  await expect(page.getByRole("tooltip")).toContainText("Matches paragraph 54 of the completion report for P000000.");
  await page.keyboard.press("Escape");
  await expect(page.getByRole("tooltip")).toBeHidden();
});

test("a term opens GLOSSARY.md's definition in a window, focus moves to its title, and Escape returns it", async ({ page }) => {
  const glossary = await readFile(new URL("../../GLOSSARY.md", import.meta.url), "utf8");
  const definition = /\*\*Comparable\*\*:\n(.+)/.exec(glossary)![1];
  await page.goto("/gallery/numbers");
  const term = page.getByRole("button", { name: "Comparable" });
  await term.click();
  const dialog = page.getByRole("dialog", { name: "Comparable" });
  await expect(dialog).toContainText(definition);
  await expect(dialog.getByRole("heading", { name: "Comparable" })).toBeFocused();
  const close = dialog.getByRole("button", { name: "Close the definition" });
  const size = (await close.boundingBox())!;
  expect([size.width, size.height]).toEqual([44, 44]);
  expect(await axe(page)).toEqual([]);
  await page.keyboard.press("Escape");
  await expect(dialog).toBeHidden();
  await expect(term).toBeFocused();
});

test("the open Menu panel and the view popover pass axe", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 900 });
  await page.goto("/gallery/navigation?menu=open&viewer=loading");
  await expect(page.locator("[data-menu-panel]")).toBeVisible();
  expect(await axe(page)).toEqual([]);

  await page.setViewportSize({ width: 1440, height: 900 });
  for (const viewer of ["", "&viewer=loading", "&viewer=signed-out", "&viewer=error"]) {
    await page.goto(`/gallery/navigation?view=open${viewer}`);
    await expect(page.getByRole("dialog", { name: "Your view" })).toBeVisible();
    expect(await axe(page), viewer).toEqual([]);
  }
  await expect(page.getByRole("dialog", { name: "Your view" })).toContainText("I can't tell which account you signed in with.");
});

test("a loading button keeps its name, its label and its width, and a disabled one stays focusable", async ({ page }) => {
  await page.goto("/gallery/buttons");
  const loading = page.locator("[data-state-section=loading] button").first();
  await expect(loading).toHaveAccessibleName("Mark as checked");
  await expect(loading).toHaveAttribute("aria-busy", "true");
  // Every variant keeps its label in sight beside the spinner, at the width it has at rest. The
  // widths are measured once Open Sans has loaded, since the fallback font sets other widths.
  await fontsSettled(page);
  const width = async (section: string, variant: string) =>
    Math.round((await page.locator(`[data-state-section=${section}] [data-button=${variant}]`).first().boundingBox())!.width);
  expect(await width("loading", "primary")).toBe(await width("variants", "primary"));
  expect(await width("loading", "secondary")).toBe(await width("variants", "secondary"));
  expect(await width("loading", "ghost")).toBe(await width("variants", "ghost"));
  for (const button of await page.locator("[data-state-section=loading] button").all()) {
    expect(await button.locator("span").evaluate((el) => getComputedStyle(el).opacity)).toBe("1");
    await expect(button.locator("svg.animate-spin")).toHaveCount(1);
  }
  const disabled = page.locator("[data-state-section=disabled] button").first();
  await disabled.focus();
  await expect(disabled).toBeFocused();
  await expect(disabled).toHaveAttribute("aria-disabled", "true");
});

// The tab strip centers its selected tab again when Open Sans arrives, so the tab tests measure
// after the font loads. The gallery draws after the page loads, so it may not have asked for
// Open Sans yet, and then fonts.ready resolves at once. Asking for each weight the gallery uses
// waits for those files. Two frames later the strip has re-centered for the new widths.
const fontsSettled = (page: Page) =>
  page.evaluate(async () => {
    await Promise.all(["400", "600", "700"].map((weight) => document.fonts.load(`${weight} 16px 'Open Sans'`)));
    await new Promise((done) => requestAnimationFrame(() => requestAnimationFrame(done)));
  });

// True once the tabs' bold Open Sans has loaded, so a measure is not taken in the fallback face.
const tabFontLoaded = (page: Page) => page.evaluate(() => document.fonts.check("700 16px 'Open Sans'"));

// DESIGN.md section 5: tabs on a light surface never wrap. Five section tabs need about 537 px,
// so on a phone the row scrolls inside its own strip: every tab keeps one top, the hairline
// runs under the whole strip, the selected tab starts in view, and no focus ring is clipped.
test("tabs on a light surface keep one row at 390 and 320 px, with the selected tab in view", async ({ page }) => {
  for (const width of [390, 320]) {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/gallery/links");
    await fontsSettled(page);
    for (const section of ["tabs", "tabs-later"]) {
      const strip = page.locator(`[data-state-section=${section}] [data-tab-strip]`);
      const at = `${section} at ${width} px`;
      const measure = () =>
        strip.evaluate((row) => {
          const box = (el: Element) => {
            const { top, right, bottom, left } = el.getBoundingClientRect();
            return { top, right, bottom, left };
          };
          return {
            strip: box(row),
            nav: { ...box(row.parentElement!), line: getComputedStyle(row.parentElement!).borderBottomWidth },
            tabs: [...row.querySelectorAll("a")].map(box),
            current: box(row.querySelector("[aria-current=page]")!),
            focused: document.activeElement?.closest("[data-tab-strip]") === row ? box(document.activeElement!) : null,
            scrolls: row.scrollWidth > row.clientWidth,
          };
        });
      const shape = await measure();
      expect(new Set(shape.tabs.map((tab) => tab.top)).size, at).toBe(1);
      expect(shape.scrolls, at).toBe(true);
      // A side with more tabs out of sight fades, so a reader can tell the row goes on.
      expect(await strip.getAttribute("data-more"), at).not.toBe("none");
      // The hairline is the nav's bottom border, the width of the column, right under the tabs.
      expect(shape.nav.line, at).toBe("1px");
      expect(shape.nav.bottom - 1, at).toBe(shape.tabs[0].bottom);
      // The selected tab and its 4 px of focus ring sit inside the visible strip.
      expect(shape.current.left - 4, at).toBeGreaterThanOrEqual(shape.strip.left);
      expect(shape.current.right + 4, at).toBeLessThanOrEqual(shape.strip.right);
      expect(shape.current.top - 4, at).toBeGreaterThanOrEqual(shape.strip.top);
      expect(shape.current.bottom + 4, at).toBeLessThanOrEqual(shape.strip.bottom);
      // A keyboard user who tabs to the last tab sees it whole, ring and all.
      await strip.getByRole("link").last().focus();
      const focused = (await measure()).focused!;
      expect(focused.right + 4, at).toBeLessThanOrEqual(shape.strip.right + 0.5);
      expect(focused.left - 4, at).toBeGreaterThanOrEqual(shape.strip.left - 0.5);
    }
  }
  // On a wide screen the row fits, so it neither scrolls nor fades.
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/gallery/links");
  for (const strip of await page.locator("[data-tab-strip]").all()) {
    expect(await strip.evaluate((row) => row.scrollWidth > row.clientWidth)).toBe(false);
    await expect(strip).toHaveAttribute("data-more", "none");
  }
});

// A pointer focuses a link on mousedown. If the strip scrolled then, the link would move out
// from under the mouseup and the click would be lost, so only keyboard focus scrolls it. A
// reader taps where the row fades, because the fade says more tabs are there.
async function pressInFade(page: Page, press: (x: number, y: number) => Promise<void>) {
  for (const width of [390, 320]) {
    await page.setViewportSize({ width, height: 900 });
    // The tabs section has more tabs to the right of its selected tab, tabs-later to the left.
    for (const [section, side] of [["tabs", "right"], ["tabs-later", "left"]] as const) {
      await page.goto("/gallery/links");
      await fontsSettled(page);
      const at = `${section}, ${side} fade, at ${width} px`;
      expect(await tabFontLoaded(page), `${at}: the tabs are measured in Open Sans`).toBe(true);
      const strip = page.locator(`[data-state-section=${section}] [data-tab-strip]`);
      // The press is at a point in the window, so the strip must be in the window first.
      await strip.scrollIntoViewIfNeeded();
      const target = await strip.evaluate((row, side) => {
        const edge = row.getBoundingClientRect();
        // The fade is the 32 px at the strip's edge. Press in the middle of the largest part of
        // a tab inside it.
        const [fadeLeft, fadeRight] = side === "right" ? [edge.right - 32, edge.right] : [edge.left, edge.left + 32];
        const parts = [...row.querySelectorAll("a")].map((tab) => {
          const box = tab.getBoundingClientRect();
          const [left, right] = [Math.max(box.left, fadeLeft), Math.min(box.right, fadeRight)];
          return { width: right - left, x: (left + right) / 2, y: box.top + box.height / 2, href: tab.getAttribute("href")! };
        });
        return parts.sort((a, b) => b.width - a.width)[0];
      }, side);
      await expect(strip, `${at}: the side fades`).toHaveAttribute("data-more", side === "right" ? /end|both/ : /start|both/);
      expect(target.width, `${at}: a tab shows in the fade`).toBeGreaterThanOrEqual(8);
      expect(target.y, `${at}: the press is in the window`).toBeGreaterThan(0);
      expect(target.y, `${at}: the press is in the window`).toBeLessThan(page.viewportSize()!.height);
      await press(target.x, target.y);
      await expect(page, at).toHaveURL(new RegExp(`${target.href}$`));
    }
  }
}

test("a click on a tab in the fade follows its link", async ({ page }) => {
  await pressInFade(page, (x, y) => page.mouse.click(x, y));
});

test.describe("on a touch screen", () => {
  test.use({ hasTouch: true });
  test("a tap on a tab in the fade follows its link", async ({ page }) => {
    await pressInFade(page, (x, y) => page.touchscreen.tap(x, y));
  });
});

// The guard for fontsSettled. A slow font is what made the tab tests fail about 1 run in 30
// when the helper only waited for fonts.ready, so here every font arrives half a second late.
// The tab tests above must still measure, and press, in Open Sans.
test("the tab tests wait for Open Sans even when it arrives late", async ({ page }) => {
  await page.route("**/*.woff2", async (route) => {
    await new Promise((done) => setTimeout(done, 500));
    await route.fallback();
  });
  await pressInFade(page, (x, y) => page.mouse.click(x, y));
});

// When the selected tab sits less than a fade's width from the row's end, the row goes all
// the way to that end. At 375 and 390 px, centering Procurement would scroll 2 or 3 px and
// fade out Summary's left edge as if a tab sat before it.
test("a selected tab near the row's start leaves the first tab whole, with no fade on its side", async ({ page }) => {
  for (const width of [375, 390]) {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/gallery/links");
    await fontsSettled(page);
    const strip = page.locator("[data-state-section=tabs] [data-tab-strip]");
    expect(await strip.evaluate((row) => row.scrollLeft), `at ${width} px`).toBe(0);
    await expect(strip, `at ${width} px`).toHaveAttribute("data-more", "end");
  }
});

// The Answer page promises that in each sample the sentences, the table, the check line and the
// steps count the same things. The check line tells a reader how far to trust an answer, and
// later tickets copy these samples, so the counts are checked here, not just stated.
const NUMBER_WORDS = ["one", "two", "three", "four", "five", "six", "seven", "eight", "nine"];
// The numbers a reader sees in a piece of text: numerals, and one to nine in words (DESIGN.md
// section 7, rule 12).
const numbersIn = (text: string) =>
  [...text.matchAll(new RegExp(`\\d[\\d,.]*\\d|\\d|\\b(?:${NUMBER_WORDS.join("|")})\\b`, "gi"))].map(([found]) => {
    const word = NUMBER_WORDS.indexOf(found.toLowerCase());
    return word >= 0 ? word + 1 : Number(found.replace(/,/g, ""));
  });

async function answerSample(page: Page, section: string) {
  const answer = page.locator(`[data-state-section=${section}] [data-answer]`);
  return answer.evaluate((root) => {
    // The text under "In short", without the markers' numbers and their previews.
    const inShort = root.querySelector("[data-in-short]")!.cloneNode(true) as HTMLElement;
    inShort.querySelectorAll("[data-citation], [role=tooltip]").forEach((el) => el.remove());
    return {
      sentences: inShort.textContent!,
      markers: root.querySelectorAll("[data-in-short] [data-citation]").length,
      checkLine: root.querySelector("[data-check-line]")!.textContent!,
      // "I removed one sentence." or "I removed no sentences."
      removed: root.querySelector("[data-removed-lead]")!.textContent!,
      steps: [...root.querySelectorAll("[data-steps] li")].map((li) => li.textContent!),
      rows: root.querySelectorAll("[data-table-view=table] tbody tr").length,
    };
  });
}

test("each answer sample's sentences, table, check line and steps count the same things", async ({ page }) => {
  await page.goto("/gallery/answer");
  const checked = (line: string) => Number(line.match(/Checked: (\d+) of (\d+) numbers?/)![2]);

  // Ready: the check line counts the numbers in the sentences that were kept, and the step that
  // wrote them counts the kept sentences and the removed one.
  const ready = await answerSample(page, "ready");
  expect(checked(ready.checkLine), `"${ready.sentences}" against "${ready.checkLine}"`).toBe(numbersIn(ready.sentences).length);
  const wrote = ready.steps.find((step) => step.startsWith("I wrote"))!;
  expect(numbersIn(wrote), wrote).toEqual([ready.markers + (numbersIn(ready.removed)[0] ?? 0)]);

  // Abstention: the sentence, the table's rows, the check line and the steps all give one count.
  // The test above pins that count to 12 and the exact words around it.
  const held = await answerSample(page, "abstained");
  const shown = held.rows;
  expect(numbersIn(held.sentences).every((n) => n === shown), held.sentences).toBe(true);
  expect(checked(held.checkLine), held.checkLine).toBe(shown);
  for (const step of held.steps.filter((step) => numbersIn(step).length > 0)) expect(numbersIn(step), step).toEqual([shown]);
});

// Each marker in the states row stands under its label, on the label's left edge.
test("each marker in the citation states row starts on its label's left edge", async ({ page }) => {
  await page.goto("/gallery/citations");
  const row = page.locator("[data-state-section=markers] p.text-caption");
  await expect(row).toHaveCount(3);
  for (const label of await row.all()) {
    const edges = await label.evaluate((p) => [
      p.getBoundingClientRect().left,
      p.parentElement!.querySelector("[data-citation]")!.getBoundingClientRect().left,
    ]);
    expect(edges[1], (await label.textContent())!).toBeCloseTo(edges[0], 0);
  }
});

// The strip centers its selected tab before the first paint, often in the fallback face. When
// Open Sans arrives the tabs change width, so the strip centers the tab again. Here letter
// spacing stands in for the font.
test("the strip centers its selected tab again when the tabs change width, as when the web font arrives", async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 900 });
  await page.goto("/gallery/links");
  await fontsSettled(page);
  const strip = page.locator("[data-state-section=tabs] [data-tab-strip]");
  await strip.evaluate((row) => row.querySelectorAll("a").forEach((tab) => (tab.style.letterSpacing = "2px")));
  await expect
    .poll(() =>
      strip.evaluate((row) => {
        const box = row.getBoundingClientRect();
        const tab = row.querySelector("[aria-current=page]")!.getBoundingClientRect();
        return Math.round(tab.left + tab.width / 2 - (box.left + box.width / 2));
      }),
    )
    .toBe(0);
});

// Where the strip rests once it has stopped moving: a wheel scroll may glide over a few frames.
const restingScroll = (strip: Locator) =>
  strip.evaluate(async (row) => {
    let [last, still] = [-1, 0];
    while (still < 5) {
      await new Promise(requestAnimationFrame);
      still = row.scrollLeft === last ? still + 1 : 0;
      last = row.scrollLeft;
    }
    return last;
  });

// Once a reader has pressed, scrolled or focused the strip, it does not move by itself, even
// when a tab changes width, so it cannot shift a tab out from under a press. Each way leaves the
// strip somewhere other than where it would center itself, so each case fails without the
// handler that notes it (onFocus, onWheel, onPointerDown in Tabs.tsx).
const HANDLE: Record<string, (page: Page, strip: Locator) => Promise<void>> = {
  // A keyboard user tabs to the last tab, and the strip scrolls it clear of the fade.
  "keyboard focus": async (_page, strip) => {
    await strip.getByRole("link").last().focus();
  },
  // A wheel or a trackpad moves the strip without pressing or focusing anything.
  "a wheel scroll": async (page, strip) => {
    const box = (await strip.boundingBox())!;
    await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
    const before = await strip.evaluate((row) => row.scrollLeft);
    await page.mouse.wheel(60, 0);
    await expect.poll(() => strip.evaluate((row) => row.scrollLeft)).not.toBe(before);
  },
  // A swipe on a phone starts with a press that focuses nothing, then the row scrolls.
  "a press": async (_page, strip) => {
    await strip.dispatchEvent("pointerdown");
    await strip.evaluate((row) => (row.scrollLeft = 20));
  },
};

for (const [how, handle] of Object.entries(HANDLE)) {
  test(`the strip stays where a reader left it after ${how}, when the tabs change width`, async ({ page }) => {
    await page.setViewportSize({ width: 320, height: 900 });
    await page.goto("/gallery/links");
    await fontsSettled(page);
    const strip = page.locator("[data-state-section=tabs] [data-tab-strip]");
    await strip.scrollIntoViewIfNeeded();
    await handle(page, strip);
    const left = await restingScroll(strip);
    await strip.evaluate((row) => row.querySelectorAll("a").forEach((tab) => (tab.style.letterSpacing = "2px")));
    await fontsSettled(page);
    expect(await strip.evaluate((row) => row.scrollLeft), how).toBe(left);
  });
}

test("the Plan check page shows the plan check at the page's full width, so its columns fit as they do on Check a plan", async ({ page }) => {
  await page.goto("/gallery/plan-check");
  await page.evaluate(() => document.fonts.ready);
  for (const width of [1024, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    const table = page.locator("[data-state-section=ready] [data-view=table]");
    await expect(table).toBeVisible();
    // The frame's margin is 72 px from 1024 px, so the page's 12 columns are the width less 144 px.
    expect(Math.round((await table.boundingBox())!.width), `${width} px`).toBe(width - 144);
    // No cell's text runs past its content box.
    const overflow = await page.evaluate(() =>
      Array.from(document.querySelectorAll("[data-view=table] th, [data-view=table] td")).flatMap((cell) => {
        if (cell.getClientRects().length === 0) return [];
        const right = cell.getBoundingClientRect().right - parseFloat(getComputedStyle(cell).paddingRight) + 0.5;
        const range = document.createRange();
        range.selectNodeContents(cell);
        return Array.from(range.getClientRects()).some((rect) => rect.right > right) ? [cell.textContent ?? ""] : [];
      }),
    );
    expect(overflow, `${width} px`).toEqual([]);
  }
});

// Ticket 14's evidence drawer, on the gallery's Evidence page. The record is KE-NWWDA-229129-CW-RFB
// as check_plan returned it (tests/fixtures/api/check-plan-p156634-nwwda-2026-10-09.json), whose
// Estimated amount the plan check writes as 300,000.00 (DESIGN.md section 6).
test("the drawer's record view writes the STEP amount in STEP's form, right-aligned, keeps the market approach whole, names every field and ends with its source", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/gallery/evidence");
  const record = page.locator("[data-state-section=record]");
  const amount = record.locator("[data-record] dd", { hasText: "300,000.00" });
  await expect(amount).toHaveText("300,000.00");
  expect(await amount.evaluate((element) => [getComputedStyle(element).textAlign, getComputedStyle(element).fontVariantNumeric])).toEqual([
    "right",
    "tabular-nums",
  ]);
  // "Open - National" moves to the next line whole, so no line ends inside STEP's own dash.
  const approach = record.locator("[data-record] [data-market-approach]");
  await expect(approach).toHaveText("Open - National");
  expect(await approach.evaluate((element) => element.getClientRects().length)).toBe(1);
  // Every value has its name: the description's is STEP's "Description".
  const groups = await record.locator("[data-record] > div").evaluateAll((divs) => divs.map((div) => [div.querySelectorAll("dt").length, div.querySelectorAll("dd").length]));
  expect(groups.every(([dt, dd]) => dt === 1 && dd === 1)).toBe(true);
  await expect(record.locator("[data-record] dt").first()).toHaveText("Description");
  await expect(record.locator("[data-source]")).toHaveText(
    "Source: Procurement Plan, Northern Water Works Development Agency, P156634, version of October 9, 2026, page 3.",
  );
});

// The 14 brief, section 5.11: one source line for a record, in its card and in its drawer. An ISR section
// (tests/ground_truth/values.toml, isr-1-pdo-indicators) is cited by its section, never by its key "s4",
// and a quote from it (isr-1-rural-access-end-target) is highlighted in its card.
test("a record's evidence card ends with its drawer's source line, and an ISR section's card and drawer name the section", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 900 });
  await page.goto("/gallery/evidence");
  const recordSource = "Source: Procurement Plan, Northern Water Works Development Agency, P156634, version of October 9, 2026, page 3.";
  await expect(page.locator("[data-card-sample=record] [data-source]")).toHaveText(recordSource);
  await expect(page.locator("[data-state-section=record] [data-source]")).toHaveText(recordSource);
  // The STEP reference in a record's heading moves to its own line whole when it fits there: at 430 px
  // the drawer sample's heading is too narrow for "Activity" and the reference together.
  await page.setViewportSize({ width: 430, height: 900 });
  for (const where of ["[data-card-sample=record]", "[data-state-section=record] [role=dialog] h2"]) {
    const reference = page.locator(where).locator(".font-mono", { hasText: "KE-NWWDA-229129-CW-RFB" });
    const lines = await reference.evaluate((element) => {
      const range = document.createRange();
      range.selectNodeContents(element);
      return new Set(Array.from(range.getClientRects(), (rect) => Math.round(rect.top))).size;
    });
    expect(lines, where).toBe(1);
  }
  await page.setViewportSize({ width: 390, height: 900 });

  await expect(page.locator("[data-card-sample=section] [data-source]")).toHaveText(
    "Source: Implementation Status and Results Report, P130164, February 22, 2014, section Project Development Objective Indicators, page 2.",
  );
  await expect(page.locator("[data-card-sample=section] mark")).toHaveText("Highlight starts. Percentage Value 67.00 67.00 80.00 Highlight ends.");
  const section = page.locator("[data-state-section=section] [role=dialog]");
  await expect(section.getByRole("heading", { level: 2 })).toHaveText("Rajasthan Road Sector Modernization, section Project Development Objective Indicators");
  await expect(section).toContainText("The whole section, word for word.");
  await expect(section.locator("[data-meta-line]")).not.toContainText("¶");
  // The switcher's tabs name two sections, and a long tab wraps inside its pill.
  const tabs = page.locator("[data-state-section=switcher-section]").getByRole("tab");
  await expect(tabs.first()).toHaveAccessibleName("ISR, Project Development Objective Indicators");
  await expect(tabs.nth(1)).toHaveAccessibleName(/^ICR, Annex\s/);
  await expect(page.locator("[data-state-section=switcher-section] [data-passage] mark")).toHaveText(
    "Highlight starts. Percentage Value 67.00 67.00 80.00 Highlight ends.",
  );
  const overflow = await tabs.first().evaluate((tab) => tab.scrollWidth > tab.clientWidth || tab.getBoundingClientRect().right > window.innerWidth);
  expect(overflow).toBe(false);
});

test("the drawer's meta line breaks only after a middle dot, and the switcher's tabs read ICR ¶54", async ({ page }) => {
  for (const width of [1440, 1024, 390]) {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/gallery/evidence");
    // Each part of the line keeps to one line: "PDF page 23 of 66", "October 10, 2019", "Section III.B".
    const parts = page.locator("[data-state-section=from-answer] [data-meta-line] [data-meta-part]");
    await expect(parts).toHaveCount(6);
    const lines = await parts.evaluateAll((elements) =>
      elements.slice(2).map((element) => {
        const range = document.createRange();
        range.selectNodeContents(element);
        return new Set(Array.from(range.getClientRects(), (rect) => Math.round(rect.top))).size;
      }),
    );
    expect(lines, `at ${width} px`).toEqual([1, 1, 1, 1]);
  }
  // "ICR ¶54", with a space between the short name and the mark that the tab really draws.
  const tabs = page.locator("[data-state-section=switcher]").getByRole("tab");
  const gaps = await tabs.evaluateAll((elements) =>
    elements.map((tab) => {
      const name = document.createTreeWalker(tab, NodeFilter.SHOW_TEXT).nextNode()!;
      const range = document.createRange();
      range.selectNodeContents(name);
      return [name.textContent, Math.round(tab.querySelector("[data-para-mark]")!.getBoundingClientRect().left - range.getBoundingClientRect().right)];
    }),
  );
  expect(gaps.map(([name]) => name)).toEqual(["ICR", "ICR"]);
  expect(gaps.every(([, gap]) => Number(gap) >= 3)).toBe(true);
  await expect(tabs.first()).toHaveAccessibleName("ICR paragraph 54");
});

// Ticket 90 (DESIGN.md section 4, Radius): corners by role, so a control and a fact never share a shape. Controls
// take 4 px, data keeps the pill and containers take 8 px. Every element a selector finds on screen is measured.
const CONTROL = "4px";
const DATA = "32px";
const CONTAINER = "8px";
async function corners(page: Page, shapes: [string, string][]) {
  return page.evaluate(
    (all) =>
      all.flatMap(([selector, radius]) => {
        const shown = Array.from(document.querySelectorAll(selector)).filter((el) => el.getClientRects().length > 0);
        const wrong = shown.map((el) => getComputedStyle(el).borderTopLeftRadius).filter((found) => found !== radius);
        return shown.length === 0 ? [`${selector}: none on screen`] : wrong.map((found) => `${selector}: ${found}, not ${radius}`);
      }),
    shapes,
  );
}

// The gallery draws its page after the load, so a measure waits for the page's title.
async function openGallery(page: Page, slug: string) {
  await page.goto(`/gallery/${slug}`);
  await expect(page.locator("[data-gallery-root] h1")).toBeVisible();
}

const PAGE_CORNERS: [string, [string, string][]][] = [
  ["buttons", [["[data-button]", CONTROL]]],
  ["badges", [["[data-badge]", DATA]]],
  ["cards", [["[data-state-section=card] > div > section", CONTAINER], ["[data-empty-state]", CONTAINER]]],
  ["citations", [["[data-citation]", DATA]]],
  ["table", [["[data-table-view=table]:not([aria-hidden]), [data-table-view=cards] > li", CONTAINER], ["[data-empty-state]", CONTAINER]]],
];

test("buttons have 4 px corners, badges and citation markers keep the pill, and cards, tables and the evidence card 8 px, at 1440, 1024 and 390 px; a press scales a button to 0.98 and its release snaps back", async ({
  page,
}) => {
  for (const [slug, shapes] of PAGE_CORNERS) {
    await openGallery(page, slug);
    for (const width of [1440, 1024, 390]) {
      await page.setViewportSize({ width, height: 900 });
      expect(await corners(page, shapes), `${slug} at ${width} px`).toEqual([]);
      if (slug === "citations") {
        // The evidence card is a popover, a container.
        const marker = page.locator("p").getByRole("link", { name: /^Source 1:/ });
        await marker.hover();
        await expect(page.getByRole("tooltip")).toBeVisible();
        expect(await corners(page, [["[data-radix-popper-content-wrapper] > *", CONTAINER]]), `evidence card at ${width} px`).toEqual([]);
        await page.mouse.move(5, 5);
        await expect(page.getByRole("tooltip")).toBeHidden();
      }
    }
    if (slug !== "buttons") continue;
    // DESIGN.md section 4, Motion: pressed, a primary or secondary button eases to 0.98 over 120 ms. The transition is
    // set only while it is pressed, so the release snaps back at once.
    await page.setViewportSize({ width: 1440, height: 900 });
    for (const variant of ["primary", "secondary"]) {
      const button = page.locator(`[data-state-section=variants] [data-button=${variant}]`);
      const look = () => button.evaluate((el) => ({ transform: getComputedStyle(el).transform, moves: getComputedStyle(el).transitionProperty.includes("transform") }));
      await button.hover();
      expect(await look(), `${variant} at rest`).toEqual({ transform: "none", moves: false });
      await page.mouse.down();
      await expect.poll(look, { message: `${variant} pressed` }).toEqual({ transform: "matrix(0.98, 0, 0, 0.98, 0, 0)", moves: true });
      await page.mouse.up();
      expect(await look(), `${variant} released`).toEqual({ transform: "none", moves: false });
    }
    // A ghost button and a disabled one do not scale.
    for (const quiet of ["[data-state-section=variants] [data-button=ghost]", "[data-state-section=disabled] [data-button=primary]"]) {
      await page.locator(quiet).hover();
      await page.mouse.down();
      await page.waitForTimeout(150);
      expect(await page.locator(quiet).evaluate((el) => getComputedStyle(el).transform), quiet).toBe("none");
      await page.mouse.up();
    }
  }
});

test("a list search, a key hint and a toggle button have a control's 4 px corners", async ({ page }) => {
  await openGallery(page, "hub");
  expect(await corners(page, [["[data-list-search] input", CONTROL]])).toEqual([]);
  await openGallery(page, "retrieval");
  expect(await corners(page, [["[data-key-hint]", CONTROL], ["[data-toggle]", CONTROL]])).toEqual([]);
});
