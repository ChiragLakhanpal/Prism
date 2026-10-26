// Calls to Strata's server. Paths start with /api; in development Vite passes them on to the
// server, and in the Databricks App the server serves them itself. Each call carries the
// viewer's session through the App's proxy, so nothing here holds a token.

// The server's error body, when it sent one: a code such as "permission" or "data_service", and
// the reference (the request's trace id) that finds the details in the server's log.
export type ErrorBody = { code?: string; trace_id?: string };

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly path: string,
    readonly body: ErrorBody = {},
  ) {
    super(`${path} answered HTTP ${status}.`);
  }
}

async function call<T>(path: string, init: RequestInit): Promise<T> {
  const response = await fetch(path, { ...init, headers: { Accept: "application/json", ...init.headers } });
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as ErrorBody;
    throw new ApiError(response.status, path, body && typeof body === "object" ? body : {});
  }
  return (await response.json()) as T;
}

export function getJson<T>(path: string, init: { signal?: AbortSignal } = {}): Promise<T> {
  return call<T>(path, { method: "GET", signal: init.signal });
}

export function postJson<T>(path: string, body: unknown, init: { signal?: AbortSignal } = {}): Promise<T> {
  return call<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal: init.signal,
  });
}

// A write that replaces a record, such as saving the baseline (ticket 21).
export function putJson<T>(path: string, body: unknown): Promise<T> {
  return call<T>(path, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
}

export function deleteJson<T>(path: string): Promise<T> {
  return call<T>(path, { method: "DELETE" });
}

// GET /api/me: who the Databricks App says is viewing. The token never leaves the server.
// staff says whether the viewer has the World Bank staff role (ticket 37): Following and Follow are theirs.
export type Me = {
  email: string | null;
  name: string | null;
  signed_in: boolean;
  has_token: boolean;
  staff?: boolean;
  // Ticket 38: the implementing agency whose team the viewer is on, and the view the server applies to them.
  agency?: { name: string; agency_id: string } | null;
  own_view?: "staff" | "piu";
  // The language of answers and drafts in effect, and where it came from (ticket 42).
  language?: import("./lang").WorkingLanguage;
};

// One page of a list the server searches and pages (ticket 21): the rows shown, and the range and
// count the count line states, all the server's, so the screen counts nothing.
export type Paged<Row> = {
  as_of: string;
  query: string;
  total: number;
  page: number;
  pages: number;
  page_size: number;
  first: number;
  last: number;
  rows: Row[];
};

// GET /api/projects?q=&page=: every project Strata holds a record for, active ones first, then by name.
export type ProjectRow = { project_id: string; project_name: string; country: string | null; status: string | null };
export type ProjectList = Paged<ProjectRow> & { records_through: string | null };

// GET /api/projects/{pid}/packages?q=&page=: every activity in each agency's latest plan.
export type PackageRow = {
  activity_reference_no: string;
  description: string | null;
  implementing_agency: string;
  agency_id: string;
  plan_date: string;
  method: string | null;
  market_approach: string | null;
  estimated_amount_usd: string | null;
  process_status: string | null;
};
export type PackageList = Paged<PackageRow> & { read_through: string | null };

// GET /api/projects/{pid}: the project page's header and each agency's plan versions, newest first.
export type PlanVersion = {
  document_id: string;
  plan_date: string;
  disclosed_on: string | null;
  is_latest: boolean;
  read: boolean;
  activities: number | null;
  // Ticket 21: the version saved as the baseline, and whether it shows before "Show all".
  is_baseline?: boolean;
  shown?: boolean;
};

// The baseline of an agency's plans (ticket 21): who saved it is null outside the World Bank staff view.
export type Baseline = {
  plan_date: string;
  document_id: string;
  saved_by: string | null;
  saved_on: string;
  evidence_id: string;
  public_from: string;
};

export type ChangeKind = "added" | "dropped" | "redated" | "reestimated";
export type ChangeCounts = Record<ChangeKind, number>;
export type ChangeState = "compared" | "earliest" | "previous_not_read";

// version_count and shown_count are the route's counts, so the screen never counts them.
export type Agency = {
  implementing_agency: string;
  agency_id: string;
  versions: PlanVersion[];
  version_count: number;
  shown_count?: number;
  baseline?: Baseline | null;
  changes?: { state: ChangeState; previous_plan_date: string | null; counts: ChangeCounts | null } | null;
};
export type ProjectPage = {
  as_of: string;
  project: {
    project_id: string;
    project_name: string;
    // The header's name: the record's without a final "Project", as the server gives it.
    display_name?: string | null;
    country: string | null;
    status: string | null;
    implementing_agencies: string[];
  };
  agencies: Agency[];
  documents_through: string | null;
};

// GET /api/projects/{pid}/procurement/{agencyId}/{version}/changes: what changed since the version before.
export type ChangedActivity = {
  activity_reference_no: string;
  description: string | null;
  method: string | null;
  market_approach: string | null;
  estimated_amount_usd: string | null;
  process_status: string | null;
};
export type MovedStep = { step: string; was: string; now: string | null; days: number | null; direction: "later" | "earlier" | null };
export type PlanChanges = {
  as_of: string;
  state: ChangeState;
  plan: { document_id: string; plan_date: string; implementing_agency: string; agency_id: string };
  previous: { document_id: string; plan_date: string; implementing_agency: string; agency_id: string } | null;
  counts: ChangeCounts | null;
  added: ChangedActivity[];
  dropped: ChangedActivity[];
  redated: { activity_reference_no: string; description: string | null; steps: MovedStep[] }[];
  reestimated: { activity_reference_no: string; description: string | null; was: string; now: string; change: string; direction: "more" | "less" }[];
};

// GET /api/projects/{pid}/summary: every value the Summary shows, with its source, and each source as
// the evidence drawer shows it (src/strata/server/summary.py).
export type FactSource = {
  evidence_id: string | null;
  kind: "projects_api" | "loans" | "loan_history" | "isr" | "projects_api_ratings" | "icr" | "ieg_ratings";
  date: string | null;
  sequence?: number | null;
  fiscal_year?: number | null;
  loans?: number;
};
export type Fact = {
  key: string;
  value: string | null;
  values?: string[];
  loans?: { loan_number: string; value: string }[];
  loan_ids?: string[];
  source: FactSource;
};
export type Summary = {
  as_of: string;
  project: { project_id: string; project_name: string; display_name: string | null; status: string | null };
  lead: {
    kind: "closed" | "active" | "pipeline" | "dropped";
    closing_date: string | null;
    moves: number | null;
    commitment: string | null;
    disbursed: string | null;
    canceled: string | null;
    // Whether any amount was canceled, which the route decides, since "1,234.5" does not read as a number.
    any_canceled: boolean;
    // Whether the loans data reports more disbursed and canceled than committed, which the route decides.
    amounts_exceed_commitment: boolean;
    disbursed_as_of: string | null;
  };
  dates: Fact[];
  // The history's own source: the month the closing date last changed, or the history's first month.
  history: { known: boolean; rows: { first_recorded: string; before: string; after: string; source: FactSource }[]; source?: FactSource | null };
  money: Fact[];
  ratings: Fact[];
  who: Fact[];
  // Evidence events (web/src/lib/answer.ts), each source once.
  sources: import("./answer").EvidenceEvent[];
};

// GET /api/projects/{pid}/documents: every document listed for the project, by type.
export type DocumentGroupKey = "pad" | "project_paper" | "isr" | "procurement_plan" | "icr" | "icr_review" | "ppar" | "other";
export type ListedDocument = {
  document_id: string;
  type: DocumentGroupKey;
  document_type: string;
  document_date: string | null;
  disclosed_on: string | null;
  read: boolean;
  doc_key: string | null;
  pages_read: number | null;
  pdf_pages: number | null;
  partial: boolean;
  pdf_url: string | null;
  sequence: number | null;
  agency: string | null;
  language: string | null;
  reissue: { document_id: string; document_date: string | null; disclosed_on: string | null; doc_key: string | null; pdf_url: string | null } | null;
  shown: boolean;
};
export type DocumentList = {
  as_of: string;
  project: { project_id: string; display_name: string | null };
  // Whether the project is in the set whose documents I fetch: the projects config/slice.toml's criteria
  // select and the ones it names.
  in_document_set: boolean;
  groups: { type: DocumentGroupKey; count: number; shown_count: number; documents: ListedDocument[] }[];
  total: number;
  shown_total: number;
  documents_through: string | null;
};

// GET /api/projects/{pid}/documents/{doc}?page=&para=&passage=: one page of a document.
export type SourcePageAnswer = {
  as_of: string;
  state: "page" | "doc_unread" | "not_found" | "ambiguous" | "not_public";
  project: { project_id: string; display_name: string | null };
  asked: { page: number | null; para: string | null; passage: string | null };
  canonical?: string | null;
  ambiguous?: { type: DocumentGroupKey; count: number };
  disclosed_on?: string | null;
  document?: {
    document_id: string;
    doc_key: string | null;
    type: DocumentGroupKey;
    document_type: string;
    document_date: string | null;
    disclosed_on: string | null;
    pdf_pages: number | null;
    pdf_url: string | null;
    language: string | null;
    sequence: number | null;
    agency: string | null;
    replaces?: { doc_key: string | null; document_date: string | null } | null;
    replaced_by?: { doc_key: string | null; document_date: string | null } | null;
  };
  page?: number;
  correction?: { kind: "moved" | "no_para" | "page_range"; para: string | null; page: number } | null;
  highlight?: { passage_id: string; para: string | null } | null;
  page_state?: "read" | "unread" | "empty" | "front_matter";
  passages?: { passage_id: string; section_path: string | null; paragraph: string; numbered: boolean; part: number; language: string | null; text: string; from_page_before: boolean }[];
  tables?: { title: string | null; rows: { passage_id: string; row: number | null; cells: [string, string][] }[] }[];
  plan_rows?: { activity_reference_no: string; description: string | null; review_type: string | null; method: string | null; market_approach: string | null; estimated_amount_usd: string | null; actual_amount_usd: string | null; process_status: string | null }[];
  page_text?: string[] | null;
};

// GET /api/projects/{pid}/procurement/{agencyId}[/{version}]: check_plan's result
// (config/tools.toml, [tools.check_plan]). Every number the screen states is in it.
export type Mark = "needs_a_look" | "watch" | "data_note";
export type Reason = {
  code: string;
  mark: Mark;
  evidence_ids: string[];
  planned_completion_on?: string | null;
  planned_completion_plan_date?: string | null;
  closing_date?: string | null;
  days_to_close?: number | null;
  signed_on?: string | null;
  actual_amount_usd?: string | null;
  estimated_amount_usd?: string | null;
  ratio?: number | null;
  ratio_exact?: string | null;
  days_late?: number | null;
  planned_signing_on?: string | null;
  planned_signing_plan_date?: string | null;
  reference_method_code?: string | null;
  reference_method?: string | null;
  method?: string | null;
  process_status?: string | null;
  step?: string | null;
  // Ticket 21: the delay from the baseline, when one was saved, for a reason that states a delay.
  baseline?: {
    state: "late" | "early" | "on_date" | "past" | "ahead" | "not_in_baseline" | "no_date";
    planned_on: string | null;
    days: number | null;
    plan_date: string;
  };
};
export type Activity = {
  evidence_id: string;
  public_from: string;
  // An upload's row may have no reference yet (ticket 38); a published plan's always has one.
  activity_reference_no: string;
  // An upload's row: its place in the officer's file, and whether a published plan of the project lists it.
  position?: number | null;
  listed?: boolean | null;
  section: string | null;
  description: string | null;
  review_type: string | null;
  method: string | null;
  market_approach: string | null;
  estimated_amount_usd: string | null;
  actual_amount_usd: string | null;
  process_status: string | null;
  marks: { mark: Mark; reasons: Reason[] }[];
};
export type CheckPlanResult = {
  tool: "check_plan";
  as_of: string;
  view: string;
  rows: Activity[];
  abstention: {
    reason: string;
    implementing_agency?: string;
    agency_name?: string | null;
    agency_id?: string;
    plan_date?: string;
    latest_plan_date?: string | null;
    public_from?: string;
  } | null;
  plan: {
    document_id: string;
    project_id: string;
    implementing_agency: string;
    agency_id: string;
    plan_date: string;
    disclosed_on: string | null;
    public_from: string;
    is_latest: boolean;
    pdf_url: string | null;
  } | null;
  project: {
    project_id: string;
    project_name: string;
    // The name as the project's page header gives it, by the server's rule (the route adds it to the tool's row).
    display_name?: string | null;
    status: string | null;
    closing_date: string | null;
    record_date: string | null;
    days_to_close: number | null;
  } | null;
  checks_run: string[];
  thresholds: { completion_passed_min_estimated_usd: string; days_before_closing: number; actual_to_estimate_ratio: string };
  counts: {
    activities: number;
    checked: number;
    not_fully_checked: number;
    needs_a_look: number;
    watch: number;
    data_note: number;
    // The activities with a signal (needs a look or watch): the rows a draft of review notes covers.
    signal: number;
    marked: number;
    unmarked: number;
  } | null;
  // Ticket 21: the baseline saved for this agency's plans, as the view may see it.
  baseline?: Baseline | null;
};

// A package as its newest public Procurement Plan row states it (find_comparables' package field,
// and GET /api/packages/{stepRef}).
export type PackageFacts = {
  evidence_id: string;
  public_from: string;
  step_reference: string;
  description: string | null;
  project_id: string;
  project_name: string | null;
  country_code: string | null;
  country_name: string | null;
  section: string | null;
  category: string | null;
  method: string | null;
  market_approach: string | null;
  review_type: string | null;
  estimated_amount_usd: string | null;
  process_status: string | null;
  planned_notice_on: string | null;
  planned_signing_on: string | null;
  plan: {
    document_id: string;
    implementing_agency: string;
    agency_id: string;
    plan_date: string;
    disclosed_on: string | null;
    pdf_page: number;
  };
};

// GET /api/packages/{stepRef}: the package workspace's header.
export type PackageResult = { as_of: string; package: PackageFacts };

// ── The time estimate (ticket 26) ──
// GET /api/packages/{stepRef}/estimate and GET /api/planned-packages/{id}/estimate: estimate_time's result
// (config/tools.toml, [tools.estimate_time]) and the viewer's saved plan-date choice. Every figure is the tool's;
// a comparison, a plan-date choice and section 4 render from this one answer, with no request.
export type EstimatePoints = { q25: number; q50: number; q75: number; q80: number };
export type EstimateAbstention =
  | { reason: "too_few_comparables"; count: number; min_comparables: number }
  | { reason: "outside_training"; feature: string; value: number; low: number; high: number }
  | { reason: "asof_before_training"; as_of: string }
  | { reason: "no_model" }
  | { reason: "unknown_package" | "no_public_notice" | "no_comparables" | "none_measurable"; [key: string]: unknown };
// Why a comparison, an approach or a combination has no time estimate.
export type CellAbstention =
  | { reason: "too_few_in_subgroup"; k: number; n: number; min_subgroup: number }
  | { reason: "not_in_model"; lever: string }
  | { reason: "outside_training" | "value_not_learned"; [key: string]: unknown };
export type Lever = "market_approach" | "lots" | "prequalification";
export type Comparison = {
  lever: Lever;
  value: string | number;
  own: string | number;
  k: number;
  rest: number;
  n: number;
  matching_ids: string[];
  // Comparable packages whose records give no value for the lever, counted among the others.
  unrecorded_ids: string[];
  estimate: (EstimatePoints & { days: EstimatePoints }) | null;
  abstention: CellAbstention | null;
};
export type Approach = {
  market_approach: string;
  lots: number;
  prequalification: string;
  k: number;
  // The comparable packages that went with it, which its count opens in the evidence drawer.
  matching_ids: string[];
  is_as_described: boolean;
  estimate: (EstimatePoints & { days: EstimatePoints }) | null;
  abstention: CellAbstention | null;
};
export type TrackRecord =
  | {
      year: number;
      n: number;
      m: number;
      expected: number;
      misses: number;
      misses_early: number | null;
      misses_late: number | null;
      ran_on: string | null;
      mlflow_run_id: string | null;
      abstention: null;
    }
  | { year: number; abstention: { reason: "too_few_unseen_packages"; n: number; min_unseen_packages: number } }
  // The viewer can't read strata.ops, so the backtest results may exist unread.
  | { year: null; abstention: { reason: "not_readable" } };
export type TestYear = {
  year: number;
  n: number | null;
  m: number | null;
  expected: number | null;
  error_estimate_months: number | null;
  error_past_range_months: number | null;
  error_plan_months: number | null;
  mlflow_run_id: string | null;
  abstention: string | null;
};
export type PlanDatePoint = { months: number; ran_longer: number | null; total: number | null; in10: number | null };
export type PlanDateChoice = "middle" | "eight_in_ten";
export type EstimateResult = {
  tool: "estimate_time";
  as_of: string;
  view: string;
  rows: {
    evidence_id: string;
    as_described: boolean;
    market_approach: string | null;
    prequalification: string | null;
    review_type: string | null;
    q25: number | null;
    q50: number | null;
    q75: number | null;
    q80: number | null;
    abstention: string | null;
  }[];
  abstention: EstimateAbstention | null;
  package: {
    step_reference: string | null;
    described: {
      market_approach: string | null;
      prequalification: string | null;
      lots: number | null;
      review_type: string | null;
      estimated_amount_usd: number | null;
      category: string | null;
      method: string | null;
      country_code: string | null;
    } | null;
  };
  comparables: { n: number; signed: number; still_open: number };
  estimate:
    | (EstimatePoints & {
        days: EstimatePoints;
        model: string;
        model_version: number;
        model_alias: string;
        training_through: string;
        scored_on: string;
        scored: "batch" | "request";
      })
    | null;
  difference: {
    middle_diff_months: number;
    direction: "later" | "earlier" | "same";
    reasons: { code: "size_larger" | "size_smaller"; k: number; n: number }[];
  } | null;
  track_record: TrackRecord | null;
  test_years: TestYear[];
  plan_dates: { middle: PlanDatePoint; eight_in_ten: PlanDatePoint; default: PlanDateChoice } | null;
  comparisons: Comparison[];
  // Section 4's counts, each the tool's: those whose records give the whole approach, those of them the thresholds
  // rule out for this package, and those whose records don't give it.
  options: {
    approaches: Approach[];
    count: number;
    recorded: number;
    ruled_out: number;
    unrecorded: number;
    n: number;
    review_type: string | null;
  } | null;
  axis_max_months: number | null;
  thresholds: { min_comparables: number; min_subgroup: number; min_unseen_packages: number };
  sources: { key: string; dataset_name: string }[];
  records_through: string | null;
  plan_date_choice: PlanDateChoice | null;
};

// One comparable package (config/tools.toml, [tools.find_comparables.result]).
export type Comparable = {
  evidence_id: string;
  public_from: string;
  source: { project_id: string; notice_id: string; contract_id: string | null; award_notice_id: string | null; signed_in: string | null };
  step_reference: string;
  project_id: string;
  country_code: string | null;
  country_name: string | null;
  notice_id: string;
  notice_date: string;
  signed_on: string | null;
  still_open: boolean;
  days: number;
  months: number;
  rank: number;
};

export type CoverageReason =
  | "no_step_reference"
  | "no_notice"
  | "canceled"
  | "signed_before_notice"
  | "no_review_type"
  | "no_market_approach"
  | "no_amount";

// GET /api/packages/{stepRef}/comparables: find_comparables' result. Every number the section
// states is in it, except the plan line's readout, which counts its rows.
// A quantile dot (ticket 12), with the packages it stands for, how many of them are still open, and their
// shortest and longest months, as find_comparables gives them (ticket 15: a dot opens the drawer at them).
export type QuantileDot = {
  k: number;
  days: number;
  months: number;
  reached: boolean;
  step_references: string[];
  count: number;
  still_open: number;
  low_months: number;
  high_months: number;
};

export type ComparablesResult = {
  tool: "find_comparables";
  as_of: string;
  view: string;
  rows: Comparable[];
  coverage: { matched: number; used: number; not_used: { reason: CoverageReason; count: number; evidence_ids: string[] }[] };
  abstention:
    | { reason: "too_few_comparables"; count: number; min_comparables: number }
    | { reason: "no_public_notice"; field: string; value: string }
    | { reason: "no_comparables" | "none_measurable"; matched: number }
    | { reason: "unknown_package"; step_reference: string }
    | null;
  package: PackageFacts | null;
  criteria: {
    method: string | null;
    category: string | null;
    market_approach: string | null;
    review_type: string | null;
    country: string | null;
    country_name: string | null;
    notice_from: string;
    notice_to: string;
    size_from_usd: number | null;
    size_to_usd: number | null;
    from_package: string[];
  } | null;
  counts: { comparables: number; signed: number; still_open: number; canceled: number; canceled_as_still_open: boolean } | null;
  past_range: { q25: number | null; q50: number | null; q75: number | null; q80: number | null } | null;
  plan: {
    days: number;
    months: number;
    planned_notice_on: string;
    planned_signing_on: string;
    plan_date: string;
    within: number;
    in10: number | null;
  } | null;
  quantile_dots: QuantileDot[] | null;
  // The numbers each "in 10" phrase states, and the words that go with the plan's share, as the tool
  // decided them: the screen picks its title from these words and never works them out again.
  frequencies: {
    q80: [number, number] | null;
    plan: { words: "fewer_than" | "about" | "more_than"; states: [number, number] } | null;
  } | null;
  thresholds: { min_comparables: number; quantile_dots_above: number; quantile_dots: number; max_plan_months: number; canceled_as_still_open: boolean };
  sources: { key: string; dataset_name: string }[];
  records_through: string | null;
};
