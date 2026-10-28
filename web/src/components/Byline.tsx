// Byline (ticket 111; DESIGN.md section 1, principle 6, and section 5): Strata's own words open with its byline,
// and a record's words end with their source. One line, 8 px above the words it names (the words keep the margin):
// "Strata" in the wordmark's weight (700) at the label size in ink-heading, then what Strata did in label (600,
// ink-muted). "Strata, in short" over an answer, where it is the answer's h3; "Strata found" over a finding;
// "Strata held back" over a held-back sentence. No icon, no color and no border, so it cannot be mistaken for the
// current mark or a quote. It never sits over a table, a quote, a STEP row, a Worth knowing line or a record.
import { copy } from "../copy";
import { cx } from "../lib/cx";
import { Fill } from "./Fill";

export type BylineKind = "inShort" | "found" | "heldBack";

export function Byline({ kind, as: Tag = "p", className }: { kind: BylineKind; as?: "p" | "h3"; className?: string }) {
  return (
    <Tag data-byline={kind} className={cx("text-label text-ink-muted", className)}>
      <Fill template={copy.byline[kind]} slots={{ strata: <span className="font-bold text-ink-heading">{copy.byline.strata}</span> }} />
    </Tag>
  );
}
