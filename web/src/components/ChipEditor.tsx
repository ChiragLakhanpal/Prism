// A criterion chip's editor (the 15 brief, section 4): a popover anchored 8 px under its chip from a window of
// 768 px, a bottom sheet below that. Top to bottom: the field's label as its heading, where the value came
// from, STEP's field name and value word for word, the control the field's kind calls for, whether a change
// updates the past range, and the actions. A commit closes the editor and gives focus back to the chip;
// Escape, the close button or a press outside closes it with nothing changed.
//
// Controls by kind: a choice is a list of radio options 40 px tall, and a choice that takes old method names,
// or the country, has a text field above its options that narrows them, so you can type: an old name such as
// ICB lists the method it is now. Text, an amount, a count and months are text fields committed with "Use
// this" or Enter. A computed value shows its options only after "Set it yourself".
import { useEffect, useId, useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import { X } from "lucide-react";
import { copy } from "../copy";
import { cx } from "../lib/cx";
import { formatNumber } from "../lib/format";
import type { Change, FieldValue, FormField, PackageForm } from "../lib/packages";
import { Button } from "./Button";
import { monthsText, stepValue, valueText } from "./Criteria";

const words = copy.packageWorkspace.editor;

// "15 million", "15m", "15,000,000", "US$15 million" and "$15 M" all read as 15,000,000.
export function parseAmount(raw: string): number | null {
  const text = raw.trim().toLowerCase().replace(/^us\$|^\$|^usd/, "").replace(/usd$/, "").replace(/,/g, "").trim();
  const match = /^(\d+(?:\.\d+)?)\s*(million|mn|m|billion|bn|b|thousand|k)?$/.exec(text);
  if (!match) return null;
  const scale = { million: 1e6, mn: 1e6, m: 1e6, billion: 1e9, bn: 1e9, b: 1e9, thousand: 1e3, k: 1e3 }[match[2] ?? ""] ?? 1;
  const amount = Math.round(Number(match[1]) * scale * 100) / 100;
  return amount > 0 ? amount : null;
}

// The field's text as the editor opens: a number alone, with its unit beside the field, so "Use this" commits the
// value as it is.
function initialText(field: FormField, value: string | number | null, form: PackageForm): string {
  if (value === null) return "";
  if (field.kind === "amount") return formatNumber(Number(value), { compact: false });
  if (field.kind === "months") return monthsText(Number(value));
  if (field.kind === "count") return String(value);
  if (field.kind === "choice" || field.kind === "country") return "";
  return valueText(field, value, form);
}

type Option = { value: string; label: string; caption?: string; send: string };

function optionsFor(field: FormField, form: PackageForm, typed: string): Option[] {
  const text = typed.trim().toLowerCase();
  if (field.kind === "country") {
    return form.countries
      .filter((country) => !text || country.name.toLowerCase().includes(text) || country.code.toLowerCase() === text)
      .map((country) => ({ value: country.code, label: country.name, send: country.code }));
  }
  const listed = field.options
    .filter((option) => !text || option.label.toLowerCase().includes(text) || option.value.toLowerCase().includes(text))
    .map((option) => ({ value: option.value, label: option.label, send: option.value }));
  // An old method name lists the method it is now, sent as typed, so the server also sets its market approach.
  const old = field.aliases ? form.aliases[typed.trim().replace(/\s+/g, " ").replace(/[\u2018\u2019]/g, "'").toUpperCase()] : undefined;
  if (old) {
    const now = field.options.find((option) => option.value === old.method);
    if (now) return [{ value: now.value, label: now.label, caption: words.oldName(typed.trim()), send: typed.trim() }, ...listed.filter((one) => one.value !== now.value)];
  }
  return listed;
}

// Where the value came from; a computed value adds its rule, as the note states it (the 15 brief, section 7.6).
function provenanceLine(field: FormField, value: FieldValue, form: PackageForm, rule: ReactNode): ReactNode {
  if (value.value === null) return words.empty;
  if (value.provenance === "sentence") return words.fromSentence;
  if (value.provenance === "default") return words.fromDefault;
  if (value.provenance === "unlisted") return words.fromUnlisted(value.read_as ?? "");
  if (value.provenance === "guess") return words.fromGuess;
  if (value.provenance === "computed") return rule ? <>{words.fromComputed} {rule}</> : words.fromComputed;
  return field.source === "computed" && value.computed !== null
    ? `${words.fromYou} ${words.thresholdsGive(valueText(field, value.computed, form))}`
    : words.fromYou;
}

export function EditorBody({
  field,
  value,
  form,
  approximate,
  preview,
  headingId,
  rule = null,
  onCommit,
}: {
  field: FormField;
  value: FieldValue;
  form: PackageForm;
  approximate: boolean;
  preview: boolean;
  headingId: string;
  // A computed field's rule sentence, for its provenance line.
  rule?: ReactNode;
  onCommit: (change: Change) => void;
}) {
  const [text, setText] = useState(() => initialText(field, value.value, form));
  // Whether the person changed the value: on a guess, "Use this" would do what "Keep" does until then (ticket 60).
  const [edited, setEdited] = useState(false);
  const guessed = value.provenance === "guess" && value.value !== null;
  const [error, setError] = useState<string | null>(null);
  const [settingComputed, setSettingComputed] = useState(false);
  const inputId = useId();
  const errorId = useId();
  const readBackId = useId();
  const listName = useId();
  const choosing = field.kind === "choice" || field.kind === "country";
  const typing = field.kind === "country" || (field.kind === "choice" && field.aliases);
  const computedHidden = field.source === "computed" && value.provenance === "computed" && !settingComputed;
  const step = stepValue(field, value.value);
  const amount = field.kind === "amount" ? parseAmount(text) : null;

  const commitText = () => {
    const raw = text.trim();
    if (field.kind === "amount") {
      if (amount === null) return setError(copy.packageWorkspace.editor.errors.amount);
      return onCommit({ field: field.key, action: "set", value: amount });
    }
    if (field.kind === "months") {
      const months = Number(raw.replace(",", "."));
      if (!/^\d+([.,]\d)?$/.test(raw) || months < 0.5 || months > form.max_months) {
        return setError(words.errors.months(formatNumber(form.max_months, { compact: false })));
      }
      return onCommit({ field: field.key, action: "set", value: months });
    }
    if (field.kind === "count") {
      const count = Number(raw);
      if (!/^\d+$/.test(raw) || count < 1 || count > form.max_count) return setError(words.errors.count(formatNumber(form.max_count, { compact: false })));
      return onCommit({ field: field.key, action: "set", value: count });
    }
    if (!raw) return setError(words.errors.text);
    return onCommit({ field: field.key, action: "set", value: raw });
  };

  const options = choosing ? optionsFor(field, form, text) : [];
  // An arrow key moves between the options, which a radio group would also check; only a press, Space or Enter
  // chooses, so arrowing past an option never commits it.
  const arrowed = useRef(false);
  const onTypeKey = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key !== "Enter") return;
    event.preventDefault();
    if (choosing) {
      if (options.length === 0) return setError(field.kind === "country" ? words.errors.country : words.errors.choice);
      return onCommit({ field: field.key, action: "set", value: options[0].send });
    }
    commitText();
  };

  return (
    <div className="flex flex-col gap-3">
      <h2 id={headingId} className="text-body font-bold text-ink-heading">
        {field.label}
      </h2>
      <p className="text-caption text-ink">{provenanceLine(field, value, form, rule)}</p>
      {step && field.step_field && <p className="text-caption text-ink-muted">{words.stepLine(field.step_field, step)}</p>}
      {preview ? (
        <p className="text-caption text-ink-muted">{copy.packageWorkspace.preview}</p>
      ) : (
        <>
          {!computedHidden && typing && (
            <input
              id={inputId}
              type="text"
              autoComplete="off"
              aria-label={field.label}
              aria-describedby={error ? errorId : undefined}
              aria-invalid={error ? true : undefined}
              value={text}
              onChange={(event) => {
                setText(event.target.value);
                setError(null);
              }}
              onKeyDown={onTypeKey}
              className="h-11 w-full rounded-sm border border-line-strong bg-surface px-3 text-body text-ink"
            />
          )}
          {!computedHidden && choosing && (
            <div
              role="radiogroup"
              aria-labelledby={headingId}
              aria-describedby={error ? errorId : undefined}
              className="flex max-h-72 flex-col overflow-y-auto"
              data-options
              onKeyDown={(event) => {
                arrowed.current = event.key.startsWith("Arrow");
              }}
            >
              {options.map((option) => {
                const checked = option.value === value.value && !option.caption;
                return (
                  // The whole 40 px row is the target. The radio itself is hidden from sight but not from the
                  // keyboard or a screen reader; the row draws its circle and its focus ring.
                  <label
                    key={`${option.value}-${option.send}`}
                    data-focus-ring
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
                      onChange={() => {
                        if (arrowed.current) arrowed.current = false;
                        else onCommit({ field: field.key, action: "set", value: option.send });
                      }}
                      onClick={(event) => {
                        // A press on the option already chosen chooses it again, such as a computed value you now
                        // set yourself; Enter does the same from the keyboard.
                        if (checked && event.detail !== 0) onCommit({ field: field.key, action: "set", value: option.send });
                      }}
                      onKeyDown={(event) => {
                        if (event.key !== "Enter") return;
                        event.preventDefault();
                        onCommit({ field: field.key, action: "set", value: option.send });
                      }}
                      className="peer sr-only"
                    />
                    <span
                      aria-hidden="true"
                      className={cx(
                        "flex size-4 shrink-0 items-center justify-center rounded-full border-2",
                        checked ? "border-primary" : "border-line-strong",
                      )}
                    >
                      {checked && <span className="size-2 rounded-full bg-primary" />}
                    </span>
                    <span className="min-w-0">
                      <span className="block">{option.label}</span>
                      {option.caption && <span className="block text-caption text-ink-muted">{option.caption}</span>}
                    </span>
                  </label>
                );
              })}
            </div>
          )}
          {!choosing && (
            <div className="flex flex-col gap-1">
              <div className="flex items-center gap-2">
                <input
                  id={inputId}
                  type="text"
                  inputMode={field.kind === "count" || field.kind === "months" ? "decimal" : undefined}
                  autoComplete="off"
                  aria-label={field.label}
                  aria-describedby={[error && errorId, field.kind === "amount" && amount !== null && readBackId].filter(Boolean).join(" ") || undefined}
                  aria-invalid={error ? true : undefined}
                  value={text}
                  maxLength={field.kind === "text" ? form.text_limit : undefined}
                  onChange={(event) => {
                    setText(event.target.value);
                    setEdited(true);
                    setError(null);
                  }}
                  onKeyDown={onTypeKey}
                  className={cx(
                    "h-11 min-w-0 flex-1 rounded-sm border bg-surface px-3 text-body text-ink",
                    field.kind === "months" || field.kind === "count" ? "max-w-[88px] text-right tabular-nums" : "",
                    error ? "border-error-icon" : "border-line-strong",
                  )}
                />
                {field.kind === "months" && <span className="text-small text-ink">{words.unit}</span>}
                {field.kind === "count" && (field.unit || field.unit_one) && (
                  <span className="text-small text-ink">{(Number(text) === 1 ? field.unit_one : field.unit) ?? field.unit}</span>
                )}
              </div>
              {field.kind === "amount" && amount !== null && !error && (
                <p id={readBackId} className="text-caption text-ink-muted" data-read-back>
                  {words.amountReadBack(formatNumber(amount, { compact: false }))}
                </p>
              )}
            </div>
          )}
          {error && (
            <p id={errorId} className="text-caption text-error" data-editor-error>
              {error}
            </p>
          )}
          <p className="text-caption text-ink-muted">{field.picks ? words.picks : words.doesNotPick}</p>
          <div className="flex flex-wrap gap-2">
            {!choosing && (!guessed || edited) && (
              <Button variant="secondary" onClick={commitText}>
                {words.use}
              </Button>
            )}
            {guessed && (
              <Button variant="secondary" onClick={() => onCommit({ field: field.key, action: "keep" })}>
                {words.keep(valueText(field, value.value, form, approximate))}
              </Button>
            )}
            {computedHidden && (
              <Button variant="ghost" flush onClick={() => setSettingComputed(true)}>
                {words.setYourself}
              </Button>
            )}
            {field.source === "computed" && value.provenance === "you" && (
              <Button variant="secondary" onClick={() => onCommit({ field: field.key, action: "use_computed" })}>
                {words.useComputed}
              </Button>
            )}
            {field.optional && value.value !== null && (
              <Button variant="ghost" flush onClick={() => onCommit({ field: field.key, action: "remove" })}>
                {words.remove}
              </Button>
            )}
          </div>
        </>
      )}
    </div>
  );
}

