// Section 5 of the package workspace, "Check your criteria" (ticket 31; DESIGN.md section 5; the 31 brief). It is
// optional, so it starts collapsed (CollapsedSection) with a summary that says how many comparable packages
// published their qualification criteria, read with the page. Opened, it shows the intro, the paste field, the
// check line and removed box over everything below them, then four parts in the order of the argument: your
// criteria item by item, the rejected bids, the cost estimate and the lessons.
//
// The package-level run (rejected bids, cost estimate, lessons) starts the first time the section opens, not with
// the page, unless a saved run with the same comparable packages and records date came with the summary. A
// comparison runs only on "Compare the criteria", which saves the text first; it never reruns by itself. Closing
// the section cancels nothing. The pasted text travels only in the request's body and lives only in the page's
// state and the owner's saved run: never in an address, never in the evidence-open log.
//
// CheckCriteriaView draws every state from its props, so the design gallery shows each one; CheckCriteria reads,
// streams and keeps the state.
import { useCallback, useEffect, useId, useMemo, useRef, useState, type ReactNode, type Ref } from "react";
import { CircleX } from "lucide-react";
import { copy } from "../copy";
import { WHAT_I_DONT_DO, dataReadinessHref } from "../routes";
import type { Checks, Comparison, CriteriaSummary, PackageRun, RemovedEntry } from "../lib/criteria";
import { forgetLessons, publicListId, rememberCosts, rememberItems, rememberLessons, rememberPublic, rememberSides } from "../lib/criteria";
import { formatCount, formatNumber } from "../lib/format";
import { useLoad } from "../lib/load";
import { address } from "../lib/router";
import { streamEvents } from "../lib/sse";
import { useStore } from "../lib/store";
import { previewReason, withReadParams } from "../lib/view";
import { cx } from "../lib/cx";
import { Alert } from "./Alert";
import { Button } from "./Button";
import { CheckLine, RemovedBox, type Removed } from "./Checks";
import { CollapsedSection } from "./CollapsedSection";
import { CostEstimate } from "./CostLane";
import { CriteriaLessons, CriteriaNotes, CriteriaTable, markerNumbers, openFrom, Part, RejectedBids } from "./CriteriaParts";
import { Fill } from "./Fill";
import { Num } from "./Num";
import { Skeleton, SkeletonLine } from "./Skeleton";
import { Steps, type Step } from "./Steps";
import { TextLink } from "./TextLink";
import { SECTION_5, usePageNumbers } from "../lib/markers";

const words = copy.criteria;
export const SECTION_ID = "check-criteria";
const RUN_STEPS = ["notices", "reasons", "cost", "lessons", "checks"];
const COMPARE_STEPS = ["read", "find", "compare", "checks"];
// A comparison's failure codes the page gives itself: the request failed after the save (internal), or before it,
// so the text was not kept (unsaved). Each has its words under copy.criteria.errors.
const INTERNAL = "internal";
const UNSAVED = "unsaved";

export type StepState = { key: string; state: "running" | "done" };
export type RunState =
  | { status: "idle" }
  | { status: "running"; steps: StepState[] }
  | { status: "ready"; result: PackageRun }
  | { status: "error"; code: string; requestId?: string };
export type CompareState =
  | { status: "idle" }
  | { status: "running"; steps: StepState[]; previous: Comparison | null }
  | { status: "ready"; result: Comparison; stale: boolean }
  | { status: "error"; code: string; requestId?: string; previous: Comparison | null };
export type SummaryState =
  | { status: "loading" }
  | { status: "error"; requestId?: string; onRetry: () => void }
  | { status: "ready"; data: CriteriaSummary };

export type ViewProps = {
  summary: SummaryState;
  open: boolean;
  onToggle: () => void;
  run: RunState;
  comparison: CompareState;
  text: string;
  onText: (text: string) => void;
  onCompare: () => void;
  onRetryRun?: () => void;
  fieldError: "empty" | "tooLong" | null;
  edited: boolean;
  saveFailed?: boolean;
  preview: boolean;
  checks: Checks | null;
  announce?: string;
  headingRef?: Ref<HTMLHeadingElement>;
  // The section's id: #check-criteria on a page; the design gallery gives each sample its own.
  sectionId?: string;
  // The page's as-of date (?asof=), when it has one: each part's source line then says the records were read as
  // of it (the 31 brief, 5.7).
  asOf?: string | null;
};

