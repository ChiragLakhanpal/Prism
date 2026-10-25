// How a source the answer stream sent is named on screen (the 14 brief, sections 4.4, 4.5 and 5.11 to
// 5.13): the evidence card's title and excerpt, the marker's accessible name, and the drawer's meta
// line. Every field comes from the stream's evidence event (src/strata/agent/verifier.py); nothing
// here looks anything up.
import { copy } from "../copy";
import type { EvidenceEvent } from "./answer";
import { formatDate } from "./format";

export type PassageFields = {
  docType: string;
  pcode: string;
  // The project's name without "Project" at its end, since its ID beside it already says so.
  project: string;
  date: string;
  section: string | null;
  para: string;
  numbered: boolean;
  page: number | null;
  pages: number | null;
  text: string;
  lang: string | null;
  pdfUrl: string | null;
  // Ticket 18: what the passage is (a paragraph, a table row, a table's summary or a notice's text),
  // whether the layout parser read it from a scanned page, its table and row, and its notice.
  kind: "paragraph" | "table_row" | "table_summary" | "notice_text";
  scanned: boolean;
  tableTitle: string | null;
  tableRow: number | null;
  // The last PDF page a passage runs onto, such as a table's summary that covers pages 65 to 70.
  lastPage: number | null;
  cells: [string, string][];
  noticeId: string | null;
  noticeUrl: string | null;
  // Ticket 21: the document's key in its project and the passage's id, for the source view's address.
  docKey: string | null;
  passageId: string | null;
};

// Where in its document a passage sits: a numbered paragraph ("54", or an item such as 10.b), or else
// its section. An ISR numbers no paragraphs, so ticket 11 keys each section ("s4") and marks the
// passage unnumbered; that key is never shown, since no reader could find "paragraph s4" in the PDF.
export type Place = { kind: "paragraph" | "section"; text: string };

export function placeOf(fields: PassageFields): Place {
  return fields.numbered ? { kind: "paragraph", text: fields.para } : { kind: "section", text: keepClosingId(fields.section ?? fields.para) };
}

// A section's closing ID, such as "1.A" in "Annex 1.A" or "III.B", is tied to the word before it by a
// no-break space, so a heading or a tab never ends a line on "Annex". A name of words alone, such as
// "Project Development Objective Indicators", still wraps between them.
function keepClosingId(section: string): string {
  return section.replace(/ (\S*[0-9.]\S*)$/, "\u00a0$1");
}

// A table's title keeps the ID of an annex, appendix or table with its word, "Annex 4", so a narrow
// meta line or heading never ends a line on "Annex" (design review r2 P8).
function keepIdWithWord(title: string): string {
  return title.replace(/\b(Annex|Annexe|Appendix|Table|Schedule) (?=[0-9A-Z])/g, "$1\u00a0");
}

export function shortProjectName(name: string): string {
  return name.replace(/\s+Project$/, "");
}

export function passageFields(evidence: EvidenceEvent): PassageFields {
  const row = evidence.row;
  const source = (row.source ?? {}) as Record<string, any>;
  return {
    docType: String(source.document_type ?? row.document_type ?? ""),
    pcode: String(source.project_id ?? row.project_id ?? ""),
    project: shortProjectName(String(source.project_name ?? "")),
    date: source.document_date ? formatDate(String(source.document_date)) : "",
    section: (source.section_path ?? row.section_path ?? null) as string | null,
    para: String(source.paragraph ?? row.paragraph ?? ""),
    numbered: Boolean(source.paragraph_numbered ?? row.paragraph_numbered ?? true),
    page: (source.pdf_page ?? row.pdf_page ?? null) as number | null,
    pages: (source.pdf_pages ?? null) as number | null,
    text: String(row.text ?? ""),
    lang: (row.language ?? null) as string | null,
    pdfUrl: (source.pdf_url ?? null) as string | null,
    kind: (row.kind ?? "paragraph") as PassageFields["kind"],
    scanned: Boolean(row.scanned),
    tableTitle: row.table_title ? keepIdWithWord(String(row.table_title)) : null,
    tableRow: (row.table_row ?? null) as number | null,
    lastPage: (row.last_pdf_page ?? null) as number | null,
    cells: (row.cells ?? []) as [string, string][],
    noticeId: (row.notice_id ?? source.notice_id ?? null) as string | null,
    noticeUrl: (source.notice_url ?? null) as string | null,
    docKey: (source.doc_key ?? row.doc_key ?? null) as string | null,
    passageId: (row.passage_id ?? null) as string | null,
  };
}

// The record a What citation names: its STEP reference or other key, from the row a tool returned.
export function recordReference(evidence: EvidenceEvent): string {
  const row = evidence.row;
  return String(row.activity_reference_no ?? row.reference ?? evidence.id.split(":").slice(1).join(":"));
}

// A lesson in Strata's library (get_lessons and the lesson review writer cite it by version): its
// statement, version and decision date, from the row the tool returned. Null for any other source.
export const LESSON_TABLE = "strata.ops.lesson_versions";
export type LessonRecord = { statement: string; version: number; decidedOn: string | null };

export function lessonOf(evidence: EvidenceEvent): LessonRecord | null {
  if (evidence.kind !== "record" || evidence.id.split(":")[0] !== LESSON_TABLE) return null;
  const row = evidence.row;
  return {
    statement: String(row.statement ?? ""),
    version: Number(row.version ?? 0),
    decidedOn: (row.decided_on ?? null) as string | null,
  };
}

