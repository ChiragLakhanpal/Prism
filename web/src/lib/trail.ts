// The contract trail's and the Connections tab's answers (ticket 22; src/strata/server/trail.py and edges.py),
// and the small helpers their screens share. The server chooses, orders and counts; these only write what it gave.
import { copy } from "../copy";
import { stepFamilies } from "../steps";
import { formatCount, formatNumber } from "./format";
import type { ContractsHeld } from "./timeline";

export type Field = { key: string; value: string; kind: string };
export type SourceFields = Record<string, string | number | null>;

export type PlanRecord = {
  evidence_id: string;
  public_from: string;
  description: string | null;
  estimated_amount_usd: string | null;
  fields: Field[];
  steps: { step: string; first_planned_on: string | null; actual_on: string | null }[];
  first_plan_date: string | null;
  plan_date: string;
  agency_id: string;
  implementing_agency: string | null;
  source: SourceFields;
};
export type NoticeRecord = {
  evidence_id: string;
  public_from: string;
  notice_id: string;
  notice_type: string;
  notice_date: string;
  readvertised: boolean;
  url: string | null;
  fields: Field[];
  source: SourceFields;
};
export type Bid = {
  bid: number;
  outcome: "awarded" | "not_awarded" | "rejected" | "none";
  name: string | null;
  is_individual_consultant: boolean;
  is_joint_venture: boolean;
  members: string[];
  country: string | null;
  price_at_opening: string | null;
  evaluated_price: string | null;
  reason: string | null;
};
export type AwardRecord = {
  evidence_id: string;
  public_from: string;
  notice_id: string;
  notice_date: string;
  currency: string | null;
  labels: { price_at_opening: string | null; evaluated_price: string | null };
  lists_scores: boolean;
  proposals: boolean;
  bids: Bid[];
  bid_count: number;
  url: string | null;
  source: SourceFields;
};
export type ContractRecord = {
  evidence_id: string;
  public_from: string;
  contract_id: string;
  contract_reference: string;
  signed_on: string | null;
  amount: string | null;
  currency: string | null;
  from_notice: boolean;
  record_noun: string;
  award_notice_id: string | null;
  description: string | null;
  supplier: { name: string | null; country: string | null; is_individual_consultant: boolean; is_joint_venture: boolean; members: string[] };
  source: SourceFields;
};
export type Topic = { kind: "category" | "sector" | "place" | "name"; code?: string; name?: string; text?: string };
export type ParagraphRecord = {
  evidence_id: string;
  public_from: string;
  passage_id: string;
  stratum: "Why" | "How" | "What";
  short_name: string | null;
  contract_evidence_id: string;
  contract_reference: string | null;
  document_id: string;
  document_type: string;
  document_date: string;
  paragraph: string;
  paragraph_numbered: boolean;
  section_path: string;
  // What tells two cards of one report apart when they would share a title: a section, or a page.
  title_section: string | null;
  title_page: number | null;
  pdf_page: number | null;
  doc_key: string | null;
  language: string | null;
  text: string;
  highlights: [number, number][];
  topics: Topic[];
};

export type ParagraphGroup = {
  document_id: string;
  document_type: string;
  short_name: string | null;
  stratum: "Why" | "How" | "What";
  document_date: string;
  count: number;
  shown: number;
};

type StageBase = { found: boolean; reason: string | null; joined_on?: "key" | "together" };
export type Stage =
  | (StageBase & { stage: "plan"; records: PlanRecord[] })
  | (StageBase & { stage: "notice"; records: NoticeRecord[]; method?: string | null; market_approach?: string | null })
  | (StageBase & { stage: "bids"; records: AwardRecord[] })
  | (StageBase & { stage: "contract"; records: ContractRecord[] })
  | (StageBase & {
      stage: "paragraphs";
      records: ParagraphRecord[];
      // The reports the paragraphs come from, oldest first, each with how many it holds and how many show at first.
      groups: ParagraphGroup[];
      threshold: string;
      coverage?: { read: number; total: number; source_key: string } | null;
    });

export type LeadPart =
  | { kind: "estimated"; amount: string; currency: string; evidence_id: string }
  | { kind: "advertised"; date: string; evidence_id: string; reference: string }
  | { kind: "signed"; date: string; amount: string | null; currency: string | null; evidence_id: string; reference: string; record_noun: string }
  | { kind: "signed_many"; count: number; first_date: string; last_date: string; evidence_id: string };

export type Trail = {
  as_of: string;
  data_through: string | null;
  activity: {
    step_reference: string;
    project_id: string;
    project_name: string | null;
    display_name: string | null;
    description: string | null;
    method: string | null;
    consultants: boolean;
    implementing_agency: string | null;
    href: string;
  };
  moved: boolean;
  lead: {
    parts: LeadPart[];
    no_estimate: boolean;
    missing: "notice" | "contract" | "notice_and_contract" | null;
    // Each award notice's bids, in date order.
    bids: { count: number; notice_id: string; evidence_id: string; proposals: boolean }[];
    many_contracts: boolean;
    paragraphs: number | null;
  };
  stages: Stage[];
};

