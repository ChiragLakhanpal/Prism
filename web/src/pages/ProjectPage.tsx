// A project's page, the hub (the 10 and 21 briefs), at /projects/:pid and its tabs. The header is the
// wireframe's one line in the h1, "Rajasthan Road Sector Modernization · P130164 · India · closed", with
// the project ID as a ProjectId link and the status lowercased from the copy file, then the implementing
// agency line. Under it the tab row shows the five tabs in the copy file's order, which lives there alone: Summary,
// Procurement, Timeline, Documents and Connections.
//
// Ticket 99 made the head shorter: the ID, country and status in the h1's line take 400, the agency line keeps one
// line with "Show all agencies" on it, and World Bank staff's Follow control sits at the head's right from a page area
// of 46rem (under the agency line below it), so the tab row starts within 200 px of the head's top at 1440 px.
//
// The app keeps this page in place while you move between its tabs (Match.frame), so the header and the
// tab row never redraw; a tab opened from the row keeps focus on its link and says "Showing Procurement."
// through a polite status (the 21 brief, section 11.2). The header is not sticky, even with ticket 37's
// follow control: following is an occasional act, not the page's task (the 37 brief, section 6.1).
//
// States: loading (the h1 names the project for a screen reader, and bars stand in for the line and the
// agency line, while the tab row is real), populated, a project Strata has no record of, a service that
// didn't answer, and an account that can't read Strata's tables. Each tab draws its own states.
import { useEffect, useRef, useState } from "react";
import { Breadcrumb } from "../components/Breadcrumb";
import { EightColumns } from "../components/EightColumns";
import { Fill } from "../components/Fill";
import { LoadError } from "../components/LoadError";
import { AgencyLine, ProjectHeaderLine } from "../components/ProjectHeader";
import { ProjectIdText } from "../components/ProjectId";
import { Skeleton, SkeletonLine, SkeletonText } from "../components/Skeleton";
import { Tabs } from "../components/Tabs";
import { TextLink } from "../components/TextLink";
import { copy } from "../copy";
import type { ProjectPage as Page } from "../lib/api";
import { useLoad } from "../lib/load";
import { address, navigate } from "../lib/router";
import { useStore } from "../lib/store";
import { setPageTitle } from "../lib/title";
import { keptQuery, useAllows, withReadParams } from "../lib/view";
import { staffRole } from "../lib/following";
import { FollowControl } from "../components/FollowControl";
import { TAB_PATH, type ProjectTab } from "../routes";
import { ConnectionsTab } from "./project/ConnectionsTab";
import { DocumentsTab } from "./project/DocumentsTab";
import { ProcurementTab } from "./project/ProcurementTab";
import { SummaryTab } from "./project/SummaryTab";
import { TimelineTab } from "./project/TimelineTab";

const words = copy.projectPage;

