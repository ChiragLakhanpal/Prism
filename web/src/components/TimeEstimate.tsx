// The time estimate's parts of section 1, "How long it took" (ticket 26; the 26 brief): lane 2's data for the range
// chart, the summary's sentences, "Compare with", the track record with its table of test years, the plan-date
// choice and the time estimate's table in the twin. PastRange.tsx places them; every number is estimate_time's,
// written by web/src/lib/format.ts through Num, and nothing here counts, rounds or decides a value.
import { useId, useRef, type ReactNode, type Ref } from "react";
import { copy } from "../copy";
import type { ApiError, Comparison, EstimatePoints, EstimateResult, PlanDateChoice } from "../lib/api";
import type { PlanDateChoiceState } from "../lib/estimates";
import { formatCount, formatDate, formatNumber } from "../lib/format";
import { Button } from "./Button";
import { Fill } from "./Fill";
import { Num, type NumCheck } from "./Num";
import { backtestFrom, estimateFrom, FromLine, modelFrom } from "./NumFrom";
import type { Lane2 } from "./RangeChart";
import { SegmentedControl } from "./SegmentedControl";
import { Skeleton, SkeletonLine, SkeletonWords } from "./Skeleton";
import { Source } from "./Source";
import { Table, type Column, type Row } from "./Table";

const words = copy.timeEstimate;
const what = copy.whatIf;
const POINTS = ["q25", "q50", "q75", "q80"] as const;
// The plan-date choice's two options, the stored values ticket 27's section 2 shares.
const PLAN_DATE_CHOICES: PlanDateChoice[] = ["middle", "eight_in_ten"];

export type EstimateState =
  | { status: "loading" }
  | { status: "error"; error: ApiError | null; onRetry: () => void; retrying: boolean }
  | { status: "ready"; result: EstimateResult };

// The viewer's plan-date choice (web/src/lib/estimates.ts, usePlanDateChoice): the one chosen, how to choose (saved
// 500 ms after the last move, ticket 15's rule), whether this view may change it, whether the last save failed, and
// how many saves have landed, so the section says each one once.
export type PlanDateProps = PlanDateChoiceState;

export const months1 = (value: number) => formatNumber(value, { decimals: 1, compact: false });
const whole = (value: number) => formatNumber(value, { compact: false });

// An option's words: its segment label ("Open national", "3 lots", "Prequalification") and its words inside a
// sentence ("open national", "3 lots", "prequalification").
export function optionWords(lever: string, value: string | number): { label: string; inSentence: string } {
  if (lever === "lots") {
    const text = what.lots(Number(value));
    return { label: text, inSentence: text };
  }
  const labels = lever === "market_approach" ? what.label_market_approach : what.label_prequalification;
  const inSentence = lever === "market_approach" ? what.inSentence_market_approach : what.inSentence_prequalification;
  const text = String(value);
  return { label: labels[text] ?? text, inSentence: inSentence[text] ?? text };
}

const pointsOf = (points: EstimatePoints): EstimatePoints => ({ q25: points.q25, q50: points.q50, q75: points.q75, q80: points.q80 });

export const estimated = (state: EstimateState | undefined) =>
  state?.status === "ready" && state.result.abstention === null && state.result.estimate ? state.result : null;

// The sentence for a package outside what the model learned from, the same in lane 2 and in the chart's text
// alternative: which feature, and whether the package lies above or below what the model saw.
function outsideSentence(abstention: { feature: string; value: number; high: number }): string {
  const side = abstention.value > abstention.high ? "high" : "low";
  const sentences = words.abstain.outside[abstention.feature as keyof typeof words.abstain.outside];
  return sentences ? sentences[side] : words.abstain.outsideOther;
}

// Lane 2's message for an abstention, in the first person (the 26 brief, sections 7.5 and 7.6).
export function abstentionMessage(result: EstimateResult): ReactNode {
  const abstention = result.abstention!;
  if (abstention.reason === "too_few_comparables") {
    return abstention.count === 1 ? words.abstain.fewOne : <Fill template={words.abstain.few} slots={{ n: <Num count={abstention.count} /> }} />;
  }
  if (abstention.reason === "outside_training") return outsideSentence(abstention);
  if (abstention.reason === "asof_before_training") {
    return <Fill template={words.abstain.beforeTraining} slots={{ date: <Num date={abstention.as_of} /> }} />;
  }
  return words.abstain.noModel;
}

