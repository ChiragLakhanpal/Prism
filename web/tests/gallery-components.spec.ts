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
  const nums = page.locator("[data-state-section=ratios] [data-num]");
  await expect(nums).toHaveText(["6 of 12", "31 of 37, about 8 in 10", "42 of 50, 84 percent", "93 of 118, 79%"]);
  await expect(page.locator("[data-state-section=formats] [data-num]")).toHaveText([
    "1,234", "12.5K", "296K", "1.3M", "2.5B", "0.46", "45.7", "457",
  ]);
  expect(await nums.first().evaluate((el) => getComputedStyle(el).fontVariantNumeric)).toBe("tabular-nums");
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
  for (const viewer of ["", "&viewer=loading", "&viewer=error"]) {
    await page.goto(`/gallery/navigation?view=open${viewer}`);
    await expect(page.getByRole("dialog", { name: "Your view" })).toBeVisible();
    expect(await axe(page), viewer).toEqual([]);
  }
  await expect(page.getByRole("dialog", { name: "Your view" })).toContainText("I can't tell which account you signed in with.");
});

test("a loading button keeps its name and a disabled one stays focusable", async ({ page }) => {
  await page.goto("/gallery/buttons");
  const loading = page.locator("[data-state-section=loading] button").first();
  await expect(loading).toHaveAccessibleName("Mark as checked");
  await expect(loading).toHaveAttribute("aria-busy", "true");
  const disabled = page.locator("[data-state-section=disabled] button").first();
  await disabled.focus();
  await expect(disabled).toBeFocused();
  await expect(disabled).toHaveAttribute("aria-disabled", "true");
});
