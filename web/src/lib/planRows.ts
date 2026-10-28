// A plan check row's records in the evidence drawer (ticket 100; DESIGN.md section 5, Plan check table): the reason,
// what I checked, the plan row, its source and its two links. They come from check_plan's result, which the page already
// holds, so the plan check remembers each row's records in the evidence store, as ticket 15's quantile dots are, and
// the drawer never asks the server for them. A link to the address with the drawer open shows them once the check has
// loaded.
//
// The id is plan-row-check: and the plan row's own evidence id, such as
// plan-row-check:strata.silver.plan_rows:40132287/KE-NWWDA-229129-CW-RFB, so two versions of a plan never share one.
// An upload's row has no evidence id, and goes by its key in the upload.
export const PLAN_ROW_CHECK = "plan-row-check:";

export function isPlanRowCheck(id: string): boolean {
  return id.startsWith(PLAN_ROW_CHECK);
}

export function planRowCheckId(source: string): string {
  return `${PLAN_ROW_CHECK}${source}`;
}

// The record the drawer records as opened for the viewer: the plan row itself. An upload's row is no published record,
// so nothing is recorded for it.
export function planRowSource(id: string): string | null {
  const source = id.slice(PLAN_ROW_CHECK.length);
  return source.startsWith("strata.") ? source : null;
}
