// Part 3 of section 5, the cost estimate (ticket 31; DESIGN.md sections 5 and 6, Cost lane; the 31 brief, section
// 4.5): one lane on a percent axis, one dot per comparable package placed by how far its signed amount was from
// its own cost estimate, with a fixed zero line, "At the cost estimate", and the count on each side. It reuses the
// past range's lane mechanics (brief 12): the exact-position beeswarm (RangeChart.swarm), dots in chart-cat1-text
// with a surface ring, one tab stop with arrow keys between the dots, a tooltip on hover and focus that Escape
// hides, and a "Show the table" twin. The middle half's band and tick and their labels show only from
// min_comparables packages; below it the section abstains in the first person, the dots, the zero line and its
// counts stay, and the table twin opens by default with every package (brief 12's pattern). The chart never
// animates. Every number is the tool's: the counts, the band of cost estimates, the quartiles and each package's
// difference, which Num writes with a true minus sign.
import { useEffect, useId, useLayoutEffect, useRef, useState, type KeyboardEvent } from "react";
import { copy } from "../copy";
import { costRecordId, type Cost, type CostRow } from "../lib/criteria";
import { formatAmountText, formatCount, formatNumber, formatSignedPercent } from "../lib/format";
import { Button } from "./Button";
import { Fill } from "./Fill";
import { FootStrip } from "./FootStrip";
import { MonoWords } from "./MonoWords";
import { Num } from "./Num";
import { fromLine, toolFrom } from "./NumFrom";
import { chartType, swarm, titleSize } from "./RangeChart";
import { Source } from "./Source";
import { Table } from "./Table";
import { TextLink } from "./TextLink";
import { openFrom, partSource, useOpenId } from "./CriteriaParts";

const words = copy.cost;
// Row B holds the line's label and the counts beside it: 32 px, or 48 when the counts stack because one side
// has no room beside the line (the brief's 48 px under 400 px).
const ROW_B = 32;
const ROW_B_STACKED = 48;
const ROW_C = 24;
const AXIS = 32;
const PAD = 8;
// The plot keeps this far from each side, so the first and last axis labels, such as "−100%" and "+400%", stay
// whole inside the chart.
const EDGE = 24;
const HALO = { stroke: "var(--color-surface)", strokeWidth: 3, paintOrder: "stroke", strokeLinejoin: "round" } as const;

// About five ticks (the 31 brief, section 4.5): every 25 points, every 10 when the span is 60 points or less, and
// every 50 when it is over 200; a step doubles while it would draw more than seven. The range covers every dot
// and zero.
export function percentAxis(values: number[]): { min: number; max: number; step: number } {
  const low = Math.min(0, ...values);
  const high = Math.max(0, ...values);
  const span = high - low;
  let step = span <= 60 ? 10 : span > 200 ? 50 : 25;
  const bounds = () => ({ min: Math.floor(low / step) * step, max: Math.max(step, Math.ceil(high / step) * step) });
  while ((bounds().max - bounds().min) / step + 1 > 7) step *= 2;
  const { min, max } = bounds();
  return { min: min === max ? min - step : min, max, step };
}

function usd(value: string): string {
  return words.amount(formatAmountText(Number(value)));
}

function dotName(row: CostRow): string {
  return words.dotName(row.step_reference, formatSignedPercent(row.diff_pct, { style: "words" }));
}

export function CostTitle({ cost, onCount }: { cost: Cost; onCount?: () => void }) {
  const { above, m } = cost.counts;
  // Counted from every record set the tool read: the plan rows' cost estimates, the notices and the signed contracts.
  const from = fromLine(toolFrom(cost));
  const num = (value: number) => (
    <Num value={value} check={onCount ? { tooltip: words.countTooltip, from, act: words.countAct, opens: "rows", onOpen: onCount } : undefined} />
  );
  if (above === 0) return <Fill template={words.titleNone} slots={{ m: num(m) }} />;
  if (above === m) return <Fill template={words.titleAll} slots={{ m: num(m) }} />;
  if (above === 1) return <Fill template={words.titleOne} slots={{ m: num(m) }} />;
  return <Fill template={words.title} slots={{ above: num(above), m: num(m) }} />;
}

function titleText(cost: Cost): string {
  const { above, m } = cost.counts;
  const n = (value: number) => formatNumber(value, { compact: false });
  if (above === 0) return words.titleNone.replace("{m}", n(m));
  if (above === m) return words.titleAll.replace("{m}", n(m));
  if (above === 1) return words.titleOne.replace("{m}", n(m));
  return words.title.replace("{above}", n(above)).replace("{m}", n(m));
}

