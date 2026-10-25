// The Drafts tab (the 35 brief, section 5.8), at /drafts: your team's drafts in three groups, To check,
// Checked and Exported, always in that order and each with its count line, so the page keeps its shape.
// Rows are newest first by their last change, 20 at a time. Each row is the draft's title as a link,
// then plain sentences, and on your own drafts to check, how many of their sources you opened, the list
// that empties as you work. Your own discarded drafts sit in a fold under the groups, since only you can
// restore them. With no drafts at all, brief 06's empty-state card takes the groups' place.
import { useEffect, useId, useRef, useState } from "react";
import { Button } from "../components/Button";
import { EmptyState } from "../components/Card";
import { Fill } from "../components/Fill";
import { LoadError } from "../components/LoadError";
import { PageHeader } from "../components/PageHeader";
import { Skeleton, SkeletonLine } from "../components/Skeleton";
import { TextLink } from "../components/TextLink";
import { ProjectId } from "../components/ProjectId";
import { copy } from "../copy";
import type { DraftGroup, DraftList, DraftRow as Row } from "../lib/drafts";
import { draftHref, storeFailed } from "../lib/drafts";
import { formatCount, formatDate, formatNumber } from "../lib/format";
import { useLoad } from "../lib/load";

const words = copy.draft.tab;
const page = copy.pages.drafts;
// The previews say the same for every kind; they read the one kind there is today.
const PREVIEW = copy.draft.kinds.review_notes;
const GROUPS: DraftGroup[] = ["to_check", "checked", "exported"];
const PAGE_SIZE = 20;
const whole = (value: number) => formatNumber(value, { compact: false });
const short = (iso: string) => formatDate(iso.slice(0, 10), { style: "table" });
const day = (iso: string) => formatDate(iso.slice(0, 10));

// Who acted, and when: the check and the export each keep their own time, so a restored draft still says
// when it was checked.
function lineTwo(row: Row): string {
  const author = row.author.name ?? "";
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

export function DraftRow({ row, linkRef }: { row: Row; linkRef?: (element: HTMLAnchorElement | null) => void }) {
  const subject = row.subject;
  const kind = copy.draft.kinds[row.kind];
  return (
    <li className="border-t border-line p-4 first:border-t-0" data-draft-row={row.draft_id}>
      <TextLink ref={linkRef} href={draftHref(row.draft_id)} className="text-body font-semibold">
        {row.kind === "mission_brief"
          ? kind.rowTitle(subject.project_name, "")
          : kind.rowTitle(subject.implementing_agency, short(subject.plan_date))}
      </TextLink>
      <p className="mt-1 text-small text-ink-muted">
        {row.kind === "mission_brief" ? (
          // The title already names the project (the 37 brief, section 9.8): "P156634, Kenya. Drafted by you on ...".
          <Fill template={subject.country ? words.projectCountry : words.projectOnly} slots={{ pid: <ProjectId pid={subject.project_id} />, country: subject.country ?? "" }} />
        ) : (
          <>
            <Fill template={words.project} slots={{ name: subject.project_name, pid: <ProjectId pid={subject.project_id} /> }} />{" "}
            {row.state !== "discarded" && <>{kind.rowNotes(row.notes, formatCount(row.notes, { capital: true }))} </>}
          </>
        )}{" "}
        {lineTwo(row)}
      </p>
      {row.opened && (
        <p className="mt-1 text-small text-ink" data-numbers>
          {words.opened(whole(row.opened.count), whole(row.opened.of))}
        </p>
      )}
    </li>
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
    <section aria-labelledby={headingId} data-draft-group={group}>
      <h2 id={headingId} className="text-title text-ink-heading">
        {words.groups[group]}
      </h2>
      {count > 0 ? (
        <>
          <p className="mt-1 text-caption text-ink-muted">{words.count(count, formatCount(count, { capital: true }))}</p>
          <ul className="mt-2 rounded-md border border-line bg-surface">
            {rows.slice(0, shown).map((row, index) => (
              <DraftRow key={row.draft_id} row={row} linkRef={index === focusFrom.current ? (element) => (first.current = element) : undefined} />
            ))}
          </ul>
          {rows.length > shown && (
            <Button
              className="mt-3"
              variant="secondary"
              onClick={() => {
                focusFrom.current = shown;
                setShown(shown + PAGE_SIZE);
              }}
            >
              {words.more(whole(PAGE_SIZE))}
            </Button>
          )}
        </>
      ) : (
        <p className="mt-1 text-small text-ink-muted">{words.empty[group]}</p>
      )}
    </section>
  );
}

function Discarded({ rows, count }: { rows: Row[]; count: number }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  const sentence = useId();
  return (
    <div data-discarded-fold className="text-small">
      <div className="flex flex-wrap items-center gap-x-4">
        <p id={sentence} className="text-ink-muted">
          {words.discardedFold(count, formatCount(count))}
        </p>
        <Button variant="ghost" flush onPage aria-expanded={open} aria-controls={id} aria-describedby={sentence} onClick={() => setOpen(!open)}>
          {open ? words.hideDiscarded(count) : words.showDiscarded(count)}
        </Button>
      </div>
      <ul id={id} hidden={!open} className="mt-2 rounded-md border border-line bg-surface">
        {rows.map((row) => (
          <DraftRow key={row.draft_id} row={row} />
        ))}
      </ul>
    </div>
  );
}

export function DraftsList({ list }: { list: DraftList }) {
  if (list.total === 0) {
    return <EmptyState title={page.emptyTitle} body={page.emptyBody} link={{ href: "/packages", text: page.link }} />;
  }
  return (
    <div className="flex flex-col gap-8">
      {GROUPS.map((group) => (
        <Group key={group} group={group} rows={list.groups[group]} count={list.counts[group]} />
      ))}
      {list.discarded_count > 0 && <Discarded rows={list.discarded} count={list.discarded_count} />}
    </div>
  );
}

function Loading() {
  return (
    <div aria-busy="true" className="flex flex-col gap-8" data-drafts-loading>
      <p role="status" className="sr-only">
        {words.loading}
      </p>
      {GROUPS.map((group) => (
        <section key={group}>
          <h2 className="text-title text-ink-heading">{words.groups[group]}</h2>
          <SkeletonLine className="mt-1 text-caption" width="w-40" />
          {group === "to_check" && (
            <div className="mt-2 rounded-md border border-line bg-surface">
              {[0, 1].map((index) => (
                <div key={index} className="h-16 border-t border-line p-4 first:border-t-0">
                  <Skeleton className="h-4 w-3/5" />
                  <Skeleton className="mt-2 h-3 w-4/5" />
                </div>
              ))}
            </div>
          )}
        </section>
      ))}
    </div>
  );
}

export function DraftsPage({ search }: { search: string }) {
  const view = new URLSearchParams(search).get("view");
  return (
    <div className="layout-grid">
      <div className="col-span-12 min-w-0 @lg/page:col-span-8" data-drafts-page>
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
