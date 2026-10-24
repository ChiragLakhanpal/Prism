// The three lines that say how far to trust an answer (DESIGN.md section 5).
//
// Check line: what the verifier checked and what it did not, in the neutral state and never
// success green, because a green banner reads as "safe". Its text starts on the removed box's text
// edge, 48 px in (the box's 4 px border, 16 px padding, 16 px icon and 12 px gap), so the two read
// as one column, with no check-mark icon (ticket 02's round 7 review). Dates the verifier matched
// get their own clause, so "numbers" never counts a date (ticket 14).
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

// "{part} of {whole} numbers match records", in the form for its whole.
function ratio(forms: { one: string; many: string }, part: number, whole: number): string {
  return (whole === 1 ? forms.one : forms.many).replace("{part}", n(part)).replace("{whole}", n(whole));
}

// What the line says was not checked, from the verifier's checks event: whether each sentence follows
// from its sources until ticket 24 runs the fourth check, then a clause for each tool that ran and
// has one, then a draft kind's own clauses (config/drafts.toml). src/strata/drafts/runtime.py writes
// the evidence pack's line by the same rule.
export function notCheckedFor(checks: { checks_run: number[]; tools: string[] }, own: string[] = []): NotChecked[] {
  const clauses = copy.checkLine.notCheckedClauses;
  const keys = Object.keys(clauses) as NotChecked[];
  return [
    ...(checks.checks_run.includes(4) ? [] : (["sentences"] as NotChecked[])),
    ...keys.filter((key) => checks.tools.includes(key)),
    ...own.filter((key): key is NotChecked => key in clauses),
  ];
}

// "A, or B", or "A, B, or C".
function joinClauses(clauses: string[]): string {
  const words = copy.checkLine;
  if (clauses.length <= 2) return clauses.join(words.notCheckedJoin);
  return clauses.slice(0, -1).join(words.notCheckedComma) + words.notCheckedJoin + clauses[clauses.length - 1];
}

export function CheckLine({
  numbers,
  dates,
  quotes,
  notChecked,
}: {
  numbers?: { matched: number; total: number };
  dates?: { matched: number; total: number };
  quotes?: { found: number; total: number };
  notChecked: NotChecked[];
}) {
  const words = copy.checkLine;
  const clauses = [
    numbers && numbers.total > 0 && ratio(words.numbers, numbers.matched, numbers.total),
    dates && dates.total > 0 && ratio(words.dates, dates.matched, dates.total),
    quotes && quotes.total > 0 && ratio(words.quotes, quotes.found, quotes.total),
  ].filter((clause): clause is string => Boolean(clause));
  const checked = (clauses.length ? clauses : [words.sourcesOnly]).join(words.clauseJoin);
  return (
    <p data-check-line data-numbers className="rounded-md bg-neutral-bg py-2 pr-4 pl-12 text-small text-neutral">
      <span className="font-semibold">{words.checked}</span> {checked}
      {words.end}{" "}
      {notChecked.length > 0 && (
        <>
          <span className="font-semibold">{words.notChecked}</span>{" "}
          {joinClauses(notChecked.map((clause) => words.notCheckedClauses[clause]))}
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
          <span data-removed-lead className="font-semibold">{lead}</span>
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
