// Eight columns (DESIGN.md section 5): columns 1 to 8 of the page's 12-column grid, and the full
// width below the breakpoint. Alerts, empty states and prose keep to them from 1024 px (lg); prose
// also stops at 72 characters. A table keeps to them only from 1200 px (xl), because below that the
// eight columns are narrower than a table's 640 px and a column would scroll out of view. It draws
// nothing of its own, so the pages that use it show it. What a page puts beside the eight columns (the space line,
// ticket 110) takes columns 9 to 12 from the same breakpoint, top-aligned with them, and is not shown below it; both
// sit in the grid's first row, so hiding it moves nothing.
import type { ReactNode } from "react";
import { cx } from "../lib/cx";

// The class names are written out whole, so Tailwind finds them.
const FROM = { lg: "@lg/page:col-span-8", xl: "@xl/page:col-span-8" } as const;
const BESIDE = {
  lg: "hidden @lg/page:col-span-4 @lg/page:col-start-9 @lg/page:block",
  xl: "hidden @xl/page:col-span-4 @xl/page:col-start-9 @xl/page:block",
} as const;

export function EightColumns({
  children,
  className,
  prose = false,
  breakpoint = "lg",
  beside,
}: {
  children: ReactNode;
  className?: string;
  prose?: boolean;
  breakpoint?: keyof typeof FROM;
  beside?: ReactNode;
}) {
  return (
    <div className={cx("layout-grid", className)}>
      <div className={cx("col-span-12 min-w-0", beside != null && "col-start-1 row-start-1", prose && "max-w-[72ch]", FROM[breakpoint])}>{children}</div>
      {beside != null && <div className={cx("row-start-1 min-w-0", BESIDE[breakpoint])}>{beside}</div>}
    </div>
  );
}
