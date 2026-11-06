// ResearchProgress: a deep research run while it goes (ticket 157), in place of the ask box's steps, which keep their
// no-check-marks rule (Steps.tsx). The run's plan event (src/strata/research/run.py) lists every step it will take, so
// the rail shows them all at once:
//
// - The title, and under it "Step n of N · m:ss elapsed · usually 2 to 3 minutes". The clock ticks each second from the
//   run's start on this computer; it is the only time the tab claims as a fact. Past the usual high end the line says
//   "longer than usual", and the running step says "I'm still working on this step." once no event has come for 30
//   seconds, as the ask box does.
// - The Progress meter (DESIGN.md): an 8 px pill track in surface-2 with a primary fill, full width of the prose
//   column, role="progressbar" valued by the steps done, so it moves on every step and sits still while the writer
//   works, which the writing row explains.
// - One row per planned step with a 16 px lucide icon and its state in words for a screen reader: circle-check done,
//   loader-circle running, circle to do, circle-minus not reached. Each row holds a result line from the start, so
//   nothing moves when a step finishes except its icon and that line.
// - One polite live region that says the running step's present-tense sentence, one sentence per step change.
import { useEffect, useState, type ReactNode } from "react";
import { Circle, CircleCheck, CircleMinus, LoaderCircle } from "lucide-react";
import { copy } from "../copy";
import { cx } from "../lib/cx";
import { formatCount, formatDate } from "../lib/format";
import { sourceWords, type PlannedStep, type ResearchPlan, type ResearchStep } from "../lib/research";

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

// The line under a step: what it gave once done, what it is doing while it runs.
function resultOf(step: ResearchStep | undefined, state: State, checked: number): ReactNode {
  if (!step) return null;
  if (step.kind === "source") {
    if (state === "not_reached") return words.progress.notReached(step.note);
    if (state !== "done") return null;
    const kept = keptWords(step.items ?? 0);
    return step.stored_on ? words.progress.readOn(formatDate(step.stored_on), kept) : kept;
  }
  if (step.kind === "writing") {
    if (step.kept_from) return words.steps.kept(formatDate(step.kept_from));
    if (state === "running") return words.progress.writing.running;
    const count = step.sentences ?? 0;
    return count === 1 ? words.progress.writing.one : words.progress.writing.several(figure(count));
  }
  if (step.kind === "checking") {
    if (state === "running") return step.sentences ? words.progress.checked(figure(Math.min(checked, step.sentences)), figure(step.sentences)) : null;
    const removed = step.removed ?? 0;
    return removed === 0 ? words.steps.check.none : removed === 1 ? words.steps.check.one : words.steps.check.several(formatCount(removed));
  }
  return null;
}

// The present-tense sentence the live region says while a step runs, in the ask box's words.
function runningSentence(planned: PlannedStep, step: ResearchStep | undefined): string {
  if (planned.kind === "facts") return words.steps.facts.running;
  if (planned.kind === "writing") return words.steps.write.running;
  if (planned.kind === "checking") return words.steps.check.running;
  return words.steps.source.running(sourceWords(step?.source ?? planned.id.replace(/^source-/, ""), step?.label ?? planned.label));
}

export function ResearchProgress({
  name,
  plan,
  steps,
  checked,
  started,
  lastEventAt,
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

  const parts = [
    ...(plan ? [words.progress.step(figure(n), figure(total))] : []),
    longer ? `${words.progress.elapsed(clock(elapsed))}, ${words.progress.longer}` : words.progress.elapsed(clock(elapsed)),
    ...(plan ? [words.progress.usual(figure(Math.round(low / 60)), figure(Math.round(high / 60)))] : []),
  ];

  return (
    <div data-research-progress className="max-w-prose">
      <p className="text-body text-ink">{words.progress.title(name)}</p>
      <p data-progress-line className="mt-1 text-small text-ink-muted tabular-nums">
        {parts.join(" · ")}
      </p>
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
            className="h-full rounded-pill bg-primary transition-[width] duration-120 motion-reduce:transition-none"
            style={{ width: `${total > 0 ? (finished / total) * 100 : 0}%` }}
          />
        </div>
      ) : (
        <div aria-hidden="true" className="mt-3 h-2 w-full rounded-pill bg-surface-2" />
      )}
      <ol className="mt-4 flex flex-col gap-2">
        {rows.map(({ planned: step, step: sent, state }) => {
          const { Icon, className } = ICONS[state];
          const reached = state !== "todo";
          const result = resultOf(sent, state, checked);
          return (
            <li key={step.id} data-progress-id={step.id} data-progress-step={state} className="flex items-start gap-3">
              <Icon aria-hidden="true" className={cx("mt-0.5 size-4 shrink-0", className)} />
              <div className="min-w-0">
                <p data-progress-title className={cx("text-small", reached ? "text-ink" : "text-ink-muted")}>
                  {words.progress.label[step.kind] ?? step.label}
                  <span className="sr-only">, {words.progress.state[state]}</span>
                </p>
                <p data-progress-result className="min-h-[1lh] text-small text-ink-muted">
                  {result}
                </p>
                {state === "running" && stillWorking && <p className="text-small text-ink-muted">{copy.steps.stillWorking}</p>}
              </div>
            </li>
          );
        })}
      </ol>
      <p className="mt-4 text-small text-ink-muted">{words.progress.keepOpen}</p>
      <p aria-live="polite" className="sr-only">
        {current ? runningSentence(current.planned, current.step) : ""}
      </p>
    </div>
  );
}