// Row E's sentence while comparing with an option that has no time estimate.
function shortNote(comparison: Comparison, option: string): string {
  const abstention = comparison.abstention!;
  if (abstention.reason === "too_few_in_subgroup") return what.short.too_few_in_subgroup(formatCount(comparison.k), option);
  if (abstention.reason === "not_in_model") return what.short.not_in_model;
  if (abstention.reason === "outside_training") return what.short.outside_training;
  return what.short.value_not_learned;
}

// What lane 2 draws, from estimate_time's answer and the comparison pressed, if any.
export function lane2For(state: EstimateState, comparison: Comparison | null): Lane2 {
  if (state.status === "loading") return { kind: "loading" };
  if (state.status === "error") return { kind: "message", tone: "error", text: words.abstain.error };
  const result = state.result;
  if (result.abstention !== null || !result.estimate) return { kind: "message", tone: "abstain", text: abstentionMessage(result) };
  const described = pointsOf(result.estimate);
  const labelsOf = (points: EstimatePoints) => ({
    middle: words.middle(months1(points.q25), months1(points.q75), months1(points.q50)),
    in10: words.in10(months1(points.q80)),
  });
  if (!comparison) {
    return { kind: "estimate", bar: described, ghost: null, labels: labelsOf(described), note: null, keyBar: words.keyDescribed, keyGhost: null };
  }
  const option = optionWords(comparison.lever, comparison.value);
  const bar = comparison.estimate ? pointsOf(comparison.estimate) : null;
  return {
    kind: "estimate",
    bar,
    ghost: described,
    labels: bar ? labelsOf(bar) : null,
    note: bar ? null : shortNote(comparison, option.inSentence),
    keyBar: bar ? words.keyWith(option.inSentence) : null,
    keyGhost: words.keyDescribed,
  };
}

// The same abstention as plain text, for the chart's text alternative.
function abstentionText(result: EstimateResult): string {
  const abstention = result.abstention!;
  if (abstention.reason === "asof_before_training") return words.abstain.beforeTraining.replace("{date}", formatDate(abstention.as_of));
  if (abstention.reason === "outside_training") return outsideSentence(abstention);
  return words.abstain.noModel;
}

// The chart's text alternative for lane 2, after lane 1's sentences.
export function lane2Alt(state: EstimateState, comparison: Comparison | null, total: number): string {
  if (state.status !== "ready") return state.status === "error" ? words.abstain.error : "";
  const result = state.result;
  if (result.abstention?.reason === "too_few_comparables") return words.alt.abstainFew;
  if (result.abstention !== null || !result.estimate) return abstentionText(result);
  const e = result.estimate;
  if (!comparison) return words.alt.described(months1(e.q25), months1(e.q75), months1(e.q50), months1(e.q80));
  const option = optionWords(comparison.lever, comparison.value).inSentence;
  const ghost = words.alt.ghost(months1(e.q25), months1(e.q75), months1(e.q50), months1(e.q80));
  const k = whole(comparison.k);
  if (comparison.estimate) {
    const w = comparison.estimate;
    return `${words.alt.comparing(option, k, whole(total), months1(w.q25), months1(w.q75), months1(w.q50), months1(w.q80))} ${ghost}`;
  }
  const note = comparison.abstention?.reason === "too_few_in_subgroup" ? words.alt.comparingFew : words.alt.comparingNone;
  return `${note(option, k, whole(total))} ${ghost}`;
}

// ── The summary's sentences ──────────────────────────────────────────────

export type SummaryLinks = {
  // Opens the test-year table and moves focus to its caption: a time estimate figure's evidence is the backtest.
  onTestYears: () => void;
  // Opens section 1's table twin: at the time estimate table, or at the comparables table.
  onTwin: () => void;
  // Opens the drawer's list of the packages a comparison's count names.
  onWentWith: (comparison: Comparison, element: HTMLElement) => void;
};

function months(value: number, check?: NumCheck) {
  return <Num value={value} options={{ decimals: 1, compact: false }} check={check} />;
}

