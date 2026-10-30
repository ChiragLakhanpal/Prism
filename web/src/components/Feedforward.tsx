// Feedforward as a button's description (ticket 126, the tuck-away inventory's pattern 5; DESIGN.md section 5): what a
// button will do that its label does not say, such as "The draft waits in Drafts for you to check. I send nothing.",
// is no longer a caption under the button. It is the button's tooltip, which opens on hover and keyboard focus, and its
// aria-describedby, so a screen reader still hears it with the button. A control whose own line a rule keeps on first
// sight, such as an upload's "never submits" (DESIGN.md section 7, rule 39), keeps its visible caption instead.
import { cloneElement, useId, type ReactElement, type ReactNode } from "react";
import { Tooltip } from "./Popover";

export function Feedforward({ sentence, children }: { sentence: ReactNode; children: ReactElement<{ "aria-describedby"?: string }> }) {
  const id = useId();
  const own = children.props["aria-describedby"];
  const button = cloneElement(children, { "aria-describedby": [own, id].filter(Boolean).join(" ") });
  return (
    <>
      <Tooltip trigger={button} keepDescription>
        {sentence}
      </Tooltip>
      {/* Hidden, yet a description may name it: the button's accessible description reads it. */}
      <span id={id} hidden data-feedforward-description>
        {sentence}
      </span>
    </>
  );
}
