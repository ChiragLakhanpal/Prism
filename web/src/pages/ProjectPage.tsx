// A project's page (the 10 brief, section 3), at /projects/:pid and /projects/:pid/procurement: the
// header (the project's name, its ID in Roboto Mono, country, status and implementing agencies, as
// labelled pairs), a row of section tabs showing only the tabs that are built (Procurement, until
// ticket 21 adds Summary), and the Procurement tab: each implementing agency's Procurement Plan
// versions, newest first, in the order the route gives. A version Strata read links to its plan
// check; a version it did not read is plain text marked "Not read".
//
// States: loading, populated, an agency with no plan, a project with no plans, a project Strata has
// no record of, a service that didn't answer, and an account that can't read Strata's tables.
import { useEffect, useId, useLayoutEffect, useRef, useState, type ReactNode } from "react";
import { Breadcrumb } from "../components/Breadcrumb";
import { Button } from "../components/Button";
import { EmptyState } from "../components/Card";
import { EightColumns } from "../components/EightColumns";
import { Fill } from "../components/Fill";
import { LoadError } from "../components/LoadError";
import { Num } from "../components/Num";
import { Skeleton, SkeletonLine, SkeletonText } from "../components/Skeleton";
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

const mono = (text: ReactNode) => <span className="font-mono font-medium">{text}</span>;

// The header's labelled pairs. The short ones share a row; a wide one (the agencies) takes a row of
// its own, so the header has the same shape however many agencies a project names.
type Pair = { label: ReactNode; value: ReactNode; wide?: boolean };

function Pairs({ pairs, hidden }: { pairs: Pair[]; hidden?: boolean }) {
  return (
    <dl aria-hidden={hidden || undefined} className="mt-4 grid grid-cols-2 gap-x-6 gap-y-2 md:flex md:flex-wrap">
      {pairs.map((pair, index) => (
        <div key={index} className={pair.wide ? "col-span-2 min-w-0 md:basis-full" : undefined}>
          <dt className="text-caption text-ink-muted">{pair.label}</dt>
          {pair.value}
        </div>
      ))}
    </dl>
  );
}

const value = (text: ReactNode) => <dd className="text-small text-ink">{text}</dd>;

// The agencies keep to two lines. When the names need more, "Show all agencies" follows them; it
// shows only while the two lines hide a name, measured again whenever the list's width changes.
function Agencies({ names }: { names: string[] }) {
  const id = useId();
  const list = useRef<HTMLElement>(null);
  const [open, setOpen] = useState(false);
  const [hides, setHides] = useState(false);
  useLayoutEffect(() => {
    const element = list.current;
    if (!element || open) return;
    const measure = () => setHides(element.scrollHeight > element.clientHeight + 1);
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(element);
    return () => observer.disconnect();
  }, [open]);
  return (
    <>
      <dd ref={list} id={id} className={open ? "text-small text-ink" : "line-clamp-2 text-small text-ink"}>
        {names.join(words.agencyJoin)}
      </dd>
      {(hides || open) && (
        // 4 px above the button keep its focus ring off the agencies' second line.
        <dd className="mt-1">
          <Button variant="ghost" flush aria-expanded={open} aria-controls={id} onClick={() => setOpen(!open)}>
            {open ? words.fewerAgencies : words.allAgencies}
          </Button>
        </dd>
      )}
    </>
  );
}

// While the project loads: the same pairs as bars, with the agencies' two lines and the place of
// "Show all agencies", so the tabs below do not move when the project arrives.
const LOADING_PAIRS: Pair[] = [
  ...["w-16", "w-12", "w-10"].map((label) => ({
    label: <SkeletonLine width={label} />,
    value: <SkeletonLine className="text-small" width="w-20" />,
  })),
  {
    label: <SkeletonLine width="w-32" />,
    value: (
      <>
        <SkeletonText className="text-small" widths={["w-full", "w-3/5"]} />
        <span className="mt-1 flex h-11 items-center text-small">
          <Skeleton className="h-[1em] w-32" />
        </span>
      </>
    ),
    wide: true,
  },
];

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

