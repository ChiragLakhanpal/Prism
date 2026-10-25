// The Sources list of suggested PPSD rows (ticket 36; the 36 brief, section 5.5): one item per footnote, numbered as
// its marker is. Each item's first line is the footnote's text as the Word file gets it ("In Word: ..."), built once
// on the server, so the page and the Word file cannot differ; then where it is cited, and each source the marker
// carries with whether you opened it. The heading is the one the bar's "You opened" link moves focus to, and the
// caption gives the server's counts.
import { copy } from "../copy";
import type { Draft } from "../lib/drafts";
import { evidenceHref, openEvidence } from "../lib/evidence";
import { formatNumber } from "../lib/format";
import { DRAWER_ID } from "./AnswerPanel";
import { CitationMarker } from "./CitationMarker";
import type { OpenSource } from "./DraftNotes";
import { Fill } from "./Fill";
import { footnoteSources } from "./PpsdRows";
import { SOURCES_ID } from "./SourcesList";

const whole = (value: number) => formatNumber(value, { compact: false });

export function PpsdSources({ draft, opened, openedCount, open }: {
  draft: Draft;
  opened: ReadonlySet<string>;
  openedCount: number;
  open: OpenSource;
}) {
  const ppsd = draft.ppsd!;
  const footnotes = draft.footnotes ?? [];
  const rows = new Map(ppsd.rows.map((row) => [row.row_key, row]));
  const headers = new Map(ppsd.forms[ppsd.form].columns.map((column) => [column.key, column.header]));
  const words = copy.draft.sources;
  return (
    <section aria-labelledby={SOURCES_ID} data-sources data-footnotes>
      <h2 id={SOURCES_ID} tabIndex={-1} className="text-title text-ink-heading focus:outline-none">
        {words.title}
      </h2>
      <p className="mt-2 max-w-[72ch] text-caption text-ink-muted" data-sources-caption data-numbers>
        {words.caption(whole(openedCount), whole(draft.opened.of), draft.citations, whole(draft.citations))}
      </p>
      <ol aria-labelledby={SOURCES_ID} className="mt-4 flex flex-col gap-4">
        {footnotes.map((footnote) => {
          const row = rows.get(footnote.row_key)!;
          const first = footnote.evidence_ids[0];
          const seen = footnote.evidence_ids.every((id) => opened.has(id));
          return (
            <li key={footnote.number} data-footnote={footnote.number} className="grid grid-cols-[auto_minmax(0,1fr)] gap-3">
              <span className="pt-0.5">
                <CitationMarker
                  n={footnote.number}
                  evidenceId={first}
                  source={footnoteSources(footnote, row)}
                  href={evidenceHref(first)}
                  drawerId={DRAWER_ID}
                  active={open.id === first && open.sentence === null}
                  opened={seen}
                  onOpen={(marker) => openEvidence(first, { serial: null, sentence: null, marker, runId: null })}
                />
              </span>
              <div className="min-w-0">
                <p className="text-small text-ink" data-in-word>
                  <Fill template={copy.ppsd.inWord} slots={{ text: footnote.text }} />
                </p>
                <p className="mt-1 text-caption text-ink-muted">{copy.ppsd.citedIn(headers.get(footnote.cell) ?? footnote.cell, row.risk_label)}</p>
                <p data-opened={seen} className={seen ? "text-caption text-ink-muted" : "text-caption text-ink"}>
                  {seen ? words.opened : words.notOpened}
                </p>
              </div>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
