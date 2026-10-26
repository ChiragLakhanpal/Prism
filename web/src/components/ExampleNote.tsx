// The Example note (ticket 41; the 41 design brief, 3.3 and 5.12): on the page of an item the seed command set up, the
// Tag "Example" and one first-person caption that says what Strata set up and what is real. Never an Alert and never
// coloured, because an example is not a state.
import type { ReactNode } from "react";
import { Tag } from "./LessonParts";
import { copy } from "../copy";

export function ExampleNote({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <p data-example-note className={`flex flex-wrap items-center gap-2 text-caption text-ink-muted ${className}`}>
      <Tag>{copy.home.example}</Tag>
      <span>{children}</span>
    </p>
  );
}
