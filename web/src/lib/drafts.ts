// Drafts in the browser (ticket 35): the shapes the draft routes answer with (src/strata/server/drafts.py),
// the acts a draft's author takes, the writing stream, and what one page hands the next. Every count a
// draft screen states comes from the server; nothing here counts sources, notes or citations.
import type { ChecksEvent, EvidenceEvent, RemovedEvent, SentenceEvent } from "./answer";
import { ApiError, postJson } from "./api";
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
};

export type DraftFile = { name: string; media_type: string; size: number };

// The kinds of draft (config/drafts.toml); each has its words under copy.draft.kinds.<kind>.
export type DraftKind = "review_notes" | "mission_brief";

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
  written: { notes: number; sentences: number };
  notes: DraftNote[];
  evidence: Record<string, EvidenceEvent>;
  checks: ChecksEvent;
  // How many checks the verifier ran on this draft.
  checks_count: number;
  removed: (RemovedEvent & { key: string })[];
  sources: DraftSource[];
  citations: number;
  opened: { count: number; of: number };
  layout: { columns: string[]; export: "word"; sources_list: boolean; removed_box: "always" | "when_removed"; not_checked: string[] };
  holds: { key: string; copy: string }[];
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
export function writingHref(pid: string, agencyId: string, version: string): string {
  return `/drafts/new?${new URLSearchParams({ kind: "review_notes", pid, agency: agencyId, version }).toString()}`;
}

// ── Writing ──────────────────────────────────────────────────────────────

export type WriteStep = {
  id: "read" | "write" | "check" | "save";
  status: "running" | "done";
  plan_date?: string;
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
  // A mission brief (ticket 37) names only its project.
  request: { kind: DraftKind; project_id: string; agency_id?: string; plan_date?: string; idempotency_key: string };
  // The plan check the client held when the person asked, for the activity cells that show at once; none for a
  // mission brief, which shows its project and its five part headings instead.
  plan: CheckPlanResult | null;
  rows: Activity[];
  project?: { project_id: string; project_name: string; country: string | null };
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
export function startWriting(request: Writing["request"], plan: CheckPlanResult | null, rows: Activity[], project?: Writing["project"]) {
  const current = writing.get();
  if (current && current.request.idempotency_key === request.idempotency_key && current.phase === "writing") return;
  stopping?.abort();
  stopping = new AbortController();
  writing.set({ request, plan, rows, project, phase: "writing", steps: [], draftId: null, removed: [], checks: null, error: null, reference: null, lastEventAt: Date.now() });
  void run(request, stopping.signal);
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
