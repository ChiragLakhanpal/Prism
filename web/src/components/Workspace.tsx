// The workspace layout (DESIGN.md section 4, Page layouts, Workspace; ticket 95), for pages read top to bottom while
// sources open: Home, the package workspace, a planned package, a draft and a lesson's review page.
//
// From a frame of 1200 px (the window less the sidebar, @container frame) the work (an answer panel, the page head and
// the zones) takes columns 1 to 7 and the side panel columns 9 to 12, both measured on the frame. The evidence drawer
// opens into columns 8 to 12: the work keeps its place and width, the drawer fills from the work's end plus a gutter to
// the window's edge, 384 to 600 px, and the side panel hides (app.css, "The workspace layout"). The side panel sticks
// 24 px under the bar. Below that frame the page is one column, and the side panel's content goes where the page says:
// folded into the head (fold "head": an object's facts become the page head's facts line, and the panel is not drawn)
// or after the work (fold "after", as Home's side panels do). The DOM keeps the reading order either way: a panel that
// folds into the head comes before the zones, and one that follows the work comes after them.
import type { ReactNode } from "react";
import { cx } from "../lib/cx";

export function Workspace({
  answer,
  head,
  side,
  fold = "after",
  children,
}: {
  // The answer to a question asked from the box, above the page head.
  answer?: ReactNode;
  head: ReactNode;
  side?: ReactNode;
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
        // From a frame of 75rem: columns 9 to 12 beside the answer, the head and the zones, 24 px under the bar.
        "@xl/frame:col-span-4 @xl/frame:col-start-9 @xl/frame:row-span-3 @xl/frame:row-start-1",
        "@xl/frame:sticky @xl/frame:top-[calc(var(--frame-top)+1.5rem)] @xl/frame:mt-0 @xl/frame:block @xl/frame:self-start",
      )}
    >
      {side}
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
