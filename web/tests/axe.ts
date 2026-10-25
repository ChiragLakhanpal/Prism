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

export async function scan(page: Page, within?: string) {
  const frames = page.frames().length - 1;
  if (frames > 0) {
    throw new Error(`The page holds ${frames} frame(s), and these scans cannot check a frame from another origin.`);
  }
  const builder = new AxeBuilder({ page }).withTags(WCAG_22_AA).setLegacyMode();
  return (within ? builder.include(within) : builder).analyze();
}
