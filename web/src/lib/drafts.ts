// Drafts in the browser (ticket 35): the shapes the draft routes answer with (src/strata/server/drafts.py),
// the acts a draft's author takes, the writing stream, and what one page hands the next. Every count a
// draft screen states comes from the server; nothing here counts sources, notes or citations.
import { currentLanguage } from "./lang";
import type { ChecksEvent, DisagreementEvent, EvidenceEvent, RemovedEvent, SentenceEvent } from "./answer";
import { ApiError, postJson, putJson } from "./api";
import type { Activity, CheckPlanResult } from "./api";
import { streamEvents, StreamError } from "./sse";
import { createStore } from "./store";

export type DraftState = "draft" | "checked" | "exported" | "discarded";
export type Who = { at: string; by: string | null; you: boolean };

export type DraftNote = {
  key: string;
  activity_reference_no: string;
  evidence_id: string;
  description: string | null;
  mark: "needs_a_look" | "watch";
  state: "written" | "abstained" | "refused";
  refusal: string | null;
  sentences: SentenceEvent[];
  // A mission brief's part (ticket 37): why it has no records, the records its table shows, and its totals.
  part?: string;
  reason?: string | null;
  table?: BriefRecord[];
  totals?: Record<string, any> | null;
  agencies_without_plans?: string[];
  // A suggested PPSD row's cell (ticket 36): its key, the row it belongs to and which of Strata's two cells it is.
  cell_key?: string;
  row_key?: string;
  cell?: "risk_description" | "mitigation";
  // A Project Paper summary's part (ticket 36): the PPSD drafts it drew on, and the track record's counts.
  drafts?: { draft_id: string; package_title: string | null; checked_by: string | null; checked_at: string | null; rows: number }[];
  counts?: Record<string, number | null> | null;
  packages?: { evidence_id: string; step_reference: string; first_planned_on: string | null; signed_on: string | null; state: string }[];
  signed_from?: string;
};

// One record behind a mission brief's part (project_records): its fields by key, as the evidence drawer shows it.
export type BriefRecord = {
  evidence_id: string;
  public_from: string;
  part: string;
  reference: string;
  source: { source_key: string; document_type: string; project_id: string; document_date: string | null };
  fields: { key: string; value: any; kind: string }[];
};

export type DraftSource = {
  evidence_id: string;
  number: number;
  cited_in: string[];
  opened: boolean;
  last_opened_at: string | null;
};

export type DraftSubject = {
  project_id: string;
  project_name: string;
  implementing_agency: string;
  agency_id: string;
  plan_date: string;
  document_id: string;
  pdf_url: string | null;
  signal: number;
  // A mission brief's (ticket 37).
  country?: string | null;
  as_of?: string;
  // The data-freshness day the brief's records run through.
  data_through?: string | null;
  isr_date?: string | null;
  isr_sequence?: number | null;
  closing_date?: string | null;
  // Suggested PPSD rows' package (ticket 36): its title, its STEP reference or none yet, and a planned package's id.
  package_title?: string;
  step_reference?: string | null;
  package_id?: string | null;
  // The Project Paper summary's count of the project's implementing agencies with plans (ticket 36).
  agencies_with_plans?: number | null;
};

export type DraftFile = { name: string; media_type: string; size: number };

// The kinds of draft (config/drafts.toml); each has its words under copy.draft.kinds.<kind>.
// Ticket 38 adds an implementing agency's planned dates and its own PPSD rows.
export type DraftKind = "review_notes" | "mission_brief" | "ppsd_rows" | "project_paper" | "step_rows" | "ppsd_rows_agency";
// Suggested PPSD rows and the agency's own, which share one workflow and one page.
export const isPpsdKind = (kind: string | null | undefined) => kind === "ppsd_rows" || kind === "ppsd_rows_agency";

// A hold that keeps a draft from export (config/drafts.toml): how many items it has left, and the anchor of the
// first, which the bar's hold line links to (ticket 36).
export type Hold = { key: string; copy: string; left: number; first_anchor: string | null };