function stepsOf(keys: string[], steps: StepState[]): Step[] {
  return steps.map((step) => ({ key: step.key, running: words.steps[step.key]?.running, done: words.steps[step.key]?.done, state: step.state }));
}

function Code({ code }: { code?: string }) {
  if (!code) return null;
  return (
    <p className="mt-2 text-caption text-ink-muted">
      <Fill template={words.code} slots={{ code: <span className="font-mono">{code}</span> }} />
    </p>
  );
}

function ErrorBlock({ message, code, onRetry }: { message: ReactNode; code?: string; onRetry?: () => void }) {
  return (
    <div data-part-error>
      <Alert
        state="error"
        action={onRetry && (
          <Button variant="secondary" onClick={onRetry}>
            {words.tryAgain}
          </Button>
        )}
      >
        {message}
      </Alert>
      <Code code={code} />
    </div>
  );
}

function Summary({ summary, compared }: { summary: CriteriaSummary; compared: Comparison | null }) {
  const n = summary.public_criteria_count;
  const nNum = <PublicCount summary={summary} />;
  if (summary.state === "no_comparables" || summary.state === "not_measurable") return <p>{words.summaryNoComparables}</p>;
  if (summary.state === "none_public") {
    return (
      <p>
        <Fill template={words.summaryNonePublic} slots={{ total: <Num value={summary.comparables_total} /> }} /> {words.summaryAlsoNonePublic}
      </p>
    );
  }
  if (compared && compared.item_count > 0) {
    const date = <Num date={compared.compared_at.slice(0, 10)} />;
    return (
      <p>
        {compared.item_count === 1 ? (
          <Fill template={words.summaryComparedOne} slots={{ date, n: nNum }} />
        ) : (
          <Fill template={words.summaryCompared} slots={{ date, count: formatCount(compared.item_count), n: nNum }} />
        )}{" "}
        {words.summaryAlso}
      </p>
    );
  }
  return (
    <p data-summary-text className="text-pretty">
      {n === 1 ? words.summaryOne : <Fill template={words.summary} slots={{ n: nNum }} />} {words.summaryAlso}
    </p>
  );
}

// How many comparable packages published their criteria: a tab stop that opens their list in the drawer (view A),
// in the summary and in the intro alike (the 31 brief, 7.1).
function PublicCount({ summary }: { summary: CriteriaSummary }) {
  return (
    <Num
      value={summary.public_criteria_count}
      check={{ tooltip: words.nTooltip, onOpen: (element) => openFrom(publicListId(summaryKey(summary)), element) }}
    />
  );
}

// The key the packages whose criteria are public are held under, for the drawer's list.
function summaryKey(summary: CriteriaSummary): string {
  return summary.signature;
}

// The words for a removed sentence follow what the server says it was (entry.source): an award notice is a record
// with no pages, so a reason quoted from it and not found is "not in the record it cites", and a reading is about
// your own words.
function toRemoved(entries: RemovedEntry[]): Removed[] {
  const reasons = copy.removed.reasons as Record<string, { item: string; joined: string }>;
  return entries.map((entry) => {
    const onRecord = entry.reason === "quote_not_on_page" && entry.source === "record_quote";
    const reading = entry.reason === "not_supported" && entry.source === "reading";
    const reason = onRecord ? words.quoteNotInSource : reading ? words.readingNotSupported : (reasons[entry.reason] ?? copy.removed.unknownReason);
    return { sentence: entry.sentence, reason: reason.item, reasonJoined: reason.joined };
  });
}

function SectionChecks({ checks, removed, compared }: { checks: Checks | null; removed: RemovedEntry[]; compared: boolean }) {
  if (!checks) return null;
  const noPages = checks.quotes_without_pages > 0;
  // The line counts what is on screen, as the answer panel's does (ticket 24), with check 4's judged part.
  const shown = checks.shown ?? checks;
  return (
    <div className="mt-6 flex flex-col gap-2" data-section-checks>
      <CheckLine
        numbers={shown.numbers}
        dates={shown.dates}
        quotes={shown.quotes}
        judged={checks.shown ? { judged: checks.shown.judged, proven: checks.shown.proven } : undefined}
        quoteWords={noPages ? words.quotesInSources : undefined}
        notChecked={[...(checks.checks_run.includes(4) ? [] : (["sentences"] as const)), "find_comparables"]}
        notCheckedText={compared ? [words.notCheckedItems] : []}
      />
      {removed.length > 0 && <RemovedBox removed={toRemoved(removed)} />}
    </div>
  );
}

