// The app's theme is DESIGN.md's theme (criterion 1 of ticket 02). The test reads the
// custom properties the built app puts on :root and compares them with DESIGN.md itself.
import type { Page } from "@playwright/test";
import { expect, mockApi, recorded, test } from "./mocked";
import { normalize, shapeRow, themeBlock, typeScale } from "./design-md";
import { SPACE_STEPS } from "../lint/rules";

async function rootTokens(page: Page): Promise<Map<string, string>> {
  await mockApi(page, { "/api/me": { body: await recorded("me.json") } });
  await page.goto("/");
  const pairs = await page.evaluate(() => {
    const found: [string, string][] = [];
    const visit = (rules: CSSRuleList) => {
      for (const rule of Array.from(rules)) {
        if (rule instanceof CSSStyleRule && /(^|,\s*):root\b/.test(rule.selectorText)) {
          for (const name of Array.from(rule.style)) {
            if (name.startsWith("--")) found.push([name, rule.style.getPropertyValue(name)]);
          }
        }
        if ("cssRules" in rule && !(rule instanceof CSSStyleRule)) visit((rule as CSSGroupingRule).cssRules);
      }
    };
    for (const sheet of Array.from(document.styleSheets)) visit(sheet.cssRules);
    return found;
  });
  return new Map(pairs.map(([name, value]) => [name, normalize(value)]));
}

const inSectionTwo = (name: string) =>
  name.startsWith("--color-") || name.startsWith("--radius-") || /^--font-(?!weight)/.test(name);

const px = (value: string) => (value.endsWith("rem") ? parseFloat(value) * 16 : parseFloat(value));

test("the app's theme has every token in DESIGN.md section 2's theme block, with the same value, and no others", async ({
  page,
}) => {
  const design = await themeBlock();
  const app = await rootTokens(page);
  const appNames = [...app.keys()].filter(inSectionTwo).sort();

  expect(design.size).toBeGreaterThan(30);
  expect(appNames).toEqual([...design.keys()].sort());

  // The build minifies values (#002244 becomes #024), so the browser compares what each one
  // computes to: DESIGN.md's value and the app's token, applied to the same property.
  const differences = await page.evaluate((tokens) => {
    const probe = document.createElement("div");
    document.body.append(probe);
    const property = (name: string) =>
      name.startsWith("--color-") ? "color" : name.startsWith("--radius-") ? "border-top-left-radius" : "font-family";
    const computed = (name: string, value: string) => {
      probe.style.setProperty(property(name), value);
      return getComputedStyle(probe).getPropertyValue(property(name));
    };
    const found = tokens
      .map(([name, value]) => ({ name, design: computed(name, value), app: computed(name, `var(${name})`) }))
      .filter((token) => token.design !== token.app || token.app === "");
    probe.remove();
    return found;
  }, [...design]);
  expect(differences).toEqual([]);
});

test("the app's type scale has each step in DESIGN.md section 3, at its size, line height, weight and tracking", async ({
  page,
}) => {
  const steps = await typeScale();
  const app = await rootTokens(page);

  expect(steps.map((step) => step.token)).toEqual([
    "display", "h1", "h2", "h3", "title", "body", "small", "caption", "label", "button",
  ]);
  for (const step of steps) {
    const name = `--text-${step.token}`;
    expect(px(app.get(name) ?? ""), name).toBe(step.size);
    const lineHeight = app.get(`${name}--line-height`) ?? "";
    expect(step.lineHeight.includes(".") ? lineHeight : String(px(lineHeight)), `${name} line height`).toBe(step.lineHeight);
    expect(app.get(`${name}--font-weight`), `${name} weight`).toBe(String(step.weight));
    const tracking = app.get(`${name}--letter-spacing`)?.replace(/^(-?)\./, "$10.") ?? null;
    expect(tracking, `${name} tracking`).toBe(step.tracking);
  }
});

test("the app's spacing steps and breakpoints are the ones in DESIGN.md section 4", async ({ page }) => {
  const app = await rootTokens(page);
  const spacing = (await shapeRow("Space")).match(/\d+/g)!.map(Number);
  const breakpoints = (await shapeRow("Breakpoints")).match(/\d{3,4}/g)!.map(Number);

  // Spacing classes count in steps of --spacing; the class lint allows only DESIGN.md's steps.
  expect(px(app.get("--spacing") ?? "")).toBe(4);
  expect(SPACE_STEPS.map((step) => step * 4)).toEqual(spacing);
  const appBreakpoints = [...app].filter(([name]) => name.startsWith("--breakpoint-")).map(([, value]) => px(value));
  expect(appBreakpoints.sort((a, b) => a - b)).toEqual(breakpoints.sort((a, b) => a - b));
});
