// Status badges (DESIGN.md section 5): a pill with a 16 px icon and 14 px text. Each kind has
// its own icon shape and names itself in words, so nothing depends on color alone. Badges
// mark exceptions; the icon is hidden from screen readers because the word carries the state.
//
// Signals: Needs a look, Watch, No signals, and Not checked (ticket 37). Data readiness: Partial, Gap. Plan checks: Data
// note. A dashed border marks the ones that mean something is missing from the record. Lessons (ticket
// 29): the four evidence badges (Restated by IEG, IEG's lesson, Awaiting IEG review, Rests on the ICR
// alone), May repeat a lesson, Being re-checked, and Overdue, amber because a late decision is stale work.
// Rebidding risk (ticket 28): Experimental, neutral with a flask, no visible border and an 8 px icon gap, the one
// quiet mark of an estimate the blueprint labels experimental (the 28 brief, section 4.2). Designed, not built (ticket
// 46): Experimental's quiet look with drafting-compass, the mark of a part the proposal describes but the app does
// not have yet (the 46 brief, section 12.2); DesignedNotBuilt sets it beside what Strata does instead.
import { Circle, CircleDashed, DraftingCompass, FlaskConical, Info, TriangleAlert, type LucideIcon } from "lucide-react";
import { copy } from "../copy";
import { cx } from "../lib/cx";
import { STATES, type State } from "./state";

export type BadgeKind =
  | "needs-a-look"
  | "watch"
  | "no-signals"
  | "not-checked"
  | "partial"
  | "gap"
  | "data-note"
  | "restated"
  | "ieg-lesson"
  | "awaiting"
  | "not-restated"
  | "may-repeat"
  | "rechecking"
  | "overdue"
  | "ieg-restates"
  | "two-reports-disagree"
  | "sources-differ"
  | "chip-warning"
  | "chip-info"
  | "own-project"
  | "their-project"
  | "audit-sample"
  | "experimental"
  | "designed-not-built"
  | "changed"
  | "retired-wrong"
  | "retired-outdated";

const lessons = copy.lessons.badges;

type Kind = { state: State; Icon: LucideIcon; dashed: boolean; text: string; quiet?: boolean };

const KINDS: Record<BadgeKind, Kind> = {
  "needs-a-look": { state: "warning", Icon: TriangleAlert, dashed: false, text: copy.badge.needsALook },
  watch: { state: "info", Icon: Info, dashed: false, text: copy.badge.watch },
  "no-signals": { state: "neutral", Icon: Circle, dashed: false, text: copy.badge.noSignals },
  // Following (ticket 37): no check could run, so the Gap look, not the No signals all-clear.
  "not-checked": { state: "neutral", Icon: CircleDashed, dashed: true, text: copy.badge.notChecked },
  partial: { state: "warning", Icon: TriangleAlert, dashed: false, text: copy.badge.partial },
  gap: { state: "neutral", Icon: CircleDashed, dashed: true, text: copy.badge.gap },
  "data-note": { state: "neutral", Icon: CircleDashed, dashed: true, text: copy.badge.dataNote },
  restated: { state: "info", Icon: Info, dashed: false, text: lessons.restated },
  "ieg-lesson": { state: "info", Icon: Info, dashed: false, text: lessons.ieg_lesson },
  awaiting: { state: "neutral", Icon: CircleDashed, dashed: true, text: lessons.awaiting },
  "not-restated": { state: "neutral", Icon: CircleDashed, dashed: false, text: lessons.not_restated },
  "may-repeat": { state: "info", Icon: Info, dashed: false, text: lessons.mayRepeat },
  rechecking: { state: "info", Icon: Info, dashed: false, text: lessons.rechecking },
  overdue: { state: "warning", Icon: TriangleAlert, dashed: false, text: lessons.overdue },
  // The evidence drawer's IEG line on a risk's lesson (ticket 30): an info badge, as Watch is.
  "ieg-restates": { state: "info", Icon: Info, dashed: false, text: copy.packageRisks.drawer.iegRestates },
  // A disagreement card's (ticket 24): warning only when it changes the answer.
  "two-reports-disagree": { state: "warning", Icon: TriangleAlert, dashed: false, text: copy.badge.twoReportsDisagree },
  "sources-differ": { state: "info", Icon: Info, dashed: false, text: copy.badge.sourcesDiffer },
  // A project timeline's disagreement line, as its list item names it below 768 px (ticket 23): the label the
  // ticket fixes, in the state its card takes.
  "chip-warning": { state: "warning", Icon: TriangleAlert, dashed: false, text: copy.timeline.chip },
  "chip-info": { state: "info", Icon: Info, dashed: false, text: copy.timeline.chip },
  // Passage reports (ticket 32): information for a reviewer, never a warning.
  "own-project": { state: "info", Icon: Info, dashed: false, text: copy.passageReports.badgeOwnProject },
  "their-project": { state: "info", Icon: Info, dashed: false, text: copy.passageReports.badgeTheirProject },
  "audit-sample": { state: "info", Icon: Info, dashed: false, text: copy.passageReports.badgeAudit },
  // A version notice's change badges (ticket 39): Changed is information; Retired as wrong holds the draft's export,
  // so it is amber, never red, since the draft is out of date and nothing failed; Retired as out of date is neutral.
  changed: { state: "info", Icon: Info, dashed: false, text: lessons.changed },
  "retired-wrong": { state: "warning", Icon: TriangleAlert, dashed: false, text: lessons.retiredWrong },
  "retired-outdated": { state: "neutral", Icon: CircleDashed, dashed: false, text: lessons.retiredOutdated },
  // Quiet: its 1px border is transparent, so it keeps every badge's height, and its icon sits 8 px from the word.
  experimental: { state: "neutral", Icon: FlaskConical, dashed: false, text: copy.badge.experimental, quiet: true },
  "designed-not-built": { state: "neutral", Icon: DraftingCompass, dashed: false, text: copy.badge.designedNotBuilt, quiet: true },
};

export function StatusBadge({ kind, className, describedBy }: { kind: BadgeKind; className?: string; describedBy?: string }) {
  const { state, Icon, dashed, text, quiet = false } = KINDS[kind];
  const look = STATES[state];
  return (
    <span
      data-badge={kind}
      aria-describedby={describedBy}
      className={cx(
        "inline-flex items-center rounded-pill border px-3 py-1 text-small font-semibold whitespace-nowrap",
        quiet ? "gap-2" : "gap-1",
        dashed ? "border-dashed" : "border-solid",
        look.box,
        look.text,
        quiet ? "border-transparent" : look.border,
        className,
      )}
    >
      <Icon aria-hidden="true" className={cx("size-4 shrink-0", look.icon)} />
      {text}
    </span>
  );
}
