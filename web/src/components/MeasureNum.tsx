// MeasureNum: a number that opens a window (the 16 design brief, section 5.8; DESIGN.md section 5, Number
// tooltip, Window variant): a data readiness measure's number, or Home's briefing count word (ticket 96). It
// is Num with a dotted underline: hover or focus shows its tooltip, which says what the number is, where it
// came from and, when a window opens, what a click does, and a click or Enter opens the window, with its
// name, its definition and its rows: a measure's numerator and denominator, when it was measured and the
// table it counted, or the list of what a count word counts. The window is non-modal: focus moves to its
// title as it opens, and Escape or its 44 px close button closes it and returns focus to the number. A
// number with no window behind it, such as a count of the rows below, has the tooltip alone, with no
// action line.
import { useId, useRef, useState, type ReactNode } from "react";
import * as RadixPopover from "@radix-ui/react-popover";
import { copy } from "../copy";
import { cx } from "../lib/cx";
import { numBody, NumTip, type NumValue } from "./Num";
import { DOTTED_UNDERLINE, Tooltip } from "./Popover";
import { DEFINITION_WINDOW, DefinitionContent, type DefinitionRows } from "./Term";

// counted names the measure behind the window, by its source and its name in strata.ops.data_readiness,
// on the number as data-source and data-measure, so a test can check each window against the registries.
export type Measure = { title: ReactNode; definition: ReactNode; rows?: DefinitionRows; counted?: { source: string; measure: string } };

export function MeasureNum({
  value,
  tooltip,
  from,
  act,
  measure,
  className,
  inText = false,
}: {
  value: NumValue;
  // What the number is, the tooltip's first part.
  tooltip: ReactNode;
  // Where it came from, with its date (num.from).
  from?: ReactNode;
  // What a click opens, when a window does; a measure's window by default.
  act?: ReactNode;
  measure?: Measure;
  className?: string;
  // A number in a line of running text, such as a headline or a briefing, keeps its padding inside the line's own
  // height, so each line keeps its pitch (ticket 91's review). In a stack of values its padding spaces them.
  inText?: boolean;
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
      data-num-click={measure ? "" : undefined}
      data-num-opens={measure ? "window" : undefined}
      data-source={measure?.counted?.source}
      data-measure={measure?.counted?.measure}
      aria-haspopup={measure ? "dialog" : undefined}
      aria-expanded={measure ? open : undefined}
      onClick={() => measure && setOpen((was) => !was)}
      // A short number, such as "two" or "10", pads its hit area to 24 px with a layer over it, not
      // its type (DESIGN.md section 10). In running text, the negative margin keeps its 2 px of padding inside
      // the line's own height, so a line in lead type that holds one stays 28 px tall (ticket 91's review).
      className={cx(
        "relative inline cursor-pointer py-0.5 text-left tabular-nums after:absolute after:-inset-x-2 after:-inset-y-1 after:content-['']",
        inText && "-my-0.5",
        DOTTED_UNDERLINE,
        className,
      )}
    >
      {numBody(value)}
    </button>
  );
  const tip = <NumTip what={tooltip} from={from} act={measure ? (act ?? copy.num.act.measure) : undefined} />;
  if (!measure) return <Tooltip trigger={trigger}>{tip}</Tooltip>;
  return (
    <RadixPopover.Root open={open} onOpenChange={setOpen}>
      <RadixPopover.Anchor asChild>
        <span>
          <Tooltip trigger={trigger}>{tip}</Tooltip>
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
