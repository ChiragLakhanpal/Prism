// Following in the browser (ticket 37): the shapes GET /api/following and the follow routes answer with
// (src/strata/server/following.py), the viewer's staff role, and the words each row's parts are built from. Every
// count, status, ratio and date the page states is the server's; nothing here counts, sums, rounds or subtracts.
import { copy } from "../copy";
import type { EvidenceEvent } from "./answer";
import { formatCount, formatDate } from "./format";
import { createStore } from "./store";

export type SignalKey = "completion_passed" | "above_estimate" | "late_direct" | "closing_moves" | "restructured" | "isr_lowered" | "disbursement";
export type Status = "needs_a_look" | "watch" | "no_signals" | "not_checked" | "closed" | "pipeline" | "dropped";

export type SignalItem = Record<string, any> & { evidence_id: string; public_from: string };
export type Signal = {
  evidence_id: string;
  public_from: string;
  // evidence_id: the record the line's marker opens and names (the latest move, for the closing date).
  source: { source_key: string; project_id: string; document_id: string | null; date: string | null; evidence_id?: string };
  check: SignalKey;
  strong: boolean;
  count: number;
  values: Record<string, any>;
  items: SignalItem[];
};

export type Check = { key: SignalKey; ran: boolean; missing: string | null; fired: boolean; strong: boolean };

export type FollowedProject = {
  project: {
    evidence_id: string;
    project_id: string;
    project_name: string;
    country: string | null;
    status: string | null;
    closing_date: string | null;
    closing_kind: "closes" | "past_closing" | "closed" | "pipeline" | "dropped" | null;
    days_to_close: number | null;
  };
  status: Status;
  rows: Signal[];
  checks: Check[];
  counts: { signals: number; strong: number; ran: number; checks: number; not_ran: number };
  following_since: string | null;
  mission_brief: { draft_id: string; created_at: string } | null;
  // A follow the seed command made for you (ticket 41), labeled "Example".
  example?: boolean;
};

export type Counts = {
  total: number;
  checked: number;
  needs_a_look: number;
  watch: number;
  not_checked: number;
  no_signals: number;
  closed: number;
  pipeline: number;
  // Closed, dropped and in the pipeline together.
  ended: number;
  folded: number;
  shown: number;
  partly: number;
  fully: number;
  partly_folded: number;
};

export type Thresholds = {
  look_min: number;
  strong: SignalKey[];
  strong_from: Partial<Record<SignalKey, number>>;
  plan_months: number;
  completion_passed_min_millions: string;
  actual_to_estimate_ratio: string;
  late_direct_min_millions: string;
  late_direct_months: number;
  closing_moves_min: number;
  restructured_levels: number[];
  restructured_months: number;
  disbursement_max_percent: number;
  disbursement_months: number;
};

export type TrackCounts = { n: number | null; k: number | null; few: boolean };
export type TrackRecord = {
  run_id: string;
  ran_on: string;
  dates: string[];
  window_months: number;
  cohort: number;
  min: number;
  status: Record<"needs_a_look" | "watch" | "no_signals", TrackCounts>;
  checks: Record<SignalKey, TrackCounts>;
};

export type Following = {
  as_of: string;
  checked_on: string;
  past: boolean;
  data_through: string | null;
  projects: FollowedProject[];
  counts: Counts;
  thresholds: Thresholds;
  missing: string[];
  evidence: EvidenceEvent[];
  track_record: TrackRecord | null;
  // How many checks project_signals runs, and the sources it reads (config/tools.toml), for the page's words and
  // the coverage line's link to Data readiness.
  checks: number;
  sources: string[];
};

// The order the track record lists the checks in; how many checks run, and the sources they read, are the server's
// (Following's checks and sources).
export const CHECK_ORDER: SignalKey[] = ["completion_passed", "above_estimate", "late_direct", "closing_moves", "restructured", "isr_lowered", "disbursement"];
export const FOLDED: ReadonlySet<Status> = new Set(["no_signals", "closed", "pipeline", "dropped"]);
export const FOLLOWING_HREF = "/projects/following";

// Whether the viewer has the World Bank staff role, from /api/me (App.tsx sets it once per page load): null
// while it loads.
export const staffRole = createStore<boolean | null>(null);

const words = copy.following;

// The finding: "You follow 14 projects. One needs a look, one is worth watching, and 12 have no signals."
export function finding(counts: Counts, statusOfOne: Status | null): string {
  if (counts.total === 1 && statusOfOne) return words.one[statusOfOne];
  if (counts.shown === 0 && counts.not_checked === 0) return words.allQuiet.replace("{total}", formatCount(counts.total));
  const word = (n: number, first: boolean) => formatCount(n, { capital: first });
  const made: string[] = [];
  const add = (n: number, part: (n: number, word: string) => string) => {
    if (n > 0) made.push(part(n, word(n, made.length === 0)));
  };
  add(counts.needs_a_look, words.parts.look);
  add(counts.watch, words.parts.watch);
  add(counts.no_signals, words.parts.none);
  add(counts.closed, words.parts.closed);
  add(counts.pipeline, words.parts.pipeline);
  if (counts.not_checked > 0) {
    const part = words.parts.notChecked(counts.not_checked, formatCount(counts.not_checked));
    made.push(made.length === 0 ? part.charAt(0).toUpperCase() + part.slice(1) : part);
  }
  const joined =
    made.length <= 1 ? made.join("") : made.length === 2 ? made.join(words.partsTwo) : made.slice(0, -1).join(words.partsJoin) + words.partsLast + made.at(-1);
  return words.finding.replace("{total}", formatCount(counts.total)).replace("{parts}", joined);
}

// The status header's number word, from the thresholds file: "three".
export const lookWord = (thresholds: Thresholds) => formatCount(thresholds.look_min);

// The status header's text: "needs a look means three signals or one strong one; ...".
export const statusDef = (thresholds: Thresholds) => words.cols.status.def(lookWord(thresholds));

// The meta line's closing date wording, by the server's closing kind.
export function metaTemplate(project: FollowedProject["project"]): string {
  if (!project.closing_date && project.closing_kind !== "pipeline") return words.meta.undated;
  return words.meta[project.closing_kind ?? "undated"] ?? words.meta.undated;
}

// The reasons a row could not run every check, each once, in the order of the checks.
export function missingReasons(entry: FollowedProject): string[] {
  const seen: string[] = [];
  for (const check of entry.checks) if (check.missing && !seen.includes(check.missing)) seen.push(check.missing);
  return seen;
}

export const shortDate = (iso: string) => formatDate(iso, { style: "table" });

// The record a signal's marker opens: the one its source names, so the marker's name and its drawer agree.
export const markerRecord = (signal: Signal): string | undefined => signal.source.evidence_id ?? signal.items[0]?.evidence_id;
