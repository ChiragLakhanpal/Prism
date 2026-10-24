// The range chart, lane 1 (DESIGN.md sections 5 and 6, the 12 brief): the past range of comparable
// packages on a month axis, one dot per package, with the plan as a full-height line you can move.
//
// The drawn layer is one svg with role="img", named by a hidden paragraph that states the same
// numbers (the alt text). The controls sit over it as siblings, because children of role="img" are
// hidden from assistive technology: the plan line is a role="slider" you drag, move with the arrow
// keys or set by clicking the axis row, and the dots are one group with one tab stop and arrow keys
// between them. A dot shows its package on hover or focus, and Escape hides that.
//
// The chart is 240 px tall in every state, in five rows: the lane label and its key (A), the plan's
// readout (B), the lane with the middle half, the middle, the 8-in-10 line and the dots, the
// statistics' labels (C), and the axis. A swarm too tall for the lane makes the lane taller in 16 px
// steps before the first paint, and never after. Each dot's centre is exactly its months, and dots
// that would overlap move up or down from the lane's centre in a fixed order, so the same data always
// draws the same picture and no dot sits on the wrong side of the plan line the readout counts against.
//
// Every number arrives from the tool, written by the caller with web/src/lib/format.ts; the chart only
// places it. Text over marks has a surface halo. There is no animation.
import { useCallback, useEffect, useId, useLayoutEffect, useMemo, useRef, useState, type KeyboardEvent, type PointerEvent } from "react";
import { cx } from "../lib/cx";
import { formatNumber } from "../lib/format";

export type RangeMark = {
  key: string;
  months: number;
  // A package still open, or a quantile dot the curve never reached, is drawn hollow.
  hollow: boolean;
  // The dot's accessible name, from the copy file.
  name: string;
  tip: { header: string; mono: boolean; number: string; line: string };
};

export type RangeStats = { q25: number | null; q50: number | null; q75: number | null; q80: number | null };

export type PlanMove = "drag" | "drag-end" | "key" | "axis";

const ROW_A = 24;
const ROW_C = 40;
const AXIS = 32;
const PAD = 8;
const MAX_LANE = 160;
const HIT = 12; // a dot answers the pointer within 12 px of its centre
const NEAR_LINE = 8; // a fine pointer can grab the plan line within 8 px of it
const TIP_GAP = 8;

// DESIGN.md section 6: type sizes by chart width (s, m, l).
export function chartType(width: number): { s: number; m: number; l: number } {
  if (width < 400) return { s: 12, m: 14, l: 16 };
  if (width <= 700) return { s: 13, m: 15, l: 18 };
  return { s: 14, m: 16, l: 20 };
}

// About five ticks: every 3 months up to 12, every 6 up to 36, every 12 above that.
export function axisFor(largest: number): { max: number; step: number } {
  const step = largest <= 12 ? 3 : largest > 36 ? 12 : 6;
  return { max: Math.max(step, Math.ceil(largest / step) * step), step };
}

export const snap = (value: number, max: number) => Math.min(max, Math.max(0.5, Math.round(value * 2) / 2));

// The vertical offsets that keep dots apart, in the order given, or null when the swarm is taller than the lane.
function swarm(xs: number[], r: number, lane: number): number[] | null {
  const gap = 2 * r + 1;
  const limit = lane / 2 - r - 1;
  const placed: { x: number; y: number }[] = [];
  for (const x of xs) {
    const near = placed.filter((p) => Math.abs(p.x - x) < gap);
    const candidates = [0];
    for (const p of near) {
      const dy = Math.sqrt(gap * gap - (p.x - x) ** 2);
      candidates.push(p.y - dy, p.y + dy);
    }
    candidates.sort((a, b) => Math.abs(a) - Math.abs(b) || a - b);
    const y = candidates.find((c) => near.every((p) => (p.x - x) ** 2 + (p.y - c) ** 2 >= gap * gap - 0.01)) ?? 0;
    if (Math.abs(y) > limit) return null;
    placed.push({ x, y });
  }
  return placed.map((p) => p.y);
}

