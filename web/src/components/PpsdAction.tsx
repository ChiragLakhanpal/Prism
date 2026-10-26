// "Suggest {n} PPSD risk rows" (ticket 36; the 36 brief, sections 3.1, 5.1 and 8.4): the package workspace's one
// solid button. It sits in the sticky header from a page area of 768 px, so it stays in reach while the column
// scrolls, and inside section 3 under the last risk below that, where the selection is made; only one copy is ever
// in the accessibility tree, the other display: none. Its count is your own selection, from the same state section 3
// shows, so the button says what it will make before the click.
//
// Held, with its reason, when no risk shown is selected, when the selection could not be saved, and in a preview;
// gone, with a caption, as of a past date; absent while section 3 has no rows.
import { copy } from "../copy";
import { cx } from "../lib/cx";
import { startPpsdRows } from "../lib/drafts";
import { useStore } from "../lib/store";
import { officerAgency } from "../lib/uploads";
import { formatNumber } from "../lib/format";
import { navigate } from "../lib/router";
import { Button } from "./Button";
import { Fill } from "./Fill";
import { TextLink } from "./TextLink";
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
  inline = false,
}: {
  pkg: { id: string; title: string; step_reference: string | null };
  selection: RiskSelection | null;
  preview: boolean;
  asOf: boolean;
  // Below 768 px, inside section 3; from 768 px, in the sticky header.
  inline?: boolean;
}) {
  const reasonId = useId();
  const describedId = useId();
  const feedforwardId = useId();
  // An implementing agency officer drafts the agency's own kind, in their own words (ticket 38).
  const officer = Boolean(useStore(officerAgency));
  if (!selection || selection.rows === 0) return null;
  const shown = inline ? "@md/page:hidden" : "hidden @md/page:flex";
  if (asOf) {
    return (
      <p className={cx("max-w-[320px] text-caption text-ink-muted", inline ? "@md/page:hidden" : "hidden @md/page:block")} data-ppsd-action="asof">
        {words.asof}
      </p>
    );
  }
  const held = preview || selection.saveFailed || selection.chosen === 0;
  const reason = preview ? (previewReason("start_draft") ?? words.heldPreview) : selection.saveFailed ? words.heldSaveFailed : inline ? words.heldNoneInline : (
    <Fill template={words.heldNone} slots={{ section: <TextLink href="#risks">{words.heldNoneLink}</TextLink> }} />
  );
  const start = () => {
    if (held) return;
    navigate(startPpsdRows({ ...pkg, selected: selection.chosen }, null, officer ? "ppsd_rows_agency" : "ppsd_rows"));
  };
  return (
    <div
      className={cx("flex-col items-start gap-2", shown, inline && "flex border-b border-line pb-4")}
      data-ppsd-action={held ? "held" : "live"}
      data-placement={inline ? "inline" : "header"}
    >
      <Button
        variant="primary"
        held={held}
        aria-describedby={held ? reasonId : [describedId, feedforwardId].join(" ")}
        onClick={start}
        className={inline ? "w-full min-[30rem]:w-auto" : undefined}
      >
        {held ? (officer ? words.agencyHeldLabel : words.heldLabel)
          : (officer ? words.agencyButton : words.button)(selection.chosen, formatNumber(selection.chosen, { compact: false }))}
      </Button>
      {held ? (
        <p id={reasonId} className="max-w-[320px] text-caption text-ink-muted" data-ppsd-held>
          {reason}
        </p>
      ) : (
        <>
          <p id={describedId} className="sr-only">
            {officer ? words.agencyDescription : words.description}
          </p>
          <p id={feedforwardId} className="max-w-[320px] text-caption text-ink-muted">
            {words.feedforward}
          </p>
        </>
      )}
    </div>
  );
}
