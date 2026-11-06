// A project's deep research brief in the browser (ticket 149): the shape GET /api/projects/{pid}/research answers with
// and the run's stream (POST, the answer stream's events: step, evidence, removed, done, error), as ticket 148's routes
// answer them (src/strata/server/research.py; recorded in tests/fixtures/api by tests/record_research_api.py). The
// page counts and checks nothing here: every sentence, date and number is the writer's, kept by the verifier, and each
// source's item is the reader's (ticket 147's item shape). This file only reads the answer into one shape, numbers the
// cited items in reading order, as an answer numbers its sources, and finds what each part of the page shows.
import { copy } from "../copy";
import type { EvidenceEvent, RemovedEvent, StepEvent } from "./answer";
import { formatDate } from "./format";

export type ResearchSentence = {
  text: string;
  evidence_ids: string[];
  // record, quote or summary; advice in the questions.
  kind: string;
  quote: { text: string; evidence_id: string } | null;
  // The picture's paragraph the sentence sits in, from 0 (ticket 156); absent elsewhere.
  paragraph?: number | null;
};

export type ResearchLocation = { geo_loc_id: string; name: string; latitude: number | null; longitude: number | null };

// One item a reader returned (ticket 147), as the run kept it.
export type ResearchItem = {
  evidence_id: string;
  public_from: string | null;
  source: { key: string; label: string; kind: string; license: string | null; url_of_source: string | null };
  kind: string;
  title: string;
  text: string;
  url: string;
  published: string | null;
  date_known: boolean;
  observed: string | null;
  location: ResearchLocation | null;
  // A satellite item's tile addresses: two years, nine tiles each, oldest first.
  image_urls: string[][];
  author: string | null;
  read_on: string | null;
};

export type Development = { date: string | null; date_known: boolean; sentences: ResearchSentence[] };
export type Site = { title: ResearchSentence; sentences: ResearchSentence[]; location: ResearchLocation | null };
export type Voice = ResearchSentence & { who: string; outlet: string; date: string | null; date_known: boolean };
export type Question = { lead: string; sentences: ResearchSentence[] };

export type Sections = {
  headline: ResearchSentence | null;
  picture: ResearchSentence[];
  bottom_line: ResearchSentence[];
  developments: Development[];
  by_site: Site[];
  voices: Voice[];
  questions: Question[];
  could_not_see: ResearchSentence[];
};

// What each source gave the run: how many items, or why it was not reached.
export type Coverage = { source: string; label: string; kind: string; reached: boolean; status: string | number | null; note: string | null; items: number | null; section?: string | null };

export type RemovedSentence = RemovedEvent & { section?: string | null };

export type ProjectFacts = {
  project_id: string;
  project_name: string | null;
  country_name: string | null;
  implementing_agencies: string[];
  closing_date: string | null;
};

export type Brief = {
  status: "ready";
  project_id: string;
  run_id: string | null;
  read_on: string | null;
  project: ProjectFacts | null;
  sections: Sections;
  removed: RemovedSentence[];
  coverage: Coverage[];
  // Each cited item as the evidence drawer shows it, by its evidence id.
  evidence: Record<string, EvidenceEvent>;
};

export type BriefAnswer = { status: "none" } | Brief;

// The section of the brief each kind of source feeds, for the one line a source not reached leaves under it. A
// coverage entry that names its section keeps it.
export const FEEDS: Record<string, keyof Sections> = {
  bank_report: "picture",
  procurement: "developments",
  news: "developments",
  complaint: "voices",
  social: "voices",
  satellite: "by_site",
  field_photo: "by_site",
  site_condition: "by_site",
  agency_statement: "developments",
  sanctions: "questions",
};

// The developments on one printed sheet: the sample's first sheet held eleven (build5.py).
export const DEVELOPMENTS_PER_SHEET = 11;

const list = <T,>(value: unknown): T[] => (Array.isArray(value) ? (value as T[]) : []);

