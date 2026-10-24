// The answer panel (the 14 brief, section 4.7): the answer to the question asked from the one box,
// in the page under the band, on columns 1 to 8 from 1024 px. It draws the stream's run
// (web/src/lib/answer.ts) as ticket 02's Answer: steps while it works, then "In short" with citation
// markers, the check line with the stream's counts, and the removed box, open.
//
// Screen readers hear each step once, when it starts, and then "The answer is ready.", through one
// status line that is on the page before any of it changes. Events can arrive faster than anyone can
// listen, so the line moves on at most every ANNOUNCE_GAP_MS.
import { Fragment, useEffect, useMemo, useState, type ReactNode } from "react";
import { X } from "lucide-react";
import { copy } from "../copy";
import {
  askAgain,
  closeAnswer,
  removeScope,
  ask,
  type ChecksEvent,
  type EvidenceEvent,
  type Run,
  type SentenceEvent,
  type StepEvent,
} from "../lib/answer";
import { evidenceHref, loadVisited, openEvidence } from "../lib/evidence";
import { formatCount, formatDate } from "../lib/format";
import { passageFields, recordReference } from "../lib/sources";
import { Answer, type AnswerState } from "./Answer";
import { Button } from "./Button";
import { CitationMarker } from "./CitationMarker";
import type { NotChecked, Removed } from "./Checks";
import { EvidenceCard } from "./EvidenceCard";
import { Fill } from "./Fill";
import { Num } from "./Num";
import type { Step } from "./Steps";
import { TextLink } from "./TextLink";

export const ANNOUNCE_GAP_MS = 500;
const STILL_WORKING_MS = 30_000;
export const DRAWER_ID = "evidence-drawer";

const mono = (text: string) => <span className="font-mono">{text}</span>;

// ── Steps ──────────────────────────────────────────────────────────────

function toolLines(step: StepEvent): { running: string; done: string } {
  const count = step.count ?? 0;
  const words = step.tool ? copy.steps.tools[step.tool as keyof typeof copy.steps.tools] : undefined;
  if (!words) {
    const name = (step.tool ?? "").replace(/_/g, " ");
    return { running: copy.steps.otherTool.running(name), done: copy.steps.otherTool.done(name) };
  }
  const scope = step.project_id ?? null;
  return { running: words.running(scope), done: words.done(count, formatCount(count), scope) };
}

function stepLines(step: StepEvent, checks: ChecksEvent | null): { running: string; done: string } {
  if (step.kind === "tool") return toolLines(step);
  if (step.kind === "write") {
    const count = step.count ?? 0;
    return { running: copy.steps.write.running, done: copy.steps.write.done(count, formatCount(count)) };
  }
  const words = copy.steps.check;
  if (!checks) return { running: words.running, done: words.done };
  const removed = checks.sentences.removed;
  return {
    running: words.running,
    done: words.doneCounted(
      words.numbers(checks.numbers.total, formatCount(checks.numbers.total)),
      words.quotes(checks.quotes.total, formatCount(checks.quotes.total)),
      words.removed(removed, formatCount(removed)),
    ),
  };
}

export function stepsOf(run: Run): Step[] {
  const started = run.steps.length > 0 || run.phase !== "streaming";
  const steps: Step[] = [{ key: "read", ...copy.steps.read, state: started ? "done" : "running" }];
  for (const step of run.steps) steps.push({ key: step.id, ...stepLines(step, run.checks), state: step.status });
  if (run.phase === "streaming") {
    if (!run.steps.some((step) => step.kind === "write")) steps.push({ key: "todo-write", running: "", done: copy.steps.write.todo, state: "todo" });
    if (!run.steps.some((step) => step.kind === "check")) steps.push({ key: "todo-check", running: "", done: copy.steps.check.todo, state: "todo" });
  }
  return steps;
}

// What the status line says, in order: each step as it starts, then the answer.
function announcements(run: Run): string[] {
  const said = [copy.steps.read.running, ...run.steps.map((step) => stepLines(step, run.checks).running)];
  const answered = run.phase === "done" || (run.phase === "failed" && run.error === "content_filter");
  if (answered) {
    const removed = run.checks?.sentences.removed ?? 0;
    const kept = run.checks?.sentences.kept ?? 0;
    said.push(removed > 0 && kept > 0 ? copy.answer.readyRemoved(removed, formatCount(removed)) : copy.answer.ready);
  }
  return said;
}

function Announcer({ messages }: { messages: string[] }) {
  const [shown, setShown] = useState(-1);
  useEffect(() => {
    if (shown >= messages.length - 1) return;
    const timer = setTimeout(() => setShown((index) => index + 1), shown < 0 ? 100 : ANNOUNCE_GAP_MS);
    return () => clearTimeout(timer);
  }, [shown, messages.length]);
  return (
    <p role="status" data-answer-status className="sr-only">
      {shown >= 0 ? messages[shown] : ""}
    </p>
  );
}

// ── Sentences ──────────────────────────────────────────────────────────

export type Opened = { id: string | null; sentence: number | null };

