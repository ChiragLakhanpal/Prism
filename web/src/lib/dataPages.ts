// The Data tab's two reads (the 16 design brief): GET /api/data/readiness, the data_readiness_for
// tool's answer as the viewer, and GET /api/data/sources, the source registry's datasets, which
// answers with the warehouse down. The shapes are config/tools.toml's [tools.data_readiness_for]
// and src/strata/tools/data_readiness_for.py's registry_page. The page computes no number: every
// count, sum and share arrives from the tool.
import { createStore } from "./store";
import { withPageParams } from "./view";

// A sentence's part: text, or a number with the result row it comes from, what it counts, and, when
// it is neither that row's count nor its denominator, what it is (a shortfall, or days late).
export type Segment =
  | { text: string }
  // An in-page link, such as "the hardest documents I read" to #hardest-documents (ticket 18).
  | { link: string; href: string }
  // Text set in mono, such as a project ID.
  | { mono: string }
  | {
      number: number;
      row: number | null;
      noun: string | null;
      noun_one?: string | null;
      role?: "missing" | "days" | null;
      // For a shortfall: what its records lack, so its tooltip can name them.
      lack?: string | null;
      // A check of what I found: what I found none of, which the tooltip says instead of what the records lack.
      not_found?: string | null;
    };

export type MeasureRow = {
  evidence_id: string;
  public_from: string;
  source: { table: string; source_key: string; measure: string; subjects: string[]; measured_on: string; counted_in: string | null };
  source_key: string;
  measure: string;
  kind: string;
  subjects: string[];
  count: number | null;
  denominator: number | null;
  // The share as the tool rounded it (data_readiness_for.share): a percent from 50 rows, about N in
  // 10 from 20, and whether a part rounds to an end of its scale.
  share_percent: number | null;
  share_bound: "under" | "over" | null;
  in_ten: number | null;
  in_ten_exact: boolean | null;
  as_of: string | null;
  measured_on: string;
  run_ids: string[];
};

export type Column = "coverage" | "linked" | "read_well" | "fresh";
export const COLUMNS: Column[] = ["coverage", "linked", "read_well", "fresh"];

export type Cell = {
  measure?: string | null;
  row?: number | null;
  counts?: string;
  counts_one?: string | null;
  noun?: string;
  noun_one?: string | null;
  status?: "partial" | "gap" | null;
  note?: string | null;
  years_row?: number | null;
  schedule?: string;
  late_days?: number | null;
  // The day the refresh was paused (config/thresholds.toml's ingestion.paused_since), in place of late_days (ticket 134).
  paused_since?: string | null;
  published_as_table?: boolean;
  // Ticket 18: a row whose records arrive as text; a document collection's projects, those its documents
  // belong to; and
  // its Read well share split by route for its window, the published text first.
  published_as_text?: boolean;
  projects_row?: number | null;
  // A document collection's pilot projects read, out of every pilot project (design review r2 B1).
  slice_row?: number | null;
  routes?: { route: "published_text" | "layout_parser"; row: number | null }[];
};

export type Scope =
  | { kind: "every_country" }
  | { kind: "countries"; names: string[] }
  | { kind: "projects"; count: number }
  // A document collection's slice, from the slice file (ticket 18), and whether the hardest documents,
  // whose projects are read too, show below.
  | { kind: "slice"; sectors: string[]; countries: string[]; first_fiscal_year: number; last_fiscal_year: number; shelf: boolean };

export type SourceRow =
  | {
      type: "measured" | "unmeasured";
      id: string;
      source_key: string;
      label: string;
      stratum: string;
      scope: Scope;
      covers: string | null;
      cells: Record<Column, Cell>;
    }
  | { type: "gap"; id: string; source_key: string; label: string; first_fiscal_year: number; last_fiscal_year: number; note: string };

// spell_out: the headline above doesn't spell STEP out, so the kind's count must (copy's countsSpelled).
export type Kind = {
  kind: string;
  tool: string;
  status: "ready" | "partial" | "gap";
  ready_for: number | null;
  holds_back: Segment[][];
  spell_out: boolean;
};

// row is the fix measure's result row; projects_row is the measure that counted its projects, or null
// when they are the measure's own projects that fall short.
export type Fix = {
  rank: number;
  gap: string;
  projects: number;
  row: number;
  projects_row: number | null;
  projects_from: "measure" | "subjects";
  sentence: Segment[];
};

