// The workspace layout (DESIGN.md section 4, Page layouts, Workspace; ticket 95), for pages read top to bottom while
// sources open: Home, the package workspace, a planned package, a draft and a lesson's review page.
//
// From a frame of 1200 px (the window less the sidebar, @container frame) the work (an answer panel, the page head and
// the zones) takes columns 1 to 7 and the side panel columns 9 to 12, both measured on the frame. The evidence drawer
// opens into columns 8 to 12: the work keeps its place and width, the drawer fills from the work's end plus a gutter to
// the window's edge, 384 to 600 px, and the side panel hides (app.css, "The workspace layout"). The side panel sticks
// 24 px under the bar, or, when the page gives the column a part to stick after it (sideSticky), only that part sticks
// and the panel scrolls with the page (ticket 130, the design lead's Option W2). Below that frame the page is one column, and the side panel's content goes where the page says:
// folded into the head (fold "head": an object's facts become the page head's facts line, and the panel is not drawn)
// or after the work (fold "after", as Home's side panels do). The DOM keeps the reading order either way: a panel that
// folds into the head comes before the zones, and one that follows the work comes after them.
import type { ReactNode } from "react";
import { cx } from "../lib/cx";

export function Workspace({
  answer,
  head,
  side,
  sideSticky,
  fold = "after",
  children,
}: {
  // The answer to a question asked from the box, above the page head.
  answer?: ReactNode;
  head: ReactNode;
  side?: ReactNode;
  // What the side column holds under its panel, 16 px down, which sticks 24 px under the bar for the rest of the page
  // while the window is at least 45rem tall, so all of it stays in view (app.css, "The workspace layout"). The page
  // passes it only from a frame of 75rem, where the side column shows: the package workspace's step tracker.
  sideSticky?: ReactNode;
  fold?: "head" | "after";
  // The zones.
  children: ReactNode;
}) {
  const slot = side != null && (
    <div
      data-side-slot
      data-fold={fold}
      className={cx(
        "col-span-12 min-w-0",
        fold === "head" ? "hidden" : "mt-8",
        // From a frame of 75rem: columns 9 to 12 beside the answer, the head and the zones.
        "@xl/frame:col-span-4 @xl/frame:col-start-9 @xl/frame:row-span-3 @xl/frame:row-start-1 @xl/frame:mt-0 @xl/frame:block",
        // The whole panel sticks 24 px under the bar; with a part that sticks after it, the slot spans the work's
        // height instead, so that part sticks for the rest of the page while the panel scrolls with it (ticket 130).
        sideSticky == null ? "@xl/frame:sticky @xl/frame:top-[calc(var(--frame-top)+1.5rem)] @xl/frame:self-start" : "@xl/frame:self-stretch",
      )}
    >
      {side}
      {sideSticky != null && (
        <div data-side-sticky className="mt-4">
          {sideSticky}
        </div>
      )}
    </div>
  );
  return (
    <div data-workspace className="layout-grid">
      {answer != null && (
        <div data-workspace-work className="col-span-12 mb-6 min-w-0 @xl/frame:col-span-7 @xl/frame:col-start-1 @xl/frame:row-start-1">
          {answer}
        </div>
      )}
      <div data-workspace-work className="col-span-12 min-w-0 @xl/frame:col-span-7 @xl/frame:col-start-1 @xl/frame:row-start-2">
        {head}
      </div>
      {fold === "head" && slot}
      <div data-workspace-work data-zones className="col-span-12 mt-8 min-w-0 @xl/frame:col-span-7 @xl/frame:col-start-1 @xl/frame:row-start-3">
        {children}
      </div>
      {fold === "after" && slot}
    </div>
  );
}
