// The evidence card (DESIGN.md section 5; the 14 brief, section 4.4): what a citation marker's hover
// or keyboard focus shows. The stratum eyebrow and the marker's number, the source as its title, the
// sentences the match is in, whole, with the neighbors that fit in 280 characters (lib/sources.ts,
// excerpt), with the matching words highlighted, and the source line. It
// holds no links or buttons, so a keyboard never has to enter it; a click on the marker opens the
// whole paragraph in the evidence drawer.
import type { ReactNode } from "react";
import { copy } from "../copy";
import type { EvidenceEvent } from "../lib/answer";
import { excerpt, highlightsFor, lessonOf, passageFields, placeOf, recordKind, recordReference, recordSource, summarySourceKey } from "../lib/sources";
import { dotTitle } from "./ComparableRecords";
import { highlighted, withoutMarkers } from "./Document";
import { Fill } from "./Fill";
import { fillText } from "./LessonParts";
import { Num } from "./Num";
import { ProjectId } from "./ProjectId";
import { Lang } from "./Lang";
import { DocumentSource, Source } from "./Source";
import { stepListTitle } from "./StepsDrawer";

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
// only when it does not (DESIGN.md section 5, Page header; PageHeader.tsx's WithIds). A lesson is titled by
// its statement, in the title font: its id is Strata's own and means nothing to a reader.
export function sourceTitle(evidence: EvidenceEvent) {
  // A comparable package opened from the range chart is headed by its STEP reference alone (ticket 15).
  if (evidence.kind === "package") {
    return <span className="inline-block max-w-full wrap-anywhere font-mono">{recordReference(evidence)}</span>;
  }
  // A quantile dot's packages are headed by how many there are (ticket 15).
  if (evidence.kind === "dot") return dotTitle(evidence);
  // The risks section's lists of completion reports (ticket 30).
  if (evidence.kind === "risk-reports") return copy.packageRisks.drawer.reportsTitle;
  if (evidence.kind === "risk-reports-all") return copy.packageRisks.drawer.allTitle;
  // Section 2's lists: one step's comparable packages, and the packages behind "ran longest" (ticket 27).
  if (evidence.kind === "steps" || evidence.kind === "steps-longest") return stepListTitle(evidence);
  // Two versions of a lesson (ticket 39), or a retired lesson.
  if (evidence.kind === "versions") {
    const view = evidence.row as { a: number; b: number; retired_as: string | null };
    return view.retired_as ? copy.versions.retiredTitle : fillText(copy.versions.title, { a: view.a, b: view.b });
  }
  const lesson = lessonOf(evidence);
  if (lesson) return <span data-lesson-title>{lesson.statement}</span>;
  // A passage a lesson rests on, as get_lessons returns it inside its row (ticket 36): "ICR P130164 paragraph 54,
  // page 23", as its marker names it.
  const cited = lessonPassage(evidence);
  if (cited) {
    return cited.section
      ? fillText(copy.ppsd.markerSection, { doc: cited.doc, section: cited.place })
      : fillText(copy.ppsd.markerParagraph, { doc: cited.doc, pcode: cited.pid, para: cited.place, page: cited.page ?? "" });
  }
  if (evidence.kind === "record") {
    const named = briefRecordTitle(evidence);
    if (named) return named;
    const text = recordReference(evidence);
    // A project's own ID is a link to its page (ticket 21's ProjectId rule).
    const reference = /^P\d{6}$/.test(text) ? <ProjectId pid={text} /> : <span className="inline-block max-w-full wrap-anywhere font-mono">{text}</span>;
    return <Fill template={copy.evidence.recordTitle} slots={{ kind: recordKind(evidence), reference }} />;
  }
  const fields = passageFields(evidence);
  const place = placeOf(fields);
  // Ticket 18's passages: a table row or its summary names its table, and a notice its ID, in mono.
  if (fields.kind === "notice_text" && fields.noticeId) {
    return <Fill template={copy.evidence.noticeTitle} slots={{ id: <span className="font-mono">{fields.noticeId}</span> }} />;
  }
  if (fields.kind === "table_row" || fields.kind === "table_summary") {
    const project = <span lang={fields.lang ?? undefined}>{fields.project}</span>;
    if (!fields.tableTitle) return <Fill template={copy.evidence.tableTitleUntitled} slots={{ project, page: String(fields.page ?? "") }} />;
    return (
      <Fill
        template={fields.kind === "table_summary" ? copy.evidence.summaryTitle : copy.evidence.tableTitle}
        slots={{ project, table: fields.tableTitle }}
      />
    );
  }
  return place.kind === "paragraph" ? (
    <Fill template={copy.evidence.title} slots={{ project: fields.project, para: place.text }} />
  ) : (
    <Fill template={copy.evidence.titleSection} slots={{ project: fields.project, section: place.text }} />
  );
}