type Layout = { r: number; lane: number; offsets: number[] };

function fit(xs: number[], r: number, minR: number, lane: number): Layout {
  for (const radius of r === minR ? [r] : [r, minR]) {
    const offsets = swarm(xs, radius, lane);
    if (offsets) return { r: radius, lane, offsets };
  }
  for (let taller = lane + 16; taller <= MAX_LANE; taller += 16) {
    const offsets = swarm(xs, minR, taller);
    if (offsets) return { r: minR, lane: taller, offsets };
  }
  return { r: minR, lane: MAX_LANE, offsets: swarm(xs, minR, Number.MAX_SAFE_INTEGER) ?? xs.map(() => 0) };
}

// The widths of the svg text a label needs to stay inside the plot, read after each render.
function useTextWidths(keys: string[]) {
  const refs = useRef<Record<string, SVGTextElement | null>>({});
  const [widths, setWidths] = useState<Record<string, number>>({});
  const [fontsReady, setFontsReady] = useState(0);
  useEffect(() => {
    let live = true;
    document.fonts?.ready.then(() => live && setFontsReady((n) => n + 1));
    return () => {
      live = false;
    };
  }, []);
  useLayoutEffect(() => {
    const next: Record<string, number> = {};
    for (const key of keys) {
      const element = refs.current[key];
      next[key] = element ? element.getComputedTextLength() : 0;
    }
    setWidths((now) => (keys.every((key) => Math.abs((now[key] ?? -1) - next[key]) < 0.5) ? now : next));
  });
  void fontsReady;
  const ref = useCallback((key: string) => (element: SVGTextElement | null) => {
    refs.current[key] = element;
  }, []);
  return { widths, ref };
}

// A 3 px surface halo under text that sits over marks (DESIGN.md section 6).
const HALO = { stroke: "var(--color-surface)", strokeWidth: 3, paintOrder: "stroke", strokeLinejoin: "round" } as const;

const clamp = (value: number, low: number, high: number) => Math.min(Math.max(value, low), Math.max(low, high));

