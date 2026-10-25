// Section 5 of the package workspace, "Check your criteria" (ticket 31): what the server returns, and the drawer's
// views the section holds on the page.
//
// GET .../criteria is the collapsed summary, read with the page; POST .../criteria/run streams the package-level
// run (rejected bids, the cost estimate and the lessons); POST .../criteria/compare streams a comparison of pasted
// qualification criteria (src/strata/server/criteria.py). Every number below is a tool's or the verifier's: the
// browser counts nothing (CLAUDE.md rule 1). The pasted text travels only in a request body, never in an address.
//
// Three drawer views come from data already on the page, so the drawer opens at once (the 31 brief, section 5.6):
// the packages whose criteria are public (criteria-public:{key}), the notices behind one item
// (criteria-item:{check_id}:{item_key}) and a comparable package's cost records (package-cost:{step_ref}). The
// section remembers them in the evidence store, as ticket 15's quantile dots do, and the drawer never asks the
// server for them.
import type { EvidenceEvent } from "./answer";
import { remember } from "./evidence";

export const CRITERIA_PUBLIC = "criteria-public:";
export const CRITERIA_ITEM = "criteria-item:";
export const PACKAGE_COST = "package-cost:";

// Whether the drawer finds this id on the page rather than on the server.
export function heldOnPage(id: string): boolean {
  return id.startsWith(CRITERIA_PUBLIC) || id.startsWith(CRITERIA_ITEM) || id.startsWith(PACKAGE_COST);
}

export type Counts = { total: number; matched: number };
export type Checks = {
  checks_run: number[];
  sentences: { written: number; kept: number; removed: number };
  numbers: Counts;
  dates: Counts;
  quotes: { total: number; found: number };
  sources: { total: number; returned: number };
  quotes_without_pages: number;
};
export type RemovedEntry = {
  index: number;
  sentence: string;
  reason: string;
  reasons: { check: number; code: string; text: string | null }[];
  about: string;
};
export type Limits = {
  max_chars: number;
  counter_left: number;
  rows_per_group: number;
  lessons_per_group: number;
  lesson_factors: string[];
  min_comparables: number;
};
export type PublicEntry = { step_reference: string; notice_id: string; notice_date: string | null; country_name: string | null; passage_id: string };

export type RejectedRow = {
  evidence_id: string;
  public_from: string;
  step_reference: string;
  country_name: string | null;
  notice_id: string;
  notice_date: string | null;
  item_key: string;
  reason: { quote: string; lang: string };
  bids: number;
  rank: number;
  removed: boolean;
};
export type RejectedGroup = { item_key: string; count: number; rows: number; label: string; phrase: string };
export type Rejected = {
  state: "ok" | "none_rejected" | "no_award_notices" | "no_comparables";
  counts: { total: number; m: number; n: number };
  groups: RejectedGroup[];
  rows: RejectedRow[];
  sources: { key: string; dataset_name: string }[];
  records_through: string | null;
};

export type CostContract = { contract_id: string; amount_usd: string; signed_on: string | null };
export type CostRow = {
  evidence_id: string;
  step_reference: string;
  project_id: string | null;
  country_code: string | null;
  country_name: string | null;
  description: string | null;
  estimated_amount_usd: string;
  signed_amount_usd: string;
  diff_pct: number;
  contracts: CostContract[];
  rank: number;
  source: { plan: { document_id: string; plan_date: string | null; pdf_page: number; implementing_agency: string | null }; contract_ids: string[] };
};
export type Cost = {
  rows: CostRow[];
  coverage: { matched: number; used: number; not_used: { reason: string; count: number; evidence_ids: string[] }[] };
  package: { step_reference: string | null; estimated_amount_usd: string | null; evidence_id: string | null; given: boolean };
  counts: { total: number; m: number; open: number; no_estimate: number; no_usd: number; above: number; below: number; at: number };
  band: { low_usd: string; high_usd: string } | null;
  quartiles: { q25: number; q50: number; q75: number } | null;
  quantile_dots: { k: number; diff_pct: number; count: number; step_references: string[] }[] | null;
  min_comparables: number;
  sources: { key: string; dataset_name: string }[];
  records_through: string | null;
  abstention: { reason: string; count?: number } | null;
  as_of: string;
};

