// The frame every page shares: the navy bar, the box band, the page, and the independent-demo
// footer (DESIGN.md sections 5 and 8). One header (the banner landmark) holds the bar and the
// band, so the Main navigation, the search landmark around the box and the stamp sit in it. The
// page grows, so the footer sits at the bottom of short pages.
import type { ReactNode } from "react";
import { copy } from "../copy";

export function Footer() {
  return (
    <footer className="border-t border-line">
      <p className="layout py-6 text-caption text-pretty text-ink-muted">{copy.footer}</p>
    </footer>
  );
}

export function Frame({ nav, band, children }: { nav: ReactNode; band: ReactNode; children: ReactNode }) {
  return (
    <div className="flex min-h-dvh flex-col bg-page">
      <header>
        {nav}
        {band}
      </header>
      <main id="main" tabIndex={-1} className="flex-1 pb-12 focus-visible:outline-none md:pb-16">
        {children}
      </main>
      <Footer />
    </div>
  );
}
