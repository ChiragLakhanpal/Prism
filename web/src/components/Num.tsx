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
  formatToolShare,
  formatYear,
  type DateStyle,
  type NumberOptions,
  type ToolShare,
} from "../lib/format";
import { DOTTED_UNDERLINE, Tooltip } from "./Popover";

export type NumValue =
  | { value: number; options?: NumberOptions }
  | { count: number; capital?: boolean }
  | { year: number }
  // today, an ISO date, decides whether a short date needs its year; the browser's date when unset.
  | { date: string; style?: DateStyle; today?: string }
  | { part: number; whole: number; show?: "text" | "count"; style?: "sentence" | "table" }
  // A share a tool rounded, written as it came: the browser divides nothing.
  | { share: ToolShare; style?: "sentence" | "table" }
  // A number or date as a checked answer sentence wrote it: the verifier matched it to a record at
  // that rounding, so it is shown as written (ticket 14).
  | { written: string };

export type NumCheck = {
  // What a tooltip says about where the number came from, from the copy file and the tool.
  tooltip: ReactNode;
  // Opens the rows behind the number, or its definition.
  onOpen?: () => void;
  // Numbers inside an answer leave the tab order to the citation markers beside them.
  tabStop?: boolean;
  // A name that says more than the number, starting with it: "1 of 1 completion reports, for {risk}" (ticket 30).
  name?: string;
};

export function numText(num: NumValue): string {
  if ("written" in num) return num.written;
  if ("value" in num) return formatNumber(num.value, num.options);
  if ("count" in num) return formatCount(num.count, { capital: num.capital });
  if ("year" in num) return formatYear(num.year);
  if ("date" in num) return formatDate(num.date, { style: num.style, today: num.today });
  if ("share" in num) return formatToolShare(num.share, { style: num.style }).text;
  const ratio = formatRatio(num.part, num.whole, { style: num.style });
  return num.show === "count" ? ratio.count : ratio.text;
}

// A number as Num and MeasureNum show it. A share keeps its count and its frequency each on one
// line, so "20 of 21, more than 9 in 10" can break only after the comma. Anything else is its text.
export function numBody(num: NumValue): ReactNode {
  return written(num, numText(num));
}

function written(num: NumValue, text: string): ReactNode {
  if (!("share" in num)) return text;
  const { frequency } = formatToolShare(num.share, { style: num.style });
  if (!frequency || !text.endsWith(frequency)) return text;
  return (
    <>
      <span className="whitespace-nowrap">{text.slice(0, text.length - frequency.length).trimEnd()}</span>{" "}
      <span className="whitespace-nowrap">{frequency}</span>
    </>
  );
}

// NumLines (ticket 27; DESIGN.md section 5, Num): one checkable number on two lines, such as a step's planned date
// over the days it rests on ("Apr 1, 2027" over "28 days after the plan's date"). The lines are given already
// written, each number in them through Num with no check of its own, so one tab stop, one dotted underline and one
// tooltip cover both, and a click opens the rows behind them. The first line may be words instead of a number, as
// "Not dated yet" is before a start date, with the second line's days still under it. With no second line it is one
// checkable line of words with numbers in it, such as the days of a step that needs an earlier step's date. Its
// lines start on the left; className can set them on the right, as the narrow step list does (items-end text-right).
export function NumLines({
  first,
  second,
  check,
  firstClassName,
  secondClassName,
  className = "items-start text-left",
}: {
  first: ReactNode;
  second?: ReactNode;
  check: NumCheck;
  firstClassName?: string;
  secondClassName?: string;
  className?: string;
}) {
  return (
    <Tooltip
      trigger={
        <button
          type="button"
          data-num
          data-num-lines
          tabIndex={check.tabStop === false ? -1 : undefined}
          aria-label={check.name}
          onClick={check.onOpen}
          // One line of caption text keeps a 24 px target (WCAG 2.5.8), centred in it.
          className={cx("group inline-flex max-w-full cursor-pointer flex-col py-0.5 tabular-nums", !second && "min-h-6 justify-center", className)}
        >
          <span className={cx(DOTTED_UNDERLINE, "group-hover:decoration-solid", firstClassName)}>{first}</span>
          {second && <span className={cx(DOTTED_UNDERLINE, "group-hover:decoration-solid", secondClassName)}>{second}</span>}
        </button>
      }
    >
      {check.tooltip}
    </Tooltip>
  );
}

// A date in a sentence ("October 31, 2026", at most 18 characters) never breaks across lines.
const sentenceDate = (num: NumValue) => "date" in num && (num.style ?? "sentence") === "sentence";

// inCaption: a number you can check in caption text, whose line is shorter than the body's, takes 4 px above and
// below instead of 2, so its target stays 24 px tall (DESIGN.md section 10), such as a threshold in the package
// workspace's computed note (ticket 15).
export function Num({ check, className, inCaption = false, ...num }: NumValue & { check?: NumCheck; className?: string; inCaption?: boolean }) {
  const text = numText(num as NumValue);
  const body = written(num as NumValue, text);
  if (!check) {
    return (
      <span data-num className={cx("tabular-nums", sentenceDate(num as NumValue) && "whitespace-nowrap", className)}>
        {body}
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
          aria-label={check.name}
          onClick={check.onOpen}
          className={cx(
            // A button lays out as an inline block, so its padding would make its line taller than the
            // body's 24 px; the negative margin keeps the 28 px hit area inside the line's own height.
            "inline cursor-pointer text-left tabular-nums",
            inCaption ? "-my-1 py-1" : "-my-0.5 py-0.5",
            DOTTED_UNDERLINE,
            className,
          )}
        >
          {body}
        </button>
      }
    >
      {check.tooltip}
    </Tooltip>
  );
}
