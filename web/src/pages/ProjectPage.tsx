// A project's page (the 10 brief, section 3), at /projects/:pid and /projects/:pid/procurement: the
// header (the project's name, its ID in Roboto Mono, country, status and implementing agencies, as
// labelled pairs), a row of section tabs showing only the tabs that are built (Procurement, until
// ticket 21 adds Summary), and the Procurement tab: each implementing agency's Procurement Plan
// versions, newest first, in the order the route gives. A version Strata read links to its plan
// check; a version it did not read is plain text marked "Not read".
//
// States: loading, populated, an agency with no plan, a project with no plans, a project Strata has
// no record of, a service that didn't answer, and an account that can't read Strata's tables.
import { useEffect, useRef, type ReactNode } from "react";
import { Breadcrumb } from "../components/Breadcrumb";
import { EmptyState } from "../components/Card";
import { Fill } from "../components/Fill";
import { LoadError } from "../components/LoadError";
import { Num } from "../components/Num";
import { Skeleton, SkeletonLine } from "../components/Skeleton";
import { Table, type Column, type Row } from "../components/Table";
import { Tabs } from "../components/Tabs";
import { TextLink } from "../components/TextLink";
import { copy } from "../copy";
import type { Agency, ProjectPage as Page } from "../lib/api";
import { formatDate } from "../lib/format";
import { useLoad } from "../lib/load";

const words = copy.projectPage;
const plans = copy.procurement;

const columns: Column[] = [
  { key: "version", header: plans.columns.version, width: "w-1/2" },
  { key: "disclosed", header: plans.columns.disclosed },
  { key: "activities", header: plans.columns.activities, numeric: true },
];

const mono = (text: ReactNode) => <span className="font-mono">{text}</span>;

function Pairs({ pairs }: { pairs: { label: ReactNode; value: ReactNode; wide?: boolean }[] }) {
  return (
    <dl className="mt-4 grid grid-cols-2 gap-x-6 gap-y-2 md:flex md:flex-wrap">
      {pairs.map((pair, index) => (
        <div key={index} className={pair.wide ? "col-span-2" : undefined}>
          <dt className="text-caption text-ink-muted">{pair.label}</dt>
          <dd className="text-small text-ink">{pair.value}</dd>
        </div>
      ))}
    </dl>
  );
}

function AgencyPlans({ agency, pid, through }: { agency: Agency; pid: string; through: string | null }) {
  if (agency.version_count === 0) {
    return (
      <section data-agency={agency.agency_id}>
        <h3 className="text-title text-ink-heading">{agency.implementing_agency}</h3>
        <p className="mt-2 text-small text-ink-muted">{plans.agencyEmpty}</p>
      </section>
    );
  }
  const rows: Row[] = agency.versions.map((version) => {
    const label = plans.versionLink(formatDate(version.plan_date, { style: "table" }));
    return {
      id: version.document_id,
      cells: {
        version: (
          <>
            {version.read ? (
              <TextLink href={`/projects/${pid}/procurement/${agency.agency_id}/${version.plan_date}`}>{label}</TextLink>
            ) : (
              label
            )}
            {version.is_latest && (
              <>
                {" "}
                <span className="ml-2 text-caption text-ink-muted">{plans.latest}</span>
              </>
            )}
          </>
        ),
        disclosed: version.disclosed_on ? <Num date={version.disclosed_on} style="table" /> : copy.notInRecord,
        activities:
          version.read && version.activities !== null ? (
            <Num value={version.activities} options={{ compact: false }} />
          ) : (
            <span className="text-ink-muted">{plans.notRead}</span>
          ),
      },
    };
  });
  return (
    <section data-agency={agency.agency_id}>
      <Table
        title={agency.implementing_agency}
        level={3}
        count={{ noun: plans.noun, one: plans.nounOne, total: agency.version_count }}
        columns={columns}
        rowHeader="version"
        state={{ status: "ready", rows }}
        source={
          through ? (
            <Fill template={plans.source} slots={{ pid: mono(pid), date: formatDate(through) }} />
          ) : (
            <Fill template={plans.sourceUndated} slots={{ pid: mono(pid) }} />
          )
        }
      />
      {agency.versions.some((version) => !version.read) && <p className="mt-2 max-w-prose text-caption text-ink-muted">{plans.unreadNote}</p>}
    </section>
  );
}

