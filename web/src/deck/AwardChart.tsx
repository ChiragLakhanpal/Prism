// C1, contract award rows per fiscal year (the 47 brief, section 4.4): drawn by code from the measures snapshot's
// award-rows-by-year series, the same result the proposal's award-gap figure draws (ticket 46), so a bar is never a
// number typed by hand. One bar a fiscal year, coloured by the dataset or the award notices the rows came from, with
// DESIGN.md section 6's categorical text variants (bars are essential marks), about five rounded ticks, a dashed
// grid and the years no awards dataset covers marked above their bars. The slide's title states the finding, so the
// chart has none of its own; its key names the three sources, because their names are too long to sit over bars a
// year wide. Its table twin lists the same rows.
import { formatNumber } from "../lib/format";
import { deckCopy } from "./copy";
import type { DeckResult } from "./data";

const words = deckCopy.slides.gap;
// DESIGN.md section 6's categorical text variants, as the theme's chart tokens, in the order the series lists them.
const FILLS = ["fill-chart-cat2-text", "fill-chart-cat3-text", "fill-chart-cat1-text"];
const SWATCHES = ["bg-chart-cat2-text", "bg-chart-cat3-text", "bg-chart-cat1-text"];
const INKS = ["text-chart-cat2-text", "text-chart-cat3-text", "text-chart-cat1-text"];

type Row = { fiscal_year: number; fiscal_year_label: string; dataset: string; award_rows: number };

export function rowsOf(result: DeckResult): Row[] {
  return (result.series ?? []) as unknown as Row[];
}

function ticks(top: number): number[] {
  for (const step of [1, 2, 5, 10, 20, 25, 50, 100, 200, 250, 500, 1000, 2000, 2500, 5000, 10000, 20000, 50000]) {
    if (top / step <= 5) return Array.from({ length: Math.ceil(top / step) + 1 }, (_, i) => i * step);
  }
  return [0, top];
}

export function AwardKey({ result }: { result: DeckResult }) {
  const groups = [...new Set(rowsOf(result).map((row) => row.dataset))];
  return (
    <ul className="flex flex-wrap gap-x-4 gap-y-1 text-caption text-chart-text" data-chart-key>
      {groups.map((group, index) => (
        <li key={group} className={`flex items-center gap-2 font-semibold ${INKS[index % INKS.length]}`}>
          <span aria-hidden="true" className={`inline-block size-3 ${SWATCHES[index % SWATCHES.length]}`} />
          {group}
        </li>
      ))}
    </ul>
  );
}

export function AwardChart({
  result,
  gap,
  width,
  height,
  labelledById,
  describedById,
}: {
  result: DeckResult;
  gap: { start: number; end: number } | null;
  width: number;
  height: number;
  labelledById: string;
  describedById: string;
}) {
  const rows = rowsOf(result);
  const groups = [...new Set(rows.map((row) => row.dataset))];
  const years = rows.map((row) => row.fiscal_year);
  const first = Math.min(...years);
  const last = Math.max(...years);
  const left = 44;
  const right = width - 4;
  const top = 28;
  const bottom = height - 22;
  const marks = ticks(Math.max(...rows.map((row) => row.award_rows), 1));
  const scale = (bottom - top) / marks[marks.length - 1];
  const slot = (right - left) / (last - first + 1);
  const x = (year: number) => left + (year - first) * slot;
  return (
    <svg role="img" aria-labelledby={labelledById} aria-describedby={describedById} width={width} height={height} className="block tabular-nums" data-award-chart>
      {marks.map((tick) => (
        <g key={tick}>
          {tick > 0 && <line x1={left} x2={right} y1={bottom - tick * scale} y2={bottom - tick * scale} className="stroke-chart-grey200" strokeDasharray="4 4" />}
          <text x={left - 6} y={bottom - tick * scale + 4} textAnchor="end" fontSize={13} className="fill-chart-text-subtle">
            {formatNumber(tick, { compact: false })}
          </text>
        </g>
      ))}
      {gap && (
        <g data-gap>
          <line x1={x(gap.start)} x2={x(gap.end + 1)} y1={top - 4} y2={top - 4} className="stroke-chart-grey300" strokeWidth={3} />
          <text x={(x(gap.start) + x(gap.end + 1)) / 2} y={top - 12} textAnchor="middle" className="fill-chart-text-subtle text-chart-label uppercase">
            {words.gapLabel}
          </text>
        </g>
      )}
      {rows.map((row) => (
        <rect
          key={row.fiscal_year}
          x={x(row.fiscal_year) + slot * 0.15}
          y={bottom - row.award_rows * scale}
          width={slot * 0.7}
          height={row.award_rows * scale}
          className={FILLS[groups.indexOf(row.dataset) % FILLS.length]}
        />
      ))}
      <line x1={left} x2={right} y1={bottom} y2={bottom} className="stroke-chart-grey300" />
      {rows
        .filter((row) => row.fiscal_year % 5 === 0 || row.fiscal_year === first || row.fiscal_year === last)
        .map((row) => (
          <text key={row.fiscal_year} x={x(row.fiscal_year) + slot / 2} y={bottom + 16} textAnchor="middle" fontSize={13} className="fill-chart-text-subtle">
            {row.fiscal_year_label}
          </text>
        ))}
    </svg>
  );
}

export function AwardTable({ result, caption }: { result: DeckResult; caption: string }) {
  const t = words.table;
  return (
    <table className="w-full border-collapse text-small tabular-nums" data-award-table>
      <caption className="sr-only">{caption}</caption>
      <thead className="bg-surface-2 text-left">
        <tr>
          <th scope="col" className="px-3 py-2 font-semibold">{t.year}</th>
          <th scope="col" className="px-3 py-2 text-right font-semibold">{t.rows}</th>
          <th scope="col" className="px-3 py-2 font-semibold">{t.from}</th>
        </tr>
      </thead>
      <tbody>
        {rowsOf(result).map((row) => (
          <tr key={row.fiscal_year} className="border-t border-line">
            <th scope="row" className="px-3 py-1 text-left font-normal">{row.fiscal_year_label}</th>
            <td className="px-3 py-1 text-right">{formatNumber(row.award_rows, { compact: false })}</td>
            <td className="px-3 py-1">{row.dataset}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
