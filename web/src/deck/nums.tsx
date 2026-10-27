// The deck's numbers (the 47 brief, section 6.2): every number on a slide is checkable as in the app. A number is a
// MeasureNum with a dotted underline; hover or focus shows what it counts, its source kind and when it was measured
// ("45 of 52 benchmark questions. Benchmark run, measured Oct 20, 2026."), and a click or Enter opens its window.
//
// Each one sits in a <data> element whose data-source-key names where it came from: "r:<key>" for a result in the
// measures snapshot, "s:<key>" for a setting, "rubric:<key>" for the assessment's points and "tool:<name>" for the
// demo package's recorded answers ("tool:find_comparables" or "tool:estimate_time"). The number check (src/strata/proposal/numbers.py) reads a slide's HTML and accepts
// a number only inside such an element, so a number typed into a slide fails it. In the speaker notes the same
// numbers are plain text, still inside their <data> element.
import type { ReactNode } from "react";
import { MeasureNum } from "../components/MeasureNum";
import { numText, type NumValue } from "../components/Num";
import { formatDate } from "../lib/format";
import { deckCopy } from "./copy";
import type { DeckData, DeckResult } from "./data";

const words = deckCopy.num;
// Where the demo package's numbers came from: its recorded find_comparables answer, or its recorded estimate_time
// answer for the time estimate's months, each with the date its tool ran. No slide of the second draft draws them yet;
// ticket 116's recorded answer on the planning demo slide does.
export const TOOL_KEY = "tool:find_comparables";
export const ESTIMATE_KEY = "tool:estimate_time";
export type ToolKey = typeof TOOL_KEY | typeof ESTIMATE_KEY;
const TOOL_TOOLTIP: Record<ToolKey, (step: string, date: string) => string> = { [TOOL_KEY]: words.tool, [ESTIMATE_KEY]: words.estimate };
const day = (iso: string | undefined) => (iso ? formatDate(iso, { style: "table" }) : "");
const whole = (value: number) => numText({ value, options: { compact: false } });

function Bound({ sourceKey, children }: { sourceKey: string; children: ReactNode }) {
  return <data data-source-key={sourceKey}>{children}</data>;
}

function resultRows(result: DeckResult) {
  return [
    ...(result.n !== undefined && result.n !== null ? [{ label: words.rows.counted, value: whole(result.n) }] : []),
    ...(result.d !== undefined && result.d !== null ? [{ label: words.rows.outOf, value: whole(result.d) }] : []),
    { label: words.rows.kind, value: result.kind },
    { label: words.rows.measured, value: day(result.measured_on) },
    ...(result.run_id ? [{ label: words.rows.run, value: <span className="font-mono">{result.run_id}</span> }] : []),
    { label: words.rows.table, value: <span className="font-mono wrap-break-word">{result.table}</span> },
  ];
}

// A number from a result in the measures snapshot. value is how it is written; the tooltip counts what the
// result counts, from its own numerator and denominator. tooltipValue is the number as the tooltip writes it before
// the result's noun, where value carries a unit of its own, as "US$7.80" does before "US dollars".
export function ResultNum({ result, resultKey, value, tooltipValue }: { result: DeckResult; resultKey: string; value: NumValue; tooltipValue?: string }) {
  const tooltip =
    result.d !== undefined && result.d !== null && result.n !== undefined && result.n !== null && "part" in value
      ? words.ratio(whole(result.n), whole(result.d), result.noun, result.kind, day(result.measured_on))
      : words.count(tooltipValue ?? numText(value), result.noun, result.kind, day(result.measured_on));
  return (
    <Bound sourceKey={`r:${resultKey}`}>
      <MeasureNum
        value={value}
        tooltip={tooltip}
        measure={{ title: result.name, definition: words.definition(result.kind, result.table), rows: resultRows(result) }}
      />
    </Bound>
  );
}

// A design count or a planning choice, written as a word ("six checks", "two countries") from its setting.
export function SettingWord({ data, settingKey, capital = false }: { data: DeckData; settingKey: string; capital?: boolean }) {
  const setting = data.settings[settingKey];
  const kind = words.kinds[setting.kind];
  return (
    <Bound sourceKey={`s:${settingKey}`}>
      <MeasureNum
        value={{ count: setting.value, capital }}
        tooltip={words.setting(setting.name, setting.where)}
        measure={{
          title: setting.name,
          definition: words.settingDefinition(kind),
          rows: [
            { label: words.rows.kind, value: kind },
            { label: words.rows.where, value: setting.where },
          ],
        }}
      />
    </Bound>
  );
}

// A number one of the demo package's recorded tool answers gave: its count of comparable packages from
// find_comparables, or the time estimate's months from estimate_time. date is the day that tool ran.
export function ToolNum({ step, date, value, sourceKey = TOOL_KEY }: { step: string; date: string; value: NumValue; sourceKey?: ToolKey }) {
  return (
    <Bound sourceKey={sourceKey}>
      <MeasureNum value={value} tooltip={TOOL_TOOLTIP[sourceKey](step, day(date))} />
    </Bound>
  );
}

// A dimension's points, from the rubric registry, which cites the assessment brief.
export function RubricPoints({ dimensionKey, points }: { dimensionKey: string; points: number }) {
  return (
    <Bound sourceKey={`rubric:${dimensionKey}`}>
      <MeasureNum value={{ value: points, options: { compact: false } }} tooltip={words.rubric} />
    </Bound>
  );
}

// A number in the speaker notes: plain text, bound to where it came from.
export function NoteNum({ sourceKey, text }: { sourceKey: string; text: string }) {
  return <Bound sourceKey={sourceKey}>{text}</Bound>;
}
