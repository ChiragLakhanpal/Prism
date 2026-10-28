// Foot strip (DESIGN.md section 5, Foot strip; ticket 95): the end of each block of evidence in a Task zone's panel,
// where provenance always has its place. The panel's full width on the page grey, a 1 px line over it, padding 16 and
// 24 (16 below a 768 px window), on the zone body's left edge. It holds the block's Note, its coverage line and its
// source line, in caption, 8 px apart, each at most 65 characters a line; a line that holds a number you can check,
// such as the coverage line's "49 of 65", is 24 px tall (app.css, "Task zones").
import type { ReactNode } from "react";

export function FootStrip({ children }: { children: ReactNode }) {
  return (
    <div data-foot-strip className="text-caption text-ink-muted [&>*]:max-w-prose">
      {children}
    </div>
  );
}
