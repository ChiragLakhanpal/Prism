// The answer to the question asked from the one box (ticket 14): the stream's events as they arrive
// (POST /api/ask, src/strata/server/app.py), kept as one run. The answer panel draws the run; nothing
// here counts or checks anything, because the check line's counts come from the stream's checks event
// (spec, "The agent and the answer contract").
//
// One question at a time: a new question replaces the run and stops the one before. The run belongs to
// the history entry it was asked on (web/src/lib/router.ts), so Back to that page shows it again and a
// full reload drops it.
import { remember } from "./evidence";
import { StreamError, streamEvents } from "./sse";
import { createStore } from "./store";

export type StepEvent = {
  id: string;
  kind: "tool" | "write" | "check";
  tool?: string;
  project_id?: string | null;
  status: "running" | "done";
  count?: number;
  removed?: number;
};
export type Mention = { text: string; evidence_id: string | null };
export type SentenceEvent = {
  index: number;
  text: string;
  kind: string;
  evidence_ids: string[];
  numbers: Mention[];
  dates: Mention[];
  quote: { text: string; evidence_id: string } | null;
};
export type EvidenceEvent = {
  id: string;
  kind: "passage" | "record";
  tool: string | null;
  stratum: "What" | "How" | "Why" | null;
  short_name: string | null;
  // The row a tool returned: for a passage, its source line's fields and its whole paragraph.
  row: Record<string, any>;
  // Where each sentence's quote sits in the paragraph.
  highlights: { sentence: number; start: number; end: number }[];
};
export type ChecksEvent = {
  checks_run: number[];
  sentences: { written: number; kept: number; removed: number };
  numbers: { total: number; matched: number };
  dates: { total: number; matched: number };
  quotes: { total: number; found: number };
  sources: { total: number; returned: number };
  tools: string[];
};
export type RemovedEvent = { index: number; sentence: string; reason: string; reasons: { check: number; code: string; text: string | null }[] };

export type Asked = {
  question: string;
  scope: string | null;
  asOf: string | null;
  view: string | null;
  lang: string | null;
  // The history entry it was asked on.
  key: string;
};

export type Run = {
  serial: number;
  asked: Asked;
  // streaming until the done event; failed with an error code; dropped when the stream ended early.
  phase: "streaming" | "done" | "failed" | "dropped";
  steps: StepEvent[];
  sentences: SentenceEvent[];
  evidence: Record<string, EvidenceEvent>;
  checks: ChecksEvent | null;
  removed: RemovedEvent[];
  error: string | null;
  runId: string | null;
  // When the last event arrived, for "I'm still working on this step."
  lastEventAt: number;
};

export const answer = createStore<Run | null>(null);

// The scope chips removed on the page you are on: by the box's remove button or Backspace, or by
// "Ask across all projects" in an empty answer. A new page brings its chip back.
export const removedScopes = createStore<ReadonlySet<string>>(new Set());

export function removeScope(scope: string) {
  removedScopes.set((all) => new Set([...all, scope]));
}

let serial = 0;
let stopping: AbortController | null = null;

function update(id: number, change: (run: Run) => Run) {
  answer.set((run) => (run && run.serial === id ? change({ ...run, lastEventAt: Date.now() }) : run));
}

function apply(id: number, type: string, data: any) {
  if (type === "step") {
    update(id, (run) => {
      const steps = run.steps.some((step) => step.id === data.id)
        ? run.steps.map((step) => (step.id === data.id ? (data as StepEvent) : step))
        : [...run.steps, data as StepEvent];
      return { ...run, steps };
    });
  } else if (type === "sentence") {
    update(id, (run) => ({ ...run, sentences: [...run.sentences, data as SentenceEvent] }));
  } else if (type === "evidence") {
    remember(data as EvidenceEvent);
    update(id, (run) => ({ ...run, evidence: { ...run.evidence, [data.id]: data as EvidenceEvent } }));
  } else if (type === "checks") {
    update(id, (run) => ({ ...run, checks: data as ChecksEvent }));
  } else if (type === "removed") {
    update(id, (run) => ({ ...run, removed: [...run.removed, data as RemovedEvent] }));
  } else if (type === "error") {
    update(id, (run) => ({ ...run, error: String(data.code ?? "internal") }));
  } else if (type === "done") {
    update(id, (run) => ({ ...run, runId: data.run_id ?? null, phase: run.error ? "failed" : "done" }));
  }
}

async function stream(id: number, asked: Asked, signal: AbortSignal) {
  const payload = { question: asked.question, scope: asked.scope, asof: asked.asOf, view: asked.view ?? "staff", lang: asked.lang ?? "en" };
  try {
    for await (const event of streamEvents("/api/ask", payload, { signal })) {
      apply(id, event.type, event.data);
      if (event.type === "done") return;
    }
    if (!signal.aborted) update(id, (run) => ({ ...run, phase: "dropped" }));
  } catch (error) {
    if (signal.aborted) return;
    // The server did not open the stream: a 503 is the agent not responding.
    if (error instanceof StreamError) {
      update(id, (run) => ({ ...run, phase: "failed", error: error.status === 503 ? "agent_unavailable" : "internal" }));
    } else {
      update(id, (run) => ({ ...run, phase: "dropped" }));
    }
  }
}

// Ask a question: the panel opens at once with its first step, and the stream fills it.
export function ask(asked: Asked) {
  stopping?.abort();
  stopping = new AbortController();
  serial += 1;
  answer.set({
    serial,
    asked,
    phase: "streaming",
    steps: [],
    sentences: [],
    evidence: {},
    checks: null,
    removed: [],
    error: null,
    runId: null,
    lastEventAt: Date.now(),
  });
  void stream(serial, asked, stopping.signal);
}

// Ask the same question again, with the same scope.
export function askAgain() {
  const run = answer.get();
  if (run) ask(run.asked);
}

// "Close the answer": stop a stream in progress and close the panel.
export function closeAnswer() {
  stopping?.abort();
  stopping = null;
  answer.set(null);
}
