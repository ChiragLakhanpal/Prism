// Whether focus was last inside an element that has no element of its own around it, as a Task zone's section or one
// block of zone 1 (ticket 101). find names the element from a stable ref, such as the zone's heading, at the moment
// focus moves; the answer lives in a ref, which the caller reads after a rerender to put focus back on its heading when
// the element focus was on went away. One document-wide focusin listener per caller, removed when it unmounts.
import { useEffect, useRef, type RefObject } from "react";

export function useFocusWithin(find: () => HTMLElement | null): RefObject<boolean> {
  const inside = useRef(false);
  useEffect(() => {
    const track = (event: FocusEvent) => {
      inside.current = Boolean(find()?.contains(event.target as Node | null));
    };
    document.addEventListener("focusin", track);
    return () => document.removeEventListener("focusin", track);
    // find reads a ref, so the first one stays right for the component's life.
  }, []);
  return inside;
}
