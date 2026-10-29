// Section 1 of the package workspace, "How long it took" (the 12 brief): find_comparables' result as
// a card with the finding as its title, the plan control, lane 1 of the range chart, the summary,
// the note on what "comparable" meant, the coverage line, the source line and a "Show the table" twin.
//
// Since ticket 101 it is zone 1, a Task zone panel numbered 1 (DESIGN.md section 5, Task zone): its first block opens
// on the finding in the finding style, and its Note, coverage line and source line end the block in its foot strip;
// "Advertised again" (ticket 28) is its second block. A number in the finding or the summary opens "Show the table"
// filtered to the rows it counts, scrolls the table's title under the bar and moves focus to the count line, which
// repeats the pressed number and no other, with "Show all {total}" after it. When the time estimate holds back, its
// first-person sentence sits under the chart in body, never inside lane 2. A failed request is the error alert in the
// zone's body under its header, and "Advertised again", which comes from its own tool, stays.
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
// and the summary's place follows the page column's width too. The exceptions are the table twin,
// which reads its own frame's width (@table-fit/table:, 49rem), as the comment at its columns says, and,
// in the workspace from a frame of 75rem, the summary's place and the plan control's reset button, which
// keep theirs when the drawer opens (usePageNarrow), as the zones keep their width.
import { useCallback, useEffect, useId, useLayoutEffect, useRef, useState, type ReactNode, type Ref, type RefObject } from "react";
import { CircleDashed } from "lucide-react";
import { copy } from "../copy";
import type { ApiError, Comparable, ComparablesResult, Comparison } from "../lib/api";
import { forgetDotList, openPlanRow, openWentWith, rangeCriteria, rangeIds, rememberDots, type OpenComparable } from "../lib/packages";
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
import { Byline } from "./Byline";
import { CoverageLine } from "./Checks";
import { Fill, Joined } from "./Fill";
import { FootStrip } from "./FootStrip";
import { LoadError } from "./LoadError";
import { MonoWords } from "./MonoWords";
import { Num, type NumCheck } from "./Num";
import { FromLine, fromText, planFrom, recordsFrom, wholeDate } from "./NumFrom";
import { axisFor, chartType, RangeChart, type PlanMove, type RangeMark } from "./RangeChart";
import { Skeleton, SkeletonLine, SkeletonText, SkeletonWords } from "./Skeleton";
import { Source } from "./Source";
import { Table, type Column, type Row } from "./Table";
import { TaskZone, ZoneBlock } from "./TaskZone";
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
// In the workspace layout, from a frame of 75rem the zones keep their place and width when the drawer narrows
// the page area (app.css, "The workspace layout"), so the summary keeps its place too: there the page is never
// narrow, and a dot and its records share one screen with nothing moving (principle 5; ticket 101's critique).
function usePageNarrow(element: RefObject<HTMLElement | null>): boolean {
  const [narrow, setNarrow] = useState(() => typeof window !== "undefined" && window.matchMedia("(width < 48rem)").matches);
  useLayoutEffect(() => {
    const node = element.current;
    const column = node?.closest<HTMLElement>("[data-page-column]") ?? document.documentElement;
    const frame = node?.closest("[data-workspace]") ? node.closest<HTMLElement>("[data-frame]") : null;
    const update = () => {
      const rem = parseFloat(getComputedStyle(document.documentElement).fontSize) || 16;
      const steady = frame !== null && frame.getBoundingClientRect().width >= 75 * rem;
      setNarrow(!steady && column.getBoundingClientRect().width < 48 * rem);
    };
    update();
    const observer = new ResizeObserver(update);
    observer.observe(column);
    if (frame) observer.observe(frame);
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

// Whether the page's fonts have loaded: at once when they already have, as on every later visit, and otherwise when
// document.fonts says they are ready.
function useFontsReady(): boolean {
  const [ready, setReady] = useState(() => typeof document === "undefined" || !document.fonts || document.fonts.status === "loaded");
  useEffect(() => {
    if (ready) return;
    let live = true;
    document.fonts.ready.then(() => {
      if (live) setReady(true);
    });
    return () => {
      live = false;
    };
  }, [ready]);
  return ready;
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
  pressedNumber,
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
  // its count alone, and is given the zone's one polite live region to say its own failure in (ticket 60).
  after?: ReactNode | ((comparing: boolean, say: (text: string) => void) => ReactNode);
  // A number already pressed, so the table opens filtered to the rows it counts, as the design gallery shows it
  // (ticket 101's design review, round 2). On a page a person presses the number.
  pressedNumber?: RowFilter["key"];
}) {
  const loading = state.status === "loading";
  const result = state.status === "ready" ? state.result : null;
  // Where a dot opens the drawer, each quantile dot's list is held for it (ticket 15). A link to a dot's list
  // that these comparables have no dots for closes the drawer, rather than leave it waiting.
  const canOpen = Boolean(open);
  useEffect(() => {
    if (!canOpen || !result) return;
    if (result.quantile_dots) rememberDots(result);
    else forgetDotList();
    rangeIds.set(result.rows.map((row) => row.evidence_id));
    rangeCriteria.set(result.criteria);
    return () => {
      rangeIds.set([]);
      rangeCriteria.set(null);
    };
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
  // "Compare with" shows only with a given time estimate. Nothing holds its row while the estimate loads, since a
  // held-back estimate, as on the demo package, draws none (ticket 59; the critique of round 2).
  let compareSlot: ReactNode = null;
  if (populated && estimateResult && estimateResult.abstention === null && estimateResult.estimate) {
    compareSlot = <CompareControl result={estimateResult} pressed={pressed} onPress={press} />;
  }

  // A status line under the zone's name, such as "Finding comparable packages for your new criteria.", or a line
  // before the finding, such as the criteria find_comparables used, which the status replaces while it shows.
  const leadLine = status ? (
    <p className="text-small text-ink-muted" data-section-status>
      {status}
    </p>
  ) : lead && (body || state.status === "ready") ? (
    <div>{lead}</div>
  ) : null;
  // "Compare with" sits just above the chart it changes (the 26 brief, section 3.1), in the block's flow, since a
  // zone's header holds only its name and its tag (DESIGN.md section 5, Task zone).
  const compare = compareSlot && (
    <div className="mt-4 max-w-full min-w-0" data-compare>
      {compareSlot}
    </div>
  );

  return (
    <TaskZone
      number={words.number}
      name={words.heading}
      panel
      headingRef={headingRef}
      busy={loading || busy}
      sectionKey="took"
      className="scroll-mt-24"
      marks={{
        "data-past-range": body ? "custom" : state.status === "ready" ? kind(state.result) : state.status,
        "data-lane2": estimate ? estimate.status : undefined,
      }}
      live={
        <>
          {/* One polite region for the whole zone, its second block's failure included, which may come while the
              section still loads (ticket 60). */}
          {loading && !quiet ? (
            <p role="status" className="sr-only">
              {words.loading}
            </p>
          ) : (
            <p role="status" className="sr-only" data-live>
              {announce}
            </p>
          )}
        </>
      }
    >
      {body ? (
        <ZoneBlock data-block="took">
          <div>
            {leadLine}
            {body}
          </div>
        </ZoneBlock>
      ) : state.status === "loading" ? (
        <PastRangeLoading lead={leadLine} twoLanes={estimate !== undefined} />
      ) : state.status === "error" ? (
        // A failed block's error alert takes the block's place; the header and "Advertised again" stay.
        <ZoneBlock data-block="took">
          <LoadError
            error={state.error}
            message={state.message ?? words.error}
            permission={words.permission}
            onRetry={state.onRetry}
            retrying={state.retrying}
            attempt={state.attempt}
          />
        </ZoneBlock>
      ) : (
        <Ready
          result={state.result}
          open={open}
          planned={planned}
          more={more}
          lead={leadLine}
          compare={compare}
          estimate={estimate}
          comparison={comparison}
          planDate={planDate}
          say={setAnnounce}
          pressedNumber={pressedNumber}
        />
      )}
      {/* The block after the result is drawn in every state but a body, the loading one too: it decides itself what
          stands in its place while the section loads, its own skeleton or nothing, so the card ends where it will and
          a rerun keeps it (ticket 59; the 28 review, follow-up 2; the critique of round 1). It says its own failure in
          the zone's one live region (ticket 60). */}
      {!body && (typeof after === "function" ? after(comparison !== null, setAnnounce) : after)}
    </TaskZone>
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
type Lane2Props = {
  estimate?: EstimateState;
  comparison: Comparison | null;
  planDate?: PlanDateProps;
  say: (text: string) => void;
  pressedNumber?: RowFilter["key"];
};

function Ready({
  result,
  open,
  planned,
  more,
  lead,
  compare,
  ...lane2
}: { result: ComparablesResult; open?: OpenComparable; planned?: PlannedMonths; more?: ReactNode; lead?: ReactNode; compare?: ReactNode } & Lane2Props) {
  const abstention = result.abstention;
  if (abstention?.reason === "no_public_notice") {
    return (
      <NoChartBlock lead={lead} title={words.empty.notMeasurableTitle}>
        <p className="mt-2 max-w-prose text-body text-ink">
          <Fill template={words.empty.notMeasurableBody} slots={{ field: abstention.field, value: abstention.value }} />
        </p>
        {result.package && (
          <p className="mt-4">
            <TextLink href={planCheckHref(result.package)}>{words.empty.notMeasurableLink}</TextLink>
          </p>
        )}
      </NoChartBlock>
    );
  }
  if (abstention?.reason === "none_measurable") {
    return (
      <NoChartBlock
        lead={lead}
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
      </NoChartBlock>
    );
  }
  if (abstention?.reason === "no_comparables" || abstention?.reason === "unknown_package" || result.rows.length === 0) {
    // A planned package's criteria are the person's, so the state says how to compare with more (the 15 brief).
    if (planned) {
      return (
        <NoChartBlock lead={lead} title={copy.packageWorkspace.section.noneFound}>
          <p className="mt-4">
            <TextLink href={dataReadinessHref(result.sources.map((source) => source.key), result.tool)}>{words.empty.noneLink}</TextLink>
          </p>
        </NoChartBlock>
      );
    }
    return (
      <NoChartBlock lead={lead} title={words.empty.noneTitle}>
        <p className="mt-2 max-w-prose text-body text-ink">
          <Looked result={result} />
        </p>
        <p className="mt-4">
          <TextLink href={dataReadinessHref(result.sources.map((source) => source.key), result.tool)}>{words.empty.noneLink}</TextLink>
        </p>
      </NoChartBlock>
    );
  }
  return <Populated result={result} open={open} planned={planned} more={more} lead={lead} compare={compare} {...lane2} />;
}

// Ticket 47: the range chart for a slide, from a recorded find_comparables answer and, for lane 2, a recorded
// estimate_time answer: the same chart the package workspace draws, read-only, or its own table in its place.
const SILENT = () => undefined;
export function RangeFigure({ result, estimate, twin }: { result: ComparablesResult; estimate?: EstimateState; twin: boolean }) {
  return <Populated result={result} estimate={estimate} comparison={null} say={SILENT} figure={{ twin }} />;
}

// A state with no chart: a first-person title beside the dashed circle of the neutral state, as zone 1's one block.
function NoChartBlock({ title, lead, children }: { title: ReactNode; lead?: ReactNode; children: ReactNode }) {
  return (
    <ZoneBlock data-block="took">
      <div>
        {lead}
        <div className={cx("flex gap-3", lead ? "mt-4" : undefined)} data-no-chart>
          <CircleDashed aria-hidden="true" className="size-6 shrink-0 text-line-strong" />
          <div className="min-w-0">
            <h3 className="text-h2 text-balance text-ink-heading">{title}</h3>
            {children}
          </div>
        </div>
      </div>
    </ZoneBlock>
  );
}

// The plan check with this package's row in view, as the "In the plan" fact links it.
export const planCheckHref = (pkg: { project_id: string; step_reference: string; plan: { agency_id: string; plan_date: string } }) =>
  `/projects/${pkg.project_id}/procurement/${pkg.plan.agency_id}/${pkg.plan.plan_date}#${encodeURIComponent(pkg.step_reference)}`;

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

// What each matching package left out lacked, each count under ten in words. The sentence says what each count
// counts, so the counts are plain text: given the coverage count's tooltip, they would share a What sentence with it.
function gapsOf(result: ComparablesResult) {
  return result.coverage.not_used.map((entry) => (
    <Fill key={entry.reason} template={words.reasons[entry.reason](entry.count)} slots={{ count: <Num count={entry.count} /> }} />
  ));
}

// What a coverage count counts, in its tooltip, and the notices and contract awards it was counted from.
function coverageCheck(result: ComparablesResult, what: string = words.explain.coverage): NumCheck {
  const records = recordsFrom(result.sources, result.records_through);
  return { tooltip: what, from: records ? <FromLine words={records} /> : undefined };
}

// Packages matched but none could be measured: what they lacked, without "Based on 0 of". The count of matching
// packages can be checked, as the populated coverage line's count can.
function Unmeasured({ result }: { result: ComparablesResult }) {
  const matched = <Num count={result.coverage.matched} check={coverageCheck(result, words.explain.matched)} />;
  return (
    <p data-coverage-line className="text-small text-ink">
      <Fill template={words.empty.unmeasuredOf} slots={{ matched, gaps: <Joined items={gapsOf(result)} /> }} />{" "}
      <TextLink href={dataReadinessHref(result.sources.map((source) => source.key), result.tool)}>{copy.coverage.link}</TextLink>
    </p>
  );
}

function Coverage({ result, check, linked = true }: { result: ComparablesResult; check?: NumCheck; linked?: boolean }) {
  const { coverage } = result;
  const gaps = gapsOf(result);
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
      href={linked ? dataReadinessHref(result.sources.map((source) => source.key), result.tool) : undefined}
    />
  );
}

// Ticket 116: the coverage line and the source line the section prints under its chart, for a slide that draws a
// recorded answer with RangeFigure. The slide stands in for the app when the app is down, so the coverage line has no
// link into it.
export function RangeFigureLines({ result }: { result: ComparablesResult }) {
  return (
    <>
      <Coverage result={result} check={coverageCheck(result)} linked={false} />
      <Source>
        <SourceLine result={result} />
      </Source>
    </>
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
  lead,
  compare,
  pressedNumber,
}: {
  result: ComparablesResult;
  open?: OpenComparable;
  planned?: PlannedMonths;
  more?: ReactNode;
  figure?: { twin: boolean };
  // The line before the finding, and "Compare with", from the zone (PastRange).
  lead?: ReactNode;
  compare?: ReactNode;
} & Lane2Props) {
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
  const [tableOpen, setTableOpen] = useState(abstained || Boolean(pressedNumber));
  const [page, setPage] = useState(0);
  // The rows a pressed number counts (ticket 101), or null for every row.
  const [filter, setFilter] = useState<RowFilter | null>(() => (pressedNumber ? rowFilters(result)[pressedNumber] : null));
  const [measure, width] = useWidth<HTMLDivElement>();
  const narrow = usePageNarrow(measure);
  const fontsReady = useFontsReady();
  const inputRef = useRef<HTMLInputElement>(null);
  const captionRef = useRef<HTMLSpanElement>(null);
  const countRef = useRef<HTMLParagraphElement>(null);
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

  // A pressed number opens the table filtered to the rows it counts (ticket 101): its title scrolls under the bar and
  // focus moves to the count line, which repeats the pressed number. "Show all" brings every row back.
  const landOnRows = (shown: RowFilter | null) => {
    setFilter(shown);
    setPage(0);
    setTableOpen(true);
    requestAnimationFrame(() => {
      captionRef.current?.scrollIntoView({ block: "start" });
      countRef.current?.focus({ preventScroll: true });
    });
  };
  // The filters the tool's own numbers can name: the plan row's months and its count, and the past range's points.
  const filters = rowFilters(result);
  const toRows = (shown: RowFilter | null) => () => landOnRows(shown);
  // Each number in the finding and the summary has its own What sentence (DESIGN.md, Number tooltip), comes from the
  // notices and contract awards the tool counted, and opens the table at the rows it counts, as its action line says.
  const records = recordsFrom(result.sources, result.records_through);
  const fromRecords = records ? <FromLine words={records} /> : undefined;
  const opensRows = (act: ReactNode, shown: RowFilter | null) => ({ from: fromRecords, act, opens: "rows", onOpen: toRows(shown) }) as const;
  const toAll = opensRows(copy.num.act.all(abstained ? spelled(total) : whole(total)), null);
  const withinRows = result.plan && filters.within ? opensRows(words.act.within(result.plan.within, spelled(result.plan.within)), filters.within) : toAll;
  const explainWithin: NumCheck | undefined = planRowMonths === null ? undefined : { tooltip: words.explain.within(months1(planRowMonths)), ...withinRows };
  const explainShare: NumCheck | undefined = planRowMonths === null ? undefined : { tooltip: words.explain.share(months1(planRowMonths)), ...withinRows };
  const explainTotal: NumCheck = { tooltip: words.explain.total(open, spelled(open)), ...toAll };
  // The middle half, the middle one and the 8-in-10 point count the packages still open as not signed yet.
  const statistic = (what: string, rows: ReturnType<typeof opensRows>): NumCheck => ({
    tooltip: open > 0 ? <>{what} {words.explain.openCounted(open, spelled(open))}</> : what,
    ...rows,
  });
  const explainMiddle = statistic(words.explain.middle(whole(total)), filters.middle ? opensRows(words.act.middle, filters.middle) : toAll);
  const explainMedian = statistic(words.explain.median, filters.median ? opensRows(words.act.median, filters.median) : toAll);
  const explainIn10 = statistic(words.explain.in10, filters.in10 && range?.q80 != null ? opensRows(words.act.in10(months1(range.q80)), filters.in10) : toAll);
  // The plan's months open the plan row they came from in the evidence drawer.
  const planWhat = pkg ? { tooltip: words.explain.plan, from: <FromLine words={planFrom(pkg.plan.implementing_agency, pkg.plan.plan_date)} /> } : null;
  const explainPlan: NumCheck | undefined = !pkg || !planWhat
    ? undefined
    : pkg.evidence_id && !figure
      ? { ...planWhat, act: copy.num.act.planRow, opens: "record", onOpen: (element: HTMLElement) => openPlanRow(pkg.evidence_id, element) }
      : planWhat;

  const type = chartType(width || 800);

  // ── The finding, at the plan row's own months ──
  const count = (value: number, check?: NumCheck) => <Num value={value} options={{ compact: false }} check={check} />;
  const q = (value: number | null, check: NumCheck) => (value === null ? null : <Num value={value} options={{ decimals: 1, compact: false }} check={check} />);
  let title: ReactNode;
  // Below 20 comparable packages the count of those signed within the plan follows the finding in body (ticket 101).
  let fewCount: ReactNode = null;
  if (abstained) {
    title =
      total === 1 ? (
        words.title.abstainOne
      ) : (
        <Fill template={words.title.abstain} slots={{ n: <Num count={total} check={explainTotal} /> }} />
      );
    if (result.plan) {
      const w = result.plan.within;
      const f = words.fewCount;
      const template = total === 1 ? (w === 0 ? f.noneOne : f.allOne) : w === 0 ? f.none : w === total ? f.all : f.some;
      fewCount = (
        <Fill
          template={template}
          slots={{
            within: <Num count={w} capital check={explainWithin} />,
            total: <Num count={total} />,
            plan: <Num value={result.plan.months} options={{ decimals: 1, compact: false }} check={explainPlan} />,
          }}
        />
      );
    }
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
          within: count(w, explainWithin),
          total: count(total, explainTotal),
          in10: share === null ? null : count(share.states[0], explainShare),
          plan: <Num value={result.plan.months} options={{ decimals: 1, compact: false }} check={explainPlan} />,
        }}
      />
    );
  } else if (range?.q25 != null && range.q75 != null) {
    title = <Fill template={words.title.noPlan} slots={{ total: count(total, explainTotal), q25: q(range.q25, explainMiddle), q75: q(range.q75, explainMiddle) }} />;
  } else {
    title = <Fill template={words.title.noPlanNoRange} slots={{ total: count(total, explainTotal) }} />;
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
        <Fill template={s.middleOnly} slots={{ q50: q(range.q50, explainMedian) }} />
      ) : (
        <Fill template={s.middle} slots={{ q25: q(range.q25, explainMiddle), q75: q(range.q75, explainMiddle), q50: q(range.q50, explainMedian) }} />
      );
    const second = range?.q80 == null ? s.noIn10 : <Fill template={s.in10} slots={{ q80: q(range.q80, explainIn10) }} />;
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
  // A dot's tooltip ends with where it came from and, when a click opens it, what that opens (DESIGN.md, Number
  // tooltip, Dot variant); its name says the same, since screen readers do not hear its tooltip.
  // The dot's name reads the From line as written; its tooltip keeps the date on one line.
  const dotFrom = records ? fromText(records) : "";
  const dotFromTip = records ? fromText(records, true) : "";
  const dotAct = opening ? (quantile ? c.openHintDots : c.openHint) : "";
  const marks: RangeMark[] = quantile
    ? quantile.map((dot) => ({
        key: `dot-${dot.k}`,
        months: dot.months,
        hollow: !dot.reached,
        beyond: !dot.reached,
        name: [(dot.reached ? c.dotQuantile : c.dotQuantileOpen)(whole(dot.k), whole(quantile.length), whole(total), months1(dot.months)), dotFrom, dotAct]
          .filter(Boolean)
          .join(" "),
        tip: {
          header: c.tipQuantile(whole(dot.k), whole(quantile.length)),
          mono: false,
          number: dot.reached ? c.tipMonths(months1(dot.months)) : c.tipPast(months1(dot.months)),
          line: dot.reached ? c.tipQuantileLine(whole(total), whole(quantile.length)) : c.tipQuantileOpen,
          from: dotFromTip,
        },
      }))
    : rows.map((row, index) => markFor(row, index, total, { from: dotFrom, fromTip: dotFromTip, act: dotAct }, comparison));

  const altParts = [
    quantile
      ? c.altDots(whole(total), whole(quantile.length), whole(axis.max))
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
      narrow={narrow}
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

  // The chart draws once the section has its width and the fonts have loaded, since its rows' heights come from its
  // labels' widths in Open Sans; until then the placeholder holds its height (ticket 59; the 12 review, round 11, P1).
  const chart = width > 0 && fontsReady && (
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
            keyLead={Boolean(quantile)}
            labels={{
              lane: c.lane,
              // The subtitle says what a quantile dot is, so the key does not say it again (ticket 58); a count in the key
              // is in words from one to nine, as the alt text and the summary write it (ticket 58; rule 12).
              keySigned: quantile ? null : c.keySigned(formatCount(counts.signed)),
              keyHollow: open > 0 ? (quantile ? c.keyOpenDots(formatCount(open, { capital: true })) : c.keyOpen(formatCount(open))) : null,
              plan: c.plan,
              middle:
                range?.q25 != null && range.q75 != null && range.q50 != null
                  ? c.middle(months1(range.q25), months1(range.q75), months1(range.q50))
                  : null,
              in10: range?.q80 != null ? c.in10(months1(range.q80)) : null,
              axisLast: c.axisLast(whole(axis.max)),
              alt: altParts.join(" "),
              group: quantile ? c.groupDots(whole(total), whole(quantile.length)) : c.group(whole(total)),
              groupHelp: opening ? (quantile ? c.groupHelpOpenDots : c.groupHelpOpen) : c.groupHelp,
              slider: c.slider,
              openHint: quantile ? c.openHintDots : c.openHint,
              open: quantile ? c.openDots : c.openRecords,
              lane2: copy.timeEstimate.lane,
              lane2Short: copy.timeEstimate.laneShort,
            }}
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
            lane2={estimate ? lane2For(estimate, comparison) : undefined}
            messageBelow={!figure}
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
  const placeholder = !(width > 0 && fontsReady) && <div style={{ height: estimate ? TWO_LANE_HEIGHT : CHART_HEIGHT }} data-chart-placeholder />;

  // Ticket 47: a slide shows the chart alone, read-only, or its table twin in the chart's place (the 47 brief,
  // section 4.4). The slide's own title states the finding, so there is no heading, plan control or summary here.
  if (figure) {
    return (
      <div ref={measure} data-range-figure={figure.twin ? "table" : "chart"}>
        {figure.twin ? (
          // A slide's twin lists every row at once up to the quantile dots' threshold, as before the page's 20-row pages
          // (ticket 101's review, follow-up 3).
          <ComparablesTable
            result={result}
            plan={plan}
            page={page}
            onPage={setPage}
            captionRef={captionRef}
            comparison={null}
            pageAbove={result.thresholds.quantile_dots_above}
          />
        ) : (
          <>
            {chart}
            {placeholder}
          </>
        )}
      </div>
    );
  }

  // When the time estimate holds back, its first-person sentence sits under the chart in body, with the neutral
  // dashed circle, never inside lane 2 (ticket 101; DESIGN.md section 5, Range chart).
  const lane2 = estimate ? lane2For(estimate, comparison) : undefined;
  const heldBack = lane2?.kind === "message" && lane2.tone === "abstain" ? lane2.text : null;

  return (
    <ZoneBlock
      data-block="took"
      foot={
        // The block's Note, its coverage line and its source line end it, in its foot strip.
        <FootStrip>
          <Note result={result} />
          <Coverage result={result} check={coverageCheck(result)} />
          <Source>
            <SourceLine result={result} />
          </Source>
        </FootStrip>
      }
    >
      <div ref={measure}>
        {lead && <div className="mb-4">{lead}</div>}
        {/* Strata's own words open with its byline, 8 px above them (ticket 111): what it found, or that it held back. */}
        <Byline kind={abstained ? "heldBack" : "found"} />
        {/* The finding, the page's largest type (DESIGN.md section 1, principle 6): or, below 20 comparable packages,
            the first-person sentence that holds back, with the count after it in body. */}
        <p id={ids.title} className="mt-2 max-w-[22.5em] text-finding text-balance text-ink-heading" data-finding>
          {title}
        </p>
        {fewCount && (
          <p className="mt-3 max-w-prose text-body text-ink" data-few-count>
            {fewCount}
          </p>
        )}
        {abstained && more}
        {narrow && <div className="mt-2">{summaryBlock}</div>}
        <p className="mt-2 text-ink-muted" style={{ fontSize: type.m }}>
          {quantile ? <Fill template={words.subtitleDots} slots={{ total: whole(total), dots: whole(quantile.length) }} /> : words.subtitle}
        </p>
        <div className="mt-4">{control}</div>
        {compare}
        <figure aria-labelledby={ids.title} className="mt-4" data-chart-figure>
          {chart}
          {placeholder}
        </figure>
        {heldBack && (
          <div className="mt-4 flex items-start gap-2" data-lane2-message="abstain">
            <CircleDashed aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-line-strong" />
            <p className="min-w-0 max-w-prose text-body text-ink">{heldBack}</p>
          </div>
        )}
        {/* While the time estimate loads, the sentence of one that holds back keeps its place under the chart, unseen and
            unheard, as the demo package draws it, so the chart and the card's end stay put (ticket 59; the critique of
            round 2). A given estimate draws its track record here instead. */}
        {estimate?.status === "loading" && (
          <div aria-hidden="true" className="mt-4 flex items-start gap-2" data-lane2-message="loading">
            <span className="size-5 shrink-0" />
            <p className="min-w-0 max-w-prose text-body">
              <SkeletonWords text={copy.timeEstimate.abstain.outsideOther} />
            </p>
          </div>
        )}
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
        <div className="mt-4">
          <Button
            variant="ghost"
            flush
            aria-expanded={tableOpen}
            aria-controls={ids.table}
            onClick={() => {
              // Only a pressed number filters the table: opened by this button, it lists every package from the first
              // page (ticket 101's review, follow-up 4).
              if (!tableOpen) {
                setFilter(null);
                setPage(0);
              }
              setTableOpen(!tableOpen);
            }}
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
              countRef={countRef}
              filter={filter}
              onShowAll={() => landOnRows(null)}
              open={opening}
              comparison={comparison}
            />
          )}
        </div>
      </div>
    </ZoneBlock>
  );
}

function markFor(
  row: Comparable,
  index: number,
  total: number,
  tip: { from: string; fromTip: string; act: string },
  comparison: Comparison | null = null,
): RangeMark {
  const c = words.chart;
  const m = months1(row.months);
  const country = row.country_name ?? copy.notInRecord;
  // Its sentence, with full dates (DESIGN.md section 7, rule 13); in the tooltip each date stays on one line.
  const sentence = (date: (iso: string) => string) =>
    row.still_open ? c.tipOpen(country, date(row.notice_date)) : c.tipSigned(country, date(row.notice_date), date(row.signed_on!));
  const line = sentence(formatDate);
  const own = c.dotName(row.step_reference, m, [line, tip.from, tip.act].filter(Boolean).join(" "), whole(index + 1), whole(total));
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
      line: sentence((iso) => wholeDate(formatDate(iso))),
      from: tip.fromTip,
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
  narrow,
  onType,
  onReset,
}: {
  // A package planned from a sentence: the line is the person's own plan, with no plan row behind it.
  planned?: boolean;
  // Whether the page lays out narrow (usePageNarrow), which places the reset button.
  narrow: boolean;
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
        {resetButton(narrow ? "hidden" : "inline", false)}
      </div>
      {/* The helper sits right under the input it explains, and one caption line is kept under the helper for the
          error, so the error appears between the helper and the chart without moving the chart (ticket 59). */}
      <div className={cx("mt-1", narrow ? "grid" : "block")}>
      <p id={ids.helper} className={cx("col-start-1 row-start-1 text-caption text-ink-muted", moved && narrow && "invisible")}>
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
      {resetButton(cx("col-start-1 row-start-1 self-start", !narrow && "hidden"), true)}
      </div>
      <p id={ids.error} className="mt-1 min-h-lh text-caption text-error">
        {invalid && w.invalid(whole(maxMonths))}
      </p>
    </div>
  );
}

// ── The table twin ───────────────────────────────────────────────────────

// The rows a number in the finding or the summary counts (ticket 101), and the count line that says so: it repeats the
// pressed number and no other, so it never states a number the tool did not return. The rows are chosen by the same
// months the table's last column and the chart's dots show.
export type RowFilter = { key: "within" | "middle" | "median" | "in10"; line: string; keep: (row: Comparable) => boolean };

function rowFilters(result: ComparablesResult): Record<RowFilter["key"], RowFilter | null> {
  const shown = words.table.shown;
  const plan = result.plan;
  const range = result.abstention ? null : result.past_range;
  const total = whole(result.counts?.comparables ?? result.rows.length);
  const q25 = range?.q25 ?? null;
  const q75 = range?.q75 ?? null;
  const q50 = range?.q50 ?? null;
  const q80 = range?.q80 ?? null;
  // A filter that would leave no row is not offered: its number opens every row instead.
  const some = (filter: RowFilter | null) => (filter && result.rows.some(filter.keep) ? filter : null);
  // Nor is "the middle package" when two or more packages share the middle's months, at one decimal.
  const one = (filter: RowFilter | null) => (filter && result.rows.filter(filter.keep).length === 1 ? filter : null);
  // The quartiles are Kaplan-Meier days on which a package was signed, and a package still open is censored, so every
  // statistic's rows are signed packages, as the plan's count is (ticket 101's review, follow-up 2).
  const signed = (row: Comparable) => !row.still_open;
  return {
    // The plan's count is the tool's own (plan.within); a plan of none counted opens no rows.
    within: some(
      plan && plan.within > 0
        ? { key: "within", line: shown.within(whole(plan.within), total, months1(plan.months)), keep: (row) => signed(row) && row.months <= plan.months }
        : null,
    ),
    middle: some(
      q25 !== null && q75 !== null
        ? { key: "middle", line: shown.middle(months1(q25), months1(q75)), keep: (row) => signed(row) && row.months >= q25 && row.months <= q75 }
        : null,
    ),
    median: one(q50 !== null ? { key: "median", line: shown.median(months1(q50)), keep: (row) => signed(row) && row.months === q50 } : null),
    in10: some(q80 !== null ? { key: "in10", line: shown.in10(months1(q80)), keep: (row) => signed(row) && row.months <= q80 } : null),
  };
}

function ComparablesTable({
  result,
  plan,
  page,
  onPage,
  captionRef,
  countRef,
  filter = null,
  onShowAll,
  open,
  comparison = null,
  pageAbove = PAGE,
}: {
  result: ComparablesResult;
  plan: number | null;
  // Above how many rows the table pages, 20 at a time.
  pageAbove?: number;
  page: number;
  onPage: (page: number) => void;
  captionRef: Ref<HTMLSpanElement>;
  // The count line, which takes focus when a pressed number lands on the rows it counts.
  countRef?: Ref<HTMLParagraphElement>;
  // The rows a pressed number counts, and the button after its count line that shows every row again.
  filter?: RowFilter | null;
  onShowAll?: () => void;
  open?: OpenComparable;
  // Ticket 26: while comparing, a column says whether each package went with the option.
  comparison?: Comparison | null;
}) {
  const t = words.table;
  const all = result.rows;
  const rows = filter ? all.filter(filter.keep) : all;
  const total = all.length;
  // Twenty rows a page (ticket 101; the plan's section 7.4: "Show all 49" shows the first 20 of 49).
  const paged = rows.length > pageAbove;
  const from = paged ? page * PAGE : 0;
  const shown = paged ? rows.slice(from, from + PAGE) : rows;
  // With one line per cell the six columns need about 776 px, so the table shows when its frame has
  // 49rem and cards below that (cardsBelow="fit", DESIGN.md section 5, Tables). That is from a page area
  // of about 930 to 1199 px and from about 1360 px, where the page's content reaches its 1280 px (ticket 94). There a STEP reference keeps to one line, a date fits
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
  // Its source line is the zone's foot strip's, or a slide's RangeFigureLines', so the table repeats none (ticket 101).
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
            {total === 1 ? t.captionOne : filter ? t.captionFiltered : t.caption(spelled(total))}
          </span>
        }
        level={4}
        count={{
          noun: t.noun,
          one: t.nounOne,
          total,
          from: from + 1,
          to: from + shown.length,
          // Every row of a few is in words, as every count line writes one to nine (Table's countText; ticket 58).
          text: filter?.line,
        }}
        countRef={countRef}
        countAction={
          filter && (
            <Button variant="ghost" flush onClick={onShowAll} data-show-all>
              {t.showAll(whole(total))}
            </Button>
          )
        }
        columns={columns}
        rowHeader="package"
        cardsBelow="fit"
        cardRows
        cardsNote={t.columns.monthsCards}
        selected={open?.opened ?? null}
        state={{ status: "ready", rows: tableRows }}
      />
      {paged && (
        <div className="mt-3 flex flex-wrap gap-3">
          <Button variant="secondary" disabled={page === 0} onClick={() => onPage(page - 1)}>
            {t.previous}
          </Button>
          <Button variant="secondary" disabled={from + PAGE >= rows.length} onClick={() => onPage(page + 1)}>
            {t.next}
          </Button>
        </div>
      )}
    </>
  );
}

