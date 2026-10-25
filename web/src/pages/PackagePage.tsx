// The package workspace (the 12 brief), at /packages/:id, where :id is the package's STEP reference.
// It reads two things as the viewer, side by side: the package as its newest public plan row states
// it (GET /api/packages/:id), for the header and the facts, and find_comparables (GET
// /api/packages/:id/comparables) for section 1, "How long it took". Each has its own loading and
// error state, so a section that fails leaves the header and the facts usable.
//
// One narrative column: columns 1 to 8 of the grid from 1200 px, leaving the right side for the
// evidence drawer that ticket 15 opens, and all 12 below that. The header (the package's
// Description as the h1 and its STEP reference) sticks from 768 px, and the page keeps scroll
// padding at its height plus 16 px, so a focused dot or link is never hidden under it. Every width
// on this page is the page area's, not the window's, since the evidence drawer narrows it (DESIGN.md
// section 4): its breakpoints are container queries on the page column (@md/page:). Later tickets
// add sections below section 1 in the PPSD's order.
import { useEffect, useRef, type ReactNode } from "react";
import { Breadcrumb, type Crumb } from "../components/Breadcrumb";
import { EightColumns } from "../components/EightColumns";
import { Fill } from "../components/Fill";
import { LoadError } from "../components/LoadError";
import { MonoWords } from "../components/MonoWords";
import { FactsSkeleton, mono, PackageFactsList, PackageHeader } from "../components/PackageFacts";
import { PastRange, type PastRangeState } from "../components/PastRange";
import { RisksSection } from "../components/RisksSection";
import { SkeletonLine, SkeletonText } from "../components/Skeleton";
import { StepsSection } from "../components/StepsSection";
import { TextLink } from "../components/TextLink";
import { copy } from "../copy";
import type { ComparablesResult, PackageResult } from "../lib/api";
import { useLoad } from "../lib/load";
import { useOpenComparable } from "../lib/packages";
import { useScrollPadding } from "../lib/useScrollPadding";

const words = copy.packagePage;

export function PackagePage({ stepRef }: { stepRef: string }) {
  const base = `/api/packages/${encodeURIComponent(stepRef)}`;
  const [load, retry] = useLoad<PackageResult>(base);
  const [section, retrySection] = useLoad<ComparablesResult>(`${base}/comparables`);
  const header = useRef<HTMLDivElement>(null);
  const sectionHeading = useRef<HTMLHeadingElement>(null);
  const pkg = load.status === "ready" ? load.data.package : null;
  useScrollPadding(header, Boolean(pkg), { gap: 16 });
  // A dot or a row of section 1 opens its comparable package in the evidence drawer (ticket 15).
  const opening = useOpenComparable();

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
        <div className="mt-8">
          <PastRange state={{ status: "loading" }} />
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
        <PackageHeader headerRef={header} title={facts.description ?? mono(facts.step_reference)} reference={mono(facts.step_reference)} />
        <p className="mt-4 max-w-prose text-body text-ink-muted">{copy.pages.package.purpose}</p>
        <div className="mt-4">
          <PackageFactsList pkg={facts} />
        </div>
        <div className="mt-8">
          <PastRange state={sectionState} headingRef={sectionHeading} open={opening} />
        </div>
        {/* Section 2, the planned date for each STEP step (ticket 27), collapsed until opened. */}
        <div className="mt-6 @lg/page:mt-8">
          <StepsSection packageKey={facts.step_reference} kind="step" />
        </div>
        {/* Section 3, procurement risks and what helped (ticket 30), with section 1's default criteria. */}
        <div className="mt-6 @lg/page:mt-8">
          <RisksSection apiHref={base} packageKey={facts.step_reference} kind="step" />
        </div>
      </>
    );
  }

  return (
    <EightColumns breakpoint="xl">
      <div data-package-page={load.status}>
        {/* Below 768 px the trail shows its parent, the project, whose name takes two lines; it holds them while loading. */}
        <div className={load.status === "loading" ? "min-h-[2lh] text-caption @md/page:min-h-0" : undefined}>
          <Breadcrumb trail={crumbs} />
        </div>
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