// Suggested PPSD rows (ticket 36): the template registry's columns for each form, the guidance's ratings and stages,
// the Table I result, the rows, the values people set and the counts the progress line states. Every count is the
// server's.
export type PpsdColumn = {
  key: string;
  header: string;
  letter: string | null;
  filled_by: "strata" | "people";
  control: "text" | "rating" | "score" | "stage" | null;
  hold: "owners" | "ratings" | null;
  max_length: number | null;
};
export type PpsdSource = {
  evidence_id: string;
  doc_short: string;
  doc_type: string;
  pcode: string;
  locator: { kind: string; text: string };
  page: number | null;
  date: string | null;
};
export type PpsdRow = {
  row_key: string;
  risk_key: string;
  risk_label: string;
  k: number;
  m: number;
  counts_evidence_id: string;
  lesson: { id: string; evidence_id: string; version: number; decided_on: string | null };
  sources: PpsdSource[];
  cells: { risk_description: string; mitigation: string };
  removed?: boolean;
};
export type TableI = { applies: boolean; amount: string | null; threshold: string | null; currency: string; category: string | null; risk_level: string };
export type PpsdView = {
  form: "short" | "long";
  forms: Record<"short" | "long", { name: string; columns: PpsdColumn[] }>;
  ratings: { value: number; label: string; short: string }[];
  score: { definition: string; minimum: number; maximum: number };
  stages: string[];
  table_i: TableI;
  selected: number;
  rows: PpsdRow[];
  values: { row_key: string; field: string; value: string | null }[];
  counts: { total: number; owners_set: number; rated: number };
};
// One footnote per marker (ticket 36): the sources the marker carries and the text Word gets, which the page shows
// as its "In Word:" line.
export type Footnote = { number: number; evidence_ids: string[]; text: string; row_key: string; cell: string; sentence: number; position: number };
// Planned dates (ticket 38): the one choice, each activity with its steps as estimate_time dated them, the counts the
// page states, and STEP's columns the file leaves to people. Every date and count is the server's.
export type DatesChoice = { planned_date: string | null; days: number | null; days_relation: string | null; longer: number | null; in10: number | null };
export type DatesStep = {
  step_key: string;
  label: string | null;
  step_name: string | null;
  is_anchor: boolean | null;
  comparables_n: number | null;
  abstain_reason: string | null;
  plan_first_date: string | null;
  middle: DatesChoice | null;
  cautious: DatesChoice | null;
  list_id: string;
  removed: string[] | null;
};
export type DatesActivity = {
  key: string;
  position: number;
  reference: string | null;
  description: string | null;
  section: string | null;
  fields: Record<string, string | null>;
  family: string | null;
  family_reason: string | null;
  basis: string | null;
  needs_start_date: boolean | null;
  abstain_all: { n: number } | null;
  steps: DatesStep[];
  // The steps that can take a date and how many each choice dated, counted by the server after the verifier.
  counts: { steps: number; dated: { middle: number; cautious: number } };
};
export type DatesView = {
  choice: "middle" | "cautious";
  activities: DatesActivity[];
  counts: { activities: number; steps: number; dated: { middle: number; cautious: number }; lists: number; no_family: number };
  min_comparables: number | null;
  // About how many in 10 comparable packages ran later than the cautious date, from the thresholds file.
  cautious_in10: number;
  left_to_people: string[];
  csv_columns: string[];
};
export type SummaryView = {
  agencies_with_plans: number | null;
  ppsd_rows: number;
  parts: { part: string; reason: string | null; state: string | null }[];
};

export type Draft = {
  draft_id: string;
  kind: DraftKind;
  state: DraftState;
  discarded_from: DraftState | null;
  author: { name: string | null; you: boolean };
  created_at: string;
  checked: Who | null;
  discarded: Who | null;
  subject: DraftSubject;
  counts: { signal: number; written: number };
  // Suggested PPSD rows also keep how many rows the writer wrote (ticket 36): two cells each.
  written: { notes: number; sentences: number; rows?: number };
  notes: DraftNote[];
  evidence: Record<string, EvidenceEvent>;
  // The language the writer wrote it in, when it is not English (ticket 42).
  lang?: string;
  checks: ChecksEvent;
  // How many checks the verifier ran on this draft.
  checks_count: number;
  removed: (RemovedEvent & { key: string })[];
  sources: DraftSource[];
  citations: number;
  opened: { count: number; of: number };
  layout: { columns: string[]; export: "word" | "step_rows"; sources_list: boolean; removed_box: "always" | "when_removed"; not_checked: string[] };
  holds: Hold[];
  // Ticket 36: suggested PPSD rows' form, fields and footnotes, a summary's parts, and the disagreements check 6
  // attached with the report kept on each.
  ppsd?: PpsdView;
  footnotes?: Footnote[];
  summary?: SummaryView;
  dates?: DatesView;
  disagreements?: DisagreementEvent[];
  choices?: { disagreement_id: string; kept: "lean" | "other"; reason: string | null; at: string | null; by: string | null }[];
  // A state made up for layout only (tests/record_ppsd_api.py), never a finding.
  made_up?: string;
  may_act: boolean;
  export: {
    export_id: string;
    exported_at: string;
    by: string | null;
    you: boolean;
    footnotes: number;
    sources: number;
    opened: number;
    // How many sources the author kept in place of one Strata leaned on, with a reason (ticket 23).
    disagreements: number;
    files: DraftFile[];
    files_available: boolean;
  } | null;
};

