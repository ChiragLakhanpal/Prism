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
import { DraftNotes, NoteSentences, WrittenIn, type NoteRow } from "../components/DraftNotes";
import { ENGLISH, languageName, workingLanguage } from "../lib/lang";
import { citedInParts, MissionBriefParts } from "../components/MissionBriefParts";
import { Fill } from "../components/Fill";
import { LoadError } from "../components/LoadError";
import { Num } from "../components/Num";
import { PaperSheet } from "../components/PaperSheet";
import { PpsdRows } from "../components/PpsdRows";
import { PpsdSources } from "../components/PpsdSources";
import { IdText, ProjectId, ProjectIdText } from "../components/ProjectId";
import { Skeleton, SkeletonLine, SkeletonText } from "../components/Skeleton";
import { SourcesList } from "../components/SourcesList";
import { StepRowsDraft } from "../components/StepRowsDraft";
import { AccessLabel } from "../components/AccessLabel";
import { DiscardedOn, StateStepper } from "../components/StateStepper";
import { DraftDisagreements } from "../components/DraftDisagreements";
import type { Step } from "../components/Steps";
import { TextLink } from "../components/TextLink";
import { copy } from "../copy";
import { ApiError, getJson } from "../lib/api";
import type { RemovedEvent } from "../lib/answer";
import { cx } from "../lib/cx";
import { act, draftScope, fileHref, preloaded, refusalOf, setField, setForm, storeFailed, type Action, type Draft } from "../lib/drafts";
import { evidenceIn, openEvidence, openedAt, origin, recordOpened, remember } from "../lib/evidence";
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

// What the removed box lists, for a saved draft or a writing that saved nothing (DraftNewPage, WritingDatesPage).
export function removedItems(holder: { removed: RemovedEvent[] }, kind: KindWords): Removed[] {
  // The kind's own words for a reason first, then the answer's.
  const reasons: Record<string, { item: string; joined: string }> = { ...copy.removed.reasons, ...kind.removedReasons };
  return holder.removed.map((item) => {
    const code = [item.reason, ...item.reasons.map((reason) => reason.code)].find((one) => one in reasons);
    const reason = code ? reasons[code] : copy.removed.unknownReason;
    return { sentence: item.sentence, reason: reason.item, reasonJoined: reason.joined };
  });
}

