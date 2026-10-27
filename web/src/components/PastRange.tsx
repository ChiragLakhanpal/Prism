// Section 1 of the package workspace, "How long it took" (the 12 brief): find_comparables' result as
// a card with the finding as its title, the plan control, lane 1 of the range chart, the summary,
// the note on what "comparable" meant, the coverage line, the source line and a "Show the table" twin.
//
// States: loading (static skeletons sized like the content), populated (20 to 60 comparables, one dot
// each), more than 60 (20 quantile dots), no plan dates (no line until you type a number), the
// abstention below 20 comparables (no band, no middle, no 8-in-10 line and no "in 10" anywhere, and
// the table opens by default), no comparable package, packages matched but none measurable, a package
// with no public notice to measure from, and an error with "Try again".
//
// Every number is the tool's. The plan line's readout, the slider's value text and the table's last
// column count the returned rows signed within the line's months; the title states the finding at
// the plan row's own months, as the tool counted it. Below 768 px the summary comes before the chart
// in the page's order, so the sentence leads and focus never jumps.
//
// Every width here is the page area's, not the window's, since the evidence drawer narrows it
// (DESIGN.md section 4): the classes are container queries on the page column (@md/page:, @lg/page:),
// and the summary's place follows the page column's width too. The one exception is the table twin,
// which reads its own frame's width (@table-fit/table:, 49rem), as the comment at its columns says.
import { useCallback, useEffect, useId, useLayoutEffect, useRef, useState, type ReactNode, type Ref, type RefObject } from "react";
import { CircleDashed } from "lucide-react";
import { copy } from "../copy";
import type { ApiError, Comparable, ComparablesResult, Comparison } from "../lib/api";
import { forgetDotList, openWentWith, rememberDots, type OpenComparable } from "../lib/packages";
import {
  CompareControl,
  dotComparisonName,
  estimated,
  EstimateExtras,
  EstimateSentences,
  lane2Alt,
  lane2For,
  optionWords,
  TimeEstimateTable,
  wentWithCell,
  type EstimateState,
  type PlanDateProps,
} from "./TimeEstimate";
import { cx } from "../lib/cx";
import { formatCount, formatDate, formatNumber } from "../lib/format";
import { dataReadinessHref } from "../routes";
import { Button } from "./Button";
import { CoverageLine } from "./Checks";
import { Fill, Joined } from "./Fill";
import { LoadError } from "./LoadError";
import { MonoWords } from "./MonoWords";
import { Num, type NumCheck } from "./Num";
import { axisFor, chartType, RangeChart, type PlanMove, type RangeMark } from "./RangeChart";
import { Skeleton, SkeletonLine, SkeletonText } from "./Skeleton";
import { Source } from "./Source";
import { Table, type Column, type Row } from "./Table";
import { TextLink } from "./TextLink";

const words = copy.pastRange;
const PAGE = 20;
// The chart's height: 240 px for lane 1 alone (ticket 12), and 392 px with lane 2, the time estimate (ticket 26).
const CHART_HEIGHT = 240;
export const TWO_LANE_HEIGHT = 392;

const months1 = (value: number) => formatNumber(value, { decimals: 1, compact: false });
const whole = (value: number) => formatNumber(value, { compact: false });
// A count standing alone in a sentence: one to nine in words (DESIGN.md section 7, rule 12).
const spelled = (value: number) => formatCount(value);
const tableDate = (iso: string) => formatDate(iso, { style: "table" });

export type PastRangeState =
  | { status: "loading" }
  | { status: "error"; error: ApiError | null; retrying: boolean; attempt: number; onRetry: () => void; message?: string }
  | { status: "ready"; result: ComparablesResult };

// Whether the page area is narrower than 48rem, the width @md/page: starts at. It measures the page
// column around the element (the app's and the gallery's Frame both have one), or the window where
// there is none. The first guess is the window's, and the page column's width replaces it before the
// first paint, so the summary never moves on screen. It reads the exact width, as the container
// queries do, since clientWidth rounds and a page area beside the drawer has fractions of a pixel.
function usePageNarrow(element: RefObject<HTMLElement | null>): boolean {
  const [narrow, setNarrow] = useState(() => typeof window !== "undefined" && window.matchMedia("(width < 48rem)").matches);
  useLayoutEffect(() => {
    const column = element.current?.closest<HTMLElement>("[data-page-column]") ?? document.documentElement;
    const update = () => {
      const rem = parseFloat(getComputedStyle(document.documentElement).fontSize) || 16;
      setNarrow(column.getBoundingClientRect().width < 48 * rem);
    };
    update();
    const observer = new ResizeObserver(update);
    observer.observe(column);
    return () => observer.disconnect();
  }, [element]);
  return narrow;
}

function useWidth<T extends HTMLElement>(): [RefObject<T | null>, number] {
  const element = useRef<T>(null);
  const [width, setWidth] = useState(0);
  useLayoutEffect(() => {
    const node = element.current;
    if (!node) return;
    const update = () => setWidth(Math.floor(node.clientWidth));
    update();
    const observer = new ResizeObserver(update);
    observer.observe(node);
    return () => observer.disconnect();
  }, []);
  return [element, width];
}

// Ticket 15: a dot or a table row opens its comparable package in the evidence drawer, and the opened one
// stays marked (web/src/lib/packages.ts, useOpenComparable); and for a package planned from a sentence, the
// plan is the person's own months, kept in their plan chip, rather than a plan row's dates.
export type PlannedMonths = { months: number | null; onChange: (months: number) => void };

