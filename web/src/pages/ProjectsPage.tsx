// All projects (the 10 brief, section 4, and the 21 brief, section 8), at /projects?q=&page=: every
// project Strata holds a record for, 20 a page, in the order the route gives (an exact project ID first,
// then active projects, then by name). A List search filters them on the server as you type, by part of a
// name, a project ID with or without its P, or a country; the route counts the matches and the page's
// range, so the screen counts nothing. Each project ID is a ProjectId link to its page.
//
// Ticket 99 (the shell redesign; DESIGN.md section 5, Task zone and Tables): the list is one panel named "All
// projects", which holds the search, the count line, the table, the pages and, in its foot strip, the source. A project's
// name wraps in full however long it is (P180287's 104 characters), and the rows turn to cards below a page area of
// 34rem. Following and All projects are the sidebar's items under Projects, so the page has no row of its own to switch.
//
// States: loading, populated, searching (the rows stay at full contrast and the count line says it is
// searching), no match (the panel keeps its name and the search keeps the query, and the no-match sentence, its body
// and "Show all projects" take the list's place, with no count line, table or pages), no records at all (a row with
// one sentence and one link, since there is nothing to search), a service that didn't answer and an account that can't
// read Strata's tables (the panel keeps its name and its search, and the alert takes the list's place).
import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { EmptyState } from "../components/Card";
import { Fill } from "../components/Fill";
import { FootStrip } from "../components/FootStrip";
import { ListSearch } from "../components/ListSearch";
import { LoadError } from "../components/LoadError";
import { PageHeader } from "../components/PageHeader";
import { Pagination } from "../components/Pagination";
import { ProjectId } from "../components/ProjectId";
import { Skeleton, SkeletonLine, SkeletonText } from "../components/Skeleton";
import { Source } from "../components/Source";
import { countSaid, Table, type Column, type Count, type Row } from "../components/Table";
import { TaskZone } from "../components/TaskZone";
import { TextLink } from "../components/TextLink";
import { copy } from "../copy";
import type { ProjectList } from "../lib/api";
import { formatDate, formatNumber } from "../lib/format";
import { usePagedList } from "../lib/paged";
import { useStore } from "../lib/store";
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
const whole = (value: number) => formatNumber(value, { compact: false });

// While the list loads, each Project cell holds the ID link's 24 px box and bars for the name, so a skeleton row is as
// tall as a project's row. Most names take two lines below a page area of 1200 px and one from it.
const PROJECT_SKELETON = (
  <>
    <span aria-hidden="true" className="flex h-6 items-center">
      <Skeleton className="h-[1em] w-16" />
    </span>
    <SkeletonText className="mt-1 text-small @xl/page:hidden" widths={["w-full", "w-2/5"]} />
    <SkeletonLine className="mt-1 hidden text-small @xl/page:flex" width="w-3/5" />
  </>
);

