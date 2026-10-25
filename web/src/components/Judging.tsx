// The judging page's parts (DESIGN.md section 5; the 32 brief, sections 2.7 and 3.2):
//
// - ProgressMeter: an 8 px pill track in surface-2 with a primary fill, always beside the sentence that states its
//   ratio, and aria-hidden, since the sentence carries the value. No meter without its ratio.
// - PassageMap: a disclosure, a ghost button with aria-expanded, then a nav "Passages for this query" holding an ol
//   of 32 px chip links, 8 px apart. Not graded: the Gap style's dashed border; graded: a solid border, surface-2 and
//   a check; current: tint with an inset 1 px primary shadow. A chip never shows which grade you gave.
// - GradeBar: the Draft bar's frame for judging. From a page area of 1024 px it sticks to the bottom of the window,
//   on surface with a 1 px line on top, held to the column: the label and its note on the left, three equal-width
//   secondary toggle buttons with key hints on the right. Below 1024 px it sits under the passage, its buttons
//   stacked full width. The page's bottom scroll padding follows its height while it sticks (DESIGN.md section 10).
import { useId, useLayoutEffect, useRef, type ReactNode } from "react";
import { Check, ChevronDown } from "lucide-react";
import { copy } from "../copy";
import { cx } from "../lib/cx";
import { GRADES, type Grade } from "../lib/retrieval";
import { Button } from "./Button";
import { fillText } from "./LessonParts";
import { ToggleButton } from "./ToggleButton";

const words = copy.judging;

export function ProgressMeter({ part, whole, children }: { part: number; whole: number; children: ReactNode }) {
  const share = whole > 0 ? Math.min(part / whole, 1) : 0;
  return (
    <div className="flex flex-col gap-2 @md/page:flex-row @md/page:items-center @md/page:gap-3" data-progress>
      <span aria-hidden="true" className="block h-2 w-full overflow-hidden rounded-pill bg-surface-2 @md/page:w-60">
        <span
          className="block h-full rounded-pill bg-primary transition-[width] duration-120 motion-reduce:transition-none"
          style={{ width: `${share * 100}%` }}
        />
      </span>
      <span className="text-small text-ink tabular-nums">{children}</span>
    </div>
  );
}

export function PassageMap({ open, onToggle, count, current, graded, href, onChoose }: {
  open: boolean;
  onToggle: () => void;
  count: number;
  // The passage on screen, from 1.
  current: number;
  graded: boolean[];
  href: (n: number) => string;
  onChoose: (n: number) => void;
}) {
  return (
    <div className="flex flex-col gap-2" data-passage-map={open ? "open" : "closed"}>
      <div>
        <Button variant="ghost" flush onPage icon={ChevronDown} aria-expanded={open} onClick={onToggle}>
          {open ? words.mapHide : fillText(words.mapShow, { pool: count })}
        </Button>
      </div>
      {open && (
        <nav aria-label={words.mapLabel}>
          <ol className="flex flex-wrap gap-2">
            {Array.from({ length: count }, (_, index) => {
              const n = index + 1;
              const done = graded[index];
              const here = n === current;
              return (
                <li key={n}>
                  <a
                    href={href(n)}
                    aria-current={here ? "step" : undefined}
                    aria-label={fillText(done ? words.chipGraded : words.chipNotGraded, { i: n })}
                    onClick={(event) => {
                      event.preventDefault();
                      onChoose(n);
                    }}
                    data-chip={done ? "graded" : "not-graded"}
                    className={cx(
                      "inline-flex h-8 min-w-8 items-center justify-center gap-1 rounded-pill border px-2 text-small text-ink tabular-nums",
                      "transition-paint duration-120 motion-reduce:transition-none",
                      done ? "border-solid border-line-strong bg-surface-2" : "border-dashed border-line-strong bg-surface",
                      here ? "bg-tint shadow-[inset_0_0_0_1px_var(--color-primary)]" : "hover:bg-tint-hover",
                    )}
                  >
                    {n}
                    {done && <Check aria-hidden="true" className="size-3" />}
                  </a>
                </li>
              );
            })}
          </ol>
        </nav>
      )}
    </div>
  );
}

export function GradeBar({ n, chosen, locked, onGrade, disabled = false, mine, theirs, sample = false }: {
  n: number;
  chosen: Grade | null;
  // Both judges finished: the buttons give way to the two grades.
  locked: boolean;
  onGrade: (grade: Grade) => void;
  disabled?: boolean;
  mine?: Grade | null;
  theirs?: Grade | null;
  // A design gallery sample: it never sticks, so several can sit on one page.
  sample?: boolean;
}) {
  const bar = useRef<HTMLDivElement>(null);
  const id = useId();
  const labelId = `${id}-label`;
  const noteId = `${id}-note`;
  // While the bar sticks, the page's bottom scroll padding is its height, so a focused control is never under it.
  useLayoutEffect(() => {
    const element = bar.current;
    if (!element || sample) return;
    const root = document.documentElement;
    const pad = () => {
      const sticks = getComputedStyle(element).position === "sticky";
      root.style.setProperty("--sticky-bottom", sticks ? `${element.offsetHeight + 8}px` : "0px");
      root.style.scrollPaddingBottom = sticks ? `${element.offsetHeight + 8}px` : "";
    };
    pad();
    const watch = new ResizeObserver(pad);
    watch.observe(element);
    return () => {
      watch.disconnect();
      root.style.removeProperty("--sticky-bottom");
      root.style.scrollPaddingBottom = "";
    };
  }, []);
  return (
    <div
      ref={bar}
      data-grade-bar={locked ? "locked" : "ready"}
      className={cx("border-t border-line bg-surface py-4", !sample && "@lg/page:sticky @lg/page:bottom-0 @lg/page:z-10")}
    >
      <div role="group" aria-labelledby={labelId} aria-describedby={locked ? undefined : noteId} className="flex flex-col gap-3 @lg/page:flex-row @lg/page:items-center @lg/page:justify-between">
        <div className="min-w-0">
          <p id={labelId} className="text-small font-bold text-ink-heading">
            {fillText(words.barLabel, { i: n })}
          </p>
          {!locked && (
            <p id={noteId} className="text-caption text-ink-muted">
              <span className="hidden @lg/page:inline">{words.barNote}</span>
              <span className="@lg/page:hidden">{words.barNoteNarrow}</span>
            </p>
          )}
        </div>
        {locked ? (
          <div className="text-small text-ink" data-locked-grades>
            <p>{fillText(words.lockedYours, { grade: mine ? words.grades[mine] : "" })}</p>
            <p>{fillText(words.lockedTheirs, { grade: theirs ? words.grades[theirs] : "" })}</p>
          </div>
        ) : (
          <div className="grid shrink-0 grid-cols-1 gap-3 @lg/page:grid-cols-[repeat(3,10.5rem)]">
            {GRADES.map((grade) => (
              <ToggleButton
                key={grade}
                variant="secondary"
                pressed={chosen === grade}
                disabled={disabled}
                hint={words.keys[grade]}
                aria-keyshortcuts={words.keys[grade]}
                onClick={() => onGrade(grade)}
                data-grade={grade}
                className="w-full px-4 whitespace-nowrap"
              >
                {words.grades[grade]}
              </ToggleButton>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
