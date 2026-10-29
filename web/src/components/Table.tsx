// Table (DESIGN.md section 5): a title sentence that states the finding, a count line
// ("Showing 1 to 20 of 99 sources."), a surface-2 header with units in the column heads, numbers
// right-aligned in tabular numerals, and a source line below. Below 768 px each row becomes a
// card, so nothing scrolls sideways. A table whose columns need more than the 672 px a 768 px
// screen leaves, such as ticket 10's plan check, sets cardsBelow="lg" and becomes cards below
// 1024 px instead. A table that keeps to columns 1 to 8, whose columns need more room than they
// leave at 1200 px, such as the past range's, sets cardsBelow="fit" and reads its own width
// instead of the page area's. In a card each column's head sits above its value, and
// every value starts at one left edge: text runs the card's full width, and two or more
// numbers and short values share a grid of 120 px columns, so they sit side by side (the 10
// brief's activity card). A list in a Task zone panel, as All projects (ticket 99), sets inPanel:
// the panel is its frame, and cardsBelow="list" keeps its three columns down to a 34rem page area.
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
import { createElement, useId, type ReactNode, type Ref, useLayoutEffect, useRef, useState } from "react";
import { copy } from "../copy";
import { cx } from "../lib/cx";
import { formatCount, formatNumber } from "../lib/format";
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

// What the count line counts: "Showing all four activities.", or "Showing 1 to 20 of 99 sources."
// when the rows are one page of more.
// one is the noun for a single row ("version"), so one row reads "Showing 1 version".
// text: the count line in words of the screen's own, such as "Showing 6 of 61 versions" for rows that are
// not one range (the five newest versions and the baseline, ticket 21).
export type Count = { noun: string; one?: string; total: number; from?: number; to?: number; text?: string };

type Level = 2 | 3 | 4 | 5;

