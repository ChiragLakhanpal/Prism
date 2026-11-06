// The figures' order on How Prism works and each slot's size (the second draft's brief, sections 4 and 5), apart
// from the registry's drawings, so a screen test can read them without loading an SVG.
import type { FigureWordsId } from "./words";

// Every figure of both talks, by key: Prism's own talk's and the deep research talk's (ticket 162).
export type FigureId = FigureWordsId;
export type Slot = "stage" | "half" | "hairline";

// Each slot's drawing size in logical px, which is also its viewBox: a figure is drawn 1:1. The stage fills a slide's
// content box under its title; the half sits beside text; a hairline figure has the kernel's own 400 by 320 box.
export const SLOTS: Record<Slot, { width: number; height: number }> = {
  stage: { width: 864, height: 352 },
  half: { width: 420, height: 352 },
  hairline: { width: 400, height: 320 },
};

// How Prism works shows them in this order, one section each: the order the talk reaches them.
export const PAGE_ORDER: FigureId[] = [
  "core-sample",
  "strata",
  "one-answer",
  "layers",
  "architecture",
  "pipeline",
  "reading",
  "knowledge-model",
  "retrieval",
  "languages",
  "estimate",
  "checks",
  "ladder",
  "loops",
  // The deep research talk's figures (ticket 162; .notes/deck3/brief.md, section 6), in the order it reaches them.
  "merge-timeline",
  "two-apps",
  "five-ways",
  "brief-sections",
  "record-gap",
  "research-run",
  "evidence-ladder",
  "post-funnel",
];
