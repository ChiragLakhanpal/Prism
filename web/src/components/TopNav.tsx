// The top navigation (DESIGN.md section 5): a navy bar, 56 px tall, with the logo, the Strata wordmark (a link to
// Home) and the view switch. Nouns navigate. The sections are the sidebar beside the page (Sidebar.tsx, ticket 92).
//
// From 1024 px (64rem) the view switch sits in the bar. Below 1024 px a labeled Menu button opens the Menu sheet,
// which holds the sidebar's items and the view lines; below 360 px the button keeps its name with its word hidden.
// On navy, focus uses focus-on-dark.
//
// When the window crosses 1024 px, the control that had focus can vanish with its half of the bar, which would drop
// focus to the page. Focus moves to the control that now holds the same thing instead: the pill or the view popover
// to the Menu button, and the Menu button to the pill (DESIGN.md section 10). The sidebar hands its own items to the
// Menu button.
//
// The view switch (ticket 40; the 40 brief, section 3): the pill names the view the server applied, and in a preview
// it fills white with navy text, as the Menu button does below 1024 px. Its popover (the Menu sheet's foot below
// 1024 px) holds the views as link rows, a past-date field and the language of answers and drafts (ticket 42). Every
// row and date is an address, so the mode lives in the address and survives Back, reload and a shared link.
import { useEffect, useId, useRef, useState, type FormEvent, type ReactNode, type RefObject } from "react";
import * as RadixPopover from "@radix-ui/react-popover";
import { Check, ChevronDown, CircleX, Menu as MenuIcon } from "lucide-react";
import { copy } from "../copy";
import { cx } from "../lib/cx";
import { navigate } from "../lib/router";
import { withMode, type Preview, type View } from "../lib/view";
import { Button } from "./Button";
import { useMenuSheet, WIDE } from "./Frame";
import { LanguageChoice } from "./LanguageChoice";
import { POPOVER } from "./Popover";
import { SECTIONS, type Section } from "./sections";
import { Skeleton } from "./Skeleton";
import { SkipLink } from "./SkipLink";

export { SECTIONS, type Section };

export type Viewer =
  | { status: "loading" }
  // agency: the implementing agency whose team the viewer is on (ticket 38), whose view the server applies.
  | { status: "signed-in"; email: string; agency?: string | null }
  | { status: "signed-out" }
  | { status: "error" };

// The view the bar shows, from GET /api/me, or from the address while it loads (App.tsx).
export type NavMode = {
  // The viewer's own view, and the preview the server applied (or the address asks for, while /api/me loads).
  own: "staff" | "piu";
  preview: Preview | null;
  // The views the popover offers, own first; empty while /api/me loads.
  offered: View[];
  // The implementing agency the agency rows name in a sentence, from the roles file through /api/me.
  agency: string | null;
  // The sections of the applied view, or null while they are not known (a preview while /api/me loads).
  tabs: Section[] | null;
  // The pages the applied view hides (config/roles.toml through GET /api/me), so the sidebar leaves out their items.
  hidden: string[];
  // The address, for the rows' and the date's links.
  pathname: string;
  search: string;
  // The page's as-of date, which the date field holds.
  asOf: string | null;
  // No view known yet and none in the address: the pill is a skeleton (the 40 brief, 3.2).
  unknown: boolean;
};

export const STAFF_MODE: NavMode = {
  own: "staff", preview: null, offered: ["staff", "piu", "public"], agency: null, tabs: SECTIONS.map((section) => section.key),
  hidden: [], pathname: "/", search: "", asOf: null, unknown: false,
};

// The view popover hangs 8 px below the navy bar, not 8 px below the pill, so no white lip of
// it sits on the bar. The 32 px pill is centered in the 56 px bar, 12 px above its bottom edge.
const BELOW_BAR = 12 + 8;

// In a preview the pill and the Menu button fill white with navy text (about 16:1), tint on hover and when open.
const PREVIEW_LOOK = "border-surface bg-surface text-navy hover:bg-tint data-[state=open]:bg-tint aria-expanded:bg-tint";
const OWN_LOOK = "border-surface text-surface hover:bg-primary-hover data-[state=open]:bg-primary-hover aria-expanded:bg-primary-hover";

export function pillLabel(mode: NavMode): string {
  const words = copy.nav.view.pill;
  if (mode.preview === "piu") return words.previewOfficer;
  if (mode.preview === "public") return words.previewPublic;
  return mode.own === "piu" ? words.officer : words.staff;
}

// Calls back each time the window crosses 1024 px, with whether it is now wide. The callbacks
// here use only state setters and refs, which never change, so the first one is kept.
function useWideChange(onChange: (wide: boolean) => void) {
  useEffect(() => {
    const wide = window.matchMedia(WIDE);
    const changed = () => onChange(wide.matches);
    wide.addEventListener("change", changed);
    return () => wide.removeEventListener("change", changed);
  }, []);
}

