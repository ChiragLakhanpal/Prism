// The review page for one item of the lesson review queue (ticket 29; the 29 design brief, sections 2.5 and
// 5.5 to 5.16), at /lessons/review/:itemId. One reading column: the evidence first, then the tags, the
// writer's summary, likely repeats and the history, and the decision form last, with no sticky action panel,
// so nobody reaches "Add to the library" before reading the quote.
//
// The verbatim quote is the one bold thing on the page: in its evidence card, in the highlight fill, under the
// statement it supports. Each card's marker opens the evidence drawer with no hover preview, since the card is
// the preview. The writer's summary comes from a stored note, so the page makes no model call while you wait;
// a summary that finishes while the page is open waits behind "Show my summary", so the form never moves.
//
// After a save the outcome panel takes the form's place and focus moves to it. A decided item shows the same
// page, read-only, with the outcome panel where the form was.
import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { Alert } from "../components/Alert";
import { Breadcrumb } from "../components/Breadcrumb";
import { Button } from "../components/Button";
import { EmptyState } from "../components/Card";
import { CheckLine, notCheckedFor, RemovedBox } from "../components/Checks";
import { CitationMarker } from "../components/CitationMarker";
import { DecisionForm, ReasonField, type Done, type GaveWay } from "../components/DecisionForm";
import { NoteSentences } from "../components/DraftNotes";
import { highlighted } from "../components/Document";
import { Fill } from "../components/Fill";
import { LessonCard, LessonSources } from "../components/LessonCard";
import { EvidenceBadge, fillText, Tag } from "../components/LessonParts";
import { ProjectId } from "../components/ProjectId";
import { ClockLine, HistoryList, OutcomePanel, statusOf } from "../components/LessonReview";
import { LoadError } from "../components/LoadError";
import { Num } from "../components/Num";
import { PageAlert } from "../components/PageAlert";
import { SidePanel } from "../components/SidePanel";
import { Skeleton, SkeletonLine, SkeletonText } from "../components/Skeleton";
import { StatusBadge } from "../components/StatusBadge";
import { Workspace } from "../components/Workspace";
import { DRAWER_ID } from "../components/AnswerPanel";
import type { State } from "../components/state";
import { copy } from "../copy";
import { getJson, postJson } from "../lib/api";
import { formatDate } from "../lib/format";
import { evidenceHref, evidenceIn, openEvidence, remember, visited as visitedStore } from "../lib/evidence";
import { useLoad } from "../lib/load";
import { address } from "../lib/router";
import { useStore } from "../lib/store";
import { setPageTitle } from "../lib/title";
import { itemHref, LESSONS_HREF, lessonHref, QUEUE_HREF, removedOf, type LessonEvidence, type ReviewItem, type Saved } from "../lib/lessons";
import { refreshLessonsMe } from "./LessonsPages";
import { DocumentColumn } from "./DraftPage";

const words = copy.lessons;
const r = words.review;

// ── The evidence ─────────────────────────────────────────────────────────

function cardTitle(evidence: LessonEvidence): string {
  const slots = { para: evidence.locator.text, section: evidence.locator.text };
  if (evidence.doc_short === "ICR Review") return fillText(r.titleIcrReview, slots);
  if (evidence.doc_short === "PPAR") return fillText(r.titlePpar, slots);
  return fillText(r.titleIcr, slots);
}

// The marker's name in brief 14's shape, the same as the summary's markers to the same source: "Source 1:
// Implementation Completion and Results Report, October 10, 2019, paragraph 54".
function markerName(evidence: LessonEvidence): string {
  const date = evidence.date ? formatDate(evidence.date) : "";
  return evidence.locator.kind === "section"
    ? copy.evidence.markerSourceSection(evidence.doc_type, date, evidence.locator.text)
    : copy.evidence.markerSource(evidence.doc_type, date, evidence.locator.text);
}