// What kind of record a What citation names ("Activity", "Contract"), by the table before the colon
// in its evidence id, so a contract a later tool cites is never called an activity.
export function recordKind(evidence: EvidenceEvent): string {
  const table = evidence.id.split(":")[0];
  // A notice a package advertised again cites (ticket 28) is named by its type.
  if (table === "strata.silver.notices") {
    const type = ((evidence.row.source ?? {}) as Record<string, unknown>).document_type;
    return type === "Contract Award" ? copy.evidence.noticeRecordKinds.award : copy.evidence.noticeRecordKinds.other;
  }
  return copy.evidence.recordKinds[table] ?? copy.evidence.summaryRecordKinds[table] ?? copy.evidence.recordKindOther;
}

// The source_key a project's Summary gives each record it cites (ticket 21), such as projects_api.
export function summarySourceKey(evidence: EvidenceEvent): string | null {
  const source = (evidence.row.source ?? {}) as Record<string, any>;
  return typeof source.source_key === "string" ? source.source_key : null;
}

export type RecordSource = { docType: string; agency: string | null; pcode: string; date: string | null; page: number | null };

// Where a record came from, from the source fields its tool returned with it.
export function recordSource(evidence: EvidenceEvent): RecordSource {
  const source = (evidence.row.source ?? {}) as Record<string, any>;
  return {
    docType: String(source.document_type ?? ""),
    agency: (source.implementing_agency ?? null) as string | null,
    pcode: String(source.project_id ?? evidence.row.project_id ?? ""),
    date: (source.plan_date ?? source.document_date ?? null) as string | null,
    page: (source.pdf_page ?? null) as number | null,
  };
}

// The paragraph's highlights for one sentence of the answer, as [start, end] ranges.
export function highlightsFor(evidence: EvidenceEvent, sentence: number | null): [number, number][] {
  if (sentence === null) return [];
  return evidence.highlights.filter((highlight) => highlight.sentence === sentence).map((highlight) => [highlight.start, highlight.end]);
}

// The longest excerpt the evidence card quotes, in characters. A section of an ISR is table text with
// no sentence ends, so without a limit the card would quote all of it.
const EXCERPT_MAX = 280;

export type Excerpt = { text: string; range: [number, number] | null; cutBefore: boolean; cutAfter: boolean };

// The excerpt the evidence card quotes, with the match's place in it: the sentences the match is in,
// whole, then the sentence before and the one after, each only while the excerpt stays within
// EXCERPT_MAX. A paragraph's own number ("54. ") is left out. A sentence ends at a stop followed by a
// space or the end, so "80.00" or "US$1.5 million" is never cut at its decimal point. Only when the
// matched sentences alone are longer, such as an ISR's table text, is the excerpt cut between words,
// never inside the match, and it says where it was cut.
export function excerpt(text: string, range: [number, number] | null): Excerpt {
  const lead = /^\s*\d+(?:\.\d+)*\.\s+/.exec(text)?.[0].length ?? 0;
  const spans: [number, number][] = [];
  const sentence = /(?:[^.!?]|[.!?]+(?!["')\]]*(?:\s|$)))+(?:[.!?]+["')\]]*|$)\s*/g;
  sentence.lastIndex = lead;
  for (let match = sentence.exec(text); match && match[0]; match = sentence.exec(text)) {
    spans.push([match.index, match.index + match[0].length]);
  }
  if (spans.length === 0) return { text: text.slice(lead).trim(), range: null, cutBefore: false, cutAfter: false };
  const holding = (offset: number) => Math.max(0, spans.findIndex(([start, end]) => offset >= start && offset < end));
  const size = (a: number, b: number) => text.slice(spans[a][0], spans[b][1]).trimEnd().length;
  let first = range ? holding(range[0]) : 0;
  let last = range ? Math.max(first, holding(range[1] - 1)) : 0;
  if (first > 0 && size(first - 1, last) <= EXCERPT_MAX) first -= 1;
  if (last < spans.length - 1 && size(first, last + 1) <= EXCERPT_MAX) last += 1;
  let start = spans[first][0];
  let end = start + size(first, last);
  let cutBefore = false;
  let cutAfter = false;
  if (end - start > EXCERPT_MAX) {
    // The match stays whole. A third of the room it leaves goes before it and the rest after it, and
    // each cut moves back to a space. With no match, the excerpt is cut after its first EXCERPT_MAX.
    const [matchStart, matchEnd] = range && range[0] >= start && range[1] <= end ? range : [start, start];
    const before = Math.max(0, Math.floor((EXCERPT_MAX - (matchEnd - matchStart)) / 3));
    const from = Math.max(start, Math.min(matchStart - before, end - EXCERPT_MAX));
    if (from > start) {
      const space = text.indexOf(" ", from);
      start = space === -1 ? matchStart : Math.min(matchStart, space + 1);
      cutBefore = true;
    }
    const to = Math.min(end, Math.max(start + EXCERPT_MAX, matchEnd));
    if (to < end) {
      end = Math.max(matchEnd, text.lastIndexOf(" ", to));
      while (end > Math.max(start, matchEnd) && /[\s,;:·-]/.test(text[end - 1])) end -= 1;
      cutAfter = true;
    }
  }
  const shown = text.slice(start, end);
  const inside = range && range[0] >= start && range[1] <= end ? ([range[0] - start, range[1] - start] as [number, number]) : null;
  return { text: shown, range: inside, cutBefore, cutAfter };
}
