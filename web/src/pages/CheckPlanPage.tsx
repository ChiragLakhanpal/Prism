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
import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { Alert } from "../components/Alert";
import { Breadcrumb, type Crumb } from "../components/Breadcrumb";
import { Button } from "../components/Button";
import { EmptyState } from "../components/Card";
import { TextLink } from "../components/TextLink";
import { EightColumns } from "../components/EightColumns";
import { Fill, Unbroken } from "../components/Fill";
import { LoadError } from "../components/LoadError";
import { BaselinePanel, useBaselineView } from "../components/BaselinePanel";
import { ChangeTables, changedRows } from "../components/ChangeTables";
import { Num } from "../components/Num";
import { checkPill, PlanCheck, PlanCheckHeader, PlanCheckSkeleton, planSubtitle, type CheckedPlan } from "../components/PlanCheck";
import { ProjectIdText } from "../components/ProjectId";
import { Skeleton, SkeletonLine, SkeletonText } from "../components/Skeleton";
import { copy } from "../copy";
import { ApiError, getJson, type CheckPlanResult, type PlanChanges } from "../lib/api";
import { changed, changeList } from "../lib/changes";
import { draftHref, newKey, startWriting, stopped, writingHref, type Existing, type ExistingDraft } from "../lib/drafts";
import { ProjectPaperPanel } from "../components/ProjectPaperPanel";
import { PROJECT_PAPER_STOPPED } from "../lib/drafts";
import { formatCount, formatDate, formatNumber } from "../lib/format";
import { useLoad } from "../lib/load";
import { address, navigate } from "../lib/router";
import { useStore } from "../lib/store";
import { setPageTitle } from "../lib/title";
import { appliedView, previewOf, withReadParams } from "../lib/view";
import { useScrollPadding } from "../lib/useScrollPadding";
import { fill } from "../routes";

const words = copy.checkPlan;
const short = (iso: string) => formatDate(iso, { style: "table" });
const whole = (value: number) => formatNumber(value, { compact: false });

// How long the populated page waits for the existing-draft lookup once the plan check is ready to draw. A
// notice that arrived after the page was drawn would push it down, so a later answer is dropped for this
// visit (the 35 design review).
const LOOKUP_WAIT_MS = 300;

// The review notes the team already started on this plan version. The lookup starts at mount on both
// routes: with a version in the address it asks for that version; with none it asks for every version of
// the agency's plans and takes the one the check shows once it is ready. The wait is counted from when the
// check is ready, so a lookup that answers while a slow check is still loading is always shown. Settled
// when the lookup answers, or LOOKUP_WAIT_MS after the check is ready, whichever comes first.
function useExistingDraft(pid: string, agencyId: string, version: string | undefined, enabled: boolean, planDate: string | null) {
  const [answer, setAnswer] = useState<{ key: string; found: Existing } | null>(null);
  const [gaveUp, setGaveUp] = useState<string | null>(null);
  const key = enabled ? `${pid}/${agencyId}/${version ?? ""}` : null;
  useEffect(() => {
    if (!key) return;
    const controller = new AbortController();
    const query = new URLSearchParams({ kind: "review_notes", project_id: pid, agency_id: agencyId });
    if (version) query.set("plan_date", version);
    getJson<Existing>(`/api/drafts/existing?${query.toString()}`, { signal: controller.signal }).then(
      (found) => setAnswer({ key, found }),
      () => setAnswer({ key, found: { draft: null } }),
    );
    return () => controller.abort();
  }, [key]);
  const checkReady = planDate !== null;
  const answered = answer !== null && answer.key === key;
  useEffect(() => {
    if (!key || !checkReady || answered) return;
    const timer = setTimeout(() => setGaveUp(key), LOOKUP_WAIT_MS);
    return () => clearTimeout(timer);
  }, [key, checkReady, answered]);
  // Once the wait is over, a late answer never shows, so the page never moves after it is drawn.
  const late = key !== null && gaveUp === key;
  const found = !late && answered ? answer.found : null;
  const draft = found && planDate ? ("by_plan_date" in found ? (found.by_plan_date[planDate] ?? null) : found.draft) : null;
  return { settled: key === null || answered || late, draft };
}

