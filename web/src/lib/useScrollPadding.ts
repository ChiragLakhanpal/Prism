// A page whose header sticks keeps the document's scroll padding at the header's height plus a gap,
// so a focused element is never hidden under it (DESIGN.md section 10). The header sticks only from
// a breakpoint, so below it the padding is cleared. Check a plan's header sticks from 64rem with an
// 8 px gap, and the package workspace's from 48rem with 16 px (the 10 and 12 briefs).
import { useEffect, type RefObject } from "react";

export function useScrollPadding(
  header: RefObject<HTMLElement | null>,
  active: boolean,
  { from, gap }: { from: "48rem" | "64rem"; gap: number },
) {
  useEffect(() => {
    const element = header.current;
    if (!element || !active) return;
    const wide = window.matchMedia(`(width >= ${from})`);
    const update = () => {
      document.documentElement.style.scrollPaddingTop = wide.matches ? `${element.offsetHeight + gap}px` : "";
    };
    update();
    const observer = new ResizeObserver(update);
    observer.observe(element);
    wide.addEventListener("change", update);
    return () => {
      observer.disconnect();
      wide.removeEventListener("change", update);
      document.documentElement.style.scrollPaddingTop = "";
    };
  }, [header, active, from, gap]);
}