export function RangeChart({
  width,
  marks,
  big = false,
  stats,
  axisMax,
  step,
  plan,
  ownPlan,
  readout,
  keySigned,
  keyHollow,
  keyLead = false,
  laneLabel,
  planLabel,
  middleLabel,
  in10Label,
  axisLastLabel,
  alt,
  groupName,
  groupHelp,
  sliderName,
  valueText,
  onPlan,
}: {
  width: number;
  marks: RangeMark[];
  // Quantile dots are drawn larger.
  big?: boolean;
  // Null when the tool abstained: no band, no middle and no 8-in-10 line.
  stats: RangeStats | null;
  axisMax: number;
  step: number;
  // The plan line's months now, and the plan row's own months, or null when there is none.
  plan: number | null;
  ownPlan: number | null;
  // The readout's count line, "2 of 49 signed within 1.5 months".
  readout: string | null;
  // The key: the signed count beside a filled dot and the open count beside a hollow one. With
  // keyLead, the first half is a lead with no dot, such as "Each dot is 1 in 20 of the packages".
  keySigned: string | null;
  keyHollow: string | null;
  keyLead?: boolean;
  laneLabel: string;
  planLabel: string;
  middleLabel: string | null;
  in10Label: string | null;
  axisLastLabel: string;
  alt: string;
  groupName: string;
  groupHelp: string;
  sliderName: string;
  valueText: string | null;
  onPlan: (value: number, how: PlanMove) => void;
}) {
  const altId = useId();
  const helpId = useId();
  const narrow = width < 400;
  const type = chartType(width);
  const rowB = narrow ? 48 : 32;
  const baseLane = narrow ? 96 : 112;
  const plotRight = width - PAD;
  const x = useCallback((months: number) => PAD + (Math.min(months, axisMax) / axisMax) * (width - 2 * PAD), [axisMax, width]);
  const monthsAt = (px: number) => ((px - PAD) / Math.max(1, width - 2 * PAD)) * axisMax;

  const xs = useMemo(() => marks.map((mark) => x(mark.months)), [marks, x]);
  const r0 = big ? (narrow ? 5 : 6) : narrow ? 4 : 4.5;
  const layout = useMemo(() => fit(xs, r0, big ? r0 : 4, baseLane), [xs, r0, big, baseLane]);
  const laneTop = ROW_A + rowB;
  const laneBottom = laneTop + layout.lane;
  const axisY = laneBottom + ROW_C;
  const height = axisY + AXIS;
  const centre = laneTop + layout.lane / 2;
  const dots = marks.map((mark, index) => ({ ...mark, cx: xs[index], cy: centre + layout.offsets[index] }));

  const ticks = Array.from({ length: Math.floor(axisMax / step) + 1 }, (_, index) => index * step);
  const { widths, ref } = useTextWidths(["lane", "keySigned", "keyHollow", "plan", "readout", "middle", "in10"]);

  // ── Hover, focus and the tooltip ─────────────────────────────────────
  const [hover, setHover] = useState<number | null>(null);
  const [focused, setFocused] = useState<number | null>(null);
  const [active, setActive] = useState(0);
  const [dismissed, setDismissed] = useState<number | null>(null);
  const hideTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const dotRefs = useRef<(HTMLSpanElement | null)[]>([]);
  const tipRef = useRef<HTMLDivElement>(null);
  const shown = focused ?? hover;
  const tipFor = shown !== null && shown !== dismissed && dots[shown] ? dots[shown] : null;
  const [tipBox, setTipBox] = useState({ w: 0, h: 0 });
  useLayoutEffect(() => {
    const element = tipRef.current;
    if (!element) return;
    const next = { w: element.offsetWidth, h: element.offsetHeight };
    setTipBox((now) => (now.w === next.w && now.h === next.h ? now : next));
  });
  useEffect(() => () => clearTimeout(hideTimer.current), []);

  const nearest = (px: number, py: number): number | null => {
    let best: number | null = null;
    let distance = HIT;
    dots.forEach((dot, index) => {
      const d = Math.hypot(dot.cx - px, dot.cy - py);
      if (d <= distance) {
        distance = d;
        best = index;
      }
    });
    return best;
  };

  // ── The plan line ────────────────────────────────────────────────────
  const [drag, setDrag] = useState<{ pointer: number; from: number } | null>(null);
  const [knobHover, setKnobHover] = useState(false);
  const frame = useRef<number | undefined>(undefined);
  const wrapper = useRef<HTMLDivElement>(null);
  const planX = plan === null ? null : x(plan);
  const local = (event: PointerEvent) => {
    const box = wrapper.current!.getBoundingClientRect();
    return { px: event.clientX - box.left, py: event.clientY - box.top };
  };
  const moveTo = (px: number, how: PlanMove) => onPlan(snap(monthsAt(px), axisMax), how);

  const onPointerDown = (event: PointerEvent<HTMLDivElement>) => {
    const { px, py } = local(event);
    const onKnob = (event.target as HTMLElement).closest("[data-plan-knob]") !== null;
    const nearLine = planX !== null && event.pointerType !== "touch" && Math.abs(px - planX) <= NEAR_LINE && py >= ROW_A && py <= axisY;
    if (plan !== null && (onKnob || nearLine)) {
      event.preventDefault();
      wrapper.current!.setPointerCapture(event.pointerId);
      setDrag({ pointer: event.pointerId, from: plan });
      return;
    }
    if (py >= axisY && plan !== null) {
      moveTo(px, "axis");
      return;
    }
    const found = nearest(px, py);
    if (found !== null) {
      setHover(found);
      setDismissed(null);
    } else if (event.pointerType !== "mouse") {
      setHover(null);
    }
  };

  const onPointerMove = (event: PointerEvent<HTMLDivElement>) => {
    const { px, py } = local(event);
    if (drag) {
      if (frame.current) cancelAnimationFrame(frame.current);
      frame.current = requestAnimationFrame(() => moveTo(px, "drag"));
      return;
    }
    if (event.pointerType !== "mouse") return;
    const found = nearest(px, py);
    if (found !== null) {
      clearTimeout(hideTimer.current);
      if (found !== hover) setDismissed(null);
      setHover(found);
    } else if (hover !== null) {
      clearTimeout(hideTimer.current);
      hideTimer.current = setTimeout(() => setHover(null), 100);
    }
  };

  const endDrag = (event: PointerEvent<HTMLDivElement>) => {
    if (!drag) return;
    if (frame.current) cancelAnimationFrame(frame.current);
    const { px } = local(event);
    wrapper.current?.releasePointerCapture(drag.pointer);
    setDrag(null);
    moveTo(px, "drag-end");
  };

  const onWrapperKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key !== "Escape" || drag) return;
    if (shown !== null) {
      setDismissed(shown);
      event.preventDefault();
    }
  };

  // Escape during a drag puts the line back where the drag began, wherever focus is.
  useEffect(() => {
    if (!drag) return;
    const onKey = (event: globalThis.KeyboardEvent) => {
      if (event.key !== "Escape") return;
      event.preventDefault();
      if (frame.current) cancelAnimationFrame(frame.current);
      wrapper.current?.releasePointerCapture(drag.pointer);
      setDrag(null);
      onPlan(drag.from, "drag-end");
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [drag, onPlan]);

  const onSliderKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (plan === null) return;
    const moves: Record<string, number> = {
      ArrowRight: plan + 0.5,
      ArrowUp: plan + 0.5,
      ArrowLeft: plan - 0.5,
      ArrowDown: plan - 0.5,
      PageUp: plan + 3,
      PageDown: plan - 3,
      Home: 0.5,
      End: axisMax,
    };
    if (!(event.key in moves)) return;
    event.preventDefault();
    onPlan(snap(moves[event.key], axisMax), "key");
  };

  const focusDot = (index: number) => {
    setActive(index);
    dotRefs.current[index]?.focus();
  };
  const onGroupKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    const index = focused ?? active;
    const next: Record<string, number> = {
      ArrowLeft: index - 1,
      ArrowUp: index - 1,
      ArrowRight: index + 1,
      ArrowDown: index + 1,
      Home: 0,
      End: dots.length - 1,
    };
    if (!(event.key in next)) return;
    event.preventDefault();
    focusDot(Math.min(dots.length - 1, Math.max(0, next[event.key])));
  };

  // ── Labels ───────────────────────────────────────────────────────────
  const glyph = narrow ? 4 : 4.5;
  const signedWidth = widths.keySigned ?? 0;
  const hollowWidth = widths.keyHollow ?? 0;
  const keyWidth =
    (keySigned ? (keyLead ? 0 : 2 * glyph + 6) + signedWidth + 16 : 0) + (keyHollow ? 2 * glyph + 6 + hollowWidth : 0);
  // When the lane label and the key don't both fit on row A, the key keeps the row: it is the legend.
  const showLaneLabel = PAD + (widths.lane ?? 0) + 12 + keyWidth <= plotRight;
  const keyStart = showLaneLabel ? PAD + (widths.lane ?? 0) + 12 : PAD;
  const hollowStart = keySigned ? keyStart + (keyLead ? 0 : 2 * glyph + 6) + signedWidth + 16 : keyStart;
  const textBaseline = ROW_A / 2 + type.s * 0.35;

  // Row B: the readout sits right of the line in the left 55 percent of the plot, else left of it.
  const onRight = planX !== null && planX <= PAD + 0.55 * (width - 2 * PAD);
  const readoutWidth = Math.max(widths.readout ?? 0, widths.plan ?? 0);
  const readoutX =
    planX === null ? 0 : onRight ? clamp(planX + 10, PAD, plotRight - readoutWidth) : clamp(planX - 10, PAD + readoutWidth, plotRight);
  const showPlanWord = plan !== null && ownPlan !== null && plan === ownPlan;
  const readoutLine1 = ROW_A + type.s + 2;
  const readoutLine2 = readoutLine1 + type.s + 3;

  // Row C: the middle's label centred on its tick, the 8-in-10 label beside its line.
  const middleWidth = widths.middle ?? 0;
  const middleX = stats?.q50 != null ? clamp(x(stats.q50) - middleWidth / 2, PAD, plotRight - middleWidth) : 0;
  const in10Width = widths.in10 ?? 0;
  const q80x = stats?.q80 != null ? x(stats.q80) : 0;
  const in10Right = q80x + 4 + in10Width <= plotRight;
  const rowC1 = laneBottom + type.s + 2;
  const rowC2 = rowC1 + type.s + 4;

  const tipLeft = tipFor ? clamp(tipFor.cx - tipBox.w / 2, 0, width - tipBox.w) : 0;
  const above = tipFor ? tipFor.cy - layout.r - TIP_GAP - tipBox.h : 0;
  const tipTop = tipFor ? (above >= 0 ? above : tipFor.cy + layout.r + TIP_GAP) : 0;
  const knobLeft = planX ?? 0;

  return (
    <div
      ref={wrapper}
      data-range-chart
      className="relative touch-pan-y select-none"
      style={{ width, height }}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={endDrag}
      onPointerCancel={endDrag}
      onPointerLeave={() => {
        if (drag) return;
        clearTimeout(hideTimer.current);
        hideTimer.current = setTimeout(() => setHover(null), 100);
      }}
      onKeyDown={onWrapperKeyDown}
    >
      <p id={altId} className="sr-only" data-chart-alt>
        {alt}
      </p>
      <svg role="img" aria-labelledby={altId} width={width} height={height} className="block overflow-visible" data-chart-drawing>
        {/* Gridlines, behind everything. */}
        {ticks.map((tick) => (
          <line key={tick} x1={x(tick)} x2={x(tick)} y1={laneTop} y2={axisY} className="stroke-chart-grey200" strokeWidth={1} strokeDasharray="3 3" />
        ))}

        {/* Row A: the lane label and the key. */}
        <text
          ref={ref("lane")}
          x={PAD}
          y={textBaseline}
          fontSize={type.s}
          fontWeight={600}
          opacity={showLaneLabel ? 1 : 0}
          className="fill-chart-text-subtle uppercase"
        >
          {laneLabel}
        </text>
        {keySigned && (
          <>
            {!keyLead && <circle cx={keyStart + glyph} cy={ROW_A / 2} r={glyph} className="fill-chart-cat1-text" />}
            <text ref={ref("keySigned")} x={keyLead ? keyStart : keyStart + 2 * glyph + 6} y={textBaseline} fontSize={type.s} className="fill-chart-text">
              {keySigned}
            </text>
          </>
        )}
        {keyHollow && (
          <>
            <circle cx={hollowStart + glyph} cy={ROW_A / 2} r={glyph - 0.75} strokeWidth={1.5} className="fill-surface stroke-chart-cat1-text" />
            <text ref={ref("keyHollow")} x={hollowStart + 2 * glyph + 6} y={textBaseline} fontSize={type.s} className="fill-chart-text">
              {keyHollow}
            </text>
          </>
        )}

        {/* The lane: the middle half, the middle and the 8-in-10 point. */}
        {stats?.q25 != null && stats.q75 != null && (
          <rect
            data-band
            x={x(stats.q25)}
            y={laneTop + 8}
            width={Math.max(1, x(stats.q75) - x(stats.q25))}
            height={layout.lane - 16}
            rx={4}
            strokeWidth={1}
            className="fill-chart-grey200 stroke-line-strong"
          />
        )}
        {stats?.q80 != null && (
          <line data-in10 x1={q80x} x2={q80x} y1={laneTop} y2={laneBottom} strokeWidth={1.5} className="stroke-chart-grey400" />
        )}
        {stats?.q50 != null && (
          <line
            data-middle
            x1={x(stats.q50)}
            x2={x(stats.q50)}
            y1={laneTop + 2}
            y2={laneBottom - 2}
            strokeWidth={2.5}
            className="stroke-chart-grey500"
          />
        )}

        {/* The dots, each with a surface ring so touching dots stay apart. */}
        {dots.map((dot, index) => (
          <g key={dot.key} data-dot={dot.hollow ? "hollow" : "filled"}>
            <circle cx={dot.cx} cy={dot.cy} r={layout.r + 2} className="fill-surface" />
            {dot.hollow ? (
              <circle cx={dot.cx} cy={dot.cy} r={layout.r - 0.75} strokeWidth={1.5} className="fill-surface stroke-chart-cat1-text" />
            ) : (
              <circle cx={dot.cx} cy={dot.cy} r={layout.r} className="fill-chart-cat1-text" />
            )}
            {hover === index && focused === null && (
              <circle cx={dot.cx} cy={dot.cy} r={layout.r + 2} fill="none" strokeWidth={2} className="stroke-chart-grey500" />
            )}
          </g>
        ))}

        {/* The axis. */}
        <line x1={PAD} x2={plotRight} y1={axisY} y2={axisY} strokeWidth={1} className="stroke-line-strong" />
        {ticks.map((tick, index) => (
          <g key={tick}>
            <line x1={x(tick)} x2={x(tick)} y1={axisY} y2={axisY + 4} strokeWidth={1} className="stroke-line-strong" />
            <text
              x={x(tick)}
              y={axisY + 6 + type.s}
              textAnchor={index === 0 ? "start" : index === ticks.length - 1 ? "end" : "middle"}
              fontSize={type.s}
              className="fill-chart-text-subtle tabular-nums"
            >
              {index === ticks.length - 1 ? axisLastLabel : formatNumber(tick, { compact: false })}
            </text>
          </g>
        ))}

        {/* The plan: a line through everything, with a surface halo, and its readout in row B. */}
        {planX !== null && (
          <g data-plan-line>
            <line x1={planX} x2={planX} y1={ROW_A} y2={axisY} strokeWidth={4} className="stroke-surface" />
            <line x1={planX} x2={planX} y1={ROW_A} y2={axisY} strokeWidth={2} className="stroke-chart-grey500" />
            {showPlanWord && (
              <text
                ref={ref("plan")}
                x={readoutX}
                y={readoutLine1}
                textAnchor={onRight ? "start" : "end"}
                fontSize={type.s}
                fontWeight={600}
                className="fill-chart-text"
                style={HALO}
              >
                {planLabel}
              </text>
            )}
            {readout && (
              <text
                ref={ref("readout")}
                data-readout
                x={readoutX}
                y={showPlanWord ? readoutLine2 : readoutLine1}
                textAnchor={onRight ? "start" : "end"}
                fontSize={type.s}
                className="fill-chart-text tabular-nums"
                style={HALO}
              >
                {readout}
              </text>
            )}
          </g>
        )}
        {/* Row C: the statistics' labels, over the plan line, each with its halo. */}
        {middleLabel && stats?.q50 != null && (
          <text ref={ref("middle")} x={middleX} y={rowC1} fontSize={type.s} className="fill-chart-text" style={HALO}>
            {middleLabel}
          </text>
        )}
        {in10Label && stats?.q80 != null && (
          <text
            ref={ref("in10")}
            x={in10Right ? q80x + 4 : q80x - 4}
            y={rowC2}
            textAnchor={in10Right ? "start" : "end"}
            fontSize={type.s}
            className="fill-chart-text"
            style={HALO}
          >
            {in10Label}
          </text>
        )}

      </svg>

      {/* The plan line as a slider: dragged by its knob or within 8 px of the line, moved by the arrow
          keys, or set by clicking the axis row. Only the knob stops the page from scrolling under a thumb. */}
      {plan !== null && planX !== null && (
        <div
          role="slider"
          tabIndex={0}
          aria-label={sliderName}
          aria-valuemin={0.5}
          aria-valuemax={axisMax}
          aria-valuenow={plan}
          aria-valuetext={valueText ?? undefined}
          aria-orientation="horizontal"
          data-plan-knob
          data-dragging={drag ? "" : undefined}
          onKeyDown={onSliderKeyDown}
          onPointerEnter={() => setKnobHover(true)}
          onPointerLeave={() => setKnobHover(false)}
          // The knob is the slider itself, 12 by 24 px, so its focus ring sits 2 px around it. An
          // ::after pads its hit area to 24 by 44 px, and to 44 by 44 px for a coarse pointer.
          className={cx(
            "absolute flex h-6 w-3 cursor-ew-resize touch-none items-center justify-center gap-0.5 rounded-pill",
            "after:absolute after:-inset-x-1.5 after:-inset-y-2.5 after:content-[''] pointer-coarse:after:-inset-x-4",
            drag ? "bg-primary-pressed" : knobHover ? "bg-primary-hover" : "bg-primary",
          )}
          style={{ left: knobLeft, top: ROW_A, transform: "translateX(-50%)" }}
        >
          <span aria-hidden="true" className="h-3 w-px bg-surface" />
          <span aria-hidden="true" className="h-3 w-px bg-surface" />
        </div>
      )}

      {/* The dots as one group with one tab stop: arrow keys move between them, and each one's name
          says everything its tooltip shows. */}
      <p id={helpId} className="sr-only">
        {groupHelp}
      </p>
      <div role="group" aria-label={groupName} aria-describedby={helpId} onKeyDown={onGroupKeyDown} className="pointer-events-none absolute inset-0">
        {dots.map((dot, index) => (
          <span
            key={dot.key}
            ref={(element) => {
              dotRefs.current[index] = element;
            }}
            role="img"
            aria-label={dot.name}
            tabIndex={index === active ? 0 : -1}
            data-dot-target={index}
            onFocus={() => {
              setFocused(index);
              setActive(index);
              setDismissed(null);
            }}
            onBlur={() => setFocused(null)}
            // An ::after pads the dot to a 24 px target, the 12 px around its centre the pointer answers within.
            className="absolute rounded-full after:absolute after:-inset-2 after:content-['']"
            style={{ left: dot.cx - layout.r, top: dot.cy - layout.r, width: 2 * layout.r, height: 2 * layout.r }}
          />
        ))}
      </div>

      {/* A dot's tooltip: hidden from screen readers, because the dot's name says the same. */}
      {tipFor && (
        <div
          ref={tipRef}
          aria-hidden="true"
          data-dot-tooltip
          onPointerEnter={() => clearTimeout(hideTimer.current)}
          onPointerLeave={() => {
            clearTimeout(hideTimer.current);
            hideTimer.current = setTimeout(() => setHover(null), 100);
          }}
          className="absolute z-10 max-w-[240px] animate-fade-in rounded-sm border-[0.5px] border-chart-grey200 bg-surface px-3 py-2 shadow-popover"
          style={{ left: tipLeft, top: tipTop, fontSize: type.s }}
        >
          <p className={cx("font-semibold text-chart-text", tipFor.tip.mono && "font-mono wrap-anywhere")}>{tipFor.tip.header}</p>
          <p className="font-bold text-chart-text tabular-nums" style={{ fontSize: type.m }}>
            {tipFor.tip.number}
          </p>
          <p className="text-chart-text-subtle">{tipFor.tip.line}</p>
        </div>
      )}
    </div>
  );
}
