// The evidence drawer's views of the risks section (ticket 30; the 30 brief, section 6.7), inside brief 14's
// frame (EvidenceDrawer.tsx):
//
// - A source opened from a row: under the heading, the row's claim ("From this page", the risk, "What helped:"
//   and the lesson, its version and decision date), then the IEG line, which describes the lesson and so stays
//   put when you switch tabs, then the switcher over the row's sources. The IEG line is the info badge "IEG's
//   review restates this lesson" with IEG's own words under it, or one sentence that the lesson rests on the
//   completion report alone, because IEG's review is still to come or did not restate it. A lesson IEG wrote
//   itself says so in one sentence (ticket 58).
// - The completion reports behind a row's count, newest first, each a button that opens its paragraph with a
//   way back to the list; and every report counted, each a link to its document in the source view (ticket 21),
//   since ticket 23's document view in the drawer has not landed.
import { useEffect, useRef, type KeyboardEvent } from "react";
import { copy } from "../copy";
import type { EvidenceEvent } from "../lib/answer";
import { cx } from "../lib/cx";
import { formatCount, formatDate, formatNumber } from "../lib/format";
import { locatorText, type AllReportsRow, type ReportsRow, type RiskRow } from "../lib/risks";
import { Fill } from "./Fill";
import { Num } from "./Num";
import { StatusBadge } from "./StatusBadge";
import { TextLink } from "./TextLink";

const words = copy.packageRisks.drawer;

export function RowClaim({ row }: { row: RiskRow }) {
  const lesson = row.lesson;
  return (
    <div data-claim data-row-claim={row.risk_key} className="flex flex-col gap-3">
      <div>
        <p className="text-caption text-ink-muted">{words.fromPage}</p>
        <div className="mt-1 border-l-2 border-line-strong pl-3">
          <p className="text-small font-semibold text-ink-heading">{row.risk_label}</p>
          <p className="text-small text-ink">
            <Fill template={words.helped} slots={{ lesson: lesson.text }} />
          </p>
          <p className="text-caption text-ink-muted">
            <Fill template={words.version} slots={{ version: <Num value={lesson.version} options={{ compact: false }} />, date: <Num date={lesson.decided_on} /> }} />
          </p>
        </div>
      </div>
      <IegLine status={lesson.ieg_status} quote={lesson.ieg_quote} />
    </div>
  );
}

// A lesson's IEG line, from its ieg_status and IEG's restating words: here and in section 5's view F (ticket 31). In view
// F, which can stand alone as a full-screen sheet, IEG is spelled out (spelled; ticket 58).
export function IegLine({ status, quote, spelled = false }: { status: string; quote: RiskRow["lesson"]["ieg_quote"]; spelled?: boolean }) {
  if (status === "restated" && quote) {
    return (
      <div data-ieg-line="restated" className="flex flex-col items-start gap-1">
        <StatusBadge kind="ieg-restates" />
        <p className="text-caption text-ink-muted">
          <Fill template={spelled ? words.iegWroteSpelled : words.iegWrote} slots={{ doc: quote.doc_short, quote: <span lang={quote.lang ?? undefined}>{quote.text}</span> }} />
        </p>
      </div>
    );
  }
  // A lesson IEG wrote itself says so, rather than no line at all (ticket 58).
  if (status === "ieg_lesson") return <p data-ieg-line="ieg_lesson" className="text-caption text-ink-muted">{spelled ? words.iegLessonSpelled : words.iegLesson}</p>;
  if (status === "awaiting") return <p data-ieg-line="awaiting" className="text-caption text-ink-muted">{words.awaiting}</p>;
  if (status === "not_restated") return <p data-ieg-line="not_restated" className="text-caption text-ink-muted">{words.notRestated}</p>;
  return null;
}

// One pill-shaped tab per source of the row, "ICR ¶54" and "ICR Review 10.b", heard with "paragraph" spelled
// out. Left and Right move between them, Home and End jump to the ends, and selection follows focus.
// row: a risk's row, or any sources with the same tab words, such as a lesson IEG restated (ticket 60).
export function RowSwitcher({ row, current, panelId, onChoose }: {
  row: { sources: Pick<RiskRow["sources"][number], "evidence_id" | "doc_short" | "locator">[] };
  current: string;
  panelId: string;
  onChoose: (id: string) => void;
}) {
  const refs = useRef<(HTMLButtonElement | null)[]>([]);
  const ids = row.sources.map((source) => source.evidence_id);
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
    <div role="tablist" aria-label={words.switcher} className="flex flex-wrap gap-2" data-row-switcher>
      {row.sources.map((source, at) => {
        const selected = source.evidence_id === current;
        return (
          <button
            key={source.evidence_id}
            ref={(element) => {
              refs.current[at] = element;
            }}
            type="button"
            role="tab"
            id={`${panelId}-tab-${at}`}
            aria-selected={selected}
            aria-controls={panelId}
            tabIndex={selected ? 0 : -1}
            onClick={() => onChoose(source.evidence_id)}
            onKeyDown={onKeyDown}
            className={cx(
              "inline-flex min-h-8 items-center rounded-pill border border-line-strong px-3 py-1 text-left text-small text-ink transition-paint duration-150",
              selected ? "bg-tint shadow-[inset_0_0_0_1px_var(--color-primary)]" : "bg-surface hover:bg-tint-hover",
            )}
          >
            {/* One inline span, so the space after the short name stays inside the flex tab; "¶" is heard as
                "paragraph". */}
            <span>
              <Fill
                template={words.tab}
                slots={{
                  doc: source.doc_short,
                  locator:
                    source.locator.kind === "paragraph" ? (
                      <>
                        <span aria-hidden="true">{copy.evidence.paraMark}</span>
                        <span className="sr-only">{copy.evidence.paraSpoken}</span>
                        {source.locator.text}
                      </>
                    ) : (
                      locatorText(source.locator)
                    ),
                }}
              />
            </span>
          </button>
        );
      })}
    </div>
  );
}

