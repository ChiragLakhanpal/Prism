// The Drafts list (the 35 brief, section 5.8; DESIGN.md section 5, Drafts list; ticket 103), at /drafts: your team's
// drafts in one panel holding three groups, To check, Checked and Exported, always in that order, so the page keeps its
// shape. Each group is an h2 with its count line after it and its rows, newest first by their last change, 20 at a
// time. Each row is the draft's title as a link, then its project and the drafted, checked or exported line in small,
// then its notes and, on your own drafts to check, how many of their sources you opened, in caption. Your own discarded
// drafts fold under the groups, inside the panel, since only you can restore them. With no drafts at all, a Task zone
// row in the panel's place says so and links to Packages; a failed load is the error alert in the panel's place.
import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { Button } from "../components/Button";
import { EmptyState } from "../components/Card";
import { Fill } from "../components/Fill";
import { LoadError } from "../components/LoadError";
import { PageHeader } from "../components/PageHeader";
import { Skeleton, SkeletonLine } from "../components/Skeleton";
import { TaskZone } from "../components/TaskZone";
import { TextLink } from "../components/TextLink";
import { ProjectId } from "../components/ProjectId";
import { Tag } from "../components/LessonParts";
import { copy } from "../copy";
import { cx } from "../lib/cx";
import { isPpsdKind } from "../lib/drafts";
import type { DraftGroup, DraftList, DraftRow as Row } from "../lib/drafts";
import { draftHref, storeFailed } from "../lib/drafts";
import { formatCount, formatDate, formatNumber } from "../lib/format";
import { useLoad } from "../lib/load";
import { draftTitle } from "../lib/lessonsPage";

const words = copy.draft.tab;
const page = copy.pages.drafts;
// The previews say the same for every kind; they read the one kind there is today.
const PREVIEW = copy.draft.kinds.review_notes;
const GROUPS: DraftGroup[] = ["to_check", "checked", "exported"];
const PAGE_SIZE = 20;
const whole = (value: number) => formatNumber(value, { compact: false });
const day = (iso: string) => formatDate(iso.slice(0, 10));
// The panel's sides: 24 px from a 48rem window, 16 px below it, for the group heads, the rows and the fold alike.
const SIDES = "px-4 md:px-6";
// A row in the panel: a line over it, 12 px above its title and 16 px under its last line.
const PANEL_ROW = cx("pt-3 pb-4", SIDES);

// Who acted, and when: the check and the export each keep their own time, so a restored draft still says
// when it was checked.
function lineTwo(row: Row): string {
  const author = row.author.name ?? "";
  // A draft the seed command set up (ticket 41): no person drafted it, so the row says Strata set it up.
  if (row.example && row.state === "draft") return copy.home.exampleSetUp(day(row.created_at));
  const checked = row.checked ?? row.changed;
  const exported = row.exported ?? row.changed;
  switch (row.state) {
    case "draft":
      return row.author.you ? words.draftedYou(day(row.created_at)) : words.draftedOther(author, day(row.created_at));
    case "checked":
      return checked.you ? words.checkedYou(day(checked.at)) : words.checkedOther(checked.by ?? author, day(checked.at));
    case "exported":
      return exported.you ? words.exportedYou(day(exported.at)) : words.exportedOther(exported.by ?? author, day(exported.at));
    default:
      return words.discardedYou(day(row.changed.at));
  }
}

// The row's project: a mission brief's title already names it, so its line gives the P-code and the country (the 37
// brief, section 9.8); suggested PPSD rows name the package's project, or say the package came from a sentence.
function ProjectLine({ row }: { row: Row }) {
  const subject = row.subject;
  if (row.kind === "mission_brief") {
    return (
      <Fill template={subject.country ? words.projectCountry : words.projectOnly} slots={{ pid: <ProjectId pid={subject.project_id} />, country: subject.country ?? "" }} />
    );
  }
  if (isPpsdKind(row.kind) && !subject.project_id) return <>{words.packageNoProject}</>;
  return <Fill template={words.project} slots={{ name: subject.project_name, pid: <ProjectId pid={subject.project_id} /> }} />;
}

