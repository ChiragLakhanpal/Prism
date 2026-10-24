// The Lessons tab (ticket 29; the 29 design brief, sections 2.3 to 2.8 and 5.1 to 5.4), at /lessons and
// /lessons/review:
//
// - The frame: the h1 and brief 06's purpose, then, for lesson reviewers only, a row of sub-tabs, "Lessons" and
//   "Waiting for review ({waiting})". Everyone else sees no row, since a row of one tab offers no choice. The
//   viewer's roles (/api/lessons/me) load once a page load, so switching tabs never moves the row.
// - Lessons: the interim library, eight lesson cards a page, newest decision first (by date, never by use).
// - Waiting for review: the tab's purpose, the server's lead sentence, the quote check's caption, the rows
//   grouped "Waiting for you" and "With other reviewers", oldest first, and the decisions of the last 90 days.
//   Anyone who is not a lesson reviewer gets the no-access card (the route answers 403 not_a_reviewer).
//
// Every Lessons page keeps to columns 1 to 7 from a 1200 px window, so the evidence drawer opens into the
// free space and the column never moves (DESIGN.md section 4, Document column).
import { useEffect, useRef, useState, type ReactNode } from "react";
import { EmptyState } from "../components/Card";
import { Fill } from "../components/Fill";
import { LessonCard } from "../components/LessonCard";
import { Pagination, Sentence, fillText } from "../components/LessonParts";
import { QueueRow } from "../components/LessonReview";
import { LoadError } from "../components/LoadError";
import { Num } from "../components/Num";
import { PageHeader } from "../components/PageHeader";
import { Skeleton, SkeletonLine } from "../components/Skeleton";
import { Table, type Row as TableRow } from "../components/Table";
import { Tabs } from "../components/Tabs";
import { TextLink } from "../components/TextLink";
import { copy } from "../copy";
import { getJson } from "../lib/api";
import { formatNumber } from "../lib/format";
import { useStore } from "../lib/store";
import { address } from "../lib/router";
import { evidenceIn, visited as visitedStore } from "../lib/evidence";
import { useLoad, type Load } from "../lib/load";
import { createStore } from "../lib/store";
import { setPageTitle } from "../lib/title";
import { itemHref, LESSONS_HREF, pageHref, QUEUE_HREF, type Library, type Me, type Queue, type QueueRow as Row } from "../lib/lessons";
import { dataReadinessHref } from "../routes";
import { DocumentColumn } from "./DraftPage";

const words = copy.lessons;
const page = copy.pages.lessons;

// ── Who is viewing: loaded once a page load, refreshed after a save ─────

type MeState = { status: "loading" } | { status: "ready"; me: Me } | { status: "error" };
export const lessonsMe = createStore<MeState>({ status: "loading" });
let asked = false;

export async function refreshLessonsMe() {
  try {
    lessonsMe.set({ status: "ready", me: await getJson<Me>("/api/lessons/me") });
  } catch {
    lessonsMe.set((current) => (current.status === "ready" ? current : { status: "error" }));
  }
}

function useMe(): MeState {
  const me = useStore(lessonsMe);
  useEffect(() => {
    if (asked) return;
    asked = true;
    void refreshLessonsMe();
  }, []);
  return me;
}

// The tab the frame last showed, so switching tabs says which one shows (the 29 brief, section 5.1).
let lastTab: "library" | "review" | null = null;

export function LessonsFrame({ tabKey: tab, me, children }: { tabKey: "library" | "review"; me: MeState; children: ReactNode }) {
  const [announced, setAnnounced] = useState("");
  const reviewer = me.status === "ready" && me.me.tabs.includes("review");
  useEffect(() => {
    if (lastTab && lastTab !== tab) setAnnounced(tab === "library" ? words.tabs.showingLibrary : words.tabs.showingQueue);
    lastTab = tab;
  }, [tab]);
  const waiting = me.status === "ready" ? (me.me.waiting ?? 0) : 0;
  return (
    <DocumentColumn>
      <div data-lessons-frame={tab}>
        <PageHeader title={page.title} purpose={page.purpose} />
        {reviewer && (
          <div className="mt-6" data-lessons-tabs>
            <Tabs
              label={words.tabs.label}
              tabs={[
                { key: "library", label: words.tabs.library, href: LESSONS_HREF, current: tab === "library" },
                {
                  key: "review",
                  // Plain text, so the link's name reads "Waiting for review (3)" with no gaps around the number.
                  label: fillText(words.tabs.queue, { waiting: formatNumber(waiting, { compact: false }) }),
                  href: QUEUE_HREF,
                  current: tab === "review",
                },
              ]}
            />
          </div>
        )}
        <p role="status" className="clip-visually">
          {announced}
        </p>
        {/* Until the viewer's roles return, only the h1 and the purpose show, so the sub-tab row never pushes
            the content down (the 29 brief, section 5.1). */}
        {me.status !== "loading" && <div className={reviewer ? "mt-6 @md/page:mt-8" : "mt-8"}>{children}</div>}
      </div>
    </DocumentColumn>
  );
}

