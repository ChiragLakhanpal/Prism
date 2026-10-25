// Term: a GLOSSARY.md word with a dotted underline. A click, Enter or a tap opens its
// DefinitionWindow. DefinitionWindow: a non-modal window labeled by its title, with the full
// definition, optional rows (a measure's numerator and denominator, say), and a 44 px close
// button. Focus moves to the title when it opens; Escape closes it and focus returns to the
// word that opened it. DefinitionWindow draws the word that opens it too, so a measure's name
// and a Term carry the same dotted underline.
import { useId, useRef, type ReactNode, type RefObject } from "react";
import * as RadixPopover from "@radix-ui/react-popover";
import { X } from "lucide-react";
import { copy } from "../copy";
import { terms } from "../glossary";
import { cx } from "../lib/cx";
import { DOTTED_UNDERLINE, POPOVER } from "./Popover";

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
        <h2 ref={heading} id={titleId} tabIndex={-1} className="pt-2 text-title text-ink-heading outline-none">
          {title}
        </h2>
        <RadixPopover.Close
          aria-label={copy.definition.close}
          className="-mt-2 -mr-2 flex size-11 shrink-0 items-center justify-center rounded-pill text-ink-muted hover:bg-tint-hover hover:text-ink"
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

export function DefinitionWindow({
  label,
  title,
  children,
  rows,
  triggerClassName,
  describedBy,
}: {
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
}) {
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

export function Term({ term, children }: { term: string; children?: ReactNode }) {
  const definition = terms[term];
  if (!definition) throw new Error(`GLOSSARY.md has no term "${term}".`);
  return (
    <DefinitionWindow title={term} label={children ?? term}>
      {definition}
    </DefinitionWindow>
  );
}
