// Section 3 of the package workspace, procurement risks and what helped (ticket 30; the 30 brief, section 9):
// what GET /api/packages/{ref}/risks and GET /api/planned-packages/{id}/risks return, the source pill's
// formatter, and the rows and lists the page holds for the evidence drawer.
//
// The risk-table builder (src/strata/packages/risks.py) counts, ranks and checks everything. The page fills copy
// templates, formats numbers and dates through Num, and keeps the person's own selection, nothing else.
import type { EvidenceEvent } from "./answer";
import type { IegStatus } from "./lessons";
import { copy } from "../copy";
import { known, remember } from "./evidence";
import { createStore } from "./store";

export type Locator = { kind: "paragraph" | "section"; text: string };

// A passage a row's lesson rests on: the completion report's paragraph first, then IEG's documents.
export type RiskSource = {
  evidence_id: string;
  passage_id: string;
  role: "source" | "restatement";
  doc_type: string;
  doc_short: string;
  pcode: string;
  project_name: string | null;
  date: string | null;
  para: string;
  locator: Locator;
  page: number | null;
  quote: string;
  public_from: string | null;
};

// A completion report a count lists: its project and document, and, for a row's count, the passage that raised
// the risk.
export type RiskReport = {
  project_id: string;
  project_name: string | null;
  document_id: string;
  version: number | null;
  document_type: string;
  doc_short: string;
  date: string | null;
  public_from: string | null;
  evidence_id?: string;
  passage_id?: string;
  paragraph?: string;
  page?: number | null;
};

export type RiskLesson = {
  id: string;
  evidence_id: string;
  version: number;
  decided_on: string;
  text: string;
  fit: number | null;
  ieg_status: IegStatus;
  review_date: string | null;
  ieg_quote: { text: string; lang: string | null; doc_short: string; evidence_id: string } | null;
};

export type RiskRow = {
  risk_key: string;
  risk_label: string;
  k: number;
  lesson: RiskLesson;
  sources: RiskSource[];
  reports: RiskReport[];
  // Ticket 22's award notices and ticket 23's disagreements have not landed, so these are always null for now.
  related_notices: { count: number; evidence_id: string } | null;
  disagreement: { id: string; changes_claim: boolean } | null;
};

export type RemovedRow = {
  risk_key: string;
  risk_label: string;
  claim_kind: "count" | "helped";
  k: number;
  lesson_text: string;
  check: number;
  reason_code: string;
};

export type RiskChecks = {
  counts: {
    checks_run: number[];
    sentences: { written: number; kept: number; removed: number };
    numbers: { total: number; matched: number };
    dates: { total: number; matched: number };
    quotes: { total: number; found: number };
  };
  tools: string[];
  judge_failed: boolean;
  unjudged: number;
  removed: RemovedRow[];
};

export type EmptyReason = "missing_criteria" | "no_comparables" | "no_reports" | "no_lessons" | "all_removed";

export type RisksResult = {
  rows: RiskRow[];
  p: number | null;
  m: number | null;
  most_common: { risk_keys: string[]; k_max: number } | null;
  max_rows: number;
  coverage: { missing: { reason_code: string; count: number }[]; sources: string[] };
  counted: RiskReport[];
  verifier: RiskChecks | null;
  empty_reason: EmptyReason | null;
  missing: string[];
  written: number | null;
  selected_keys: string[];
  selected_not_shown: { risk_key: string; risk_label: string }[];
  counts_evidence_id: string | null;
  source_names: string[];
  data_through: string | null;
  as_of: string | null;
};

// Where each kind of package keeps its section and its selection.
export const risksPath = (base: string) => `${base}/risks`;
export const selectionPath = (base: string) => `${base}/risk-selection`;

// ── The source pill ──────────────────────────────────────────────────────

function fill(template: string, slots: Record<string, string>): string {
  return template.replace(/\{(\w+)\}/g, (slot, name: string) => slots[name] ?? slot);
}