export function PastRange({
  state,
  headingRef,
  open,
  planned,
  body,
  status,
  busy = false,
  lead,
  more,
  quiet = false,
  after,
  estimate,
  planDate,
}: {
  state: PastRangeState;
  headingRef?: Ref<HTMLHeadingElement>;
  open?: OpenComparable;
  planned?: PlannedMonths;
  // Ticket 26: estimate_time's answer, which draws lane 2, "Compare with" in the heading row, the summary's lane 2
  // sentences, the track record and the plan-date choice. Without it the section is ticket 12's lane 1 alone.
  estimate?: EstimateState;
  planDate?: PlanDateProps;
  // The section's body in place of the result, such as a planned package's plan prompt (ticket 15).
  body?: ReactNode;
  // A status line under the heading, such as "Finding comparable packages for your new criteria.", which
  // the section announces; busy marks the section as updating.
  status?: ReactNode;
  busy?: boolean;
  // A line under the heading before the finding, such as the criteria find_comparables used. While a status
  // line shows, the status takes its place, since the line is out of date until the rerun answers.
  lead?: ReactNode;
  // Where find_comparables gave no range, how to compare with more, after the sentence that says why
  // (ticket 15, brief 7.7).
  more?: ReactNode;
  // The page says what is happening in its own live region, such as the planned package's steps and
  // reruns, so the section's own loading status stays silent and nothing is heard twice.
  quiet?: boolean;
  // A block at the end of the card that counts the same comparable packages, such as "Advertised again" (ticket
  // 28), drawn after the result and never in place of a body such as the plan prompt. As a function it learns
  // whether a "Compare with" segment is pressed (ticket 26), so "Advertised again" can say the comparison leaves
  // its count alone.
  after?: ReactNode | ((comparing: boolean) => ReactNode);
}) {
  const headingId = useId();
  const loading = state.status === "loading";
  const result = state.status === "ready" ? state.result : null;
  // Where a dot opens the drawer, each quantile dot's list is held for it (ticket 15). A link to a dot's list
  // that these comparables have no dots for closes the drawer, rather than leave it waiting.
  const canOpen = Boolean(open);
  useEffect(() => {
    if (!canOpen || !result) return;
    if (result.quantile_dots) rememberDots(result);
    else forgetDotList();
  }, [canOpen, result]);

  // The section's one polite live region, which says steps and results (the 12 brief), the comparisons too.
  const [announce, setAnnounce] = useState("");
  // One comparison at a time: the lever whose "Compare with" segment is pressed (the 26 brief, section 6.2).
  const [pressed, setPressed] = useState<string | null>(null);
  const estimateResult = estimate?.status === "ready" ? estimate.result : null;
  const comparison = estimateResult?.comparisons.find((one) => one.lever === pressed) ?? null;
  // A new answer comes from new criteria: the comparison it came from is gone, so it is released and said once.
  const shownEstimate = useRef(estimateResult);
  const shownComparison = useRef<Comparison | null>(null);
  shownComparison.current = comparison;
  useEffect(() => {
    if (shownEstimate.current === estimateResult) return;
    const was = shownComparison.current;
    if (was) setAnnounce(copy.whatIf.announce.criteria(optionWords(was.lever, was.value).inSentence));
    setPressed(null);
    shownEstimate.current = estimateResult;
  }, [estimateResult]);
  const press = (lever: string | null) => {
    setPressed(lever);
    const described = estimated(estimate);
    const chosen = estimateResult?.comparisons.find((one) => one.lever === lever) ?? null;
    if (!described?.estimate) return;
    const b = described.estimate;
    const one = (value: number) => formatNumber(value, { decimals: 1, compact: false });
    if (!chosen) {
      setAnnounce(copy.whatIf.announce.released(one(b.q25), one(b.q75)));
      return;
    }
    const option = optionWords(chosen.lever, chosen.value).inSentence;
    const k = formatNumber(chosen.k, { compact: false });
    const n = formatNumber(chosen.n, { compact: false });
    setAnnounce(
      chosen.estimate
        ? copy.whatIf.announce.pressed(option, k, n, one(chosen.estimate.q25), one(chosen.estimate.q75), one(b.q25), one(b.q75))
        : copy.whatIf.announce.pressedNone(option, k, n),
    );
  };
  // A plan date chosen is said once its save lands (the 26 brief, section 9.6).
  const savedCount = planDate?.saved ?? 0;
  useEffect(() => {
    const dates = estimateResult?.plan_dates;
    if (!savedCount || !dates || !planDate) return;
    const months = dates[planDate.chosen ?? dates.default].months;
    setAnnounce(copy.timeEstimate.planDates.announce(formatNumber(months, { decimals: 1, compact: false })));
  }, [savedCount]);
  const populated = result !== null && !body && ["range", "dots", "abstention"].includes(kind(result));
  let compareSlot: ReactNode = null;
  if (populated && estimate?.status === "loading") {
    compareSlot = <Skeleton className="h-8 w-60 rounded-pill" />;
  } else if (populated && estimateResult && estimateResult.abstention === null && estimateResult.estimate) {
    compareSlot = <CompareControl result={estimateResult} pressed={pressed} onPress={press} />;
  }

  return (
    <section
      aria-labelledby={headingId}
      aria-busy={loading || busy || undefined}
      data-past-range={body ? "custom" : state.status === "ready" ? kind(state.result) : state.status}
      data-lane2={estimate ? estimate.status : undefined}
      className="rounded-md border border-line bg-surface p-4 @md/page:p-6"
    >
      <p className="text-label text-ink-muted uppercase">{words.eyebrow}</p>
      {/* "Compare with" sits in the heading row, beside what it changes, and wraps under the heading when the row
          is too narrow (the 26 brief, section 3.1). */}
      <div className="mt-1 flex flex-wrap items-center justify-between gap-x-6 gap-y-3" data-heading-row>
        <h2 ref={headingRef} id={headingId} tabIndex={-1} className="text-h2 text-ink-heading focus:outline-none">
          <span aria-hidden="true">{words.number} </span>
          {words.heading}
        </h2>
        {compareSlot && (
          <div className="min-w-0 max-w-full" data-compare>
            {compareSlot}
          </div>
        )}
      </div>
      {status ? (
        <p className="mt-2 text-small text-ink-muted" data-section-status>
          {status}
        </p>
      ) : (
        lead && (body || state.status === "ready") && <div className="mt-2">{lead}</div>
      )}
      {body}
      {!body && state.status === "loading" && <PastRangeSkeleton twoLanes={estimate !== undefined} />}
      {!body && state.status === "error" && (
        <div className="mt-4">
          <LoadError
            error={state.error}
            message={state.message ?? words.error}
            permission={words.permission}
            onRetry={state.onRetry}
            retrying={state.retrying}
            attempt={state.attempt}
          />
        </div>
      )}
      {!body && result && (
        <Ready
          result={result}
          open={open}
          planned={planned}
          more={more}
          estimate={estimate}
          comparison={comparison}
          planDate={planDate}
          say={setAnnounce}
        />
      )}
      {!body && result && (typeof after === "function" ? after(comparison !== null) : after)}
      {loading && !quiet && (
        <p role="status" className="sr-only">
          {words.loading}
        </p>
      )}
      {populated && (
        <p role="status" className="sr-only" data-live>
          {announce}
        </p>
      )}
    </section>
  );
}

type Kind = "range" | "dots" | "abstention" | "none" | "unmeasured" | "not-measurable";

function kind(result: ComparablesResult): Kind {
  switch (result.abstention?.reason) {
    case "no_public_notice":
      return "not-measurable";
    case "none_measurable":
      return "unmeasured";
    case "no_comparables":
    case "unknown_package":
      return "none";
    case "too_few_comparables":
      return "abstention";
    default:
      return result.quantile_dots ? "dots" : "range";
  }
}

// What lane 2 and its parts need from the section: estimate_time's answer, the comparison pressed in the heading
// row, the plan-date choice, and the section's live region.
type Lane2Props = { estimate?: EstimateState; comparison: Comparison | null; planDate?: PlanDateProps; say: (text: string) => void };