export function ProjectsPage() {
  const list = usePagedList<ProjectList>("/api/projects", NAMES);
  const shownView = useStore(appliedView);
  // The implementing agency view the server applied: an officer's own view, or the staff preview of it.
  const agencyView = shownView?.applied.view === "piu";
  const { load, shown, query } = list;
  const headingId = useId();
  // The count line, said once each time a search settles, through a polite status.
  const [said, setSaid] = useState("");
  const settled = useRef<string | null>(null);
  // One page of more reads as a range in words ("Showing 1 to 20 of 93 projects"); all of them, as the Table says it.
  const count = (data: ProjectList): Count => {
    const range = data.first > 1 || data.last < data.total;
    return {
      noun: words.noun,
      one: words.nounOne,
      total: data.total,
      text: range ? words.countRange(whole(data.first), whole(data.last), whole(data.total)) : undefined,
    };
  };

  useEffect(() => {
    if (load.status !== "ready") return;
    const key = `${load.data.query}|${load.data.page}`;
    if (settled.current !== null && settled.current !== key) setSaid(load.data.total === 0 ? words.noMatchTitle : countSaid(count(load.data)));
    settled.current = key;
  }, [load]);

  const search = <ListSearch className="@md/page:w-1/2" label={words.search.label} value={query} onSearch={list.search} />;
  const source = (through: string | null) => (
    <FootStrip>
      <Source>{through ? <Fill template={words.source} slots={{ date: formatDate(through) }} /> : words.sourceUndated}</Source>
    </FootStrip>
  );
  // The zone's parts under its name: the body with the search (and whatever takes the list's place), then the table,
  // the pages and the foot strip.
  const panel = (body: ReactNode, rest: ReactNode = null) => (
    <TaskZone
      panel
      name={words.tableTitle}
      headingId={headingId}
      sectionKey="projects"
      marks={{ "data-projects-page": load.status }}
      className="col-span-12 mt-8"
      live={
        <p role="status" className="sr-only">
          {said}
        </p>
      }
    >
      <div data-zone-body>
        {search}
        {body}
      </div>
      {rest}
    </TaskZone>
  );

  let zone: ReactNode;
  if (load.status === "error") {
    zone = panel(<LoadError error={load.error} message={words.error} permission={words.permission} onRetry={list.retry} retrying={load.retrying} attempt={load.attempt} />);
  } else if (!shown) {
    zone = panel(
      <p role="status" className="sr-only">
        {words.loading}
      </p>,
      <>
        <Table
          title={words.tableTitle}
          labelledBy={headingId}
          level={2}
          // All projects is a paged list, so its first page's count line holds its place while it loads (ticket 126:
          // a list that shows every row has none).
          count={{ noun: words.noun, total: 0, from: 1, to: 1 }}
          columns={columns}
          rowHeader="project"
          cardsBelow="list"
          inPanel
          state={{ status: "loading", rows: 8, header: PROJECT_SKELETON, shortTitle: true }}
        />
        <FootStrip>
          <SkeletonLine className="text-caption" width="w-2/5" />
        </FootStrip>
      </>,
    );
  } else if (shown.total === 0 && !shown.query) {
    // Nothing to search yet: one sentence and one link, as a row on the page grey (DESIGN.md section 1, principle 7).
    zone = (
      <TaskZone
        name={words.tableTitle}
        state="empty"
        sectionKey="projects"
        marks={{ "data-projects-page": load.status }}
        className="col-span-12 mt-8"
        summary={
          <>
            <p className="text-pretty">
              {words.emptyTitle} {words.emptyBody}
            </p>
            <p className="mt-2">
              <TextLink href="/data">{words.emptyLink}</TextLink>
            </p>
          </>
        }
      />
    );
  } else if (shown.total === 0) {
    zone = panel(<EmptyState bare level={3} title={words.noMatchTitle} body={words.noMatchBody} link={{ href: "/projects", text: words.noMatchLink }} />, source(shown.records_through));
  } else {
    const rows: Row[] = shown.rows.map((project) => ({
      id: project.project_id,
      cells: {
        project: (
          <>
            {/* The P-code's link is a 24 px box (WCAG 2.5.8), and the name wraps in full under it, however long. */}
            <ProjectId pid={project.project_id} className="flex h-6 w-fit items-center" />
            <span className="mt-1 block text-small text-ink" data-project-name={project.project_id}>
              {project.project_name}
            </span>
          </>
        ),
        country: project.country ?? blank,
        status: project.status ?? blank,
      },
    }));
    zone = panel(
      null,
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
          cardsBelow="list"
          inPanel
          state={{ status: "ready", rows }}
        />
        {shown.pages > 1 && (
          <div data-zone-pager>
            <Pagination label={words.pages} page={shown.page} pages={shown.pages} href={list.href} />
          </div>
        )}
        {source(shown.records_through)}
      </>,
    );
  }

  return (
    <div className="layout-grid">
      <div className="col-span-12">
        <div className="@md/page:w-2/3">
          <PageHeader title={copy.pages.projects.title} />
        </div>
      </div>
      {/* Your agency's projects, in the implementing agency view (ticket 40): an officer's own, and the staff preview's. */}
      {agencyView && (
        <div className="col-span-12 @md/page:col-span-8">
          <AgencyProjects asOf={shownView?.asof.applied ?? null} />
        </div>
      )}
      {zone}
    </div>
  );
}
