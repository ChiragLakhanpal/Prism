// Answer: the body of a cited answer, in each of its states. Ticket 14 puts it in the answer
// panel under the band and feeds it from the stream.
//
// Streaming: the steps, then skeleton bars sized to "In short" and the check line.
// Ready: "In short", the verified sentences with their markers, the check line, the removed
//   box, and the steps folded into a disclosure. A partial refusal (ticket 24) opens "In short":
//   what I don't do, then "I answered the rest of your question.", with its link, and the answer
//   follows. A disagreement card can break "In short" under the sentence it concerns.
// Abstained: a tool held back (fewer than 20 comparables, say). Its own first-person sentence
//   stands in "In short", the check line and the removed box sit under it as in Ready, and
//   the rows it returned follow them, so the proof stays beside the sentence it checks.
// Unsupported: every sentence the agent wrote failed a check. "In short" says so, the removed box
//   lists each one with its reason, and there is no check line.
// Empty: nothing in the records or documents answers the question, said in the first person.
// Refused: a request on the refusal list, answered in plain text with no alert.
// Error: the steps done so far, an error alert, "Try again" when trying again can help, and the
//   answer's ID when the run has one. When a service a check needs did not answer (the model that
//   judges sentences, or the question of which reports disagree) and no sentence survived, the
//   removed box under the alert lists every sentence I wrote.
import { useId, useState, type ClipboardEvent, type ReactNode } from "react";
import { ChevronDown } from "lucide-react";
import { copy } from "../copy";
import { cx } from "../lib/cx";
import { Alert } from "./Alert";
import { Button } from "./Button";
import { CheckLine, RemovedBox, type NotChecked, type Removed } from "./Checks";
import { WORD_JOINER } from "./CitationMarker";
import { numText } from "./Num";
import { LoadingLabel, Skeleton, SkeletonLine, SkeletonText } from "./Skeleton";
import { Steps, type Step } from "./Steps";

type Checks = {
  numbers?: { matched: number; total: number };
  dates?: { matched: number; total: number };
  quotes?: { found: number; total: number };
  judged?: { judged: number; proven: number };
  notChecked: NotChecked[];
  removed: Removed[];
  names?: string[];
  // A service a check needs did not answer: "Try again" in the removed box, with its note.
  retry?: { onRetry: () => void; note?: string };
};

export type AnswerState =
  // announce is false in the answer panel, which announces steps in its own live region.
  | { status: "streaming"; steps: Step[]; stillWorking?: boolean; announce?: boolean }
  // wide: a disagreement card breaks "In short", so the blocks keep their own measure (each paragraph at
  // about 65 characters) and the card takes the answer's full width.
  | { status: "ready"; steps: Step[]; runId: string; sentences: ReactNode; checks: Checks; refusal?: ReactNode; wide?: boolean }
  | { status: "abstained"; steps: Step[]; runId: string; sentence: ReactNode; rows: ReactNode; checks: Checks }
  // refusal: a partial refusal's paragraph, which still opens "In short" when nothing else survived.
  | { status: "unsupported"; steps: Step[]; runId: string; message: ReactNode; removed: Removed[]; refusal?: ReactNode }
  | { status: "empty"; steps: Step[]; runId: string; message: ReactNode; action?: ReactNode }
  | { status: "refused"; steps: Step[]; runId: string; message: ReactNode; note?: ReactNode }
  // runId: the run's ID, shown under the alert so it can be shared; onRetry: no button without it.
  | { status: "error"; steps: Step[]; message: ReactNode; onRetry?: () => void; runId?: string; removed?: Removed[] };

// A copied answer reads "...rebidding". [1]", without the word joiners that keep each marker on its
// sentence's line (CitationMarker.tsx), so a pasted sentence matches the one the verifier checked.
function withoutWordJoiners(event: ClipboardEvent<HTMLDivElement>) {
  const text = window.getSelection()?.toString();
  if (!text) return;
  event.clipboardData.setData("text/plain", text.replaceAll(WORD_JOINER, ""));
  event.preventDefault();
}

// wide: the children are blocks that keep their own measure, so a disagreement card can take the
// answer's full width while its paragraphs stay at about 65 characters a line.
function InShort({ children, wide = false }: { children: ReactNode; wide?: boolean }) {
  return (
    <>
      <h3 className="text-label text-ink-muted uppercase">{copy.answer.inShort}</h3>
      <div data-in-short onCopy={withoutWordJoiners} className={cx("mt-2 text-body text-ink", !wide && "max-w-prose")}>
        {children}
      </div>
    </>
  );
}

