// Term: a GLOSSARY.md word with a dotted underline. A click, Enter or a tap opens its
// DefinitionWindow. DefinitionWindow: a non-modal window labeled by its title, with the full
// definition, optional rows (a measure's numerator and denominator, say), and a 44 px close
// button. Focus moves to the title when it opens; Escape closes it and focus returns to the
// word that opened it. DefinitionWindow draws the word that opens it too, so a measure's name
// and a Term carry the same dotted underline.
//
// openOnHover (ticket 27, a step label's full STEP name): the window also opens on a mouse hover
// and on keyboard focus, as a tooltip does, without taking focus, and closes when the pointer
// leaves it and its word or when focus moves on. A click, Enter or a tap pins it open as usual,
// with focus on its title, and then only Escape, its close button or a click outside close it.
// Glossary Terms elsewhere keep opening on click only.
import { useCallback, useEffect, useId, useRef, useState, type FocusEvent, type PointerEvent, type ReactNode, type RefObject } from "react";
import * as RadixPopover from "@radix-ui/react-popover";
import { X } from "lucide-react";
import { copy } from "../copy";
import { terms } from "../glossary";
import { cx } from "../lib/cx";
import { claimHoverCard, DOTTED_UNDERLINE, HOVER_DELAY, movedHere, POPOVER, releaseHoverCard, RETURNING, returning, scrolledUnder, watchPointer } from "./Popover";

export type DefinitionRows = { label: ReactNode; value: ReactNode }[];

// What a DefinitionWindow holds: its title, which takes focus as it opens, a 44 px close button,
// the definition, and optional rows. MeasureNum's window holds the same.
export function DefinitionContent({
  titleId,
  heading,
  title,
  children,
  rows,
}: {
  titleId: string;
  heading: RefObject<HTMLHeadingElement | null>;
  title: ReactNode;
  children: ReactNode;
  rows?: DefinitionRows;
}) {
  return (
    <>
      <div className="flex items-start justify-between gap-2">
        <h2 ref={heading} id={titleId} tabIndex={-1} className="pt-2 text-h2 text-ink-heading outline-none">
          {title}
        </h2>
        <RadixPopover.Close
          aria-label={copy.definition.close}
          className="-mt-2 -mr-2 flex size-11 shrink-0 items-center justify-center rounded-sm text-ink-muted hover:bg-tint-hover hover:text-ink"
        >
          <X aria-hidden="true" className="size-4" />
        </RadixPopover.Close>
      </div>
      <div className="mt-2 text-small text-ink">{children}</div>
      {rows && (
        <dl className="mt-3 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 border-t border-line pt-3 text-small">
          {rows.map((row, index) => (
            <div key={index} className="contents">
              <dt className="text-ink-muted">{row.label}</dt>
              <dd className="text-right tabular-nums wrap-anywhere text-ink">{row.value}</dd>
            </div>
          ))}
        </dl>
      )}
    </>
  );
}

export const DEFINITION_WINDOW = cx(POPOVER, "w-[min(22.5rem,calc(100vw-2rem))] p-4");

type DefinitionWindowProps = {
  // The word or measure name in the text that opens the window.
  label: ReactNode;
  title: ReactNode;
  children: ReactNode;
  rows?: DefinitionRows;
  // A trigger that stands alone in small type, such as Check a plan's count line, keeps 24 px of
  // height with "inline-flex min-h-6 items-center" (WCAG 2.5.8).
  triggerClassName?: string;
  // Words a screen reader hears with the trigger without opening the window, such as a step label's full STEP
  // name (ticket 27: "In STEP: Bid Evaluation Report and Recommendation for Award").
  describedBy?: string;
  // Opens on hover and keyboard focus too, as a step label does (see the top of this file).
  openOnHover?: boolean;
};

export function DefinitionWindow({ openOnHover = false, ...props }: DefinitionWindowProps) {
  return openOnHover ? <HoverDefinitionWindow {...props} /> : <ClickDefinitionWindow {...props} />;
}

function ClickDefinitionWindow({ label, title, children, rows, triggerClassName, describedBy }: Omit<DefinitionWindowProps, "openOnHover">) {
  const titleId = useId();
  const heading = useRef<HTMLHeadingElement>(null);
  return (
    <RadixPopover.Root>
      <RadixPopover.Trigger asChild>
        <button
          type="button"
          data-term
          aria-describedby={describedBy}
          className={cx("inline cursor-pointer py-0.5 text-left", DOTTED_UNDERLINE, triggerClassName)}
        >
          {label}
        </button>
      </RadixPopover.Trigger>
      <RadixPopover.Portal>
        <RadixPopover.Content
          side="bottom"
          align="start"
          sideOffset={8}
          collisionPadding={16}
          aria-labelledby={titleId}
          aria-modal="false"
          onOpenAutoFocus={(event) => {
            event.preventDefault();
            heading.current?.focus();
          }}
          className={DEFINITION_WINDOW}
        >
          <DefinitionContent titleId={titleId} heading={heading} title={title} rows={rows}>
            {children}
          </DefinitionContent>
        </RadixPopover.Content>
      </RadixPopover.Portal>
    </RadixPopover.Root>
  );
}

// The window a step label opens: "peek" is open from a hover or keyboard focus and holds no focus; "pinned" is open
// from a click, Enter or a tap, with focus on its title.
type Shown = "closed" | "peek" | "pinned";

