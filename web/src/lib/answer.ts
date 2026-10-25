// The answer to the question asked from the one box (ticket 14): the stream's events as they arrive
// (POST /api/ask, src/strata/server/app.py), kept as one run. The answer panel draws the run; nothing
// here counts or checks anything, because the check line's counts come from the stream's checks event
// (spec, "The agent and the answer contract").
//
// One question at a time: a new question replaces the run and stops the one before. The run belongs to
// the history entry it was asked on (web/src/lib/router.ts), so Back to that page shows it again and a
// full reload drops it.
import { closeDrawerOf, remember } from "./evidence";
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
  // A quantile dot's packages (ticket 15) are no source: the page holds them, and the drawer lists them.
  kind: "passage" | "record" | "package" | "dot";
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

// One event of the stream, added to the run.
export function withEvent(run: Run, type: string, data: any): Run {
  switch (type) {
    case "step": {
      const steps = run.steps.some((step) => step.id === data.id)
        ? run.steps.map((step) => (step.id === data.id ? (data as StepEvent) : step))
        : [...run.steps, data as StepEvent];
      return { ...run, steps };
    }
    case "sentence":
      return { ...run, sentences: [...run.sentences, data as SentenceEvent] };
    case "evidence":
      return { ...run, evidence: { ...run.evidence, [data.id]: data as EvidenceEvent } };
    case "checks":
      return { ...run, checks: data as ChecksEvent };
    case "removed":
      return { ...run, removed: [...run.removed, data as RemovedEvent] };
    case "error":
      return { ...run, error: String(data.code ?? "internal") };
    case "done":
      return { ...run, runId: data.run_id ?? null, phase: run.error ? "failed" : "done" };
    default:
      return run;
  }
}

// Each source the answer cites, numbered once, in order of first appearance; a source cited again
// keeps its number (the 14 brief, section 4.1). The panel's markers and the drawer's claim block both
// read it, so the two never disagree.
export function citationNumbers(run: Pick<Run, "sentences">): Map<string, number> {
  const numbers = new Map<string, number>();
  for (const sentence of run.sentences) for (const id of sentence.evidence_ids) if (!numbers.has(id)) numbers.set(id, numbers.size + 1);
  return numbers;
}

// A run before its first event.
export function newRun(serialNumber: number, asked: Asked): Run {
  return {
    serial: serialNumber,
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
  };
}

function apply(id: number, type: string, data: any) {
  if (type === "evidence") remember(data as EvidenceEvent);
  update(id, (run) => withEvent(run, type, data));
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

// The answer on screen is going away: stop its stream and close the drawer it opened.
function leave() {
  stopping?.abort();
  const before = answer.get();
  if (before) closeDrawerOf(before.serial);
}

// Ask a question: the panel opens at once with its first step, and the stream fills it. A drawer
// the old answer opened closes with it.
export function ask(asked: Asked) {
  leave();
  stopping = new AbortController();
  serial += 1;
  answer.set(newRun(serial, asked));
  void stream(serial, asked, stopping.signal);
}

// Ask the same question again, with the same scope.
export function askAgain() {
  const run = answer.get();
  if (run) ask(run.asked);
}

// "Close the answer": stop a stream in progress, and close the panel and the drawer it opened.
export function closeAnswer() {
  leave();
  stopping = null;
  answer.set(null);
}
