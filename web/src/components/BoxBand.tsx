// The white band under the navy bar (DESIGN.md section 5): the one box, which "/" focuses from
// anywhere outside a text field, and the data-freshness stamp. From 768 px the box spans
// columns 1 to 8 and the stamp columns 9 to 12, right-aligned; below that the stamp sits
// under the box. Fixed slots keep the band from moving while the stamp loads.
//
// The box is a combobox (WAI-ARIA's list autocomplete with automatic selection): as you type, a
// list under it says what Enter will do, laid over the page so the band never grows. Its options
// come from the intent rules (web/src/lib/intents.ts, through IntentBox.tsx); this file draws them.
// On a project or package page the box holds a removable scope chip.
import { useEffect, useId, useRef, useState, type KeyboardEvent as ReactKeyboardEvent, type ReactNode, type RefObject } from "react";
import { CircleX, Search, X, type LucideIcon } from "lucide-react";
import { copy } from "../copy";
import { cx } from "../lib/cx";
import { Fill } from "./Fill";
import { DOTTED_UNDERLINE } from "./Popover";
import { Skeleton } from "./Skeleton";

export function typingInAField(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  return target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName);
}

// "/" with no modifier key, outside a text field: the key that focuses the box. Panels that the
// key closes first, such as the Menu, ask the same question.
export function isBoxShortcut(event: KeyboardEvent): boolean {
  return event.key === "/" && !event.ctrlKey && !event.metaKey && !event.altKey && !typingInAField(event.target);
}

// One option in the box's list of what Enter will do: an icon, the label with any ID in Roboto Mono,
// and a second line in caption ink-muted where there is one.
export type BoxOption = {
  key: string;
  icon: LucideIcon;
  label: ReactNode;
  line?: ReactNode;
};

// The scope chip inside the box, on a project or package page: "Within P130164" with a 24 px remove
// button. Below 768 px it shows the ID only.
function ScopeChip({ scope, onRemove }: { scope: string; onRemove: () => void }) {
  return (
    <span data-scope-chip className="flex h-8 shrink-0 items-center gap-2 rounded-pill border border-line-strong bg-surface pr-1 pl-3">
      <span className="hidden text-small text-ink-muted md:inline">{copy.box.chipWithin}</span>
      <span className="font-mono text-small text-ink">{scope}</span>
      {/* Its own focus ring, inside the box's, 4 px clear of the ID. */}
      <button
        type="button"
        data-focus-ring
        aria-label={copy.box.chipRemove(scope)}
        onClick={onRemove}
        className="flex size-6 items-center justify-center rounded-pill text-ink-muted transition-paint duration-150 hover:bg-tint-hover hover:text-ink"
      >
        <X aria-hidden="true" className="size-4" />
      </button>
    </span>
  );
}

