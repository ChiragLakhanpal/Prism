// The view and the as-of date (ticket 40): World Bank staff, the implementing agency preview or the public preview,
// and a past date. The address is the state: ?view= and ?asof= ride on every internal link (lib/router.ts) and on every
// call to the server (lib/api.ts), which applies them (src/strata/server/views.py) and says what it applied in GET
// /api/me (appliedView below). The browser shows only what the server returns, and holds no view's rule of its own:
// the tabs, the hidden pages and the reasons a preview gives all come from the roles file's [views], through /api/me.
import { copy } from "../copy";
import { isDay } from "../routes";
import { createStore, useStore } from "./store";

export type View = "staff" | "piu" | "public";
export type Preview = "piu" | "public";

export function viewOf(search: string): View {
  const asked = new URLSearchParams(search).get("view");
  return asked === "piu" || asked === "public" ? asked : "staff";
}

// What GET /api/me says the server applied to the address, or null until it answers.
export type AppliedView = {
  own: "staff" | "piu";
  views: View[];
  applied: { view: View; preview: boolean; problem: "unknown" | null };
  preview_agency: { name: string; short_name: string | null; agency_id: string };
  tabs: string[];
  hidden: string[];
  capabilities: string[];
  reasons: Record<string, string>;
  asof: { applied: string | null; problem: "unreadable" | "not_past" | null };
};

export const appliedView = createStore<AppliedView | null>(null);

// The preview the address asks for, before the server confirms it: a preview's pill and banner render at once from
// the address (the 40 brief, section 9). The server's answer, once in, wins.
export function previewOf(search: string): Preview | null {
  const shown = appliedView.get();
  if (shown) return shown.applied.preview ? (shown.applied.view as Preview) : null;
  const view = viewOf(search);
  return view === "staff" ? null : view;
}

// The page's as-of date, as the address gives it, when it is a day I can read.
export function asOfOf(search: string): string | null {
  const asked = new URLSearchParams(search).get("asof");
  return asked && isDay(asked) ? asked : null;
}

// The page's as-of date and view, passed on to each read it makes, so every answer holds only what was public by that
// date (ADR 0002) and what that view may see. Only a preview's view leaves the page; the staff view is the server's
// default. A date I can't read stays behind too, so the page shows today's data, as the shell's alert then says.
export function readParams(search: string): Record<string, string> {
  const kept: Record<string, string> = {};
  const asOf = asOfOf(search);
  if (asOf) kept.asof = asOf;
  const view = viewOf(search);
  if (view !== "staff") kept.view = view;
  return kept;
}

// The address's own values of these keys, as a query string for a link that keeps them ("?view=piu&asof=..."),
// or "" when it has none, such as a project's tab links keeping ?view=, ?asof= and ?lang=.
export function keptQuery(search: string, keys: string[]): string {
  const params = new URLSearchParams(search);
  const kept = new URLSearchParams();
  for (const key of keys) {
    const value = params.get(key);
    if (value) kept.set(key, value);
  }
  const rest = kept.toString();
  return rest ? `?${rest}` : "";
}

// An API path with the page's as-of date and view added to its query, replacing any it named.
export function withReadParams(api: string, search: string): string {
  const [path, query = ""] = api.split("?");
  const params = new URLSearchParams(query);
  for (const [key, value] of Object.entries(readParams(search))) params.set(key, value);
  const rest = params.toString();
  return rest ? `${path}?${rest}` : path;
}

// Every call to the server carries the page's view and date (the 40 brief, section 10), unless the call names its own.
// The rest of the address is left exactly as written.
export function withPageParams(api: string, search: string = window.location.search): string {
  if (!api.startsWith("/api/")) return api;
  const [path, query = ""] = api.split("?");
  const named = new URLSearchParams(query);
  const added = Object.entries(readParams(search)).filter(([key]) => !named.has(key));
  if (added.length === 0) return api;
  const extra = new URLSearchParams(added).toString();
  return `${path}?${query ? `${query}&` : ""}${extra}`;
}

// The keys a link keeps from the address, so the mode survives navigation (the 40 brief, section 2).
export const MODE_KEYS = ["view", "asof", "lang"] as const;

// The current address with one key set, or removed with null, keeping every other key: the view rows, "Leave the
// preview", "Back to today" and "Show this date" build their links this way. ?evidence= goes, since the drawer closes.
export function withMode(pathname: string, search: string, changes: Partial<Record<"view" | "asof", string | null>>): string {
  const params = new URLSearchParams(search);
  params.delete("evidence");
  for (const [key, value] of Object.entries(changes)) {
    if (value === null || value === undefined) params.delete(key);
    else params.set(key, value);
  }
  const rest = params.toString();
  return rest ? `${pathname}?${rest}` : pathname;
}

// One typed lookup into the copy file, for a copy key the server names, such as a preview's reason
// ("draft.bar.hold.preview"). A key with no sentence is a bug in the roles file, which tests/registries check.
export function copyAt(key: string): string {
  let value: unknown = copy;
  for (const part of key.split(".")) value = value && typeof value === "object" ? (value as Record<string, unknown>)[part] : undefined;
  if (typeof value !== "string") throw new Error(`The copy file has no sentence at ${key}.`);
  return value;
}

// The sentence a held control shows in a preview for an act the preview does not keep, from the roles file's reason
// through /api/me, the same copy key the server's 403 names. Null outside a preview, or while /api/me loads.
export function previewReason(capability: string, shown: AppliedView | null = appliedView.get()): string | null {
  if (!shown?.applied.preview || shown.capabilities.includes(capability)) return null;
  const key = shown.reasons[capability];
  return key ? copyAt(key) : null;
}

// previewReason for a held control in a preview, as a component reads it: the sentence the roles file names for the
// act, or the control's own words where no applied view is known, such as a design gallery sample.
export function usePreviewReason(capability: string, fallback: string): string {
  return previewReason(capability, useStore(appliedView)) ?? fallback;
}

// Whether the view the server applied has a capability of the roles file's [views], as GET /api/me listed it. Before it
// answers, a page is in the person's own view, and the server refuses anything that view lacks.
export function allows(capability: string, shown: AppliedView | null = appliedView.get()): boolean {
  return !shown || shown.capabilities.includes(capability);
}

export function useAllows(capability: string): boolean {
  return allows(capability, useStore(appliedView));
}

// Whether the view the server applied shows a page, by its key in routes.ts, such as "package" for a link that opens a
// package page. A page the view hides keeps its address and says why (RoutePage), so a link to it is left out.
export function useShows(page: string): boolean {
  const shown = useStore(appliedView);
  return !shown || !shown.hidden.includes(page);
}

// The agency the agency view names in a sentence: "the Northern Water Works Development Agency (NWWDA)".
export function agencyInSentence(shown: AppliedView): string {
  return copy.view.agencyInSentence(shown.preview_agency.name, shown.preview_agency.short_name);
}
