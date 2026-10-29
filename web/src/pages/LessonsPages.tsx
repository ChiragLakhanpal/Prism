// The Lessons tab (ticket 29; the 29 design brief, sections 2.3 to 2.8 and 5.1 to 5.4), at /lessons and
// /lessons/review:
//
// - The frame: the page head. Lessons, the library, states the section's purpose under its h1. The reviewer pages,
//   Waiting for review, Passage reports and Judging, are the sidebar's items under Lessons for the roles that have
//   them, each with its count in a badge hidden at zero (ticket 102; web/src/components/sections.ts), so the frame
//   draws no sub-tab row; each names itself in its h1, and its own purpose opens its body, 12 px under the h1. When a
//   page's one read fails, its error alert sits in the page's alert slot and the frame draws only the h1.
// - Lessons: ticket 39's page (web/src/pages/LessonsTab.tsx), which opens on what came in since your last visit.
// - Waiting for review: the page's purpose, the server's lead sentence, the quote check's caption, the rows
//   grouped "Waiting for you" and "With other reviewers", oldest first, and the decisions of the last 90 days.
//   Anyone who is not a lesson reviewer gets the no-access card under the Lessons h1 (the route answers 403
//   not_a_reviewer), since this page is not theirs to open.
//
// The Lessons pages are wide (the shell redesign plan, 8.3): all 12 columns, with each sentence kept to the width of
// prose. When the drawer opens, the page narrows and keeps its left edge.
import { useEffect, type ReactNode } from "react";
import { EmptyState } from "../components/Card";
import { Fill, Joined } from "../components/Fill";
import { Sentence, fillText } from "../components/LessonParts";
import { Pagination } from "../components/Pagination";
import { QueueRow } from "../components/LessonReview";
import { LoadError } from "../components/LoadError";
import { Num } from "../components/Num";
import { PageAlert } from "../components/PageAlert";
import { PageHead } from "../components/PageHead";
import { Skeleton, SkeletonLine, SkeletonText } from "../components/Skeleton";
import { Table, type Row as TableRow } from "../components/Table";
import { TextLink } from "../components/TextLink";
import { copy } from "../copy";
import { useLoad, type Load } from "../lib/load";
import { useLessonsMe } from "../lib/lessonsMe";
import { setPageTitle } from "../lib/title";
import { itemHref, LESSONS_HREF, pageHref, QUEUE_HREF, type Me, type Queue, type QueueRow as Row } from "../lib/lessons";
import { dataReadinessHref } from "../routes";

const words = copy.lessons;

// The pages the frame holds: the library, and the three reviewer pages the sidebar lists under Lessons.
export type LessonsPageKey = "lessons" | "lessonsQueue" | "lessonsReports" | "lessonsJudging";

export function LessonsFrame({ pageKey, failed = false, children }: { pageKey: LessonsPageKey; failed?: boolean; children: ReactNode }) {
  const named = copy.pages[pageKey];
  const library = pageKey === "lessons";
  // The wide layout (plan 8.3; ticket 110): all 12 columns, with each sentence kept to the width of prose, so the
  // margins even out beside the rail. When the drawer opens, the page narrows and keeps its left edge. The title has no
  // purpose under it (ticket 126).
  return (
    <div className="layout-grid">
      <div data-lessons-frame={pageKey} className="col-span-12 min-w-0">
        <PageHead title={named.title} />
        {/* A failed read's alert went to the alert slot, so nothing else draws here. */}
        {failed ? children : <div className={library ? "mt-8" : "mt-3"}>{children}</div>}
      </div>
    </div>
  );
}

// ── The library ──────────────────────────────────────────────────────────

// A line of skeleton that shows only below a page area of 768 px, where the words it stands for wrap once more.
const NARROW_ONLY = "@md/page:hidden";

