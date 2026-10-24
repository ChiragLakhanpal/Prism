// State stepper (DESIGN.md section 5; the 35 brief, section 4.4): a draft's states in order, Draft, Checked
// by you, Exported, as an ordered list. Each state's icon shape carries it as well as its word, and no
// state takes a color, because green would read as "safe" and "Checked by you" is the person's own act.
// Done: circle-check, ink-muted. Current: circle-dot in primary, the word in 700 ink-heading, with
// aria-current="step". Not reached: an empty circle in line-strong. Each word reserves its bold width,
// so the row never shifts when the current step moves. A discarded draft shows a caption instead.
import { Fragment } from "react";
import { ChevronRight, Circle, CircleCheck, CircleDot } from "lucide-react";
import { copy } from "../copy";
import { cx } from "../lib/cx";

export type StepperState = "draft" | "checked" | "exported";

const ORDER: StepperState[] = ["draft", "checked", "exported"];

export function StateStepper({ state, checkedBy }: {
  state: StepperState;
  // The author's name when the viewer is a teammate: "Checked by Ana Example".
  checkedBy?: string | null;
}) {
  const words = copy.draft.state;
  const labels: Record<StepperState, string> = {
    draft: words.draft,
    checked: checkedBy ? words.checkedOther(checkedBy) : words.checkedYou,
    exported: words.exported,
  };
  const at = ORDER.indexOf(state);
  return (
    <ol aria-label={words.label} data-stepper={state} className="flex flex-wrap items-center gap-x-2 gap-y-1 text-small">
      {ORDER.map((step, index) => {
        const done = index < at;
        const current = index === at;
        const Icon = done ? CircleCheck : current ? CircleDot : Circle;
        return (
          <Fragment key={step}>
            {index > 0 && (
              <li aria-hidden="true" className="flex items-center">
                <ChevronRight className="size-4 text-ink-muted" />
              </li>
            )}
            <li aria-current={current ? "step" : undefined} data-step-state={done ? "done" : current ? "current" : "todo"} className="flex items-center gap-1">
              <Icon
                aria-hidden="true"
                className={cx("size-4 shrink-0 transition-opacity duration-150", current ? "text-primary" : done ? "text-ink-muted" : "text-line-strong")}
              />
              {/* The bold width is reserved by an invisible bold copy of the word drawn by ::after from
                  data-text, so a change of weight moves nothing and the word is read once. */}
              <span
                data-text={labels[step]}
                className={cx(
                  "inline-flex flex-col after:invisible after:h-0 after:overflow-hidden after:font-bold after:content-[attr(data-text)]",
                  current ? "font-bold text-ink-heading" : "text-ink-muted",
                )}
              >
                {labels[step]}
              </span>
              {done && <span className="sr-only">{words.doneSuffix}</span>}
            </li>
          </Fragment>
        );
      })}
    </ol>
  );
}

// In place of the stepper on a discarded draft.
export function DiscardedOn({ date }: { date: string }) {
  return <p className="text-caption text-ink-muted">{copy.draft.state.discarded(date)}</p>;
}
