// The step tracker at the top of the package workspace (ticket 115): section 2's steps, from the bid invitation to the
// contract's completion, as nodes joined by one line, each marked in words and in form as done (a tick and the
// actual date), next (filled), planned (an outline), late (the warning colour and the days late) or unknown (dots).
//
// - The states, dates and days late are the steps routes' (src/strata/server/tracker.py), read from the package's plan
//   as of the page's date. The browser adds no days and compares no dates (CLAUDE.md rule 1).
// - For a screen reader it is a list named by its heading, one item per step, whose text says the state in words.
//   One node is a tab stop, the step that needs a look (the first late or next one); the arrow keys, Home and End
//   move focus along the nodes.
// - The next node's fill enters over 160 ms when the steps arrive (DESIGN.md section 4, Motion), and nothing moves
//   under reduced motion.
// - From a 768 px page area the nodes sit in a row; below it they stack, with the line running down beside them.
// - While the steps load it holds its place with static bars; when they fail, section 2 says so and offers Try again,
//   so the tracker shows nothing.
import { useId, useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import { Check, TriangleAlert } from "lucide-react";
import { copy } from "../copy";
import { cx } from "../lib/cx";
import type { StepDate, StepState } from "../lib/steps";
import { familyStep, stepFamily } from "../steps";
import { Fill } from "./Fill";
import { Num } from "./Num";
import { Source } from "./Source";
import type { StepsState } from "./StepsSection";

const words = copy.stepTracker;

const date = (iso: string) => <Num date={iso} />;

// The state in words, then the date it rests on.
function stateLine(step: StepDate): ReactNode {
  switch (step.state) {
    case "done":
      return <Fill template={words.done} slots={{ date: date(step.actual_date!) }} />;
    case "next":
      return words.next;
    case "late":
      return step.late_days === 1 ? words.lateOne : <Fill template={words.late} slots={{ days: <Num value={step.late_days!} options={{ compact: false }} /> }} />;
    case "unknown":
      return words.unknown;
    case "planned":
      return null;
  }
}

function dateLine(step: StepDate): ReactNode {
  if (step.state === "done") return null;
  if (step.state === "unknown") return step.plan_latest_date ? words.noActual : words.notInPlan;
  return <Fill template={words.plannedFor} slots={{ date: date(step.plan_latest_date!) }} />;
}

const STATE_TEXT: Record<StepState, string> = {
  done: "text-success font-semibold",
  next: "text-ink-heading font-semibold",
  planned: "text-ink-muted",
  late: "text-warning font-semibold",
  unknown: "text-ink-muted",
};

const NODE: Record<StepState, string> = {
  done: "border-success bg-success text-surface",
  next: "border-primary bg-surface",
  planned: "border-line-strong bg-surface",
  late: "border-warning-icon bg-warning-bg text-warning-icon",
  unknown: "border-dotted border-line-strong bg-surface",
};

function Node({ state }: { state: StepState }) {
  return (
    <span
      aria-hidden="true"
      data-step-node={state}
      className={cx("relative z-10 flex size-6 shrink-0 items-center justify-center rounded-full border-2", NODE[state])}
    >
      {state === "done" && <Check data-node-tick className="size-4" strokeWidth={3} />}
      {state === "next" && <span data-node-fill className="animate-fill-in absolute inset-0.5 rounded-full bg-primary" />}
      {state === "late" && <TriangleAlert className="size-3" strokeWidth={2.5} />}
    </span>
  );
}

const KEYS: Record<string, (index: number, last: number) => number> = {
  ArrowRight: (index, last) => Math.min(index + 1, last),
  ArrowDown: (index, last) => Math.min(index + 1, last),
  ArrowLeft: (index) => Math.max(index - 1, 0),
  ArrowUp: (index) => Math.max(index - 1, 0),
  Home: () => 0,
  End: (_, last) => last,
};

export function StepTracker({ state }: { state: StepsState }) {
  const headingId = useId();
  const list = useRef<HTMLOListElement>(null);
  const [focused, setFocused] = useState<number | null>(null);
  if (state.status === "loading") return <TrackerSkeleton />;
  if (state.status === "error") return null;
  const dates = state.result.step_dates;
  const family = stepFamily(dates?.family);
  if (!dates || !family || dates.steps.length === 0) return null;
  const steps = dates.steps;
  const current = Math.max(0, steps.findIndex((step) => step.state === "late" || step.state === "next"));
  const stop = focused ?? current;
  const plan = steps.find((step) => step.plan_latest_version_date)?.plan_latest_version_date ?? null;

  const move = (event: KeyboardEvent<HTMLOListElement>) => {
    const to = KEYS[event.key];
    if (!to) return;
    event.preventDefault();
    const index = to(stop, steps.length - 1);
    setFocused(index);
    list.current?.querySelectorAll<HTMLElement>("[data-step-state]")[index]?.focus();
  };

  return (
    <section aria-labelledby={headingId} data-step-tracker className="rounded-md border border-line bg-surface p-4 @md/page:p-6">
      <h2 id={headingId} className="text-h3 text-ink-heading">
        {words.heading}
      </h2>
      <ol ref={list} aria-labelledby={headingId} onKeyDown={move} className="mt-4 flex flex-col @md/page:flex-row" data-numbers>
        {steps.map((step, index) => (
          <li
            key={step.step_key}
            data-step-state={step.state}
            tabIndex={index === stop ? 0 : -1}
            onFocus={() => setFocused(index)}
            className={cx(
              "relative flex min-w-0 gap-3 rounded-sm pb-4 last:pb-0",
              "@md/page:flex-1 @md/page:flex-col @md/page:items-center @md/page:gap-2 @md/page:px-1 @md/page:pb-0 @md/page:text-center",
            )}
          >
            {/* One line joins the nodes: each step but the last draws its part, to the next node's centre. */}
            {index < steps.length - 1 && (
              <span
                aria-hidden="true"
                className="absolute top-3 bottom-0 left-3 w-0.5 -translate-x-1/2 bg-line @md/page:bottom-auto @md/page:left-1/2 @md/page:h-0.5 @md/page:w-full @md/page:translate-x-0 @md/page:-translate-y-1/2"
              />
            )}
            <Node state={step.state} />
            <span className="flex min-w-0 flex-col">
              <span className="text-small font-semibold wrap-break-word text-ink">{familyStep(family, step.step_key)?.label ?? step.step_key}</span>
              {stateLine(step) && <span className={cx("text-caption", STATE_TEXT[step.state])}>{stateLine(step)}</span>}
              {dateLine(step) && <span className="text-caption text-ink-muted">{dateLine(step)}</span>}
            </span>
          </li>
        ))}
      </ol>
      {plan ? (
        <Source className="mt-4">
          <Fill template={words.source} slots={{ plan: date(plan), date: date(state.result.as_of) }} />
        </Source>
      ) : (
        <p data-tracker-note className="mt-4 text-caption text-ink-muted">
          {words.none}
        </p>
      )}
    </section>
  );
}

// One line of words as a static bar, at the caption's 20 px line height. A wide line shows only from a 768 px page area,
// where a label and a date take two lines in their narrow column; a narrow one only below it, where the source line
// takes two.
const SHOWN = { always: "flex", wide: "hidden @md/page:flex", narrow: "flex @md/page:hidden" };
function Bar({ width, kind = "always" }: { width: string; kind?: keyof typeof SHOWN }) {
  return (
    <span className={cx("h-5 items-center", SHOWN[kind])}>
      <span className={cx("block h-3.5 rounded-xs bg-surface-2", width)} />
    </span>
  );
}

// Static bars where the tracker will be, laid out as it is, so the page under it barely moves when the steps arrive:
// the title, six nodes with their words, and the source line.
export function TrackerSkeleton() {
  return (
    <div aria-hidden="true" data-step-tracker-skeleton className="rounded-md border border-line bg-surface p-4 @md/page:p-6">
      <span className="flex h-6 items-center">
        <span className="block h-4 w-48 rounded-xs bg-surface-2" />
      </span>
      <span className="mt-4 flex flex-col @md/page:flex-row">
        {Array.from({ length: 6 }, (_, index) => (
          <span key={index} className="flex gap-3 pb-4 last:pb-0 @md/page:flex-1 @md/page:flex-col @md/page:items-center @md/page:gap-2 @md/page:px-1 @md/page:pb-0">
            <span className="block size-6 shrink-0 rounded-full bg-surface-2" />
            <span className="flex flex-col @md/page:items-center">
              <Bar width="w-32 @md/page:w-16" />
              <Bar width="w-12" kind="wide" />
              <Bar width="w-24 @md/page:w-16" />
              <Bar width="w-40 @md/page:w-16" />
              <Bar width="w-12" kind="wide" />
            </span>
          </span>
        ))}
      </span>
      <span className="mt-4 flex flex-col">
        <Bar width="w-4/5" />
        <Bar width="w-2/5" kind="narrow" />
      </span>
    </div>
  );
}
