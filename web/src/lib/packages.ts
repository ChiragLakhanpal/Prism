// Packages planned from a sentence, in the browser (ticket 15): the shapes the planned package routes answer
// with (src/strata/server/packages.py), the planning stream, what the reading page hands the package's page,
// the box's modes, and opening a comparable in the evidence drawer. Every value a chip shows comes from the
// server; the browser only writes it in words, through the package form schema the server hands it.
import { useCallback } from "react";
import type { EvidenceEvent } from "./answer";
import type { ComparablesResult, Comparable, QuantileDot } from "./api";
import { postJson } from "./api";
import { closeEvidence, evidenceIn, known, openEvidence, origin, remember } from "./evidence";
import { address } from "./router";
import { streamEvents, StreamError } from "./sse";
import { createStore, useStore } from "./store";

// unlisted: the sentence named a value the form does not list, such as a method STEP has no name for, so the field
// took its default, and read_as keeps the sentence's words (ticket 15's verification round 3, V4).
export type Provenance = "sentence" | "default" | "unlisted" | "guess" | "computed" | "you";

export type FormGroup = { key: string; label: string; name: string };
export type FormOption = { value: string; label: string };
export type FormField = {
  key: string;
  group: string;
  kind: "choice" | "text" | "amount" | "count" | "country" | "months";
  source: "typed" | "computed" | "guessed";
  label: string;
  add_label: string;
  step_field: string | null;
  picks: string | null;
  default: string | null;
  options: FormOption[];
  rule: "review" | "market_approach" | null;
  optional: boolean;
  unit: string | null;
  unit_one: string | null;
  aliases: boolean;
};
export type PackageForm = {
  groups: FormGroup[];
  fields: FormField[];
  countries: { code: string; name: string }[];
  // Old method names by their upper-case spelling, and what each is now (strata.lakehouse.clean).
  aliases: Record<string, { method: string; market_approach: string | null }>;
  // The limits a person's values must keep, each defined once in the server (src/strata/packages/form.py).
  max_months: number;
  max_count: number;
  text_limit: number;
};

export type FieldValue = {
  key: string;
  group: string;
  value: string | number | null;
  provenance: Provenance | null;
  // What the thresholds give a computed field, whether or not the person set it themselves.
  computed: string | null;
  // The sentence's own words for a value the form does not list; only an unlisted value has them.
  read_as?: string | null;
};

// A rule's source, and the date of the table it was checked against, which is null until the owner checks it.
export type ReviewRule = { category: string; threshold_usd: number; risk_rating: string; source: string; as_of: string | null };
export type MarketRule = { country: string; category: string; threshold_usd: number; source: string; as_of: string | null };

export type PlannedPackage = {
  package_id: string;
  sentence: string;
  step_reference: string | null;
  created_at: string;
  saved_at: string;
  plan_before_range: boolean | null;
  fields: FieldValue[];
  guesses: number;
  rules: { review?: ReviewRule; market_approach?: MarketRule };
  // A computed value a change recomputed: to is null when the thresholds give no value any more.
  changed: { field: string; from: string; to: string | null; cause: string }[];
  refusal: "dividing" | null;
  approximate: boolean;
  comparables_query: Record<string, string> | null;
  missing: string[];
};

// example: the seed command planned it for you (ticket 41).
export type PlannedPage = { package: PlannedPackage; form: PackageForm; example?: boolean };

export type PlannedRow =
  | {
      type: "package";
      package_id: string;
      description: string | null;
      country: string | null;
      country_name: string | null;
      step_reference: string | null;
      project_id: string | null;
      guesses: number;
      last_worked_on: string;
      // A package the seed command planned for you (ticket 41), labeled "Example".
      example?: boolean;
    }
  | {
      type: "plan_check";
      project_id: string;
      agency_id: string;
      implementing_agency: string | null;
      plan_date: string;
      latest: boolean;
      activities: number | null;
      country_name: null;
      last_worked_on: string;
    };
export type PlannedList = { rows: PlannedRow[]; counts: { packages: number; plan_checks: number; total: number } };

export type Change = {
  field: string;
  action: "set" | "remove" | "keep" | "use_computed";
  value?: string | number | null;
  plan_before_range?: boolean;
};

export const valueOf = (pkg: PlannedPackage, key: string) => pkg.fields.find((field) => field.key === key)?.value ?? null;

// GET /api/comparables for a package's criteria, as find_comparables takes them.
export function comparablesPath(query: Record<string, string>): string {
  const params = new URLSearchParams(Object.entries(query).sort(([a], [b]) => a.localeCompare(b)));
  return `/api/comparables?${params.toString()}`;
}

export function savePackage(packageId: string, change: Change): Promise<{ package: PlannedPackage }> {
  return postJson(`/api/planned-packages/${encodeURIComponent(packageId)}`, change);
}

// ── Planning: the stream, which outlives the reading page ───────────────

export type PlanStep = { id: string; status: "running" | "done" | "failed"; count?: number; guesses?: number };

