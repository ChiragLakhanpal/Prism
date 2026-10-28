// Ticket 94: where the focused element lands under the parts that stick. The frame's one hook (web/src/lib/sticky.ts)
// keeps the document's scroll padding at the bar plus a sticky head, plus 8 px, and at a sticky foot and the ask bar
// plus 8 px, so Tab and Shift+Tab never leave the focused element under the bar, the head, the foot or the box that
// floats at the window's foot (ticket 113).
import type { Page } from "@playwright/test";

// Where the focused element sits against the parts that stick now, or null when focus is in the bar, the sidebar, a
// sticky part itself or outside main.
function placeOfFocus() {
  const focused = document.activeElement as HTMLElement | null;
  if (!focused || !focused.closest("main") || focused.closest("[data-sticky]")) return null;
  const box = focused.getBoundingClientRect();
  if (box.height === 0) return null;
  // A part that sticks covers the element where their boxes share a whole pixel of height; a sticky head that has
  // not reached its place yet sits below the element and covers nothing. The ask bar covers only its box: the page
  // shows through its margins.
  const sticking = (part: Element | null): part is Element => part !== null && getComputedStyle(part).position === "sticky";
  const ask = document.querySelector("[data-box-band]");
  const parts = [document.querySelector("header.top-bar"), ...document.querySelectorAll("main [data-sticky]")]
    .filter(sticking)
    .map((part) => part.getBoundingClientRect());
  if (sticking(ask)) parts.push(ask.querySelector("form > [data-focus-ring]")!.getBoundingClientRect());
  const covers = (part: DOMRect) => Math.min(box.bottom, part.bottom) - Math.max(box.top, part.top) >= 1;
  return {
    name: `${focused.tagName.toLowerCase()} ${(focused.textContent ?? "").trim().slice(0, 40)}`,
    hidden: parts.some(covers) || Math.round(box.bottom) > window.innerHeight,
  };
}

// Tab forward the given number of times from the page's h1, then Shift+Tab as many times back, and list every focused
// element in main that a part that sticks covered, with how many were checked.
export async function tabUnderStickyParts(page: Page, presses: number): Promise<{ checked: number; covered: string[] }> {
  await page.locator("main h1").first().focus();
  const covered: string[] = [];
  let checked = 0;
  for (const key of [...Array(presses).fill("Tab"), ...Array(presses).fill("Shift+Tab")]) {
    await page.keyboard.press(key);
    const place = await page.evaluate(placeOfFocus);
    if (!place) continue;
    checked += 1;
    if (place.hidden) covered.push(`${key}: ${place.name}`);
  }
  return { checked, covered };
}