function Refusal({ refusal }: { refusal: NonNullable<Comparison["refusal"]> }) {
  const lead = copy.refusals[refusal.key].lead;
  return (
    <div className="flex flex-col gap-2" data-refusal={refusal.key}>
      <p className="max-w-prose text-body text-ink">
        {lead} {refusal.partial ? words.refusal.partial : words.refusal.instead}
      </p>
      <p className="text-caption text-ink-muted">
        {/* Ticket 24's note and its "What I don't do" heading on How Strata works, as the answer panel links them. */}
        <Fill template={copy.answer.refusalNote} slots={{ link: <TextLink href={WHAT_I_DONT_DO.href}>{copy.answer.refusalLink}</TextLink> }} />
      </p>
    </div>
  );
}

function TableSkeleton() {
  return (
    <div aria-hidden="true" className="flex flex-col gap-3" data-criteria-skeleton>
      <SkeletonLine className="text-body" width="w-4/5" />
      <SkeletonLine className="text-caption" width="w-1/3" />
      <Skeleton className="h-12 w-full" />
      {[0, 1, 2, 3].map((row) => (
        <Skeleton key={row} className="h-[72px] w-full" />
      ))}
    </div>
  );
}

// Rejected bids while the run reads them (the 31 brief, 6.7): the count line, the intro, then three rows of three
// lines each, the size of what lands.
function RejectedSkeleton() {
  return (
    <div aria-hidden="true" className="flex flex-col gap-2" data-rejected-skeleton>
      <SkeletonLine className="text-body" width="w-3/5" />
      <SkeletonLine className="text-caption" width="w-11/12" />
      <div className="mt-2 flex flex-col gap-4 pl-2 @md/page:pl-4">
        {[0, 1, 2].map((row) => (
          <div key={row} className="flex flex-col gap-1">
            <SkeletonLine className="text-small" width="w-2/5" />
            <SkeletonLine className="text-small" width="w-3/5" />
            <SkeletonLine className="text-caption" width="w-1/3" />
          </div>
        ))}
      </div>
    </div>
  );
}

function PartOne({ comparison, readinessHref, steps, onRetry, asOf }: {
  comparison: CompareState; readinessHref: string; steps: ReactNode; onRetry: () => void; asOf: string | null;
}) {
  const shown = comparison.status === "ready" ? comparison.result : comparison.status === "running" || comparison.status === "error" ? comparison.previous : null;
  if (comparison.status === "idle") return null;
  // A save that failed before any comparison is said under the field alone (the 31 brief, 6.5).
  if (comparison.status === "error" && comparison.code === "store" && !comparison.previous) return null;
  return (
    <Part heading={words.items.heading} busy={comparison.status === "running"} partKey="items">
      {steps}
      {comparison.status === "ready" && comparison.stale && (
        <div className="mb-3">
          <Alert state="info">{words.items.staleComparables}</Alert>
        </div>
      )}
      {/* A failed save is said once, under the field. A content filter is no failure of Strata's: a plain
          sentence (brief 14's pattern). Any other code has its own sentence and "Try again". */}
      {comparison.status === "error" && comparison.code === "content_filter" && (
        <p className="max-w-prose text-body text-ink" data-content-filter>{words.errors.content_filter}</p>
      )}
      {comparison.status === "error" && comparison.code !== "content_filter" && comparison.code !== "store" && (
        <ErrorBlock message={words.errors[comparison.code] ?? words.items.error} code={comparison.requestId} onRetry={onRetry} />
      )}
      {comparison.status === "running" && !shown && <TableSkeleton />}
      {shown && shown.refusal && <Refusal refusal={shown.refusal} />}
      {shown && (!shown.refusal || shown.refusal.partial) && shown.items.length === 0 && !shown.refusal && (
        <p className="max-w-prose text-body text-ink" data-none-found>{words.items.noneFound}</p>
      )}
      {shown && (!shown.refusal || shown.refusal.partial) && shown.items.length > 0 && (
        <div className="mt-3" aria-busy={comparison.status === "running" || undefined}>
          <CriteriaTable comparison={shown} />
          <CriteriaNotes comparison={shown} readinessHref={readinessHref} asOf={asOf} />
        </div>
      )}
    </Part>
  );
}

