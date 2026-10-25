// The small parts the Lessons pages share (ticket 29; the 29 design brief, section 3.2):
//
// - Tag: a label that is not a control, 24 px tall in small ink on surface-2 with the Cards' 8 px radius, no
//   border, no hover and no focus stop, so nobody mistakes it for a chip they can click, and a label that
//   wraps reads as a box, not a blob (DESIGN.md section 5, Tag).
// - SourceChip: brief 22's Paragraph chip with the document's short name in front ("ICR ¶54", "ICR Review
//   10.b"). A 32 px pill link that opens the evidence drawer at its source. It never holds a P-code.
// - EvidenceBadge: the Status badge for IEG's part in a lesson's evidence, by the server's ieg_status.
// - Sentence: a sentence the server built, each number written by Num, so the page counts nothing.
//
// Pagination and ProjectId, which this file held before ticket 21 landed, are shared components now
// (web/src/components/Pagination.tsx and ProjectId.tsx).
import { Fragment, type ReactNode } from "react";
import { copy } from "../copy";
import { cx } from "../lib/cx";
import { evidenceHref, openEvidence } from "../lib/evidence";
import type { IegStatus, LessonEvidence, Segment } from "../lib/lessons";
import { Num } from "./Num";
import { StatusBadge, type BadgeKind } from "./StatusBadge";

const words = copy.lessons;

export function Tag({ children }: { children: ReactNode }) {
  return (
    <span data-tag className="inline-flex min-h-6 items-center rounded-md bg-surface-2 px-2 py-0.5 text-small text-ink">
      {children}
    </span>
  );
}

const BADGES: Record<IegStatus, BadgeKind> = {
  restated: "restated",
  ieg_lesson: "ieg-lesson",
  awaiting: "awaiting",
  not_restated: "not-restated",
};

export function EvidenceBadge({ status, describedBy }: { status: IegStatus; describedBy?: string }) {
  return <StatusBadge kind={BADGES[status]} describedBy={describedBy} />;
}

// "ICR ¶54" or "ICR Review 10.b".
export function chipText(evidence: LessonEvidence): string {
  const slots = { doc: evidence.doc_short, para: evidence.locator.text, section: evidence.locator.text };
  return fillText(evidence.locator.kind === "section" ? words.card.chipSection : words.card.chipParagraph, slots);
}

export function fillText(template: string, slots: Record<string, string | number>): string {
  return template.replace(/\{(\w+)\}/g, (slot, name: string) => (name in slots ? String(slots[name]) : slot));
}

export function SourceChip({ evidence, active = false, visited = false }: { evidence: LessonEvidence; active?: boolean; visited?: boolean }) {
  const slots = { doc: evidence.doc_type, pid: evidence.pid, para: evidence.locator.text, section: evidence.locator.text, page: evidence.page };
  const name = fillText(evidence.locator.kind === "section" ? words.card.chipNameSection : words.card.chipNameParagraph, slots);
  return (
    <a
      href={evidenceHref(evidence.evidence_id)}
      data-source-chip={evidence.evidence_id}
      aria-current={active ? "true" : undefined}
      onClick={(event) => {
        if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.button !== 0) return;
        event.preventDefault();
        openEvidence(evidence.evidence_id, { serial: null, sentence: null, marker: event.currentTarget, runId: null, highlight: evidence.highlight ?? null });
      }}
      className={cx(
        "inline-flex h-8 items-center rounded-pill border px-3 text-small tabular-nums no-underline transition-paint duration-150",
        active
          ? "border-primary bg-tint text-primary shadow-[inset_0_0_0_1px_var(--color-primary)]"
          : visited
            ? "border-line-strong bg-surface-2 text-ink-muted hover:bg-tint-hover"
            : "border-line-strong bg-surface text-ink hover:bg-tint-hover",
      )}
    >
      {chipText(evidence)}
      {/* The name starts with the chip's own words (WCAG 2.5.3, label in name), then says what it opens. Its
          P-code repeats the card's visible ProjectId link, so the ProjectId sweep leaves it out. */}
      <span className="clip-visually" data-project-id-exempt>
        {words.card.chipNameJoin}
        {name}
      </span>
    </a>
  );
}

// A sentence the server built: its words, and each number as Num writes it in a sentence.
export function Sentence({ segments }: { segments: Segment[] }) {
  return (
    <>
      {segments.map((segment, index) => (
        <Fragment key={index}>{"text" in segment ? segment.text : <Num count={segment.number} capital={segment.capital} />}</Fragment>
      ))}
    </>
  );
}