export type Planning = {
  // A key per planning, so a page knows the stream it shows is its own.
  key: string;
  sentence: string;
  read: boolean;
  phase: "reading" | "saved" | "done" | "failed" | "no_package" | "dropped";
  steps: PlanStep[];
  error: string | null;
  // The package form schema, which the stream sends first, so the card can draw its groups.
  form: PackageForm | null;
  packageId: string | null;
  package: PlannedPackage | null;
  // find_comparables' result for the new package, once the workflow's last step returns it.
  comparables: ComparablesResult | null;
  // Whether the workflow's comparables step ended, with or without a result.
  compared: boolean;
};

export const planning = createStore<Planning | null>(null);
// A package's page, handed over once by the reading page that saved it, so the package's page renders at once,
// with whether the reading page's h1 had focus, so the new h1 takes it (focus never moves when the reading
// finishes). The package's page takes it out, so a later visit reads the package as it is then.
export type Handed = PlannedPage & { focusHeading: boolean };
export const preloaded = createStore<Record<string, Handed>>({});

let controller: AbortController | null = null;
const newKey = () => Math.random().toString(36).slice(2, 10);

function update(key: string, change: (now: Planning) => Planning) {
  planning.set((now) => (now && now.key === key ? change(now) : now));
}

export function startPlanning(sentence: string, read = true): string {
  controller?.abort();
  controller = new AbortController();
  const key = newKey();
  planning.set({
    key, sentence, read, phase: "reading", steps: [], error: null, form: null, packageId: null, package: null, comparables: null,
    compared: false,
  });
  const signal = controller.signal;
  void (async () => {
    try {
      for await (const event of streamEvents("/api/planned-packages", { sentence, read }, { signal })) {
        const data = event.data as Record<string, unknown>;
        if (event.type === "form") {
          update(key, (now) => ({ ...now, form: data.form as PackageForm }));
        } else if (event.type === "step") {
          const step = data as unknown as PlanStep;
          // A compare step that is done still has its comparables event to come, so only one that failed ends the
          // wait; otherwise the page would read the comparables a second time (ticket 15's verification round 3, V2).
          update(key, (now) => ({
            ...now,
            steps: [...now.steps.filter((one) => one.id !== step.id), step],
            compared: now.compared || (step.id === "compare" && step.status === "failed"),
          }));
        } else if (event.type === "package") {
          const pkg = data.package as PlannedPackage;
          update(key, (now) => ({ ...now, phase: "saved", packageId: pkg.package_id, package: pkg }));
        } else if (event.type === "comparables") {
          update(key, (now) => ({ ...now, comparables: data.result as ComparablesResult, compared: true }));
        } else if (event.type === "error") {
          const code = String(data.code ?? "internal");
          update(key, (now) => ({ ...now, phase: code === "no_package" ? "no_package" : "failed", error: code }));
        } else if (event.type === "done") {
          update(key, (now) => ({ ...now, phase: now.phase === "saved" ? "done" : now.phase, compared: true }));
        }
      }
      update(key, (now) => (now.phase === "reading" ? { ...now, phase: "dropped" } : { ...now, compared: true }));
    } catch (error) {
      if (signal.aborted) return;
      const code = error instanceof StreamError ? String(error.body?.code ?? "internal") : null;
      update(key, (now) =>
        now.packageId ? { ...now, compared: true } : { ...now, phase: code ? "failed" : "dropped", error: code ?? now.error },
      );
    }
  })();
  return key;
}

// ── The box's modes ─────────────────────────────────────────────────────

// The Packages tab's buttons put the one box into a mode and move focus there (the 15 brief, section 7.1):
// plan, which lists "Plan a package from this sentence" first, or check, which lists each agency's latest plan
// for a project ID. Escape or leaving the box ends the mode. text fills the box, as "Change the sentence" does.
export type BoxMode = { mode: "plan" | "check"; text?: string; at: number } | null;
export const boxMode = createStore<BoxMode>(null);

export function enterBoxMode(mode: "plan" | "check", text?: string) {
  boxMode.set({ mode, text, at: Date.now() });
}

// ── Opening a comparable in the evidence drawer ──────────────────────────

export const COMPARABLE = "strata.gold.package:";
// The evidence ids of the comparable packages the past range on this page counts (ticket 101), so the drawer
// says a package is "in the past range" only when it is. A project's timeline opens the same kind of record for
// a contract mark, and that page has no past range.
export const rangeIds = createStore<string[]>([]);
// The criteria find_comparables used for that past range, so the drawer's "Why I compared it" lists only those it
// used, and none it left out, such as a planned package's market approach and review type (ticket 60). Null with no
// past range on the page: the drawer then lists all five.
export const rangeCriteria = createStore<ComparablesResult["criteria"]>(null);
// A quantile dot's list of the packages it stands for, by the dot's number. It is no source: the page that
// draws the dots holds the list (rememberDots), so the drawer never asks the server for it.
export const DOT = "comparables-dot:";

export type OpenComparable = {
  onOpen: (row: Comparable, element: HTMLElement) => void;
  onOpenDot: (dot: QuantileDot, element: HTMLElement) => void;
  // The opened mark's key: a package's STEP reference, or dot-{k} for a quantile dot whose list, or one of
  // whose packages, the drawer shows.
  opened: string | null;
};

