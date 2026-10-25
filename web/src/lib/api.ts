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

export function putJson<T>(path: string, body: unknown, init: { signal?: AbortSignal } = {}): Promise<T> {
  return call<T>(path, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal: init.signal,
  });
}

// GET /api/me: who the Databricks App says is viewing. The token never leaves the server.
export type Me = { email: string | null; name: string | null; signed_in: boolean; has_token: boolean };

// GET /api/projects: every project Strata holds a record for, active ones first, then by name.
export type ProjectRow = { project_id: string; project_name: string; country: string | null; status: string | null };
export type ProjectList = { as_of: string; total: number; rows: ProjectRow[]; records_through: string | null };

// GET /api/projects/{pid}: the project page's header and each agency's plan versions, newest first.
export type PlanVersion = {
  document_id: string;
  plan_date: string;
  disclosed_on: string | null;
  is_latest: boolean;
  read: boolean;
  activities: number | null;
};
// version_count is the route's count of the versions, so the screen never counts them.
export type Agency = { implementing_agency: string; agency_id: string; versions: PlanVersion[]; version_count: number };
export type ProjectPage = {
  as_of: string;
  project: { project_id: string; project_name: string; country: string | null; status: string | null; implementing_agencies: string[] };
  agencies: Agency[];
  documents_through: string | null;
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
};
export type Activity = {
  evidence_id: string;
  public_from: string;
  activity_reference_no: string;
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
