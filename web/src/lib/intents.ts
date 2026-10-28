// The one box's intent rules (the 14 brief, section 4.3): what Enter will do with what you typed. They
// run in the browser on every keystroke, so the list changes within 100 ms; a rule that needs a record
// to know where to go looks it up in the background, and the lookup fills in the option's second line.
//
// This is the one place the box learns a new kind of input (CLAUDE.md rule 9). Each rule says how to
// recognize its kind in the whole input and inside free text, how to look it up, and where choosing it
// goes. Ticket 15 adds "Plan a package from this sentence"; "Check this plan" comes later. Anything no
// rule recognizes offers "Ask this", and nothing is sent until the person chooses.
import { copy } from "../copy";
import { ApiError, getJson } from "./api";
import { createStore } from "./store";

export type Found =
  // plans: each implementing agency's latest published plan that I read, for the box's check mode (ticket 15).
  | { kind: "project"; pcode: string; name: string; country: string | null; plans?: { agency: string; agencyId: string; planDate: string }[] }
  | { kind: "loan"; loan: string; pcode: string; name: string | null }
  | { kind: "activity"; stepRef: string; pcode: string; agency: string; agencyId: string; planDate: string; isLatest: boolean };

export type Intent = {
  kind: Found["kind"];
  // The ID as the option shows it: P130164, IDA-60290 or a STEP reference.
  id: string;
  // What the lookup asks the server for.
  query: string;
  // A bare number may be any lender's loan, so its option shows only once the lookup finds one.
  needsLookup?: boolean;
};

// What a lookup came back with. "missing" is a record that does not exist; "failed" is a lookup that
// could not run.
export type Lookup = { status: "pending" } | { status: "found"; found: Found } | { status: "missing" } | { status: "failed" };

type Rule = {
  kind: Intent["kind"];
  // The intent when the whole input, trimmed, is this kind of ID.
  whole: (text: string) => Intent | null;
  // Each ID of this kind inside free text.
  within: (text: string) => Intent[];
  lookup: (intent: Intent, signal: AbortSignal) => Promise<Found | null>;
  // Where choosing the option goes once the record is known.
  href: (found: Found) => string;
};

const PCODE = /\bP\d{6}\b/gi;
const LENDER_LOAN = /\b(IDA|IBRD|TF)\s*(?:[-/–]\s*)?(\d{5,6})\b/gi;
const BARE_LOAN = /^\d{5,6}$/;
const STEP_REFERENCE = /\b[A-Z]{2}-[A-Z0-9][A-Z0-9&.()]*-\d+-(?:CW|GO|CS|NC)-[A-Z]+(?:-[A-Z0-9]+)*\b/gi;

const whole = (pattern: RegExp, text: string) => {
  const match = new RegExp(`^(?:${pattern.source})$`, "i").exec(text);
  return match;
};

// A lookup that finds nothing answers 404; any other failure is thrown, so the box can say it failed.
async function found<T>(path: string, signal: AbortSignal, read: (body: T) => Found): Promise<Found | null> {
  try {
    return read(await getJson<T>(path, { signal }));
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null;
    throw error;
  }
}

const project = (pcode: string): Intent => ({ kind: "project", id: pcode.toUpperCase(), query: pcode.toUpperCase() });
const loan = (lender: string, digits: string): Intent => ({
  kind: "loan",
  id: `${lender.toUpperCase()}-${digits}`,
  query: `${lender.toUpperCase()}-${digits}`,
});
const activity = (ref: string): Intent => ({ kind: "activity", id: ref.toUpperCase(), query: ref.toUpperCase() });