export type LessonEntry = {
  lesson_id: string;
  version: number;
  statement: string;
  ieg_status: string;
  evidence_id: string;
  passage_evidence_id: string;
  passage_id: string;
  quote: string;
  document_type: string;
  doc_short: string;
  project_id: string;
  document_date: string | null;
  para: string | null;
  locator: "paragraph" | "section";
  page: number | null;
  // The paragraph the quote is in, the quote's place in it and the paragraph's language, for the card's excerpt;
  // null when the paragraph could not be read.
  excerpt: { text: string; range: number[] | null; lang: string } | null;
  removed: boolean;
};
export type LessonGroup = { factor: string; lessons: LessonEntry[] };

export type PackageRun = {
  check_id: string;
  signature: string;
  records_through: string | null;
  as_of: string;
  labels: Record<string, { label: string; phrase: string }>;
  rejected: Rejected;
  cost: Cost;
  lessons: { state: "ok" | "none"; groups: LessonGroup[] };
  checks: Checks;
  removed: RemovedEntry[];
  section_checks?: Checks | null;
};

export type Relation = "less" | "same" | "more" | "different";
export type ItemNotice = {
  step_reference: string;
  country_name: string | null;
  notice_id: string;
  notice_date: string | null;
  relation: Relation;
  requirement: { text: string; lang: string; start: number; end: number };
  passage_id: string;
};
export type ComparedItem = {
  item_key: string;
  label: string;
  phrase: string;
  your_excerpt: { text: string; shortened: boolean };
  reading: string | null;
  reading_removed: boolean;
  stated: number;
  compared: number;
  less: number;
  same: number;
  more: number;
  different: number;
  same_or_less: number;
  not_stated: number;
  rejected_packages: number;
  notices: ItemNotice[];
};
export type Refusal = { key: "live_tenders" | "review_decisions"; partial: boolean };
export type Comparison = {
  check_id: string;
  compared_at: string;
  signature: string;
  records_through: string | null;
  as_of: string | null;
  refusal: Refusal | null;
  content_filtered: boolean;
  items: ComparedItem[];
  // How many items the reader found and the app compared: the server counts them, never the browser.
  item_count: number;
  unplaced: string[];
  fx_count: number;
  coverage: { n: number; total: number; open: number; missing: number } | null;
  sources: { key: string; dataset_name: string }[];
  checks: Checks | null;
  removed: RemovedEntry[];
  section_checks?: Checks | null;
};
export type SavedComparison = {
  check_id: string;
  status: string;
  pasted_text: string | null;
  result: Comparison | null;
  // False when the newest comparison failed after its text was saved: the table is the last one that finished,
  // from earlier text.
  text_compared: boolean;
  stale: boolean;
  compared_at: string;
};

export type CriteriaSummary = {
  state: "ok" | "none_public" | "no_comparables" | "not_measurable";
  comparables_total: number;
  public_criteria_count: number;
  public: PublicEntry[];
  signature: string;
  records_through: string | null;
  limits: Limits;
  comparison: SavedComparison | null;
  package_run: PackageRun | null;
  section_checks: Checks | null;
  public_sources: string[];
};

// ── The drawer's views from the page ─────────────────────────────────────

export function publicListId(key: string): string {
  return `${CRITERIA_PUBLIC}${key}`;
}

export function itemListId(checkId: string, itemKey: string): string {
  return `${CRITERIA_ITEM}${checkId}:${itemKey}`;
}

export function costRecordId(stepRef: string): string {
  return `${PACKAGE_COST}${stepRef}`;
}

// The drawer's view of each list or record the section holds, as the evidence store keeps it.
export function publicListEvent(key: string, entries: PublicEntry[]): EvidenceEvent {
  return { id: publicListId(key), kind: "criteria_public", tool: "compare_criteria", stratum: "What", short_name: null,
    row: { count: entries.length, entries }, highlights: [] };
}

export function itemListEvent(comparison: Comparison, item: ComparedItem): EvidenceEvent {
  return { id: itemListId(comparison.check_id, item.item_key), kind: "criteria_item", tool: "compare_criteria", stratum: "What",
    short_name: null, row: { ...item, public: comparison.coverage?.n ?? 0, count: item.notices.length }, highlights: [] };
}

export function costRecordEvent(row: CostRow): EvidenceEvent {
  return { id: costRecordId(row.step_reference), kind: "package_cost", tool: "compare_cost_estimates", stratum: "How",
    short_name: null, row, highlights: [] };
}

export function rememberPublic(key: string, entries: PublicEntry[]) {
  remember(publicListEvent(key, entries));
}

export function rememberItems(comparison: Comparison) {
  for (const item of comparison.items) remember(itemListEvent(comparison, item));
}

export function rememberCosts(cost: Cost) {
  for (const row of cost.rows) remember(costRecordEvent(row));
}
