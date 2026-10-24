// Sources list (DESIGN.md section 5; the 35 brief, section 4.5): the distinct sources a draft cites, numbered
// as its markers are, under an h2 the draft bar's "You opened" link moves focus to. Each item has its
// citation marker, its source line, the notes that cite it, and whether you opened it. The words and the
// marker's visited look carry that state together. The caption gives the server's counts: how many you
// opened, and how many citations become footnotes in the Word file.
import { copy } from "../copy";
import type { EvidenceEvent } from "../lib/answer";
import type { DraftSource } from "../lib/drafts";
import { evidenceHref, openEvidence } from "../lib/evidence";
import { formatNumber } from "../lib/format";
import { DRAWER_ID, markerSource } from "./AnswerPanel";
import { CitationMarker } from "./CitationMarker";
import { EvidenceCard, RecordSourceLine, sourceTitle } from "./EvidenceCard";
import { Fill, Joined } from "./Fill";
import type { OpenSource } from "./DraftNotes";

const whole = (value: number) => formatNumber(value, { compact: false });

export const SOURCES_ID = "sources";

export function SourcesList({
  sources,
  evidence,
  opened,
  openedCount,
  total,
  citations,
  open,
}: {
  sources: DraftSource[];
  evidence: Record<string, EvidenceEvent>;
  // The sources opened since the draft was saved, with this page's own opens added.
  opened: ReadonlySet<string>;
  openedCount: number;
  // How many distinct sources the draft cites, as the server counted them.
  total: number;
  citations: number;
  open: OpenSource;
}) {
  const words = copy.draft.sources;
  return (
    <section aria-labelledby={SOURCES_ID} data-sources>
      <h2 id={SOURCES_ID} tabIndex={-1} className="text-title text-ink-heading focus:outline-none">
        {words.title}
      </h2>
      <p className="mt-2 max-w-[72ch] text-caption text-ink-muted" data-sources-caption data-numbers>
        {words.caption(whole(openedCount), whole(total), citations, whole(citations))}
      </p>
      <ol aria-labelledby={SOURCES_ID} className="mt-4 flex flex-col gap-4">
        {sources.map((source) => {
          const id = source.evidence_id;
          const seen = opened.has(id);
          const refs = source.cited_in.map((ref) => (
            <span key={ref} className="inline-block max-w-full wrap-anywhere font-mono">
              {ref}
            </span>
          ));
          return (
            <li key={id} data-source-item={id} className="grid grid-cols-[auto_minmax(0,1fr)] gap-3">
              <span className="pt-0.5">
                <CitationMarker
                  n={source.number}
                  evidenceId={id}
                  source={markerSource(evidence[id], id)}
                  href={evidenceHref(id)}
                  drawerId={DRAWER_ID}
                  active={open.id === id && open.sentence === null}
                  opened={seen}
                  preview={evidence[id] ? <EvidenceCard evidence={evidence[id]} n={source.number} sentence={null} visited={seen} /> : undefined}
                  onOpen={(marker) => openEvidence(id, { serial: null, sentence: null, marker, runId: null })}
                />
              </span>
              <div className="min-w-0">
                {/* The record's title, as the drawer heads it, so each source says which record it is. */}
                {evidence[id] && (
                  <p className="text-small font-semibold text-ink-heading" data-source-title>
                    {sourceTitle(evidence[id])}
                  </p>
                )}
                {evidence[id] && <RecordSourceLine evidence={evidence[id]} />}
                <p className="mt-1 text-caption text-ink-muted">
                  <Fill template={words.citedIn(source.cited_in.length)} slots={{ refs: <Joined items={refs} /> }} />
                </p>
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
