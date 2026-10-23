// Table (DESIGN.md section 5): a title sentence that states the finding, a count line
// ("Showing 1–20 of 99 sources"), a surface-2 header with units in the column heads, numbers
// right-aligned in tabular numerals, and a source line below. Below 768 px each row becomes a
// card, so nothing scrolls sideways. In a card each column's head sits above its value, and
// every value starts at one left edge: text runs the card's full width, and two or more
// numbers share a grid of 120 px columns, so they sit side by side (the 10 brief's activity
// card).
//
// States, each saying only what is true in it:
// - Ready: the title, the count line, the rows and the source line. A ready table has rows;
//   a screen with none passes the empty state, and development builds stop on the mistake.
// - Loading: skeleton lines where the title, count and source lines go, and skeleton rows under
//   the real column heads. The columns have fixed widths and each skeleton line is one line
//   tall, so nothing moves when the rows arrive. Below 768 px the title's skeleton holds two
//   lines, because a finding sentence wraps there.
// - Empty: only an empty-state card that says, in the first person, what will appear.
// - Error: only an error alert, with "Try again" when the caller can ask again.
// A finding, a count or a source line never sits over rows that are not there.
import { createElement, useId, type ReactNode } from "react";
import { copy } from "../copy";
import { cx } from "../lib/cx";
import { formatNumber } from "../lib/format";
import { Alert } from "./Alert";
import { Button } from "./Button";
import { EmptyState } from "./Card";
import { LoadingLabel, SkeletonLine, SkeletonText } from "./Skeleton";
import { Source } from "./Source";

export type Column = {
  key: string;
  // The header with its unit, such as "Estimated Amount (US$)". A Term can carry its definition.
  header: ReactNode;
  numeric?: boolean;
  // The column's share of the table, as a width class such as "w-2/5". Columns without one
  // share what is left. Fixed widths keep the columns still while the rows load.
  width?: string;
};

export type Row = { id: string; cells: Record<string, ReactNode> };

export type TableState =
  | { status: "ready"; rows: Row[] }
  | { status: "loading"; rows: number }
  | { status: "empty"; title: ReactNode; body: ReactNode; link?: { href: string; text: ReactNode } }
  | { status: "error"; message: ReactNode; onRetry?: () => void };

// What the count line counts: "Showing all 4 activities", or "Showing 1–20 of 99 sources"
// when the rows are one page of more.
export type Count = { noun: string; total: number; from?: number; to?: number };

type Level = 2 | 3 | 4 | 5;

const n = (value: number) => formatNumber(value, { compact: false });

// A card's fields: a grid of 120 px columns that numbers share, with text, or a number with no
// other number beside it, across the full row. Each field sits at the foot of its grid row, as
// the table's heads sit at the foot of the header, so a head that wraps to two lines keeps its
// value level with its neighbor's.
const CARD_FIELDS = "mt-2 grid grid-cols-[repeat(auto-fit,minmax(7.5rem,1fr))] gap-x-4 gap-y-2";
const cardField = (column: Column, shared: boolean) =>
  cx("flex min-w-0 flex-col justify-end", !(column.numeric && shared) && "col-span-full");

function countText({ noun, total, from, to }: Count): string {
  return from !== undefined && to !== undefined && (from > 1 || to < total)
    ? copy.table.showing(n(from), n(to), n(total), noun)
    : copy.table.showingAll(n(total), noun);
}

