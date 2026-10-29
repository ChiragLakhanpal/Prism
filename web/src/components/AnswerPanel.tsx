// The answer panel (the 14 brief, section 4.7): the answer to the question asked from the one box,
// in the page under the band, on columns 1 to 8 from 1024 px. It draws the stream's run
// (web/src/lib/answer.ts) as ticket 02's Answer: steps while it works, then "In short" with citation
// markers, the check line with the stream's counts, and the removed box, open. Ticket 24 adds the six
// checks under the verifier's step, the disagreement check 6 shows under its sentence, the reasons of
// checks 4 to 6, and the refusals, whose words come from the copy file by the stream's key.
//
// Screen readers hear each step once, when it starts, and then "The answer is ready.", through one
// status line that is on the page before any of it changes. Events can arrive faster than anyone can
// listen, so the line moves on at most every ANNOUNCE_GAP_MS.
import { Fragment, useEffect, useMemo, useState, type ReactNode } from "react";
import { X } from "lucide-react";
import { copy } from "../copy";
import {
  askAgain,
  citationNumbers,
  closeAnswer,
  removeScope,
  ask,
  type ChecksEvent,
  type DisagreementEvent,
  type EvidenceEvent,
  type Run,
  type SentenceEvent,
  type StepEvent,
} from "../lib/answer";
import { evidenceHref, loadVisited, openEvidence } from "../lib/evidence";
import { ENGLISH, langOf, languageName, workingLanguage } from "../lib/lang";
import { useRevealAfterWait } from "../lib/reveal";
import { useStore } from "../lib/store";
import { formatCount, formatDate, formatNumber } from "../lib/format";
import { highlightsFor, lessonOf, namedSection, passageFields, placeOf, recordKind, recordReference } from "../lib/sources";
import { Answer, type AnswerState } from "./Answer";
import { Button } from "./Button";
import { CitationMarker } from "./CitationMarker";
import { Lang } from "./Lang";
import { HowChecked, notCheckedFor, sixChecks, type Removed } from "./Checks";
import { DisagreementCard, SideSaid, type CardSide } from "./DisagreementCard";
import { changesLine, ruleSentence, sideFull, sideInSentence, sideMeta, sideOpen, sideShort, subjectOf, whatChanges, type SideData } from "../lib/disagreement";
import { EvidenceCard } from "./EvidenceCard";
import { Fill } from "./Fill";
import { inSentence, MonoWords } from "./MonoWords";
import { Num, type NumCheck } from "./Num";
import { evidenceFrom, FromLine } from "./NumFrom";
import { RETURNING } from "./Popover";
import type { Step } from "./Steps";
import { IdText, linkProjectIds } from "./ProjectId";
import { TextLink } from "./TextLink";
import { RefusalWindow } from "./WhatIDontDo";

export const ANNOUNCE_GAP_MS = 500;
const STILL_WORKING_MS = 30_000;
export const DRAWER_ID = "evidence-drawer";

// An ID in a line Strata writes: a P-code links to its project page (ticket 21), anything else is in mono.
// A P-code as the page header sets it; a STEP reference as the box sets it, by MonoWords, so "Asked within
// KE-NWWDA-541055-CW-RFB." never breaks inside the reference while it fits a line (ticket 59).
const mono = (text: string) => (/^P\d{6}$/.test(text) ? <IdText id={text} /> : <MonoWords text={text} />);

// ── Steps ──────────────────────────────────────────────────────────────

function toolLines(step: StepEvent): { running: string; done: string } {
  const count = step.count ?? 0;
  const words = step.tool ? copy.steps.tools[step.tool as keyof typeof copy.steps.tools] : undefined;
  if (!words) {
    const name = (step.tool ?? "").replace(/_/g, " ");
    return { running: copy.steps.otherTool.running(name), done: copy.steps.otherTool.done(name) };
  }
  const scope = step.project_id ?? null;
  // A call that abstained says why, when its tool has a sentence for the code (ticket 58).
  const abstained = step.abstention ? (words as { abstained?: Record<string, string> }).abstained?.[step.abstention] : undefined;
  return { running: words.running(scope), done: abstained ?? words.done(count, formatCount(count), scope) };
}

