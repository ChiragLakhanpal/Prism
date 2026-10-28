// The space line (DESIGN.md section 5, Space line; ticket 110). A reading page that keeps columns 9 to 12 free for the
// evidence drawer says, in one caption line in those columns, what the space is for: the package page from a page area
// of 75rem, a draft's page from a frame of 75rem. The page places it (EightColumns' and DocumentColumn's beside slot);
// this draws the line, and hides it while the drawer is open, which moves nothing else, since the line sits in its own
// grid area beside the work. Ticket 101's side panel takes its place on the package page.
import { PanelRight } from "lucide-react";
import { address } from "../lib/router";
import { evidenceIn } from "../lib/evidence";
import { useStore } from "../lib/store";

export function SpaceLine({ children }: { children: string }) {
  const open = evidenceIn(useStore(address).search) !== null;
  if (open) return null;
  return (
    <p data-space-line className="flex items-start gap-2 text-caption text-ink-muted">
      <PanelRight aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
      {children}
    </p>
  );
}
