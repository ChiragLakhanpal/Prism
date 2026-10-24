// Skeleton: static surface-2 blocks sized to the content they stand in for, so nothing moves
// when the content arrives. No shimmer and no motion. The region that is loading sets
// aria-busy and carries the "Loading" text for screen readers; the blocks are hidden from them.
import { copy } from "../copy";
import { cx } from "../lib/cx";

export function Skeleton({ className }: { className: string }) {
  return <span aria-hidden="true" data-skeleton className={cx("block rounded-xs bg-surface-2", className)} />;
}

// One line of text: a box exactly one line tall in the text style around it (1lh), holding a
// bar as tall as the font. A line of skeleton takes the same height as the line it stands for.
export function SkeletonLine({ width, className }: { width: string; className?: string }) {
  return (
    <span aria-hidden="true" className={cx("flex h-lh items-center", className)}>
      <Skeleton className={cx("h-[1em]", width)} />
    </span>
  );
}

// Lines of text, one per entry, at the given widths, with no gap: a paragraph of n lines. It is a
// span with display flex, so it can stand in for a heading's text: a heading holds only phrasing
// content.
export function SkeletonText({ widths, className }: { widths: string[]; className?: string }) {
  return (
    <span aria-hidden="true" className={cx("flex flex-col", className)}>
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
