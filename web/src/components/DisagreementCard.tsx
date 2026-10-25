// Disagreement card (DESIGN.md section 5), its read-only body: two sources that disagree, side by side
// in the order they were written, with equal weight (the same border, fill and type on both sides), the
// tag "Strata leans on this" on one, the evidence ladder's rule in one sentence and what you would
// treat as true if you kept the other. Warning state with "Two reports disagree" when keeping the other
// side would change the answer; otherwise the info state with "Sources differ". Never red.
//
// Ticket 24 builds it for an answer, where it sits directly under the sentence it concerns (the 24
// brief, section 4.4). The card is a size container: its sides sit side by side when the card itself
// is 560 px (35rem) wide or more, and stack, the earlier on top, below that, so it reads the same in
// the answer, in the drawer and on a project page. Ticket 23 adds the "Keep the other source" action.
import type { ReactNode } from "react";
import { cx } from "../lib/cx";
import { StatusBadge } from "./StatusBadge";
import { STATES } from "./state";

export type CardSide = {
  // "{source}, {date}. {written}." from the copy file.
  meta: string;
  // The side Strata leans on carries the tag.
  leaned: boolean;
  // What the source said: a rating or a quote, ending with its citation marker.
  said: ReactNode;
};

export function DisagreementCard({
  warning,
  name,
  leanTag,
  sides,
  rule,
  whatChanges,
}: {
  warning: boolean;
  // The group's accessible name: the badge's words and the two sources.
  name: string;
  leanTag: string;
  sides: [CardSide, CardSide];
  rule: string;
  whatChanges?: string;
}) {
  const look = STATES[warning ? "warning" : "info"];
  return (
    <div
      role="group"
      aria-label={name}
      data-disagreement={warning ? "warning" : "info"}
      className={cx("@container/disagreement rounded-md border p-3", look.box, look.border)}
    >
      <StatusBadge kind={warning ? "two-reports-disagree" : "sources-differ"} />
      <div data-disagreement-sides className="mt-3 grid grid-cols-1 gap-3 @min-[35rem]/disagreement:grid-cols-2">
        {sides.map((side, index) => (
          <div key={index} data-side={side.leaned ? "leaned" : "other"} className="rounded-md border border-line bg-surface p-3">
            <p className="text-caption text-ink-muted [overflow-wrap:anywhere]">{side.meta}</p>
            {side.leaned && <p className="text-caption font-semibold text-ink">{leanTag}</p>}
            <p className="mt-1 text-small text-ink">{side.said}</p>
          </div>
        ))}
      </div>
      <p className="mt-3 text-small text-ink">{rule}</p>
      {whatChanges && <p className="mt-3 text-small text-ink">{whatChanges}</p>}
    </div>
  );
}
