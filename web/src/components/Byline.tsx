// Byline (ticket 111; DESIGN.md section 1, principle 6, and section 5): which words are Prism's own. Since ticket 126
// it shows no words: the question above an answer and the answer's first-person sentences already say whose words they
// are. What stays is the data attribute, and over an answer a screen-reader-only h3, so heading navigation still lands
// on the answer: "Prism, in short" over a ready, unsupported or refused answer, and "Prism held back" over one that
// abstains, the screen's sign that the verifier let an uncited sentence stand on a tool's abstention (checks 2 and 4).
// A finding that runs no model, such as the plan check's or section 1's, keeps only data-byline on its own block.
import { copy } from "../copy";
import { Fill } from "./Fill";

export type BylineKind = "inShort" | "found" | "heldBack";

// The answer's h3, which only a screen reader reads.
export function Byline({ kind }: { kind: Exclude<BylineKind, "found"> }) {
  return (
    <h3 data-byline={kind} className="sr-only">
      <Fill template={copy.byline[kind]} slots={{ strata: copy.byline.strata }} />
    </h3>
  );
}
