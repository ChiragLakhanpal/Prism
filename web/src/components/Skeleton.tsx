// Skeleton: static surface-2 blocks sized to the content they stand in for, so nothing moves
// when the content arrives. No shimmer and no motion. The region that is loading sets
// aria-busy and carries the "Loading" text for screen readers; the blocks are hidden from them.
import type { CSSProperties } from "react";
import { copy } from "../copy";
import { cx } from "../lib/cx";

// radius: the shape it stands for, such as rounded-pill for a button or a badge. inline: words inside a line
// of real text, as tall as the font, so the real words around it wrap as they will once it loads.
export function Skeleton({ className, radius = "rounded-xs", inline = false }: { className: string; radius?: string; inline?: boolean }) {
  return (
    <span
      aria-hidden="true"
      data-skeleton
      className={cx(inline ? "inline-block h-[1em] max-w-full align-[-0.125em]" : "block", "bg-surface-2", radius, className)}
    />
  );
}

// One line of text: a box exactly one line tall in the text style around it (1lh), holding a
// bar as tall as the font. A line of skeleton takes the same height as the line it stands for.
// style sets a text size the type tokens don't name, such as a chart's title by its width.
export function SkeletonLine({ width, className, style }: { width: string; className?: string; style?: CSSProperties }) {
  return (
    <span aria-hidden="true" className={cx("flex h-lh items-center", className)} style={style}>
      <Skeleton className={cx("h-[1em]", width)} />
    </span>
  );
}

// Lines of text, one per entry, at the given widths, with no gap: a paragraph of n lines. It is a
// span with display flex, so it can stand in for a heading's text: a heading holds only phrasing
// content.
export function SkeletonText({ widths, className, style }: { widths: string[]; className?: string; style?: CSSProperties }) {
  return (
    <span aria-hidden="true" className={cx("flex flex-col", className)} style={style}>
      {widths.map((width, index) => (
        <SkeletonLine key={index} width={width} />
      ))}
    </span>
  );
}

// The words a screen reader hears while a region loads.
export function LoadingLabel() {
  return <span className="sr-only">{copy.loading}</span>;
}