export function EvidenceCardFull({ evidence, n, open, visited }: { evidence: LessonEvidence; n: number; open: boolean; visited: boolean }) {
  const titleId = useId();
  const excerpt = evidence.excerpt;
  return (
    <article aria-labelledby={titleId} data-lesson-evidence={evidence.evidence_id} className="flex flex-col gap-3 rounded-md border border-line bg-surface p-4 @md/page:p-6">
      <div className="flex items-start justify-between gap-3">
        <p className="text-label text-ink-muted">{r.eyebrow}</p>
        <CitationMarker
          n={n}
          evidenceId={evidence.evidence_id}
          source={markerName(evidence)}
          href={evidenceHref(evidence.evidence_id)}
          drawerId={DRAWER_ID}
          active={open}
          opened={visited}
          onOpen={(marker) => openEvidence(evidence.evidence_id, { serial: null, sentence: null, marker, runId: null, highlight: evidence.highlight ?? null })}
        />
      </div>
      <h3 id={titleId} className="-mt-1 text-h2 text-ink-heading wrap-anywhere">
        {cardTitle(evidence)}
      </h3>
      {evidence.role === "restatement" && <p className="text-caption text-ink-muted">{r.restatedCaption}</p>}
      <p className="max-w-prose text-body text-ink" lang={evidence.language && evidence.language !== "en" ? evidence.language : undefined} data-excerpt>
        {copy.evidence.quoteOpen}
        {excerpt?.starts_inside && copy.evidence.cut}
        {excerpt ? highlighted(excerpt.text, [excerpt.highlight]) : evidence.quote}
        {excerpt?.ends_inside && copy.evidence.cut}
        {copy.evidence.quoteClose}
      </p>
      <LessonSources evidence={[evidence]} />
      <p className="rounded-sm bg-neutral-bg px-3 py-2 text-small text-neutral" data-check-line>
        <span className="font-semibold">{copy.checkLine.checked}</span> {fillText(r.checkedOnPage, { page: evidence.page })}{" "}
        <span className="font-semibold">{copy.checkLine.notChecked}</span> {r.notCheckedLesson}
      </p>
    </article>
  );
}

// ── The tags ─────────────────────────────────────────────────────────────

