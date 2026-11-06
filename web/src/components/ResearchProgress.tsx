// ResearchProgress: a deep research run while it goes (ticket 157), in place of the ask box's steps, which keep their
// no-check-marks rule (Steps.tsx). The run's plan event (src/strata/research/run.py) lists every step it will take, so
// the rail shows them all at once:
//
// - The title, and under it "Step n of N · m:ss elapsed · usually 2 to 3 minutes". The clock ticks each second from the
//   run's start on this computer; it is the only time the tab claims as a fact. Past the usual high end the line says
//   "longer than usual" in place of the usual time, and the running step says "I'm still working on this step." once
//   no event has come for 30 seconds, as the ask box does.
// - A run written from sources read ahead of time (ticket 152) says the day it read them once, in one sentence under the
//   step count; no row carries a date (ticket 159).
// - The Progress meter (DESIGN.md): an 8 px pill track in surface-2 with a primary fill, full width of the prose
//   column, role="progressbar" valued by the steps done, so it moves on every step and sits still while the writer
//   works, which the writing row explains.
// - One row per planned step, one line each: a 16 px lucide icon in a fixed box (circle-check done, loader-circle
//   running, circle to do, circle-minus not reached, with its state in words for a screen reader), the step's label,
//   clipped with an ellipsis rather than wrapped, and after it in ink-muted only what the step gave: "kept 4 items",
//   "not reached", "70 sentences", "checked 12 of 65 sentences".
// - Each source's note (why it was not reached, or the day it was read) waits behind one closed disclosure.
// - One polite live region that says the running step's present-tense sentence, one sentence per step change.
//
// Nothing moves while the stream goes on (ticket 159): every row has one height, the icons share one box, the clock sits
// in a box of fixed width in tabular figures, the read sentence's line is held from the start when the run is a stored
// one, and only the meter's fill (300 ms, motion-meter) and the spinner move, neither under reduced motion. The step's
// number is not boxed: a box wide enough for "10" leaves a gap before "7" that reads as a fault, and the words after it
// move once, by one figure, at step 10.
import { useEffect, useState } from "react";
import { Circle, CircleCheck, CircleMinus, LoaderCircle } from "lucide-react";
import { copy } from "../copy";
import { cx } from "../lib/cx";
import { formatDate } from "../lib/format";
import { sourceWords, type PlannedStep, type ResearchPlan, type ResearchStep } from "../lib/research";
import { Disclosure } from "./Disclosure";
import { Fill } from "./Fill";

const words = copy.research;
const STILL_WORKING_MS = 30_000;

type State = "done" | "running" | "todo" | "not_reached";

const ICONS = {
  done: { Icon: CircleCheck, className: "text-primary" },
  running: { Icon: LoaderCircle, className: "animate-spin text-primary motion-reduce:animate-none" },
  todo: { Icon: Circle, className: "text-ink-muted" },
  not_reached: { Icon: CircleMinus, className: "text-ink-muted" },
} as const;

function stateOf(step: ResearchStep | undefined): State {
  if (!step) return "todo";
  return step.status === "running" ? "running" : step.status === "not_reached" ? "not_reached" : "done";
}

