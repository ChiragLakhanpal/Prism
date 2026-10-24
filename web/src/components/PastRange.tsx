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
import { useCallback, useEffect, useId, useLayoutEffect, useRef, useState, type ReactNode, type Ref } from "react";
import { CircleDashed } from "lucide-react";
import { copy } from "../copy";
import type { ApiError, Comparable, ComparablesResult } from "../lib/api";
import { cx } from "../lib/cx";
import { formatDate, formatNumber } from "../lib/format";
import { Button } from "./Button";
import { CoverageLine } from "./Checks";
import { Fill, Joined } from "./Fill";
import { LoadError } from "./LoadError";
import { Num, type NumCheck } from "./Num";
import { axisFor, chartType, RangeChart, type PlanMove, type RangeMark } from "./RangeChart";
import { Skeleton, SkeletonLine, SkeletonText } from "./Skeleton";
import { Source } from "./Source";
import { Table, type Column, type Row } from "./Table";
import { TextLink } from "./TextLink";

const words = copy.pastRange;
const PAGE = 20;
const CHART_HEIGHT = 240;

const months1 = (value: number) => formatNumber(value, { decimals: 1, compact: false });
const whole = (value: number) => formatNumber(value, { compact: false });
const tableDate = (iso: string) => formatDate(iso, { style: "table" });

export type PastRangeState =
  | { status: "loading" }
  | { status: "error"; error: ApiError | null; retrying: boolean; attempt: number; onRetry: () => void }
  | { status: "ready"; result: ComparablesResult };

function useNarrow(): boolean {
  const query = "(width < 48rem)";
  const [narrow, setNarrow] = useState(() => typeof window !== "undefined" && window.matchMedia(query).matches);
  useEffect(() => {
    const list = window.matchMedia(query);
    const update = () => setNarrow(list.matches);
    update();
    list.addEventListener("change", update);
    return () => list.removeEventListener("change", update);
  }, []);
  return narrow;
}