// The agencies the project record names that have published no plan, together after the ones
// with plans, so the exceptions stand out and the rest fold into one block.
function OtherAgencies({ agencies }: { agencies: Agency[] }) {
  return (
    <section data-other-agencies>
      <h3 className="text-title text-ink-heading">{plans.otherAgencies}</h3>
      <p className="mt-2 text-small text-ink-muted">{plans.othersEmpty}</p>
      <ul className="mt-2 list-disc pl-6 text-small text-ink">
        {agencies.map((agency) => (
          <li key={agency.agency_id} data-agency={agency.agency_id}>
            {agency.implementing_agency}
          </li>
        ))}
      </ul>
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
    // The bar stands in for the name; a screen reader hears the project's ID.
    <>
      <span className="sr-only">
        <Fill template={copy.breadcrumb.projectId} slots={{ pid: idText }} />
      </span>
      <Skeleton className="inline-block h-[1em] w-[200px] align-middle" />
    </>
  ) : (
    <Fill template={copy.breadcrumb.projectId} slots={{ pid: idText }} />
  );

  if (notFound) {
    return (
      <div className="layout-grid" data-project-page="not-found">
        <div className="col-span-12 md:col-span-8">
          <Breadcrumb trail={[projectsCrumb, { text: <Fill template={copy.breadcrumb.projectId} slots={{ pid: idText }} /> }]} />
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
  const agencies: Pair[] = project
    ? [{
        label: project.implementing_agencies.length > 1 ? words.label.agencies : words.label.agency,
        value: <Agencies names={project.implementing_agencies} />,
        wide: true,
      }]
    : [];
  const header =
    load.status === "loading" ? (
      <Pairs pairs={LOADING_PAIRS} hidden />
    ) : project ? (
      <Pairs
        pairs={[
          { label: words.label.id, value: value(mono(project.project_id)) },
          { label: words.label.country, value: value(project.country ?? copy.notInRecord) },
          { label: words.label.status, value: value(project.status ?? copy.notInRecord) },
          ...(project.implementing_agencies.length > 0 ? agencies : []),
        ]}
      />
    ) : null;

  // Three columns read best at the prose width, so the version tables keep to columns 1 to 8 from
  // 1200 px (EightColumns breakpoint="xl"); the alert and the empty state do from 1024 px.
  let tab: ReactNode;
  if (load.status === "loading") {
    tab = (
      <EightColumns breakpoint="xl">
        <Table title="" level={3} count={{ noun: plans.noun, total: 0 }} columns={columns} rowHeader="version" state={{ status: "loading", rows: 3 }} />
        <p role="status" className="sr-only">
          {words.loading}
        </p>
      </EightColumns>
    );
  } else if (load.status === "error") {
    tab = (
      <EightColumns>
        <LoadError error={load.error} message={words.error} permission={words.permission} onRetry={retry} retrying={load.retrying} attempt={load.attempt} />
      </EightColumns>
    );
  } else if (load.data.agencies.every((agency) => agency.version_count === 0)) {
    tab = (
      <EightColumns>
        <EmptyState
          level={3}
          title={plans.projectEmptyTitle}
          body={plans.projectEmptyBody}
          link={{ href: "/data", text: plans.projectEmptyLink }}
        />
      </EightColumns>
    );
  } else {
    const withPlans = load.data.agencies.filter((agency) => agency.version_count > 0);
    const without = load.data.agencies.filter((agency) => agency.version_count === 0);
    tab = (
      <EightColumns breakpoint="xl">
        <div className="flex flex-col gap-10">
          {(without.length > 1 ? withPlans : load.data.agencies).map((agency) => (
            <AgencyPlans key={agency.agency_id} agency={agency} pid={pid} through={load.data.documents_through} />
          ))}
          {without.length > 1 && <OtherAgencies agencies={without} />}
        </div>
      </EightColumns>
    );
  }

  return (
    <div className="layout-grid" data-project-page={load.status}>
      <div className="col-span-12 md:col-span-8">
        <Breadcrumb trail={[projectsCrumb, { text: current }]} />
        <h1 ref={title} tabIndex={-1} className="mt-4 text-h1 text-ink-heading focus:outline-none">
          {project ? (
            project.project_name
          ) : load.status === "loading" ? (
            // A route change focuses this h1, so it names the project while the bars stand in for
            // its name. Most names take two lines below 1200 px and one from it.
            <>
              <span className="sr-only">
                <Fill template={copy.pages.project.title} slots={{ pid: idText }} />
              </span>
              <SkeletonText className="xl:hidden" widths={["w-full", "w-3/5"]} />
              <SkeletonLine className="hidden xl:flex" width="w-3/5" />
            </>
          ) : (
            <Fill template={copy.pages.project.title} slots={{ pid: idText }} />
          )}
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
      <div className="col-span-12 mt-6">{tab}</div>
    </div>
  );
}
