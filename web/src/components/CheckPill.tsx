// The check pill (the 10 brief): how much Prism checked, such as "9 activities checked". Neutral and
// not a control. It has no icon, which keeps it apart from a status badge; ticket 15 reuses it for
// "23 numbers checked · 1 removed".
import type { ReactNode } from "react";

export function CheckPill({ children }: { children: ReactNode }) {
  return (
    <span
      data-check-pill
      className="inline-flex items-center rounded-pill border border-line-strong bg-neutral-bg px-3 py-1 text-small font-semibold whitespace-nowrap text-neutral tabular-nums"
    >
      {children}
    </span>
  );
}
