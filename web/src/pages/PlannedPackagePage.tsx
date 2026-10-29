// A package planned from a sentence (the 15 brief), at /packages/new while I read the sentence and at
// /packages/:id once it is saved. One narrative column, columns 1 to 7 from a 1200 px window, so the evidence
// drawer opens into the free space beside it (DESIGN.md section 4, Page layouts, Workspace); all 12 below that.
//
// Top to bottom: the breadcrumb; the header, sticky from a page area of 768 px, with the title, "No STEP
// reference yet" and the saved stamp; the purpose; the "What I understood" card; and section 1, the past range
// of comparable packages, which find_comparables fills from the criteria that pick comparables. A change to a
// chip saves at once; a change to a chip that picks comparables reruns find_comparables, and only the latest
// request may draw. With no plan yet, section 1 asks for the plan before it shows the range, so the range
// doesn't set the plan. A dot or a table row opens its package's records in the evidence drawer.
//
// The reading page holds no package: nothing is saved until the reader has read the sentence. When the save
// returns, the address is replaced with the package's, quietly, so focus stays where it was and Back returns
// to where the person typed. A reload of /packages/new, with no reading behind it, goes to the Packages tab
// with the box in plan mode.
import { useCallback, useEffect, useId, useRef, useState, type ReactNode, type RefObject } from "react";
import * as RadixPopover from "@radix-ui/react-popover";
import { CircleX } from "lucide-react";
import { Alert } from "../components/Alert";
import { Breadcrumb } from "../components/Breadcrumb";
import { Button } from "../components/Button";
import { EmptyState } from "../components/Card";
import { ExampleNote } from "../components/ExampleNote";
import { EditorBody, EditorSheet } from "../components/ChipEditor";
import { CardTop, ChipGroups, ChipSkeletons, ComputedNote, CriterionChip, RefusalAlert, ruleSentence, valueText } from "../components/Criteria";
import { Fill } from "../components/Fill";
import { Num } from "../components/Num";
import { ApproachOptions, approachState } from "../components/ApproachOptions";
import { PastRange, TWO_LANE_HEIGHT, type PastRangeState } from "../components/PastRange";
import { Rebidding } from "../components/RebiddingBlock";
import type { EstimateState } from "../components/TimeEstimate";
import { plannedRebiddingPath } from "../lib/rebidding";
import { RisksSection } from "../components/RisksSection";
import { CheckCriteria } from "../components/CheckCriteria";
import { ExistingPpsdNotice } from "../components/ExistingDraftNotice";
import { PpsdAction, type RiskSelection } from "../components/PpsdAction";
import { StepTracker } from "../components/StepTracker";
import { StepsSection, type StepsState } from "../components/StepsSection";
import { PageHead } from "../components/PageHead";
import { StageLabel } from "../components/StageLabel";
import { TaskZone, ZoneBlock } from "../components/TaskZone";
import { Workspace as WorkspaceLayout } from "../components/Workspace";
import { useAnswerInPage } from "../components/AnswerSlot";
import { POPOVER } from "../components/Popover";
import { SkeletonLine } from "../components/Skeleton";
import { Steps, type Step } from "../components/Steps";
import { copy } from "../copy";
import { ApiError, getJson, type ComparablesResult, type EstimateResult } from "../lib/api";
import { usePlanDateChoice } from "../lib/estimates";
import { useLoad } from "../lib/load";
import { cx } from "../lib/cx";
import { formatCount, formatDate, formatYear } from "../lib/format";
import {
  comparablesPath,
  enterBoxMode,
  planning as planningStore,
  preloaded,
  savePackage,
  startPlanning,
  useOpenComparable,
  valueOf,
  type Change,
  type FieldValue,
  type FormField,
  type Handed,
  type PackageForm,
  type PlannedPackage,
  type PlannedPage,
  type Planning,
} from "../lib/packages";
import { staffRole } from "../lib/following";
import { address, navigate } from "../lib/router";
import { useStore } from "../lib/store";
import { setPageTitle } from "../lib/title";
import { DocumentColumn } from "./DraftPage";

const words = copy.packageWorkspace;
const NARROW = "(width < 48rem)";
// A rerun that answers within this long never shows the skeleton, so a quick change never flashes.
const SKELETON_AFTER_MS = 400;
// Dragging the plan line or holding an arrow key saves this long after the movement stops.
const PLAN_SAVE_AFTER_MS = 500;
// Section 1's plan prompt holds the chart's height, so the section does not jump when the chart replaces it: 392 px
// with lane 2, the time estimate (ticket 26).
const CHART_HEIGHT = TWO_LANE_HEIGHT;
// What describes a package to estimate_time (ticket 26): its comparables' criteria and its own fields. A save that
// changes one of these reads the time estimate again; a change of the plan alone does not.
const DESCRIBED = ["estimated_amount_usd", "market_approach", "review_type", "prequalification", "lots"];
const estimateKey = (pkg: PlannedPackage) => JSON.stringify([pkg.comparables_query, ...DESCRIBED.map((key) => valueOf(pkg, key))]);

function useNarrowWindow(): boolean {
  const [narrow, setNarrow] = useState(() => window.matchMedia(NARROW).matches);
  useEffect(() => {
    const query = window.matchMedia(NARROW);
    const update = () => setNarrow(query.matches);
    query.addEventListener("change", update);
    return () => query.removeEventListener("change", update);
  }, []);
  return narrow;
}

function previewOf(search: string): "piu" | "public" | null {
  const view = new URLSearchParams(search).get("view");
  return view === "piu" || view === "public" ? view : null;
}

