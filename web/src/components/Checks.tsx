// The three lines that say how far to trust an answer (DESIGN.md section 5).
//
// Check line: what the verifier checked and what it did not, in the neutral state and never
// success green, because a green banner reads as "safe". Its text starts on the removed box's text
// edge, 48 px in (the box's 4 px border, 16 px padding, 16 px icon and 12 px gap), so the two read
// as one column. Ticket 111 puts a 16 px tick in ink-muted in that indent beside "Checked", where the box has its
// icon, hidden from screen readers; the line stays neutral (ticket 02's round 7 review). Dates the verifier matched
// get their own clause, so "numbers" never counts a date (ticket 14). Three labeled parts, each on
// its own line, from the firmest kind of checking to none (the 24 brief, section 4.1): "Checked:"
// (exact matches, counted), "Judged by a model:" (check 4, only when a sentence on screen was
// judged) and "Not checked:" (a clause per tool that leaves a gap, or the fallback). It is still one
// paragraph, so a screen reader reads it straight through.
// Coverage line: a sentence with its denominator, linked to Data readiness. The gap sentence
// ends the first sentence when some cases lacked what the count needs; a period ends it when
// none did.
// Removed box: the sentences the checks removed, with their reasons, open under "In short". Every
// one is listed, the first in the lead and the others below, all visible, as plain text with no
// dotted numbers and no markers (the 24 brief, section 4.3).
import { useId, type ReactNode } from "react";
import { Check, CircleDashed } from "lucide-react";
import { copy } from "../copy";
import { cx } from "../lib/cx";
import { formatCount, formatNumber } from "../lib/format";
import { Button } from "./Button";
import { Num, numText, type NumCheck } from "./Num";
import { TextLink } from "./TextLink";

const n = (value: number) => formatNumber(value, { compact: false });

export type NotChecked = keyof typeof copy.checkLine.notCheckedClauses;

// "{part} of {whole} numbers match records", in the form for its whole.
function ratio(forms: { one: string; many: string }, part: number, whole: number): string {
  return (whole === 1 ? forms.one : forms.many).replace("{part}", n(part)).replace("{whole}", n(whole));
}