function stepLines(step: StepEvent, checks: ChecksEvent | null, refused = false): { running: string; done: string } {
  if (step.kind === "tool") return toolLines(step);
  if (step.kind === "write") {
    const count = step.count ?? 0;
    // A full refusal wrote no sentence because it turned the request down, and its step says so.
    return { running: copy.steps.write.running, done: refused ? copy.steps.write.refused : copy.steps.write.done(count, formatCount(count)) };
  }
  const words = copy.steps.check;
  // The verifier's own steps are said while they run and fold into its done line.
  if (step.kind === "judge") {
    const count = step.count ?? 0;
    return { running: words.judge(count, formatCount(count)), done: "" };
  }
  if (step.kind === "disagreement") return { running: words.disagreement, done: "" };
  if (!checks) return { running: words.running, done: words.done };
  const { written, removed } = checks.sentences;
  return { running: words.running, done: words.doneSix(written, formatCount(written), removed, formatCount(removed)) };
}

// A step's line with its project ID in mono, as every ID Strata writes (DESIGN.md section 3).
function withMonoId(text: string, id: string | null | undefined): ReactNode {
  if (!id || !text.includes(id)) return text;
  return text.split(id).flatMap((part, index) => (index === 0 ? [part] : [<Fragment key={index}>{mono(id)}</Fragment>, part]));
}

export function stepsOf(run: Run): Step[] {
  const started = run.steps.length > 0 || run.phase !== "streaming";
  const refused = Boolean(run.refusal && !run.refusal.partial);
  const steps: Step[] = [{ key: "read", ...copy.steps.read, state: started ? "done" : "running" }];
  for (const step of run.steps) {
    const lines = stepLines(step, run.checks, refused);
    // The verifier's own steps, asking the judge and getting the other side of a disagreement, sit inside its
    // step while they run, with no spinner of their own, and fold into its done line (the 24 brief, 4.2).
    if (step.kind === "judge" || step.kind === "disagreement") {
      const verifier = steps.find((one) => one.key === "check");
      if (step.status === "running" && verifier?.state === "running") verifier.items = [...(verifier.items ?? []), lines.running];
      continue;
    }
    const items = step.kind === "check" && step.status === "done" && run.checks?.judge ? sixChecks(run.checks) : undefined;
    steps.push({ key: step.id, running: withMonoId(lines.running, step.project_id), done: withMonoId(lines.done, step.project_id), state: step.status, items });
  }
  if (run.phase === "streaming") {
    if (!run.steps.some((step) => step.kind === "write")) steps.push({ key: "todo-write", running: "", done: copy.steps.write.todo, state: "todo" });
    if (!run.steps.some((step) => step.kind === "check")) steps.push({ key: "todo-check", running: "", done: copy.steps.check.todo, state: "todo" });
  }
  return steps;
}

// What the status line says, in order: each step as it starts, then the answer.
function announcements(run: Run): string[] {
  const said = [copy.steps.read.running, ...run.steps.map((step) => stepLines(step, run.checks).running)];
  const answered = run.phase === "done" || (run.phase === "failed" && run.error === "content_filter");
  if (answered) {
    const removed = run.checks?.sentences.removed ?? 0;
    const kept = run.checks?.sentences.kept ?? 0;
    const { judge: unjudged, unasked } = outages(run);
    // Only a warning is announced: an info note changes nothing in the answer (the 24 brief, section 5.8).
    // The verifier counts the sentences a warning follows.
    const warned = run.checks?.disagreements?.warned ?? 0;
    // When nothing survived because a service did not answer, the error alert speaks (role="alert"), so the
    // status line says nothing more: "The answer is ready." after it would say the opposite.
    if (!run.refusal && kept === 0 && unjudged + unasked > 0) return said;
    said.push(
      run.refusal && !run.refusal.partial
        ? copy.answer.ready
        : unjudged > 0 && kept > 0
          ? copy.answer.readyUnjudged(unjudged, formatCount(unjudged))
          : unasked > 0 && kept > 0
            ? copy.answer.readyUnasked(unasked, formatCount(unasked))
            : warned > 0
            ? copy.answer.readyDisagree(warned, formatCount(warned))
            : removed > 0 && kept > 0
              ? copy.answer.readyRemoved(removed, formatCount(removed))
              : copy.answer.ready,
    );
  }
  return said;
}

function Announcer({ messages }: { messages: string[] }) {
  const [shown, setShown] = useState(-1);
  useEffect(() => {
    if (shown >= messages.length - 1) return;
    const timer = setTimeout(() => setShown((index) => index + 1), shown < 0 ? 100 : ANNOUNCE_GAP_MS);
    return () => clearTimeout(timer);
  }, [shown, messages.length]);
  return (
    <p role="status" data-answer-status className="sr-only">
      {shown >= 0 ? messages[shown] : ""}
    </p>
  );
}

// ── Sentences ──────────────────────────────────────────────────────────

export type Opened = { id: string | null; sentence: number | null };

