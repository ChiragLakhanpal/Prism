// The fill-in chip (ticket 36; the 36 brief, section 4.3; DESIGN.md section 5): a field only a person fills, such as
// a suggested PPSD row's Risk Owner, or in the Long Form its ratings, score and stage. It is brief 15's criterion
// chip and chip editor, so Prism has one pattern for "choose this to set a value": empty, it is the plus chip
// ("Set the owner", or "Set" under a column label); set, it is the typed chip with the value; open, it takes the tint
// and an inset ring, so its size never changes. Its editor is a popover 8 px under it from a window of 768 px, and a
// bottom sheet below that. A commit shows the value at once, closes the editor and gives focus back to the chip; a
// failed save puts the last saved value back and offers Try again with your text still in it. Removing a value says
// "Remove", never the word rule 19 bans. Read-only (a teammate, an exported or discarded draft, a preview), it is
// plain text, or "Not set", with no tab stop.
import { useEffect, useId, useRef, useState, type KeyboardEvent } from "react";
import * as RadixPopover from "@radix-ui/react-popover";
import { CircleX, Plus } from "lucide-react";
import { copy } from "../copy";
import { cx } from "../lib/cx";
import type { PpsdColumn, PpsdView } from "../lib/drafts";
import { formatCount } from "../lib/format";
import { Button } from "./Button";
import { EditorSheet } from "./ChipEditor";
import { Fill } from "./Fill";
import { POPOVER } from "./Popover";

const words = copy.fill;
const NARROW = "(width < 48rem)";
// The owner's counter shows from this many characters before the limit (brief 23's counter).
const COUNTER_FROM = 20;

function useNarrowWindow(): boolean {
  const [narrow, setNarrow] = useState(() => window.matchMedia(NARROW).matches);
  useEffect(() => {
    const query = window.matchMedia(NARROW);
    const update = () => setNarrow(query.matches);
    query.addEventListener("change", update);
    return () => query.removeEventListener("change", update);
  }, []);
  return narrow;
}

// The value as the chip shows it: a rating with its label ("4, High"), anything else as set.
export function shownValue(column: PpsdColumn, value: string, ppsd: PpsdView): string {
  if (column.control !== "rating") return value;
  const level = ppsd.ratings.find((one) => String(one.value) === value);
  return level ? words.ratingOption(level.value, level.label) : value;
}

export type FillChipProps = {
  // The anchor id the bar's hold line links to: fill-{row}-{field}.
  id: string;
  column: PpsdColumn;
  ppsd: PpsdView;
  riskLabel: string;
  value: string | null;
  // The author, in Draft or Checked by you, staff view: the chip edits. Anyone else reads plain text.
  editable: boolean;
  onSave: (value: string | null) => Promise<boolean>;
};