// "¶54" for a numbered paragraph, or the section number the document uses, "10.b".
export function locatorText(locator: Locator, spoken = false): string {
  const words = copy.packageRisks;
  if (locator.kind === "section") return locator.text;
  return fill(spoken ? words.pillParagraphSpoken : words.pillParagraph, { para: locator.text });
}

// One formatter for every pill: "{doc_short} {pcode} {locator}", such as "ICR P130164 ¶54", or without the
// P-code for a later pill from the same project, "ICR Review 10.b". The PPSD draft's footnotes reuse it (the 36
// brief, section 6.3).
export function pillText(source: { doc_short: string; pcode: string; locator: Locator }, withProject = true, spoken = false): string {
  const words = copy.packageRisks;
  const slots = { doc: source.doc_short, pcode: source.pcode, locator: locatorText(source.locator, spoken) };
  return fill(withProject ? words.pill : words.pillNoProject, slots);
}

// Each of a row's sources with whether its pill shows the P-code: a later pill from the same project drops it.
export function pillsOf(sources: RiskSource[]): { source: RiskSource; withProject: boolean }[] {
  return sources.map((source, index) => ({ source, withProject: !sources.slice(0, index).some((before) => before.pcode === source.pcode) }));
}

// ── The rows and lists the page holds for the evidence drawer ────────────

// A row's count opens the completion reports that raised its risk, and the finding's {m} every report counted.
// Neither is a source on the server: the page that draws the section holds them, as the past range's dots are.
export const REPORTS = "risk-reports:";
export const ALL_REPORTS = "risk-reports-all:";

export const reportsId = (packageKey: string, riskKey: string) => `${REPORTS}${packageKey}:${riskKey}`;
export const allReportsId = (packageKey: string) => `${ALL_REPORTS}${packageKey}`;
export const isRiskList = (id: string | null | undefined) => Boolean(id && (id.startsWith(REPORTS) || id.startsWith(ALL_REPORTS)));

export type ReportsRow = { risk_key: string; risk_label: string; k: number; m: number; entries: RiskReport[] };
export type AllReportsRow = { m: number; entries: RiskReport[] };

export function reportsList(packageKey: string, row: RiskRow, m: number): EvidenceEvent {
  return {
    id: reportsId(packageKey, row.risk_key),
    kind: "risk-reports",
    tool: "get_lessons",
    stratum: "Why",
    short_name: null,
    row: { risk_key: row.risk_key, risk_label: row.risk_label, k: row.k, m, entries: row.reports } satisfies ReportsRow,
    highlights: [],
  };
}

export function allReportsList(packageKey: string, result: RisksResult): EvidenceEvent {
  return {
    id: allReportsId(packageKey),
    kind: "risk-reports-all",
    tool: "get_lessons",
    stratum: "Why",
    short_name: null,
    row: { m: result.m ?? 0, entries: result.counted } satisfies AllReportsRow,
    highlights: [],
  };
}

// The rows on the page, so a drawer opened at one of their sources, from a pill or from the address after a
// reload, can show the row's claim, its IEG line and its switcher (the 30 brief, section 5.4).
export const pageRows = createStore<RiskRow[]>([]);

// Hold the section's rows and lists. A rerun's replace the earlier ones.
export function rememberRisks(packageKey: string, result: RisksResult) {
  pageRows.set(result.rows);
  if (result.m) remember(allReportsList(packageKey, result));
  for (const row of result.rows) remember(reportsList(packageKey, row, result.m ?? 0));
}

export function forgetRisks() {
  pageRows.set([]);
}

// The one row whose sources hold this evidence id, or null when none or more than one does: a claim shows only
// when it is the claim the source was opened for.
export function rowOf(id: string, rows: RiskRow[] = pageRows.get()): RiskRow | null {
  const holding = rows.filter((row) => row.sources.some((source) => source.evidence_id === id));
  return holding.length === 1 ? holding[0] : null;
}

// Whether a list the drawer was asked for is one the page holds now.
export const heldList = (id: string) => Boolean(known.get()[id]);
