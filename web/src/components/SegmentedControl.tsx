// Segmented control (DESIGN.md section 5; the 27 brief, section 4.3): two to four touching pill segments for one
// choice, such as section 2's "Date each step with". A fieldset with a visible legend and native radios, so the
// keyboard gets one tab stop and the arrow keys move and select, as the WAI-ARIA radio group does.
//
// Each segment: small text, 4 px by 16 px padding, at least 32 px tall (44 px below a 768 px page area, where the
// segments stack full width), a 1px line-strong border and a surface fill; the outer corners are radius-pill. The
// selected one has the tint fill, an inset 2px primary ring, so its size never changes, and a 16 px check in primary
// before its text: the check is the shape that carries the state, since tint against surface alone is 1.06:1.
// Hover gives an unselected segment tint-hover; focus draws the 2px focus outline with 2px offset on the focused
// segment, which rises above its neighbours. It is never disabled: in a preview it still works.
//
// kind is "choice" here. Ticket 26 adds the toggle kind ("Compare with": buttons with aria-pressed, at most one
// pressed) to this same component, with this look.
import { useId, type ReactNode } from "react";
import { Check } from "lucide-react";
import { cx } from "../lib/cx";

export type Segment<T extends string> = { value: T; label: ReactNode };

export function SegmentedControl<T extends string>({
  legend,
  options,
  value,
  onChange,
  describedBy,
  kind = "choice",
}: {
  legend: ReactNode;
  options: Segment<T>[];
  value: T;
  onChange: (value: T) => void;
  // Captions under the control that say more about the choice, such as that a preview does not save it.
  describedBy?: string;
  kind?: "choice";
}) {
  const name = useId();
  return (
    <fieldset aria-describedby={describedBy} data-segmented={kind} className="min-w-0">
      <legend className="text-small text-ink-muted">{legend}</legend>
      <div className="mt-2 flex flex-col @md/page:inline-flex @md/page:flex-row">
        {options.map((option, index) => {
          const selected = option.value === value;
          const first = index === 0;
          const last = index === options.length - 1;
          return (
            <label
              key={option.value}
              data-segment={option.value}
              data-selected={selected || undefined}
              className={cx(
                "relative flex min-h-11 cursor-pointer items-center gap-2 border border-line-strong px-4 py-1 text-small text-ink",
                "@md/page:min-h-8",
                // The segments touch: each after the first drops the border it would share with its neighbour.
                !first && "border-t-0 @md/page:border-t @md/page:border-l-0",
                first && "rounded-t-lg @md/page:rounded-l-pill @md/page:rounded-tr-none",
                last && "rounded-b-lg @md/page:rounded-r-pill @md/page:rounded-bl-none",
                selected ? "z-1 bg-tint shadow-[inset_0_0_0_2px_var(--color-primary)]" : "bg-surface hover:bg-tint-hover",
                "has-[input:focus-visible]:z-2 has-[input:focus-visible]:outline-2 has-[input:focus-visible]:outline-offset-2",
                "has-[input:focus-visible]:outline-focus has-[input:focus-visible]:outline-solid",
              )}
            >
              <input
                type="radio"
                name={name}
                value={option.value}
                checked={selected}
                onChange={() => onChange(option.value)}
                className="peer sr-only"
              />
              {/* Both states hold the icon's 16 px, so selecting moves nothing. */}
              <span aria-hidden="true" className="flex size-4 shrink-0 items-center justify-center">
                {selected && <Check className="size-4 text-primary" />}
              </span>
              <span className="min-w-0">{option.label}</span>
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}
