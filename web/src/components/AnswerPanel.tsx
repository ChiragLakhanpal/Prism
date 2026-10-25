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
import { formatCount, formatDate, formatNumber } from "../lib/format";
import { highlightsFor, lessonOf, passageFields, placeOf, recordKind, recordReference } from "../lib/sources";
import { Answer, type AnswerState } from "./Answer";
import { Button } from "./Button";
import { CitationMarker } from "./CitationMarker";
import { notCheckedFor, type Removed } from "./Checks";
import { DisagreementCard } from "./DisagreementCard";
import { EvidenceCard } from "./EvidenceCard";
import { Fill } from "./Fill";
import { Num } from "./Num";
import { RETURNING } from "./Popover";
import type { Step } from "./Steps";
import { IdText, linkProjectIds } from "./ProjectId";
import { TextLink } from "./TextLink";
import { WHAT_I_DONT_DO } from "../routes";

export const ANNOUNCE_GAP_MS = 500;
const STILL_WORKING_MS = 30_000;
export const DRAWER_ID = "evidence-drawer";

// An ID in a line Strata writes: a P-code links to its project page (ticket 21), anything else is in mono.
const mono = (text: string) => <IdText id={text} />;

// ── Steps ──────────────────────────────────────────────────────────────

function toolLines(step: StepEvent): { running: string; done: string } {
  const count = step.count ?? 0;
  const words = step.tool ? copy.steps.tools[step.tool as keyof typeof copy.steps.tools] : undefined;
  if (!words) {
    const name = (step.tool ?? "").replace(/_/g, " ");
    return { running: copy.steps.otherTool.running(name), done: copy.steps.otherTool.done(name) };
  }
  const scope = step.project_id ?? null;
  return { running: words.running(scope), done: words.done(count, formatCount(count), scope) };
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

// The six checks under the verifier's done line, each in the past tense, with its counts over every
// sentence the agent wrote (the 24 brief, section 5.1).
export function sixChecks(checks: ChecksEvent): string[] {
  const six = copy.steps.check.six;
  const judge = checks.judge;
  const fourth = !judge
    ? []
    : judge.called && judge.responded === false
      ? [six.judgeSilent(judge.unjudged, formatCount(judge.unjudged))]
      : judge.called
        ? [six.judged(judge.judged, formatCount(judge.judged), judge.followed), ...(judge.proven > 0 ? [six.proven(judge.proven, formatCount(judge.proven))] : [])]
        : [six.notJudged];
  const disputed = checks.disagreements?.disputed ?? 0;
  const sixth =
    disputed === 0
      ? six.disputedNone
      : (checks.disagreements?.attached ?? 0) > 0
        ? six.disputedAdded(disputed, formatCount(disputed, { capital: true }))
        : six.disputedBoth(disputed, formatCount(disputed, { capital: true }));
  return [
    six.numbers(checks.checked?.matched ?? 0, checks.checked?.total ?? 0),
    six.sources(checks.sources.returned, checks.sources.total),
    six.quotes(checks.quotes.found, checks.quotes.total),
    fourth.join(" "),
    six.advice(checks.advice?.cited ?? 0, checks.advice?.total ?? 0),
    sixth,
  ].filter(Boolean);
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
    const reference = <span className="font-mono">{recordReference(evidence)}</span>;
    return <Fill template={words.numTooltipRecord} slots={{ kind: recordKind(evidence), reference }} />;
  }
  const fields = passageFields(evidence);
  const kind = words.docKinds[evidence.short_name ?? ""] ?? fields.docType;
  const place = placeOf(fields);
  const pid = <span className="font-mono">{fields.pcode}</span>;
  if (date && !quoted(evidence, date.sentence, date.text)) return <Fill template={words.numTooltipReportDate} slots={{ kind, pid }} />;
  return place.kind === "paragraph" ? (
    <Fill template={words.numTooltip} slots={{ para: place.text, kind, pid }} />
  ) : (
    <Fill template={words.numTooltipSection} slots={{ section: place.text, kind, pid }} />
  );
}

