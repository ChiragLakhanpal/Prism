// What changed in a Procurement Plan since the version before it, as words (the 21 brief, sections 4.2 and
// 5.4): "added two activities and re-dated three", from the route's counts, in the order added, dropped,
// re-dated, re-estimated. The page passes the counts on as words; it adds nothing up.
import { copy } from "../copy";
import type { ChangeCounts, ChangeKind } from "./api";
import { formatCount } from "./format";

export const CHANGE_KINDS: ChangeKind[] = ["added", "dropped", "redated", "reestimated"];

export function changeList(counts: ChangeCounts): string {
  return copy.changes.changeList(
    CHANGE_KINDS.filter((kind) => counts[kind] > 0).map((kind) => ({ kind, count: formatCount(counts[kind]), one: counts[kind] === 1 })),
  );
}

// Whether the route found any change.
export function changed(counts: ChangeCounts | null): boolean {
  return counts !== null && CHANGE_KINDS.some((kind) => counts[kind] > 0);
}