export type DraftRow = {
  draft_id: string;
  kind: DraftKind;
  state: DraftState;
  subject: DraftSubject;
  notes: number;
  author: { name: string | null; you: boolean };
  created_at: string;
  changed: Who;
  // When the notes were marked as checked and exported, by whom: a restore is not a check.
  checked: Who | null;
  exported: Who | null;
  opened: { count: number; of: number } | null;
  // Suggested PPSD rows' progress (ticket 36): owners set and rows rated, from the server.
  progress?: { total: number; owners_set: number; rated: number; form: "short" | "long"; rows: number };
};

export type DraftGroup = "to_check" | "checked" | "exported";
export type DraftList = {
  groups: Record<DraftGroup, DraftRow[]>;
  counts: Record<DraftGroup, number>;
  discarded: DraftRow[];
  discarded_count: number;
  total: number;
};

export type ExistingDraft = { draft_id: string; created_at: string; author: { name: string | null; you: boolean } };
// GET /api/drafts/existing: with a plan date, the open draft on that version; with none, the open draft on
// each version of the agency's plans, by its date.
export type Existing = { draft: ExistingDraft | null } | { by_plan_date: Record<string, ExistingDraft> };

export type Action = "check" | "export" | "discard" | "restore";

// An act the server refused: a preview, not the author, a state another tab changed, or a hold.
export type Refusal = { code: string; state?: DraftState; holds?: string[] };

export async function act(draft: Draft, action: Action, view: string | null): Promise<Draft> {
  return postJson<Draft>(`/api/drafts/${encodeURIComponent(draft.draft_id)}/${action}`, {
    expected_state: draft.state,
    view: view === "piu" || view === "public" ? view : "staff",
  });
}

export function refusalOf(error: unknown): Refusal | null {
  return error instanceof ApiError && (error.status === 409 || error.status === 403) ? (error.body as Refusal) : null;
}

// The app's own store of drafts refused or is missing: not the viewer's account, and nothing they can fix.
export function storeFailed(error: ApiError | null): boolean {
  return error?.body.code === "draft_store" || error?.body.code === "no_data_service";
}

export function fileHref(draftId: string, name: string): string {
  return `/api/drafts/${encodeURIComponent(draftId)}/files/${encodeURIComponent(name)}`;
}

// The draft page's address, and the writing page's for a plan version.
export const draftHref = (draftId: string) => `/drafts/${encodeURIComponent(draftId)}`;
export function writingHref(pid: string, agencyId: string, version: string, kind: DraftKind = "review_notes"): string {
  return `/drafts/new?${new URLSearchParams({ kind, pid, agency: agencyId, version }).toString()}`;
}
export const ppsdWritingHref = (packageId: string, kind: DraftKind = "ppsd_rows") =>
  `/drafts/new?${new URLSearchParams({ kind, package: packageId }).toString()}`;
// Planned dates (ticket 38): the writing page for an upload or a published plan, named by its id only.
export const datesWritingHref = (source: string) => `/drafts/new?${new URLSearchParams({ kind: "step_rows", from: source }).toString()}`;

// A person's own value on a field only people fill (ticket 36): a risk owner, a rating, the score or the stage, or
// its removal (null). The server answers with the draft as its page now shows it.
export function setField(draft: Draft, rowKey: string, field: string, value: string | null, view: string | null): Promise<Draft> {
  return putJson<Draft>(`/api/drafts/${encodeURIComponent(draft.draft_id)}/fields`, {
    row_key: rowKey, field, value, view: view === "piu" || view === "public" ? view : "staff",
  });
}

export function setForm(draft: Draft, form: "short" | "long", view: string | null): Promise<Draft> {
  return putJson<Draft>(`/api/drafts/${encodeURIComponent(draft.draft_id)}/form`, {
    form, view: view === "piu" || view === "public" ? view : "staff",
  });
}

// The latest value a person set on one field of one row.
export function valueOf(draft: Draft, rowKey: string, field: string): string | null {
  return draft.ppsd?.values.find((entry) => entry.row_key === rowKey && entry.field === field)?.value ?? null;
}