function Ready({
  result,
  open,
  planned,
  more,
  ...lane2
}: { result: ComparablesResult; open?: OpenComparable; planned?: PlannedMonths; more?: ReactNode } & Lane2Props) {
  const abstention = result.abstention;
  if (abstention?.reason === "no_public_notice") {
    return (
      <NoChart title={words.empty.notMeasurableTitle}>
        <p className="mt-2 max-w-prose text-body text-ink">
          <Fill template={words.empty.notMeasurableBody} slots={{ field: abstention.field, value: abstention.value }} />
        </p>
        {result.package && (
          <p className="mt-4">
            <TextLink href={planCheckHref(result.package)}>{words.empty.notMeasurableLink}</TextLink>
          </p>
        )}
      </NoChart>
    );
  }
  if (abstention?.reason === "none_measurable") {
    return (
      <NoChart
        title={
          <Fill
            template={words.empty.unmeasuredTitle(abstention.matched)}
            slots={{ matched: <Num count={abstention.matched} capital /> }}
          />
        }
      >
        <div className="mt-2">
          <Unmeasured result={result} />
        </div>
        {more}
      </NoChart>
    );
  }
  if (abstention?.reason === "no_comparables" || abstention?.reason === "unknown_package" || result.rows.length === 0) {
    // A planned package's criteria are the person's, so the state says how to compare with more (the 15 brief).
    if (planned) {
      return (
        <NoChart title={copy.packageWorkspace.section.noneFound}>
          <p className="mt-4">
            <TextLink href={readinessHref(result)}>{words.empty.noneLink}</TextLink>
          </p>
        </NoChart>
      );
    }
    return (
      <NoChart title={words.empty.noneTitle}>
        <p className="mt-2 max-w-prose text-body text-ink">
          <Looked result={result} />
        </p>
        <p className="mt-4">
          <TextLink href={readinessHref(result)}>{words.empty.noneLink}</TextLink>
        </p>
      </NoChart>
    );
  }
  return <Populated result={result} open={open} planned={planned} more={more} {...lane2} />;
}

// Ticket 47: the range chart for a slide, from a recorded find_comparables answer and, for lane 2, a recorded
// estimate_time answer: the same chart the package workspace draws, read-only, or its own table in its place.
const SILENT = () => undefined;
export function RangeFigure({ result, estimate, twin }: { result: ComparablesResult; estimate?: EstimateState; twin: boolean }) {
  return <Populated result={result} estimate={estimate} comparison={null} say={SILENT} figure={{ twin }} />;
}

// A state with no chart: a first-person title beside the dashed circle of the neutral state.
function NoChart({ title, children }: { title: ReactNode; children: ReactNode }) {
  return (
    <div className="mt-4 flex gap-3" data-no-chart>
      <CircleDashed aria-hidden="true" className="size-6 shrink-0 text-line-strong" />
      <div className="min-w-0">
        <h3 className="text-title text-balance text-ink-heading">{title}</h3>
        {children}
      </div>
    </div>
  );
}

// The plan check with this package's row in view, as the "In the plan" fact links it.
export const planCheckHref = (pkg: { project_id: string; step_reference: string; plan: { agency_id: string; plan_date: string } }) =>
  `/projects/${pkg.project_id}/procurement/${pkg.plan.agency_id}/${pkg.plan.plan_date}#${encodeURIComponent(pkg.step_reference)}`;

// Data readiness, showing only the sources behind the answer and naming the tool that wrote the line.
const readinessHref = (result: ComparablesResult) =>
  dataReadinessHref(
    result.sources.map((source) => source.key),
    result.tool,
  );

// The criteria the tool used, as phrases: the fields compared, and the others in a second sentence.
function criteriaParts(result: ComparablesResult, form: "note" | "empty") {
  const criteria = result.criteria;
  if (!criteria) return { fields: [] as ReactNode[], parts: [] as ReactNode[] };
  const f = copy.packagePage.facts;
  const named: [string, string | null][] = [
    [f.method, criteria.method],
    [words.note.category, criteria.category],
    [f.marketApproach, criteria.market_approach],
    [f.reviewType, criteria.review_type],
  ];
  const fields = named
    .filter((entry): entry is [string, string] => entry[1] !== null)
    .map(([field, value]) => <Fill key={field} template={words.note.field} slots={{ field, value }} />);
  const amount = (value: number) => formatNumber(value, { compact: false });
  const e = words.empty;
  const n = words.note;
  const parts: ReactNode[] = [];
  const { size_from_usd: from, size_to_usd: to } = criteria;
  if (from !== null && to !== null) {
    parts.push(<Fill key="size" template={form === "note" ? n.size : e.noneSize} slots={{ from: amount(from), to: amount(to) }} />);
  } else if (from !== null) {
    parts.push(<Fill key="size" template={form === "note" ? n.sizeFrom : e.noneSizeFrom} slots={{ from: amount(from) }} />);
  } else if (to !== null) {
    parts.push(<Fill key="size" template={form === "note" ? n.sizeTo : e.noneSizeTo} slots={{ to: amount(to) }} />);
  }
  if (criteria.country_name) {
    parts.push(<Fill key="region" template={form === "note" ? n.region : e.noneRegion} slots={{ region: criteria.country_name }} />);
  }
  parts.push(
    <Fill
      key="period"
      template={form === "note" ? n.period : e.nonePeriod}
      slots={{ from: <Num date={criteria.notice_from} />, to: <Num date={criteria.notice_to} /> }}
    />,
  );
  return { fields, parts };
}

function Looked({ result }: { result: ComparablesResult }) {
  const { fields, parts } = criteriaParts(result, "empty");
  return (
    <>
      {fields.length > 0 && (
        <>
          <Fill template={words.empty.noneLooked} slots={{ fields: <Joined items={fields} /> }} />{" "}
        </>
      )}
      <Fill template={words.empty.noneHadTo} slots={{ parts: <Joined items={parts} /> }} /> {words.empty.noneEnd}
    </>
  );
}

function Note({ result }: { result: ComparablesResult }) {
  const { fields, parts } = criteriaParts(result, "note");
  return (
    <p className="text-chart-text-subtle" data-chart-note>
      <span className="font-bold text-chart-text">{words.note.label}</span>{" "}
      {fields.length > 0 && (
        <>
          <Fill template={words.note.same} slots={{ fields: <Joined items={fields} /> }} />{" "}
        </>
      )}
      <Fill template={words.note.they} slots={{ parts: <Joined items={parts} /> }} />
    </p>
  );
}

// What each matching package left out lacked, each count under ten in words.
function gapsOf(result: ComparablesResult, check?: NumCheck) {
  return result.coverage.not_used.map((entry) => (
    <Fill key={entry.reason} template={words.reasons[entry.reason](entry.count)} slots={{ count: <Num count={entry.count} check={check} /> }} />
  ));
}

