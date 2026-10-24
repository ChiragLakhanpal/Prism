// The draft bar (DESIGN.md section 5; the 35 brief, section 4.3), and what takes its place: the export
// success panel (4.6) and the discarded notice (4.7).
//
// The bar is a section named "Check and export" at the end of the document column, held to it, on
// surface with a 1px line on top. It sticks to the bottom of the window only when the window is at least
// 768 px wide and 640 px tall; otherwise it sits at the end of the page, because a sticky bar this tall
// would cover the note you are checking. It always has two rows. Row 1 says what exporting does and is
// not: the kind's lead sentence, the fixed consequence sentence, how many sources you opened (a link to
// the Sources list), and the hold line when export is held. Row 2 has Discard at the left edge, set apart
// by the whole row, and Export to Word and the solid button at the right. In Draft the solid button is
// Mark as checked and Export to Word is held; once checked, and with no hold left, Export to Word is the
// solid button. Only the author acts: a teammate reads one line instead of the buttons.
//
// A busy button shows its busy label within 100 ms and keeps its width, and the bar is aria-busy until
// the server answers. The state changes only when the server confirms it. A status line announces each
// change, and a failure shows as a line between the rows.
import { forwardRef, useEffect, useId, useRef, type ReactNode, type Ref } from "react";
import { Check, CircleX, Info } from "lucide-react";
import { copy } from "../copy";
import { cx } from "../lib/cx";
import type { Action, Draft } from "../lib/drafts";
import { fileHref } from "../lib/drafts";
import { formatNumber } from "../lib/format";
import { Alert } from "./Alert";
import { Button } from "./Button";
import { Fill } from "./Fill";
import { SOURCES_ID } from "./SourcesList";
import { TextLink } from "./TextLink";

const whole = (value: number) => formatNumber(value, { compact: false });
// After the notes are marked as checked, Export to Word takes Mark as checked's place under the pointer.
// For this long after it turns solid, a click on it is the end of the click that checked the notes.
const SETTLE_MS = 400;

// Sticky only in a window at least 768 px wide and 640 px tall (48rem by 40rem). Every class name with
// this media query is written out whole, so Tailwind finds it.
export const STICKY = "[@media(min-width:48rem)_and_(min-height:40rem)]:sticky [@media(min-width:48rem)_and_(min-height:40rem)]:bottom-0";

export type BarProps = {
  draft: Draft;
  // The kind's words: the lead sentences, the hold line and the teammate's line.
  words: { barLead: string; barLeadTeammate: (author: string) => string; holdNotChecked: string; readOnly: (author: string) => string };
  opened: number;
  // The act the server is answering, if any; the act that failed, if any.
  busy: Action | null;
  failed: Action | null;
  // What the status line says now.
  status: string;
  onAct: (action: Action) => void;
  exportRef?: Ref<HTMLButtonElement>;
  checkRef?: Ref<HTMLButtonElement>;
  // A line under row 1 that says the draft changed elsewhere and was reloaded.
  notice?: string | null;
  // Its margin, on the bar itself: the bar must be a direct child of the tall page, or sticky has no room.
  className?: string;
};

// Each hold's sentence by the copy key its registry entry names (config/drafts.toml, [holds.<key>].copy):
// the kind's own sentence for notChecked, and the shared ones for every other hold.
export function holdLines(words: BarProps["words"]): Record<string, string> {
  return { ...copy.draft.bar.hold, notChecked: words.holdNotChecked };
}

function holdLine(draft: Draft, words: BarProps["words"]): string | null {
  const lines = holdLines(words);
  const said = draft.holds.map((hold) => lines[hold.copy]).filter(Boolean);
  return said.length ? said.join(" ") : null;
}

