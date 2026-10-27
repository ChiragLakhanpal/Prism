// Accessibility and craft checks on every gallery page (criterion 7 of ticket 02, DESIGN.md
// section 10): axe finds no WCAG 2.2 AA violations, every tab stop shows a 2 px focus outline
// with a 2 px offset, targets are at least 24 by 24 px and buttons 44 px tall, motion stops
// under reduced motion and runs 120 to 200 ms otherwise, and the page reflows at 320 px.
import { scan } from "./axe";
import type { Page } from "@playwright/test";
import { expect, test } from "./mocked";
import { galleryCopy } from "../src/gallery/copy";

const FOCUS = ["rgb(182, 73, 12)", "rgb(245, 146, 108)"];
const SLUGS = ["", ...Object.keys(galleryCopy.pages)];

async function open(page: Page, path: string, width: number) {
  await page.setViewportSize({ width, height: 900 });
  await page.goto(`/gallery/${path}`);
  await expect(page.locator("[data-gallery-root] h1")).toBeVisible();
  // Let fade-ins finish, so contrast is measured on what stays on screen. Spinners never end.
  await page.waitForFunction(() =>
    document.getAnimations().every((a) => a.playState !== "running" || a.effect?.getTiming().iterations === Infinity),
  );
  // Measure in the web fonts, as a reader sees the page: under load, a P-code in a caption could still be in
  // the fallback mono font, whose shorter line made its link 23 px tall instead of 25 (ticket 15's drawer).
  await page.evaluate(() => document.fonts.ready);
}

async function violations(page: Page) {
  const results = await scan(page);
  return results.violations.map(
    (v) => `${v.id}: ${v.nodes.map((node) => `${node.target.join(" ")} ${node.failureSummary ?? ""}`).join("; ")}`,
  );
}

async function tabStops(page: Page) {
  const seen = new Set<string>();
  const problems: string[] = [];
  for (let i = 0; i < 200; i += 1) {
    await page.keyboard.press("Tab");
    const focus = await page.evaluate(() => {
      const el = document.activeElement as HTMLElement | null;
      if (!el || el === document.body) return null;
      const ring = (el.closest("[data-focus-ring]") as HTMLElement | null) ?? el;
      const style = getComputedStyle(ring);
      const path = `${el.tagName.toLowerCase()}:${el.textContent?.trim().slice(0, 30) ?? ""}:${Math.round(el.getBoundingClientRect().y + scrollY)}`;
      return { path, width: style.outlineWidth, offset: style.outlineOffset, style: style.outlineStyle, color: style.outlineColor };
    });
    if (!focus || seen.has(focus.path)) break;
    seen.add(focus.path);
    if (focus.width !== "2px" || focus.offset !== "2px" || focus.style !== "solid" || !FOCUS.includes(focus.color)) {
      problems.push(`${focus.path} ${focus.style} ${focus.width} offset ${focus.offset} ${focus.color}`);
    }
  }
  return { stops: seen.size, problems };
}

function smallTargets(page: Page) {
  return page.evaluate(() => {
    const targets = Array.from(
      document.querySelectorAll<HTMLElement>("a[href], button, input, [tabindex]:not([tabindex='-1']), summary"),
    ).filter((el) => el.getClientRects().length > 0 && !el.classList.contains("sr-only"));
    return targets.flatMap((el) => {
      const rect = el.getBoundingClientRect();
      // An ::after laid over the element (the citation marker's) pads its hit area.
      const after = getComputedStyle(el, "::after");
      const laid = after.position === "absolute" && after.content !== "none";
      const pad = (value: string) => (laid ? Math.max(0, -parseFloat(value) || 0) : 0);
      const width = rect.width + pad(after.left) + pad(after.right);
      const height = rect.height + pad(after.top) + pad(after.bottom);
      const isButton = el.hasAttribute("data-button");
      // A number you can check sits inside a sentence, such as "186 days", so it is an inline
      // target, which WCAG 2.5.8 exempts from the width; it still keeps a line 24 px tall (the
      // 10 brief, section 5).
      const inSentence = el.hasAttribute("data-num");
      const ok = (inSentence || width >= 24) && height >= 24 && (!isButton || Math.round(rect.height) === 44);
      const label = `${el.tagName.toLowerCase()} "${el.textContent?.trim().slice(0, 30)}"`;
      return ok ? [] : [`${label} ${Math.round(width)}x${Math.round(height)}`];
    });
  });
}