// One lesson card's frame, block for block: the eyebrow, the statement, the quote, the chips, the evidence
// badge, the Tags, the decided and rules lines, the source line and the re-check button.
function CardFrame() {
  return (
    <div className="flex flex-col gap-3 rounded-md border border-line bg-surface p-4 @md/page:p-6" data-skeleton-card>
      <SkeletonLine className="text-label" width="w-2/5" />
      <span className="-mt-1 flex flex-col text-h2">
        <SkeletonLine width="w-4/5" />
        <SkeletonLine width="w-1/2" className={NARROW_ONLY} />
      </span>
      <span className="flex max-w-prose flex-col text-body">
        <SkeletonLine width="w-full" />
        <SkeletonLine width="w-full" />
        <SkeletonLine width="w-3/5" />
        <SkeletonLine width="w-full" className={NARROW_ONLY} />
        <SkeletonLine width="w-2/5" className={NARROW_ONLY} />
      </span>
      <div className="flex gap-2">
        <Skeleton className="h-8 w-20" radius="rounded-pill" />
        <Skeleton className="h-8 w-28" radius="rounded-pill" />
      </div>
      <Skeleton className="h-[30px] w-40" radius="rounded-pill" />
      <div className="flex flex-wrap gap-2">
        <Skeleton className="h-6 w-56 max-w-full" radius="rounded-md" />
        <Skeleton className="h-6 w-24" radius="rounded-md" />
      </div>
      <span className="flex max-w-prose flex-col text-caption">
        <SkeletonLine width="w-full" />
        <SkeletonLine width="w-3/5" />
        <SkeletonLine width="w-full" className={NARROW_ONLY} />
        <SkeletonLine width="w-1/2" className={NARROW_ONLY} />
      </span>
      <SkeletonText className="max-w-prose text-caption" widths={["w-full", "w-2/5"]} />
      <Skeleton className="h-11 w-40" radius="rounded-sm" />
    </div>
  );
}

// The library zone's body while it loads: the count line and three cards' frames. The sources note above the zones is
// static copy, so the page draws it for real (LessonsTab.tsx).
export function LibrarySkeleton() {
  return (
    <div aria-busy="true" data-library="loading" className="flex flex-col">
      <p role="status" className="clip-visually">
        {words.library.loading}
      </p>
      <SkeletonLine className="text-caption" width="w-80 max-w-full" />
      <div className="mt-4 flex flex-col gap-4">
        {[0, 1, 2].map((index) => (
          <CardFrame key={index} />
        ))}
      </div>
    </div>
  );
}

function pageOf(search: string): number {
  const asked = Number(new URLSearchParams(search).get("page") ?? "1");
  return Number.isInteger(asked) && asked >= 1 ? asked : 1;
}

// ── Waiting for review ───────────────────────────────────────────────────