export const DraftBar = forwardRef(function DraftBar(
  { draft, words, opened, busy, failed, status, onAct, exportRef, checkRef, notice, className }: BarProps,
  ref: Ref<HTMLElement>,
) {
  const bar = copy.draft.bar;
  const author = draft.author.name ?? "";
  const mine = draft.author.you;
  const hold = mine ? holdLine(draft, words) : null;
  const checked = draft.state === "checked";
  // The solid button: Export to Word once checked with no hold left, else Mark as checked.
  const exportPrimary = checked && draft.holds.length === 0;
  const held = draft.holds.length > 0 || !draft.may_act;
  const holdId = useId();
  // When Export to Word turned solid in this visit: a click that lands just after is not a request to
  // export. A draft that opens already checked has no such moment.
  const solidSince = useRef(0);
  const wasPrimary = useRef(exportPrimary);
  useEffect(() => {
    if (exportPrimary && !wasPrimary.current) solidSince.current = Date.now();
    wasPrimary.current = exportPrimary;
  }, [exportPrimary]);
  const exportClick = (event: React.MouseEvent<HTMLButtonElement>) => {
    // The second click of a double click, or a click in the moment after the button changed under the
    // pointer: export can't be undone, so it waits for a deliberate press. A key press has detail 0.
    if (event.detail > 1 || Date.now() - solidSince.current < SETTLE_MS) return;
    onAct("export");
  };
  const describedBy = hold ? holdId : undefined;
  return (
    <section
      ref={ref}
      aria-label={bar.label}
      aria-busy={busy !== null}
      data-draft-bar={draft.state}
      className={cx("z-10 border-t border-line bg-surface px-4 py-3 md:px-6", STICKY, className)}
    >
      <p className="max-w-[80ch] text-small text-ink" data-bar-lead>
        {mine ? words.barLead : words.barLeadTeammate(author)} {bar.consequence}{" "}
        <TextLink href={`#${SOURCES_ID}`} onClick={focusSources} data-opened-link>
          {bar.opened(whole(opened), whole(draft.opened.of))}
        </TextLink>
        {bar.end}
        {hold && (
          <>
            {" "}
            <span id={holdId} data-hold-line>
              {hold}
            </span>
          </>
        )}
      </p>
      {failed && (
        <p role="alert" className="mt-2 flex items-start gap-2 text-small text-error">
          <CircleX aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-error-icon" />
          {bar.failed[failed]}
        </p>
      )}
      {!failed && notice && (
        <p className="mt-2 flex items-start gap-2 text-small text-ink" data-bar-notice>
          <Info aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-info-icon" />
          {notice}
        </p>
      )}
      <p role="status" className="sr-only" data-bar-status>
        {status}
      </p>
      {mine ? (
        <div
          className={cx(
            "mt-3 flex flex-col",
            "[@media(min-width:48rem)_and_(min-height:40rem)]:flex-row [@media(min-width:48rem)_and_(min-height:40rem)]:items-center",
            "[@media(min-width:48rem)_and_(min-height:40rem)]:justify-between [@media(min-width:48rem)_and_(min-height:40rem)]:gap-2",
          )}
        >
          <div>
            <Button
              variant="ghost"
              flush
              held={!draft.may_act}
              aria-describedby={!draft.may_act ? describedBy : undefined}
              loading={busy === "discard"}
              busyLabel={bar.busy.discard}
              onClick={() => onAct("discard")}
            >
              {bar.discard}
            </Button>
          </div>
          <div
            className={cx(
              "mt-4 flex flex-col gap-2 border-t border-line pt-4",
              "[@media(min-width:48rem)_and_(min-height:40rem)]:mt-0 [@media(min-width:48rem)_and_(min-height:40rem)]:flex-row",
              "[@media(min-width:48rem)_and_(min-height:40rem)]:border-t-0 [@media(min-width:48rem)_and_(min-height:40rem)]:pt-0",
            )}
          >
            <Button
              ref={exportRef}
              variant={exportPrimary ? "primary" : "secondary"}
              held={held}
              aria-describedby={held ? describedBy : undefined}
              loading={busy === "export"}
              busyLabel={bar.busy.export}
              onClick={exportClick}
              className="w-full [@media(min-width:48rem)_and_(min-height:40rem)]:w-auto"
            >
              {bar.export}
            </Button>
            {!checked && (
              <Button
                ref={checkRef}
                variant="primary"
                held={!draft.may_act}
                aria-describedby={!draft.may_act ? describedBy : undefined}
                loading={busy === "check"}
                busyLabel={bar.busy.check}
                onClick={() => onAct("check")}
                className="w-full [@media(min-width:48rem)_and_(min-height:40rem)]:w-auto"
              >
                {bar.check}
              </Button>
            )}
          </div>
        </div>
      ) : (
        <p className="mt-3 text-caption text-ink-muted" data-read-only>
          {words.readOnly(author)}
        </p>
      )}
    </section>
  );
});

// The bar's "You opened" link moves focus to the Sources heading, in the page.
function focusSources() {
  requestAnimationFrame(() => document.getElementById(SOURCES_ID)?.focus());
}

// ── Export success ───────────────────────────────────────────────────────

