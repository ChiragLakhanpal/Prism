// Term: a GLOSSARY.md word with a dotted underline. A click, Enter or a tap opens its
// DefinitionWindow. DefinitionWindow: a non-modal window labelled by its title, with the full
// definition, optional rows (a measure's numerator and denominator, say), and a 44 px close
// button. Focus moves to the title when it opens; Escape closes it and focus returns to the
// word that opened it.
import { useId, useRef, type ReactNode } from "react";
import * as RadixPopover from "@radix-ui/react-popover";
import { X } from "lucide-react";
import { copy } from "../copy";
import { terms } from "../glossary";
import { cx } from "../lib/cx";
import { POPOVER } from "./Popover";

export function DefinitionWindow({
  trigger,
  title,
  children,
  rows,
}: {
  trigger: ReactNode;
  title: ReactNode;
  children: ReactNode;
  rows?: { label: ReactNode; value: ReactNode }[];
}) {
  const titleId = useId();
  const heading = useRef<HTMLHeadingElement>(null);
  return (
    <RadixPopover.Root>
      <RadixPopover.Trigger asChild>{trigger}</RadixPopover.Trigger>
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
          className={cx(POPOVER, "w-[min(22.5rem,calc(100vw-2rem))] p-4")}
        >
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
                  <dd className="text-right tabular-nums text-ink">{row.value}</dd>
                </div>
              ))}
            </dl>
          )}
        </RadixPopover.Content>
      </RadixPopover.Portal>
    </RadixPopover.Root>
  );
}

export function Term({ term, children }: { term: string; children?: ReactNode }) {
  const definition = terms[term];
  if (!definition) throw new Error(`GLOSSARY.md has no term "${term}".`);
  return (
    <DefinitionWindow
      title={term}
      trigger={
        <button
          type="button"
          data-term
          className="inline cursor-pointer py-0.5 text-left underline decoration-line-strong decoration-dotted decoration-1 underline-offset-3 hover:decoration-solid"
        >
          {children ?? term}
        </button>
      }
    >
      {definition}
    </DefinitionWindow>
  );
}