function altText(cost: Cost): string {
  const n = (value: number) => formatNumber(value, { compact: false });
  const { m, below, at, above } = cost.counts;
  // Quantile dots each stand for an equal share of the packages, and the text alternative says so (ticket 59).
  const template = cost.quantile_dots ? words.altQuantile.replaceAll("{dots}", n(cost.quantile_dots.length)) : words.alt;
  const base = template.replace("{m}", n(m)).replace("{below}", n(below)).replace("{at}", n(at)).replace("{above}", n(above));
  if (!cost.quartiles) return base;
  const say = (value: number) => formatSignedPercent(value, { style: "words" });
  return `${base} ${words.altMiddle.replace("{q25}", say(cost.quartiles.q25)).replace("{q75}", say(cost.quartiles.q75)).replace("{q50}", say(cost.quartiles.q50))}`;
}

type QuantileDot = NonNullable<Cost["quantile_dots"]>[number];
// A dot on the lane: one comparable package, or a quantile dot that stands for an equal share of them.
type Mark = { key: string; diff: number; row: CostRow | null; dot: QuantileDot | null };

function quantileName(dot: QuantileDot, dots: number, total: number): string {
  const n = (value: number) => formatNumber(value, { compact: false });
  return words.dotQuantile(n(dot.k), n(dots), n(dot.count), n(total), formatSignedPercent(dot.diff_pct, { style: "words" }));
}

