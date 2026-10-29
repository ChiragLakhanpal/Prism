// Section 1's "Advertised again" block (ticket 28; the 28 brief, section 5): what GET
// /api/packages/{ref}/rebidding and GET /api/rebidding return (the rebidding_risk tool), where each kind of package
// asks for it, and the cases the page holds for the evidence drawer.
//
// The tool counts, groups, orders and rounds everything, and decides whether its model is shown. The page fills
// copy templates and formats numbers and dates through Num, nothing else.
import { createStore } from "./store";

export type RebidEvidence = {
  evidence_id: string;
  public_from: string;
  record_kind: "notice" | "award_notice" | "plan_row";
  // The notice's id, or the plan row's STEP reference.
  reference: string;
  // The notice's date, or the plan version's.
  date: string;
  agency: string | null;
};

export type RebidCase = {
  evidence_id: string;
  public_from: string;
  step_reference: string;
  project_id: string | null;
  country_name: string | null;
  reason_code: string;
  row_kind: "quote" | "again" | "no_award" | "canceled_row";
  quote: { text: string; lang: string; notice_id: string } | null;
  dates: { notice_date: string | null; bids_due: string | null; again_on: string | null; plan_date: string | null };
  process_status: string | null;
  evidence: RebidEvidence[];
  label_sources: string[];
  rank: number;
};

export type RebidGroup = { reason_code: string; count: number; step_references: string[] };

export type RebidModel = {
  shown: boolean;
  in10: number | null;
  band: "below_1" | "about" | "above_9" | null;
  not_shown_reason: "too_few" | "not_better" | "no_results" | "not_scored" | "not_in_plan" | null;
  min_comparables: number;
  learner: string | null;
  track_record: { n_test: number; test_year: number; beat_baseline: boolean; baseline_code: string; run_date: string } | null;
  score_date: string | null;
};

export type RebiddingResult = {
  tool: "rebidding_risk";
  as_of: string;
  view: string;
  rows: RebidCase[];
  abstention: { reason: string } | null;
  m: number;
  n: number;
  past_range_total: number;
  denominator_reason: string | null;
  groups: RebidGroup[];
  model: RebidModel;
  sources: { key: string; dataset_name: string }[];
  notice_source_keys: string[];
  records_through: string | null;
  // The rows each group shows before "Show {n} more" (config/thresholds.toml, rebidding.rows_per_group).
  rows_per_group: number;
};

// Where each kind of package asks: a STEP row by its reference, a package planned from a sentence by its criteria.
export const rebiddingPath = (base: string) => `${base}/rebidding`;

export function plannedRebiddingPath(query: Record<string, string>): string {
  const params = new URLSearchParams(Object.entries(query).sort(([a], [b]) => a.localeCompare(b)));
  return `/api/rebidding?${params.toString()}`;
}

// The cases on the page, with the day their records run through, so a drawer opened at one of their records, from
// a marker or from the address after a reload, can show the row's claim and its switcher.
export type PageCases = { rows: RebidCase[]; through: string | null };
export const pageCases = createStore<PageCases>({ rows: [], through: null });

// The one case whose records hold this evidence id, or null when none or more than one does.
export function caseOf(id: string, cases: RebidCase[] = pageCases.get().rows): RebidCase | null {
  const holding = cases.filter((one) => one.evidence.some((item) => item.evidence_id === id));
  return holding.length === 1 ? holding[0] : null;
}

// The evidence ids the block's markers cite, in the order the page draws them: group by group, row by row, the
// rows not shown yet included, so a number never changes when the list opens (the 28 brief, section 6.4).
export function citedIds(result: RebiddingResult): string[] {
  const byRef = new Map(result.rows.map((row) => [row.step_reference, row]));
  return result.groups.flatMap((group) => group.step_references.flatMap((ref) => byRef.get(ref)?.evidence.map((item) => item.evidence_id) ?? []));
}
