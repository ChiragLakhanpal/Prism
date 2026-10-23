// The gallery's components behave as DESIGN.md section 5 says (criteria 5, 6 and 7 of ticket
// 02): badges carry their state in an icon shape and a word, the citation marker names its
// source, the check line is neutral, Num never turns a small count into a percentage, and the
// open states (Menu, view popover, tooltip, DefinitionWindow) pass axe and close on Escape.
import { readFile } from "node:fs/promises";
import AxeBuilder from "@axe-core/playwright";
import type { Page } from "@playwright/test";
import { expect, test } from "./mocked";

const WCAG_22_AA = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

async function axe(page: Page) {
  await page.waitForFunction(() =>
    document.getAnimations().every((a) => a.playState !== "running" || a.effect?.getTiming().iterations === Infinity),
  );
  const results = await new AxeBuilder({ page }).withTags(WCAG_22_AA).analyze();
  return results.violations.map((v) => `${v.id}: ${v.nodes.map((node) => node.target.join(" ")).join(", ")}`);
}

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

test("the citation marker's accessible name names the source, and a copy of it reads [1]", async ({ page }) => {
  await page.goto("/gallery/citations");
  const marker = page.getByRole("link", { name: "Source 1: Implementation Completion and Results Report, June 30, 2021, paragraph 54" }).first();
  await expect(marker).toBeVisible();
  expect(await marker.textContent()).toBe("[1]");
  await expect(
    page.getByRole("link", { name: "Source 2: Implementation Status and Results Report, March 4, 2024, paragraph 12, opened" }).first(),
  ).toBeVisible();
});

test("hovering or focusing a marker shows its evidence card, and Escape closes it", async ({ page }) => {
  await page.goto("/gallery/citations");
  const marker = page.locator("p").getByRole("link", { name: /^Source 1:/ });
  await marker.focus();
  const card = page.getByRole("tooltip");
  await expect(card).toContainText("The contracts were advertised again");
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
    "1,234", "12.5K", "296K", "1.3M", "2.5B", "0.46", "45.7", "457",
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
  await expect(cards).toHaveCount(5 + 8 + 5);
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
  const tableCards = page.locator("[data-table=ready] ul > li");
  await expect(tableCards).toHaveCount(4);
  const tops = await tableCards.evaluateAll((items) =>
    items.map((item) => [...item.querySelectorAll("[data-card-field=number] dd")].map((dd) => Math.round(dd.getBoundingClientRect().top))),
  );
  for (const card of tops) {
    expect(card).toHaveLength(2);
    expect(new Set(card).size).toBe(1);
  }
});

test("the steps toggle lines up with the answer's text, and its fill and focus ring stay inside the card", async ({ page }) => {
  for (const width of [390, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/gallery/answer");
    for (const state of ["ready", "abstained", "empty", "refused"]) {
      const answer = page.locator(`[data-answer=${state}]`);
      const card = (await answer.locator("xpath=..").boundingBox())!;
      const toggle = page.locator(`[data-answer=${state}] > div:last-child > button`);
      // DESIGN.md section 10's focus ring: a 2 px outline at a 2 px offset.
      const ring = 4;
      const button = (await toggle.boundingBox())!;
      const icon = (await toggle.locator("svg").boundingBox())!;
      const text = (await answer.locator("h3, p").first().boundingBox())!;
      // The card's 1 px border stays clear of the fill and the ring.
      expect(button.x - ring, `${state} at ${width}`).toBeGreaterThan(card.x + 1);
      // The icon box starts within 2 px of the text, the width of the button's clear border.
      expect(Math.abs(icon.x - text.x), `${state} at ${width}`).toBeLessThanOrEqual(2);
    }
  }
});

test("the abstention's sentence, table and check line count the same 12 packages", async ({ page }) => {
  await page.goto("/gallery/answer");
  const answer = page.locator("[data-answer=abstained]");
  await expect(answer).toContainText("only 12 comparable packages. Here are all 12.");
  await expect(answer.locator("table tbody tr")).toHaveCount(12);
  await expect(answer.locator("[data-table]")).toContainText("Showing all 12 comparable packages");
  await expect(answer.locator("[data-check-line]")).toContainText("Checked: 12 of 12 numbers match records.");
  await answer.getByRole("button", { name: "Show the three steps I took" }).click();
  await expect(answer.locator("[data-steps]")).toContainText("I found 12 comparable packages.");
  await expect(answer.locator("[data-steps]")).toContainText("I checked the 12 numbers in the table against the records.");
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
  // Every variant keeps its label in sight beside the spinner, at the width it has at rest.
  const width = async (section: string, variant: string) =>
    Math.round((await page.locator(`[data-state-section=${section}] [data-button=${variant}]`).first().boundingBox())!.width);
  expect(await width("loading", "primary")).toBe(await width("variants", "primary"));
  expect(await width("loading", "secondary")).toBe(await width("with-icon", "secondary"));
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
