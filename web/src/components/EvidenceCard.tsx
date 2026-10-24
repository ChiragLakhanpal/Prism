// The evidence card (DESIGN.md section 5; the 14 brief, section 4.4): what a citation marker's hover
// or keyboard focus shows. The stratum eyebrow and the marker's number, the source as its title, two or
// three whole sentences around the match with the matching words highlighted, and the source line. It
// holds no links or buttons, so a keyboard never has to enter it; a click on the marker opens the
// whole paragraph in the evidence drawer.
import { copy } from "../copy";
import type { EvidenceEvent } from "../lib/answer";
import { excerpt, highlightsFor, passageFields, recordReference } from "../lib/sources";
import { highlighted } from "./Document";
import { Fill } from "./Fill";
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

export function sourceTitle(evidence: EvidenceEvent) {
  if (evidence.kind === "record") {
    return <Fill template={copy.evidence.recordTitle} slots={{ kind: copy.checkPlan.columns.activity, reference: <span className="font-mono">{recordReference(evidence)}</span> }} />;
  }
  const fields = passageFields(evidence);
  return fields.numbered ? (
    <Fill template={copy.evidence.title} slots={{ project: fields.project, para: fields.para }} />
  ) : (
    <Fill template={copy.evidence.titleSection} slots={{ project: fields.project, section: fields.section ?? fields.para }} />
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
            para={fields.para}
            page={fields.page ?? 0}
          />
        </>
      )}
      {!fields && <Source className="mt-2">{recordReference(evidence)}</Source>}
      {visited && <p className="mt-1 text-caption text-ink-muted">{copy.evidence.visited}</p>}
    </div>
  );
}
