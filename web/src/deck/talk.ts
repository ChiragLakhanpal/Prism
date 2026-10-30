// The talk's shape (the second draft's brief, section 3): five topics between the bookends, and how the deck moves
// through slides and the presses inside them. Nothing here draws; Deck.tsx and the notes window share it, and the
// screen tests read it.
//
// A slide takes `steps` presses before the deck moves on: each press brings in one point, tile or figure step. A
// slide arrives at step 0 when the talk moves forward onto it, showing its title and the structure of its figure,
// and whole when the talk moves back onto it or the page loads on it. A press after the last step moves to the next
// slide.

export const TOPIC_ORDER = ["strata", "work", "built", "answers", "grows"] as const;
export type TopicKey = (typeof TOPIC_ORDER)[number];
export type Part = "open" | TopicKey | "close";

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

export function segments(parts: Part[], n: number): Record<TopicKey, Segment[]> {
  const found = Object.fromEntries(TOPIC_ORDER.map((topic) => [topic, [] as Segment[]])) as Record<TopicKey, Segment[]>;
  parts.forEach((part, index) => {
    if (part === "open" || part === "close") return;
    const at = index + 1;
    found[part].push(at < n ? "passed" : at === n ? "current" : "later");
  });
  return found;
}
