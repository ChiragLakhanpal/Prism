// The shell's media queries and visibility, in one place (ticket 92's review, follow-ups 4 and 5).
import { useEffect, useRef, useState } from "react";

// Whether a media query matches now, kept current as the window changes.
export function useMedia(query: string): boolean {
  const [matches, setMatches] = useState(() => window.matchMedia(query).matches);
  useEffect(() => {
    const media = window.matchMedia(query);
    const update = () => setMatches(media.matches);
    update();
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, [query]);
  return matches;
}

// Call onChange each time one of these media queries starts or stops matching, with the latest onChange, so a caller
// may pass a new function on every render.
export function useMediaChange(queries: string[], onChange: () => void) {
  const latest = useRef(onChange);
  latest.current = onChange;
  const key = queries.join("\n");
  useEffect(() => {
    const media = key.split("\n").map((query) => window.matchMedia(query));
    const changed = () => latest.current();
    media.forEach((one) => one.addEventListener("change", changed));
    return () => media.forEach((one) => one.removeEventListener("change", changed));
  }, [key]);
}

// Whether an element is drawn now: it has a box, and neither it nor a parent hides it. Element.checkVisibility says
// the same, but Safari before 17.4 lacks it, and a blur handler that called it there threw (ticket 92's review,
// follow-up 4).
export function isShown(element: Element): boolean {
  return element.getClientRects().length > 0 && getComputedStyle(element).visibility !== "hidden";
}
