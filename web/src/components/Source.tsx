// The source line that ends a table, a card or a passage (DESIGN.md principle 1 and section 5):
// "Source:" in bold, then where the rows or words came from, in caption ink-muted with
// tabular numerals. Every source line in Strata is drawn here, so a change lands once.
import type { ReactNode } from "react";
import { copy } from "../copy";
import { cx } from "../lib/cx";

export function Source({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <p data-source className={cx("text-caption text-ink-muted", className)} data-numbers>
      <span className="font-bold">{copy.source}</span> {children}
    </p>
  );
}

// A document's source line: "Source: Implementation Completion and Results Report, P000000,
// June 30, 2021, paragraph 54, page 23." The project ID is in mono.
export function DocumentSource({
  docType,
  pcode,
  date,
  para,
  page,
  className,
}: {
  docType: string;
  pcode: string;
  // Already written by Num or formatDate, such as "June 30, 2021".
  date: string;
  // A paragraph number, or an item such as 10.b in an ICR Review.
  para: number | string;
  page: number;
  className?: string;
}) {
  const words = copy.document.sourceLine(docType, date, String(para), String(page));
  return (
    <Source className={className}>
      {words.before}
      <span className="font-mono">{pcode}</span>
      {words.after}
    </Source>
  );
}