// What changed in the version the check shows, since the agency's version before it (ticket 21). It is read
// once the check is ready, since the latest-plan route learns the version's date from the check. A route
// that has no such comparison answers 404, and the page then shows neither the change line nor the list.
function usePlanChanges(pid: string, agencyId: string, planDate: string | null, search: string) {
  const [answer, setAnswer] = useState<{ key: string; changes: PlanChanges | null; failed: boolean; error: ApiError | null } | null>(null);
  const [attempt, setAttempt] = useState(0);
  const key = planDate ? withReadParams(`/api/projects/${encodeURIComponent(pid)}/procurement/${encodeURIComponent(agencyId)}/${planDate}/changes`, search) : null;
  useEffect(() => {
    if (!key) return;
    const controller = new AbortController();
    getJson<PlanChanges>(key, { signal: controller.signal }).then(
      (changes) => setAnswer({ key, changes, failed: false, error: null }),
      (error: unknown) => {
        if (controller.signal.aborted) return;
        const apiError = error instanceof ApiError ? error : null;
        setAnswer({ key, changes: null, failed: apiError?.status !== 404, error: apiError });
      },
    );
    return () => controller.abort();
  }, [key, attempt]);
  const found = answer && answer.key === key ? answer : null;
  return {
    changes: found?.changes ?? null,
    failed: found?.failed ?? false,
    error: found?.error ?? null,
    settled: found !== null,
    attempt,
    retry: () => setAttempt((n) => n + 1),
  };
}

// The change line when only the comparison failed: it says so and links the section below, which holds
// the alert and Try again.
export function ChangeLineError() {
  const line = words.changes;
  return (
    <p className="mt-2 text-body text-ink" data-change-line>
      {line.error}{" "}
      <TextLink href="#changes" className="whitespace-nowrap">
        {line.errorLink}
      </TextLink>
    </p>
  );
}

// The change section when only the comparison failed: the error takes the section body's place under its
// heading (the 21 brief, section 5.4), with the request's reference when the server gave one.
export function ChangesError({
  headingRef,
  error,
  onRetry,
  attempt,
}: {
  headingRef?: React.Ref<HTMLHeadingElement>;
  error: ApiError | null;
  onRetry: () => void;
  attempt: number;
}) {
  return (
    <section aria-labelledby="changes" data-changes="error">
      <EightColumns prose>
        <h2 ref={headingRef} id="changes" tabIndex={-1} className="scroll-mt-4 text-title text-ink-heading focus:outline-none">
          {copy.changes.titleUnknown}
        </h2>
        <div className="mt-2">
          <LoadError error={error} message={copy.changes.error} permission={copy.changes.error} onRetry={onRetry} retrying={false} attempt={attempt} />
        </div>
      </EightColumns>
    </section>
  );
}

// The change line under the method sentence, with its link to the change list below (#changes).
function ChangeLine({ changes }: { changes: PlanChanges }) {
  const line = words.changes;
  const prev = changes.previous ? <Num date={changes.previous.plan_date} /> : null;
  let text: ReactNode;
  let link = false;
  if (changes.state === "earliest") text = line.earliest;
  else if (changes.state === "previous_not_read") text = <Fill template={line.prevUnread} slots={{ prev_date: prev }} />;
  else if (!changed(changes.counts)) text = <Fill template={line.same} slots={{ prev_date: prev }} />;
  else {
    text = <Fill template={line.line} slots={{ prev_date: prev, change_list: <Unbroken text={changeList(changes.counts!)} /> }} />;
    link = true;
  }
  return (
    <p className="mt-2 text-body text-ink" data-change-line>
      {text}
      {link && (
        <>
          {" "}
          <TextLink href="#changes" className="whitespace-nowrap">
            {line.link}
          </TextLink>
        </>
      )}
    </p>
  );
}