// The lane itself: an svg drawing named by the alt text, and over it one group of dots with one tab stop.
function Lane({ cost, onOpen, onTable, title, width }: {
  cost: Cost; onOpen: (row: CostRow, element: HTMLElement) => void; onTable: () => void; title: string; width: number;
}) {
  const [active, setActive] = useState(0);
  const [shown, setShown] = useState<number | null>(null);
  const [hidden, setHidden] = useState(false);
  const altId = useId();
  const dots = useRef<(HTMLSpanElement | null)[]>([]);
  // The dot the pointer last showed the tooltip of.
  const hovered = useRef<number | null>(null);
  const open = useOpenId();
  const rows = cost.rows;
  // Above past_range.quantile_dots_above comparable packages the tool returns quantile dots, each standing for an equal
  // share of the packages at its share's middle difference, as the past range draws them (brief 12): the lane draws
  // those, and a dot's press opens the table twin, which keeps every package (ticket 59; the 31 review, round 3, F5).
  const quantile = cost.quantile_dots;
  const marks: Mark[] = quantile
    ? quantile.map((dot) => ({ key: `dot-${dot.k}`, diff: dot.diff_pct, row: null, dot }))
    : rows.map((row) => ({ key: row.step_reference, diff: row.diff_pct, row, dot: null }));
  const openMark = (mark: Mark, element: HTMLElement) => (mark.row ? onOpen(mark.row, element) : onTable());
  const type = chartType(width || 600);
  const narrow = width > 0 && width < 400;
  // Quantile dots are drawn larger, as on the past range (DESIGN.md section 6), and r 4 below 400 px, where 20 of them
  // share a short lane. They are spaced so each dot's surface ring keeps 1 px clear of the next, so every one of them
  // can be counted (ticket 59; the critique of round 1).
  const r = quantile ? (narrow ? 4 : 6) : narrow ? 4 : 4.5;
  const spacing = quantile ? r + 1.5 : r;
  const lane = 96;
  const ranged = Boolean(cost.quartiles);
  const axis = percentAxis(rows.map((row) => row.diff_pct));
  const x = (value: number) => EDGE + ((value - axis.min) / (axis.max - axis.min)) * Math.max(0, width - 2 * EDGE);
  const offsets = swarm(marks.map((mark) => x(mark.diff)), spacing, lane) ?? marks.map(() => 0);
  const zero = x(0);
  const textWidth = (text: string) => text.length * type.s * 0.56;
  const ticks: number[] = [];
  for (let tick = axis.min; tick <= axis.max + 1e-9; tick += axis.step) ticks.push(tick);
  // When two labels would touch, such as six on a 182 px plot at 320 px, every second tick keeps its label;
  // every tick keeps its gridline. Zero is always labelled.
  const widest = Math.max(...ticks.map((tick) => textWidth(formatSignedPercent(tick))));
  const thin = ticks.length > 1 && (width - 2 * EDGE) / (ticks.length - 1) < widest + 12;
  const zeroAt = ticks.findIndex((tick) => Math.abs(tick) < 1e-9);
  const labelled = (index: number) => !thin || (index - (zeroAt >= 0 ? zeroAt : 0)) % 2 === 0;
  const clampText = (centreX: number, text: string, size: number) => {
    const half = (text.length * size * 0.56) / 2;
    return Math.min(Math.max(centreX, PAD + half), Math.max(PAD + half, width - PAD - half));
  };
  const { below, above } = cost.counts;
  const belowText = words.below.replace("{below}", formatNumber(below, { compact: false }));
  const aboveText = words.above.replace("{above}", formatNumber(above, { compact: false }));
  // Each count sits beside the line, below to its left and above to its right; when a side has no room there,
  // the two stack under the line's label, each kept whole inside the plot.
  const stacked = (below > 0 && zero - 8 - textWidth(belowText) < PAD) || (above > 0 && zero + 8 + textWidth(aboveText) > width - PAD);
  const rowB = stacked ? ROW_B_STACKED : ROW_B;
  const height = rowB + lane + (ranged ? ROW_C : 0) + AXIS;
  const laneTop = rowB;
  const centre = laneTop + lane / 2;
  // Stacked, the line's label and the two counts are three rows from one left edge, the label's own, kept inside the
  // plot, so the counts never step down and across each other (ticket 59; the 31 critique, round 3, follow-up 5; the
  // design review of round 1, follow-up 5).
  const stackWidth = Math.max(textWidth(words.line), below > 0 ? textWidth(belowText) : 0, above > 0 ? textWidth(aboveText) : 0);
  const stackX = Math.min(Math.max(zero - textWidth(words.line) / 2, PAD), Math.max(PAD, width - PAD - stackWidth));
  const tip = shown !== null && !hidden ? marks[shown] : null;
  // The dot whose centre is nearest the pointer, among all of them, measured in the lane's own box.
  const nearestTo = (event: { clientX: number; clientY: number; currentTarget: HTMLElement }, from: number) => {
    const box = (event.currentTarget.parentElement ?? event.currentTarget).getBoundingClientRect();
    const at = { x: event.clientX - box.left, y: event.clientY - box.top };
    const distance = (index: number) => (x(marks[index].diff) - at.x) ** 2 + (centre + offsets[index] - at.y) ** 2;
    return marks.reduce((best, _, index) => (distance(index) < distance(best) ? index : best), from);
  };
  const middleLabel = cost.quartiles
    ? words.middleLabel
        .replace("{q25}", formatSignedPercent(cost.quartiles.q25))
        .replace("{q75}", formatSignedPercent(cost.quartiles.q75))
        .replace("{q50}", formatSignedPercent(cost.quartiles.q50))
    : "";
  const keys = (event: KeyboardEvent) => {
    const last = marks.length - 1;
    const next =
      event.key === "ArrowRight" || event.key === "ArrowDown" ? Math.min(last, active + 1)
        : event.key === "ArrowLeft" || event.key === "ArrowUp" ? Math.max(0, active - 1)
          : event.key === "Home" ? 0 : event.key === "End" ? last : null;
    if (next !== null) {
      event.preventDefault();
      setActive(next);
      setHidden(false);
      dots.current[next]?.focus();
      return;
    }
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      const element = dots.current[active];
      if (element) openMark(marks[active], element);
      return;
    }
    if (event.key === "Escape" && shown !== null && !hidden) {
      // The tooltip closes first, and the drawer only on the next press (the 31 brief, section 7.2).
      event.preventDefault();
      event.stopPropagation();
      setHidden(true);
    }
  };
  useEffect(() => {
    if (active > marks.length - 1) setActive(0);
  }, [marks.length, active]);
  return (
    <div className="relative mt-2" onKeyDown={keys} data-cost-lane>
      <p id={altId} className="sr-only">{altText(cost)}</p>
      {width > 0 && (
        <svg role="img" aria-labelledby={altId} width={width} height={height} className="block overflow-visible" data-cost-drawing>
          {/* The middle half and the middle, only from min_comparables packages. */}
          {ranged && cost.quartiles && (
            <>
              <rect x={x(cost.quartiles.q25)} y={laneTop + 8} width={Math.max(1, x(cost.quartiles.q75) - x(cost.quartiles.q25))} height={lane - 16}
                strokeWidth={1} className="fill-chart-grey200 stroke-line-strong" />
              <line x1={x(cost.quartiles.q50)} x2={x(cost.quartiles.q50)} y1={laneTop + 8} y2={laneTop + lane - 8}
                strokeWidth={2.5} className="stroke-chart-grey500" />
              <text x={clampText(x(cost.quartiles.q50), middleLabel, type.s)} y={laneTop + lane + 16} textAnchor="middle"
                fontSize={type.s} className="fill-chart-text" style={HALO}>
                {middleLabel}
              </text>
            </>
          )}
          {/* The axis: its ticks and labels with a true minus sign. */}
          <line x1={EDGE} x2={width - EDGE} y1={height - AXIS} y2={height - AXIS} strokeWidth={1} className="stroke-line-strong" />
          {ticks.map((tick, index) => (
            <g key={tick}>
              <line x1={x(tick)} x2={x(tick)} y1={laneTop} y2={height - AXIS} strokeDasharray="2 3" strokeWidth={1} className="stroke-chart-grey200" />
              {labelled(index) && (
                <text x={x(tick)} y={height - AXIS + 18} textAnchor="middle" fontSize={type.s} className="fill-chart-text" data-axis-label>
                  {formatSignedPercent(tick)}
                </text>
              )}
            </g>
          ))}
          {/* The zero line, with a 1 px surface halo on each side. It starts under row B when the counts stack
              there, and stops at the lane when row C holds the middle half's label, so no label is crossed;
              the axis's 0% tick still marks zero below. */}
          <line x1={zero} x2={zero} y1={stacked ? rowB : 14} y2={ranged ? laneTop + lane : height - AXIS} strokeWidth={4} className="stroke-surface" />
          <line x1={zero} x2={zero} y1={stacked ? rowB : 14} y2={ranged ? laneTop + lane : height - AXIS} strokeWidth={2}
            className="stroke-chart-grey500" data-zero-line />
          {/* Row B: the line's label, then the counts on each side; a side with no package is left out. */}
          <text x={stacked ? stackX : clampText(zero, words.line, type.s)} y={11} textAnchor={stacked ? "start" : "middle"} fontSize={type.s} fontWeight={600}
            className="fill-chart-text" style={HALO} data-line-label>
            {words.line}
          </text>
          {!stacked && below > 0 && (
            <text x={zero - 8} y={27} textAnchor="end" fontSize={type.s} className="fill-chart-text" style={HALO} data-row-b="below">
              {belowText}
            </text>
          )}
          {!stacked && above > 0 && (
            <text x={zero + 8} y={27} textAnchor="start" fontSize={type.s} className="fill-chart-text" style={HALO} data-row-b="above">
              {aboveText}
            </text>
          )}
          {stacked && below > 0 && (
            <text x={stackX} y={27} textAnchor="start" fontSize={type.s} className="fill-chart-text" style={HALO} data-row-b="below">
              {belowText}
            </text>
          )}
          {stacked && above > 0 && (
            <text x={stackX} y={below > 0 ? 43 : 27} textAnchor="start" fontSize={type.s} className="fill-chart-text" style={HALO} data-row-b="above">
              {aboveText}
            </text>
          )}
          {/* One dot per comparable package with both amounts, or one per quantile above the threshold. */}
          {marks.map((mark, index) => {
            const opened = mark.row !== null && open === costRecordId(mark.row.step_reference);
            return (
              <g key={mark.key}>
                <circle cx={x(mark.diff)} cy={centre + offsets[index]} r={r} strokeWidth={2}
                  className="fill-chart-cat1-text stroke-surface" />
                {(opened || (shown === index && !hidden)) && (
                  <circle cx={x(mark.diff)} cy={centre + offsets[index]} r={r + 2} strokeWidth={2}
                    className={opened ? "fill-none stroke-info-icon" : "fill-none stroke-chart-grey500"} />
                )}
              </g>
            );
          })}
        </svg>
      )}
      {/* The dots as one group with one tab stop: arrow keys move between them, and each one's name says what
          its tooltip shows. Enter opens its cost records. */}
      <div role="group" aria-label={title} className="pointer-events-none absolute inset-0">
        {width > 0 &&
          marks.map((mark, index) => (
            <span
              key={mark.key}
              ref={(element) => {
                dots.current[index] = element;
              }}
              role="img"
              aria-label={mark.row ? dotName(mark.row) : quantileName(mark.dot!, marks.length, cost.counts.m)}
              tabIndex={index === active ? 0 : -1}
              data-cost-dot={mark.key}
              onFocus={() => {
                setActive(index);
                setShown(index);
                setHidden(false);
              }}
              onBlur={() => setShown(null)}
              // Each dot's target is 8 px wider than the dot, so in a cluster the pointer is over whichever is on top: the
              // dot nearest the pointer shows its tooltip, and a press opens it (the 31 design review, F6; ticket 59, the
              // design review of round 2, follow-up 2, where at 320 px a hover on dot 10 showed dot 11's value).
              onPointerEnter={(event) => {
                hovered.current = nearestTo(event, index);
                setShown(hovered.current);
                setHidden(false);
              }}
              onPointerMove={(event) => {
                const near = nearestTo(event, index);
                if (near === hovered.current) return;
                hovered.current = near;
                setShown(near);
              }}
              onPointerLeave={() => setShown((current) => (current === hovered.current ? null : current))}
              onClick={(event) => {
                // A click from the keyboard has no place on the screen, so it opens the dot that has focus.
                if (event.detail === 0) return openMark(mark, event.currentTarget);
                const nearest = nearestTo(event, index);
                openMark(marks[nearest], dots.current[nearest] ?? event.currentTarget);
              }}
              className="pointer-events-auto absolute cursor-pointer rounded-full after:absolute after:-inset-2 after:content-['']"
              style={{ left: x(mark.diff) - r, top: centre + offsets[index] - r, width: 2 * r, height: 2 * r }}
            />
          ))}
      </div>
      {tip && (
        <div
          aria-hidden="true"
          data-cost-tooltip
          className="absolute z-10 w-max max-w-[240px] rounded-sm border-[0.5px] border-chart-grey200 bg-surface px-3 py-2 shadow-popover"
          style={{
            left: Math.min(Math.max(0, x(tip.diff) - 120), Math.max(0, width - 240)),
            // Below 400 px of chart width it opens under the dot, so it never covers the subtitle or the line's
            // label above the lane.
            ...(narrow
              ? { top: centre + offsets[shown!] + r + 8 }
              : { top: Math.max(0, centre + offsets[shown!] - r - 8), transform: "translateY(-100%)" }),
            fontSize: type.s,
          }}
        >
          {tip.row ? (
            <>
              <p className="font-semibold text-chart-text">
                <MonoWords text={tip.row.step_reference} />
              </p>
              <p className="font-bold text-chart-text tabular-nums" style={{ fontSize: type.m }}>
                {formatSignedPercent(tip.row.diff_pct)}
              </p>
              <p className="text-chart-text-subtle">
                {(tip.row.country_name ? words.tooltipLine : words.tooltipLineNoCountry)
                  .replace("{signed}", usd(tip.row.signed_amount_usd))
                  .replace("{estimate}", usd(tip.row.estimated_amount_usd))
                  .replace("{country}", tip.row.country_name ?? "")}
              </p>
              <p className="mt-1 text-chart-text-subtle">{words.tooltipOpen}</p>
            </>
          ) : (
            <>
              <p className="font-semibold text-chart-text">{words.tipQuantile(formatNumber(tip.dot!.count, { compact: false }))}</p>
              <p className="font-bold text-chart-text tabular-nums" style={{ fontSize: type.m }}>
                {formatSignedPercent(tip.dot!.diff_pct)}
              </p>
              <p className="text-chart-text-subtle">{words.tipQuantileLine}</p>
              <p className="mt-1 text-chart-text-subtle">{words.tooltipOpenDots}</p>
            </>
          )}
        </div>
      )}
    </div>
  );
}

