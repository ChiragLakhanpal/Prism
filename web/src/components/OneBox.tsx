// The one box (DESIGN.md section 5, Ask bar), which "/" focuses from anywhere outside a text field, and the
// data-freshness stamp. The box floats at the bottom center of the page column (Frame.tsx's ask bar; ticket 113, which
// moved it out of the navy bar): white with a 1 px line-strong edge, 4 px corners and the popover shadow, up to 640 px
// wide. The stamp sits at the sidebar's foot, under Data (Sidebar.tsx).
//
// The box is a combobox (WAI-ARIA's list autocomplete with automatic selection): as you type, a
// list above it says what Enter will do, laid over the page so the ask bar never grows. Its options
// come from the intent rules (web/src/lib/intents.ts, through IntentBox.tsx); this file draws them.
// On a project or package page the box holds a removable scope chip.
import { useEffect, useId, useLayoutEffect, useRef, useState, type KeyboardEvent as ReactKeyboardEvent, type ReactNode, type RefObject } from "react";
import { CircleX, Search, X, type LucideIcon } from "lucide-react";
import { copy } from "../copy";
import { cx } from "../lib/cx";
import { Fill } from "./Fill";
import { MonoWords } from "./MonoWords";
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
  // An option the view holds, listed so it stays discoverable, with its reason as its line (ticket 15's plan
  // option in a preview). Choosing it does nothing.
  disabled?: boolean;
};

