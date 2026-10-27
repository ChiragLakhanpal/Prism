// Where a focused or linked-to element lands under the parts that stick (DESIGN.md section 10; ticket 94). The frame
// owns it, in one hook: from 1024 px the bar sticks at the top of the window, a page head that holds the page's
// primary action may stick under it, and a bar such as the draft bar may stick to the window's foot. The hook keeps the
// document's scroll padding at the bar plus any sticky head, plus 8 px, and at any sticky foot plus 8 px, so the
// browser never leaves a focused element under them (WCAG 2.4.11).
//
// A page marks those parts, and nothing else: data-sticky="top" on a head, data-sticky="bottom" on a foot. Whether a
// part sticks now is its own computed position, since each sticks only where its page area or the window is wide or
// tall enough, and the evidence drawer narrows the page area. The same paddings go to --sticky-top and --sticky-bottom
// while such a part sticks, which shift the scroll margins of the controls inside it (app.css), so the Tab key does not
// scroll the page to bring a control in a stuck part out of that part's own padding.
import { useLayoutEffect, type RefObject } from "react";

// The space a focused element keeps from the edge of a part that sticks.
export const STICKY_GAP = 8;

const sticks = (element: HTMLElement) => getComputedStyle(element).position === "sticky";

// The tallest part on that edge that sticks now, or null when none does.
function stuckHeight(parts: HTMLElement[]): number | null {
  const stuck = parts.filter(sticks).map((part) => part.offsetHeight);
  return stuck.length ? Math.max(...stuck) : null;
}

export function useStickyPadding(page: RefObject<HTMLElement | null>) {
  useLayoutEffect(() => {
    const within = page.current;
    if (!within) return;
    const root = document.documentElement;
    let watched: HTMLElement[] = [];
    const resized = new ResizeObserver(() => update());
    const update = () => {
      const parts = [...within.querySelectorAll<HTMLElement>("[data-sticky]")];
      if (parts.length !== watched.length || parts.some((part, index) => part !== watched[index])) {
        resized.disconnect();
        for (const part of parts) resized.observe(part);
        watched = parts;
      }
      // The bar sticks from 1024 px, where frame-top is its height; below, it scrolls away and frame-top is 0.
      const bar = parseFloat(getComputedStyle(root).getPropertyValue("--frame-top")) || 0;
      const head = stuckHeight(parts.filter((part) => part.dataset.sticky === "top"));
      const foot = stuckHeight(parts.filter((part) => part.dataset.sticky === "bottom"));
      const top = bar > 0 || head !== null ? bar + (head ?? 0) + STICKY_GAP : 0;
      const bottom = foot !== null ? foot + STICKY_GAP : 0;
      root.style.scrollPaddingTop = top ? `${top}px` : "";
      root.style.scrollPaddingBottom = bottom ? `${bottom}px` : "";
      if (head !== null) root.style.setProperty("--sticky-top", `${top}px`);
      else root.style.removeProperty("--sticky-top");
      if (foot !== null) root.style.setProperty("--sticky-bottom", `${bottom}px`);
      else root.style.removeProperty("--sticky-bottom");
    };
    update();
    // A part mounts, unmounts, or changes the classes that make it stick; the window's size changes where the bar and
    // the parts stick.
    const changed = new MutationObserver(update);
    changed.observe(within, { childList: true, subtree: true, attributes: true, attributeFilter: ["class", "data-sticky"] });
    window.addEventListener("resize", update);
    return () => {
      changed.disconnect();
      resized.disconnect();
      window.removeEventListener("resize", update);
      root.style.scrollPaddingTop = "";
      root.style.scrollPaddingBottom = "";
      root.style.removeProperty("--sticky-top");
      root.style.removeProperty("--sticky-bottom");
    };
  }, [page]);
}
