// The Lessons page's data (ticket 39; the 39 design brief, section 9): what /api/lessons/page, /api/lessons/library
// and the version choices return, and the addresses the page links to. The server counts everything, decides each
// notice's tier and writes each count's word; the page formats dates and fills copy templates, and nothing else.
import { copy } from "../copy";
import type { RemovedEvent } from "./answer";
import { isPpsdKind } from "./drafts";
import { formatDate } from "./format";
import type { Item, LessonCard, LessonEvidence } from "./lessons";

// A draft's title, as the Drafts tab and the Lessons page's "Used in" line write it.
export function draftTitle(kindKey: string, subject: Partial<Record<string, string | null>>): string {
  const kinds = copy.draft.kinds as Record<string, { rowTitle: (title: string, date: string) => string }>;
  const kind = kinds[kindKey] ?? kinds.review_notes;
  if (kindKey === "mission_brief") return kind.rowTitle(subject.project_name ?? "", "");
  if (isPpsdKind(kindKey)) return kind.rowTitle(subject.package_title ?? "", "");
  const date = subject.plan_date ? formatDate(subject.plan_date.slice(0, 10), { style: "table" }) : "";
  return kind.rowTitle(subject.implementing_agency ?? "", date);
}

// The sentence that names a draft's row, from its kind's copy (config/drafts.toml, row_label).
export function rowLabel(kindKey: string, label: { n: number; risk_label: string } | null | undefined): string | null {
  const kinds = copy.draft.kinds as Record<string, { rowLabel?: string }>;
  const template = kinds[kindKey]?.rowLabel;
  if (!template || !label) return null;
  return template.replace("{n}", String(label.n)).replace("{risk_label}", label.risk_label);
}

// A sentence the server built: words, a count (with the word the server chose and the items it opens), a numeral, a
// date, or an in-page link.
export type PageSegment =
  | { text: string }
  | { number: number; word?: string; capital?: boolean; popover?: string | null; numeral?: boolean }
  | { date: string | null }
  | { link: string; href: string };

export type ReportItem = {
  kind: "icr" | "review" | "ppar";
  doc_type: string;
  doc_short: string;
  document_id: string;
  doc_key: string;
  pid: string;
  project_name: string | null;
  disclosed_on: string | null;
};

export type DigestLesson = { lesson_id: string; version: number; statement: string; decided_on: string; change_kind: string; state: string; exported_uses?: DraftUse[] };

// A draft a notice names: its kind and subject give its title, as the Drafts tab writes it.
export type DraftUse = {
  draft_id: string;
  kind: string;
  subject: Record<string, string | null>;
  cites: number;
  row_key?: string;
  draft_state?: string;
  row_label?: { n: number; risk_label: string } | null;
  holds_export?: boolean;
  can_act?: boolean;
  can_update?: boolean;
};

export type Strengthened = {
  segments: PageSegment[];
  count: number;
  items: { lesson_id: string; a: number; b: number; statement: string; decided_on: string; was: { quotes?: number; reports?: number }; now: { quotes?: number; reports?: number }; uses: DraftUse[] }[];
};

export type Digest = {
  kind: "first" | "since" | "nothing";
  segments: PageSegment[];
  counts: { total?: number; rechecking?: number; reports?: Record<string, number>; new?: number; changed?: number; retired?: number; proposed: number | null };
  items: { reports?: ReportItem[]; new?: DigestLesson[]; changed?: DigestLesson[]; retired?: DigestLesson[] };
  strengthened: Strengthened | null;
};

export type Tier = "narrowed" | "retired_outdated" | "retired_wrong";
export type Change = { field: string; was: string; now: string; was_ranges: [number, number][]; now_ranges: [number, number][] };

// What a version notice shows, on the Lessons tab (with every use) and under a draft row.
export type NoticeBody = {
  lesson_id: string;
  tier: Tier;
  holds_export: boolean;
  a: number;
  b: number;
  statement_a: string;
  statement_b: string;
  changes: Change[];
  decided_on: string;
  retired_on: string | null;
  retired_as: string | null;
  reason: string;
  between: { version: number; decided_on: string }[];
  anchor: string;
  // The longest reason the keep route takes (lesson_review.reason_max_chars).
  reason_max_chars: number;
};