export function StepsTaken({ steps: all, runId, idLabel = copy.steps.answerId }: { steps: Step[]; runId: string; idLabel?: string }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  const steps = all.filter((step) => step.state !== "todo");
  const count = steps.length;
  return (
    <div className="mt-4">
      {/* Flush, so its icon lines up with the text above and its fill and focus ring stay
          inside the card around the answer. */}
      <Button
        variant="ghost"
        flush
        icon={ChevronDown}
        aria-expanded={open}
        aria-controls={id}
        onClick={() => setOpen(!open)}
        className={cx("[&>svg]:transition-transform", open && "[&>svg]:rotate-180")}
      >
        {open ? copy.steps.hide : count === 1 ? copy.steps.showOne : copy.steps.show(numText({ count }))}
      </Button>
      <div id={id} hidden={!open} className="mt-2">
        <Steps steps={steps} />
        {/* On the steps' text edge, past their icon rail, so the opened list has one left edge. */}
        <p className="mt-2 pl-6 text-caption text-ink-muted">
          {idLabel} <span className="font-mono">{runId}</span>
        </p>
      </div>
    </div>
  );
}

// The check line and the removed box keep the answer's measure, about 65 characters a line.
function ChecksBlock({ checks }: { checks: Checks }) {
  return (
    <div className="mt-4 flex max-w-prose flex-col gap-2">
      <CheckLine numbers={checks.numbers} dates={checks.dates} quotes={checks.quotes} judged={checks.judged} notChecked={checks.notChecked} />
      <RemovedBox removed={checks.removed} names={checks.names} retry={checks.retry} />
    </div>
  );
}

export function Answer({ state }: { state: AnswerState }) {
  switch (state.status) {
    case "streaming":
      return (
        <div data-answer="streaming" aria-busy="true">
          <Steps steps={state.steps} stillWorking={state.stillWorking} reserveLines={4} announce={state.announce ?? true} />
          <LoadingLabel />
          {/* "In short", three lines of answer and the check line, each at its own size. */}
          <div className="mt-6 max-w-prose">
            <SkeletonLine className="text-label" width="w-1/6" />
            <SkeletonText className="mt-2 text-body" widths={["w-full", "w-11/12", "w-3/5"]} />
            <Skeleton className="mt-4 h-14 w-full rounded-md" />
          </div>
        </div>
      );
    case "ready":
      return (
        <div data-answer="ready">
          <InShort wide={state.wide}>
            {state.refusal && <div className="mb-4 max-w-prose">{state.refusal}</div>}
            {state.sentences}
          </InShort>
          <ChecksBlock checks={state.checks} />
          <StepsTaken steps={state.steps} runId={state.runId} />
        </div>
      );
    case "abstained":
      return (
        <div data-answer="abstained">
          <InShort>{state.sentence}</InShort>
          <ChecksBlock checks={state.checks} />
          <div className="mt-6">{state.rows}</div>
          <StepsTaken steps={state.steps} runId={state.runId} />
        </div>
      );
    case "unsupported":
      return (
        <div data-answer="unsupported">
          <InShort>
            {state.refusal && <div className="mb-4">{state.refusal}</div>}
            {state.message}
          </InShort>
          <div className="mt-4 max-w-prose">
            <RemovedBox removed={state.removed} all />
          </div>
          <StepsTaken steps={state.steps} runId={state.runId} />
        </div>
      );
    case "empty":
      return (
        <div data-answer="empty">
          <p className="max-w-prose text-body text-ink">{state.message}</p>
          {state.action && <div className="mt-4">{state.action}</div>}
          <StepsTaken steps={state.steps} runId={state.runId} />
        </div>
      );
    case "refused":
      return (
        <div data-answer="refused">
          <InShort>{state.message}</InShort>
          {state.note && <p className="mt-2 text-caption text-ink-muted">{state.note}</p>}
          <StepsTaken steps={state.steps} runId={state.runId} />
        </div>
      );
    case "error":
      return (
        <div data-answer="error">
          {state.steps.length > 0 && <Steps steps={state.steps} rail={false} />}
          {/* The alert keeps the answer's measure, as the check line and the removed box do. */}
          <Alert
            state="error"
            live="alert"
            className={cx(state.steps.length > 0 && "mt-4", "max-w-prose")}
            action={
              state.onRetry && (
                <Button variant="secondary" onClick={state.onRetry}>
                  {copy.answer.tryAgain}
                </Button>
              )
            }
          >
            {state.message}
          </Alert>
          {state.removed && state.removed.length > 0 && (
            <div className="mt-4 max-w-prose">
              <RemovedBox removed={state.removed} all />
            </div>
          )}
          {state.runId && (
            <p className="mt-2 text-caption text-ink-muted">
              {copy.steps.answerId} <span className="font-mono">{state.runId}</span>
            </p>
          )}
        </div>
      );
  }
}
