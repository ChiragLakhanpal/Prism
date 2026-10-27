// The top bar (DESIGN.md section 5, Top bar; ticket 93): the navy banner that carries the World Bank Group logo, the
// Strata wordmark (a link to Home), the one box and the view switch. Nouns navigate. The sections are the sidebar beside
// the page (Sidebar.tsx, ticket 92), and the data stamp sits at its foot.
//
// From 1024 px (64rem) everything sits on one 56 px row that sticks. Below 1024 px the bar scrolls with the page and has
// two rows: a labeled Menu button, the logo and the wordmark, with the view switch at the right from 768 px, then the box
// across the window. Below 768 px the view switch is at the Menu sheet's foot. On navy, focus uses focus-on-dark.
//
// When the window crosses 768 or 1024 px, the control that had focus can vanish with its part of the bar, which would
// drop focus to the page. Focus moves to the control that now holds the same thing instead: the view switch or its
// popover to the Menu button below 768 px, and the Menu button to the view switch from 1024 px (DESIGN.md section 10).
// The sidebar hands its own items to the Menu button.
//
// The view switch (ticket 40; the 40 brief, section 3): the button names the view the server applied, and in a preview
// it fills white with navy text, as the Menu button does. Its popover (the Menu sheet's foot below 768 px) holds the
// views as link rows, a past-date field and the language of answers and drafts (ticket 42). Every row and date is an
// address, so the mode lives in the address and survives Back, reload and a shared link.
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

// The view switch is in the bar from 768 px (48rem), and at the Menu sheet's foot below.
export const VIEW_IN_BAR = "(min-width: 48rem)";

// Calls back each time the window crosses one of the queries' widths. The callbacks here use only state setters and
// refs, which never change, so the first one is kept.
function useWidthChange(queries: string[], onChange: () => void) {
  useEffect(() => {
    const media = queries.map((query) => window.matchMedia(query));
    media.forEach((one) => one.addEventListener("change", onChange));
    return () => media.forEach((one) => one.removeEventListener("change", onChange));
  }, []);
}

const shown = (element: Element) => element.getClientRects().length > 0 && element.checkVisibility({ visibilityProperty: true });

// The control Tab reaches after this one in the page's order, leaving out what is hidden or inert and the popover
// itself, which is portaled to the end of the page.
function nextInPage(from: HTMLElement): HTMLElement | null {
  const tabbable = [
    ...document.querySelectorAll<HTMLElement>("a[href], button:not([disabled]), input:not([disabled]), select, textarea, [tabindex]:not([tabindex='-1'])"),
  ].filter((element) => element === from || (!element.closest("[data-radix-popper-content-wrapper], [inert]") && shown(element)));
  const at = tabbable.indexOf(from);
  return at < 0 ? null : (tabbable[at + 1] ?? null);
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

  // Narrowing the window below 768 px hides the view switch, so the popover closes with it.
  useWidthChange([VIEW_IN_BAR], () => !window.matchMedia(VIEW_IN_BAR).matches && setOpen(false));
  if (mode.unknown) {
    // Before the viewer is known, an outline button with no text, since an officer's label differs from staff's.
    return <Skeleton className="block h-8 w-[193px] border border-surface bg-transparent" radius="rounded-sm" />;
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
          "flex h-8 shrink-0 items-center gap-1 rounded-sm border px-3 text-button whitespace-nowrap",
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
            // control it closes the popover and moves on to what follows the view switch in the page, the sidebar's
            // first item from 1024 px, and Shift+Tab before the first goes back to the view switch (the 40 brief, 8.3).
            if (event.key !== "Tab") return;
            const focusable = [...event.currentTarget.querySelectorAll<HTMLElement>("a[href], input:not([type=radio]), input[type=radio]:checked, button")].filter(
              (element) => element.getClientRects().length > 0,
            );
            const first = focusable[0];
            const last = focusable[focusable.length - 1];
            const atEdge = event.shiftKey ? document.activeElement === first : document.activeElement === last;
            if (!atEdge) return;
            event.preventDefault();
            after.current = event.shiftKey || !pill.current ? pill.current : nextInPage(pill.current);
            setOpen(false);
          }}
          onCloseAutoFocus={(event) => {
            if (after.current) {
              event.preventDefault();
              after.current.focus();
              after.current = null;
              return;
            }
            // Below 768 px the view switch is hidden and the Menu sheet holds the view panel, so focus goes there.
            if (!window.matchMedia(VIEW_IN_BAR).matches) {
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
  box,
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
  // The one box (IntentBox in the app, OneBox in the gallery), in the bar's search slot.
  box?: ReactNode;
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

  // A focused control that the new width hides hands focus to the one that now holds the same thing: the view switch
  // when it shows, and the Menu button otherwise.
  useWidthChange([VIEW_IN_BAR, WIDE], () => {
    const active = document.activeElement;
    const root = bar.current;
    const focused = active instanceof HTMLElement && root?.contains(active) ? active : active === document.body ? hidden.current : null;
    hidden.current = null;
    if (!root || !focused || !root.contains(focused) || focused.getClientRects().length > 0) return;
    const pill = root.querySelector<HTMLElement>("[data-view-pill]");
    (pill && pill.getClientRects().length > 0 ? pill : sheet.button.current)?.focus();
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
      {/* Shown below the bar, over the page, so it never covers the logo or the wordmark (DESIGN.md section 10). */}
      <SkipLink />
      <div data-bar-row className="bar-row">
        <div className="bar-brand flex h-14 min-w-0 items-center pl-3 lg:pl-4">
          {/* A fixed width, 96 px or 44 px below 360 px, so the logo after it never moves when the font arrives and
              web/index.html paints it in the same place. */}
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
              "flex h-11 w-11 shrink-0 items-center justify-center gap-2 rounded-sm border text-button xs:w-24 lg:hidden",
              "transition-paint duration-150",
              mode.preview ? PREVIEW_LOOK : OWN_LOOK,
            )}
          >
            <MenuIcon aria-hidden="true" className="size-4 shrink-0" />
            {/* Below 360 px the word is hidden from sight, and the button keeps its name (DESIGN.md section 5, Menu sheet). */}
            <span className="max-xs:clip-visually">{copy.nav.menu}</span>
          </button>
          {logo && (
            <div data-logo-slot className="ml-3 flex h-14 shrink-0 items-center py-4 lg:ml-0">
              {logo}
            </div>
          )}
          <a
            href={withModeOf(homeHref, mode.search)}
            className="ml-6 flex h-10 shrink-0 items-center rounded-sm px-1 text-h3 text-surface underline-offset-4 hover:underline"
          >
            {copy.appName}
          </a>
        </div>
        {box && (
          <div data-box-band className="bar-box min-w-0">
            {box}
          </div>
        )}
        <div className="bar-view hidden pl-6 md:block lg:pl-0">
          <ViewSwitch viewer={viewer} mode={mode} defaultOpen={viewOpen} menuButton={sheet.button} />
        </div>
      </div>
    </div>
  );
}
