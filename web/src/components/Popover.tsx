// The floating surfaces: a tooltip that opens on hover or focus, and a non-modal window that
// opens on click (DefinitionWindow, the view popover). A window uses DESIGN.md section 4's popover
// look (surface, a 1 px line, radius 8, the section shadow); a tooltip the same with 4 px corners. Both
// sit 8 px from what opened them and close on Escape. Radix places them and keeps them on screen.
//
// The tooltip follows WCAG 1.4.13 and DESIGN.md section 5, Number tooltip (ticket 96): hover opens it after the
// pointer rests 150 ms, and keyboard focus at once; one opened while another is open, or less than 300 ms after
// another closed, appears at once with no movement, so moving along a row of numbers stays fast; otherwise it
// enters over 160 ms, growing from 0.97 out of the side that touches its trigger. The pointer can move onto it;
// it hides 100 ms after the pointer leaves both, and at once on blur. Escape hides it until the pointer or the
// focus leaves its trigger, and focus stays put. Only one is open at a time; a tap never opens it; focus the app
// gives back after a dialog closes does not open it, so it never covers what you return to; and a trigger the
// page scrolled under a resting pointer opens nothing until the pointer moves. A trigger inside the page's
// finding ([data-finding]) opens its tooltip under the whole finding, still left aligned with the trigger, so it
// never covers the sentence being read. It is built on Radix Popover rather than Radix Tooltip, because Radix
// Tooltip closes on any scroll, and tabbing to a number lower on the page scrolls it into view.
import {
  cloneElement,
  isValidElement,
  useCallback,
  useEffect,
  useId,
  useRef,
  useState,
  type ReactElement,
  type ReactNode,
  type Ref,
  type SyntheticEvent,
} from "react";
import * as RadixPopover from "@radix-ui/react-popover";
import { cx } from "../lib/cx";

export const POPOVER =
  "z-50 rounded-md border border-line bg-surface text-ink shadow-popover data-[state=open]:animate-fade-in";

// A tooltip: the popover's look with 4 px corners (DESIGN.md section 4, Radius), entering by tip-in (app.css). An
// evidence card keeps a container's 8 px.
const TOOLTIP = "z-50 border border-line bg-surface text-ink shadow-popover tip-in";

// The mark of something you can check or look up: a number with its source, a GLOSSARY.md
// term, a measure, the data date. One 1 px dotted line in line-strong, solid on hover, so
// every one of them looks the same.
export const DOTTED_UNDERLINE =
  "underline decoration-line-strong decoration-dotted decoration-1 underline-offset-3 hover:decoration-solid";

// How long hover waits before it opens a card, how long a card stays after the pointer leaves it and its trigger,
// and how soon after one card closes the next opens at once (DESIGN.md section 4, Motion).
export const HOVER_DELAY = 150;
const HIDE_DELAY = 100;
const NEXT_AT_ONCE = 300;
export const RETURNING = "data-returning";
export const returning = (element: Element) => element.hasAttribute(RETURNING);
const open = new Set<() => void>();
// When the last card that hover or focus opened closed, by the page's clock.
let lastClosed = Number.NEGATIVE_INFINITY;

// Only one card that hover or focus opened is open at a time: claiming the place closes the others, each by its
// own hide. A step label's definition window opened on hover takes part too (Term.tsx, openOnHover).
export function claimHoverCard(hide: () => void) {
  for (const other of open) if (other !== hide) other();
  open.add(hide);
}
export function releaseHoverCard(hide: () => void) {
  open.delete(hide);
}

// Where the pointer last moved to, and that move. When the page scrolls under a pointer that has not moved, the browser
// tells the page what is now under it with the pointer where it was, so a trigger the pointer entered at that same point
// came to it, and it waits for a move to another point. A real move into a trigger enters it before the move itself
// arrives, so its point is still a new one.
let pointer = { x: Number.NaN, y: Number.NaN };
let moved: Event | null = null;
let watching = false;
export function watchPointer() {
  if (watching) return;
  watching = true;
  window.addEventListener(
    "pointermove",
    (event) => {
      if (event.clientX === pointer.x && event.clientY === pointer.y) return;
      pointer = { x: event.clientX, y: event.clientY };
      moved = event;
    },
    { capture: true, passive: true },
  );
}