// The notes a row counts: review notes their notes, suggested PPSD rows their rows (ticket 36). A mission brief and a
// Project Paper summary have fixed parts, and a discarded draft counts none.
function notesOf(row: Row): number | null {
  if (row.state === "discarded" || row.kind === "mission_brief" || row.kind === "project_paper") return null;
  if (isPpsdKind(row.kind)) return row.progress ? row.progress.rows : null;
  return row.notes;
}

// Home's Waiting for you lists the same rows in its side panel (ticket 98), with its own sides (className).
export function DraftRow({ row, linkRef, className = "p-4 first:border-t-0" }: {
  row: Row;
  linkRef?: (element: HTMLAnchorElement | null) => void;
  className?: string;
}) {
  const kind = copy.draft.kinds[row.kind];
  const notes = notesOf(row);
  const progress = row.state !== "discarded" ? row.progress : undefined;
  // The caption line's sentences, in order: the notes, the owners set and rows rated, then the sources you opened.
  const parts: ReactNode[] = [];
  if (notes !== null) parts.push(kind.rowNotes(notes, formatCount(notes, { capital: true })));
  // Suggested PPSD rows say how many owners are set, and in the Long Form how many rows are rated, from the copy file's
  // one owner count (ticket 36; tickets 35's Drafts tab and 41's Home read it).
  if (progress) parts.push(copy.ppsd.progressCount(whole(progress.owners_set), whole(progress.total)));
  if (progress?.form === "long") parts.push(copy.ppsd.progressRated(whole(progress.rated), whole(progress.total)));
  if (row.opened) parts.push(words.opened(whole(row.opened.count), whole(row.opened.of)));
  return (
    <li className={cx("border-t border-line", className)} data-draft-row={row.draft_id}>
      <TextLink ref={linkRef} href={draftHref(row.draft_id)} className="text-body font-semibold">
        {draftTitle(row.kind, row.subject as unknown as Record<string, string | null>)}
      </TextLink>
      {row.example && (
        <span className="ml-2 inline-block align-middle">
          <Tag>{copy.home.example}</Tag>
        </span>
      )}
      <p className="mt-1 text-small text-ink" data-row-line>
        <ProjectLine row={row} /> {lineTwo(row)}
      </p>
      {parts.length > 0 && (
        <p className="mt-1 text-caption text-ink-muted" data-numbers>
          {parts.map((part, index) => (
            <span key={index}>
              {index > 0 && " "}
              {part}
            </span>
          ))}
        </p>
      )}
    </li>
  );
}

// A group's head: its name, then its count line on the same line where it fits.
function GroupHead({ id, name, count }: { id?: string; name: string; count: ReactNode }) {
  return (
    <div className={cx("flex flex-wrap items-baseline gap-x-3 gap-y-1 pt-4 pb-2", SIDES)}>
      <h2 id={id} className="text-h2 text-ink-heading">
        {name}
      </h2>
      {count}
    </div>
  );
}

function Group({ group, rows, count }: { group: DraftGroup; rows: Row[]; count: number }) {
  const [shown, setShown] = useState(PAGE_SIZE);
  const first = useRef<HTMLAnchorElement | null>(null);
  const focusFrom = useRef<number | null>(null);
  const headingId = useId();
  useEffect(() => {
    if (focusFrom.current !== null) first.current?.focus();
    focusFrom.current = null;
  }, [shown]);
  return (
    <section aria-labelledby={headingId} data-draft-group={group} className="border-t border-line first:border-t-0">
      <GroupHead
        id={headingId}
        name={words.groups[group]}
        count={
          count > 0 && (
            <p className="text-caption text-ink-muted" data-group-count>
              {words.count(count, formatCount(count, { capital: true }))}
            </p>
          )
        }
      />
      {count > 0 ? (
        <>
          <ul>
            {rows.slice(0, shown).map((row, index) => (
              <DraftRow
                key={row.draft_id}
                row={row}
                className={PANEL_ROW}
                linkRef={index === focusFrom.current ? (element) => (first.current = element) : undefined}
              />
            ))}
          </ul>
          {rows.length > shown && (
            <div className={cx("pb-4", SIDES)}>
              <Button
                variant="secondary"
                onClick={() => {
                  focusFrom.current = shown;
                  setShown(shown + PAGE_SIZE);
                }}
              >
                {words.more(whole(PAGE_SIZE))}
              </Button>
            </div>
          )}
        </>
      ) : (
        <p className={cx("pb-4 text-small text-ink-muted", SIDES)}>{words.empty[group]}</p>
      )}
    </section>
  );
}

