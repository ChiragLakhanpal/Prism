// The retrieval loop's data on screen (ticket 32): the evidence drawer's feedback row, Lessons > Passage reports
// and Lessons > Judging. Every value comes from the server (src/strata/server/feedback.py); the browser counts,
// rounds and decides nothing, and formats dates and joins words from the copy file only.
import { ApiError, getJson, postJson } from "./api";
import { createStore } from "./store";

// ── The feedback row ─────────────────────────────────────────────────────

export type ReportKind = "wrong_passage" | "not_useful";
export type ReportStatus = "waiting" | "ranked_lower" | "ranked_lower_by_agreement" | "kept";

export type MyReport = {
  report_id: string;
  kind: ReportKind;
  reason: string | null;
  status: ReportStatus;
  reported_on: string;
  decided_on: string | null;
  reviewer_reason: string | null;
  agreeing_count: number | null;
  query_kind: string;
};

// What an answer's evidence event says about the row: whether it shows, why not, and the answer it belongs to.
export type Feedback = {
  allowed: boolean;
  why_not: "record" | "no_question" | "private_upload" | "preview" | null;
  run_id: string | null;
  mode: "pilot" | "scale";
  my_report: MyReport | null;
  // The server's limit on a reason (config/thresholds.toml, retrieval.reason_max_chars).
  limits: { reason_max_chars: number };
};

// Whether the drawer draws the row: for a passage a search found, and disabled in a preview.
export const showsRow = (feedback: Feedback | undefined | null): feedback is Feedback =>
  Boolean(feedback && (feedback.allowed || feedback.why_not === "preview"));

// The viewer's report on each source of each answer, by "{evidence id} {run id}", so reopening the same passage
// for the same answer shows what became of it. undefined: not asked yet.
export const reports = createStore<Record<string, MyReport | null>>({});
export const reportKey = (evidenceId: string, runId: string) => `${evidenceId} ${runId}`;

export async function loadReport(evidenceId: string, runId: string): Promise<void> {
  try {
    const found = await getJson<{ my_report: MyReport | null }>(
      `/api/feedback?evidence_id=${encodeURIComponent(evidenceId)}&run_id=${encodeURIComponent(runId)}`,
    );
    reports.set((held) => ({ ...held, [reportKey(evidenceId, runId)]: found.my_report }));
  } catch {
    // A row that can't read its report starts idle; sending one still works or says why not.
  }
}

export async function sendReport(body: { evidence_id: string; run_id: string; sentence_id: number | null; kind: ReportKind; reason: string | null }): Promise<MyReport> {
  try {
    const sent = await postJson<{ my_report: MyReport }>("/api/feedback", { ...body, view: "staff" });
    reports.set((held) => ({ ...held, [reportKey(body.evidence_id, body.run_id)]: sent.my_report }));
    return sent.my_report;
  } catch (error) {
    // Already sent from another tab: show that report.
    const held = error instanceof ApiError ? (error.body as { code?: string; values?: { my_report?: MyReport } }) : null;
    if (held?.code === "already_sent" && held.values?.my_report) {
      reports.set((all) => ({ ...all, [reportKey(body.evidence_id, body.run_id)]: held.values!.my_report! }));
      return held.values.my_report;
    }
    throw error;
  }
}

export async function withdrawReport(evidenceId: string, runId: string, reportId: string): Promise<void> {
  await postJson(`/api/feedback/${encodeURIComponent(reportId)}/withdraw`, {});
  reports.set((held) => ({ ...held, [reportKey(evidenceId, runId)]: null }));
}

// ── Passage reports ──────────────────────────────────────────────────────

export const REPORTS_HREF = "/lessons/reports";
export const reportHref = (groupId: string) => `${REPORTS_HREF}/${encodeURIComponent(groupId)}`;
export const JUDGING_HREF = "/lessons/judging";
export const queryHref = (queryId: string, passage?: number) =>
  `${JUDGING_HREF}/${encodeURIComponent(queryId)}${passage && passage > 1 ? `?p=${passage}` : ""}`;

