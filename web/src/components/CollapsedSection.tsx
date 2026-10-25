// Collapsed section (DESIGN.md section 5; the 27 brief, section 4.4): a package workspace section that opens on
// demand, so the column reads as one sequence of siblings (progressive disclosure). A Card with section 1's
// eyebrow and numbered heading, a summary line, and a ghost "Show the ..." button with aria-expanded and
// aria-controls; the same card holds the open body, so opening never swaps it for another. Tickets 26 (section 4)
// and 31 (section 5) reuse it.
//
// From a 768 px page area the button sits at the right of the header block, top-aligned with the heading; below it
// the button sits under the summary, left-aligned. Opening and closing are instant and focus stays on the button.
// States: collapsed, open, loading (a summary skeleton; the button still works), error (an alert replaces the
// summary and the button is hidden) and no content (summary only, button hidden).
import { useId, type ReactNode, type Ref } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import { Button } from "./Button";
import { SkeletonText } from "./Skeleton";

export function CollapsedSection({
  id,
  eyebrow,
  number,
  heading,
  summary,
  open,
  onToggle,
  showLabel,
  hideLabel,
  loading = false,
  canOpen = true,
  busy = false,
  headingRef,
  children,
  stateKey,
  live,
}: {
  id: string;
  eyebrow: string;
  number: string;
  heading: string;
  // The summary line, or the error alert that takes its place.
  summary: ReactNode;
  open: boolean;
  onToggle: () => void;
  showLabel: string;
  hideLabel: string;
  // The summary is still loading: two static bars hold its place.
  loading?: boolean;
  // False when there is nothing to open (an error, no method family): the button is hidden.
  canOpen?: boolean;
  busy?: boolean;
  headingRef?: Ref<HTMLHeadingElement>;
  children?: ReactNode;
  // The value of data-state, by which tests and captures find the section's state.
  stateKey?: string;
  // The section's polite live region, present before any text changes, whether the section is open or not.
  live?: ReactNode;
}) {
  const headingId = useId();
  const bodyId = useId();
  const button = canOpen && (
    <Button
      variant="ghost"
      icon={open ? ChevronUp : ChevronDown}
      aria-expanded={open}
      aria-controls={bodyId}
      onClick={onToggle}
      data-disclosure
      className="self-start"
    >
      {open ? hideLabel : showLabel}
    </Button>
  );
  return (
    <section
      id={id}
      aria-labelledby={headingId}
      aria-busy={busy || undefined}
      data-collapsed-section={open ? "open" : "collapsed"}
      data-state={stateKey}
      className="scroll-mt-24 rounded-md border border-line bg-surface p-4 @md/page:p-6"
    >
      <div className="flex flex-col gap-2 @md/page:flex-row @md/page:items-start @md/page:justify-between @md/page:gap-6">
        <div className="min-w-0 flex-1">
          <p className="text-label text-ink-muted uppercase">{eyebrow}</p>
          <h2 ref={headingRef} id={headingId} tabIndex={-1} className="mt-2 text-h2 text-ink-heading focus:outline-none">
            <span aria-hidden="true">{number} </span>
            {heading}
          </h2>
          <div className="mt-2 max-w-prose text-body text-ink" data-section-summary>
            {loading ? <SkeletonText className="text-body" widths={["w-9/10", "w-9/20"]} /> : summary}
          </div>
        </div>
        {button && <div className="flex @md/page:pt-6">{button}</div>}
      </div>
      <div id={bodyId} hidden={!open} data-section-body>
        {open && <div className="mt-6">{children}</div>}
      </div>
      {live}
    </section>
  );
}