function motion(page: Page) {
  return page.evaluate(() =>
    Array.from(document.querySelectorAll<HTMLElement>("*")).flatMap((el) => {
      const style = getComputedStyle(el);
      const transitions = style.transitionDuration.split(",").map((part) => parseFloat(part) * 1000);
      const finite = style.animationIterationCount !== "infinite" && style.animationName !== "none";
      const animation = finite ? style.animationDuration.split(",").map((part) => parseFloat(part) * 1000) : [];
      // Spinners turn until loading ends, so only finite animations count.
      return [...transitions, ...animation].filter((ms) => ms > 0);
    }),
  );
}

// Each page opens once for each width and state it is checked in, and every check of that view runs
// on that load (ticket 55: a page took nine loads, now four). The checks that only read the page come
// first, then axe, which may scroll, then the tab stops, which move the focus, so each check sees the
// page as a fresh load shows it. Each check is soft, so one that fails still lets the others report.
for (const slug of SLUGS) {
  const name = slug || "index";

  // The navigation page is also checked at 390 px with the Menu panel open, for targets and tab stops.
  const views: [string, number][] = [[slug, 1440], [slug, 390], ...(slug === "navigation" ? [["navigation?menu=open", 390] as [string, number]] : [])];

  test(`${name}: at 1440 and 390 px, targets are at least 24 by 24 px and buttons 44 px tall, axe finds no WCAG 2.2 AA violations, and every tab stop shows a 2 px focus outline with a 2 px offset; at 1440 px, motion runs 120 to 200 ms`, async ({ page }) => {
    for (const [path, width] of views) {
      const view = `${path} at ${width}`;
      await open(page, path, width);
      expect.soft(await smallTargets(page), `targets, ${view}`).toEqual([]);
      if (path === slug && width === 1440) {
        expect.soft((await motion(page)).filter((ms) => ms < 120 || ms > 200), `motion, ${view}`).toEqual([]);
      }
      if (path === slug) {
        expect.soft(await violations(page), `axe, ${view}`).toEqual([]);
      }
      const { stops, problems } = await tabStops(page);
      expect.soft(stops, `tab stops, ${view}`).toBeGreaterThan(5);
      expect.soft(problems, `tab stops, ${view}`).toEqual([]);
    }
  });

  test(`${name}: the page reflows at 320 px with no horizontal scroll, and motion stops under reduced motion`, async ({ page }) => {
    await open(page, slug, 320);
    expect.soft(await page.evaluate(() => document.documentElement.scrollWidth), "reflow at 320").toBeLessThanOrEqual(320);

    await page.emulateMedia({ reducedMotion: "reduce" });
    await open(page, slug, 1440);
    expect.soft(await motion(page), "reduced motion at 1440").toEqual([]);
    expect
      .soft(
        await page.evaluate(() =>
          Array.from(document.querySelectorAll("*")).filter((el) => getComputedStyle(el).animationName !== "none").length,
        ),
        "animations under reduced motion at 1440",
      )
      .toBe(0);
    if (slug === "buttons") {
      // Ticket 90: under reduced motion a pressed button does not scale, and nothing on it transitions.
      const primary = page.locator("[data-state-section=variants] [data-button=primary]");
      await primary.hover();
      await page.mouse.down();
      await page.waitForTimeout(150);
      const pressed = await primary.evaluate((el) => ({
        transform: getComputedStyle(el).transform,
        transitions: getComputedStyle(el).transitionDuration.split(",").filter((part) => parseFloat(part) > 0).length,
      }));
      await page.mouse.up();
      expect.soft(pressed, "a pressed button under reduced motion").toEqual({ transform: "none", transitions: 0 });
    }
  });
}