export type DotEntry = { step_reference: string; evidence_id: string; months: number; still_open: boolean };

// A quantile dot's list as the drawer shows it: the dot, the comparables' count, and each package it stands for
// with its months, from the rows find_comparables returned with it.
export function dotList(result: ComparablesResult, dot: QuantileDot): EvidenceEvent {
  const rows = new Map(result.rows.map((row) => [row.step_reference, row]));
  const entries: DotEntry[] = dot.step_references.flatMap((reference) => {
    const row = rows.get(reference);
    return row ? [{ step_reference: reference, evidence_id: row.evidence_id, months: row.months, still_open: row.still_open }] : [];
  });
  return {
    id: `${DOT}${dot.k}`,
    kind: "dot",
    tool: "find_comparables",
    stratum: "What",
    short_name: null,
    row: { ...dot, total: result.counts?.comparables ?? result.rows.length, entries },
    highlights: [],
  };
}

// Hold each quantile dot's list, so a dot opens its list at once and a link to a list reopens it once the dots
// are drawn again. A rerun's dots replace the earlier ones.
export function rememberDots(result: ComparablesResult) {
  for (const dot of result.quantile_dots ?? []) remember(dotList(result, dot));
}

// The drawer open at a dot's list these comparables have no dots for, as from a link: close it, since no
// list will come. A "went with" list waits for its time estimate instead.
export function forgetDotList() {
  const id = evidenceIn(address.get().search);
  if (id?.startsWith(DOT) && !id.startsWith(WENT_WITH) && !known.get()[id]) closeEvidence();
}

// The packages a "{k} of {n} went with" count names (ticket 26; the 26 brief, section 4.5): the drawer's list view,
// held by the page under the dots' prefix, so the drawer asks the server for nothing and gives focus back to the
// count. Each package opens its records from the list, with "Back to the {k} packages" above them.
export const WENT_WITH = `${DOT}with-`;

// What a list is of: the packages a comparison's count names, or (section 4) an approach's.
export type WentWith = { key: string; k: number; n: number; matching_ids: string[] };

export function wentWithList(result: ComparablesResult, comparison: WentWith, option: string): EvidenceEvent {
  const rows = new Map(result.rows.map((row) => [row.step_reference, row]));
  const entries: DotEntry[] = comparison.matching_ids.flatMap((reference) => {
    const row = rows.get(reference);
    return row ? [{ step_reference: reference, evidence_id: row.evidence_id, months: row.months, still_open: row.still_open }] : [];
  });
  const months = entries.map((entry) => entry.months);
  return {
    id: `${WENT_WITH}${comparison.key}`,
    kind: "dot",
    tool: "estimate_time",
    stratum: "What",
    short_name: null,
    row: {
      k: comparison.k,
      count: entries.length,
      total: comparison.n,
      went_with: option,
      still_open: entries.filter((entry) => entry.still_open).length,
      low_months: months.length ? Math.min(...months) : 0,
      high_months: months.length ? Math.max(...months) : 0,
      step_references: comparison.matching_ids,
      entries,
    },
    highlights: [],
  };
}

// A package's own plan row in the evidence drawer, from the side panel's marker, the facts line's "Show the plan row"
// or the plan's months in the finding (ticket 101): focus goes back to the element that opened it.
export function openPlanRow(evidenceId: string, element: HTMLElement) {
  openEvidence(evidenceId, { serial: null, sentence: null, marker: element, runId: null });
}

export function openWentWith(result: ComparablesResult, comparison: WentWith, option: string, element: HTMLElement) {
  const list = wentWithList(result, comparison, option);
  remember(list);
  openEvidence(list.id, { serial: null, sentence: null, marker: element, runId: null, fallback: headingOf(element) });
}

// A dot or a table row opens its comparable package's records in the evidence drawer, through the address's
// ?evidence= (ticket 14's parameter), and the drawer gives focus back to the element that opened it, or to
// section 1's heading when a rerun has redrawn that element away. A quantile dot opens the list of the
// packages it stands for, and each of them opens its records from there (the 15 brief, section 6).
export function useOpenComparable(): OpenComparable {
  const here = useStore(address);
  const from = useStore(origin);
  const id = evidenceIn(here.search);
  const onOpen = useCallback((row: Comparable, element: HTMLElement) => {
    openEvidence(row.evidence_id, { serial: null, sentence: null, marker: element, runId: null, fallback: headingOf(element) });
  }, []);
  const onOpenDot = useCallback((dot: QuantileDot, element: HTMLElement) => {
    openEvidence(`${DOT}${dot.k}`, { serial: null, sentence: null, marker: element, runId: null, fallback: headingOf(element) });
  }, []);
  let opened: string | null = null;
  if (id?.startsWith(DOT)) opened = `dot-${id.slice(DOT.length)}`;
  else if (id?.startsWith(COMPARABLE)) opened = from?.list ? `dot-${from.list.id.slice(DOT.length)}` : id.slice(COMPARABLE.length);
  return { onOpen, onOpenDot, opened };
}

const headingOf = (element: HTMLElement) => element.closest("[data-past-range]")?.querySelector<HTMLElement>("h2") ?? null;
