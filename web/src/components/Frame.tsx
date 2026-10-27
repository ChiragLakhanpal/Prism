// The frame every page shares: the navy bar, the sidebar, the page, and the independent-demo footer (DESIGN.md
// sections 5 and 8). One header (the banner landmark) holds the bar, so the search landmark around the box sits in
// it, and from 1024 px it sticks to the top of the window (ticket 93). The page grows, so the footer sits at the bottom
// of short pages.
//
// Under the bar, the sidebar, the page column and the evidence drawer sit side by side (tickets 14 and 92): the
// drawer narrows the page instead of covering it. The page column is a size container, so a page lays out by its
// own width, not the window's. Below 768 px the drawer is a modal sheet, and below 1024 px the sidebar is the
// Menu sheet; while either is open, everything else is inert behind it.
//
// The Menu sheet's state lives here, because three parts share it: the Menu button in the bar opens it, the
// sidebar draws it, and the frame makes the rest of the page inert. Closing it from inside (Escape, "Close the
// menu", the scrim) returns focus to the Menu button; a widening window closes it and leaves focus where it is.
import { createContext, useCallback, useContext, useEffect, useId, useMemo, useRef, useState, type ReactNode, type RefObject } from "react";
import { flushSync } from "react-dom";
import { copy } from "../copy";
import { isBoxShortcut } from "./BoxBand";

export function Footer() {
  return (
    <footer className="border-t border-line">
      <p className="layout py-6 text-caption text-pretty text-ink-muted">{copy.footer}</p>
    </footer>
  );
}

// The sidebar is beside the page from 1024 px (64rem), and the Menu sheet below.
export const WIDE = "(min-width: 64rem)";

export type MenuSheet = {
  open: boolean;
  // Opens or closes the Menu sheet. Closing returns focus to the Menu button unless returnFocus is false.
  setOpen: (open: boolean, returnFocus?: boolean) => void;
  // The Menu button in the bar, where focus returns.
  button: RefObject<HTMLButtonElement | null>;
  // The sheet's id, for the Menu button's aria-controls.
  sheetId: string;
};

const MenuSheetContext = createContext<MenuSheet>({ open: false, setOpen: () => {}, button: { current: null }, sheetId: "" });

export function useMenuSheet(): MenuSheet {
  return useContext(MenuSheetContext);
}

export function Frame({
  nav,
  sidebar,
  children,
  aside,
  inertPage = false,
  menuOpen: menuOpenAtStart = false,
}: {
  // The top bar, with the box (TopNav.tsx).
  nav: ReactNode;
  // The sidebar beside the page from 1024 px, and the Menu sheet below (Sidebar.tsx).
  sidebar?: ReactNode;
  children: ReactNode;
  // The evidence drawer, beside the page.
  aside?: ReactNode;
  // A modal sheet is open: the bar and the page take no focus and no clicks.
  inertPage?: boolean;
  // For the gallery: open the Menu sheet on the first render.
  menuOpen?: boolean;
}) {
  const [menuOpen, setMenuOpenNow] = useState(menuOpenAtStart);
  const button = useRef<HTMLButtonElement>(null);
  const sheetId = useId();
  const returnFocus = useRef(false);
  const openNow = useRef(menuOpen);
  openNow.current = menuOpen;

  const setOpen = useCallback((open: boolean, back = true) => {
    returnFocus.current = !open && back;
    setMenuOpenNow(open);
  }, []);

  // Focus goes back to the Menu button once the bar is no longer inert.
  useEffect(() => {
    if (menuOpen || !returnFocus.current) return;
    returnFocus.current = false;
    button.current?.focus();
  }, [menuOpen]);

  useEffect(() => {
    const wide = window.matchMedia(WIDE);
    // Widening the window to 1024 px closes the sheet; its items are the sidebar now, so focus stays on them.
    const widened = () => wide.matches && setOpen(false, false);
    // Escape closes the sheet. "/" closes it before the box takes focus, so the box is no longer inert when it does:
    // this listens in the capture phase, ahead of the box's own listener.
    const onKey = (event: KeyboardEvent) => {
      if (!openNow.current) return;
      if (event.key === "Escape") setOpen(false);
      else if (isBoxShortcut(event)) flushSync(() => setOpen(false, false));
    };
    wide.addEventListener("change", widened);
    document.addEventListener("keydown", onKey, true);
    return () => {
      wide.removeEventListener("change", widened);
      document.removeEventListener("keydown", onKey, true);
    };
  }, [setOpen]);

  const sheet = useMemo(() => ({ open: menuOpen, setOpen, button, sheetId }), [menuOpen, setOpen, sheetId]);
  const inert = inertPage || menuOpen;
  return (
    <MenuSheetContext.Provider value={sheet}>
      <div className="flex min-h-window flex-col bg-page">
        {/* The header sticks from 1024 px, not the bar inside it, since a sticky part sticks only inside its parent. */}
        <header inert={inert} className="top-bar">
          {nav}
        </header>
        <div className="flex flex-1 items-stretch">
          {sidebar}
          <div data-page-column inert={inert} className="@container/page flex min-w-0 flex-1 flex-col">
            <main id="main" tabIndex={-1} className="flex-1 pb-12 focus-visible:outline-none @md/page:pb-16">
              {children}
            </main>
            <Footer />
          </div>
          {/* The drawer keeps its place in the row; it takes no focus while the Menu sheet is open. */}
          <div inert={menuOpen} className="contents">
            {aside}
          </div>
        </div>
      </div>
    </MenuSheetContext.Provider>
  );
}
