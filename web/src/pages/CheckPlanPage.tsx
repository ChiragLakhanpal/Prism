// Check a plan (the 10 brief, section 2), at /projects/:pid/procurement/:agencyId/:version, or with no
// version for the agency's latest plan. It asks the server for check_plan's result as the viewer and
// shows one of these states (section 6): loading, the populated check, an agency with no plan, a
// plan with no activities, a version the agency never published, a version not public by the as-of
// date, a project Strata has no record of, a service that didn't answer, and an account that can't
// read Strata's tables.
//
// The header sticks from 1024 px, so the page keeps scroll-padding-top at its height plus 8 px and a
// focused control is never hidden under it (DESIGN.md section 10). A visually hidden status says
// "Checking this plan." and then "Checked nine activities.".
import { useEffect, useRef, useState, type ReactNode, type RefObject } from "react";
import { Breadcrumb, type Crumb } from "../components/Breadcrumb";
import { EmptyState } from "../components/Card";
import { Fill } from "../components/Fill";
import { LoadError } from "../components/LoadError";
import { checkPill, PlanCheck, PlanCheckHeader, PlanCheckSkeleton, type CheckedPlan } from "../components/PlanCheck";
import { Skeleton } from "../components/Skeleton";
import { copy } from "../copy";
import type { CheckPlanResult } from "../lib/api";
import { formatCount, formatDate } from "../lib/format";
import { useLoad } from "../lib/load";

const words = copy.checkPlan;
const short = (iso: string) => formatDate(iso, { style: "table" });

// From 1024 px the header sticks; keep focused elements 8 px clear of it.
function useScrollPadding(header: RefObject<HTMLDivElement | null>, active: boolean) {
  useEffect(() => {
    const element = header.current;
    if (!element || !active) return;
    const wide = window.matchMedia("(width >= 64rem)");
    const update = () => {
      document.documentElement.style.scrollPaddingTop = wide.matches ? `${element.offsetHeight + 8}px` : "";
    };
    update();
    const observer = new ResizeObserver(update);
    observer.observe(element);
    wide.addEventListener("change", update);
    return () => {
      observer.disconnect();
      wide.removeEventListener("change", update);
      document.documentElement.style.scrollPaddingTop = "";
    };
  }, [header, active]);
}

