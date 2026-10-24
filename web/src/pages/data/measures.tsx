// How the Data readiness page writes the tool's numbers and sentences: every number is a Num, a
// measure's number opens its window, and every sentence the server built keeps its words. Nothing
// here computes a number; each one is a count, a sum or a share the tool returned.
import { Fragment, type ReactNode } from "react";
import { MeasureNum, type Measure } from "../../components/MeasureNum";
import { Num, numText, type NumValue } from "../../components/Num";
import { copy } from "../../copy";
import type { Column, MeasureRow, Segment } from "../../lib/dataPages";

const words = copy.dataReadiness;

// The window's name and definition for a measure, by the column it fills.
const KIND_COLUMN: Record<string, Column> = { coverage: "coverage", linked: "linked", read_well: "read_well", fresh: "fresh" };

export type Measures = { rows: MeasureRow[]; asOf: string };

function window(row: MeasureRow, column: Column | null, asOf: string): Measure {
  const day = (iso: string) => numText({ date: iso, style: "table", today: asOf });
  const rows = [
    ...(row.count !== null ? [{ label: words.number.numerator, value: <Num value={row.count} options={{ compact: false }} /> }] : []),
    ...(row.denominator !== null
      ? [{ label: words.number.denominator, value: <Num value={row.denominator} options={{ compact: false }} /> }]
      : []),
    ...(row.as_of ? [{ label: words.number.latest, value: day(row.as_of) }] : []),
    { label: words.number.measured, value: day(row.measured_on) },
    ...(row.source.counted_in
      ? [{ label: words.number.countedIn, value: <span className="font-mono">{row.source.counted_in}</span> }]
      : []),
  ];
  if (column === null) return { title: words.fixes.title, definition: words.fixes.caption, rows };
  return { title: words.sources.columns[column].label, definition: words.sources.definitions[column], rows };
}

function tooltip(row: MeasureRow, noun: string | null, asOf: string, shown: "ratio" | "count" | "day", count?: number): string {
  const measured = numText({ date: row.measured_on, style: "table", today: asOf });
  const n = (value: number) => numText({ value, options: { compact: false } });
  if (shown === "day" && row.as_of) return words.number.day(numText({ date: row.as_of, style: "table", today: asOf }), measured);
  if (shown === "ratio" && row.count !== null && row.denominator !== null) {
    return words.number.ratio(n(row.count), n(row.denominator), noun ?? "", measured);
  }
  return words.number.count(n(count ?? row.count ?? 0), noun ?? "", measured);
}

// A number from one of the tool's rows, with its tooltip and its window.
export function MeasureValue({
  measures,
  index,
  value,
  noun,
  column,
  shown = "count",
  className,
}: {
  measures: Measures;
  index: number;
  value: NumValue;
  noun: string | null;
  column?: Column | null;
  shown?: "ratio" | "count" | "day";
  className?: string;
}) {
  const row = measures.rows[index];
  const owner = column === undefined ? (KIND_COLUMN[row.kind] ?? null) : column;
  return (
    <MeasureNum
      value={value}
      className={className}
      tooltip={tooltip(row, noun, measures.asOf, shown, "count" in value ? value.count : undefined)}
      measure={window(row, owner, measures.asOf)}
    />
  );
}

// A sentence the tool built: its text as it came, and each number as a Num. A number with a row
// behind it opens that measure; a count with none, such as the kinds of question, says where it
// was counted.
export function Sentence({ segments, measures, about }: { segments: Segment[]; measures: Measures; about?: string }) {
  return (
    <>
      {segments.map((segment, index): ReactNode => {
        if ("text" in segment) return <Fragment key={index}>{segment.text}</Fragment>;
        if (segment.row === null) {
          return <MeasureNum key={index} value={{ count: segment.number }} tooltip={about ?? words.number.kinds} />;
        }
        return (
          <MeasureValue key={index} measures={measures} index={segment.row} value={{ count: segment.number }} noun={segment.noun} />
        );
      })}
    </>
  );
}
