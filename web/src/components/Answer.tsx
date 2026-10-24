// Answer: the body of a cited answer, in each of its states. Ticket 14 puts it in the answer
// panel under the band and feeds it from the stream.
//
// Streaming: the steps, then skeleton bars sized to "In short" and the check line.
// Ready: "In short", the verified sentences with their markers, the check line, the removed
//   box, and the steps folded into a disclosure.
// Abstained: a tool held back (fewer than 20 comparables, say). Its own first-person sentence
//   stands in "In short", the check line and the removed box sit under it as in Ready, and
//   the rows it returned follow them, so the proof stays beside the sentence it checks.
// Unsupported: every sentence the agent wrote failed a check. "In short" says so, the removed box
//   lists each one with its reason, and there is no check line.
// Empty: nothing in the records or documents answers the question, said in the first person.
// Refused: a request on the refusal list, answered in plain text with no alert.
// Error: the steps done so far, an error alert and "Try again".
import { useId, useState, type ReactNode } from "react";
import { ChevronDown } from "lucide-react";
import { copy } from "../copy";
import { cx } from "../lib/cx";
import { Alert } from "./Alert";
import { Button } from "./Button";
import { CheckLine, RemovedBox, type NotChecked, type Removed } from "./Checks";
import { numText } from "./Num";
import { LoadingLabel, Skeleton, SkeletonLine, SkeletonText } from "./Skeleton";
import { Steps, type Step } from "./Steps";

type Checks = {
  numbers?: { matched: number; total: number };
  dates?: { matched: number; total: number };
  quotes?: { found: number; total: number };
  notChecked: NotChecked[];
  removed: Removed[];
  names?: string[];
};

export type AnswerState =
  // announce is false in the answer panel, which announces steps in its own live region.
  | { status: "streaming"; steps: Step[]; stillWorking?: boolean; announce?: boolean }
  | { status: "ready"; steps: Step[]; runId: string; sentences: ReactNode; checks: Checks }
  | { status: "abstained"; steps: Step[]; runId: string; sentence: ReactNode; rows: ReactNode; checks: Checks }
  | { status: "unsupported"; steps: Step[]; runId: string; message: ReactNode; removed: Removed[] }
  | { status: "empty"; steps: Step[]; runId: string; message: ReactNode; action?: ReactNode }
  | { status: "refused"; steps: Step[]; runId: string; message: ReactNode; note?: ReactNode }
  | { status: "error"; steps: Step[]; message: ReactNode; onRetry: () => void };

function InShort({ children }: { children: ReactNode }) {
  return (
    <>
      <h3 className="text-label text-ink-muted uppercase">{copy.answer.inShort}</h3>
      <div data-in-short className="mt-2 max-w-prose text-body text-ink">{children}</div>
    </>
  );
}

function StepsTaken({ steps: all, runId }: { steps: Step[]; runId: string }) {
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
        <p className="mt-2 text-caption text-ink-muted">
          {copy.steps.answerId} <span className="font-mono">{runId}</span>
        </p>
      </div>
    </div>
  );
}

// The check line and the removed box keep the answer's measure, about 65 characters a line.
function ChecksBlock({ checks }: { checks: Checks }) {
  return (
    <div className="mt-4 flex max-w-prose flex-col gap-2">
      <CheckLine numbers={checks.numbers} dates={checks.dates} quotes={checks.quotes} notChecked={checks.notChecked} />
      <RemovedBox removed={checks.removed} names={checks.names} />
    </div>
  );
}

export function Answer({ state }: { state: AnswerState }) {
  switch (state.status) {
    case "streaming":
      return (
        <div data-answer="streaming" aria-busy="true">
          <Steps steps={state.steps} stillWorking={state.stillWorking} reserveLines={6} announce={state.announce ?? true} />
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
          <InShort>{state.sentences}</InShort>
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
          <InShort>{state.message}</InShort>
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
          {state.steps.length > 0 && <Steps steps={state.steps} />}
          {/* The alert keeps the answer's measure, as the check line and the removed box do. */}
          <Alert
            state="error"
            live="alert"
            className="mt-4 max-w-prose"
            action={
              <Button variant="secondary" onClick={state.onRetry}>
                {copy.answer.tryAgain}
              </Button>
            }
          >
            {state.message}
          </Alert>
        </div>
      );
  }
}
