// The frame every page shares: the navy bar, the box band, the page, and the independent-demo
// footer (DESIGN.md sections 5 and 8). One header (the banner landmark) holds the bar and the
// band, so the Main navigation, the search landmark around the box and the stamp sit in it. The
// page grows, so the footer sits at the bottom of short pages.
//
// Under the band, the page column and the evidence drawer sit side by side (ticket 14): the drawer
// narrows the page instead of covering it. The page column is a size container, so a page lays out
// by its own width, not the window's. Below 768 px the drawer is a modal sheet, and everything else
// is inert behind it.
import type { ReactNode } from "react";
import { copy } from "../copy";

export function Footer() {
  return (
    <footer className="border-t border-line">
      <p className="layout py-6 text-caption text-pretty text-ink-muted">{copy.footer}</p>
    </footer>
  );
}

export function Frame({
  nav,
  band,
  children,
  aside,
  inertPage = false,
}: {
  nav: ReactNode;
  band: ReactNode;
  children: ReactNode;
  // The evidence drawer, beside the page.
  aside?: ReactNode;
  // A modal sheet is open: the bar, the band and the page take no focus and no clicks.
  inertPage?: boolean;
}) {
  return (
    <div className="flex min-h-dvh flex-col bg-page">
      <header inert={inertPage}>
        {nav}
        {band}
      </header>
      <div className="flex flex-1 items-stretch">
        <div data-page-column inert={inertPage} className="@container/page flex min-w-0 flex-1 flex-col">
          <main id="main" tabIndex={-1} className="flex-1 pb-12 focus-visible:outline-none md:pb-16">
            {children}
          </main>
          <Footer />
        </div>
        {aside}
      </div>
    </div>
  );
}
