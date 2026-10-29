// A STEP reference in Roboto Mono that stays readable as one ID inside running text (DESIGN.md
// section 5, Reference words). Each part between spaces is its own inline box: it moves to the next
// line whole when it fits there, and breaks after a hyphen only when it is wider than the line, so
// the page never scrolls sideways. A reference with a county's name, such as KE-THARAKA NITHI
// COUNTY-428127-GO-RFQ, breaks at its spaces first. The space between two parts is Roboto Mono too, so
// it is one character wide, as in a reference set whole in mono, and the line can still break there.
// The text after it, such as a full stop, stays in the last part's box, so it never starts a line.
// The scope chip, the package workspace's not-found sentence, the past range's table and a dot's
// details on its chart all use it, so they wrap a reference the same way. An answer's sentences and a
// draft's notes keep their own type and wrap each reference they name by the same rule (inSentence).
import { Fragment, type ReactNode } from "react";
import { cx } from "../lib/cx";
import { Fill, Joined } from "./Fill";

export function MonoWords({
  text,
  before = "",
  after = "",
  medium = false,
  mono = true,
  className,
}: {
  text: string;
  // An opening quote mark or bracket, or a label such as "award notice" with a no-break space after it, kept in the first
  // part's box so it never ends a line apart from the reference.
  before?: ReactNode;
  after?: string;
  // Roboto Mono 500, as an ID in a sentence; 400 otherwise.
  medium?: boolean;
  // false keeps the type of the text around it, as a sentence the agent wrote does.
  mono?: boolean;
  // Classes for each part's box, such as its alignment and colour.
  className?: string;
}) {
  const parts = text.split(" ");
  return parts.map((part, index) => (
    <Fragment key={index}>
      {index > 0 && (mono ? <span className="font-mono"> </span> : " ")}
      <span className={cx("inline-block max-w-full wrap-anywhere", className)}>
        {index === 0 && before}
        <span className={cx(mono && "font-mono", medium && "font-medium")}>{part}</span>
        {index === parts.length - 1 && after}
      </span>
    </Fragment>
  ));
}

// A STEP reference as a sentence writes it, a county's name and its space included (KE-MIGORI COUNTY-532367-CW-RFB),
// with an opening quote mark or bracket right before it and the closing marks and stops right after it.
const REFERENCE_IN_TEXT =
  /([("\u201c\u2018[]?)(?<![A-Za-z0-9-])([A-Z]{2}-[A-Z0-9][A-Z0-9&.()]*(?: [A-Z][A-Z0-9&.()]*)*-\d+-(?:CW|GO|CS|NC)-[A-Z]+(?:-[A-Z0-9]+)*)(?![A-Za-z0-9])([.,;:)\]"\u201d\u2019]*)/g;

// A sentence's text with each STEP reference it names set by MonoWords in the sentence's own type, so "KE-ICTA-571738-CW-RFB"
// moves to the next line whole, and "KE-MIGORI COUNTY-532367-CW-RFB" breaks at its space and nowhere else (ticket 59).
// `from` is where the text starts in its sentence, which keys each reference.
export function inSentence(text: string, from = 0): ReactNode[] {
  const pieces: ReactNode[] = [];
  let at = 0;
  for (const match of text.matchAll(REFERENCE_IN_TEXT)) {
    const [whole, before, reference, after] = match;
    if (match.index! > at) pieces.push(text.slice(at, match.index));
    pieces.push(
      <Fragment key={`reference-${from + match.index!}`}>
        <MonoWords text={reference} before={before} after={after} mono={false} />
      </Fragment>,
    );
    at = match.index! + whole.length;
  }
  if (at < text.length) pieces.push(text.slice(at));
  return pieces;
}

// One sentence that ends with a list of STEP references, each set by MonoWords with the full stop kept in the last
// one's box, so it never starts a line: "The activities I counted: KE-NWWDA-229129-CW-RFB and KE-NWWDA-541062-CW-RFQ."
// A count word's tooltip says what it counts this way (DESIGN.md section 5, Number tooltip; ticket 96).
export function ListedRefs({ template, refs, end }: { template: string; refs: string[]; end: string }) {
  const items = refs.map((ref, index) => <MonoWords key={ref} text={ref} after={index === refs.length - 1 ? end : ""} />);
  return <Fill template={template} slots={{ refs: <Joined items={items} /> }} />;
}
