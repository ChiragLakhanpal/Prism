// A draft's page (the 35 brief), at /drafts/:draftId: one document column, read top to bottom in the
// argument's order. What I drafted and how I checked it (the lede, the method, the check line, the
// removed box and the steps), then the notes, then the sources, then the action. The column spans
// columns 1 to 7 from a page area of 1200 px, so the evidence drawer opens beside the notes; the notes are
// a table when the column is at least 560 px wide, and cards below that.
//
// The header sticks from 1024 px; the draft bar sticks to the bottom of a window at least 768 px wide and
// 640 px tall. Scroll padding keeps a focused control clear of both (DESIGN.md section 10), measured as
// their heights change. Only the draft's author acts; the server holds the state machine, and the page
// changes state only when the server says so.
import { useCallback, useEffect, useId, useLayoutEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { Alert } from "../components/Alert";
import { StepsTaken } from "../components/Answer";
import { Breadcrumb } from "../components/Breadcrumb";
import { EmptyState } from "../components/Card";
import { CheckLine, notCheckedFor, RemovedBox, type Removed } from "../components/Checks";
import { DiscardedNotice, DraftBar, ExportSuccess } from "../components/DraftBar";
import { DraftNotes, NoteSentences, type NoteRow } from "../components/DraftNotes";
import { Fill } from "../components/Fill";
import { LoadError } from "../components/LoadError";
import { Num } from "../components/Num";
import { Skeleton, SkeletonLine, SkeletonText } from "../components/Skeleton";
import { SourcesList } from "../components/SourcesList";
import { DiscardedOn, StateStepper } from "../components/StateStepper";
import type { Step } from "../components/Steps";
import { TextLink } from "../components/TextLink";
import { copy } from "../copy";
import { ApiError, getJson } from "../lib/api";
import { cx } from "../lib/cx";
import { act, draftScope, fileHref, preloaded, refusalOf, type Action, type Draft } from "../lib/drafts";
import { evidenceIn, openedAt, origin, remember } from "../lib/evidence";
import { download } from "../lib/export";
import { formatCount, formatDate, formatNumber } from "../lib/format";
import { address } from "../lib/router";
import { useStore } from "../lib/store";

const words = copy.draft;
const kind = copy.draft.kinds.review_notes;
const whole = (value: number) => formatNumber(value, { compact: false });
const day = (iso: string) => formatDate(iso.slice(0, 10));
const short = (iso: string) => formatDate(iso.slice(0, 10), { style: "table" });

type Loaded =
  | { status: "loading" }
  | { status: "ready"; draft: Draft }
  | { status: "missing" }
  | { status: "error"; error: ApiError | null; retrying: boolean; attempt: number };

function useDraft(draftId: string): [Loaded, (draft: Draft) => void, () => void] {
  const held = preloaded.get()[draftId];
  const [loaded, setLoaded] = useState<Loaded>(held ? { status: "ready", draft: held } : { status: "loading" });
  const [attempt, setAttempt] = useState(held ? -1 : 0);
  useEffect(() => {
    if (attempt < 0) return;
    const controller = new AbortController();
    getJson<Draft>(`/api/drafts/${encodeURIComponent(draftId)}`, { signal: controller.signal }).then(
      (draft) => setLoaded({ status: "ready", draft }),
      (error: unknown) => {
        if (controller.signal.aborted) return;
        if (error instanceof ApiError && error.status === 404) setLoaded({ status: "missing" });
        else setLoaded({ status: "error", error: error instanceof ApiError ? error : null, retrying: false, attempt });
      },
    );
    return () => controller.abort();
  }, [draftId, attempt]);
  const replace = useCallback((draft: Draft) => setLoaded({ status: "ready", draft }), []);
  const reload = useCallback(() => {
    setLoaded((current) => (current.status === "error" ? { ...current, retrying: true } : current));
    setAttempt((count) => Math.max(count, 0) + 1);
  }, []);
  return [loaded, replace, reload];
}

// Keeps focused elements 8 px clear of the sticky header and the sticky bar, as each one's height
// changes (DESIGN.md section 10; WCAG 2.4.11).
function useScrollPadding(header: HTMLElement | null, bar: HTMLElement | null) {
  useLayoutEffect(() => {
    const root = document.documentElement;
    const update = () => {
      const stuck = (element: HTMLElement | null) => element && getComputedStyle(element).position === "sticky";
      root.style.scrollPaddingTop = stuck(header) ? `${header!.offsetHeight + 8}px` : "";
      root.style.scrollPaddingBottom = stuck(bar) ? `${bar!.offsetHeight + 8}px` : "";
    };
    update();
    const observer = new ResizeObserver(update);
    for (const element of [header, bar]) if (element) observer.observe(element);
    window.addEventListener("resize", update);
    return () => {
      observer.disconnect();
      window.removeEventListener("resize", update);
      root.style.scrollPaddingTop = "";
      root.style.scrollPaddingBottom = "";
    };
  }, [header, bar]);
}

function removedItems(draft: Draft): Removed[] {
  const reasons = copy.removed.reasons as Record<string, { item: string; joined: string }>;
  return draft.removed.map((item) => {
    const code = [item.reason, ...item.reasons.map((reason) => reason.code)].find((one) => one in reasons);
    const reason = code ? reasons[code] : copy.removed.unknownReason;
    return { sentence: item.sentence, reason: reason.item, reasonJoined: reason.joined };
  });
}

// The writing's four steps, as the draft keeps them, past tense.
function stepsOf(draft: Draft): Step[] {
  const steps = kind.steps;
  const checks = draft.checks;
  const done = (key: string, text: string): Step => ({ key, running: "", done: text, state: "done" });
  return [
    done("read", steps.read.done(day(draft.subject.plan_date))),
    done("write", steps.write.done(draft.written.sentences, formatCount(draft.written.sentences), draft.written.notes, formatCount(draft.written.notes))),
    done("check", words.writing.checkDone(formatCount(checks.checks_run.length), checks.sentences.written, formatCount(checks.sentences.written),
      checks.sentences.removed, formatCount(checks.sentences.removed))),
    done("save", steps.save.done),
  ];
}

export function DraftHeader({ title, subtitle, state, headerRef }: {
  title: ReactNode;
  subtitle: ReactNode;
  state: ReactNode;
  headerRef?: (element: HTMLDivElement | null) => void;
}) {
  return (
    <div ref={headerRef} data-draft-header className="border-b border-line bg-page py-4 @lg/page:sticky @lg/page:top-0 @lg/page:z-10">
      <div className="flex flex-wrap items-start justify-between gap-x-6 gap-y-2">
        <div className="min-w-0">
          <h1 tabIndex={-1} className="text-h1 text-ink-heading focus:outline-none">
            {title}
          </h1>
          <p className="mt-2 text-body text-ink-muted">{subtitle}</p>
        </div>
        <div className="min-w-0 @lg/page:mt-2">{state}</div>
      </div>
    </div>
  );
}

export function DraftCrumbs({ pid, name, last }: { pid: string; name: ReactNode; last: ReactNode }) {
  const drafts = { text: copy.nav.tabs.drafts, href: "/drafts" };
  return (
    <Breadcrumb
      back={drafts}
      trail={[
        drafts,
        { text: <Fill template={copy.breadcrumb.project} slots={{ name, pid: <span className="font-mono font-medium">{pid}</span> }} />, href: `/projects/${pid}` },
        { text: last },
      ]}
    />
  );
}

export function subtitleOf(agency: string, planDate: string): ReactNode {
  return <Fill template={kind.subtitle} slots={{ agency, date: <Num date={planDate} /> }} />;
}

// The column: columns 1 to 7 from a page area of 1200 px, all 12 below. It is the notes' size container.
export function DocumentColumn({ children }: { children: ReactNode }) {
  return (
    <div className="layout-grid">
      <div data-document-column className="@container/doc col-span-12 min-w-0 @xl/page:col-span-7">
        {children}
      </div>
    </div>
  );
}

export function DraftPage({ draftId, search }: { draftId: string; search: string }) {
  const params = new URLSearchParams(search);
  const view = params.get("view");
  if (view === "piu" || view === "public") return <PreviewCard view={view} />;
  return <Draft draftId={draftId} view={view} />;
}

function PreviewCard({ view }: { view: "piu" | "public" }) {
  return (
    <DocumentColumn>
      <div data-draft-page="preview">
        <h1 tabIndex={-1} className="sr-only">
          {copy.pages.draft.title}
        </h1>
        <EmptyState
          title={view === "piu" ? kind.previewPiuTitle : words.page.publicTitle}
          body={view === "piu" ? kind.previewPiuBody : words.page.publicBody}
        />
      </div>
    </DocumentColumn>
  );
}

function Draft({ draftId, view }: { draftId: string; view: string | null }) {
  const [loaded, replace, reload] = useDraft(draftId);
  const [busy, setBusy] = useState<Action | null>(null);
  const [failed, setFailed] = useState<Action | null>(null);
  const [status, setStatus] = useState("");
  const [conflict, setConflict] = useState(false);
  const [fresh, setFresh] = useState(false);
  const [header, setHeader] = useState<HTMLDivElement | null>(null);
  const [bar, setBar] = useState<HTMLElement | null>(null);
  const exportButton = useRef<HTMLButtonElement>(null);
  const checkButton = useRef<HTMLButtonElement>(null);
  const success = useRef<HTMLHeadingElement>(null);
  const discarded = useRef<HTMLSpanElement>(null);
  // A draft the writing page just saved opens here with no request; the page says it is ready.
  const [justWritten] = useState(() => Boolean(preloaded.get()[draftId]));
  const [announced, setAnnounced] = useState("");
  const focusNext = useRef<"export" | "check" | "success" | "discarded" | null>(null);
  const ledeId = useId();
  const loadedAt = useRef(Date.now());
  const here = useStore(address);
  const opens = useStore(openedAt);
  const from = useStore(origin);
  useScrollPadding(header, bar);

  const draft = loaded.status === "ready" ? loaded.draft : null;

  // The draft's sources open in the drawer at once, from what the draft keeps, with no request.
  useEffect(() => {
    if (!draft) return;
    for (const evidence of Object.values(draft.evidence)) remember(evidence);
    draftScope.set(draft.subject.project_id);
    document.title = copy.pageTitle(kind.pageTitle(draft.subject.implementing_agency, short(draft.subject.plan_date)));
  }, [draft]);
  useEffect(() => () => draftScope.set(null), []);

  // Arriving, the h1 has focus (brief 06). A draft that arrives after its skeleton, or from the writing page
  // whose h1 had focus, keeps focus on the h1 without scrolling, and the writing page's draft says it is ready.
  const ready = loaded.status === "ready";
  useEffect(() => {
    if (!ready) return;
    if (document.activeElement === document.body || document.activeElement === null) {
      document.querySelector<HTMLElement>("main h1")?.focus({ preventScroll: true });
    }
    if (justWritten && draft) {
      const timer = setTimeout(() => setAnnounced(kind.ready(draft.counts.written, formatCount(draft.counts.written))), 100);
      return () => clearTimeout(timer);
    }
  }, [ready]);

  // Focus moves where the brief says once the server has answered and the page has drawn.
  useEffect(() => {
    const target = focusNext.current;
    focusNext.current = null;
    if (target === "export") exportButton.current?.focus();
    if (target === "check") checkButton.current?.focus();
    if (target === "discarded") discarded.current?.focus();
    if (target === "success" && success.current) {
      const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      success.current.closest("section")?.scrollIntoView({ block: "end", behavior: reduce ? "auto" : "smooth" });
      success.current.focus({ preventScroll: true });
    }
  }, [draft]);

  // The sources opened since the draft was saved: the server's, and those this page opened since it loaded.
  const opened = useMemo(() => {
    const set = new Set<string>(draft?.sources.filter((source) => source.opened).map((source) => source.evidence_id) ?? []);
    for (const [id, at] of Object.entries(opens)) if (at >= loadedAt.current) set.add(id);
    return set;
  }, [draft, opens]);
  const numbers = useMemo(() => new Map(draft?.sources.map((source) => [source.evidence_id, source.number]) ?? []), [draft]);
  const openedCount = draft ? draft.sources.filter((source) => opened.has(source.evidence_id)).length : 0;

  if (loaded.status === "loading") return <DraftSkeleton />;
  if (loaded.status === "missing") {
    return (
      <DocumentColumn>
        <div data-draft-page="missing">
          <h1 tabIndex={-1} className="sr-only">
            {copy.pages.draft.title}
          </h1>
          <EmptyState title={words.page.notFoundTitle} body={words.page.notFoundBody} link={{ href: "/drafts", text: words.page.notFoundLink }} />
        </div>
      </DocumentColumn>
    );
  }
  if (loaded.status === "error") {
    return (
      <DocumentColumn>
        <div data-draft-page="error">
          <h1 tabIndex={-1} className="sr-only">
            {copy.pages.draft.title}
          </h1>
          <LoadError
            error={loaded.error}
            message={words.page.error}
            permission={words.page.permission}
            onRetry={reload}
            retrying={loaded.retrying}
            attempt={loaded.attempt}
          />
        </div>
      </DocumentColumn>
    );
  }

  const d = loaded.draft;
  const subject = d.subject;
  const planHref = `/projects/${subject.project_id}/procurement/${subject.agency_id}/${subject.plan_date}`;
  const open = { id: evidenceIn(here.search), sentence: from && from.serial === null ? from.sentence : null };

  const onAct = async (action: Action) => {
    if (busy) return;
    setBusy(action);
    setFailed(null);
    if (action === "export") setStatus(words.bar.exportStarted);
    try {
      const next = await act(d, action, view);
      if (action === "export") {
        setFresh(true);
        focusNext.current = "success";
        const word = next.export?.files.find((file) => file.name.endsWith(".docx"));
        if (word) download(fileHref(next.draft_id, word.name), word.name);
      } else if (action === "check") {
        focusNext.current = "export";
        setStatus(kind.markedChecked);
      } else if (action === "discard") {
        focusNext.current = "discarded";
        setStatus("");
      } else {
        focusNext.current = next.state === "checked" ? "export" : "check";
        setStatus(next.state === "checked" ? words.bar.restoredChecked : words.bar.restored);
      }
      setConflict(false);
      replace(next);
    } catch (error) {
      const refusal = refusalOf(error);
      if (refusal?.code === "stale") {
        setConflict(true);
        reload();
      } else {
        setFailed(action);
        setStatus("");
      }
    } finally {
      setBusy(null);
    }
  };

  const signal = d.counts.signal;
  const written = d.counts.written;
  const refs = d.notes.filter((note) => note.state === "written").map((note) => note.activity_reference_no);
  const counted = (
    <div>
      <p className="font-semibold">{copy.checkPlan.explain.counted}</p>
      <ul className="mt-1 font-mono">
        {refs.map((ref) => (
          <li key={ref}>{ref}</li>
        ))}
      </ul>
    </div>
  );
  const lede =
    written === signal ? (
      <Fill template={kind.lede(signal)} slots={{ count: <Num count={signal} check={{ tooltip: counted }} /> }} />
    ) : (
      <Fill template={kind.ledePartial} slots={{ written: <Num count={written} check={{ tooltip: counted }} />, count: <Num count={signal} /> }} />
    );

  const rows: NoteRow[] = d.notes.map((note) => ({
    key: note.activity_reference_no,
    mark: note.mark,
    description: note.description,
    href: `${planHref}#${note.activity_reference_no}`,
    note:
      note.state === "written" ? (
        <NoteSentences sentences={note.sentences} evidence={d.evidence} numbers={numbers} opened={opened} open={open} />
      ) : note.state === "refused" ? (
        <p className="text-small text-ink">{kind.refused[note.refusal ?? ""] ?? kind.refusedOther}</p>
      ) : (
        <p className="text-small text-ink-muted">{kind.abstain}</p>
      ),
  }));

  const removed = removedItems(d);
  const showRemoved = d.layout.removed_box === "always" || removed.length > 0;
  const created = day(d.created_at);

  let end: ReactNode;
  if (d.state === "exported" && d.export) {
    end = <ExportSuccess draft={d} fresh={fresh} headingRef={success} date={day} />;
  } else if (d.state === "discarded") {
    end = (
      <DiscardedNotice
        ref={setBar}
        sentenceRef={discarded}
        sentence={kind.discarded}
        restoring={busy === "restore"}
        may_act={d.author.you && view !== "piu" && view !== "public"}
        failed={failed === "restore"}
        onRestore={() => onAct("restore")}
      />
    );
  } else {
    end = (
      <DraftBar
        ref={setBar}
        draft={d}
        words={kind}
        opened={openedCount}
        busy={busy}
        failed={failed}
        status={status}
        onAct={onAct}
        exportRef={exportButton}
        checkRef={checkButton}
      />
    );
  }

  return (
    <DocumentColumn>
      <div data-draft-page={d.state}>
        {conflict && (
          <Alert state="info" live="status" className="mb-6">
            {words.conflict}
          </Alert>
        )}
        <DraftCrumbs pid={subject.project_id} name={subject.project_name} last={kind.crumb(short(subject.plan_date))} />
        <div className="mt-4">
          <DraftHeader
            headerRef={setHeader}
            title={kind.title}
            subtitle={subtitleOf(subject.implementing_agency, subject.plan_date)}
            state={
              d.state === "discarded" && d.discarded ? (
                <DiscardedOn date={day(d.discarded.at)} />
              ) : (
                <StateStepper state={d.state === "discarded" ? "draft" : d.state} checkedBy={d.author.you ? null : d.author.name} />
              )
            }
          />
        </div>
        <div className="mt-6 max-w-[72ch]">
          <h2 id={ledeId} tabIndex={-1} className="text-title text-pretty text-ink-heading focus:outline-none" data-lede>
            {lede}
          </h2>
          <p className="mt-2 text-body text-ink">
            <Fill template={kind.method} slots={{ check: <TextLink href={planHref}>{kind.methodLink}</TextLink> }} />
          </p>
        </div>
        <div className="mt-4 flex max-w-prose flex-col gap-2">
          <CheckLine numbers={d.checks.numbers} dates={d.checks.dates} quotes={d.checks.quotes} notChecked={notCheckedFor(d.checks, d.layout.not_checked)} />
          {showRemoved && <RemovedBox removed={removed} />}
        </div>
        <StepsTaken steps={stepsOf(d)} runId={d.draft_id} idLabel={words.idLabel} />
        <p className="mt-6 text-caption text-ink-muted" data-count-line data-numbers>
          {kind.countLine(signal, whole(signal))}
        </p>
        <div className="mt-2">
          <DraftNotes rows={rows} caption={kind.tableCaption(subject.implementing_agency, day(subject.plan_date))} cardsLabelId={ledeId} />
        </div>
        {d.layout.sources_list && (
          <div className="mt-8">
            <SourcesList sources={d.sources} evidence={d.evidence} opened={opened} openedCount={openedCount} citations={d.citations} open={open} />
          </div>
        )}
        <p className="mt-6 max-w-[72ch] text-small text-ink-muted" data-not-visible>
          {copy.checkPlan.notVisible}
        </p>
        <p className="mt-2 text-caption text-ink-muted" data-meta>
          {d.author.you ? kind.metaYou(created) : kind.metaTeammate(d.author.name ?? "", created)}
        </p>
        <div className="mt-8">{end}</div>
        <p role="status" className="sr-only" data-page-status>
          {announced}
        </p>
      </div>
    </DocumentColumn>
  );
}

// While the draft loads (the 35 brief, section 8.3): the places of the header, the lede, the method, the
// check line, the removed box, the table's real head over three rows, the sources and the bar.
function DraftSkeleton() {
  const columns = kind.columns;
  return (
    <DocumentColumn>
      <div data-draft-page="loading" aria-busy="true">
        <p role="status" className="sr-only">
          {words.page.loading}
        </p>
        <nav aria-hidden="true" className="text-caption">
          <SkeletonLine width="w-[200px] max-w-full" />
        </nav>
        <div className="mt-4 border-b border-line py-4">
          <h1 tabIndex={-1} className="focus:outline-none">
            <span className="sr-only">{copy.pages.draft.title}</span>
            <Skeleton className="h-7 w-[200px] max-w-full" />
          </h1>
          <Skeleton className="mt-2 h-4 w-[280px] max-w-full" />
          <Skeleton className="mt-2 h-5 w-[300px] max-w-full" />
        </div>
        <div className="mt-6 max-w-[72ch]">
          <SkeletonText className="text-title" widths={["w-full", "w-2/5"]} />
          <SkeletonText className="mt-2 text-body" widths={["w-full", "w-4/5"]} />
        </div>
        <Skeleton className="mt-4 h-9 w-full max-w-prose rounded-sm" />
        <Skeleton className="mt-2 h-12 w-full max-w-prose rounded-sm" />
        <div className="mt-8 hidden overflow-hidden rounded-md border border-line bg-surface @min-[35rem]/doc:block">
          <table className="w-full table-fixed border-collapse text-small">
            <thead className="bg-surface-2">
              <tr>
                <th scope="col" className="w-60 p-3 text-left font-semibold text-ink-heading">
                  {columns.activity}
                </th>
                <th scope="col" className="p-3 text-left font-semibold text-ink-heading">
                  {columns.note}
                </th>
              </tr>
            </thead>
            <tbody>
              {[0, 1, 2].map((index) => (
                <tr key={index} className="h-30 border-t border-line align-top">
                  <td className="p-3">
                    <Skeleton className="h-7 w-28 rounded-pill" />
                    <SkeletonText className="mt-1" widths={["w-4/5", "w-3/5"]} />
                  </td>
                  <td className="p-3">
                    <SkeletonText widths={["w-full", "w-11/12", "w-3/5"]} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <ul aria-hidden="true" className="mt-8 flex flex-col gap-3 @min-[35rem]/doc:hidden">
          {[0, 1, 2].map((index) => (
            <li key={index} className="h-50 rounded-md border border-line bg-surface p-4">
              <Skeleton className="h-7 w-28 rounded-pill" />
              <SkeletonText className="mt-2 text-small" widths={["w-4/5", "w-full", "w-3/5"]} />
            </li>
          ))}
        </ul>
        <div className="mt-8 flex flex-col gap-2">
          {[0, 1, 2].map((index) => (
            <Skeleton key={index} className="h-4 w-4/5" />
          ))}
        </div>
        <section aria-label={words.bar.label} className={cx("mt-8 border-t border-line bg-surface px-4 py-3 md:px-6")}>
          <p className="max-w-[80ch] text-small text-ink">{words.bar.consequence}</p>
          <div className="mt-3 flex justify-between gap-2">
            <Skeleton className="h-11 w-28 rounded-pill" />
            <Skeleton className="h-11 w-40 rounded-pill" />
          </div>
        </section>
      </div>
    </DocumentColumn>
  );
}