export function titleOf(pkg: PlannedPackage, form: PackageForm): string {
  const description = valueOf(pkg, "description");
  const country = valueOf(pkg, "country");
  const name = country ? form.countries.find((one) => one.code === country)?.name : null;
  return description && name ? words.title(String(description), name) : words.titleNew;
}

export function PlannedPackagePage({ packageId, search }: { packageId: string | null; search: string }) {
  const preview = previewOf(search);
  if (preview === "public") return <PublicView />;
  if (packageId === null) return <ReadingPage />;
  return <SavedPackage packageId={packageId} preview={preview === "piu"} />;
}

// The public view holds no packages: the workspace and the Packages tab both show this (brief 7.5 and 7.9).
export function PublicView() {
  return (
    <DocumentColumn>
      <div data-planned-package="public">
        <h1 tabIndex={-1} className="sr-only">
          {copy.pages.plannedPackage.title}
        </h1>
        <EmptyState title={words.publicTitle} body={words.publicBody} link={{ href: "/projects", text: words.publicLink }} />
      </div>
    </DocumentColumn>
  );
}

// ── The header and its saved stamp ───────────────────────────────────────

export type Saving = { status: "saved"; at: string } | { status: "saving" } | { status: "failed" } | { status: "unsaved" };

// "Saved at 9:14 a.m.", in World Bank style.
function clockTime(iso: string): string {
  const parts = new Intl.DateTimeFormat("en-US", { hour: "numeric", minute: "2-digit", hour12: true }).formatToParts(new Date(iso));
  const hour = parts.find((part) => part.type === "hour")?.value ?? "";
  const minute = parts.find((part) => part.type === "minute")?.value ?? "";
  const period = (parts.find((part) => part.type === "dayPeriod")?.value ?? "").toLowerCase().replace(/([ap])m/, "$1.m.");
  return `${hour}:${minute} ${period}`;
}

function stampText(saving: Saving, now: number, preview: boolean): string {
  const s = words.stamp;
  if (preview) return s.preview;
  if (saving.status === "unsaved") return s.notSaved;
  if (saving.status === "saving") return s.saving;
  if (saving.status === "failed") return s.failed;
  const at = new Date(saving.at);
  const minutes = Math.floor((now - at.getTime()) / 60_000);
  if (minutes < 1) return s.justNow;
  if (minutes < 60) return s.minutes(minutes);
  if (new Date(now).toDateString() === at.toDateString()) return s.at(clockTime(saving.at));
  return s.on(formatDate(saving.at));
}

// The saved stamp: caption text, not a live region, refreshed once a minute in silence. A failed save shows
// "Not saved" with a "Try again" button.
export function SavedStamp({ saving, preview, onRetry }: { saving: Saving; preview: boolean; onRetry?: () => void }) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 60_000);
    return () => clearInterval(timer);
  }, []);
  useEffect(() => setNow(Date.now()), [saving]);
  return (
    <p data-saved-stamp={preview ? "preview" : saving.status} className={cx("flex flex-wrap items-center gap-2 text-caption", saving.status === "failed" ? "text-error" : "text-ink-muted")}>
      {/* The icon sits in the text's line, so the stamp keeps the reference line's baseline. */}
      <span>
        {saving.status === "failed" && !preview && <CircleX aria-hidden="true" className="mr-1 inline size-4 align-[-3px]" />}
        {stampText(saving, now, preview)}
      </span>
      {saving.status === "failed" && onRetry && !preview && (
        <Button variant="ghost" flush onClick={onRetry} className="h-6">
          {words.stamp.tryAgain}
        </Button>
      )}
    </p>
  );
}

// The page head (ticket 101; DESIGN.md section 5, Page head): the breadcrumb, parents only, the title as the h1, then
// the reference line in the ID line's place, which carries the saved stamp after "No STEP reference yet", and the
// purpose. It does not stick, and holds no action: "Suggest {n} PPSD risk rows" sits in zone 3. Below 768 px the stamp
// takes a line of its own.
function Header({
  title,
  stamp,
  headingRef,
  loading = false,
}: {
  title: ReactNode;
  stamp: ReactNode;
  headingRef?: RefObject<HTMLHeadingElement | null>;
  loading?: boolean;
}) {
  return (
    <div data-package-header>
      <PageHead
        trail={packagesOnly}
        held
        title={title}
        titleRef={headingRef}
        loading={loading}
        meta={
          loading ? (
            <SkeletonLine className="text-small" width="w-40" />
          ) : (
            <div className="flex flex-col gap-x-2 @md/page:flex-row @md/page:flex-wrap @md/page:items-baseline" data-reference-line>
              <p className="text-small text-ink-muted">{words.referenceNone}</p>
              {stamp && (
                <>
                  <span aria-hidden="true" className="hidden text-caption text-ink-muted @md/page:inline">
                    {copy.evidence.meta.dot}
                  </span>
                  {stamp}
                </>
              )}
            </div>
          )
        }
        purpose={words.purpose}
      />
    </div>
  );
}

// The breadcrumb names the page's parents only (DESIGN.md section 5, Page head), so a package's title shows once.
const packagesOnly = [{ text: words.breadcrumbPackages, href: "/packages" }];

// "What I understood" (the 15 brief): the sentence, the chips and the computed note, in an unnumbered Task zone panel
// before zone 1 (ticket 101), named by the zone's h2, whose id the editor and links name.
function UnderstoodZone({ children }: { children: ReactNode }) {
  return (
    <TaskZone name={words.card.heading} headingId="what-i-understood" panel sectionKey="understood" marks={{ "data-criteria-card": "" }}>
      <ZoneBlock data-block="understood">
        <div>{children}</div>
      </ZoneBlock>
    </TaskZone>
  );
}

