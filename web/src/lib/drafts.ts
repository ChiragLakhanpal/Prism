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
};

export type DraftFile = { name: string; media_type: string; size: number };

export type Draft = {
  draft_id: string;
  kind: "review_notes";
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
    files: DraftFile[];
    files_available: boolean;
  } | null;
};

export type DraftRow = {
  draft_id: string;
  kind: "review_notes";
  state: DraftState;
  subject: DraftSubject;
  notes: number;
  author: { name: string | null; you: boolean };
  created_at: string;
  changed: Who;
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

export type Existing = { draft: { draft_id: string; created_at: string; author: { name: string | null; you: boolean } } | null };

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
  count?: number;
  notes?: number;
  sentences?: number;
  checks_run?: number[];
  written?: number;
  removed?: number;
};

// A draft being written: what Check a plan handed over, and the stream's events so far.
export type Writing = {
  request: { kind: "review_notes"; project_id: string; agency_id: string; plan_date: string; idempotency_key: string };
  // The plan check the client held when the person asked, for the activity cells that show at once.
  plan: CheckPlanResult;
  rows: Activity[];
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
export function startWriting(request: Writing["request"], plan: CheckPlanResult, rows: Activity[]) {
  const current = writing.get();
  if (current && current.request.idempotency_key === request.idempotency_key && current.phase === "writing") return;
  stopping?.abort();
  stopping = new AbortController();
  writing.set({ request, plan, rows, phase: "writing", steps: [], draftId: null, removed: [], checks: null, error: null, reference: null, lastEventAt: Date.now() });
  void run(request, stopping.signal);
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
    const code = error instanceof StreamError ? (error.status === 403 ? "permission" : error.status === 503 ? "data_service" : "internal") : null;
    update((current) => (code ? { ...current, phase: "failed", error: code } : { ...current, phase: "dropped" }));
  }
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
