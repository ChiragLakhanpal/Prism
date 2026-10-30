// The draft bar (DESIGN.md section 5; the 35 brief, section 4.3), and what takes its place: the export
// success panel (4.6) and the discarded notice (4.7).
//
// The bar is a section named "Check and export" at the end of the document column, held to it, on
// surface with a 1px line on top. It sticks to the bottom of the window only when the window is at least
// 768 px wide and 640 px tall and the document column at least 30rem wide; otherwise it sits at the end of
// the page with its buttons stacked, because a sticky bar this tall would cover the note you are checking.
// It always has two rows. Row 1 says what exporting does and is not: the kind's lead sentence, the fixed
// consequence sentence, how many sources you opened (a link to the Sources list), and the hold line when
// export is held. Row 2 has Discard at the left edge, set apart
// by the whole row, and Export to Word and the solid button at the right. In Draft the solid button is
// Mark as checked and Export to Word is held; once checked, and with no hold left, Export to Word is the
// solid button. Only the author acts: a teammate reads one line instead of the buttons. Once the notes are checked, a
// line after row 1 says who checked them and when (ticket 103). Its bottom padding adds the phone's safe area.
//
// A busy button shows its busy label within 100 ms and keeps its width, and the bar is aria-busy until
// the server answers. The state changes only when the server confirms it. A status line announces each
// change, and a failure shows as a line between the rows.
import { forwardRef, Fragment, useEffect, useId, useRef, type ReactNode, type Ref } from "react";
import { Check, CircleX, Info } from "lucide-react";
import { copy } from "../copy";
import { cx } from "../lib/cx";
import type { Action, Draft } from "../lib/drafts";
import { fileHref } from "../lib/drafts";
import { formatCount, formatDate, formatNumber } from "../lib/format";
import { Alert } from "./Alert";
import { Button } from "./Button";
import { Fill } from "./Fill";
import { SOURCES_ID } from "./SourcesList";
import { TextLink } from "./TextLink";
import { previewReason } from "../lib/view";

const whole = (value: number) => formatNumber(value, { compact: false });
// After the notes are marked as checked, Export to Word takes Mark as checked's place under the pointer.
// For this long after it turns solid, a click on it is the end of the click that checked the notes.
const SETTLE_MS = 400;

// Sticky only where the bar-sticks variant holds (app.css): a window at least 768 px wide and 640 px tall,
// and a document column at least 30rem wide. Every class name is written out whole, so Tailwind finds it.
export const STICKY = "bar-sticks:sticky bar-sticks:bottom-0";
// The room above the bar, or the discarded notice, at the end of its column. Where the bar sticks, the box floats 16 px
// above it and rides up with it as it lets go at the column's end (ticket 113), so the room is the box's 56 px (ticket
// 127), its 16 px gap and 8 px more, or the box would sit on the draft's last line for good (app.css, ask-room).
export const BAR_ROOM = "mt-8 bar-sticks:ask-room";
// The fixed consequence sentence, with each hyphenated word kept whole at a line end, so its key word never
// breaks as "no-" and "objection". The draft page's skeleton shows it too, since it is true before the
// draft loads (the 35 brief, section 8.3).
export function Consequence() {
  const parts = copy.draft.bar.consequence.split(/(\S+-\S+)/);
  return (
    <>
      {parts.map((part, index) =>
        index % 2 === 1 ? (
          <span key={index} className="whitespace-nowrap">
            {part}
          </span>
        ) : (
          part
        ),
      )}
    </>
  );
}

// The bar's two rows of buttons: stacked where the bar does not stick (Discard, a 1px rule with 16 px above
// and below, then the full-width buttons 8 px apart), and one row with Discard at the far left where it
// does (the bar-sticks variant in app.css). The draft page's skeleton draws its pills with the same classes,
// so they stand where the buttons will.
export const BAR_BUTTONS = cx("mt-3 flex flex-col", "bar-sticks:flex-row bar-sticks:items-center bar-sticks:justify-between bar-sticks:gap-2");
export const BAR_MAIN = cx(
  "mt-4 flex flex-col gap-2 border-t border-line pt-4",
  "bar-sticks:mt-0 bar-sticks:flex-row bar-sticks:border-t-0 bar-sticks:pt-0",
);
export const BAR_BUTTON_WIDTH = "w-full bar-sticks:w-auto";

// The discarded notice takes the bar's place, so when it sticks it ends the scrolling notes the same way: a
// 1px rule above it and 12 px of the page above and below the alert, so no text is cut at the alert's edge.
const STICKY_FRAME = "bar-sticks:border-t bar-sticks:border-line bar-sticks:py-3";