// A sentence's text with each number and date the verifier matched drawn by Num: a dotted underline,
// a tooltip naming the source, and a click that opens it. Numbers are not tab stops; the markers carry
// the keyboard to the same sources.
export function sentenceText(sentence: SentenceEvent, evidence: Record<string, EvidenceEvent>, open: (id: string) => void): ReactNode[] {
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
    parts.push(sentence.text.slice(at, mention.start));
    const tooltip = numTooltip(evidence[mention.id], mention.date ? { sentence: sentence.index, text: mention.text } : null);
    const num = (
      <Num
        key={mention.start}
        written={mention.text}
        check={tooltip ? { tooltip, tabStop: false, onOpen: () => open(mention.id) } : undefined}
      />
    );
    // A number is a button, which a line may break after; the punctuation that follows it stays on its
    // line, so no line starts with a period or a comma (ticket 35's review notes showed it).
    const stop = /^[.,;:)\]]+/.exec(sentence.text.slice(mention.end))?.[0] ?? "";
    parts.push(
      stop ? (
        <span key={mention.start} className="whitespace-nowrap">
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
  parts.push(sentence.text.slice(at));
  return parts;
}

// A side of a disagreement, named in full ("Implementation Status and Results Report (ISR) 7") and short
// ("ISR 7"), from its document type and the short name its evidence event carries.
function sideNames(side: DisagreementEvent["sides"][number], evidence: EvidenceEvent | undefined) {
  const short = evidence?.short_name ?? null;
  const paragraph = side.paragraph_numbered ? side.paragraph : null;
  const words = copy.disagreement;
  const full = words.sourceFull(side.document_type ?? recordKind({ id: side.evidence_id } as EvidenceEvent), short, side.sequence, paragraph);
  return { full, short: short ? words.sourceShort(short, side.sequence, paragraph) : full };
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
  const close = (key: string) => {
    if (paragraph.length) blocks.push(<p key={key} className="max-w-prose">{paragraph}</p>);
    paragraph = [];
  };
  run.sentences.forEach((sentence) => {
    // Its source is open in the drawer, opened from this sentence of this answer.
    const active = opened.id !== null && opened.sentence === sentence.index && sentence.evidence_ids.includes(opened.id);
    paragraph.push(
      <Fragment key={sentence.index}>
        {paragraph.length > 0 && " "}
        <span data-sentence-text={sentence.index} className={active ? "bg-tint [box-decoration-break:clone]" : undefined}>
          {sentenceText(sentence, run.evidence, (id) => open(id, sentence.index, null))}
          {sentence.evidence_ids.map((id) => markerFor(id, sentence.index, active))}
        </span>
      </Fragment>,
    );
    const cards = run.disagreements.filter((found) => found.after === sentence.index);
    if (cards.length === 0) return;
    close(`sentence${sentence.index}`);
    for (const found of cards) blocks.push(<AnswerDisagreement key={found.id} found={found} run={run} markerFor={markerFor} />);
  });
  close("end");
  return <div className="flex flex-col gap-3">{blocks}</div>;
}

// A disagreement check 6 shows under its sentence: both sides, the rule and what changes if you keep
// the other, every word from the copy file and the stream's values.
function AnswerDisagreement({
  found,
  run,
  markerFor,
}: {
  found: DisagreementEvent;
  run: Run;
  markerFor: (id: string, sentence: number, active: boolean) => ReactNode;
}) {
  const words = copy.disagreement;
  const named = found.sides.map((side) => sideNames(side, run.evidence[side.evidence_id]));
  const leaned = found.sides.findIndex((side) => side.leaned);
  const other = leaned === 0 ? 1 : 0;
  const rules = words.rule as Record<string, string>;
  const rule = (rules[found.rule_id ?? ""] ?? "").replace("{lean}", named[leaned]?.short ?? "").replace("{other}", named[other]?.short ?? "");
  const keep = found.if_you_keep;
  const written = words.written as Record<string, string>;
  const sides = found.sides.map((side, index) => ({
    meta: words.meta
      .replace("{source}", named[index].full)
      .replace("{date}", side.made_at ? formatDate(side.made_at) : "")
      .replace("{written}", written[side.evidence_tier ?? "record"] ?? written.record),
    leaned: side.leaned,
    said: (
      <>
        {side.quote ? copy.removed.quoted(side.quote) : words.rated(side.field_name ?? "", side.value ?? "")}
        {markerFor(side.evidence_id, found.after, false)}
      </>
    ),
  })) as [{ meta: string; leaned: boolean; said: ReactNode }, { meta: string; leaned: boolean; said: ReactNode }];
  const badge = found.changes_answer ? copy.badge.twoReportsDisagree : copy.badge.sourcesDiffer;
  return (
    <DisagreementCard
      warning={found.changes_answer}
      name={words.groupName(badge, named[0].short, named[1].short)}
      leanTag={words.lean}
      sides={sides}
      rule={rule}
      whatChanges={keep && keep.field_name && keep.value && leaned >= 0 ? words.whatChanges(named[other].short, keep.field_name, keep.value) : undefined}
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

// The removed sentences a service did not let me check, by its reason code: the model that judges
// sentences did not respond (judge), or I couldn't ask which reports disagree (unasked); and the rest.
export const OUTAGE_REASONS = { judge: "judge_unavailable", unasked: "disagreements_unavailable" } as const;
function outages(run: Run): { judge: number; unasked: number; other: number } {
  const judge = run.removed.filter((item) => item.reason === OUTAGE_REASONS.judge).length;
  const unasked = run.removed.filter((item) => item.reason === OUTAGE_REASONS.unasked).length;
  return { judge, unasked, other: run.removed.length - judge - unasked };
}

// Words that stay capitalized when a removed sentence is reported: those written with a capital in the
// middle of a sentence in this answer or its passages, such as Rajasthan or Kenya.
function names(run: Run): string[] {
  const texts = [...run.sentences.map((sentence) => sentence.text), ...Object.values(run.evidence).map((evidence) => String(evidence.row.text ?? ""))];
  const found = new Set<string>();
  for (const text of texts) for (const match of text.matchAll(/[a-z,;:]\s+([A-Z][a-z]+)/g)) found.add(match[1]);
  return [...found];
}

// "How Strata works lists what I don't do, and why.", under every refusal.
const refusalNote = () => (
  <Fill template={copy.answer.refusalNote} slots={{ link: <TextLink href={WHAT_I_DONT_DO.href}>{copy.answer.refusalLink}</TextLink> }} />
);

function stateOf(run: Run, opened: Opened, visited: ReadonlySet<string>, stillWorking: boolean): AnswerState {
  const steps = stepsOf(run);
  const runId = run.runId ?? "";
  if (run.phase === "streaming") return { status: "streaming", steps, stillWorking, announce: false };
  const done = steps.filter((step) => step.state === "done");
  if (run.phase === "failed" && run.error === "content_filter") {
    return { status: "refused", steps: done, runId, message: copy.answer.errors.content_filter, note: refusalNote() };
  }
  const refusal = run.refusal ? (copy.refusals as Record<string, { lead: string; instead: string }>)[run.refusal.key] : undefined;
  if (run.phase === "done" && refusal && run.refusal && !run.refusal.partial) {
    return { status: "refused", steps: done, runId, message: <>{refusal.lead} {refusal.instead}</>, note: refusalNote() };
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
          {refusal.lead} {copy.answer.refusalPartial}
        </p>
        <p className="mt-2 text-caption text-ink-muted">{refusalNote()}</p>
      </>
    ) : undefined;
  if (checks.sentences.kept === 0 && outage.judge + outage.unasked > 0) {
    // Nothing survived because a service a check needs did not answer: an error, not an empty answer, with
    // every sentence I wrote listed under it (the 24 brief, section 5.5). Above the alert sits only the
    // verifier's done line; its six checks stay in the disclosure of an answer that has one.
    const words = copy.answer;
    const cause = outage.judge && outage.unasked ? words.bothFailed : outage.judge ? words.judgeFailed : words.disagreementsFailed;
    return {
      status: "error",
      steps: done.map((step) => ({ ...step, items: undefined })),
      runId: run.runId ?? undefined,
      message: (
        <>
          {cause} {words.stillInBox}
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
  // sentences were removed for other reasons, since then the lead does not say why.
  const notes = [
    outage.judge > 0 && copy.removed.unjudged(outage.judge, formatCount(outage.judge)),
    outage.unasked > 0 && copy.removed.unasked(outage.unasked, formatCount(outage.unasked)),
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
      judged: checks.shown ? { judged: checks.shown.judged, proven: checks.shown.proven } : undefined,
      notChecked: notCheckedFor(checks),
      removed: removedItems(run),
      names: names(run),
      retry: notes.length ? { onRetry: askAgain, note: mixed ? notes.join(" ") : undefined } : undefined,
    },
  };
}

// "Asked within P130164, as of October 1, 2026." It names no view: until ticket 40 the server
// applies no view's rules, so a preview would be a claim about something that did not happen.
function AskedLine({ run }: { run: Run }) {
  const { scope, asOf } = run.asked;
  const words = copy.answer;
  return (
    <p data-asked className="mt-1 text-caption text-ink-muted">
      {scope ? <Fill template={words.askedWithin} slots={{ id: mono(scope) }} /> : words.askedAcross}
      {asOf && words.askedAsOf(formatDate(asOf))}
      {words.askedEnd}
    </p>
  );
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
    const box = document.querySelector<HTMLInputElement>("[data-box-band] [role=combobox]");
    box?.setAttribute(RETURNING, "");
    box?.focus();
  };

  return (
    <section aria-label={copy.answer.panel} aria-busy={run.phase === "streaming"} data-answer-panel className="mb-8">
      <div className="rounded-md border border-line bg-surface p-4 @md/page:p-6 @lg/page:p-8">
        {/* The Asked line sits a fixed 4 px under the question, whatever its length; the close
            button beside them sets no gap. */}
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <h2 className="text-title wrap-break-word text-ink-heading">{linkProjectIds(run.asked.question)}</h2>
            <AskedLine run={run} />
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
          <Answer state={stateOf(run, opened, visited, stillWorking)} />
        </div>
        <Announcer key={run.serial} messages={announcements(run)} />
      </div>
    </section>
  );
}
