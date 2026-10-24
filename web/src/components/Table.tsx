// Table (DESIGN.md section 5): a title sentence that states the finding, a count line
// ("Showing 1–20 of 99 sources"), a surface-2 header with units in the column heads, numbers
// right-aligned in tabular numerals, and a source line below. Below 768 px each row becomes a
// card, so nothing scrolls sideways. A table whose columns need more than the 672 px a 768 px
// screen leaves, such as ticket 10's plan check, sets cardsBelow="lg" and becomes cards below
// 1024 px instead. In a card each column's head sits above its value, and
// every value starts at one left edge: text runs the card's full width, and two or more
// numbers and short values share a grid of 120 px columns, so they sit side by side (the 10
// brief's activity card).
//
// States, each saying only what is true in it:
// - Ready: the title, the count line, the rows and the source line. A ready table has rows;
//   a screen with none passes the empty state, and development builds stop on the mistake.
// - Loading: skeleton lines where the title, count and source lines go, and skeleton rows under
//   the real column heads. The columns have fixed widths and each skeleton line is one line
//   tall, so nothing moves when the rows arrive. Below 768 px the title's skeleton holds two
//   lines, because a finding sentence wraps there, unless the title is a short name.
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
  // A short value, such as a date, a country or a status, which shares a card's grid with the
  // numbers instead of taking the card's full width.
  short?: boolean;
  // The head a card shows when the table's head carries a definition under its name: the name
  // alone, so the definition is not repeated in every card. The table's cardsNote then says it once.
  cardHeader?: ReactNode;
};

export type Row = { id: string; cells: Record<string, ReactNode> };

export type TableState =
  | { status: "ready"; rows: Row[] }
  // header: the row header cell's skeleton when that cell holds more than one line, such as a
  // project ID over its name, so each skeleton row is as tall as the row it stands for.
  // shortTitle: the title is a name that fits one line at every width, such as "All projects",
  // so its skeleton is one line below 768 px too.
  | { status: "loading"; rows: number; header?: ReactNode; shortTitle?: boolean }
  | { status: "empty"; title: ReactNode; body: ReactNode; link?: { href: string; text: ReactNode } }
  | { status: "error"; message: ReactNode; onRetry?: () => void };

// What the count line counts: "Showing all 4 activities", or "Showing 1–20 of 99 sources"
// when the rows are one page of more.
// one is the noun for a single row ("version"), so one row reads "Showing 1 version".
export type Count = { noun: string; one?: string; total: number; from?: number; to?: number };

type Level = 2 | 3 | 4 | 5;

// Where the rows turn into cards. The class names are written out whole, so Tailwind finds them.
export type CardsBelow = "md" | "lg";
const SHOW: Record<CardsBelow, { table: string; cards: string }> = {
  md: { table: "@md/page:block", cards: "@md/page:hidden" },
  lg: { table: "@lg/page:block", cards: "@lg/page:hidden" },
};
// The plan check (web/src/components/PlanCheck.tsx) draws its own rows and cards, at the same
// breakpoint as cardsBelow="lg".
export const CARD_BREAKPOINTS = SHOW;

const n = (value: number) => formatNumber(value, { compact: false });

// A card's fields: a grid of 120 px columns that numbers and short values share, with longer
// text, or a number with nothing beside it, across the full row. Each field sits at the foot of
// its grid row, as the table's heads sit at the foot of the header, so a head that wraps to two
// lines keeps its value level with its neighbor's. The plan check's activity cards
// (web/src/components/PlanCheck.tsx) use the same grid and fields.
export const CARD_FIELDS = "grid grid-cols-[repeat(auto-fit,minmax(7.5rem,1fr))] gap-x-4 gap-y-2";
export const CARD_FIELD = "flex min-w-0 flex-col justify-end";
const sharesGrid = (column: Column) => Boolean(column.numeric || column.short);
const cardField = (column: Column, shared: boolean) => cx(CARD_FIELD, !(sharesGrid(column) && shared) && "col-span-full");

