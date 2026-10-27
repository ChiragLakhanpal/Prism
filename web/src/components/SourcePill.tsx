// The source pill (DESIGN.md section 5; the 30 brief, section 4.2): the citation marker with the source's short
// name in place of a number, for a column or list whose only job is sources, such as the risk table's Sources.
// "ICR P130164 ¶54", or "ICR Review 10.b" for a later pill from the same project (web/src/lib/risks.ts, pillText).
//
// The citation marker's pill and states: 20 px tall, a 1px primary border on surface, 12px/700 primary text with
// tabular numerals and the P-code in Roboto Mono 500; hover tint-hover and the evidence card after its delay;
// focus the 2px focus outline and the card at once; active (its source is open) tint with an inset 1px primary
// ring; visited surface-2, line-strong and ink-muted, with ", opened" in its name. An ::after pads the target to
// at least 24 by 24 px, and no state changes its size. It is a link to the page with ?evidence= and the passage's
// id, so it opens in a new tab; a click opens the evidence drawer instead. Source pills take no number, so a
// numbered marker elsewhere on the page keeps its number.
import { copy } from "../copy";
import { cx } from "../lib/cx";
import { formatDate } from "../lib/format";
import { evidenceHref } from "../lib/evidence";
import { locatorText, type RiskSource } from "../lib/risks";
import { Fill } from "./Fill";
import { Tooltip } from "./Popover";
import { DocumentSource } from "./Source";

// The evidence card a pill shows on hover and focus: the stratum, the source, the words the lesson quotes from
// it, and its source line. A row shows a lesson, not the paragraph's words, so the card adds the quote.
export function PillCard({ source }: { source: RiskSource }) {
  const project = source.project_name ?? source.pcode;
  return (
    <div data-evidence-card className="flex flex-col p-1">
      <p className="text-label text-ink-muted">{copy.evidence.eyebrow.Why}</p>
      <p className="mt-1 text-h2 text-ink-heading">
        {source.locator.kind === "paragraph" ? (
          <Fill template={copy.evidence.title} slots={{ project, para: source.locator.text }} />
        ) : (
          <Fill template={copy.evidence.titleSection} slots={{ project, section: source.locator.text }} />
        )}
      </p>
      <p data-excerpt className="mt-2 text-small text-ink">
        {copy.evidence.quoteOpen}
        {source.quote}
        {copy.evidence.quoteClose}
      </p>
      <DocumentSource
        className="mt-2"
        docType={source.doc_type}
        pcode={source.pcode}
        date={source.date ? formatDate(source.date) : ""}
        place={{ kind: source.locator.kind, text: source.locator.text }}
        page={source.page ?? 0}
      />
    </div>
  );
}

export function SourcePill({
  source,
  withProject = true,
  active = false,
  opened = false,
  onOpen,
  controlsId = "evidence-drawer",
}: {
  source: RiskSource;
  // A later pill from the same project drops the P-code.
  withProject?: boolean;
  // Its source is open in the evidence drawer now.
  active?: boolean;
  // Opened before.
  opened?: boolean;
  onOpen: (pill: HTMLElement) => void;
  // The evidence drawer's id, or null where no drawer opens, as in the design gallery.
  controlsId?: string | null;
}) {
  const words = copy.packageRisks;
  // The name is the pill's own words, with "¶" heard as "paragraph", then the document's full name and date, so it
  // starts with what the pill shows (WCAG 2.5.3): "ICR P130164 paragraph 54, Implementation Completion and Results
  // Report, October 10, 2019".
  const locator =
    source.locator.kind === "paragraph" ? (
      <>
        <span aria-hidden="true">{copy.evidence.paraMark}</span>
        <span className="sr-only">{copy.evidence.paraSpoken}</span>
        {source.locator.text}
      </>
    ) : (
      locatorText(source.locator)
    );
  const pill = (
    <a
      href={evidenceHref(source.evidence_id)}
      data-source-pill={source.evidence_id}
      aria-expanded={controlsId ? active : undefined}
      aria-controls={controlsId ?? undefined}
      onClick={(event) => {
        if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.button !== 0) return;
        event.preventDefault();
        onOpen(event.currentTarget);
      }}
      className={cx(
        "relative inline-flex min-h-5 max-w-full items-center rounded-pill border px-2 text-left align-[1px]",
        "text-label font-bold tabular-nums no-underline transition-paint duration-150",
        "after:absolute after:-inset-0.5 after:content-['']",
        active
          ? "border-primary bg-tint text-primary shadow-[inset_0_0_0_1px_var(--color-primary)]"
          : opened
            ? "border-line-strong bg-surface-2 text-ink-muted hover:bg-tint-hover"
            : "border-primary bg-surface text-primary hover:bg-tint-hover",
      )}
    >
      <span>
        {source.doc_short}{" "}
        {withProject && <span className="font-mono font-medium whitespace-nowrap">{source.pcode}</span>}
        {withProject && " "}
        <span className="whitespace-nowrap">{locator}</span>
      </span>
      <span className="sr-only">{words.pillNameAfter(source.doc_type, source.date ? formatDate(source.date) : "", opened)}</span>
    </a>
  );
  // A pill whose source the drawer shows in full opens no card beside it.
  return (
    <Tooltip trigger={pill} width="w-[min(22.5rem,calc(100vw-3.5rem))]" quiet={active}>
      <PillCard source={source} />
    </Tooltip>
  );
}