// A count that opens the drawer's list of the packages it names: the drawer gives focus back to it.
function WentWithCount({ comparison, option, capital, onOpen, from }: { comparison: Comparison; option: string; capital?: boolean; onOpen: SummaryLinks["onWentWith"]; from: ReactNode }) {
  const anchor = useRef<HTMLSpanElement>(null);
  return (
    <span ref={anchor}>
      <Num
        count={comparison.k}
        capital={capital}
        check={{
          tooltip: what.explainCount(option, whole(comparison.n)),
          from,
          act: what.explainCountAct,
          opens: "record",
          onOpen: () => {
            const button = anchor.current?.querySelector("button");
            if (button) onOpen(comparison, button);
          },
        }}
      />
    </span>
  );
}

// The sentences lane 2 adds to the summary paragraph: the time estimate, why the lanes differ and, while
// comparing, the comparison; or the sentence an abstention adds.
export function EstimateSentences({ state, comparison, links }: { state: EstimateState; comparison: Comparison | null; links: SummaryLinks }) {
  // While the estimate loads, the sentence a held-back estimate adds holds its place, unseen and unheard, so the summary
  // keeps its lines when the answer arrives (ticket 59; the critique of round 2).
  if (state.status === "loading") return <SkeletonWords text={words.abstain.outsideSummary} />;
  if (state.status !== "ready") return null;
  const result = state.result;
  if (result.abstention?.reason === "too_few_comparables") {
    return <Fill template={words.abstain.fewSummary} slots={{ min: whole(result.thresholds.min_comparables) }} />;
  }
  if (result.abstention !== null || !result.estimate) return <>{words.abstain.outsideSummary}</>;
  const e = result.estimate;
  // The middle half's ends share one What sentence, as one record that opens one thing; the 8-in-10 point has its own.
  const model = { from: <FromLine words={modelFrom(e.scored_on)} />, act: words.explain.estimateAct, opens: "rows", onOpen: links.onTestYears } as const;
  const explainMiddle: NumCheck = { tooltip: words.explain.estimateMiddle, ...model };
  const explainIn10: NumCheck = { tooltip: words.explain.estimateIn10, ...model };
  // The difference from the past range and the counts behind it, which the time estimate worked out for this package.
  const worked = <FromLine words={estimateFrom(result.as_of)} />;
  const lane = (
    <Fill
      template={words.summary}
      slots={{ e25: months(e.q25, explainMiddle), e75: months(e.q75, explainMiddle), e80: months(e.q80, explainIn10) }}
    />
  );
  const parts: ReactNode[] = [lane];
  const difference = result.difference;
  if (difference) {
    if (difference.direction === "same") parts.push(words.why.same);
    else {
      const later = difference.direction === "later";
      const diff = months(difference.middle_diff_months, { tooltip: words.explain.diff, from: worked, act: words.explain.diffAct, opens: "rows", onOpen: links.onTwin });
      const reasons = difference.reasons.map((reason) => (
        <Fill
          key={reason.code}
          template={words.reasons[reason.code]}
          slots={{
            k: (
              <Num
                count={reason.k}
                check={{ tooltip: words.explain[reason.code](whole(reason.n)), from: worked, act: words.explain.sizeAct, opens: "rows", onOpen: links.onTwin }}
              />
            ),
            n: <Num value={reason.n} options={{ compact: false }} />,
          }}
        />
      ));
      const template =
        reasons.length === 0
          ? later ? words.why.laterOnly : words.why.earlierOnly
          : reasons.length === 1
            ? later ? words.why.later : words.why.earlier
            : later ? words.why.laterTwo : words.why.earlierTwo;
      parts.push(<Fill template={template} slots={{ diff, reason1: reasons[0], reason2: reasons[1] }} />);
    }
  }
  if (comparison) {
    const option = optionWords(comparison.lever, comparison.value).inSentence;
    const k = <WentWithCount comparison={comparison} option={option} capital onOpen={links.onWentWith} from={worked} />;
    const n = <Num value={comparison.n} options={{ compact: false }} />;
    if (comparison.estimate) {
      const w = comparison.estimate;
      const withOption: NumCheck = { tooltip: words.explain.estimateMiddleWith, ...model };
      const withOptionIn10: NumCheck = { tooltip: words.explain.estimateIn10With, ...model };
      parts.push(
        <Fill
          template={what.summary}
          slots={{
            k, n, option,
            w25: months(w.q25, withOption), w75: months(w.q75, withOption), w80: months(w.q80, withOptionIn10),
            b25: months(e.q25, explainMiddle), b75: months(e.q75, explainMiddle), b80: months(e.q80, explainIn10),
          }}
        />,
      );
    } else {
      const reason = comparison.abstention?.reason;
      const template =
        reason === "too_few_in_subgroup"
          ? comparison.k === 1 ? what.abstainOne : what.abstain
          : reason === "not_in_model" ? what.notInModel : what.notLearned;
      parts.push(<Fill template={template} slots={{ k, n, option }} />);
    }
    if (comparison.lever === "lots" && result.package.described?.review_type) {
      parts.push(<Fill template={what.lotsReview} slots={{ reviewType: result.package.described.review_type }} />);
    }
  }
  return (
    <>
      {parts.map((part, index) => (
        <span key={index}>
          {index > 0 && " "}
          {part}
        </span>
      ))}
    </>
  );
}

