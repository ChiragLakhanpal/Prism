// Citation markers numbered once per page, in DOM order (the 28 brief, section 6.4; DESIGN.md section 5, Citation
// marker). Each part of a page that draws numbered markers registers the evidence ids it cites, in its own order,
// under its place on the page (section 1's block before section 5's lists). A marker's number counts every id
// registered before it, those in closed lists and rows not shown yet included, so a number never changes when a
// list opens, and an evidence id cited twice keeps its first number. The answer panel numbers its own markers.
import { useEffect, useMemo } from "react";
import { createStore, useStore } from "./store";

export const SECTION_1 = 1;
export const SECTION_5 = 5;

const registered = createStore<Record<number, string[]>>({});

export function numbersFrom(parts: Record<number, string[]>): Map<string, number> {
  const numbers = new Map<string, number>();
  for (const place of Object.keys(parts).map(Number).sort((a, b) => a - b)) {
    for (const id of parts[place]) if (!numbers.has(id)) numbers.set(id, numbers.size + 1);
  }
  return numbers;
}

// The page's numbers, with this part's ids registered under its place while it is on the page.
export function usePageNumbers(place: number, ids: string[]): Map<string, number> {
  const key = ids.join("\n");
  useEffect(() => {
    registered.set((parts) => ({ ...parts, [place]: key ? key.split("\n") : [] }));
    return () =>
      registered.set((parts) => {
        const rest = { ...parts };
        delete rest[place];
        return rest;
      });
  }, [place, key]);
  const parts = useStore(registered);
  // Before the effect has run, this part's own ids count after those already registered.
  return useMemo(() => numbersFrom({ ...parts, [place]: key ? key.split("\n") : [] }), [parts, place, key]);
}

// The page's numbers of the drawer claim's sources as they stand, in their order, leaving out any the page has not
// numbered (ticket 60: a claim with two records ends with both numbers).
export function useMarkerNumbers(ids: string[]): number[] {
  const parts = useStore(registered);
  const numbers = numbersFrom(parts);
  return ids.map((id) => numbers.get(id)).filter((n): n is number => n !== undefined);
}
