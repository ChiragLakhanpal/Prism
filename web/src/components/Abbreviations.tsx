// A source's own words with each GLOSSARY.md abbreviation in them, such as "MTR", opening its Term, so the words stay
// word for word and the window spells the abbreviation out (DESIGN.md section 7, rule 10; ticket 58). The
// abbreviations are the GLOSSARY.md terms that end with one in brackets, such as "Mid-term review (MTR)", so a new one
// is one GLOSSARY.md entry.
import { Fragment, type ReactNode } from "react";
import { terms } from "../glossary";
import { cx } from "../lib/cx";
import { DefinitionWindow, Term } from "./Term";

// An abbreviation a specialist reads every day, such as "PAD", "ISR", "ICR", "PPAR" or "PDO", written short on a chart
// label, in a legend or in a foot strip, with a Term's window that spells it out (ticket 126, the tuck-away inventory's
// pattern 4; DESIGN.md section 7, rules 10 and 22: the window counts as the spell-out there). The words come from the
// copy file, where the sentence that used to spell it out on screen lives.
export function Abbr({ short, spelled }: { short: string; spelled: ReactNode }) {
  return (
    // A short form such as "ISR" (19 px) or a rating code such as "S" (7 px) is under 24 px wide, so an ::after pads its
    // hit area to WCAG 2.5.8's 24 px without moving the words, as a measure's number does (MeasureNum).
    <DefinitionWindow
      label={short}
      title={short}
      inText
      triggerClassName={cx("relative after:absolute after:inset-y-0 after:content-['']", short.length < 2 ? "after:-inset-x-2.5" : "after:-inset-x-1.5")}
    >
      {spelled}
    </DefinitionWindow>
  );
}

const ABBREVIATIONS: Record<string, string> = Object.fromEntries(
  Object.keys(terms).flatMap((term) => {
    const found = / \(([A-Z]{2,})\)$/.exec(term);
    return found ? [[found[1], term]] : [];
  }),
);
const WORDS = Object.keys(ABBREVIATIONS);
const PATTERN = WORDS.length ? new RegExp(`\\b(${WORDS.join("|")})\\b`, "g") : null;

// Plain text stays plain strings, so a caller that rewrites strings, such as a notice's "[contact removed]", still
// can; from is where the text starts in its passage, so the keys stay unique across a passage's parts.
export function withAbbreviations(text: string, from = 0): ReactNode[] {
  if (!PATTERN) return [text];
  const parts: ReactNode[] = [];
  let at = 0;
  for (const match of text.matchAll(PATTERN)) {
    if (match.index > at) parts.push(text.slice(at, match.index));
    parts.push(
      <Fragment key={`abbr-${from + match.index}`}>
        <Term term={ABBREVIATIONS[match[1]]}>{match[1]}</Term>
      </Fragment>,
    );
    at = match.index + match[1].length;
  }
  if (at < text.length) parts.push(text.slice(at));
  return parts;
}
