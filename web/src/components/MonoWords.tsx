// A STEP reference in Roboto Mono that stays readable as one ID inside running text (DESIGN.md
// section 5, Reference words). Each part between spaces is its own inline box: it moves to the next
// line whole when it fits there, and breaks after a hyphen only when it is wider than the line, so
// the page never scrolls sideways. A reference with a county's name, such as KE-THARAKA NITHI
// COUNTY-428127-GO-RFQ, breaks at its spaces first. The space between two parts is Roboto Mono too, so
// it is one character wide, as in a reference set whole in mono, and the line can still break there.
// The text after it, such as a full stop, stays in the last part's box, so it never starts a line.
// The scope chip, the package workspace's not-found sentence, the past range's table and a dot's
// details on its chart all use it, so they wrap a reference the same way.
import { Fragment } from "react";
import { cx } from "../lib/cx";

export function MonoWords({
  text,
  after = "",
  medium = false,
  className,
}: {
  text: string;
  after?: string;
  // Roboto Mono 500, as an ID in a sentence; 400 otherwise.
  medium?: boolean;
  // Classes for each part's box, such as its alignment and colour.
  className?: string;
}) {
  const parts = text.split(" ");
  return parts.map((part, index) => (
    <Fragment key={index}>
      {index > 0 && <span className="font-mono"> </span>}
      <span className={cx("inline-block max-w-full wrap-anywhere", className)}>
        <span className={cx("font-mono", medium && "font-medium")}>{part}</span>
        {index === parts.length - 1 && after}
      </span>
    </Fragment>
  ));
}
