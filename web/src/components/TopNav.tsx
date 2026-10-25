// The top navigation (DESIGN.md section 5): a navy bar, 56 px tall, with the logo, the
// Strata wordmark (a link to Home), five tabs and the view switch. Nouns navigate.
//
// From 1024 px (64rem) the tabs and the view switch sit in the bar. The full bar is 856 px
// wide and the 768 grid gives 672, so below 1024 a labeled Menu button holds them in a panel
// that pushes the page down. Below 360 px the button stacks its icon over its label.
//
// On navy, the selected tab has a 3 px white underline and hover a line-strong one; focus uses
// focus-on-dark. Only one Main navigation is exposed at a time: the bar's below 1024 px is
// display: none, and so is the panel's from 1024 px.
//
// When the window crosses 1024 px, the control that had focus can vanish with its half of the
// bar, which would drop focus to the page. Focus moves to the control that now holds the same
// thing instead: a tab to its twin, the pill or the view popover to the Menu button, and the
// Menu button to the pill (DESIGN.md section 10).
import { useEffect, useId, useRef, useState, type ReactNode, type RefObject } from "react";
import * as RadixPopover from "@radix-ui/react-popover";
import { ChevronDown, CircleX, Menu as MenuIcon, X } from "lucide-react";
import { copy } from "../copy";
import { cx } from "../lib/cx";
import { isBoxShortcut } from "./BoxBand";
import { POPOVER } from "./Popover";
import { Skeleton } from "./Skeleton";
import { SkipLink } from "./SkipLink";

export type Section = keyof typeof copy.nav.tabs;
export const SECTIONS: { key: Section; href: string }[] = [
  { key: "packages", href: "/packages" },
  { key: "projects", href: "/projects" },
  { key: "lessons", href: "/lessons" },
  { key: "drafts", href: "/drafts" },
  { key: "data", href: "/data" },
];

export type Viewer =
  | { status: "loading" }
  // agency: the implementing agency whose team the viewer is on (ticket 38), whose view the server applies.
  | { status: "signed-in"; email: string; agency?: string | null }
  | { status: "signed-out" }
  | { status: "error" };

const officerOf = (viewer: Viewer) => (viewer.status === "signed-in" ? (viewer.agency ?? null) : null);

const WIDE = "(min-width: 64rem)";

// The view popover hangs 8 px below the navy bar, not 8 px below the pill, so no white lip of
// it sits on the bar. The 32 px pill is centered in the 56 px bar, 12 px above its bottom edge.
const BELOW_BAR = 12 + 8;

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

// Who is signed in, as the first of the view lines. An error carries the circle-x icon, as the
// freshness stamp's does, so it does not read like the signed-in line.
function WhoLine({ viewer }: { viewer: Viewer }) {
  if (viewer.status === "loading") return <Skeleton className="h-[13px] w-[200px] max-w-full" />;
  if (viewer.status === "error") {
    return (
      <p className="flex items-start gap-1 text-caption text-ink-muted">
        <CircleX aria-hidden="true" className="size-4 shrink-0 text-error-icon" />
        {copy.nav.view.identityError}
      </p>
    );
  }
  return (
    <p className="text-caption text-ink-muted">
      {viewer.status === "signed-in" ? copy.nav.view.signedIn(viewer.email) : copy.nav.view.signedOut}
    </p>
  );
}

// The three lines about who is viewing, in the view popover and at the foot of the Menu panel.
function ViewLines({ viewer }: { viewer: Viewer }) {
  return (
    <div className="flex flex-col gap-2">
      <WhoLine viewer={viewer} />
      <p className="text-small text-pretty text-ink">
        {officerOf(viewer) ? copy.nav.view.currentOfficer(officerOf(viewer)!) : copy.nav.view.current}
      </p>
      <p className="text-caption text-pretty text-ink-muted">
        {officerOf(viewer) ? copy.nav.view.notReadyOfficer : copy.nav.view.notReady}
      </p>
    </div>
  );
}