export function FillChip({ id, column, ppsd, riskLabel, value, editable, onSave }: FillChipProps) {
  const narrow = useNarrowWindow();
  const [open, setOpen] = useState(false);
  // The value shown while a save is on its way, and whether the last save failed (with the text tried).
  const [pending, setPending] = useState<{ value: string | null } | null>(null);
  const [failed, setFailed] = useState<string | null | undefined>(undefined);
  const [draftText, setDraftText] = useState<string | null>(null);
  const chip = useRef<HTMLButtonElement>(null);
  const headingId = useId();
  const shown = pending ? pending.value : value;

  if (!editable) {
    return (
      <span className={cx("text-small", shown ? "text-ink" : "text-ink-muted")} data-fill-read-only={column.key}>
        {shown ? shownValue(column, shown, ppsd) : words.readOnlyEmpty}
      </span>
    );
  }

  const close = () => {
    setOpen(false);
    requestAnimationFrame(() => chip.current?.focus());
  };
  const commit = async (next: string | null) => {
    setPending({ value: next });
    setFailed(undefined);
    setOpen(false);
    requestAnimationFrame(() => chip.current?.focus());
    const saved = await onSave(next);
    setPending(null);
    if (!saved) {
      setFailed(next);
      setDraftText(next);
    } else setDraftText(null);
  };

  const empty = shown === null || shown === "";
  const label = column.key === "risk_owner" ? words.ownerEmpty : words.ratingEmpty;
  const name = empty
    ? column.key === "risk_owner" ? words.nameOwnerEmpty(riskLabel) : words.nameEmpty(column.header, riskLabel)
    : words.nameSet(column.header, riskLabel, shownValue(column, shown!, ppsd));
  const button = (
    <button
      ref={chip}
      id={id}
      type="button"
      aria-haspopup="dialog"
      aria-expanded={open}
      aria-label={name}
      data-fill-chip={column.key}
      data-look={empty ? "empty" : "set"}
      onClick={() => setOpen((now) => !now)}
      className={cx(
        "inline-flex min-h-8 max-w-full items-center gap-1 rounded-pill border border-line-strong bg-surface px-3 py-1 text-left text-small",
        "transition-paint duration-150 hover:bg-tint-hover",
        empty ? "text-primary" : "text-ink",
        open && "bg-tint shadow-[inset_0_0_0_1px_var(--color-primary)]",
      )}
    >
      {empty && <Plus aria-hidden="true" className="size-4 shrink-0" />}
      <span className="min-w-0 wrap-break-word">{empty ? label : shownValue(column, shown!, ppsd)}</span>
    </button>
  );
  const body = (
    <FillEditor
      column={column}
      ppsd={ppsd}
      riskLabel={riskLabel}
      value={shown}
      initial={draftText}
      headingId={headingId}
      onCommit={commit}
    />
  );
  const error = failed !== undefined && (
    <span className="mt-1 flex flex-wrap items-center gap-x-2 text-caption text-error" data-fill-failed>
      <CircleX aria-hidden="true" className="size-4 shrink-0 text-error-icon" />
      {words.saveFailed}
      <Button variant="ghost" flush onClick={() => setOpen(true)} className="min-h-6">
        {words.tryAgain}
      </Button>
    </span>
  );
  if (narrow) {
    return (
      <span className="inline-flex max-w-full flex-col items-start">
        {button}
        {error}
        {open && (
          <EditorSheet labelledBy={headingId} onClose={close}>
            {body}
          </EditorSheet>
        )}
      </span>
    );
  }
  return (
    <span className="inline-flex max-w-full flex-col items-start">
      <RadixPopover.Root open={open} onOpenChange={(next) => !next && setOpen(false)}>
        <RadixPopover.Anchor asChild>
          <span className="inline-flex max-w-full">{button}</span>
        </RadixPopover.Anchor>
        <RadixPopover.Portal>
          <RadixPopover.Content
            role="dialog"
            aria-labelledby={headingId}
            side="bottom"
            align="start"
            sideOffset={8}
            collisionPadding={16}
            data-fill-editor="popover"
            onCloseAutoFocus={(event) => {
              event.preventDefault();
              chip.current?.focus();
            }}
            onInteractOutside={(event) => {
              if ((event.target as Element | null)?.closest?.("[data-fill-chip]")) event.preventDefault();
            }}
            className={cx(POPOVER, "w-[min(320px,calc(100vw-32px))] p-4")}
          >
            {body}
          </RadixPopover.Content>
        </RadixPopover.Portal>
      </RadixPopover.Root>
      {error}
    </span>
  );
}

