// Fact table (DESIGN.md section 5; the 21 brief, sections 3.1 and 10): a Table with no count line, for a
// group of facts such as a project's dates. Its title is a noun in the title token, because it lists facts
// rather than stating a finding. Three columns: the fact's label as the row header, its value (with the
// units in the column's head), and its source, with a citation marker. The header row is surface-2.
//
// Below 768 px each row stacks: the label in caption, the value in body, the source in caption. The table
// keeps explicit ARIA roles (table, row, columnheader, rowheader, cell), because a table laid out as blocks
// loses them in some browsers. While it loads, the real title and header stand over skeleton rows 48 px
// tall, as many as the populated table has, so nothing moves when the facts arrive.
import { createElement, type ReactNode } from "react";
import { copy } from "../copy";
import { cx } from "../lib/cx";
import { Fill } from "./Fill";
import { LoadingLabel, SkeletonLine } from "./Skeleton";

export type FactRow = {
  key: string;
  label: ReactNode;
  value: ReactNode;
  // A caption under the value, such as why a category stands in for a risk rating.
  note?: ReactNode;
  source: ReactNode;
};

// The table's three columns: 38, 24 and 38 percent, as the brief sets them; and in a frame of 45rem or more,
// as the Summary's 7 columns are at 1440 px, 33, 31 and 36, so a rating such as "Moderately Unsatisfactory"
// and a source such as "Projects API, ISR of Dec 28, 2018" each keep to one line (the 21 critique, round 3,
// item 4). The frame is the section, a size container. The widths sit on the column heads, which are hidden
// below 768 px, where the rows stack.
const WIDTHS = ["w-[38%] @fact-wide/facts:w-[33%]", "w-[24%] @fact-wide/facts:w-[31%]", "w-[38%] @fact-wide/facts:w-[36%]"];
const CELL = "block @md/page:table-cell px-3 @md/page:py-3 align-top";
const STACK = "block @md/page:table-row";

export function FactTable({
  title,
  caption,
  labelHeader,
  valueHeader,
  sourceHeader,
  rows,
  numeric = false,
  loadingRows,
  level = 3,
}: {
  title: ReactNode;
  // The table's name for a screen reader, such as "Dates for Rajasthan Road Sector Modernization".
  caption: ReactNode;
  // The label column's head, read by screen readers only.
  labelHeader: ReactNode;
  // The value column's head, with its units, such as "US$, millions".
  valueHeader: ReactNode;
  sourceHeader: ReactNode;
  rows: FactRow[];
  // The values are numbers: right-aligned in tabular numerals.
  numeric?: boolean;
  // While the facts load: how many skeleton rows stand in for them.
  loadingRows?: number;
  level?: 2 | 3 | 4;
}) {
  const loading = loadingRows !== undefined;
  const value = cx(CELL, "pb-3 text-body text-ink @md/page:pb-3", numeric && "@md/page:text-right @md/page:tabular-nums");
  return (
    <section data-fact-table data-loading={loading || undefined} aria-busy={loading || undefined} className="@container/facts">
      {createElement(`h${level}`, { className: "text-h2 text-ink-heading" }, title)}
      {loading && <LoadingLabel />}
      <div className="mt-2 overflow-hidden rounded-md border border-line bg-surface">
        <table role="table" className="block w-full border-collapse text-small @md/page:table @md/page:table-fixed">
          <caption className="sr-only">{caption}</caption>
          <thead role="rowgroup" className="sr-only @md/page:not-sr-only @md/page:table-header-group @md/page:bg-surface-2">
            <tr role="row" className={STACK}>
              {[labelHeader, valueHeader, sourceHeader].map((head, index) => (
                <th
                  key={index}
                  role="columnheader"
                  scope="col"
                  className={cx(
                    "px-3 py-2 align-bottom font-semibold text-ink-heading",
                    WIDTHS[index],
                    index === 1 && numeric ? "text-right" : "text-left",
                  )}
                >
                  {index === 0 ? <span className="sr-only">{head}</span> : head}
                </th>
              ))}
            </tr>
          </thead>
          <tbody role="rowgroup" className="block @md/page:table-row-group">
            {loading
              ? Array.from({ length: loadingRows }, (_, index) => (
                  <tr key={index} role="row" aria-hidden="true" className={cx(STACK, "border-line py-3 @md/page:h-12 @md/page:py-0", index > 0 && "border-t")}>
                    {[0, 1, 2].map((cell) => (
                      <td key={cell} role="cell" className={cx(CELL, "py-1")}>
                        <SkeletonLine className="text-small" width={cell === 1 && numeric ? "ml-auto w-1/2" : "w-4/5"} />
                      </td>
                    ))}
                  </tr>
                ))
              : rows.map((row, index) => (
                  <tr key={row.key} role="row" data-fact={row.key} className={cx(STACK, "border-line pt-3 @md/page:pt-0", index > 0 && "border-t")}>
                    {/* Each cell's first line is 24 px, the value's, so the three columns share a baseline. */}
                    <th role="rowheader" scope="row" className={cx(CELL, "text-left text-caption font-normal text-ink-muted @md/page:text-small @md/page:leading-6 @md/page:text-ink")}>
                      {row.label}
                      {/* Stacked, the column heads are hidden, so a number's units follow its label. */}
                      {numeric && (
                        <span aria-hidden="true" className="@md/page:hidden">
                          <Fill template={copy.table.stackedUnit} slots={{ unit: valueHeader }} />
                        </span>
                      )}
                    </th>
                    <td role="cell" className={value}>
                      {row.value}
                      {row.note && <span className="mt-1 block text-caption text-ink-muted">{row.note}</span>}
                    </td>
                    <td role="cell" className={cx(CELL, "pb-3 text-caption text-ink-muted tabular-nums @md/page:leading-6")} data-fact-source>
                      {row.source}
                    </td>
                  </tr>
                ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
