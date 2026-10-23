// The top navigation (DESIGN.md section 5): a navy bar, 56 px tall, with the logo, the
// Strata wordmark (a link to Home), five tabs and the view switch. Nouns navigate.
//
// From 1024 px (64rem) the tabs and the view switch sit in the bar. The full bar is 844 px
// wide and the 768 grid gives 672, so below 1024 a labelled Menu button holds them in a panel
// that pushes the page down. Below 360 px the button stacks its icon over its label.
//
// On navy, the selected tab has a 3 px white underline and hover a line-strong one; focus uses
// focus-on-dark. Only one Main navigation is exposed at a time: the bar's below 1024 px is
// display: none, and so is the panel's from 1024 px.
import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import * as RadixPopover from "@radix-ui/react-popover";
import { ChevronDown, Menu as MenuIcon, X } from "lucide-react";
import { copy } from "../copy";
import { cx } from "../lib/cx";
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

export type Viewer = { status: "loading" } | { status: "signed-in"; email: string } | { status: "error" };

const WIDE = "(min-width: 64rem)";

// The three lines about who is viewing, in the view popover and at the foot of the Menu panel.
function ViewLines({ viewer }: { viewer: Viewer }) {
  return (
    <div className="flex flex-col gap-2">
      {viewer.status === "loading" ? (
        <Skeleton className="h-[13px] w-[200px] max-w-full" />
      ) : (
        <p className="text-caption text-ink-muted">
          {viewer.status === "signed-in" ? copy.nav.view.signedIn(viewer.email) : copy.nav.view.identityError}
        </p>
      )}
      <p className="text-small text-ink">{copy.nav.view.current}</p>
      <p className="text-caption text-ink-muted">{copy.nav.view.notReady}</p>
    </div>
  );
}

function ViewSwitch({ viewer, defaultOpen }: { viewer: Viewer; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(defaultOpen ?? false);
  const body = useRef<HTMLDivElement>(null);
  return (
    <RadixPopover.Root open={open} onOpenChange={setOpen}>
      <RadixPopover.Trigger
        aria-haspopup="dialog"
        className={cx(
          "flex h-8 shrink-0 items-center gap-1 rounded-pill border border-surface px-3 text-button whitespace-nowrap text-surface",
          "transition-paint duration-150 hover:bg-primary-hover data-[state=open]:bg-primary-hover",
        )}
      >
        {copy.nav.view.pill}
        <ChevronDown aria-hidden="true" className={cx("size-4 transition-transform duration-150", open && "rotate-180")} />
      </RadixPopover.Trigger>
      <RadixPopover.Portal>
        <RadixPopover.Content
          align="end"
          sideOffset={8}
          collisionPadding={16}
          aria-label={copy.nav.view.dialog}
          onOpenAutoFocus={(event) => {
            event.preventDefault();
            body.current?.focus();
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

function BarTab({ section, current }: { section: (typeof SECTIONS)[number]; current: boolean }) {
  return (
    <a
      href={section.href}
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

function PanelRow({ section, current }: { section: (typeof SECTIONS)[number]; current: boolean }) {
  return (
    <a
      href={section.href}
      aria-current={current ? "page" : undefined}
      data-nav-tab={section.key}
      className={cx(
        "relative mx-1 flex h-12 items-center rounded-sm text-body font-bold text-ink-heading transition-paint duration-150",
        "before:absolute before:inset-y-0 before:left-0 before:w-[3px]",
        current ? "bg-tint before:bg-primary" : "hover:bg-tint-hover",
      )}
      style={{ paddingInline: "calc(var(--layout-margin) - 0.25rem)" }}
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
}: {
  // The logo, at least 24 px tall. The slot gives it clear space of half its height.
  logo: ReactNode;
  // The tab whose section holds the page; none on Home and the not-found page.
  current?: Section;
  home?: boolean;
  viewer: Viewer;
  homeHref?: string;
  // For the gallery: open the Menu panel or the view popover on the first render.
  menuOpen?: boolean;
  viewOpen?: boolean;
}) {
  const [menuOpen, setMenuOpen] = useState(menuOpenAtStart);
  const menuButton = useRef<HTMLButtonElement>(null);
  const panelId = useId();

  // Widening the window to 1024 px closes the panel.
  useEffect(() => {
    const wide = window.matchMedia(WIDE);
    const close = () => wide.matches && setMenuOpen(false);
    wide.addEventListener("change", close);
    return () => wide.removeEventListener("change", close);
  }, []);

  return (
    <header
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
          <div data-logo-slot className="flex h-14 shrink-0 items-center py-4 pr-3">
            {logo}
          </div>
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
                  <BarTab section={section} current={section.key === current} />
                </li>
              ))}
            </ul>
          </nav>
          <div className="ml-auto hidden pl-6 lg:block">
            <ViewSwitch viewer={viewer} defaultOpen={viewOpen} />
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
              "size-11 flex-col justify-center gap-0.5 text-label uppercase",
              "xs:h-11 xs:w-auto xs:flex-row xs:gap-2 xs:px-3 xs:text-button xs:normal-case",
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
          <ul>
            {SECTIONS.map((section) => (
              <li key={section.key}>
                <PanelRow section={section} current={section.key === current} />
              </li>
            ))}
          </ul>
        </nav>
        <div className="layout mt-2 border-t border-line pt-4 pb-2">
          <ViewLines viewer={viewer} />
        </div>
      </div>
    </header>
  );
}