export function Table({
  title,
  count,
  columns,
  state,
  source,
  rowHeader,
  level = 3,
}: {
  // The finding the rows show, as a sentence.
  title: ReactNode;
  count?: Count;
  columns: Column[];
  state: TableState;
  source?: ReactNode;
  // The column that names each row, used as the card's heading below 768 px.
  rowHeader: string;
  // The title's heading level; each card's heading is one level below it.
  level?: Level;
}) {
  const titleId = useId();
  const countId = useId();

  if (state.status === "empty") {
    return (
      <div data-table="empty">
        <EmptyState level={level} title={state.title} body={state.body} link={state.link} />
      </div>
    );
  }
  if (state.status === "error") {
    return (
      <div data-table="error">
        <Alert
          state="error"
          live="alert"
          action={
            state.onRetry && (
              <Button variant="secondary" onClick={state.onRetry}>
                {copy.answer.tryAgain}
              </Button>
            )
          }
        >
          {state.message}
        </Alert>
      </div>
    );
  }

  if (import.meta.env.DEV && state.status === "ready" && state.rows.length === 0) {
    throw new Error("A ready table needs rows. Pass the empty state instead.");
  }

  const loading = state.status === "loading";
  const rows = state.status === "ready" ? state.rows : [];
  const skeletonRows = Array.from({ length: loading ? state.rows : 0 }, (_, index) => index);
  const align = (column: Column) => (column.numeric ? "text-right" : "text-left");
  const cardHeading = `h${level + 1}`;
  const fields = columns.filter((column) => column.key !== rowHeader);
  // Numbers share the card's grid only when there are two or more of them.
  const shared = fields.filter((column) => column.numeric).length > 1;

  return (
    // The named, focusable scroll region below is the table's one landmark, so this section
    // carries no name of its own.
    <section data-table={state.status} aria-busy={loading || undefined} className="flex flex-col gap-2">
      {loading ? (
        <>
          <LoadingLabel />
          <SkeletonText className="text-title md:hidden" widths={["w-full", "w-3/5"]} />
          <div className="hidden md:block">
            <SkeletonLine className="text-title" width="w-3/5" />
          </div>
          {count && <SkeletonLine className="text-caption" width="w-1/5" />}
        </>
      ) : (
        <>
          {createElement(`h${level}`, { id: titleId, className: "text-title text-ink-heading" }, title)}
          {count && (
            <p id={countId} className="text-caption text-ink-muted" data-numbers>
              {countText(count)}
            </p>
          )}
        </>
      )}

      {/* From 768 px, a table. In a narrow column it scrolls inside its frame, which then takes
          focus so a keyboard can scroll it too. */}
      <div
        tabIndex={loading ? undefined : 0}
        role={loading ? undefined : "region"}
        aria-labelledby={loading ? undefined : titleId}
        aria-hidden={loading || undefined}
        className="hidden overflow-x-auto rounded-md border border-line bg-surface md:block"
      >
        <table
          aria-labelledby={loading ? undefined : titleId}
          aria-describedby={count && !loading ? countId : undefined}
          className="w-full min-w-[40rem] table-fixed border-collapse text-small"
        >
          <thead className="bg-surface-2">
            <tr>
              {columns.map((column) => (
                <th
                  key={column.key}
                  scope="col"
                  className={cx("px-3 py-2 align-bottom font-semibold text-ink-heading", align(column), column.width)}
                >
                  {column.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {skeletonRows.map((index) => (
              <tr key={index} className="border-t border-line">
                {columns.map((column) => (
                  <td key={column.key} className="px-3 py-2">
                    <SkeletonLine width={column.numeric ? "ml-auto w-1/2" : "w-4/5"} />
                  </td>
                ))}
              </tr>
            ))}
            {rows.map((row) => (
              <tr key={row.id} className="border-t border-line align-top">
                {columns.map((column) =>
                  column.key === rowHeader ? (
                    <th key={column.key} scope="row" className={cx("px-3 py-2 font-normal wrap-break-word text-ink", align(column))}>
                      {row.cells[column.key]}
                    </th>
                  ) : (
                    <td key={column.key} className={cx("px-3 py-2 wrap-break-word text-ink", align(column))}>
                      {row.cells[column.key]}
                    </td>
                  ),
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Below 768 px, one card per row: the row's name as its heading, then each column's head
          above its value, every value from one left edge. A loading card has the same lines. */}
      <ul aria-labelledby={loading ? undefined : titleId} aria-hidden={loading || undefined} className="flex flex-col gap-3 md:hidden">
        {skeletonRows.map((index) => (
          <li key={index} className="rounded-md border border-line bg-surface p-4">
            <SkeletonLine className="text-small" width="w-3/5" />
            <dl className={CARD_FIELDS}>
              {fields.map((column) => (
                <div key={column.key} className={cardField(column, shared)}>
                  <dt className="text-caption text-ink-muted">{column.header}</dt>
                  <dd>
                    <SkeletonLine className="text-small" width={column.numeric ? "w-1/2" : "w-4/5"} />
                  </dd>
                </div>
              ))}
            </dl>
          </li>
        ))}
        {rows.map((row) => (
          <li key={row.id} className="rounded-md border border-line bg-surface p-4">
            {createElement(cardHeading, { className: "text-small font-semibold wrap-break-word text-ink-heading" }, row.cells[rowHeader])}
            <dl className={CARD_FIELDS} data-numbers>
              {fields.map((column) => (
                <div key={column.key} data-card-field={column.numeric ? "number" : "text"} className={cardField(column, shared)}>
                  <dt className="text-caption text-ink-muted">{column.header}</dt>
                  <dd className="text-small wrap-break-word text-ink">{row.cells[column.key]}</dd>
                </div>
              ))}
            </dl>
          </li>
        ))}
      </ul>

      {source && (loading ? <SkeletonLine className="text-caption" width="w-2/5" /> : <Source>{source}</Source>)}
    </section>
  );
}