// ── Reading the sentence ─────────────────────────────────────────────────

// Every step: each one done, then the one in progress, which is the next one not done while the stream is open,
// even before its own event comes, then the steps still to come, as "To do: ..." in ink-muted.
function readingSteps(current: Planning): Step[] {
  const s = words.steps;
  const by = Object.fromEntries(current.steps.map((step) => [step.id, step]));
  const order: (keyof typeof s)[] = current.read ? ["read", "compute", "save", "compare"] : ["save", "compare"];
  let running = false;
  return order.map((id) => {
    if (by[id]?.status === "done" && !running) return { key: id, running: s[id].running, done: s[id].done, state: "done" };
    if (!running) {
      running = true;
      return { key: id, running: s[id].running, done: s[id].done, state: "running" };
    }
    return { key: id, running: s[id].running, done: s[id].todo, state: "todo" };
  });
}

function ReadingPage() {
  const current = useStore(planningStore);
  const opening = useRef(false);
  const heading = useRef<HTMLHeadingElement>(null);

  // A reload, or an address with no reading behind it: the Packages tab, with the box in plan mode.
  useEffect(() => {
    if (current) return;
    navigate("/packages", { replace: true });
    enterBoxMode("plan");
  }, [current]);

  // Saved: hand the package and its schema to its page, and become that page in place.
  useEffect(() => {
    if (!current || !current.packageId || !current.package || !current.form || opening.current) return;
    opening.current = true;
    const id = current.packageId;
    const focusHeading = document.activeElement === heading.current;
    preloaded.set((all) => ({ ...all, [id]: { package: current.package!, form: current.form!, focusHeading } }));
    navigate(`/packages/${encodeURIComponent(id)}`, { replace: true, quiet: true });
  }, [current?.packageId, current?.form]);

  useEffect(() => setPageTitle(words.documentTitle(words.titleNew)), []);

  if (!current) return null;
  const failed = current.phase === "failed" || current.phase === "dropped";
  const message = current.phase === "dropped" ? words.readErrors.dropped : (words.readErrors[current.error ?? "internal"] ?? words.readErrors.internal);
  const retry = current.error !== "no_reader";
  return (
    <div data-planned-package={current.phase === "no_package" ? "no-package" : failed ? "failed" : "reading"} aria-busy={!failed && current.phase === "reading"}>
      <WorkspaceLayout
        head={<Header title={words.titleNew} headingRef={heading} stamp={<SavedStamp saving={{ status: "unsaved" }} preview={false} />} />}
      >
        <UnderstoodZone>
          <CardTop sentence={current.sentence} guesses={null} named={false} />
          {current.phase === "no_package" ? (
            <div className="mt-4" data-no-package>
              <h3 tabIndex={-1} className="text-h2 text-ink-heading">
                {words.noPackageTitle}
              </h3>
              <p className="mt-2 max-w-prose text-body text-ink">{words.noPackageBody}</p>
              <div className="mt-4 flex flex-wrap gap-3">
                <Button variant="primary" onClick={() => enterBoxMode("plan", current.sentence)}>
                  {words.changeSentence}
                </Button>
                <Button variant="secondary" onClick={() => startPlanning(current.sentence, false)}>
                  {words.setYourself}
                </Button>
              </div>
            </div>
          ) : failed ? (
            <div className="mt-4" data-read-error={current.error ?? current.phase}>
              <Alert
                state="error"
                live="alert"
                action={
                  <div className="flex flex-wrap gap-3">
                    {retry && (
                      <Button variant="primary" onClick={() => startPlanning(current.sentence, current.read)}>
                        {words.tryAgain}
                      </Button>
                    )}
                    <Button variant="secondary" onClick={() => startPlanning(current.sentence, false)}>
                      {words.setYourself}
                    </Button>
                  </div>
                }
              >
                {message}
              </Alert>
            </div>
          ) : (
            <>
              <div className="mt-4">
                <Steps steps={readingSteps(current)} reserveLines={4} />
              </div>
              <div className="mt-4">
                <ChipSkeletons form={current.form} />
              </div>
            </>
          )}
        </UnderstoodZone>
        {!failed && current.phase !== "no_package" && (
          <>
            <StageLabel>{copy.packagePage.stages.planning}</StageLabel>
            <PastRange state={{ status: "loading" }} quiet />
          </>
        )}
      </WorkspaceLayout>
    </div>
  );
}

// ── A saved package ──────────────────────────────────────────────────────

type Section =
  | { status: "loading" }
  | { status: "ready"; result: ComparablesResult; query: string }
  | { status: "error"; error: ApiError | null; query: string }
  | { status: "none" };

const queryKey = (pkg: PlannedPackage) => (pkg.comparables_query ? JSON.stringify(pkg.comparables_query) : "");

// The package as it looks the moment a change is made, before the server answers (the 15 brief: a chip shows
// its new value within 100 ms). The server's answer replaces it.
// An old method name such as ICB, only for a field that takes them: typed as a description, it is just words.
function aliasOf(form: PackageForm, change: Change) {
  if (change.action !== "set" || !form.fields.find((one) => one.key === change.field)?.aliases) return undefined;
  return form.aliases[String(change.value ?? "").trim().replace(/\s+/g, " ").replace(/[\u2018\u2019]/g, "'").toUpperCase()];
}

