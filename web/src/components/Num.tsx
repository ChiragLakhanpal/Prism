// Num: every number Strata shows. It writes the number by DESIGN.md sections 6 and 7 (through
// web/src/lib/format.ts), with tabular numerals, so a ratio under 20 cases can never become a
// percentage. A number with a check is a button with a dotted underline: hover or focus shows
// where it came from, and a click opens its rows or its definition (DESIGN.md section 1:
// every number ends with a source).
import type { ReactNode } from "react";
import { cx } from "../lib/cx";
import {
  formatCount,
  formatDate,
  formatNumber,
  formatRatio,
  formatYear,
  type DateStyle,
  type NumberOptions,
} from "../lib/format";
import { DOTTED_UNDERLINE, Tooltip } from "./Popover";

export type NumValue =
  | { value: number; options?: NumberOptions }
  | { count: number }
  | { year: number }
  // today, an ISO date, decides whether a short date needs its year; the browser's date when unset.
  | { date: string; style?: DateStyle; today?: string }
  | { part: number; whole: number; show?: "text" | "count"; style?: "sentence" | "table" };

export type NumCheck = {
  // What a tooltip says about where the number came from, from the copy file and the tool.
  tooltip: ReactNode;
  // Opens the rows behind the number, or its definition.
  onOpen?: () => void;
  // Numbers inside an answer leave the tab order to the citation markers beside them.
  tabStop?: boolean;
};

export function numText(num: NumValue): string {
  if ("value" in num) return formatNumber(num.value, num.options);
  if ("count" in num) return formatCount(num.count);
  if ("year" in num) return formatYear(num.year);
  if ("date" in num) return formatDate(num.date, { style: num.style, today: num.today });
  const ratio = formatRatio(num.part, num.whole, { style: num.style });
  return num.show === "count" ? ratio.count : ratio.text;
}

export function Num({ check, className, ...num }: NumValue & { check?: NumCheck; className?: string }) {
  const text = numText(num as NumValue);
  if (!check) {
    return (
      <span data-num className={cx("tabular-nums", className)}>
        {text}
      </span>
    );
  }
  return (
    <Tooltip
      trigger={
        <button
          type="button"
          data-num
          tabIndex={check.tabStop === false ? -1 : undefined}
          onClick={check.onOpen}
          className={cx(
            "inline cursor-pointer py-0.5 text-left tabular-nums",
            DOTTED_UNDERLINE,
            className,
          )}
        >
          {text}
        </button>
      }
    >
      {check.tooltip}
    </Tooltip>
  );
}
