// The Lessons pages' data (ticket 29; the 29 design brief, section 9): what /api/lessons/me, /api/lessons,
// /api/lessons/review and /api/lessons/review/{item_id} return, and the addresses the pages link to. The
// server decides who may do what, counts every day and total, and chooses each count's words; the pages
// format dates and fill copy templates, and nothing else.
import type { EvidenceEvent, SentenceEvent } from "./answer";
import type { Removed } from "../components/Checks";
import { copy } from "../copy";

export type Item = { key: string; label: string };
export type IegStatus = "restated" | "ieg_lesson" | "awaiting" | "not_restated";
export type Stage = "recommendation" | "decision" | "cross_check" | "decided";
export type Kind = "new" | "recheck" | "cross_check";

// A sentence the server built, each number marked for Num (ticket 16's segments).
export type Segment = { text: string } | { number: number; capital?: boolean };

// An edition of the procurement rules (config/editions.toml): name for a sentence ("Its projects followed
// {name}."), short for a label ("Rules followed").
export type Edition = { key: string; name: string; short: string };

export type Me = {
  signed_in: boolean;
  tabs: ("library" | "review")[];
  acts: string[];
  regions: string[];
  role: string | null;
  waiting: number | null;
  // The business days a lesson has, so the queue's purpose shows while the queue itself loads.
  limit_days: number | null;
};

// One quote a lesson rests on, with what its source line and chip need.
export type LessonEvidence = {
  evidence_id: string;
  passage_id: string;
  role: "source" | "restatement";
  doc_type: string;
  doc_short: string;
  pid: string;
  project_name: string | null;
  date: string | null;
  report_number: string | null;
  locator: { kind: "paragraph" | "section"; text: string };
  page: number;
  quote: string;
  restated_by_ieg: boolean;
  // The quote's place in its passage's words, so a chip or a card opens the drawer with it highlighted.
  highlight?: [number, number] | null;
  // On the review page: the passage's words and the excerpt a card shows.
  text?: string;
  language?: string | null;
  excerpt?: { text: string; highlight: [number, number]; starts_inside: boolean; ends_inside: boolean } | null;
};

export type LessonCard = {
  lesson_id: string;
  version: number;
  statement: string;
  risk_factors: Item[];
  stage: Item | null;
  kind: Item | null;
  edition: Edition | null;
  sector: string | null;
  pid: string;
  ieg_status: IegStatus;
  review_date: string | null;
  decided_on: string;
  state: "current" | "rechecking";
  rechecking_since: string | null;
  region: string | null;
  quote: string | null;
  evidence: LessonEvidence[];
};

export type Library = {
  as_of: string;
  page: number;
  pages: number;
  page_size: number;
  total: number;
  from: number;
  to: number;
  can_recheck: boolean;
  // The re-check reason's limit, from config/thresholds.toml's [lesson_review].
  limits: { reason_max_chars: number };
  waiting: number | null;
  lessons: LessonCard[];
};

export type Clock = { day: number | null; limit_days: number | null; start_on: string; due_on: string; overdue_days: number; last_day: boolean };
export type Act = { name: string; role: string; phrase: string; on: string; reason: string | null; region: string | null; repeat_of: string | null; change: Record<string, unknown> | null };
export type Can = { act: "recommend" | "decide" | "cross_check" | null; reason_code: string | null; values: Record<string, string> };

export type QueueRow = {
  item_id: string;
  kind: Kind;
  stage: Stage;
  group: "you" | "others";
  statement: string;
  source: LessonEvidence | null;
  region: string;
  project: { pid: string; name: string | null; country: string | null; sector: string | null };
  ieg_status: IegStatus;
  review_date: string | null;
  may_repeat: boolean;
  clock: Clock | null;
  recommendation: Act | null;
  origin: { kind: string; name: string | null; on: string; reason: string | null; region: string | null } | null;
  decided: { region: string; on: string | null } | null;
  can: Can;
};

export type DecidedRow = {
  item_id: string;
  kind: Kind;
  statement: string;
  pid: string;
  project_name: string | null;
  outcome: string;
  version: number | null;
  decided_on: string;
  days_from_publication: number | null;
  // The day the report became public, which the days count from (null for a re-check).
  published_on: string | null;
};