function applied(pkg: PlannedPackage, form: PackageForm, change: Change): PlannedPackage {
  const fields = pkg.fields.map((value): FieldValue => {
    if (value.key !== change.field) return value;
    if (change.action === "remove") return { ...value, value: null, provenance: null };
    if (change.action === "keep") return { ...value, provenance: "you" };
    if (change.action === "use_computed") return { ...value, value: value.computed, provenance: "computed" };
    const alias = aliasOf(form, change);
    return { ...value, value: alias ? alias.method : (change.value ?? null), provenance: "you" };
  });
  const alias = aliasOf(form, change);
  const withAlias = alias?.market_approach
    ? fields.map((value) => (value.key === "market_approach" ? { ...value, value: alias.market_approach, provenance: "you" as const } : value))
    : fields;
  return {
    ...pkg,
    fields: withAlias,
    guesses: withAlias.filter((value) => value.provenance === "guess").length,
    changed: [],
    approximate: change.field === "estimated_amount_usd" && change.action === "set" ? false : pkg.approximate,
  };
}

function SavedPackage({ packageId, preview }: { packageId: string; preview: boolean }) {
  // The reading page's hand-over, taken once: a later visit reads the package as it is then.
  const [handed] = useState<Handed | null>(() => preloaded.get()[packageId] ?? null);
  useEffect(() => {
    if (handed) preloaded.set(({ [packageId]: _taken, ...rest }) => rest);
  }, [handed, packageId]);
  const [page, setPage] = useState<{ status: "loading" } | { status: "ready"; data: PlannedPage } | { status: "error"; error: ApiError | null; attempt: number }>(
    handed ? { status: "ready", data: handed } : { status: "loading" },
  );
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (handed) return;
    const controller = new AbortController();
    getJson<PlannedPage>(`/api/planned-packages/${encodeURIComponent(packageId)}`, { signal: controller.signal }).then(
      (data) => setPage({ status: "ready", data }),
      (error: unknown) => {
        if (!controller.signal.aborted) setPage({ status: "error", error: error instanceof ApiError ? error : null, attempt });
      },
    );
    return () => controller.abort();
  }, [packageId, attempt]);

  if (page.status === "loading") return <LoadingPackage />;
  if (page.status === "error") {
    if (page.error?.status === 404) {
      return (
        <DocumentColumn>
          <div data-planned-package="not-found" className="min-h-svh">
            <Breadcrumb trail={packagesOnly} held />
            <h1 tabIndex={-1} className="sr-only">
              {copy.pages.plannedPackage.title}
            </h1>
            <EmptyState className="mt-4" title={words.notFoundTitle} body={words.notFoundBody} link={{ href: "/packages", text: words.notFoundLink }} />
          </div>
        </DocumentColumn>
      );
    }
    return (
      <DocumentColumn>
        <div data-planned-package="error" className="min-h-svh">
          <h1 tabIndex={-1} className="sr-only">
            {copy.pages.plannedPackage.title}
          </h1>
          <Alert
            state="error"
            live="alert"
            action={
              <Button variant="secondary" onClick={() => setAttempt((count) => count + 1)}>
                {words.tryAgain}
              </Button>
            }
          >
            {words.loadError}
          </Alert>
        </div>
      </DocumentColumn>
    );
  }
  return <Workspace initial={page.data} preview={preview} focusHeading={handed?.focusHeading ?? false} />;
}

function LoadingPackage() {
  return (
    <div data-planned-package="loading" aria-busy="true" className="min-h-svh">
      <WorkspaceLayout head={<Header title={words.loading} stamp={null} loading />}>
        <UnderstoodZone>
          <ChipSkeletons form={null} />
        </UnderstoodZone>
        <StageLabel>{copy.packagePage.stages.planning}</StageLabel>
        <PastRange state={{ status: "loading" }} />
      </WorkspaceLayout>
    </div>
  );
}

