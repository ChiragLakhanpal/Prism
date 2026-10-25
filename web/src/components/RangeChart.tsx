// The range chart, lane 1 (DESIGN.md sections 5 and 6, the 12 brief): the past range of comparable
// packages on a month axis, one dot per package, with the plan as a full-height line you can move.
//
// The drawn layer is one svg with role="img", named by a hidden paragraph that states the same
// numbers (the alt text). The controls sit over it as siblings, because children of role="img" are
// hidden from assistive technology: the plan line is a role="slider" you drag, move with the arrow
// keys or set by clicking the axis row, and the dots are one group with one tab stop and arrow keys
// between them. A dot shows its package on hover or focus, and Escape hides that. While the pointer
// moves toward the tooltip, inside the band from where it last was on its dot (8 px each side) to the
// tooltip, the tooltip keeps its dot even over other dots, and shows another dot only after the pointer
// rests on it for 100 ms. A pointer moving along the dots leaves that band at once, so the tooltip
// follows it.
//
// The chart is 240 px tall, in five rows: the lane label and its key (A), the plan's readout (B), the
// lane with the middle half, the middle, the 8-in-10 line and the dots, the statistics' labels (C), and
// the axis. From 400 px wide, a readout that takes two lines makes row B, and the chart, 16 px taller.
// A swarm too tall for the lane makes the lane taller in 16 px steps before the first paint, and never
// after. A reader's text spacing can make rows A, B and C taller too. Each dot's centre is exactly its months, and dots
// that would overlap move up or down from the lane's centre in a fixed order, so the same data always
// draws the same picture and no dot sits on the wrong side of the plan line the readout counts against.
//
// Every number arrives from the tool, written by the caller with web/src/lib/format.ts; the chart only
// places it. Text over marks has a surface halo. There is no animation.
import {
  Fragment,
  useCallback,
  useEffect,
  useId,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  type KeyboardEvent,
  type PointerEvent,
  type ReactNode,
} from "react";
import { CircleDashed, CircleX } from "lucide-react";
import { cx } from "../lib/cx";
import { formatNumber } from "../lib/format";
import { MonoWords } from "./MonoWords";

// Lane 2, the time estimate (ticket 26; the 26 brief, section 5). The chart is 392 px tall at every width when it
// has lane 2: row A, the lane 1 label over its key (40 px), row B, lane 1 (112 px, 96 under 400 px wide), row C, a
// 16 px divider, row D, the lane 2 label over its key (40 px), lane 2 (40 px), row E, its two label lines (40 px),
// and the axis (32 px). A reader's text spacing can make a label row taller, as on lane 1.
export type Lane2Points = { q25: number; q50: number; q75: number; q80: number };
export type Lane2 =
  // A static bar where the estimate will be, while lane 1 has drawn and lane 2 has not.
  | { kind: "loading" }
  // An abstention or an error: HTML over the lane and row E, so it wraps.
  | { kind: "message"; tone: "abstain" | "error"; text: ReactNode }
  // The estimate: bar is the solid estimate shown now (the comparison's while comparing, null when too few went
  // with it); ghost is the estimate as described while comparing; note replaces row E's lines when bar is null.
  | {
      kind: "estimate";
      bar: Lane2Points | null;
      ghost: Lane2Points | null;
      labels: { middle: string; in10: string } | null;
      note: string | null;
      keyBar: string | null;
      keyGhost: string | null;
    };

// One part of a key: a glyph drawn as the mark it stands for, then its words.
type KeyGlyph = "filled" | "hollow" | "grey" | "bar" | "ghost" | "none";
type KeyPart = { glyph: KeyGlyph; text: string };
const KEY_A = ["keyA0", "keyA1", "keyA2"];
const KEY_D = ["keyD0", "keyD1"];

// Where each part of a key sits: on one line while they fit, each part moving whole to the next line when not.
// A part wider than the whole room takes two lines of its own (tall), as a reader's text spacing makes the quantile
// key at 320 px (breakFor), and the next part starts on the line after it.
function placeParts(parts: KeyPart[], widths: number[], glyphWidth: (glyph: KeyGlyph) => number, room: number, gap: number, tall: boolean[] = []) {
  const at: { x: number; line: number }[] = [];
  let x = 0;
  let line = 0;
  parts.forEach((part, index) => {
    const width = glyphWidth(part.glyph) + widths[index];
    const afterTall = index > 0 && tall[index - 1];
    if (index > 0 && (afterTall || tall[index] || x + gap + width > room)) {
      line += afterTall ? 2 : 1;
      x = 0;
    } else if (index > 0) x += gap;
    at.push({ x, line });
    x += width;
  });
  return { at, lines: line + 1 + (tall[parts.length - 1] ? 1 : 0) };
}

export type RangeMark = {
  key: string;
  months: number;
  // A package still open, or a quantile dot the curve never reached, is drawn hollow.
  hollow: boolean;
  // A quantile dot the curve never reached: it sits past its months, so it is pinned at the plot's
  // right edge with a chevron, and the axis is not stretched to reach it.
  beyond?: boolean;
  // The dot's accessible name, from the copy file.
  name: string;
  tip: { header: string; mono: boolean; number: string; line: string };
};

export type RangeStats = { q25: number | null; q50: number | null; q75: number | null; q80: number | null };

export type PlanMove = "drag" | "drag-end" | "key" | "axis";

// The widest readout for plans from `from` months up to the next band's: one line, and the copy's two.
export type ReadoutBand = { from: number; one: string; lines: [string, string] };

const ROW_A = 24;
const ROW_C = 40;
const AXIS = 32;
const PAD = 8;
const MAX_LANE = 160;
const HIT = 12; // a dot answers the pointer within 12 px of its centre
const BAND = 8; // the band's half-width where it starts, at the pointer's last point on its dot
const NEAR_LINE = 8; // a fine pointer can grab the plan line within 8 px of it
const TIP_GAP = 8;
// The readout's lines, as useTextWidths measures them: two from the copy, or more where its words wrap.
const READOUT_LINES = ["readout0", "readout1", "readout2", "readout3", "readout4", "readout5"];

// DESIGN.md section 6: type sizes by chart width (s, m, l).
export function chartType(width: number): { s: number; m: number; l: number } {
  if (width < 400) return { s: 12, m: 14, l: 16 };
  if (width <= 700) return { s: 13, m: 15, l: 18 };
  return { s: 14, m: 16, l: 20 };
}

// About five ticks: every 3 months up to 12, every 6 up to 36, every 12 above that, stepping up to
// 24 and 48 so there are at most six labels, or five when the chart is under 400 px wide.
const STEPS = [3, 6, 12, 24, 48];
export function axisFor(largest: number, width = Number.POSITIVE_INFINITY): { max: number; step: number } {
  const most = width < 400 ? 5 : 6;
  const first = largest <= 12 ? 3 : largest > 36 ? 12 : 6;
  const steps = STEPS.filter((step) => step >= first);
  const fits = (step: number) => Math.max(step, Math.ceil(largest / step) * step) / step + 1 <= most;
  const step = steps.find(fits) ?? steps[steps.length - 1];
  return { max: Math.max(step, Math.ceil(largest / step) * step), step };
}

export const snap = (value: number, max: number) => Math.min(max, Math.max(0.5, Math.round(value * 2) / 2));