// A mission brief's records that a kind and a key would name badly (ticket 37): the totals record ("Record
// P156634@2026-10-23"), an agency's latest plan (an agency name is no key) and an ISR rating, of which a brief cites
// several for one project. Null for any other record.
function briefRecordTitle(evidence: EvidenceEvent): ReactNode | null {
  const table = evidence.id.split(":")[0];
  const row = evidence.row;
  const field = (key: string) => (Array.isArray(row.fields) ? row.fields : []).find((one: { key: string }) => one.key === key)?.value;
  if (table === "strata.tools.project_records") {
    const pid = String(evidence.id.split(":")[1] ?? "").split("@")[0];
    return <Fill template={copy.evidence.totalsTitle} slots={{ pid: <ProjectId pid={pid} /> }} />;
  }
  if (table === "strata.silver.plan_versions" && field("implementing_agency")) {
    return <Fill template={copy.evidence.planVersionTitle} slots={{ agency: String(field("implementing_agency")) }} />;
  }
  if (table === "strata.silver.isr_ratings" && field("sequence") !== undefined && field("rating_name")) {
    return <Fill template={copy.evidence.isrRatingTitle} slots={{ n: String(field("sequence")), rating: String(field("rating_name")) }} />;
  }
  return null;
}

// A record's source line, the same in the evidence card and the drawer (the 14 brief, section 5.11):
// "Source: Procurement Plan, Northern Water Works Development Agency, P156634, version of October 9,
// 2026, page 3."
export function RecordSourceLine({ evidence, className }: { evidence: EvidenceEvent; className?: string }) {
  const source = recordSource(evidence);
  const words = copy.evidence;
  // "Source: Strata's lesson library, version 1, decided on October 27, 2026."
  const lesson = lessonOf(evidence);
  if (lesson) {
    const version = <Num value={lesson.version} />;
    return (
      <Source className={className}>
        {lesson.decidedOn ? (
          <Fill template={words.lessonSource} slots={{ version, date: <Num date={lesson.decidedOn} /> }} />
        ) : (
          <Fill template={words.lessonSourceUndated} slots={{ version }} />
        )}
      </Source>
    );
  }
  // A passage a lesson rests on (ticket 36), as the evidence pack and the Word footnote name it: "Implementation
  // Completion and Results Report, P130164, October 10, 2019, paragraph 54, page 23."
  const cited = lessonPassage(evidence);
  if (cited) {
    const place = fillText(cited.section ? words.passageSection : words.passageParagraph, { para: cited.place, section: cited.place });
    return (
      <Source className={className}>
        <Fill
          template={words.passageSource}
          slots={{ doc: cited.type, pid: <ProjectId pid={cited.pid} />, date: cited.date ? <Num date={cited.date} /> : "", place, page: String(cited.page ?? "") }}
        />
      </Source>
    );
  }
  // A record a project's Summary cites names its source by its key: "World Bank projects API, record of
  // August 1, 2023." Its project is the page's, so the line leaves the project ID out.
  const key = summarySourceKey(evidence);
  if (key && words.summaryRecordSources[key]) {
    return (
      <Source className={className}>
        <Fill template={words.summaryRecordSources[key]} slots={{ date: source.date ? <Num date={source.date} /> : "" }} />
      </Source>
    );
  }
  // A tool's totals record, such as a mission brief's (ticket 37): "Strata's totals of the records above, as of ...".
  const tool = (evidence.row.source ?? {}) as Record<string, unknown>;
  if (typeof tool.tool === "string") {
    return (
      <Source className={className}>
        <Fill template={words.toolSource} slots={{ date: evidence.row.public_from ? <Num date={String(evidence.row.public_from)} /> : "" }} />
      </Source>
    );
  }
  const date = source.date ? <Num date={source.date} /> : null;
  const pid = <ProjectId pid={source.pcode} />;
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
  // A notice is a record, though search returns its text as a passage (the 18 brief, section 7.4).
  if (evidence.kind === "passage" && evidence.row.kind === "notice_text") return copy.evidence.noticeEyebrow;
  if (lessonOf(evidence)) return copy.evidence.lessonEyebrow;
  if (evidence.kind === "versions") return copy.versions.eyebrow;
  // A quantile dot's list of packages is no record, so it names only its stratum.
  if (evidence.kind === "dot") return copy.evidence.package.dot.eyebrow;
  if (evidence.kind === "risk-reports" || evidence.kind === "risk-reports-all") return copy.packageRisks.drawer.reportsEyebrow;
  const stratum = evidence.kind === "record" || evidence.kind === "package" ? "What" : (evidence.stratum ?? "Why");
  return copy.evidence.eyebrow[stratum];
}