function CostTable({ cost, open: openId, onOpen, titleId }: {
  cost: Cost; open: string | null; onOpen: (row: CostRow, element: HTMLElement) => void; titleId: string;
}) {
  // A STEP reference such as KE-KIMAWASCO-141042-CW-RFB stays on one line at 1440 px (the 31 design review, F13).
  const columns = [
    { key: "package", header: words.columns.package, width: "w-[36%]" },
    // Country takes a card's full row, so it never starts a line below a two-line head beside it (ticket 59).
    { key: "country", header: words.columns.country, width: "w-[10%]" },
    {
      key: "estimated",
      header: (
        <>
          <span className="block">{words.columns.estimated}</span>
          <span className="block text-caption font-normal text-ink-muted">{words.columns.estimatedDefinition}</span>
        </>
      ),
      cardHeader: words.columns.estimated,
      numeric: true,
    },
    {
      key: "signed",
      header: (
        <>
          <span className="block">{words.columns.signed}</span>
          <span className="block text-caption font-normal text-ink-muted">{words.columns.signedDefinition}</span>
        </>
      ),
      cardHeader: words.columns.signed,
      numeric: true,
    },
    {
      key: "diff",
      header: (
        <>
          <span className="block">{words.columns.diff}</span>
          <span className="block text-caption font-normal text-ink-muted">{words.columns.diffDefinition}</span>
        </>
      ),
      cardHeader: words.columns.diff,
      numeric: true,
    },
  ];
  const rows = cost.rows.map((row) => ({
    id: row.step_reference,
    cells: {
      package: (
        <button
          type="button"
          aria-label={words.openRecords(row.step_reference)}
          onClick={(event) => onOpen(row, event.currentTarget)}
          className="relative -my-1 py-1 text-left font-mono text-small text-primary underline hover:text-link-hover"
          data-cost-row={row.step_reference}
        >
          <MonoWords text={row.step_reference} className="underline" />
        </button>
      ),
      country: row.country_name ?? "",
      estimated: <Num value={Number(row.estimated_amount_usd)} options={{ decimals: 2, compact: false }} />,
      signed: <Num value={Number(row.signed_amount_usd)} options={{ decimals: 2, compact: false }} />,
      diff: <Num signedPercent={row.diff_pct} />,
    },
  }));
  const selected = openId?.startsWith("package-cost:") ? openId.slice("package-cost:".length) : null;
  return (
    // The chart's title just above names the table twin, so the twin repeats no title of its own (the 31
    // critique, round 1): its count line takes focus when a count in the title opens it.
    <Table
      title={<CostTitle cost={cost} />}
      labelledBy={titleId}
      countLead
      count={{ noun: "", total: cost.counts.m, text: cost.counts.m === 1 ? words.tableCountOne : words.tableCount.replace("{m}", formatCount(cost.counts.m)) }}
      columns={columns}
      state={{ status: "ready", rows }}
      rowHeader="package"
      level={4}
      selected={selected}
      // Cards below a 49rem frame, as the past range's table (ticket 101's critique, round 2), so a STEP reference
      // never breaks at a hyphen in the work column.
      cardsBelow="fit"
    />
  );
}

