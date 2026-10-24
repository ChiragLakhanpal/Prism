// The view the address asks for (ticket 40 builds the view switch): World Bank staff, the implementing
// agency preview or the public preview. A preview can only take things away, such as the baseline's saver
// in the implementing agency view and the baseline itself in the public view (ticket 21).
export type View = "staff" | "piu" | "public";

export function viewOf(search: string): View {
  const asked = new URLSearchParams(search).get("view");
  return asked === "piu" || asked === "public" ? asked : "staff";
}

// The page's as-of date and view, passed on to each read it makes, so every answer holds only what was
// public by that date (ADR 0002) and what that view may see (the 21 review, round 2; ticket 40 builds the
// switch between them).
export function readParams(search: string): Record<string, string> {
  const asked = new URLSearchParams(search);
  const kept: Record<string, string> = {};
  for (const key of ["asof", "view"]) {
    const value = asked.get(key);
    if (value) kept[key] = value;
  }
  return kept;
}

// An API path with the page's as-of date and view added to its query.
export function withReadParams(api: string, search: string): string {
  const [path, query = ""] = api.split("?");
  const params = new URLSearchParams(query);
  for (const [key, value] of Object.entries(readParams(search))) params.set(key, value);
  const rest = params.toString();
  return rest ? `${path}?${rest}` : path;
}
