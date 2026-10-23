// Table (DESIGN.md section 5): a title sentence that states the finding, a count line
// ("Showing 1–20 of 99 sources"), a surface-2 header with units in the column heads, numbers
// right-aligned in tabular numerals, and a source line below. Below 768 px each row becomes a
// card, so nothing scrolls sideways.
//
// States: ready, loading (skeleton rows sized to the table), empty (an empty-state card that
// says what to do next) and error (an alert with "Try again").
import { useId, type ReactNode } from "react";
import { copy } from "../copy";
import { cx } from "../lib/cx";
import { LoadingLabel, Skeleton } from "./Skeleton";

export type Column = {
  key: string;
  // The header with its unit, such as "Estimated Amount (US$)". A Term can carry its definition.
  header: ReactNode;
  numeric?: boolean;
};

export type Row = { id: string; cells: Record<string, ReactNode> };

export type TableState =
  | { status: "ready"; rows: Row[] }
  | { status: "loading"; rows: number }
  | { status: "empty"; empty: ReactNode }
  | { status: "error"; error: ReactNode };

export function Table({
  title,
  count,
  columns,
  state,
  source,
  rowHeader,
}: {
  title: ReactNode;
  count?: ReactNode;
  columns: Column[];
  state: TableState;
  source?: ReactNode;
  // The column that names each row, used as the card's heading below 768 px.
  rowHeader: string;
}) {
  const titleId = useId();
  const countId = useId();
  const loading = state.status === "loading";
  const rows = state.status === "ready" ? state.rows : [];
  const align = (column: Column) => (column.numeric ? "text-right" : "text-left");

  return (
    <section data-table aria-labelledby={titleId} aria-busy={loading || undefined} className="flex flex-col gap-2">
      <h3 id={titleId} className="text-title text-ink-heading">
        {title}
      </h3>
      {count && state.status !== "empty" && state.status !== "error" && (
        <p id={countId} className="text-caption text-ink-muted" data-numbers>
          {count}
        </p>
      )}
      {loading && <LoadingLabel />}

      {state.status === "empty" && state.empty}
      {state.status === "error" && state.error}

      {(state.status === "ready" || loading) && (
        <>
          {/* A wide table scrolls inside its frame between 768 and 1024 px; the frame takes focus so
              a keyboard can scroll it too. */}
          <div
            tabIndex={0}
            role="region"
            aria-labelledby={titleId}
            className="hidden overflow-x-auto rounded-md border border-line bg-surface md:block"
          >
            <table aria-labelledby={titleId} aria-describedby={count ? countId : undefined} className="w-full border-collapse text-small">
              <thead className="bg-surface-2">
                <tr>
                  {columns.map((column) => (
                    <th key={column.key} scope="col" className={cx("px-3 py-2 align-bottom font-semibold text-ink-heading", align(column))}>
                      {column.header}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {loading
                  ? Array.from({ length: state.rows }, (_, index) => (
                      <tr key={index} className="border-t border-line">
                        {columns.map((column) => (
                          <td key={column.key} className="px-3 py-3">
                            <Skeleton className={cx("h-4", column.numeric ? "ml-auto w-16" : "w-4/5")} />
                          </td>
                        ))}
                      </tr>
                    ))
                  : rows.map((row) => (
                      <tr key={row.id} className="border-t border-line align-top">
                        {columns.map((column) =>
                          column.key === rowHeader ? (
                            <th key={column.key} scope="row" className={cx("px-3 py-2 font-normal text-ink", align(column))}>
                              {row.cells[column.key]}
                            </th>
                          ) : (
                            <td key={column.key} className={cx("px-3 py-2 text-ink", align(column))}>
                              {row.cells[column.key]}
                            </td>
                          ),
                        )}
                      </tr>
                    ))}
              </tbody>
            </table>
          </div>

          <ul aria-labelledby={titleId} className="flex flex-col gap-2 md:hidden">
            {loading
              ? Array.from({ length: state.rows }, (_, index) => (
                  <li key={index} className="rounded-md border border-line bg-surface p-4">
                    <Skeleton className="h-4 w-3/5" />
                    <Skeleton className="mt-3 h-4 w-full" />
                    <Skeleton className="mt-2 h-4 w-4/5" />
                  </li>
                ))
              : rows.map((row) => (
                  <li key={row.id} className="rounded-md border border-line bg-surface p-4">
                    <h4 className="text-small font-semibold text-ink-heading">{row.cells[rowHeader]}</h4>
                    <dl className="mt-2 flex flex-col gap-1 text-small" data-numbers>
                      {columns
                        .filter((column) => column.key !== rowHeader)
                        .map((column) => (
                          <div key={column.key} className="flex justify-between gap-4">
                            <dt className="text-ink-muted">{column.header}</dt>
                            <dd className={cx("text-ink", align(column))}>{row.cells[column.key]}</dd>
                          </div>
                        ))}
                    </dl>
                  </li>
                ))}
          </ul>
        </>
      )}

      {source && (
        <p className="text-caption text-ink-muted">
          <span className="font-bold">{copy.table.source}</span> {source}
        </p>
      )}
    </section>
  );
}
