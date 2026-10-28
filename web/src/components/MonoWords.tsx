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
import { Fill, Joined } from "./Fill";

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

// One sentence that ends with a list of STEP references, each set by MonoWords with the full stop kept in the last
// one's box, so it never starts a line: "The activities I counted: KE-NWWDA-229129-CW-RFB and KE-NWWDA-541062-CW-RFQ."
// A count word's tooltip says what it counts this way (DESIGN.md section 5, Number tooltip; ticket 96).
export function ListedRefs({ template, refs, end }: { template: string; refs: string[]; end: string }) {
  const items = refs.map((ref, index) => <MonoWords key={ref} text={ref} after={index === refs.length - 1 ? end : ""} />);
  return <Fill template={template} slots={{ refs: <Joined items={items} /> }} />;
}
