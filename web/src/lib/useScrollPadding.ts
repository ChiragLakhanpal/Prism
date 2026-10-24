// A page whose header sticks keeps the document's scroll padding at the header's height plus a gap,
// so a focused element is never hidden under it (DESIGN.md section 10). A header sticks only when its
// page area is wide enough, and the page area narrows when the evidence drawer opens (ticket 14), so
// the header's own position says whether it sticks; when it does not, the padding is cleared. Check a
// plan's header sticks from a page area of 64rem with an 8 px gap, and the package workspace's from
// 48rem with 16 px (the 10 and 12 briefs). The same padding goes to --sticky-top, which shifts the
// scroll margin of a control in Check a plan's header, such as the draft action (app.css), so Shift+Tab
// into the header does not scroll the page (ticket 35).
import { useEffect, type RefObject } from "react";

export function useScrollPadding(header: RefObject<HTMLElement | null>, active: boolean, { gap }: { gap: number }) {
  useEffect(() => {
    const element = header.current;
    if (!element || !active) return;
    const root = document.documentElement;
    const update = () => {
      const padding = getComputedStyle(element).position === "sticky" ? `${element.offsetHeight + gap}px` : "";
      root.style.scrollPaddingTop = padding;
      root.style.setProperty("--sticky-top", padding);
    };
    update();
    const observer = new ResizeObserver(update);
    observer.observe(element);
    return () => {
      observer.disconnect();
      root.style.scrollPaddingTop = "";
      root.style.removeProperty("--sticky-top");
    };
  }, [header, active, gap]);
}
