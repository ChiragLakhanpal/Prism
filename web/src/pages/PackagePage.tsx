// The package workspace (the 12 brief), at /packages/:id, where :id is the package's STEP reference.
// It reads two things as the viewer, side by side: the package as its newest public plan row states
// it (GET /api/packages/:id), for the header and the facts, and find_comparables (GET
// /api/packages/:id/comparables) for section 1, "How long it took". Each has its own loading and
// error state, so a section that fails leaves the header and the facts usable.
//
// One narrative column: columns 1 to 8 of the grid from 1200 px, leaving the right side for the
// evidence drawer that ticket 15 opens, and all 12 below that. While no drawer is open, the space line in columns 9 to
// 12 says what that side is for (ticket 110). The header (the package's
// Description as the h1 and its STEP reference) sticks from 768 px, and the page keeps scroll
// padding at its height plus 16 px, so a focused dot or link is never hidden under it. Every width
// on this page is the page area's, not the window's, since the evidence drawer narrows it (DESIGN.md
// section 4): its breakpoints are container queries on the page column (@md/page:). Later tickets
// add sections below section 1 in the PPSD's order; ticket 31 adds section 5, "Check your criteria".
import { useEffect, useRef, useState, type ReactNode } from "react";
import { Breadcrumb, type Crumb } from "../components/Breadcrumb";
import { ExistingPpsdNotice } from "../components/ExistingDraftNotice";
import { PpsdAction, type RiskSelection } from "../components/PpsdAction";
import { EightColumns } from "../components/EightColumns";
import { Fill } from "../components/Fill";
import { LoadError } from "../components/LoadError";
import { MonoWords } from "../components/MonoWords";
import { FactsSkeleton, mono, PackageFactsList, PackageHeader } from "../components/PackageFacts";
import { ApproachOptions, approachState } from "../components/ApproachOptions";
import { PastRange, type PastRangeState } from "../components/PastRange";
import { Rebidding } from "../components/RebiddingBlock";
import type { EstimateState } from "../components/TimeEstimate";
import { RisksSection } from "../components/RisksSection";
import { CheckCriteria } from "../components/CheckCriteria";
import { SkeletonLine, SkeletonText } from "../components/Skeleton";
import { SpaceLine } from "../components/SpaceLine";
import { StepTracker, TrackerSkeleton } from "../components/StepTracker";
import { StepsSection, type StepsState } from "../components/StepsSection";
import { TextLink } from "../components/TextLink";
import { copy } from "../copy";
import type { ComparablesResult, EstimateResult, PackageResult } from "../lib/api";
import { usePlanDateChoice } from "../lib/estimates";
import { useLoad } from "../lib/load";
import { useOpenComparable } from "../lib/packages";
import { rebiddingPath } from "../lib/rebidding";
import { address } from "../lib/router";
import { useStore } from "../lib/store";
import { staffRole } from "../lib/following";
import { viewOf } from "../lib/view";

const words = copy.packagePage;

// Section 1's criteria on a STEP row's page, by find_comparables' own parameter names: none, so the tool reads the
// package's own from its plan row. Section 2 sends the same query, so the two count the same comparables (ticket 27's
// review round 2, follow-up 5).
const SECTION_1_CRITERIA = new URLSearchParams();

