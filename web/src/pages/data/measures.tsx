// How the Data readiness page writes the tool's numbers and sentences: every number is a Num, a
// measure's number opens its window, and every sentence the server built keeps its words. Nothing
// here computes a number; each one is a count, a sum or a share the tool returned.
//
// Every tooltip names what the number counts ("528 of 603 contracts. Measured Oct 23, 2026."), and
// every window shows the number that opened it: a number that is neither the measure's count nor
// its denominator, such as a shortfall, gets its own first row.
import { Fragment, type ReactNode } from "react";
import { MeasureNum, type Measure } from "../../components/MeasureNum";
import { Num, numText, type NumValue } from "../../components/Num";
import { copy } from "../../copy";
import type { Column, MeasureRow, Segment } from "../../lib/dataPages";

const words = copy.dataReadiness;

// The window's name and definition for a measure, by the column it fills, when the copy file's
// measureWindows has no words of its own for that measure.
const KIND_COLUMN: Record<string, Column> = { coverage: "coverage", linked: "linked", read_well: "read_well", fresh: "fresh" };

export type Measures = { rows: MeasureRow[]; asOf: string };

// What a number counts, in the plural and, when the registry gives one, the singular.
export type Noun = { many: string; one?: string | null };

// A number that opened a window and is not one of the measure's own numbers: a shortfall or days late.
export type Role = "missing" | "days";
const ROLE_LABEL: Record<Role, string> = { missing: words.number.missingLabel, days: words.number.days };

function measureWindow(row: MeasureRow, column: Column | null, asOf: string, clicked: { role: Role; value: number } | null): Measure {
  const day = (iso: string) => numText({ date: iso, style: "table", today: asOf });
  const rows = [
    ...(clicked ? [{ label: ROLE_LABEL[clicked.role], value: <Num value={clicked.value} options={{ compact: false }} /> }] : []),
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
  // A measure that fills no column, such as a check or a fix's own measure, has its own words, so
  // its window never borrows a column's name and definition (design review r5 B1).
  const own = words.measureWindows[row.measure];
  if (own) return { title: own.title, definition: own.definition, rows };
  if (column === null) return { title: words.fixes.title, definition: words.fixes.caption, rows };
  return { title: words.sources.columns[column].label, definition: words.sources.definitions[column], rows };
}

function said(noun: Noun | null, n: number): string {
  if (!noun?.many) {
    // Every number says what it counts (design review B1); a missing noun is a gap in the registry
    // or the copy file, which web/tests/lint.spec.ts catches. The page still renders.
    if (import.meta.env.DEV) console.error("A data readiness number has no noun to say what it counts.");
    return "";
  }
  return n === 1 && noun.one ? noun.one : noun.many;
}

export type TooltipKind = "ratio" | "count" | "day" | "missing";

function tooltip(row: MeasureRow, noun: Noun | null, asOf: string, kind: TooltipKind, count?: number, lack?: string | null): string {
  const measured = numText({ date: row.measured_on, style: "table", today: asOf });
  const n = (value: number) => numText({ value, options: { compact: false } });
  if (kind === "day" && row.as_of) return words.number.day(numText({ date: row.as_of, style: "table", today: asOf }), measured);
  // A shortfall names what its records lack: "75 of 603 contracts lack a STEP reference."
  if (kind === "missing" && lack && count !== undefined && row.denominator !== null) {
    const says = count === 1 ? words.number.missingOne : words.number.missing;
    return says(n(count), n(row.denominator), said(noun, row.denominator), lack, measured);
  }
  if (kind === "ratio" && row.count !== null && row.denominator !== null) {
    return words.number.ratio(n(row.count), n(row.denominator), said(noun, row.denominator), measured);
  }
  const shown = count ?? row.count ?? 0;
  return words.number.count(n(shown), said(noun, shown), measured);
}

// A number from one of the tool's rows, with its tooltip and its window.
export function MeasureValue({
  measures,
  index,
  value,
  noun,
  windowColumn,
  tooltipKind = "count",
  role,
  lack,
  className,
}: {
  measures: Measures;
  index: number;
  value: NumValue;
  noun: Noun | null;
  windowColumn?: Column | null;
  tooltipKind?: TooltipKind;
  role?: Role | null;
  lack?: string | null;
  className?: string;
}) {
  const row = measures.rows[index];
  const owner = windowColumn === undefined ? (KIND_COLUMN[row.kind] ?? null) : windowColumn;
  const count = "count" in value ? value.count : "value" in value ? value.value : undefined;
  return (
    <MeasureNum
      value={value}
      className={className}
      tooltip={tooltip(row, noun, measures.asOf, role === "missing" && lack ? "missing" : tooltipKind, count, lack)}
      measure={measureWindow(row, owner, measures.asOf, role && count !== undefined ? { role, value: count } : null)}
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
          <MeasureValue
            key={index}
            measures={measures}
            index={segment.row}
            value={{ count: segment.number }}
            noun={segment.noun ? { many: segment.noun, one: segment.noun_one } : null}
            role={segment.role}
            lack={segment.lack}
          />
        );
      })}
    </>
  );
}
