// Skeleton: static surface-2 blocks sized to the content they stand in for, so nothing moves
// when the content arrives. No shimmer and no motion. The region that is loading sets
// aria-busy and carries the "Loading" text for screen readers; the blocks are hidden from them.
import { copy } from "../copy";
import { cx } from "../lib/cx";

export function Skeleton({ className }: { className: string }) {
  return <span aria-hidden="true" data-skeleton className={cx("block rounded-xs bg-surface-2", className)} />;
}

// Lines of text: one 16 px bar per entry, at the given width, 8 px apart.
export function SkeletonText({ widths, className }: { widths: string[]; className?: string }) {
  return (
    <div className={cx("flex flex-col gap-2", className)}>
      {widths.map((width, index) => (
        <Skeleton key={index} className={cx("h-4", width)} />
      ))}
    </div>
  );
}

// The words a screen reader hears while a region loads.
export function LoadingLabel() {
  return <span className="sr-only">{copy.loading}</span>;
}
