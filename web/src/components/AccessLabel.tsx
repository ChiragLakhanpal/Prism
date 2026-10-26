// The access label (DESIGN.md section 5; the 38 brief, 4.2.1): the classification of an implementing agency team's
// private content, "Official Use Only · visible to your team", from the copy file. An outlined surface pill with a
// lucide lock and no state colour, so it never reads as a status. It sits with the title on every page that holds a
// team's upload or draft, and above the file field before a file is chosen. It is not interactive. The middle dot is
// hidden from screen readers, which hear a comma instead. The compact form, for lists, is the lock and "Official Use
// Only" in caption text.
import { Lock } from "lucide-react";
import { copy } from "../copy";
import { cx } from "../lib/cx";

const words = copy.upload;

export function AccessLabel({ className, compact = false }: { className?: string; compact?: boolean }) {
  if (compact) {
    return (
      <span className={cx("inline-flex items-center gap-1 text-caption text-ink-muted", className)} data-access-label="compact">
        <Lock aria-hidden="true" className="size-4 shrink-0" />
        {words.accessCompact}
      </span>
    );
  }
  return (
    <p
      className={cx(
        "inline-flex min-h-[30px] max-w-full items-center gap-2 rounded-pill border border-line-strong bg-surface px-3 py-1",
        "text-small font-semibold text-ink",
        className,
      )}
      data-access-label
    >
      <Lock aria-hidden="true" className="size-4 shrink-0 text-ink-muted" />
      <span>
        {words.access.lead} <span aria-hidden="true">{words.access.dot}</span>
        <span className="sr-only">{words.access.comma}</span> {words.access.rest}
      </span>
    </p>
  );
}