const clock = (seconds: number) => `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
// The rail's lines are status lines beside a clock, as "Step 2 of 13 · 0:27 elapsed", so their counts stay figures.
const figure = (count: number) => String(count);

function keptWords(count: number): string {
  return count === 0 ? words.progress.kept.none : count === 1 ? words.progress.kept.one : words.progress.kept.several(figure(count));
}

// What a step gave, after its label: once done, and while the writer or the checks run. Never a date (ticket 159).
function resultOf(step: ResearchStep | undefined, state: State, checked: number): string | null {
  if (!step) return null;
  if (step.kind === "facts") return state === "done" ? words.progress.result.facts : null;
  if (step.kind === "source") {
    if (state === "not_reached") return words.progress.result.notReached;
    return state === "done" ? keptWords(step.items ?? 0) : null;
  }
  if (step.kind === "writing") {
    if (step.kept_from) return words.progress.result.keptBrief;
    if (state === "running") return words.progress.writing.running;
    const count = step.sentences ?? 0;
    return count === 1 ? words.progress.writing.one : words.progress.writing.several(figure(count));
  }
  if (step.kind === "checking") {
    if (state === "running") return step.sentences ? words.progress.checked(figure(Math.min(checked, step.sentences)), figure(step.sentences)) : null;
    const removed = step.removed ?? 0;
    return removed === 0 ? words.progress.removed.none : removed === 1 ? words.progress.removed.one : words.progress.removed.several(figure(removed));
  }
  return null;
}

// A source's line behind the disclosure: its note once read ("read on November 5, 2026"), why it was not reached, or
// its state while it waits or runs.
function noteOf(step: ResearchStep | undefined, state: State): string {
  if (state === "not_reached") return words.progress.notes.notReached(step?.note);
  if (state === "done") return step?.note || keptWords(step?.items ?? 0);
  return words.progress.state[state];
}

// The present-tense sentence the live region says while a step runs, in the ask box's words.
function runningSentence(planned: PlannedStep, step: ResearchStep | undefined): string {
  if (planned.kind === "facts") return words.steps.facts.running;
  if (planned.kind === "writing") return words.steps.write.running;
  if (planned.kind === "checking") return words.steps.check.running;
  return words.steps.source.running(sourceWords(step?.source ?? planned.id.replace(/^source-/, ""), step?.label ?? planned.label));
}

// One row's height and the gap between rows, so the list holds its height from the plan.
const ROW = "1.5rem";
const GAP = "0.5rem";

export function ResearchProgress({
  name,
  plan,
  steps,
  checked,
  started,
  lastEventAt,
  stored = false,
}: {
  // The project's name, for the title.
  name: string;
  // The run's plan, once it has come; until then the rail shows the steps the stream has sent.
  plan: ResearchPlan | null;
  steps: ResearchStep[];
  // The sentences checked so far: the stream's sentence and removed events.
  checked: number;
  // When the run started and when its last event came, from Date.now().
  started: number;
  lastEventAt: number;
  // The run writes from sources read ahead of time (research.live_sources false, ticket 152), so the line that says
  // the day they were read is held from the start, before the first source's step names the day.
  stored?: boolean;
}) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);

  const byId = new Map(steps.map((step) => [step.id, step]));
  const planned: PlannedStep[] = plan ? plan.steps : steps.map((step) => ({ id: step.id, kind: step.kind, label: step.label ?? step.id }));
  const rows = planned.map((step) => ({ planned: step, step: byId.get(step.id), state: stateOf(byId.get(step.id)) }));
  const total = rows.length;
  const finished = rows.filter((one) => one.state === "done" || one.state === "not_reached").length;
  const runningAt = rows.findIndex((one) => one.state === "running");
  const n = runningAt >= 0 ? runningAt + 1 : Math.min(finished + 1, total);
  const elapsed = Math.max(0, Math.floor((now - started) / 1000));
  const [low, high] = plan ? plan.usual_seconds : [0, 0];
  const longer = plan !== null && elapsed > high;
  const stillWorking = longer && now - lastEventAt > STILL_WORKING_MS;
  const current = runningAt >= 0 ? rows[runningAt] : null;
  const readOn = steps.find((step) => step.stored_on)?.stored_on ?? null;
  const sources = rows.filter((one) => one.planned.kind === "source");
  const missed = sources.some((one) => one.state === "not_reached");

  return (
    <div data-research-progress className="@container/progress max-w-prose">
      <p data-progress-heading className="text-body text-ink">
        {words.progress.title(name)}
      </p>
      <p data-progress-line className="mt-1 text-small text-ink-muted tabular-nums">
        {plan && (
          <>
            <Fill template={words.progress.step} slots={{ n: figure(n), total: figure(total) }} />
            {" · "}
          </>
        )}
        <Fill
          template={words.progress.elapsed}
          slots={{
            clock: (
              <span data-progress-clock className="inline-block min-w-[3.5ch]">
                {clock(elapsed)}
              </span>
            ),
          }}
        />
        {plan && (
          <>
            {" · "}
            {longer ? words.progress.longer : words.progress.usual(figure(Math.round(low / 60)), figure(Math.round(high / 60)))}
          </>
        )}
      </p>
      {(stored || readOn) && (
        // The sentence's line, held before the day is known: two lines on a narrow column, where it wraps, and one on a
        // column of 36rem or more, where it fits.
        <p data-progress-read className="min-h-[2lh] text-small text-ink-muted @min-[36rem]/progress:min-h-[1lh]">
          {readOn ? words.readOnStored(formatDate(readOn)) : null}
        </p>
      )}
      {plan ? (
        <div
          role="progressbar"
          aria-label={words.progress.meter}
          aria-valuemin={0}
          aria-valuemax={total}
          aria-valuenow={finished}
          aria-valuetext={words.progress.meterText(figure(finished), figure(total))}
          className="mt-3 h-2 w-full overflow-hidden rounded-pill bg-surface-2"
        >
          <div
            className="h-full rounded-pill bg-primary transition-[width] duration-(--motion-meter) ease-[ease] motion-reduce:transition-none"
            style={{ width: `${total > 0 ? (finished / total) * 100 : 0}%` }}
          />
        </div>
      ) : (
        <div aria-hidden="true" className="mt-3 h-2 w-full rounded-pill bg-surface-2" />
      )}
      <ol className="mt-4 flex flex-col" style={{ gap: GAP, minHeight: plan ? `calc(${total} * ${ROW} + ${Math.max(0, total - 1)} * ${GAP})` : undefined }}>
        {rows.map(({ planned: step, step: sent, state }) => {
          const { Icon, className } = ICONS[state];
          const label = words.progress.label[step.kind] ?? step.label;
          const result = state === "running" && stillWorking ? copy.steps.stillWorking : resultOf(sent, state, checked);
          return (
            <li key={step.id} data-progress-id={step.id} data-progress-step={state} className="flex items-center gap-3 text-small" style={{ height: ROW }}>
              <span data-progress-icon aria-hidden="true" className="flex size-4 shrink-0 items-center justify-center">
                <Icon className={cx("size-4", className)} />
              </span>
              <span data-progress-title title={label} className={cx("min-w-0 truncate", state === "todo" ? "text-ink-muted" : "text-ink")}>
                {label}
                <span className="sr-only">, {words.progress.state[state]}</span>
              </span>
              {result && <span className="sr-only">, </span>}
              <span data-progress-result className="shrink-0 whitespace-nowrap text-ink-muted">
                {result}
              </span>
            </li>
          );
        })}
      </ol>
      <p data-progress-keep className="mt-4 text-small text-ink-muted">
        {words.progress.keepOpen}
      </p>
      {plan && sources.length > 0 && (
        <Disclosure label={missed ? words.progress.notes.missed : words.progress.notes.all} className="mt-2">
          <ul className="flex flex-col gap-1 text-small text-ink-muted">
            {sources.map(({ planned: step, step: sent, state }) => (
              <li key={step.id} data-progress-note={step.id}>
                <span className="text-ink">{step.label}</span>: {noteOf(sent, state)}
              </li>
            ))}
          </ul>
        </Disclosure>
      )}
      <p aria-live="polite" className="sr-only">
        {current ? runningSentence(current.planned, current.step) : ""}
      </p>
    </div>
  );
}
