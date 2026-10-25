// The view the address asks for (ticket 40 builds the view switch): World Bank staff, the implementing
// agency preview or the public preview. A preview can only take things away, such as the baseline's saver
// in the implementing agency view and the baseline itself in the public view (ticket 21).
import { isDay } from "../routes";

export type View = "staff" | "piu" | "public";

export function viewOf(search: string): View {
  const asked = new URLSearchParams(search).get("view");
  return asked === "piu" || asked === "public" ? asked : "staff";
}

// The page's as-of date and view, passed on to each read it makes, so every answer holds only what was
// public by that date (ADR 0002) and what that view may see (the 21 review, round 2; ticket 40 builds the
// switch between them).
// Only a preview's view ("piu" or "public") leaves the page; the staff view is the server's default. A date I can't
// read stays behind too, so the page shows today's data, as the shell's alert then says (App.tsx, alerts).
export function readParams(search: string): Record<string, string> {
  const kept: Record<string, string> = {};
  const asOf = new URLSearchParams(search).get("asof");
  if (asOf && isDay(asOf)) kept.asof = asOf;
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

// An API path with the page's as-of date and view added to its query.
export function withReadParams(api: string, search: string): string {
  const [path, query = ""] = api.split("?");
  const params = new URLSearchParams(query);
  for (const [key, value] of Object.entries(readParams(search))) params.set(key, value);
  const rest = params.toString();
  return rest ? `${path}?${rest}` : path;
}