export type SuccessProps = {
  draft: Draft;
  // Just exported in this visit: the panel fades in and its heading takes focus.
  fresh: boolean;
  headingRef?: Ref<HTMLHeadingElement>;
  // "These notes" in the teammate's heading: the kind's words.
  revisitTeammate?: (author: string, date: string, count: number, countText: string) => string;
  date: (iso: string) => string;
  className?: string;
};

export function ExportSuccess({ draft, fresh, headingRef, date, className }: SuccessProps) {
  const headingId = useId();
  const words = copy.draft.exported;
  const record = draft.export!;
  const footnotes = record.footnotes;
  const title = fresh
    ? words.title(footnotes, whole(footnotes))
    : draft.author.you
      ? words.revisitTitle(date(record.exported_at), footnotes, whole(footnotes))
      : words.revisitTeammate(record.by ?? "", date(record.exported_at), footnotes, whole(footnotes));
  const captions: Record<string, string> = {
    docx: words.word(footnotes, whole(footnotes)),
    pdf: words.pdf,
    csv: words.csv,
  };
  // The Word file first, then the evidence pack's PDF and CSV.
  const order = ["docx", "pdf", "csv"];
  const files = [...record.files].sort((a, b) => order.indexOf(extension(a.name)) - order.indexOf(extension(b.name)));
  return (
    <section
      aria-labelledby={headingId}
      data-export-success={fresh ? "fresh" : "revisit"}
      className={cx("flex gap-3 rounded-r-md border-l-4 border-success bg-success-bg p-4 md:p-6", fresh && "animate-[fade-in_200ms_ease-out]", className)}
    >
      <Check aria-hidden="true" className="size-5 shrink-0 text-success" />
      <div className="min-w-0">
        <h2 id={headingId} ref={headingRef} tabIndex={-1} className="text-title text-ink-heading focus:outline-none" data-numbers>
          {title}
        </h2>
        <p className="mt-2 max-w-[72ch] text-body text-ink">
          {!record.files_available
            ? words.revisitBodyMissing
            : fresh
              ? words.body(record.sources, whole(record.sources), record.disagreements > 0)
              : words.revisitBody}
        </p>
        {record.files_available ? (
          <ul aria-label={words.filesLabel} className="mt-4 flex flex-col gap-2">
            {files.map((file) => (
              <li key={file.name} className="text-small">
                <TextLink
                  href={fileHref(draft.draft_id, file.name)}
                  download={file.name}
                  aria-label={words.fileName(file.name, captions[extension(file.name)])}
                  className="block w-fit max-w-full font-mono wrap-anywhere"
                >
                  {file.name}
                </TextLink>
                <span className="mt-0.5 block text-caption text-ink-muted">{captions[extension(file.name)]}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-4 text-body text-ink">
            <Fill template={words.filesMissing} slots={{ id: <span className="font-mono">{draft.draft_id}</span> }} />
          </p>
        )}
      </div>
    </section>
  );
}

function extension(name: string): string {
  return name.slice(name.lastIndexOf(".") + 1);
}

// ── Discarded ────────────────────────────────────────────────────────────

export const DiscardedNotice = forwardRef(function DiscardedNotice(
  {
    sentence,
    restoring,
    may_act,
    failed,
    onRestore,
    sentenceRef,
    className,
  }: {
    className?: string;
    sentence: ReactNode;
    restoring: boolean;
    may_act: boolean;
    failed: boolean;
    onRestore: () => void;
    // The sentence takes focus after Discard, so a screen reader hears what happened first.
    sentenceRef?: Ref<HTMLSpanElement>;
  },
  ref: Ref<HTMLElement>,
) {
  return (
    <section ref={ref} aria-label={copy.draft.bar.label} aria-busy={restoring} data-discarded-notice className={cx("z-10 bg-page", STICKY, className)}>
      <Alert state="info">
        <span ref={sentenceRef} tabIndex={-1} className="focus:outline-none" data-discarded-sentence>
          {sentence}
        </span>
      </Alert>
      {failed && (
        <p role="alert" className="mt-2 flex items-start gap-2 text-small text-error">
          <CircleX aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-error-icon" />
          {copy.draft.bar.failed.restore}
        </p>
      )}
      <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2 pb-3">
        {may_act && (
          <Button variant="secondary" loading={restoring} busyLabel={copy.draft.bar.busy.restore} onClick={onRestore}>
            {copy.draft.discarded.restore}
          </Button>
        )}
        <TextLink href="/drafts">{copy.draft.discarded.link}</TextLink>
      </div>
    </section>
  );
});