function sentence(value: unknown): ResearchSentence | null {
  if (typeof value === "string") return { text: value, evidence_ids: [], kind: "summary", quote: null };
  if (!value || typeof value !== "object") return null;
  const found = value as Record<string, unknown>;
  // A group or a voice may hold its sentence under "sentence" (ticket 148 leaves the wrapping to the writer's JSON).
  if (typeof found.text !== "string" && found.sentence) return sentence(found.sentence);
  if (typeof found.text !== "string") return null;
  return {
    text: found.text,
    evidence_ids: list<string>(found.evidence_ids),
    kind: typeof found.kind === "string" ? found.kind : "record",
    quote: (found.quote as ResearchSentence["quote"]) ?? null,
    paragraph: typeof found.paragraph === "number" ? found.paragraph : null,
  };
}

// The picture as the writer's short paragraphs (ticket 156): sentences with the same paragraph number stay together, in
// order; a brief written before paragraphs reads as one.
export function paragraphsOf(sentences: ResearchSentence[]): ResearchSentence[][] {
  const groups: ResearchSentence[][] = [];
  let last: number | null | undefined;
  for (const said of sentences) {
    if (groups.length === 0 || said.paragraph !== last) groups.push([]);
    groups[groups.length - 1].push(said);
    last = said.paragraph;
  }
  return groups;
}

const sentences = (value: unknown): ResearchSentence[] => list(value).map(sentence).filter((one): one is ResearchSentence => one !== null);

// A part whose sentences come as a list, or as one sentence.
const partSentences = (part: Record<string, unknown>): ResearchSentence[] => {
  if (Array.isArray(part.sentences)) return sentences(part.sentences);
  const one = sentence(part.sentence ?? part.question ?? null);
  return one ? [one] : [];
};

function itemOf(event: EvidenceEvent): ResearchItem | null {
  const row = event.row as Partial<ResearchItem> | undefined;
  return row && typeof row === "object" && typeof row.url === "string" ? (row as ResearchItem) : null;
}

// The project's facts the brief's subject names (ticket 148: project_id, project_name, closing_date, as_of).
function subjectFacts(subject: Record<string, any> | null | undefined): ProjectFacts | null {
  if (!subject || typeof subject !== "object") return null;
  return {
    project_id: String(subject.project_id ?? ""),
    project_name: subject.project_name ?? null,
    country_name: subject.country_name ?? null,
    implementing_agencies: list<string>(subject.implementing_agencies),
    closing_date: subject.closing_date ?? null,
  };
}

// What each source gave the run, from the summary record's sources_reached and sources_not_reached (ticket 148's
// research_evidence: each with its key, label, kind and note, and a reached source's items).
function coverageFrom(summary: Record<string, any> | null | undefined): Coverage[] {
  const entry = (source: Record<string, any>, reached: boolean): Coverage => ({
    source: String(source.key ?? ""),
    label: String(source.label ?? source.key ?? ""),
    kind: String(source.kind ?? ""),
    reached,
    status: null,
    note: source.note ?? null,
    items: reached && typeof source.items === "number" ? source.items : null,
  });
  return [...list<Record<string, any>>(summary?.sources_reached).map((source) => entry(source, true)), ...list<Record<string, any>>(summary?.sources_not_reached).map((source) => entry(source, false))];
}

