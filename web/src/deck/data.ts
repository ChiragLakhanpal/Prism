// The deck's data (ticket 47; the 47 brief, sections 6 and 9.1): one JSON file the built app serves at
// /deck/data.json, written by `python -m strata.proposal deck` (src/strata/proposal/deck.py) from the dated measures
// snapshot the proposal cites, the registries and the demo package's recorded answers. The deck never queries the
// warehouse, so it opens in a cold demo, and it never computes a number: each one arrives here as a tool or a query
// returned it.
import type { ComparablesResult, EstimateResult } from "../lib/api";

export type DeckResult = {
  measured: boolean;
  // What the results register (docs/proposal/results.toml) says the result is.
  name: string;
  kind: string;
  noun: string;
  table: string;
  measured_on?: string;
  run_id?: string;
  n?: number;
  d?: number;
  value?: number;
  low?: number;
  high?: number;
  level?: number;
  budget?: number;
  latest?: string;
  period?: string;
  series?: Record<string, string | number | null>[];
};

export type DeckSetting = { value: number; name: string; where: string; kind: "Count" | "Setting" };

export type DeckData = {
  pulled_on: string | null;
  results: Record<string, DeckResult>;
  settings: Record<string, DeckSetting>;
  checks: number[];
  rubric: { source: string; anchor: string; dimensions: { key: string; name: string; points: number }[] };
  urls: { app: string | null; dashboard: string | null; repo: string | null; deck: string | null; proposal: string | null };
  presenter: { name: string | null; date: string | null };
  designed_not_built: { key: string; name: string; route: string }[];
  // The demo package, its project and its plan's address (config/slice.toml [demo_plan]), and its recorded answers.
  // The second draft adds the plan's date, the Start here links the demo slides open
  // (config/examples.toml, filled as Home fills them), the sentence the package demo types into the box, and the
  // question the answer demo asks (the demo-ready command's smoke question in evals/benchmark.yaml).
  demo: {
    step_reference: string;
    project_id: string;
    agency: string;
    plan_date?: string;
    plan_href: string;
    links?: Partial<Record<"checkPlan" | "planPackage" | "wholeStory", string>>;
    sentence?: string;
    question?: string;
    comparables: ComparablesResult | null;
    estimate: EstimateResult | null;
  };
  // The showcase project (config/slice.toml [showcase]), whose disagreement the ladder slide quotes.
  showcase: { project_id: string };
  award_gap: { start: number; end: number } | null;
};

export const DECK_DATA = "/deck/data.json";

export async function loadDeck(): Promise<DeckData> {
  const response = await fetch(DECK_DATA, { headers: { Accept: "application/json" } });
  if (!response.ok) throw new Error(String(response.status));
  return (await response.json()) as DeckData;
}

// A result the snapshot measured, or null, so a slide shows its "not measured yet" words instead.
export function measured(data: DeckData, key: string): DeckResult | null {
  const found = data.results[key];
  return found?.measured ? found : null;
}
