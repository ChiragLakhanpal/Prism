// How the Data readiness page writes the tool's numbers and sentences: every number is a Num, a
// measure's number opens its window, and every sentence the server built keeps its words. Nothing
// here computes a number; each one is a count, a sum or a share the tool returned.
//
// Every tooltip names what the number counts ("528 of 603 contracts."), then when I measured it ("From my measures on
// October 23, 2026.") and, for a number with a window, what a click opens (DESIGN.md section 5, Number tooltip; ticket
// 96). Every window shows the number that opened it: a number that is neither the measure's count nor its
// denominator, such as a shortfall, gets its own first row.
import { Fragment, type MouseEvent, type ReactNode } from "react";
import { MeasureNum, type Measure } from "../../components/MeasureNum";
import { Num, numText, type NumValue } from "../../components/Num";
import { FromLine, measuresFrom, wholeDate } from "../../components/NumFrom";
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

// A table's three-part name, which a narrow window breaks only after a dot ("strata.silver." then
// "plan_listings"), so the name a reader copies or searches for never splits inside a word. A part
// too wide for the cell on its own still breaks, rather than spill out of the window.
function TableName({ name }: { name: string }) {
  return (
    <span className="font-mono wrap-break-word">
      {name.split(/(?<=\.)/).map((part, index) => (
        <Fragment key={index}>
          {part}
          <wbr />
        </Fragment>
      ))}
    </span>
  );
}

// A window's own words and more rows, for a number that no registry entry names, such as the stress
// shelf's (ticket 18): its title, its definition and rows after the measure's own numbers.
export type WindowWords = { title: string; definition: ReactNode; rows?: { label: string; value: ReactNode }[] };

function measureWindow(
  row: MeasureRow,
  column: Column | null,
  asOf: string,
  clicked: { role: Role; value: number } | null,
  extra: { label: string; value: ReactNode }[] = [],
  own?: WindowWords,
): Measure {
  const day = (iso: string) => numText({ date: iso, style: "table", today: asOf });
  const rows = [
    ...(clicked ? [{ label: ROLE_LABEL[clicked.role], value: <Num value={clicked.value} options={{ compact: false }} /> }] : []),
    ...(row.count !== null ? [{ label: words.number.numerator, value: <Num value={row.count} options={{ compact: false }} /> }] : []),
    ...(row.denominator !== null
      ? [{ label: words.number.denominator, value: <Num value={row.denominator} options={{ compact: false }} /> }]
      : []),
    ...(row.as_of ? [{ label: words.number.latest, value: day(row.as_of) }] : []),
    ...extra,
    ...(own?.rows ?? []),
    { label: words.number.measured, value: day(row.measured_on) },
    ...(row.source.counted_in ? [{ label: words.number.countedIn, value: <TableName name={row.source.counted_in} /> }] : []),
  ];
  const counted = { source: row.source_key, measure: row.measure };
  if (own) return { title: own.title, definition: own.definition, rows, counted };
  // A measure that fills no column, such as a check or a fix's own measure, has its own words, so
  // its window never borrows a column's name and definition (design review r5 B1).
  const words_ = words.measureWindows[row.measure];
  if (words_) return { title: words_.title, definition: words_.definition, rows, counted };
  if (column === null) return { title: words.fixes.title, definition: words.fixes.caption, rows, counted };
  return { title: words.sources.columns[column].label, definition: words.sources.definitions[column], rows, counted };
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
  const n = (value: number) => numText({ value, options: { compact: false } });
  // The date stays on one line in the tooltip (ticket 59).
  // A date in a sentence is written in full (DESIGN.md rule 13), as its From line writes it.
  if (kind === "day" && row.as_of) return words.number.day(wholeDate(numText({ date: row.as_of })));
  // A shortfall names what its records lack: "75 of 603 contracts lack a STEP reference."
  if (kind === "missing" && lack && count !== undefined && row.denominator !== null) {
    const says = count === 1 ? words.number.missingOne : words.number.missing;
    return says(n(count), n(row.denominator), said(noun, row.denominator), lack);
  }
  if (kind === "missing" && row.kind === "read_well" && count !== undefined && row.denominator !== null) {
    return words.number.unread(n(count), n(row.denominator), said(noun, row.denominator));
  }
  if (kind === "ratio" && row.count !== null && row.denominator !== null) {
    return words.number.ratio(n(row.count), n(row.denominator), said(noun, row.denominator));
  }
  const shown = count ?? row.count ?? 0;
  return words.number.count(n(shown), said(noun, shown));
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
  extraRows,
  window: own,
  inText = false,
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
  // More rows for the window, after the measure's own numbers, such as a share's split by route.
  extraRows?: { label: string; value: ReactNode }[];
  // The window's own words, for a number no registry entry names.
  window?: WindowWords;
  // A number in a sentence, rather than in a table's stack of values (MeasureNum's inText).
  inText?: boolean;
}) {
  const row = measures.rows[index];
  const owner = windowColumn === undefined ? (KIND_COLUMN[row.kind] ?? null) : windowColumn;
  const count = "count" in value ? value.count : "value" in value ? value.value : undefined;
  return (
    <MeasureNum
      value={value}
      className={className}
      tooltip={tooltip(row, noun, measures.asOf, role === "missing" && (lack || row.kind === "read_well") ? "missing" : tooltipKind, count, lack)}
      from={<FromLine words={measuresFrom(row.measured_on)} />}
      inText={inText}
      measure={measureWindow(row, owner, measures.asOf, role && count !== undefined ? { role, value: count } : null, extraRows, own)}
    />
  );
}