function Coverage({ cost, readinessHref }: { cost: Cost; readinessHref: string }) {
  const { m, total, open, no_estimate: none, no_usd: usdOnly } = cost.counts;
  const gaps = [
    open > 0 && <Fill key="open" template={words.coverageOpen} slots={{ open: <Num count={open} /> }} />,
    none > 0 && <Fill key="none" template={words.coverageNoEstimate} slots={{ none: <Num count={none} /> }} />,
    usdOnly > 0 && <Fill key="usd" template={words.coverageNoUsd} slots={{ usd: <Num count={usdOnly} /> }} />,
  ].filter(Boolean);
  const joined = gaps.map((gap, index) => (
    <span key={index}>
      {index > 0 && (index === gaps.length - 1 ? words.coverageAnd : words.coverageComma)}
      {gap}
    </span>
  ));
  return (
    <p className="max-w-prose text-caption text-pretty text-ink-muted" data-coverage-line>
      {gaps.length === 0 ? (
        <Fill template={words.coverageAll} slots={{ total: <Num value={total} /> }} />
      ) : m === 0 ? (
        <Fill template={words.coverageNone} slots={{ total: <Num value={total} />, gaps: <>{joined}</> }} />
      ) : (
        <Fill template={words.coverage} slots={{ m: <Num value={m} />, total: <Num value={total} />, gaps: <>{joined}</> }} />
      )}{" "}
      <TextLink href={readinessHref}>{words.coverageLink}</TextLink>
    </p>
  );
}

