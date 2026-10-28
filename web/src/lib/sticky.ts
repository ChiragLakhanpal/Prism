// Where a focused or linked-to element lands under the parts that stick (DESIGN.md section 10; ticket 94). The frame
// owns it, in one hook: from 1024 px the bar sticks at the top of the window, a page head that holds the page's
// primary action may stick under it, a bar such as the draft bar may stick to the window's foot, and the ask bar, which
// holds the one box, always sticks at the foot (ticket 113). The hook keeps the document's scroll padding at the bar plus
// any sticky head, plus 8 px, and at the parts that stick at the foot plus 8 px, so the browser never leaves a focused
// element under them (WCAG 2.4.11).
//
// A page marks those parts, and nothing else: data-sticky="top" on a head, data-sticky="bottom" on a foot. Whether a
// part sticks now is its own computed position, since each sticks only where its page area or the window is wide or
// tall enough, and the evidence drawer narrows the page area. The same paddings go to --sticky-top and --sticky-bottom
// while such a part sticks, which shift the scroll margins of the controls inside it (app.css), so the Tab key does not
// scroll the page to bring a control in a stuck part out of that part's own padding.
//
// The ask bar floats above a page's own foot bar: where the draft bar or the grade bar sticks, the hook writes that
// bar's height as --sticky-foot, which the ask bar sticks above (app.css), and the bottom padding counts both. While
// focus is in the ask bar, the padding leaves it out: the box itself has focus then, and a browser scrolls a text
// field's caret out of the scroll padding as you type, which would carry the page to its end, since the ask bar always
// sits inside its own padding.
import { useLayoutEffect, type RefObject } from "react";

// The space a focused element keeps from the edge of a part that sticks.
export const STICKY_GAP = 8;

// The frame's ask bar (Frame.tsx), the one part at the foot that is not a page's own.
const ASK_BAR = "data-box-band";

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
    // Whether focus is in the ask bar's box.
    let typing = false;
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
      const feet = parts.filter((part) => part.dataset.sticky === "bottom");
      // The page's own foot bar, and the ask bar that floats above it.
      const foot = stuckHeight(feet.filter((part) => !part.hasAttribute(ASK_BAR)));
      const ask = typing ? null : stuckHeight(feet.filter((part) => part.hasAttribute(ASK_BAR)));
      const top = bar > 0 || head !== null ? bar + (head ?? 0) + STICKY_GAP : 0;
      const bottom = foot !== null || ask !== null ? (foot ?? 0) + (ask ?? 0) + STICKY_GAP : 0;
      root.style.scrollPaddingTop = top ? `${top}px` : "";
      root.style.scrollPaddingBottom = bottom ? `${bottom}px` : "";
      if (head !== null) root.style.setProperty("--sticky-top", `${top}px`);
      else root.style.removeProperty("--sticky-top");
      if (bottom) root.style.setProperty("--sticky-bottom", `${bottom}px`);
      else root.style.removeProperty("--sticky-bottom");
      if (foot !== null) root.style.setProperty("--sticky-foot", `${foot}px`);
      else root.style.removeProperty("--sticky-foot");
    };
    update();
    // A part mounts, unmounts, or changes the classes that make it stick; the window's size changes where the bar and
    // the parts stick.
    const changed = new MutationObserver(update);
    changed.observe(within, { childList: true, subtree: true, attributes: true, attributeFilter: ["class", "data-sticky"] });
    window.addEventListener("resize", update);
    // Set at once, in the focus event, since the browser brings a newly focused element into view right after it.
    const focusMoved = (event: FocusEvent) => {
      const to = event.type === "focusin" ? event.target : event.relatedTarget;
      const now = to instanceof Element && to.closest(`[${ASK_BAR}]`) !== null;
      if (now === typing) return;
      typing = now;
      update();
    };
    document.addEventListener("focusin", focusMoved);
    document.addEventListener("focusout", focusMoved);
    return () => {
      changed.disconnect();
      resized.disconnect();
      window.removeEventListener("resize", update);
      document.removeEventListener("focusin", focusMoved);
      document.removeEventListener("focusout", focusMoved);
      root.style.scrollPaddingTop = "";
      root.style.scrollPaddingBottom = "";
      root.style.removeProperty("--sticky-top");
      root.style.removeProperty("--sticky-bottom");
      root.style.removeProperty("--sticky-foot");
    };
  }, [page]);
}
