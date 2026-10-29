// The disagreement card's words, built once from either place a disagreement arrives (ticket 23): the answer
// stream's disagreement event (ticket 24) and the evidence drawer's disagreement view (GET /api/evidence?id=
// disagreement:{id}). Both give each side in the order it was written, with its kind of report, its field and
// value or its quote, and the side Strata leans on; every sentence comes from the copy file and these values.
import { copy } from "../copy";
import { formatDate } from "./format";

export type SideData = {
  evidence_id: string;
  assertion_id: string | null;
  // The kind of report, by the documents API's type (config/project_page.toml's groups): pad, isr, icr, icr_review,
  // ppar, or record for a side that rests on a record.
  type: string | null;
  document_type: string | null;
  sequence: number | null;
  paragraph: string | null;
  paragraph_numbered: boolean | null;
  evidence_tier: string | null;
  made_at: string | null;
  field_name: string | null;
  value: string | null;
  value_form: string | null;
  quote: string | null;
  // The whole sentence that holds the quote, which the drawer's card shows (the server's disagreement view).
  sentence?: string | null;
  leaned: boolean;
  months_after_event?: number | null;
  doc_key?: string | null;
};

const words = copy.disagreement;
const card = words.card;

const paragraphOf = (side: SideData) => (side.paragraph_numbered ? side.paragraph : null);
const typeOf = (side: SideData) => side.type ?? (side.document_type ? "other" : "record");
// The word the side's report uses for a numbered place: "section" for an ICR Review, "paragraph" for the others.
export const placeWordOf = (side: SideData) => words.placeWord[typeOf(side)] ?? words.placeWordOther;

// "ISR 7", "ICR paragraph 78": a side's name in the card's group name, the drawer's heading and its tabs.
export function sideShort(side: SideData): string {
  const short = words.shortType[typeOf(side)] ?? words.shortType.other;
  return words.sourceShort(short, side.sequence, paragraphOf(side), placeWordOf(side));
}

// "Implementation Status and Results Report (ISR) 7": the first name on a screen that spells the abbreviation out.
export function sideFull(side: SideData): string {
  const short = words.shortType[typeOf(side)] ?? null;
  return words.sourceFull(side.document_type ?? short ?? "", short, side.sequence, paragraphOf(side), placeWordOf(side));
}

// "ISR 7", "ICR, paragraph 78": a side's title on the timeline and in the drawer.
export function sideTitle(side: SideData): string {
  const short = words.shortType[typeOf(side)] ?? words.shortType.other;
  const named = words.sourceShort(short, side.sequence, null);
  const paragraph = paragraphOf(side);
  return paragraph
    ? card.titlePara.replace("{short}", named).replace("{place}", placeWordOf(side)).replace("{para}", paragraph)
    : card.title.replace("{short}", named);
}

// "August 26, 2016. Written during the project."
export function sideMeta(side: SideData): string {
  const written = (words.written as Record<string, string>)[side.evidence_tier ?? "record"] ?? words.written.record;
  return card.meta.replace("{date}", side.made_at ? formatDate(side.made_at) : "").replace("{written}", written);
}

// "Open ISR 7", "Open paragraph 78".
export function sideOpen(side: SideData): string {
  const paragraph = paragraphOf(side);
  const named = paragraph ? card.openPara.replace("{place}", placeWordOf(side)).replace("{para}", paragraph) : sideShort(side);
  return card.open.replace("{side}", named);
}

export function subjectOf(attribute: string | null, event: string | null): string {
  const subject = (attribute && card.subject[attribute]) || card.subjectOther;
  const at = event ? card.subjectAt[event] : undefined;
  return at ? at.replace("{subject}", subject) : subject;
}

// "the ICR", "ISR 7": a side's report as a sentence names it, as the timeline does, never its paragraph, since the
// rule is about which report Strata leans on. The what-changes line, the keep line and the keep button use it too,
// so the card names the other report one way (the 23 brief, section 7.5, {other_short}).
export function sideInSentence(side: SideData): string {
  const short = copy.timeline.short;
  return (short[typeOf(side)] ?? short.other).replace("{sequence}", String(side.sequence ?? ""));
}

export function ruleSentence(ruleId: string | null, sides: SideData[]): string {
  const lean = sides.find((side) => side.leaned);
  const other = sides.find((side) => !side.leaned);
  const rules = words.rule as Record<string, string>;
  return (rules[ruleId ?? ""] ?? "").replace("{lean}", lean ? sideInSentence(lean) : "").replace("{other}", other ? sideInSentence(other) : "");
}

export function whatChanges(sides: SideData[], ifYouKeep: { field_name: string | null; value: string | null } | null): string | undefined {
  const other = sides.find((side) => !side.leaned);
  if (!other || !ifYouKeep?.field_name || !ifYouKeep.value || !sides.some((side) => side.leaned)) return undefined;
  return words.whatChanges(sideInSentence(other), ifYouKeep.field_name, ifYouKeep.value);
}

// "Rated three months after the mid-term review of May 16, 2016.", when get_disagreements gives the months: a count
// from one to nine in words (DESIGN.md section 7).
export function sideContext(side: SideData, event: string | null, moment: string | null): string | null {
  if (event !== "mid_term_review" || side.months_after_event == null || !moment) return null;
  const months = side.months_after_event;
  const template = side.value_form === "rating" ? card.rated(months) : card.written(months);
  return template.replace("{months}", inWords(months)).replace("{date}", formatDate(moment));
}

const inWords = (count: number) => (count >= 1 && count <= 9 ? copy.num.words[count - 1] : String(count));

// "That changes one sentence in this answer."
export function changesLine(count: number, kind: "answer" | "draft"): string {
  const template = kind === "answer" ? card.changesAnswer(count) : card.changesDraft(count);
  return template.replace("{n}", inWords(count));
}