export function CostEstimate({ cost, readinessHref, asOf = null }: {
  cost: Cost; readinessHref: string;
  // The page's as-of date, when it has one: the source line then says the records were read as of it.
  asOf?: string | null;
}) {
  const abstain = cost.abstention?.reason === "too_few_comparables";
  const [table, setTable] = useState(abstain);
  const captionRef = useRef<HTMLDivElement>(null);
  const titleId = useId();
  const root = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(0);
  useLayoutEffect(() => {
    const element = root.current;
    if (!element) return;
    const measure = () => setWidth(element.clientWidth);
    measure();
    const watch = new ResizeObserver(measure);
    watch.observe(element);
    return () => watch.disconnect();
  }, []);
  // A count in the title opens the table twin and moves focus to its caption (the 31 brief, section 6.10).
  const showTable = () => {
    setTable(true);
    requestAnimationFrame(() => captionRef.current?.querySelector<HTMLElement>("[data-page-lead]")?.focus());
  };
  const open = useOpenId();
  const onOpen = (row: CostRow, element: HTMLElement) => openFrom(costRecordId(row.step_reference), element);
  const estimate = cost.package.estimated_amount_usd;
  const intro = cost.band && (
    <p className="max-w-prose text-body text-ink" data-cost-intro>
      <Fill
        template={
          cost.quantile_dots
            ? (estimate ? words.introQuantile : words.introNoEstimateQuantile).replace("{dots}", formatNumber(cost.quantile_dots.length, { compact: false }))
            : estimate
              ? words.intro
              : words.introNoEstimate
        }
        slots={{
          estimate: estimate ? usd(estimate) : "",
          low: usd(cost.band.low_usd),
          high: usd(cost.band.high_usd),
        }}
      />
    </p>
  );
  // The coverage and source lines end the part in its foot strip, after the table (ticket 101's critique, round 2).
  const foot = (
    <FootStrip part>
      <Coverage cost={cost} readinessHref={readinessHref} />
      {(cost.records_through || asOf) && (
        <Source>
          {partSource({ sources: cost.sources, through: cost.records_through, asOf: asOf ? cost.as_of : null, template: words.source,
            templateAsOf: words.sourceAsOf })}
        </Source>
      )}
    </FootStrip>
  );
  if (!cost.rows.length) {
    return (
      <div ref={root} className="flex flex-col gap-2" data-cost="none">
        <p className="max-w-prose text-body text-ink">{words.none}</p>
        {foot}
      </div>
    );
  }
  const type = chartType(width || 600);
  return (
    <div ref={root} className="flex flex-col gap-2" data-cost={abstain ? "abstain" : "ranged"}>
      {intro}
      <p id={titleId} className="mt-2 font-bold text-chart-text" style={{ fontSize: titleSize(type) }} data-cost-title>
        <CostTitle cost={cost} onCount={showTable} />
      </p>
      {abstain && (
        <p className="max-w-prose text-body text-pretty text-ink" data-cost-abstain>
          {cost.counts.m === 1 ? words.abstainOne : <Fill template={words.abstain} slots={{ m: <Num count={cost.counts.m} /> }} />}
        </p>
      )}
      <p className="text-chart-text-subtle" style={{ fontSize: type.m }}>{words.subtitle}</p>
      {/* With quantile dots, brief 12's key line says what a dot stands for. */}
      {cost.quantile_dots && (
        <p className="text-chart-text-subtle" style={{ fontSize: type.s }} data-cost-key>
          {words.keyDots(formatNumber(cost.counts.m, { compact: false }), formatNumber(cost.quantile_dots.length, { compact: false }))}
        </p>
      )}
      <Lane cost={cost} onOpen={onOpen} onTable={showTable} title={titleText(cost)} width={width} />
      {cost.quartiles && (
        <p className="max-w-prose text-body text-ink" data-cost-middle>
          <Fill
            template={words.middle}
            slots={{
              m: <Num value={cost.counts.m} />,
              q25: <Num signedPercent={cost.quartiles.q25} words />,
              q75: <Num signedPercent={cost.quartiles.q75} words />,
              q50: <Num signedPercent={cost.quartiles.q50} words />,
            }}
          />
        </p>
      )}
      {cost.counts.at > 0 && (
        <p className="text-caption text-ink-muted">
          {cost.counts.at === 1 ? words.atOne : <Fill template={words.at} slots={{ at: <Num count={cost.counts.at} capital /> }} />}
        </p>
      )}
      <div>
        <Button variant="ghost" flush aria-expanded={table} onClick={() => setTable((value) => !value)}>
          {table ? words.hideTable : words.showTable}
        </Button>
      </div>
      {table && (
        <div ref={captionRef} className="mt-2" data-cost-table>
          <CostTable cost={cost} open={open} onOpen={onOpen} titleId={titleId} />
        </div>
      )}
      {foot}
    </div>
  );
}