// ── The library ──────────────────────────────────────────────────────────

function LibrarySkeleton() {
  return (
    <div aria-busy="true" data-library="loading" className="flex flex-col gap-4">
      <p role="status" className="clip-visually">
        {words.library.loading}
      </p>
      <Skeleton className="h-[13px] w-80 max-w-full" />
      {[0, 1, 2].map((index) => (
        <div key={index} className="flex flex-col gap-3 rounded-md border border-line bg-surface p-4 @md/page:p-6">
          <Skeleton className="h-3 w-2/5" />
          <Skeleton className="h-[18px] w-4/5" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-3/5" />
          <div className="flex gap-2">
            <Skeleton className="h-8 w-20" radius="rounded-pill" />
            <Skeleton className="h-8 w-24" radius="rounded-pill" />
          </div>
          <Skeleton className="h-[13px] w-[70%]" />
        </div>
      ))}
    </div>
  );
}

export function LibraryList({ library, open = null, visited = new Set() }: { library: Library; open?: string | null; visited?: ReadonlySet<string> }) {
  const countRef = useRef<HTMLParagraphElement>(null);
  const count =
    library.total === 1
      ? words.library.countOne
      : library.from <= 1 && library.to >= library.total
        ? <Fill template={words.library.countAll} slots={{ total: <Num count={library.total} /> }} />
        : (
            <Fill
              template={words.library.countRange}
              slots={{ from: <Num value={library.from} options={{ compact: false }} />, to: <Num value={library.to} options={{ compact: false }} />, total: <Num value={library.total} options={{ compact: false }} /> }}
            />
          );
  return (
    <div data-library="ready" className="flex flex-col">
      <p ref={countRef} tabIndex={-1} data-lead className="text-caption text-ink-muted outline-none" data-numbers>
        {count}
      </p>
      <p className="mt-1 max-w-prose text-caption text-ink-muted">{words.sourcesNote}</p>
      <ul aria-label={words.library.list} className="mt-4 flex flex-col gap-4">
        {library.lessons.map((card) => (
          <li key={card.lesson_id}>
            <LessonCard card={card} canRecheck={library.can_recheck} open={open} visited={visited} />
          </li>
        ))}
      </ul>
      {library.pages > 1 && (
        <div className="mt-8">
          <Pagination page={library.page} pages={library.pages} href={(n) => pageHref(LESSONS_HREF, n)} />
        </div>
      )}
    </div>
  );
}

export function LibraryBody({ load, me, retry }: { load: Load<Library>; me: MeState; retry: () => void }) {
  const here = useStore(address);
  const seen = useStore(visitedStore);
  if (load.status === "loading") return <LibrarySkeleton />;
  if (load.status === "error") {
    return (
      <LoadError error={load.error} message={words.library.error} permission={words.library.permission} onRetry={retry} retrying={load.retrying} attempt={load.attempt} />
    );
  }
  const library = load.data;
  if (library.total === 0) {
    const waiting = me.status === "ready" && me.me.tabs.includes("review") && (me.me.waiting ?? 0) > 0;
    return (
      <EmptyState
        title={page.emptyTitle}
        body={page.emptyBody}
        link={waiting ? { href: QUEUE_HREF, text: words.library.reviewerLink } : { href: "/data", text: page.link }}
      />
    );
  }
  if (library.lessons.length === 0) {
    return (
      <EmptyState
        title={fillText(words.library.outOfRangeTitle, { page: library.page })}
        body={library.pages === 1 ? words.library.outOfRangeBodyOne : <Fill template={words.library.outOfRangeBody} slots={{ pages: <Num count={library.pages} /> }} />}
        link={{ href: LESSONS_HREF, text: words.library.firstPage }}
      />
    );
  }
  return <LibraryList library={library} open={evidenceIn(here.search)} visited={seen} />;
}

