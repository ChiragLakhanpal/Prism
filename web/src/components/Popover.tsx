// The floating surfaces: a tooltip that opens on hover or focus, and a non-modal window that
// opens on click (DefinitionWindow, the view popover). Both use DESIGN.md section 4's popover
// look (surface, a 1 px line, radius 8, the section shadow), sit 8 px from what opened them,
// fade in over 160 ms (DESIGN.md section 4, Motion), and close on Escape. Radix places them and keeps them on screen.
//
// The tooltip follows WCAG 1.4.13 and the ticket 14 brief: hover opens it after 150 ms and
// focus at once; the pointer can move onto it; it closes 150 ms after the pointer leaves both;
// Escape closes it and focus stays put; only one is open at a time; a tap never opens it; focus
// the app gives back after a dialog closes does not open it, so it never covers what you return to. It
// is built on Radix Popover rather than Radix Tooltip, because Radix Tooltip closes on any
// scroll, and tabbing to a number lower on the page scrolls it into view.
import { useCallback, useEffect, useId, useRef, useState, type ReactNode } from "react";
import * as RadixPopover from "@radix-ui/react-popover";
import { cx } from "../lib/cx";

export const POPOVER =
  "z-50 rounded-md border border-line bg-surface text-ink shadow-popover data-[state=open]:animate-fade-in";

// The mark of something you can check or look up: a number with its source, a GLOSSARY.md
// term, a measure, the data date. One 1 px dotted line in line-strong, solid on hover, so
// every one of them looks the same.
export const DOTTED_UNDERLINE =
  "underline decoration-line-strong decoration-dotted decoration-1 underline-offset-3 hover:decoration-solid";

// How long hover waits before it opens a card, and before it closes one the pointer left.
export const HOVER_DELAY = 150;
const DELAY = HOVER_DELAY;
export const RETURNING = "data-returning";
export const returning = (element: Element) => element.hasAttribute(RETURNING);
const open = new Set<() => void>();

// Only one card that hover or focus opened is open at a time: claiming the place closes the others, each by its
// own hide. A step label's definition window opened on hover takes part too (Term.tsx, openOnHover).
export function claimHoverCard(hide: () => void) {
  for (const other of open) if (other !== hide) other();
  open.add(hide);
}
export function releaseHoverCard(hide: () => void) {
  open.delete(hide);
}

export function Tooltip({
  trigger,
  children,
  width = "max-w-(--tooltip-width)",
  quiet = false,
  side = "bottom",
  pressKeepsOpen = false,
}: {
  // One element that can take focus, such as a link or a button.
  trigger: ReactNode;
  children: ReactNode;
  width?: string;
  // Opens on nothing, as a marker whose source the evidence drawer already shows in full.
  quiet?: boolean;
  // Below the trigger, or above it where text under it must stay in view, as under a title's count (ticket 23).
  side?: "top" | "bottom";
  // A press on the trigger keeps the tooltip open, as the copy key's "Copied" follows its press (ticket 112). Otherwise
  // a press anywhere closes it.
  pressKeepsOpen?: boolean;
}) {
  const [shown, setShown] = useState(false);
  const id = useId();
  // The last press on the trigger. Radix reports a press outside the card when the click ends, and by then the press's
  // target may be gone, as the copy key's icon is once it turns into a check, so the press itself is compared.
  const pressed = useRef<Event | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  const hide = useCallback(() => {
    clearTimeout(timer.current);
    setShown(false);
    releaseHoverCard(hide);
  }, []);
  const show = useCallback(() => {
    clearTimeout(timer.current);
    claimHoverCard(hide);
    setShown(true);
  }, [hide]);
  const after = (action: () => void) => {
    clearTimeout(timer.current);
    timer.current = setTimeout(action, DELAY);
  };
  useEffect(() => hide, [hide]);

  return (
    <RadixPopover.Root open={shown} onOpenChange={(next) => (next ? show() : hide())}>
      <RadixPopover.Anchor
        asChild
        onPointerDown={(event) => {
          pressed.current = event.nativeEvent;
        }}
        aria-describedby={shown ? id : undefined}
        // Focus the app gives back, as when the evidence drawer closes (data-returning, set by
        // web/src/App.tsx), returns the reader to the answer without covering it, and so does the
        // pointer the page moved back under the trigger. The card opens again once the pointer or
        // the focus leaves and comes back.
        onPointerEnter={(event) => event.pointerType === "mouse" && !quiet && !returning(event.currentTarget) && after(show)}
        onPointerLeave={(event) => {
          if (event.pointerType !== "mouse") return;
          event.currentTarget.removeAttribute(RETURNING);
          after(hide);
        }}
        onFocus={(event) => (quiet || returning(event.currentTarget) ? hide() : show())}
        onBlur={(event) => {
          event.currentTarget.removeAttribute(RETURNING);
          hide();
        }}
      >
        {trigger}
      </RadixPopover.Anchor>
      <RadixPopover.Portal>
        <RadixPopover.Content
          id={id}
          role="tooltip"
          side={side}
          align="start"
          sideOffset={8}
          collisionPadding={16}
          onOpenAutoFocus={(event) => event.preventDefault()}
          onCloseAutoFocus={(event) => event.preventDefault()}
          // Radix reads the focus that opened the tooltip as focus outside it, and would close it
          // at once when Tab moves onto its trigger. The trigger's own blur closes it instead.
          onFocusOutside={(event) => event.preventDefault()}
          onPointerDownOutside={(event) => {
            if (pressKeepsOpen && event.detail.originalEvent === pressed.current) event.preventDefault();
          }}
          onPointerEnter={() => clearTimeout(timer.current)}
          onPointerLeave={() => after(hide)}
          className={cx(POPOVER, "px-3 py-2 text-small", width)}
        >
          {children}
        </RadixPopover.Content>
      </RadixPopover.Portal>
    </RadixPopover.Root>
  );
}