// What a coverage count counts, in its tooltip.
const EXPLAIN_COVERAGE: NumCheck = { tooltip: words.explain.coverage };

// Packages matched but none could be measured: what they lacked, without "Based on 0 of". Each count
// can be checked, as on the populated coverage line.
function Unmeasured({ result }: { result: ComparablesResult }) {
  const matched = <Num count={result.coverage.matched} check={EXPLAIN_COVERAGE} />;
  return (
    <p data-coverage-line className="text-small text-ink">
      <Fill template={words.empty.unmeasuredOf} slots={{ matched, gaps: <Joined items={gapsOf(result, EXPLAIN_COVERAGE)} /> }} />{" "}
      <TextLink href={readinessHref(result)}>{copy.coverage.link}</TextLink>
    </p>
  );
}

function Coverage({ result, check }: { result: ComparablesResult; check?: NumCheck }) {
  const { coverage } = result;
  const gaps = gapsOf(result, check);
  return (
    <CoverageLine
      part={coverage.used}
      whole={coverage.matched}
      noun={words.coverageNoun}
      check={check}
      gap={
        gaps.length > 0 ? (
          <>
            <Joined items={gaps} />
            {words.reasonsEnd}
          </>
        ) : undefined
      }
      href={readinessHref(result)}
    />
  );
}

function SourceLine({ result }: { result: ComparablesResult }) {
  const sources = <Joined items={result.sources.map((source) => source.dataset_name)} />;
  return result.records_through ? (
    <Fill template={words.source} slots={{ sources, date: <Num date={result.records_through} /> }} />
  ) : (
    <Fill template={words.sourceUndated} slots={{ sources }} />
  );
}

// ── The populated states ─────────────────────────────────────────────────

