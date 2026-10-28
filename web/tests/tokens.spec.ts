// The app's theme is DESIGN.md's theme (criterion 1 of ticket 02; ticket 90 added the redesigned shell's type,
// radius and motion tokens). The test reads the custom properties the built app puts on :root and compares them
// with DESIGN.md itself.
import type { Page } from "@playwright/test";
import { expect, mockApi, recorded, test } from "./mocked";
import { normalize, shapeRow, themeBlock, typeScale } from "./design-md";
import { SPACE_STEPS } from "../lint/rules";

async function rootTokens(page: Page): Promise<Map<string, string>> {
  await mockApi(page, { "/api/me": { body: await recorded("me.json") } });
  await page.goto("/");
  const pairs = await page.evaluate(() => {
    const found: [string, string][] = [];
    // The theme's own values, in its layer: a value a media query sets for a narrow window, such as the h1's
    // 20 px below 48rem, is checked against DESIGN.md by the type scale test below.
    const visit = (rules: CSSRuleList) => {
      for (const rule of Array.from(rules)) {
        if (rule instanceof CSSStyleRule && /(^|,\s*):root\b/.test(rule.selectorText)) {
          for (const name of Array.from(rule.style)) {
            if (name.startsWith("--")) found.push([name, rule.style.getPropertyValue(name)]);
          }
        }
        if (rule instanceof CSSLayerBlockRule) visit(rule.cssRules);
      }
    };
    for (const sheet of Array.from(document.styleSheets)) visit(sheet.cssRules);
    return found;
  });
  return new Map(pairs.map(([name, value]) => [name, normalize(value)]));
}

// The tokens DESIGN.md section 2's theme block names: colors, the two families and the weights, radii, the type
// scale, the two motion curves and six times, and the tooltip's width. Tailwind's own settings, such as --spacing
// and the breakpoints, are checked against section 4 below.
const inThemeBlock = (name: string) => /^--(color|radius|font|text|ease|motion|tooltip)-/.test(name);

const px = (value: string) => (value.endsWith("rem") ? parseFloat(value) * 16 : parseFloat(value));

test("the app's theme has every token in DESIGN.md section 2's theme block, with the same value, and no others", async ({
  page,
}) => {
  const design = await themeBlock();
  const app = await rootTokens(page);
  const appNames = [...app.keys()].filter(inThemeBlock).sort();

  expect(design.size).toBeGreaterThan(30);
  expect(appNames).toEqual([...design.keys()].sort());

  // The build minifies values (#002244 becomes #024), so the browser compares what each one
  // computes to: DESIGN.md's value and the app's token, applied to the same property.
  const differences = await page.evaluate((tokens) => {
    const probe = document.createElement("div");
    document.body.append(probe);
    const property = (name: string) => {
      if (name.startsWith("--color-")) return "color";
      if (name.startsWith("--radius-")) return "border-top-left-radius";
      if (name.startsWith("--font-weight-") || name.endsWith("--font-weight")) return "font-weight";
      if (name.startsWith("--font-")) return "font-family";
      if (name.endsWith("--line-height")) return "line-height";
      if (name.endsWith("--letter-spacing")) return "letter-spacing";
      if (name.startsWith("--text-")) return "font-size";
      if (name.startsWith("--ease-")) return "transition-timing-function";
      if (name.startsWith("--motion-")) return "transition-duration";
      return "width";
    };
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

test("the app's type scale has each step in DESIGN.md section 3, at its size, line height, weight and tracking, and the retired title and box corners are gone", async ({
  page,
}) => {
  const steps = await typeScale();
  const app = await rootTokens(page);

  expect(steps.map((step) => step.token)).toEqual([
    "display", "finding", "h1", "h2", "h3", "lead", "body", "small", "caption", "label", "chart-label", "button",
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

  // `title` is retired into h2 and the box's 22 px corners into a control's 4 px (DESIGN.md sections 3 and 4). The deck
  // moved their last uses, so neither token is left on :root.
  for (const name of ["--text-title", "--text-title--line-height", "--text-title--font-weight", "--radius-box"]) {
    expect(app.has(name), name).toBe(false);
  }

  // The finding and the h1 step down below 48rem, so the longest title still leaves the finding in a phone's first
  // screen (DESIGN.md section 3). Each is measured on a line inside the page.
  const sized = async () =>
    page.evaluate((tokens) => {
      const main = document.querySelector("main")!;
      return tokens.map((token) => {
        const line = document.createElement("p");
        line.className = `text-${token}`;
        main.append(line);
        const style = getComputedStyle(line);
        const found = { token, size: parseFloat(style.fontSize), lineHeight: String(parseFloat(style.lineHeight)) };
        line.remove();
        return found;
      });
    }, steps.filter((step) => step.below).map((step) => step.token));
  const stepping = steps.filter((step) => step.below);
  expect(stepping.map((step) => step.token)).toEqual(["finding", "h1"]);
  await page.setViewportSize({ width: 1440, height: 900 });
  expect(await sized()).toEqual(stepping.map((step) => ({ token: step.token, size: step.size, lineHeight: step.lineHeight })));
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await sized()).toEqual(stepping.map((step) => ({ token: step.token, ...step.below })));
});

test("the app's spacing steps and breakpoints are the ones in DESIGN.md section 4", async ({ page }) => {
  const app = await rootTokens(page);
  // The Space row starts with the scale ("2, 4, 8, ... 64 px"), then names each step's role.
  const space = await shapeRow("Space");
  const spacing = space.slice(0, space.indexOf(" px")).match(/\d+/g)!.map(Number);
  const breakpoints = (await shapeRow("Breakpoints")).match(/\d{3,4}/g)!.map(Number);

  // Spacing classes count in steps of --spacing; the class lint allows only DESIGN.md's steps.
  expect(px(app.get("--spacing") ?? "")).toBe(4);
  expect(SPACE_STEPS.map((step) => step * 4)).toEqual(spacing);
  const appBreakpoints = [...app].filter(([name]) => name.startsWith("--breakpoint-")).map(([, value]) => px(value));
  expect(appBreakpoints.sort((a, b) => a - b)).toEqual(breakpoints.sort((a, b) => a - b));

  // The Grid row's widest content is app.css's --layout-max (ticket 110: 1440 px, so a wide page fills a laptop's frame).
  const widest = /content at most (\d+)px wide/.exec(await shapeRow("Grid"));
  expect(widest, "DESIGN.md's Grid row names the widest content").not.toBeNull();
  const layout = await page.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue("--layout-max").trim());
  expect(px(layout)).toBe(Number(widest![1]));
});