export function OneBox({
  value,
  onChange,
  options = [],
  notes = [],
  open = false,
  active = 0,
  scope,
  scopeKind = "project",
  onRemoveScope,
  onChoose,
  onKeyDown,
  onFocusChange,
  onPointerDown,
  inputRef,
  shortcut = true,
  focusedHint,
}: {
  value: string;
  onChange: (value: string) => void;
  // What Enter will do, best first. The list shows while open is true and there are options.
  options?: BoxOption[];
  // Lines under the list that are not options: an ID no record holds, or a lookup that failed.
  notes?: ReactNode[];
  open?: boolean;
  // The option Enter does.
  active?: number;
  // The page's scope chip: a P-code or a STEP reference.
  scope?: string | null;
  scopeKind?: "project" | "package";
  onRemoveScope?: () => void;
  onChoose?: (index: number) => void;
  onKeyDown?: (event: ReactKeyboardEvent<HTMLInputElement>) => void;
  onFocusChange?: (focused: boolean) => void;
  // A click or a tap in the box, which asks for its list as clearly as Down does.
  onPointerDown?: () => void;
  inputRef?: RefObject<HTMLInputElement | null>;
  // Only the band's box answers "/"; a second box, such as a gallery sample, sets false.
  shortcut?: boolean;
  // The gallery shows the hint as if the box had focus.
  focusedHint?: boolean;
}) {
  const ownInput = useRef<HTMLInputElement>(null);
  const input = inputRef ?? ownInput;
  const listId = useId();
  const hintId = useId();
  const scopedId = useId();
  const notesId = useId();
  const inputId = useId();
  const [focused, setFocused] = useState(false);

  useEffect(() => {
    if (!shortcut) return;
    const onKey = (event: KeyboardEvent) => {
      if (!isBoxShortcut(event) || event.isComposing) return;
      event.preventDefault();
      const element = input.current;
      if (!element) return;
      element.focus();
      element.setSelectionRange(element.value.length, element.value.length);
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [shortcut, input]);

  const showHint = (focused || focusedHint) && value.length === 0;
  const showList = open && value.trim().length > 0 && options.length > 0;
  const showNotes = open && value.trim().length > 0 && notes.length > 0;
  const described = [showHint && hintId, scope && scopedId, showNotes && notesId].filter(Boolean).join(" ") || undefined;
  const optionId = (index: number) => `${listId}-${index}`;
  const placeholder = scope ? (scopeKind === "package" ? copy.box.placeholderPackage : copy.box.placeholderProject) : null;

  return (
    <form
      role="search"
      className="relative"
      onSubmit={(event) => {
        event.preventDefault();
      }}
    >
      <label htmlFor={inputId} className="sr-only">
        {copy.box.label}
      </label>
      {scope && (
        <span id={scopedId} hidden>
          {copy.box.scoped(scope)}
        </span>
      )}
      <div
        data-focus-ring
        className={cx(
          "flex h-11 items-center gap-2 rounded-pill border border-line-strong bg-surface pr-4 transition-paint duration-150",
          scope ? "pl-1" : "pl-4",
          "hover:border-ink has-[input:focus-visible]:outline-2 has-[input:focus-visible]:outline-offset-2",
          "has-[input:focus-visible]:outline-focus has-[input:focus-visible]:outline-solid",
        )}
      >
        {scope ? (
          <ScopeChip scope={scope} onRemove={() => onRemoveScope?.()} />
        ) : (
          <Search aria-hidden="true" className="size-4 shrink-0 text-ink-muted" />
        )}
        <div className="relative min-w-0 flex-1">
          <input
            ref={input}
            id={inputId}
            type="text"
            role="combobox"
            value={value}
            placeholder=" "
            autoComplete="off"
            spellCheck={false}
            aria-autocomplete="list"
            aria-expanded={showList}
            aria-controls={listId}
            aria-activedescendant={showList ? optionId(active) : undefined}
            aria-keyshortcuts={shortcut ? "/" : undefined}
            aria-describedby={described}
            onChange={(event) => onChange(event.target.value)}
            onFocus={() => {
              setFocused(true);
              onFocusChange?.(true);
            }}
            onBlur={() => {
              setFocused(false);
              onFocusChange?.(false);
            }}
            onKeyDown={onKeyDown}
            onPointerDown={onPointerDown}
            className="peer h-10 w-full bg-transparent text-body text-ink focus-visible:outline-none"
          />
          <span
            aria-hidden="true"
            className="pointer-events-none absolute inset-0 hidden items-center truncate text-body text-ink-muted peer-placeholder-shown:flex"
          >
            {placeholder ? (
              <span className="truncate">{placeholder}</span>
            ) : (
              <>
                <span className="truncate md:hidden">{copy.box.placeholderNarrow}</span>
                <span className="hidden truncate md:inline">{copy.box.placeholderWide}</span>
              </>
            )}
          </span>
        </div>
        <kbd
          aria-hidden="true"
          className={cx(
            "hidden shrink-0 rounded-sm border border-line-strong px-1 font-mono text-caption text-ink-muted [@media(hover:none)]:hidden",
            !focused && value.length === 0 && "lg:inline",
          )}
        >
          /
        </kbd>
      </div>
      {(showHint || showList || showNotes) && (
        <div
          data-box-popup
          className="absolute inset-x-0 top-full z-40 mt-1 rounded-md border border-line bg-surface py-1 shadow-popover"
          // A click on an option keeps focus in the box, so the list stays a list of what Enter will do.
          onMouseDown={(event) => event.preventDefault()}
        >
          {showHint && (
            <p id={hintId} className="px-4 py-2 text-caption text-ink-muted">
              <Fill template={copy.box.hint} slots={{ pid: <span className="font-mono">{copy.box.hintId}</span> }} />
            </p>
          )}
          {showList && (
            <ul id={listId} role="listbox" aria-label={copy.box.listName}>
              {options.map((option, index) => {
                const selected = index === active;
                return (
                  <li
                    key={option.key}
                    id={optionId(index)}
                    role="option"
                    aria-selected={selected}
                    data-box-option={option.key}
                    onClick={() => onChoose?.(index)}
                    className={cx(
                      "flex min-h-11 cursor-pointer items-center gap-3 px-4 py-2 text-body text-ink",
                      selected ? "bg-tint shadow-[inset_3px_0_0_var(--color-primary)]" : "hover:bg-tint-hover",
                    )}
                  >
                    <option.icon aria-hidden="true" className="size-4 shrink-0 text-ink-muted" />
                    <span className="min-w-0 flex-1">
                      <span className="block wrap-anywhere">{option.label}</span>
                      {option.line && <span className="block text-caption wrap-anywhere text-ink-muted">{option.line}</span>}
                    </span>
                    {selected && (
                      <kbd aria-hidden="true" className="shrink-0 rounded-sm border border-line-strong px-1 font-mono text-caption text-ink-muted">
                        {copy.box.enter}
                      </kbd>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
          {showNotes && (
            <div id={notesId} className="flex flex-col gap-1 px-4 py-2">
              {notes.map((note, index) => (
                <p key={index} className="text-caption text-ink-muted">
                  {note}
                </p>
              ))}
            </div>
          )}
        </div>
      )}
    </form>
  );
}

export type Freshness =
  | { status: "loading"; slow?: boolean }
  | { status: "ready"; date: string }
  | { status: "empty" }
  | { status: "error" };

// The data-freshness stamp: caption text, a link to the Data page with a dotted underline
// (the mark of a value you can check), and five honest states. It is not a live region.
export function FreshnessStamp({ freshness, href = "/data" }: { freshness: Freshness; href?: string }) {
  const descriptionId = useId();
  const link = (text: string) => (
    <>
      <a
        href={href}
        aria-describedby={descriptionId}
        className={cx("inline-flex min-h-6 items-center text-caption text-ink-muted tabular-nums hover:text-link-hover", DOTTED_UNDERLINE)}
      >
        {text}
      </a>
      {/* Hidden, so it is read once through aria-describedby and never again as page text. */}
      <span id={descriptionId} hidden>
        {copy.stamp.description}
      </span>
    </>
  );
  let body: ReactNode;
  if (freshness.status === "loading") {
    body = freshness.slow ? (
      <span className="text-caption text-ink-muted">{copy.stamp.loading}</span>
    ) : (
      <Skeleton className="h-[13px] w-[124px]" />
    );
  } else if (freshness.status === "ready") body = link(copy.stamp.ready(freshness.date));
  else if (freshness.status === "empty") body = link(copy.stamp.empty);
  else
    body = (
      <span className="inline-flex items-center gap-1 text-caption text-ink-muted">
        <CircleX aria-hidden="true" className="size-4 shrink-0 text-error-icon" />
        {copy.stamp.error}
      </span>
    );
  return (
    <div data-stamp aria-busy={freshness.status === "loading" || undefined} className="flex min-h-6 items-center md:justify-end">
      {body}
    </div>
  );
}

export function BoxBand({ box, stamp }: { box: ReactNode; stamp?: ReactNode }) {
  return (
    <div data-box-band className="border-b border-line bg-surface">
      <div className="layout layout-grid min-h-[68px] items-center gap-y-2 py-3">
        <div className="col-span-12 md:col-span-8">{box}</div>
        <div className="col-span-12 md:col-span-4">{stamp}</div>
      </div>
    </div>
  );
}
