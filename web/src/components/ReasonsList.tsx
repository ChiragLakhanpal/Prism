// One group of the Reasons list (DESIGN.md section 5): grouped reasons quoted word for word, built first for section
// 5's rejected bids (ticket 31) and shared with section 1's "Advertised again" block (ticket 28). Its caller draws
// the rows, each an li, and wraps the group in a @container/reasons element, so the heading's count moves under its
// label below 480 px of the group's own width.
//
// The h4 holds the label and "{c} of {n}" in small, with tabular numerals, and hidden words, so it reads "{label}, {c}
// of the {n} packages". The rows come in the caller's order; the first perGroup show, and a flush ghost "Show {n}
// more" shows the rest, then goes, and focus moves to the first row it showed. Hidden rows keep their markers'
// numbers, since the caller numbers every row once per page.
import { useEffect, useRef, useState, type ReactNode } from "react";
import { Button } from "./Button";

export function ReasonGroup({
  headingId,
  label,
  count,
  name,
  note,
  perGroup,
  rows,
  moreLabel,
}: {
  headingId: string;
  label: ReactNode;
  // "{c} of {n}", as the caller's copy writes it.
  count: ReactNode;
  // The heading's whole name, heard by screen readers.
  name: string;
  // A caption under the heading, such as section 5's "Your criteria set this item."
  note?: ReactNode;
  perGroup: number;
  rows: ReactNode[];
  moreLabel: (more: number) => ReactNode;
}) {
  const [all, setAll] = useState(false);
  const list = useRef<HTMLUListElement>(null);
  useEffect(() => {
    if (all) list.current?.children[perGroup]?.querySelector<HTMLElement>("button")?.focus();
  }, [all, perGroup]);
  const more = rows.length - perGroup;
  return (
    <>
      <h4
        id={headingId}
        tabIndex={-1}
        className="flex flex-col text-small font-bold text-ink-heading focus:outline-none @[30rem]/reasons:flex-row @[30rem]/reasons:items-baseline @[30rem]/reasons:justify-between @[30rem]/reasons:gap-4"
      >
        <span aria-hidden="true">{label}</span>
        {/* Under its label, below 480 px of the group's width, the count is a caption; beside it, small at 600 (the 28
            brief, 3.4; ticket 59). */}
        <span
          aria-hidden="true"
          className="text-caption font-normal text-ink-muted tabular-nums @[30rem]/reasons:text-small @[30rem]/reasons:font-semibold @[30rem]/reasons:text-ink"
        >
          {count}
        </span>
        <span className="sr-only">{name}</span>
      </h4>
      {note}
      <ul ref={list} aria-labelledby={headingId} className="mt-2 flex flex-col gap-4 pl-2 @md/page:pl-4">
        {rows.slice(0, all ? rows.length : perGroup)}
      </ul>
      {!all && more > 0 && (
        <div className="mt-2 pl-2 @md/page:pl-4">
          <Button variant="ghost" flush onClick={() => setAll(true)}>
            {moreLabel(more)}
          </Button>
        </div>
      )}
    </>
  );
}