// The answer as the page reads it: a brief, or none yet. GET answers {status: "none"}, or {status: "written"} with the
// brief's sections at the top level, its subject, the run's summary record, the evidence its sentences cite by id and
// the sentences the verifier removed. Missing parts read as empty, so a brief the writer left a section out of still
// shows the rest.
export function briefFrom(answer: unknown): BriefAnswer {
  const found = (answer ?? {}) as Record<string, any>;
  const raw = (found.sections ?? found) as Record<string, unknown>;
  if (found.status === "none" || !(raw.headline || Array.isArray(raw.picture))) return { status: "none" };
  const evidence: Record<string, EvidenceEvent> = {};
  const events = Array.isArray(found.evidence) ? found.evidence : Object.values(found.evidence ?? {});
  for (const event of events as EvidenceEvent[]) if (event?.id) evidence[event.id] = event;
  // Items the answer lists on their own become the drawer's records.
  for (const item of list<ResearchItem>(found.items)) {
    if (item?.evidence_id && !evidence[item.evidence_id]) {
      evidence[item.evidence_id] = { id: item.evidence_id, kind: "record", tool: "research_evidence", stratum: null, short_name: null, row: item, highlights: [] };
    }
  }
  return {
    status: "ready",
    project_id: String(found.project_id ?? found.subject?.project_id ?? ""),
    run_id: found.run_id ?? null,
    read_on: found.read_on ?? found.run?.as_of ?? found.subject?.as_of ?? found.as_of ?? null,
    project: found.project ?? subjectFacts(found.subject),
    sections: {
      headline: sentence(raw.headline),
      picture: sentences(raw.picture),
      bottom_line: list(raw.bottom_line).flatMap((part) => (part && typeof part === "object" && !("text" in (part as object)) ? partSentences(part as Record<string, unknown>) : sentences([part]))),
      developments: list<Record<string, unknown>>(raw.developments).map((row) => ({
        date: typeof row.date === "string" ? row.date : null,
        date_known: row.date_known !== false && typeof row.date === "string",
        sentences: partSentences(row),
      })),
      by_site: list<Record<string, unknown>>(raw.by_site).map((group) => ({
        title: sentence(group.title) ?? { text: String(group.name ?? ""), evidence_ids: [], kind: "summary", quote: null },
        sentences: partSentences(group),
        location: (group.location as ResearchLocation) ?? null,
      })),
      voices: list<Record<string, unknown>>(raw.voices).flatMap((voice) => {
        const said = sentence(voice);
        if (!said) return [];
        // who is null when the item's words don't name the speaker (ticket 148 keeps only a name the item prints).
        return [{ ...said, who: typeof voice.who === "string" ? voice.who : "", outlet: String(voice.outlet ?? ""), date: typeof voice.date === "string" ? voice.date : null, date_known: voice.date_known !== false && typeof voice.date === "string" }];
      }),
      questions: list<Record<string, unknown>>(raw.questions).map((question) => ({
        lead: typeof question.lead === "string" ? question.lead : (sentence(question.lead)?.text ?? ""),
        sentences: partSentences(question),
      })),
      could_not_see: sentences(raw.could_not_see),
    },
    removed: list<RemovedSentence>(found.removed),
    coverage: Array.isArray(found.coverage) ? list<Coverage>(found.coverage) : coverageFrom(found.summary),
    evidence,
  };
}

// Every sentence of the brief in reading order: the order the screen and the sheets show them.
export function readingOrder(sections: Sections): ResearchSentence[] {
  return [
    ...(sections.headline ? [sections.headline] : []),
    ...sections.picture,
    ...sections.bottom_line,
    ...sections.developments.flatMap((row) => row.sentences),
    ...sections.by_site.flatMap((group) => [group.title, ...group.sentences]),
    ...sections.voices,
    ...sections.questions.flatMap((question) => question.sentences),
    ...sections.could_not_see,
  ];
}

// Each cited item, numbered once, in order of first citation; an item cited again keeps its number (as
// lib/answer.ts's citationNumbers numbers an answer's sources). The markers and the Sources list both read it.
export function briefNumbers(sections: Sections): Map<string, number> {
  const numbers = new Map<string, number>();
  for (const said of readingOrder(sections)) for (const id of said.evidence_ids) if (!numbers.has(id)) numbers.set(id, numbers.size + 1);
  return numbers;
}

export function itemFor(brief: Brief, id: string): ResearchItem | null {
  const event = brief.evidence[id];
  return event ? itemOf(event) : null;
}

// The run's summary record (research_evidence's counts, which a sentence cites for a number), as a source's name.
const SUMMARY = "strata.tools.research_evidence:";

// A voice's line: who said it when the item names them, the outlet, and the date or "undated".
export function voiceTemplate(voice: { who: string; date: string | null; date_known: boolean }): string {
  const words = copy.research;
  const dated = voice.date_known && voice.date;
  if (!voice.who) return dated ? words.voiceLineOutlet : words.voiceLineOutletUndated;
  return dated ? words.voiceLine : words.voiceLineUndated;
}

// A cited source's name: an item's outlet and date, the summary record's words, or the id itself.
export function sourceName(brief: Brief, id: string): string {
  const item = itemFor(brief, id);
  if (item) return itemName(item);
  return id.startsWith(SUMMARY) ? copy.research.summarySource : id;
}