// ── "Compare with" ───────────────────────────────────────────────────────

export function CompareControl({ result, pressed, onPress }: { result: EstimateResult; pressed: string | null; onPress: (lever: string | null) => void }) {
  const descriptionId = useId();
  if (result.comparisons.length === 0) {
    return (
      <p className="text-small text-ink-muted" data-compare-none>
        {what.none}
      </p>
    );
  }
  return (
    <>
      <SegmentedControl
        kind="toggle"
        legend={what.label}
        describedBy={descriptionId}
        pressed={pressed}
        onPress={onPress}
        options={result.comparisons.map((comparison) => {
          const option = optionWords(comparison.lever, comparison.value);
          return { value: comparison.lever, label: option.label, description: what.segment(option.inSentence) };
        })}
      />
      <span id={descriptionId} className="sr-only">
        {what.description}
      </span>
    </>
  );
}

// ── Under the chart: the track record and the plan-date choice ───────────

function TrackRecordLine({ result, onTestYears }: { result: EstimateResult; onTestYears: () => void }) {
  const track = result.track_record;
  const t = words.track;
  if (track === null) return <>{t.none}</>;
  // not_readable, the only answer with no test year: the viewer can't read strata.ops.
  if (track.year === null) return <>{t.notReadable}</>;
  if (track.abstention !== null) {
    return <Fill template={t.unavailable} slots={{ min: whole(track.abstention.min_unseen_packages), year: <Num year={track.year} /> }} />;
  }
  // Each number of the track record says what it is, from the backtest for its year, and opens every test year.
  const x = words.explain;
  const check = (what: string): NumCheck => ({
    tooltip: what,
    from: <FromLine words={backtestFrom(String(track.year))} />,
    act: x.trackAct,
    opens: "rows",
    onOpen: onTestYears,
  });
  const count = (value: number, what: string) => <Num value={value} options={{ compact: false }} check={check(what)} />;
  const early = track.misses_early ?? 0;
  return (
    <>
      <span className="font-bold text-chart-text">{t.label}</span>{" "}
      <Fill
        template={t.sentence}
        slots={{
          n: count(track.n, x.trackN),
          year: <Num year={track.year} check={check(x.trackYear)} />,
          m: count(track.m, x.trackM),
          expected: count(track.expected, x.trackExpected),
        }}
      />
      {early > 0 && track.misses_late !== null && (
        <>
          {" "}
          <Fill template={t.misses} slots={{ misses: count(track.misses, x.trackMisses), late: count(track.misses_late, x.trackLate) }} />
        </>
      )}
    </>
  );
}

// The two plan dates' labels: the time estimate's middle and 8-in-10 point, each with how many unseen packages ran
// longer than that point of their own time estimate, with the count first under 50 (DESIGN.md section 7, rule 15).
function planDateLabels(result: EstimateResult): [string, string] {
  const dates = result.plan_dates!;
  const p = words.planDates;
  const fill = (template: string, values: Record<string, string>) => template.replace(/\{(\w+)\}/g, (_, key: string) => values[key] ?? "");
  const tracked = result.track_record !== null && result.track_record.abstention === null;
  const label = (point: typeof dates.middle, middle: boolean) => {
    const value = months1(point.months);
    if (!tracked || point.in10 === null || point.total === null || point.ran_longer === null) {
      return fill(middle ? p.noTrackMiddle : p.noTrackEight, { months: value });
    }
    const counted = point.total < 50;
    const half = middle && point.in10 === 5;
    const template = counted ? (half ? p.countedHalf : p.counted) : half ? p.middleHalf : middle ? p.middle : p.eight;
    return fill(template, { months: value, in10: whole(point.in10), k: whole(point.ran_longer), n: whole(point.total) });
  };
  return [label(dates.middle, true), label(dates.eight_in_ten, false)];
}