// ── Loading ──────────────────────────────────────────────────────────────

// The block while find_comparables answers: the skeleton in the block's body and the foot strip's three lines under
// it, as the drawn block has its Note, coverage line and source line in its foot strip (ticket 101). The lines each part
// takes are read from the block's own width, w, and set from the demo package's section at 320 to 1440 px, so the
// chart starts within 24 px of the skeleton's and the block ends within 48 px of it (ticket 59).
function PastRangeLoading({ lead, twoLanes }: { lead: ReactNode; twoLanes: boolean }) {
  const [measure, width] = useWidth<HTMLDivElement>();
  const narrow = usePageNarrow(measure);
  const w = width || 800;
  return (
    <ZoneBlock
      data-block="took"
      foot={
        <FootStrip>
          <PastRangeFootSkeleton width={w} />
        </FootStrip>
      }
    >
      <div ref={measure}>
        {lead}
        <PastRangeSkeleton twoLanes={twoLanes} width={w} narrow={narrow} />
      </div>
    </ZoneBlock>
  );
}

const skeletonLines = (count: number, last = "w-3/5") => Array.from({ length: count }, (_, index) => (index === count - 1 ? last : "w-full"));

// Sized like the populated section at each width, in its order: below 768 px (narrow, as the drawn section reads it)
// the summary comes right after the finding, and the helper's place is at least the reset button's height; from 768 px
// the summary follows the chart. The subtitle is the copy file's own sentence, held as skeleton words, at the chart's
// type size (chartType), read from the section's width as the populated section reads it.
function PastRangeSkeleton({ twoLanes, width, narrow }: { twoLanes: boolean; width: number; narrow: boolean }) {
  const type = chartType(width);
  const finding = narrow ? (width < 300 ? 5 : width < 380 ? 4 : width < 560 ? 3 : 2) : width < 560 ? 3 : 2;
  // With lane 2 the summary holds its sentences too.
  const summary = twoLanes
    ? narrow
      ? width < 290 ? 10 : width < 350 ? 8 : width < 400 ? 7 : width < 460 ? 6 : width < 600 ? 5 : 4
      : width < 780 ? 4 : 3
    : narrow
      ? width < 290 ? 8 : width < 350 ? 6 : width < 470 ? 5 : width < 600 ? 4 : 3
      : width < 640 ? 4 : width < 900 ? 3 : 2;
  const summaryLines = <SkeletonText className={cx(narrow ? "mt-2" : "mt-4", "text-body")} widths={skeletonLines(summary, "w-2/5")} />;
  // Lane 2's sentence under the chart, as when the time estimate holds back (the fixture's demo package).
  const lane2Lines = width < 300 ? 4 : width < 420 ? 3 : 2;
  return (
    <div aria-hidden="true" data-past-range-skeleton>
      {/* The byline's line over the finding (ticket 111), and the finding's lines in its own style (ticket 101). */}
      <SkeletonLine className="text-label" width="w-24" />
      <SkeletonText className="mt-2 max-w-[22.5em] text-finding" widths={skeletonLines(finding)} />
      {narrow && summaryLines}
      <p className="mt-2" style={{ fontSize: type.m }}>
        <SkeletonWords text={words.subtitle} />
      </p>
      <div className="mt-4 flex flex-wrap items-center gap-x-3 gap-y-2">
        <SkeletonLine className="text-small" width="w-28" />
        <Skeleton className="h-11 w-[88px] rounded-sm" />
      </div>
      {/* Under 300 px the plan's row takes a second row of its own. */}
      {width < 300 && <span className="block h-11" />}
      {/* The helper under the input, then the error's held line. Below 768 px the helper's place holds the reset button
          too, so it is at least 44 px tall. */}
      {narrow ? <SkeletonText className="mt-1 min-h-11 text-caption" widths={skeletonLines(2)} /> : <SkeletonLine className="mt-1 text-caption" width="w-3/5" />}
      <span className="mt-1 block min-h-lh text-caption" />
      {/* Under 300 px the chart's key takes a second line of row A (DESIGN.md section 6). */}
      <div className="mt-4" style={{ height: (twoLanes ? TWO_LANE_HEIGHT : CHART_HEIGHT) + (width < 300 ? 16 : 0) }} data-chart-skeleton>
        <Skeleton className="h-full w-full rounded-md" />
      </div>
      {/* Ticket 26: lane 2's sentence after the chart, as a time estimate that holds back writes it; one that is given
          has its track record and its plan-date choice there instead (ticket 59, set from the fixture). */}
      {twoLanes && <SkeletonText className="mt-4 text-body" widths={skeletonLines(lane2Lines)} />}
      {!narrow && summaryLines}
      {/* "Show the table". */}
      <span className="mt-4 block h-11" />
    </div>
  );
}

// The foot strip's places while the block loads: the Note, the coverage line, whose numbers you can check make its
// lines 24 px, and the source line.
function PastRangeFootSkeleton({ width }: { width: number }) {
  const note = width < 300 ? 5 : width < 360 ? 4 : 3;
  const coverage = width < 300 ? 7 : width < 420 ? 5 : 4;
  const source = width < 300 ? 6 : width < 360 ? 5 : width < 480 ? 4 : 3;
  return (
    <>
      <SkeletonText className="text-caption" widths={skeletonLines(note)} />
      <SkeletonText className="text-caption leading-6" widths={skeletonLines(coverage)} />
      <SkeletonText className="text-caption" widths={skeletonLines(source)} />
    </>
  );
}