// The writing's four steps, as the draft keeps them, past tense. The number of checks is the server's. Suggested PPSD
// rows count the risks selected and the rows written, as the write step stored them (ticket 36).
function stepsOf(draft: Draft, kind: KindWords): Step[] {
  const steps = kind.steps;
  const checks = draft.checks;
  const done = (key: string, text: string): Step => ({ key, running: "", done: text, state: "done" });
  const read = draft.kind === "mission_brief" ? "" : draft.ppsd ? formatCount(draft.ppsd.selected) : day(draft.subject.plan_date);
  const notes = draft.ppsd ? (draft.written.rows ?? draft.ppsd.counts.total) : draft.written.notes;
  return [
    done("read", steps.read.done(read)),
    done("write", steps.write.done(draft.written.sentences, formatCount(draft.written.sentences), notes, formatCount(notes))),
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

// Suggested PPSD rows' breadcrumb and subtitle (ticket 36): the package, as the workspace names it, links back to it.
export function packageHref(subject: { package_id?: string | null; step_reference?: string | null }): string {
  return `/packages/${encodeURIComponent(subject.package_id ?? subject.step_reference ?? "")}`;
}

export function PackageCrumbs({ title, href, last }: { title: string; href: string; last: ReactNode }) {
  const drafts = { text: copy.nav.tabs.drafts, href: "/drafts" };
  return <Breadcrumb back={drafts} held trail={[drafts, { text: title, href }, { text: last }]} />;
}

export function ppsdSubtitle(title: string, reference: string | null | undefined): ReactNode {
  return (
    <Fill
      template={copy.draft.kinds.ppsd_rows.subtitle}
      slots={{ title, reference: reference ? <IdText id={reference} /> : copy.ppsd.noReference }}
    />
  );
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
  const current = useStore(workingLanguage)?.code ?? ENGLISH;
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
    for (const evidence of Object.values(draft.evidence)) {
      // A passage a lesson rests on comes inside get_lessons' row, without its text (ticket 36), so the drawer asks
      // the server for the whole passage rather than show that part.
      const row = (evidence as { row?: Record<string, unknown> }).row;
      if (draft.ppsd && row && row.passage_id && !row.text) continue;
      remember(evidence);
    }
    draftScope.set(draft.subject.project_id ?? null);
    setPageTitle(draft.kind === "mission_brief"
      ? copy.draft.kinds.mission_brief.pageTitle(draft.subject.project_name, draft.subject.project_id)
      : draft.ppsd
        ? copy.draft.kinds[draft.kind].pageTitle(draft.subject.package_title ?? "", "")
        : copy.draft.kinds[draft.kind].pageTitle(draft.subject.implementing_agency, short(draft.subject.plan_date)));
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
      // Planned dates count the steps dated with the draft's choice (ticket 38); every other kind its notes.
      const done = draft.dates ? draft.dates.counts.dated[draft.dates.choice] : draft.counts.written;
      const timer = setTimeout(() => setAnnounced(ready(done, formatCount(done))), 100);
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
        // The Word file, or a draft of planned dates' STEP rows (ticket 38), downloads at once; the evidence pack waits.
        const word = next.export?.files.find((file) => file.name.endsWith(".docx"))
          ?? next.export?.files.find((file) => file.name.endsWith(".csv") && !file.name.endsWith("-evidence-pack.csv"));
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
  // A mission brief (ticket 37): five parts, with the project's name, country and records' date.
  const brief = d.kind === "mission_brief";
  // Suggested PPSD rows and the Project Paper summary (ticket 36), by what the kind's writer adds to the page, so a
  // kind registered with the same writer (ticket 38's agency variant) gets the same page in its own words.
  const ppsd = d.ppsd ?? null;
  const paper = Boolean(d.summary);
  // Planned dates (ticket 38), and every draft an implementing agency team makes, which is Official Use Only.
  const dates = d.dates ?? null;
  const agencyDraft = d.kind === "step_rows" || d.kind === "ppsd_rows_agency";
  const editable = d.author.you && view !== "piu" && view !== "public" && (d.state === "draft" || d.state === "checked");
  const lede = dates ? (
    dates.counts.dated[dates.choice] === dates.counts.steps ? (
      <Fill template={kind.lede(dates.counts.activities)} slots={{ total: formatCount(dates.counts.steps), count: formatCount(dates.counts.activities) }} />
    ) : (
      <Fill template={kind.ledePartial} slots={{ written: formatCount(dates.counts.dated[dates.choice]), total: formatCount(dates.counts.steps),
        count: formatCount(dates.counts.activities) }} />
    )
  ) : ppsd ? (
    ppsd.counts.total === ppsd.selected ? (
      <Fill template={kind.lede(ppsd.selected)} slots={{ count: formatCount(ppsd.selected) }} />
    ) : (
      <Fill template={kind.ledePartial} slots={{ written: formatCount(ppsd.counts.total), count: formatCount(ppsd.selected) }} />
    )
  ) : paper ? (
    <Fill template={kind.lede(d.summary?.ppsd_rows ?? 0)} slots={{ count: formatCount(d.summary?.ppsd_rows ?? 0) }} />
  ) : brief ? (
    written === d.notes.length ? kind.lede(written) : copy.mission.ledePartial(formatCount(written))
  ) : written === signal ? (
      <Fill template={kind.lede(signal)} slots={{ count: <Num count={signal} check={{ tooltip: counted }} /> }} />
    ) : (
      <Fill template={kind.ledePartial} slots={{ written: <Num count={written} check={{ tooltip: counted }} />, count: <Num count={signal} /> }} />
    );

  // A field a person sets (ticket 36): the value shows at once, the progress line and the bar follow from the
  // server's answer, and the page's polite region says what happened.
  const onSave = async (rowKey: string, field: string, value: string | null): Promise<boolean> => {
    try {
      const next = await setField(d, rowKey, field, value, view);
      const counts = next.ppsd!.counts;
      const total = whole(counts.total);
      const risk = next.ppsd!.rows.find((row) => row.row_key === rowKey)?.risk_label ?? "";
      const header = next.ppsd!.forms[next.ppsd!.form].columns.find((column) => column.key === field)?.header ?? field;
      if (field === "risk_owner") {
        const all = value !== null && counts.owners_set === counts.total;
        setAnnounced(
          all && next.state === "draft" ? copy.ppsd.allOwners(formatCount(counts.total))
            : all && next.holds.length === 0 ? copy.ppsd.exportReady
              : value === null ? copy.ppsd.ownerRemoved(whole(counts.owners_set), total) : copy.ppsd.ownerSet(whole(counts.owners_set), total),
        );
      } else {
        setAnnounced(next.state === "checked" && next.holds.length === 0 ? copy.ppsd.exportReady : copy.ppsd.fieldSet(header, risk));
      }
      replace(next);
      return true;
    } catch {
      setAnnounced(copy.fill.saveFailed);
      return false;
    }
  };
  const onForm = async (form: "short" | "long") => {
    try {
      const next = await setForm(d, form, view);
      replace(next);
      setAnnounced(form === "long" ? copy.ppsd.showingLong(whole(next.ppsd!.counts.rated), whole(next.ppsd!.counts.total)) : copy.ppsd.showingShort);
    } catch {
      setAnnounced(copy.ppsd.formFailed);
    }
  };

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
        words={dates ? { ...kind, exportLabel: copy.draft.kinds.step_rows.dates.exportButton, openedLine: copy.draft.kinds.step_rows.dates.barOpened } : kind}
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

  const writtenIn = d.lang ?? ENGLISH;
  return (
    <WrittenIn.Provider value={writtenIn}>
    <DocumentColumn>
      <div data-draft-page={d.state}>
        {conflict && (
          <Alert state="info" live="status" className="mb-6">
            {words.conflict}
          </Alert>
        )}
        {ppsd ? (
          <PackageCrumbs title={subject.package_title ?? ""} href={packageHref(subject)} last={kind.crumb("")} />
        ) : (
          <DraftCrumbs pid={subject.project_id} name={subject.project_name} last={brief ? kind.title : kind.crumb(short(subject.plan_date))} />
        )}
        <DraftHeader
          className="mt-4"
          headerRef={setHeader}
          title={kind.title}
          subtitle={brief ? (
            <Fill template={kind.subtitle} slots={{ name: subject.project_name, pid: <ProjectId pid={subject.project_id} />, country: subject.country ?? "" }} />
          ) : ppsd ? ppsdSubtitle(subject.package_title ?? "", subject.step_reference) : subtitleOf(kind, subject.implementing_agency, subject.plan_date)}
          state={
            d.state === "discarded" && d.discarded ? (
              <DiscardedOn date={day(d.discarded.at)} />
            ) : (
              <StateStepper state={d.state === "discarded" ? "draft" : d.state} checkedBy={d.author.you ? null : d.author.name} />
            )
          }
        />
        {agencyDraft && <AccessLabel className="mt-2" />}
        <div className="mt-6 max-w-[72ch]">
          <h2 id={ledeId} tabIndex={-1} className="text-title text-pretty text-ink-heading focus:outline-none" data-lede>
            {lede}
          </h2>
          <p className="mt-2 text-body text-ink">
            {brief ? (
              <Fill template={copy.mission.method} slots={{ date: formatDate(subject.data_through ?? subject.as_of ?? created) }} />
            ) : paper || dates ? (
              kind.method
            ) : (
              <Fill
                template={kind.method}
                slots={{ check: <TextLink href={ppsd ? `${packageHref(subject)}#risks` : planHref}>{kind.methodLink}</TextLink> }}
              />
            )}
          </p>
          {/* The language the writer wrote it in, when it is not English or not your choice now (the 42 brief, 3.6). */}
          {(writtenIn !== ENGLISH || writtenIn !== current) && (
            <p className="mt-2 text-caption text-ink-muted" data-draft-language>
              {copy.draft.language(languageName(writtenIn))}
            </p>
          )}
          {paper && (subject.agencies_with_plans ?? 0) > 1 && (
            <p className="mt-2 text-caption text-ink-muted" data-scope-caption>
              {copy.paper.scope(subject.project_id, formatCount(subject.agencies_with_plans ?? 0), subject.implementing_agency)}
            </p>
          )}
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
        {!dates && <StepsTaken steps={stepsOf(d, kind)} runId={d.draft_id} idLabel={words.idLabel} />}
        {dates ? (
          <div className="mt-6">
            <StepRowsDraft
              view={dates}
              lists={d.evidence}
              onOpen={(listId, element) => {
                // The drawer records no step's list it opens elsewhere (section 2 holds those), so the draft records
                // its own: the bar's count of lists opened moves at once, and the evidence pack says it was opened.
                openEvidence(listId, { serial: null, sentence: null, marker: element, runId: null });
                recordOpened(listId, null);
              }}
              editable={d.author.you && d.state === "draft" && view !== "piu" && view !== "public"}
              onChoice={async (choice) => {
                try {
                  replace(await setField(d, "", "choice", choice, view));
                } catch {
                  setAnnounced(copy.fill.saveFailed);
                }
              }}
            />
          </div>
        ) : ppsd ? (
          <div className="mt-6">
            <PpsdRows draft={d} editable={editable} opened={opened} open={open} ledeId={ledeId} onSave={onSave} onForm={onForm} />
          </div>
        ) : paper ? (
          <div className="mt-6">
            <PaperSheet draft={d} numbers={numbers} opened={opened} open={open} />
          </div>
        ) : brief ? (
          <div className="mt-8">
            <MissionBriefParts notes={d.notes} evidence={d.evidence} numbers={numbers} opened={opened} open={open} subject={subject} />
          </div>
        ) : (
          <>
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
          </>
        )}
        {/* The cards check 6 attached (ticket 36): a warning card holds export until its author keeps a report. */}
        {(d.disagreements ?? []).length > 0 && (
          <div className="mt-8">
            <DraftDisagreements
              draft={d}
              choosing={editable}
              preview={view === "piu" || view === "public"}
              onChange={() => {
                getJson<Draft>(`/api/drafts/${encodeURIComponent(d.draft_id)}`).then(replace, () => undefined);
              }}
            />
          </div>
        )}
        {d.layout.sources_list && ppsd && (
          <div className="mt-8">
            <PpsdSources draft={d} opened={opened} openedCount={openedCount} open={open} />
          </div>
        )}
        {d.layout.sources_list && !ppsd && (
          <div className="mt-8">
            <SourcesList
              sources={d.sources}
              evidence={d.evidence}
              opened={opened}
              openedCount={openedCount}
              total={d.opened.of}
              citations={d.citations}
              open={open}
              citedIn={brief ? citedInParts : undefined}
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
    </WrittenIn.Provider>
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