export function CheckPlanPage({ pid, agencyId, version }: { pid: string; agencyId: string; version?: string }) {
  const path = `/api/projects/${encodeURIComponent(pid)}/procurement/${encodeURIComponent(agencyId)}${version ? `/${version}` : ""}`;
  const [load, retry] = useLoad<CheckPlanResult>(path);
  const header = useRef<HTMLDivElement>(null);
  const finding = useRef<HTMLHeadingElement>(null);
  const [said, setSaid] = useState<string>(words.status.checking);

  const result = load.status === "ready" ? load.data : null;
  const checked = result && !result.abstention && result.plan && result.project && result.counts ? (result as CheckedPlan) : null;
  useScrollPadding(header, Boolean(checked));

  useEffect(() => {
    if (load.status === "loading") setSaid(words.status.checking);
    if (checked) {
      const total = checked.counts.activities;
      setSaid(total === 1 ? words.status.checkedOne : words.status.checked(formatCount(total)));
    }
  }, [load.status, checked]);

  // After a "Try again" that works, the finding takes focus, so a screen reader reads the result.
  useEffect(() => {
    if (load.status === "ready" && load.afterRetry) finding.current?.focus();
  }, [load]);

  const procurementHref = `/projects/${pid}/procurement`;
  const projectCrumb = (name: ReactNode): Crumb => ({ text: name, href: `/projects/${pid}` });
  const named = (name: string) => <Fill template={copy.breadcrumb.project} slots={{ name, pid: <span className="font-mono">{pid}</span> }} />;
  const unnamed = <Fill template={copy.breadcrumb.projectId} slots={{ pid: <span className="font-mono">{pid}</span> }} />;
  const trail = (project: ReactNode, last: ReactNode): Crumb[] => [
    { text: copy.breadcrumb.projects, href: "/projects" },
    projectCrumb(project),
    { text: copy.breadcrumb.procurement, href: procurementHref },
    { text: last },
  ];
  const versionCrumb = version ? copy.breadcrumb.plan(short(version)) : null;

  let body: ReactNode;
  let crumbs: Crumb[];
  if (load.status === "loading") {
    crumbs = trail(<Skeleton className="inline-block h-[1em] w-[200px] align-middle" />, versionCrumb ?? words.agencyUnknown);
    body = (
      <>
        <div className="border-b border-line py-4">
          <h1 tabIndex={-1} className="text-h1 text-ink-heading focus:outline-none">
            <span className="sr-only">{words.status.checking}</span>
            <Skeleton className="h-[1.2em] w-3/5 max-w-[560px]" />
          </h1>
          <Skeleton className="mt-2 h-4 w-60" />
          <Skeleton className="mt-3 h-[30px] w-[170px] rounded-pill" />
        </div>
        <PlanCheckSkeleton slow={load.slow} />
        <p className="mt-6 max-w-[72ch] text-small text-ink-muted">{words.notVisible}</p>
      </>
    );
  } else if (load.status === "error") {
    crumbs = trail(unnamed, versionCrumb ?? words.agencyUnknown);
    body = (
      <>
        <PlanCheckHeader agency={words.agencyUnknown} />
        <div className="mt-6 max-w-[72ch]">
          <LoadError
            error={load.error}
            message={words.error}
            permission={words.permission}
            onRetry={retry}
            retrying={load.retrying}
            attempt={load.attempt}
          />
        </div>
      </>
    );
  } else if (checked) {
    crumbs = trail(named(checked.project.project_name), copy.breadcrumb.plan(short(checked.plan.plan_date)));
    body = (
      <>
        <PlanCheckHeader
          headerRef={header}
          agency={checked.plan.implementing_agency}
          plan={words.subtitle(formatDate(checked.plan.plan_date))}
          pill={checkPill(checked)}
        />
        <PlanCheck result={checked} findingRef={finding} />
      </>
    );
  } else {
    const found = load.data;
    const abstention = found.abstention;
    const agency = abstention?.agency_name ?? abstention?.implementing_agency ?? found.plan?.implementing_agency ?? null;
    const knownAgency = abstention?.reason === "no_plan_from_agency" ? (abstention.agency_name ?? null) : agency;
    crumbs = trail(found.project ? named(found.project.project_name) : unnamed, versionCrumb ?? knownAgency ?? words.agencyUnknown);
    const allPlans = { href: procurementHref, text: words.allPlans };
    let title: ReactNode = words.noPlanTitleUnnamed;
    let text: ReactNode = words.noPlanBody;
    let link: { href: string; text: ReactNode } | undefined = allPlans;
    const latest = abstention?.latest_plan_date;
    const latestLink = latest && abstention?.agency_id
      ? { href: `${procurementHref}/${abstention.agency_id}/${latest}`, text: words.latestLink(short(latest)) }
      : allPlans;
    switch (abstention?.reason) {
      case "unknown_project":
        title = <Fill template={copy.projectPage.notFoundTitle} slots={{ pid: <span className="font-mono">{pid}</span> }} />;
        text = copy.projectPage.notFoundBody;
        link = { href: "/projects", text: copy.projectPage.notFoundLink };
        break;
      case "no_plan_from_agency":
        title = abstention.agency_name ? words.noPlanTitle(abstention.agency_name) : words.noPlanTitleUnnamed;
        break;
      case "version_not_found":
        if (latest) {
          title = words.notFoundTitle(formatDate(abstention.plan_date!));
          text = words.notFoundBody(formatDate(latest));
          link = latestLink;
        }
        break;
      case "version_not_public":
        title = words.notPublicTitle(formatDate(found.as_of));
        text = words.notPublicBody(formatDate(abstention.public_from!));
        link = latestLink;
        break;
      case "no_plan_as_of":
        title = words.noPlanAsOfTitle(formatDate(found.as_of));
        text = words.noPlanBody;
        break;
      case "no_activities":
        title = words.noActivitiesTitle;
        text = words.noActivitiesBody;
        link = { href: "/data", text: words.dataReadiness };
        break;
    }
    body = (
      <>
        <PlanCheckHeader
          agency={knownAgency ?? words.agencyUnknown}
          plan={found.plan ? words.subtitle(formatDate(found.plan.plan_date)) : undefined}
        />
        <EmptyState className="mt-6" title={title} body={text} link={link} />
      </>
    );
  }

  return (
    <div data-check-plan-page={load.status}>
      <Breadcrumb trail={crumbs} />
      <div className="mt-4">{body}</div>
      <p role="status" className="sr-only">
        {said}
      </p>
    </div>
  );
}
