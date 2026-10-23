// Answer: the body of a cited answer, in each of its states. Ticket 14 puts it in the answer
// panel under the band and feeds it from the stream.
//
// Streaming: the steps, then skeleton bars sized to "In short" and the check line.
// Ready: "In short", the verified sentences with their markers, the check line, the removed
//   box, and the steps folded into a disclosure.
// Abstained: a tool held back (fewer than 20 comparables, say). Its own first-person sentence
//   stands in "In short", and the rows it returned follow.
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
import { Skeleton, LoadingLabel } from "./Skeleton";
import { Steps, type Step } from "./Steps";

type Checks = {
  numbers?: { matched: number; total: number };
  quotes?: { found: number; total: number };
  notChecked: NotChecked[];
  removed: Removed[];
  names?: string[];
};

export type AnswerState =
  | { status: "streaming"; steps: Step[]; stillWorking?: boolean }
  | { status: "ready"; steps: Step[]; runId: string; sentences: ReactNode; checks: Checks }
  | { status: "abstained"; steps: Step[]; runId: string; sentence: ReactNode; rows: ReactNode; checks: Checks }
  | { status: "empty"; steps: Step[]; runId: string; message: ReactNode }
  | { status: "refused"; steps: Step[]; runId: string; message: ReactNode; note?: ReactNode }
  | { status: "error"; steps: Step[]; message: ReactNode; onRetry: () => void };

function InShort({ children }: { children: ReactNode }) {
  return (
    <>
      <h3 className="text-label text-ink-muted uppercase">{copy.answer.inShort}</h3>
      <div className="mt-2 max-w-prose text-body text-ink">{children}</div>
    </>
  );
}

function StepsTaken({ steps, runId }: { steps: Step[]; runId: string }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  const count = steps.length;
  return (
    <div className="mt-4">
      <Button variant="ghost" icon={ChevronDown} aria-expanded={open} aria-controls={id} onClick={() => setOpen(!open)}
        className={cx("[&>svg]:transition-transform", open && "[&>svg]:rotate-180")}>
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

function ChecksBlock({ checks }: { checks: Checks }) {
  return (
    <>
      <div className="mt-4">
        <CheckLine numbers={checks.numbers} quotes={checks.quotes} notChecked={checks.notChecked} />
      </div>
      <div className="mt-2">
        <RemovedBox removed={checks.removed} names={checks.names} />
      </div>
    </>
  );
}

export function Answer({ state }: { state: AnswerState }) {
  switch (state.status) {
    case "streaming":
      return (
        <div data-answer="streaming" aria-busy="true">
          <Steps steps={state.steps} stillWorking={state.stillWorking} reserveLines={6} />
          <LoadingLabel />
          <div className="mt-6 flex max-w-prose flex-col gap-2">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-11/12" />
            <Skeleton className="h-4 w-3/5" />
            <Skeleton className="mt-2 h-9 w-full rounded-md" />
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
          <div className="mt-4">{state.rows}</div>
          <ChecksBlock checks={state.checks} />
          <StepsTaken steps={state.steps} runId={state.runId} />
        </div>
      );
    case "empty":
      return (
        <div data-answer="empty">
          <p className="max-w-prose text-body text-ink">{state.message}</p>
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
          <Alert
            state="error"
            live="alert"
            className="mt-4"
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
