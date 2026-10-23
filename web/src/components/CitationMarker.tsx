// The citation marker (DESIGN.md section 5): an inline pill holding the source's number, 12 px
// bold primary, 20 px tall. Its accessible name names the source ("Source 1: Implementation
// Completion and Results Report, June 30, 2021, paragraph 54"). Hover or focus shows the
// evidence card; a click opens the source; Escape closes the card.
//
// The brackets sit in the page but out of sight, so a copied answer reads "[1]". An ::after
// pads the hit area to 24 by 24 px without changing the line. No state changes its size.
import type { ReactNode } from "react";
import { copy } from "../copy";
import { cx } from "../lib/cx";
import { Tooltip } from "./Popover";

export function CitationMarker({
  n,
  source,
  href,
  preview,
  opened = false,
  active = false,
  onOpen,
}: {
  n: number;
  // The document type, date and paragraph, as the name reads them.
  source: string;
  href: string;
  // The evidence card shown on hover and focus.
  preview?: ReactNode;
  // Opened before: the marker recedes, so unopened sources draw the eye.
  opened?: boolean;
  // Its source is open in the evidence drawer now.
  active?: boolean;
  onOpen?: () => void;
}) {
  const marker = (
    <a
      href={href}
      data-citation={n}
      aria-label={copy.citation.name(n, source, opened)}
      aria-current={active ? "true" : undefined}
      onClick={
        onOpen &&
        ((event) => {
          event.preventDefault();
          onOpen();
        })
      }
      className={cx(
        "relative mx-0.5 inline-flex h-5 min-w-5 items-center justify-center rounded-pill border px-1 align-[1px]",
        "text-label font-bold tabular-nums no-underline transition-paint duration-150",
        "after:absolute after:-inset-0.5 after:content-['']",
        active
          ? "border-primary bg-tint text-primary shadow-[inset_0_0_0_1px_var(--color-primary)]"
          : opened
            ? "border-line-strong bg-surface-2 text-ink-muted hover:bg-tint-hover"
            : "border-primary bg-surface text-primary hover:bg-tint-hover",
      )}
    >
      <span className="clip-visually">[</span>
      {n}
      <span className="clip-visually">]</span>
    </a>
  );
  return preview ? (
    <Tooltip trigger={marker} width="w-[min(22.5rem,calc(100vw-3.5rem))]">
      {preview}
    </Tooltip>
  ) : (
    marker
  );
}
