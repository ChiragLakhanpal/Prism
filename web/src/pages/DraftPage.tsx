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
import { BAR_BUTTONS, BAR_MAIN, Consequence, DiscardedNotice, DraftBar, ExportSuccess, STICKY } from "../components/DraftBar";
import { DraftNotes, NoteSentences, type NoteRow } from "../components/DraftNotes";
import { Fill } from "../components/Fill";
import { LoadError } from "../components/LoadError";
import { Num } from "../components/Num";
import { ProjectIdText } from "../components/ProjectId";
import { Skeleton, SkeletonLine, SkeletonText } from "../components/Skeleton";
import { SourcesList } from "../components/SourcesList";
import { DiscardedOn, StateStepper } from "../components/StateStepper";
import type { Step } from "../components/Steps";
import { TextLink } from "../components/TextLink";
import { copy } from "../copy";
import { ApiError, getJson } from "../lib/api";
import { cx } from "../lib/cx";
import { act, draftScope, fileHref, preloaded, refusalOf, storeFailed, type Action, type Draft } from "../lib/drafts";
import { evidenceIn, openedAt, origin, remember } from "../lib/evidence";
import { download } from "../lib/export";
import { formatCount, formatDate, formatNumber } from "../lib/format";
import { address } from "../lib/router";
import { useStore } from "../lib/store";
import { setPageTitle } from "../lib/title";

const words = copy.draft;
type KindWords = (typeof copy.draft.kinds)[keyof typeof copy.draft.kinds];
// Before a draft loads, its kind is not known yet: the skeleton draws the one kind there is today.
const SKELETON_KIND: KindWords = copy.draft.kinds.review_notes;
const whole = (value: number) => formatNumber(value, { compact: false });
const day = (iso: string) => formatDate(iso.slice(0, 10));
const short = (iso: string) => formatDate(iso.slice(0, 10), { style: "table" });

type Loaded =
  | { status: "loading" }
  | { status: "ready"; draft: Draft }
  | { status: "missing" }
  | { status: "error"; error: ApiError | null; retrying: boolean; attempt: number };

// A draft the writing page just saved opens with no request, once: the entry is taken from the store, so
// the same draft opened again later in the visit (from Drafts, or with Back and Forward) is read from the
// server, which holds its state now. It is read in the initializer and removed in an effect, which
// StrictMode may run twice without harm.
function useDraft(draftId: string): [Loaded, (draft: Draft) => void, () => void, boolean] {
  const [held] = useState<Draft | null>(() => preloaded.get()[draftId] ?? null);
  useEffect(() => {
    if (held) preloaded.set(({ [draftId]: _taken, ...rest }) => rest);
  }, [held, draftId]);
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
  return [loaded, replace, reload, held !== null];
}

// Whether this sticky part of the page sticks now: the header, the bar or the discarded notice sit in the
// page like any other block on a phone, in a short window, or beside the open drawer below about 960 px.
const sticks = (element: HTMLElement | null | undefined) => Boolean(element && getComputedStyle(element).position === "sticky");

// Keeps focused elements 8 px clear of the sticky header and the sticky bar, as each one's height
// changes (DESIGN.md section 10; WCAG 2.4.11). The same paddings go to --sticky-top and --sticky-bottom,
// which shift the scroll margins of the controls inside those parts (app.css), so the Tab key does not
// scroll the page to bring a control in the bar out of the bar's own padding.
function useScrollPadding(header: HTMLElement | null, bar: HTMLElement | null) {
  useLayoutEffect(() => {
    const root = document.documentElement;
    const update = () => {
      const top = sticks(header) ? `${header!.offsetHeight + 8}px` : "";
      const bottom = sticks(bar) ? `${bar!.offsetHeight + 8}px` : "";
      root.style.scrollPaddingTop = top;
      root.style.scrollPaddingBottom = bottom;
      root.style.setProperty("--sticky-top", top);
      root.style.setProperty("--sticky-bottom", bottom);
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
      root.style.removeProperty("--sticky-top");
      root.style.removeProperty("--sticky-bottom");
    };
  }, [header, bar]);
}

function removedItems(draft: Draft, kind: KindWords): Removed[] {
  // The kind's own words for a reason first, then the answer's.
  const reasons: Record<string, { item: string; joined: string }> = { ...copy.removed.reasons, ...kind.removedReasons };
  return draft.removed.map((item) => {
    const code = [item.reason, ...item.reasons.map((reason) => reason.code)].find((one) => one in reasons);
    const reason = code ? reasons[code] : copy.removed.unknownReason;
    return { sentence: item.sentence, reason: reason.item, reasonJoined: reason.joined };
  });
}

