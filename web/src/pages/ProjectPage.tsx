// A project's page, the hub (the 10 and 21 briefs), at /projects/:pid and its tabs. The header is the
// wireframe's one line in the h1, "Rajasthan Road Sector Modernization · P130164 · India · closed", with
// the project ID as a ProjectId link and the status lowercased from the copy file, then the implementing
// agency line. Under it the tab row shows the built tabs in the copy file's order: Summary, Procurement and
// Documents (Timeline and Connections join when tickets 23 and 22 land).
//
// The app keeps this page in place while you move between its tabs (Match.frame), so the header and the
// tab row never redraw; a tab opened from the row keeps focus on its link and says "Showing Procurement."
// through a polite status (the 21 brief, section 11.2). The header is not sticky: it holds no action until
// ticket 37 adds Follow.
//
// States: loading (the h1 names the project for a screen reader, and bars stand in for the line and the
// agency line, while the tab row is real), populated, a project Strata has no record of, a service that
// didn't answer, and an account that can't read Strata's tables. Each tab draws its own states.
import { useEffect, useId, useLayoutEffect, useRef, useState, type ReactNode } from "react";
import { Breadcrumb } from "../components/Breadcrumb";
import { Button } from "../components/Button";
import { EightColumns } from "../components/EightColumns";
import { Fill } from "../components/Fill";
import { LoadError } from "../components/LoadError";
import { ProjectId } from "../components/ProjectId";
import { Skeleton, SkeletonLine, SkeletonText } from "../components/Skeleton";
import { Tabs } from "../components/Tabs";
import { TextLink } from "../components/TextLink";
import { copy } from "../copy";
import type { ProjectPage as Page } from "../lib/api";
import { useLoad } from "../lib/load";
import { address, navigate } from "../lib/router";
import { useStore } from "../lib/store";
import { setPageTitle } from "../lib/title";
import { BUILT_TABS, TAB_PATH, type ProjectTab } from "../routes";
import { DocumentsTab } from "./project/DocumentsTab";
import { ProcurementTab } from "./project/ProcurementTab";
import { SummaryTab } from "./project/SummaryTab";

const words = copy.projectPage;

// The view and as-of date the address asks for, passed on to the project's reads, since the baseline is
// hidden in the public view and shown without its saver in the implementing agency view.
export function readParams(search: string, keys: string[] = ["view"]): string {
  const params = new URLSearchParams(search);
  const kept = new URLSearchParams();
  for (const key of keys) {
    const value = params.get(key);
    if (value) kept.set(key, value);
  }
  const rest = kept.toString();
  return rest ? `?${rest}` : "";
}

// The agencies keep to two lines. When the names need more, "Show all agencies" follows them; it shows
// only while the two lines hide a name, measured again whenever the line's width changes. Two agency
// names hold commas, so the names are set apart with semicolons.
function AgencyLine({ names }: { names: string[] }) {
  const id = useId();
  const line = useRef<HTMLParagraphElement>(null);
  const [open, setOpen] = useState(false);
  const [hides, setHides] = useState(false);
  useLayoutEffect(() => {
    const element = line.current;
    if (!element || open) return;
    const measure = () => setHides(element.scrollHeight > element.clientHeight + 1);
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(element);
    return () => observer.disconnect();
  }, [open]);
  if (names.length === 0) return <p className="mt-2 max-w-prose text-body text-ink-muted">{words.noAgency}</p>;
  return (
    <div className="mt-2" data-agency-line>
      <p ref={line} id={id} className={open ? "max-w-prose text-body text-ink-muted" : "line-clamp-2 max-w-prose text-body text-ink-muted"}>
        <Fill template={names.length > 1 ? words.agenciesLine : words.agencyLine} slots={{ agencies: names.join(words.agencyJoin) }} />
      </p>
      {(hides || open) && (
        // 4 px above the button keep its focus ring off the agencies' second line.
        <div className="mt-1">
          <Button variant="ghost" flush onPage aria-expanded={open} aria-controls={id} onClick={() => setOpen(!open)}>
            {open ? words.fewerAgencies : words.allAgencies}
          </Button>
        </div>
      )}
    </div>
  );
}

// The h1's one line. Each " · item" keeps together, so a dot never ends a line and an item never splits:
// the line breaks only at the space before a dot, or inside the project's name.
function HeaderLine({ project }: { project: Page["project"] }) {
  const status = project.status ? (words.statusInline[project.status] ?? project.status) : null;
  const item = (content: ReactNode) => (
    <>
      {" "}
      <span className="whitespace-nowrap text-ink-muted">
        {words.dot}
        {content}
      </span>
    </>
  );
  return (
    <>
      <span className="text-ink-heading">{project.display_name ?? project.project_name}</span>
      {item(<ProjectId pid={project.project_id} />)}
      {project.country && item(project.country)}
      {status && item(status)}
    </>
  );
}