// Who is signed in, as the first line of the view panel. An error carries the circle-x icon, as the
// freshness stamp's does, so it does not read like the signed-in line.
function WhoLine({ viewer, id }: { viewer: Viewer; id?: string }) {
  if (viewer.status === "loading") return <Skeleton className="h-[13px] w-[200px] max-w-full" />;
  if (viewer.status === "error") {
    return (
      <p id={id} className="flex items-start gap-1 text-caption text-ink-muted">
        <CircleX aria-hidden="true" className="size-4 shrink-0 text-error-icon" />
        {copy.nav.view.identityError}
      </p>
    );
  }
  return (
    <p id={id} className="text-caption text-ink-muted">
      {viewer.status === "signed-in" ? copy.nav.view.signedIn(viewer.email) : copy.nav.view.signedOut}
    </p>
  );
}

// One view as a link row: its label and what it is, the current one marked with a check, tint and a 3 px bar.
function ViewRow({ view, mode, current }: { view: View; mode: NavMode; current: boolean }) {
  const desc = useId();
  const rows = copy.nav.view.rows;
  const own = view === mode.own;
  const label = rows[view].label;
  const description =
    view === "staff" ? rows.staff.desc : view === "public" ? rows.public.desc : own ? rows.piu.descOwn(mode.agency ?? "") : rows.piu.descPreview(mode.agency ?? "");
  return (
    <li>
      <a
        data-mode
        data-view-row={view}
        href={withMode(mode.pathname, mode.search, { view: own ? null : view })}
        aria-current={current ? "true" : undefined}
        aria-describedby={desc}
        className={cx(
          "relative flex min-h-12 items-start gap-2 rounded-sm px-3 py-2 transition-paint duration-150",
          "before:absolute before:inset-y-0 before:left-0 before:w-[3px] before:rounded-l-sm",
          current ? "bg-tint before:bg-primary" : "hover:bg-tint-hover",
        )}
      >
        <span className="mt-0.5 flex size-4 shrink-0 items-center justify-center">
          {current && <Check aria-hidden="true" className="size-4 text-primary" />}
        </span>
        <span className="flex flex-col">
          <span className="text-small font-bold text-ink-heading">{label}</span>
          <span id={desc} className="text-caption text-pretty text-ink-muted">
            {description}
          </span>
        </span>
      </a>
    </li>
  );
}

// The past-date field (the 40 brief, 3.3): a native date input and "Show this date", which opens the page as of that
// date. It checks the date here and the server checks it again.
function DateForm({ mode, onDone }: { mode: NavMode; onDone: () => void }) {
  const words = copy.nav.view.date;
  const field = useId();
  const hint = useId();
  const errorId = useId();
  const [value, setValue] = useState(mode.asOf ?? "");
  const [error, setError] = useState<string | null>(null);
  const input = useRef<HTMLInputElement>(null);
  // Yesterday, by this computer's calendar: the latest past date the field offers.
  const now = new Date();
  const today = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
  const submit = (event: FormEvent) => {
    event.preventDefault();
    const problem = !value ? words.errorEmpty : value >= today ? words.errorNotPast : null;
    setError(problem);
    if (problem) {
      input.current?.focus();
      return;
    }
    onDone();
    navigate(withMode(mode.pathname, mode.search, { asof: value }), { exact: true });
  };
  return (
    <form noValidate onSubmit={submit} data-date-form className="flex flex-col items-start gap-2">
      <label htmlFor={field} className="text-small font-bold text-ink-heading">
        {words.label}
      </label>
      <input
        ref={input}
        id={field}
        type="date"
        value={value}
        onChange={(event) => setValue(event.target.value)}
        aria-describedby={error ? `${hint} ${errorId}` : hint}
        aria-invalid={error ? "true" : undefined}
        className="h-11 w-full rounded-sm border border-line-strong bg-surface px-3 text-body text-ink"
      />
      <p id={hint} className="text-caption text-ink-muted">
        {words.hint}
      </p>
      {error && (
        <p id={errorId} className="flex items-start gap-1 text-caption text-error">
          <CircleX aria-hidden="true" className="size-4 shrink-0 text-error-icon" />
          {error}
        </p>
      )}
      <Button variant="secondary" type="submit" className="mt-1">
        {words.submit}
      </Button>
    </form>
  );
}