function markerSource(evidence: EvidenceEvent | undefined, id: string): string {
  if (!evidence) return id;
  if (evidence.kind === "record") return copy.evidence.markerRecord(copy.checkPlan.columns.activity, recordReference(evidence));
  const fields = passageFields(evidence);
  return fields.numbered
    ? copy.evidence.markerSource(fields.docType, fields.date, fields.para)
    : copy.evidence.markerSourceSection(fields.docType, fields.date, fields.section ?? fields.para);
}

function numTooltip(evidence: EvidenceEvent | undefined): string | null {
  if (!evidence) return null;
  if (evidence.kind === "record") return copy.evidence.numTooltipRecord(copy.checkPlan.columns.activity, recordReference(evidence));
  const fields = passageFields(evidence);
  const kind = copy.evidence.docKinds[evidence.short_name ?? ""] ?? fields.docType;
  return copy.evidence.numTooltip(fields.para, kind, fields.pcode);
}

// A sentence's text with each number and date the verifier matched drawn by Num: a dotted underline,
// a tooltip naming the source, and a click that opens it. Numbers are not tab stops; the markers carry
// the keyboard to the same sources.
function sentenceText(sentence: SentenceEvent, evidence: Record<string, EvidenceEvent>, open: (id: string) => void): ReactNode[] {
  const found: { start: number; end: number; text: string; id: string }[] = [];
  let cursor = 0;
  for (const mention of [...sentence.numbers, ...sentence.dates]) {
    const id = mention.evidence_id ?? sentence.evidence_ids[0];
    const start = sentence.text.indexOf(mention.text, cursor);
    if (!id || start < 0) continue;
    found.push({ start, end: start + mention.text.length, text: mention.text, id });
    cursor = start + mention.text.length;
  }
  found.sort((a, b) => a.start - b.start);
  const parts: ReactNode[] = [];
  let at = 0;
  for (const mention of found) {
    if (mention.start < at) continue;
    parts.push(sentence.text.slice(at, mention.start));
    const tooltip = numTooltip(evidence[mention.id]);
    parts.push(
      <Num
        key={mention.start}
        written={mention.text}
        check={tooltip ? { tooltip, tabStop: false, onOpen: () => open(mention.id) } : undefined}
      />,
    );
    at = mention.end;
  }
  // The sentence's last characters stay with its marker (CitationMarker's word joiner).
  parts.push(sentence.text.slice(at));
  return parts;
}

export function AnswerSentences({
  run,
  opened,
  visited,
}: {
  run: Run;
  // The source the evidence drawer shows, and the sentence whose marker opened it.
  opened: Opened;
  visited: ReadonlySet<string>;
}) {
  const numbers = useMemo(() => {
    const numbering = new Map<string, number>();
    for (const sentence of run.sentences) for (const id of sentence.evidence_ids) if (!numbering.has(id)) numbering.set(id, numbering.size + 1);
    return numbering;
  }, [run.sentences]);
  const open = (id: string, sentence: number, marker: HTMLElement | null) =>
    openEvidence(id, { sentence, marker, runId: run.runId });
  return (
    <>
      {run.sentences.map((sentence, index) => {
        const active = opened.id !== null && opened.sentence === sentence.index;
        return (
          <Fragment key={sentence.index}>
            {index > 0 && " "}
            <span
              data-sentence-text={sentence.index}
              className={active ? "bg-tint [box-decoration-break:clone]" : undefined}
            >
              {sentenceText(sentence, run.evidence, (id) => open(id, sentence.index, null))}
              {sentence.evidence_ids.map((id) => {
                const n = numbers.get(id)!;
                const evidence = run.evidence[id];
                return (
                  <CitationMarker
                    key={id}
                    n={n}
                    evidenceId={id}
                    sentence={sentence.index}
                    source={markerSource(evidence, id)}
                    href={evidenceHref(id)}
                    drawerId={DRAWER_ID}
                    active={opened.id === id && active}
                    opened={visited.has(id)}
                    preview={evidence ? <EvidenceCard evidence={evidence} n={n} sentence={sentence.index} visited={visited.has(id)} /> : undefined}
                    onOpen={(marker) => open(id, sentence.index, marker)}
                  />
                );
              })}
            </span>
          </Fragment>
        );
      })}
    </>
  );
}

// ── The panel ──────────────────────────────────────────────────────────

function removedItems(run: Run): Removed[] {
  return run.removed.map((item) => {
    const reason = copy.removed.reasons[item.reason as keyof typeof copy.removed.reasons] ?? copy.removed.reasons.number_not_in_records;
    return { sentence: item.sentence, reason: reason.item, reasonJoined: reason.joined };
  });
}

// Words that stay capitalized when a removed sentence is reported: those written with a capital in the
// middle of a sentence in this answer or its passages, such as Rajasthan or Kenya.
function names(run: Run): string[] {
  const texts = [...run.sentences.map((sentence) => sentence.text), ...Object.values(run.evidence).map((evidence) => String(evidence.row.text ?? ""))];
  const found = new Set<string>();
  for (const text of texts) for (const match of text.matchAll(/[a-z,;:]\s+([A-Z][a-z]+)/g)) found.add(match[1]);
  return [...found];
}