function Populated({
  result,
  open: opening,
  planned,
  more,
  estimate,
  comparison,
  planDate,
  say: setAnnounce,
  figure,
}: { result: ComparablesResult; open?: OpenComparable; planned?: PlannedMonths; more?: ReactNode; figure?: { twin: boolean } } & Lane2Props) {
  const abstained = result.abstention?.reason === "too_few_comparables";
  const rows = result.rows;
  const total = rows.length;
  const counts = result.counts!;
  const open = counts.still_open;
  const quantile = !abstained && result.quantile_dots ? result.quantile_dots : null;
  // The plan row's own months, from its planned dates, as find_comparables returned them; for a package
  // planned from a sentence, the person's own plan from their plan chip (ticket 15).
  const planRowMonths = planned ? planned.months : (result.plan?.months ?? null);
  const maxMonths = result.thresholds.max_plan_months;
  const pkg = result.package;

  const [plan, setPlan] = useState<number | null>(planRowMonths);
  const [text, setText] = useState(planRowMonths === null ? "" : months1(planRowMonths));
  const [invalid, setInvalid] = useState(false);
  const [axisValue, setAxisValue] = useState<number | null>(planRowMonths);
  const [tableOpen, setTableOpen] = useState(abstained);
  const [page, setPage] = useState(0);
  const [measure, width] = useWidth<HTMLDivElement>();
  const narrow = usePageNarrow(measure);
  const inputRef = useRef<HTMLInputElement>(null);
  const captionRef = useRef<HTMLSpanElement>(null);
  // Ticket 26: the test years under the track record, and the table twin's time estimate table.
  const [yearsOpen, setYearsOpen] = useState(false);
  const yearsCaptionRef = useRef<HTMLSpanElement>(null);
  const estimateCaptionRef = useRef<HTMLDivElement>(null);
  const axisTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const sayTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  useEffect(
    () => () => {
      clearTimeout(axisTimer.current);
      clearTimeout(sayTimer.current);
    },
    [],
  );
  // The plan chip and the plan line are one value: a plan typed in the chip moves the line (ticket 15).
  const plannedMonths = planned?.months;
  useEffect(() => {
    if (plannedMonths === undefined || plannedMonths === null) return;
    setPlan((now) => (now === plannedMonths ? now : plannedMonths));
    setText((now) => (Number(now.replace(",", ".")) === plannedMonths ? now : months1(plannedMonths)));
    setAxisValue(plannedMonths);
    setInvalid(false);
  }, [plannedMonths]);

  const ids = { title: useId(), input: useId(), helper: useId(), error: useId(), table: useId() };
  const withinOf = useCallback(
    (months: number) => rows.filter((row) => !row.still_open && row.months <= months).length,
    [rows],
  );
  const within = plan === null ? null : withinOf(plan);
  // The axis covers what is placed on it: every dot, or every quantile dot the curve reached, the 8-in-10
  // point, the plan row's months and the months typed. A quantile dot never reached sits at the plot's
  // edge instead of stretching the axis to its last follow-up.
  const placed = quantile ? quantile.filter((dot) => dot.reached).map((dot) => dot.months) : rows.map((row) => row.months);
  const range = abstained ? null : result.past_range;
  // Ticket 26: lane 2 shares the axis, which covers the largest 8-in-10 point across the time estimate's whole
  // grid, so pressing a comparison never rescales it.
  const described = estimated(estimate);
  const largest = Math.max(...placed, range?.q80 ?? 0, planRowMonths ?? 0, axisValue ?? 0, described?.axis_max_months ?? 0, 0.5);
  const axis = axisFor(largest, width || Number.POSITIVE_INFINITY);
  const say = (months: number) => setAnnounce(words.chart.announce(whole(withinOf(months)), whole(total), months1(months)));

  const onPlannedChange = planned?.onChange;
  const onPlan = useCallback(
    (value: number, how: PlanMove) => {
      setPlan(value);
      setText(months1(value));
      setInvalid(false);
      if (how === "drag-end" || how === "axis") setAnnounce(words.chart.announce(whole(withinOf(value)), whole(total), months1(value)));
      // A planned package keeps the line's months as its plan; the page saves it once the movement stops.
      if (how !== "drag") onPlannedChange?.(value);
    },
    [withinOf, total, onPlannedChange],
  );

  const onType = (raw: string) => {
    setText(raw);
    const cleaned = raw.trim().replace(",", ".");
    const value = /^\d+(\.\d?)?$/.test(cleaned) ? Number(cleaned) : NaN;
    if (!(value >= 0.5 && value <= maxMonths)) {
      setInvalid(cleaned !== "");
      return;
    }
    setInvalid(false);
    setPlan(value);
    onPlannedChange?.(value);
    clearTimeout(axisTimer.current);
    axisTimer.current = setTimeout(() => setAxisValue(value), 300);
    clearTimeout(sayTimer.current);
    sayTimer.current = setTimeout(() => say(value), 500);
  };

  const reset = () => {
    if (planRowMonths === null) return;
    setPlan(planRowMonths);
    setText(months1(planRowMonths));
    setInvalid(false);
    setAxisValue(planRowMonths);
    say(planRowMonths);
    inputRef.current?.focus();
  };

  const showRows = () => {
    setTableOpen(true);
    requestAnimationFrame(() => captionRef.current?.focus());
  };
  const explainCounts: NumCheck | undefined = planRowMonths === null ? undefined : {
    tooltip: words.explain.counts(months1(planRowMonths), whole(total), spelled(open)),
    onOpen: showRows,
  };
  const explainQuantiles: NumCheck = { tooltip: words.explain.quantiles(whole(total), spelled(open)), onOpen: showRows };
  const explainPlan: NumCheck | undefined = pkg
    ? { tooltip: words.explain.plan(pkg.plan.implementing_agency, formatDate(pkg.plan.plan_date)) }
    : undefined;

  const type = chartType(width || 800);

  // ── The finding, at the plan row's own months ──
  const count = (value: number, check?: NumCheck) => <Num value={value} options={{ compact: false }} check={check} />;
  const q = (value: number | null) => (value === null ? null : <Num value={value} options={{ decimals: 1, compact: false }} check={explainQuantiles} />);
  let title: ReactNode;
  if (abstained) {
    title =
      total === 1 ? (
        words.title.abstainOne
      ) : (
        <Fill template={words.title.abstain} slots={{ n: <Num count={total} /> }} />
      );
  } else if (result.plan) {
    const w = result.plan.within;
    const t = words.title;
    // The words for the share come from the tool with its numbers (CLAUDE.md rule 4).
    const share = result.frequencies?.plan ?? null;
    const template =
      w === 0 ? t.none : w === total ? t.all : share?.words === "fewer_than" ? t.fewerThanOne : share?.words === "more_than" ? t.moreThanNine : t.about;
    title = (
      <Fill
        template={template}
        slots={{
          within: count(w, explainCounts),
          total: count(total, explainCounts),
          in10: share === null ? null : count(share.states[0], explainCounts),
          plan: <Num value={result.plan.months} options={{ decimals: 1, compact: false }} check={explainPlan} />,
        }}
      />
    );
  } else if (range?.q25 != null && range.q75 != null) {
    title = <Fill template={words.title.noPlan} slots={{ total: count(total), q25: q(range.q25), q75: q(range.q75) }} />;
  } else {
    title = <Fill template={words.title.noPlanNoRange} slots={{ total: count(total) }} />;
  }

  // ── The summary ──
  const s = words.summary;
  let summary: ReactNode;
  if (abstained) {
    summary = (
      <>
        <Fill template={s.abstain} slots={{ min: whole(result.thresholds.min_comparables) }} />
        {open > 0 && (
          <>
            {" "}
            {open === 1 ? s.abstainOpenOne : <Fill template={s.abstainOpenMany} slots={{ open: <Num count={open} capital /> }} />}
          </>
        )}
      </>
    );
  } else {
    // With no plan dates the title gives the middle half, so the summary starts with the middle one.
    const titled = !result.plan && range?.q25 != null && range.q75 != null;
    const first =
      range?.q75 == null || range.q25 == null || range.q50 == null ? (
        s.noUpper
      ) : titled ? (
        <Fill template={s.middleOnly} slots={{ q50: q(range.q50) }} />
      ) : (
        <Fill template={s.middle} slots={{ q25: q(range.q25), q75: q(range.q75), q50: q(range.q50) }} />
      );
    const second = range?.q80 == null ? s.noIn10 : <Fill template={s.in10} slots={{ q80: q(range.q80) }} />;
    summary = (
      <>
        {first} {second}
        {open > 0 && (
          <>
            {" "}
            {open === 1 ? (
              <Fill template={s.openOne} slots={{ total: count(total) }} />
            ) : (
              <Fill template={s.openMany} slots={{ open: <Num count={open} capital />, total: count(total) }} />
            )}
          </>
        )}
      </>
    );
  }

  // ── The chart's marks and words ──
  const c = words.chart;
  const marks: RangeMark[] = quantile
    ? quantile.map((dot) => ({
        key: `dot-${dot.k}`,
        months: dot.months,
        hollow: !dot.reached,
        beyond: !dot.reached,
        name: (dot.reached ? c.dotQuantile : c.dotQuantileOpen)(whole(dot.k), whole(total), months1(dot.months)),
        tip: {
          header: c.tipQuantile(whole(dot.k)),
          mono: false,
          number: dot.reached ? c.tipMonths(months1(dot.months)) : c.tipPast(months1(dot.months)),
          line: dot.reached ? c.tipQuantileLine(whole(total)) : c.tipQuantileOpen,
        },
      }))
    : rows.map((row, index) => markFor(row, index, total, comparison));

  const altParts = [
    quantile
      ? c.altDots(whole(total), whole(axis.max))
      : open > 0
        ? c.alt(spelled(total), whole(axis.max), spelled(counts.signed), spelled(open))
        : c.altAllSigned(spelled(total), whole(axis.max), spelled(counts.signed)),
  ];
  if (abstained) altParts.push(c.altAbstain);
  else if (range?.q25 != null && range.q75 != null && range.q50 != null) {
    altParts.push(
      range.q80 != null
        ? c.altRange(months1(range.q25), months1(range.q75), months1(range.q50), months1(range.q80))
        : `${c.altMiddle(months1(range.q25), months1(range.q75), months1(range.q50))} ${c.altNoIn10}`,
    );
  } else altParts.push(c.altNoUpper);
  // Ticket 26: with lane 2 the alt text starts by naming both lanes, and lane 2's sentence follows lane 1's.
  if (estimate) {
    altParts.unshift(copy.timeEstimate.alt.lanes(whole(axis.max)));
    const second = lane2Alt(estimate, comparison, total);
    if (second) altParts.push(second);
  }
  if (plan !== null && within !== null) altParts.push(c.altPlan(months1(plan), whole(within), whole(total)));
  if (counts.canceled > 0) {
    altParts.push((counts.canceled_as_still_open ? c.altCanceledCounted : c.altCanceledLeftOut)(counts.canceled, spelled(counts.canceled)));
  }

  const readout = plan === null || within === null ? null : c.readout(whole(within), whole(total), months1(plan));
  const readoutLines: [string, string] | null =
    plan === null || within === null ? null : [c.readoutCount(whole(within), whole(total)), c.readoutWithin(months1(plan))];
  // The widest readout the line can reach: every package signed, by the axis's last month. Where the
  // axis passes 10 months, plans under 10 have a digit fewer, so they get their own widest readout, by
  // 9.9 months. The chart chooses the readout's lines from these, so its rows stay the same while the
  // line moves.
  const widestBy = (from: number, months: number) => ({
    from,
    one: c.readout(whole(total), whole(total), months1(months)),
    lines: [c.readoutCount(whole(total), whole(total)), c.readoutWithin(months1(months))] as [string, string],
  });
  const readoutWidest = axis.max >= 10 ? [widestBy(0, 9.9), widestBy(10, axis.max)] : [widestBy(0, axis.max)];
  const valueText =
    plan === null || within === null
      ? null
      : (plan === planRowMonths ? c.valueTextPlan : c.valueText)(months1(plan), whole(within), whole(total));

  const control = (
    <PlanControl
      ids={ids}
      inputRef={inputRef}
      text={text}
      invalid={invalid}
      maxMonths={maxMonths}
      planRowMonths={planned ? null : planRowMonths}
      plan={plan}
      notice={result.plan?.planned_notice_on ?? null}
      signing={result.plan?.planned_signing_on ?? null}
      planned={Boolean(planned)}
      onType={onType}
      onReset={reset}
    />
  );

  // Ticket 26: the time estimate's figures open the test-year table, the difference opens the twin at the time
  // estimate table, a reason's count opens it at the comparables, and a comparison's count opens the drawer's list.
  const openYears = () => {
    setYearsOpen(true);
    requestAnimationFrame(() => yearsCaptionRef.current?.focus());
  };
  const openTwin = () => {
    setTableOpen(true);
    requestAnimationFrame(() => (estimateCaptionRef.current?.querySelector<HTMLElement>("[data-table-caption]") ?? captionRef.current)?.focus());
  };
  const summaryBlock = (
    <p className="text-body text-ink" data-summary>
      {summary}
      {estimate && (
        <>
          {" "}
          <span data-summary-estimate>
            <EstimateSentences
              state={estimate}
              comparison={comparison}
              links={{
                onTestYears: openYears,
                onTwin: openTwin,
                onWentWith: (shown, element) => {
                  if (opening) openWentWith(result, { ...shown, key: shown.lever }, optionWords(shown.lever, shown.value).inSentence, element);
                },
              }}
            />
          </span>
        </>
      )}
    </p>
  );

  const chart = width > 0 && (
          <RangeChart
            readOnly={Boolean(figure)}
            width={width}
            marks={marks}
            big={Boolean(quantile)}
            stats={range}
            axisMax={axis.max}
            step={axis.step}
            plan={plan}
            ownPlan={planRowMonths}
            readout={readout}
            readoutLines={readoutLines}
            readoutWidest={readoutWidest}
            keySigned={quantile ? c.keyDots(whole(total)) : c.keySigned(whole(counts.signed))}
            keyHollow={open > 0 ? (quantile ? c.keyOpenDots(formatCount(open, { capital: true })) : c.keyOpen(whole(open))) : null}
            keyLead={Boolean(quantile)}
            laneLabel={c.lane}
            planLabel={c.plan}
            middleLabel={
              range?.q25 != null && range.q75 != null && range.q50 != null
                ? c.middle(months1(range.q25), months1(range.q75), months1(range.q50))
                : null
            }
            in10Label={range?.q80 != null ? c.in10(months1(range.q80)) : null}
            axisLastLabel={c.axisLast(whole(axis.max))}
            alt={altParts.join(" ")}
            groupName={quantile ? c.groupDots(whole(total)) : c.group(whole(total))}
            groupHelp={opening ? (quantile ? c.groupHelpOpenDots : c.groupHelpOpen) : c.groupHelp}
            sliderName={c.slider}
            valueText={valueText}
            onPlan={onPlan}
            onOpen={
              opening
                ? (key, element) => {
                    // A quantile dot lists the packages it stands for; any other dot is one package.
                    const dot = quantile?.find((one) => `dot-${one.k}` === key);
                    const row = quantile ? undefined : rows.find((one) => one.step_reference === key);
                    if (dot) opening.onOpenDot(dot, element);
                    else if (row) opening.onOpen(row, element);
                  }
                : undefined
            }
            opened={opening?.opened ?? null}
            openHint={quantile ? c.openHintDots : c.openHint}
            openLabel={quantile ? c.openDots : c.openRecords}
            lane2={estimate ? lane2For(estimate, comparison) : undefined}
            lane2Label={copy.timeEstimate.lane}
            lane2LabelShort={copy.timeEstimate.laneShort}
            matching={comparison && !quantile ? new Set(comparison.matching_ids) : null}
            compareKey={
              comparison
                ? {
                    match: copy.whatIf.key.match(whole(comparison.k), optionWords(comparison.lever, comparison.value).inSentence),
                    others: copy.whatIf.key.others(whole(comparison.rest)),
                    open: open > 0 ? copy.whatIf.key.open : null,
                  }
                : null
            }
          />
  );
  const placeholder = width === 0 && <div style={{ height: estimate ? TWO_LANE_HEIGHT : CHART_HEIGHT }} />;

  // Ticket 47: a slide shows the chart alone, read-only, or its table twin in the chart's place (the 47 brief,
  // section 4.4). The slide's own title states the finding, so there is no heading, plan control or summary here.
  if (figure) {
    return (
      <div ref={measure} data-range-figure={figure.twin ? "table" : "chart"}>
        {figure.twin ? (
          <ComparablesTable result={result} plan={plan} page={page} onPage={setPage} captionRef={captionRef} comparison={null} />
        ) : (
          <>
            {chart}
            {placeholder}
          </>
        )}
      </div>
    );
  }

  return (
    <div ref={measure} className="mt-4">
      <h3 id={ids.title} className="font-bold text-pretty text-ink-heading" style={{ fontSize: type.l, lineHeight: 1.3 }} data-finding>
        {title}
      </h3>
      {abstained && more}
      {narrow && <div className="mt-2">{summaryBlock}</div>}
      <p className="mt-2 text-ink-muted" style={{ fontSize: type.m }}>
        {quantile ? <Fill template={words.subtitleDots} slots={{ total: whole(total) }} /> : words.subtitle}
      </p>
      <div className="mt-4">{control}</div>
      <figure aria-labelledby={ids.title} className="mt-4" data-chart-figure>
        {chart}
        {placeholder}
      </figure>
      {!narrow && <div className="mt-4">{summaryBlock}</div>}
      {/* Ticket 26: the track record, its test years and the plan-date choice, about lane 2, after the chart. */}
      {estimate && (
        <div className="mt-4" style={{ fontSize: type.s }}>
          <EstimateExtras
            state={estimate}
            planDate={planDate}
            yearsOpen={yearsOpen}
            onToggleYears={() => setYearsOpen((now) => !now)}
            onOpenYears={openYears}
            yearsCaptionRef={yearsCaptionRef}
          />
        </div>
      )}
      <div className="mt-4 flex flex-col gap-2" style={{ fontSize: type.s }}>
        <Note result={result} />
        <Coverage result={result} check={EXPLAIN_COVERAGE} />
        <Source>
          <SourceLine result={result} />
        </Source>
      </div>
      <div className="mt-4">
        <Button
          variant="ghost"
          flush
          aria-expanded={tableOpen}
          aria-controls={ids.table}
          onClick={() => setTableOpen((now) => !now)}
        >
          {tableOpen ? words.table.hide : words.table.show}
        </Button>
      </div>
      <div id={ids.table} hidden={!tableOpen} className="mt-2" data-comparables-table>
        {tableOpen && described && (
          <div ref={estimateCaptionRef} className="mb-6">
            <TimeEstimateTable result={described} comparison={comparison} />
          </div>
        )}
        {tableOpen && (
          <ComparablesTable
            result={result}
            plan={plan}
            page={page}
            onPage={setPage}
            captionRef={captionRef}
            open={opening}
            comparison={comparison}
          />
        )}
      </div>
    </div>
  );
}