// The writing's four steps, as the draft keeps them, past tense. The number of checks is the server's.
function stepsOf(draft: Draft, kind: KindWords): Step[] {
  const steps = kind.steps;
  const checks = draft.checks;
  const done = (key: string, text: string): Step => ({ key, running: "", done: text, state: "done" });
  return [
    done("read", steps.read.done(day(draft.subject.plan_date))),
    done("write", steps.write.done(draft.written.sentences, formatCount(draft.written.sentences), draft.written.notes, formatCount(draft.written.notes))),
    done("check", words.writing.checkDone(formatCount(draft.checks_count), checks.sentences.written, formatCount(checks.sentences.written),
      checks.sentences.removed, formatCount(checks.sentences.removed))),
    done("save", steps.save.done),
  ];
}

// The sticky header: it sticks from a page area of 1024 px, and in a window of 1200 px or more, where the
// column keeps its place beside the evidence drawer. It must be a direct child of the tall page, with its
// margin on itself (className), or sticky has no room to move. Its type sets a height such as 134.89 px, and
// a stuck header whose bottom edge falls inside a pixel lets the notes under it show through that pixel, so
// its bottom padding takes up the fraction and the header ends on a whole pixel.
export function DraftHeader({ title, subtitle, state, headerRef, className }: {
  title: ReactNode;
  subtitle: ReactNode;
  state: ReactNode;
  headerRef?: (element: HTMLDivElement | null) => void;
  className?: string;
}) {
  const [element, setElement] = useState<HTMLDivElement | null>(null);
  const ref = useCallback((node: HTMLDivElement | null) => {
    setElement(node);
    headerRef?.(node);
  }, [headerRef]);
  useLayoutEffect(() => {
    if (!element) return;
    // The content box only, so the padding this sets never sets it off again.
    const observer = new ResizeObserver(([entry]) => {
      const content = entry.contentRect.height;
      element.style.paddingBottom = `calc(var(--spacing) * 4 + ${Math.ceil(content) - content}px)`;
    });
    observer.observe(element);
    return () => observer.disconnect();
  }, [element]);
  return (
    <div
      ref={ref}
      data-draft-header
      className={cx("border-b border-line bg-page py-4 @lg/page:sticky @lg/page:top-0 @lg/page:z-10 xl:sticky xl:top-0 xl:z-10", className)}
    >
      <div className="flex flex-wrap items-start justify-between gap-x-6 gap-y-2">
        <div className="min-w-0">
          <h1 tabIndex={-1} className="text-h1 text-ink-heading focus:outline-none">
            {title}
          </h1>
          <p className="mt-2 text-body text-ink-muted">{subtitle}</p>
        </div>
        <div className="min-w-0 @lg/page:mt-2 xl:mt-2">{state}</div>
      </div>
    </div>
  );
}

export function DraftCrumbs({ pid, name, last }: { pid: string; name: ReactNode; last: ReactNode }) {
  const drafts = { text: copy.nav.tabs.drafts, href: "/drafts" };
  return (
    <Breadcrumb
      back={drafts}
      held
      trail={[
        drafts,
        // The crumb is the link to the project, so its ID is plain mono inside it, never a link inside a link.
        { text: <Fill template={copy.breadcrumb.project} slots={{ name, pid: <ProjectIdText pid={pid} /> }} />, href: `/projects/${pid}` },
        { text: last },
      ]}
    />
  );
}

export function subtitleOf(kind: KindWords, agency: string, planDate: string): ReactNode {
  return <Fill template={kind.subtitle} slots={{ agency, date: <Num date={planDate} /> }} />;
}

// The page's width without a classic scroll bar, which 100vw counts, for app.css's document column, so the
// column lines up with the navy bar and the footer, which center in the same width.
function useWindowInline() {
  useLayoutEffect(() => {
    const root = document.documentElement;
    const update = () => root.style.setProperty("--window-inline", `${root.clientWidth}px`);
    update();
    const observer = new ResizeObserver(update);
    observer.observe(root);
    window.addEventListener("resize", update);
    return () => {
      observer.disconnect();
      window.removeEventListener("resize", update);
      root.style.removeProperty("--window-inline");
    };
  }, []);
}

// The column: columns 1 to 7 from a page area of 1200 px, all 12 below. It is the notes' size container.
// In a window of 1200 px or more it keeps the same place and width when the evidence drawer narrows the
// page area (the 35 brief, section 3.2; app.css, "A draft's document column").
export function DocumentColumn({ children }: { children: ReactNode }) {
  useWindowInline();
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
  if (view === "piu" || view === "public") return <PreviewCard view={view} kind={SKELETON_KIND} />;
  return <Draft draftId={draftId} view={view} />;
}

