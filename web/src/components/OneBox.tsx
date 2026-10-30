// The one box (DESIGN.md section 5, Ask bar), which "/" focuses from anywhere outside a text field, and the
// data-freshness stamp. The box floats at the foot of the page column (Frame.tsx's ask bar; ticket 113, which moved it
// out of the navy bar), on the grid from a frame of 75rem (ticket 127). It has presence (ticket 127, the design lead's
// Option A after the Mobbin pass): white, a 1 px primary edge drawn inside it, 4 px corners and shadow-float; one row of
// 56 px from 1024 px, led by the search icon in primary. Its field is named "Ask Strata" without printing it, and the
// placeholder says the word (the owner's call of October 29, 2026). The stamp sits at the sidebar's foot, under Data
// (Sidebar.tsx).
//
// The box is a combobox (WAI-ARIA's list autocomplete with automatic selection): as you type, a
// list above it says what Enter will do, laid over the page so the ask bar never grows. Its options
// come from the intent rules (web/src/lib/intents.ts, through IntentBox.tsx); this file draws them.
// On a project or package page the box holds a removable scope chip.
import { useEffect, useId, useLayoutEffect, useRef, useState, type KeyboardEvent as ReactKeyboardEvent, type ReactNode, type RefObject } from "react";
import { CircleX, CornerDownLeft, Search, X, type LucideIcon } from "lucide-react";
import { copy } from "../copy";
import { cx } from "../lib/cx";
import { Fill } from "./Fill";
import { MonoWords } from "./MonoWords";
import { DOTTED_UNDERLINE } from "./Popover";
import { Skeleton } from "./Skeleton";
import { KeyHint } from "./ToggleButton";

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
  // The label as plain words, which name the Enter button while this is the option Enter will choose (ticket 127).
  name?: string;
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
      // 4 px above and below it, so with a row of its own it keeps 8 px from the box's edge and from the text's row; from
      // 1024 px 12 px before the text field (ticket 127).
      className="my-1 flex min-h-8 max-w-full min-w-0 cursor-auto items-center gap-2 rounded-lg border border-line-strong bg-surface pr-1 pl-3 lg:mr-1"
    >
      <span className="min-w-0 py-1 text-small">
        {/* A reference that holds a space, such as KE-UASIN GISHU COUNTY-571338-CW-RFB, is long enough without "Within",
            which would cut the placeholder beside it (ticket 59; DESIGN.md section 5, Scope chip). */}
        <span className={cx("mr-2 hidden text-ink-muted", !scope.includes(" ") && "md:@min-[35rem]/box:inline")}>{copy.box.chipWithin}</span>
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
  modePlaceholderShort,
  modeHelp,
  suggestions = null,
  suggestionActive = -1,
  onChooseSuggestion,
  enterName,
  onEnter,
  children,
}: {
  // Ticket 127: the Enter button's name, the option Enter will choose (IntentBox); without one, the option at active, or
  // "Ask this".
  enterName?: string;
  // What a press on the Enter button does: what Enter does.
  onEnter?: () => void;
  // A mode the Packages tab put the box in (ticket 15): its own placeholder, and a help line that describes
  // the box and takes the hint's place.
  modePlaceholder?: string;
  // The mode's placeholder below 768 px, so it is never cut (ticket 58).
  modePlaceholderShort?: string;
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
  const sentenceId = useId();
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
  // The field's name is "Ask Strata", not printed (ticket 127). The sentence that was its name describes it wherever
  // the hint or a mode's help line does not, last.
  const described = [(showHint || modeHelp) && hintId, scope && scopedId, showNotes && notesId, !(showHint || modeHelp) && sentenceId]
    .filter(Boolean)
    .join(" ");
  // Ticket 127: once the box holds text, the Enter button takes the "/" hint's place, named for the option Enter will
  // choose.
  const typed = value.trim().length > 0;
  const enter = enterName ?? options[active]?.name ?? copy.box.option.ask;
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
  // From 768 px the placeholder says "Strata" (ticket 127); below it the short form, so it is never cut. A mode's
  // placeholder may have no short form.
  const placeholder =
    modePlaceholder ??
    (scope ? (scopeKind === "package" ? copy.box.placeholderPackage : copy.box.placeholderProject) : copy.box.placeholderWide);
  const spaced = Boolean(scope?.includes(" ") && !modePlaceholder);
  const placeholderShort = modePlaceholder
    ? modePlaceholderShort
    : scope
      ? scopeKind === "package"
        ? copy.box.placeholderPackageShort
        : copy.box.placeholderProjectShort
      : copy.box.placeholderShort;

  return (
    <form
      role="search"
      className="@container/box relative"
      onSubmit={(event) => {
        event.preventDefault();
      }}
    >
      {/* The sentence that was the field's name, now its description (ticket 127). */}
      <span id={sentenceId} hidden>
        {copy.box.label}
      </span>
      {scope && (
        <span id={scopedId} hidden>
          {copy.box.scoped(scope)}
        </span>
      )}
      {/* One row is 56 px from 1024 px, the navy bar's height: 8 px around a 40 px row, 12 px before the icon and 8 px
          after the Enter button. Below 1024 px one row is 48 px, 4 px around the 40 px row; when a long scope chip
          pushes the text field to a second row, the chip takes the first with 4 px above and below it, 8 px over the
          text's row, so the box is 96 px, and the chip and the text share one left edge (ticket 127). A control's 4 px
          corners. Its 1 px primary edge is drawn inside it, so the edge moves nothing in it, with shadow-float under it
          (ticket 127). In the ask bar from 1024 px it keeps one row (app.css). While anything inside it has focus, its
          focus ring shows around it. The box shows the text cursor, so a press anywhere in it outside the field, a
          button or the chip, such as the rest of the chip's row, the search icon or the "/" hint, acts as a press on
          the field. */}
      <div
        data-focus-ring
        onPointerDown={(event) => {
          if ((event.target as Element).closest("input, button, [data-scope-chip]")) return;
          event.preventDefault();
          input.current?.focus();
          onPointerDown?.();
        }}
        className={cx(
          "flex min-h-12 w-full cursor-text flex-wrap items-center gap-x-2 gap-y-2 rounded-sm bg-surface py-1 pr-1 pl-3 lg:min-h-14 lg:py-2 lg:pr-2",
          "shadow-float inset-ring inset-ring-primary",
          "focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-focus focus-within:outline-solid",
        )}
      >
        {/* The 20 px search icon in primary. With a chip below 1024 px the icon hides, so the chip and the text share one
            left edge; below 360 px it always hides, for the field's room. */}
        <Search aria-hidden="true" className={cx("size-5 shrink-0 text-primary", scope ? "max-lg:hidden" : "max-xs:hidden")} />
        {scope && <ScopeChip scope={scope} onRemove={() => onRemoveScope?.()} />}
        {/* The text field and its "/" hint wrap together, so the hint never takes a row of its own. Below 1024 px the
            field goes under the chip when less than 176 px is left beside it, the width of a package page's whole
            placeholder, so "Ask about this package" is never cut; from 768 px, where the "/" hint shows after the
            field, less than 254 px, "Ask Strata about this package" and the hint (tickets 113 and 127, since the box
            is at most 640 px wide). */}
        <div className="flex min-h-10 min-w-0 flex-[1_1_176px] items-center gap-2 md:flex-[1_1_254px]">
          <div className="relative min-w-0 flex-1">
            <input
              ref={input}
              type="text"
              role="combobox"
              // Its name, never printed in the row; the placeholder says it from 768 px (ticket 127).
              aria-label={copy.box.name}
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
              {placeholderShort ? (
                // Below 768 px the short form, so it is never cut (tickets 58 and 93); the field's description keeps the
                // whole sentence. A reference that holds a space, such as KE-UASIN GISHU COUNTY-571338-CW-RFB, makes the
                // chip so long that from 1024 px, where the box keeps one row, the short form shows in a box under
                // 42rem too (ticket 127).
                <>
                  <span className={cx("truncate md:hidden", spaced && "lg:@max-[42rem]/box:inline")} data-placeholder>
                    {placeholderShort}
                  </span>
                  <span className={cx("hidden truncate md:inline", spaced && "lg:@max-[42rem]/box:hidden")} data-placeholder>
                    {placeholder}
                  </span>
                </>
              ) : (
                <span className="truncate" data-placeholder>
                  {placeholder}
                </span>
              )}
            </span>
          </div>
          {/* The control at the row's end keeps its place and changes with the text (ticket 127). At rest, the "/" hint,
              from 768 px where a pointer can hover, 12 px from the box's edge. Once the box holds text, the Enter
              button: 40 by 40, outlined in primary and never filled, since a page keeps one solid button, named for the
              option Enter will choose, which it shows as its tooltip. A press on it does what Enter does and keeps
              focus in the field. */}
          {typed ? (
            <button
              type="button"
              data-enter-button
              aria-label={enter}
              title={enter}
              onMouseDown={(event) => event.preventDefault()}
              onClick={() => onEnter?.()}
              className="flex size-10 shrink-0 items-center justify-center rounded-sm text-primary inset-ring inset-ring-primary transition-paint duration-150 hover:bg-tint"
            >
              <CornerDownLeft aria-hidden="true" className="size-4" />
            </button>
          ) : (
            <kbd
              aria-hidden="true"
              className={cx(
                "mr-2 hidden shrink-0 rounded-sm border border-line-strong px-1 font-mono text-caption text-ink-muted lg:mr-1 [@media(hover:none)]:hidden",
                !focused && value.length === 0 && "md:inline",
              )}
            >
              /
            </kbd>
          )}
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
          // While open it is the bar's upper half, 8 px above it, so it shares the bar's shadow-float (ticket 127).
          className="absolute inset-x-0 bottom-full z-40 mb-2 max-h-[calc(100dvh-var(--bar-height)-96px)] overflow-y-auto overscroll-contain rounded-md border border-line bg-surface pt-1 pb-1 shadow-float md:can-hover:pb-0"
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
          {/* The foot strip names the keys in Key hints, so the list teaches itself (ticket 127, from incident.io's
              palette): on page with a 1 px line over it, held to the list's foot as it scrolls. It shows where Key hints
              show, from 768 px on a device that can hover, and is aria-hidden, since the combobox names its keys. */}
          <div
            data-box-keys
            aria-hidden="true"
            className="sticky bottom-0 mt-1 hidden flex-wrap items-center gap-x-4 gap-y-1 border-t border-line bg-page px-3 py-2 text-caption text-ink-muted md:can-hover:flex"
          >
            <span>
              <Fill template={copy.box.keys.choose} slots={{ enter: <KeyHint>{copy.box.enter}</KeyHint> }} />
            </span>
            <span>
              <Fill template={copy.box.keys.move} slots={{ up: <KeyHint>{copy.box.keys.up}</KeyHint>, down: <KeyHint>{copy.box.keys.down}</KeyHint> }} />
            </span>
            <span>
              <Fill template={copy.box.keys.close} slots={{ escape: <KeyHint>{copy.box.keys.escape}</KeyHint> }} />
            </span>
          </div>
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
