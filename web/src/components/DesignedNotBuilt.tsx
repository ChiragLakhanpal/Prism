// The "Designed, not built" label (ticket 46; the 46 brief, section 12.2; DESIGN.md section 5): the Status badge,
// then at once one first-person sentence saying what Prism does instead. It sits beside the heading of the part
// that would hold the feature, as the Experimental badge does.
//
// Every label names its item in config/designed_not_built.toml, the one list the proposal's "Designed, not built"
// table also reads, and takes its sentence from copy.designedNotBuilt.items. web/tests/sweep.spec.ts opens every
// route and fails when a label shows with no entry for its route, or an entry has no label at its route. Use this
// component, never the badge alone, so every label can be found by its data-dnb key.
import { useId } from "react";
import { StatusBadge } from "./StatusBadge";

export function DesignedNotBuilt({ item, instead }: { item: string; instead: string }) {
  const id = useId();
  return (
    <span data-dnb={item} className="inline-flex flex-wrap items-center gap-x-2 gap-y-1">
      <StatusBadge kind="designed-not-built" describedBy={id} />
      <span id={id} data-dnb-instead className="text-small text-ink-muted">
        {instead}
      </span>
    </span>
  );
}