function notChecked(checks: ChecksEvent): NotChecked[] {
  const clauses: NotChecked[] = ["sentences"];
  if (checks.tools.includes("find_comparables")) clauses.push("comparables");
  if (checks.tools.includes("search_passages")) clauses.push("passages");
  return clauses;
}

function stateOf(run: Run, opened: Opened, visited: ReadonlySet<string>, stillWorking: boolean): AnswerState {
  const steps = stepsOf(run);
  const runId = run.runId ?? "";
  if (run.phase === "streaming") return { status: "streaming", steps, stillWorking, announce: false };
  const done = steps.filter((step) => step.state === "done");
  if (run.phase === "failed" && run.error === "content_filter") {
    return {
      status: "refused",
      steps: done,
      runId,
      message: copy.answer.refusedContentFilter,
      note: <Fill template={copy.answer.refusalNote} slots={{ link: <TextLink href="/data">{copy.answer.refusalLink}</TextLink> }} />,
    };
  }
  if (run.phase !== "done" || !run.checks) {
    const said = run.phase === "dropped" ? copy.answer.dropped : (copy.answer.errors[run.error as keyof typeof copy.answer.errors] ?? copy.answer.errors.internal);
    return {
      status: "error",
      steps: done,
      message: (
        <>
          {said} {copy.answer.stillInBox}
        </>
      ),
      onRetry: askAgain,
    };
  }
  const { checks } = run;
  if (checks.sentences.written === 0) {
    const scope = run.asked.scope;
    return {
      status: "empty",
      steps: done,
      runId,
      message: scope ? (
        <Fill template={copy.answer.emptyScoped} slots={{ id: mono(scope) }} />
      ) : (
        <Fill template={copy.answer.emptyUnscoped} slots={{ link: <TextLink href="/data">{copy.answer.emptyLink}</TextLink> }} />
      ),
      action: scope ? (
        <Button
          variant="secondary"
          onClick={() => {
            removeScope(scope);
            ask({ ...run.asked, scope: null });
          }}
        >
          {copy.answer.askAcross}
        </Button>
      ) : undefined,
    };
  }
  if (checks.sentences.kept === 0) {
    const written = checks.sentences.written;
    return { status: "unsupported", steps: done, runId, message: copy.answer.nothingSurvived(written, formatCount(written)), removed: removedItems(run) };
  }
  return {
    status: "ready",
    steps: done,
    runId,
    sentences: <AnswerSentences run={run} opened={opened} visited={visited} />,
    checks: {
      numbers: checks.numbers,
      dates: checks.dates,
      quotes: checks.quotes,
      notChecked: notChecked(checks),
      removed: removedItems(run),
      names: names(run),
    },
  };
}

function AskedLine({ run }: { run: Run }) {
  const { scope, asOf, view } = run.asked;
  const words = copy.answer;
  const preview = view === "piu" || view === "public" ? words.previewViews[view] : null;
  return (
    <p className="mt-1 text-caption text-ink-muted">
      {scope ? <Fill template={words.askedWithin} slots={{ id: mono(scope) }} /> : words.askedAcross}
      {asOf && words.askedAsOf(formatDate(asOf))}
      {preview && words.askedPreview(preview)}
      {words.askedEnd}
    </p>
  );
}

export function AnswerPanel({ run, opened, visited }: { run: Run; opened: Opened; visited: ReadonlySet<string> }) {
  const [stillWorking, setStillWorking] = useState(false);
  useEffect(() => {
    if (run.phase !== "streaming") {
      setStillWorking(false);
      return;
    }
    const timer = setInterval(() => setStillWorking(Date.now() - run.lastEventAt > STILL_WORKING_MS), 1000);
    return () => clearInterval(timer);
  }, [run.phase, run.lastEventAt]);

  // When the answer lands, its markers learn which sources this viewer opened before.
  useEffect(() => {
    if (run.phase === "done") void loadVisited(Object.keys(run.evidence));
  }, [run.phase, run.serial]);

  const close = () => {
    closeAnswer();
    document.querySelector<HTMLInputElement>("[data-box-band] [role=combobox]")?.focus();
  };

  return (
    <section aria-label={copy.answer.panel} aria-busy={run.phase === "streaming"} data-answer-panel className="mb-8">
      <div className="rounded-md border border-line bg-surface p-4 md:p-6 lg:p-8">
        <div className="flex items-start justify-between gap-4">
          <h2 className="min-w-0 text-title wrap-anywhere text-ink-heading">{run.asked.question}</h2>
          <Button variant="ghost" icon={X} onClick={close} className="hidden -mt-2 -mr-2 md:inline-flex">
            {copy.answer.close}
          </Button>
          <Button variant="ghost" icon={X} iconOnly onClick={close} className="-mt-2 -mr-2 md:hidden">
            {copy.answer.close}
          </Button>
        </div>
        <AskedLine run={run} />
        <div className="mt-6">
          <Answer state={stateOf(run, opened, visited, stillWorking)} />
        </div>
        <Announcer key={run.serial} messages={announcements(run)} />
      </div>
    </section>
  );
}
