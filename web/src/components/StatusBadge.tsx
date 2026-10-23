// Status badges (DESIGN.md section 5): a pill with a 16 px icon and 14 px text. Each kind has
// its own icon shape and names itself in words, so nothing depends on colour alone. Badges
// mark exceptions; the icon is hidden from screen readers because the word carries the state.
//
// Signals: Needs a look, Watch, No signals. Data readiness: Partial, Gap. Plan checks: Data
// note. A dashed border marks the two that mean something is missing from the record.
import { Circle, CircleDashed, Info, TriangleAlert, type LucideIcon } from "lucide-react";
import { copy } from "../copy";
import { cx } from "../lib/cx";
import { STATES, type State } from "./state";

export type BadgeKind = "needs-a-look" | "watch" | "no-signals" | "partial" | "gap" | "data-note";

const KINDS: Record<BadgeKind, { state: State; Icon: LucideIcon; dashed: boolean; text: string }> = {
  "needs-a-look": { state: "warning", Icon: TriangleAlert, dashed: false, text: copy.badge.needsALook },
  watch: { state: "info", Icon: Info, dashed: false, text: copy.badge.watch },
  "no-signals": { state: "neutral", Icon: Circle, dashed: false, text: copy.badge.noSignals },
  partial: { state: "warning", Icon: TriangleAlert, dashed: false, text: copy.badge.partial },
  gap: { state: "neutral", Icon: CircleDashed, dashed: true, text: copy.badge.gap },
  "data-note": { state: "neutral", Icon: CircleDashed, dashed: true, text: copy.badge.dataNote },
};

export function StatusBadge({ kind, className }: { kind: BadgeKind; className?: string }) {
  const { state, Icon, dashed, text } = KINDS[kind];
  const look = STATES[state];
  return (
    <span
      data-badge={kind}
      className={cx(
        "inline-flex items-center gap-1 rounded-pill border px-3 py-1 text-small font-semibold whitespace-nowrap",
        dashed ? "border-dashed" : "border-solid",
        look.box,
        look.text,
        look.border,
        className,
      )}
    >
      <Icon aria-hidden="true" className={cx("size-4 shrink-0", look.icon)} />
      {text}
    </span>
  );
}