// ── Writing ──────────────────────────────────────────────────────────────

export type WriteStep = {
  id: "read" | "write" | "check" | "save";
  status: "running" | "done";
  plan_date?: string;
  // What suggested PPSD rows' and a Project Paper summary's read step read, and the rows the writer wrote (ticket 36).
  selected?: number;
  rows?: number;
  packages?: number;
  ppsd_rows?: number;
  // What a mission brief's read step read (ticket 37).
  plans?: number;
  awards?: number;
  isrs?: number;
  count?: number;
  notes?: number;
  sentences?: number;
  checks_run?: number[];
  checks?: number;
  written?: number;
  removed?: number;
};

// A draft being written: what Check a plan handed over, and the stream's events so far.
export type Writing = {
  // A mission brief (ticket 37) names only its project; suggested PPSD rows (ticket 36) name their package, and its
  // section 1 criteria for a package from a STEP row.
  request: {
    kind: DraftKind;
    project_id?: string;
    agency_id?: string;
    plan_date?: string;
    package?: string;
    criteria?: Record<string, string | number>;
    // Planned dates (ticket 38): upload:{id} or plan:{pid}:{agency}:{date}.
    source?: string;
    idempotency_key: string;
    // The language of answers and drafts in effect when the person asked (ticket 42), fixed for the draft.
    lang?: string;
  };
  // The plan check the client held when the person asked, for the activity cells that show at once; none for a
  // mission brief, which shows its project and its five part headings instead.
  plan: CheckPlanResult | null;
  rows: Activity[];
  project?: { project_id: string; project_name: string; country: string | null };
  // Suggested PPSD rows' package as the workspace showed it, and how many risks were selected, for the header and
  // the skeleton rows (ticket 36).
  package?: { id: string; title: string; step_reference: string | null; selected: number };
  // The Project Paper summary's plan, for its header (ticket 36).
  summaryPlan?: { project_id: string; project_name: string; agency_id: string; implementing_agency: string; plan_date: string };
  // Planned dates (ticket 38): the upload or plan they are drafted from, for the header, and what the server counted
  // when no step could be dated.
  datesPlan?: { project_id: string; project_name: string; implementing_agency: string; date: string; upload: boolean; back: string };
  nothingDated?: { activities: number; steps: number; min_comparables: number | null };
  phase: "writing" | "done" | "nothing" | "failed" | "dropped";
  steps: WriteStep[];
  draftId: string | null;
  removed: RemovedEvent[];
  checks: ChecksEvent | null;
  error: string | null;
  // What an error tells the data team to look for: the run's trace id, or else its run id.
  reference: string | null;
  lastEventAt: number;
};

export const writing = createStore<Writing | null>(null);
// The draft the writing page saved, so the draft page opens on it without loading it again.
export const preloaded = createStore<Record<string, Draft>>({});
// Check a plan's notice after "Stop writing", shown once.
export const stopped = createStore<string | null>(null);
// What the Project Paper summary's Stop writing adds to the plan check's address in that store, so the check's
// notice names the summary (ticket 36).
export const PROJECT_PAPER_STOPPED = "#project_paper";
// The project a draft page is about, for the box's scope chip (App.tsx).
export const draftScope = createStore<string | null>(null);

let stopping: AbortController | null = null;

function update(change: (current: Writing) => Writing) {
  writing.set((current) => (current ? change({ ...current, lastEventAt: Date.now() }) : current));
}

function withEvent(current: Writing, type: string, data: any): Writing {
  switch (type) {
    case "step": {
      const step = data as WriteStep;
      const steps = current.steps.some((one) => one.id === step.id)
        ? current.steps.map((one) => (one.id === step.id ? step : one))
        : [...current.steps, step];
      return { ...current, steps };
    }
    case "draft":
      return { ...current, draftId: String(data.draft_id), phase: "done" };
    case "nothing_dated":
      return { ...current, phase: "nothing", nothingDated: { activities: data.counts?.activities ?? 0, steps: data.counts?.steps ?? 0,
        min_comparables: data.min_comparables ?? null } };
    case "nothing_survived":
      return { ...current, phase: "nothing", removed: data.removed as RemovedEvent[], checks: data.checks as ChecksEvent };
    case "error":
      return { ...current, phase: "failed", error: String(data.code ?? "internal") };
    case "done":
      return { ...current, reference: data.trace_ids?.application_insights ?? data.run_id ?? null };
    default:
      return current;
  }
}

