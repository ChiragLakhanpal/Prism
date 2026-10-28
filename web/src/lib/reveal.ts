// Whether what a wait produced should enter with a reveal (ticket 111; DESIGN.md section 4, Motion): a reveal follows a
// wait and never a page load. It is true from the render where the wait ends, when the wait showed for at least
// minMs, until key changes: a new question's run, or another plan's address. A result that was ready when the part
// first drew, such as an answer shown again by Back, or one that came faster than minMs, is drawn at once.
//
// The reveal itself is a CSS transition from @starting-style, so it runs once, when its element is first drawn;
// later renders keep the class and move nothing.
import { useRef } from "react";

// How long a page's narration must have shown before what replaces it enters (DESIGN.md section 4, Motion): a
// faster result appears at once, since a reveal after a blink would only slow it down.
export const REVEAL_AFTER_MS = 400;

export function useRevealAfterWait(waiting: boolean, key: string | number, minMs = 0): boolean {
  const state = useRef<{ key: string | number; since: number | null; reveal: boolean }>({ key, since: null, reveal: false });
  if (state.current.key !== key) state.current = { key, since: null, reveal: false };
  const now = state.current;
  if (waiting) {
    now.since ??= performance.now();
    now.reveal = false;
  } else if (now.since !== null) {
    now.reveal = performance.now() - now.since >= minMs;
    now.since = null;
  }
  return !waiting && now.reveal;
}
