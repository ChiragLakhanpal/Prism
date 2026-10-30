// The words section 1 gives find_comparables' period of notices (ticket 137), in the note on what "comparable" meant
// and in the state where no package matched. The tool decides how the period ends (criteria.period); this only picks
// its words, so the note and the tool can never disagree. A period that runs forward is a part of the "They ..."
// sentence ("had notices from {from} to {to}"), or, for a plan older than the period's start, a sentence of its own
// that says why it runs to the as-of date. A period that would end before it starts names no range: its sentence says
// why no package can match. A range whose end comes before its start is never written, whatever the case says.
import { copy } from "../copy";
import type { ComparablesResult } from "./api";

type Criteria = Pick<NonNullable<ComparablesResult["criteria"]>, "notice_from" | "notice_to" | "period">;

// "note" for the note under a chart, "empty" for the state with no comparable package.
export type PeriodForm = "note" | "empty";

// The template, and the ISO dates its {from}, {to} and {asOf} slots take. part is true when the template is a part of
// the "They ..." sentence, false when it is a sentence of its own.
export type PeriodWords = { template: string; part: boolean; slots: { from?: string; to?: string; asOf?: string } };

export function periodWords(criteria: Criteria, form: PeriodForm, asOf: string): PeriodWords {
  const note = copy.pastRange.note;
  const empty = copy.pastRange.empty;
  const range = { from: criteria.notice_from, to: criteria.notice_to };
  // ISO dates sort as text, so a period that ends before it starts is caught whatever the tool called it.
  const backwards = criteria.notice_to < criteria.notice_from;
  switch (backwards ? (criteria.period === "before_data" ? "before_data" : "ends_before_start") : criteria.period) {
    case "plan_before_data":
      return { template: form === "note" ? note.periodOlder : empty.nonePeriodOlder, part: false, slots: range };
    case "plan_before_start":
      return { template: form === "note" ? note.periodOlderThanStart : empty.nonePeriodOlderThanStart, part: false, slots: range };
    case "before_data":
      return { template: empty.noneBeforeData, part: false, slots: { from: criteria.notice_from, asOf } };
    case "ends_before_start":
      return { template: empty.noneEndsBeforeStart, part: false, slots: {} };
    default:
      return { template: form === "note" ? note.period : empty.nonePeriod, part: true, slots: range };
  }
}

// Whether the period can hold any package: false when it would end before it starts.
export const periodRuns = (criteria: Criteria) =>
  criteria.notice_from <= criteria.notice_to && criteria.period !== "before_data" && criteria.period !== "ends_before_start";