export function markerSource(evidence: EvidenceEvent | undefined, id: string): string {
  if (!evidence) return id;
  const lesson = lessonOf(evidence);
  if (lesson) return copy.evidence.markerLesson(formatNumber(lesson.version, { compact: false }), lesson.statement);
  if (evidence.kind === "record") return copy.evidence.markerRecord(recordKind(evidence), recordReference(evidence));
  const fields = passageFields(evidence);
  const place = placeOf(fields);
  return place.kind === "paragraph"
    ? copy.evidence.markerSource(fields.docType, fields.date, place.text)
    : copy.evidence.markerSourceSection(fields.docType, fields.date, place.text);
}

// Whether the words a sentence quotes from a passage hold this value, ignoring runs of whitespace.
function quoted(evidence: EvidenceEvent, sentence: number, value: string): boolean {
  const squeeze = (text: string) => text.replace(/\s+/g, " ");
  const text = passageFields(evidence).text;
  return highlightsFor(evidence, sentence).some(([start, end]) => squeeze(text.slice(start, end)).includes(squeeze(value)));
}

// "Matches paragraph 54 of the completion report for P130164.", with the ID in Roboto Mono. A passage
// backs a number only inside the words a sentence quotes, but it also backs its report's date, which
// the paragraph may not hold: then the tooltip names the report's date.
function numTooltip(evidence: EvidenceEvent | undefined, date: { sentence: number; text: string } | null): ReactNode {
  if (!evidence) return null;
  const words = copy.evidence;
  if (evidence.kind === "record") {
    // A reference moves to the next line whole when it fits there, and its full stop never starts a line.
    const reference = <MonoWords text={recordReference(evidence)} after={words.numTooltipRecordEnd} />;
    const kind = words.numTooltipKinds[evidence.id.split(":")[0]] ?? recordKind(evidence);
    return <Fill template={words.numTooltipRecord} slots={{ kind, reference }} />;
  }
  const fields = passageFields(evidence);
  const kind = words.docKinds[evidence.short_name ?? ""] ?? fields.docType;
  const place = placeOf(fields);
  const pid = <span className="font-mono">{fields.pcode}</span>;
  if (date && !quoted(evidence, date.sentence, date.text)) return <Fill template={words.numTooltipReportDate} slots={{ kind, pid }} />;
  return place.kind === "paragraph" ? (
    <Fill template={words.numTooltip} slots={{ para: place.text, kind, pid }} />
  ) : (
    <Fill template={namedSection(place) ? words.numTooltipSection : words.numTooltipSectionNumbered} slots={{ section: place.text, kind, pid }} />
  );
}

// The STEP references of the records a sentence cites, longest first, so a reference that holds a shorter one is
// found whole. The sentence sets each one in Roboto Mono, as an ID in a sentence (ticket 58).
function stepReferences(sentence: SentenceEvent, evidence: Record<string, EvidenceEvent>): string[] {
  const ids = [...sentence.evidence_ids, ...sentence.numbers.map((m) => m.evidence_id), ...sentence.dates.map((m) => m.evidence_id)];
  const found = new Set<string>();
  for (const id of ids) {
    const reference = id ? evidence[id]?.row?.step_reference : undefined;
    if (evidence[id ?? ""]?.kind === "record" && typeof reference === "string" && reference) found.add(reference);
  }
  return [...found].sort((a, b) => b.length - a.length);
}