export function PackagePage({ stepRef }: { stepRef: string }) {
  const base = `/api/packages/${encodeURIComponent(stepRef)}`;
  const criteria = SECTION_1_CRITERIA.toString();
  const [load, retry] = useLoad<PackageResult>(base);
  const [section, retrySection] = useLoad<ComparablesResult>(`${base}/comparables${criteria ? `?${criteria}` : ""}`);
  // Ticket 26: estimate_time beside find_comparables, so lane 1 can draw before lane 2 arrives.
  const [estimateLoad, retryEstimate] = useLoad<EstimateResult>(`${base}/estimate`);
  const estimate: EstimateState =
    estimateLoad.status === "loading"
      ? { status: "loading" }
      : estimateLoad.status === "error"
        ? { status: "error", error: estimateLoad.error, onRetry: retryEstimate, retrying: estimateLoad.retrying }
        : { status: "ready", result: estimateLoad.data };
  const here = useStore(address);
  const planDate = usePlanDateChoice(
    `${base}/plan-dates`,
    estimateLoad.status === "ready" ? estimateLoad.data.plan_date_choice : null,
    viewOf(here.search) !== "staff",
  );
  const sectionHeading = useRef<HTMLHeadingElement>(null);
  const pkg = load.status === "ready" ? load.data.package : null;
  // A dot or a row of section 1 opens its comparable package in the evidence drawer (ticket 15).
  const opening = useOpenComparable();
  // Section 3's selection, for "Suggest {n} PPSD risk rows" (ticket 36).
  const [selection, setSelection] = useState<RiskSelection | null>(null);
  // Section 2's answer, which the tracker at the top of the page draws from (ticket 115).
  const [steps, setSteps] = useState<StepsState>({ status: "loading" });
  const preview = viewOf(here.search) !== "staff";
  // Suggested PPSD rows are a World Bank staff draft (config/drafts.toml, staff_only): a viewer without the role gets
  // no action, and ticket 38's agency variant gives the implementing agency its own.
  const staff = useStore(staffRole) !== false;
  const asOf = new URLSearchParams(here.search).has("asof");

  // After a "Try again" that works, the section's heading takes focus, so focus is not lost.
  useEffect(() => {
    if (section.status === "ready" && section.afterRetry) sectionHeading.current?.focus();
  }, [section]);

  const projectCrumb = (name: ReactNode, pid: string): Crumb => ({ text: name, href: `/projects/${pid}` });
  const trail = (project: Crumb | null): Crumb[] => [
    { text: words.breadcrumbPackages, href: "/packages" },
    ...(project ? [project] : []),
    { text: mono(stepRef) },
  ];

  const notFound = load.status === "error" && load.error?.status === 404;
  let body: ReactNode;
  let crumbs: Crumb[];
  if (load.status === "loading") {
    crumbs = trail(null);
    body = (
      <>
        <PackageHeader
          title={
            <>
              <span className="sr-only">{stepRef}</span>
              {/* A Description takes four lines or so below 768 px, and two above, since most STEP
                  descriptions are longer than one line of the h1. */}
              <SkeletonText className="@md/page:hidden" widths={["w-full", "w-full", "w-full", "w-3/5"]} />
              <SkeletonText className="hidden @md/page:flex" widths={["w-full", "w-2/5"]} />
            </>
          }
          reference={<SkeletonLine width="w-48" />}
          sticky={false}
        />
        <p className="mt-4 max-w-prose text-body text-ink-muted">{copy.pages.package.purpose}</p>
        <div className="mt-4">
          <FactsSkeleton />
        </div>
        <div className="mt-6">
          <TrackerSkeleton />
        </div>
        <div className="mt-8">
          <PastRange state={{ status: "loading" }} estimate={{ status: "loading" }} />
        </div>
      </>
    );
  } else if (notFound) {
    crumbs = trail(null);
    body = (
      <>
        <PackageHeader title={words.notFoundTitle} reference={mono(stepRef)} sticky={false} />
        <p className="mt-4 max-w-prose text-body text-ink">
          <Fill template={words.notFoundBody} slots={{ ref: <MonoWords text={stepRef} after="." medium /> }} />
        </p>
        <p className="mt-4">
          <TextLink href="/projects">{words.notFoundLink}</TextLink>
        </p>
      </>
    );
  } else if (load.status === "error") {
    crumbs = trail(null);
    body = (
      <>
        <PackageHeader title={mono(stepRef)} reference={null} sticky={false} />
        <div className="mt-6">
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
  } else {
    const facts = load.data.package;
    const ppsdPackage = { id: facts.step_reference, title: facts.description ?? facts.step_reference, step_reference: facts.step_reference };
    const name = facts.project_name ? (
      <Fill template={copy.breadcrumb.project} slots={{ name: facts.project_name, pid: mono(facts.project_id) }} />
    ) : (
      <Fill template={copy.breadcrumb.projectId} slots={{ pid: mono(facts.project_id) }} />
    );
    crumbs = trail(projectCrumb(name, facts.project_id));
    const sectionState: PastRangeState =
      section.status === "loading"
        ? { status: "loading" }
        : section.status === "error"
          ? { status: "error", error: section.error, retrying: section.retrying, attempt: section.attempt, onRetry: retrySection }
          : { status: "ready", result: section.data };
    body = (
      <>
        <PackageHeader
          title={facts.description ?? mono(facts.step_reference)}
          reference={mono(facts.step_reference)}
          copyReference={facts.step_reference}
          action={staff ? <PpsdAction pkg={ppsdPackage} selection={selection} preview={preview} asOf={asOf} /> : undefined}
        />
        <p className="mt-4 max-w-prose text-body text-ink-muted">{copy.pages.package.purpose}</p>
        <div className="mt-4">
          <PackageFactsList pkg={facts} />
        </div>
        {/* Where each step stands in the plan (ticket 115), from section 2's answer. */}
        <div className="mt-6">
          <StepTracker state={steps} />
        </div>
        <div className="mt-8">
          <PastRange
            state={sectionState}
            headingRef={sectionHeading}
            open={opening}
            estimate={estimate}
            planDate={planDate}
            after={(comparing) => (
              <Rebidding path={rebiddingPath(base)} section={section.status === "ready" ? section.data : null} comparing={comparing} />
            )}
          />
        </div>
        {/* Section 2, the planned date for each STEP step (ticket 27), collapsed until opened. */}
        <div className="mt-6 @lg/page:mt-8">
          <StepsSection packageKey={facts.step_reference} kind="step" criteria={criteria} onState={setSteps} />
        </div>
        {/* Section 3, procurement risks and what helped (ticket 30), with section 1's default criteria; it tells the
            page what is selected, for "Suggest {n} PPSD risk rows" (ticket 36). */}
        <div className="mt-6 @lg/page:mt-8">
          <RisksSection
            apiHref={base}
            packageKey={facts.step_reference}
            kind="step"
            onSelection={setSelection}
            action={staff ? <PpsdAction pkg={ppsdPackage} selection={selection} preview={preview} asOf={asOf} inline /> : undefined}
          />
        </div>
        {/* Section 4, procurement approach options (ticket 26), from the same time estimate. */}
        <div className="mt-6 @lg/page:mt-8">
          <ApproachOptions
            state={approachState(
              section.status === "ready" ? { status: "ready", result: section.data } : { status: section.status },
              estimate,
              false,
              retrySection,
            )}
          />
        </div>
        {/* Section 5, "Check your criteria" (ticket 31). */}
        <div className="mt-6 @lg/page:mt-8">
          <CheckCriteria base={base} preview={viewOf(here.search) !== "staff"} />
        </div>
      </>
    );
  }

  return (
    <EightColumns breakpoint="xl" beside={<SpaceLine>{copy.evidence.spaceHint.package}</SpaceLine>}>
      <div data-package-page={load.status}>
        {/* Below 768 px the trail shows its parent, the project, whose name takes two lines; it holds them while loading. */}
        <div className={load.status === "loading" ? "min-h-[2lh] text-caption @md/page:min-h-0" : undefined}>
          <Breadcrumb trail={crumbs} />
        </div>
        {/* Ticket 36's notices about suggested PPSD rows sit above the h1, outside the body, so the body's children
            keep their places when the package arrives and the page does not shift. */}
        {load.status === "ready" && <ExistingPpsdNotice packageKey={load.data.package.step_reference} />}
        <div className="mt-4">{body}</div>
        {load.status === "loading" && (
          <p role="status" className="sr-only">
            {words.loading}
          </p>
        )}
      </div>
    </EightColumns>
  );
}
