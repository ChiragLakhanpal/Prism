// Side panel (DESIGN.md section 5, Side panel; ticket 95): an object's facts or state beside its work, in columns 9 to
// 12 of a workspace page from a frame of 1200 px (Workspace.tsx places it, sticks it 24 px under the bar and hides it
// while the evidence drawer is open, since the drawer opens in its place). A panel with 24 px padding (16 below a 768 px
// page area), an h2 that names what it holds, a definition list (labels in label over values in small, 16 px apart;
// two columns once the panel's content is 18rem wide, long values across both), and its source line with a citation
// marker under a hairline where it has one. While its object loads, its labels stand over value bars and its source
// line keeps its space. A side panel that holds only a sentence, such as Waiting for you with no drafts, is a row in
// the side column, not a panel.
import { useId, type ReactNode } from "react";
import { cx } from "../lib/cx";
import { SkeletonLine, SkeletonText } from "./Skeleton";

export type SideFact = { label: ReactNode; value: ReactNode; wide?: boolean };

export function SidePanel({
  title,
  facts,
  source,
  sentence,
  loading = false,
  headingId: namedId,
  children,
}: {
  title: ReactNode;
  facts?: SideFact[];
  // The source line, with its citation marker where it has one.
  source?: ReactNode;
  // All the panel holds: it is then a row, not a panel.
  sentence?: ReactNode;
  loading?: boolean;
  // The h2's id when a part inside the panel is named by it too, such as a review page's history list (ticket 102).
  headingId?: string;
  // What the panel holds when it is not a list of facts, such as Waiting for you's drafts (ticket 98).
  children?: ReactNode;
}) {
  const ownId = useId();
  const headingId = namedId ?? ownId;
  if (sentence != null && !facts && children == null) {
    return (
      <section aria-labelledby={headingId} data-side-panel="row" className="border-y border-line py-4">
        <h2 id={headingId} className="text-h2 text-ink-heading">
          {title}
        </h2>
        <p className="mt-2 max-w-prose text-body text-ink">{sentence}</p>
      </section>
    );
  }
  return (
    <section
      aria-labelledby={headingId}
      aria-busy={loading || undefined}
      data-side-panel="panel"
      className="@container/side rounded-md border border-line bg-surface p-4 @md/page:p-6"
    >
      <h2 id={headingId} className="text-h2 text-ink-heading">
        {title}
      </h2>
      {facts && (
        <dl className="mt-4 grid grid-cols-1 gap-4 @facts/side:grid-cols-2">
          {facts.map((fact, index) => (
            // Each fact's value sits at its cell's foot, so a label that wraps keeps the row's values on one line, as a
            // table card's fields do (Table.tsx's CARD_FIELD; ticket 101's design review).
            <div key={index} data-side-fact className={cx("flex min-w-0 flex-col justify-end", fact.wide && "@facts/side:col-span-2")}>
              <dt className="text-label text-ink-muted">{fact.label}</dt>
              <dd className="mt-1 text-small wrap-break-word text-ink">{loading ? <SkeletonLine width="w-3/4" /> : fact.value}</dd>
            </div>
          ))}
        </dl>
      )}
      {children != null && (
        <div data-side-body className="mt-4">
          {children}
        </div>
      )}
      {source && (
        <div data-side-source className="mt-4 border-t border-line pt-4 text-caption text-ink-muted">
          {loading ? <SkeletonText widths={["w-full", "w-1/2"]} /> : source}
        </div>
      )}
    </section>
  );
}