function HoverDefinitionWindow({ label, title, children, rows, triggerClassName, describedBy }: Omit<DefinitionWindowProps, "openOnHover">) {
  const titleId = useId();
  const heading = useRef<HTMLHeadingElement>(null);
  const [shown, setShown] = useState<Shown>("closed");
  // The state as the Radix callbacks see it, which run outside a render.
  const now = useRef<Shown>("closed");
  now.current = shown;
  // Focus given back to the word after a pinned window closed, which must not open it again.
  const quiet = useRef(false);
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  // The page scrolled the word under a resting pointer: it waits for the pointer to move, as a number's tooltip does.
  const waiting = useRef(false);
  useEffect(watchPointer, []);

  // Closes a peek; a pinned window stays until Escape, its close button or a click outside.
  const hide = useCallback(() => {
    clearTimeout(timer.current);
    setShown((state) => (state === "peek" ? "closed" : state));
    releaseHoverCard(hide);
  }, []);
  const peek = useCallback(() => {
    clearTimeout(timer.current);
    claimHoverCard(hide);
    setShown((state) => (state === "closed" ? "peek" : state));
  }, [hide]);
  const after = (action: () => void) => {
    clearTimeout(timer.current);
    timer.current = setTimeout(action, HOVER_DELAY);
  };
  useEffect(() => hide, [hide]);
  // Pinning a window that hover had opened moves focus to its title, as opening it by a click does.
  useEffect(() => {
    if (shown === "pinned") heading.current?.focus();
  }, [shown]);

  return (
    <RadixPopover.Root
      open={shown !== "closed"}
      onOpenChange={(open) => {
        if (open) return;
        if (now.current === "pinned") quiet.current = true;
        clearTimeout(timer.current);
        releaseHoverCard(hide);
        setShown("closed");
      }}
    >
      <RadixPopover.Trigger asChild>
        <button
          type="button"
          data-term
          aria-describedby={describedBy}
          className={cx("inline cursor-pointer py-0.5 text-left", DOTTED_UNDERLINE, triggerClassName)}
          // A click, Enter or a tap pins the window, or closes a pinned one; Radix's own toggle would close a peek.
          onClick={(event) => {
            event.preventDefault();
            clearTimeout(timer.current);
            setShown((state) => (state === "pinned" ? "closed" : "pinned"));
          }}
          onPointerEnter={(event: PointerEvent<HTMLButtonElement>) => {
            if (event.pointerType !== "mouse" || returning(event.currentTarget)) return;
            if (scrolledUnder(event)) waiting.current = true;
            else after(peek);
          }}
          onPointerMove={(event: PointerEvent<HTMLButtonElement>) => {
            if (event.pointerType !== "mouse" || !waiting.current || !movedHere(event)) return;
            waiting.current = false;
            after(peek);
          }}
          onPointerLeave={(event: PointerEvent<HTMLButtonElement>) => {
            if (event.pointerType !== "mouse") return;
            waiting.current = false;
            event.currentTarget.removeAttribute(RETURNING);
            after(hide);
          }}
          // Keyboard focus opens it; the focus a mouse press gives does not, since the click that follows pins it.
          onFocus={(event: FocusEvent<HTMLButtonElement>) => {
            if (quiet.current) {
              quiet.current = false;
              return;
            }
            if (!returning(event.currentTarget) && event.currentTarget.matches(":focus-visible")) peek();
          }}
          onBlur={(event: FocusEvent<HTMLButtonElement>) => {
            event.currentTarget.removeAttribute(RETURNING);
            hide();
          }}
        >
          {label}
        </button>
      </RadixPopover.Trigger>
      <RadixPopover.Portal>
        <RadixPopover.Content
          side="bottom"
          align="start"
          sideOffset={8}
          collisionPadding={16}
          aria-labelledby={titleId}
          aria-modal="false"
          onOpenAutoFocus={(event) => {
            event.preventDefault();
            if (now.current === "pinned") heading.current?.focus();
          }}
          // Closing a peek leaves focus where it was; closing a pinned window gives it back to the word.
          onCloseAutoFocus={(event) => {
            if (!quiet.current) event.preventDefault();
            // Radix gives focus back right after this, unless you clicked or tabbed outside; either way the next
            // keyboard focus opens the window again.
            queueMicrotask(() => {
              quiet.current = false;
            });
          }}
          // A peek's word keeps focus outside the window, which must not close it.
          onFocusOutside={(event) => {
            if (now.current !== "pinned") event.preventDefault();
          }}
          onPointerEnter={() => clearTimeout(timer.current)}
          onPointerLeave={() => after(hide)}
          className={DEFINITION_WINDOW}
        >
          <DefinitionContent titleId={titleId} heading={heading} title={title} rows={rows}>
            {children}
          </DefinitionContent>
        </RadixPopover.Content>
      </RadixPopover.Portal>
    </RadixPopover.Root>
  );
}

export function Term({ term, children }: { term: string; children?: ReactNode }) {
  const definition = terms[term];
  if (!definition) throw new Error(`GLOSSARY.md has no term "${term}".`);
  return (
    <DefinitionWindow title={term} label={children ?? term}>
      {definition}
    </DefinitionWindow>
  );
}