function PreviewCard({ view, kind }: { view: "piu" | "public"; kind: KindWords }) {
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
  const [loaded, replace, reload, justWritten] = useDraft(draftId);
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
    setPageTitle(copy.draft.kinds[draft.kind].pageTitle(draft.subject.implementing_agency, short(draft.subject.plan_date)));
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
      const ready = copy.draft.kinds[draft.kind].ready;
      const timer = setTimeout(() => setAnnounced(ready(draft.counts.written, formatCount(draft.counts.written))), 100);
      return () => clearTimeout(timer);
    }
  }, [ready]);

  // Focus moves where the brief says once the server has answered and the page has drawn. While the bar or
  // the discarded notice sticks, it is already in view, and the page's scroll padding would otherwise make
  // the browser scroll the notes away, so focus moves without scrolling. Where it does not stick, focus
  // scrolls to it as usual (DESIGN.md section 10).
  useEffect(() => {
    const target = focusNext.current;
    focusNext.current = null;
    const move = (element: HTMLElement | null) =>
      element?.focus({ preventScroll: sticks(element.closest<HTMLElement>("[data-draft-bar],[data-discarded-notice]")) });
    if (target === "export") move(exportButton.current);
    if (target === "check") move(checkButton.current);
    if (target === "discarded") move(discarded.current);
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

  // The marker that opened the drawer stays where the reader saw it, beside its source. From a window of
  // 1200 px nothing moves; below that the narrower column may turn the notes into cards, which moves the
  // notes and everything under them, the Sources list too. So the same marker, in the view now shown, is put
  // back at the height in the window it had when it was opened, then kept clear of the sticky header and
  // bar (the 35 brief, section 3.1). A marker in a note is found by its source and sentence, since the table
  // and the cards each have one; a marker in the Sources list is the one that was opened.
  const openId = evidenceIn(here.search);
  const draftOrigin = from && from.serial === null && from.id === openId ? from : null;
  // It waits a second frame, so the scroll padding has followed the bar, which may wrap taller.
  useEffect(() => {
    if (!openId || !draftOrigin) return;
    const { sentence, marker, top } = draftOrigin;
    let frame = requestAnimationFrame(() => {
      frame = requestAnimationFrame(() => {
        const candidates =
          sentence === null
            ? [marker]
            : [...document.querySelectorAll<HTMLElement>(`[data-draft-notes] [data-citation-id="${CSS.escape(openId)}"][data-sentence="${sentence}"]`)];
        const shown = candidates.find((element) => element?.isConnected && element.getClientRects().length > 0);
        if (!shown) return;
        if (top !== null) window.scrollBy({ top: shown.getBoundingClientRect().top - top, behavior: "instant" });
        shown.scrollIntoView({ block: "nearest" });
      });
    });
    return () => cancelAnimationFrame(frame);
  }, [openId, draftOrigin]);

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
            message={storeFailed(loaded.error) ? words.page.draftStore : words.page.error}
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
  const kind: KindWords = copy.draft.kinds[d.kind];
  const subject = d.subject;
  const planHref = `/projects/${subject.project_id}/procurement/${subject.agency_id}/${subject.plan_date}`;
  const open = { id: openId, sentence: draftOrigin ? draftOrigin.sentence : null };

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
        // The draft reloads in the state it is in now; focus goes to that state's next step. An exported draft
        // ends on its export panel, which scrolls into view and takes focus, as on a revisit.
        const now = refusal.state;
        focusNext.current = now === "checked" ? "export" : now === "draft" ? "check" : now === "discarded" ? "discarded" : "success";
        setStatus(words.conflict);
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

  const removed = removedItems(d, kind);
  const showRemoved = d.layout.removed_box === "always" || removed.length > 0;
  const created = day(d.created_at);

  let end: ReactNode;
  if (d.state === "exported" && d.export) {
    end = <ExportSuccess className="mt-8" draft={d} fresh={fresh} headingRef={success} date={day} />;
  } else if (d.state === "discarded") {
    end = (
      <DiscardedNotice
        className="mt-8"
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
        className="mt-8"
        ref={setBar}
        draft={d}
        words={kind}
        notice={conflict ? words.conflict : null}
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
        <DraftHeader
          className="mt-4"
          headerRef={setHeader}
          title={kind.title}
          subtitle={subtitleOf(kind, subject.implementing_agency, subject.plan_date)}
          state={
            d.state === "discarded" && d.discarded ? (
              <DiscardedOn date={day(d.discarded.at)} />
            ) : (
              <StateStepper state={d.state === "discarded" ? "draft" : d.state} checkedBy={d.author.you ? null : d.author.name} />
            )
          }
        />
        <div className="mt-6 max-w-[72ch]">
          <h2 id={ledeId} tabIndex={-1} className="text-title text-pretty text-ink-heading focus:outline-none" data-lede>
            {lede}
          </h2>
          <p className="mt-2 text-body text-ink">
            <Fill template={kind.method} slots={{ check: <TextLink href={planHref}>{kind.methodLink}</TextLink> }} />
          </p>
        </div>
        <div className="mt-4 flex max-w-prose flex-col gap-2">
          {/* Counts over the notes' sentences on screen, and the model's part when one was judged (ticket 24), as
              src/strata/drafts/files.py writes the evidence pack's line. A draft saved before then has no shown counts. */}
          <CheckLine
            numbers={(d.checks.shown ?? d.checks).numbers}
            dates={(d.checks.shown ?? d.checks).dates}
            quotes={(d.checks.shown ?? d.checks).quotes}
            judged={d.checks.shown ? { judged: d.checks.shown.judged, proven: d.checks.shown.proven } : undefined}
            notChecked={notCheckedFor(d.checks, d.layout.not_checked)}
          />
          {showRemoved && <RemovedBox removed={removed} />}
        </div>
        <StepsTaken steps={stepsOf(d, kind)} runId={d.draft_id} idLabel={words.idLabel} />
        <p className="mt-6 text-caption text-ink-muted" data-count-line data-numbers>
          {kind.countLine(signal, whole(signal))}
        </p>
        <div className="mt-2">
          <DraftNotes
            rows={rows}
            columns={d.layout.columns.map((column) => (kind.columns as Record<string, string>)[column])}
            caption={kind.tableCaption(subject.implementing_agency, day(subject.plan_date))}
            cardsLabelId={ledeId}
          />
        </div>
        {d.layout.sources_list && (
          <div className="mt-8">
            <SourcesList
              sources={d.sources}
              evidence={d.evidence}
              opened={opened}
              openedCount={openedCount}
              total={d.opened.of}
              citations={d.citations}
              open={open}
            />
          </div>
        )}
        <p className="mt-6 max-w-[72ch] text-small text-ink-muted" data-not-visible>
          {copy.checkPlan.notVisible}
        </p>
        <p className="mt-2 text-caption text-ink-muted" data-meta>
          {d.author.you ? kind.metaYou(created) : kind.metaTeammate(d.author.name ?? "", created)}
        </p>
        {end}
        <p role="status" className="sr-only" data-page-status>
          {announced}
        </p>
      </div>
    </DocumentColumn>
  );
}

// While the draft loads (the 35 brief, section 8.3): the places of the header, the lede, the method, the
// check line, the removed box, the steps disclosure, the count line, the table's real head over three
// rows, the sources, the page's last lines and the bar, each the height of what it stands for at its
// width, so nothing moves when it loads. Below 48rem the subtitle, the lede, the method and the check line
// take more lines, the breadcrumb is the short link back to Drafts, and the bar stacks its buttons. The
// bar's frame sticks as the bar will (the bar-sticks variant), with its consequence sentence, which is true
// before the draft loads.
function DraftSkeleton() {
  const kind = SKELETON_KIND;
  // Lines that differ below 48rem and from it: one set is shown at each width.
  const lines = (narrow: string[], wide: string[], className: string) => (
    <>
      <SkeletonText className={cx(className, "md:hidden")} widths={narrow} />
      <SkeletonText className={cx(className, "hidden md:flex")} widths={wide} />
    </>
  );
  return (
    <DocumentColumn>
      <div data-draft-page="loading" aria-busy="true">
        <p role="status" className="sr-only">
          {words.page.loading}
        </p>
        <nav aria-hidden="true" className="flex h-7 items-center text-caption">
          <Skeleton className="h-[1em] w-16 md:w-[200px] md:max-w-full" />
        </nav>
        {/* The h1, the subtitle and the stepper, which the subtitle's length puts on a line of its own. */}
        <div className="mt-4 border-b border-line py-4">
          <h1 tabIndex={-1} className="text-h1 focus:outline-none">
            <span className="sr-only">{copy.pages.draft.title}</span>
            <SkeletonLine width="w-[200px] max-w-full" />
          </h1>
          {lines(["w-full", "w-full", "w-1/3"], ["w-[280px] max-w-full"], "mt-2 text-body")}
          <SkeletonLine className="mt-2 text-small @lg/page:mt-4" width="w-[300px] max-w-full" />
        </div>
        <div className="mt-6 max-w-[72ch]">
          {lines(["w-full", "w-full", "w-1/2"], ["w-full", "w-2/5"], "text-title")}
          {lines(["w-full", "w-full", "w-full", "w-3/5"], ["w-full", "w-4/5"], "mt-2 text-body")}
        </div>
        <div className="mt-4 flex max-w-prose flex-col gap-2">
          {/* The check line, six lines of small text in its box below 48rem and three from it, and the
              one-line removed box. */}
          <Skeleton className="h-34 w-full md:h-19" radius="rounded-sm" />
          <Skeleton className="h-11 w-full" radius="rounded-sm" />
        </div>
        <div className="mt-4 flex h-11 items-center">
          <Skeleton className="h-4 w-56" />
        </div>
        <SkeletonLine className="mt-6 text-caption" width="w-56" />
        <div className="mt-2 hidden overflow-hidden rounded-md border border-line bg-surface @min-[35rem]/doc:block">
          <table className="w-full table-fixed border-collapse text-small">
            <thead className="bg-surface-2">
              <tr>
                <th scope="col" className="w-60 p-3 text-left font-semibold text-ink-heading">
                  {kind.columns.activity}
                </th>
                <th scope="col" className="p-3 text-left font-semibold text-ink-heading">
                  {kind.columns.note}
                </th>
              </tr>
            </thead>
            <tbody>
              {[0, 1, 2].map((index) => (
                <tr key={index} className="h-36 border-t border-line align-top">
                  <td className="p-3">
                    <Skeleton className="h-7 w-28" radius="rounded-pill" />
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
        {/* Each card's parts where they will be: the badge, the reference, two lines of description, the
            rule, then the note. */}
        <ul aria-hidden="true" className="mt-2 flex flex-col gap-3 @min-[35rem]/doc:hidden">
          {["h-72", "h-72", "h-77"].map((height, index) => (
            <li key={index} className={cx(height, "rounded-md border border-line bg-surface p-4")}>
              <Skeleton className="h-7 w-28" radius="rounded-pill" />
              <SkeletonLine className="mt-1 text-small" width="w-48" />
              <SkeletonText className="mt-1 text-small" widths={["w-full", "w-3/5"]} />
              <div className="mt-3 border-t border-line pt-3">
                <SkeletonText className="text-small" widths={["w-full", "w-full", "w-11/12", "w-full", "w-2/5"]} />
              </div>
            </li>
          ))}
        </ul>
        <div className="mt-8">
          <SkeletonLine className="text-title" width="w-24" />
          {lines(["w-full", "w-3/5"], ["w-4/5 max-w-[72ch]"], "mt-2 text-caption")}
          <div className="mt-4 flex flex-col gap-4">
            {[0, 1, 2].map((index) => (
              <div key={index} className="h-35 @min-[35rem]/doc:h-26 @min-[50rem]/doc:h-21">
                <SkeletonText className="text-small" widths={["w-4/5", "w-3/5", "w-2/5"]} />
              </div>
            ))}
          </div>
        </div>
        <p className="mt-6 max-w-[72ch] text-small text-ink-muted">{copy.checkPlan.notVisible}</p>
        <SkeletonLine className="mt-2 text-caption" width="w-64 max-w-full" />
        <section aria-label={words.bar.label} className={cx("z-10 mt-8 border-t border-line bg-surface px-4 py-3 md:px-6", STICKY)}>
          <p className="max-w-[80ch] text-small text-ink">
            {/* The kind's lead sentence before the consequence, and the opened count and hold line after it,
                each in two parts, so they wrap over as many lines as the words will. */}
            <Skeleton inline className="w-[36ch]" /> <Skeleton inline className="w-[20ch]" /> <Consequence />{" "}
            <Skeleton inline className="w-[24ch]" /> <Skeleton inline className="w-[30ch]" />
          </p>
          <div className={BAR_BUTTONS}>
            <div>
              <Skeleton className="h-11 w-24" radius="rounded-pill" />
            </div>
            <div className={BAR_MAIN}>
              {/* Full width while stacked, and each button's width in a row. */}
              <Skeleton className="h-11 w-full bar-sticks:w-36" radius="rounded-pill" />
              <Skeleton className="h-11 w-full bar-sticks:w-40" radius="rounded-pill" />
            </div>
          </div>
        </section>
      </div>
    </DocumentColumn>
  );
}