// What the line says was not checked, from the verifier's checks event: whether each sentence follows
// from its sources where the fourth check did not run (an answer saved before ticket 24), then a clause
// for each tool that ran and has one, then a draft kind's own clauses (config/drafts.toml). A tool the
// event lists under cited_only (config/tools.toml, not_checked_when = "cited") has its clause only once a
// sentence on screen cites it: a lesson cited is not a lesson that fits, which check 5 cannot tell (the
// 24 brief, section 5.2). src/strata/drafts/files.py writes the evidence pack's line by the same rule.
// With none, the line gives the fallback.
export function notCheckedFor(
  // computed: a draft no model wrote, such as planned dates (ticket 38), has no sentences to follow from sources.
  checks: { checks_run: number[]; tools: string[]; cited_tools?: string[]; cited_only?: string[]; computed?: boolean },
  own: string[] = [],
): NotChecked[] {
  const clauses = copy.checkLine.notCheckedClauses;
  const keys = Object.keys(clauses) as NotChecked[];
  const cited = checks.cited_tools ?? [];
  const citedOnly = checks.cited_only ?? [];
  return [
    ...(checks.checks_run.includes(4) || checks.computed ? [] : (["sentences"] as NotChecked[])),
    ...keys.filter((key) => (citedOnly.includes(key) ? cited.includes(key) : checks.tools.includes(key))),
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
  judged,
  notChecked,
  quoteWords,
  notCheckedText = [],
  reveal = false,
}: {
  numbers?: { matched: number; total: number };
  dates?: { matched: number; total: number };
  quotes?: { found: number; total: number };
  // Check 4 on the sentences on screen: how many a model judged, all of which follow, since a sentence
  // that does not is removed, and how many needed no model. No part when none was judged.
  judged?: { judged: number; proven: number; crossLanguage?: number };
  notChecked: NotChecked[];
  // The quotes' clause in other words, such as "quotes are in their sources" where some quotes come from a notice,
  // which has no pages (ticket 31; the 31 brief, section 6.4).
  quoteWords?: { one: string; many: string };
  // Clauses a part of a page adds to what was not checked, already in words, such as section 5's "whether I found
  // every item in your qualification criteria".
  notCheckedText?: string[];
  // The line arrives with an answer that just streamed: its tick draws left to right 120 ms after the answer lands
  // (ticket 111). Everywhere else the tick is drawn at once.
  reveal?: boolean;
}) {
  const words = copy.checkLine;
  const clauses = [
    numbers && numbers.total > 0 && ratio(words.numbers, numbers.matched, numbers.total),
    dates && dates.total > 0 && ratio(words.dates, dates.matched, dates.total),
    quotes && quotes.total > 0 && ratio(quoteWords ?? words.quotes, quotes.found, quotes.total),
  ].filter((clause): clause is string => Boolean(clause));
  // What was not checked: the clauses for the gaps, then a part of a page's own (ticket 31).
  const unchecked = [...notChecked.map((clause) => words.notCheckedClauses[clause]), ...notCheckedText];
  const checked = (clauses.length ? clauses : [words.sourcesOnly]).join(words.clauseJoin);
  return (
    <p data-check-line data-numbers className="rounded-md bg-neutral-bg py-2 pr-4 pl-12 text-small text-neutral">
      <span data-check-part="checked" className="relative block">
        {/* The tick (ticket 111): 16 px in ink-muted in the 48 px indent beside "Checked", where the removed box has
            its icon, 28 px before the text. The line's words say "Checked", so a screen reader skips it, and the
            line stays neutral, never green. */}
        <Check aria-hidden="true" data-check-tick className={cx("absolute top-0.5 -left-7 size-4 text-ink-muted", reveal && "animate-tick-in")} />
        <strong className="font-semibold">{words.checked}</strong> {checked}
        {words.end}
      </span>{" "}
      {judged && judged.judged > 0 && (
        <>
          <span data-check-part="judged" className="block">
            <strong className="font-semibold">{words.judged}</strong> {ratio(words.judgedSentences, judged.judged, judged.judged)}
            {words.end}
            {judged.proven > 0 && (
              <>
                {" "}
                {(judged.proven === 1 ? words.provenOthers.one : words.provenOthers.many).replace("{count}", formatCount(judged.proven))}
              </>
            )}
            {/* A model judged these across two languages, so the line says how many (the 42 brief, section 5.5). */}
            {(judged.crossLanguage ?? 0) > 0 && (
              <>
                {" "}
                {judged.judged === 1
                  ? words.crossLanguage.one
                  : judged.crossLanguage === judged.judged
                    ? words.crossLanguage.all
                    : words.crossLanguage.some(formatCount(judged.crossLanguage ?? 0))}
              </>
            )}
          </span>{" "}
        </>
      )}
      <span data-check-part="not-checked" className="block">
        <strong className="font-semibold">{words.notChecked}</strong> {unchecked.length ? joinClauses(unchecked) : words.notCheckedFallback}
        {words.end}
      </span>
    </p>
  );
}

