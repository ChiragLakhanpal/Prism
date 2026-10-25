// Segmented control, choice kind (DESIGN.md section 5; briefs 26 and 27, built by ticket 32 for Judging's filter):
// a radiogroup with a visible label and one 32 px pill segment per choice, on one row from 768 px and stacked,
// 44 px each, below it. The selected segment takes the tint fill and an inset 2 px primary ring (brief 27's look,
// so no control but the page's primary button is solid navy). One tab stop: Left, Right, Up and Down move the
// selection, which follows focus and is applied 500 ms after the last move, so stepping through the choices
// does not reload the list each time; a click applies at once.
import { useEffect, useId, useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import { cx } from "../lib/cx";

export type Choice = { key: string; label: ReactNode };

const SETTLE_MS = 500;

export function SegmentedControl({ label, choices, value, onChange }: {
  label: ReactNode;
  choices: Choice[];
  value: string;
  onChange: (key: string) => void;
}) {
  const labelId = useId();
  const [shown, setShown] = useState(value);
  const refs = useRef<(HTMLButtonElement | null)[]>([]);
  const timer = useRef<number | null>(null);
  useEffect(() => setShown(value), [value]);
  useEffect(() => () => {
    if (timer.current !== null) window.clearTimeout(timer.current);
  }, []);

  const apply = (key: string, wait: boolean) => {
    setShown(key);
    if (timer.current !== null) window.clearTimeout(timer.current);
    if (!wait) {
      if (key !== value) onChange(key);
      return;
    }
    timer.current = window.setTimeout(() => key !== value && onChange(key), SETTLE_MS);
  };

  const onKeyDown = (event: KeyboardEvent<HTMLButtonElement>) => {
    const at = choices.findIndex((choice) => choice.key === shown);
    const step = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[event.key];
    if (step === undefined) return;
    event.preventDefault();
    const next = (at + step + choices.length) % choices.length;
    refs.current[next]?.focus();
    apply(choices[next].key, true);
  };

  return (
    <div className="flex flex-col gap-1 @md/page:flex-row @md/page:items-center @md/page:gap-3" data-segmented>
      <span id={labelId} className="text-small font-bold text-ink-heading">
        {label}
      </span>
      <div role="radiogroup" aria-labelledby={labelId} className="flex flex-col gap-2 @md/page:flex-row @md/page:flex-wrap">
        {choices.map((choice, index) => {
          const selected = choice.key === shown;
          return (
            <button
              key={choice.key}
              ref={(element) => {
                refs.current[index] = element;
              }}
              type="button"
              role="radio"
              aria-checked={selected}
              tabIndex={selected ? 0 : -1}
              onClick={() => apply(choice.key, false)}
              onKeyDown={onKeyDown}
              data-segment={choice.key}
              className={cx(
                "inline-flex min-h-11 items-center rounded-pill border border-line-strong px-3 text-left text-small text-ink @md/page:min-h-8",
                "transition-paint duration-150 motion-reduce:transition-none",
                selected ? "bg-tint shadow-[inset_0_0_0_2px_var(--color-primary)]" : "bg-surface hover:bg-tint-hover",
              )}
            >
              {choice.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