function Workspace({ initial, preview, focusHeading }: { initial: PlannedPage; preview: boolean; focusHeading: boolean }) {
  const form = initial.form;
  const [pkg, setPkg] = useState(initial.package);
  const [saving, setSaving] = useState<Saving>({ status: "saved", at: initial.package.saved_at });
  const [failedChange, setFailedChange] = useState<Change | null>(null);
  // The risks section's last failed save, which the saved stamp's "Try again" sends again (ticket 30).
  const retryRisks = useRef<(() => void) | null>(null);
  const [openKey, setOpenKey] = useState<string | null>(null);
  const [announce, setAnnounce] = useState("");
  const [section, setSection] = useState<Section>(initial.package.comparables_query ? { status: "loading" } : { status: "none" });
  const [updating, setUpdating] = useState(false);
  const [skeleton, setSkeleton] = useState(false);
  const [showWithout, setShowWithout] = useState(false);
  // How many reruns have answered, so the live region can say the section's new title once each.
  const [sayUpdated, setSayUpdated] = useState(0);
  const narrow = useNarrowWindow();
  const opening = useOpenComparable();
  const heading = useRef<HTMLHeadingElement>(null);
  const sectionHeading = useRef<HTMLHeadingElement>(null);
  const chips = useRef<Record<string, HTMLButtonElement | null>>({});
  const request = useRef<AbortController | null>(null);
  const planTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const editorHeading = useId();
  const plan = typeof valueOf(pkg, "plan_months") === "number" ? (valueOf(pkg, "plan_months") as number) : null;
  // Ticket 26: estimate_time for the package as saved, read again when a save changes what describes it.
  const [describedKey, setDescribedKey] = useState(() => estimateKey(initial.package));
  const estimatePath = pkg.comparables_query ? `/api/planned-packages/${encodeURIComponent(pkg.package_id)}/estimate` : null;
  const [estimateLoad, retryEstimate] = useLoad<EstimateResult>(estimatePath, describedKey);
  const estimate: EstimateState =
    estimateLoad.status === "loading"
      ? { status: "loading" }
      : estimateLoad.status === "error"
        ? { status: "error", error: estimateLoad.error, onRetry: retryEstimate, retrying: estimateLoad.retrying }
        : { status: "ready", result: estimateLoad.data };
  const planDate = usePlanDateChoice(
    `/api/planned-packages/${encodeURIComponent(pkg.package_id)}/plan-dates`,
    estimateLoad.status === "ready" ? estimateLoad.data.plan_date_choice : null,
    preview,
  );
  const title = titleOf(pkg, form);
  // Section 3's selection, for "Suggest {n} PPSD risk rows" (ticket 36). Suggested PPSD rows are a World Bank staff
  // draft (config/drafts.toml, staff_only), so a viewer without the role gets no action. The server reads the
  // criteria and the selection from this saved package, so the action sends only its id.
  const [selection, setSelection] = useState<RiskSelection | null>(null);
  // Section 2's answer, which the tracker under the criteria draws from (ticket 115).
  const [steps, setSteps] = useState<StepsState>({ status: "loading" });
  const staff = useStore(staffRole) !== false;
  const asOf = new URLSearchParams(useStore(address).search).has("asof");
  const ppsdPackage = { id: pkg.package_id, title: String(valueOf(pkg, "description") ?? title), step_reference: null };
  const ppsdAction = staff ? <PpsdAction pkg={ppsdPackage} selection={selection} preview={preview} asOf={asOf} /> : undefined;
  // An answer asked from the box: in the work's columns above the page head (ticket 98's answer slot; ticket 101).
  const asked = useAnswerInPage();
  // While the action is live it is the screen's one solid button, so section 1's "Show the past range" turns secondary.
  const ppsdLive = staff && !preview && !asOf && selection !== null && selection.chosen > 0 && !selection.saveFailed;

  useEffect(() => setPageTitle(words.documentTitle(title)), [title]);
  // Arriving from the reading page, whose h1 had focus: this page's h1 takes it, so focus stays where it was.
  useEffect(() => {
    if (focusHeading) heading.current?.focus({ preventScroll: true });
  }, [focusHeading]);

  // Leaving the page while the last save failed asks the browser's leave-page question; nothing else does.
  useEffect(() => {
    if (saving.status !== "failed") return;
    const onLeave = (event: BeforeUnloadEvent) => event.preventDefault();
    window.addEventListener("beforeunload", onLeave);
    return () => window.removeEventListener("beforeunload", onLeave);
  }, [saving.status]);

  // The criteria section 1 last asked find_comparables about, so a save that changes them reruns it.
  const fetched = useRef(queryKey(initial.package));
  const fetchComparables = useCallback((target: PlannedPackage, quiet = false) => {
    request.current?.abort();
    fetched.current = queryKey(target);
    if (!target.comparables_query) {
      setSection({ status: "none" });
      setUpdating(false);
      return;
    }
    const controller = new AbortController();
    request.current = controller;
    const query = queryKey(target);
    if (!quiet) setUpdating(true);
    const timer = setTimeout(() => setSkeleton(true), SKELETON_AFTER_MS);
    getJson<ComparablesResult>(comparablesPath(target.comparables_query), { signal: controller.signal })
      .then(
        (result) => {
          setSection({ status: "ready", result, query });
          if (!quiet) setSayUpdated((count) => count + 1);
        },
        (error: unknown) => {
          if (!controller.signal.aborted) setSection({ status: "error", error: error instanceof ApiError ? error : null, query });
        },
      )
      .finally(() => {
        clearTimeout(timer);
        if (request.current === controller) {
          setUpdating(false);
          setSkeleton(false);
        }
      });
  }, []);

  // The comparables the workflow found as it saved the package, or a read of them now.
  const planned = useStore(planningStore);
  const mine = planned && planned.packageId === initial.package.package_id ? planned : null;
  const started = useRef(false);
  useEffect(() => {
    if (started.current) return;
    if (mine && !mine.compared) return;
    started.current = true;
    if (mine?.comparables && initial.package.comparables_query) {
      setSection({ status: "ready", result: mine.comparables, query: queryKey(initial.package) });
    } else fetchComparables(initial.package, true);
    // Arriving from the reading page: say what was read, once.
    if (mine && mine.read) {
      const read = mine.steps.find((step) => step.id === "read");
      const count = read?.count ?? 0;
      const guesses = initial.package.guesses;
      setAnnounce(words.readDone(formatCount(count), guesses > 0 ? words.card.guesses(guesses, formatCount(guesses, { capital: true })) : ""));
    }
  }, [mine?.compared]);
  // Leaving aborts the read in flight. StrictMode's remount in the development build runs this cleanup and then
  // the effect above again, so the effect above must be free to start the read once more.
  useEffect(
    () => () => {
      request.current?.abort();
      started.current = false;
    },
    [],
  );
  // Once a rerun has drawn, say "Updated." with the section's title as it reads now: its finding, the
  // sentence that says why there is no range, or the plan prompt's count.
  useEffect(() => {
    if (sayUpdated === 0) return;
    const frame = requestAnimationFrame(() => {
      const shown = sectionHeading.current?.closest("section")?.querySelector("[data-finding], [data-no-chart] h3, [data-plan-prompt] [data-found]");
      const title = shown?.textContent?.replace(/\s+/g, " ").trim();
      if (title) setAnnounce(words.announce.updated(title));
    });
    return () => cancelAnimationFrame(frame);
  }, [sayUpdated]);

  const field = (key: string) => form.fields.find((one) => one.key === key)!;

  // Saves go out one after another, each once the one before it has answered, so the server always changes
  // the latest save and no change is lost to one made a moment before it (review round 2, P1).
  // The changes still waiting are drawn on top of each answer, so a chip never flips back while its own save waits.
  const queue = useRef<Promise<unknown>>(Promise.resolve());
  const lastSaved = useRef(initial.package);
  const waiting = useRef<Change[]>([]);
  const send = (change: Change) => {
    setSaving({ status: "saving" });
    waiting.current.push(change);
    queue.current = queue.current.then(() =>
      savePackage(lastSaved.current.package_id, change).then(
        ({ package: saved }) => {
          lastSaved.current = saved;
          setDescribedKey(estimateKey(saved));
          waiting.current = waiting.current.filter((one) => one !== change);
          setPkg(waiting.current.reduce((shown, next) => applied(shown, form, next), saved));
          if (waiting.current.length > 0) return;
          setFailedChange(null);
          setSaving({ status: "saved", at: saved.saved_at });
          if (saved.changed.length > 0) {
            // What a recompute changed replaces what was said, so nothing is heard twice.
            const said = saved.changed.map((one) => {
              const target = field(one.field);
              const label = target?.label ?? one.field;
              const cause = (field(one.cause)?.label ?? one.cause).toLowerCase();
              return one.to === null
                ? words.announce.emptied(label, cause)
                : words.announce.recomputed(label, valueText(target, one.from, form), valueText(target, one.to, form));
            });
            setAnnounce(said.join(" "));
          }
          if (queryKey(saved) !== fetched.current) fetchComparables(saved);
          else setUpdating(false);
        },
        () => {
          waiting.current = waiting.current.filter((one) => one !== change);
          setFailedChange(change);
          setSaving({ status: "failed" });
          setUpdating(false);
          setAnnounce(words.saveFailed);
        },
      ),
    );
  };

  const commit = (change: Change, options: { keepEditor?: boolean } = {}) => {
    if (preview) return;
    const target = field(change.field);
    const next = applied(pkg, form, change);
    const value = next.fields.find((one) => one.key === change.field);
    setPkg(next);
    if (!options.keepEditor) {
      setOpenKey(null);
      requestAnimationFrame(() => chips.current[change.field]?.focus());
    }
    const label = target.label;
    const shown = value?.value === null || value?.value === undefined ? "" : valueText(target, value.value, form);
    if (change.action === "remove") setAnnounce(words.announce.removed(label));
    else if (change.action === "keep") {
      setAnnounce(`${words.announce.kept(label, shown)} ${next.guesses > 0 ? words.card.guesses(next.guesses, formatCount(next.guesses, { capital: true })) : words.card.noGuesses}`);
    } else if (target.picks) {
      setUpdating(true);
      setAnnounce(words.announce.setPicks(label, shown));
    } else setAnnounce(words.announce.set(label, shown));
    send(change);
  };

  // The plan chip and the plan line are one value: a move of the line shows in the chip at once and saves
  // once the movement stops.
  const onPlanMoved = (months: number) => {
    if (preview) return;
    setPkg((now) => applied(now, form, { field: "plan_months", action: "set", value: months }));
    clearTimeout(planTimer.current);
    planTimer.current = setTimeout(() => send({ field: "plan_months", action: "set", value: months, plan_before_range: false }), PLAN_SAVE_AFTER_MS);
  };
  useEffect(() => () => clearTimeout(planTimer.current), []);

  const chip = (target: FormField) => {
    const value = pkg.fields.find((one) => one.key === target.key) ?? { key: target.key, group: target.group, value: null, provenance: null, computed: null };
    const open = openKey === target.key;
    const body = (
      <EditorBody
        key={`${target.key}-${String(value.value)}-${value.provenance}`}
        field={target}
        value={value}
        form={form}
        approximate={pkg.approximate}
        preview={preview}
        headingId={editorHeading}
        rule={target.source === "computed" ? ruleSentence(target, pkg, form) : null}
        onCommit={commit}
      />
    );
    const button = (
      <CriterionChip
        field={target}
        value={value}
        form={form}
        approximate={pkg.approximate}
        open={open}
        buttonRef={(element) => {
          chips.current[target.key] = element;
        }}
        onChoose={() => setOpenKey(open ? null : target.key)}
      />
    );
    if (narrow) {
      return (
        <span key={target.key} className="contents">
          {button}
          {open && (
            <EditorSheet
              labelledBy={editorHeading}
              onClose={() => {
                setOpenKey(null);
                requestAnimationFrame(() => chips.current[target.key]?.focus());
              }}
            >
              {body}
            </EditorSheet>
          )}
        </span>
      );
    }
    return (
      <RadixPopover.Root key={target.key} open={open} onOpenChange={(next) => !next && setOpenKey((now) => (now === target.key ? null : now))}>
        <RadixPopover.Anchor asChild>
          <span className="inline-flex max-w-full">{button}</span>
        </RadixPopover.Anchor>
        <RadixPopover.Portal>
          <RadixPopover.Content
            role="dialog"
            aria-labelledby={editorHeading}
            side="bottom"
            align="start"
            sideOffset={8}
            collisionPadding={16}
            data-chip-editor="popover"
            onCloseAutoFocus={(event) => {
              event.preventDefault();
              chips.current[target.key]?.focus();
            }}
            onInteractOutside={(event) => {
              // A press on another chip opens that chip's editor instead.
              if ((event.target as Element | null)?.closest?.("[data-chip]")) event.preventDefault();
            }}
            className={cx(POPOVER, "w-[min(320px,calc(100vw-32px))] p-4")}
          >
            {body}
          </RadixPopover.Content>
        </RadixPopover.Portal>
      </RadixPopover.Root>
    );
  };

  // ── Section 1 ──
  const result = section.status === "ready" ? section.result : null;
  const rangeable = result !== null && result.abstention === null && result.rows.length >= result.thresholds.min_comparables;
  const prompting = rangeable && plan === null && !showWithout;
  const missing = pkg.missing.map((key) => field(key)).filter(Boolean);
  let state: PastRangeState;
  if (section.status === "ready" && !skeleton) state = { status: "ready", result: section.result };
  else if (section.status === "error" && !skeleton)
    state = {
      status: "error",
      error: section.error,
      retrying: false,
      attempt: 0,
      onRetry: () => fetchComparables(pkg),
      message: saving.status === "failed" ? words.section.errorUnsaved : words.section.error,
    };
  else state = { status: "loading" };

  // What the package still lacks, as section 1 and section 3 name it: "the category and the country".
  const missingParts = missing.map((one) => one.add_label.replace(new RegExp(`^${words.section.missingStart} `), ""));
  const missingList =
    missingParts.length > 1 ? `${missingParts.slice(0, -1).join(copy.list.comma)}${copy.list.and}${missingParts[missingParts.length - 1]}` : missingParts[0];
  let body: ReactNode = undefined;
  if (missing.length > 0) {
    const [first, ...rest] = missing.map((one) => one.add_label);
    const list = [first, ...rest.map((label) => label.replace(new RegExp(`^${words.section.missingStart} `), ""))];
    const joined = list.length > 1 ? `${list.slice(0, -1).join(copy.list.comma)}${copy.list.and}${list[list.length - 1]}` : list[0];
    body = (
      <div className="mt-4 flex items-start" style={{ minHeight: CHART_HEIGHT / 2 }} data-missing>
        <p className="max-w-prose text-body text-ink">
          <Fill template={words.section.missing} slots={{ list: joined }} />
        </p>
      </div>
    );
  } else if (prompting && result) {
    body = (
      <PlanPrompt
        result={result}
        maxMonths={form.max_months}
        preview={preview}
        onPlan={(months) => commit({ field: "plan_months", action: "set", value: months, plan_before_range: true }, { keepEditor: true })}
        onWithout={() => setShowWithout(true)}
        showRangeVariant={ppsdLive ? "secondary" : "primary"}
      />
    );
  }

  const lead = result && missing.length === 0 ? <CriteriaLine result={result} /> : undefined;
  // With too few comparables, or none it could measure, how to compare with more follows the reason.
  const abstained = result?.abstention?.reason === "too_few_comparables" || result?.abstention?.reason === "none_measurable";
  const more = abstained && missing.length === 0 ? (
    <p className="mt-2 max-w-prose text-body text-ink" data-more>
      {words.section.more}
    </p>
  ) : undefined;

  return (
    <div data-planned-package="ready">
      <WorkspaceLayout
        answer={asked}
        head={
          <>
            {/* Ticket 36's notices about suggested PPSD rows on this package sit above the head, as on a STEP row's page. */}
            <ExistingPpsdNotice packageKey={pkg.package_id} />
            <Header
              headingRef={heading}
              title={title}
              stamp={
                <SavedStamp
                  saving={saving}
                  preview={preview}
                  onRetry={failedChange ? () => send(failedChange) : retryRisks.current ? () => retryRisks.current?.() : undefined}
                />
              }
            />
            {initial.example && <ExampleNote className="mt-4">{copy.home.exampleNotes.package(formatDate(pkg.created_at))}</ExampleNote>}
          </>
        }
      >
        <UnderstoodZone>
          <CardTop sentence={pkg.sentence} guesses={pkg.guesses} preview={preview} named={false} />
          {pkg.refusal === "dividing" && <RefusalAlert />}
          <div className="mt-4">
            <ChipGroups form={form} chip={chip} />
          </div>
          <ComputedNote pkg={pkg} form={form} />
        </UnderstoodZone>
        <StageLabel>{copy.packagePage.stages.planning}</StageLabel>
        {/* Zone 1, the past range, read from the criteria that pick comparables. */}
        <PastRange
          state={state}
          headingRef={sectionHeading}
          open={opening}
          planned={{ months: plan, onChange: onPlanMoved }}
          body={body}
          status={updating ? words.section.updating : undefined}
          busy={updating}
          lead={lead}
          more={more}
          quiet
          after={(comparing) => (
            <Rebidding
              path={pkg.comparables_query && missing.length === 0 ? plannedRebiddingPath(pkg.comparables_query) : null}
              section={section.status === "ready" && !skeleton ? section.result : null}
              sectionFailed={section.status === "error" && !skeleton}
              comparing={comparing}
            />
          )}
          estimate={pkg.comparables_query ? estimate : undefined}
          planDate={planDate}
        />
        {/* Where each step stands (ticket 115), from zone 2's answer: a package from a sentence has no plan yet. It
            follows zone 1, so the finding leads (ticket 101). */}
        <div className="my-4">
          <StepTracker state={steps} />
        </div>
        {/* Zone 2, the planned date for each STEP step (ticket 27): it reruns when a criterion changes, since the
            method family and the comparables follow the criteria. */}
        <StepsSection packageKey={pkg.package_id} kind="planned" rerunKey={`${queryKey(pkg)}|${pkg.missing.join(",")}`} onState={setSteps} />
        {/* Zone 3, procurement risks and what helped (ticket 30): it reruns with zone 1's criteria, and its selection
            saves with the package under the saved stamp and tells the page what is selected, for "Suggest {n} PPSD
            risk rows" (ticket 36), which it holds. */}
        <RisksSection
          apiHref={`/api/planned-packages/${pkg.package_id}`}
          packageKey={pkg.package_id}
          kind="planned"
          rerunKey={`${queryKey(pkg)}|${pkg.missing.join(",")}`}
          preview={preview}
          missingList={missingList}
          onSaveState={(state, retry) => {
            retryRisks.current = state === "failed" ? retry : null;
            setSaving(state === "saved" ? { status: "saved", at: new Date().toISOString() } : { status: state });
          }}
          onSelection={setSelection}
          action={ppsdAction}
        />
        {/* Zone 4, procurement approach options (ticket 26), from zone 1's time estimate. */}
        <ApproachOptions
          state={
            section.status === "none" || missing.length > 0
              ? { kind: "empty" }
              : approachState(
                  section.status === "ready" ? { status: "ready", result: section.result } : section.status === "error" ? { status: "error" } : { status: "loading" },
                  estimate,
                  prompting,
                  () => fetchComparables(pkg),
                )
          }
        />
        <StageLabel>{copy.packagePage.stages.tender}</StageLabel>
        {/* Zone 5, "Check your criteria" (ticket 31), on this package's comparables: a change of criteria reads its
            summary again. */}
        <CheckCriteria base={`/api/planned-packages/${encodeURIComponent(pkg.package_id)}`} version={queryKey(pkg)} preview={preview} />
      </WorkspaceLayout>
      <p role="status" className="sr-only" data-workspace-live>
        {announce}
      </p>
    </div>
  );
}