export type Queue = {
  as_of: string;
  limit_days: number;
  regions: string[];
  waiting: number;
  lead: Segment[] | null;
  check: { window_days: number; proposed: number; dropped: number; segments: Segment[]; readiness: { sources: string[]; from: string } };
  groups: { you: QueueRow[]; others: QueueRow[] };
  decided: { window_days: number; total: number; page: number; pages: number; from: number; to: number; rows: DecidedRow[] };
};

export type Summary = {
  status: "writing" | "ready" | "nothing_to_add" | "nothing_survived" | "failed";
  sentences?: SentenceEvent[];
  evidence?: Record<string, EvidenceEvent>;
  checks?: { checks_run: number[]; tools: string[]; numbers: { total: number; matched: number }; dates: { total: number; matched: number }; quotes: { total: number; found: number }; sentences: { written: number; kept: number; removed: number } } | null;
  removed?: { index: number; sentence: string; reason: string; reasons: { check: number; code: string; text: string | null }[] }[];
};

export type HistoryEvent = {
  event: string;
  on: string | null;
  name?: string | null;
  role?: string | null;
  region?: string | null;
  outcome?: string | null;
  reason?: string | null;
  doc_short?: string;
  pid?: string;
  project_name?: string | null;
  published_on?: string | null;
  review_date?: string | null;
  changes?: { field: string; was: unknown; now: unknown }[];
  version?: number | null;
  target?: string | null;
};

export type Outcome = {
  outcome: string;
  on: string;
  lesson_id?: string | null;
  version?: number | null;
  // The version a change or a retirement left on record, which the server counts.
  previous_version?: number | null;
  target?: string | null;
  days_from_publication?: number | null;
  published_on?: string | null;
  decided_region?: string;
};

export type ReviewItem = QueueRow & {
  read_only: boolean;
  evidence: LessonEvidence[];
  ieg_note: { kind: "awaiting" } | { kind: "alone"; review_date: string } | null;
  tags: { risk_factors?: Item[]; stage?: Item | null; kind?: Item | null; edition?: Edition | null; sector: string | null };
  // next_version: the version a re-check's change would write now, which the server counts.
  lesson: { lesson_id: string | null; version: number | null; next_version: number | null };
  summary: Summary;
  // next_version: the version merging into this lesson would write now.
  repeats: (LessonCard & { sentences: SentenceEvent[]; next_version: number | null })[];
  history: HistoryEvent[];
  outcome: Outcome | null;
  lists: { risk_factors: Item[]; stages: Item[]; kinds: Item[] };
  limits: { reason_max_chars: number; statement_max_chars: number; sample_percent: number; summary_poll_seconds: number; summary_poll_minutes: number };
};

// What a save returns, and a refusal's body.
export type Saved = { item: ReviewItem; waiting: number; next_item_id: string | null };
export type Refusal = { code: string; values: Record<string, string>; item?: ReviewItem };

// The addresses: the library, its pages, the queue and one item. Ticket 39 changes a lesson's own link to
// /lessons?show={id}, here in one place.
export const LESSONS_HREF = "/lessons";
export const QUEUE_HREF = "/lessons/review";
export const itemHref = (itemId: string) => `${QUEUE_HREF}/${encodeURIComponent(itemId)}`;
export const lessonHref = (lessonId: string) => `${LESSONS_HREF}#lesson-${encodeURIComponent(lessonId)}`;
export const pageHref = (base: string, page: number) => (page > 1 ? `${base}?page=${page}` : base);

// The removed sentences, each with its first reason that has a sentence in the copy file, as an answer's are.
export function removedOf(summary: Summary): Removed[] {
  const reasons = copy.removed.reasons as Record<string, { item: string; joined: string }>;
  return (summary.removed ?? []).map((removed) => {
    const code = [removed.reason, ...removed.reasons.map((reason) => reason.code)].find((one) => one in reasons);
    const reason = code ? reasons[code] : copy.removed.unknownReason;
    return { sentence: removed.sentence, reason: reason.item, reasonJoined: reason.joined };
  });
}
