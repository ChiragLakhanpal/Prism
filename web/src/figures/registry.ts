// The structural figures (ticket 47; the second draft's brief, section 5), defined once for the deck at /present and
// How Prism works. core-sample is a hairline figure (hairline-create, web/src/figures/hairline); the rest are
// diagram-design figures under the strata-wb profile, drawn as HTML in web/figures/ and exported as SVG beside this
// file with the skill's export_svg.py --system-fonts, so they use the app's own Open Sans and Roboto Mono. Each SVG's
// viewBox is its slot, drawn 1:1. The words people read about each figure (its title, text version and caption) are
// in web/src/deck/copy.ts under figureCopy (and the research talk's in web/src/deck/research/copy.ts), and tests/test_deck_figures.py checks every export against its source.
//
// A figure marks the parts a press brings in with data-motion-item and data-step (the skill's step markup, in its
// static "none" mode), so the deck can show it one step at a time; the source stays complete, and How Prism works
// shows it whole.
import { PAGE_ORDER, SLOTS, type FigureId, type Slot } from "./order";

export { PAGE_ORDER, SLOTS, type FigureId, type Slot };

export type Figure = { id: FigureId; slot: Slot; svg: string | null; steps: number };

// Every exported drawing beside this file, by its key. A key whose export is missing draws as its text version.
const DRAWINGS: Record<string, string> = Object.fromEntries(
  Object.entries(import.meta.glob<string>("./*.svg", { query: "?raw", import: "default", eager: true })).map(([path, svg]) => [
    path.slice(2, -4),
    svg,
  ]),
);

// How many presses a drawing takes: its highest data-step.
export function stepsIn(svg: string | null): number {
  if (!svg) return 0;
  return Math.max(0, ...[...svg.matchAll(/data-step="(\d+)"/g)].map((match) => Number(match[1])));
}

const SLOT_OF: Record<FigureId, Slot> = {
  "core-sample": "hairline",
  strata: "stage",
  "one-answer": "stage",
  layers: "stage",
  architecture: "stage",
  pipeline: "stage",
  reading: "stage",
  "knowledge-model": "stage",
  retrieval: "stage",
  languages: "stage",
  estimate: "stage",
  checks: "stage",
  ladder: "half",
  loops: "stage",
  "merge-timeline": "stage",
  "two-apps": "stage",
  "five-ways": "stage",
  "brief-sections": "stage",
  "record-gap": "stage",
  "research-run": "stage",
  "evidence-ladder": "half",
  "post-funnel": "stage",
};

export const FIGURES = Object.fromEntries(
  PAGE_ORDER.map((id) => {
    const svg = SLOT_OF[id] === "hairline" ? null : (DRAWINGS[id] ?? null);
    return [id, { id, slot: SLOT_OF[id], svg, steps: stepsIn(svg) }];
  }),
) as Record<FigureId, Figure>;

// An exported SVG as the page inlines it: without its XML declaration, and with the width and height of its
// viewBox, so it draws 1:1.
export function inline(svg: string): string {
  return svg
    .replace(/^<\?xml[^>]*>\s*/, "")
    .replace(/<svg viewBox="0 0 (\d+) (\d+)"/, (_match, width: string, height: string) => `<svg width="${width}" height="${height}" viewBox="0 0 ${width} ${height}"`);
}
