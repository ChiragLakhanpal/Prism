// The answer to the question asked from the one box (ticket 14): the stream's events as they arrive
// (POST /api/ask, src/strata/server/app.py), kept as one run. The answer panel draws the run; nothing
// here counts or checks anything, because the check line's counts come from the stream's checks event
// (spec, "The agent and the answer contract").
//
// One question at a time: a new question replaces the run and stops the one before. The run belongs to
// the history entry it was asked on (web/src/lib/router.ts), so Back to that page shows it again and a
// full reload drops it.
import { closeDrawerOf, remember } from "./evidence";
import type { Feedback } from "./retrieval";
import { StreamError, streamEvents } from "./sse";
import { createStore } from "./store";
import type { Why } from "./trail";

export type StepEvent = {
  id: string;
  // judge and disagreement are steps the verifier takes inside its own (ticket 24): asking the model
  // that judges sentences, and getting the other side of a disagreement.
  kind: "tool" | "write" | "check" | "judge" | "disagreement";
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
  // A quantile dot's packages (ticket 15) are no source: the page holds them, and the drawer lists them. So are
  // section 5's lists and cost records (ticket 31): the packages whose criteria are public, the notices behind one
  // item, and a comparable package's cost records. And so are the completion reports behind a risk's count and
  // every report the risks section counted (ticket 30), and the comparable packages behind a step's planned date
  // or behind "ran longest" (ticket 27).
  kind:
    | "passage"
    | "record"
    | "package"
    | "dot"
    | "criteria_public"
    | "criteria_item"
    | "package_cost"
    | "risk-reports"
    | "risk-reports-all"
    | "steps"
    | "steps-longest"
    // A project timeline's marks (ticket 23): a report's document view, a band's ratings, a year's contracts and a
    // disagreement's two reports.
    | "document"
    | "ratings"
    | "contracts"
    | "disagreement";
  tool: string | null;
  stratum: "What" | "How" | "Why" | null;
  short_name: string | null;
  // The row a tool returned: for a passage, its source line's fields and its whole paragraph.
  row: Record<string, any>;
  // Where each sentence's quote sits in the paragraph.
  highlights: { sentence: number; start: number; end: number }[];
  // A passage opened by its id says why it is a source for a contract it appeared together with (ticket 22), or
  // null when no link was public. A passage an answer or a page sent with it leaves it out (undefined), and the
  // drawer shows no such block for it.
  why?: Why | null;
  // Whether the drawer offers "Was this the right passage?" for this source of this answer (ticket 32). Only the
  // answer stream sends it; a source read from a link has none, and the row does not show.
  feedback?: Feedback;
};
// The verifier's counts. numbers, dates, quotes and sources are over every sentence the agent wrote, as the
// steps' six-check list gives them; shown is over the sentences on screen, as the check line gives them. The
// rest come with checks 4 to 6 (ticket 24), so an answer that ran only checks 1 to 3 lacks them.
export type ChecksEvent = {
  checks_run: number[];
  sentences: { written: number; kept: number; removed: number };
  numbers: { total: number; matched: number };
  dates: { total: number; matched: number };
  quotes: { total: number; found: number };
  sources: { total: number; returned: number };
  tools: string[];
  shown?: {
    numbers: { total: number; matched: number };
    dates: { total: number; matched: number };
    quotes: { total: number; found: number };
    judged: number;
    proven: number;
  };
  // Numbers and dates together, over every sentence written, for check 1's item in the steps.
  checked?: { total: number; matched: number };
  judge?: { called: boolean; responded: boolean | null; judged: number; followed: number; unjudged: number; proven: number };
  advice?: { total: number; cited: number };
  // warned: the sentences a warning card follows, which the status line announces.
  // unasked: the sentences removed because I couldn't ask which reports disagree (absent before ticket 24's round 3).
  disagreements?: { disputed: number; shown: number; attached: number; unasked?: number; warned: number };
  // The tools whose evidence the kept sentences cite, and those whose "Not checked" clause needs that.
  cited_tools?: string[];
  cited_only?: string[];
};
// kind is the claim's kind (record, quote, summary, advice), sent since ticket 24's round 2.
export type RemovedEvent = {
  index: number;
  sentence: string;
  kind?: string;
  reason: string;
  reasons: { check: number; code: string; text: string | null }[];
};
// A request on the refusal list (ticket 24): its key in the copy file's refusals, and whether the rest of the
// question was answered.
export type RefusalEvent = { key: string; partial: boolean };
// One side of a disagreement, as get_disagreements returned it.
export type DisagreementSide = {
  evidence_id: string;
  // The assertion keeping a side posts (ticket 23), and the kind of report (config/project_page.toml's groups).
  assertion_id: string | null;
  type: string | null;
  document_type: string | null;
  report_number: string | null;
  sequence: number | null;
  paragraph: string | null;
  paragraph_numbered: boolean | null;
  evidence_tier: string | null;
  made_at: string | null;
  field_name: string | null;
  value: string | null;
  value_form: string | null;
  quote: string | null;
  months_after_event?: number | null;
  doc_key?: string | null;
  leaned: boolean;
};
// A disagreement the verifier's check 6 shows under the sentence it concerns (after), with both sides in the
// order they were written.
export type DisagreementEvent = {
  id: string;
  // The id keeping a side posts to (POST /api/disagreements/{id}/choices), the sentences keeping the other side
  // would change and how many they are, which the card says as it comes (ticket 23): one shape for both cards.
  disagreement_id?: string | null;
  changes_sentence_ids?: number[];
  changes_count?: number;
  period_event?: string | null;
  after: number;
  changes_answer: boolean;
  attached_by_verifier: boolean;
  attribute: string | null;
  rule_id: string | null;
  sides: DisagreementSide[];
  if_you_keep: { field_name: string | null; value: string | null } | null;
};

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
  refusal: RefusalEvent | null;
  disagreements: DisagreementEvent[];
  error: string | null;
  runId: string | null;
  // When the last event arrived, for "I'm still working on this step."
  lastEventAt: number;
  // The language the writer wrote the answer in, and the question's when the server was sure of it (ticket 42).
  lang: string;
  questionLang: string | null;
};

