// The one way the screen tests run axe: every scan checks the WCAG 2.2 AA rules, on the whole page
// or inside one part of it. Every spec calls scan() here, and tests/test_gate.py checks that no other
// file builds its own scan.
//
// The scans run in axe's legacy mode (ticket 55). axe's default run checks each frame on its own,
// then opens a blank page, loads axe into it a second time and finishes the scan there, so a page
// from another origin inside a frame can be checked too. That blank page roughly doubled the cost
// of every scan, and the axe scans set most of the Playwright tests' time. Legacy mode runs the same
// rules inside the page it checks and finds the same violations (tests/axe.spec.ts compares the
// two), but it cannot check a frame from another origin. Strata's pages hold no frames, so a scan of
// a page that holds one fails, and whoever adds a frame must check it another way.
import AxeBuilder from "@axe-core/playwright";
import type { Page } from "@playwright/test";

export const WCAG_22_AA = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

// Ticket 113: the box floats at the window's foot over whatever the page has scrolled under it, so which of the page's
// targets it partly covers, or sits within 24 px of, depends only on where the page is scrolled, and axe counts each
// such target as too small (WCAG 2.5.8). For the scan, the ask bar rests in its own place at the page column's end,
// above the footer, which it keeps as it sticks, so nothing else moves: the page's targets are checked as the page lays
// them out, and the box, its list and its chip are checked as drawn, at that place. Where a focused element lands
// against the box as the page scrolls is tested on its own, by Tab (tests/sticky.ts).
const BOX_COVERS_NOTHING = "[data-box-band] { position: relative !important; bottom: auto !important; }";

export async function scan(page: Page, within?: string) {
  const frames = page.frames().length - 1;
  if (frames > 0) {
    throw new Error(`The page holds ${frames} frame(s), and these scans cannot check a frame from another origin.`);
  }
  const builder = new AxeBuilder({ page }).withTags(WCAG_22_AA).setLegacyMode();
  const rest = await page.addStyleTag({ content: BOX_COVERS_NOTHING });
  try {
    return await (within ? builder.include(within) : builder).analyze();
  } finally {
    await rest.evaluate((style) => (style as Element).remove());
  }
}
