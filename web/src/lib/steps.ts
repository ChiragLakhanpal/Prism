// Section 2 of the package workspace, the planned date for each STEP step (ticket 27), in the browser: the shape
// the steps routes answer with (src/strata/server/steps.py, estimate_time's step_dates), the stored choice of
// dates, and the evidence drawer's two lists. Every date, day count and count here came from the tool; the browser
// adds no days and divides nothing (CLAUDE.md rule 1).
import type { EvidenceEvent } from "./answer";
import { remember } from "./evidence";

export type Choice = "middle" | "cautious";
// The one stored value tickets 26 and 27 share (strata.app.plan_date_choices): section 2 calls eight_in_ten its
// cautious dates.
export type StoredChoice = "middle" | "eight_in_ten";
export const CHOICES: Choice[] = ["middle", "cautious"];
export const stored = (choice: Choice): StoredChoice => (choice === "cautious" ? "eight_in_ten" : "middle");
export const fromStored = (choice: StoredChoice | null): Choice => (choice === "middle" ? "middle" : "cautious");

export type StepPoint = {
  planned_date: string | null;
  days: number | null;
  days_relation: "after_previous" | "after_plan" | "on_plan" | "before_plan" | null;
  longer: number | null;
  in10: number | null;
};

export type StepComparable = { step_reference: string; evidence_id: string; days: number; still_open: boolean };

export type AbstainReason = "few_comparables" | "needs_earlier_step" | "not_reached" | "not_in_plan";

export type StepDate = {
  step_key: string;
  is_anchor: boolean;
  comparables_n: number | null;
  // Of comparables_n, how many had reached the step by the records' date; the rest were still open.
  reached_n: number | null;
  comparables: StepComparable[];
  abstain_reason: AbstainReason | null;
  middle: StepPoint | null;
  cautious: StepPoint | null;
  plan_first_date: string | null;
  plan_first_version_date: string | null;
  plan_latest_date: string | null;
  plan_latest_version_date: string | null;
};

export type LongestEntry = { step_reference: string; evidence_id: string; stage_step_key: string; days: number };

export type TrackRecord = { year: number; total: number; inside: number; run_id: string | null; catch_in10: number };

export type StepDates = {
  family: string | null;
  family_reason: "no_family" | "method_not_listed" | null;
  method: string | null;
  basis: "delay" | "duration" | null;
  needs_start_date: boolean;
  start_date: string | null;
  start_range: { from: string; to: string };
  steps: StepDate[];
  longest: { step_key: string; n: number; m: number; entries: LongestEntry[] } | null;
  abstain_all: { n: number } | null;
  min_comparables: number;
  middle_in10: number;
  cautious_in10: number;
  // The tool's counts, so the screen counts nothing (CLAUDE.md rule 1): the steps that can take a date (all but a
  // package from a sentence's first step), how many each choice dated, how many have no date, how many of those for
  // too few comparable packages, and none_dated when no step has a date or days in either choice.
  dateable_n: number;
  dated_n: Record<Choice, number>;
  undated_n: number;
  few_n: number;
  none_dated: boolean;
  actual_steps_count: number | null;
  track_record: Record<Choice, TrackRecord> | null;
  // other_family: comparables planned in another STEP table, whose steps differ; unconfirmed: comparables used whose
  // first listing is not confirmed as the first published one (ticket 63). Older recordings may lack both.
  coverage: { total: number; used: number; missing: number; other_family?: number; unconfirmed?: number; reason: string; sources: string[] };
};

export type StepsResult = {
  as_of: string;
  view: string;
  step_dates: StepDates | null;
  sources: { key: string; dataset_name: string }[];
  records_through: string | null;
  plan_date_choice: StoredChoice | null;
};

// The routes for a package from a STEP row or from a sentence.
export function stepsApi(kind: "step" | "planned", key: string): string {
  return kind === "step" ? `/api/packages/${encodeURIComponent(key)}` : `/api/planned-packages/${encodeURIComponent(key)}`;
}

// ── The evidence drawer's lists ─────────────────────────────────────────

// One step's comparable packages, and the packages behind "ran longest" (the 27 brief, section 6.6). Neither is
// a source on the server: the section holds them from the answer it drew, as a quantile dot's list is held.
export const STEP_LIST = "steps:";
export const LONGEST_LIST = "steps-longest:";
export const stepListId = (packageKey: string, stepKey: string) => `${STEP_LIST}${packageKey}:${stepKey}`;
export const longestListId = (packageKey: string) => `${LONGEST_LIST}${packageKey}`;
export const isStepList = (id: string) => id.startsWith(STEP_LIST) || id.startsWith(LONGEST_LIST);

export type StepListRow = {
  family: string;
  step: StepDate;
  previous_key: string | null;
  basis: "delay" | "duration";
  records_through: string | null;
  sources: string[];
  abstain_all: boolean;
  min_comparables: number;
};

export type LongestListRow = {
  family: string;
  longest: NonNullable<StepDates["longest"]>;
  records_through: string | null;
  sources: string[];
};

export function stepList(packageKey: string, result: StepsResult, index: number): EvidenceEvent {
  const dates = result.step_dates!;
  const row: StepListRow = {
    family: dates.family!,
    step: dates.steps[index],
    previous_key: index > 0 ? dates.steps[index - 1].step_key : null,
    basis: dates.basis!,
    records_through: result.records_through,
    sources: result.sources.map((source) => source.dataset_name),
    abstain_all: dates.abstain_all !== null,
    min_comparables: dates.min_comparables,
  };
  return { id: stepListId(packageKey, dates.steps[index].step_key), kind: "steps", tool: "estimate_time", stratum: "How", short_name: null, row, highlights: [] };
}

export function longestList(packageKey: string, result: StepsResult): EvidenceEvent {
  const dates = result.step_dates!;
  const row: LongestListRow = {
    family: dates.family!,
    longest: dates.longest!,
    records_through: result.records_through,
    sources: result.sources.map((source) => source.dataset_name),
  };
  return { id: longestListId(packageKey), kind: "steps-longest", tool: "estimate_time", stratum: "How", short_name: null, row, highlights: [] };
}

// Hold every list of the answer on screen, so a count opens its list at once and a link to a list reopens it.
export function rememberStepLists(packageKey: string, result: StepsResult) {
  const dates = result.step_dates;
  if (!dates?.family) return;
  dates.steps.forEach((step, index) => {
    if (!step.is_anchor) remember(stepList(packageKey, result, index));
  });
  if (dates.longest) remember(longestList(packageKey, result));
}
