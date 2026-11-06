// The Example note (ticket 41; the 41 design brief, 3.3 and 5.12): on the page of an item the seed command set up, the
// Tag "Example". Never an Alert and never coloured, because an example is not a state. Since ticket 126 the badge says
// it is an example, and its window says how: the first-person sentence on what Prism set up and what is real, which
// opens on hover, keyboard focus, a click or a tap, as a step label's window does.
import type { ReactNode } from "react";
import { Tag } from "./LessonParts";
import { DefinitionWindow } from "./Term";
import { copy } from "../copy";

export function ExampleNote({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <p data-example-note className={`flex flex-wrap items-center gap-2 text-caption text-ink-muted ${className}`}>
      <DefinitionWindow openOnHover inText={false} label={<Tag>{copy.home.example}</Tag>} title={copy.home.example} triggerClassName="no-underline">
        <span data-example-sentence>{children}</span>
      </DefinitionWindow>
    </p>
  );
}
