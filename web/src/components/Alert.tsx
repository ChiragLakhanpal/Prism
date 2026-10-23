// Alerts (DESIGN.md section 5): the state's background, a 4 px left border in the state's
// colour, its icon, and one sentence. An action, such as "Try again", may follow.
// Errors interrupt (role="alert"); the others are read in turn (role="status") or not at all.
import type { ReactNode } from "react";
import { cx } from "../lib/cx";
import { STATES, type State } from "./state";

export function Alert({
  state,
  children,
  action,
  live,
  className,
}: {
  state: State;
  children: ReactNode;
  action?: ReactNode;
  // "alert" for errors that just happened, "status" for news, or none for alerts on load.
  live?: "alert" | "status";
  className?: string;
}) {
  const look = STATES[state];
  return (
    <div
      role={live}
      data-alert={state}
      className={cx("flex gap-3 rounded-r-md border-l-4 px-4 py-3", look.box, look.border, className)}
    >
      <look.Icon aria-hidden="true" className={cx("mt-1 size-4 shrink-0", look.icon)} />
      <div className="min-w-0 flex-1">
        <p className={cx("text-body", look.text)}>{children}</p>
        {action && <div className="mt-3">{action}</div>}
      </div>
    </div>
  );
}
