// All projects (the 10 brief, section 4, and the 21 brief, section 8), at /projects?q=&page=: every
// project Strata holds a record for, 20 a page, in the order the route gives (an exact project ID first,
// then active projects, then by name). A List search filters them on the server as you type, by part of a
// name, a project ID with or without its P, or a country; the route counts the matches and the page's
// range, so the screen counts nothing. Each project ID is a ProjectId link to its page.
//
// States: loading, populated, searching (the rows stay, dimmed after 400 ms), no match (the empty-state
// card in place of the table and the pages), no records at all, a service that didn't answer, and an
// account that can't read Strata's tables.
import { useEffect, useId, useRef, useState } from "react";
import { EmptyState } from "../components/Card";
import { EightColumns } from "../components/EightColumns";
import { Fill } from "../components/Fill";
import { ListSearch } from "../components/ListSearch";
import { LoadError } from "../components/LoadError";
import { PageHeader } from "../components/PageHeader";
import { Pagination } from "../components/Pagination";
import { ProjectId } from "../components/ProjectId";
import { Skeleton, SkeletonLine, SkeletonText } from "../components/Skeleton";
import { Source } from "../components/Source";
import { countText, Table, type Column, type Count, type Row } from "../components/Table";
import { copy } from "../copy";
import type { ProjectList } from "../lib/api";
import { formatDate } from "../lib/format";
import { usePagedList } from "../lib/paged";
import { staffRole } from "../lib/following";
import { useStore } from "../lib/store";
import { ProjectsTabs } from "../components/ProjectsTabs";
import { AgencyProjects } from "../components/AgencyProjects";
import { appliedView } from "../lib/view";

const words = copy.projectsPage;
const NAMES = { query: "q", page: "page" };

const columns: Column[] = [
  { key: "project", header: words.columns.project, width: "w-3/5" },
  { key: "country", header: words.columns.country, short: true },
  { key: "status", header: words.columns.status, short: true },
];

const blank = <span className="text-ink-muted">{copy.notInRecord}</span>;

// While the list loads, each Project cell holds a bar for the ID link and bars for the name, so a
// skeleton row is as tall as a project's row (the link's 4 px padding is pulled up by -mt-1). Most
// names take two lines below 1200 px and one from it.
const PROJECT_SKELETON = (
  <>
    <span aria-hidden="true" className="-mt-1 flex h-7 items-center">
      <Skeleton className="h-[1em] w-16" />
    </span>
    <SkeletonText className="text-small @xl/page:hidden" widths={["w-full", "w-2/5"]} />
    <SkeletonLine className="hidden text-small @xl/page:flex" width="w-3/5" />
  </>
);

export function ProjectsPage() {
  const list = usePagedList<ProjectList>("/api/projects", NAMES);
  const shownView = useStore(appliedView);
  // The implementing agency view the server applied: an officer's own view, or the staff preview of it.
  const agencyView = shownView?.applied.view === "piu";
  const staff = useStore(staffRole) === true && !shownView?.applied.preview;
  const { load, shown, query } = list;
  const headingId = useId();
  // The count line, said once each time a search settles, through a polite status.
  const [said, setSaid] = useState("");
  const settled = useRef<string | null>(null);
  const count = (data: ProjectList): Count => ({ noun: words.noun, one: words.nounOne, total: data.total, from: data.first, to: data.last });

  useEffect(() => {
    if (load.status !== "ready") return;
    const key = `${load.data.query}|${load.data.page}`;
    if (settled.current !== null && settled.current !== key) setSaid(load.data.total === 0 ? words.noMatchTitle : countText(count(load.data)));
    settled.current = key;
  }, [load]);

  let body;
  if (load.status === "error") {
    body = (
      <EightColumns>
        <LoadError error={load.error} message={words.error} permission={words.permission} onRetry={list.retry} retrying={load.retrying} attempt={load.attempt} />
      </EightColumns>
    );
  } else if (!shown) {
    body = (
      <>
        <Table
          title={words.tableTitle}
          labelledBy={headingId}
          level={2}
          count={{ noun: words.noun, total: 0 }}
          columns={columns}
          rowHeader="project"
          state={{ status: "loading", rows: 8, header: PROJECT_SKELETON, shortTitle: true }}
        />
        <p role="status" className="sr-only">
          {words.loading}
        </p>
      </>
    );
  } else if (shown.total === 0 && !shown.query) {
    body = (
      <EightColumns>
        <EmptyState title={words.emptyTitle} body={words.emptyBody} link={{ href: "/data", text: words.emptyLink }} />
      </EightColumns>
    );
  } else if (shown.total === 0) {
    body = (
      <EightColumns>
        <EmptyState level={3} title={words.noMatchTitle} body={words.noMatchBody} link={{ href: "/projects", text: words.noMatchLink }} />
      </EightColumns>
    );
  } else {
    const rows: Row[] = shown.rows.map((project, index) => ({
      id: project.project_id,
      cells: {
        project: (
          <>
            <ProjectId pid={project.project_id} className="-mt-1 block w-fit" />
            <span className="block text-small text-ink" data-row={index}>
              {project.project_name}
            </span>
          </>
        ),
        country: project.country ?? blank,
        status: project.status ?? blank,
      },
    }));
    const through = shown.records_through;
    body = (
      <>
        <Table
          title={words.tableTitle}
          labelledBy={headingId}
          level={2}
          count={count(shown)}
          countLead
          busy={list.waiting && list.searching ? words.searching : undefined}
          columns={columns}
          rowHeader="project"
          state={{ status: "ready", rows }}
        />
        <Pagination className="mt-4" label={words.pages} page={shown.page} pages={shown.pages} href={list.href} />
        <Source className="mt-2">{through ? <Fill template={words.source} slots={{ date: formatDate(through) }} /> : words.sourceUndated}</Source>
      </>
    );
  }

  return (
    <div className="layout-grid">
      <div className="col-span-12">
        <div className="@md/page:w-2/3">
          <PageHeader title={copy.pages.projects.title} purpose={staff ? copy.pages.following.purpose : copy.pages.projects.purpose} />
        </div>
        {/* World Bank staff get the Projects sub-tabs, Following and All projects (ticket 37). */}
        {staff && <ProjectsTabs following={false} />}
      </div>
      {/* Your agency's projects, in the implementing agency view (ticket 40): an officer's own, and the staff preview's. */}
      {agencyView && (
        <div className="col-span-12 @md/page:col-span-8">
          <AgencyProjects asOf={shownView?.asof.applied ?? null} />
        </div>
      )}
      <section aria-labelledby={headingId} className="col-span-12 mt-8 @lg/page:mt-8" data-projects-page={load.status}>
        {/* With the sub-tabs showing, the selected one already names the list, so its heading is for screen readers. */}
        <h2 id={headingId} className={staff ? "sr-only" : "text-title text-ink-heading"}>
          {words.tableTitle}
        </h2>
        <div className="layout-grid mt-3">
          <ListSearch className="col-span-12 @md/page:col-span-6" label={words.search.label} hint={words.search.hint} value={query} onSearch={list.search} />
        </div>
        <div className="mt-4">{body}</div>
        <p role="status" className="sr-only">
          {said}
        </p>
      </section>
    </div>
  );
}
