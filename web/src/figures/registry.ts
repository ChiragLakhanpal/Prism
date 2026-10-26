// The eight structural figures (ticket 47; the 47 brief, section 4), defined once for the deck at /present and How
// Strata works. F1 is a hairline figure (hairline-create, web/src/figures/hairline); F2 to F8 are diagram-design
// figures under the strata-wb profile, drawn as HTML in web/figures/ and exported as SVG beside this file with the
// skill's export_svg.py --system-fonts, so they use the app's own Open Sans and Roboto Mono. Each SVG's viewBox is its
// slot on the slide, drawn 1:1. The words people read about each figure (its title, text version and caption) are
// in web/src/deck/copy.ts under figureCopy, and tests/test_deck_figures.py checks every export against its source.
//
// The keys of the figures that show what one of the proposal's figures shows are the proposal's own keys (ticket 46,
// src/strata/proposal/figures.py): pipeline, reading, knowledge-model, retrieval and loops.
import knowledgeModel from "./knowledge-model.svg?raw";
import ladder from "./ladder.svg?raw";
import loops from "./loops.svg?raw";
import oneAnswer from "./one-answer.svg?raw";
import pipeline from "./pipeline.svg?raw";
import reading from "./reading.svg?raw";
import retrieval from "./retrieval.svg?raw";
import { PAGE_ORDER, SLOTS, type FigureId, type Slot } from "./order";

export { PAGE_ORDER, SLOTS, type FigureId, type Slot };

export type Figure = { id: FigureId; slot: Slot; svg: string | null; slide: number };

export const FIGURES: Record<FigureId, Figure> = {
  "core-sample": { id: "core-sample", slot: "hairline", svg: null, slide: 1 },
  "one-answer": { id: "one-answer", slot: "narrow", svg: oneAnswer, slide: 2 },
  pipeline: { id: "pipeline", slot: "wide", svg: pipeline, slide: 4 },
  reading: { id: "reading", slot: "narrow", svg: reading, slide: 5 },
  "knowledge-model": { id: "knowledge-model", slot: "wide", svg: knowledgeModel, slide: 6 },
  retrieval: { id: "retrieval", slot: "wide", svg: retrieval, slide: 9 },
  ladder: { id: "ladder", slot: "half", svg: ladder, slide: 11 },
  loops: { id: "loops", slot: "wide", svg: loops, slide: 12 },
};

// An exported SVG as the page inlines it: without its XML declaration, and with the width and height of its
// viewBox, so it draws 1:1.
export function inline(svg: string): string {
  return svg
    .replace(/^<\?xml[^>]*>\s*/, "")
    .replace(/<svg viewBox="0 0 (\d+) (\d+)"/, (_match, width: string, height: string) => `<svg width="${width}" height="${height}" viewBox="0 0 ${width} ${height}"`);
}