export function ProjectPage({ pid, tab }: { pid: string; tab: ProjectTab }) {
  const here = useStore(address);
  const [load, retry] = useLoad<Page>(`/api/projects/${encodeURIComponent(pid)}${readParams(here.search)}`);
  const title = useRef<HTMLHeadingElement>(null);
  const tabRow = useRef<HTMLDivElement>(null);
  const [showing, setShowing] = useState("");
  const idText = <span className="font-mono font-medium">{pid}</span>;

  useEffect(() => {
    if (load.status === "ready" && load.afterRetry) title.current?.focus();
  }, [load]);

  const data = load.status === "ready" ? load.data : null;
  const tabLabel = words.tab[tab];
  // The browser tab names the project and the tab: "Rajasthan Road Sector Modernization (P130164), Summary".
  useEffect(() => {
    if (data) setPageTitle(words.documentTitle(data.project.display_name ?? data.project.project_name, pid, tabLabel));
  }, [data, tab]);

  // The server's 404 for a project it has no record of; any other 404 is a service that didn't answer.
  const notFound = load.status === "error" && load.error?.status === 404 && load.error.body.code === "unknown_project";
  const projectsCrumb = { text: copy.breadcrumb.projects, href: "/projects" };
  const named = data ? (
    <Fill template={copy.breadcrumb.project} slots={{ name: data.project.project_name, pid: <ProjectId pid={pid} /> }} />
  ) : null;

  if (notFound) {
    return (
      <div className="layout-grid" data-project-page="not-found">
        <div className="col-span-12 @md/page:col-span-8">
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

  if (load.status === "error") {
    return (
      <div className="layout-grid" data-project-page="error">
        <div className="col-span-12">
          <Breadcrumb trail={[projectsCrumb, { text: <Fill template={copy.breadcrumb.projectId} slots={{ pid: idText }} /> }]} />
          <h1 ref={title} tabIndex={-1} className="sr-only">
            <Fill template={copy.pages.project.title} slots={{ pid: idText }} />
          </h1>
        </div>
        <EightColumns className="col-span-12 mt-4">
          <LoadError error={load.error} message={words.headerError} permission={words.permission} onRetry={retry} retrying={load.retrying} attempt={load.attempt} />
        </EightColumns>
      </div>
    );
  }

  const current = named ?? (
    // The bar stands in for the name; a screen reader hears the project's ID.
    <>
      <span className="sr-only">
        <Fill template={copy.breadcrumb.projectId} slots={{ pid: idText }} />
      </span>
      <Skeleton className="inline-block h-[1em] w-[200px] align-middle" />
    </>
  );

  const base = `/projects/${pid}`;
  const keep = readParams(here.search, ["view", "asof", "lang"]);
  const tabs = BUILT_TABS.map((key) => ({ key, label: words.tab[key], href: `${base}${TAB_PATH[key]}${keep}`, current: key === tab }));
  // A tab opened from the row: the address changes in place and focus stays on the tab. The page scrolls
  // only when the tab row was above the window, and then brings it to the top.
  const openTab = (href: string) => {
    navigate(href, { quiet: true });
    const next = tabs.find((candidate) => candidate.href === href);
    if (next) setShowing(words.showing(String(next.label)));
    const row = tabRow.current;
    if (row && row.getBoundingClientRect().top < 0) row.scrollIntoView({ block: "start" });
  };

  return (
    <div className="layout-grid" data-project-page={load.status}>
      <div className="col-span-12">
        <Breadcrumb trail={[projectsCrumb, { text: current }]} />
        <h1 ref={title} tabIndex={-1} data-project-header className="mt-4 text-h1 text-ink-heading focus:outline-none">
          {data ? (
            <HeaderLine project={data.project} />
          ) : (
            // A route change focuses this h1, so it names the project while a bar stands in for its line.
            <>
              <span className="sr-only">
                <Fill template={copy.pages.project.title} slots={{ pid: idText }} />
              </span>
              {/* The line takes three lines below 768 px, two up to 1024 px and one from there, for a name
                  of about 35 characters, such as P156634's. */}
              <SkeletonText className="@md/page:hidden" widths={["w-full", "w-4/5", "w-2/5"]} />
              <SkeletonText className="hidden @md/page:flex @lg/page:hidden" widths={["w-full max-w-[560px]", "w-2/5"]} />
              <SkeletonLine className="hidden @lg/page:flex" width="w-3/5 max-w-[560px]" />
            </>
          )}
        </h1>
        {data ? (
          <AgencyLine names={data.project.implementing_agencies} />
        ) : (
          // The agency line's two lines and the place of "Show all agencies", as a project with many agencies
          // has them, so the tabs below never move down when the project arrives; with fewer they move up.
          <div aria-hidden="true" className="mt-2 max-w-prose">
            <SkeletonText className="text-body" widths={["w-full", "w-3/5"]} />
            <span className="mt-1 flex h-11 items-center text-body">
              <Skeleton className="h-[1em] w-32" />
            </span>
          </div>
        )}
      </div>
      <div ref={tabRow} className="col-span-12 mt-6 scroll-mt-2">
        <Tabs label={words.sections} tabs={tabs} onNavigate={openTab} />
      </div>
      <div className="col-span-12 mt-8">
        {tab === "summary" && <SummaryTab pid={pid} />}
        {tab === "procurement" && <ProcurementTab pid={pid} load={load} retry={retry} />}
        {tab === "documents" && <DocumentsTab pid={pid} />}
      </div>
      <p role="status" className="sr-only">
        {showing}
      </p>
    </div>
  );
}