// The vertical offsets that keep dots apart, in the order given, or null when the swarm is taller than the lane.
// Section 5's cost lane places its dots the same way (ticket 31, CostLane.tsx).
export function swarm(xs: number[], r: number, lane: number): number[] | null {
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

type Box = { x: number; y: number; width: number; height: number };
const NO_BOX: Box = { x: 0, y: 0, width: 0, height: 0 };
const sameBox = (a: Box | undefined, b: Box) =>
  a !== undefined && Math.abs(a.x - b.x) < 0.5 && Math.abs(a.y - b.y) < 0.5 && Math.abs(a.width - b.width) < 0.5 && Math.abs(a.height - b.height) < 0.5;

// Where a label could take a second line: at a space, the width of its text before the space and after.
type Break = { at: number; before: number; after: number };
const sameBreaks = (a: Break[] | undefined, b: Break[]) =>
  a !== undefined && a.length === b.length && a.every((one, i) => one.at === b[i].at && Math.abs(one.before - b[i].before) < 0.5);

// The widths of the svg text a label needs to stay inside the plot, each label's box for the knockout
// drawn under it, and, for the labels that may take two lines, where each could break. They are read
// after each render, when the fonts arrive, and again when a label's size changes without a render, as
// when a reader switches on text spacing (WCAG 1.4.12) after the chart is drawn.
function useTextWidths(keys: string[], breakable: string[]) {
  const refs = useRef<Record<string, SVGTextContentElement | null>>({});
  const [widths, setWidths] = useState<Record<string, number>>({});
  const [boxes, setBoxes] = useState<Record<string, Box>>({});
  const [breaks, setBreaks] = useState<Record<string, Break[]>>({});
  // Bumped to read the labels again when nothing else renders the chart.
  const [measure, setMeasure] = useState(0);
  const observer = useRef<ResizeObserver | null>(null);
  useEffect(() => {
    let live = true;
    document.fonts?.ready.then(() => live && setMeasure((n) => n + 1));
    // The labels attached before this ran, or again after React's StrictMode ran it twice.
    if (typeof ResizeObserver !== "undefined") {
      const watch = (observer.current ??= new ResizeObserver(() => setMeasure((n) => n + 1)));
      for (const element of Object.values(refs.current)) if (element) watch.observe(element);
    }
    return () => {
      live = false;
      observer.current?.disconnect();
      observer.current = null;
    };
  }, []);
  useLayoutEffect(() => {
    const next: Record<string, number> = {};
    const nextBoxes: Record<string, Box> = {};
    const nextBreaks: Record<string, Break[]> = {};
    for (const key of keys) {
      const element = refs.current[key];
      next[key] = element ? element.getComputedTextLength() : 0;
      const box = element?.getBBox();
      nextBoxes[key] = box ? { x: box.x, y: box.y, width: box.width, height: box.height } : NO_BOX;
    }
    for (const key of breakable) {
      const element = refs.current[key];
      const spaces = element ? [...(element.textContent ?? "").matchAll(/ /g)].map((match) => match.index) : [];
      nextBreaks[key] = spaces.map((at) => ({
        at,
        before: element!.getSubStringLength(0, at),
        after: next[key] - element!.getSubStringLength(0, at + 1),
      }));
    }
    setWidths((now) => (keys.every((key) => Math.abs((now[key] ?? -1) - next[key]) < 0.5) ? now : next));
    setBoxes((now) => (keys.every((key) => sameBox(now[key], nextBoxes[key])) ? now : nextBoxes));
    setBreaks((now) => (breakable.every((key) => sameBreaks(now[key], nextBreaks[key])) ? now : nextBreaks));
  });
  void measure;
  // One callback per label, kept across renders, so React attaches it only when its element changes,
  // and each element is observed once.
  const callbacks = useRef<Record<string, (element: SVGTextContentElement | null) => void>>({});
  const ref = useCallback(
    (key: string) =>
      (callbacks.current[key] ??= (element: SVGTextContentElement | null) => {
        const old = refs.current[key];
        refs.current[key] = element;
        if (old === element || typeof ResizeObserver === "undefined") return;
        observer.current ??= new ResizeObserver(() => setMeasure((n) => n + 1));
        if (old) observer.current.unobserve(old);
        if (element) observer.current.observe(element);
      }),
    [],
  );
  return { widths, boxes, breaks, ref };
}

// A label wider than its room takes a second line, from the last space that lets its first line fit.
// Only a reader's text spacing makes one that wide: at 320 px, WCAG 1.4.12's spacing makes the middle's
// label and the quantile key wider than the chart. Null keeps the label on one line.
function breakFor(breaks: Break[] | undefined, whole: number, room: number): Break | null {
  if (whole <= room || !breaks?.length) return null;
  const fit = breaks.filter((one) => one.before <= room);
  return fit.length ? fit[fit.length - 1] : breaks[0];
}
const lineWidth = (one: Break | null, whole: number) => (one ? Math.max(one.before, one.after) : whole);

// A text filled into as few lines as fit the room, with the lines as even as they can be, so no word is
// left alone on the last one. Filling each line with words while they fit gives the fewest lines; the
// narrowest room that still gives that many evens them out. It returns the spaces where lines end,
// counted from the first space, so a text with the same words and other digits can break at the same ones.
function wrapAt(breaks: Break[] | undefined, whole: number, room: number): number[] {
  if (!breaks?.length) return [];
  // The width of the text up to and including space i, or 0 before the first word.
  const upTo = (i: number) => (i < 0 ? 0 : whole - breaks[i].after);
  const fill = (width: number) => {
    const ends: number[] = [];
    let from = -1;
    while (whole - upTo(from) > width && from < breaks.length - 1) {
      let end = from + 1;
      for (let i = from + 1; i < breaks.length; i++) if (breaks[i].before - upTo(from) <= width) end = i;
      ends.push(end);
      from = end;
    }
    return ends;
  };
  const fewest = fill(room).length;
  let low = 0;
  let high = room;
  for (let step = 0; step < 16; step++) {
    const middle = (low + high) / 2;
    if (fill(middle).length <= fewest) high = middle;
    else low = middle;
  }
  return fill(high);
}

// A text cut into lines at the spaces wrapAt chose.
function splitAt(text: string, ends: number[]): string[] {
  const spaces = [...text.matchAll(/ /g)].map((match) => match.index);
  const lines: string[] = [];
  let from = 0;
  for (const end of ends) {
    const at = spaces[end];
    if (at === undefined) break;
    lines.push(text.slice(from, at));
    from = at + 1;
  }
  lines.push(text.slice(from));
  return lines;
}

// A label's text on one line, or on two from its break, each line starting at x.
function Lines({ text, at, x, step }: { text: string; at: number | null; x: number; step: number }) {
  if (at === null) return text;
  return (
    <>
      <tspan x={x}>{text.slice(0, at)}</tspan>{" "}
      <tspan x={x} dy={step}>
        {text.slice(at + 1)}
      </tspan>
    </>
  );
}

// A surface rect under a label, its box plus 2 px, drawn after the plan line: where the label cannot
// move off the line, the line stops cleanly above it and resumes below it (DESIGN.md section 6). It
// ends at the floor, the top of the axis line's stroke, so the axis runs whole under row C.
function Knockout({ kind, box, floor }: { kind: string; box: Box | undefined; floor: number }) {
  if (!box || box.width === 0) return null;
  const top = box.y - 2;
  const bottom = Math.min(box.y + box.height + 2, floor);
  return <rect data-knockout={kind} x={box.x - 2} y={top} width={box.width + 4} height={bottom - top} className="fill-surface" />;
}

// A 3 px surface halo under text that sits over marks (DESIGN.md section 6).
const HALO = { stroke: "var(--color-surface)", strokeWidth: 3, paintOrder: "stroke", strokeLinejoin: "round" } as const;

// One part of a key: its glyph, drawn with the mark it stands for, then its words, on the key's line.
function KeyItem({
  part,
  at,
  top,
  lineGap,
  fontSize,
  glyph,
  textRef,
  breakAt = null,
}: {
  part: KeyPart;
  at: { x: number; line: number };
  top: number;
  lineGap: number;
  fontSize: number;
  glyph: number;
  textRef: (element: SVGTextContentElement | null) => void;
  // Where the words take their second line, for a part wider than the chart (breakFor), or null.
  breakAt?: number | null;
}) {
  const cy = top + at.line * lineGap;
  const textX = at.x + (part.glyph === "none" ? 0 : part.glyph === "bar" || part.glyph === "ghost" ? 22 : 2 * (part.glyph === "grey" ? 3 : glyph) + 6);
  return (
    <g data-key-part={part.glyph}>
      {part.glyph === "filled" && <circle cx={at.x + glyph} cy={cy} r={glyph} className="fill-chart-cat1-text" />}
      {part.glyph === "hollow" && <circle cx={at.x + glyph} cy={cy} r={glyph - 0.75} strokeWidth={1.5} className="fill-surface stroke-chart-cat1-text" />}
      {part.glyph === "grey" && <circle cx={at.x + 3} cy={cy} r={3} className="fill-chart-grey300" />}
      {part.glyph === "bar" && (
        <>
          <rect x={at.x} y={cy - 5} width={16} height={10} rx={2} className="fill-primary" />
          <rect x={at.x + 9} y={cy - 5} width={2} height={10} className="fill-surface" />
        </>
      )}
      {part.glyph === "ghost" && (
        <>
          <rect x={at.x} y={cy - 6} width={16} height={12} fill="none" strokeWidth={3} className="stroke-surface" />
          <rect x={at.x} y={cy - 6} width={16} height={12} fill="none" strokeWidth={1.5} strokeDasharray="4 2" className="stroke-chart-grey500" />
        </>
      )}
      <text ref={textRef} x={textX} y={cy + fontSize * 0.35} fontSize={fontSize} className="fill-chart-text">
        <Lines text={part.text} at={breakAt} x={textX} step={lineGap} />
      </text>
    </g>
  );
}

// The time estimate as described while a comparison shows: a dashed outline from its quarter to its three quarters,
// a tick at its middle and an end cap at its 8-in-10 point, each a 1.5 px grey500 dash (4, 2) over a 3 px surface
// underlay, so it reads over the navy bar and over white alike (the 26 brief, section 5.4). It never moves.
function Ghost({ points, x, centre }: { points: Lane2Points; x: (months: number) => number; centre: number }) {
  const left = x(points.q25);
  const right = x(points.q75);
  const shapes = (
    <>
      <rect x={left} y={centre - 12} width={Math.max(1, right - left)} height={24} />
      <line x1={x(points.q50)} x2={x(points.q50)} y1={centre - 12} y2={centre + 12} />
      <line x1={x(points.q80)} x2={x(points.q80)} y1={centre - 6} y2={centre + 6} />
    </>
  );
  return (
    <g data-lane2-ghost fill="none">
      <g strokeWidth={3} className="stroke-surface">
        {shapes}
      </g>
      <g strokeWidth={1.5} strokeDasharray="4 2" className="stroke-chart-grey500">
        {shapes}
      </g>
    </g>
  );
}

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
  readoutLines,
  readoutWidest,
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
  onOpen,
  opened = null,
  openHint,
  openLabel,
  lane2,
  lane2Label = "",
  lane2LabelShort = "",
  matching = null,
  compareKey = null,
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
  // The readout's count line, "2 of 49 signed within 1.5 months", and the same as two lines, "2 of 49
  // signed" over "within 1.5 months", for a chart where one line does not fit beside the line.
  readout: string | null;
  readoutLines: [string, string] | null;
  // The widest readout the line can reach from each band's months to the next band's, as one line and
  // as the copy's two: every package signed, by the band's last month. The readout's lines are chosen
  // from them, so row B stays the same while the line moves.
  readoutWidest: ReadoutBand[];
  // The key: the signed count beside a filled dot and the open count beside a hollow one. With
  // keyLead, the key is words alone, with no glyphs: a lead, "Each dot is 1 in 20 of the 103 packages.",
  // then the open count, because quantile dots do not draw open packages one by one.
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
  // Ticket 15: a click on a dot, Enter on the focused dot, or a tapped dot's "Open its records" button
  // opens that package in the evidence drawer, with the dot's element to give focus back to. The opened
  // mark, by its key, keeps a 2 px selection1 ring while the drawer shows it. Charts that open nothing,
  // such as a quantile dot's, leave these out.
  onOpen?: (key: string, element: HTMLElement) => void;
  opened?: string | null;
  // The tooltip's last line for a pointer, and the touch tooltip's button.
  openHint?: string;
  openLabel?: string;
  // Ticket 26: lane 2, the time estimate, under lane 1 on the same axis, and its label. Without it the chart
  // draws lane 1 alone, as ticket 12 built it.
  lane2?: Lane2;
  lane2Label?: string;
  // The label in fewer words, for a chart its full label would not fit in, as at 320 px with a reader's text spacing.
  lane2LabelShort?: string;
  // While comparing: the marks of the packages that went with the option keep their look, every other dot turns
  // grey300 at r 3, and row A's key says how many went with it ("{k} went with 3 lots", "{rest} others").
  matching?: ReadonlySet<string> | null;
  compareKey?: { match: string; others: string; open: string | null } | null;
}) {
  const twoLanes = lane2 !== undefined;
  const altId = useId();
  const helpId = useId();
  const narrow = width < 400;
  const type = chartType(width);
  const baseLane = narrow ? 96 : 112;
  const plotRight = width - PAD;
  const x = useCallback((months: number) => PAD + (Math.min(months, axisMax) / axisMax) * (width - 2 * PAD), [axisMax, width]);
  const monthsAt = (px: number) => ((px - PAD) / Math.max(1, width - 2 * PAD)) * axisMax;

  const r0 = big ? (narrow ? 5 : 6) : narrow ? 4 : 4.5;
  const xs = useMemo(() => marks.map((mark) => (mark.beyond ? plotRight - r0 - 2 : x(mark.months))), [marks, x, plotRight, r0]);
  const layout = useMemo(() => fit(xs, r0, big ? r0 : 4, baseLane), [xs, r0, big, baseLane]);
  const widestKeys = readoutWidest.map((_, index) => [`widest${index}`, `widest${index}-0`, `widest${index}-1`] as const);
  const { widths, boxes, breaks, ref } = useTextWidths(
    ["lane", "keySigned", "keyHollow", "plan", ...READOUT_LINES, ...widestKeys.flat(), "middle", "in10", "tickLast", "tickPrev",
      ...KEY_A, ...KEY_D, "lane2", "lane2Full", "middle2", "in102"],
    ["keySigned", "middle", "middle2", ...KEY_A, ...widestKeys.map(([one]) => one)],
  );
  // Lane 2's label, in fewer words when the full one is wider than the chart.
  const lane2Shown = lane2LabelShort && (widths.lane2Full ?? 0) > width ? lane2LabelShort : lane2Label;
  // Row A: the lane label and the key, from the chart's left edge. When the key is wider than the
  // chart, its hollow half takes a line of its own, and row A grows by that line before the first paint.
  // A signed half wider than the chart takes two lines (breakFor).
  const glyph = narrow ? 4 : 4.5;
  const signedWidth = widths.keySigned ?? 0;
  const hollowWidth = widths.keyHollow ?? 0;

  const glyphPart = keyLead ? 0 : 2 * glyph + 6;
  const signedPart = keySigned ? glyphPart + signedWidth : 0;
  const hollowPart = keyHollow ? glyphPart + hollowWidth : 0;
  // Two sentences in words alone sit a space apart; a glyph's halves sit 16 px apart.
  const keyGap = keyLead ? Math.round(type.s * 0.3) : 16;
  const keyWidth = signedPart + (keySigned && keyHollow ? keyGap : 0) + hollowPart;
  // When the lane label and the key don't both fit on row A, the key keeps the row: it is the legend.
  const showLaneLabel = (widths.lane ?? 0) + 12 + keyWidth <= width;
  const keyStart = showLaneLabel ? (widths.lane ?? 0) + 12 : 0;
  const signedBreak = keySigned ? breakFor(breaks.keySigned, signedWidth, width - glyphPart) : null;
  const keyWraps = Boolean(keySigned && keyHollow) && keyStart + keyWidth > width;
  const lineGap = type.s + 2;
  const signedLines = signedBreak ? 2 : 1;
  // With lane 2, row A is two lines: the lane label, then the key, whose parts move whole to a line of their own
  // when they don't fit. While comparing, the key counts the dots that went with the option.
  const keyAParts: KeyPart[] = compareKey
    ? [
        { glyph: keyLead ? "none" : "filled", text: compareKey.match },
        ...(keyLead ? [] : [{ glyph: "grey" as const, text: compareKey.others }]),
        ...(compareKey.open && !keyLead ? [{ glyph: "hollow" as const, text: compareKey.open }] : []),
      ]
    : [
        ...(keySigned ? [{ glyph: (keyLead ? "none" : "filled") as KeyGlyph, text: keySigned }] : []),
        ...(keyHollow ? [{ glyph: (keyLead ? "none" : "hollow") as KeyGlyph, text: keyHollow }] : []),
      ];
  const keyGlyphWidth = (glyph: KeyGlyph) => (glyph === "none" ? 0 : glyph === "bar" || glyph === "ghost" ? 22 : 2 * glyphRadius(glyph) + 6);
  function glyphRadius(kind: KeyGlyph) {
    return kind === "grey" ? 3 : glyph;
  }
  const keyABreaks = keyAParts.map((part, index) =>
    breakFor(breaks[KEY_A[index]], widths[KEY_A[index]] ?? 0, width - keyGlyphWidth(part.glyph)),
  );
  const placedA = placeParts(
    keyAParts,
    keyAParts.map((_, index) => widths[KEY_A[index]] ?? 0),
    keyGlyphWidth,
    width,
    keyGap,
    keyABreaks.map((one) => one !== null),
  );
  const rowA = twoLanes
    ? 40 + (placedA.lines - 1) * lineGap
    : ROW_A + (signedLines - 1 + (keyWraps ? 1 : 0)) * lineGap;
  const hollowStart = keyWraps ? keyStart : keySigned ? keyStart + signedPart + keyGap : keyStart;
  const textBaseline = ROW_A / 2 + type.s * 0.35;
  const hollowY = keyWraps ? signedLines * lineGap : 0;

  // Row B: the readout, beside the plan line and never across it. Its lines are chosen once for the
  // chart's width, from the widest readout the line can reach in each band of months (readoutWidest),
  // so they fit on the roomier side of the line wherever it sits, and row B never changes while the line
  // moves. A band's least room is on the roomier side of the line where the line sits nearest the middle
  // of the plot. The readout is one line where one line fits there, from 400 px wide; otherwise it is
  // the copy's two lines; and where a copy line is still too wide, as with WCAG 1.4.12's text spacing at
  // 320 px, its words fill as few lines as fit, as even as they can be (wrapAt). "Plan" sits on a line
  // above them at the plan row's own months. Row B holds it with up to two lines of the readout, and
  // grows by a line for each line past that.
  //
  // The knob is 12 px wide and its focus ring sits 2 px out and is 2 px thick, so it ends 10 px from the
  // line; the readout starts 4 px past that (GAP). Its halo's box reaches 3 px past its letters, so the
  // letters stay that far inside the chart where they can (EDGE). The room leaves that margin out: a
  // surface halo on the surface cannot be seen past the chart's edge anyway.
  const GAP = 14;
  const EDGE = 3;
  const readoutStep = type.s + 3;
  const bands = readoutWidest.map((band, index) => {
    const [one, first, second] = widestKeys[index];
    const next = readoutWidest[index + 1]?.from ?? axisMax;
    const nearest = x(clamp(axisMax / 2, Math.max(band.from, 0.5), Math.min(next, axisMax)));
    return {
      from: band.from,
      room: Math.max(nearest, width - nearest) - GAP,
      one: widths[one] ?? 0,
      copy: Math.max(widths[first] ?? 0, widths[second] ?? 0),
      breaks: breaks[one],
    };
  });
  const readoutKind = !narrow && bands.every((band) => band.one <= band.room) ? "one" : bands.every((band) => band.copy <= band.room) ? "copy" : "wrap";
  const bandEnds = bands.map((band) => (readoutKind === "wrap" ? wrapAt(band.breaks, band.one, band.room) : []));
  const readoutRows = readoutKind === "one" ? 1 : readoutKind === "copy" ? 2 : Math.max(1, ...bandEnds.map((ends) => ends.length + 1));
  const rowB = (readoutRows >= 2 ? 48 : 32) + Math.max(0, readoutRows + (ownPlan !== null ? 1 : 0) - 3) * readoutStep;
  const laneTop = rowA + rowB;
  const laneBottom = laneTop + layout.lane;
  // Row C grows by a line when the middle's label takes two (breakFor).
  const rowCStep = type.s + 4;
  const middleBreak = middleLabel ? breakFor(breaks.middle, widths.middle ?? 0, plotRight - PAD) : null;
  const rowCBottom = laneBottom + ROW_C + (middleBreak ? rowCStep : 0);
  // Lane 2's rows under lane 1's: the divider, row D (its label over its key), the lane and row E.
  const estimate = lane2?.kind === "estimate" ? lane2 : null;
  const keyDParts: KeyPart[] = estimate
    ? [
        ...(estimate.bar && estimate.keyBar ? [{ glyph: "bar" as const, text: estimate.keyBar }] : []),
        ...(estimate.ghost && estimate.keyGhost ? [{ glyph: "ghost" as const, text: estimate.keyGhost }] : []),
      ]
    : [];
  const placedD = placeParts(keyDParts, keyDParts.map((_, index) => widths[KEY_D[index]] ?? 0), keyGlyphWidth, width, 16);
  const rowDTop = rowCBottom + 16;
  const rowDHeight = 40 + (Math.max(placedD.lines, 1) - 1) * lineGap;
  const lane2Top = rowDTop + rowDHeight;
  const lane2Centre = lane2Top + 20;
  const rowETop = lane2Top + 40;
  const middle2Break = estimate?.labels && estimate.bar ? breakFor(breaks.middle2, widths.middle2 ?? 0, plotRight - PAD) : null;
  const axisY = twoLanes ? rowETop + 40 + (middle2Break ? rowCStep : 0) : rowCBottom;
  const height = axisY + AXIS;
  const centre = laneTop + layout.lane / 2;
  const dots = marks.map((mark, index) => ({ ...mark, cx: xs[index], cy: centre + layout.offsets[index] }));
  // A dot's drawn radius: r 3 while a comparison fades it, its own otherwise. Its rings follow it.
  const drawnR = (key: string) => (matching !== null && !matching.has(key) ? 3 : layout.r);

  const ticks = Array.from({ length: Math.floor(axisMax / step) + 1 }, (_, index) => index * step);

  // ── Hover, focus and the tooltip ─────────────────────────────────────
  const [hover, setHover] = useState<number | null>(null);
  const [focused, setFocused] = useState<number | null>(null);
  const [active, setActive] = useState(0);
  const [dismissed, setDismissed] = useState<number | null>(null);
  // Whether the last press on the chart was a finger's or a pen's, so a tapped dot's details hold a button.
  const [tapped, setTapped] = useState(false);
  const hideTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const restTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  // The pointer's last point on the hovered dot, where the band toward its tooltip starts.
  const apex = useRef<{ x: number; y: number } | null>(null);
  const dotRefs = useRef<(HTMLSpanElement | null)[]>([]);
  const tipRef = useRef<HTMLDivElement>(null);
  const shown = focused ?? hover;
  const tipFor = shown !== null && shown !== dismissed && dots[shown] ? dots[shown] : null;
  // The tooltip's size, and the room above the chart inside its card (the closest section), which the
  // tooltip may use: it sits above its dot whenever it fits inside the card.
  const [tipBox, setTipBox] = useState({ w: 0, h: 0, room: 0 });
  useLayoutEffect(() => {
    const element = tipRef.current;
    const chart = wrapper.current;
    if (!element || !chart) return;
    const card = chart.closest("section") ?? chart;
    const room = Math.max(0, chart.getBoundingClientRect().top - card.getBoundingClientRect().top);
    const next = { w: element.offsetWidth, h: element.offsetHeight, room };
    setTipBox((now) => (now.w === next.w && now.h === next.h && Math.abs(now.room - next.room) < 1 ? now : next));
  });
  useEffect(
    () => () => {
      clearTimeout(hideTimer.current);
      clearTimeout(restTimer.current);
    },
    [],
  );
  // The tooltip hides 100 ms after the pointer leaves both the dot and the tooltip.
  const hideLater = () => {
    clearTimeout(restTimer.current);
    clearTimeout(hideTimer.current);
    hideTimer.current = setTimeout(() => setHover(null), 100);
  };

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
  const knobRef = useRef<HTMLDivElement>(null);
  const planX = plan === null ? null : x(plan);
  const local = (event: PointerEvent) => {
    const box = wrapper.current!.getBoundingClientRect();
    return { px: event.clientX - box.left, py: event.clientY - box.top };
  };
  const moveTo = (px: number, how: PlanMove) => onPlan(snap(monthsAt(px), axisMax), how);
  // The tooltip is part of its dot's hover area (WCAG 1.4.13): the pointer on it keeps it, and a press
  // on it selects its text rather than reaching the chart under it.
  const onTip = (event: PointerEvent) => tipRef.current?.contains(event.target as Node) ?? false;

  const onPointerDown = (event: PointerEvent<HTMLDivElement>) => {
    if (onTip(event)) return;
    const { px, py } = local(event);
    const onKnob = (event.target as HTMLElement).closest("[data-plan-knob]") !== null;
    const nearLine = planX !== null && event.pointerType !== "touch" && Math.abs(px - planX) <= NEAR_LINE && py >= rowA && py <= axisY;
    if (plan !== null && (onKnob || nearLine)) {
      event.preventDefault();
      // A drag gives the slider focus, as a native slider takes it when pressed, so the arrow keys can
      // nudge the line just moved.
      knobRef.current?.focus({ preventScroll: true });
      wrapper.current!.setPointerCapture(event.pointerId);
      setDrag({ pointer: event.pointerId, from: plan });
      return;
    }
    if (py >= axisY && plan !== null) {
      moveTo(px, "axis");
      return;
    }
    const found = nearest(px, py);
    setTapped(event.pointerType !== "mouse");
    if (found !== null) {
      apex.current = { x: px, y: py };
      setHover(found);
      setDismissed(null);
      // A click on a dot opens its records; a tap shows its details, whose button opens them, since dots
      // are too small and close to tap one by one (the 15 brief, section 3).
      // The press keeps the browser from moving focus, so focus goes into the drawer, as a keyboard's Enter sends it.
      if (onOpen && event.pointerType === "mouse" && dotRefs.current[found]) {
        event.preventDefault();
        onOpen(dots[found].key, dotRefs.current[found]!);
      }
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
    if (onTip(event)) {
      clearTimeout(hideTimer.current);
      clearTimeout(restTimer.current);
      return;
    }
    track(px, py);
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
      // A dot waiting for its 100 ms rest doesn't take the tooltip back after Escape.
      clearTimeout(restTimer.current);
      setDismissed(shown);
      event.preventDefault();
    }
  };

  // Escape hides a tooltip the pointer opened, wherever focus is (WCAG 1.4.13).
  const hovered = focused === null && hover !== null && hover !== dismissed ? hover : null;
  useEffect(() => {
    if (hovered === null) return;
    const onKey = (event: globalThis.KeyboardEvent) => {
      if (event.key !== "Escape") return;
      clearTimeout(restTimer.current);
      setDismissed(hovered);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [hovered]);

  // A tap anywhere outside the chart hides a tapped dot's details; inside it, onPointerDown decides.
  useEffect(() => {
    if (hover === null) return;
    const onDown = (event: globalThis.PointerEvent) => {
      if (event.pointerType === "mouse" || wrapper.current?.contains(event.target as Node)) return;
      setHover(null);
    };
    document.addEventListener("pointerdown", onDown, true);
    return () => document.removeEventListener("pointerdown", onDown, true);
  }, [hover]);

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
    if (event.key === "Enter" && onOpen && focused !== null && dotRefs.current[focused]) {
      event.preventDefault();
      onOpen(dots[focused].key, dotRefs.current[focused]!);
      return;
    }
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
  // Row B's readout sits right of the line in the left 55 percent of the plot and left of it otherwise,
  // and on the other side when it does not fit there. Its lines always fit on the roomier side (row B,
  // above), and the current readout has the widest one's words with the same or fewer digits, so it
  // breaks at the same spaces. Should it ever fit on neither side, it takes the side with more room, and
  // the halo's margin goes before the gap to the ring: a surface halo on the surface cannot be seen past
  // the edge anyway.
  const showPlanWord = plan !== null && ownPlan !== null && plan === ownPlan;
  const band = plan === null ? 0 : bands.reduce((found, one, index) => (plan >= one.from ? index : found), 0);
  const lines =
    readout === null
      ? []
      : readoutKind === "one"
        ? [readout]
        : readoutKind === "copy"
          ? (readoutLines ?? [readout])
          : splitAt(readout, bandEnds[band] ?? []);
  const readoutWidth = Math.max(0, ...lines.map((_, index) => widths[READOUT_LINES[index]] ?? 0), showPlanWord ? (widths.plan ?? 0) : 0);
  let edge = EDGE;
  let onRight = planX !== null && planX <= PAD + 0.55 * (width - 2 * PAD);
  if (planX !== null) {
    const fitsRight = planX + GAP + readoutWidth + EDGE <= width;
    const fitsLeft = planX - GAP - readoutWidth - EDGE >= 0;
    if (!fitsRight && !fitsLeft) edge = 0;
    if (onRight && !fitsRight) onRight = fitsLeft ? false : width - planX >= planX;
    else if (!onRight && !fitsLeft) onRight = fitsRight ? true : width - planX >= planX;
  }
  const readoutX =
    planX === null ? 0 : onRight ? clamp(planX + GAP, 0, width - readoutWidth - edge) : clamp(planX - GAP, readoutWidth + edge, width);
  // Its last line's descenders stay clear of the middle tick, which starts 4 px into the lane.
  const readoutLine1 = rowA + type.s;
  const firstLine = showPlanWord ? readoutLine1 + readoutStep : readoutLine1;

  // Row C: the middle's label centred on its tick, and the 8-in-10 label beside its line, right of it
  // when it fits. Each moves off the plan line when it would cross it, if it can clear the line by 6 px;
  // where it cannot, its knockout stops the line around it.
  const middleWidth = lineWidth(middleBreak, widths.middle ?? 0);
  let middleX = stats?.q50 != null ? clamp(x(stats.q50) - middleWidth / 2, PAD, plotRight - middleWidth) : 0;
  if (stats?.q50 != null && planX !== null && middleX - 3 < planX && planX < middleX + middleWidth + 3) {
    const tick = x(stats.q50);
    const options = [planX + 6, planX - 6 - middleWidth].filter((start) => start >= PAD && start + middleWidth <= plotRight);
    if (options.length) middleX = options.reduce((a, b) => (Math.abs(a + middleWidth / 2 - tick) <= Math.abs(b + middleWidth / 2 - tick) ? a : b));
  }
  const in10Width = widths.in10 ?? 0;
  const q80x = stats?.q80 != null ? x(stats.q80) : 0;
  // Left of its line, it starts no further left than the chart's left edge. That happens where it fits
  // on neither side, as with WCAG 1.4.12's text spacing at 320 px, and where it moves off the plan line
  // near the left of a narrow chart.
  const in10Start = (right: boolean) => (right ? q80x + 4 : Math.max(0, q80x - 4 - in10Width));
  let in10Right = q80x + 4 + in10Width <= plotRight;
  if (stats?.q80 != null && planX !== null) {
    const start = in10Start(in10Right);
    const other = in10Start(!in10Right);
    const crossed = start - 3 < planX && planX < start + in10Width + 3;
    const otherFits = other >= 0 && other + in10Width <= plotRight;
    const otherClears = other + in10Width <= planX - 6 || other >= planX + 6;
    if (crossed && otherFits && otherClears) in10Right = !in10Right;
  }
  const in10Pinned = !in10Right && q80x - 4 - in10Width < 0;
  const rowC1 = laneBottom + type.s + 2;
  const rowC2 = rowC1 + rowCStep * (middleBreak ? 2 : 1);

  // Row E: lane 2's labels, placed as row C places lane 1's: the middle's centred on the notch, clamped inside the
  // plot, and the 8-in-10 label 4 px right of the end cap, or left when there is no room; each moves off the plan
  // line when it would cross it, if it can clear the line by 6 px, and its knockout stops the line otherwise.
  const bar = estimate?.bar ?? null;
  const middle2Width = lineWidth(middle2Break, widths.middle2 ?? 0);
  let middle2X = bar ? clamp(x(bar.q50) - middle2Width / 2, PAD, plotRight - middle2Width) : 0;
  if (bar && planX !== null && middle2X - 3 < planX && planX < middle2X + middle2Width + 3) {
    const notch = x(bar.q50);
    const options = [planX + 6, planX - 6 - middle2Width].filter((start) => start >= PAD && start + middle2Width <= plotRight);
    if (options.length) middle2X = options.reduce((a, b) => (Math.abs(a + middle2Width / 2 - notch) <= Math.abs(b + middle2Width / 2 - notch) ? a : b));
  }
  const in102Width = widths.in102 ?? 0;
  const e80x = bar ? x(bar.q80) : 0;
  const in102Start = (right: boolean) => (right ? e80x + 4 : Math.max(0, e80x - 4 - in102Width));
  let in102Right = e80x + 4 + in102Width <= plotRight;
  if (bar && planX !== null) {
    const start = in102Start(in102Right);
    const other = in102Start(!in102Right);
    const crossed = start - 3 < planX && planX < start + in102Width + 3;
    const otherFits = other >= 0 && other + in102Width <= plotRight;
    const otherClears = other + in102Width <= planX - 6 || other >= planX + 6;
    if (crossed && otherFits && otherClears) in102Right = !in102Right;
  }
  const in102Pinned = !in102Right && e80x - 4 - in102Width < 0;
  const rowE1 = rowETop + type.s + 2;
  const rowE2 = rowE1 + rowCStep * (middle2Break ? 2 : 1);

  // The axis: the label before the last one is dropped when it comes within 8 px of the last, whose
  // tick and gridline stay.
  const lastTick = ticks[ticks.length - 1];
  const prevTick = ticks.length > 2 ? ticks[ticks.length - 2] : null;
  const dropPrev = prevTick !== null && x(prevTick) + (widths.tickPrev ?? 0) / 2 > x(lastTick) - (widths.tickLast ?? 0) - 8;

  // The tooltip covers no dot, so the pointer can move onto it and keep it (WCAG 1.4.13) and can still
  // reach every other dot: it sits above every dot within reach of its width when that fits inside the
  // card, and below them all otherwise.
  const tipLeft = tipFor ? clamp(tipFor.cx - tipBox.w / 2, 0, width - tipBox.w) : 0;
  const underTip = tipFor ? dots.filter((dot) => dot.cx + HIT >= tipLeft && dot.cx - HIT <= tipLeft + tipBox.w).map((dot) => dot.cy) : [];
  const above = tipFor ? Math.min(tipFor.cy, ...underTip) - layout.r - TIP_GAP - tipBox.h : 0;
  const tipTop = tipFor ? (above >= -tipBox.room ? above : Math.max(tipFor.cy, ...underTip) + layout.r + TIP_GAP) : 0;
  // The band between a hovered dot and its tooltip (the safe-zone pattern menus use, as Floating UI's
  // safePolygon starts where the pointer left its trigger): from the pointer's last point on its dot,
  // 8 px to each side, to the tooltip's near edge. Inside it the pointer is on its way to the tooltip,
  // so the dots it crosses don't take the tooltip unless it rests on one. A pointer moving sideways
  // along the dots leaves it within 8 px.
  const tipAbove = tipFor !== null && tipTop < tipFor.cy;
  const inBand = (px: number, py: number) => {
    if (!tipFor || hover === null || focused !== null || tipFor.key !== dots[hover]?.key || tipBox.w === 0) return false;
    const a = apex.current ?? { x: tipFor.cx, y: tipFor.cy };
    const nearY = tipAbove ? tipTop + tipBox.h : tipTop;
    const span = nearY - a.y;
    const t = (py - a.y) / span;
    if (!(span !== 0 && t >= 0 && t <= 1)) return false;
    const left = a.x - BAND + t * (tipLeft - (a.x - BAND));
    const right = a.x + BAND + t * (tipLeft + tipBox.w - (a.x + BAND));
    return px >= left && px <= right;
  };
  // Where the mouse is now decides which dot's tooltip shows.
  function track(px: number, py: number) {
    const found = nearest(px, py);
    clearTimeout(restTimer.current);
    if (found !== null && found === hover) apex.current = { x: px, y: py };
    if (inBand(px, py)) {
      clearTimeout(hideTimer.current);
      if (found !== null && found !== hover) {
        restTimer.current = setTimeout(() => {
          apex.current = { x: px, y: py };
          setDismissed(null);
          setHover(found);
        }, 100);
      }
      return;
    }
    if (found !== null) {
      clearTimeout(hideTimer.current);
      if (found !== hover) setDismissed(null);
      apex.current = { x: px, y: py };
      setHover(found);
    } else if (hover !== null) {
      hideLater();
    }
  }
  const knobLeft = planX ?? 0;
  const chevronX = plotRight - 2 + 3;

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
      onPointerLeave={(event) => {
        // A finger lifting off sends pointerleave too; a tapped dot keeps its details until the next tap.
        if (drag || event.pointerType === "touch") return;
        hideLater();
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

        {/* Row A: the lane label and the key. With lane 2, the label takes the first line and the key the second. */}
        <text
          ref={ref("lane")}
          x={0}
          y={twoLanes ? 10 + type.s * 0.35 : textBaseline}
          fontSize={type.s}
          fontWeight={600}
          opacity={twoLanes || showLaneLabel ? 1 : 0}
          className="fill-chart-text-subtle uppercase"
        >
          {laneLabel}
        </text>
        {twoLanes && (
          <g data-key-a>
            {keyAParts.map((part, index) => (
              <KeyItem
                key={index}
                part={part}
                at={placedA.at[index]}
                top={30}
                lineGap={lineGap}
                fontSize={type.s}
                glyph={glyph}
                textRef={ref(KEY_A[index])}
                breakAt={keyABreaks[index]?.at ?? null}
              />
            ))}
          </g>
        )}
        {!twoLanes && keySigned && (
          <>
            {!keyLead && <circle cx={keyStart + glyph} cy={ROW_A / 2} r={glyph} className="fill-chart-cat1-text" />}
            <text ref={ref("keySigned")} x={keyStart + glyphPart} y={textBaseline} fontSize={type.s} className="fill-chart-text">
              <Lines text={keySigned} at={signedBreak?.at ?? null} x={keyStart + glyphPart} step={lineGap} />
            </text>
          </>
        )}
        {!twoLanes && keyHollow && (
          <>
            {!keyLead && (
              <circle cx={hollowStart + glyph} cy={ROW_A / 2 + hollowY} r={glyph - 0.75} strokeWidth={1.5} className="fill-surface stroke-chart-cat1-text" />
            )}
            <text ref={ref("keyHollow")} x={hollowStart + glyphPart} y={textBaseline + hollowY} fontSize={type.s} className="fill-chart-text">
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
            y1={laneTop + 4}
            y2={laneBottom - 2}
            strokeWidth={2.5}
            className="stroke-chart-grey500"
          />
        )}

        {/* The dots, each with a surface ring so touching dots stay apart. While comparing, a dot that did not go
            with the option turns grey300 at r 3 at the same centre, so nothing reflows. */}
        {dots.map((dot) => {
          const faded = matching !== null && !matching.has(dot.key);
          const r = faded ? 3 : layout.r;
          return (
          <g key={dot.key} data-dot={dot.hollow ? "hollow" : "filled"} data-went-with={matching === null ? undefined : faded ? "no" : "yes"}>
            <circle data-dot-mark cx={dot.cx} cy={dot.cy} r={r + 2} className="fill-surface" />
            {dot.hollow ? (
              <circle
                data-dot-mark
                cx={dot.cx}
                cy={dot.cy}
                r={r - 0.75}
                strokeWidth={1.5}
                className={cx("fill-surface", faded ? "stroke-chart-grey300" : "stroke-chart-cat1-text")}
              />
            ) : (
              <circle data-dot-mark cx={dot.cx} cy={dot.cy} r={r} className={faded ? "fill-chart-grey300" : "fill-chart-cat1-text"} />
            )}
            {dot.beyond && (
              <path
                data-beyond
                d={`M ${chevronX} ${dot.cy - 3} L ${chevronX + 3} ${dot.cy} L ${chevronX} ${dot.cy + 3}`}
                fill="none"
                strokeWidth={1.5}
                className="stroke-chart-cat1-text"
              />
            )}
          </g>
          );
        })}
        {/* The opened dot's ring, in selection1, while the evidence drawer shows its records (ticket 15). */}
        {opened !== null &&
          dots
            .filter((dot) => dot.key === opened)
            .map((dot) => (
              <circle key="opened" data-opened-ring cx={dot.cx} cy={dot.cy} r={drawnR(dot.key) + 3} fill="none" strokeWidth={2} className="stroke-info-icon" />
            ))}
        {/* The hovered dot's ring, drawn after every dot so the dots stacked around it never hide part of it. */}
        {hover !== null && focused === null && dots[hover] && (
          <circle data-hover-ring cx={dots[hover].cx} cy={dots[hover].cy} r={drawnR(dots[hover].key) + 2} fill="none" strokeWidth={2} className="stroke-chart-grey500" />
        )}

        {/* Lane 2, the time estimate (ticket 26): the divider, row D, the lane and row E. */}
        {twoLanes && (
          <g data-lane2={lane2.kind}>
            <line aria-hidden="true" data-lane-divider x1={PAD} x2={plotRight} y1={rowCBottom + 8} y2={rowCBottom + 8} strokeWidth={1} className="stroke-chart-grey200" />
            {lane2.kind === "loading" && (
              <rect data-lane2-skeleton x={PAD + 0.3 * (width - 2 * PAD)} y={lane2Centre - 10} width={0.3 * (width - 2 * PAD)} height={20} rx={2} className="fill-surface-2" />
            )}
            {bar && (
              <g data-lane2-bar>
                <rect data-lane2-move x={x(bar.q25)} y={lane2Centre - 10} width={Math.max(1, x(bar.q75) - x(bar.q25))} height={20} rx={2} className="fill-primary" />
                {x(bar.q80) - x(bar.q75) >= 2 && (
                  <rect data-lane2-move data-lane2-connector x={x(bar.q75)} y={lane2Centre - 1} width={x(bar.q80) - x(bar.q75)} height={2} className="fill-chart-grey500" />
                )}
                <rect data-lane2-move data-lane2-cap x={x(bar.q80) - 1} y={lane2Centre - 6} width={2} height={12} className="fill-chart-grey500" />
                <rect data-lane2-move data-lane2-notch x={x(bar.q50) - 1.25} y={lane2Centre - 10} width={2.5} height={20} className="fill-surface" />
              </g>
            )}
            {estimate?.ghost && <Ghost points={estimate.ghost} x={x} centre={lane2Centre} />}
          </g>
        )}

        {/* The axis. */}
        <line data-axis x1={PAD} x2={plotRight} y1={axisY} y2={axisY} strokeWidth={1} className="stroke-line-strong" />
        {ticks.map((tick, index) => (
          <g key={tick}>
            <line x1={x(tick)} x2={x(tick)} y1={axisY} y2={axisY + 4} strokeWidth={1} className="stroke-line-strong" />
            <text
              ref={index === ticks.length - 1 ? ref("tickLast") : tick === prevTick ? ref("tickPrev") : undefined}
              x={x(tick)}
              y={axisY + 6 + type.s}
              textAnchor={index === 0 ? "start" : index === ticks.length - 1 ? "end" : "middle"}
              fontSize={type.s}
              opacity={tick === prevTick && dropPrev ? 0 : 1}
              data-tick-label
              className="fill-chart-text-subtle tabular-nums"
            >
              {index === ticks.length - 1 ? axisLastLabel : formatNumber(tick, { compact: false })}
            </text>
          </g>
        ))}

        {/* The plan: a line through everything, with a surface halo, and its readout in row B. */}
        {planX !== null && (
          <g data-plan-line>
            <line x1={planX} x2={planX} y1={rowA} y2={axisY} strokeWidth={4} className="stroke-surface" />
            <line x1={planX} x2={planX} y1={rowA} y2={axisY} strokeWidth={2} className="stroke-chart-grey500" />
            {showPlanWord && (
              <text
                ref={ref("plan")}
                data-readout-plan
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
            {/* Each line is its own text, anchored on its own, so a line left of the plan line ends
                exactly at the readout's edge. The spaces between them are not drawn: they keep the
                group's text the readout's words. */}
            {lines.length > 0 && (
              <g data-readout>
                {lines.map((line, index) => (
                  <Fragment key={index}>
                    {index > 0 && " "}
                    <text
                      ref={ref(READOUT_LINES[index])}
                      x={readoutX}
                      y={firstLine + index * readoutStep}
                      textAnchor={onRight ? "start" : "end"}
                      fontSize={type.s}
                      className="fill-chart-text tabular-nums"
                      style={HALO}
                    >
                      {line}
                    </text>
                  </Fragment>
                ))}
              </g>
            )}
          </g>
        )}
        {/* Row C: the statistics' labels, over the plan line, each on its knockout and with its halo. */}
        {middleLabel && stats?.q50 != null && <Knockout kind="middle" box={boxes.middle} floor={axisY - 0.5} />}
        {in10Label && stats?.q80 != null && <Knockout kind="in10" box={boxes.in10} floor={axisY - 0.5} />}
        {middleLabel && stats?.q50 != null && (
          <text ref={ref("middle")} data-row-c="middle" x={middleX} y={rowC1} fontSize={type.s} className="fill-chart-text" style={HALO}>
            <Lines text={middleLabel} at={middleBreak?.at ?? null} x={middleX} step={rowCStep} />
          </text>
        )}
        {in10Label && stats?.q80 != null && (
          <text
            ref={ref("in10")}
            data-row-c="in10"
            x={in10Right ? q80x + 4 : in10Pinned ? 0 : q80x - 4}
            y={rowC2}
            textAnchor={in10Right || in10Pinned ? "start" : "end"}
            fontSize={type.s}
            className="fill-chart-text"
            style={HALO}
          >
            {in10Label}
          </text>
        )}
        {/* Lane 2's words, over the plan line: row D's label and key, and row E's labels, each on a knockout. */}
        {twoLanes && (
          <g data-lane2-words>
            <Knockout kind="lane2" box={boxes.lane2} floor={axisY - 0.5} />
            {keyDParts.map((_, index) => (
              <Knockout key={index} kind={`keyD${index}`} box={boxes[KEY_D[index]]} floor={axisY - 0.5} />
            ))}
            <text ref={ref("lane2")} x={0} y={rowDTop + 10 + type.s * 0.35} fontSize={type.s} fontWeight={600} className="fill-chart-text-subtle uppercase">
              {lane2Shown}
            </text>
            {keyDParts.map((part, index) => (
              <KeyItem
                key={index}
                part={part}
                at={placedD.at[index]}
                top={rowDTop + 30}
                lineGap={lineGap}
                fontSize={type.s}
                glyph={glyph}
                textRef={ref(KEY_D[index])}
              />
            ))}
            {/* Row E: the solid bar's numbers, each on its knockout over the plan line, with its halo. */}
            {bar && estimate?.labels && (
              <>
                <Knockout kind="middle2" box={boxes.middle2} floor={axisY - 0.5} />
                <Knockout kind="in102" box={boxes.in102} floor={axisY - 0.5} />
                <text ref={ref("middle2")} data-row-e="middle" x={middle2X} y={rowE1} fontSize={type.s} className="fill-chart-text" style={HALO}>
                  <Lines text={estimate.labels.middle} at={middle2Break?.at ?? null} x={middle2X} step={rowCStep} />
                </text>
                <text
                  ref={ref("in102")}
                  data-row-e="in10"
                  x={in102Right ? e80x + 4 : in102Pinned ? 0 : e80x - 4}
                  y={rowE2}
                  textAnchor={in102Right || in102Pinned ? "start" : "end"}
                  fontSize={type.s}
                  className="fill-chart-text"
                  style={HALO}
                >
                  {estimate.labels.in10}
                </text>
              </>
            )}
          </g>
        )}

      </svg>

      {/* Lane 2's messages, after the drawing so they are read with the chart: an abstention or an error over the
          lane and row E, as HTML so it wraps, with the plan line passing behind it; and, while comparing with an
          option too few went with, row E's sentence in place of its labels. */}
      {lane2?.kind === "message" && (
        <div
          data-lane2-message={lane2.tone}
          className="absolute flex items-start gap-2 bg-surface p-1 text-chart-text"
          style={{ left: PAD, top: lane2Top, width: width - 2 * PAD, minHeight: 80, fontSize: type.m }}
        >
          {lane2.tone === "error" ? (
            <CircleX aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-error-icon" />
          ) : (
            <CircleDashed aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-line-strong" />
          )}
          <p className="min-w-0">{lane2.text}</p>
        </div>
      )}
      {estimate && !estimate.bar && estimate.note && (
        <p data-lane2-note className="absolute text-chart-text" style={{ left: PAD, top: rowETop + 2, width: width - 2 * PAD, fontSize: type.s }}>
          {estimate.note}
        </p>
      )}

      {/* The widest readouts, drawn hidden in the readout's type so its lines can be chosen from them, and lane 2's
          full label, so the chart knows whether it fits. */}
      <svg aria-hidden="true" width={0} height={0} className="pointer-events-none absolute top-0 left-0 overflow-hidden" style={{ visibility: "hidden" }}>
        {twoLanes && (
          <text ref={ref("lane2Full")} fontSize={type.s} fontWeight={600} className="uppercase">
            {lane2Label}
          </text>
        )}
        {readoutWidest.flatMap((widest, index) =>
          [widest.one, ...widest.lines].map((text, part) => (
            <text key={widestKeys[index][part]} ref={ref(widestKeys[index][part])} fontSize={type.s} className="tabular-nums">
              {text}
            </text>
          )),
        )}
      </svg>

      {/* The plan line as a slider: dragged by its knob or within 8 px of the line, moved by the arrow
          keys, or set by clicking the axis row. Only the knob stops the page from scrolling under a thumb. */}
      {plan !== null && planX !== null && (
        <div
          ref={knobRef}
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
          style={{ left: knobLeft, top: rowA, transform: "translateX(-50%)" }}
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
          onPointerEnter={() => {
            clearTimeout(hideTimer.current);
            clearTimeout(restTimer.current);
          }}
          onPointerLeave={(event) => {
            if (event.pointerType === "touch") return;
            // Back in the band toward its dot, the tooltip keeps its dot; on another dot outside it, that
            // dot takes the tooltip; elsewhere it hides after 100 ms (WCAG 1.4.13).
            const { px, py } = local(event);
            track(px, py);
          }}
          // Its width is its content's, up to 240 px, so it never shrinks to the room left of the chart's edge.
          className="absolute z-10 w-max max-w-[240px] animate-fade-in cursor-text select-text rounded-sm border-[0.5px] border-chart-grey200 bg-surface px-3 py-2 shadow-popover"
          style={{ left: tipLeft, top: tipTop, fontSize: type.s }}
        >
          {/* A STEP reference breaks at its spaces first, as everywhere on the page (MonoWords). */}
          <p className="font-semibold text-chart-text">{tipFor.tip.mono ? <MonoWords text={tipFor.tip.header} /> : tipFor.tip.header}</p>
          <p className="font-bold text-chart-text tabular-nums" style={{ fontSize: type.m }}>
            {tipFor.tip.number}
          </p>
          <p className="text-chart-text-subtle">{tipFor.tip.line}</p>
          {onOpen && openHint && !tapped && <p className="mt-1 text-chart-text-subtle">{openHint}</p>}
          {/* The tooltip is hidden from screen readers, so its button leaves the tab order: a keyboard opens
              the focused dot with Enter, and the table twin's buttons are the full-size way in. */}
          {onOpen && openLabel && tapped && shown !== null && (
            <button
              type="button"
              tabIndex={-1}
              data-open-records
              onClick={() => {
                const element = dotRefs.current[shown];
                if (element) onOpen(dots[shown].key, element);
              }}
              className="mt-2 inline-flex min-h-6 items-center rounded-pill border border-primary px-3 text-small font-bold text-primary hover:bg-tint"
            >
              {openLabel}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
