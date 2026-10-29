// Collapsed section (DESIGN.md section 5; the 27 brief, section 4.4, built first by ticket 31 and shared with ticket
// 27's section 2): a package workspace section that is optional, so it starts closed with a summary that says what
// is inside. Since ticket 95 it is the closed form of a Task zone (TaskZone.tsx), and its look is the zone's: a row on
// the page grey while it is closed, a white panel once it is open, its number in the zone's number column (hidden from
// screen readers), and its tag, such as "PPSD section 6", under its name, since the Show or Hide button holds the header's
// right; since ticket 101 the package sections have no eyebrows. Its behavior stays as ticket 31 set it: a flush ghost "Show the ..." button with aria-expanded and
// aria-controls, after the summary in the DOM, at the header's right from 768 px and under the summary below it.
// States: collapsed, open, loading (static bars for the summary, the button working), error (an alert replaces the
// summary and the button is hidden, unless you had opened the section, when it stays so you can close it again) and
// no content (the summary only, no button). Opening and closing are instant and keep focus on the button; the chevron
// swaps and never rotates. A link to the section's id lands below the sticky header.
import type { ReactNode, Ref } from "react";
import { TaskZone } from "./TaskZone";

export type CollapsedState = "ready" | "loading" | "error" | "empty";

export function CollapsedSection({
  id,
  tag,
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
  foot,
  loading,
}: {
  id?: string;
  tag?: ReactNode;
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
  // The Foot strip that ends the opened zone's evidence: its note, coverage line and source line (ticket 101).
  foot?: ReactNode;
  // What holds the summary's place while it loads, in place of the zone's two skeleton bars (ticket 59).
  loading?: ReactNode;
}) {
  return (
    <TaskZone
      id={id}
      number={number}
      name={heading}
      tag={tag}
      summary={summary}
      state={state}
      error={error}
      toggle={{ open, onToggle, show: showLabel, hide: hideLabel }}
      headingRef={headingRef}
      busy={busy}
      sectionKey={sectionKey}
      live={live}
      foot={foot}
      loading={loading}
      marks={{ "data-collapsed-section": open ? "open" : state === "ready" ? "collapsed" : state }}
      className="scroll-mt-24"
    >
      {children}
    </TaskZone>
  );
}
