// The evidence card (DESIGN.md section 5; the 14 brief, section 4.4): what a citation marker's hover
// or keyboard focus shows. The stratum eyebrow and the marker's number, the source as its title, two or
// three whole sentences around the match with the matching words highlighted, and the source line. It
// holds no links or buttons, so a keyboard never has to enter it; a click on the marker opens the
// whole paragraph in the evidence drawer.
import { copy } from "../copy";
import type { EvidenceEvent } from "../lib/answer";
import { excerpt, highlightsFor, passageFields, placeOf, recordKind, recordReference, recordSource } from "../lib/sources";
import { highlighted } from "./Document";
import { Fill } from "./Fill";
import { Num } from "./Num";
import { DocumentSource, Source } from "./Source";

// A static pill with the marker's number, as the card and the drawer's claim block show it.
export function SourceNumber({ n }: { n: number }) {
  return (
    <span
      aria-hidden="true"
      className="inline-flex h-5 min-w-5 shrink-0 items-center justify-center rounded-pill border border-primary bg-surface px-1 text-label font-bold text-primary tabular-nums"
    >
      {n}
    </span>
  );
}

// A record's reference moves to the next line whole when it fits there, and breaks after its hyphens
// only when it does not (DESIGN.md section 5, Page header; PageHeader.tsx's WithIds).
export function sourceTitle(evidence: EvidenceEvent) {
  if (evidence.kind === "record") {
    const reference = <span className="inline-block max-w-full wrap-anywhere font-mono">{recordReference(evidence)}</span>;
    return <Fill template={copy.evidence.recordTitle} slots={{ kind: recordKind(evidence), reference }} />;
  }
  const fields = passageFields(evidence);
  const place = placeOf(fields);
  return place.kind === "paragraph" ? (
    <Fill template={copy.evidence.title} slots={{ project: fields.project, para: place.text }} />
  ) : (
    <Fill template={copy.evidence.titleSection} slots={{ project: fields.project, section: place.text }} />
  );
}

// A record's source line, the same in the evidence card and the drawer (the 14 brief, section 5.11):
// "Source: Procurement Plan, Northern Water Works Development Agency, P156634, version of October 9,
// 2026, page 3."
export function RecordSourceLine({ evidence, className }: { evidence: EvidenceEvent; className?: string }) {
  const source = recordSource(evidence);
  const words = copy.evidence;
  const date = source.date ? <Num date={source.date} /> : null;
  const pid = <span className="font-mono">{source.pcode}</span>;
  return (
    <Source className={className}>
      {source.agency && source.page && date ? (
        <Fill template={words.recordSource} slots={{ doc: source.docType, agency: source.agency, pid, date, page: String(source.page) }} />
      ) : (
        <Fill template={words.recordSourceShort} slots={{ doc: source.docType, pid, date: date ?? recordReference(evidence) }} />
      )}
    </Source>
  );
}

export function eyebrow(evidence: EvidenceEvent): string {
  const stratum = evidence.kind === "record" ? "What" : (evidence.stratum ?? "Why");
  return copy.evidence.eyebrow[stratum];
}

export function EvidenceCard({ evidence, n, sentence, visited = false }: { evidence: EvidenceEvent; n: number; sentence: number | null; visited?: boolean }) {
  const fields = evidence.kind === "passage" ? passageFields(evidence) : null;
  const shown = fields ? excerpt(fields.text, highlightsFor(evidence, sentence)[0] ?? null) : null;
  return (
    <div data-evidence-card className="flex flex-col p-1">
      <div className="flex items-start justify-between gap-3">
        <p className="text-label text-ink-muted uppercase">{eyebrow(evidence)}</p>
        <SourceNumber n={n} />
      </div>
      <p className="mt-1 text-title text-ink-heading">{sourceTitle(evidence)}</p>
      {fields && shown && (
        <>
          <p lang={fields.lang ?? undefined} className="mt-2 text-small text-ink">
            {copy.evidence.quoteOpen}
            {highlighted(shown.text, shown.range ? [shown.range] : [])}
            {copy.evidence.quoteClose}
          </p>
          <DocumentSource
            className="mt-2"
            docType={fields.docType}
            pcode={fields.pcode}
            date={fields.date}
            place={placeOf(fields)}
            page={fields.page ?? 0}
          />
        </>
      )}
      {!fields && <RecordSourceLine className="mt-2" evidence={evidence} />}
      {visited && <p className="mt-1 text-caption text-ink-muted">{copy.evidence.visited}</p>}
    </div>
  );
}