export type Readiness = {
  tool: string;
  as_of: string;
  view: string;
  rows: MeasureRow[];
  abstention: null | { reason: "no_measures" | "before_first_measure" | "unknown_sources"; first_measured_on?: string };
  // shown counts the Sources table's rows in view, which the alert, the count line and the headline use.
  filter: { sources: string[] | null; unknown: number; from: string | null; shown: number; total: number };
  sources: SourceRow[];
  kinds: Kind[];
  // The gaps in view, biggest first; the page reads only whether there are any.
  gaps: { id: string; type: string; status: "partial" | "gap"; row_id: string; source_key: string; column: string | null; projects: number | null; phrase: Segment[] }[];
  fixes: Fix[];
  routes: { measure: string; label: string; noun: string; row: number }[];
  headline: { segments: Segment[]; text: string } | null;
  headline_abstention: null | { reason: "unmeasured"; unmeasured: number; sources: number };
  // null when the Procurement Plans' row is out of view.
  parse_failures: { project_id: string; document_id: string; pdf_page: number; failed_on: string }[] | null;
  measured: { first: string; last: string } | null;
  // Empty when a filtered view holds none of the shelf's sources, and then the section is left out.
  stress_shelf: ShelfEntry[];
};

// One entry of the stress shelf, "The hardest documents I read" (the 18 brief, section 4), in the
// slice file's order. Each number is a result row, so it opens its window. The server sets the badge.
export type ShelfEntry = {
  key: string;
  kind: "scan_annex" | "longest_pad" | "large_plan" | "other_language" | "over_parser_limit";
  // The slice file's rule that picks the document at run time, or null for an entry that names its document.
  rule: string | null;
  position: number;
  row_id: string;
  state: "read" | "stopped_at_cap" | "not_read" | "no_document";
  project_id: string | null;
  document: {
    document_id: string;
    project_id: string;
    project_name: string | null;
    document_type: string;
    document_date: string | null;
    pdf_pages: number | null;
    pdf_url: string | null;
    language: string | null;
  } | null;
  part: string | null;
  language: string | null;
  hard_page: number | null;
  parser_row: number | null;
  outcome_row: number | null;
  read_pages_row: number | null;
  longest_row: number | null;
  status: "partial" | "gap" | null;
  unreadable: boolean;
  denominator_from: "hand_count" | "pdf_pages" | "text_references" | "passages_made" | null;
  counted_on: string | null;
  parts: number | null;
  parser: string | null;
  parser_limit_pages: number | null;
  daily_page_cap: number | null;
  measured_on: string | null;
};

export type ReadinessState =
  | { status: "loading" }
  | { status: "ready"; result: Readiness }
  | { status: "error"; reason: "timeout" | "permission" | "other"; seconds?: number };

// The page's own address parts that the tool takes, passed on as they are: the server checks them,
// and the page never shows them.
const PASSED = ["sources", "from", "asof"];

export function readinessPath(search: string): string {
  const given = new URLSearchParams(search);
  const passed = new URLSearchParams();
  for (const name of PASSED) {
    const value = given.get(name);
    if (value !== null) passed.set(name, value);
  }
  const query = passed.toString();
  return `/api/data/readiness${query ? `?${query}` : ""}`;
}

export async function readReadiness(search: string, signal?: AbortSignal): Promise<ReadinessState> {
  try {
    const response = await fetch(withPageParams(readinessPath(search)), { headers: { Accept: "application/json" }, signal });
    const body = await response.json().catch(() => ({}));
    if (response.ok) return { status: "ready", result: body as Readiness };
    if (response.status === 504) return { status: "error", reason: "timeout", seconds: body.timeout_seconds };
    if (response.status === 401 || response.status === 403) return { status: "error", reason: "permission" };
    return { status: "error", reason: "other" };
  } catch (error) {
    if (signal?.aborted) throw error;
    return { status: "error", reason: "other" };
  }
}

export type Registry = {
  datasets: { key: string; dataset_name: string; data_source: string; catalog_url: string; name_checked: string; license: string }[];
  collections: { name: string; publisher: string; origin: string; language?: string }[];
  readiness_rows: number;
  known_gaps: number;
  kinds: number;
  fixes: number;
  // The stress shelf's entries in the slice file, so the loading state holds a row for each.
  shelf: number;
};

export type RegistryState = { status: "loading" } | { status: "ready"; registry: Registry } | { status: "error" };

// The registry is read once per page load and kept across the Data tab's pages.
export const registry = createStore<RegistryState>({ status: "loading" });
let asked = false;

export function readRegistry(again = false) {
  if (asked && !again) return;
  asked = true;
  registry.set({ status: "loading" });
  fetch("/api/data/sources", { headers: { Accept: "application/json" } })
    .then(async (response) => {
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      registry.set({ status: "ready", registry: (await response.json()) as Registry });
    })
    .catch(() => registry.set({ status: "error" }));
}
