// The evidence drawer opened from a row of section 1's "Advertised again" block (ticket 28; the 28 brief, section
// 8), inside brief 14's frame (EvidenceDrawer.tsx): under the heading, the row's line as the claim, captioned "From
// this page" and ending with its marker's number as a static pill; and, for a row with two or more records (an
// activity advertised again has two notices), one tab per record, "Sources for this sentence", in marker order.
// The record itself is brief 14's record view, with the field that supports the claim highlighted.
import { useRef, type KeyboardEvent } from "react";
import { copy } from "../copy";
import { cx } from "../lib/cx";
import { useMarkerNumber } from "../lib/markers";
import type { RebidCase } from "../lib/rebidding";
import { WORD_JOINER } from "./CitationMarker";
import { SourceNumber } from "./EvidenceCard";
import { caseLine, recordTab } from "./RebiddingBlock";

const words = copy.rebid;

// number: the marker's number, for the design gallery; the page reads it from the page's numbers.
export function CaseClaim({ row, id, through, number }: { row: RebidCase; id: string; through: string | null; number?: number }) {
  const held = useMarkerNumber(id);
  const n = number ?? held;
  const lang = row.quote && row.quote.lang !== "en" ? row.quote.lang : undefined;
  return (
    <div data-claim data-rebid-claim={row.step_reference}>
      <p className="text-caption text-ink-muted">{words.fromPage}</p>
      <p className="mt-1 border-l-2 border-line-strong pl-3 text-small text-ink" lang={lang}>
        {caseLine(row, through)}
        {n !== null && (
          <>
            {WORD_JOINER}
            <span className="ml-1 inline-flex align-[1px]">
              <SourceNumber n={n} />
            </span>
          </>
        )}
      </p>
    </div>
  );
}

// Left and Right move between the tabs, Home and End jump to the ends, and selection follows focus.
export function CaseSwitcher({ row, current, panelId, onChoose }: { row: RebidCase; current: string; panelId: string; onChoose: (id: string) => void }) {
  const refs = useRef<(HTMLButtonElement | null)[]>([]);
  const ids = row.evidence.map((item) => item.evidence_id);
  const index = ids.indexOf(current);
  const onKeyDown = (event: KeyboardEvent<HTMLButtonElement>) => {
    const moves: Record<string, number> = { ArrowRight: index + 1, ArrowLeft: index - 1, Home: 0, End: ids.length - 1 };
    if (!(event.key in moves)) return;
    event.preventDefault();
    const next = (moves[event.key] + ids.length) % ids.length;
    refs.current[next]?.focus();
    onChoose(ids[next]);
  };
  return (
    <div role="tablist" aria-label={words.switcher} className="flex flex-wrap gap-2" data-rebid-switcher>
      {row.evidence.map((item, at) => {
        const selected = item.evidence_id === current;
        return (
          <button
            key={item.evidence_id}
            ref={(element) => {
              refs.current[at] = element;
            }}
            type="button"
            role="tab"
            id={`${panelId}-tab-${at}`}
            aria-selected={selected}
            aria-controls={panelId}
            tabIndex={selected ? 0 : -1}
            onClick={() => onChoose(item.evidence_id)}
            onKeyDown={onKeyDown}
            className={cx(
              "inline-flex min-h-8 items-center rounded-pill border border-line-strong px-3 py-1 text-left text-small text-ink transition-paint duration-150",
              selected ? "bg-tint shadow-[inset_0_0_0_1px_var(--color-primary)]" : "bg-surface hover:bg-tint-hover",
            )}
          >
            {recordTab(item)}
          </button>
        );
      })}
    </div>
  );
}
