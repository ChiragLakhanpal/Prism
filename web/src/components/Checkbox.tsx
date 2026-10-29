// The checkbox (DESIGN.md section 5; the 30 brief, section 4.3): a native checkbox, styled. A 20 px box with
// radius-sm and a 2px line-strong border; checked, a primary fill with a white 16 px check, so the shape carries
// the state; hover gives an unchecked box a primary border and tint-hover, and a checked one primary-hover. The
// whole label is the target, at least 44 by 44 px. Read-only, as in a preview, it stays focusable with
// aria-disabled, so a screen reader can still read its state, and a click changes nothing. It changes in the same
// frame, with no transition. Section 3's risk table uses it, and ticket 36's draft rows can.
import type { ReactNode } from "react";
import { Check } from "lucide-react";
import { cx } from "../lib/cx";

export function Checkbox({
  checked,
  onChange,
  name,
  readOnly = false,
  children,
  className,
}: {
  checked: boolean;
  onChange: (checked: boolean) => void;
  // The accessible name, "Select {risk} for the PPSD". With a visible label, it contains the label's words
  // (WCAG 2.5.3).
  name?: string;
  readOnly?: boolean;
  // A visible label beside the box, which is then its name and part of its target.
  children?: ReactNode;
  className?: string;
}) {
  return (
    // With a label, the box keeps its 44 px target but sits flush with the label's top left, and the label starts
    // 32 px in (the 20 px box and 12 px, the nearest step on DESIGN.md's space scale to the 30 brief's 36), so the
    // column under it stays clean (the 30 brief, section 3.4).
    // With a label it is a block as tall as the label's lines, so a one-line name leaves no gap under it; the input's
    // ::after keeps the 44 px target (ticket 59).
    <label
      data-checkbox={checked ? "checked" : "unchecked"}
      className={cx(children !== undefined ? "flex" : "inline-flex min-h-11 min-w-11", "cursor-pointer items-start", readOnly && "cursor-default", className)}
    >
      <span className={cx("relative inline-flex size-11 shrink-0 items-center justify-center", children !== undefined && "-my-3 -ml-3")}>
        <input
          type="checkbox"
          checked={checked}
          aria-label={name}
          aria-disabled={readOnly || undefined}
          onClick={(event) => {
            if (readOnly) event.preventDefault();
          }}
          onChange={(event) => {
            if (!readOnly) onChange(event.currentTarget.checked);
          }}
          className={cx(
            // An ::after pads the box's own target to 44 by 44 px, so the box is the target wherever it sits.
            "peer relative size-5 cursor-pointer appearance-none rounded-sm border-2 after:absolute after:-inset-3 after:content-['']",
            "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus",
            readOnly
              ? "cursor-default border-line-strong bg-surface-2"
              : "border-line-strong bg-surface hover:border-primary hover:bg-tint-hover checked:border-primary checked:bg-primary checked:hover:bg-primary-hover",
          )}
        />
        <Check
          aria-hidden="true"
          strokeWidth={3}
          className={cx("pointer-events-none absolute size-4 opacity-0 peer-checked:opacity-100", readOnly ? "text-ink-muted" : "text-surface")}
        />
      </span>
      {children !== undefined && <span className="min-w-0 pt-0.5">{children}</span>}
    </label>
  );
}