export type PassageFields = {
  passage_id: string;
  evidence_id: string;
  project_name: string | null;
  pid: string | null;
  doc_type: string | null;
  doc_date: string | null;
  para: string | null;
  paragraph_numbered: boolean | null;
  section: string | null;
  page: number | null;
  pages: number | null;
};

export type GroupRow = PassageFields & {
  group_id: string;
  kind_label: "wrong_passage" | "not_useful" | "both" | "audit";
  group: "you" | "others";
  audit: boolean;
  query_kind: string;
  report_count: number;
  first_on: string | null;
  own_project: boolean;
  decided_on: string | null;
  agreeing: number | null;
  can: boolean;
  reason_code: string | null;
  state: string;
};

export type DecidedReport = {
  group_id: string;
  project_name: string | null;
  pid: string | null;
  para: string | null;
  paragraph_numbered: boolean | null;
  section: string | null;
  query_kind: string;
  outcome: "ranked_lower" | "kept" | "ranked_lower_by_agreement" | "left_lower" | "restored";
  decided_on: string;
  report_count: number;
};

export type ReportsQueue = {
  mode: "pilot" | "scale";
  audit_every: number;
  silver_min: number;
  lead: { you: number; others: number; oldest_on: string | null };
  groups: { you: GroupRow[]; others: GroupRow[] };
  decided: { window_days: number; total: number; page: number; pages: number; from: number; to: number; rows: DecidedReport[] };
};

export type SentReport = {
  report_id: string;
  role: "staff" | "piu" | "public" | "you";
  is_you: boolean;
  kind: ReportKind;
  reported_on: string;
  question: string;
  sentence: string | null;
  reason: string | null;
  run_id: string;
  own_project: boolean;
};

export type ReportGroup = {
  group_id: string;
  stage: "waiting" | "audit" | "decided";
  kind_label: GroupRow["kind_label"];
  query_kind: string;
  state: string;
  mode: "pilot" | "scale";
  passage: PassageFields & { row: Record<string, any> | null };
  report_count: number;
  first_on: string | null;
  own_project: boolean;
  audit: { decided_on: string; agreeing: number | null } | null;
  reports: SentReport[];
  can: { decide: boolean; reopen: boolean; reason_code: string | null };
  outcome: { outcome: DecidedReport["outcome"]; decided_on: string; reviewer_name: string | null; reason: string | null; agreeing: number | null } | null;
  limits: { reason_max_chars: number };
};

// ── Judging ──────────────────────────────────────────────────────────────

export type Grade = "answers" | "partly" | "not_relevant";
export const GRADES: Grade[] = ["answers", "partly", "not_relevant"];
export type JudgeState = "not_started" | "started" | "finished";

export type QuerySummary = {
  query_id: string;
  n: number;
  query_text: string;
  notice_id: string;
  notice_ref: string | null;
  notice_date: string;
  query_date: string;
  pool: number;
  graded: number;
  my_state: JudgeState;
  other_state: JudgeState;
  agree: number | null;
  locked: boolean;
};

export type Agreement = { agree: number; pairs: number; both_done: number; kappa: number | null; withheld: boolean; min_pairs: number };

export type JudgingList = {
  total: number;
  mine_done: number;
  other_done: number;
  agreement: Agreement;
  show: "to_judge" | "finished_by_you" | "finished_by_both";
  counts: Record<"to_judge" | "finished_by_you" | "finished_by_both", number>;
  next_query: string | null;
  page: number;
  pages: number;
  from: number;
  to: number;
  queries: QuerySummary[];
};

export type PooledPassage = { passage_id: string; passage: Record<string, any>; my_grade: Grade | null; other_grade: Grade | null };

export type JudgingQuery = QuerySummary & { total: number; passages: PooledPassage[]; next_query: string | null };
