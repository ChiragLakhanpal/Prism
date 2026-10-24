// All projects (the 10 brief, section 4), at /projects: every project Strata holds a record for, in
// the order the route gives (active ones first, then by name). Each project ID links to its page.
// The first 50 rows show; "Show 50 more" adds the next 50 and moves focus to the first new row's
// link. Search arrives with ticket 21 and Following with ticket 37.
import { useEffect, useState } from "react";
import { EmptyState } from "../components/Card";
import { Button } from "../components/Button";
import { EightColumns } from "../components/EightColumns";
import { Fill } from "../components/Fill";
import { LoadError } from "../components/LoadError";
import { PageHeader } from "../components/PageHeader";
import { Skeleton, SkeletonLine } from "../components/Skeleton";
import { Source } from "../components/Source";
import { Table, type Column, type Row } from "../components/Table";
import { TextLink } from "../components/TextLink";
import { copy } from "../copy";
import type { ProjectList } from "../lib/api";
import { formatDate, formatNumber } from "../lib/format";
import { useLoad } from "../lib/load";

const words = copy.projectsPage;
export const PAGE_SIZE = 50;

const columns: Column[] = [
  { key: "project", header: words.columns.project, width: "w-3/5" },
  { key: "country", header: words.columns.country },
  { key: "status", header: words.columns.status },
];

const blank = <span className="text-ink-muted">{copy.notInRecord}</span>;

// While the list loads, each Project cell holds a bar for the ID link and one for the name, so a
// skeleton row is as tall as a project's row (the link's 4 px padding is pulled up by -mt-1).
const PROJECT_SKELETON = (
  <>
    <span aria-hidden="true" className="-mt-1 flex h-7 items-center">
      <Skeleton className="h-[1em] w-16" />
    </span>
    <SkeletonLine className="text-small" width="w-3/5" />
  </>
);

export function ProjectsPage() {
  const [load, retry] = useLoad<ProjectList>("/api/projects");
  const [shown, setShown] = useState(PAGE_SIZE);
  const [moved, setMoved] = useState(false);

  // After "Show 50 more", the first new row's link takes focus, in whichever view shows.
  useEffect(() => {
    if (!moved) return;
    const first = Array.from(document.querySelectorAll<HTMLElement>(`[data-row="${shown - PAGE_SIZE}"]`)).find(
      (element) => element.getClientRects().length > 0,
    );
    first?.focus();
  }, [shown, moved]);

  let body;
  if (load.status === "loading") {
    body = (
      <>
        <Table
          title={words.tableTitle}
          level={2}
          count={{ noun: words.noun, total: 0 }}
          columns={columns}
          rowHeader="project"
          state={{ status: "loading", rows: 8, header: PROJECT_SKELETON }}
        />
        <p role="status" className="sr-only">
          {words.loading}
        </p>
      </>
    );
  } else if (load.status === "error") {
    body = (
      <EightColumns>
        <LoadError error={load.error} message={words.error} permission={words.permission} onRetry={retry} retrying={load.retrying} attempt={load.attempt} />
      </EightColumns>
    );
  } else if (load.data.total === 0) {
    body = (
      <EightColumns>
        <EmptyState title={words.emptyTitle} body={words.emptyBody} link={{ href: "/data", text: words.emptyLink }} />
      </EightColumns>
    );
  } else {
    const { rows: all, total, records_through: through } = load.data;
    const visible = all.slice(0, shown);
    const rows: Row[] = visible.map((project, index) => ({
      id: project.project_id,
      cells: {
        project: (
          <>
            <TextLink href={`/projects/${project.project_id}`} data-row={index} className="-mt-1 block w-fit font-mono font-medium">
              {project.project_id}
            </TextLink>
            <span className="block text-small text-ink">{project.project_name}</span>
          </>
        ),
        country: project.country ?? blank,
        status: project.status ?? blank,
      },
    }));
    body = (
      <>
        <Table
          title={words.tableTitle}
          level={2}
          count={{ noun: words.noun, total, from: 1, to: visible.length }}
          columns={columns}
          rowHeader="project"
          state={{ status: "ready", rows }}
        />
        {visible.length < all.length && (
          <Button
            className="mt-4"
            variant="secondary"
            onClick={() => {
              setShown(shown + PAGE_SIZE);
              setMoved(true);
            }}
          >
            {words.more(formatNumber(PAGE_SIZE, { compact: false }))}
          </Button>
        )}
        <Source className="mt-2">
          {through ? <Fill template={words.source} slots={{ date: formatDate(through) }} /> : words.sourceUndated}
        </Source>
      </>
    );
  }

  return (
    <div className="layout-grid">
      <div className="col-span-12 md:col-span-8">
        <PageHeader title={copy.pages.projects.title} purpose={copy.pages.projects.purpose} />
      </div>
      <div className="col-span-12 mt-6 lg:mt-8" data-projects-page={load.status}>
        {body}
      </div>
    </div>
  );
}
