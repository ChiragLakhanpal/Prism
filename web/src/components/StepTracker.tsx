// The step tracker at the top of the package workspace (ticket 115): section 2's steps, from the bid invitation to the
// contract's completion, as nodes joined by one line, each marked in words and in form as done (a tick and the
// actual date), next (filled), planned (an outline), late (the warning colour and the days late) or unknown (dots).
//
// - The states, dates and days late are the steps routes' (src/strata/server/tracker.py), read from the package's plan,
//   its contract's signing and the plan's Process Status as of the page's date. The browser adds no days and compares
//   no dates (CLAUDE.md rule 1).
// - For a screen reader it is a list named by its heading, one item per step, whose text says the state in words.
//   One node is a tab stop, the step that needs a look (the first late or next one); the arrow keys, Home and End
//   move focus along the nodes.
// - The next node's fill enters over 160 ms when the steps arrive (DESIGN.md section 4, Motion), and nothing moves
//   under reduced motion.
// - From a card 36rem wide five or six nodes sit in a row, on a grid whose four rows (node, label, state, date) every
//   step shares, so the state words line up across the row however the labels wrap; below it they stack, with the
//   line running down beside them. A consulting firm's nine steps would leave each about 90 px, narrower than one
//   date, so they stay a list at every width, each step's label, state and date on one line from a 36rem card.
// - The source line ends the card in its foot strip, as each block of evidence ends (ticket 101's critique, round 2).
//   The stretch of line between two done steps is drawn in the done colour.
// - While the steps load it holds its place with static bars; when they fail, it keeps its card with one sentence
//   that points to section 2, which says why and offers Try again.
import { useId, useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import { Check, TriangleAlert } from "lucide-react";
import { copy } from "../copy";
import { cx } from "../lib/cx";
import type { StepDate, StepState } from "../lib/steps";
import { familyStep, stepFamily } from "../steps";
import { Fill } from "./Fill";
import { FootStrip } from "./FootStrip";
import { Num } from "./Num";
import { Source } from "./Source";
import type { StepsState } from "./StepsSection";

const words = copy.stepTracker;

// A step's date in the table form ("Jun 22, 2026", DESIGN.md section 7 rule 13): short, and it may break at a space,
// so it stays inside its step in a row of six even with wider letter and word spacing (WCAG 1.4.12).
const stepDate = (iso: string) => <Num date={iso} style="table" />;
// A date in the sentences under the list, in the sentence form.
const date = (iso: string) => <Num date={iso} />;

// The most steps that share one row from a 36rem card; more stay a list (the design review's R2-B1).
const ROW_MOST = 6;

// The state in words on one line, then on the next the date it rests on, so every step's state stays level and short.
function stateLine(step: StepDate): ReactNode {
  switch (step.state) {
    case "done":
      return words.done;
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

// plan is the plan version the dates come from, or null when no plan dates the steps: then the note under the list
// says once why no step has a date, and each unknown step reads only "No date".
function dateLine(step: StepDate, plan: string | null): ReactNode {
  if (step.state === "done") return stepDate(step.actual_date!);
  if (step.state === "unknown") return plan === null ? null : step.plan_latest_date ? words.noActual : words.notInPlan;
  return <Fill template={words.plannedFor} slots={{ date: stepDate(step.plan_latest_date!) }} />;
}

const STATE_TEXT: Record<StepState, string> = {
  done: "text-success font-semibold",
  next: "text-primary font-semibold",
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

function Node({ state, row }: { state: StepState; row: boolean }) {
  return (
    <span
      aria-hidden="true"
      data-step-node={state}
      className={cx("relative z-10 flex size-6 shrink-0 items-center justify-center rounded-full border-2", row && "@min-[36rem]/tracker:mb-2", NODE[state])}
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

// The card reads its own width (ticket 101's critique, round 2): beside the evidence drawer at 1280 px the page area
// narrows but the card does not, so it keeps its row of steps. Its sides are 16 px, and 24 px from a 48rem window, as
// a Task zone's are, so its text keeps the zones' edge; its foot strip takes the same sides (app.css, "Task zones").
const FRAME = "@container/tracker rounded-md border border-line bg-surface";
const INSIDE = "px-4 py-4 md:px-6";
const CARD = `${FRAME} ${INSIDE}`;

// The list's classes in its two layouts. In both, the steps stand 8 px apart with 8 px under each, so a focused step's
// ring (2 px out, 2 px wide) clears the next node, and each step's part of the line runs on through the gap to it.
const LAYOUT = {
  row: {
    list: "mt-4 flex flex-col gap-2 @min-[36rem]/tracker:grid @min-[36rem]/tracker:auto-cols-fr @min-[36rem]/tracker:grid-flow-col @min-[36rem]/tracker:grid-rows-[repeat(4,auto)] @min-[36rem]/tracker:gap-0",
    item: "@min-[36rem]/tracker:row-span-4 @min-[36rem]/tracker:grid @min-[36rem]/tracker:grid-cols-1 @min-[36rem]/tracker:grid-rows-subgrid @min-[36rem]/tracker:justify-items-center @min-[36rem]/tracker:gap-0 @min-[36rem]/tracker:px-1 @min-[36rem]/tracker:pb-0 @min-[36rem]/tracker:text-center",
    line: "@min-[36rem]/tracker:bottom-auto @min-[36rem]/tracker:left-1/2 @min-[36rem]/tracker:h-0.5 @min-[36rem]/tracker:w-full @min-[36rem]/tracker:translate-x-0 @min-[36rem]/tracker:-translate-y-1/2",
    words: "@min-[36rem]/tracker:contents",
  },
  list: {
    list: "mt-4 flex flex-col gap-2",
    item: "",
    line: "",
    words:
      "@min-[36rem]/tracker:grid @min-[36rem]/tracker:grid-cols-[minmax(0,16rem)_minmax(0,9rem)_minmax(0,1fr)] @min-[36rem]/tracker:items-baseline @min-[36rem]/tracker:gap-x-4 @min-[36rem]/tracker:pt-0.5",
  },
};

export function StepTracker({ state }: { state: StepsState }) {
  const headingId = useId();
  const list = useRef<HTMLOListElement>(null);
  const [focused, setFocused] = useState<number | null>(null);
  if (state.status === "loading") return <TrackerSkeleton />;
  // The card stays, so the page under it does not jump, with one sentence that sends you to section 2's Try again.
  if (state.status === "error")
    return (
      <section data-step-tracker className={CARD}>
        <h2 className="text-h3 text-ink-heading">{words.heading}</h2>
        <p data-tracker-error className="mt-2 text-caption text-ink-muted">
          {words.error}
        </p>
      </section>
    );
  const dates = state.result.step_dates;
  const family = stepFamily(dates?.family);
  if (!dates || !family || dates.steps.length === 0) return null;
  const steps = dates.steps;
  const layout = steps.length <= ROW_MOST ? LAYOUT.row : LAYOUT.list;
  const current = Math.max(0, steps.findIndex((step) => step.state === "late" || step.state === "next"));
  // A new answer may hold fewer steps, as when a package from a sentence changes its method family.
  const stop = focused !== null && focused < steps.length ? focused : current;
  const plan = steps.find((step) => step.plan_latest_version_date)?.plan_latest_version_date ?? null;
  // The source line names each record a done step's date came from: the plan, and for the signing the contract's.
  const recorded = new Set(steps.map((step) => step.actual_source));
  const source = recorded.has("award_notice") ? words.sourceNotice : recorded.has("contract_awards") ? words.sourceAwards : words.source;
  const counted = steps.some((step) => step.state === "late") ? words.lateTo : words.asOf;

  const move = (event: KeyboardEvent<HTMLOListElement>) => {
    const to = KEYS[event.key];
    if (!to) return;
    event.preventDefault();
    const index = to(stop, steps.length - 1);
    setFocused(index);
    const node = list.current?.querySelectorAll<HTMLElement>("[data-step-state]")[index];
    if (!node) return;
    // In the side column, where the ask box does not reach, a step already whole on screen under the bar takes focus
    // without scrolling the page: the browser would otherwise scroll it clear of the box's scroll padding, which moves
    // the page for nothing while the card sticks. A step under the bar or below the window is brought into view as
    // anywhere else (DESIGN.md section 10's rule for sticky parts; ticket 130, review round 1, B1).
    const bar = parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--frame-top")) || 0;
    const box = node.getBoundingClientRect();
    const seen = node.closest("[data-side-sticky]") !== null && box.top >= bar && box.bottom <= window.innerHeight;
    node.focus(seen ? { preventScroll: true } : undefined);
  };

  return (
    // Not a named region: the list carries the heading's name, so a screen reader hears it once.
    <section data-step-tracker className={FRAME}>
      <div className={INSIDE}>
      <h2 id={headingId} className="text-h3 text-ink-heading">
        {words.heading}
      </h2>
      <ol
        ref={list}
        aria-labelledby={headingId}
        onKeyDown={move}
        className={layout.list}
        data-numbers
      >
        {steps.map((step, index) => (
          <li
            key={step.step_key}
            data-step-state={step.state}
            tabIndex={index === stop ? 0 : -1}
            onFocus={() => setFocused(index)}
            className={cx("relative flex min-w-0 gap-3 rounded-sm pb-2 last:pb-0", layout.item)}
          >
            {/* One line joins the nodes: each step but the last draws its part, to the next node's centre. */}
            {index < steps.length - 1 && (
              <span
                aria-hidden="true"
                className={cx(
                  "absolute top-3 -bottom-2 left-3 w-0.5 -translate-x-1/2",
                  layout.line,
                  step.state === "done" && steps[index + 1].state === "done" ? "bg-success" : "bg-line",
                )}
              />
            )}
            <Node state={step.state} row={layout === LAYOUT.row} />
            {/* From a 36rem card, in a row the label, state and date each take their row of the step's subgrid,
                so an empty line keeps its row and the next step's words stay level; in a list they share one line. */}
            <span className={cx("flex min-w-0 flex-col", layout.words)}>
              <span className="text-small font-semibold text-balance wrap-break-word text-ink">{familyStep(family, step.step_key)?.label ?? step.step_key}</span>
              <span className={cx("text-caption text-balance", STATE_TEXT[step.state])}>{stateLine(step)}</span>
              <span className="text-caption text-balance text-ink-muted">{dateLine(step, plan)}</span>
            </span>
          </li>
        ))}
      </ol>
      {/* The plan's Process Status is in the side panel, so the tracker does not repeat it (ticket 126). */}
      {!plan && (
        <p data-tracker-note className="mt-4 text-caption text-ink-muted">
          {words.none}
        </p>
      )}
      </div>
      {plan && (
        <FootStrip>
          <Source>
            <Fill template={source} slots={{ plan: date(plan) }} /> <Fill template={counted} slots={{ date: date(state.result.as_of) }} />
          </Source>
        </FootStrip>
      )}
    </section>
  );
}

// One line of words as a static bar, at the caption's 20 px line height. A wide line shows only from a 36rem card,
// where a label and a date take two lines in their narrow column; a narrow one only below it, where the source line
// takes up to three, as it does when it names the contract awards data too.
const SHOWN = {
  always: "flex",
  wide: "hidden @min-[36rem]/tracker:flex",
  narrow: "flex @min-[36rem]/tracker:hidden",
  // In a row narrower than 52, 40 and 37.5rem, a step's words take one, two and three more lines than in a wide one, as
  // the demo package's steps do (ticket 59, the critique of round 2).
  rowBelow52: "hidden @min-[36rem]/tracker:@max-[52rem]/tracker:flex",
  rowBelow40: "hidden @min-[36rem]/tracker:@max-[40rem]/tracker:flex",
  rowBelow37: "hidden @min-[36rem]/tracker:@max-[37.5rem]/tracker:flex",
};
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
    <div aria-hidden="true" data-step-tracker-skeleton className={FRAME}>
      <div className={INSIDE}>
      <span className="flex h-6 items-center">
        <span className="block h-4 w-48 rounded-xs bg-surface-2" />
      </span>
      <span className="mt-4 flex flex-col @min-[36rem]/tracker:flex-row">
        {Array.from({ length: 6 }, (_, index) => (
          <span key={index} className="flex gap-3 pb-4 last:pb-0 @min-[36rem]/tracker:flex-1 @min-[36rem]/tracker:flex-col @min-[36rem]/tracker:items-center @min-[36rem]/tracker:gap-2 @min-[36rem]/tracker:px-1 @min-[36rem]/tracker:pb-0">
            <span className="block size-6 shrink-0 rounded-full bg-surface-2" />
            <span className="flex flex-col @min-[36rem]/tracker:items-center">
              <Bar width="w-32 @min-[36rem]/tracker:w-16" />
              <Bar width="w-12" kind="wide" />
              <Bar width="w-14" kind="rowBelow52" />
              <Bar width="w-10" kind="rowBelow40" />
              <Bar width="w-12" kind="rowBelow37" />
              <Bar width="w-24 @min-[36rem]/tracker:w-16" />
              <Bar width="w-40 @min-[36rem]/tracker:w-16" />
              <Bar width="w-12" kind="wide" />
            </span>
          </span>
        ))}
      </span>
      </div>
      {/* The source line in the foot strip, to the card's edges, as the drawn tracker ends (ticket 101; ticket 59, the
          critique of round 2). */}
      <FootStrip>
        <span className="flex flex-col">
          <Bar width="w-4/5" />
          <Bar width="w-2/5" />
          <Bar width="w-2/5" kind="narrow" />
        </span>
      </FootStrip>
    </div>
  );
}
