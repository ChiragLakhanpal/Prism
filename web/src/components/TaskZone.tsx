// Task zone (DESIGN.md section 5, Task zone; ticket 95): one step of a page's work, a section named by its h2. A zone
// that holds open work (evidence, a table, a form) is a white panel; a zone that is closed, holds only a sentence or
// one action, or has nothing yet is a row on the page grey with a 1 px line under it (app.css, "Task zones"). Numbers
// mark zones only where the work is a sequence: a 24 px column in h2 size, 600, ink-muted and tabular, hidden from
// screen readers. A tag, such as "PPSD section 3", sits at the header's right, or under the name when the Show or
// Hide button or one action holds the header's right.
//
// Five states. Open: a panel. Closed: a row with its one-sentence summary and a flush ghost Show button with
// aria-expanded, after the summary in the DOM and at the header's right from a 768 px window; opening makes the row
// a panel in place, at once, with focus kept on the button. Loading: the real header over static bars sized to the
// summary they stand for. Error: the error alert and its "Try again" in place of the summary; the header stays, and the
// button too if you had opened the zone, so you can close it. No content: the first-person sentence and at most one
// link, as a row, with no button.
//
// A zone's blocks of evidence are ZoneBlocks, each ending in its Foot strip. A failed block's error alert takes that
// block's place, and the header and the zone's other blocks stay. Space falls only between blocks that show, so a
// hidden block leaves no gap.
import { useId, type ReactNode, type Ref } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import { Button } from "./Button";
import { SkeletonText } from "./Skeleton";

export type ZoneState = "ready" | "loading" | "error" | "empty";

// The Show or Hide control of a zone that starts closed.
export type ZoneToggle = { open: boolean; onToggle: () => void; show: ReactNode; hide: ReactNode };

export function TaskZone({
  id,
  number,
  name,
  tag,
  panel,
  summary,
  state = "ready",
  error,
  toggle,
  corner,
  headingRef,
  headingId: namedId,
  note,
  busy = false,
  sectionKey,
  live,
  marks,
  className,
  children,
}: {
  id?: string;
  // The zone's place in a sequence, such as 2, when the page's zones are one.
  number?: ReactNode;
  name: ReactNode;
  tag?: ReactNode;
  // The form: a panel around open work, or a row. A zone with a Show or Hide control is a panel while it is open.
  panel?: boolean;
  // The zone's one sentence: a closed zone's summary, or all a row holds.
  summary?: ReactNode;
  state?: ZoneState;
  // The alert, its "Try again" and its code line, in place of the summary when the summary could not load.
  error?: ReactNode;
  toggle?: ZoneToggle;
  // One action other than Show or Hide that holds the header's right, such as Start here's Remove. It comes after the
  // sentence in the DOM, and the tag moves under the name.
  corner?: ReactNode;
  headingRef?: Ref<HTMLHeadingElement>;
  // The h2's id when an address or another page names it, such as Start here's "start-here" (ticket 98).
  headingId?: string;
  // A short line right after the name, in caption ink-muted, which the zone's name includes, such as Start here's
  // "2 of 6 done" (ticket 114; ticket 98).
  note?: ReactNode;
  busy?: boolean;
  // The zone's key, as data-section, for tests and the design gallery.
  sectionKey?: string;
  // A polite live region inside the zone and outside its body, present before any text changes, so it speaks whether
  // the zone is open or not.
  live?: ReactNode;
  // Data attributes a caller marks the section with, such as the collapsed section's state.
  marks?: Record<`data-${string}`, string | undefined>;
  className?: string;
  // With a toggle, what the zone holds once opened. Without one, the zone's blocks: ZoneBlocks.
  children?: ReactNode;
}) {
  const ownId = useId();
  const headingId = namedId ?? ownId;
  const noteId = useId();
  const bodyId = useId();
  const open = toggle?.open ?? false;
  const form = (panel ?? open) ? "panel" : "row";
  const button = toggle && state !== "empty" && (state !== "error" || open) && (
    <Button
      variant="ghost"
      icon={open ? ChevronUp : ChevronDown}
      flush
      onPage={form === "row"}
      aria-expanded={open}
      aria-controls={bodyId}
      onClick={toggle.onToggle}
      data-section-toggle
    >
      {open ? toggle.hide : toggle.show}
    </Button>
  );
  const right = button || corner;
  const hasLead = summary != null || state !== "ready" || Boolean(toggle) || Boolean(corner);
  return (
    <section
      id={id}
      aria-labelledby={note != null ? `${headingId} ${noteId}` : headingId}
      aria-busy={busy || undefined}
      data-zone={form}
      data-zone-state={state === "ready" ? (toggle ? (open ? "open" : "closed") : "open") : state}
      data-numbered={number != null ? "" : undefined}
      data-corner={right ? "" : undefined}
      data-tag-under={right && tag != null ? "" : undefined}
      data-section={sectionKey}
      className={className}
      {...marks}
    >
      <div data-zone-head>
        <h2 ref={headingRef} id={headingId} tabIndex={-1} data-zone-name className="text-h2 text-ink-heading focus:outline-none">
          {number != null && (
            <span aria-hidden="true" data-zone-number className="text-ink-muted tabular-nums">
              {number}{" "}
            </span>
          )}
          {name}
        </h2>
        {note != null && (
          <span id={noteId} data-zone-note className="text-caption text-ink-muted">
            {note}
          </span>
        )}
        {tag != null && (
          <p data-zone-tag className="text-caption text-ink-muted">
            {tag}
          </p>
        )}
      </div>
      {hasLead && (
        <div data-zone-body data-zone-lead>
          {(summary != null || state !== "ready") && (
            <div data-section-summary className="max-w-prose text-body text-ink">
              {state === "loading" ? (
                <SkeletonText className="text-body" widths={["w-[90%]", "w-[45%]"]} />
              ) : state === "error" ? (
                error
              ) : (
                summary
              )}
            </div>
          )}
          {right && (
            <div data-zone-corner className="self-start">
              {right}
            </div>
          )}
          {/* Two actions never share the header's right: with the Show or Hide button there, the action follows the
              sentence in the flow, so "reveal" and "do" are told apart by place. */}
          {button && corner && <div className="self-start">{corner}</div>}
          {toggle && (
            <div id={bodyId} hidden={!open} data-section-body>
              {open && children}
            </div>
          )}
        </div>
      )}
      {!toggle && children}
      {live}
    </section>
  );
}

// One block of a zone's evidence, ending in its foot strip, which holds the block's note, coverage line and source.
export function ZoneBlock({ foot, children, ...marks }: { foot?: ReactNode; children: ReactNode } & Record<`data-${string}`, string | undefined>) {
  return (
    <>
      <div data-zone-body {...marks}>
        {children}
      </div>
      {foot}
    </>
  );
}