function PasteField({ summary, text, onText, onCompare, fieldError, edited, comparing, preview, saveFailed }: {
  summary: CriteriaSummary; text: string; onText: (text: string) => void; onCompare: () => void; fieldError: ViewProps["fieldError"];
  edited: boolean; comparing: boolean; preview: boolean; saveFailed?: boolean;
}) {
  const id = useId();
  const hintId = useId();
  const countId = useId();
  const errorId = useId();
  const { max_chars: max, counter_left: left } = summary.limits;
  const near = text.length >= max - left;
  const described = [hintId, near ? countId : null, fieldError ? errorId : null].filter(Boolean).join(" ");
  const n = (value: number) => formatNumber(value, { compact: false });
  return (
    <div className="mt-4 flex flex-col" data-paste-field>
      <label htmlFor={id} className="text-small font-semibold text-ink">{words.field.label}</label>
      <textarea
        id={id}
        value={text}
        readOnly={preview}
        rows={8}
        aria-invalid={fieldError ? true : undefined}
        aria-describedby={described}
        onChange={(event) => onText(event.target.value)}
        className={cx(
          "mt-2 min-h-[10.5rem] w-full resize-y rounded-sm border bg-surface p-3 text-body text-ink @md/page:min-h-[13.5rem]",
          fieldError ? "border-error-icon" : "border-line-strong",
        )}
        data-criteria-text
      />
      <p id={hintId} className="mt-2 max-w-prose text-caption text-pretty text-ink-muted">{words.field.hint}</p>
      {near && (
        <p id={countId} className="text-caption text-ink-muted tabular-nums" data-char-count>
          <Fill template={words.field.count} slots={{ used: n(text.length), max: n(max) }} />
        </p>
      )}
      {fieldError && (
        <p id={errorId} className="mt-1 text-caption text-error" data-field-error>
          {fieldError === "empty" ? words.error.empty : <Fill template={words.error.tooLong} slots={{ max: n(max) }} />}
        </p>
      )}
      <div className="mt-3">
        <Button variant="secondary" onClick={onCompare} held={preview} aria-disabled={comparing || preview || undefined}
          className="w-full @md/page:w-auto" data-compare>
          {words.compare}
        </Button>
        {preview && <p className="mt-2 text-caption text-ink-muted" data-held-reason="compare_criteria">{previewReason("compare_criteria") ?? words.preview}</p>}
      </div>
      {comparing && <p className="mt-2 text-small text-ink-muted" data-compare-status>{words.status.running}</p>}
      {!comparing && edited && <p className="mt-2 text-caption text-ink-muted" data-edited>{words.status.edited}</p>}
      {saveFailed && (
        <p className="mt-2 flex items-start gap-2 text-caption text-error" data-save-failed>
          <CircleX aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-error-icon" />
          {words.errors.store}
        </p>
      )}
    </div>
  );
}

