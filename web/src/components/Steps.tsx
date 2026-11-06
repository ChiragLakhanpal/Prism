// Steps: what Prism is doing while an answer is built. The step in progress is in the present
// tense with a turning icon; done steps are in the past tense in ink-muted, with no check mark,
// so nothing suggests a step verified anything. Steps still to come are listed in ink-muted as
// "To do: ...", so the list keeps its height and turns each into a done step as it finishes
// (ticket 02's round 7 critique, settled with the 14 brief). A live region announces each step
// once, never token by token; the answer panel keeps its own and turns this one off. The list
// reserves its height, so new steps do not push the page.
import type { ReactNode } from "react";
import { LoaderCircle } from "lucide-react";
import { copy } from "../copy";
import { cx } from "../lib/cx";

// A line may set an ID in mono, so it is a node; the answer panel's own status line says the words.
// items: what a done step did, one sentence or two each, in a nested list under it, such as the
// verifier's six checks (the 24 brief, section 4.2); or, while a step runs, the steps it takes inside
// it, such as asking the model that judges sentences, indented under it in ink-muted with no spinner of
// their own. No icons and no check marks: the tense says it.
export type Step = { key: string; running: ReactNode; done: ReactNode; state: "running" | "done" | "todo"; items?: ReactNode[] };

export function Steps({
  steps,
  stillWorking = false,
  reserveLines = 0,
  announce = true,
  rail = true,
}: {
  steps: Step[];
  // No event has come for 30 seconds.
  stillWorking?: boolean;
  // Lines of height to hold while streaming, so the answer does not jump: four in the panel, for
  // reading the question, one tool, writing and checking. Each further tool adds a line.
  reserveLines?: number;
  // Announce the step in progress here. The answer panel announces steps in its own live region.
  announce?: boolean;
  // Hold the icon's width before each line, so a running step's icon and the text line up, and the
  // folded steps start under the disclosure's label. Off above an error alert, where no icon runs
  // and the lines start on the alert's edge.
  rail?: boolean;
}) {
  const current = steps.find((step) => step.state === "running");
  return (
    <div data-steps>
      <ol
        className="flex flex-col gap-1 text-small"
        style={reserveLines ? { minHeight: `calc(${reserveLines} * 1lh + ${reserveLines - 1} * 0.25rem)` } : undefined}
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
              rail && <span aria-hidden="true" className="size-4 shrink-0" />
            )}
            <span>
              {step.state === "running" ? step.running : step.done}
              {step.state === "running" && stillWorking && (
                <span className="block text-caption text-ink-muted">{copy.steps.stillWorking}</span>
              )}
              {step.state !== "todo" && step.items && step.items.length > 0 && (
                <ul data-step-items className="mt-1 flex max-w-prose list-none flex-col gap-1 pl-6 text-ink-muted">
                  {step.items.map((item, index) => (
                    <li key={index}>{item}</li>
                  ))}
                </ul>
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
