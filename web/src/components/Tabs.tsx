// Tabs on a light surface (DESIGN.md section 5): 16 px bold, five at most, the selected one
// with a 3 px primary underline. They are links in a nav with aria-current, because each one
// changes the address (the briefs for tickets 10 and 16 settled this). The navy bar's tabs
// are in TopNav, with a white underline.
//
// The tabs never wrap. When the row is wider than its column, as five section tabs are below
// 48rem, it scrolls sideways inside its own strip, and the hairline runs under the whole
// strip. The selected tab starts in the middle of the strip, so a reader sees it. Each side
// with more tabs fades out over 32 px (the tab-strip utility in app.css), so a reader can tell
// the row goes on even when a gap falls at the edge. The strip pads itself by 4 px on every
// side, and takes the 4 px back with a negative margin, so a focus ring (2 px at a 2 px
// offset) is never clipped and the tabs keep their place on the page. A tab that gets focus
// scrolls clear of the fade, ring and all. The strip does this itself, because Chrome does not
// scroll to a focused link that is already partly in view.
import { useLayoutEffect, useRef, type ReactNode } from "react";
import { cx } from "../lib/cx";

export type TabLink = { key: string; label: ReactNode; href: string; current?: boolean };

// DESIGN.md allows five tabs at most. A sixth is a mistake in the screen, so development
// builds stop on it rather than hide a tab; production shows every tab it is given.
export const MOST_TABS = 5;

export function Tabs({ label, tabs }: { label: string; tabs: TabLink[] }) {
  if (import.meta.env.DEV && tabs.length > MOST_TABS) {
    throw new Error(`Tabs got ${tabs.length} tabs, but DESIGN.md section 5 allows ${MOST_TABS} at most.`);
  }
  const strip = useRef<HTMLUListElement>(null);
  const current = tabs.find((tab) => tab.current)?.key;

  // Before the first paint, and again when the strip changes width (a phone turned on its
  // side), put the selected tab in the middle of the strip. A row that fits does not move.
  useLayoutEffect(() => {
    const row = strip.current;
    if (!row) return;
    const center = () => {
      const tab = row.querySelector<HTMLElement>("[aria-current=page]");
      if (tab) reveal(row, tab, "center");
      markEdges(row);
    };
    center();
    const observer = new ResizeObserver(center);
    observer.observe(row);
    return () => observer.disconnect();
  }, [current]);

  return (
    <nav aria-label={label} className="border-b border-line">
      <ul
        ref={strip}
        data-tab-strip
        onFocus={(event) => {
          const tab = (event.target as HTMLElement).closest("a");
          if (tab) reveal(event.currentTarget, tab, "whole");
        }}
        onScroll={(event) => markEdges(event.currentTarget)}
        className="tab-strip -mx-1 -my-1 flex gap-x-6 p-1"
      >
        {tabs.map((tab) => (
          <li key={tab.key} className="shrink-0">
            <a
              href={tab.href}
              aria-current={tab.current ? "page" : undefined}
              className={cx(
                "relative flex h-11 items-center whitespace-nowrap text-body font-bold transition-paint duration-150",
                "after:absolute after:inset-x-0 after:bottom-0 after:h-[3px] after:transition-paint after:duration-150",
                tab.current
                  ? "text-ink-heading after:bg-primary"
                  : "text-ink-muted hover:text-ink-heading hover:after:bg-line-strong",
              )}
            >
              {tab.label}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}

// The width of the fade on a side with more tabs (--tab-fade in app.css). A focused tab keeps
// this much room on each side; at the two ends of the row there is no fade, and the strip's
// own 4 px padding holds the focus ring.
const FADE = 32;

// Scroll the strip sideways so the tab is in its middle ("center"), or so the tab and its
// focus ring are clear of the fades ("whole"). A row that fits its column never moves.
function reveal(row: HTMLElement, tab: HTMLElement, how: "center" | "whole") {
  if (row.scrollWidth <= row.clientWidth) return;
  const rowBox = row.getBoundingClientRect();
  const tabBox = tab.getBoundingClientRect();
  if (how === "center") {
    row.scrollLeft += tabBox.left + tabBox.width / 2 - (rowBox.left + rowBox.width / 2);
  } else if (tabBox.left - FADE < rowBox.left) {
    row.scrollLeft -= rowBox.left - (tabBox.left - FADE);
  } else if (tabBox.right + FADE > rowBox.right) {
    row.scrollLeft += tabBox.right + FADE - rowBox.right;
  }
  markEdges(row);
}

// Tell the tab-strip utility which sides have more tabs out of sight.
function markEdges(row: HTMLElement) {
  const start = row.scrollLeft > 1;
  const end = row.scrollLeft + row.clientWidth < row.scrollWidth - 1;
  row.dataset.more = start && end ? "both" : start ? "start" : end ? "end" : "none";
}
