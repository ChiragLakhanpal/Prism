// How a source the answer stream sent is named on screen (the 14 brief, sections 4.4, 4.5 and 5.11 to
// 5.13): the evidence card's title and excerpt, the marker's accessible name, and the drawer's meta
// line. Every field comes from the stream's evidence event (src/strata/agent/verifier.py); nothing
// here looks anything up.
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
};

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
  };
}

// The record a What citation names: its STEP reference or other key, from the row a tool returned.
export function recordReference(evidence: EvidenceEvent): string {
  const row = evidence.row;
  return String(row.activity_reference_no ?? row.reference ?? evidence.id.split(":").slice(1).join(":"));
}

// The paragraph's highlights for one sentence of the answer, as [start, end] ranges.
export function highlightsFor(evidence: EvidenceEvent, sentence: number | null): [number, number][] {
  if (sentence === null) return [];
  return evidence.highlights.filter((highlight) => highlight.sentence === sentence).map((highlight) => [highlight.start, highlight.end]);
}

// Two or three whole sentences around the first match, for the evidence card, with the match's place
// in the excerpt. A paragraph's own number ("54. ") is left out.
export function excerpt(text: string, range: [number, number] | null): { text: string; range: [number, number] | null } {
  const lead = /^\s*\d+(?:\.\d+)*\.\s+/.exec(text)?.[0].length ?? 0;
  const spans: [number, number][] = [];
  const sentence = /[^.!?]+(?:[.!?]+["')\]]*|$)\s*/g;
  sentence.lastIndex = lead;
  for (let match = sentence.exec(text); match && match[0]; match = sentence.exec(text)) {
    spans.push([match.index, match.index + match[0].length]);
  }
  if (spans.length === 0) return { text: text.slice(lead).trim(), range: null };
  const at = range ? Math.max(0, spans.findIndex(([start, end]) => range[0] >= start && range[0] < end)) : 0;
  const first = Math.max(0, at - 1);
  const last = Math.min(spans.length - 1, first + 2);
  const start = spans[first][0];
  const shown = text.slice(start, spans[last][1]).trimEnd();
  const inside = range && range[0] >= start && range[1] <= start + shown.length ? ([range[0] - start, range[1] - start] as [number, number]) : null;
  return { text: shown, range: inside };
}