// A pattern that finds those references whole in a sentence, with the punctuation right after one, which stays in its
// last part's box so it never starts a line.
function referencePattern(references: string[]): RegExp | null {
  if (references.length === 0) return null;
  const alternatives = references.map((reference) => reference.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|");
  return new RegExp(`(?<![\\w-])(${alternatives})(?![\\w-])([.,;:)\\]]*)`, "g");
}

// A sentence's text with each number and date the verifier matched drawn by Num: a dotted underline and a
// tooltip naming the source and where it came from (DESIGN.md, Number tooltip). In an answer that is all (the
// Plain variant): the marker beside the sentence opens the source. In a draft's note, open is given and a click
// opens the number's record in the drawer (the Record variant), as its action line says. Numbers are not tab
// stops; the markers carry the keyboard to the same sources.
export function sentenceText(
  sentence: SentenceEvent,
  evidence: Record<string, EvidenceEvent>,
  open: ((id: string) => void) | undefined,
  // The language the sentence is written in: the words it quotes from a source in another language keep that source's
  // lang (ticket 42; the 42 brief, section 6.5).
  around: string = ENGLISH,
): ReactNode[] {
  const quoteLang = sentence.quote ? (evidence[sentence.quote.evidence_id]?.row?.language as string | undefined) : undefined;
  const quoteStart = sentence.quote && quoteLang && quoteLang !== around ? sentence.text.indexOf(sentence.quote.text) : -1;
  const quoteEnd = quoteStart < 0 ? -1 : quoteStart + sentence.quote!.text.length;
  // A cited record's STEP reference is a name, not a quote: it is set by MonoWords, so it moves to the next line whole
  // and never breaks after "KE-" (ticket 58). Any other STEP reference in the text between stays whole too, in the
  // sentence's own type (inSentence; ticket 59's verifier saw "KE-ICTA-571738-" end a line).
  const references = referencePattern(stepReferences(sentence, evidence));
  const named = (start: number, end: number): ReactNode[] => {
    const text = sentence.text.slice(start, end);
    if (!references) return inSentence(text, start);
    const pieces: ReactNode[] = [];
    let at = 0;
    for (const match of text.matchAll(references)) {
      pieces.push(...inSentence(text.slice(at, match.index), start + at));
      pieces.push(
        <span key={`reference-${start + match.index}`} data-step-reference>
          <MonoWords text={match[1]} after={match[2]} medium />
        </span>,
      );
      at = match.index + match[0].length;
    }
    pieces.push(...inSentence(text.slice(at), start + at));
    return pieces.filter((piece) => piece !== "");
  };
  // Plain text from start to end of the sentence, with the part inside the quote marked as the source's language.
  const plain = (start: number, end: number): ReactNode[] => {
    if (quoteStart < 0 || end <= quoteStart || start >= quoteEnd) return named(start, end);
    const from = Math.max(start, quoteStart);
    const to = Math.min(end, quoteEnd);
    return [
      ...named(start, from),
      <Lang key={`quote-${from}`} code={quoteLang}>
        {inSentence(sentence.text.slice(from, to), from)}
      </Lang>,
      ...named(to, end),
    ];
  };
  const found: { start: number; end: number; text: string; id: string; date: boolean }[] = [];
  // Numbers and dates each come in the order the sentence writes them, but a date may come before
  // the numbers, so each list keeps its own place in the text.
  for (const [mentions, date] of [
    [sentence.numbers, false],
    [sentence.dates, true],
  ] as const) {
    let cursor = 0;
    for (const mention of mentions) {
      const id = mention.evidence_id ?? sentence.evidence_ids[0];
      const start = sentence.text.indexOf(mention.text, cursor);
      if (!id || start < 0) continue;
      found.push({ start, end: start + mention.text.length, text: mention.text, id, date });
      cursor = start + mention.text.length;
    }
  }
  found.sort((a, b) => a.start - b.start);
  const parts: ReactNode[] = [];
  let at = 0;
  for (const mention of found) {
    if (mention.start < at) continue;
    // A currency sign right before the number stays on its line ("US$" never ends a line apart from its amount), and
    // so does an opening quote mark or bracket before it (a line never ends 'because "' with "108 of 328" on the next;
    // ticket 94's review, routed to ticket 105).
    const before = sentence.text.slice(at, mention.start);
    const sign = /[("“‘[]?(?:US\$|\$|€|£)?$/.exec(before)?.[0] ?? "";
    parts.push(...plain(at, mention.start - sign.length));
    const tooltip = numTooltip(evidence[mention.id], mention.date ? { sentence: sentence.index, text: mention.text } : null);
    const from = evidenceFrom(evidence[mention.id]);
    const base = { tooltip, from: from ? <FromLine words={from} /> : undefined, tabStop: false };
    const check: NumCheck | undefined = !tooltip
      ? undefined
      : open
        ? { ...base, act: copy.num.act.record, opens: "record", onOpen: () => open(mention.id) }
        : base;
    const num = <Num key={mention.start} written={mention.text} check={check} />;
    // A number is a button, which a line may break after; the punctuation that follows it stays on its
    // line, so no line starts with a period or a comma (ticket 35's review notes showed it), and so does a
    // currency sign before it (ticket 37's mission brief showed "US$" ending a line).
    const stop = /^[.,;:)\]]+/.exec(sentence.text.slice(mention.end))?.[0] ?? "";
    parts.push(
      stop || sign ? (
        <span key={mention.start} className="whitespace-nowrap">
          {sign}
          {num}
          {stop}
        </span>
      ) : (
        num
      ),
    );
    at = mention.end + stop.length;
  }
  // The sentence's last characters stay with its marker (CitationMarker's word joiner).
  parts.push(...plain(at, sentence.text.length));
  return parts;
}


export function AnswerSentences({
  run,
  opened,
  visited,
}: {
  run: Run;
  // The source the evidence drawer shows, and the sentence whose marker opened it.
  opened: Opened;
  visited: ReadonlySet<string>;
}) {
  const numbers = useMemo(() => citationNumbers(run), [run.sentences, run.disagreements]);
  const open = (id: string, sentence: number, marker: HTMLElement | null) =>
    openEvidence(id, { serial: run.serial, sentence, marker, runId: run.runId });
  const markerFor = (id: string, sentence: number, active: boolean) => {
    const n = numbers.get(id)!;
    const evidence = run.evidence[id];
    return (
      <CitationMarker
        key={id}
        n={n}
        evidenceId={id}
        sentence={sentence}
        source={markerSource(evidence, id)}
        href={evidenceHref(id)}
        drawerId={DRAWER_ID}
        active={opened.id === id && active}
        opened={visited.has(id)}
        preview={evidence ? <EvidenceCard evidence={evidence} n={n} sentence={sentence} visited={visited.has(id)} /> : undefined}
        onOpen={(marker) => open(id, sentence, marker)}
      />
    );
  };
  // "In short" breaks into a new paragraph after each sentence a disagreement concerns, with the card
  // between them (the 24 brief, section 4.4).
  const blocks: ReactNode[] = [];
  let paragraph: ReactNode[] = [];
  // "In short" is in the language the writer wrote it in (ticket 42); a quote keeps its source's.
  const close = (key: string) => {
    if (paragraph.length) blocks.push(<Lang key={key} code={run.lang} as="p" className="max-w-prose">{paragraph}</Lang>);
    paragraph = [];
  };
  run.sentences.forEach((sentence) => {
    // Its source is open in the drawer, opened from this sentence of this answer.
    const active = opened.id !== null && opened.sentence === sentence.index && sentence.evidence_ids.includes(opened.id);
    paragraph.push(
      <Fragment key={sentence.index}>
        {paragraph.length > 0 && " "}
        <span data-sentence-text={sentence.index} className={active ? "bg-tint [box-decoration-break:clone]" : undefined}>
          {sentenceText(sentence, run.evidence, undefined, run.lang)}
          {/* A marker is the copy file's words, read in English inside an answer in another language. */}
          <Lang code={ENGLISH}>{sentence.evidence_ids.map((id) => markerFor(id, sentence.index, active))}</Lang>
        </span>
      </Fragment>,
    );
    const cards = run.disagreements.filter((found) => found.after === sentence.index);
    if (cards.length === 0) return;
    close(`sentence${sentence.index}`);
    for (const found of cards) blocks.push(<AnswerDisagreement key={found.id} found={found} run={run} markerFor={markerFor} onOpen={open} />);
  });
  close("end");
  return <div className="flex flex-col gap-3">{blocks}</div>;
}

// A disagreement check 6 shows under its sentence: both sides, the rule and what changes if you keep
// the other, every word from the copy file and the stream's values. Once the answer is done, the card offers to
// keep the other report for this answer's run (ticket 23).
function AnswerDisagreement({
  found,
  run,
  markerFor,
  onOpen,
}: {
  found: DisagreementEvent;
  run: Run;
  markerFor: (id: string, sentence: number, active: boolean) => ReactNode;
  // Opens a side's source in the drawer, as its marker does, from the side's "Open ISR 7" link.
  onOpen: (id: string, sentence: number, element: HTMLElement) => void;
}) {
  const words = copy.disagreement;
  const sides = found.sides as SideData[];
  const lean = sides.find((side) => side.leaned);
  const other = sides.find((side) => !side.leaned);
  const cardSides = sides.map((side) => ({
    title: sideFull(side),
    titleText: sideFull(side),
    meta: sideMeta(side),
    leaned: side.leaned,
    assertionId: side.assertion_id ?? undefined,
    said: <SideSaid side={side} />,
    marker: markerFor(side.evidence_id, found.after, false),
    open: { label: sideOpen(side), href: evidenceHref(side.evidence_id), onOpen: (element: HTMLElement) => onOpen(side.evidence_id, found.after, element) },
  })) as [CardSide, CardSide];
  const badge = found.changes_answer ? copy.badge.twoReportsDisagree : copy.badge.sourcesDiffer;
  const id = found.disagreement_id ?? found.id.split(":").pop() ?? found.id;
  const view = run.asked.view;
  return (
    <DisagreementCard
      warning={found.changes_answer}
      name={words.groupName(badge, sideShort(sides[0]), sideShort(sides[1]))}
      subject={subjectOf(found.attribute, found.period_event ?? null)}
      level={4}
      sides={cardSides}
      rule={ruleSentence(found.rule_id, sides)}
      whatChanges={whatChanges(sides, found.if_you_keep)}
      changes={found.changes_count != null ? changesLine(found.changes_count, "answer") : undefined}
      keep={
        lean && other && lean.assertion_id && other.assertion_id && run.runId
          ? {
              other: sideInSentence(other),
              otherAssertionId: other.assertion_id,
              leanAssertionId: lean.assertion_id,
              target: { disagreementId: id, runId: run.runId, draftId: null, preview: view === "piu" || view === "public" },
            }
          : undefined
      }
    />
  );
}


// ── The panel ──────────────────────────────────────────────────────────

// A removed sentence's reason: its first reason code that has a sentence in the copy file, or else a
// line that makes no claim about why. Under an error alert that already names the cause, a reason with
// a short form uses it ("I couldn't check it."). Advice is quoted in the lead.
function removedItems(run: Run, underAlert = false): Removed[] {
  const reasons = copy.removed.reasons as Record<string, { item: string; joined: string; underAlert?: string }>;
  return run.removed.map((item) => {
    const code = [item.reason, ...item.reasons.map((reason) => reason.code)].find((one) => one in reasons);
    const reason = code ? reasons[code] : copy.removed.unknownReason;
    const said = underAlert && "underAlert" in reason && reason.underAlert ? reason.underAlert : reason.item;
    return { sentence: item.sentence, reason: said, reasonJoined: reason.joined, quoted: item.kind === "advice" };
  });
}

// The removed sentences a service did not let me check, as the verifier counted them (CLAUDE.md rule 1): the
// model that judges sentences did not respond (judge), or I couldn't ask which reports disagree (unasked); and
// the rest.
function outages(run: Run): { judge: number; unasked: number; other: number } {
  const judge = run.checks?.judge?.unjudged ?? 0;
  const unasked = run.checks?.disagreements?.unasked ?? 0;
  return { judge, unasked, other: (run.checks?.sentences.removed ?? 0) - judge - unasked };
}

// Words that stay capitalized when a removed sentence is reported: those written with a capital in the
// middle of a sentence in this answer or its passages, such as Rajasthan or Kenya.
function names(run: Run): string[] {
  const texts = [...run.sentences.map((sentence) => sentence.text), ...Object.values(run.evidence).map((evidence) => String(evidence.row.text ?? ""))];
  const found = new Set<string>();
  for (const text of texts) for (const match of text.matchAll(/[a-z,;:]\s+([A-Z][a-z]+)/g)) found.add(match[1]);
  return [...found];
}

// The refusal keys' words: what I don't do, what I can do instead, and why (ticket 97).
type RefusalWords = { lead: string; instead: string; why: string };

function stateOf(run: Run, opened: Opened, visited: ReadonlySet<string>, stillWorking: boolean): AnswerState {
  const steps = stepsOf(run);
  const runId = run.runId ?? "";
  if (run.phase === "streaming") return { status: "streaming", steps, stillWorking, announce: false };
  const done = steps.filter((step) => step.state === "done");
  if (run.phase === "failed" && run.error === "content_filter") {
    return { status: "refused", steps: done, runId, message: copy.answer.errors.content_filter, note: <RefusalWindow /> };
  }
  const refusal = run.refusal ? (copy.refusals as Record<string, RefusalWords>)[run.refusal.key] : undefined;
  if (run.phase === "done" && refusal && run.refusal && !run.refusal.partial) {
    return {
      status: "refused",
      steps: done,
      runId,
      message: (
        <>
          {refusal.lead} {refusal.instead} {refusal.why}
        </>
      ),
      note: <RefusalWindow />,
    };
  }
  if (run.phase !== "done" || !run.checks) {
    const errors = copy.answer.errors as Record<string, string>;
    const code = run.error && run.error in errors ? run.error : "internal";
    const said = run.phase === "dropped" ? copy.answer.dropped : code === "internal" && !run.runId ? copy.answer.internalNoId : errors[code];
    return {
      status: "error",
      steps: done,
      runId: run.runId ?? undefined,
      message: (
        <>
          {said} {copy.answer.stillInBox}
        </>
      ),
      // Trying again cannot connect a model that isn't connected.
      onRetry: run.phase !== "dropped" && code === "no_agent" ? undefined : askAgain,
    };
  }
  const { checks } = run;
  if (checks.sentences.written === 0) {
    const scope = run.asked.scope;
    return {
      status: "empty",
      steps: done,
      runId,
      message: scope ? (
        <Fill template={copy.answer.emptyScoped} slots={{ id: mono(scope) }} />
      ) : (
        <Fill template={copy.answer.emptyUnscoped} slots={{ link: <TextLink href="/data">{copy.answer.emptyLink}</TextLink> }} />
      ),
      action: scope ? (
        <Button
          variant="secondary"
          onClick={() => {
            removeScope(scope);
            ask({ ...run.asked, scope: null });
          }}
        >
          {copy.answer.askAcross}
        </Button>
      ) : undefined,
    };
  }
  const outage = outages(run);
  const partial =
    refusal && run.refusal?.partial ? (
      <>
        <p>
          {refusal.lead} {refusal.why} {copy.answer.refusalPartial}
        </p>
        <div className="mt-2">
          <RefusalWindow />
        </div>
      </>
    ) : undefined;
  if (checks.sentences.kept === 0 && outage.judge + outage.unasked > 0) {
    // Nothing survived because a service a check needs did not answer: an error, not an empty answer, with
    // every sentence I wrote listed under it (the 24 brief, section 5.5). Above the alert sits only the
    // verifier's done line; its six checks stay in the disclosure of an answer that has one.
    // When another sentence failed a check of its own, I checked some of the answer, so the alert says "all of".
    const words = outage.other > 0 ? copy.answer.failedSome : copy.answer.failed;
    const cause = outage.judge && outage.unasked ? words.both : outage.judge ? words.judge : words.disagreements;
    return {
      status: "error",
      steps: done.map((step) => ({ ...step, items: undefined })),
      runId: run.runId ?? undefined,
      message: (
        <>
          {cause} {copy.answer.stillInBox}
        </>
      ),
      onRetry: askAgain,
      removed: removedItems(run, true),
    };
  }
  if (checks.sentences.kept === 0) {
    const written = checks.sentences.written;
    return {
      status: "unsupported",
      steps: done,
      runId,
      message: copy.answer.nothingSurvived(written, formatCount(written)),
      removed: removedItems(run),
      refusal: partial,
    };
  }
  // "Try again" when a service did not let me check some sentences, with a note on how many when other
  // sentences were removed for other reasons, since then the lead does not say why. When the lead's sentence is that
  // service's only one, the lead already says it, so its note is left out and "Try again" follows the lead (ticket 58).
  const lead = run.removed[0]?.reason;
  const notes = [
    outage.judge > 0 &&
      !(outage.judge === 1 && lead === "judge_unavailable") &&
      copy.removed.unjudged(outage.judge, formatCount(outage.judge)),
    outage.unasked > 0 &&
      !(outage.unasked === 1 && lead === "disagreements_unavailable") &&
      copy.removed.unasked(outage.unasked, formatCount(outage.unasked)),
  ].filter((note): note is string => Boolean(note));
  const mixed = new Set(run.removed.map((item) => item.reason)).size > 1;
  // The check line counts the sentences on screen; an answer from before ticket 24 has only the counts
  // over everything written.
  const shown = checks.shown ?? checks;
  return {
    status: "ready",
    steps: done,
    runId,
    refusal: partial,
    wide: run.disagreements.length > 0,
    sentences: <AnswerSentences run={run} opened={opened} visited={visited} />,
    checks: {
      numbers: shown.numbers,
      dates: shown.dates,
      quotes: shown.quotes,
      judged: checks.shown
        ? { judged: checks.shown.judged, proven: checks.shown.proven, crossLanguage: checks.shown.cross_language }
        : undefined,
      sources: checks.shown?.sources,
      notChecked: notCheckedFor(checks),
      removed: removedItems(run),
      names: names(run),
      retry:
        outage.judge + outage.unasked > 0
          ? { onRetry: askAgain, note: mixed && notes.length ? notes.join(" ") : undefined }
          : undefined,
      // The window counts every sentence written, by the run that wrote this answer (ticket 105).
      how: runId && checks.judge ? <HowChecked checks={checks} id={{ answer: runId }} /> : undefined,
    },
  };
}

// "Asked within P130164, as of October 1, 2026." It names the preview the answer ran in, since the
// server applied that view's rules to every tool call (ticket 40).
function AskedLine({ run, current }: { run: Run; current: string }) {
  const { scope, asOf, view } = run.asked;
  const words = copy.answer;
  // The answer's language, when it is not English or not your choice now (the 42 brief, section 5.4).
  const named = run.lang !== ENGLISH || run.lang !== current;
  return (
    <p data-asked className="mt-1 text-caption text-ink-muted">
      {scope ? <Fill template={words.askedWithin} slots={{ id: mono(scope) }} /> : words.askedAcross}
      {asOf && words.askedAsOf(formatDate(asOf))}
      {(view === "piu" || view === "public") && words.askedPreview(copy.view.name[view])}
      {named && words.askedLanguage(languageName(run.lang))}
      {words.askedEnd}
    </p>
  );
}

// A new question scrolls the page at once so its heading sits under the bar (ticket 113): the box floats at the window's
// foot, and the answer opens at the top of the page column. The page goes to its top when the heading shows there, under
// the bar and any page alerts, and otherwise the panel's top goes to the bar's foot. Focus stays in the box.
export function scrollToAnswer() {
  const section = document.querySelector<HTMLElement>("[data-answer-panel]");
  const heading = section?.querySelector<HTMLElement>("h2");
  if (!section || !heading) return;
  const end = heading.getBoundingClientRect().bottom + window.scrollY;
  // The box's top: the page shows nothing under the box at the window's foot.
  const limit = document.querySelector("[data-box-slot] form")?.getBoundingClientRect().top ?? window.innerHeight;
  if (end <= limit) window.scrollTo({ top: 0, behavior: "instant" });
  else section.scrollIntoView({ block: "start", behavior: "instant" });
}

export function AnswerPanel({
  run,
  opened,
  visited,
  remember = true,
}: {
  run: Run;
  opened: Opened;
  visited: ReadonlySet<string>;
  // Ask the server which sources this viewer opened before. The design gallery has no server.
  remember?: boolean;
}) {
  const [stillWorking, setStillWorking] = useState(false);
  const current = useStore(workingLanguage)?.code ?? ENGLISH;
  // The answer replaces the stream's skeleton in this panel, so it enters (ticket 111); one shown again is drawn at once.
  const reveal = useRevealAfterWait(run.phase === "streaming", run.serial);
  useEffect(() => {
    if (run.phase !== "streaming") {
      setStillWorking(false);
      return;
    }
    const timer = setInterval(() => setStillWorking(Date.now() - run.lastEventAt > STILL_WORKING_MS), 1000);
    return () => clearInterval(timer);
  }, [run.phase, run.lastEventAt]);

  // When the answer lands, its markers learn which sources this viewer opened before.
  useEffect(() => {
    if (remember && run.phase === "done") void loadVisited(Object.keys(run.evidence));
  }, [run.phase, run.serial]);

  // Focus goes back to the box, where the question still is, but its list stays shut over the page
  // you return to until you press Down, type or click in it (the 14 brief, section 6.4).
  const close = () => {
    closeAnswer(run);
    const box = document.querySelector<HTMLInputElement>("[data-box-slot] [role=combobox]");
    box?.setAttribute(RETURNING, "");
    // The box always shows, at the window's foot (ticket 113), so giving it focus scrolls nothing.
    box?.focus({ preventScroll: true });
  };

  return (
    <section aria-label={copy.answer.panel} aria-busy={run.phase === "streaming"} data-answer-panel className="mb-8">
      {/* 24 px of padding from a page area of 768 px, as DESIGN.md section 4 and the prototype give it, and 16 below it
          (ticket 94's review, routed to ticket 105). */}
      <div className="rounded-md border border-line bg-surface p-4 @md/page:p-6">
        {/* The Asked line sits a fixed 4 px under the question, whatever its length; the close
            button beside them sets no gap. */}
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <h2 lang={langOf(run.questionLang)} className="text-h2 wrap-break-word text-ink-heading">
              {linkProjectIds(run.asked.question)}
            </h2>
            <AskedLine run={run} current={current} />
            {/* Ask the same question in your choice now, when the answer was written in another (the 42 brief, 5.4).
                Hidden for a refusal, an empty answer and an error, which come back in the copy file's English. */}
            {run.phase === "done" && run.sentences.length > 0 && run.lang !== current && (
              <div className="mt-2">
                <Button variant="ghost" onClick={() => ask({ ...run.asked, lang: current })}>
                  {copy.answer.askAgain(languageName(current))}
                </Button>
              </div>
            )}
          </div>
          {/* "Close the answer" in words from a page area of 768 px; below it, a 44 px icon with the same name. */}
          <div className="-mt-2 -mr-2 hidden shrink-0 @md/page:block">
            <Button variant="ghost" icon={X} onClick={close}>
              {copy.answer.close}
            </Button>
          </div>
          <div className="-mt-2 -mr-2 shrink-0 @md/page:hidden">
            <Button variant="ghost" icon={X} iconOnly onClick={close}>
              {copy.answer.close}
            </Button>
          </div>
        </div>
        <div className="mt-6">
          <Answer state={stateOf(run, opened, visited, stillWorking)} reveal={reveal} />
        </div>
        <Announcer key={run.serial} messages={announcements(run)} />
      </div>
    </section>
  );
}