export type BarProps = {
  draft: Draft;
  // The kind's words: the lead sentences, the hold line and its clauses, and the teammate's line.
  words: {
    holdNotChecked: string;
    holdClause: string;
    holdCompose: string;
    readOnly: (author: string) => string;
    // Planned dates (ticket 38): the export button names what it makes, and the opened line what was opened.
    exportLabel?: string;
    openedLine?: (opened: string, total: string) => string;
  };
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

// The hold line (the 36 brief, section 4.5): every hold left, in the kind's registry order, as one sentence. One hold
// left that is "not checked yet" is the kind's own sentence; a preview is its own sentence; otherwise "Before you
// export them, {clauses}.", two clauses joined by "and", three or more by commas with ", and" before the last. Each
// clause except "mark ... as checked" links to the first unfinished item of its kind: the link moves focus there and
// scrolls it clear of the sticky header and bar.
export function HoldLine({ draft, words }: { draft: Draft; words: BarProps["words"] }): ReactNode {
  const holds = draft.holds;
  if (holds.length === 0) return null;
  const bar = copy.draft.bar;
  const preview = holds.find((hold) => hold.key === "preview");
  if (preview) return previewReason("mark_checked") ?? (bar.hold.preview as string);
  if (holds.length === 1 && holds[0].key === "notChecked") return words.holdNotChecked;
  const clauses: ReactNode[] = holds.map((hold) => {
    if (hold.key === "notChecked") return words.holdClause;
    const forms = bar.hold[hold.copy];
    const text = typeof forms === "string" ? forms : (
      <Fill template={hold.left === 1 ? forms.one : forms.many} slots={{ count: formatCount(hold.left) }} />
    );
    if (!hold.first_anchor) return text;
    return (
      <TextLink key={hold.key} href={`#${hold.first_anchor}`} onClick={(event) => focusAnchor(event, hold.first_anchor!)} data-hold-link={hold.key}>
        {text}
      </TextLink>
    );
  });
  const joined: ReactNode[] = [];
  clauses.forEach((clause, index) => {
    if (index > 0) {
      const last = index === clauses.length - 1;
      joined.push(clauses.length === 2 ? bar.holdJoin : last ? bar.holdLastComma : bar.holdComma);
    }
    joined.push(<Fragment key={index}>{clause}</Fragment>);
  });
  return <Fill template={words.holdCompose} slots={{ clauses: <>{joined}</> }} />;
}

// A hold line's link: focus the first unfinished item and bring it out from under the sticky header and bar.
function focusAnchor(event: React.MouseEvent<HTMLAnchorElement>, anchor: string) {
  const target = document.getElementById(anchor);
  if (!target) return;
  event.preventDefault();
  target.focus({ preventScroll: true });
  target.scrollIntoView({ block: "center" });
}

export const DraftBar = forwardRef(function DraftBar(
  { draft, words, opened, busy, failed, status, onAct, exportRef, checkRef, notice, className }: BarProps,
  ref: Ref<HTMLElement>,
) {
  const bar = copy.draft.bar;
  const author = draft.author.name ?? "";
  const mine = draft.author.you;
  const hold = mine ? HoldLine({ draft, words }) : null;
  const checked = draft.state === "checked";
  // The solid button: Export to Word once checked with no hold left, else Mark as checked. Once checked, Export to
  // Word takes the primary position at once, held until the last hold lifts (the 36 brief, section 4.5).
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
  const decided = checked ? checkedLine(draft) : null;
  return (
    <section
      ref={ref}
      aria-label={bar.label}
      aria-busy={busy !== null}
      data-draft-bar={draft.state}
      data-sticky="bottom"
      className={cx("z-10 border-t border-line bg-surface px-4 pt-3 foot-safe md:px-6", STICKY, className)}
    >
      <p className="max-w-[80ch] text-small text-ink" data-bar-lead>
        {/* The h1 names the draft, so the bar opens on its fixed sentence (ticket 126; rule 19). */}
        <Consequence />{" "}
        <TextLink href={`#${SOURCES_ID}`} onClick={focusSources} className="whitespace-nowrap" data-opened-link>
          {(words.openedLine ?? bar.opened)(whole(opened), whole(draft.opened.of))}
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
      {/* Who checked the notes, and when (ticket 103; plan 9, pattern 9): once checked, the hold line gives way to this
          line, by role, with the server's date. It changes at once, with nothing that fades. */}
      {decided && (
        <p className="mt-1 text-small font-semibold text-ink-heading" data-decided-line>
          {decided}
        </p>
      )}
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
        <div className={BAR_BUTTONS}>
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
          <div className={BAR_MAIN}>
            <Button
              ref={exportRef}
              variant={checked ? "primary" : "secondary"}
              held={held}
              aria-describedby={held ? describedBy : undefined}
              loading={busy === "export"}
              busyLabel={bar.busy.export}
              onClick={exportClick}
              className={BAR_BUTTON_WIDTH}
            >
              {words.exportLabel ?? bar.export}
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
                className={BAR_BUTTON_WIDTH}
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

// "Checked by you on October 23, 2026.", or the teammate's name in its place: the Drafts list's words for the same act
// (copy.draft.tab), with the date the server recorded. Null before the notes are checked.
export function checkedLine(draft: Draft): string | null {
  if (!draft.checked) return null;
  const date = formatDate(draft.checked.at.slice(0, 10));
  const words = copy.draft.tab;
  return draft.checked.you ? words.checkedYou(date) : words.checkedOther(draft.checked.by ?? draft.author.name ?? "", date);
}

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
        <h2 id={headingId} ref={headingRef} tabIndex={-1} className="text-h2 text-ink-heading focus:outline-none" data-numbers>
          {title}
        </h2>
        {/* The bar's fixed sentence already says exporting sends nothing (rule 19), so a revisit with its files says
            nothing more here (ticket 126). */}
        {(!record.files_available || fresh) && (
          <p className="mt-2 max-w-[72ch] text-body text-ink">
            {!record.files_available ? words.revisitBodyMissing : words.body(record.sources, whole(record.sources), record.disagreements > 0)}
          </p>
        )}
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
    <section ref={ref} aria-label={copy.draft.bar.label} aria-busy={restoring} data-discarded-notice data-sticky="bottom" className={cx("z-10 bg-page", STICKY, STICKY_FRAME, className)}>
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