export function PlanDateChoiceControl({ result, planDate }: { result: EstimateResult; planDate: PlanDateProps }) {
  const [middle, eight] = planDateLabels(result);
  const selected = planDate.chosen ?? result.plan_dates!.default;
  const captionId = useId();
  // Ticket 27's choice kind, the same control as section 2's "Date each step with", since both set one stored
  // choice. In a preview it still switches, as there, and the caption says the choice is not saved.
  return (
    <div data-plan-dates>
      <SegmentedControl<PlanDateChoice>
        legend={words.planDates.label}
        value={selected}
        onChange={planDate.onChoose}
        describedBy={captionId}
        options={PLAN_DATE_CHOICES.map((value) => ({ value, label: value === "middle" ? middle : eight }))}
      />
      <p id={captionId} className="mt-2 text-caption text-ink-muted">
        {words.planDates.caption}
        {planDate.held && <> {words.planDates.preview}</>}
      </p>
      {planDate.failed && (
        <p className="mt-1 text-caption text-error" data-plan-dates-failed>
          {words.planDates.failed}
        </p>
      )}
    </div>
  );
}

// The block under the summary: the track record, its test years and the plan-date choice. It keeps 112 px while
// lane 2 loads, so the notes under it never jump when the time estimate lands; an abstention collapses it.
export function EstimateExtras({
  state,
  planDate,
  yearsOpen,
  onToggleYears,
  onOpenYears,
  yearsCaptionRef,
}: {
  state: EstimateState;
  planDate?: PlanDateProps;
  yearsOpen: boolean;
  onToggleYears: () => void;
  // Opens the test years from a number in the track record, and moves focus to the table's caption.
  onOpenYears: () => void;
  yearsCaptionRef: Ref<HTMLSpanElement>;
}) {
  // While the estimate loads, the past range holds a held-back estimate's sentence above this place, as the demo package
  // draws it, and nothing is held here (ticket 59; the critique of round 2).
  if (state.status === "loading") return null;
  if (state.status === "error") {
    const code = state.error?.body?.trace_id;
    return (
      <div className="flex min-h-28 flex-col items-start gap-2" data-estimate-extras="error">
        <Button variant="secondary" onClick={state.onRetry} loading={state.retrying}>
          {words.abstain.tryAgain}
        </Button>
        {code && (
          <p className="text-caption text-ink-muted">
            <Fill template={words.abstain.code} slots={{ code: <span className="font-mono">{code}</span> }} />
          </p>
        )}
      </div>
    );
  }
  const result = state.result;
  if (result.abstention !== null || !result.estimate) return null;
  const tracked = result.track_record !== null && result.track_record.abstention === null;
  const testYearsId = `test-years-${result.as_of}`;
  return (
    <div className="flex min-h-28 flex-col gap-4" data-estimate-extras="ready">
      <div>
        <p className="text-chart-text-subtle" data-track-record>
          <TrackRecordLine result={result} onTestYears={onOpenYears} />
        </p>
        {tracked && result.test_years.length > 0 && (
          <>
            <div className="mt-2">
              <Button variant="ghost" flush aria-expanded={yearsOpen} aria-controls={testYearsId} onClick={onToggleYears}>
                {yearsOpen ? words.track.hide : words.track.show}
              </Button>
            </div>
            <div id={testYearsId} hidden={!yearsOpen} className="mt-2" data-test-years>
              {yearsOpen && <TestYearTable result={result} captionRef={yearsCaptionRef} />}
            </div>
          </>
        )}
      </div>
      {result.plan_dates && planDate && <PlanDateChoiceControl result={result} planDate={planDate} />}
    </div>
  );
}