export function ProjectPage({ pid, tab }: { pid: string; tab: ProjectTab }) {
  const here = useStore(address);
  const staff = useStore(staffRole) === true;
  const follows = useAllows("follow");
  // The view and as-of date the address asks for go on to the project's read, since the baseline is hidden in
  // the public view and shown without its saver in the implementing agency view.
  const [load, retry] = useLoad<Page>(withReadParams(`/api/projects/${encodeURIComponent(pid)}`, here.search));
  const title = useRef<HTMLHeadingElement>(null);
  const tabRow = useRef<HTMLDivElement>(null);
  const [showing, setShowing] = useState("");
  const idText = <ProjectIdText pid={pid} />;

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
  // The current crumb names the project as the h1 does, by the server's display name, with its ID in plain
  // mono: the h1's ProjectId just below it is the link to this page, so the crumb adds no second tab stop.
  const named = data ? (
    <span data-project-crumb>
      <Fill template={copy.breadcrumb.project} slots={{ name: data.project.display_name ?? data.project.project_name, pid: idText }} />
    </span>
  ) : null;

  if (notFound) {
    return (
      <div className="layout-grid" data-project-page="not-found">
        <div className="col-span-12 @md/page:col-span-8">
          <Breadcrumb trail={[projectsCrumb, { text: <Fill template={copy.breadcrumb.projectId} slots={{ pid: idText }} /> }]} />
          <h1 ref={title} tabIndex={-1} className="mt-2 text-h1 text-ink-heading focus:outline-none">
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
  const keep = keptQuery(here.search, ["view", "asof", "lang"]);
  // The tabs in the copy file's order, the one place it lives (ticket 99).
  const tabs = (Object.keys(words.tab) as ProjectTab[]).map((key) => ({ key, label: words.tab[key], href: `${base}${TAB_PATH[key]}${keep}`, current: key === tab }));
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
      {/* The head (ticket 99): the crumb, then the h1 and the agency line beside the Follow control, which sits at the
          head's right from a page area of 46rem and under the agency line below it. */}
      <div className="col-span-12" data-project-head>
        <Breadcrumb trail={[projectsCrumb, { text: current }]} />
        <div className="mt-2 flex flex-col gap-4 @head/page:flex-row @head/page:items-start @head/page:justify-between @head/page:gap-8">
          <div className="min-w-0 flex-1">
            <h1 ref={title} tabIndex={-1} data-project-header className="text-h1 text-ink-heading focus:outline-none">
              {data ? (
                <ProjectHeaderLine project={data.project} />
              ) : (
                // A route change focuses this h1, so it names the project while a bar stands in for its line.
                <>
                  <span className="sr-only">
                    <Fill template={copy.pages.project.title} slots={{ pid: idText }} />
                  </span>
                  {/* The line takes three lines below a page area of 26rem, two to 56rem and one from there, for a name of
                      about 35 characters, such as P156634's, with its P-code, country and status (ticket 59, measured
                      at 320 to 1440 px); below 768 px each dot keeps to the word before it, so the name's last word takes
                      the second line (ticket 99). */}
                  <SkeletonText className="@[26rem]/page:hidden" widths={["w-full", "w-4/5", "w-2/5"]} />
                  <SkeletonText className="hidden @[26rem]/page:flex @[56rem]/page:hidden" widths={["w-full max-w-[560px]", "w-2/5"]} />
                  <SkeletonLine className="hidden @[56rem]/page:flex" width="w-3/5 max-w-[560px]" />
                </>
              )}
            </h1>
            {data ? (
              <AgencyLine names={data.project.implementing_agencies} />
            ) : (
              // The agency line and the place of "Show all agencies" beside it, as a project with many agencies has
              // them, so the tabs below never move down when the project arrives; with one agency they keep their place,
              // since "Show all agencies" is a compact 24 px button on the agency line's row (ticket 60).
              <div aria-hidden="true" className="mt-2 flex h-6 items-center">
                <Skeleton className="h-[1em] w-3/5 max-w-[480px]" />
              </div>
            )}
          </div>
          {/* Follow and unfollow, for World Bank staff (ticket 37), where the view the server applied keeps following:
              never in a preview (the roles file's [views]). It reads whether you follow the project by its ID, so it
              stands in its place while the project loads too. */}
          {staff && follows && (
            <div className="shrink-0">
              <FollowControl pid={pid} name={data?.project.project_name ?? null} />
            </div>
          )}
        </div>
      </div>
      <div ref={tabRow} className="col-span-12 mt-6 scroll-mt-2">
        <Tabs label={words.sections} tabs={tabs} onNavigate={openTab} />
      </div>
      {/* A screen's height, so the footer sits below the fold while a tab loads and stays there when a short
          answer, such as an error, lands: it never jumps up into view (the 21 design review, round 2, F10). */}
      <div className="col-span-12 mt-8 min-h-svh">
        {tab === "summary" && <SummaryTab pid={pid} />}
        {tab === "procurement" && <ProcurementTab pid={pid} load={load} retry={retry} />}
        {tab === "timeline" && <TimelineTab pid={pid} />}
        {tab === "documents" && <DocumentsTab pid={pid} />}
        {tab === "connections" && <ConnectionsTab pid={pid} />}
      </div>
      <p role="status" className="sr-only">
        {showing}
      </p>
    </div>
  );
}
