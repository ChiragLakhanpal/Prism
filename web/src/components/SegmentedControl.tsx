// Segmented control, choice kind (DESIGN.md section 5; briefs 26 and 27, built by ticket 32 for Judging's filter):
// a radiogroup with a visible label and two to four touching segments in one pill with a 1 px line-strong border and
// dividers, 32 px tall on one row from a 768 px page area, and stacked below it, 44 px each. Every segment is small
// text at 600 with a 16 px icon slot; the selected one takes the tint fill, an inset 2 px primary ring and a lucide
// check (brief 27's look, so no control but the page's primary button is solid navy), and nothing changes size. One
// tab stop: Left, Right, Up and Down move the selection, which follows focus and is applied 500 ms after the last
// move, so stepping through the choices does not reload the list each time; a click applies at once.
import { useEffect, useId, useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import { Check } from "lucide-react";
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
      <div
        role="radiogroup"
        aria-labelledby={labelId}
        className="flex flex-col rounded-lg border border-line-strong bg-surface @md/page:inline-flex @md/page:flex-row @md/page:self-start @md/page:rounded-pill"
      >
        {choices.map((choice, index) => {
          const selected = choice.key === shown;
          const first = index === 0;
          const last = index === choices.length - 1;
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
                "relative inline-flex min-h-11 items-center gap-2 px-3 text-left text-small font-semibold text-ink focus-visible:z-10 @md/page:min-h-8",
                "transition-paint duration-150 motion-reduce:transition-none",
                // The dividers: a line above each stacked segment but the first, and before each one on a row.
                !first && "border-t border-line-strong @md/page:border-t-0 @md/page:border-l",
                first && "rounded-t-lg @md/page:rounded-l-pill @md/page:rounded-tr-none",
                last && "rounded-b-lg @md/page:rounded-r-pill @md/page:rounded-bl-none",
                selected ? "bg-tint shadow-[inset_0_0_0_2px_var(--color-primary)]" : "bg-surface hover:bg-tint-hover",
              )}
            >
              <span aria-hidden="true" className="inline-flex size-4 shrink-0 items-center justify-center">
                {selected && <Check className="size-4 text-primary" />}
              </span>
              {choice.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