function TestYearTable({ result, captionRef }: { result: EstimateResult; captionRef: Ref<HTMLSpanElement> }) {
  const y = words.testYears;
  const years = result.test_years;
  const note = <span className="block text-caption font-normal text-ink-muted">{y.columns.note}</span>;
  const columns: Column[] = [
    { key: "year", header: y.columns.year, short: true },
    { key: "n", header: y.columns.n, numeric: true },
    { key: "m", header: y.columns.m, numeric: true },
    { key: "expected", header: y.columns.expected, numeric: true },
    { key: "mine", header: <>{y.columns.mine}{note}</>, cardHeader: y.columns.mine, numeric: true },
    { key: "past", header: <>{y.columns.past}{note}</>, cardHeader: y.columns.past, numeric: true },
    { key: "plans", header: <>{y.columns.plans}{note}</>, cardHeader: y.columns.plans, numeric: true },
  ];
  const cell = (value: number | null, months = false) => (value === null ? y.notMeasured : months ? months1(value) : whole(value));
  const rows: Row[] = years.map((year) => ({
    id: String(year.year),
    cells: year.abstention
      ? { year: String(year.year), n: y.noModel, m: y.noModel, expected: y.noModel, mine: y.noModel, past: y.noModel, plans: y.noModel }
      : {
          year: String(year.year),
          n: cell(year.n),
          m: cell(year.m),
          expected: cell(year.expected),
          mine: cell(year.error_estimate_months, true),
          past: cell(year.error_past_range_months, true),
          plans: cell(year.error_plan_months, true),
        },
  }));
  const ranOn = result.track_record && result.track_record.abstention === null ? result.track_record.ran_on : null;
  const first = years[0]?.year;
  const last = years[years.length - 1]?.year;
  return (
    <Table
      title={
        <span ref={captionRef} tabIndex={-1} className="focus:outline-none" data-test-years-caption>
          {y.caption}
        </span>
      }
      level={4}
      count={{
        noun: y.noun,
        one: y.nounOne,
        total: years.length,
        text: years.length === 1 ? y.countOne(String(first)) : y.count(formatCount(years.length), String(first), String(last)),
      }}
      columns={columns}
      rowHeader="year"
      cardsBelow="fit"
      cardsNote={y.columns.note}
      state={{ status: "ready", rows }}
      source={ranOn ? <Fill template={y.source} slots={{ date: <Num date={ranOn} /> }} /> : y.sourceUndated}
    />
  );
}

// ── Section 1's table twin: the time estimate's four points ──────────────

export function TimeEstimateTable({ result, comparison }: { result: EstimateResult; comparison: Comparison | null }) {
  const t = words.table;
  const e = result.estimate!;
  const option = comparison ? optionWords(comparison.lever, comparison.value).inSentence : null;
  const columns: Column[] = [
    { key: "point", header: t.point },
    { key: "described", header: t.described, numeric: true },
    ...(comparison?.estimate && option ? [{ key: "with", header: t.with(option), numeric: true }] : []),
  ];
  const rows: Row[] = POINTS.map((name) => ({
    id: name,
    cells: { point: t.points[name], described: months1(e[name]), with: comparison?.estimate ? months1(comparison.estimate[name]) : null },
  }));
  return (
    <div data-time-estimate-table>
      <Table
        title={t.caption}
        level={4}
        columns={columns}
        rowHeader="point"
        state={{ status: "ready", rows }}
        source={<Fill template={words.source} slots={{ date: <Num date={e.scored_on} /> }} />}
      />
    </div>
  );
}

// While comparing, the comparables table's new column: whether each package went with the option.
export function wentWithCell(comparison: Comparison, reference: string): string {
  if (comparison.matching_ids.includes(reference)) return what.table.yes;
  if (comparison.unrecorded_ids.includes(reference)) return what.table.unknown;
  return what.table.no;
}

// A dot's name while comparing, after its own.
export function dotComparisonName(comparison: Comparison, reference: string): string {
  const option = optionWords(comparison.lever, comparison.value).inSentence;
  if (comparison.matching_ids.includes(reference)) return what.dot.went(option);
  if (comparison.unrecorded_ids.includes(reference)) return what.dot.unknown(what.lever[comparison.lever]);
  return what.dot.not(option);
}