// The scope chip inside the box, on a project or package page: "Within P130164" with a 24 px remove
// button. It shows the ID only below 768 px, and whenever the box is narrower than 35rem. From 1024 px the box keeps
// one row. Below 1024 px a STEP reference is far longer than a P-code, so when the chip and a text field you can type
// in do not fit on one line, the chip takes a row of its own above the text (OneBox wraps). A reference wider than
// that row stays whole and readable as one ID (MonoWords): each part between spaces moves to the next line whole when
// it fits there, and breaks after a hyphen when it is wider than the line, as the package workspace's own references
// do. In the bar from 1024 px the chip keeps its one line, and the text field gives way first (app.css). On one line
// the chip is a 32 px pill; on more it is a box with 16 px corners. It keeps the pointer's own cursor
// (cursor-auto), so its ID shows the text cursor only where you can select it, and a press on it does not put the
// cursor in the text field.
function ScopeChip({ scope, onRemove }: { scope: string; onRemove: () => void }) {
  return (
    <span
      data-scope-chip
      className="flex min-h-8 max-w-full min-w-0 cursor-auto items-center gap-2 rounded-lg border border-line-strong bg-surface pr-1 pl-3"
    >
      <span className="min-w-0 py-1 text-small">
        <span className="mr-2 hidden text-ink-muted md:@min-[35rem]/box:inline">{copy.box.chipWithin}</span>
        <MonoWords text={scope} className="align-top text-ink" />
      </span>
      {/* Its own focus ring, inside the box's, 4 px clear of the ID. */}
      <button
        type="button"
        data-focus-ring
        aria-label={copy.box.chipRemove(scope)}
        onClick={onRemove}
        className="flex size-6 shrink-0 items-center justify-center rounded-pill text-ink-muted transition-paint duration-150 hover:bg-tint-hover hover:text-ink"
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
  modePlaceholder,
  modeHelp,
  suggestions = null,
  suggestionActive = -1,
  onChooseSuggestion,
  children,
}: {
  // A mode the Packages tab put the box in (ticket 15): its own placeholder, and a help line that describes
  // the box and takes the hint's place.
  modePlaceholder?: string;
  modeHelp?: string;
  // Ticket 112: focused and empty, a group of questions for the page under the hint, named by the page, in the list's
  // own option rows. None is chosen until Down or Up moves to one.
  suggestions?: { name: ReactNode; options: BoxOption[] } | null;
  suggestionActive?: number;
  onChooseSuggestion?: (index: number) => void;
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
  // Only the bar's box answers "/"; a second box, such as a gallery sample, sets false.
  shortcut?: boolean;
  // The gallery shows the hint as if the box had focus.
  focusedHint?: boolean;
  // More of the box's own parts, inside its search landmark, such as the status line that says the chip was removed.
  children?: ReactNode;
}) {
  const ownInput = useRef<HTMLInputElement>(null);
  const input = inputRef ?? ownInput;
  const listId = useId();
  const hintId = useId();
  const scopedId = useId();
  const notesId = useId();
  const inputId = useId();
  const [focused, setFocused] = useState(false);

  // Attached as the box mounts, before the page can take a key, so a "/" pressed as soon as the page loads lands here.
  useLayoutEffect(() => {
    if (!shortcut) return;
    const onKey = (event: KeyboardEvent) => {
      if (!isBoxShortcut(event) || event.isComposing) return;
      event.preventDefault();
      const element = input.current;
      if (!element) return;
      // The box always shows, at the window's foot, so focusing it never scrolls the page (DESIGN.md section 10).
      element.focus({ preventScroll: true });
      element.setSelectionRange(element.value.length, element.value.length);
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [shortcut, input]);

  const showHint = (focused || focusedHint) && value.length === 0;
  const showList = open && value.trim().length > 0 && options.length > 0;
  const showNotes = open && value.trim().length > 0 && notes.length > 0;
  const showSuggestions = Boolean(showHint && suggestions && suggestions.options.length > 0);
  const described =
    [(showHint || modeHelp) && hintId, scope && scopedId, showNotes && notesId].filter(Boolean).join(" ") || undefined;
  const optionId = (index: number) => `${listId}-${index}`;
  const suggestionId = (index: number) => `${listId}-s${index}`;
  const activeId = showList ? optionId(active) : showSuggestions && suggestionActive >= 0 ? suggestionId(suggestionActive) : undefined;
  // One option row: an icon, the label with any ID in mono, a second line where there is one, and the "Enter" key hint
  // on the option Enter does.
  const optionRow = (option: BoxOption, id: string, selected: boolean, choose: () => void) => (
    <li
      key={option.key}
      id={id}
      role="option"
      aria-selected={selected}
      aria-disabled={option.disabled || undefined}
      data-box-option={option.key}
      onClick={() => !option.disabled && choose()}
      className={cx(
        "flex min-h-11 items-center gap-3 px-4 py-2 text-body",
        option.disabled ? "cursor-default text-ink-muted" : "cursor-pointer text-ink",
        selected ? "bg-tint shadow-[inset_3px_0_0_var(--color-primary)]" : !option.disabled && "hover:bg-tint-hover",
      )}
    >
      <option.icon aria-hidden="true" className="size-4 shrink-0 text-ink-muted" />
      <span className="min-w-0 flex-1">
        <span className="block wrap-anywhere">{option.label}</span>
        {option.line && <span className="block text-caption wrap-anywhere text-ink-muted">{option.line}</span>}
      </span>
      {/* Below 360 px the Enter hint hides, as the box's search icon does, so a STEP reference under the option's name
          keeps to one line (ticket 59; DESIGN.md section 4, Breakpoints). */}
      {selected && !option.disabled && (
        <kbd aria-hidden="true" className="shrink-0 rounded-sm border border-line-strong px-1 font-mono text-caption text-ink-muted max-xs:hidden">
          {copy.box.enter}
        </kbd>
      )}
    </li>
  );
  const placeholder =
    modePlaceholder ?? (scope ? (scopeKind === "package" ? copy.box.placeholderPackage : copy.box.placeholderProject) : null);

  return (
    <form
      role="search"
      className="@container/box relative"
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
      {/* One row is 40 px: 4 px around a 32 px field and chip, 12 px before the first of them, with a control's 4 px
          corners. Its 1 px line-strong edge, a control's border, is drawn inside it with the popover shadow, so the
          edge moves nothing in it (ticket 113). In the ask bar from 1024 px it keeps one row (app.css). Otherwise,
          when a long scope chip pushes the text field to a second row, the chip and the text share one left edge.
          While anything inside it has focus, its focus ring shows around it. The box shows the text cursor, so a press
          anywhere in it outside the field, a button or the chip, such as the rest of the chip's row, the search icon
          or the "/" hint, acts as a press on the field. */}
      <div
        data-focus-ring
        onPointerDown={(event) => {
          if ((event.target as Element).closest("input, button, [data-scope-chip]")) return;
          event.preventDefault();
          input.current?.focus();
          onPointerDown?.();
        }}
        className={cx(
          "flex min-h-10 w-full cursor-text flex-wrap items-center gap-x-2 gap-y-1 rounded-sm bg-surface py-1 pr-1 pl-3",
          "shadow-popover inset-ring inset-ring-line-strong",
          "focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-focus focus-within:outline-solid",
        )}
      >
        {/* With a chip below 1024 px the icon hides, so the chip and the text share one left edge; below 360 px it
            always hides, for the field's room. */}
        <Search aria-hidden="true" className={cx("size-4 shrink-0 text-ink-muted", scope ? "max-lg:hidden" : "max-xs:hidden")} />
        {scope && <ScopeChip scope={scope} onRemove={() => onRemoveScope?.()} />}
        {/* The text field and its "/" hint wrap together, so the hint never takes a row of its own. Below 1024 px the
            field goes under the chip when less than 176 px is left beside it, the width of a package page's whole
            placeholder, so "Ask about this package" is never cut; from 768 px, where the "/" hint shows after the
            field, less than 210 px, the placeholder and the hint (ticket 113, since the box is at most 640 px wide). */}
        <div className="flex min-w-0 flex-[1_1_176px] items-center gap-2 md:flex-[1_1_210px]">
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
              aria-expanded={showList || showSuggestions}
              aria-controls={listId}
              aria-activedescendant={activeId}
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
              className="peer h-8 w-full bg-transparent text-body text-ink focus-visible:outline-none"
            />
            <span
              aria-hidden="true"
              className="pointer-events-none absolute inset-0 hidden items-center truncate text-body text-ink-muted peer-placeholder-shown:flex"
            >
              {placeholder ? (
                <span className="truncate" data-placeholder>
                  {placeholder}
                </span>
              ) : (
                // Below 768 px the short form, so it is never cut; the field's name keeps the whole sentence.
                <>
                  <span className="truncate md:hidden" data-placeholder>
                    {copy.box.placeholderShort}
                  </span>
                  <span className="hidden truncate md:inline" data-placeholder>
                    {copy.box.placeholderWide}
                  </span>
                </>
              )}
            </span>
          </div>
          {/* The "/" hint, from 768 px where a pointer can hover. */}
          <kbd
            aria-hidden="true"
            className={cx(
              "mr-2 hidden shrink-0 rounded-sm border border-line-strong px-1 font-mono text-caption text-ink-muted [@media(hover:none)]:hidden",
              !focused && value.length === 0 && "md:inline",
            )}
          >
            /
          </kbd>
        </div>
      </div>
      {/* A mode's help line describes the box whether or not the list shows. */}
      {modeHelp && !showHint && (
        <span id={hintId} hidden>
          {modeHelp}
        </span>
      )}
      {/* The list opens above the box at its width, at most as tall as the window less the bar and 96 px, and
          scrolls inside, so it never reaches the bar (ticket 113). */}
      {(showHint || showList || showNotes) && (
        <div
          data-box-popup
          className="absolute inset-x-0 bottom-full z-40 mb-1 max-h-[calc(100dvh-var(--bar-height)-96px)] overflow-y-auto overscroll-contain rounded-md border border-line bg-surface py-1 shadow-popover"
          // A click on an option keeps focus in the box, so the list stays a list of what Enter will do.
          onMouseDown={(event) => event.preventDefault()}
        >
          {showHint && (
            <p id={hintId} className="px-4 py-2 text-caption text-ink-muted" data-box-help={modeHelp ? "" : undefined}>
              {modeHelp ?? <Fill template={copy.box.hint} slots={{ pid: <span className="font-mono">{copy.box.hintId}</span> }} />}
            </p>
          )}
          {showList && (
            <ul id={listId} role="listbox" aria-label={copy.box.listName}>
              {options.map((option, index) => optionRow(option, optionId(index), index === active, () => onChoose?.(index)))}
            </ul>
          )}
          {showSuggestions && suggestions && (
            <div id={listId} role="listbox" aria-label={copy.box.listName} data-box-suggestions>
              <ul role="group" aria-labelledby={`${listId}-group`}>
                <li role="presentation" id={`${listId}-group`} className="px-4 pt-2 pb-1 text-label text-ink-muted">
                  {suggestions.name}
                </li>
                {suggestions.options.map((option, index) =>
                  optionRow(option, suggestionId(index), index === suggestionActive, () => onChooseSuggestion?.(index)),
                )}
              </ul>
            </div>
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
      {children}
    </form>
  );
}

export type Freshness =
  | { status: "loading"; slow?: boolean }
  | { status: "ready"; date: string }
  | { status: "empty" }
  | { status: "error" };

// The stamp's words in each state, for the Data item's tooltip when the sidebar is a rail (ticket 93). None while the
// static bar holds the stamp's place in its first second.
export function stampWords(freshness: Freshness): string | null {
  if (freshness.status === "ready") return copy.stamp.ready(freshness.date);
  if (freshness.status === "empty") return copy.stamp.empty;
  if (freshness.status === "error") return copy.stamp.error;
  return freshness.slow ? copy.stamp.loading : null;
}

// The data-freshness stamp: caption text, a link to the Data page with a dotted underline
// (the mark of a value you can check), and five honest states, in a 24 px line box. It is not a live region.
// hang: the error's icon hangs left of the stamp's edge, as at the sidebar's foot, where the stamp starts on its label's edge.
export function FreshnessStamp({ freshness, href = "/data", hang = false }: { freshness: Freshness; href?: string; hang?: boolean }) {
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
    // The icon hangs left of the stamp's edge, so the words start on the label's edge, as the date does, and keep to
    // one 24 px line at the sidebar's foot (ticket 59; the 93 review).
    body = (
      <span className={cx(hang ? "-ml-6 gap-2" : "gap-1", "inline-flex items-center text-caption text-ink-muted")} data-stamp-error>
        <CircleX aria-hidden="true" className="size-4 shrink-0 text-error-icon" />
        {copy.stamp.error}
      </span>
    );
  return (
    <div data-stamp aria-busy={freshness.status === "loading" || undefined} className="flex min-h-6 items-center">
      {body}
    </div>
  );
}