export function ProjectPage({ pid }: { pid: string }) {
  const [load, retry] = useLoad<Page>(`/api/projects/${encodeURIComponent(pid)}`);
  const title = useRef<HTMLHeadingElement>(null);
  const idText = mono(pid);

  useEffect(() => {
    if (load.status === "ready" && load.afterRetry) title.current?.focus();
  }, [load]);

  // The server's 404 for a project it has no record of; any other 404 is a service that didn't answer.
  const notFound = load.status === "error" && load.error?.status === 404 && load.error.body.code === "unknown_project";
  const data = load.status === "ready" ? load.data : null;
  const projectsCrumb = { text: copy.breadcrumb.projects, href: "/projects" };
  const current = data ? (
    <Fill template={copy.breadcrumb.project} slots={{ name: data.project.project_name, pid: idText }} />
  ) : load.status === "loading" ? (
    <Skeleton className="inline-block h-[1em] w-[200px] align-middle" />
  ) : (
    <Fill template={copy.breadcrumb.projectId} slots={{ pid: idText }} />
  );

  if (notFound) {
    return (
      <div className="layout-grid" data-project-page="not-found">
        <div className="col-span-12 md:col-span-8">
          <Breadcrumb trail={[{ text: copy.breadcrumb.projects }]} />
          <h1 ref={title} tabIndex={-1} className="mt-4 text-h1 text-ink-heading focus:outline-none">
            <Fill template={words.notFoundTitle} slots={{ pid: idText }} />
          </h1>
          <p className="mt-2 max-w-prose text-body text-ink-muted">{words.notFoundBody}</p>
          <p className="mt-4 text-body">
            <TextLink href="/projects">{words.notFoundLink}</TextLink>
          </p>
        </div>
      </div>
    );
  }

  const project = data?.project;
  const agencies = project
    ? [{ label: project.implementing_agencies.length > 1 ? words.label.agencies : words.label.agency, value: project.implementing_agencies.join(words.agencyJoin), wide: true }]
    : [];
  const header =
    load.status === "loading" ? (
      <div aria-hidden="true" className="mt-4 grid grid-cols-2 gap-x-6 gap-y-2 md:flex md:flex-wrap">
        {[0, 1, 2, 3].map((index) => (
          <div key={index} className="w-32">
            <SkeletonLine className="text-caption" width="w-3/5" />
            <SkeletonLine className="text-small" width="w-full" />
          </div>
        ))}
      </div>
    ) : project ? (
      <Pairs
        pairs={[
          { label: words.label.id, value: <span className="font-mono font-medium">{project.project_id}</span> },
          { label: words.label.country, value: project.country ?? copy.notInRecord },
          { label: words.label.status, value: project.status ?? copy.notInRecord },
          ...(project.implementing_agencies.length > 0 ? agencies : []),
        ]}
      />
    ) : null;

  let tab: ReactNode;
  if (load.status === "loading") {
    tab = (
      <>
        <Table title="" level={3} count={{ noun: plans.noun, total: 0 }} columns={columns} rowHeader="version" state={{ status: "loading", rows: 3 }} />
        <p role="status" className="sr-only">
          {words.loading}
        </p>
      </>
    );
  } else if (load.status === "error") {
    tab = (
      <LoadError error={load.error} message={words.error} permission={words.permission} onRetry={retry} retrying={load.retrying} attempt={load.attempt} />
    );
  } else if (load.data.agencies.every((agency) => agency.version_count === 0)) {
    tab = (
      <EmptyState
        level={3}
        title={plans.projectEmptyTitle}
        body={plans.projectEmptyBody}
        link={{ href: "/data", text: plans.projectEmptyLink }}
      />
    );
  } else {
    tab = (
      <div className="flex flex-col gap-10">
        {load.data.agencies.map((agency) => (
          <AgencyPlans key={agency.agency_id} agency={agency} pid={pid} through={load.data.documents_through} />
        ))}
      </div>
    );
  }

  return (
    <div className="layout-grid" data-project-page={load.status}>
      <div className="col-span-12 md:col-span-8">
        <Breadcrumb trail={[projectsCrumb, { text: current }]} />
        <h1 ref={title} tabIndex={-1} className="mt-4 text-h1 text-ink-heading focus:outline-none">
          {project ? project.project_name : load.status === "loading" ? <Skeleton className="h-[1.2em] w-3/5" /> : <Fill template={copy.pages.project.title} slots={{ pid: idText }} />}
        </h1>
        <p className="mt-2 max-w-prose text-body text-ink-muted">{copy.pages.project.purpose}</p>
        {header}
      </div>
      <div className="col-span-12 mt-6">
        <Tabs label={words.sections} tabs={[{ key: "procurement", label: words.tab.procurement, href: `/projects/${pid}/procurement`, current: true }]} />
      </div>
      <div className="col-span-12 mt-6 md:col-span-8">
        <h2 className="text-h2 text-ink-heading">{plans.title}</h2>
        <p className="mt-2 max-w-prose text-body text-ink">{plans.purpose}</p>
      </div>
      {/* Three columns read best at the prose width, so the version tables keep to columns 1 to 8. */}
      <div className="col-span-12 mt-6 lg:col-span-8">{tab}</div>
    </div>
  );
}