export type Notice = NoticeBody & { actions: ("versions" | "update" | "remove" | "keep")[]; uses: DraftUse[] };
export type RowNotice = NoticeBody & { row_key: string; can_act: boolean; actions: ("update" | "remove" | "keep")[]; row_label: { n: number; risk_label: string } | null };

export type Feedback = { never: boolean; segments: PageSegment[] | null; counts: Record<string, number> | null };

export type LibraryCard = LessonCard & {
  categories?: Item[];
  methods?: Item[];
  retired?: { as: string; on: string; reason: string } | null;
};

export type Filters = { stage: string | null; method: string | null; sector: string | null; status: string | null };

export type LibraryAnswer = {
  as_of: string;
  page: number;
  pages: number;
  page_size: number;
  total: number;
  of: number;
  from: number;
  to: number;
  status: "current" | "rechecking" | "retired";
  filters: Filters;
  narrowed: boolean;
  unknown_filter: boolean;
  shown: string | null;
  options: { stage: Item[]; method: Item[]; sector: Item[]; status: { key: string }[] };
  count: PageSegment[];
  can_recheck: boolean;
  limits: { reason_max_chars: number };
  waiting: number | null;
  lessons: LibraryCard[];
};

export type LessonsPageAnswer = {
  view: "staff" | "preview";
  as_of: string | null;
  visit: { first_visit: boolean; last_visit_on: string | null } | null;
  digest: Digest | null;
  notices: Notice[];
  new_lessons: { cards: LibraryCard[]; more: number; more_segments: PageSegment[] | null } | null;
  feedback: Feedback | null;
  library: LibraryAnswer;
};

// Two versions of a lesson, as the evidence drawer's view shows them (evidence id versions:{lesson_id}:{a}:{b}).
export type VersionBlock = {
  version: number;
  statement: string;
  risk_factors: Item[];
  stage: Item | null;
  kind: Item | null;
  categories?: Item[];
  methods?: Item[];
  sector: string | null;
  decided_on: string;
  state: string;
  change_kind: string;
  reason: string | null;
  evidence: LessonEvidence[];
};
export type VersionsView = NoticeBody & { evidence_id: string; current: number; versions: [VersionBlock, VersionBlock] };

// What a choice on a row returns.
// removed: when nothing passed, the sentences the verifier removed from the rewrite, which the notice shows.
export type ChoiceAnswer<D> = {
  outcome: "updated" | "kept" | "removed" | "restored" | "reverted" | "nothing_passed";
  back_to_draft?: boolean;
  removed?: RemovedEvent[];
  draft: D;
};

// The addresses: the library's filters keep only the keys the server knows (the 39 brief, section 4.8).
export const FILTER_KEYS = ["stage", "method", "sector", "status"] as const;

export function pageQuery(search: string): string {
  const asked = new URLSearchParams(search);
  const kept = new URLSearchParams();
  for (const key of [...FILTER_KEYS, "page", "show", "view", "asof"]) {
    const value = asked.get(key);
    if (value) kept.set(key, value);
  }
  const query = kept.toString();
  return query ? `?${query}` : "";
}

export function libraryHref(filters: Partial<Filters>, page = 1): string {
  const kept = new URLSearchParams();
  for (const key of FILTER_KEYS) {
    const value = filters[key];
    if (value) kept.set(key, value);
  }
  if (page > 1) kept.set("page", String(page));
  const query = kept.toString();
  return query ? `/lessons?${query}` : "/lessons";
}

export const showHref = (lessonId: string, retired = false) =>
  `/lessons?${retired ? "status=retired&" : ""}show=${encodeURIComponent(lessonId)}`;
export const versionsId = (lessonId: string, a: number, b: number) => `versions:${lessonId}:${a}:${b}`;
export const choiceUrl = (draftId: string, rowKey: string) =>
  `/api/drafts/${encodeURIComponent(draftId)}/rows/${encodeURIComponent(rowKey)}/lesson`;
