// The talks' shape (the second draft's brief, section 3; the research talk's brief, section 2): each talk has five
// topics between its bookends, and the deck moves through its slides and the presses inside them the same way.
// Nothing here draws; Deck.tsx and the notes window share it, and the screen tests read it.
//
// A slide takes `steps` presses before the deck moves on: each press brings in one point, tile or figure step. A
// slide arrives at step 0 when the talk moves forward onto it, showing its title and the structure of its figure,
// and whole when the talk moves back onto it or the page loads on it. A press after the last step moves to the next
// slide.
import type { ReactNode } from "react";
import type { DeckData } from "./data";
import type { Slide } from "./slides";

// The deck holds two talks on one engine: Prism's own at /present, and deep research at /present/research.
export type TalkKey = "strata" | "research";

// Each talk's topics in order, by key: the tracker shows them, and an agenda, where a talk has one, lists them.
export const TOPICS = {
  strata: ["strata", "work", "built", "answers", "grows"],
  research: ["here", "brief", "works", "decisions", "next"],
} as const satisfies Record<TalkKey, readonly string[]>;

// The first talk's topics, as the first draft named them.
export const TOPIC_ORDER = TOPICS.strata;
export type TopicKey = (typeof TOPICS)[TalkKey][number];
export type Part = "open" | TopicKey | "close";

// Where each talk lives: its address and the channel its notes window listens on, so a notes window follows its own
// deck.
export const PLACES: Record<TalkKey, { base: string; channel: string }> = {
  strata: { base: "/present", channel: "strata-deck" },
  research: { base: "/present/research", channel: "strata-deck-research" },
};

// Where a talk shows DESIGN.md section 8's sentence: along every slide's foot, along the title slide's only, or on no
// slide (the user, November 6, 2026, of the research talk: no sources or disclaimers on the slides). The reading view
// keeps the app's own footer at the end of the page whichever it is.
export type FooterOn = "every" | "title" | "none";

// A talk, as the engine takes it: its key and address, its topics in order with their names and, for a talk with an
// agenda and openers, their lines, the builder that makes its slides from the deck's data, and where its footer shows.
export type Talk = {
  key: TalkKey;
  base: string;
  channel: string;
  order: readonly TopicKey[];
  topics: (data: DeckData) => Record<string, { name: string; line?: ReactNode }>;
  build: (data: DeckData) => Slide[];
  footer: FooterOn;
};

// Whether a slide of this kind carries the footer sentence in a talk.
export const footerOn = (footer: FooterOn, kind: string) => footer === "every" || (footer === "title" && kind === "title");

// Where the talk is: the slide (1-based) and how many of its presses have been made.
export type Place = { n: number; step: number };

// The little the movement needs to know about a slide.
export type Stop = { steps: number };

const clamp = (n: number, total: number) => Math.min(Math.max(n, 1), total);

// The place one press forward: the slide's next step, or the next slide at its start. At the end it stays.
export function forward(at: Place, stops: Stop[]): Place {
  const steps = stops[at.n - 1]?.steps ?? 0;
  if (at.step < steps) return { n: at.n, step: at.step + 1 };
  return at.n < stops.length ? { n: at.n + 1, step: 0 } : at;
}

// The place one press back: the slide's step before, or the slide before, whole. At the start it stays.
export function back(at: Place, stops: Stop[]): Place {
  if (at.step > 0) return { n: at.n, step: at.step - 1 };
  return at.n > 1 ? { n: at.n - 1, step: stops[at.n - 2]?.steps ?? 0 } : at;
}

// Arriving at a slide by a jump (the notes window's outline, a link, the first load): forward onto it starts at its
// first step; back onto it, or a load, shows it whole.
export function arrive(target: number, from: number | null, stops: Stop[]): Place {
  const n = clamp(target, stops.length);
  const whole = stops[n - 1]?.steps ?? 0;
  return from !== null && n > from ? { n, step: 0 } : { n, step: whole };
}

// The keys that move the deck (DESIGN.md section 10): the arrow keys, Page Up and Page Down (a clicker's), Home and
// End; no single-character shortcut, and none while a modifier is held, focus is in a form field, or focus is inside
// a table that scrolls.
export type Move = "forward" | "back" | "first" | "last";

export function moveFor(event: KeyboardEvent): Move | null {
  if (event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return null;
  const target = event.target as HTMLElement | null;
  if (target?.closest?.("input, textarea, select, [contenteditable=true], [data-scroll-region], [role=dialog]")) return null;
  if (["ArrowRight", "ArrowDown", "PageDown"].includes(event.key)) return "forward";
  // Space and Enter move on too, as in most slide tools, except on a button or a link, which they press instead.
  if ((event.key === " " || event.key === "Enter") && !target?.closest?.("a, button, summary, [role=button], [role=link]")) return "forward";
  if (["ArrowLeft", "ArrowUp", "PageUp"].includes(event.key)) return "back";
  if (event.key === "Home") return "first";
  if (event.key === "End") return "last";
  return null;
}

// F, with no modifier and outside a field, toggles full screen.
export function fullScreenKey(event: KeyboardEvent): boolean {
  if (event.altKey || event.ctrlKey || event.metaKey) return false;
  const target = event.target as HTMLElement | null;
  if (target?.closest?.("input, textarea, select, [contenteditable=true], [role=dialog]")) return false;
  return event.key === "f" || event.key === "F";
}

export function moved(at: Place, move: Move, stops: Stop[]): Place {
  if (move === "forward") return forward(at, stops);
  if (move === "back") return back(at, stops);
  if (move === "first") return { n: 1, step: 0 };
  return { n: stops.length, step: stops[stops.length - 1]?.steps ?? 0 };
}

// What the header's tracker shows for one topic: a segment per slide of the topic, each passed, current or later.
export type Segment = "passed" | "current" | "later";

export function segments(parts: Part[], n: number, order: readonly TopicKey[] = TOPIC_ORDER): Record<string, Segment[]> {
  const found: Record<string, Segment[]> = Object.fromEntries(order.map((topic) => [topic, [] as Segment[]]));
  parts.forEach((part, index) => {
    if (part === "open" || part === "close" || !(part in found)) return;
    const at = index + 1;
    found[part].push(at < n ? "passed" : at === n ? "current" : "later");
  });
  return found;
}
