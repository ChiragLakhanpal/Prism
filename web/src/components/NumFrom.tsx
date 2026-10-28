// Where a number came from: the From line of its tooltip (DESIGN.md section 5, Number tooltip; ticket 96), one num.from
// template per kind of number, filled with the tool's own values and the date its records run through. FromLine draws
// it with its date kept on one line; fromText gives the same words as text, for a name such as a range chart dot's.
import type { ReactNode } from "react";
import { copy } from "../copy";
import type { EvidenceEvent } from "../lib/answer";
import { formatDate } from "../lib/format";
import { passageFields } from "../lib/sources";
import { Fill } from "./Fill";
import { MonoWords } from "./MonoWords";

export type FromWords = { template: string; slots: Record<string, string> };

type Source = { key: string; dataset_name: string };

// The record sets whose dates give a comparable package its months: its specific procurement notice and its signed
// contract.
export const MONTHS_SOURCES = ["notices", "awards"];

// The record sets a number was counted from, by their short names where the copy file has one ("Procurement Notices
// and Contract Awards"). Only those of the tool's sources the number was counted from, or all of them when none is.
export function sourceNames(sources: Source[], keys: string[] = MONTHS_SOURCES): string {
  const picked = sources.filter((source) => keys.includes(source.key));
  const names = (picked.length > 0 ? picked : sources).map((source) => copy.num.sources[source.key] ?? source.dataset_name);
  if (names.length < 2) return names[0] ?? "";
  return names.slice(0, -1).join(copy.list.comma) + copy.list.and + names[names.length - 1];
}

// The past range, a dot and Advertised again: "From Procurement Notices and Contract Awards, through October 13, 2026."
export function recordsFrom(sources: Source[], through: string | null | undefined, keys?: string[]): FromWords | null {
  if (!through) return null;
  return { template: copy.num.from.records, slots: { sources: sourceNames(sources, keys), date: formatDate(through) } };
}

// Every record set the tool read, for a number counted from all of them: "From Documents & Reports, Contract Awards and
// Procurement Notices, through October 13, 2026."
export function toolFrom(result: { sources: Source[]; records_through: string | null }): FromWords | null {
  return recordsFrom(result.sources, result.records_through, result.sources.map((source) => source.key));
}

// A From line drawn, or nothing when there is no date to give.
export function fromLine(words: FromWords | null): ReactNode {
  return words ? <FromLine words={words} /> : undefined;
}

// Every record set a tool read, as a list the drawer holds or a draft keeps names them: their dataset names, with their
// keys in the same order where the list has them, so each goes by its short name.
export function heldFrom(names: string[], keys: string[] | undefined, through: string | null | undefined): FromWords | null {
  const sources = names.map((dataset_name, index) => ({ key: keys?.[index] ?? "", dataset_name }));
  return recordsFrom(sources, through, sources.map((source) => source.key));
}

// The risks' counts: "From the completion reports I read, through October 13, 2026."
export function reportsFrom(through: string | null | undefined): FromWords | null {
  return through ? { template: copy.num.from.reports, slots: { date: formatDate(through) } } : null;
}

// A plan row's own value: "From the Northern Water Works Development Agency plan of October 9, 2026."
export function planFrom(agency: string, planDate: string): FromWords {
  return { template: copy.num.from.plan, slots: { agency, date: formatDate(planDate) } };
}

// The plan check's counts and days: "From my check of this plan, as of October 22, 2026."
export function checkFrom(asOf: string): FromWords {
  return { template: copy.num.from.check, slots: { date: formatDate(asOf) } };
}

// Home's briefing and lines: "From my checks on October 28, 2026."
export function homeFrom(checkedOn: string): FromWords {
  return { template: copy.num.from.home, slots: { date: formatDate(checkedOn) } };
}

// A change between two versions of a plan: "From the plans of March 5, 2026 and October 9, 2026."
export function plansFrom(was: string, now: string): FromWords {
  return { template: copy.num.from.plans, slots: { was: formatDate(was), date: formatDate(now) } };
}

