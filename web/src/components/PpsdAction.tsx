// "Suggest {n} PPSD risk rows" (ticket 36; the 36 brief, sections 3.1, 5.1 and 8.4): the package workspace's one
// solid button. Since ticket 101 it sits in zone 3 at every width, after the risks it drafts from, where the selection
// is made: the package head no longer sticks, so it holds no action. Its count is your own selection, from the same
// state section 3 shows, so the button says what it will make before the click.
//
// Held, with its reason, when no risk shown is selected, when the selection could not be saved, and in a preview;
// gone, with a caption, as of a past date; absent while section 3 has no rows.
import { copy } from "../copy";
import { startPpsdRows } from "../lib/drafts";
import { useStore } from "../lib/store";
import { officerAgency } from "../lib/uploads";
import { formatNumber } from "../lib/format";
import { navigate } from "../lib/router";
import { Button } from "./Button";
import { Feedforward } from "./Feedforward";
import { useId } from "react";
import { previewReason } from "../lib/view";

const words = copy.packageWorkspace.ppsdAction;

// What section 3 shows now: how many risks it lists, how many of them you selected, and whether the last save failed.
export type RiskSelection = { rows: number; chosen: number; saveFailed: boolean };

export function PpsdAction({
  pkg,
  selection,
  preview,
  asOf,
}: {
  pkg: { id: string; title: string; step_reference: string | null };
  selection: RiskSelection | null;
  preview: boolean;
  asOf: boolean;
}) {
  const reasonId = useId();
  const describedId = useId();
  const feedforwardId = useId();
  // An implementing agency officer drafts the agency's own kind, in their own words (ticket 38).
  const officer = Boolean(useStore(officerAgency));
  if (!selection || selection.rows === 0) return null;
  if (asOf) {
    return (
      <p className="max-w-[320px] text-caption text-ink-muted" data-ppsd-action="asof" data-placement="zone">
        {words.asof}
      </p>
    );
  }
  const held = preview || selection.saveFailed || selection.chosen === 0;
  const reason = preview ? (previewReason("start_draft") ?? words.heldPreview) : selection.saveFailed ? words.heldSaveFailed : words.heldNoneInline;
  const start = () => {
    if (held) return;
    navigate(startPpsdRows({ ...pkg, selected: selection.chosen }, null, officer ? "ppsd_rows_agency" : "ppsd_rows"));
  };
  return (
    <div className="flex flex-col items-start gap-2" data-ppsd-action={held ? "held" : "live"} data-placement="zone">
      {held ? (
        <Button variant="primary" held aria-describedby={reasonId} onClick={start} className="w-full min-[30rem]:w-auto">
          {officer ? words.agencyHeldLabel : words.heldLabel}
        </Button>
      ) : (
        // The feedforward is the button's tooltip and description (ticket 126, pattern 5).
        <Feedforward sentence={words.feedforward}>
          <Button variant="primary" aria-describedby={describedId} onClick={start} className="w-full min-[30rem]:w-auto">
            {(officer ? words.agencyButton : words.button)(selection.chosen, formatNumber(selection.chosen, { compact: false }))}
          </Button>
        </Feedforward>
      )}
      {held ? (
        <p id={reasonId} className="max-w-[320px] text-caption text-ink-muted" data-ppsd-held>
          {reason}
        </p>
      ) : (
        <p id={describedId} className="sr-only">
          {officer ? words.agencyDescription : words.description}
        </p>
      )}
    </div>
  );
}
