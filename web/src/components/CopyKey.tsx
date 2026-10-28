// The copy key (DESIGN.md section 5, Copy key; ticket 112, from fairshare's "Copy the query"): a 24 by 24 px ghost icon
// button with 4 px corners after an ID or a source, holding a 16 px lucide copy icon in ink-muted that hovers to
// tint-hover. Its name says what it copies ("Copy the STEP reference"), and the shared Tooltip says "Copy" on hover and
// focus. A press, Enter or Space writes the text to the clipboard, turns the icon into a check and the tooltip into
// "Copied" for 2 seconds, and says "Copied {what}." once in a polite status. If the write fails, the tooltip says to
// select the text instead. Focus stays on the key, and nothing on its line moves: the two icons are the same size,
// and the tooltip and the status lie outside the line. Pressed tens of times a day, so nothing animates.
//
// The key never starts a line apart from its ID: a word joiner (U+2060, as CitationMarker.tsx uses) ties it to the
// ID's last character, and the span around both keeps the browser from breaking between them. Where the ID already
// sits in a span that never wraps, as a project's header line keeps each " · item" together, joined is false, so the
// line's text stays as it was.
import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Check, Copy } from "lucide-react";
import { copy } from "../copy";
import { cx } from "../lib/cx";
import { WORD_JOINER } from "./CitationMarker";
import { Tooltip } from "./Popover";

// How long the check and "Copied" stay.
export const COPIED_MS = 2000;

type Shown = "copy" | "copied" | "failed";

export function CopyKey({
  text,
  what,
  joined = true,
  className,
}: {
  // The text the key copies, or a function that reads it when the key is pressed, as the drawer reads its source line.
  text: string | (() => string);
  // What it copies, in words that follow "Copy" and "Copied", such as copy.copyKey.reference.
  what: string;
  joined?: boolean;
  // Where it sits on its line: in the middle of a heading's line by default; a caller can give its own.
  className?: string;
}) {
  const [shown, setShown] = useState<Shown>("copy");
  const [said, setSaid] = useState("");
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  useEffect(() => () => clearTimeout(timer.current), []);

  const press = async () => {
    clearTimeout(timer.current);
    let copied = true;
    try {
      await navigator.clipboard.writeText(typeof text === "function" ? text() : text);
    } catch {
      copied = false;
    }
    setShown(copied ? "copied" : "failed");
    setSaid(copied ? copy.copyKey.said(what) : copy.copyKey.failed);
    timer.current = setTimeout(() => {
      setShown("copy");
      setSaid("");
    }, COPIED_MS);
  };

  const Icon = shown === "copied" ? Check : Copy;
  const key = (
    <button
      type="button"
      data-copy-key={shown}
      aria-label={copy.copyKey.name(what)}
      onClick={() => void press()}
      className={cx(
        // 4 px from the ID, so the focus ring (2 px at a 2 px offset) never covers its last character.
        "ml-1 inline-flex size-6 shrink-0 items-center justify-center rounded-sm text-ink-muted transition-paint hover:bg-tint-hover",
        className ?? "align-middle",
      )}
    >
      <Icon aria-hidden="true" className="size-4" />
    </button>
  );
  return (
    <span className="whitespace-nowrap">
      {joined && WORD_JOINER}
      {/* At 320 px the failure's sentence wraps inside the window's 16 px margins, so the page never scrolls sideways. */}
      <Tooltip trigger={key} pressKeepsOpen width="max-w-[min(var(--tooltip-width),calc(100vw-2rem))]">
        {shown === "copied" ? copy.copyKey.copied : shown === "failed" ? copy.copyKey.failed : copy.copyKey.tip}
      </Tooltip>
      {/* The status lies outside the line, so its words never join a heading's. */}
      {createPortal(
        <span role="status" className="sr-only" data-copy-status>
          {said}
        </span>,
        document.body,
      )}
    </span>
  );
}