function pageOf(search: string): number {
  const asked = Number(new URLSearchParams(search).get("page") ?? "1");
  return Number.isInteger(asked) && asked >= 1 ? asked : 1;
}

export function LessonsPage({ search }: { search: string }) {
  const me = useMe();
  const [load, retry] = useLoad<Library>(`/api/lessons?page=${pageOf(search)}`);
  return (
    <LessonsFrame tabKey="library" me={me}>
      <LibraryBody load={load} me={me} retry={retry} />
    </LessonsFrame>
  );
}

// ── Waiting for review ───────────────────────────────────────────────────

function Group({ groupKey: group, rows }: { groupKey: "you" | "others"; rows: Row[] }) {
  if (rows.length === 0) return null;
  const id = `queue-${group}`;
  return (
    <section aria-labelledby={id} data-queue-group={group}>
      <h2 id={id} className="text-title text-ink-heading">
        {words.queue.groups[group]}
      </h2>
      <p className="mt-1 text-caption text-ink-muted">{words.queue.order}</p>
      <ul className="mt-4">
        {rows.map((row) => (
          <QueueRow key={row.item_id} row={row} />
        ))}
      </ul>
    </section>
  );
}

function Decided({ queue }: { queue: Queue }) {
  const decided = queue.decided;
  const q = words.queue;
  const title = <Fill template={q.decidedTitle} slots={{ days: <Num value={decided.window_days} options={{ compact: false }} /> }} />;
  if (decided.total === 0) {
    return (
      <section aria-labelledby="queue-decided" data-queue-decided="none">
        <h2 id="queue-decided" className="text-title text-ink-heading">
          {title}
        </h2>
        <p className="mt-4 text-body text-ink">
          <Fill template={q.decidedNone} slots={{ days: <Num value={decided.window_days} options={{ compact: false }} /> }} />
        </p>
      </section>
    );
  }
  const rows: TableRow[] = decided.rows.map((row) => ({
    id: row.item_id,
    cells: {
      lesson: (
        <span className="flex flex-col gap-0.5">
          <TextLink href={itemHref(row.item_id)}>{row.statement}</TextLink>
          <span className="text-caption text-ink-muted">
            <Fill template={q.project} slots={{ name: row.project_name ?? "", pid: <span className="font-mono">{row.pid}</span> }} />
          </span>
        </span>
      ),
      outcome: row.version !== null ? fillText(q.outcomes[row.outcome] ?? row.outcome, { version: row.version }) : (q.outcomes[row.outcome] ?? row.outcome),
      decided: <Num date={row.decided_on} style="table" />,
      days:
        row.days_from_publication !== null ? (
          <Num
            value={row.days_from_publication}
            options={{ compact: false }}
          />
        ) : (
          <span className="text-ink-muted">{q.recheckDays}</span>
        ),
    },
  }));
  return (
    <div data-queue-decided="table">
      <Table
        level={2}
        title={title}
        count={{ noun: q.decidedNoun, one: q.decidedNounOne, total: decided.total, from: decided.from, to: decided.to }}
        rowHeader="lesson"
        columns={[
          { key: "lesson", header: q.columns.lesson, width: "w-[46%]" },
          { key: "outcome", header: q.columns.outcome, width: "w-[22%]", short: true },
          { key: "decided", header: q.columns.decided, width: "w-[14%]", short: true },
          {
            key: "days",
            header: (
              <span className="flex flex-col">
                <span>{q.columns.days}</span>
                <span className="text-caption font-normal text-ink-muted">{q.daysDefinition}</span>
              </span>
            ),
            numeric: true,
            width: "w-[18%]",
          },
        ]}
        state={{ status: "ready", rows }}
        source={q.decidedSource}
      />
      {decided.pages > 1 && (
        <div className="mt-6">
          <Pagination page={decided.page} pages={decided.pages} href={(n) => pageHref(QUEUE_HREF, n)} />
        </div>
      )}
    </div>
  );
}

