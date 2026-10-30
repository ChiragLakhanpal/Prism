// The package workspace (the 12 brief), at /packages/:id, where :id is the package's STEP reference.
// It reads two things as the viewer, side by side: the package as its newest public plan row states
// it (GET /api/packages/:id), for the page head and the facts, and find_comparables (GET
// /api/packages/:id/comparables) for zone 1, "How long it took". Each has its own loading and
// error state, so a zone that fails leaves the head and the facts usable.
//
// Since ticket 101 it is a workspace page (DESIGN.md section 4, Page layouts, Workspace; Workspace.tsx): the page head
// and five numbered Task zones in columns 1 to 7, with "Planning" before zone 1 and "Tender design" before zone 5, and
// the plan row's facts as the side panel "From the plan row" in columns 9 to 12 from a frame of 75rem. The evidence
// drawer opens in the side panel's place, and the zones keep their place and width. Below that frame the facts are one
// line in the head, with "Show the plan row", which opens the same record. The head does not stick, and its h1, the
// package's Description, wraps in full however long. Zone 1 is a panel that opens on its finding; zones 2 and 5 are
// closed rows; zones 3 and 4 are rows while they hold only their sentence, panels when they have risks or options, and
// zone 3 then holds "Suggest {n} PPSD risk rows", the page's one primary action for staff. The step tracker (ticket
// 115) follows zone 1 below a frame of 75rem, so the finding leads inside the first screen at 390 by 844 and 1024 by
// 768; from that frame it sits in the side column under "From the plan row" as a list, and sticks under the bar while
// you read the zones (ticket 130, the design lead's Option W2). It renders in one place only, chosen by the frame's
// width, so the reading order follows what the eye sees, and it hides with the side panel while the drawer is open.
import { useEffect, useRef, useState, type ReactNode } from "react";
import { type Crumb } from "../components/Breadcrumb";
import { CopyKey } from "../components/CopyKey";
import { ExistingPpsdNotice } from "../components/ExistingDraftNotice";
import { PpsdAction, type RiskSelection } from "../components/PpsdAction";
import { Fill } from "../components/Fill";
import { LoadError } from "../components/LoadError";
import { MonoWords } from "../components/MonoWords";
import { FactsPanel, factsLine, mono } from "../components/PackageFacts";
import { ApproachOptions, approachState } from "../components/ApproachOptions";
import { PageHead } from "../components/PageHead";
import { PastRange, type PastRangeState } from "../components/PastRange";
import { Rebidding } from "../components/RebiddingBlock";
import type { EstimateState } from "../components/TimeEstimate";
import { RisksSection } from "../components/RisksSection";
import { CheckCriteria } from "../components/CheckCriteria";
import { StageLabel } from "../components/StageLabel";
import { StepTracker, TrackerSkeleton } from "../components/StepTracker";
import { StepsSection, type StepsState } from "../components/StepsSection";
import { TextLink } from "../components/TextLink";
import { Workspace } from "../components/Workspace";
import { useAnswerInPage } from "../components/AnswerSlot";
import { copy } from "../copy";
import type { ComparablesResult, EstimateResult, PackageFacts, PackageResult } from "../lib/api";
import { evidenceIn } from "../lib/evidence";
import { usePlanDateChoice } from "../lib/estimates";
import { useLoad } from "../lib/load";
import { openPlanRow, useOpenComparable } from "../lib/packages";
import { rebiddingPath } from "../lib/rebidding";
import { address } from "../lib/router";
import { useStore } from "../lib/store";
import { useFrameAtLeast } from "../lib/useFrameAtLeast";
import { staffRole } from "../lib/following";
import { viewOf } from "../lib/view";

const words = copy.packagePage;

// Section 1's criteria on a STEP row's page, by find_comparables' own parameter names: none, so the tool reads the
// package's own from its plan row. Section 2 sends the same query, so the two count the same comparables (ticket 27's
// review round 2, follow-up 5).
const SECTION_1_CRITERIA = new URLSearchParams();