// The pointer entered a trigger at the point it last moved to: the page scrolled the trigger under a resting pointer.
// A step label's hover window (Term.tsx) waits for a real move too, so it never closes a number's tooltip that way.
export const scrolledUnder = (event: { clientX: number; clientY: number }) => event.clientX === pointer.x && event.clientY === pointer.y;
// A move over the trigger that is a real one, to a new point.
export const movedHere = (event: { nativeEvent: Event }) => event.nativeEvent === moved;

// Where a tooltip is placed from: its trigger, or for a trigger inside the page's finding, the whole finding's height
// at the trigger's left edge and width.
function anchorRect(trigger: HTMLElement | null): DOMRect {
  if (!trigger) return new DOMRect();
  const own = trigger.getBoundingClientRect();
  const finding = trigger.closest("[data-finding]");
  if (!finding) return own;
  const whole = finding.getBoundingClientRect();
  return new DOMRect(own.left, whole.top, own.width, whole.height);
}

type Handler<E> = ((event: E) => void) | undefined;
// The trigger's own handler first, then the tooltip's, as Radix's Slot merges them.
function both<E extends SyntheticEvent>(own: Handler<E>, added: (event: E) => void) {
  return (event: E) => {
    own?.(event);
    added(event);
  };
}

type TriggerProps = {
  ref?: Ref<HTMLElement>;
  "aria-describedby"?: string;
  onPointerDown?: (event: React.PointerEvent<HTMLElement>) => void;
  onPointerEnter?: (event: React.PointerEvent<HTMLElement>) => void;
  onPointerMove?: (event: React.PointerEvent<HTMLElement>) => void;
  onPointerLeave?: (event: React.PointerEvent<HTMLElement>) => void;
  onFocus?: (event: React.FocusEvent<HTMLElement>) => void;
  onBlur?: (event: React.FocusEvent<HTMLElement>) => void;
};