export function EvidenceCard({ evidence, n, sentence, visited = false }: { evidence: EvidenceEvent; n: number; sentence: number | null; visited?: boolean }) {
  const fields = evidence.kind === "passage" ? passageFields(evidence) : null;
  const shown = fields ? excerpt(fields.text, highlightsFor(evidence, sentence)[0] ?? null) : null;
  return (
    <div data-evidence-card className="flex flex-col p-1">
      <div className="flex items-start justify-between gap-3">
        <p className="text-label text-ink-muted">{eyebrow(evidence)}</p>
        <SourceNumber n={n} />
      </div>
      <p className="mt-1 text-h2 text-ink-heading">{sourceTitle(evidence)}</p>
      {fields && shown && fields.kind === "notice_text" && (
        <Lang as="p" code={fields.lang} data-excerpt className="mt-2 text-small text-ink">
          {copy.evidence.quoteOpen}
          {shown.cutBefore && copy.evidence.cut}
          {withoutMarkers(highlighted(shown.text, shown.range ? [shown.range] : []))}
          {shown.cutAfter && copy.evidence.cut}
          {copy.evidence.quoteClose}
        </Lang>
      )}
      {fields && shown && fields.kind !== "notice_text" && (
        <>
          <Lang as="p" code={fields.lang} data-excerpt className="mt-2 text-small text-ink">
            {copy.evidence.quoteOpen}
            {shown.cutBefore && copy.evidence.cut}
            {highlighted(shown.text, shown.range ? [shown.range] : [])}
            {shown.cutAfter && copy.evidence.cut}
            {copy.evidence.quoteClose}
          </Lang>
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

// A passage a lesson rests on, as get_lessons returns it inside its row (ticket 36): a record whose row names its
// passage and document. A Project Paper summary cites these from the PPSD rows it draws on. Null for any other source.
export function lessonPassage(evidence: EvidenceEvent): {
  doc: string; type: string; pid: string; date: string | null; place: string; section: boolean; page: number | null;
} | null {
  const row = evidence.row ?? {};
  if (evidence.kind !== "record" || !row.passage_id || !row.document_type) return null;
  return {
    doc: String(row.doc_short ?? row.document_type),
    type: String(row.document_type),
    pid: String(row.project_id ?? ""),
    date: (row.document_date ?? null) as string | null,
    place: String(row.paragraph ?? ""),
    section: row.locator === "section",
    page: (row.page ?? row.pdf_page ?? null) as number | null,
  };
}