export function QueueBody({ queue }: { queue: Queue }) {
  const q = words.queue;
  const empty = queue.groups.you.length + queue.groups.others.length === 0;
  const purpose = (
    <Fill template={q.purpose} slots={{ limit: <Num value={queue.limit_days} options={{ compact: false }} />, regions: queue.regions.join(copy.list.and) }} />
  );
  const link = dataReadinessHref(queue.check.readiness.sources, queue.check.readiness.from);
  return (
    <div data-queue="ready" className="flex flex-col">
      <p className="max-w-prose text-body text-ink-muted">{purpose}</p>
      {empty ? (
        <EmptyState className="mt-6" title={q.emptyTitle} body={q.emptyBody} link={{ href: LESSONS_HREF, text: q.emptyLink }} />
      ) : (
        <p tabIndex={-1} className="mt-4 text-title text-ink-heading outline-none @md/page:mt-6 @md/page:text-h3" data-queue-lead>
          {queue.lead && <Sentence segments={queue.lead} />}
        </p>
      )}
      <p className="mt-2 max-w-prose text-caption text-ink-muted" data-quote-check>
        <Sentence segments={queue.check.segments} /> <TextLink href={link}>{q.checkLink}</TextLink>
      </p>
      {!empty && (
        <div className="mt-8 flex flex-col gap-8 @md/page:mt-12 @md/page:gap-12">
          <Group groupKey="you" rows={queue.groups.you} />
          <Group groupKey="others" rows={queue.groups.others} />
        </div>
      )}
      <div className="mt-8 @md/page:mt-12">
        <Decided queue={queue} />
      </div>
    </div>
  );
}

function QueueSkeleton() {
  return (
    <div aria-busy="true" data-queue="loading" className="flex flex-col">
      <p role="status" className="clip-visually">
        {words.queue.loading}
      </p>
      <SkeletonLine width="w-full" className="text-body" />
      <SkeletonLine width="w-4/5" className="text-body" />
      <div className="mt-4 flex flex-col gap-2 @md/page:mt-6">
        <Skeleton className="h-5 w-full" />
        <Skeleton className="h-5 w-[70%]" />
      </div>
      <Skeleton className="mt-2 h-[13px] w-3/5" />
      <Skeleton className="mt-8 h-[18px] w-40 @md/page:mt-12" />
      {[0, 1, 2].map((index) => (
        <div key={index} className="flex flex-col gap-1 border-t-2 border-line py-4">
          <Skeleton className="h-[14px] w-2/5" />
          <Skeleton className="h-[18px] w-[90%]" />
          <Skeleton className="h-[13px] w-[70%]" />
          <Skeleton className="h-6 w-30" radius="rounded-pill" />
          <Skeleton className="h-[14px] w-3/5" />
        </div>
      ))}
    </div>
  );
}

export function NoAccess() {
  const q = words.queue;
  return <EmptyState title={q.noAccessTitle} body={q.noAccessBody} link={{ href: LESSONS_HREF, text: q.noAccessLink }} />;
}

export function QueueView({ load, retry }: { load: Load<Queue>; retry: () => void }) {
  if (load.status === "loading") return <QueueSkeleton />;
  if (load.status === "error") {
    if (load.error?.status === 403 && (load.error.body as { code?: string }).code === "not_a_reviewer") return <NoAccess />;
    return <LoadError error={load.error} message={words.queue.error} permission={words.queue.permission} onRetry={retry} retrying={load.retrying} attempt={load.attempt} />;
  }
  return <QueueBody queue={load.data} />;
}

export function QueuePage({ search }: { search: string }) {
  const me = useMe();
  const [load, retry] = useLoad<Queue>(`/api/lessons/review?page=${pageOf(search)}`);
  // Someone the roles file does not name sees the frame with no sub-tab row, and the page's title as the
  // library's, since this page is not theirs to open.
  const denied = load.status === "error" && load.error?.status === 403;
  useEffect(() => {
    if (denied) setPageTitle(page.title);
  }, [denied]);
  return (
    <LessonsFrame tabKey="review" me={denied ? { status: "error" } : me}>
      <QueueView load={load} retry={retry} />
    </LessonsFrame>
  );
}
