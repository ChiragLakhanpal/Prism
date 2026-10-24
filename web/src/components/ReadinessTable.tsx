// Readiness tables (DESIGN.md section 5; the 16 design brief, sections 3 to 6): the Data readiness
// page's "What you can ask" and "Sources" tables. Each has its title as an h2, a count line or a
// caption, a surface-2 header whose every column head holds its label and a short definition that
// is always on show, and a source line below. A label can open its full definition. Number columns
// are right-aligned stacks: the number first, then what it counts, then a badge only for Partial or
// Gap. A row can span the measure columns with one note, so no cell is ever blank.
//
// Below 768 px each row becomes a card in a list labelled by the section: the row's name as an h3,
// and each column as a term (its name and short definition) and its value, every value from one
// left edge. Numbers share a grid of 120 px columns; text takes the card's full width. The full
// definitions open from the table's heads, so a card repeats only the words.
//
// While the measures load, the real column heads stay and skeleton rows of a fixed height hold the
// rows' places, so nothing moves when they arrive. Rows have no hover: a row does nothing on a press.
import { useId, type ReactNode } from "react";
import { cx } from "../lib/cx";
import { SkeletonLine } from "./Skeleton";
import { Source } from "./Source";

export type ReadinessColumn = {
  key: string;
  // The column's head: a label that can open its full definition, and its name as plain words,
  // which the cards repeat beside each value.
  label: ReactNode;
  name: string;
  about: ReactNode;
  numeric?: boolean;
  // The column's share of the table, as a width class such as "w-1/5".
  width?: string;
};

export type ReadinessRow =
  | { id: string; header: ReactNode; caption?: ReactNode; cells: Record<string, ReactNode> }
  | { id: string; header: ReactNode; caption?: ReactNode; span: ReactNode };

export type ReadinessTableState = { status: "ready"; rows: ReadinessRow[] } | { status: "loading"; rows: number };

// Skeleton rows as tall as the rows they stand for: 64 px for a kind of question, 72 px for a source.
const ROW_HEIGHT = { kinds: "h-16", sources: "h-18" } as const;

const HEAD = "px-4 py-3 align-bottom font-semibold text-ink-heading";
const CELL = "px-4 py-3 wrap-anywhere text-ink";

function Heading({ label, about }: { label: ReactNode; about: ReactNode }) {
  return (
    <>
      <span className="block">{label}</span>
      <span className="block text-caption font-normal text-ink-muted">{about}</span>
    </>
  );
}

export function ReadinessTable({
  id,
  title,
  lines,
  head,
  columns,
  state,
  source,
  skeleton,
  spanName,
}: {
  // A key for tests and screenshots: kinds or sources.
  id: string;
  title: ReactNode;
  // The count line or the caption under the title.
  lines?: ReactNode;
  // The head of the column that names each row.
  head: { label: ReactNode; about?: ReactNode; width?: string };
  columns: ReadinessColumn[];
  state: ReadinessTableState;
  source?: ReactNode;
  skeleton: keyof typeof ROW_HEIGHT;
  // What a card's spanning note is for a screen reader, such as "Coverage, linked, read well and fresh".
  spanName?: string;
}) {
  const titleId = useId();
  const loading = state.status === "loading";
  const rows = state.status === "ready" ? state.rows : [];
  const placeholders = Array.from({ length: loading ? state.rows : 0 }, (_, index) => index);

  return (
    <section aria-labelledby={titleId} data-readiness-table={id} className="flex flex-col">
      <h2 id={titleId} className="text-title text-ink-heading">
        {title}
      </h2>
      {lines && (
        <p className="mt-1 text-caption text-pretty text-ink-muted" data-numbers>
          {lines}
        </p>
      )}

      <div data-table-view="table" className="mt-3 hidden rounded-md border border-line bg-surface md:block">
        <table className="w-full table-fixed border-collapse text-small">
          <caption className="clip-visually">{title}</caption>
          <thead className="bg-surface-2">
            <tr>
              <th scope="col" className={cx(HEAD, "text-left", head.width)}>
                <Heading label={head.label} about={head.about} />
              </th>
              {columns.map((column) => (
                <th key={column.key} scope="col" className={cx(HEAD, column.numeric ? "text-right" : "text-left", column.width)}>
                  <Heading label={column.label} about={column.about} />
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {placeholders.map((index) => (
              <tr key={index} aria-hidden="true" className={cx("border-t border-line", ROW_HEIGHT[skeleton])}>
                <td className="px-4">
                  <SkeletonLine width="w-4/5" className="text-small" />
                </td>
                {columns.map((column) => (
                  <td key={column.key} className="px-4">
                    <SkeletonLine width={column.numeric ? "ml-auto w-1/2" : "w-4/5"} className="text-small" />
                  </td>
                ))}
              </tr>
            ))}
            {rows.map((row) => (
              <tr key={row.id} data-row={row.id} className="border-t border-line align-top">
                <th scope="row" className={cx(CELL, "text-left font-normal")}>
                  <span className="block font-semibold">{row.header}</span>
                  {row.caption && <span className="block text-caption text-ink-muted">{row.caption}</span>}
                </th>
                {"span" in row ? (
                  <td colSpan={columns.length} className={CELL} data-cell={`${row.id}:span`}>
                    {row.span}
                  </td>
                ) : (
                  columns.map((column) => (
                    <td
                      key={column.key}
                      data-cell={`${row.id}:${column.key}`}
                      className={cx(CELL, column.numeric && "text-right [&>*]:items-end")}
                    >
                      {row.cells[column.key]}
                    </td>
                  ))
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <ul aria-labelledby={titleId} data-table-view="cards" className="mt-3 flex flex-col gap-4 md:hidden">
        {placeholders.map((index) => (
          <li key={index} aria-hidden="true" className="rounded-md border border-line bg-surface p-4">
            <SkeletonLine width="w-3/5" className="text-title" />
            <SkeletonLine width="w-2/5" className="text-caption" />
            <div className={cx("mt-3", ROW_HEIGHT[skeleton])} />
          </li>
        ))}
        {rows.map((row) => (
          <li key={row.id} data-card={row.id} className="rounded-md border border-line bg-surface p-4">
            <h3 className="text-title wrap-anywhere text-ink-heading">{row.header}</h3>
            {row.caption && <p className="text-caption text-ink-muted">{row.caption}</p>}
            <dl className="mt-3 grid grid-cols-[repeat(auto-fit,minmax(7.5rem,1fr))] gap-x-4 gap-y-3">
              {"span" in row ? (
                <div className="col-span-full flex flex-col">
                  <dt className="clip-visually">{spanName}</dt>
                  <dd className="text-small wrap-anywhere text-ink">{row.span}</dd>
                </div>
              ) : (
                columns.map((column) => (
                  <div key={column.key} className={cx("flex min-w-0 flex-col", !column.numeric && "col-span-full")}>
                    <dt className="text-caption text-ink-muted">
                      <span className="block font-semibold text-ink">{column.name}</span>
                      <span className="block">{column.about}</span>
                    </dt>
                    <dd className="mt-1 text-small wrap-anywhere text-ink">{row.cells[column.key]}</dd>
                  </div>
                ))
              )}
            </dl>
          </li>
        ))}
      </ul>

      {source && <Source className="mt-2">{source}</Source>}
    </section>
  );
}