export type Chip = {
  evidence_id: string;
  passage_id: string;
  paragraph: string;
  paragraph_numbered: boolean;
  section_path: string;
  pdf_page: number | null;
  // What tells two chips of one document apart when they would read alike: a section, or a page.
  label_extra: { section?: string; page?: number } | null;
  packages: string[];
  package_count: number;
};
export type DocumentNode = {
  document_id: string;
  doc_key: string;
  type: string;
  document_type: string;
  document_date: string | null;
  short_name: string | null;
  sequence: number | null;
  agency: string | null;
  href: string;
  chips: Chip[];
  more_chips: number;
};
export type PackageNode = {
  step_reference: string;
  description: string | null;
  process_status: string | null;
  contracts: number;
  first_signed_on: string | null;
  date: string | null;
  href: string;
  linked: { evidence_id: string }[];
};
export type Neighbourhood = {
  as_of: string;
  data_through: string | null;
  scored_date: string | null;
  project: { project_id: string; display_name: string | null };
  packages: PackageNode[];
  documents: DocumentNode[];
  edges: { step_reference: string; evidence_id: string }[];
  // One dashed curve per package and document that appeared together, ending level with the first chip they share.
  lines: { step_reference: string; document_id: string; evidence_id: string | null; at_rest: boolean }[];
  lines_hint: boolean;
  more: { kind: string; count: number; unread: number }[];
  finding: {
    contracts: number;
    paragraphs: number;
    documents: number;
    contract_items: string[];
    paragraph_items: { short_name: string | null; document_type: string; paragraph: string; paragraph_numbered: boolean; section_path: string }[];
    document_items: { short_name: string | null; document_type: string; document_date: string | null }[];
  };
  // The project's contracts, as the Timeline tab counts them too (ticket 138): the finding names how many of them
  // appeared together with a paragraph.
  contracts: ContractsHeld;
  shown: number;
  total: number;
  threshold: string;
  coverage: { read: number; total: number; source_key: string };
};

export type Why = {
  reference: string;
  record_noun: string;
  signed_on: string | null;
  href: string | null;
  step_reference: string | null;
  topics: Topic[];
  project_id: string;
  project_state: "closed" | "active";
  document: { type: string; short_name: string | null; date: string | null };
  months: number | null;
  direction: "after" | "before" | "same" | null;
  components: { part: string; matched: unknown; points: string }[];
  score: string;
  threshold: string;
  mentions: { kind: string; code: string | null; text: string; start: number; end: number }[];
  activity_href: string | null;
  others: { reference: string; signed_on: string | null; href: string | null }[];
  others_count: number;
  others_more: number;
  connections_href: string;
};

// An amount as a sentence writes it, with its currency, to the cent as the record gives it, and with no cents
// when they are zero: "US$300,000", "US$1,245,092.76", "INR 69,826,127.64" (the 22 brief, section 2.7).
export function amountText(amount: string, currency: string | null): string {
  const value = Number(amount);
  const written = formatNumber(value, { decimals: Number.isInteger(value) ? 0 : 2, compact: false });
  return !currency || currency === "USD" ? copy.trail.usd(written) : copy.trail.otherCurrency(currency, written);
}

// An amount in a card or table, in STEP's form with its cents: 1,245,092.76.
export function amountCell(amount: string): string {
  return formatNumber(Number(amount), { decimals: 2, compact: false });
}

// A price as the award notice gives it, in STEP's form with its cents (DESIGN.md section 6): "61503269.60" is
// written "61,503,269.60", as "69,826,127.64" already is. The value never changes; text that is not a plain
// number stays as the notice writes it.
export function noticePrice(price: string | null): string | null {
  const text = price?.trim();
  if (!text) return null;
  const plain = text.replace(/,/g, "");
  return /^\d+(\.\d+)?$/.test(plain) && /^(\d{1,3}(,\d{3})*|\d+)(\.\d+)?$/.test(text) ? amountCell(plain) : text;
}

export function currencyName(code: string | null): string {
  return code ? (copy.trail.currencyName[code] ?? code) : "";
}

// STEP's step name in its short label, from the step-label registry (web/src/steps.ts), or STEP's own name.
export function stepLabel(stepName: string): string {
  for (const family of Object.values(stepFamilies)) {
    const found = family.steps.find((step) => step.step_name === stepName);
    if (found) return found.label;
  }
  return stepName;
}

// Items joined as a sentence joins them: "A", "A and B", "A, B and C", with no serial comma.
export function joinWords(items: string[], join: { pair: string; list: string; last: string }): string {
  if (items.length <= 1) return items.join("");
  if (items.length === 2) return items.join(join.pair);
  return items.slice(0, -1).join(join.list) + join.last + items[items.length - 1];
}

// What a link's paragraph and contract both concern, in words: the category phrase, the sector phrase, then the
// places and names as written.
export function topicWords(topics: Topic[]): string[] {
  return topics.map((topic) => {
    if (topic.kind === "category") return copy.why.category[topic.code ?? ""] ?? (topic.code ?? "").toLowerCase();
    if (topic.kind === "sector") return copy.why.sector[topic.code ?? ""] ?? (topic.name ?? topic.code ?? "").toLowerCase();
    return topic.text ?? "";
  });
}

// A section as a title or a chip names it: its own name ("Results"), or a bare number as "Section 4.1".
const SECTION_NUMBER = /^[0-9IVX]+(\.[0-9A-Za-z]+)*$/;
export function sectionName(section: string): string {
  return SECTION_NUMBER.test(section) ? copy.trail.sectionNumber.replace("{section}", section) : section;
}

export function countWord(count: number): string {
  return formatCount(count);
}

export function stage<K extends Stage["stage"]>(trail: Trail, key: K): Extract<Stage, { stage: K }> {
  return trail.stages.find((found) => found.stage === key) as Extract<Stage, { stage: K }>;
}
