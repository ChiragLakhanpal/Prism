// Source tag (DESIGN.md section 5; the 23 brief, section 5.3): a quiet pill that names a side's role in a
// disagreement, "Prism leans on this" or "You kept this". It names a role, not a state, so it has no icon and no
// border, and the two sides of a card stay equal: neutral text on neutral-bg, 24 px tall.
import type { ReactNode } from "react";
import { cx } from "../lib/cx";

export function SourceTag({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <span data-source-tag className={cx("inline-flex h-6 items-center rounded-pill bg-neutral-bg px-2 py-0.5 text-caption font-semibold text-neutral", className)}>
      {children}
    </span>
  );
}
