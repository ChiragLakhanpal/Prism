// Lessons > Judging (ticket 32; the 32 design brief, sections 2.6, 2.7, 4.4, 5.5 and 5.6), for query judges:
//
// - /lessons/judging?show=&page=: how many queries you have judged, how far the other judge is, "Judge the next
//   query", your agreement where you have both finished (Cohen's kappa beside its count, withheld below min_pairs),
//   a segmented filter, and the queries in a table with Pagination.
// - /lessons/judging/:queryId?p=: one passage at a time. From a page area of 1024 px the query is pinned at the top
//   and the grade bar at the bottom, and only the paragraph between them changes. A grade saves at once and the next
//   ungraded passage takes its place; A, P and N choose a grade while focus is inside the panel or the bar. Judging
//   is blind: the page never shows a passage's rank, score or search setup, highlighted words, live feedback, or
//   the other judge's grades before both finish.
import { useEffect, useId, useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import { Alert } from "../components/Alert";
import { Breadcrumb } from "../components/Breadcrumb";
import { Button, PRIMARY_LINK } from "../components/Button";
import { EmptyState } from "../components/Card";
import { PassageBlock } from "../components/EvidenceDrawer";
import { Fill } from "../components/Fill";
import { GradeBar, PassageMap, ProgressMeter } from "../components/Judging";
import { fillText } from "../components/LessonParts";
import { OutcomePanel } from "../components/LessonReview";
import { LoadError } from "../components/LoadError";
import { Num } from "../components/Num";
import { PageAlert } from "../components/PageAlert";
import { Pagination } from "../components/Pagination";
import { SegmentedControl } from "../components/SegmentedControl";
import { Skeleton, SkeletonLine, SkeletonText } from "../components/Skeleton";
import { Table, type Row as TableRow } from "../components/Table";
import { TextLink } from "../components/TextLink";
import { copy } from "../copy";
import type { EvidenceEvent } from "../lib/answer";
import { ApiError, getJson, putJson } from "../lib/api";
import { cx } from "../lib/cx";
import { evidenceHref, openEvidence } from "../lib/evidence";
import { formatCount } from "../lib/format";
import { refusedAs, useLoad, type Load } from "../lib/load";
import { LESSONS_HREF } from "../lib/lessons";
import { navigate } from "../lib/router";
import { JUDGING_HREF, queryHref, type Grade, type JudgingList, type JudgingQuery, type PooledPassage, type QuerySummary } from "../lib/retrieval";
import { setPageTitle } from "../lib/title";
import { usePageAtLeast } from "../lib/usePageAtLeast";
import { DocumentColumn } from "./DraftPage";
import { refreshLessonsMe } from "../lib/lessonsMe";
import { LessonsFrame } from "./LessonsPages";

const w = copy.judging;
const KEYS: Record<string, Grade> = { a: "answers", p: "partly", n: "not_relevant" };
const SETTLE_MS = 300; // a grade key within this long after an advance is ignored
const SHOWS = ["to_judge", "finished_by_you", "finished_by_both"] as const;
type Show = (typeof SHOWS)[number];

// An award notice's evidence id: its record view in the evidence drawer (brief 14).
const NOTICE = "strata.gold.notice:";

const listHref = (show: Show, page = 1) => {
  const query = new URLSearchParams();
  if (show !== "to_judge") query.set("show", show);
  if (page > 1) query.set("page", String(page));
  const text = query.toString();
  return text ? `${JUDGING_HREF}?${text}` : JUDGING_HREF;
};

// ── The list of queries ──────────────────────────────────────────────────

// The award notice a query was written from, as a Roboto Mono link that opens its record in the evidence drawer, so a
// judge can check the query against it (the 32 brief, sections 2.6 and 2.7).
function NoticeLink({ query }: { query: { notice_id: string; notice_ref: string | null } }) {
  const id = `${NOTICE}${query.notice_id}`;
  return (
    <TextLink
      href={evidenceHref(id)}
      onClick={(event) => {
        event.preventDefault();
        // The link is the drawer's origin, so closing the record puts focus back on it (brief 14).
        openEvidence(id, { serial: null, sentence: null, marker: event.currentTarget, runId: null });
      }}
      // A STEP reference moves to the next line whole, and breaks inside only when it is wider than the line.
      className="inline-block max-w-full font-mono wrap-anywhere"
      data-notice-link
    >
      {query.notice_ref ?? query.notice_id}
    </TextLink>
  );
}

function Agreement({ list }: { list: JudgingList }) {
  const a = list.agreement;
  if (a.both_done === 0) return null;
  // One query is "the one query", and a count to nine is a word (ticket 58).
  const pairsTip = a.both_done === 1 ? w.tooltipPairsOne : fillText(w.tooltipPairs, { done: formatCount(a.both_done) });
  if (a.withheld || a.kappa === null) {
    return (
      <p className="max-w-prose text-small text-ink" data-agreement="withheld">
        <Fill template={w.agreeWithheld} slots={{ min: <Num value={a.min_pairs} options={{ compact: false }} />, pairs: <Num value={a.pairs} options={{ compact: false }} /> }} />
      </p>
    );
  }
  return (
    <div className="flex flex-col gap-1" data-agreement="shown">
      <p className="max-w-prose text-small text-ink">
        <Fill
          template={w.agree}
          slots={{
            agree: <Num value={a.agree} options={{ compact: false }} check={{ tooltip: pairsTip }} />,
            pairs: <Num value={a.pairs} options={{ compact: false }} check={{ tooltip: pairsTip }} />,
            kappaName: w.kappaName,
            kappa: <Num value={a.kappa} options={{ decimals: 2, compact: false }} check={{ tooltip: fillText(w.tooltipKappa, { pairs: a.pairs }) }} />,
          }}
        />
      </p>
      <p className="max-w-prose text-caption text-ink-muted">{fillText(w.agreeCaption, { kappaName: w.kappaName })}</p>
    </div>
  );
}

function Progress({ query }: { query: QuerySummary }) {
  return (
    <span className="flex flex-col gap-0.5">
      {/* Each state stays on one line. */}
      <span className="whitespace-nowrap">{fillText(w.progressYou[query.my_state], { graded: query.graded, pool: query.pool })}</span>
      <span className="whitespace-nowrap text-ink-muted">{w.progressOther[query.other_state]}</span>
    </span>
  );
}

function QueryCell({ query }: { query: QuerySummary }) {
  return (
    <span className="flex flex-col gap-0.5">
      <TextLink href={queryHref(query.query_id)}>{query.query_text}</TextLink>
      <span className="text-caption text-ink-muted">
        <Fill
          template={w.queryCaption}
          slots={{ n: <Num value={query.n} options={{ compact: false }} />, ref: <NoticeLink query={query} />, date: <Num date={query.notice_date} style="table" /> }}
        />
      </span>
    </span>
  );
}

function emptyFor(list: JudgingList): ReactNode {
  if (list.total === 0) return <EmptyState title={w.noQueriesTitle} body={w.noQueriesBody} />;
  if (list.show === "to_judge")
    return (
      <EmptyState
        title={w.emptyToJudgeTitle}
        body={<Fill template={w.emptyToJudgeBody} slots={{ done: <Num value={list.other_done} options={{ compact: false }} />, total: <Num value={list.total} options={{ compact: false }} /> }} />}
        link={{ href: listHref("finished_by_both"), text: w.emptyToJudgeLink }}
      />
    );
  if (list.show === "finished_by_you") return <EmptyState title={w.emptyYouTitle} body={w.emptyYouBody} />;
  return <EmptyState title={w.emptyBothTitle} body={w.emptyBothBody} />;
}

const COLUMNS = [
  { key: "query", header: w.columns.query, width: "w-[40%]" },
  {
    key: "pool",
    header: (
      <span className="flex flex-col">
        <span>{w.columns.pool}</span>
        <span className="text-caption font-normal text-ink-muted">{w.columns.poolDefinition}</span>
      </span>
    ),
    cardHeader: w.columns.pool,
    numeric: true,
    width: "w-[12%]",
  },
  { key: "progress", header: w.columns.progress, width: "w-[28%]" },
  {
    key: "matched",
    header: (
      <span className="flex flex-col">
        <span>{w.columns.matched}</span>
        <span className="text-caption font-normal text-ink-muted">{w.columns.matchedDefinition}</span>
      </span>
    ),
    cardHeader: w.columns.matched,
    numeric: true,
    width: "w-[20%]",
  },
];

// busy: another filter's or page's queries are on their way, so this list stays on screen, marked busy, and the
// filter keeps focus (selection follows focus, briefs 26 and 27).
export function JudgingBody({ list, onShow, busy = false }: { list: JudgingList; onShow?: (show: Show) => void; busy?: boolean }) {
  const total = <Num value={list.total} options={{ compact: false }} />;
  const lead =
    list.mine_done === 0 ? (
      list.total === 1 ? (
        w.leadNoneOne
      ) : (
        <Fill template={w.leadNone} slots={{ total: <Num count={list.total} /> }} />
      )
    ) : list.mine_done >= list.total ? (
      <Fill template={w.leadAll} slots={{ total }} />
    ) : (
      <Fill template={w.leadSome} slots={{ done: <Num value={list.mine_done} options={{ compact: false }} check={{ tooltip: w.tooltipDone }} />, total }} />
    );
  const rows: TableRow[] = list.queries.map((query) => ({
    id: query.query_id,
    cells: {
      query: <QueryCell query={query} />,
      pool: <Num value={query.pool} options={{ compact: false }} />,
      progress: <Progress query={query} />,
      matched: query.agree !== null ? fillText(w.matched, { agree: query.agree, pool: query.pool }) : <span className="text-ink-muted">{w.notYet}</span>,
    },
  }));
  return (
    <div data-judging="ready" className="flex flex-col">
      <p className="max-w-prose text-body text-ink-muted">{w.purpose}</p>
      {list.total > 0 && (
        <>
          <p tabIndex={-1} data-lead className="mt-6 max-w-prose text-lead text-pretty text-ink-heading outline-none" data-judging-lead>
            {lead}
          </p>
          <p className="mt-2 text-caption text-ink-muted">
            <Fill template={w.leadOther} slots={{ done: <Num value={list.other_done} options={{ compact: false }} />, total }} />
          </p>
          {list.next_query && (
            <div className="mt-4">
              <a href={queryHref(list.next_query)} className={cx(PRIMARY_LINK, "w-full @md/page:w-auto")} data-next-query>
                {w.next}
              </a>
            </div>
          )}
          {/* The agreement block and its space show only while a pair has been judged by both, so the filter keeps
              32 px under the next query's link either way (the 32 brief, 2.10; ticket 59). */}
          {list.agreement.both_done > 0 && (
            <div className="mt-6 @md/page:mt-8">
              <Agreement list={list} />
            </div>
          )}
          <div className="mt-6 @md/page:mt-8">
            <SegmentedControl<Show>
              legend={w.show}
              value={list.show}
              onChange={(key) => (onShow ? onShow(key) : navigate(listHref(key), { quiet: true }))}
              options={SHOWS.map((key) => ({ value: key, label: fillText(w.filters[key], { count: list.counts[key] }) }))}
            />
          </div>
        </>
      )}
      <div className="mt-4">
        {list.queries.length === 0 ? (
          emptyFor(list)
        ) : (
          <>
            <Table
              level={2}
              title={<span className="clip-visually">{w.filterNames[list.show]}</span>}
              count={{ noun: w.countNoun, one: w.countNounOne, total: list.counts[list.show], from: list.from, to: list.to }}
              busy={busy ? w.loading : undefined}
              rowHeader="query"
              columns={COLUMNS}
              state={{ status: "ready", rows }}
              source={w.source}
            />
            {list.pages > 1 && (
              <div className="mt-6">
                <Pagination page={list.page} pages={list.pages} href={(n) => listHref(list.show, n)} />
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

// The list's loading state (the 32 brief, section 5.5): the lead and its caption, the button, the filter's frame,
// the count line, the real table header and eight rows, as tall as the page they stand for, so nothing moves when it
// loads.
export function JudgingSkeleton() {
  return (
    <div aria-busy="true" data-judging="loading" className="flex min-h-svh flex-col">
      <p role="status" className="clip-visually">
        {w.loading}
      </p>
      <p className="max-w-prose text-body text-ink-muted">{w.purpose}</p>
      <SkeletonLine className="mt-6 max-w-prose text-lead" width="w-[60%]" />
      <SkeletonLine className="mt-2 text-caption" width="w-[40%]" />
      <Skeleton className="mt-4 h-11 w-full @md/page:w-50" radius="rounded-sm" />
      <SkeletonText className="mt-6 text-small @md/page:mt-8" widths={["w-full", "w-1/2"]} />
      <div className="mt-6 @md/page:mt-8" aria-hidden="true">
        <span className="block text-small text-ink-muted">{w.show}</span>
        <SegmentFrame />
      </div>
      <div className="mt-4">
        <Table
          level={2}
          title={<span className="clip-visually">{w.filterNames.to_judge}</span>}
          rowHeader="query"
          columns={COLUMNS}
          state={{
            status: "loading",
            rows: 8,
            header: (
              <span className="flex flex-col gap-1">
                <SkeletonLine className="text-small" width="w-[80%]" />
                <SkeletonLine className="text-caption" width="w-1/2" />
              </span>
            ),
          }}
        />
      </div>
    </div>
  );
}

// The filter's frame while the list loads, under its legend: three touching segments, stacked at 44 px each below a
// 768 px page area and one 32 px pill from it, with no counts yet.
function SegmentFrame() {
  return <Skeleton className="mt-2 h-33 w-full @md/page:h-8 @md/page:w-108" radius="rounded-lg @md/page:rounded-pill" />;
}

function NoAccess() {
  return <EmptyState title={w.noAccessTitle} body={w.noAccessBody} link={{ href: LESSONS_HREF, text: w.noAccessLink }} />;
}

export function JudgingView({ load, retry, last = null }: { load: Load<JudgingList>; retry: () => void; last?: JudgingList | null }) {
  if (load.status === "loading") return last ? <JudgingBody list={last} busy /> : <JudgingSkeleton />;
  // A short answer, such as an error, holds a screen's height as the skeleton did, so the footer stays below the fold.
  // A failed read's alert goes to the page's alert slot (PageAlert.tsx; ticket 102).
  if (load.status === "error") {
    return (
      <div className="min-h-svh">
        {refusedAs(load, "not_a_judge") ? (
          <NoAccess />
        ) : (
          <PageAlert>
            <LoadError error={load.error} message={w.error} permission={w.permission} onRetry={retry} retrying={load.retrying} attempt={load.attempt} />
          </PageAlert>
        )}
      </div>
    );
  }
  return <JudgingBody list={load.data} />;
}

export function JudgingPage({ search }: { search: string }) {
  const params = new URLSearchParams(search);
  const show = (SHOWS as readonly string[]).includes(params.get("show") ?? "") ? (params.get("show") as Show) : "to_judge";
  const page = Math.max(1, Number(params.get("page") ?? "1") || 1);
  const [load, retry] = useLoad<JudgingList>(`/api/judging/queries?show=${show}&page=${page}`);
  // The list on screen stays while another filter's or page's loads, so the filter keeps focus.
  const last = useRef<JudgingList | null>(null);
  if (load.status === "ready") last.current = load.data;
  const denied = refusedAs(load, "not_a_judge");
  useEffect(() => {
    if (denied) setPageTitle(copy.pages.lessons.title);
  }, [denied]);
  return (
    <LessonsFrame pageKey={denied ? "lessons" : "lessonsJudging"} failed={load.status === "error" && !denied}>
      <JudgingView load={load} retry={retry} last={last.current} />
    </LessonsFrame>
  );
}

// ── One query ────────────────────────────────────────────────────────────

const evidenceOf = (passage: PooledPassage): EvidenceEvent => ({
  id: `strata.gold.passage:${passage.passage_id}`,
  kind: "passage",
  tool: null,
  stratum: "Why",
  short_name: null,
  row: passage.passage,
  highlights: [],
});

function Differences({ query }: { query: JudgingQuery }) {
  const [open, setOpen] = useState(false);
  const differed = query.passages.map((passage, index) => ({ passage, n: index + 1 })).filter(({ passage }) => passage.other_grade && passage.other_grade !== passage.my_grade);
  return (
    <div className="flex flex-col gap-3" data-differences>
      <div>
        <Button variant="ghost" flush onPage icon={open ? ChevronUp : ChevronDown} aria-expanded={open} onClick={() => setOpen(!open)}>
          {open ? w.differencesHide : w.differencesShow}
        </Button>
      </div>
      {open &&
        (differed.length === 0 ? (
          <p className="text-body text-ink">{w.differencesNone}</p>
        ) : (
          <Table
            level={3}
            title={<span className="clip-visually">{w.differencesCaption}</span>}
            rowHeader="passage"
            columns={[
              { key: "passage", header: w.differencesColumns.passage },
              { key: "yours", header: w.differencesColumns.yours },
              { key: "theirs", header: w.differencesColumns.theirs },
            ]}
            state={{
              status: "ready",
              rows: differed.map(({ passage, n }) => ({
                id: passage.passage_id,
                cells: {
                  passage: <TextLink href={queryHref(query.query_id, n)}>{fillText(w.passageName, { i: n })}</TextLink>,
                  yours: passage.my_grade ? w.grades[passage.my_grade] : "",
                  theirs: passage.other_grade ? w.grades[passage.other_grade] : "",
                },
              })),
            }}
          />
        ))}
    </div>
  );
}

export function JudgingDesk({ query: loaded, initial, sample = false }: {
  query: JudgingQuery;
  initial?: { at?: number; mapOpen?: boolean; failed?: number; grades?: Record<string, Grade>; lockedWhileOpen?: boolean };
  // A design gallery sample: neither the header nor the grade bar sticks, so it sits inside the gallery page.
  sample?: boolean;
}) {
  const Title = sample ? "h3" : "h1";
  const [query, setQuery] = useState(loaded);
  const firstOpen = () => {
    const ungraded = loaded.passages.findIndex((passage) => !passage.my_grade);
    return ungraded >= 0 ? ungraded + 1 : 1;
  };
  const [at, setAt] = useState(initial?.at ?? firstOpen());
  const [grades, setGrades] = useState<Record<string, Grade>>(() => ({
    ...Object.fromEntries(loaded.passages.filter((p) => p.my_grade).map((p) => [p.passage_id, p.my_grade as Grade])),
    ...initial?.grades,
  }));
  const [unsaved, setUnsaved] = useState<{ passage: string; grade: Grade }[]>([]);
  const [failed, setFailed] = useState<number | null>(initial?.failed ?? null);
  // The other judge finished this query while it was open, so a grade sent then was refused as locked.
  const [lockedWhileOpen, setLockedWhileOpen] = useState(initial?.lockedWhileOpen ?? false);
  const [mapOpen, setMapOpen] = useState(initial?.mapOpen ?? false);
  const [announced, setAnnounced] = useState("");
  // Whether the header is stuck to the top of the window, so it takes its 1 px line (the 32 brief, section 2.7).
  const [stuck, setStuck] = useState(false);
  // No advance yet, so a key pressed as soon as the page opens grades.
  const lastAdvance = useRef(Number.NEGATIVE_INFINITY);
  const desk = useRef<HTMLDivElement>(null);
  const top = useRef<HTMLDivElement>(null);
  const headerRef = useRef<HTMLDivElement>(null);
  const h1 = useRef<HTMLHeadingElement>(null);
  const panelHeading = useRef<HTMLHeadingElement>(null);
  const outcome = useRef<HTMLDivElement>(null);
  const lockedAlert = useRef<HTMLDivElement>(null);
  const panelId = useId();
  // From a 1024 px page area the grade bar sticks to the bottom of the window and comes last; below it, the grade
  // buttons come right after the passage, before the definitions (the 32 brief, section 2.9).
  const wide = usePageAtLeast(desk, 64) && !sample;
  const pool = query.passages.length;
  const passage = query.passages[at - 1];
  const graded = query.passages.map((p) => Boolean(grades[p.passage_id]));
  const done = graded.filter(Boolean).length;
  const finished = pool > 0 && done === pool && unsaved.length === 0 && failed === null;
  const wasFinished = useRef(finished);

  useEffect(() => setQuery(loaded), [loaded]);
  useEffect(() => {
    if (!sample) setPageTitle(fillText(w.pageTitle, { n: query.n }));
  }, [query.n]);
  useEffect(() => {
    if (!sample && (document.activeElement === document.body || document.activeElement === null)) h1.current?.focus({ preventScroll: true });
  }, []);
  // The last grade saved: the panel that says so takes focus, so it is heard (the 32 brief, section 6.2).
  useEffect(() => {
    if (finished && !wasFinished.current && !sample) outcome.current?.focus();
    wasFinished.current = finished;
  }, [finished]);
  useEffect(() => {
    if (lockedWhileOpen && !sample) lockedAlert.current?.focus();
  }, [lockedWhileOpen]);
  useEffect(() => {
    const element = top.current;
    if (!element || sample) return;
    const watch = new IntersectionObserver(([entry]) => setStuck(!entry.isIntersecting));
    watch.observe(element);
    return () => watch.disconnect();
  }, [sample]);

  function show(n: number, focus = true) {
    setAt(n);
    if (!sample) navigate(queryHref(query.query_id, n), { replace: true, quiet: true });
    if (!focus) return;
    requestAnimationFrame(() => {
      const heading = panelHeading.current;
      if (!heading) return;
      heading.focus({ preventScroll: true });
      // Nothing sticks below a 1024 px page area, so the page scrolls, instantly, to put the next passage's heading
      // at the top of the window. From it, the page scrolls only when the heading is under the stuck header or out
      // of view, and the top scroll padding then puts it just below the header.
      const { top: at } = heading.getBoundingClientRect();
      const below = headerRef.current?.getBoundingClientRect().bottom ?? 0;
      if (!wide || at < below || at > window.innerHeight) heading.scrollIntoView({ block: "start", behavior: "instant" });
    });
  }

  async function save(entries: { passage: string; grade: Grade }[]) {
    for (const entry of entries) {
      try {
        const saved = await putJson<{ locked: boolean }>(`/api/judging/queries/${encodeURIComponent(query.query_id)}/passages/${encodeURIComponent(entry.passage)}`, { grade: entry.grade });
        if (saved.locked) await reload();
        setUnsaved((all) => all.filter((item) => item !== entry));
        // A grade saved on "Try again" counts again: its failed save took it off the meter and the map.
        setGrades((all) => (all[entry.passage] ? all : { ...all, [entry.passage]: entry.grade }));
      } catch (error) {
        if (error instanceof ApiError && error.status === 409 && (error.body as { code?: string } | null)?.code === "locked") {
          // The other judge finished while this page was open: the grades are locked, so no retry could save one.
          setUnsaved([]);
          setFailed(null);
          await reload();
          setLockedWhileOpen(true);
          return;
        }
        const n = query.passages.findIndex((p) => p.passage_id === entry.passage) + 1;
        setFailed(n);
        setGrades((all) => {
          const next = { ...all };
          delete next[entry.passage];
          return next;
        });
        return;
      }
    }
  }

  async function reload() {
    try {
      setQuery(await getJson<JudgingQuery>(`/api/judging/queries/${encodeURIComponent(query.query_id)}`));
      void refreshLessonsMe();
    } catch {
      // The grades are saved; the page shows what it has.
    }
  }

  function grade(choice: Grade) {
    if (!passage || query.locked) return;
    const entry = { passage: passage.passage_id, grade: choice };
    const next = { ...grades, [passage.passage_id]: choice };
    setGrades(next);
    setUnsaved((all) => [...all, entry]);
    setFailed(null);
    setAnnounced(fillText(w.savedAs, { grade: w.grades[choice] }));
    lastAdvance.current = performance.now();
    void save([entry]);
    // The next ungraded passage after this one. When none is left, the finished panel takes focus once the save is in.
    const order = [...query.passages.slice(at), ...query.passages.slice(0, at)];
    const following = order.find((p) => !next[p.passage_id]);
    if (following) show(query.passages.indexOf(following) + 1);
  }

  // A, P and N choose a grade while focus is inside the panel or the bar: no modifier, no text field, no repeat, and
  // never within 300 ms of an advance, so a held key or a double tap can't grade the next passage too.
  const onKey = (event: KeyboardEvent) => {
    const choice = KEYS[event.key.toLowerCase()];
    if (!choice || event.altKey || event.ctrlKey || event.metaKey || event.shiftKey || event.repeat || event.nativeEvent.isComposing) return;
    const target = event.target as HTMLElement;
    if (target.closest("input, textarea, [contenteditable=true]")) return;
    event.preventDefault();
    if (performance.now() - lastAdvance.current < SETTLE_MS) return;
    grade(choice);
  };

  // From a 1024 px page area the header sticks with 12 px of the page above its caption; its negative top margin
  // takes that room back from the gap above, so nothing moves when it sticks.
  const header = (
    <div
      ref={headerRef}
      className={cx(
        "flex flex-col gap-1 bg-page",
        !sample && "@lg/page:sticky @lg/page:top-(--frame-top) @lg/page:z-10 @lg/page:-mt-3 @lg/page:border-b @lg/page:pt-3 @lg/page:pb-3",
        !sample && (stuck ? "@lg/page:border-line" : "@lg/page:border-transparent"),
      )}
      data-judging-header
      data-sticky={sample ? undefined : "top"}
      data-stuck={stuck || undefined}
    >
      <p className="text-caption text-ink-muted">
        <Fill
          template={w.header}
          slots={{
            n: <Num value={query.n} options={{ compact: false }} />,
            total: <Num value={query.total} options={{ compact: false }} />,
            ref: <NoticeLink query={query} />,
            date: <Num date={query.notice_date} />,
          }}
        />
      </p>
      <Title ref={h1} tabIndex={-1} className="text-h3 text-balance text-ink-heading focus:outline-none">
        {query.query_text}
      </Title>
      <div className="mt-2">
        <ProgressMeter part={done} whole={pool}>
          <Fill template={w.meter} slots={{ graded: <Num value={done} options={{ compact: false }} />, pool: <Num value={pool} options={{ compact: false }} /> }} />
        </ProgressMeter>
      </div>
    </div>
  );

  let main: ReactNode;
  if (pool === 0) {
    main = (
      <EmptyState
        title={<Fill template={w.emptyPoolTitle} slots={{ date: <Num date={query.query_date} /> }} />}
        body={w.emptyPoolBody}
        link={{ href: query.next_query ? queryHref(query.next_query) : JUDGING_HREF, text: w.emptyPoolLink }}
      />
    );
  } else {
    // A failed save sits at the top of the grade bar, so it sticks with it and stays in view after the advance.
    const failedAlert = failed !== null && (
      <Alert
        state="error"
        live="alert"
        action={
          <Button variant="secondary" onClick={() => { setFailed(null); void save(unsaved); }}>
            {copy.feedback.tryAgain}
          </Button>
        }
      >
        {fillText(w.saveFailed, { i: failed })}
      </Alert>
    );
    // Once you finish, the bar stays so you can change a grade until the other judge finishes (brief section 4.2).
    // From a 1024 px page area a failed save sits at the top of the sticky bar; below it, right after the panel's
    // heading, so it is in view after the page scrolls to the next passage.
    const gradeBar = passage && (
      <GradeBar
        sample={sample}
        n={at}
        chosen={grades[passage.passage_id] ?? null}
        locked={query.locked}
        mine={passage.my_grade ?? grades[passage.passage_id] ?? null}
        theirs={passage.other_grade}
        onGrade={grade}
        notice={(wide && failedAlert) || undefined}
        done={done === pool}
      />
    );
    main = (
      <>
        <p className="text-caption text-ink-muted">
          <Fill template={w.poolNote} slots={{ date: <Num date={query.query_date} /> }} />
        </p>
        <PassageMap open={mapOpen} onToggle={() => setMapOpen(!mapOpen)} count={pool} current={at} graded={graded} href={(n) => queryHref(query.query_id, n)} onChoose={(n) => show(n)} />
        {finished && !query.locked ? (
          <div className="flex flex-col gap-4" data-judging-finished="mine">
            <OutcomePanel ref={outcome} state="info" lead={fillText(w.finishedLead, { pool })} body={w.finishedBody} />
            <Next query={query} />
          </div>
        ) : null}
        {query.locked && (
          <div className="flex flex-col gap-4" data-judging-finished="both">
            {lockedWhileOpen && (
              <div ref={lockedAlert} tabIndex={-1} className="outline-none" data-locked-while-open>
                <Alert state="info" live="status">
                  {w.lockedWhileOpen}
                </Alert>
              </div>
            )}
            <OutcomePanel ref={outcome} state="info" lead={fillText(w.bothLead, { agree: query.agree ?? 0, pool })} body={w.bothBody} />
            <Differences query={query} />
            <Next query={query} />
          </div>
        )}
        {passage && (
          <section
            aria-labelledby={panelId}
            tabIndex={-1}
            onKeyDown={onKey}
            className="flex flex-col gap-3 outline-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
            data-judging-panel
          >
            <h2 id={panelId} ref={panelHeading} tabIndex={-1} className="scroll-mt-4 text-h2 text-ink-heading focus:outline-none">
              {fillText(w.panel, { i: at, pool })}
            </h2>
            {!wide && failedAlert}
            <PassageBlock evidence={evidenceOf(passage)} />
            {!wide && gradeBar}
            <dl className="mt-3 grid gap-x-4 gap-y-2 text-caption text-ink @md/page:grid-cols-[auto_1fr]">
              {(["answers", "partly", "not_relevant"] as Grade[]).map((key) => (
                <div key={key} className="contents">
                  <dt className="font-semibold">{w.grades[key]}</dt>
                  <dd className="text-ink-muted">{w.definitions[key]}</dd>
                </div>
              ))}
            </dl>
            <p className="text-caption text-ink-muted">{w.guidance}</p>
            {/* Locked, the keys grade nothing, so the line that names them goes. */}
            {!query.locked && <p className="hidden text-caption text-ink-muted @md/page:block">{w.keysNote}</p>}
            <div className="flex justify-between gap-4 text-small">
              {at > 1 ? (
                <TextLink href={queryHref(query.query_id, at - 1)} onClick={(event) => { event.preventDefault(); show(at - 1); }}>
                  {w.previous}
                </TextLink>
              ) : <span />}
              {at < pool ? (
                <TextLink href={queryHref(query.query_id, at + 1)} onClick={(event) => { event.preventDefault(); show(at + 1); }}>
                  {w.nextPassage}
                </TextLink>
              ) : <span />}
            </div>
            {/* Room above the sticky grade bar, so the last line never hides under it. A locked bar doesn't stick. */}
            {!query.locked && <div className="hidden h-24 @lg/page:block" aria-hidden="true" />}
          </section>
        )}
        {wide && gradeBar && (
          <div onKeyDown={onKey} className="contents">
            {gradeBar}
          </div>
        )}
      </>
    );
  }

  return (
    <div ref={desk} data-judging-query={query.query_id} className="flex flex-col gap-4">
      <Breadcrumb
        held
        trail={[{ text: copy.lessons.tabs.library, href: LESSONS_HREF }, { text: w.title, href: JUDGING_HREF }, { text: fillText(w.breadcrumb, { n: query.n }) }]}
        back={{ text: w.breadcrumbBack, href: JUDGING_HREF }}
      />
      {/* Scrolls out of view as the header sticks, which then takes its line. It sits on the header's top edge,
          12 px above where the flow puts it, since the header's negative margin moves the header up by that much. */}
      <div ref={top} aria-hidden="true" className={cx("-mb-4 h-0", !sample && "@lg/page:relative @lg/page:-top-3")} />
      {header}
      {main}
      <p role="status" className="clip-visually">
        {announced}
      </p>
    </div>
  );
}

function Next({ query }: { query: JudgingQuery }) {
  return query.next_query ? (
    <div className="flex flex-col gap-3 @md/page:flex-row @md/page:items-center @md/page:gap-6">
      <a href={queryHref(query.next_query)} className={PRIMARY_LINK}>
        {w.next}
      </a>
      <TextLink href={JUDGING_HREF}>{w.backToJudging}</TextLink>
    </div>
  ) : (
    <div className="flex flex-col gap-2">
      <p className="text-body text-ink">{fillText(w.afterLast, { total: query.total })}</p>
      <TextLink href={JUDGING_HREF}>{w.backToJudging}</TextLink>
    </div>
  );
}

// One query's loading state (the 32 brief, section 5.6): the header, the panel's heading and a passage block's frame,
// and the grade bar with its buttons held until the pool arrives, all as tall as the page they stand for.
export function JudgingQuerySkeleton({ n = 1, sample = false }: { n?: number; sample?: boolean }) {
  return (
    <div aria-busy="true" data-judging-query="loading" className={cx("flex flex-col gap-3", !sample && "min-h-svh")}>
      <p role="status" className="clip-visually">
        {w.loadingOne}
      </p>
      <SkeletonLine className="text-caption" width="w-[70%]" />
      <span className="flex flex-col text-h3">
        <SkeletonLine width="w-full" />
        <SkeletonLine width="w-3/5" />
      </span>
      <Skeleton className="h-2 w-60" radius="rounded-pill" />
      <SkeletonLine className="mt-3 text-h2" width="w-30" />
      <div className="rounded-md border border-line">
        <Skeleton className="h-8 w-full rounded-b-none" />
        <SkeletonText className="max-w-prose p-4 text-body" widths={["w-full", "w-full", "w-full", "w-full", "w-full", "w-3/5"]} />
      </div>
      <GradeBar sample={sample} n={n} chosen={null} locked={false} disabled onGrade={() => undefined} />
    </div>
  );
}

export function JudgingQueryPage({ queryId, search }: { queryId: string; search: string }) {
  const [load, retry] = useLoad<JudgingQuery>(`/api/judging/queries/${encodeURIComponent(queryId)}`);
  const asked = Number(new URLSearchParams(search).get("p") ?? "0");
  const trail = <Breadcrumb held trail={[{ text: copy.lessons.tabs.library, href: LESSONS_HREF }, { text: w.title, href: JUDGING_HREF }]} back={{ text: w.breadcrumbBack, href: JUDGING_HREF }} />;
  const denied = refusedAs(load, "not_a_judge");
  useEffect(() => {
    if (denied) setPageTitle(copy.pages.lessons.title);
  }, [denied]);
  let body: ReactNode;
  // A short answer holds a screen's height as the skeleton did, so the footer stays below the fold.
  const empty = (title: ReactNode, text: string, link: { href: string; text: string }) => (
    <div className="min-h-svh">
      {trail}
      <h1 tabIndex={-1} className="clip-visually">{w.breadcrumbBack}</h1>
      <EmptyState className="mt-6" title={title} body={text} link={link} />
    </div>
  );
  if (load.status === "loading") body = <>{trail}<JudgingQuerySkeleton n={asked >= 1 ? asked : 1} /></>;
  else if (load.status === "error") {
    if (refusedAs(load, "unknown_query")) body = empty(<Fill template={w.notFoundTitle} slots={{ id: <span className="font-mono font-medium wrap-anywhere">{queryId}</span> }} />, w.notFoundBody, { href: JUDGING_HREF, text: w.notFoundLink });
    else if (refusedAs(load, "not_assigned")) body = empty(w.notAssignedTitle, w.notAssignedBody, { href: JUDGING_HREF, text: w.notAssignedLink });
    else if (denied) {
      body = (
        <div className="min-h-svh">
          <h1 tabIndex={-1} className="text-h1 text-ink-heading focus:outline-none">{copy.pages.lessons.title}</h1>
          <p className="mt-2 max-w-prose text-body text-pretty text-ink-muted">{copy.pages.lessons.purpose}</p>
          <div className="mt-8">
            <NoAccess />
          </div>
        </div>
      );
    } else
      body = (
        <div className="min-h-svh">
          {trail}
          <h1 tabIndex={-1} className="clip-visually">{w.breadcrumbBack}</h1>
          <div className="mt-6">
            <LoadError error={load.error} message={w.errorOne} permission={w.permission} onRetry={retry} retrying={load.retrying} attempt={load.attempt} />
          </div>
        </div>
      );
  } else {
    const at = asked >= 1 && asked <= load.data.passages.length ? asked : undefined;
    body = <JudgingDesk query={load.data} initial={at ? { at } : undefined} />;
  }
  return <DocumentColumn>{body}</DocumentColumn>;
}