function useWidth<T extends HTMLElement>(): [Ref<T>, number] {
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

export function PastRange({ state, headingRef }: { state: PastRangeState; headingRef?: Ref<HTMLHeadingElement> }) {
  const headingId = useId();
  const loading = state.status === "loading";
  const result = state.status === "ready" ? state.result : null;
  return (
    <section
      aria-labelledby={headingId}
      aria-busy={loading || undefined}
      data-past-range={state.status === "ready" ? kind(state.result) : state.status}
      className="rounded-md border border-line bg-surface p-4 md:p-6"
    >
      <p className="text-label text-ink-muted uppercase">{words.eyebrow}</p>
      <h2 ref={headingRef} id={headingId} tabIndex={-1} className="mt-1 text-h2 text-ink-heading focus:outline-none">
        <span aria-hidden="true">{words.number} </span>
        {words.heading}
      </h2>
      {state.status === "loading" && <PastRangeSkeleton />}
      {state.status === "error" && (
        <div className="mt-4">
          <LoadError
            error={state.error}
            message={words.error}
            permission={words.permission}
            onRetry={state.onRetry}
            retrying={state.retrying}
            attempt={state.attempt}
          />
        </div>
      )}
      {result && <Ready result={result} />}
      {loading && (
        <p role="status" className="sr-only">
          {words.loading}
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

function Ready({ result }: { result: ComparablesResult }) {
  const abstention = result.abstention;
  if (abstention?.reason === "no_public_notice") {
    return (
      <NoChart title={words.empty.notMeasurableTitle}>
        <p className="mt-2 max-w-prose text-body text-ink">
          <Fill template={words.empty.notMeasurableBody} slots={{ field: abstention.field, value: abstention.value }} />
        </p>
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
          <Coverage result={result} />
        </div>
      </NoChart>
    );
  }
  if (abstention?.reason === "no_comparables" || abstention?.reason === "unknown_package" || result.rows.length === 0) {
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
  return <Populated result={result} />;
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

const readinessHref = (result: ComparablesResult) =>
  `/data?sources=${result.sources.map((source) => source.key).join(",")}&from=${result.tool}`;

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
    <p className="text-ink-muted" data-chart-note>
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

function Coverage({ result, check }: { result: ComparablesResult; check?: NumCheck }) {
  const { coverage } = result;
  const gaps = coverage.not_used.map((entry) => (
    <Fill
      key={entry.reason}
      template={words.reasons[entry.reason](entry.count)}
      slots={{ count: <Num value={entry.count} options={{ compact: false }} check={check} /> }}
    />
  ));
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

function Populated({ result }: { result: ComparablesResult }) {
  const abstained = result.abstention?.reason === "too_few_comparables";
  const rows = result.rows;
  const total = rows.length;
  const counts = result.counts!;
  const open = counts.still_open;
  const quantile = !abstained && result.quantile_dots ? result.quantile_dots : null;
  const own = result.plan?.months ?? null;
  const maxMonths = result.thresholds.max_plan_months;
  const pkg = result.package!;

  const [plan, setPlan] = useState<number | null>(own);
  const [text, setText] = useState(own === null ? "" : months1(own));
  const [invalid, setInvalid] = useState(false);
  const [axisValue, setAxisValue] = useState<number | null>(own);
  const [announce, setAnnounce] = useState("");
  const [tableOpen, setTableOpen] = useState(abstained);
  const [page, setPage] = useState(0);
  const [measure, width] = useWidth<HTMLDivElement>();
  const narrow = useNarrow();
  const inputRef = useRef<HTMLInputElement>(null);
  const captionRef = useRef<HTMLSpanElement>(null);
  const axisTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const sayTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  useEffect(
    () => () => {
      clearTimeout(axisTimer.current);
      clearTimeout(sayTimer.current);
    },
    [],
  );

  const ids = { title: useId(), input: useId(), helper: useId(), error: useId(), table: useId() };
  const withinOf = useCallback(
    (months: number) => rows.filter((row) => !row.still_open && row.months <= months).length,
    [rows],
  );
  const within = plan === null ? null : withinOf(plan);
  const largest = Math.max(...rows.map((row) => row.months), ...(quantile ?? []).map((dot) => dot.months), own ?? 0, axisValue ?? 0, 0.5);
  const axis = axisFor(largest);
  const say = (months: number) => setAnnounce(words.chart.announce(whole(withinOf(months)), whole(total), months1(months)));

  const onPlan = useCallback(
    (value: number, how: PlanMove) => {
      setPlan(value);
      setText(months1(value));
      setInvalid(false);
      if (how === "drag-end" || how === "axis") setAnnounce(words.chart.announce(whole(withinOf(value)), whole(total), months1(value)));
    },
    [withinOf, total],
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
    clearTimeout(axisTimer.current);
    axisTimer.current = setTimeout(() => setAxisValue(value), 300);
    clearTimeout(sayTimer.current);
    sayTimer.current = setTimeout(() => say(value), 500);
  };

  const reset = () => {
    if (own === null) return;
    setPlan(own);
    setText(months1(own));
    setInvalid(false);
    setAxisValue(own);
    say(own);
    inputRef.current?.focus();
  };

  const showRows = () => {
    setTableOpen(true);
    requestAnimationFrame(() => captionRef.current?.focus());
  };
  const explainCounts: NumCheck | undefined = own === null ? undefined : {
    tooltip: words.explain.counts(months1(own), whole(total), whole(open)),
    onOpen: showRows,
  };
  const explainQuantiles: NumCheck = { tooltip: words.explain.quantiles(whole(total), whole(open)), onOpen: showRows };
  const explainPlan: NumCheck = {
    tooltip: words.explain.plan(pkg.plan.implementing_agency, formatDate(pkg.plan.plan_date)),
  };
  const explainCoverage: NumCheck = { tooltip: words.explain.coverage };

  const type = chartType(width || 800);
  const range = abstained ? null : result.past_range;

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
    const { within: w, in10 } = result.plan;
    const t = words.title;
    const template = w === 0 ? t.none : w === total ? t.all : in10 === 0 ? t.fewerThanOne : in10 === 10 ? t.moreThanNine : t.about;
    title = (
      <Fill
        template={template}
        slots={{
          within: count(w, explainCounts),
          total: count(total, explainCounts),
          in10: in10 === null ? null : count(in10, explainCounts),
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
    const first =
      range?.q75 == null || range.q25 == null || range.q50 == null ? (
        s.noUpper
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
        name: (dot.reached ? c.dotQuantile : c.dotQuantileOpen)(whole(dot.k), whole(total), months1(dot.months)),
        tip: {
          header: c.tipQuantile(whole(dot.k)),
          mono: false,
          number: dot.reached ? c.tipMonths(months1(dot.months)) : c.tipPast(months1(dot.months)),
          line: dot.reached ? c.tipQuantileLine(whole(total)) : c.tipQuantileOpen,
        },
      }))
    : rows.map((row, index) => markFor(row, index, total));

  const altParts = [
    quantile ? c.altDots(whole(total), whole(axis.max)) : c.alt(whole(total), whole(axis.max), whole(counts.signed), whole(open)),
  ];
  if (abstained) altParts.push(c.altAbstain);
  else if (range?.q25 != null && range.q75 != null && range.q50 != null) {
    altParts.push(
      range.q80 != null
        ? c.altRange(months1(range.q25), months1(range.q75), months1(range.q50), months1(range.q80))
        : `${c.altMiddle(months1(range.q25), months1(range.q75), months1(range.q50))} ${c.altNoIn10}`,
    );
  } else altParts.push(c.altNoUpper);
  if (plan !== null && within !== null) altParts.push(c.altPlan(months1(plan), whole(within), whole(total)));
  if (counts.canceled > 0) {
    altParts.push((counts.canceled_as_still_open ? c.altCanceledCounted : c.altCanceledLeftOut)(counts.canceled, whole(counts.canceled)));
  }

  const readout = plan === null || within === null ? null : c.readout(whole(within), whole(total), months1(plan));
  const valueText =
    plan === null || within === null
      ? null
      : (plan === own ? c.valueTextPlan : c.valueText)(months1(plan), whole(within), whole(total));

  const control = (
    <PlanControl
      ids={ids}
      inputRef={inputRef}
      text={text}
      invalid={invalid}
      maxMonths={maxMonths}
      own={own}
      plan={plan}
      notice={result.plan?.planned_notice_on ?? null}
      signing={result.plan?.planned_signing_on ?? null}
      onType={onType}
      onReset={reset}
    />
  );

  const summaryBlock = (
    <p className="text-body text-ink" data-summary>
      {summary}
    </p>
  );

  return (
    <div ref={measure} className="mt-4">
      <h3 id={ids.title} className="font-bold text-pretty text-ink-heading" style={{ fontSize: type.l, lineHeight: 1.3 }} data-finding>
        {title}
      </h3>
      {narrow && <div className="mt-2">{summaryBlock}</div>}
      <p className="mt-2 text-ink-muted" style={{ fontSize: type.m }}>
        {quantile ? <Fill template={words.subtitleDots} slots={{ total: whole(total) }} /> : words.subtitle}
      </p>
      <div className="mt-4">{control}</div>
      <figure aria-labelledby={ids.title} className="mt-4" data-chart-figure>
        {width > 0 && (
          <RangeChart
            width={width}
            marks={marks}
            big={Boolean(quantile)}
            stats={range}
            axisMax={axis.max}
            step={axis.step}
            plan={plan}
            ownPlan={own}
            readout={readout}
            keySigned={quantile ? c.keyDots(whole(total)) : c.keySigned(whole(counts.signed))}
            keyHollow={open > 0 ? c.keyOpen(whole(open)) : null}
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
            groupHelp={c.groupHelp}
            sliderName={c.slider}
            valueText={valueText}
            onPlan={onPlan}
          />
        )}
        {width === 0 && <div style={{ height: CHART_HEIGHT }} />}
      </figure>
      {!narrow && <div className="mt-4">{summaryBlock}</div>}
      <div className="mt-4 flex flex-col gap-2" style={{ fontSize: type.s }}>
        <Note result={result} />
        <Coverage result={result} check={explainCoverage} />
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
        {tableOpen && (
          <ComparablesTable
            result={result}
            plan={plan}
            page={page}
            onPage={setPage}
            captionRef={captionRef}
          />
        )}
      </div>
      <p role="status" className="sr-only" data-live>
        {announce}
      </p>
    </div>
  );
}

function markFor(row: Comparable, index: number, total: number): RangeMark {
  const c = words.chart;
  const m = months1(row.months);
  const country = row.country_name ?? copy.notInRecord;
  return {
    key: row.step_reference,
    months: row.months,
    hollow: row.still_open,
    name: row.still_open
      ? c.dotOpen(row.step_reference, country, m, whole(index + 1), whole(total))
      : c.dotSigned(row.step_reference, country, m, formatDate(row.signed_on!), whole(index + 1), whole(total)),
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
  own,
  plan,
  notice,
  signing,
  onType,
  onReset,
}: {
  ids: { input: string; helper: string; error: string };
  inputRef: Ref<HTMLInputElement>;
  text: string;
  invalid: boolean;
  maxMonths: number;
  own: number | null;
  plan: number | null;
  notice: string | null;
  signing: string | null;
  onType: (raw: string) => void;
  onReset: () => void;
}) {
  const w = words.control;
  const moved = own !== null && plan !== null && plan !== own;
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
              "h-11 w-[88px] rounded-md border bg-surface px-3 text-right text-body text-ink tabular-nums",
              invalid ? "border-error-icon" : "border-line-strong",
            )}
          />
          <span className="text-small text-ink">{w.unit}</span>
        </span>
        {moved && (
          <Button variant="ghost" onClick={onReset}>
            {w.reset(months1(own))}
          </Button>
        )}
      </div>
      {invalid && (
        <p id={ids.error} className="mt-1 text-caption text-error">
          {w.invalid(whole(maxMonths))}
        </p>
      )}
      <p id={ids.helper} className="mt-1 text-caption text-ink-muted">
        {notice && signing ? (
          // Plain plan values, so they carry no popover (ticket 10's rule); the months worked out from them do.
          <Fill template={w.helper} slots={{ notice: <Num date={notice} />, signing: <Num date={signing} /> }} />
        ) : (
          w.helperNoPlan
        )}
      </p>
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
}: {
  result: ComparablesResult;
  plan: number | null;
  page: number;
  onPage: (page: number) => void;
  captionRef: Ref<HTMLSpanElement>;
}) {
  const t = words.table;
  const rows = result.rows;
  const total = rows.length;
  const paged = total > result.thresholds.quantile_dots_above;
  const from = paged ? page * PAGE : 0;
  const shown = paged ? rows.slice(from, from + PAGE) : rows;
  const columns: Column[] = [
    { key: "package", header: t.columns.package, width: "w-[30%]" },
    { key: "country", header: t.columns.country, short: true },
    { key: "notice", header: t.columns.notice, short: true },
    { key: "signed", header: t.columns.signed, short: true },
    {
      key: "months",
      header: (
        <>
          {t.columns.months}
          <span className="block text-caption font-normal text-ink-muted">{t.columns.monthsNote}</span>
        </>
      ),
      numeric: true,
    },
    ...(plan === null ? [] : [{ key: "within", header: t.columns.within(months1(plan)), short: true }]),
  ];
  const tableRows: Row[] = shown.map((row) => ({
    id: row.step_reference,
    cells: {
      package: <span className="font-mono wrap-anywhere">{row.step_reference}</span>,
      country: row.country_name ?? copy.notInRecord,
      notice: tableDate(row.notice_date),
      signed: row.signed_on ? tableDate(row.signed_on) : t.stillOpen,
      months: months1(row.months),
      within: plan === null ? null : row.still_open ? (row.months <= plan ? t.notYet : t.no) : row.months <= plan ? t.yes : t.no,
    },
  }));
  return (
    <>
      <Table
        title={
          <span ref={captionRef} tabIndex={-1} className="focus:outline-none" data-table-caption>
            {total === 1 ? t.captionOne : t.caption(whole(total))}
          </span>
        }
        level={4}
        count={{ noun: t.noun, one: t.nounOne, total, from: from + 1, to: from + shown.length }}
        columns={columns}
        rowHeader="package"
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

function PastRangeSkeleton() {
  return (
    <div aria-hidden="true" className="mt-4" data-past-range-skeleton>
      <SkeletonText className="text-title" widths={["w-full", "w-3/5"]} />
      <SkeletonLine className="mt-2 text-body" width="w-4/5" />
      <div className="mt-4 flex items-center gap-3">
        <SkeletonLine className="text-small" width="w-28" />
        <Skeleton className="h-11 w-[88px] rounded-md" />
      </div>
      <div className="mt-4" style={{ height: CHART_HEIGHT }}>
        <Skeleton className="h-full w-full rounded-md" />
      </div>
      <SkeletonText className="mt-4 text-body" widths={["w-full", "w-full", "w-2/5"]} />
      <SkeletonText className="mt-4 text-caption" widths={["w-full", "w-4/5", "w-3/5"]} />
    </div>
  );
}
