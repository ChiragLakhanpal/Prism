// Collapsed section (DESIGN.md section 5; the 27 brief, section 4.4, built first by ticket 31 and shared with ticket
// 27's section 2): a package workspace section that is optional, so it starts closed with a summary that says what
// is inside. A Card with the label eyebrow, the numbered h2 (its number hidden from screen readers), the summary of
// one or two sentences, and a flush ghost "Show the ..." button with aria-expanded and aria-controls. From a 768 px
// page area the button sits at the right of the header, its middle level with the h2's; below it, under the
// summary, its chevron on the summary's text edge. States: collapsed, open, loading (two static bars for the
// summary, the button working), error (an alert replaces the summary and the button is hidden, unless you had
// opened the section, when it stays so you can close it again) and no content (the summary only, no button).
// Opening and closing are instant and keep focus on the button; the chevron swaps and never rotates. A link to the
// section's id lands below the sticky header.
import { useId, type ReactNode, type Ref } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import { Button } from "./Button";
import { Skeleton } from "./Skeleton";

export type CollapsedState = "ready" | "loading" | "error" | "empty";

export function CollapsedSection({
  id,
  eyebrow,
  number,
  heading,
  summary,
  state = "ready",
  open,
  onToggle,
  showLabel,
  hideLabel,
  error,
  headingRef,
  children,
  busy = false,
  sectionKey,
  live,
}: {
  id?: string;
  eyebrow: ReactNode;
  number: ReactNode;
  heading: ReactNode;
  summary: ReactNode;
  state?: CollapsedState;
  open: boolean;
  onToggle: () => void;
  showLabel: ReactNode;
  hideLabel: ReactNode;
  // The alert, its "Try again" and its code line, in place of the summary when the summary could not load.
  error?: ReactNode;
  headingRef?: Ref<HTMLHeadingElement>;
  children?: ReactNode;
  busy?: boolean;
  // The section's key, as data-section, for tests and the design gallery.
  sectionKey?: string;
  // A polite live region inside the section and outside its body, present before any text changes, so it speaks
  // whether the section is open or not (ticket 27's section 2).
  live?: ReactNode;
}) {
  const headingId = useId();
  const bodyId = useId();
  const button = state !== "empty" && (state !== "error" || open) && (
    <Button
      variant="ghost"
      icon={open ? ChevronUp : ChevronDown}
      flush
      aria-expanded={open}
      aria-controls={bodyId}
      onClick={onToggle}
      // The 44 px button and the 30 px heading share a middle line, not a top edge (the 31 design review, F8).
      className="shrink-0 @md/page:-mt-2"
      data-section-toggle
    >
      {open ? hideLabel : showLabel}
    </Button>
  );
  return (
    <section
      id={id}
      aria-labelledby={headingId}
      aria-busy={busy || undefined}
      data-collapsed-section={open ? "open" : state === "ready" ? "collapsed" : state}
      data-section={sectionKey}
      className="scroll-mt-24 rounded-md border border-line bg-surface p-4 @md/page:p-6"
    >
      <div className="flex flex-col gap-2 @md/page:flex-row @md/page:items-start @md/page:justify-between @md/page:gap-6">
        <div className="min-w-0 flex-1">
          <p className="text-label text-ink-muted uppercase">{eyebrow}</p>
          <h2 ref={headingRef} id={headingId} tabIndex={-1} className="mt-2 text-h2 text-ink-heading focus:outline-none">
            <span aria-hidden="true">{number} </span>
            {heading}
          </h2>
          <div className="mt-2 max-w-[65ch] text-body text-ink" data-section-summary>
            {state === "loading" ? (
              <div aria-hidden="true" className="flex flex-col gap-2 py-1">
                <Skeleton className="h-4 w-[90%]" />
                <Skeleton className="h-4 w-[45%]" />
              </div>
            ) : state === "error" ? (
              error
            ) : (
              summary
            )}
          </div>
        </div>
        {button && <div className="@md/page:mt-6">{button}</div>}
      </div>
      <div id={bodyId} hidden={!open} data-section-body>
        {open && children}
      </div>
      {live}
    </section>
  );
}