export function CoverageLine({
  part,
  whole,
  noun,
  gap,
  href,
  check,
}: {
  part: number;
  whole: number;
  // What the denominator counts, such as "matching packages", from the tool's copy.
  noun: string;
  // The sentence that says what the rest lacked, with its own numbers.
  gap?: ReactNode;
  // Data readiness, filtered to the sources behind the line.
  href: string;
  // What the counts count, for a reader who checks them.
  check?: NumCheck;
}) {
  return (
    <p data-coverage-line className="text-small text-ink">
      {copy.coverage.basedOn} <Num part={part} whole={whole} show="count" check={check} /> {noun}
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
  // It gave advice: the lead quotes it whole, with the list item's reason, rather than report it, since
  // advice is often an order that does not read as reported speech.
  quoted?: boolean;
};

// Removed sentences as the verifier sent them, in the box's words: a kind's own words for a reason first (such as
// suggested PPSD rows' "It cited a source other than this risk's records."), then the shared ones.
export function removedFrom(
  items: { sentence: string; reason: string; reasons: { code: string }[] }[],
  kindReasons: Record<string, { item: string; joined: string }> = {},
): Removed[] {
  const reasons: Record<string, { item: string; joined: string }> = { ...copy.removed.reasons, ...kindReasons };
  return items.map((item) => {
    const code = [item.reason, ...item.reasons.map((reason) => reason.code)].find((one) => one in reasons);
    const reason = code ? reasons[code] : copy.removed.unknownReason;
    return { sentence: item.sentence, reason: reason.item, reasonJoined: reason.joined };
  });
}

// "It said bids were usually opened within 45 days": the sentence without its final period,
// with its first letter lowercased unless the first word is a name or a code (IDA, P130164), "I" (section
// 5's "I read this as ..."), or appears capitalized elsewhere in the answer.
export function asReported(sentence: string, names: string[] = []): string {
  const text = sentence.replace(/[.\s]+$/, "");
  const first = text.split(/\s/)[0] ?? "";
  const keep = /\d|.[A-Z]|^I($|['\u2019])/.test(first) || names.includes(first.replace(/\W+$/, ""));
  return keep ? text : text.charAt(0).toLowerCase() + text.slice(1);
}

// The removed box's lead in another unit than sentences, such as the risks section's rows (ticket 30): "I
// removed one risk."
// "all" takes the count and its text, since two is "both", never "all two" (ticket 24).
export type RemovedLead = {
  none: string;
  one: string;
  several: (count: string) => string;
  all: (count: number, countText: string) => string;
  allOne: string;
};

export function RemovedBox({
  removed,
  all = false,
  names,
  lead: leads = copy.removed,
  item,
  retry,
}: {
  removed: Removed[];
  // Every sentence the agent wrote failed a check.
  all?: boolean;
  // Words that stay capitalized when a sentence is reported, from the answer and its passages.
  names?: string[];
  lead?: RemovedLead;
  // One removed item after the first, from what it said and its reason, as plain text (the risks section,
  // ticket 30). Without it, each item quotes its sentence in its own quote element, then gives its reason.
  item?: (sentence: string, reason: string) => string;
  // A service a check needs did not answer (the judge, or get_disagreements), so "Try again" follows the
  // lead and asks the question again, after a note on how many it could not check when other sentences
  // were removed for other reasons (the 24 brief, section 5.4).
  retry?: { onRetry: () => void; note?: string };
}) {
  const words = copy.removed;
  const othersId = useId();
  const count = removed.length;
  const lead =
    count === 0
      ? leads.none
      : all
        ? count === 1
          ? leads.allOne
          : leads.all(count, numText({ count }))
        : count === 1
          ? leads.one
          : leads.several(numText({ count }));
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
              {first.quoted ? (
                <>
                  {count === 1 ? words.itSaidQuoted : words.firstSaidQuoted}{" "}
                  <q className="text-ink [quotes:none]">{words.quoted(first.sentence)}</q> {first.reason}
                </>
              ) : (
                (count === 1 ? words.itSaid : words.firstSaid)(asReported(first.sentence, names), first.reasonJoined)
              )}
            </>
          )}
        </p>
        {retry && (
          <>
            {retry.note && (
              <p data-unjudged className="mt-2">
                {retry.note}
              </p>
            )}
            <div className="mt-2">
              <Button variant="secondary" onClick={retry.onRetry}>
                {copy.answer.tryAgain}
              </Button>
            </div>
          </>
        )}
        {(all ? removed : others).length > 0 && (
          <>
            {!all && (
              <p id={othersId} className="mt-2">
                {others.length === 1 ? words.other : words.others}
              </p>
            )}
            <ul aria-labelledby={all ? undefined : othersId} className="mt-2 flex list-disc flex-col gap-1 pl-4">
              {(all ? removed : others).map((entry, index) =>
                item ? (
                  <li key={index}>{item(entry.sentence, entry.reason)}</li>
                ) : (
                  <li key={index}>
                    {/* The sentence in its own quote element, in ink, so a screen reader and the eye can tell
                        it from its reason. Its straight quote marks are the copy file's, so the browser adds none. */}
                    <q className="text-ink [quotes:none]">{words.quoted(entry.sentence)}</q> {entry.reason}
                  </li>
                ),
              )}
            </ul>
          </>
        )}
      </div>
    </div>
  );
}