export function CheckPlanPage({ pid, agencyId, version }: { pid: string; agencyId: string; version?: string }) {
  const path = withReadParams(`/api/projects/${encodeURIComponent(pid)}/procurement/${encodeURIComponent(agencyId)}${version ? `/${version}` : ""}`, useStore(address).search);
  const [load, retry] = useLoad<CheckPlanResult>(path);
  // The check read again after a baseline was saved or removed, shown in place of the first one.
  const [fresh, setFresh] = useState<{ path: string; result: CheckPlanResult } | null>(null);
  const changesHeading = useRef<HTMLHeadingElement>(null);
  const header = useRef<HTMLDivElement>(null);
  const finding = useRef<HTMLHeadingElement>(null);
  const slotId = useId();
  const search = useStore(address).search;
  const params = new URLSearchParams(search);
  // A preview as the server applied it (GET /api/me), so an officer's own ?view=piu is not one.
  const shownView = useStore(appliedView);
  const preview = shownView ? shownView.applied.preview : previewOf(search) !== null;
  const asOf = params.get("asof");
  const baselineView = useBaselineView();
  // The draft action's slot holds a button on today's check outside a preview.
  const slotShown = !preview && asOf === null;

  const result = load.status === "ready" ? (fresh && fresh.path === path ? fresh.result : load.data) : null;
  const ready = result && !result.abstention && result.plan && result.project && result.counts ? (result as CheckedPlan) : null;
  // The populated page waits, at most LOOKUP_WAIT_MS after the check is ready, for the notice that names an
  // open draft.
  const lookup = useExistingDraft(pid, agencyId, version, !preview, ready?.plan.plan_date ?? null);
  // What changed in this version is read from the start when the address names the version, and once the
  // check names it otherwise. The populated page waits for it, so the change line arrives with the check.
  const planChanges = usePlanChanges(pid, agencyId, version ?? ready?.plan.plan_date ?? null, search);
  const waiting = ready !== null && (!lookup.settled || !planChanges.settled);
  const checked = waiting ? null : ready;
  useScrollPadding(header, Boolean(checked), { gap: 8 });
  const { changes } = planChanges;
  const listed = changes !== null && changes.state === "compared" && changed(changes.counts);

  // "#changes" in the address, from "See what changed" or a link straight to it: the change list's heading takes
  // focus once it is drawn. The heading needs both the comparison and the check, and either may answer first,
  // so this runs again when each lands. It moves on the next frame, after the route change has focused the h1
  // (the 21 critique, round 3).
  const drawn = listed && checked !== null;
  useEffect(() => {
    let frame = 0;
    const follow = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
        if (window.location.hash !== "#changes" || !changesHeading.current) return;
        changesHeading.current.scrollIntoView({ block: "start" });
        changesHeading.current.focus({ preventScroll: true });
      });
    };
    if (drawn) follow();
    window.addEventListener("hashchange", follow);
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("hashchange", follow);
    };
  }, [drawn]);

  // The browser tab names the agency's plan once the check names it: "{agency}, plan of Oct 9, 2026".
  useEffect(() => {
    if (checked) setPageTitle(fill(copy.pages.checkPlan.windowTitle, { agency: checked.plan.implementing_agency, date: short(checked.plan.plan_date) }));
  }, [checked]);

  // The visually hidden status announces steps: checking, then how many activities were checked.
  // Any other end has its own alert or heading, so the status then says nothing.
  const total = checked?.counts.activities;
  const statusText =
    load.status === "loading" || waiting
      ? words.status.checking
      : total === undefined
        ? ""
        : total === 1
          ? words.status.checkedOne
          : words.status.checked(formatCount(total));

  // After a "Try again" that works, the finding takes focus, so a screen reader reads the result.
  useEffect(() => {
    if (load.status === "ready" && load.afterRetry) finding.current?.focus();
  }, [load]);

  const procurementHref = `/projects/${pid}/procurement`;
  const projectCrumb = (name: ReactNode): Crumb => ({ text: name, href: `/projects/${pid}` });
  // An ID from the address in Roboto Mono 500 (DESIGN.md section 5, Page header).
  const idText = <ProjectIdText pid={pid} />;
  const named = (name: string) => <Fill template={copy.breadcrumb.project} slots={{ name, pid: idText }} />;
  const unnamed = <Fill template={copy.breadcrumb.projectId} slots={{ pid: idText }} />;
  const trail = (project: ReactNode, last: ReactNode): Crumb[] => [
    { text: copy.breadcrumb.projects, href: "/projects" },
    projectCrumb(project),
    { text: copy.breadcrumb.procurement, href: procurementHref },
    { text: last },
  ];
  const versionCrumb = version ? copy.breadcrumb.plan(short(version)) : null;
  // The header's h1 and the line under it. With no agency's name, a known date makes the h1
  // "Procurement Plan of October 9, 2026" and nothing goes under it, so the words come once.
  const headerWords = (agency: ReactNode | null, planDate: string | undefined) =>
    agency
      ? { agency, plan: planDate ? planSubtitle(planDate) : undefined }
      : { agency: planDate ? planSubtitle(planDate) : words.agencyUnknown };

  let body: ReactNode;
  let crumbs: Crumb[];
  if (load.status === "loading" || waiting) {
    // The project's name is not known yet, so its link reads "Project P156634" to a screen reader.
    const loadingName = (
      <>
        <span className="sr-only">{unnamed}</span>
        <Skeleton className="inline-block h-[1em] w-[200px] align-middle" />
      </>
    );
    crumbs = trail(loadingName, versionCrumb ?? words.agencyUnknown);
    // Every state renders PlanCheckHeader first, so React keeps the one h1 that a route change
    // focused, and focus stays on it when the check arrives (DESIGN.md section 5, Page header).
    body = (
      <>
        <PlanCheckHeader
          agency={
            // An agency's name takes two lines below 768 px and one from it, as most do. Beside the pill and
            // the draft action (ticket 35), a long name takes two lines again from 1024 to 1199 px.
            <>
              <span className="sr-only">{words.status.checking}</span>
              {slotShown ? (
                <>
                  <SkeletonText className="@md/page:hidden @lg/page:flex @xl/page:hidden" widths={["w-full", "w-3/5"]} />
                  <SkeletonLine className="hidden @md/page:flex @lg/page:hidden @xl/page:flex" width="w-3/5 max-w-[560px]" />
                </>
              ) : (
                <>
                  <SkeletonText className="@md/page:hidden" widths={["w-full", "w-3/5"]} />
                  <SkeletonLine className="hidden @md/page:flex" width="w-3/5 max-w-[560px]" />
                </>
              )}
            </>
          }
          plan={<SkeletonLine width="w-60" />}
          pill={<Skeleton className="h-[30px] w-[170px] rounded-pill" />}
          // The draft action's places, so the rows stay put when the check arrives (ticket 35). Its caption
          // takes two lines below 768 px.
          action={slotShown ? <Skeleton className="h-11 w-56 rounded-pill" /> : undefined}
          feedforward={
            slotShown ? (
              <>
                <SkeletonText className="text-caption @md/page:hidden" widths={["w-60", "w-24"]} />
                <SkeletonLine className="hidden text-caption @md/page:flex" width="w-80" />
              </>
            ) : undefined
          }
          sticky={false}
        />
        <PlanCheckSkeleton slow={load.status === "loading" && load.slow} baseline={baselineView} />
        <p className="mt-6 max-w-[72ch] text-small text-ink-muted">{words.notVisible}</p>
      </>
    );
  } else if (load.status === "error") {
    crumbs = trail(unnamed, versionCrumb ?? words.agencyUnknown);
    body = (
      <>
        <PlanCheckHeader {...headerWords(null, version)} />
        <EightColumns className="mt-6">
          <LoadError
            error={load.error}
            message={words.error}
            permission={words.permission}
            onRetry={retry}
            retrying={load.retrying}
            attempt={load.attempt}
          />
        </EightColumns>
      </>
    );
  } else if (checked) {
    crumbs = trail(named(checked.project.display_name ?? checked.project.project_name), copy.breadcrumb.plan(short(checked.plan.plan_date)));
    const slot = draftSlot(checked);
    body = (
      <>
        <PlanCheckHeader
          headerRef={header}
          agency={checked.plan.implementing_agency}
          plan={planSubtitle(checked.plan.plan_date)}
          pill={checkPill(checked)}
          action={slot.action}
          feedforward={slot.feedforward}
        />
        <PlanCheck
          result={checked}
          findingRef={finding}
          changed={changedRows(changes)}
          afterMethod={
            <>
              {changes ? <ChangeLine changes={changes} /> : planChanges.failed && <ChangeLineError />}
              <div className="mt-4">
                <BaselinePanel
                  pid={pid}
                  agencyId={checked.plan.agency_id}
                  agency={checked.plan.implementing_agency}
                  planDate={checked.plan.plan_date}
                  baseline={checked.baseline ?? null}
                  view={baselineView}
                  readOnly={asOf !== null}
                  refresh={async () => {
                    const next = await getJson<CheckPlanResult>(path);
                    setFresh({ path, result: next });
                    return next;
                  }}
                />
              </div>
            </>
          }
          after={
            listed ? (
              <ChangeTables ref={changesHeading} changes={changes!} agency={checked.plan.implementing_agency} />
            ) : planChanges.failed ? (
              <ChangesError headingRef={changesHeading} error={planChanges.error} onRetry={planChanges.retry} attempt={planChanges.attempt} />
            ) : undefined
          }
        />
        {/* "Drafts from this check" (ticket 36): the Project Paper summary, at the end of the page. */}
        <div className="mt-8">
          <ProjectPaperPanel
            plan={{
              project_id: checked.plan.project_id,
              project_name: checked.project.display_name ?? checked.project.project_name,
              agency_id: checked.plan.agency_id,
              implementing_agency: checked.plan.implementing_agency,
              plan_date: checked.plan.plan_date,
            }}
            preview={preview}
            asOf={asOf !== null}
          />
        </div>
      </>
    );
  } else {
    const found = load.data;
    const abstention = found.abstention;
    const agency = abstention?.agency_name ?? abstention?.implementing_agency ?? found.plan?.implementing_agency ?? null;
    const knownAgency = abstention?.reason === "no_plan_from_agency" ? (abstention.agency_name ?? null) : agency;
    crumbs = trail(found.project ? named(found.project.display_name ?? found.project.project_name) : unnamed, versionCrumb ?? knownAgency ?? words.agencyUnknown);
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
        title = <Fill template={copy.projectPage.notFoundTitle} slots={{ pid: idText }} />;
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
        text = words.notPublicBody;
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
        <PlanCheckHeader {...headerWords(knownAgency, found.plan?.plan_date)} />
        <EightColumns className="mt-6">
          <EmptyState title={title} body={text} link={link} />
        </EightColumns>
      </>
    );
  }

  // The draft action (the 35 brief, section 5.1): from today's check only, never in a preview, which
  // draws nothing in the slot (brief 10), and only when check_plan marked an activity with a signal.
  function draftSlot(result: CheckedPlan): { action?: ReactNode; feedforward?: ReactNode } {
    const action = words.draftAction;
    if (preview) return {};
    if (asOf !== null) return { feedforward: <p className="text-caption text-ink-muted" data-draft-slot="asof">{action.asof}</p> };
    const count = result.counts.signal;
    if (count === 0) return { feedforward: <p className="max-w-[40ch] text-caption text-ink-muted @lg/page:text-right" data-draft-slot="none">{action.none}</p> };
    const start = () => {
      // The rows the notes will be on, in the plan check's order: needs a look first, then watch.
      const rank = (row: CheckedPlan["rows"][number]) => (row.marks.some((mark) => mark.mark === "needs_a_look") ? 0 : 1);
      const rows = result.rows
        .filter((row) => row.marks.some((mark) => mark.mark === "needs_a_look" || mark.mark === "watch"))
        .map((row, index) => ({ row, index }))
        .sort((a, b) => rank(a.row) - rank(b.row) || a.index - b.index)
        .map(({ row }) => row);
      const request = { kind: "review_notes" as const, project_id: result.plan.project_id, agency_id: result.plan.agency_id,
        plan_date: result.plan.plan_date, idempotency_key: newKey() };
      startWriting(request, result, rows);
      navigate(writingHref(result.plan.project_id, result.plan.agency_id, result.plan.plan_date));
    };
    return {
      action: (
        <Button variant="primary" aria-describedby={`${slotId}-description ${slotId}-feedforward`} onClick={start}
          className="w-full xs:w-auto" data-draft-action>
          {action.button(count, whole(count))}
        </Button>
      ),
      feedforward: (
        <>
          <p id={`${slotId}-feedforward`} className="text-caption text-ink-muted @lg/page:text-right" data-draft-slot="feedforward">
            {action.feedforward}
          </p>
          <span id={`${slotId}-description`} className="sr-only">
            {action.description}
          </span>
        </>
      ),
    };
  }

  return (
    <div data-check-plan-page={load.status}>
      <DraftNotices existing={lookup.draft} />
      <Breadcrumb trail={crumbs} />
      <div className="mt-4">{body}</div>
      <p role="status" className="sr-only">
        {statusText}
      </p>
    </div>
  );
}

