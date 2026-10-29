// Ticket 59: a skeleton stands where its section will be drawn, so the page does not jump when the answer arrives.
// A test holds one /api answer, notes where the skeleton sits at each window width, releases the answer, and notes
// where the drawn section sits at the same widths, in one page load: the window is resized between the measures, as a
// person who turns a tablet would. The tops and ends are on the page, not the window, so scrolling changes nothing.
import type { Page } from "@playwright/test";
import { expect } from "./mocked";
import { fontsLoaded } from "./settled";

// The widths criterion 3 of ticket 59 names, from the narrowest phone to a wide laptop.
export const SKELETON_WIDTHS = [320, 390, 450, 496, 640, 767, 768, 1024, 1440];

export type Place = { top: number; bottom: number };
export type Shift = { width: number; top: number; end: number };
// A section: one element, or the run from one element's top to another's bottom, such as a page's head and the
// finding under it, which a skeleton stands for together.
export type Section = string | { from: string; to: string };

const first = (section: Section) => (typeof section === "string" ? section : section.from);

// Where the first shown element a selector matches sits on the page, once two frames have drawn at this size and the
// place has stopped changing (a chart or a list may lay out again from a ResizeObserver).
async function placeOf(page: Page, section: Section): Promise<Place> {
  const { from, to } = typeof section === "string" ? { from: section, to: section } : section;
  let last: Place | null = null;
  for (let tries = 0; tries < 20; tries++) {
    const place = await page.evaluate(async ({ from, to }) => {
      await new Promise((done) => requestAnimationFrame(() => requestAnimationFrame(done)));
      const shown = (wanted: string) => Array.from(document.querySelectorAll(wanted)).find((found) => found.getClientRects().length > 0);
      const [start, end] = [shown(from), shown(to)];
      if (!start || !end) return null;
      return { top: Math.round(start.getBoundingClientRect().top + window.scrollY), bottom: Math.round(end.getBoundingClientRect().bottom + window.scrollY) };
    }, { from, to });
    if (place && last && place.top === last.top && place.bottom === last.bottom) return place;
    if (place) last = place;
  }
  if (!last) throw new Error(`nothing on the page matches ${JSON.stringify(section)}`);
  return last;
}

async function placesAt(page: Page, section: Section, widths: number[], height: number): Promise<Record<number, Place>> {
  const places: Record<number, Place> = {};
  for (const width of widths) {
    await page.setViewportSize({ width, height });
    places[width] = await placeOf(page, section);
  }
  return places;
}

// Hold the answer to the request `hold` matches, open `path`, and measure `skeleton` at each width; then release the
// answer and measure `drawn` at each width. Mock the page's other requests before calling it: the held route is added
// last, so it answers first. The result is how far the drawn section's top and end lie from the skeleton's.
export async function skeletonShift(
  page: Page,
  options: {
    path: string;
    hold: string | RegExp;
    answer: { status?: number; body: string };
    skeleton: Section;
    drawn: Section;
    widths?: number[];
    height?: number;
    // What shows only once the answer is drawn, when `drawn` names a part that shows in both states, such as a head.
    loaded?: string;
    // A step to run once the skeleton shows and before it is measured, such as opening a closed section.
    prepare?: (page: Page) => Promise<void>;
    // A step to run once the answer is drawn and before it is measured, such as waiting for a chart.
    ready?: (page: Page) => Promise<void>;
  },
): Promise<Shift[]> {
  const { widths = SKELETON_WIDTHS, height = 900, loaded = first(options.drawn) } = options;
  await page.setViewportSize({ width: widths[0], height });
  let release!: () => void;
  const held = new Promise<void>((resolve) => (release = resolve));
  await page.route(options.hold, async (route) => {
    await held;
    await route.fulfill({ status: options.answer.status ?? 200, contentType: "application/json", body: options.answer.body });
  });
  await page.goto(options.path);
  await options.prepare?.(page);
  await expect(page.locator(first(options.skeleton)).filter({ visible: true }).first()).toBeVisible();
  await fontsLoaded(page);
  const before = await placesAt(page, options.skeleton, widths, height);
  release();
  await expect(page.locator(loaded).filter({ visible: true }).first()).toBeVisible();
  if (first(options.skeleton) !== first(options.drawn)) await expect(page.locator(first(options.skeleton)).filter({ visible: true })).toHaveCount(0);
  await options.ready?.(page);
  await fontsLoaded(page);
  const after = await placesAt(page, options.drawn, widths, height);
  return widths.map((width) => ({ width, top: after[width].top - before[width].top, end: after[width].bottom - before[width].bottom }));
}

// The widths at which the drawn section's top moved more than 24 px from the skeleton's, or its end more than 48 px
// (ticket 59, criterion 3), as "width: top +N, end +M" lines; an empty list passes.
export function jumps(shifts: Shift[], limits = { top: 24, end: 48 }): string[] {
  return shifts
    .filter((shift) => Math.abs(shift.top) > limits.top || Math.abs(shift.end) > limits.end)
    .map((shift) => `${shift.width}: top ${shift.top >= 0 ? "+" : ""}${shift.top}, end ${shift.end >= 0 ? "+" : ""}${shift.end}`);
}
