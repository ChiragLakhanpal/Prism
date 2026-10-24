// Eight columns (DESIGN.md section 5): columns 1 to 8 of the page's 12-column grid, and the full
// width below the breakpoint. Alerts, empty states and prose keep to them from 1024 px (lg); prose
// also stops at 72 characters. A table keeps to them only from 1200 px (xl), because below that the
// eight columns are narrower than a table's 640 px and a column would scroll out of view. It draws
// nothing of its own, so the pages that use it show it.
import type { ReactNode } from "react";
import { cx } from "../lib/cx";

// The class names are written out whole, so Tailwind finds them.
const FROM = { lg: "lg:col-span-8", xl: "xl:col-span-8" } as const;

export function EightColumns({
  children,
  className,
  prose = false,
  breakpoint = "lg",
}: {
  children: ReactNode;
  className?: string;
  prose?: boolean;
  breakpoint?: keyof typeof FROM;
}) {
  return (
    <div className={cx("layout-grid", className)}>
      <div className={cx("col-span-12 min-w-0", prose && "max-w-[72ch]", FROM[breakpoint])}>{children}</div>
    </div>
  );
}
