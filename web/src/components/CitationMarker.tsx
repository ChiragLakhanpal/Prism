// The citation marker (DESIGN.md section 5): an inline pill holding the source's number, 12 px
// bold primary, 20 px tall. Its accessible name names the source ("Source 1: Implementation
// Completion and Results Report, June 30, 2021, paragraph 54"). Hover or focus shows the
// evidence card; a click opens the source; Escape closes the card.
//
// The brackets sit in the page but out of sight, so a copied answer reads "[1]". An ::after
// pads the hit area to 24 by 24 px without changing the line. No state changes its size. A
// 4 px margin on each side keeps the focus ring (2 px at a 2 px offset) off the period before
// it and the word after it.
//
// The marker never starts a line. A word joiner (U+2060) ties it to the last word of the
// sentence it cites, and the span around both keeps the browser from breaking between them,
// so the last word wraps with its marker. A marker at the head of a line would read as the
// source of the next sentence (CLAUDE.md rule 2).
//
// In the answer panel (ticket 14) the marker is a real link to the page with ?evidence=<id>, so it
// can open in a new tab; a click opens the evidence drawer instead, and the marker says whether the
// drawer shows its source (aria-expanded, with aria-controls naming the drawer).
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
  drawerId,
  evidenceId,
  sentence,
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
  // Opens the source; it gets the marker, so focus can come back to it.
  onOpen?: (marker: HTMLElement) => void;
  // The evidence drawer's id, when a click opens it.
  drawerId?: string;
  // The source and the sentence the marker cites, so focus can find it again.
  evidenceId?: string;
  sentence?: number;
}) {
  const marker = (
    <a
      href={href}
      data-citation={n}
      aria-label={copy.citation.name(n, source, opened)}
      aria-current={active && !drawerId ? "true" : undefined}
      aria-expanded={drawerId ? active : undefined}
      aria-controls={drawerId}
      data-citation-id={evidenceId}
      data-sentence={sentence}
      onClick={
        onOpen &&
        ((event) => {
          if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.button !== 0) return;
          event.preventDefault();
          onOpen(event.currentTarget);
        })
      }
      className={cx(
        "relative mx-1 inline-flex h-5 min-w-5 items-center justify-center rounded-pill border px-1 align-[1px]",
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
  return (
    <span className="whitespace-nowrap">
      {WORD_JOINER}
      {preview ? (
        // The marker whose source the drawer shows in full opens no card beside it.
        <Tooltip trigger={marker} width="w-[min(22.5rem,calc(100vw-3.5rem))]" card quiet={active && Boolean(drawerId)}>
          {preview}
        </Tooltip>
      ) : (
        marker
      )}
    </span>
  );
}

// Ties a marker or an icon to the word before it, so neither starts a line. A copied answer drops it
// (Answer.tsx).
export const WORD_JOINER = "\u2060";
