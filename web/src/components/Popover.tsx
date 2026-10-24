// The floating surfaces: a tooltip that opens on hover or focus, and a non-modal window that
// opens on click (DefinitionWindow, the view popover). Both use DESIGN.md section 4's popover
// look (surface, a 1 px line, radius 8, the section shadow), sit 8 px from what opened them,
// fade in over 120 ms, and close on Escape. Radix places them and keeps them on screen.
//
// The tooltip follows WCAG 1.4.13 and the ticket 14 brief: hover opens it after 150 ms and
// focus at once; the pointer can move onto it; it closes 150 ms after the pointer leaves both;
// Escape closes it and focus stays put; only one is open at a time; a tap never opens it. It
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

const DELAY = 150;
const open = new Set<() => void>();

export function Tooltip({
  trigger,
  children,
  width = "max-w-[20rem]",
}: {
  // One element that can take focus, such as a link or a button.
  trigger: ReactNode;
  children: ReactNode;
  width?: string;
}) {
  const [shown, setShown] = useState(false);
  const id = useId();
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  const hide = useCallback(() => {
    clearTimeout(timer.current);
    setShown(false);
    open.delete(hide);
  }, []);
  const show = useCallback(() => {
    clearTimeout(timer.current);
    for (const other of open) if (other !== hide) other();
    open.add(hide);
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
        aria-describedby={shown ? id : undefined}
        onPointerEnter={(event) => event.pointerType === "mouse" && after(show)}
        onPointerLeave={(event) => event.pointerType === "mouse" && after(hide)}
        onFocus={show}
        onBlur={hide}
      >
        {trigger}
      </RadixPopover.Anchor>
      <RadixPopover.Portal>
        <RadixPopover.Content
          id={id}
          role="tooltip"
          side="bottom"
          align="start"
          sideOffset={8}
          collisionPadding={16}
          onOpenAutoFocus={(event) => event.preventDefault()}
          onCloseAutoFocus={(event) => event.preventDefault()}
          // Radix reads the focus that opened the tooltip as focus outside it, and would close it
          // at once when Tab moves onto its trigger. The trigger's own blur closes it instead.
          onFocusOutside={(event) => event.preventDefault()}
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
