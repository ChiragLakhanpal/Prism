// Whether the page area is at least this wide, in rem: the width the @container/page queries test (Frame.tsx's
// page column). It narrows when the evidence drawer opens (ticket 14). A page uses it only where the DOM order
// itself must change with the width, as the judging page's grade buttons do (the 32 brief, section 2.9): below
// a 64rem page area they come right after the passage, and from it they sit last, in a bar pinned to the bottom.
// Styling alone stays with the container queries.
import { useLayoutEffect, useState, type RefObject } from "react";

export function usePageAtLeast(inside: RefObject<HTMLElement | null>, rem: number): boolean {
  const [wide, setWide] = useState(false);
  useLayoutEffect(() => {
    const page = inside.current?.closest<HTMLElement>("[data-page-column]") ?? null;
    if (!page) return;
    const update = () => {
      const root = parseFloat(getComputedStyle(document.documentElement).fontSize) || 16;
      setWide(page.clientWidth >= rem * root);
    };
    update();
    const watch = new ResizeObserver(update);
    watch.observe(page);
    return () => watch.disconnect();
  }, [inside, rem]);
  return wide;
}