// The view panel: who is signed in, the views as link rows, the past-date field. A viewer whose identity failed sees
// only the error line (the 40 brief, 7.1).
export function ViewPanel({ viewer, mode, onDone, whoId }: { viewer: Viewer; mode: NavMode; onDone: () => void; whoId?: string }) {
  const group = useId();
  const current: View = mode.preview ?? mode.own;
  if (viewer.status === "error") return <WhoLine viewer={viewer} id={whoId} />;
  return (
    <div className="flex flex-col gap-3">
      <WhoLine viewer={viewer} id={whoId} />
      <div>
        <p id={group} className="text-small font-bold text-ink-heading">
          {copy.nav.view.group}
        </p>
        {mode.offered.length > 0 ? (
          <ul aria-labelledby={group} className="mt-2 flex flex-col gap-1">
            {mode.offered.map((view) => (
              <ViewRow key={view} view={view} mode={mode} current={view === current} />
            ))}
          </ul>
        ) : (
          <div className="mt-2 flex flex-col gap-1">
            {[0, 1, 2].map((index) => (
              <Skeleton key={index} className="h-12 w-full" />
            ))}
          </div>
        )}
      </div>
      <div className="border-t border-line pt-4">
        <DateForm mode={mode} onDone={onDone} />
      </div>
    </div>
  );
}

function ViewSwitch({
  viewer,
  mode,
  defaultOpen,
  menuButton,
}: {
  viewer: Viewer;
  mode: NavMode;
  defaultOpen?: boolean;
  // Where focus goes when a narrowing window closes the popover.
  menuButton: RefObject<HTMLButtonElement | null>;
}) {
  const [open, setOpen] = useState(defaultOpen ?? false);
  const pill = useRef<HTMLButtonElement>(null);
  const content = useRef<HTMLDivElement>(null);
  const whoId = useId();
  // Where Tab or Shift+Tab sends focus once the popover has closed. The popover is portaled to
  // the end of the page, so without this Tab past its last control would leave the page.
  const after = useRef<HTMLElement | null>(null);

  // Narrowing the window below 1024 px hides the pill, so the popover closes with it.
  useWideChange((wide) => !wide && setOpen(false));
  if (mode.unknown) {
    // Before the viewer is known, an outline pill with no text, since an officer's label differs from staff's.
    return <Skeleton className="block h-8 w-[193px] border border-surface bg-transparent" radius="rounded-pill" />;
  }
  return (
    <RadixPopover.Root open={open} onOpenChange={setOpen}>
      {/* Keyed by its look, so a change of view draws the new fill at once instead of fading it (the 40 brief, 9). */}
      <RadixPopover.Trigger
        key={mode.preview ?? "own"}
        ref={pill}
        data-view-pill
        data-preview={mode.preview ?? undefined}
        aria-haspopup="dialog"
        className={cx(
          "flex h-8 shrink-0 items-center gap-1 rounded-pill border px-3 text-button whitespace-nowrap",
          "transition-paint duration-150",
          mode.preview ? PREVIEW_LOOK : OWN_LOOK,
        )}
      >
        {pillLabel(mode)}
        <ChevronDown aria-hidden="true" className={cx("size-4 transition-transform duration-150", open && "rotate-180")} />
      </RadixPopover.Trigger>
      <RadixPopover.Portal>
        <RadixPopover.Content
          ref={content}
          align="end"
          sideOffset={BELOW_BAR}
          collisionPadding={16}
          aria-label={copy.nav.view.dialog}
          aria-describedby={whoId}
          onOpenAutoFocus={(event) => {
            // Focus lands on the current view's row, so you can move to another at once (the 40 brief, 8.2).
            event.preventDefault();
            const row = content.current?.querySelector<HTMLElement>("[data-view-row][aria-current]");
            (row ?? content.current?.querySelector<HTMLElement>("a, input, button"))?.focus();
          }}
          onKeyDown={(event) => {
            // Tab moves through the rows, the date field and its button, and the language group; past the last
            // control it closes the popover and moves on to the box, and Shift+Tab before the first goes back to the
            // pill (the 40 brief, 8.3).
            if (event.key !== "Tab") return;
            const focusable = [...event.currentTarget.querySelectorAll<HTMLElement>("a[href], input:not([type=radio]), input[type=radio]:checked, button")].filter(
              (element) => element.getClientRects().length > 0,
            );
            const first = focusable[0];
            const last = focusable[focusable.length - 1];
            const atEdge = event.shiftKey ? document.activeElement === first : document.activeElement === last;
            if (!atEdge) return;
            event.preventDefault();
            after.current = event.shiftKey ? pill.current : document.querySelector<HTMLElement>("[data-box-band] input");
            setOpen(false);
          }}
          onCloseAutoFocus={(event) => {
            if (after.current) {
              event.preventDefault();
              after.current.focus();
              after.current = null;
              return;
            }
            // Below 1024 px the pill is hidden and the Menu sheet holds the view panel, so focus goes there.
            if (!window.matchMedia(WIDE).matches) {
              event.preventDefault();
              menuButton.current?.focus();
            }
          }}
          className={cx(POPOVER, "max-h-[calc(100vh-4.5rem)] w-80 overflow-y-auto p-4")}
        >
          <div data-view-popover>
            <ViewPanel viewer={viewer} mode={mode} whoId={whoId} onDone={() => setOpen(false)} />
          </div>
          {viewer.status !== "error" && (
            <div className="mt-4 border-t border-line pt-4">
              <LanguageChoice />
            </div>
          )}
        </RadixPopover.Content>
      </RadixPopover.Portal>
    </RadixPopover.Root>
  );
}

