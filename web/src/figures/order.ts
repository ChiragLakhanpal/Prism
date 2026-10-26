// The figures' order on How Strata works and each slot's size (the 47 brief, sections 3.4 and 8), apart from the
// registry's drawings, so a screen test can read them without loading an SVG.
import type { FigureCopyId } from "../deck/copy";

export type FigureId = FigureCopyId;
export type Slot = "wide" | "narrow" | "half" | "hairline";

// Each slot's drawing size in logical px. The credit row adds 36 px under the drawing.
export const SLOTS: Record<Slot, { width: number; height: number }> = {
  wide: { width: 864, height: 268 },
  narrow: { width: 568, height: 268 },
  half: { width: 420, height: 268 },
  hairline: { width: 346, height: 277 },
};

// How Strata works shows them in this order, one section each.
export const PAGE_ORDER: FigureId[] = ["core-sample", "one-answer", "pipeline", "reading", "knowledge-model", "retrieval", "ladder", "loops"];