// The time estimate: "From my model scored on October 1, 2026."
export function modelFrom(scoredOn: string): FromWords {
  return { template: copy.num.from.model, slots: { date: formatDate(scoredOn) } };
}

// A count or difference the time estimate worked out: "From my time estimate, as of October 28, 2026."
export function estimateFrom(asOf: string): FromWords {
  return { template: copy.num.from.estimate, slots: { date: formatDate(asOf) } };
}

// The rebidding model's track record: "From my model's saved test results of October 1, 2026."
export function testsFrom(runDate: string): FromWords {
  return { template: copy.num.from.tests, slots: { date: formatDate(runDate) } };
}

// The time estimate's track record: "From my backtest for 2025."
export function backtestFrom(year: string): FromWords {
  return { template: copy.num.from.backtest, slots: { year } };
}

// A number a checked sentence matched in a source the tool returned: a plan row by its plan, a document's passage by
// its document, and any other record by the day it became public.
export function evidenceFrom(evidence: EvidenceEvent | undefined): FromWords | null {
  if (!evidence) return null;
  const source = (evidence.row?.source ?? {}) as Record<string, unknown>;
  if (typeof source.implementing_agency === "string" && typeof source.plan_date === "string") {
    return planFrom(source.implementing_agency, source.plan_date);
  }
  if (evidence.kind === "passage") {
    const fields = passageFields(evidence);
    if (fields.date) return { template: copy.num.from.document, slots: { doc: fields.docType, pid: fields.pcode, date: fields.date } };
  }
  const since = evidence.row?.public_from;
  return typeof since === "string" ? { template: copy.num.from.record, slots: { date: formatDate(since) } } : null;
}

// A date in a tooltip's text keeps its spaces from breaking, so it stays on one line (DESIGN.md, Number tooltip).
export const wholeDate = (date: string) => date.replaceAll(" ", "\u00a0");

// The From line as text. In a tooltip drawn as text, such as a range chart dot's, its date is kept whole.
export function fromText(words: FromWords, dateWhole = false): string {
  return words.template.replace(/\{(\w+)\}/g, (slot, name: string) => {
    const value = words.slots[name];
    if (value === undefined) return slot;
    return dateWhole && name === "date" ? wholeDate(value) : value;
  });
}

// One record by its kind and reference, as the activity page names it: "From the notice OP00123456, public since
// April 14, 2021." The reference is set in Roboto Mono (FromLine).
export function namedRecordFrom(kind: string, reference: string, since: string): FromWords {
  return { template: copy.num.from.named, slots: { kind, reference, date: formatDate(since) } };
}

// The report paragraphs that appeared together with a contract: "From the links I scored between the contract and
// the project's reports, through October 23, 2026."
export function linksFrom(through: string): FromWords {
  return { template: copy.num.from.links, slots: { date: formatDate(through) } };
}

// A data readiness measure's number, or a count of the rows the page shows from the measures: "From my measures on
// October 23, 2026."
export function measuresFrom(measuredOn: string): FromWords {
  return { template: copy.num.from.measures, slots: { date: formatDate(measuredOn) } };
}

// One of my own settings, as the measured run used it: "From the settings I used on October 23, 2026."
export function settingsFrom(usedOn: string): FromWords {
  return { template: copy.num.from.settings, slots: { date: formatDate(usedOn) } };
}

// A date never breaks inside a tooltip, so "October 13, 2026" stays on one line (ticket 59). A P-code and a record's
// reference are set in Roboto Mono, as everywhere (DESIGN.md section 5, ProjectId and Reference words).
export function FromLine({ words }: { words: FromWords }) {
  const { pid, reference } = words.slots;
  return (
    <Fill
      template={words.template}
      slots={{
        ...words.slots,
        date: (
          <span data-num-date className="whitespace-nowrap">
            {words.slots.date}
          </span>
        ),
        ...(pid !== undefined && { pid: <span className="font-mono">{pid}</span> }),
        ...(reference !== undefined && { reference: <MonoWords text={reference} /> }),
      }}
    />
  );
}
