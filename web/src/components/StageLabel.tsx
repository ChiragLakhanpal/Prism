// Stage label (DESIGN.md section 5, Stage label; ticket 95): the stage of the zones that follow, such as "Planning" or
// "Tender design", in label on the page grey, with a 1 px line from 12 px after its word to the column's right edge
// (app.css). It sits 8 px above the first zone of its stage and 32 px after the zone before it, once where the stage
// changes, never on every zone. It replaces the package sections' eyebrows.
import type { ReactNode } from "react";

export function StageLabel({ children }: { children: ReactNode }) {
  return (
    <p data-stage-label className="mt-8 mb-2 flex items-center gap-3 text-label text-ink-muted first:mt-0">
      {children}
    </p>
  );
}