function Tags({ item }: { item: ReviewItem }) {
  const id = useId();
  const t = r.terms;
  const rows: [string, ReactNode][] = [
    [t.risk_factors, <span key="f" className="flex flex-wrap gap-2">{(item.tags.risk_factors ?? []).map((factor) => <Tag key={factor.key}>{factor.label}</Tag>)}</span>],
    [t.stage, item.tags.stage?.label ?? ""],
    [t.kind, item.tags.kind?.label ?? ""],
    // Ticket 39: procurement categories and selection methods; none means every one.
    [t.categories, (item.tags.categories ?? []).map((tag) => tag.label).join(copy.list.comma) || t.none],
    [t.methods, (item.tags.methods ?? []).map((tag) => tag.label).join(copy.list.comma) || t.none],
    [t.rules, item.tags.edition ? item.tags.edition.short : words.card.rulesUnknown],
    [t.project, <Fill key="p" template={words.queue.project} slots={{ name: item.project.name ?? "", pid: <ProjectId pid={item.project.pid} /> }} />],
    [t.sector, item.tags.sector ?? ""],
  ];
  return (
    <section aria-labelledby={id}>
      <h2 id={id} className="text-h2 text-ink-heading">
        {r.tagsTitle}
      </h2>
      <p className="mt-1 text-caption text-ink-muted">
        {item.kind === "new" ? r.tagsCaption : <Fill template={r.tagsCaptionVersion} slots={{ version: <Num value={item.lesson.version ?? 1} /> }} />}
      </p>
      <dl className="mt-4 grid gap-x-4 gap-y-3 text-small @md/page:grid-cols-[30%_1fr]">
        {rows.map(([term, value]) => (
          <div key={term} className="contents">
            <dt className="font-semibold text-ink-heading">{term}</dt>
            <dd className="-mt-2 text-ink @md/page:mt-0">{value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

// ── The writer's summary ─────────────────────────────────────────────────

function Summary({ item, numbers, onRetried }: { item: ReviewItem; numbers: Map<string, number>; onRetried: (item: ReviewItem) => void }) {
  const id = useId();
  const here = useStore(address);
  const seen = useStore(visitedStore);
  const summary = item.summary;
  const [shown, setShown] = useState(summary);
  const [ready, setReady] = useState<ReviewItem | null>(null);
  const [rewriting, setRewriting] = useState(false);
  const first = useRef<HTMLParagraphElement>(null);
  const focusFirst = useRef(false);

  useEffect(() => setShown(item.summary), [item.summary]);
  useEffect(() => {
    for (const evidence of Object.values(shown.evidence ?? {})) remember(evidence);
  }, [shown]);
  useEffect(() => {
    if (focusFirst.current) first.current?.focus();
    focusFirst.current = false;
  }, [shown]);

  // While the writer is still writing, ask every 15 seconds while the tab is visible, for at most 10 minutes.
  useEffect(() => {
    if (shown.status !== "writing") return;
    const started = Date.now();
    const timer = window.setInterval(async () => {
      if (Date.now() - started > item.limits.summary_poll_minutes * 60_000) return window.clearInterval(timer);
      if (document.visibilityState !== "visible") return;
      try {
        const fresh = await getJson<ReviewItem>(`/api/lessons/review/${encodeURIComponent(item.item_id)}`);
        if (fresh.summary.status !== "writing") {
          setReady(fresh);
          window.clearInterval(timer);
        }
      } catch {
        // The next try may work; the summary is not needed to decide.
      }
    }, item.limits.summary_poll_seconds * 1000);
    return () => window.clearInterval(timer);
  }, [shown.status, item.item_id, item.limits]);

  const open = { id: evidenceIn(here.search), sentence: null };
  let body: ReactNode;
  if (rewriting) body = <p className="text-body text-ink-muted">{r.summaryRewriting}</p>;
  else if (shown.status === "writing" && ready)
    body = (
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2" data-summary-ready>
        <p className="text-body text-ink">{r.summaryReady}</p>
        <Button
          variant="ghost"
          onClick={() => {
            focusFirst.current = true;
            setShown(ready.summary);
            onRetried(ready);
          }}
        >
          {r.summaryShow}
        </Button>
      </div>
    );
  else if (shown.status === "writing") body = <p className="text-body text-ink-muted">{r.summaryWriting}</p>;
  else if (shown.status === "nothing_to_add") body = <p className="text-body text-ink">{r.summaryNothing}</p>;
  else if (shown.status === "failed")
    body = (
      <div className="flex flex-col items-start gap-4">
        <p className="text-body text-ink">{r.summaryFailed}</p>
        <Button
          variant="secondary"
          onClick={async () => {
            setRewriting(true);
            try {
              const saved = await postJson<{ item: ReviewItem }>(`/api/lessons/review/${encodeURIComponent(item.item_id)}/summary`, {});
              focusFirst.current = true;
              setShown(saved.item.summary);
              onRetried(saved.item);
            } catch {
              // It stays failed, and the button stays for another try.
            } finally {
              setRewriting(false);
            }
          }}
        >
          {r.summaryTryAgain}
        </Button>
      </div>
    );
  else {
    const checks = shown.checks;
    const sentences = shown.sentences ?? [];
    body = (
      <div className="flex flex-col gap-4">
        {sentences.length > 0 && (
          <div ref={first} tabIndex={-1} className="outline-none">
            <NoteSentences sentences={sentences} evidence={shown.evidence ?? {}} numbers={numbers} opened={seen} open={open} textSize="body" />
          </div>
        )}
        {shown.status === "nothing_survived" && <p className="text-body text-ink">{r.summaryNoneSurvived}</p>}
        {checks && (
          <CheckLine
            numbers={checks.numbers.total ? checks.numbers : undefined}
            dates={checks.dates.total ? checks.dates : undefined}
            quotes={checks.quotes.total ? checks.quotes : undefined}
            notChecked={notCheckedFor(checks)}
          />
        )}
        {(shown.removed ?? []).length > 0 && <RemovedBox removed={removedOf(shown)} all={shown.status === "nothing_survived"} />}
      </div>
    );
  }
  return (
    <section aria-labelledby={id} data-summary={rewriting ? "rewriting" : shown.status === "writing" && ready ? "became-ready" : shown.status}>
      <h2 id={id} className="text-h2 text-ink-heading">
        {r.summaryTitle}
      </h2>
      <div className="mt-4 max-w-prose">{body}</div>
      {item.kind === "new" && item.repeats.length === 0 && shown.status !== "failed" && shown.status !== "writing" && (
        <p className="mt-4 text-caption text-ink-muted">{r.repeatsNone}</p>
      )}
    </section>
  );
}

function Repeats({ item, numbers }: { item: ReviewItem; numbers: Map<string, number> }) {
  const id = useId();
  const here = useStore(address);
  const seen = useStore(visitedStore);
  if (item.kind !== "new" || item.repeats.length === 0) return null;
  const open = { id: evidenceIn(here.search), sentence: null };
  return (
    <section aria-labelledby={id} data-repeats>
      <h2 id={id} className="text-h2 text-ink-heading">
        {r.repeatsTitle}
      </h2>
      <div className="mt-4 flex flex-col gap-4">
        {item.repeats.map((repeat) => (
          <div key={repeat.lesson_id} className="flex flex-col gap-4">
            <div className="max-w-prose">
              <NoteSentences sentences={repeat.sentences} evidence={item.summary.evidence ?? {}} numbers={numbers} opened={seen} open={open} textSize="body" />
            </div>
            <LessonCard card={repeat} level={3} compact open={open.id} visited={seen} />
          </div>
        ))}
      </div>
    </section>
  );
}

// ── After a save, and on a decided record ────────────────────────────────

type Panel = { state: State; lead: ReactNode; body: ReactNode; links: { href: string; text: ReactNode }[] };

function nextLinks(saved: Saved | null, library: string | null): { href: string; text: ReactNode }[] {
  const links: { href: string; text: ReactNode }[] = library ? [{ href: library, text: words.form.seeInLibrary }] : [];
  if (saved?.next_item_id) links.push({ href: itemHref(saved.next_item_id), text: words.form.nextItem });
  else links.push({ href: QUEUE_HREF, text: words.form.backToQueue });
  return links;
}

function afterSave(done: Done): Panel {
  const o = words.outcome;
  const item = done.saved.item;
  const outcome = item.outcome;
  const date = item.clock ? <Num date={item.clock.due_on} /> : outcome ? <Num date={outcome.on} /> : null;
  const target = outcome?.target ?? item.repeats.find((repeat) => repeat.lesson_id === done.choice)?.statement ?? "";
  const version = outcome?.version ? <Num value={outcome.version} /> : null;
  const fill = (words: { lead: string; body: string }, slots: Record<string, ReactNode>) => ({
    lead: <Fill template={words.lead} slots={slots} />,
    body: <Fill template={words.body} slots={slots} />,
  });
  if (done.verb === "recommend") {
    const key = item.kind === "recheck" ? "recommendedRecheck" : done.choice === "repeat" ? "recommendedRepeat" : done.choice === "reject" ? "recommendedReject" : "recommended";
    const phrase = words.row.phrases[done.choice] ?? "";
    return { state: "info", ...fill(o[key], { date: date ?? "", target, phrase }), links: nextLinks(done.saved, null) };
  }
  if (done.verb === "cross_check") {
    const key = done.choice === "agree" ? "agree" : "disagree";
    return { state: "info", ...fill(o[key], { region: item.decided?.region ?? "" }), links: nextLinks(done.saved, null) };
  }
  const key = (outcome?.outcome ?? "added") as keyof typeof o;
  const state: State = key === "rejected" || key === "retired_wrong" || key === "retired_outdated" ? "neutral" : "success";
  const previous = outcome?.previous_version ? <Num value={outcome.previous_version} /> : "";
  const library = key === "added" || key === "merged" || key === "changed" ? lessonHref(outcome?.lesson_id ?? "") : null;
  const words_ = o[key] as { lead: string; body: string };
  return { state, ...fill(words_, { target, version: version ?? "", previous }), links: nextLinks(done.saved, library) };
}

function recordPanel(item: ReviewItem): Panel | null {
  const outcome = item.outcome;
  if (!outcome) return null;
  const words_ = words.outcome.record[outcome.outcome];
  if (!words_) return null;
  const slots = {
    date: <Num date={outcome.on} />,
    target: outcome.target ?? "",
    version: outcome.version ? <Num value={outcome.version} /> : "",
    region: item.region,
  };
  const state: State = outcome.outcome === "rejected" || outcome.outcome.startsWith("retired") ? "neutral" : outcome.outcome === "agree" || outcome.outcome === "disagree" ? "info" : "success";
  return { state, lead: <Fill template={words_.lead} slots={slots} />, body: <Fill template={words_.body} slots={slots} />, links: [] };
}

// Who acted while the page was open, and when: the newest act in the item's history.
function staleSlots(item: ReviewItem): Record<string, ReactNode> {
  const acts: Record<string, string> = { recommended: "recommend", decided: "decide", cross_checked: "cross_check" };
  const last = [...item.history].reverse().find((event) => event.event in acts);
  return {
    name: last?.name ?? "",
    act: words.form.staleActs[last ? acts[last.event] : "recommend"],
    date: last?.on ? <Num date={last.on} /> : "",
  };
}

function CannotAct({ code, values, item }: { code: string; values: Record<string, string>; item: ReviewItem }) {
  const template = r.cannot[code];
  if (!template) return null;
  return (
    <Alert state="neutral">
      <Fill
        template={template}
        slots={{
          name: values.project_name ?? item.project.name ?? "",
          pid: <ProjectId pid={values.pid ?? item.project.pid} />,
          region: values.region ?? values.decided_region ?? item.region,
        }}
      />
    </Alert>
  );
}

// ── The page ─────────────────────────────────────────────────────────────

export function ReviewView({ item: loaded, initial }: { item: ReviewItem; initial?: { gaveWay?: GaveWay; done?: Done; form?: Parameters<typeof DecisionForm>[0]["initial"] } }) {
  const [item, setItem] = useState(loaded);
  const [done, setDone] = useState<Done | null>(initial?.done ?? null);
  const [gaveWay, setGaveWay] = useState<GaveWay | null>(initial?.gaveWay ?? null);
  const panel = useRef<HTMLDivElement>(null);
  const alertRef = useRef<HTMLDivElement>(null);
  const here = useStore(address);
  const seen = useStore(visitedStore);
  const historyId = useId();
  const sourcesNoteId = useId();
  const evidenceId = useId();
  const open = evidenceIn(here.search);

  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => setItem(loaded), [loaded]);
  // Arriving, the h1 has focus (brief 06). The statement arrives after the skeleton, which has no h1, so a
  // page that loaded with nothing focused gives the statement focus without scrolling.
  useEffect(() => {
    if (document.activeElement === document.body || document.activeElement === null) heading.current?.focus({ preventScroll: true });
  }, []);
  useEffect(() => {
    setPageTitle(fillText(r.pageTitle, { statement: loaded.statement }));
  }, [loaded.statement]);
  useEffect(() => {
    if (done) panel.current?.focus();
  }, [done]);
  useEffect(() => {
    if (gaveWay) alertRef.current?.focus();
  }, [gaveWay]);

  // Markers are numbered in page order: the evidence cards first, then each new source the summary cites.
  const numbers = new Map<string, number>();
  for (const evidence of item.evidence) numbers.set(evidence.evidence_id, numbers.size + 1);
  for (const sentence of [...(item.summary.sentences ?? []), ...item.repeats.flatMap((repeat) => repeat.sentences)])
    for (const id of sentence.evidence_ids) if (!numbers.has(id)) numbers.set(id, numbers.size + 1);

  const decided = item.stage === "decided";
  const record = decided && !done ? recordPanel(item) : null;
  const after = done ? afterSave(done) : null;
  const kind = words.kinds[item.kind];
  const status = statusOf(item);

  let action: ReactNode = null;
  if (after) action = <OutcomePanel ref={panel} {...after} />;
  else if (record) action = <OutcomePanel {...record} />;
  else if (gaveWay?.kind === "stale")
    action = (
      <div ref={alertRef} tabIndex={-1} className="flex flex-col gap-4 outline-none" data-gave-way="stale">
        <Alert state="info" live="status">
          <Fill
            template={words.form.staleLead}
            slots={staleSlots(gaveWay.item)}
          />{" "}
          {words.form.staleBody}
        </Alert>
        <ReasonField label={words.form.staleReason} value={gaveWay.reason} max={item.limits.reason_max_chars} readOnly />
      </div>
    );
  else if (gaveWay?.kind === "refused")
    action = (
      <div ref={alertRef} tabIndex={-1} className="flex flex-col gap-4 outline-none" data-gave-way="refused">
        <Alert state="error" live="alert">
          {fillText(words.form.refused, { act: words.form.acts[gaveWay.verb] ?? words.form.acts.decide })}
        </Alert>
        <CannotAct code={gaveWay.code} values={gaveWay.values} item={item} />
      </div>
    );
  else if (gaveWay?.kind === "lost")
    action = (
      <div ref={alertRef} tabIndex={-1} className="outline-none" data-gave-way="lost">
        <Alert state="error" live="alert">
          {words.form.lostRole}
        </Alert>
      </div>
    );
  else if (item.can.act)
    action = (
      <DecisionForm
        item={item}
        initial={initial?.form}
        onDone={(result) => {
          setItem(result.saved.item);
          setDone(result);
          void refreshLessonsMe();
        }}
        onGaveWay={(found) => {
          if (found.kind === "stale") setItem(found.item);
          setGaveWay(found);
        }}
      />
    );
  else if (item.can.reason_code) action = <CannotAct code={item.can.reason_code} values={item.can.values} item={item} />;

  const clockLine = decided ? (
    item.outcome?.days_from_publication !== null && item.outcome?.days_from_publication !== undefined && item.outcome.published_on ? (
      <Fill
        template={r.decidedOn}
        slots={{
          date: <Num date={item.outcome.on} />,
          days: (
            <Num
              value={item.outcome.days_from_publication}
              options={{ compact: false }}
              check={{ tooltip: <Fill template={r.decidedTooltip} slots={{ published: <Num date={item.outcome.published_on} />, date: <Num date={item.outcome.on} /> }} /> }}
            />
          ),
        }}
      />
    ) : item.outcome ? (
      <Fill template={r.decidedOnRecheck} slots={{ date: <Num date={item.outcome.on} /> }} />
    ) : null
  ) : item.clock ? (
    <Fill template={r.clockRegion} slots={{ clock: <ClockLine clock={item.clock} />, region: item.region }} />
  ) : null;

  // The workspace layout (ticket 102; DESIGN.md section 4, Page layouts, Workspace): the head and the work in columns
  // 1 to 7 from a frame of 75rem, so the evidence drawer opens into the free columns and the work never moves, and the
  // history as the side panel in columns 9 to 12, which hides while the drawer is open. Below that frame the page is
  // one column and the history follows the work.
  const head = (
    <div data-page-head>
      <Breadcrumb
        held
        trail={[{ text: words.tabs.library, href: LESSONS_HREF }, { text: words.queueTitle, href: QUEUE_HREF }, { text: kind }]}
        back={{ text: r.breadcrumbBack, href: QUEUE_HREF }}
      />
      <p className="mt-4 text-small font-semibold text-ink-heading" data-status>
        {status}
      </p>
      <h1 ref={heading} tabIndex={-1} className="mt-2 text-h1 text-balance wrap-anywhere text-ink-heading focus:outline-none">
        {item.statement}
      </h1>
      {clockLine && <p className="mt-2 text-body text-ink-muted">{clockLine}</p>}
      <div className="mt-3 flex flex-wrap gap-2">
        <EvidenceBadge status={item.ieg_status} describedBy={sourcesNoteId} />
        {item.may_repeat && !decided && <StatusBadge kind="may-repeat" />}
        {(item.clock?.overdue_days ?? 0) > 0 && <StatusBadge kind="overdue" />}
      </div>
    </div>
  );
  const history = (
    <SidePanel title={decided ? r.historyDone : r.historyOpen} headingId={historyId}>
      <HistoryList events={item.history} lists={item.lists} headingId={historyId} stacked />
    </SidePanel>
  );

  return (
    <div data-review-page={item.item_id}>
      <Workspace head={head} side={history}>
      <section aria-labelledby={evidenceId}>
        <h2 id={evidenceId} className="text-h2 text-ink-heading">
          {r.evidenceTitle}
        </h2>
        <p id={sourcesNoteId} className="mt-1 max-w-prose text-caption text-ink-muted">
          {words.sourcesNote}
        </p>
        <div className="mt-4 flex flex-col gap-4">
          {item.evidence.map((evidence) => (
            <EvidenceCardFull key={evidence.evidence_id} evidence={evidence} n={numbers.get(evidence.evidence_id)!} open={open === evidence.evidence_id} visited={seen.has(evidence.evidence_id)} />
          ))}
          {item.ieg_note && (
            <Alert state="neutral">
              {item.ieg_note.kind === "awaiting" ? r.awaitingNote : <Fill template={r.aloneNote} slots={{ date: <Num date={item.ieg_note.review_date} /> }} />}
            </Alert>
          )}
        </div>
      </section>

      <div className="mt-8 @md/page:mt-12">
        <Tags item={item} />
      </div>
      <div className="mt-8 @md/page:mt-12">
        <Summary item={item} numbers={numbers} onRetried={(fresh) => setItem({ ...item, summary: fresh.summary, repeats: fresh.repeats, may_repeat: fresh.may_repeat })} />
      </div>
      {item.kind === "new" && item.repeats.length > 0 && (
        <div className="mt-8 @md/page:mt-12">
          <Repeats item={item} numbers={numbers} />
        </div>
      )}
      {action && <div className="mt-8 @md/page:mt-12" data-review-action>{action}</div>}
      </Workspace>
    </div>
  );
}

// A line of skeleton that shows only below a page area of 768 px, where the words it stands for wrap once more.
const NARROW_ONLY = "@md/page:hidden";

// One evidence card's frame, block for block, as tall as an ICR card at each width: the eyebrow and marker,
// the title, the quote, the source line and the check line.
function EvidenceFrame() {
  return (
    <div className="flex flex-col gap-3 rounded-md border border-line bg-surface p-4 @md/page:p-6" data-skeleton-card>
      <div className="flex items-start justify-between gap-3">
        <SkeletonLine className="text-label" width="w-1/4" />
        <Skeleton className="size-5" radius="rounded-pill" />
      </div>
      <span className="-mt-1 flex flex-col text-h2">
        <SkeletonLine width="w-3/4" />
        <SkeletonLine width="w-1/3" className={NARROW_ONLY} />
      </span>
      <span className="flex max-w-prose flex-col text-body">
        <SkeletonLine width="w-full" />
        <SkeletonLine width="w-full" />
        <SkeletonLine width="w-1/2" />
        <SkeletonLine width="w-full" className={NARROW_ONLY} />
        <SkeletonLine width="w-full" className={NARROW_ONLY} />
        <SkeletonLine width="w-3/5" className={NARROW_ONLY} />
      </span>
      <SkeletonText className="text-caption" widths={["w-full", "w-1/4"]} />
      <Skeleton className="h-14 w-full @md/page:h-10" radius="rounded-sm" />
    </div>
  );
}

export function ReviewSkeleton() {
  return (
    <div aria-busy="true" data-review-page="loading" className="flex flex-col">
      <p role="status" className="clip-visually">
        {r.loading}
      </p>
      <SkeletonLine className="mt-4 text-small" width="w-[30%]" />
      <span className="mt-2 flex flex-col text-h1">
        <SkeletonLine width="w-full" />
        <SkeletonLine width="w-3/5" />
        <SkeletonLine width="w-2/5" className={NARROW_ONLY} />
      </span>
      <span className="mt-2 flex flex-col text-body">
        <SkeletonLine width="w-1/2" />
        <SkeletonLine width="w-1/3" className={NARROW_ONLY} />
      </span>
      <Skeleton className="mt-3 h-[30px] w-40" radius="rounded-pill" />
      <h2 className="mt-8 text-h2 text-ink-heading @md/page:mt-12">{r.evidenceTitle}</h2>
      {/* Static copy, so "The evidence" and the cards never move when the item arrives. */}
      <p className="mt-1 max-w-prose text-caption text-ink-muted">{words.sourcesNote}</p>
      <div className="mt-4 flex flex-col gap-4">
        {[0, 1].map((index) => (
          <EvidenceFrame key={index} />
        ))}
      </div>
    </div>
  );
}

export function ReviewPage({ itemId }: { itemId: string }) {
  const [load, retry] = useLoad<ReviewItem>(`/api/lessons/review/${encodeURIComponent(itemId)}`);
  // Someone who is not a lesson reviewer reads the page as the library's: "Lessons | Strata".
  const denied = load.status === "error" && load.error?.status === 403;
  useEffect(() => {
    if (denied) setPageTitle(copy.pages.lessons.title);
  }, [denied]);
  const trail = (
    <Breadcrumb held trail={[{ text: words.tabs.library, href: LESSONS_HREF }, { text: words.queueTitle, href: QUEUE_HREF }]} back={{ text: r.breadcrumbBack, href: QUEUE_HREF }} />
  );
  let body: ReactNode;
  if (load.status === "loading") body = <>{trail}<ReviewSkeleton /></>;
  else if (load.status === "error") {
    const code = (load.error?.body as { code?: string } | undefined)?.code;
    if (load.error?.status === 404 && code === "unknown_item") {
      body = (
        <>
          {trail}
          <h1 tabIndex={-1} className="clip-visually">{r.breadcrumbBack}</h1>
          <EmptyState
            className="mt-6"
            title={<Fill template={r.notFoundTitle} slots={{ id: <span className="font-mono font-medium wrap-anywhere">{itemId}</span> }} />}
            body={r.notFoundBody}
            link={{ href: QUEUE_HREF, text: r.notFoundLink }}
          />
        </>
      );
    } else if (load.error?.status === 403 && code === "not_a_reviewer") {
      body = (
        <>
          <h1 tabIndex={-1} className="text-h1 text-ink-heading focus:outline-none">{copy.pages.lessons.title}</h1>
          <p className="mt-2 max-w-prose text-body text-pretty text-ink-muted">{copy.pages.lessons.purpose}</p>
          <div className="mt-8">
            <EmptyState title={words.queue.noAccessTitle} body={words.queue.noAccessBody} link={{ href: LESSONS_HREF, text: words.queue.noAccessLink }} />
          </div>
        </>
      );
    } else {
      // The page's one read failed: its error alert sits in the page's alert slot, and under the breadcrumb the h1
      // names the page (ticket 102; the shell redesign plan, 8.5).
      body = (
        <>
          {trail}
          <h1 tabIndex={-1} className="mt-2 text-h1 text-ink-heading focus:outline-none">{copy.pages.lessonReview.title}</h1>
          <PageAlert>
            <LoadError error={load.error} message={r.error} permission={r.permission} onRetry={retry} retrying={load.retrying} attempt={load.attempt} />
          </PageAlert>
        </>
      );
    }
  } else return <ReviewView item={load.data} />;
  // Until the item arrives, and when it cannot, the page keeps to the workspace's work columns.
  return (
    <DocumentColumn>
      <div className="pb-0">{body}</div>
    </DocumentColumn>
  );
}
