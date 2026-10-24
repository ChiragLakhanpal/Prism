// MeasureNum: a number that a data readiness measure gave (the 16 design brief, section 5.8). It is
// Num with a dotted underline: hover or focus shows a tooltip that says what was counted and when,
// and a click or Enter opens the measure's window, with its name, its definition, its numerator and
// denominator, when it was measured and the table it counted. The window is non-modal: focus moves
// to its title as it opens, and Escape or its 44 px close button closes it and returns focus to the
// number. A number with no measure behind it, such as a count of the rows below, has the tooltip
// alone.
import { useId, useRef, useState, type ReactNode } from "react";
import * as RadixPopover from "@radix-ui/react-popover";
import { cx } from "../lib/cx";
import { numBody, type NumValue } from "./Num";
import { DOTTED_UNDERLINE, Tooltip } from "./Popover";
import { DEFINITION_WINDOW, DefinitionContent, type DefinitionRows } from "./Term";

export type Measure = { title: ReactNode; definition: ReactNode; rows: DefinitionRows };

export function MeasureNum({
  value,
  tooltip,
  measure,
  className,
}: {
  value: NumValue;
  tooltip: ReactNode;
  measure?: Measure;
  className?: string;
}) {
  const [open, setOpen] = useState(false);
  const button = useRef<HTMLButtonElement>(null);
  const heading = useRef<HTMLHeadingElement>(null);
  const titleId = useId();
  const trigger = (
    <button
      ref={button}
      type="button"
      data-num
      aria-haspopup={measure ? "dialog" : undefined}
      aria-expanded={measure ? open : undefined}
      onClick={() => measure && setOpen((was) => !was)}
      // A short number, such as "two" or "10", pads its hit area to 24 px with a layer over it, not
      // its type (DESIGN.md section 10).
      className={cx(
        "relative inline cursor-pointer py-0.5 text-left tabular-nums after:absolute after:-inset-x-2 after:-inset-y-1 after:content-['']",
        DOTTED_UNDERLINE,
        className,
      )}
    >
      {numBody(value)}
    </button>
  );
  if (!measure) return <Tooltip trigger={trigger}>{tooltip}</Tooltip>;
  return (
    <RadixPopover.Root open={open} onOpenChange={setOpen}>
      <RadixPopover.Anchor asChild>
        <span>
          <Tooltip trigger={trigger}>{tooltip}</Tooltip>
        </span>
      </RadixPopover.Anchor>
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
          onCloseAutoFocus={(event) => {
            event.preventDefault();
            button.current?.focus();
          }}
          // A press on the number itself toggles the window; it is not a press outside it.
          onInteractOutside={(event) => {
            if (button.current?.contains(event.target as Node)) event.preventDefault();
          }}
          className={DEFINITION_WINDOW}
        >
          <DefinitionContent titleId={titleId} heading={heading} title={measure.title} rows={measure.rows}>
            {measure.definition}
          </DefinitionContent>
        </RadixPopover.Content>
      </RadixPopover.Portal>
    </RadixPopover.Root>
  );
}
