// The refusal window (ticket 97; the redesign's plan, section 8.4; DESIGN.md section 5, Refusal). Under every refusal,
// in the answer panel and in the package's "Check your criteria", a flush ghost "See everything I turn down" opens a
// non-modal window, "What I turn down", that lists each refusal's lead and its why from the copy file's refusal keys,
// the same keys the refusal itself is written from. It is DESIGN.md's window, as the Measure number's: focus moves to
// its title as it opens, and Escape or its 44 px close button closes it and returns focus to the button. A long list
// scrolls inside the window, which keeps to the screen. WhatIDontDo, the window's body, was the last section of How
// Prism works until that page left the Data tab.
import { useId, useRef, useState } from "react";
import * as RadixPopover from "@radix-ui/react-popover";
import { List } from "lucide-react";
import { copy } from "../copy";
import { cx } from "../lib/cx";
import { Button } from "./Button";
import { DEFINITION_WINDOW, DefinitionContent } from "./Term";

// Every refusal's lead with its why, in the copy file's order.
export function WhatIDontDo() {
  return (
    <>
      <p>{copy.answer.refusalWindowIntro}</p>
      <dl data-dont-do className="mt-3 flex flex-col gap-3 border-t border-line pt-3">
        {Object.entries(copy.refusals).map(([key, refusal]) => (
          <div key={key} data-dont-do-key={key}>
            <dt className="font-semibold text-ink">{refusal.lead}</dt>
            <dd className="mt-1 text-ink">{refusal.why}</dd>
          </div>
        ))}
      </dl>
    </>
  );
}

export function RefusalWindow() {
  const [open, setOpen] = useState(false);
  const button = useRef<HTMLButtonElement>(null);
  const heading = useRef<HTMLHeadingElement>(null);
  const titleId = useId();
  return (
    <RadixPopover.Root open={open} onOpenChange={setOpen}>
      <RadixPopover.Anchor asChild>
        <span className="inline-flex">
          <Button
            ref={button}
            variant="ghost"
            flush
            icon={List}
            aria-haspopup="dialog"
            aria-expanded={open}
            data-refusal-all
            onClick={() => setOpen((was) => !was)}
          >
            {copy.answer.refusalAll}
          </Button>
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
          data-refusal-window
          onOpenAutoFocus={(event) => {
            event.preventDefault();
            heading.current?.focus();
          }}
          onCloseAutoFocus={(event) => {
            event.preventDefault();
            button.current?.focus();
          }}
          // A press on the button itself toggles the window; it is not a press outside it.
          onInteractOutside={(event) => {
            if (button.current?.contains(event.target as Node)) event.preventDefault();
          }}
          className={cx(DEFINITION_WINDOW, "max-h-[min(36rem,var(--radix-popover-content-available-height))] overflow-y-auto")}
        >
          <DefinitionContent titleId={titleId} heading={heading} title={copy.answer.refusalWindow}>
            <WhatIDontDo />
          </DefinitionContent>
        </RadixPopover.Content>
      </RadixPopover.Portal>
    </RadixPopover.Root>
  );
}