export const answer = createStore<Run | null>(null);
// Ticket 21: the last finished answer asked on each other history entry, kept for the session, so Back to
// a page shows its answer again even after a question was asked somewhere else, such as on the source view
// a citation opened.
export const earlier = createStore<Record<string, Run>>({});

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
    case "refusal":
      return { ...run, refusal: data as RefusalEvent };
    case "disagreement":
      return { ...run, disagreements: [...run.disagreements, data as DisagreementEvent] };
    case "error":
      return { ...run, error: String(data.code ?? "internal") };
    case "done":
      return { ...run, runId: data.run_id ?? null, phase: run.error ? "failed" : "done" };
    case "language":
      return { ...run, lang: String(data.lang ?? run.lang), questionLang: data.question_lang ?? null };
    default:
      return run;
  }
}

// Each source the answer cites, numbered once, in order of first appearance; a source cited again
// keeps its number (the 14 brief, section 4.1). A disagreement shown under a sentence comes next in
// reading order, so the side the sentence cited keeps its number and the other side gets the next one
// (the 24 brief, section 4.4). The panel's markers and the drawer's claim block both read it, so the
// two never disagree.
export function citationNumbers(run: Pick<Run, "sentences"> & { disagreements?: DisagreementEvent[] }): Map<string, number> {
  const numbers = new Map<string, number>();
  const add = (id: string) => {
    if (!numbers.has(id)) numbers.set(id, numbers.size + 1);
  };
  for (const sentence of run.sentences) {
    sentence.evidence_ids.forEach(add);
    for (const found of run.disagreements ?? []) if (found.after === sentence.index) found.sides.forEach((side) => add(side.evidence_id));
  }
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
    refusal: null,
    disagreements: [],
    error: null,
    runId: null,
    lastEventAt: Date.now(),
    lang: asked.lang ?? "en",
    questionLang: null,
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
  const before = answer.get();
  if (before && before.phase !== "streaming" && before.asked.key !== asked.key) {
    earlier.set((kept) => ({ ...kept, [before.asked.key]: before }));
  }
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

// "Close the answer": stop a stream in progress, and close the panel and the drawer it opened. An answer
// kept from an earlier page (ticket 21) closes on its own, and the current one stays.
export function closeAnswer(shown: Run | null = answer.get()) {
  if (shown) {
    earlier.set((kept) => {
      const { [shown.asked.key]: _left, ...rest } = kept;
      return rest;
    });
  }
  const current = answer.get();
  if (shown && current && shown.serial !== current.serial) {
    closeDrawerOf(shown.serial);
    return;
  }
  leave();
  stopping = null;
  answer.set(null);
}