// The day of the newest measure, which a count of the page's own rows comes from.
export function latestMeasured(measures: Measures): string | null {
  return measures.rows.reduce<string | null>((latest, row) => (latest === null || row.measured_on > latest ? row.measured_on : latest), null);
}

// A sentence the tool built: its text as it came, and each number as a Num. A number with a row
// behind it opens that measure; a count with none, such as the kinds of question, says where it
// was counted.
export function Sentence({
  segments,
  measures,
  about,
  inText = false,
}: {
  segments: Segment[];
  measures: Measures;
  about?: string;
  // A headline in lead type, whose lines keep their 28 px pitch with a number in them (MeasureNum's inText).
  inText?: boolean;
}) {
  return (
    <>
      {segments.map((segment, index): ReactNode => {
        if ("text" in segment) return <Fragment key={index}>{segment.text}</Fragment>;
        if ("mono" in segment) {
          return (
            <span key={index} className="font-mono">
              {segment.mono}
            </span>
          );
        }
        if ("link" in segment) return <InPageLink key={index} href={segment.href} text={segment.link} />;
        if (segment.row === null) {
          const measured = latestMeasured(measures);
          return (
            <MeasureNum
              key={index}
              value={{ count: segment.number }}
              tooltip={about ?? words.number.kinds}
              from={measured ? <FromLine words={measuresFrom(measured)} /> : undefined}
              inText={inText}
            />
          );
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
            inText={inText}
          />
        );
      })}
    </>
  );
}

// A link to a section of this page, such as "the hardest documents I read" (the 18 brief, section 6.2):
// it moves focus to the section's heading, which takes tabindex -1, and the address gains the
// section's id, so Back returns to the link.
export function InPageLink({ href, text }: { href: string; text: string }) {
  const onClick = (event: MouseEvent<HTMLAnchorElement>) => {
    const target = document.getElementById(href.slice(1));
    if (!target) return;
    event.preventDefault();
    window.history.pushState(window.history.state, "", href);
    target.focus();
    target.scrollIntoView({ block: "start" });
  };
  return (
    <a
      href={href}
      onClick={onClick}
      className="py-1 text-primary underline decoration-1 underline-offset-3 transition-paint duration-150 hover:text-link-hover"
    >
      {text}
    </a>
  );
}