function ViewSwitch({
  viewer,
  defaultOpen,
  menuButton,
}: {
  viewer: Viewer;
  defaultOpen?: boolean;
  // Where focus goes when a narrowing window closes the popover.
  menuButton: RefObject<HTMLButtonElement | null>;
}) {
  const [open, setOpen] = useState(defaultOpen ?? false);
  const body = useRef<HTMLDivElement>(null);
  const pill = useRef<HTMLButtonElement>(null);
  // Where Tab or Shift+Tab sends focus once the popover has closed. The popover is portaled to
  // the end of the page and holds nothing to focus, so without this Tab would leave the page.
  const after = useRef<HTMLElement | null>(null);

  // Narrowing the window below 1024 px hides the pill, so the popover closes with it.
  useWideChange((wide) => !wide && setOpen(false));
  return (
    <RadixPopover.Root open={open} onOpenChange={setOpen}>
      <RadixPopover.Trigger
        ref={pill}
        data-view-pill
        aria-haspopup="dialog"
        className={cx(
          "flex h-8 shrink-0 items-center gap-1 rounded-pill border border-surface px-3 text-button whitespace-nowrap text-surface",
          "transition-paint duration-150 hover:bg-primary-hover data-[state=open]:bg-primary-hover",
        )}
      >
        {officerOf(viewer) ? copy.nav.view.pill.officer : copy.nav.view.pill.staff}
        <ChevronDown aria-hidden="true" className={cx("size-4 transition-transform duration-150", open && "rotate-180")} />
      </RadixPopover.Trigger>
      <RadixPopover.Portal>
        <RadixPopover.Content
          align="end"
          sideOffset={BELOW_BAR}
          collisionPadding={16}
          aria-label={copy.nav.view.dialog}
          onOpenAutoFocus={(event) => {
            event.preventDefault();
            body.current?.focus();
          }}
          onKeyDown={(event) => {
            // Tab closes the popover and moves on to the box, the next control after the pill;
            // Shift+Tab closes it and goes back to the pill (the 06 brief's keyboard table).
            if (event.key !== "Tab") return;
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
            // Below 1024 px the pill is hidden and the Menu holds the view lines, so focus goes there.
            if (!window.matchMedia(WIDE).matches) {
              event.preventDefault();
              menuButton.current?.focus();
            }
          }}
          className={cx(POPOVER, "w-80 p-4")}
        >
          {/* Focus lands here so the three lines are read; it is not a control, so no ring. */}
          <div ref={body} tabIndex={-1} data-view-popover className="outline-none">
            <ViewLines viewer={viewer} />
          </div>
        </RadixPopover.Content>
      </RadixPopover.Portal>
    </RadixPopover.Root>
  );
}

function BarTab({ section, current, href }: { section: (typeof SECTIONS)[number]; current: boolean; href?: string }) {
  return (
    <a
      href={href ?? section.href}
      aria-current={current ? "page" : undefined}
      data-nav-tab={section.key}
      className={cx(
        "relative flex h-10 items-center px-3 text-body font-bold whitespace-nowrap text-surface",
        "after:absolute after:inset-x-3 after:bottom-0 after:h-[3px] after:transition-paint after:duration-150",
        current ? "after:bg-surface" : "hover:after:bg-line-strong",
      )}
    >
      {copy.nav.tabs[section.key]}
    </a>
  );
}

function PanelRow({
  section,
  current,
  onNavigate,
  href,
}: {
  section: (typeof SECTIONS)[number];
  current: boolean;
  href?: string;
  // A row opens its page and closes the panel.
  onNavigate: () => void;
}) {
  return (
    <a
      href={href ?? section.href}
      aria-current={current ? "page" : undefined}
      onClick={onNavigate}
      data-nav-tab={section.key}
      // Inset 6 px from each side (4 px here and 2 px on the list), so the 2 px focus ring with its
      // 2 px offset (DESIGN.md section 10) ends 2 px inside the panel and its edge never clips it
      // (the 06 brief). The text still starts on the grid margin.
      className={cx(
        "relative mx-1 flex h-12 items-center rounded-sm text-body font-bold text-ink-heading transition-paint duration-150",
        "before:absolute before:inset-y-0 before:left-0 before:w-[3px]",
        current ? "bg-tint before:bg-primary" : "hover:bg-tint-hover",
      )}
      style={{ paddingInline: "calc(var(--layout-margin) - 0.375rem)" }}
    >
      {copy.nav.tabs[section.key]}
    </a>
  );
}

