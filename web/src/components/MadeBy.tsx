// Made-by window (ticket 126, the tuck-away inventory's pattern 1; DESIGN.md section 5): how Strata built a block, such
// as "I built this summary from World Bank records as of October 29, 2026. No model wrote it.", which a reader rarely
// asks for, so it is one press away instead of on first sight. A lucide info icon button, a 24 px target in ink-muted,
// sits after the last word of the sentence or heading it describes. Its accessible name says what it opens ("How I
// built this summary"), and it opens a DefinitionWindow as a step label does: on hover and keyboard focus, and pinned
// by a click, Enter or a tap. The window holds the made-by sentence with its dates as Nums, so the as-of date stays a
// number the reader can check (CLAUDE.md rule 2). The Summary, Data readiness, Following and Home use it.
//
// InfoWindow is the same icon and window for a note that answers a question only some readers ask, such as why a
// project's loan amounts add up to more than its commitment (the Summary's Money table, kind "money-note").
import type { ReactNode } from "react";
import { Info } from "lucide-react";
import { DefinitionWindow } from "./Term";

type InfoKind = "made-by" | "money-note" | "note";

export function InfoWindow({ name, children, kind }: { name: string; children: ReactNode; kind: InfoKind }) {
  return (
    // A word joiner keeps the icon on the line of the word before it, so it never starts a line alone. It is drawn by
    // CSS, so the sentence's own text, which a test or a copy reads, stays the sentence's.
    <span
      data-made-by={kind === "made-by" ? "" : undefined}
      data-money-note={kind === "money-note" ? "" : undefined}
      className="whitespace-nowrap before:content-['\2060']"
    >
      <DefinitionWindow openOnHover iconLabel={name} title={name} label={<Info aria-hidden="true" className="size-4" />} triggerClassName="ml-1">
        {children}
      </DefinitionWindow>
    </span>
  );
}

export function MadeBy({ name, children }: { name: string; children: ReactNode }) {
  return (
    <InfoWindow name={name} kind="made-by">
      <p data-made-by-sentence>{children}</p>
    </InfoWindow>
  );
}