// Below 768 px: a bottom sheet over a scrim, modal, with a 44 px close button. Focus moves into it and stays
// there until it closes, and Escape closes it.
export function EditorSheet({ labelledBy, onClose, children }: { labelledBy: string; onClose: () => void; children: ReactNode }) {
  const panel = useRef<HTMLDivElement>(null);
  // The page hands a new onClose on each of its renders, such as when a save answers; the sheet reads the
  // latest one, so a render never moves focus back to the sheet's first control.
  const close = useRef(onClose);
  close.current = onClose;
  useEffect(() => {
    const element = panel.current;
    const first = element?.querySelector<HTMLElement>("input, button:not([data-sheet-close])");
    (first ?? element)?.focus();
    const onKey = (event: globalThis.KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        event.stopPropagation();
        close.current();
      }
      if (event.key !== "Tab" || !element) return;
      const focusable = [...element.querySelectorAll<HTMLElement>("button, input, [tabindex='0']")].filter((one) => !one.hasAttribute("disabled"));
      if (focusable.length === 0) return;
      const [head, tail] = [focusable[0], focusable[focusable.length - 1]];
      if (event.shiftKey && document.activeElement === head) {
        event.preventDefault();
        tail.focus();
      } else if (!event.shiftKey && document.activeElement === tail) {
        event.preventDefault();
        head.focus();
      }
    };
    document.addEventListener("keydown", onKey, true);
    const root = document.documentElement;
    const before = root.style.overflow;
    root.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey, true);
      root.style.overflow = before;
    };
  }, []);
  return (
    <div className="fixed inset-0 z-50 flex flex-col justify-end bg-scrim" onClick={(event) => event.target === event.currentTarget && close.current()}>
      <div
        ref={panel}
        role="dialog"
        aria-modal="true"
        aria-labelledby={labelledBy}
        tabIndex={-1}
        data-chip-editor="sheet"
        className="max-h-[80vh] animate-sheet-in overflow-y-auto rounded-t-lg bg-surface px-4 pt-2 pb-6"
        style={{ paddingBottom: "max(1.5rem, env(safe-area-inset-bottom))" }}
      >
        <div className="flex justify-end">
          <Button variant="ghost" icon={X} iconOnly onClick={onClose} data-sheet-close>
            {words.close}
          </Button>
        </div>
        {children}
      </div>
    </div>
  );
}
