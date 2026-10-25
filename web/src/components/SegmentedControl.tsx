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
// The toggle kind (ticket 26's "Compare with"; the 26 brief, section 4.2) has this look too: a group of buttons
// with aria-pressed, at most one pressed, and pressing the pressed one releases it. Each carries a 16 px plus, or the
// check while pressed, so the state is a shape as well as a fill. It is one tab stop too (roving tabindex, entering
// on the pressed segment or the first): Left and Right, or Up and Down, move focus with wrapping, Home and End go to
// the ends, and focus never presses, since a press redraws the chart and is announced; Space or Enter presses.
import { useId, useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import { Check, Plus } from "lucide-react";
import { cx } from "../lib/cx";

export type Segment<T extends string> = { value: T; label: ReactNode; description?: string };

type ChoiceProps<T extends string> = {
  legend: ReactNode;
  options: Segment<T>[];
  value: T;
  onChange: (value: T) => void;
  // Captions under the control that say more about the choice, such as that a preview does not save it.
  describedBy?: string;
  kind?: "choice";
};

type ToggleProps<T extends string> = {
  legend: ReactNode;
  options: Segment<T>[];
  // The pressed segment, or null when none is.
  pressed: T | null;
  onPress: (value: T | null) => void;
  // A sentence a screen reader hears with the group, such as how the toggles work.
  describedBy?: string;
  kind: "toggle";
};

// One segment's look, shared by both kinds: the touching borders, the outer corners, and the selected tint with its
// inset ring.
function segmentClass(selected: boolean, first: boolean, last: boolean) {
  return cx(
    "relative flex min-h-11 cursor-pointer items-center gap-2 border border-line-strong px-4 py-1 text-left text-small text-ink",
    "@md/page:min-h-8",
    !first && "border-t-0 @md/page:border-t @md/page:border-l-0",
    first && "rounded-t-lg @md/page:rounded-l-pill @md/page:rounded-tr-none",
    last && "rounded-b-lg @md/page:rounded-r-pill @md/page:rounded-bl-none",
    selected ? "z-1 bg-tint shadow-[inset_0_0_0_2px_var(--color-primary)]" : "bg-surface hover:bg-tint-hover",
  );
}

function ToggleGroup<T extends string>({ legend, options, pressed, onPress, describedBy }: ToggleProps<T>) {
  const legendId = useId();
  const buttons = useRef<(HTMLButtonElement | null)[]>([]);
  const [focused, setFocused] = useState<number | null>(null);
  const pressedIndex = options.findIndex((option) => option.value === pressed);
  const stop = focused ?? (pressedIndex >= 0 ? pressedIndex : 0);
  const move = (to: number) => {
    const next = (to + options.length) % options.length;
    setFocused(next);
    buttons.current[next]?.focus();
  };
  const onKeyDown = (event: KeyboardEvent<HTMLButtonElement>, index: number) => {
    if (event.key === "ArrowRight" || event.key === "ArrowDown") move(index + 1);
    else if (event.key === "ArrowLeft" || event.key === "ArrowUp") move(index - 1);
    else if (event.key === "Home") move(0);
    else if (event.key === "End") move(options.length - 1);
    else return;
    event.preventDefault();
  };
  return (
    <div data-segmented="toggle" className="min-w-0">
      <span id={legendId} className="text-small text-ink-muted">
        {legend}
      </span>
      <div
        role="group"
        aria-labelledby={legendId}
        aria-describedby={describedBy}
        className="mt-2 flex flex-col @md/page:inline-flex @md/page:flex-row"
        onBlur={(event) => {
          if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setFocused(null);
        }}
      >
        {options.map((option, index) => {
          const on = option.value === pressed;
          return (
            <button
              key={option.value}
              ref={(element) => {
                buttons.current[index] = element;
              }}
              type="button"
              aria-pressed={on}
              aria-description={option.description}
              tabIndex={index === stop ? 0 : -1}
              data-segment={option.value}
              data-selected={on || undefined}
              onFocus={() => setFocused(index)}
              onKeyDown={(event) => onKeyDown(event, index)}
              onClick={() => onPress(on ? null : option.value)}
              className={cx(
                segmentClass(on, index === 0, index === options.length - 1),
                "focus-visible:z-2 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus focus-visible:outline-solid",
              )}
            >
              {/* Both icons are 16 px, so pressing moves nothing. */}
              <span aria-hidden="true" className="flex size-4 shrink-0 items-center justify-center">
                {on ? <Check className="size-4 text-primary" /> : <Plus className="size-4 text-ink-muted" />}
              </span>
              <span className="min-w-0">{option.label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

export function SegmentedControl<T extends string>(props: ChoiceProps<T> | ToggleProps<T>) {
  return props.kind === "toggle" ? <ToggleGroup {...props} /> : <ChoiceGroup {...props} />;
}

function ChoiceGroup<T extends string>({ legend, options, value, onChange, describedBy, kind = "choice" }: ChoiceProps<T>) {
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
                // The segments touch: each after the first drops the border it would share with its neighbour.
                segmentClass(selected, first, last),
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