function Group({ groupKey: group, rows }: { groupKey: "you" | "others"; rows: Row[] }) {
  if (rows.length === 0) return null;
  const id = `queue-${group}`;
  return (
    <section aria-labelledby={id} data-queue-group={group}>
      <h2 id={id} className="text-h2 text-ink-heading">
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
        <h2 id="queue-decided" className="text-h2 text-ink-heading">
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
          {/* The link sits inside a line of its own, so its padding takes no room and its first line is level with the
              Outcome's and Decided's (ticket 59). */}
          <span>
            <TextLink href={itemHref(row.item_id)}>{row.statement}</TextLink>
          </span>
          <span className="text-caption text-ink-muted">
            <Fill template={q.project} slots={{ name: row.project_name ?? "", pid: <span className="font-mono">{row.pid}</span> }} />
          </span>
        </span>
      ),
      outcome: row.version !== null ? fillText(q.outcomes[row.outcome] ?? row.outcome, { version: row.version }) : (q.outcomes[row.outcome] ?? row.outcome),
      // A date keeps to one line (DESIGN.md section 5, Tables).
      decided: (
        <span className="whitespace-nowrap">
          <Num date={row.decided_on} style="table" />
        </span>
      ),
      // The knowledge loop's leading indicator, checkable as the decided record's is: its tooltip says what
      // it counts from and to.
      days:
        row.days_from_publication !== null ? (
          <Num
            value={row.days_from_publication}
            options={{ compact: false }}
            check={
              row.published_on
                ? { tooltip: <Fill template={copy.lessons.review.decidedTooltip} slots={{ published: <Num date={row.published_on} />, date: <Num date={row.decided_on} /> }} /> }
                : undefined
            }
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
        // As cards, each card shows the days' column by its name alone, and the definition ends the count
        // line's row once (DESIGN.md section 5, Tables).
        cardsNote={q.daysCards}
        columns={[
          // The days' head takes a quarter, so its name and its definition each keep to one line at 1440 px.
          { key: "lesson", header: q.columns.lesson, width: "w-[40%]" },
          { key: "outcome", header: q.columns.outcome, width: "w-[20%]", short: true },
          { key: "decided", header: q.columns.decided, width: "w-[16%]", short: true },
          {
            key: "days",
            header: (
              <span className="flex flex-col">
                <span>{q.columns.days}</span>
                <span className="text-caption font-normal text-ink-muted">{q.daysDefinition}</span>
              </span>
            ),
            cardHeader: q.columns.days,
            numeric: true,
            width: "w-[24%]",
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

// The tab's purpose names the day limit and the viewer's regions: "... for South Asia, East Asia and Pacific and
// Africa ...". The frame's /api/lessons/me gives both, so it shows while the queue loads, and the queue gives
// them again with its answer.
function QueuePurpose({ limitDays, regions }: { limitDays: number; regions: string[] }) {
  return (
    <p className="max-w-prose text-body text-ink-muted" data-queue-purpose>
      <Fill template={words.queue.purpose} slots={{ limit: <Num value={limitDays} options={{ compact: false }} />, regions: <Joined items={regions} /> }} />
    </p>
  );
}

export function QueueBody({ queue }: { queue: Queue }) {
  const q = words.queue;
  const empty = queue.groups.you.length + queue.groups.others.length === 0;
  const link = dataReadinessHref(queue.check.readiness.sources, queue.check.readiness.from);
  return (
    <div data-queue="ready" className="flex flex-col">
      <QueuePurpose limitDays={queue.limit_days} regions={queue.regions} />
      {empty ? (
        <EmptyState className="mt-6" title={q.emptyTitle} body={q.emptyBody} link={{ href: LESSONS_HREF, text: q.emptyLink }} />
      ) : (
        // At most 65 characters a line, as the purpose above it wraps (ticket 91's critique; ticket 102).
        <p tabIndex={-1} className="mt-4 max-w-prose text-lead text-pretty text-ink-heading outline-none @md/page:mt-6" data-queue-lead>
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

// The queue's skeleton: the tab's purpose for real when the viewer's roles have loaded (static copy and two
// values the frame already holds), then the lead, the quote check's caption and three rows.
export function QueueSkeleton({ me }: { me?: Me | null }) {
  return (
    <div aria-busy="true" data-queue="loading" className="flex flex-col">
      <p role="status" className="clip-visually">
        {words.queue.loading}
      </p>
      {me && me.limit_days !== null && me.regions.length > 0 ? (
        <QueuePurpose limitDays={me.limit_days} regions={me.regions} />
      ) : (
        <SkeletonText className="max-w-prose text-body" widths={["w-full", "w-full", "w-full", "w-full", "w-full", "w-2/5"]} />
      )}
      {/* Each part in the text style of what it stands for, so each line is as tall as the line it holds. The lines
          each part takes by the page area were measured on the fixture's queue at 320 to 1440 px (ticket 59): the
          lead takes a third line below 26rem, the quote check's caption a fourth below 26rem and a fifth below 22.5rem;
          a row's statement takes two lines below 37.5rem, and its source sentence two below 43rem and three below
          22.5rem. */}
      <span className="mt-4 flex max-w-prose flex-col text-lead @md/page:mt-6">
        <SkeletonLine width="w-full" />
        <SkeletonLine width="w-3/5" />
        <SkeletonLine width="w-2/5" className="@[26rem]/page:hidden" />
      </span>
      <span className="mt-2 flex max-w-prose flex-col text-caption">
        <SkeletonLine width="w-full" />
        <SkeletonLine width="w-full" />
        <SkeletonLine width="w-1/3" />
        <SkeletonLine width="w-1/2" className="@[26rem]/page:hidden" />
        <SkeletonLine width="w-1/3" className="@[22.5rem]/page:hidden" />
      </span>
      <div className="mt-8 @md/page:mt-12">
        <SkeletonLine className="text-h2" width="w-40" />
        <SkeletonLine className="mt-1 text-caption" width="w-24" />
        <div className="mt-4">
          {[0, 1, 2].map((index) => (
            <div key={index} className="border-t-2 border-line py-4" data-skeleton-row>
              {/* Every bar in the row keeps to the prose width, as the lead's do, since a row's lines end there on a
                  wide page (the critique of round 1; the design review of round 2, follow-up 4). */}
              <div className="flex max-w-prose flex-col gap-1">
                <SkeletonLine className="text-small" width="w-2/5" />
                <span className="flex flex-col text-h2">
                  <SkeletonLine width="w-[90%]" />
                  <SkeletonLine width="w-1/2" className="@[37.5rem]/page:hidden" />
                </span>
                <span className="flex flex-col text-caption">
                  <SkeletonLine width="w-full" />
                  <SkeletonLine width="w-3/5" className="@[43rem]/page:hidden" />
                  <SkeletonLine width="w-2/5" className="@[22.5rem]/page:hidden" />
                </span>
                <div className="py-1">
                  <Skeleton className="h-[30px] w-40" radius="rounded-pill" />
                </div>
                <SkeletonLine className="text-small" width="w-3/5" />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export function NoAccess() {
  const q = words.queue;
  return <EmptyState title={q.noAccessTitle} body={q.noAccessBody} link={{ href: LESSONS_HREF, text: q.noAccessLink }} />;
}

const notAReviewer = (load: Load<Queue>) => load.status === "error" && load.error?.status === 403 && (load.error.body as { code?: string }).code === "not_a_reviewer";

// A failed read's alert goes to the page's alert slot (PageAlert.tsx); in the design gallery it stays in place.
export function QueueView({ load, retry, me = null }: { load: Load<Queue>; retry: () => void; me?: Me | null }) {
  if (load.status === "loading") return <QueueSkeleton me={me} />;
  if (load.status === "error") {
    if (notAReviewer(load)) return <NoAccess />;
    return (
      <PageAlert>
        <LoadError error={load.error} message={words.queue.error} permission={words.queue.permission} onRetry={retry} retrying={load.retrying} attempt={load.attempt} />
      </PageAlert>
    );
  }
  return <QueueBody queue={load.data} />;
}

export function QueuePage({ search }: { search: string }) {
  // Who is viewing (lib/lessonsMe.ts): loaded once a page load, refreshed after a save.
  const me = useLessonsMe();
  const [load, retry] = useLoad<Queue>(`/api/lessons/review?page=${pageOf(search)}`);
  // Someone the roles file does not name sees the Lessons h1 and its purpose over the no-access card, and the
  // page's title as the library's, since this page is not theirs to open.
  const denied = notAReviewer(load);
  useEffect(() => {
    if (denied) setPageTitle(copy.pages.lessons.title);
  }, [denied]);
  return (
    <LessonsFrame pageKey={denied ? "lessons" : "lessonsQueue"} failed={load.status === "error" && !denied}>
      <QueueView load={load} retry={retry} me={me.status === "ready" ? me.me : null} />
    </LessonsFrame>
  );
}