function Discarded({ rows, count }: { rows: Row[]; count: number }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  const sentence = useId();
  return (
    <div data-discarded-fold className="border-t border-line text-small">
      <div className={cx("flex flex-wrap items-center gap-x-3 gap-y-1 py-3", SIDES)}>
        <p id={sentence} className="text-ink">
          {words.discardedFold(count, formatCount(count))}
        </p>
        <Button variant="ghost" flush onPage aria-expanded={open} aria-controls={id} aria-describedby={sentence} onClick={() => setOpen(!open)}>
          {open ? words.hideDiscarded(count) : words.showDiscarded(count)}
        </Button>
      </div>
      <ul id={id} hidden={!open}>
        {rows.map((row) => (
          <DraftRow key={row.draft_id} row={row} className={PANEL_ROW} />
        ))}
      </ul>
    </div>
  );
}

// The panel that holds the groups and the fold, named for screen readers, since its groups carry the headings.
function Panel({ children, busy }: { children: ReactNode; busy?: boolean }) {
  return (
    <section aria-label={words.panelLabel} aria-busy={busy || undefined} data-drafts-panel="" className="rounded-md border border-line bg-surface">
      {children}
    </section>
  );
}

export function DraftsList({ list }: { list: DraftList }) {
  if (list.total === 0) {
    // Nothing to check yet: the first-person sentence and its one link, as a row on the page grey (plan 8.5).
    return (
      <TaskZone
        name={page.emptyTitle}
        state="empty"
        sectionKey="drafts"
        marks={{ "data-empty-state": "" }}
        summary={
          <>
            <p>{page.emptyBody}</p>
            <p className="mt-2">
              <TextLink href="/packages">{page.link}</TextLink>
            </p>
          </>
        }
      />
    );
  }
  return (
    <Panel>
      {GROUPS.map((group) => (
        <Group key={group} group={group} rows={list.groups[group]} count={list.counts[group]} />
      ))}
      {list.discarded_count > 0 && <Discarded rows={list.discarded} count={list.discarded_count} />}
    </Panel>
  );
}

// While the list loads: the panel with its three real group names over static bars, and two rows to check.
function Loading() {
  return (
    <div data-drafts-loading>
      <p role="status" className="sr-only">
        {words.loading}
      </p>
      <Panel busy>
        {GROUPS.map((group) => (
          <div key={group} className="border-t border-line first:border-t-0">
            <GroupHead name={words.groups[group]} count={<SkeletonLine className="text-caption" width="w-20" />} />
            {group === "to_check" &&
              [0, 1].map((index) => (
                <div key={index} className={cx("border-t border-line", PANEL_ROW)}>
                  <Skeleton className="h-4 w-3/5" />
                  <Skeleton className="mt-2 h-3 w-4/5" />
                  <Skeleton className="mt-2 h-3 w-2/5" />
                </div>
              ))}
          </div>
        ))}
      </Panel>
    </div>
  );
}

// The Drafts list takes the wide layout (plan 8.3; ticket 110): all 12 columns, so the margins even out beside the rail.
export function DraftsPage({ search }: { search: string }) {
  const view = new URLSearchParams(search).get("view");
  return (
    <div className="layout-grid">
      <div className="col-span-12 min-w-0" data-drafts-page>
        <PageHeader title={page.title} purpose={page.purpose} />
        <div className="mt-6 @lg/page:mt-8">
          {view === "piu" ? (
            <EmptyState title={PREVIEW.previewPiuTitle} body={PREVIEW.previewPiuBody} />
          ) : view === "public" ? (
            <EmptyState title={copy.draft.page.publicTitle} body={copy.draft.page.publicBody} />
          ) : (
            <TeamDrafts />
          )}
        </div>
      </div>
    </div>
  );
}

function TeamDrafts() {
  const [load, retry] = useLoad<DraftList>("/api/drafts");
  if (load.status === "loading") return <Loading />;
  if (load.status === "error") {
    return (
      <LoadError
        error={load.error}
        message={storeFailed(load.error) ? words.draftStore : words.error}
        permission={words.permission}
        onRetry={retry}
        retrying={load.retrying}
        attempt={load.attempt}
      />
    );
  }
  return <DraftsList list={load.data} />;
}
