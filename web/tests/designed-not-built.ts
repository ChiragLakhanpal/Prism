// The "Designed, not built" label check (ticket 46; the 46 brief, sections 12.3 and 15): the labels the sweep found
// on each route against config/designed_not_built.toml. Each problem is the build's own sentence for the "Label and
// list disagree" state.
export type Label = { route: string; key: string };
export type Item = { key: string; route: string };

export function labelProblems(labels: Label[], items: Item[], swept: string[]): string[] {
  const listed = new Set(items.map((item) => item.key));
  const unlisted = labels
    .filter((label) => !listed.has(label.key))
    .map((label) => `${label.key} is labeled "Designed, not built" in Prism at ${label.route} but is missing from the proposal's list.`);
  const unlabeled = items
    .filter((item) => !labels.some((label) => label.key === item.key && label.route === item.route))
    .map((item) =>
      swept.includes(item.route)
        ? `${item.key} is in the proposal's list, but Prism shows no label at ${item.route}.`
        : `${item.key} is in the proposal's list at ${item.route}, which web/tests/sweep.spec.ts does not open. Add the route to ROUTES there.`,
    );
  return [...unlisted, ...unlabeled];
}