// Above the page, in brief 06's alert slot's place: "I stopped writing ..." once after "Stop writing", and
// a notice naming the review notes the team already started on this plan version, newest first.
function DraftNotices({ existing }: { existing: ExistingDraft | null }) {
  // Read once, then cleared, so the notice shows on this visit only.
  const [stoppedHere] = useState(() => stopped.get());
  useEffect(() => stopped.set(null), []);
  const action = copy.checkPlan.draftAction;
  const notices: ReactNode[] = [];
  if (stoppedHere) {
    // Stop writing on the Project Paper summary (ticket 36) marks its way back with the kind.
    const said = stoppedHere.endsWith(PROJECT_PAPER_STOPPED) ? copy.checkPlan.ppAction.stopped : action.stopped;
    notices.push(<Alert key="stopped" state="info" live="status">{said}</Alert>);
  }
  if (existing) {
    const date = formatDate(existing.created_at.slice(0, 10));
    notices.push(
      <Alert key="existing" state="info" action={<TextLink href={draftHref(existing.draft_id)}>{action.existingLink}</TextLink>}>
        <span data-existing-draft>
          {existing.author.you ? action.existingYou(date) : action.existingTeammate(existing.author.name ?? "", date)}
        </span>
      </Alert>,
    );
  }
  if (notices.length === 0) return null;
  return <div className="mb-6 flex max-w-[72ch] flex-col gap-2">{notices}</div>;
}