// Where the rows turn into cards. The class names are written out whole, so Tailwind finds them.
// md and lg read the page area. fit reads the table's own frame, which is a container of its own
// then: cards while the frame is under 49rem (784 px, the table-fit container size in app.css). It is
// for a table whose columns need that much wherever it sits, as the past range's need about 776 px
// with one line per cell, because a table that keeps to columns 1 to 8 has less room at 1200 px than
// at 1024 px. The 8 px over leave room for small font differences between systems. narrow reads its own frame
// too, with cards under 30rem (480 px): for a table of three short columns, as the evidence drawer's list of a
// band's ISRs (ticket 23), which stays a table in the 576 px drawer and becomes cards in the 410 px one.
// list reads the page area, with cards under 34rem (544 px): for a list of three columns in a panel, as All projects
// (ticket 99), which keeps its columns on a 768 px tablet and turns to cards on a phone.
export type CardsBelow = "md" | "lg" | "fit" | "narrow" | "list";
const SHOW: Record<CardsBelow, { table: string; cards: string }> = {
  md: { table: "@md/page:block", cards: "@md/page:hidden" },
  lg: { table: "@lg/page:block", cards: "@lg/page:hidden" },
  fit: { table: "@table-fit/table:block", cards: "@table-fit/table:hidden" },
  narrow: { table: "@table-narrow/table:block", cards: "@table-narrow/table:hidden" },
  list: { table: "@list/page:block", cards: "@list/page:hidden" },
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
// A card as a row of the panel around it (cardRows): a 1 px line over each card after the first, and 12 px sides that
// reach into the panel's body, so a selected row's tint keeps its text off its edges. The line runs on the text's
// edges, not the tint's, as the prototype's do (ticket 101's design review, round 2).
const CARD_ROW =
  "relative -mx-3 px-3 py-4 first:pt-2 before:absolute before:inset-x-3 before:top-0 before:h-px before:bg-line first:before:hidden";
const sharesGrid = (column: Column) => Boolean(column.numeric || column.short);
const cardField = (column: Column, shared: boolean) => cx(CARD_FIELD, !(sharesGrid(column) && shared) && "col-span-full");

// A count line from a table's shown and total rows and its noun, by DESIGN.md's one rule: "Showing 2 of 14 sources.",
// "Showing all 14 sources.", "Showing both sources." or "Showing the one source." The numbers are the route's or the
// tool's; this only writes them (the 58 review, round 3, follow-up 1).
export function countLineOf(shown: number, total: number, noun: { one: string; many: string }): string {
  const whole = (value: number) => formatNumber(value, { compact: false });
  return copy.table.showingOf(shown, total, whole(shown), whole(total), formatCount(total), noun);
}

export function countText({ noun, one, total, from, to, text }: Count): string {
  if (text) return text;
  if (total === 1 && one) return copy.table.showingOne(one);
  return from !== undefined && to !== undefined && (from > 1 || to < total)
    ? copy.table.showing(n(from), n(to), n(total), noun)
    : copy.table.showingAll(total, formatCount(total), noun);
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
  labelledBy,
  busy,
  countLead = false,
  selected,
  inPanel = false,
  cardRows = false,
  countRef,
  countAction,
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
  // Below which width the rows become cards: a page area of md (768 px, the default) or lg
  // (1024 px), or fit, a frame of the table's own under 49rem.
  cardsBelow?: CardsBelow;
  // A sentence that ends the count line's row only while the rows are cards, such as the definition
  // a column's head carries in the table, said once there because cards have no column heads.
  cardsNote?: ReactNode;
  // A list whose heading and search sit above the table (ticket 21's All projects and Packages): the id
  // of that heading, which names the table, so the table draws no title of its own in any state.
  labelledBy?: string;
  // A new page of rows is on its way, such as while a search waits for its answer: the rows stay at full
  // contrast, marked busy, and this sentence takes the count line's place (the 21 brief, section 8.1, as the
  // round 2 design review changed it: a fade dropped muted text under 4.5:1).
  busy?: ReactNode;
  // The count line takes focus after Previous page or Next page (data-page-lead, App.tsx), so the new range is read.
  countLead?: boolean;
  // The row whose details show elsewhere, such as the comparable the evidence drawer shows (ticket 15):
  // it takes the selected row's tint fill.
  selected?: string | null;
  // The table is a Task zone panel's open work (DESIGN.md section 5, Tables; ticket 99's All projects): it draws no frame
  // of its own, its count line sits on the zone's edges, its rows run the panel's full width with their outer cells on
  // those edges, and its cards are rows divided by a line (app.css, "A table in a panel"). The zone names it
  // (labelledBy), and the panel's foot strip holds its source.
  inPanel?: boolean;
  // A table inside a panel's body, as the past range's in zone 1 (ticket 101): the panel frames its cards, so they are
  // rows divided by a 1 px line, not boxes; the table keeps its own frame and title.
  cardRows?: boolean;
  // The count line, which a caller moves focus to, as the past range does when a pressed number lands on the rows it
  // counts (ticket 101): the line then takes focus without a tab stop.
  countRef?: Ref<HTMLParagraphElement>;
  // One flush button right after the count, such as the past range's "Show all 49" (ticket 101).
  countAction?: ReactNode;
}) {
  const ownTitleId = useId();
  const titleId = labelledBy ?? ownTitleId;
  const countId = useId();
  // The frame is a tab stop only while its table is wider than it, so a keyboard can scroll it; a frame that scrolls
  // nothing never takes the first Tab and scrolls the page for nothing (ticket 60).
  const frame = useRef<HTMLDivElement>(null);
  const [overflows, setOverflows] = useState(false);
  useLayoutEffect(() => {
    const element = frame.current;
    if (!element) return;
    const measure = () => setOverflows(element.scrollWidth > element.clientWidth + 1);
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(element);
    const table = element.firstElementChild;
    if (table) observer.observe(table);
    return () => observer.disconnect();
  });

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
    <section
      data-table={state.status}
      data-table-panel={inPanel || undefined}
      aria-busy={loading || Boolean(busy) || undefined}
      className={cx("flex flex-col", !inPanel && "gap-2", (cardsBelow === "fit" || cardsBelow === "narrow") && "@container/table")}
    >
      {loading ? (
        <>
          <LoadingLabel />
          {labelledBy ? null : state.shortTitle ? (
            <SkeletonLine className="text-h2" width="w-2/5" />
          ) : (
            <>
              <SkeletonText className="text-h2 @md/page:hidden" widths={["w-full", "w-3/5"]} />
              <div className="hidden @md/page:block">
                <SkeletonLine className="text-h2" width="w-3/5" />
              </div>
            </>
          )}
          {count && (
            <div data-count-row>
              <SkeletonLine className="text-caption" width="w-1/5" />
            </div>
          )}
        </>
      ) : (
        <>
          {!labelledBy && createElement(`h${level}`, { id: titleId, className: "text-h2 text-ink-heading" }, title)}
          {count && (
            // The count, and the cards' note as its own element at the row's end, which wraps to a line
            // of its own when the two don't fit (DESIGN.md section 5, the Plan check table).
            <div data-count-row className="flex flex-wrap items-baseline justify-between gap-x-4 text-caption text-ink-muted">
              <div className="flex flex-wrap items-baseline gap-x-3">
                <p
                  ref={countRef}
                  id={countId}
                  data-numbers
                  data-page-lead={countLead || undefined}
                  tabIndex={countLead || countRef ? -1 : undefined}
                  // A keyboard press that lands here shows the focus ring; a pointer's shows none (ticket 101's design review).
                  className="[&:not(:focus-visible)]:outline-none"
                >
                  {busy ?? countText(count)}
                </p>
                {countAction}
              </div>
              {cardsNote && (
                <p className={SHOW[cardsBelow].cards} data-cards-note>
                  {cardsNote}
                </p>
              )}
            </div>
          )}
        </>
      )}

      {/* From a page area of 768 px (or 1024 px with cardsBelow="lg", or a frame of 49rem with "fit"),
          a table. In a narrow column it scrolls inside its frame, which then takes focus so a keyboard
          can scroll it too, and only then (ticket 60). */}
      <div
        ref={frame}
        tabIndex={loading ? undefined : overflows ? 0 : -1}
        role={loading ? undefined : "region"}
        aria-labelledby={loading ? undefined : titleId}
        aria-hidden={loading || undefined}
        data-table-view="table"
        className={cx("hidden overflow-x-auto bg-surface", !inPanel && "rounded-md border border-line", SHOW[cardsBelow].table)}
      >
        <table
          aria-labelledby={loading ? undefined : titleId}
          aria-describedby={count && !loading ? countId : undefined}
          // A narrow table shows only from a 30rem frame, and a list's from a 34rem page area, so each keeps no wider
          // minimum that would scroll sideways.
          className={cx("w-full table-fixed border-collapse text-small", cardsBelow === "narrow" || cardsBelow === "list" ? "min-w-[30rem]" : "min-w-[40rem]")}
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
              <tr
                key={row.id}
                data-selected={row.id === selected || undefined}
                className={cx("border-t border-line align-top", row.id === selected && "bg-tint")}
              >
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
        className={cx("flex flex-col", !inPanel && !cardRows && "gap-3", SHOW[cardsBelow].cards)}
      >
        {skeletonRows.map((index) => (
          <li key={index} className={inPanel ? "border-t border-line py-4" : cardRows ? CARD_ROW : "rounded-md border border-line bg-surface p-4"}>
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
          <li
            key={row.id}
            data-selected={row.id === selected || undefined}
            className={cx(
              inPanel ? "border-t border-line py-4" : cardRows ? CARD_ROW : "rounded-md border border-line p-4",
              row.id === selected ? "bg-tint" : "bg-surface",
            )}
          >
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
