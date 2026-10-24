// The view the address asks for (ticket 40 builds the view switch): World Bank staff, the implementing
// agency preview or the public preview. A preview can only take things away, such as the baseline's saver
// in the implementing agency view and the baseline itself in the public view (ticket 21).
export type View = "staff" | "piu" | "public";

export function viewOf(search: string): View {
  const asked = new URLSearchParams(search).get("view");
  return asked === "piu" || asked === "public" ? asked : "staff";
}