// A link keeps the address's view, date and language, so the mode survives a move between pages.
export function withModeOf(href: string, search: string): string {
  const params = new URLSearchParams(search);
  const kept = new URLSearchParams();
  for (const key of ["view", "asof", "lang"]) {
    const value = params.get(key);
    if (value) kept.set(key, value);
  }
  const rest = kept.toString();
  return rest ? `${href}${href.includes("?") ? "&" : "?"}${rest}` : href;
}

export function TopNav({
  logo,
  viewer,
  homeHref = "/",
  viewOpen,
  mode = STAFF_MODE,
  modeLineId,
}: {
  // The logo, at least 24 px tall. The slot gives it clear space of half its height, and 24 px
  // before the wordmark, so the two never read as one co-branded name (DESIGN.md section 9). The app and
  // the gallery pass the World Bank's official file (web/src/assets/world-bank-logo.md).
  logo?: ReactNode;
  viewer: Viewer;
  homeHref?: string;
  // For the gallery: open the view popover on the first render.
  viewOpen?: boolean;
  // The view the server applied (ticket 40).
  mode?: NavMode;
  // The visually hidden line that says the mode, which describes the Menu button in a preview.
  modeLineId?: string;
}) {
  const sheet = useMenuSheet();
  const bar = useRef<HTMLDivElement>(null);
  // The control a resize just hid. Chrome takes focus from it before it reports the media
  // change, so the bar notes it on blur and forgets it after the frame.
  const hidden = useRef<HTMLElement | null>(null);

  // A focused control that the new width hides hands focus to the control at the bar's right end: the pill when the
  // window widens, the Menu button when it narrows.
  useWideChange((wide) => {
    const active = document.activeElement;
    const root = bar.current;
    const focused = active instanceof HTMLElement && root?.contains(active) ? active : active === document.body ? hidden.current : null;
    hidden.current = null;
    if (!root || !focused || !root.contains(focused) || focused.getClientRects().length > 0) return;
    (wide ? root.querySelector<HTMLElement>("[data-view-pill]") : sheet.button.current)?.focus();
  });

  return (
    <div
      ref={bar}
      data-nav-bar
      className="on-navy relative bg-navy text-surface"
      onBlur={(event) => {
        const target = event.target as HTMLElement;
        if (event.relatedTarget || target.getClientRects().length > 0) return;
        hidden.current = target;
        requestAnimationFrame(() => (hidden.current = null));
      }}
    >
      <SkipLink />
      <div className="layout flex h-14 items-center">
        {logo && (
          <div data-logo-slot className="flex h-14 shrink-0 items-center py-4 pr-6">
            {logo}
          </div>
        )}
        <a
          href={withModeOf(homeHref, mode.search)}
          className="flex h-10 shrink-0 items-center text-h3 text-surface underline-offset-4 hover:underline"
        >
          {copy.appName}
        </a>
        <div className="ml-auto hidden pl-6 lg:block">
          <ViewSwitch viewer={viewer} mode={mode} defaultOpen={viewOpen} menuButton={sheet.button} />
        </div>
        <button
          key={mode.preview ?? "own"}
          ref={sheet.button}
          type="button"
          data-menu-button
          aria-expanded={sheet.open}
          aria-controls={sheet.sheetId}
          aria-describedby={mode.preview && modeLineId ? modeLineId : undefined}
          data-preview={mode.preview ?? undefined}
          onClick={() => sheet.setOpen(!sheet.open)}
          className={cx(
            "ml-auto flex h-11 min-w-11 shrink-0 items-center justify-center gap-2 rounded-sm border px-3 text-button lg:hidden",
            "transition-paint duration-150",
            mode.preview ? PREVIEW_LOOK : OWN_LOOK,
          )}
        >
          <MenuIcon aria-hidden="true" className="size-4" />
          {/* Below 360 px the word is hidden from sight, and the button keeps its name (DESIGN.md section 5, Menu sheet). */}
          <span className="max-xs:clip-visually">{copy.nav.menu}</span>
        </button>
      </div>
    </div>
  );
}