export const RULES: Rule[] = [
  {
    kind: "project",
    whole: (text) => (whole(PCODE, text) ? project(text) : null),
    within: (text) => [...text.matchAll(PCODE)].map((match) => project(match[0])),
    lookup: (intent, signal) =>
      found<{
        project: { project_id: string; project_name: string; country: string | null };
        agencies?: { implementing_agency: string; agency_id: string; versions: { plan_date: string; is_latest: boolean; read: boolean }[] }[];
      }>(
        `/api/projects/${encodeURIComponent(intent.query)}`,
        signal,
        (body) => ({
          kind: "project",
          pcode: body.project.project_id,
          name: body.project.project_name,
          country: body.project.country,
          plans: (body.agencies ?? []).flatMap((agency) => {
            const latest = agency.versions.find((version) => version.is_latest && version.read);
            return latest ? [{ agency: agency.implementing_agency, agencyId: agency.agency_id, planDate: latest.plan_date }] : [];
          }),
        }),
      ),
    href: (record) => `/projects/${record.kind === "project" ? record.pcode : ""}`,
  },
  {
    kind: "loan",
    whole: (text) => {
      const match = whole(LENDER_LOAN, text);
      if (match) return loan(match[1], match[2]);
      return BARE_LOAN.test(text) ? { kind: "loan", id: text, query: text, needsLookup: true } : null;
    },
    within: (text) => [...text.matchAll(LENDER_LOAN)].map((match) => loan(match[1], match[2])),
    lookup: (intent, signal) =>
      found<{ loan_number_as_written: string | null; loan_number: string; project_id: string; project_name: string | null }>(
        `/api/lookup/loan?q=${encodeURIComponent(intent.query)}`,
        signal,
        (body) => ({ kind: "loan", loan: body.loan_number_as_written ?? body.loan_number, pcode: body.project_id, name: body.project_name }),
      ),
    href: (record) => `/projects/${record.pcode}`,
  },
  {
    kind: "activity",
    whole: (text) => (whole(STEP_REFERENCE, text) ? activity(text) : null),
    within: (text) => [...text.matchAll(STEP_REFERENCE)].map((match) => activity(match[0])),
    lookup: (intent, signal) =>
      found<{ activity_reference_no: string; project_id: string; implementing_agency: string; agency_id: string; plan_date: string; is_latest: boolean }>(
        `/api/lookup/activity?q=${encodeURIComponent(intent.query)}`,
        signal,
        (body) => ({
          kind: "activity",
          stepRef: body.activity_reference_no,
          pcode: body.project_id,
          agency: body.implementing_agency,
          agencyId: body.agency_id,
          planDate: body.plan_date,
          isLatest: body.is_latest,
        }),
      ),
    // Ticket 10's Check a plan opens the fold if it must, scrolls the row into view and focuses it when
    // the address's hash names its reference.
    href: (record) => {
      if (record.kind !== "activity") return "/";
      const plan = `/projects/${record.pcode}/procurement/${record.agencyId}${record.isLatest ? "" : `/${record.planDate}`}`;
      return `${plan}#${encodeURIComponent(record.stepRef)}`;
    },
  },
];

export const ruleFor = (kind: Intent["kind"]): Rule => RULES.find((rule) => rule.kind === kind)!;

export const intentKey = (intent: Intent) => `${intent.kind}:${intent.query}`;

// What the input can mean, best first. The whole input as an ID comes first, with "Ask this" after it;
// free text asks first, and an input that holds exactly one ID lists that ID's option second.
export function intentsFor(input: string): { ids: Intent[]; askFirst: boolean } {
  const text = input.trim();
  if (!text) return { ids: [], askFirst: true };
  for (const rule of RULES) {
    const intent = rule.whole(text);
    if (intent) return { ids: [intent], askFirst: false };
  }
  const inside = RULES.flatMap((rule) => rule.within(text));
  const distinct = [...new Map(inside.map((intent) => [intentKey(intent), intent])).values()];
  return { ids: distinct.length === 1 ? distinct : [], askFirst: true };
}

export async function lookUp(intent: Intent, signal: AbortSignal): Promise<Lookup> {
  try {
    const record = await ruleFor(intent.kind).lookup(intent, signal);
    return record ? { status: "found", found: record } : { status: "missing" };
  } catch {
    return { status: "failed" };
  }
}

export const hrefFor = (record: Found) => ruleFor(record.kind).href(record);

// Ticket 112: the questions the box suggests while it is focused and empty. They are config/examples.toml's [[ask]]
// rows, which GET /api/me sends (as ask) to World Bank staff in their own view, and to no one in a preview or as of a
// date. Each is a question of evals/benchmark.yaml without its as-of date; the words are copy.box.suggest's.
export type AskPage = "package" | "project" | "plan_check" | "home";
export type AskRow = { key: string; page: AskPage; within: string | null };
export const askRows = createStore<AskRow[]>([]);
export const SUGGESTIONS_SHOWN = 3;

// One suggestion as the box lists it: its words, the ID that fills {id}, and what it is asked within.
export type Suggestion = { key: string; template: string; id: string | null; within: string | null };

// The page's suggestions, at most three: its own rows with {id} its scope, asked within that scope; on Home, and on
// any page with no scope (or whose scope chip was removed), Home's rows, each asked within its own example.
export function suggestionsFor(rows: AskRow[], page: AskPage | null, scope: string | null): { page: AskPage; items: Suggestion[] } {
  const shown: AskPage = scope && page ? page : "home";
  const words = copy.box.suggest as unknown as Record<string, unknown>;
  const items: Suggestion[] = [];
  for (const row of rows) {
    const template = words[row.key];
    if (row.page !== shown || typeof template !== "string") continue;
    const within = shown === "home" ? row.within : scope;
    if (shown === "home" && !within) continue;
    items.push({ key: row.key, template, id: within, within });
  }
  return { page: shown, items: items.slice(0, SUGGESTIONS_SHOWN) };
}

// The words a suggestion asks: its template with {id} filled.
export const suggestionText = (suggestion: Suggestion) => suggestion.template.replaceAll("{id}", suggestion.id ?? "");