export function CheckCriteriaView(props: ViewProps) {
  const { summary, open, onToggle, run, comparison, preview, headingRef } = props;
  const data = summary.status === "ready" ? summary.data : null;
  const compared = comparison.status === "ready" ? comparison.result : comparison.status === "idle" ? null : comparison.previous;
  const result = run.status === "ready" ? run.result : null;
  // Numbered once per page (brief 28): section 1's "Advertised again" markers come first.
  const cited = useMemo(() => [...markerNumbers(result?.rejected ?? null, result?.lessons.groups ?? null).keys()], [result]);
  const numbers = usePageNumbers(SECTION_5, cited);
  const yours = useMemo(() => new Set((compared?.items ?? []).map((item) => item.item_key)), [compared]);
  const removed = [...(result?.removed ?? []), ...(compared?.removed ?? [])];
  const readiness = (from: string, keys: string[]) => dataReadinessHref(keys, from);
  const publicKeys = data?.public_sources ?? ["notices", "awards"];
  const state = data?.state;
  const runSteps = run.status === "running" && (
    <div className="mt-6" data-run-steps>
      <Steps steps={stepsOf(RUN_STEPS, run.steps)} reserveLines={6} announce={false} />
    </div>
  );
  const compareSteps = comparison.status === "running" && (
    <div className="mb-3" data-compare-steps>
      <Steps steps={stepsOf(COMPARE_STEPS, comparison.steps)} reserveLines={4} announce={false} />
    </div>
  );
  const body = data && (
    <div className="mt-6">
      {state === "ok" ? (
        <p className="max-w-prose text-body text-ink" data-criteria-intro>
          {data.public_criteria_count === 1 ? words.introOne : <Fill template={words.intro} slots={{ n: <PublicCount summary={data} /> }} />}
        </p>
      ) : (
        <div className="flex flex-col gap-2">
          <p className="max-w-prose text-body text-ink" data-criteria-intro>
            {words.introNonePublic}
          </p>
          <p className="text-caption">
            <TextLink href={readiness("compare_criteria", publicKeys)}>{words.introNonePublicLink}</TextLink>
          </p>
        </div>
      )}
      {state === "ok" && (
        <PasteField summary={data} text={props.text} onText={props.onText} onCompare={props.onCompare} fieldError={props.fieldError}
          edited={props.edited} comparing={comparison.status === "running"} preview={preview} saveFailed={props.saveFailed} />
      )}
      {run.status === "running" && <Skeleton className="mt-6 h-9 w-full" />}
      <SectionChecks checks={props.checks} removed={removed} compared={Boolean(compared && compared.items.length)} />
      {runSteps}
      <PartOne comparison={comparison} readinessHref={readiness("compare_criteria", compared?.sources.map((source) => source.key) ?? publicKeys)}
        steps={compareSteps} onRetry={props.onCompare} asOf={props.asOf ?? null} />
      <Part heading={words.rejected.heading} busy={run.status === "running"} partKey="rejected">
        {run.status === "running" && <RejectedSkeleton />}
        {run.status === "error" && <ErrorBlock message={words.rejected.error} code={run.requestId} onRetry={props.onRetryRun} />}
        {result && (
          <RejectedBids rejected={result.rejected} numbers={numbers} yourItems={yours} perGroup={data.limits.rows_per_group}
            readinessHref={readiness("rejected_bids", result.rejected.sources.map((source) => source.key))}
            asOf={props.asOf ? result.as_of : null} />
        )}
      </Part>
      <Part heading={copy.cost.heading} busy={run.status === "running"} partKey="cost">
        {/* The lane's reserved height: intro, title, subtitle, row B, the lane and the axis (the 31 brief, 6.8). */}
        {run.status === "running" && <Skeleton className="h-[19.5rem] w-full" />}
        {run.status === "error" && <ErrorBlock message={copy.cost.error} code={run.requestId} onRetry={props.onRetryRun} />}
        {result && (
          <CostEstimate cost={result.cost} readinessHref={readiness("compare_cost_estimates", result.cost.sources.map((source) => source.key))}
            asOf={props.asOf ?? null} />
        )}
      </Part>
      <Part heading={copy.criteriaLessons.heading} busy={run.status === "running"} partKey="lessons">
        {run.status === "running" && (
          <div aria-hidden="true" className="flex flex-col gap-4">
            <Skeleton className="h-40 w-full rounded-md" />
            <Skeleton className="h-40 w-full rounded-md" />
          </div>
        )}
        {run.status === "error" && <ErrorBlock message={copy.criteriaLessons.error} code={run.requestId} onRetry={props.onRetryRun} />}
        {result && <CriteriaLessons groups={result.lessons.groups} numbers={numbers} />}
      </Part>
    </div>
  );
  const noContent = state === "no_comparables" || state === "not_measurable";
  return (
    <>
      <CollapsedSection
        id={props.sectionId ?? SECTION_ID}
        eyebrow={words.eyebrow}
        number={words.number}
        heading={words.heading}
        headingRef={headingRef}
        sectionKey="check-criteria"
        state={summary.status === "loading" ? "loading" : summary.status === "error" ? "error" : noContent ? "empty" : "ready"}
        open={open && !noContent && summary.status === "ready"}
        onToggle={onToggle}
        showLabel={words.show}
        hideLabel={words.hide}
        busy={run.status === "running" || comparison.status === "running"}
        summary={data ? <Summary summary={data} compared={compared} /> : null}
        error={
          summary.status === "error" && (
            <div>
              <Alert state="error" action={<Button variant="secondary" onClick={summary.onRetry}>{words.tryAgain}</Button>}>
                {words.summaryError}
              </Alert>
              <Code code={summary.requestId} />
            </div>
          )
        }
      >
        {body}
      </CollapsedSection>
      <p aria-live="polite" className="sr-only" data-criteria-live>
        {props.announce}
      </p>
    </>
  );
}