// The plan row's record in the evidence drawer, opened from the side panel's marker, the facts line's button or the
// finding's plan months; the opener gets focus back when it closes.
const planRowOf = (pkg: PackageFacts) => (element: HTMLElement) => openPlanRow(pkg.evidence_id, element);

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
  // An answer asked from the box: in the work's columns above the page head (ticket 98's answer slot).
  const asked = useAnswerInPage();
  // A dot or a row of section 1 opens its comparable package in the evidence drawer (ticket 15).
  const opening = useOpenComparable();
  // Section 3's selection, for "Suggest {n} PPSD risk rows" (ticket 36).
  const [selection, setSelection] = useState<RiskSelection | null>(null);
  // Section 2's answer, which the step tracker draws from (ticket 115).
  const [steps, setSteps] = useState<StepsState>({ status: "loading" });
  const preview = viewOf(here.search) !== "staff";
  // Suggested PPSD rows are a World Bank staff draft (config/drafts.toml, staff_only): a viewer without the role gets
  // no action, and ticket 38's agency variant gives the implementing agency its own.
  const staff = useStore(staffRole) !== false;
  const asOf = new URLSearchParams(here.search).has("asof");
  const openId = evidenceIn(here.search);
  // From a frame of 75rem the step tracker is in the side column; below it, after zone 1 (ticket 130).
  const root = useRef<HTMLDivElement>(null);
  const trackerBeside = useFrameAtLeast(root, 75);

  // After a "Try again" that works, the section's heading takes focus, so focus is not lost.
  useEffect(() => {
    if (section.status === "ready" && section.afterRetry) sectionHeading.current?.focus();
  }, [section]);

  const packagesCrumb: Crumb = { text: words.breadcrumbPackages, href: "/packages" };
  const notFound = load.status === "error" && load.error?.status === 404;

  let head: ReactNode;
  let side: ReactNode = undefined;
  // The step tracker, or its skeleton while the package loads, in the one place the frame's width gives it.
  let tracker: ReactNode = null;
  let zones: ReactNode = null;
  if (load.status === "loading") {
    // The head holds the places of its ID line and its facts line, so nothing under it moves when the package arrives.
    head = (
      <PageHead
        trail={[packagesCrumb]}
        held
        holdBack
        title={stepRef}
        id={stepRef}
        loading
        narrowLines={3}
        narrowestLines={4}
        facts={{ line: null, show: words.factsShow, onShow: () => undefined }}
      />
    );
    side = <FactsPanel pkg={null} />;
    tracker = <TrackerSkeleton />;
    zones = (
      <>
        <StageLabel>{words.stages.planning}</StageLabel>
        <PastRange state={{ status: "loading" }} estimate={{ status: "loading" }} />
        {!trackerBeside && <div className="my-4">{tracker}</div>}
      </>
    );
  } else if (notFound) {
    head = <PageHead trail={[packagesCrumb]} held title={words.notFoundTitle} id={stepRef} />;
    zones = (
      <>
        <p className="max-w-prose text-body text-ink">
          <Fill template={words.notFoundBody} slots={{ ref: <MonoWords text={stepRef} after="." medium /> }} />
        </p>
        <p className="mt-4">
          <TextLink href="/projects">{words.notFoundLink}</TextLink>
        </p>
      </>
    );
  } else if (load.status === "error") {
    // The page's one request failed: its error alert sits in the head's alert slot, and the reference is the h1.
    head = (
      <PageHead
        trail={[packagesCrumb]}
        held
        title={mono(stepRef)}
        alert={
          <LoadError error={load.error} message={words.error} permission={words.permission} onRetry={retry} retrying={load.retrying} attempt={load.attempt} />
        }
      />
    );
  } else {
    const facts = load.data.package;
    const ppsdPackage = { id: facts.step_reference, title: facts.description ?? facts.step_reference, step_reference: facts.step_reference };
    // The project's name as Check a plan's crumb and the project's header give it (the 58 critique, round 3).
    const projectName = facts.display_name ?? facts.project_name;
    const name = projectName ? (
      <Fill template={copy.breadcrumb.project} slots={{ name: projectName, pid: mono(facts.project_id) }} />
    ) : (
      <Fill template={copy.breadcrumb.projectId} slots={{ pid: mono(facts.project_id) }} />
    );
    const planRowOpen = openId === facts.evidence_id;
    head = (
      <PageHead
        // Ticket 36's notices about suggested PPSD rows sit in the head's alert slot, above the breadcrumb.
        alert={<ExistingPpsdNotice packageKey={facts.step_reference} />}
        trail={[packagesCrumb, { text: name, href: `/projects/${facts.project_id}` }]}
        held
        title={facts.description ?? mono(facts.step_reference)}
        id={facts.step_reference}
        // Ticket 112: the copy key copies the STEP reference. The 24 px key keeps the 20 px line's height.
        idAction={
          <>
            <CopyKey text={facts.step_reference} what={copy.copyKey.reference} className="-my-0.5 align-top" />
            {/* A reference that breaks STEP's form, kept as the plan reader read it (ticket 131). */}
            {facts.reference_as_read && <span className="ml-2">{words.referenceAsRead}</span>}
          </>
        }
        facts={{ line: factsLine(facts), show: words.factsShow, onShow: planRowOf(facts), expanded: planRowOpen }}
      />
    );
    side = <FactsPanel pkg={facts} opened={planRowOpen} onOpen={planRowOf(facts)} />;
    tracker = <StepTracker state={steps} />;
    const sectionState: PastRangeState =
      section.status === "loading"
        ? { status: "loading" }
        : section.status === "error"
          ? { status: "error", error: section.error, retrying: section.retrying, attempt: section.attempt, onRetry: retrySection }
          : { status: "ready", result: section.data };
    zones = (
      <>
        <StageLabel>{words.stages.planning}</StageLabel>
        {/* Zone 1, "How long it took", with "Advertised again" (ticket 28) as its second block. */}
        <PastRange
          state={sectionState}
          headingRef={sectionHeading}
          open={opening}
          estimate={estimate}
          planDate={planDate}
          after={(comparing) => (
            <Rebidding
              path={rebiddingPath(base)}
              section={section.status === "ready" ? section.data : null}
              sectionFailed={section.status === "error"}
              sectionLoading={section.status === "loading"}
              comparing={comparing}
            />
          )}
        />
        {/* Where each step stands in the plan (ticket 115), from zone 2's answer, here below a frame of 75rem. */}
        {!trackerBeside && <div className="my-4">{tracker}</div>}
        {/* Zone 2, the planned date for each STEP step (ticket 27), closed until opened. */}
        <StepsSection packageKey={facts.step_reference} kind="step" criteria={criteria} onState={setSteps} />
        {/* Zone 3, procurement risks and what helped (ticket 30), with zone 1's default criteria; it tells the page
            what is selected, for "Suggest {n} PPSD risk rows" (ticket 36), which it holds. */}
        <RisksSection
          apiHref={base}
          packageKey={facts.step_reference}
          kind="step"
          onSelection={setSelection}
          action={staff ? <PpsdAction pkg={ppsdPackage} selection={selection} preview={preview} asOf={asOf} /> : undefined}
        />
        {/* Zone 4, procurement approach options (ticket 26), from the same time estimate. */}
        <ApproachOptions
          state={approachState(
            section.status === "ready" ? { status: "ready", result: section.data } : { status: section.status },
            estimate,
            false,
          )}
        />
        <StageLabel>{words.stages.tender}</StageLabel>
        {/* Zone 5, "Check your criteria" (ticket 31). */}
        <CheckCriteria base={base} preview={viewOf(here.search) !== "staff"} />
      </>
    );
  }

  return (
    <div ref={root} data-package-page={load.status}>
      <Workspace answer={asked} head={head} side={side} sideSticky={side != null && trackerBeside ? tracker : undefined} fold="head">
        {zones}
      </Workspace>
      {load.status === "loading" && (
        <p role="status" className="sr-only">
          {words.loading}
        </p>
      )}
    </div>
  );
}