// The completion reports that raised a row's risk, newest first. Each opens its paragraph, and the one you came
// back from takes focus.
export function RiskReportsView({ evidence, focusEntry = null, onOpen }: { evidence: EvidenceEvent; focusEntry?: string | null; onOpen?: (evidenceId: string) => void }) {
  const row = evidence.row as ReportsRow;
  const back = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    if (focusEntry) back.current?.focus();
  }, [focusEntry]);
  return (
    <div data-risk-reports={row.risk_key} className="flex flex-col gap-4">
      <div data-claim>
        <p className="text-caption text-ink-muted">{words.fromPage}</p>
        <p className="mt-1 border-l-2 border-line-strong pl-3 text-small font-semibold text-ink-heading">{row.risk_label}</p>
      </div>
      <p className="text-small text-ink">
        {row.m === 1 ? (
          // One report read: no "1 of 1 completion reports" (the 58 design review, follow-up 5).
          <Fill template={words.reportsFindingOne} slots={{ risk: row.risk_label }} />
        ) : (
          <Fill template={words.reportsFinding} slots={{ k: <Num value={row.k} options={{ compact: false }} />, m: <Num value={row.m} options={{ compact: false }} />, risk: row.risk_label }} />
        )}
      </p>
      <p className="text-caption text-ink-muted">{words.reportsNote}</p>
      <ul className="flex flex-col divide-y divide-line border-y border-line">
        {row.entries.map((entry) => (
          <li key={entry.evidence_id ?? entry.document_id}>
            <button
              ref={entry.evidence_id === focusEntry ? back : undefined}
              type="button"
              data-report-entry={entry.evidence_id}
              // The list lands on the report you came back from, marked with tint (ticket 105).
              data-landed={entry.evidence_id === focusEntry ? "" : undefined}
              onClick={() => entry.evidence_id && onOpen?.(entry.evidence_id)}
              className={cx(
                "flex min-h-11 w-full cursor-pointer flex-col items-start gap-1 px-2 py-2 text-left",
                entry.evidence_id === focusEntry ? "bg-tint" : "hover:bg-tint-hover",
              )}
            >
              <span className="text-small text-primary underline decoration-1 underline-offset-3">
                {entry.project_name ?? entry.project_id} (<span className="font-mono">{entry.project_id}</span>)
              </span>
              <span className="text-caption text-ink-muted">
                <Fill template={words.reportEntry} slots={{ doc: entry.doc_short, date: entry.date ? formatDate(entry.date, { style: "short" }) : "", para: entry.paragraph ?? "" }} />
              </span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

// Every completion report the section counted. Each links to its document's page under its project.
export function AllReportsView({ evidence }: { evidence: EvidenceEvent }) {
  const row = evidence.row as AllReportsRow;
  return (
    <div data-risk-reports-all className="flex flex-col gap-4">
      <p className="text-small text-ink">{row.m === 1 ? words.allSentenceOne : words.allSentence(formatNumber(row.m, { compact: false }))}</p>
      <ul className="flex flex-col divide-y divide-line border-y border-line">
        {row.entries.map((entry) => (
          <li key={entry.document_id} className="flex min-h-11 flex-col gap-1 px-2 py-2">
            <TextLink href={`/projects/${entry.project_id}/documents/${encodeURIComponent(entry.doc_key ?? entry.document_id)}`} className="text-small">
              {entry.project_name ?? entry.project_id} (<span className="font-mono">{entry.project_id}</span>)
            </TextLink>
            <span className="text-caption text-ink-muted">
              <Fill template={words.allEntry} slots={{ doc: entry.doc_short, date: entry.date ? formatDate(entry.date, { style: "short" }) : "" }} />
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

// The way back from a report's paragraph to the list it was opened from.
export function backToReports(count: number): string {
  return count === 1 ? words.backOne : words.back(formatCount(count));
}