function markFor(row: Comparable, index: number, total: number, comparison: Comparison | null = null): RangeMark {
  const c = words.chart;
  const m = months1(row.months);
  const country = row.country_name ?? copy.notInRecord;
  const own = row.still_open
    ? c.dotOpen(row.step_reference, country, m, whole(index + 1), whole(total))
    : c.dotSigned(row.step_reference, country, m, formatDate(row.signed_on!), whole(index + 1), whole(total));
  return {
    key: row.step_reference,
    months: row.months,
    hollow: row.still_open,
    // While comparing, its name also says whether it went with the option (the 26 brief, section 9.4).
    name: comparison ? `${own} ${dotComparisonName(comparison, row.step_reference)}` : own,
    tip: {
      header: row.step_reference,
      mono: true,
      number: c.tipMonths(m),
      line: row.still_open
        ? c.tipOpen(tableDate(row.notice_date), country)
        : c.tipSigned(tableDate(row.signed_on!), tableDate(row.notice_date), country),
    },
  };
}

// ── The plan control ─────────────────────────────────────────────────────

function PlanControl({
  ids,
  inputRef,
  text,
  invalid,
  maxMonths,
  planRowMonths,
  plan,
  notice,
  signing,
  planned = false,
  onType,
  onReset,
}: {
  // A package planned from a sentence: the line is the person's own plan, with no plan row behind it.
  planned?: boolean;
  ids: { input: string; helper: string; error: string };
  inputRef: Ref<HTMLInputElement>;
  text: string;
  invalid: boolean;
  maxMonths: number;
  planRowMonths: number | null;
  plan: number | null;
  notice: string | null;
  signing: string | null;
  onType: (raw: string) => void;
  onReset: () => void;
}) {
  const w = words.control;
  const moved = planRowMonths !== null && plan !== null && plan !== planRowMonths;
  // The reset button keeps its place while hidden, so showing it moves nothing: at the row's end from
  // 768 px, and below that in the helper's place, which holds the taller of the two, so no empty row
  // sits between the control and the chart. Only one of the two buttons is ever displayed.
  // visibility: hidden also takes it out of the tab order and the accessibility tree; the hidden helper
  // still describes the input, since aria-describedby reads hidden text.
  // In the helper's place it sits flush, so its label starts on the label's edge above; in the input's
  // row it keeps its padding, so its focus ring stays 8 px clear of "months" (DESIGN.md section 5, Buttons).
  const resetButton = (className: string, flush: boolean) =>
    planRowMonths !== null && (
      <span className={cx(className, !moved && "invisible")} data-plan-reset>
        <Button variant="ghost" flush={flush} onClick={onReset}>
          {w.reset(months1(planRowMonths))}
        </Button>
      </span>
    );
  return (
    <div data-plan-control>
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
        <label htmlFor={ids.input} className="text-small font-semibold text-ink">
          {w.label}
        </label>
        <span className="flex items-center gap-2">
          <input
            ref={inputRef}
            id={ids.input}
            type="text"
            inputMode="decimal"
            autoComplete="off"
            value={text}
            aria-invalid={invalid || undefined}
            aria-describedby={invalid ? `${ids.error} ${ids.helper}` : ids.helper}
            onChange={(event) => onType(event.target.value)}
            className={cx(
              "h-11 w-[88px] rounded-sm border bg-surface px-3 text-right text-body text-ink tabular-nums",
              invalid ? "border-error-icon" : "border-line-strong",
            )}
          />
          <span className="text-small text-ink">{w.unit}</span>
        </span>
        {resetButton("hidden @md/page:inline", false)}
      </div>
      {/* One caption line is kept for the error, so it appears without moving the chart. */}
      <p id={ids.error} className="mt-1 min-h-lh text-caption text-error">
        {invalid && w.invalid(whole(maxMonths))}
      </p>
      <div className="grid @md/page:block">
      <p id={ids.helper} className={cx("col-start-1 row-start-1 text-caption text-ink-muted", moved && "invisible @md/page:visible")}>
        {planned ? (
          plan !== null ? w.helperPlanned : w.helperPlannedNone
        ) : notice && signing ? (
          // Plain plan values, so they carry no popover (ticket 10's rule); the months worked out from them do.
          <Fill template={w.helper} slots={{ notice: <Num date={notice} />, signing: <Num date={signing} /> }} />
        ) : plan !== null ? (
          w.helperTyped
        ) : (
          w.helperNoPlan
        )}
      </p>
      {resetButton("col-start-1 row-start-1 self-start @md/page:hidden", true)}
      </div>
    </div>
  );
}