// The editor's body: the field's name as its heading, the row it is for, then the control the field calls for, and
// the buttons. A rating or a stage is a list of options, and choosing one commits it; the owner and the score are
// text fields committed with their button or Enter.
function FillEditor({
  column,
  ppsd,
  riskLabel,
  value,
  initial,
  headingId,
  onCommit,
}: {
  column: PpsdColumn;
  ppsd: PpsdView;
  riskLabel: string;
  value: string | null;
  initial: string | null;
  headingId: string;
  onCommit: (value: string | null) => void;
}) {
  const [text, setText] = useState(initial ?? value ?? "");
  const [error, setError] = useState<string | null>(null);
  const inputId = useId();
  const hintId = useId();
  const errorId = useId();
  const counterId = useId();
  const listName = useId();
  const limit = column.max_length ?? 120;
  const options =
    column.control === "rating"
      ? ppsd.ratings.map((level) => ({ value: String(level.value), label: words.ratingOption(level.value, level.label) }))
      : column.control === "stage"
        ? ppsd.stages.map((stage) => ({ value: stage, label: stage }))
        : null;
  const remove =
    column.key === "risk_owner" ? words.ownerRemove : column.control === "score" ? words.scoreRemove : column.control === "stage" ? words.stageRemove : words.ratingRemove;

  const submit = () => {
    const raw = text.trim();
    if (column.control === "score") {
      const { minimum, maximum } = ppsd.score;
      if (!/^\d+$/.test(raw) || Number(raw) < minimum || Number(raw) > maximum) {
        return setError(words.scoreError(String(minimum), String(maximum)));
      }
      return onCommit(raw);
    }
    if (!raw) return setError(column.key === "risk_owner" ? words.ownerError : words.stageError);
    return onCommit(raw);
  };
  const onKey = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key !== "Enter") return;
    event.preventDefault();
    submit();
  };
  const left = limit - text.length;
  const describedBy = [error ? errorId : null, hintId, left <= COUNTER_FROM ? counterId : null].filter(Boolean).join(" ");

  return (
    <div className="flex flex-col gap-3" data-fill-editor-body={column.key}>
      <h2 id={headingId} className="text-body font-bold text-ink-heading">
        {column.header}
      </h2>
      <p className="text-caption text-ink">{words.editorRow(riskLabel)}</p>
      {options ? (
        <div role="radiogroup" aria-labelledby={headingId} className="flex max-h-72 flex-col overflow-y-auto" data-options>
          {options.map((option) => {
            const checked = option.value === value;
            return (
              <label
                key={option.value}
                className={cx(
                  "flex min-h-10 cursor-pointer items-center gap-3 rounded-md px-2 text-small text-ink hover:bg-tint-hover",
                  "has-[input:focus-visible]:outline-2 has-[input:focus-visible]:outline-offset-2",
                  "has-[input:focus-visible]:outline-focus has-[input:focus-visible]:outline-solid",
                  checked && "bg-tint",
                )}
              >
                <input
                  type="radio"
                  name={listName}
                  checked={checked}
                  onChange={() => onCommit(option.value)}
                  onKeyDown={(event) => {
                    if (event.key !== "Enter") return;
                    event.preventDefault();
                    onCommit(option.value);
                  }}
                  className="peer sr-only"
                />
                <span
                  aria-hidden="true"
                  className={cx("flex size-4 shrink-0 items-center justify-center rounded-full border-2", checked ? "border-primary" : "border-line-strong")}
                >
                  {checked && <span className="size-2 rounded-full bg-primary" />}
                </span>
                <span className="min-w-0">{option.label}</span>
              </label>
            );
          })}
        </div>
      ) : (
        <div className="flex flex-col gap-1">
          <label htmlFor={inputId} className="text-small font-semibold text-ink">
            {column.key === "risk_owner" ? words.ownerLabel : words.scoreLabel}
          </label>
          <input
            id={inputId}
            type="text"
            inputMode={column.control === "score" ? "numeric" : undefined}
            autoComplete="off"
            aria-describedby={describedBy}
            aria-invalid={error ? true : undefined}
            value={text}
            maxLength={limit}
            onChange={(event) => {
              setText(event.target.value);
              setError(null);
            }}
            onKeyDown={onKey}
            className={cx("h-11 w-full rounded-sm border bg-surface px-3 text-body text-ink", error ? "border-error-icon" : "border-line-strong")}
          />
          <p id={hintId} className="text-caption text-ink-muted">
            {column.key === "risk_owner" ? words.ownerHint : <Fill template={words.scoreHint} slots={{ definition: ppsd.score.definition }} />}
          </p>
          {column.key === "risk_owner" && left <= COUNTER_FROM && (
            <p id={counterId} className="text-caption text-ink-muted" data-counter>
              {words.counter(formatCount(left))}
            </p>
          )}
          {error && (
            <p id={errorId} className="text-caption text-error" data-fill-error>
              {error}
            </p>
          )}
        </div>
      )}
      <div className="flex flex-wrap gap-2">
        {!options && (
          <Button variant="secondary" onClick={submit}>
            {column.key === "risk_owner" ? words.ownerSubmit : words.scoreSubmit}
          </Button>
        )}
        {value && (
          <Button variant="ghost" flush onClick={() => onCommit(null)}>
            {remove}
          </Button>
        )}
      </div>
    </div>
  );
}