export function TopNav({
  logo,
  current,
  home = false,
  viewer,
  homeHref = "/",
  menuOpen: menuOpenAtStart = false,
  viewOpen,
  projectsHref,
}: {
  // The logo, at least 24 px tall. The slot gives it clear space of half its height, and 24 px
  // before the wordmark, so the two never read as one co-branded name (DESIGN.md section 9). The app and
  // the gallery pass the World Bank's official file (web/src/assets/world-bank-logo.md).
  logo?: ReactNode;
  // The tab whose section holds the page; none on Home and the not-found page.
  current?: Section;
  home?: boolean;
  viewer: Viewer;
  homeHref?: string;
  // For the gallery: open the Menu panel or the view popover on the first render.
  menuOpen?: boolean;
  viewOpen?: boolean;
  // Where the Projects tab goes: Following for World Bank staff (ticket 37), All projects for everyone else.
  projectsHref?: string;
}) {
  const [menuOpen, setMenuOpen] = useState(menuOpenAtStart);
  const menuButton = useRef<HTMLButtonElement>(null);
  const header = useRef<HTMLDivElement>(null);
  // The control a resize just hid. Chrome takes focus from it before it reports the media
  // change, so the header notes it on blur and forgets it after the frame.
  const hidden = useRef<HTMLElement | null>(null);
  const panelId = useId();

  // "/" anywhere outside a text field focuses the box (OneBox), and closes the Menu panel first.
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (isBoxShortcut(event)) setMenuOpen(false);
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  // Widening the window to 1024 px closes the panel. A focused control that the new width hides
  // hands focus to its twin, or to the control at the bar's right end (the pill or the Menu).
  useWideChange((wide) => {
    if (wide) setMenuOpen(false);
    const active = document.activeElement;
    const root = header.current;
    const focused = active instanceof HTMLElement && root?.contains(active) ? active : active === document.body ? hidden.current : null;
    hidden.current = null;
    if (!root || !focused || focused.getClientRects().length > 0) return;
    const key = focused.dataset.navTab;
    const twin = key && wide ? root.querySelector<HTMLElement>(`[data-nav-bar] [data-nav-tab=${key}]`) : null;
    (twin ?? (wide ? root.querySelector<HTMLElement>("[data-view-pill]") : menuButton.current))?.focus();
  });

  // A div, not a header: the frame's one header holds this bar and the box band together.
  return (
    <div
      ref={header}
      onBlur={(event) => {
        const target = event.target as HTMLElement;
        if (event.relatedTarget || target.getClientRects().length > 0) return;
        hidden.current = target;
        requestAnimationFrame(() => (hidden.current = null));
      }}
      onKeyDown={(event) => {
        // Escape in the open Menu closes it and returns focus to the Menu button.
        if (event.key === "Escape" && menuOpen) {
          setMenuOpen(false);
          menuButton.current?.focus();
        }
      }}
    >
      <div data-nav-bar className="on-navy relative bg-navy text-surface">
        <SkipLink />
        <div className="layout flex h-14 items-center">
          {logo && (
            <div data-logo-slot className="flex h-14 shrink-0 items-center py-4 pr-6">
              {logo}
            </div>
          )}
          <a
            href={homeHref}
            aria-current={home ? "page" : undefined}
            className="flex h-10 shrink-0 items-center text-h3 text-surface underline-offset-4 hover:underline"
          >
            {copy.appName}
          </a>
          <nav aria-label={copy.nav.label} className="ml-6 hidden lg:block">
            <ul className="flex items-center">
              {SECTIONS.map((section) => (
                <li key={section.key}>
                  <BarTab section={section} current={section.key === current} href={section.key === "projects" ? projectsHref : undefined} />
                </li>
              ))}
            </ul>
          </nav>
          <div className="ml-auto hidden pl-6 lg:block">
            <ViewSwitch viewer={viewer} defaultOpen={viewOpen} menuButton={menuButton} />
          </div>
          <button
            ref={menuButton}
            type="button"
            aria-expanded={menuOpen}
            aria-controls={panelId}
            onClick={() => setMenuOpen(!menuOpen)}
            className={cx(
              "ml-auto flex shrink-0 items-center rounded-md border border-surface text-surface xs:rounded-pill lg:hidden",
              "transition-paint duration-150 hover:bg-primary-hover aria-expanded:bg-primary-hover",
              "size-11 flex-col justify-center gap-0.5 text-label",
              "xs:h-11 xs:w-auto xs:flex-row xs:gap-2 xs:px-3 xs:text-button",
            )}
          >
            {menuOpen ? <X aria-hidden="true" className="size-4" /> : <MenuIcon aria-hidden="true" className="size-4" />}
            {copy.nav.menu}
          </button>
        </div>
      </div>
      <div
        id={panelId}
        hidden={!menuOpen}
        data-menu-panel
        className="animate-menu-in border-b border-line bg-surface py-2 lg:hidden"
      >
        <nav aria-label={copy.nav.label}>
          <ul className="px-0.5">
            {SECTIONS.map((section) => (
              <li key={section.key}>
                <PanelRow
                  section={section}
                  current={section.key === current}
                  href={section.key === "projects" ? projectsHref : undefined}
                  onNavigate={() => setMenuOpen(false)}
                />
              </li>
            ))}
          </ul>
        </nav>
        <div className="layout mt-2 border-t border-line pt-4 pb-2">
          <ViewLines viewer={viewer} />
        </div>
      </div>
    </div>
  );
}
