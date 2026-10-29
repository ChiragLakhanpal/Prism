// The frame every page shares: the navy bar, the sidebar, the page, the ask bar and the independent-demo footer
// (DESIGN.md sections 5 and 8). One header (the banner landmark) holds the bar, and from 1024 px it sticks to the top
// of the window (ticket 93). main holds at least the window's height less that bar, so a short page never pulls the
// footer into the first screen (ticket 94).
//
// The ask bar (ticket 113, the user's request of October 27, 2026): the one box floats at the bottom center of the page
// column, the column's last part before the footer, sticking at the window's foot. So it centers in the page column,
// narrows with it when the evidence drawer opens and never covers the drawer, and at the end of a page it sits above
// the footer's disclaimer instead of over it. It comes after the page's content in the Tab order, and its form is its
// own search landmark. It is marked as a part that sticks at the foot, so the frame's one hook counts it in the page's
// bottom scroll padding, and it floats above a page's own foot bar, such as the draft bar (lib/sticky.ts).
//
// Under the bar, the sidebar, the page column and the evidence drawer sit side by side (tickets 14 and 92): the
// drawer narrows the page instead of covering it. The page column and the drawer sit in the frame, the window less
// the sidebar, a size container the drawer does not change (ticket 94). The page column is a size container too, so a
// page lays out by its own width, not the window's; its margins follow the window, so the drawer never moves the
// page's left edge. The frame owns the parts that stick: one hook keeps focused elements clear of the bar, a sticky
// page head and a sticky foot (lib/sticky.ts). Below 768 px the drawer is a modal sheet, and below 1024 px the
// sidebar is the Menu sheet; while either is open, everything else is inert behind it.
//
// The Menu sheet's state lives here, because three parts share it: the Menu button in the bar opens it, the
// sidebar draws it, and the frame makes the rest of the page inert. Closing it from inside (Escape, "Close the
// menu", the scrim) returns focus to the Menu button; a widening window closes it and leaves focus where it is.
import { createContext, useCallback, useContext, useEffect, useId, useMemo, useRef, useState, type ReactNode, type RefObject } from "react";
import { flushSync } from "react-dom";
import { copy } from "../copy";
import { useStickyPadding } from "../lib/sticky";
import { isBoxShortcut } from "./OneBox";

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
  box,
  sidebar,
  children,
  aside,
  inertPage = false,
  menuOpen: menuOpenAtStart = false,
}: {
  // The top bar (TopNav.tsx).
  nav: ReactNode;
  // The one box (IntentBox in the app, OneBox in the gallery), which floats at the page column's foot.
  box?: ReactNode;
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
    // A layer open inside the sheet, such as the view switch's popover (ticket 59), takes Escape first and closes alone.
    const onKey = (event: KeyboardEvent) => {
      if (!openNow.current) return;
      if (event.key === "Escape") {
        if (!document.getElementById(sheetId)?.querySelector("[data-sheet-layer]")) setOpen(false);
      } else if (isBoxShortcut(event)) flushSync(() => setOpen(false, false));
    };
    wide.addEventListener("change", widened);
    document.addEventListener("keydown", onKey, true);
    return () => {
      wide.removeEventListener("change", widened);
      document.removeEventListener("keydown", onKey, true);
    };
  }, [setOpen, sheetId]);

  const sheet = useMemo(() => ({ open: menuOpen, setOpen, button, sheetId }), [menuOpen, setOpen, sheetId]);
  const inert = inertPage || menuOpen;
  const page = useRef<HTMLDivElement>(null);
  useStickyPadding(page);
  return (
    <MenuSheetContext.Provider value={sheet}>
      <div className="flex min-h-window flex-col bg-page">
        {/* The header sticks from 1024 px, not the bar inside it, since a sticky part sticks only inside its parent. */}
        <header inert={inert} className="top-bar">
          {nav}
        </header>
        <div className="flex flex-1 items-stretch">
          {sidebar}
          {/* The frame: the window less the sidebar, which the drawer opening beside the page does not change. */}
          <div data-frame className="@container/frame flex min-w-0 flex-1 items-stretch">
            <div ref={page} data-page-column inert={inert} className="@container/page flex min-w-0 flex-1 flex-col">
              {/* main grows to push the footer down and never shrinks below its content (flex: 1 0 auto). With flex-1
                  (1 1 0%), Chromium kept main's old height when a closed Task zone opened inside the page column, so
                  the footer printed over the opened content (ticket 100's critique, round 1). */}
              <main id="main" tabIndex={-1} className="min-h-main grow shrink-0 pb-12 focus-visible:outline-none @md/page:pb-16">
                {children}
              </main>
              {box && (
                <div data-box-slot data-sticky="bottom" className="ask-bar">
                  {box}
                </div>
              )}
              <Footer />
            </div>
            {/* The drawer keeps its place in the row; it takes no focus while the Menu sheet is open. */}
            <div inert={menuOpen} className="contents">
              {aside}
            </div>
          </div>
        </div>
      </div>
    </MenuSheetContext.Provider>
  );
}