// The criteria find_comparables used, as it returned them, under section 1's heading.
function CriteriaLine({ result }: { result: ComparablesResult }) {
  const criteria = result.criteria;
  if (!criteria) return null;
  const s = words.section;
  const parts = [criteria.category, criteria.method, criteria.market_approach, criteria.review_type ? s.review(criteria.review_type) : null, criteria.country_name]
    .filter((part): part is string => Boolean(part));
  const from = formatYear(Number(criteria.notice_from.slice(0, 4)));
  const to = formatYear(Number(criteria.notice_to.slice(0, 4)));
  parts.push(s.notices(from, to));
  return (
    <p className="text-small text-ink-muted" data-criteria-line>
      <Fill template={s.criteria} slots={{ list: parts.join(copy.list.comma) }} />
    </p>
  );
}

// Section 1's body while the package has no plan and the person has not chosen to see the range without one:
// the forcing question before the range (the 15 brief, section 4), at the chart's height.
export function PlanPrompt({
  result,
  maxMonths,
  preview,
  onPlan,
  onWithout,
  showRangeVariant = "primary",
}: {
  result: ComparablesResult;
  maxMonths: number;
  preview: boolean;
  onPlan: (months: number) => void;
  onWithout: () => void;
  // "Show the past range" is the screen's one solid button until ticket 36's "Suggest PPSD risk rows" takes
  // that place (brief 36), when it turns secondary.
  showRangeVariant?: "primary" | "secondary";
}) {
  const [text, setText] = useState("");
  const [invalid, setInvalid] = useState(false);
  const inputId = useId();
  const errorId = useId();
  const count = result.counts?.comparables ?? result.rows.length;
  const show = () => {
    const raw = text.trim().replace(",", ".");
    const months = Number(raw);
    if (!/^\d+(\.\d)?$/.test(raw) || months < 0.5 || months > maxMonths) {
      setInvalid(true);
      return;
    }
    onPlan(months);
  };
  return (
    <div className="mt-4 flex flex-col gap-3" style={{ minHeight: CHART_HEIGHT }} data-plan-prompt>
      <p className="max-w-prose text-body text-ink">{words.section.promptQuestion}</p>
      <p className="text-body text-ink" data-found>
        <Fill template={words.section.promptFound(count, "{n}")} slots={{ n: <Num count={count} /> }} />
      </p>
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
        <label htmlFor={inputId} className="text-small font-semibold text-ink">
          {words.section.promptLabel}
        </label>
        <span className="flex items-center gap-2">
          <input
            id={inputId}
            type="text"
            inputMode="decimal"
            autoComplete="off"
            value={text}
            disabled={preview}
            aria-invalid={invalid || undefined}
            aria-describedby={invalid ? errorId : undefined}
            onChange={(event) => {
              setText(event.target.value);
              setInvalid(false);
            }}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                event.preventDefault();
                show();
              }
            }}
            className={cx(
              "h-11 w-[88px] rounded-sm border bg-surface px-3 text-right text-body text-ink tabular-nums",
              invalid ? "border-error-icon" : "border-line-strong",
            )}
          />
          <span className="text-small text-ink">{copy.pastRange.control.unit}</span>
        </span>
      </div>
      <p id={errorId} className="min-h-[1.5em] text-caption text-error">
        {invalid && words.editor.errors.months(String(maxMonths))}
      </p>
      <div className="flex flex-wrap gap-3">
        <Button variant={showRangeVariant} onClick={show} held={preview}>
          {words.section.showRange}
        </Button>
        {/* Flush, so its label keeps to the text's edge when the buttons stack (DESIGN.md section 5, Buttons). */}
        <Button variant="ghost" flush onClick={onWithout}>
          {words.section.showWithout}
        </Button>
      </div>
      {preview && <p className="text-caption text-ink-muted">{words.preview}</p>}
    </div>
  );
}