function countText({ noun, one, total, from, to }: Count): string {
  if (total === 1 && one) return copy.table.showingOne(one);
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
  cardsBelow = "md",
  cardsNote,
}: {
  // The finding the rows show, as a sentence.
  title: ReactNode;
  count?: Count;
  columns: Column[];
  state: TableState;
  source?: ReactNode;
  // The column that names each row, used as the card's heading when the rows are cards.
  rowHeader: string;
  // The title's heading level; each card's heading is one level below it.
  level?: Level;
  // Below which breakpoint the rows become cards: md (768 px, the default) or lg (1024 px).
  cardsBelow?: CardsBelow;
  // A sentence that ends the count line's row only while the rows are cards, such as the definition
  // a column's head carries in the table, said once there because cards have no column heads.
  cardsNote?: ReactNode;
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
  const skeletonHeader = loading ? state.header : undefined;
  const align = (column: Column) => (column.numeric ? "text-right" : "text-left");
  const cardHeading = `h${level + 1}`;
  const fields = columns.filter((column) => column.key !== rowHeader);
  // Numbers and short values share the card's grid only when there are two or more of them.
  const shared = fields.filter(sharesGrid).length > 1;

  return (
    // The named, focusable scroll region below is the table's one landmark, so this section
    // carries no name of its own.
    <section data-table={state.status} aria-busy={loading || undefined} className="flex flex-col gap-2">
      {loading ? (
        <>
          <LoadingLabel />
          {state.shortTitle ? (
            <SkeletonLine className="text-title" width="w-2/5" />
          ) : (
            <>
              <SkeletonText className="text-title @md/page:hidden" widths={["w-full", "w-3/5"]} />
              <div className="hidden @md/page:block">
                <SkeletonLine className="text-title" width="w-3/5" />
              </div>
            </>
          )}
          {count && <SkeletonLine className="text-caption" width="w-1/5" />}
        </>
      ) : (
        <>
          {createElement(`h${level}`, { id: titleId, className: "text-title text-ink-heading" }, title)}
          {count && (
            // The count, and the cards' note as its own element at the row's end, which wraps to a line
            // of its own when the two don't fit (DESIGN.md section 5, the Plan check table).
            <div className="flex flex-wrap items-baseline justify-between gap-x-4 text-caption text-ink-muted">
              <p id={countId} data-numbers>
                {countText(count)}
              </p>
              {cardsNote && (
                <p className={SHOW[cardsBelow].cards} data-cards-note>
                  {cardsNote}
                </p>
              )}
            </div>
          )}
        </>
      )}

      {/* From 768 px (or 1024 px with cardsBelow="lg"), a table. In a narrow column it scrolls
          inside its frame, which then takes focus so a keyboard can scroll it too. */}
      <div
        tabIndex={loading ? undefined : 0}
        role={loading ? undefined : "region"}
        aria-labelledby={loading ? undefined : titleId}
        aria-hidden={loading || undefined}
        data-table-view="table"
        className={cx("hidden overflow-x-auto rounded-md border border-line bg-surface", SHOW[cardsBelow].table)}
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
                  <td key={column.key} className="px-3 py-2 align-top">
                    {column.key === rowHeader && skeletonHeader ? (
                      skeletonHeader
                    ) : (
                      <SkeletonLine width={column.numeric ? "ml-auto w-1/2" : "w-4/5"} />
                    )}
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

      {/* Below the breakpoint, one card per row: the row's name as its heading, then each
          column's head above its value, every value from one left edge. A loading card has the
          same lines. */}
      <ul
        aria-labelledby={loading ? undefined : titleId}
        aria-hidden={loading || undefined}
        data-table-view="cards"
        className={cx("flex flex-col gap-3", SHOW[cardsBelow].cards)}
      >
        {skeletonRows.map((index) => (
          <li key={index} className="rounded-md border border-line bg-surface p-4">
            {skeletonHeader ? <div className="text-small">{skeletonHeader}</div> : <SkeletonLine className="text-small" width="w-3/5" />}
            <dl className={cx("mt-2", CARD_FIELDS)}>
              {fields.map((column) => (
                <div key={column.key} className={cardField(column, shared)}>
                  <dt className="text-caption text-ink-muted">{column.cardHeader ?? column.header}</dt>
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
            <dl className={cx("mt-2", CARD_FIELDS)} data-numbers>
              {fields.map((column) => (
                <div key={column.key} data-card-field={column.numeric ? "number" : "text"} className={cardField(column, shared)}>
                  <dt className="text-caption text-ink-muted">{column.cardHeader ?? column.header}</dt>
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
