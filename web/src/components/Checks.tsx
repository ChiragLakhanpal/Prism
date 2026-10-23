// The three lines that say how far to trust an answer (DESIGN.md section 5).
//
// Check line: what the verifier checked and what it did not, in the neutral state and never
// success green, because a green banner reads as "safe".
// Coverage line: a sentence with its denominator, linked to Data readiness. The gap sentence
// ends the first sentence when some cases lacked what the count needs; a period ends it when
// none did.
// Removed box: the sentences the checks removed, with their reasons, open under "In short".
import type { ReactNode } from "react";
import { CircleDashed } from "lucide-react";
import { copy } from "../copy";
import { formatNumber } from "../lib/format";
import { Num, numText } from "./Num";
import { TextLink } from "./TextLink";

const n = (value: number) => formatNumber(value, { compact: false });

export type NotChecked = keyof typeof copy.checkLine.notCheckedClauses;

export function CheckLine({
  numbers,
  quotes,
  notChecked,
}: {
  numbers?: { matched: number; total: number };
  quotes?: { found: number; total: number };
  notChecked: NotChecked[];
}) {
  const words = copy.checkLine;
  const clauses = [
    numbers && numbers.total > 0 && words.numbers(n(numbers.matched), numbers.total, n(numbers.total)),
    quotes && quotes.total > 0 && words.quotes(n(quotes.found), quotes.total, n(quotes.total)),
  ].filter((clause): clause is string => Boolean(clause));
  const checked = (clauses.length ? clauses : [words.sourcesOnly]).join(words.clauseJoin);
  return (
    <p data-check-line data-numbers className="rounded-md bg-neutral-bg px-3 py-2 text-small text-neutral">
      <span className="font-semibold">{words.checked}</span> {checked}
      {words.end}{" "}
      {notChecked.length > 0 && (
        <>
          <span className="font-semibold">{words.notChecked}</span>{" "}
          {notChecked.map((clause) => words.notCheckedClauses[clause]).join(words.notCheckedJoin)}
          {words.end}
        </>
      )}
    </p>
  );
}

export function CoverageLine({
  part,
  whole,
  noun,
  gap,
  href,
}: {
  part: number;
  whole: number;
  // What the denominator counts, such as "matching packages", from the tool's copy.
  noun: string;
  // The sentence that says what the rest lacked, with its own numbers.
  gap?: ReactNode;
  // Data readiness, filtered to the sources behind the line.
  href: string;
}) {
  return (
    <p data-coverage-line className="text-small text-ink">
      {copy.coverage.basedOn} <Num part={part} whole={whole} show="count" /> {noun}
      {gap ? (
        <>
          {copy.coverage.join}
          {gap}
        </>
      ) : (
        copy.coverage.end
      )}{" "}
      <TextLink href={href}>{copy.coverage.link}</TextLink>
    </p>
  );
}

export type Removed = {
  // The sentence as the agent wrote it.
  sentence: string;
  // The reason as a list item ("No record supports this number.") and as a clause ("no record
  // supports that number"), from the copy file's verifier reasons.
  reason: string;
  reasonJoined: string;
};

// "It said bids were usually opened within 45 days": the sentence without its final period,
// with its first letter lowercased unless the first word is a name or a code (IDA, P130164)
// or appears capitalized elsewhere in the answer.
export function asReported(sentence: string, names: string[] = []): string {
  const text = sentence.replace(/[.\s]+$/, "");
  const first = text.split(/\s/)[0] ?? "";
  const keep = /\d|.[A-Z]/.test(first) || names.includes(first.replace(/\W+$/, ""));
  return keep ? text : text.charAt(0).toLowerCase() + text.slice(1);
}

export function RemovedBox({
  removed,
  all = false,
  names,
}: {
  removed: Removed[];
  // Every sentence the agent wrote failed a check.
  all?: boolean;
  // Words that stay capitalized when a sentence is reported, from the answer and its passages.
  names?: string[];
}) {
  const words = copy.removed;
  const count = removed.length;
  const lead =
    count === 0
      ? words.none
      : all
        ? count === 1
          ? words.allOne
          : words.all(numText({ count }))
        : count === 1
          ? words.one
          : words.several(numText({ count }));
  const [first, ...others] = removed;
  return (
    <div data-removed-box className="flex gap-3 rounded-r-md border-l-4 border-line-strong bg-neutral-bg px-4 py-3 text-small text-neutral">
      <CircleDashed aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-line-strong" />
      <div className="min-w-0">
        <p>
          <span className="font-semibold">{lead}</span>
          {first && !all && (
            <>
              {" "}
              {(count === 1 ? words.itSaid : words.firstSaid)(asReported(first.sentence, names), first.reasonJoined)}
            </>
          )}
        </p>
        {(all ? removed : others).length > 0 && (
          <>
            {!all && <p className="mt-2">{words.others}</p>}
            <ul className="mt-2 flex list-disc flex-col gap-1 pl-4">
              {(all ? removed : others).map((item, index) => (
                <li key={index}>{words.item(item.sentence, item.reason)}</li>
              ))}
            </ul>
          </>
        )}
      </div>
    </div>
  );
}