export function Tooltip({
  trigger,
  children,
  // At most the tooltip width, and never wider than the window less its 16 px edges, so at 320 px it stays whole on
  // screen (WCAG 1.4.10).
  width = "max-w-[min(var(--tooltip-width),calc(100vw-2rem))]",
  quiet = false,
  side = "bottom",
  pressKeepsOpen = false,
  card = false,
  keepDescription = false,
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
  // An evidence card, a container with 8 px corners, rather than a tooltip's 4 px.
  card?: boolean;
  // The trigger's own description already holds the tooltip's words, as Feedforward's hidden sentence does, so it stays
  // while the tooltip shows and the tooltip adds nothing to it (the 126 review, follow-up 1).
  keepDescription?: boolean;
}) {
  const [shown, setShown] = useState(false);
  // Opened at once, with no movement: by keyboard focus, or while or right after another card was open.
  const [instant, setInstant] = useState(false);
  const id = useId();
  const element = useRef<HTMLElement | null>(null);
  // The last press on the trigger. Radix reports a press outside the card when the click ends, and by then the press's
  // target may be gone, as the copy key's icon is once it turns into a check, so the press itself is compared.
  const pressed = useRef<Event | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const showing = useRef(false);
  // Escape hid the card: it stays hidden until the pointer or the focus leaves the trigger (WCAG 1.4.13).
  const dismissed = useRef(false);
  // The page scrolled the trigger under a resting pointer: the card waits for the pointer to move.
  const waiting = useRef(false);
  // The point Radix places the card from, read each time it places it.
  const anchor = useRef({ getBoundingClientRect: () => anchorRect(element.current), get contextElement() { return element.current ?? undefined; } });

  useEffect(watchPointer, []);
  const hide = useCallback(() => {
    clearTimeout(timer.current);
    if (showing.current) lastClosed = performance.now();
    showing.current = false;
    setShown(false);
    releaseHoverCard(hide);
  }, []);
  const show = useCallback(
    (atOnce: boolean) => {
      clearTimeout(timer.current);
      claimHoverCard(hide);
      showing.current = true;
      setInstant(atOnce);
      setShown(true);
    },
    [hide],
  );
  // A resting pointer: the card opens after 150 ms, or at once while another is open or right after one closed.
  const rest = () => {
    clearTimeout(timer.current);
    if (dismissed.current || showing.current) return;
    const another = [...open].some((other) => other !== hide);
    if (another || performance.now() - lastClosed < NEXT_AT_ONCE) show(true);
    else timer.current = setTimeout(() => show(false), HOVER_DELAY);
  };
  const leave = () => {
    clearTimeout(timer.current);
    timer.current = setTimeout(hide, HIDE_DELAY);
  };
  useEffect(() => hide, [hide]);

  if (!isValidElement(trigger)) return <>{trigger}</>;
  const own = (trigger as ReactElement<TriggerProps>).props;
  const wired = cloneElement(trigger as ReactElement<TriggerProps>, {
    ref: (node: HTMLElement | null) => {
      element.current = node;
      const ref = own.ref;
      if (typeof ref === "function") ref(node);
      else if (ref) (ref as { current: HTMLElement | null }).current = node;
    },
    "aria-describedby": shown && !keepDescription ? id : own["aria-describedby"],
    onPointerDown: both(own.onPointerDown, (event) => {
      pressed.current = event.nativeEvent;
    }),
    // Focus the app gives back, as when the evidence drawer closes (data-returning, set by web/src/App.tsx), returns
    // the reader to the answer without covering it, and so does the pointer the page moved back under the trigger.
    // The card opens again once the pointer or the focus leaves and comes back.
    onPointerEnter: both(own.onPointerEnter, (event) => {
      if (event.pointerType !== "mouse" || quiet || returning(event.currentTarget)) return;
      if (scrolledUnder(event)) waiting.current = true;
      else rest();
    }),
    onPointerMove: both(own.onPointerMove, (event) => {
      if (event.pointerType !== "mouse" || !waiting.current || !movedHere(event)) return;
      waiting.current = false;
      rest();
    }),
    onPointerLeave: both(own.onPointerLeave, (event) => {
      if (event.pointerType !== "mouse") return;
      event.currentTarget.removeAttribute(RETURNING);
      waiting.current = false;
      dismissed.current = false;
      leave();
    }),
    onFocus: both(own.onFocus, (event) => {
      if (quiet || returning(event.currentTarget)) hide();
      else if (!dismissed.current) show(true);
    }),
    onBlur: both(own.onBlur, (event) => {
      event.currentTarget.removeAttribute(RETURNING);
      dismissed.current = false;
      hide();
    }),
  });

  return (
    <RadixPopover.Root open={shown} onOpenChange={(next) => (next ? show(true) : hide())}>
      {wired}
      <RadixPopover.Anchor virtualRef={anchor} />
      <RadixPopover.Portal>
        <RadixPopover.Content
          id={id}
          role="tooltip"
          side={side}
          align="start"
          sideOffset={8}
          collisionPadding={16}
          data-instant={instant ? "" : undefined}
          onOpenAutoFocus={(event) => event.preventDefault()}
          onCloseAutoFocus={(event) => event.preventDefault()}
          onEscapeKeyDown={() => {
            dismissed.current = true;
          }}
          // Radix reads the focus that opened the tooltip as focus outside it, and would close it
          // at once when Tab moves onto its trigger. The trigger's own blur closes it instead.
          onFocusOutside={(event) => event.preventDefault()}
          onPointerDownOutside={(event) => {
            if (pressKeepsOpen && event.detail.originalEvent === pressed.current) event.preventDefault();
          }}
          onPointerEnter={() => clearTimeout(timer.current)}
          onPointerLeave={leave}
          className={cx(TOOLTIP, card ? "rounded-md" : "rounded-sm", "px-3 py-2 text-small", width)}
        >
          {children}
        </RadixPopover.Content>
      </RadixPopover.Portal>
    </RadixPopover.Root>
  );
}
