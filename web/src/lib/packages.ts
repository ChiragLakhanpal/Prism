// Packages planned from a sentence, in the browser (ticket 15): the shapes the planned package routes answer
// with (src/strata/server/packages.py), the planning stream, what the reading page hands the package's page,
// the box's modes, and opening a comparable in the evidence drawer. Every value a chip shows comes from the
// server; the browser only writes it in words, through the package form schema the server hands it.
import { useCallback } from "react";
import type { ComparablesResult, Comparable } from "./api";
import { postJson } from "./api";
import { evidenceIn, openEvidence } from "./evidence";
import { address } from "./router";
import { streamEvents, StreamError } from "./sse";
import { createStore, useStore } from "./store";

export type Provenance = "sentence" | "default" | "guess" | "computed" | "you";

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
  max_months: number;
};

export type FieldValue = {
  key: string;
  group: string;
  value: string | number | null;
  provenance: Provenance | null;
  // What the thresholds give a computed field, whether or not the person set it themselves.
  computed: string | null;
};

export type ReviewRule = { category: string; threshold_usd: number; risk_rating: string; source: string; as_of: string };
export type MarketRule = { country: string; category: string; threshold_usd: number; source: string; as_of: string };

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
  changed: { field: string; from: string; to: string; cause: string }[];
  refusal: "dividing" | null;
  approximate: boolean;
  comparables_query: Record<string, string> | null;
  missing: string[];
};

export type PlannedPage = { package: PlannedPackage; form: PackageForm };

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
          update(key, (now) => ({
            ...now,
            steps: [...now.steps.filter((one) => one.id !== step.id), step],
            compared: now.compared || (step.id === "compare" && step.status !== "running"),
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

export type OpenComparable = { onOpen: (row: Comparable, element: HTMLElement) => void; opened: string | null };

// A dot or a table row opens its comparable package's records in the evidence drawer, through the address's
// ?evidence= (ticket 14's parameter), and the drawer gives focus back to the element that opened it.
export function useOpenComparable(): OpenComparable {
  const here = useStore(address);
  const id = evidenceIn(here.search);
  const onOpen = useCallback((row: Comparable, element: HTMLElement) => {
    openEvidence(row.evidence_id, { serial: null, sentence: null, marker: element, runId: null });
  }, []);
  return { onOpen, opened: id && id.startsWith(COMPARABLE) ? id.slice(COMPARABLE.length) : null };
}