// The sources not reached under one section, from the run's coverage.
export function notReachedIn(brief: Brief, section: keyof Sections): Coverage[] {
  return brief.coverage.filter((entry) => !entry.reached && (entry.section ?? FEEDS[entry.kind]) === section);
}

// A site's satellite items: those its sentences cite, and those the reader made for its location.
export function satelliteFor(brief: Brief, site: Site): ResearchItem[] {
  const cited = new Set([site.title, ...site.sentences].flatMap((said) => said.evidence_ids));
  const found: ResearchItem[] = [];
  for (const event of Object.values(brief.evidence)) {
    const item = itemOf(event);
    if (!item || item.kind !== "satellite" || item.image_urls.length < 2) continue;
    const here = site.location && item.location && item.location.geo_loc_id === site.location.geo_loc_id;
    if (cited.has(item.evidence_id) || here) found.push(item);
  }
  return found;
}

// A mosaic's year, from its tile address (s2cloudless-2018_3857).
export function tileYear(urls: string[]): string | null {
  const found = /s2cloudless-(\d{4})/.exec(urls[0] ?? "");
  return found ? found[1] : null;
}

// The developments in sheets of DEVELOPMENTS_PER_SHEET, for the print view.
export function developmentSheets(rows: Development[]): Development[][] {
  const sheets: Development[][] = [];
  for (let at = 0; at < rows.length; at += DEVELOPMENTS_PER_SHEET) sheets.push(rows.slice(at, at + DEVELOPMENTS_PER_SHEET));
  return sheets;
}

// A run's step, as the stream sends it (ticket 148): facts; source-<key>, done with its items or not_reached with its
// note; writing; checking, done with how many sentences it kept and removed.
export type ResearchStep = Omit<StepEvent, "kind" | "status"> & {
  kind: string;
  status: "running" | "done" | "not_reached";
  source?: string;
  label?: string;
  items?: number;
  note?: string | null;
  // The day the stored run read the sources, when the brief is written from it (ticket 152).
  stored_on?: string | null;
  // The day of the brief kept when the writer or the judge failed in the demo's setting (ticket 152).
  kept_from?: string | null;
  // The sentences the writer wrote: on writing done and on checking running (ticket 157).
  sentences?: number;
  kept?: number;
  removed?: number;
};

// The run's plan, sent once after the facts step (ticket 157, src/strata/research/run.py): every step the run will take,
// in order, and how long a run usually takes, low and high, in seconds. The tab lists these steps and no others.
export type PlannedStep = { id: string; kind: string; label: string };
export type ResearchPlan = { steps: PlannedStep[]; usual_seconds: [number, number] };

export function planFrom(data: unknown): ResearchPlan | null {
  const plan = data as Partial<ResearchPlan> | null;
  if (!plan || !Array.isArray(plan.steps) || !Array.isArray(plan.usual_seconds) || plan.usual_seconds.length !== 2) return null;
  return { steps: plan.steps, usual_seconds: [Number(plan.usual_seconds[0]), Number(plan.usual_seconds[1])] };
}

// The checks' own steps (check 4's judge, check 6's disagreements) run inside checking, whose line says when it is done.
const INSIDE_CHECKING = new Set(["judge", "disagreement"]);

export function withStep(steps: ResearchStep[], step: ResearchStep): ResearchStep[] {
  if (INSIDE_CHECKING.has(step.kind)) return steps;
  return steps.some((one) => one.id === step.id) ? steps.map((one) => (one.id === step.id ? { ...one, ...step } : one)) : [...steps, step];
}

// A source's name inside a sentence: the copy file's, else the registry's label the server sent.
export function sourceWords(key: string | undefined, label?: string | null): string {
  return (key && copy.research.source[key]) || label || key || "";
}

const filled = (template: string, values: Record<string, string>) => template.replace(/\{(\w+)\}/g, (slot, name: string) => values[name] ?? slot);

// "The Star, January 14, 2026": an item's outlet or agency and its date, or "undated" when the outlet prints none.
export function itemName(item: ResearchItem | null, style: "sentence" | "table" = "sentence"): string {
  if (!item) return "";
  const author = item.author || item.source.label;
  const words = copy.research;
  return item.date_known && item.published ? filled(words.sourceName, { author, date: formatDate(item.published, { style }) }) : filled(words.sourceNameUndated, { author });
}