// ── The table twin ───────────────────────────────────────────────────────

function ComparablesTable({
  result,
  plan,
  page,
  onPage,
  captionRef,
  open,
  comparison = null,
}: {
  result: ComparablesResult;
  plan: number | null;
  page: number;
  onPage: (page: number) => void;
  captionRef: Ref<HTMLSpanElement>;
  open?: OpenComparable;
  // Ticket 26: while comparing, a column says whether each package went with the option.
  comparison?: Comparison | null;
}) {
  const t = words.table;
  const rows = result.rows;
  const total = rows.length;
  const paged = total > result.thresholds.quantile_dots_above;
  const from = paged ? page * PAGE : 0;
  const shown = paged ? rows.slice(from, from + PAGE) : rows;
  // With one line per cell the six columns need about 776 px, so the table shows when its frame has
  // 49rem and cards below that (cardsBelow="fit", DESIGN.md section 5, Tables). That is from a page area
  // of about 930 to 1199 px and from about 1411 px. There a STEP reference keeps to one line, a date fits
  // its 7rem column, and the Months head's definition takes three lines. No cell is kept from wrapping,
  // so with WCAG 1.4.12's text spacing a reference breaks after a hyphen and a date at its space, and no
  // text runs into the next column.
  const columns: Column[] = [
    { key: "package", header: t.columns.package, width: "w-[15.25rem]" },
    { key: "country", header: t.columns.country, short: true, width: "w-[5.5rem]" },
    { key: "notice", header: t.columns.notice, short: true, width: "w-[7rem]" },
    { key: "signed", header: t.columns.signed, short: true, width: "w-[7rem]" },
    {
      key: "months",
      header: (
        <>
          {t.columns.months}
          <span className="block text-caption font-normal text-ink-muted">{t.columns.monthsNote}</span>
        </>
      ),
      cardHeader: t.columns.months,
      numeric: true,
      width: "w-[9rem]",
    },
    ...(plan === null ? [] : [{ key: "within", header: t.columns.within(months1(plan)), short: true }]),
    ...(comparison ? [{ key: "wentWith", header: copy.whatIf.table.column(optionWords(comparison.lever, comparison.value).inSentence), short: true }] : []),
  ];
  const tableRows: Row[] = shown.map((row) => ({
    id: row.step_reference,
    cells: {
      // A reference with a county's name breaks at its spaces first (MonoWords); one with no spaces
      // keeps to one line in the table, where its column fits it. Where the drawer can open, the
      // reference is a button that opens the package's records (ticket 15), the full-size way in on a phone.
      package: open ? (
        <button
          type="button"
          data-open-row={row.step_reference}
          aria-label={t.openRow(row.step_reference)}
          onClick={(event) => open.onOpen(row, event.currentTarget)}
          className="inline cursor-pointer py-1 text-left text-primary underline decoration-1 underline-offset-3 hover:text-link-hover"
        >
          <MonoWords text={row.step_reference} />
        </button>
      ) : (
        <MonoWords text={row.step_reference} />
      ),
      country: row.country_name ?? copy.notInRecord,
      notice: tableDate(row.notice_date),
      signed: row.signed_on ? tableDate(row.signed_on) : t.stillOpen,
      months: months1(row.months),
      within: plan === null ? null : row.still_open ? (row.months <= plan ? t.notYet : t.no) : row.months <= plan ? t.yes : t.no,
      wentWith: comparison ? wentWithCell(comparison, row.step_reference) : null,
    },
  }));
  return (
    <>
      <Table
        title={
          <span ref={captionRef} tabIndex={-1} className="focus:outline-none" data-table-caption>
            {total === 1 ? t.captionOne : t.caption(spelled(total))}
          </span>
        }
        level={4}
        count={{ noun: t.noun, one: t.nounOne, total, from: from + 1, to: from + shown.length }}
        columns={columns}
        rowHeader="package"
        cardsBelow="fit"
        cardsNote={t.columns.monthsCards}
        selected={open?.opened ?? null}
        state={{ status: "ready", rows: tableRows }}
        source={<SourceLine result={result} />}
      />
      {paged && (
        <div className="mt-3 flex flex-wrap gap-3">
          <Button variant="secondary" disabled={page === 0} onClick={() => onPage(page - 1)}>
            {t.previous}
          </Button>
          <Button variant="secondary" disabled={from + PAGE >= total} onClick={() => onPage(page + 1)}>
            {t.next}
          </Button>
        </div>
      )}
    </>
  );
}

