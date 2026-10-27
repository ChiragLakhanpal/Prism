// The deck's type ramp, written once (the second draft's brief, section 2). On the 960 by 540 canvas the sizes are
// canvas pixels, so a slide keeps its layout whatever the reader's default font size, and the canvas scales as one
// unit (DESIGN.md section 4). In the reading view the same roles take the page's own tokens (DESIGN.md section 3).
//
// One element leads each slide: on a text slide the title, on a figure slide the figure, with a smaller title. Then
// the points, then notes and the source line, smallest and muted. Titles are ink-heading, body ink, notes and
// receded points ink-muted, action primary; the one focal mark is the figures' accent.
import type { CSSProperties } from "react";

export type Mode = "present" | "read";

export type Role =
  | "statement" // the title slide's statement
  | "title" // a text slide's title, DESIGN.md's display token
  | "figureTitle" // a figure slide's title, second to its figure
  | "topic" // an opener's topic name
  | "body" // a point, a tile's head, a demo's line
  | "head" // a tile's or a phase's head
  | "note" // what a tile or a phase says under its head; a topic's line
  | "result" // a measured number on a results slide
  | "source" // the source line under a slide's content
  | "label"; // a column head, a topic number

const CANVAS: Record<Role, CSSProperties> = {
  statement: { fontSize: 36, lineHeight: 1.15, fontWeight: 700 },
  title: { fontSize: 32, lineHeight: 1.2, fontWeight: 700 },
  figureTitle: { fontSize: 24, lineHeight: 1.25, fontWeight: 700 },
  topic: { fontSize: 40, lineHeight: 1.1, fontWeight: 700 },
  // Body text sits well under the titles, the figures and the measured numbers, so it never competes with them.
  body: { fontSize: 18, lineHeight: 1.5, fontWeight: 400 },
  head: { fontSize: 18, lineHeight: 1.3, fontWeight: 700 },
  note: { fontSize: 14, lineHeight: 1.5, fontWeight: 400 },
  result: { fontSize: 40, lineHeight: 1.05, fontWeight: 700 },
  source: { fontSize: 12, lineHeight: 1.45, fontWeight: 400 },
  label: { fontSize: 12, lineHeight: 1.2, fontWeight: 600 },
};

const PAGE: Record<Role, string> = {
  statement: "text-display",
  title: "text-h1",
  figureTitle: "text-h1",
  topic: "text-h1",
  body: "text-body",
  head: "text-h2",
  note: "text-small",
  result: "text-h1",
  source: "text-caption",
  label: "text-label",
};

// A role's type in a mode: canvas pixels as a style on a slide, the page's token as a class in the reading view.
export function type(role: Role, mode: Mode): { className?: string; style?: CSSProperties } {
  return mode === "present" ? { style: CANVAS[role] } : { className: PAGE[role] };
}

// The footer's sentence and the header's words, on the canvas only: the reading view has the app's own footer.
export const FOOTER: CSSProperties = { fontSize: 11, lineHeight: 1.2 };
export const TRACKER: CSSProperties = { fontSize: 12, lineHeight: 1 };

// An item a press brings in. Its state is in its attributes: aria-hidden until its step, data-current on its step,
// and data-receded after it, when its text takes the muted colour (a rule more specific than the text's own, so a
// head or a display number recedes too). It moves in with an opacity, a 6 px rise and a visibility change over
// 200 ms (DESIGN.md section 10: 120 to 200 ms), and its text changes colour over the same time. Under reduced motion
// nothing moves or fades; the items still step.
export const STEP = [
  "transition-[opacity,translate,visibility,color,border-color] duration-200 ease-out motion-reduce:transition-none",
  "[&_*]:transition-colors [&_*]:duration-200 [&_*]:ease-out motion-reduce:[&_*]:transition-none",
  "[&[data-receded]]:text-ink-muted [&[data-receded]_*]:text-ink-muted",
].join(" ");
export const SHOWN = "visible opacity-100 translate-y-0";
export const UNREACHED = "invisible opacity-0 translate-y-1.5 motion-reduce:translate-y-0";
