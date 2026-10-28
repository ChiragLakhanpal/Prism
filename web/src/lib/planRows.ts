// A plan check row's records in the evidence drawer (ticket 100; DESIGN.md section 5, Plan check table): the reason,
// what I checked, the plan row, its source and its two links. They come from check_plan's result, which the page already
// holds, so the plan check remembers each row's records in the evidence store, as ticket 15's quantile dots are, and
// the drawer never asks the server for them. A link to the address with the drawer open shows them once the check has
// loaded.
//
// The id is plan-row-check: and the plan row's own evidence id, such as
// plan-row-check:strata.silver.plan_rows:40132287/KE-NWWDA-229129-CW-RFB, so two versions of a plan never share one.
// An upload's row has no evidence id, and goes by its key in the upload.
import { useEffect, useLayoutEffect } from "react";
import { createStore } from "./store";

export const PLAN_ROW_CHECK = "plan-row-check:";

// Whether a plan check that will hold rows' records is still loading on this page. A link that opens a row's records
// waits for it; once nothing is loading and the page holds no records for the id (the check failed or abstained, or
// the link was opened on another page), the drawer says it could not find them, never "Loading" for ever (ticket
// 100's review, F2). CheckPlanPage and UploadCheckPage set it while their check loads.
export const planRowsLoading = createStore(false);

// A check page says whether its check is still loading. It says so before the first paint, so a link never shows
// "could not find" while the check is on its way, and says it is done only after the page's effects ran, by when the
// plan check has remembered its rows' records (PlanCheck's effect, a child's, runs first).
export function useRowsLoading(loading: boolean): void {
  useLayoutEffect(() => {
    if (loading) planRowsLoading.set(true);
  }, [loading]);
  useEffect(() => {
    if (!loading) planRowsLoading.set(false);
  }, [loading]);
  useEffect(() => () => planRowsLoading.set(false), []);
}

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
