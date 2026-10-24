// Steps: what Strata is doing while an answer is built. The step in progress is in the present
// tense with a turning icon; done steps are in the past tense in ink-muted, with no check mark,
// so nothing suggests a step verified anything. Steps still to come are listed in ink-muted as
// "To do: ...", so the list keeps its height and turns each into a done step as it finishes
// (ticket 02's round 7 critique, settled with the 14 brief). A live region announces each step
// once, never token by token; the answer panel keeps its own and turns this one off. The list
// reserves its height, so new steps do not push the page.
import { LoaderCircle } from "lucide-react";
import { copy } from "../copy";
import { cx } from "../lib/cx";

export type Step = { key: string; running: string; done: string; state: "running" | "done" | "todo" };

export function Steps({
  steps,
  stillWorking = false,
  reserveLines = 0,
  announce = true,
}: {
  steps: Step[];
  // No event has come for 30 seconds.
  stillWorking?: boolean;
  // Lines of height to hold while streaming, so the answer does not jump (six in the panel).
  reserveLines?: number;
  // Announce the step in progress here. The answer panel announces steps in its own live region.
  announce?: boolean;
}) {
  const current = steps.find((step) => step.state === "running");
  return (
    <div data-steps>
      <ol
        className="flex flex-col gap-1 text-small"
        style={reserveLines ? { minHeight: `calc(${reserveLines} * 1.45em + ${reserveLines - 1} * 0.25rem)` } : undefined}
      >
        {steps.map((step) => (
          <li
            key={step.key}
            data-step={step.state}
            className={cx("flex items-start gap-2", step.state === "running" ? "text-ink" : "text-ink-muted")}
          >
            {step.state === "running" ? (
              <LoaderCircle aria-hidden="true" className="mt-0.5 size-4 shrink-0 animate-spin text-primary" />
            ) : (
              <span aria-hidden="true" className="size-4 shrink-0" />
            )}
            <span>
              {step.state === "running" ? step.running : step.done}
              {step.state === "running" && stillWorking && (
                <span className="block text-caption text-ink-muted">{copy.steps.stillWorking}</span>
              )}
            </span>
          </li>
        ))}
      </ol>
      {announce && (
        <p aria-live="polite" className="sr-only">
          {current?.running}
        </p>
      )}
    </div>
  );
}