// ── Loading ──────────────────────────────────────────────────────────────

// Sized like the populated section at each width, in its order: below 768 px the summary comes right
// after the title, and the helper's place is at least the reset button's height; from 768 px the summary follows
// the chart. Its type sizes are the chart's own (chartType), read from the section's width, as the
// populated section reads them.
function PastRangeSkeleton({ twoLanes = false }: { twoLanes?: boolean }) {
  const [measure, width] = useWidth<HTMLDivElement>();
  const type = chartType(width || 800);
  const lines = (count: number, last = "w-3/5") => Array.from({ length: count }, (_, index) => (index === count - 1 ? last : "w-full"));
  // The title and the summary hold checkable numbers, whose buttons make each line a little taller: pb-2.
  return (
    <div ref={measure} aria-hidden="true" className="mt-4" data-past-range-skeleton>
      <SkeletonText className="pb-2 @md/page:hidden" widths={lines(3)} style={{ fontSize: type.l, lineHeight: 1.3 }} />
      <SkeletonText className="hidden pb-2 @md/page:flex" widths={lines(2)} style={{ fontSize: type.l, lineHeight: 1.3 }} />
      <SkeletonText className="mt-2 pb-2 text-body @md/page:hidden" widths={lines(7, "w-2/5")} />
      <SkeletonText className="mt-2 @md/page:hidden" widths={lines(3)} style={{ fontSize: type.m }} />
      <SkeletonLine className="mt-2 hidden @md/page:flex" width="w-4/5" style={{ fontSize: type.m }} />
      <div className="mt-4 flex flex-wrap items-center gap-x-3 gap-y-2">
        <SkeletonLine className="text-small" width="w-28" />
        <Skeleton className="h-11 w-[88px] rounded-sm" />
      </div>
      <span className="mt-1 block min-h-lh text-caption" />
      {/* Below 768 px the helper's place holds the reset button too, so it is at least 44 px tall. */}
      <SkeletonText className="min-h-11 text-caption @md/page:hidden" widths={lines(2)} />
      <SkeletonLine className="hidden text-caption @md/page:flex" width="w-3/5" />
      <div className="mt-4" style={{ height: twoLanes ? TWO_LANE_HEIGHT : CHART_HEIGHT }} data-chart-skeleton>
        <Skeleton className="h-full w-full rounded-md" />
      </div>
      <SkeletonText className="mt-4 hidden pb-2 text-body @md/page:flex" widths={lines(3, "w-2/5")} />
      {/* Ticket 26: the track record and the plan-date choice keep 112 px, so nothing jumps when they land. */}
      {twoLanes && (
        <div className="mt-4 flex min-h-28 flex-col gap-2" style={{ fontSize: type.s }}>
          <SkeletonLine width="w-full" />
          <SkeletonLine width="w-3/5" />
          <Skeleton className="h-8 w-full max-w-90 rounded-pill" />
        </div>
      )}
      <div className="mt-4 flex flex-col gap-2" style={{ fontSize: type.s }}>
        <SkeletonText className="@md/page:hidden" widths={lines(3)} />
        <SkeletonText className="hidden @md/page:flex" widths={lines(2)} />
        <SkeletonText className="pb-2 text-small @md/page:hidden" widths={lines(6)} />
        <SkeletonText className="hidden pb-2 text-small @md/page:flex" widths={lines(2)} />
        <SkeletonText className="@md/page:hidden" widths={lines(4)} />
        <SkeletonText className="hidden @md/page:flex" widths={lines(2)} />
      </div>
      <span className="mt-4 block h-11" />
    </div>
  );
}