// Start writing: one request with one idempotency key, so a double click or React's StrictMode never
// starts two writers. A writing already started for the same key is left alone.
export function startWriting(request: Writing["request"], plan: CheckPlanResult | null, rows: Activity[], project?: Writing["project"],
  extra: Pick<Writing, "package" | "summaryPlan" | "datesPlan"> = {}) {
  const current = writing.get();
  if (current && current.request.idempotency_key === request.idempotency_key && current.phase === "writing") return;
  stopping?.abort();
  stopping = new AbortController();
  request = { ...request, lang: request.lang ?? currentLanguage() };
  writing.set({ request, plan, rows, project, ...extra, phase: "writing", steps: [], draftId: null, removed: [], checks: null,
    error: null, reference: null, lastEventAt: Date.now() });
  void run(request, stopping.signal);
}

// "Suggest {n} PPSD risk rows" on the package workspace (ticket 36): start the writer for the package, and the
// writing page's address. The server reads the risks selected in section 3 itself; the request never carries them.
export function startPpsdRows(pkg: NonNullable<Writing["package"]>, criteria: Record<string, string | number> | null,
  kind: DraftKind = "ppsd_rows"): string {
  startWriting({ kind, package: pkg.id, ...(criteria ? { criteria } : {}), idempotency_key: newKey() }, null, [],
    undefined, { package: pkg });
  return ppsdWritingHref(pkg.id, kind);
}

// "Draft planned dates ({n} activities)" on an upload's check (ticket 38): start dating its steps, and the writing
// page's address. The request names the upload by its id only.
export function startDates(upload: { upload_id: string; uploaded_on: string; project_id: string },
  check: { plan: { implementing_agency: string } | null; project: { project_name: string; display_name?: string | null } | null }): string {
  const source = `upload:${upload.upload_id}`;
  startWriting({ kind: "step_rows", source, idempotency_key: newKey() }, null, [], undefined, {
    datesPlan: { project_id: upload.project_id, project_name: check.project?.display_name ?? check.project?.project_name ?? "",
      implementing_agency: check.plan?.implementing_agency ?? "", date: upload.uploaded_on, upload: true,
      back: `/packages/uploads/${encodeURIComponent(upload.upload_id)}` } });
  return datesWritingHref(source);
}

// "Draft a Project Paper summary" at the end of Check a plan (ticket 36).
export function startProjectPaper(plan: NonNullable<Writing["summaryPlan"]>): string {
  startWriting({ kind: "project_paper", project_id: plan.project_id, agency_id: plan.agency_id, plan_date: plan.plan_date,
    idempotency_key: newKey() }, null, [], undefined, { summaryPlan: plan });
  return writingHref(plan.project_id, plan.agency_id, plan.plan_date, "project_paper");
}

// "Add to mission brief" on a Following row (ticket 37): start the writer for the project, and the writing page's
// address. One key per press, so a double click never starts two writers.
export function startMissionBrief(project: NonNullable<Writing["project"]>): string {
  startWriting({ kind: "mission_brief", project_id: project.project_id, idempotency_key: newKey() }, null, [], project);
  return `/drafts/new?${new URLSearchParams({ kind: "mission_brief", pid: project.project_id }).toString()}`;
}

async function run(request: Writing["request"], signal: AbortSignal) {
  try {
    for await (const event of streamEvents("/api/drafts", { ...request, view: "staff" }, { signal })) {
      update((current) => withEvent(current, event.type, event.data));
      if (event.type === "done") {
        update((current) => (current.phase === "writing" ? { ...current, phase: "dropped" } : current));
        return;
      }
    }
    if (!signal.aborted) update((current) => (current.phase === "writing" ? { ...current, phase: "dropped" } : current));
  } catch (error) {
    if (signal.aborted) return;
    const code = error instanceof StreamError ? refusedStream(error) : null;
    update((current) => (code ? { ...current, phase: "failed", error: code } : { ...current, phase: "dropped" }));
  }
}

// Why the server would not open the stream, from its answer's code where it gave one: a server with no
// draft store says so in the store's words, not the data service's.
function refusedStream(error: StreamError): string {
  const code = typeof error.body?.code === "string" ? error.body.code : null;
  if (code === "no_data_service" || code === "draft_store") return "draft_store";
  if (error.status === 403) return "permission";
  return error.status === 503 ? "data_service" : "internal";
}

// "Stop writing": cancel the stream. The server saves nothing it has not finished.
export function stopWriting() {
  stopping?.abort();
  stopping = null;
  writing.set(null);
}

// A new idempotency key for one press of the button.
export function newKey(): string {
  return Math.random().toString(36).slice(2, 12);
}