// ── The section on a page ────────────────────────────────────────────────

function parseRequestId(error: unknown): string | undefined {
  const body = (error as { body?: Record<string, unknown> } | null)?.body;
  const id = body?.request_id ?? body?.trace_id;
  return typeof id === "string" ? id : undefined;
}

export function CheckCriteria({ base, version, preview }: {
  // The package's API path: /api/packages/{step_reference} or /api/planned-packages/{package_id}.
  base: string;
  // Changes when the comparable packages may have changed, such as a planned package's criteria.
  version?: string;
  preview: boolean;
}) {
  const here = useStore(address);
  const summaryPath = withReadParams(`${base}/criteria${version ? `?v=${encodeURIComponent(version)}` : ""}`, here.search);
  const [load, retry] = useLoad<CriteriaSummary>(summaryPath);
  const [open, setOpen] = useState(() => typeof window !== "undefined" && window.location.hash === `#${SECTION_ID}`);
  const [run, setRun] = useState<RunState>({ status: "idle" });
  const [comparison, setComparison] = useState<CompareState>({ status: "idle" });
  const [text, setText] = useState("");
  const [comparedText, setComparedText] = useState<string | null>(null);
  const [fieldError, setFieldError] = useState<ViewProps["fieldError"]>(null);
  const [saveFailed, setSaveFailed] = useState(false);
  const [checks, setChecks] = useState<Checks | null>(null);
  const [announce, setAnnounce] = useState("");
  const heading = useRef<HTMLHeadingElement>(null);
  const runAbort = useRef<AbortController | null>(null);
  const compareAbort = useRef<AbortController | null>(null);
  const seeded = useRef<string | null>(null);
  const data = load.status === "ready" ? load.data : null;
  const asOf = new URLSearchParams(here.search).get("asof");
  const view = new URLSearchParams(here.search).get("view") ?? "staff";

  // The summary brings the saved runs: they show at once, and the text comes back for its owner only.
  useEffect(() => {
    if (!data || seeded.current === data.signature) return;
    seeded.current = data.signature;
    rememberPublic(summaryKey(data), data.public, data.public_criteria_count);
    if (data.package_run) {
      setRun({ status: "ready", result: data.package_run });
      rememberCosts(data.package_run.cost);
      rememberLessons(data.package_run.lessons.groups);
      rememberSides(data.package_run);
    } else {
      setRun((current) => (current.status === "ready" ? { status: "idle" } : current));
    }
    const saved = data.comparison;
    if (saved?.result) {
      setComparison({ status: "ready", result: saved.result, stale: saved.stale });
      rememberItems(saved.result);
    }
    if (saved?.pasted_text && !text) {
      setText(saved.pasted_text);
      // When the newest comparison failed after its save, the table is from earlier text: the field says the
      // text changed since the comparison.
      setComparedText(saved.result ? (saved.text_compared ? saved.pasted_text : "") : null);
    }
    setChecks(data.section_checks);
    // The text is the person's own; a new summary never replaces what they typed.
  }, [data]);

  // The lessons leave the drawer's view F with the section.
  useEffect(() => forgetLessons, []);

  // A link to #check-criteria opens the section and moves focus to its heading.
  useEffect(() => {
    if (open && window.location.hash === `#${SECTION_ID}` && data) heading.current?.focus();
  }, [Boolean(data)]);

  const startRun = useCallback(async () => {
    runAbort.current?.abort();
    const controller = new AbortController();
    runAbort.current = controller;
    setRun({ status: "running", steps: [] });
    try {
      for await (const event of streamEvents(`${base}/criteria/run`, { view, asof: asOf }, { signal: controller.signal })) {
        const payload = event.data as Record<string, any>;
        if (event.type === "step") {
          setRun((current) => {
            const steps = current.status === "running" ? current.steps.filter((step) => step.key !== payload.id) : [];
            if (payload.status === "running") setAnnounce(words.steps[payload.id]?.running ?? "");
            return { status: "running", steps: [...steps, { key: payload.id, state: payload.status === "done" ? "done" : "running" }] };
          });
        } else if (event.type === "package_run") {
          const result = payload as PackageRun;
          rememberCosts(result.cost);
          rememberLessons(result.lessons.groups);
          rememberSides(result);
          setRun({ status: "ready", result });
          if (result.section_checks) setChecks(result.section_checks);
          setAnnounce(words.runDone);
        } else if (event.type === "error") {
          setRun({ status: "error", code: String(payload.code), requestId: payload.request_id });
          setAnnounce(words.runError);
        }
      }
    } catch (error) {
      if (controller.signal.aborted) return;
      setRun({ status: "error", code: "internal", requestId: parseRequestId(error) });
    }
  }, [base, view, asOf]);

  // The package-level run starts the first time the section opens, unless a saved run came with the summary.
  useEffect(() => {
    if (open && data && (data.state === "ok" || data.state === "none_public") && run.status === "idle") void startRun();
  }, [open, data, run.status, startRun]);

  const onCompare = useCallback(async () => {
    if (!data || preview || comparison.status === "running") return;
    const trimmed = text.trim();
    if (!trimmed) return setFieldError("empty");
    if (trimmed.length > data.limits.max_chars) return setFieldError("tooLong");
    setFieldError(null);
    setSaveFailed(false);
    compareAbort.current?.abort();
    const controller = new AbortController();
    compareAbort.current = controller;
    const previous = comparison.status === "ready" ? comparison.result : comparison.status === "idle" ? null : comparison.previous;
    setComparison({ status: "running", steps: [], previous });
    setAnnounce(words.status.running);
    let saved = false;
    try {
      for await (const event of streamEvents(`${base}/criteria/compare`, { text: trimmed, view, asof: asOf }, { signal: controller.signal })) {
        const payload = event.data as Record<string, any>;
        if (event.type === "saved") {
          saved = true;
          setComparedText(text);
        }
        if (event.type === "step") {
          setComparison((current) => {
            const steps = current.status === "running" ? current.steps.filter((step) => step.key !== payload.id) : [];
            if (payload.status === "running") setAnnounce(words.steps[payload.id]?.running ?? "");
            return { status: "running", steps: [...steps, { key: payload.id, state: payload.status === "done" ? "done" : "running" }], previous };
          });
        } else if (event.type === "comparison") {
          const result = payload as Comparison;
          rememberItems(result);
          setComparison({ status: "ready", result, stale: false });
          setComparedText(text);
          if (result.section_checks) setChecks(result.section_checks);
          setAnnounce(
            result.refusal ? copy.refusals[result.refusal.key].lead
              : result.items.length ? words.compareDone(result.items.length, formatCount(result.items.length))
                : words.noneFoundDone,
          );
        } else if (event.type === "error") {
          if (payload.code === "store") setSaveFailed(true);
          // A failure before the save means the text was not kept: the words never say it was.
          const failure = payload.code === "store" || saved ? String(payload.code) : UNSAVED;
          setComparison({ status: "error", code: failure, requestId: payload.request_id, previous });
          setAnnounce(words.errors[failure] ?? words.items.error);
        }
      }
    } catch (error) {
      if (controller.signal.aborted) return;
      const failure = saved ? INTERNAL : UNSAVED;
      setComparison({ status: "error", code: failure, requestId: parseRequestId(error), previous });
      setAnnounce(words.errors[failure]);
    }
  }, [data, preview, comparison, text, base, view, asOf]);

  const summary: SummaryState =
    load.status === "loading"
      ? { status: "loading" }
      : load.status === "error"
        ? { status: "error", requestId: parseRequestId(load.error), onRetry: retry }
        : { status: "ready", data: load.data };
  return (
    <CheckCriteriaView
      summary={summary}
      open={open}
      onToggle={() => setOpen((value) => !value)}
      run={run}
      comparison={comparison}
      text={text}
      onText={(next) => {
        setText(next);
        if (fieldError) setFieldError(null);
      }}
      onCompare={() => void onCompare()}
      onRetryRun={() => void startRun()}
      fieldError={fieldError}
      edited={comparedText !== null && text !== comparedText}
      saveFailed={saveFailed}
      preview={preview}
      checks={checks}
      announce={announce}
      headingRef={heading}
      asOf={asOf}
    />
  );
}
