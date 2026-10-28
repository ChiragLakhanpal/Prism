// The evidence trail (DESIGN.md section 5; the 23 brief, section 4): a project's reports, events and records in
// three lanes, Why, How and What, on one time axis. Circles are reports, diamonds events and squares records; the
// How lane's band row shows the ISRs' ratings of progress, lighter for better, each band naming its rating; a
// dashed line, in its card's state colour, joins two reports that disagree, with a 24 px chip that reads
// "2 reports disagree". There are no gridlines, so dashes always mean a disagreement.
//
// As the range chart does (ticket 12), the drawn layer is one svg with role="img", named by a hidden paragraph
// that holds the alt text the server wrote; the items sit over it as links in one group with one tab stop, because
// children of role="img" are hidden from assistive technology. Left and Right move in date order across the lanes,
// Up and Down to the nearest item in time in the lane above or below, Home and End to the ends, and Enter opens
// the item's source in the evidence drawer. An item shows its tooltip on hover or focus, and Escape hides it.
//
// The chart is 352 px tall in every state. Every date and count comes from the payload: the chart only places it.
import { Info, TriangleAlert } from "lucide-react";
import { useEffect, useId, useLayoutEffect, useMemo, useRef, useState, type KeyboardEvent, type MouseEvent, type ReactNode } from "react";
import { copy } from "../copy";
import { cx } from "../lib/cx";
import { evidenceHref } from "../lib/evidence";
import { formatDate } from "../lib/format";
import {
  AXIS_Y,
  BAND_ROW,
  HEIGHT,
  LANES,
  PAD,
  ROWS,
  axisFor,
  bandLabelFits,
  bandLabels,
  capitalize,
  chartType,
  itemName,
  joinNames,
  lineFor,
  markLabel,
  markY,
  othersOf,
  placeLabels,
  scaleFor,
  shortName,
  yearX,
  type BandItem,
  type Box,
  type Item,
  type Lane,
  type Line,
  type MarkItem,
  type Placed,
  type Timeline,
} from "../lib/timeline";
import { SegmentText } from "./SegmentText";

const words = copy.timeline;
// Rating bands (DESIGN.md section 6): chart greys, lighter for better, and white words on the two darkest.
const BAND_LOOK: Record<string, { fill: string; text: string }> = {
  "Highly Satisfactory": { fill: "fill-surface", text: "fill-chart-grey500" },
  Satisfactory: { fill: "fill-chart-grey100", text: "fill-chart-grey500" },
  "Moderately Satisfactory": { fill: "fill-chart-grey200", text: "fill-chart-grey500" },
  "Moderately Unsatisfactory": { fill: "fill-chart-grey300", text: "fill-chart-grey500" },
  Unsatisfactory: { fill: "fill-chart-grey400", text: "fill-surface" },
  "Highly Unsatisfactory": { fill: "fill-chart-grey500", text: "fill-surface" },
};
const HIT = 24;
const CHIP_ICON = 16;
export type LineState = "info" | "warning";

// One canvas for every label's width, in the chart's own fonts. Tracking is in em, added after each character as the
// browser draws it.
let canvas: HTMLCanvasElement | null = null;
function measure(text: string, size: number, weight = 400, mono = false, tracking = 0): number {
  canvas ??= typeof document !== "undefined" ? document.createElement("canvas") : null;
  const context = canvas?.getContext("2d");
  if (!context) return text.length * size * (0.6 + tracking);
  context.font = `${weight} ${size}px ${mono ? '"Roboto Mono"' : '"Open Sans"'}`;
  return context.measureText(text).width + text.length * size * tracking;
}

// A lane label draws in the chart label's step (app.css, --text-chart-label: 12 px, 600, +0.02em), whatever the
// chart's own sizes, so its box is measured in the same (ticket 99, from ticket 91's verify).
const LANE_LABEL = { size: 12, weight: 600, tracking: 0.02 };

// The fonts arrive after the first paint: measure again then.
function useFontsReady(): number {
  const [ready, setReady] = useState(0);
  useEffect(() => {
    let live = true;
    document.fonts?.ready.then(() => live && setReady((n) => n + 1));
    return () => {
      live = false;
    };
  }, []);
  return ready;
}

function Shape({ item, x, y, active, hovered }: { item: MarkItem; x: number; y: number; active: boolean; hovered: boolean }) {
  const replaced = item.kind === "report" && Boolean(item.replaced_by) && !active;
  const look = cx(
    "stroke-2",
    active ? "fill-primary stroke-primary" : "fill-surface",
    !active && (replaced ? "stroke-chart-grey300" : "stroke-chart-grey500"),
  );
  const ring = "fill-none stroke-surface stroke-2";
  const outline = hovered && !active ? <ShapeOutline item={item} x={x} y={y} /> : null;
  if (item.kind === "report") {
    return (
      <g data-shape="circle">
        <circle cx={x} cy={y} r={8} className={ring} />
        <circle cx={x} cy={y} r={6} className={look} />
        {outline}
      </g>
    );
  }
  if (item.kind === "event") {
    const r = 6;
    const points = `${x},${y - r} ${x + r},${y} ${x},${y + r} ${x - r},${y}`;
    return (
      <g data-shape="diamond">
        <polygon points={`${x},${y - r - 2} ${x + r + 2},${y} ${x},${y + r + 2} ${x - r - 2},${y}`} className={ring} />
        <polygon points={points} className={look} />
        {outline}
      </g>
    );
  }
  const side = item.kind === "group" ? 14 : 10;
  return (
    <g data-shape="square">
      <rect x={x - side / 2 - 2} y={y - side / 2 - 2} width={side + 4} height={side + 4} className={ring} />
      <rect x={x - side / 2} y={y - side / 2} width={side} height={side} className={look} />
      {outline}
    </g>
  );
}

// The hover look: a 2px grey500 ring 2 px outside the shape.
function ShapeOutline({ item, x, y }: { item: MarkItem; x: number; y: number }) {
  const ring = "fill-none stroke-chart-grey500 stroke-2";
  if (item.kind === "report") return <circle cx={x} cy={y} r={10} className={ring} />;
  if (item.kind === "event") return <polygon points={`${x},${y - 10} ${x + 10},${y} ${x},${y + 10} ${x - 10},${y}`} className={ring} />;
  const side = (item.kind === "group" ? 14 : 10) + 8;
  return <rect x={x - side / 2} y={y - side / 2} width={side} height={side} className={ring} />;
}

type Tip = { header: string; main: string; line: string; mono?: boolean };

function tipFor(item: Item, items: Item[]): Tip {
  // A date in a tooltip stays on one line: "May 4, 2023", never "May / 4, 2023".
  const long = (iso: string) => formatDate(iso).replace(/ /g, "\u00a0");
  if (item.kind === "report") {
    if (item.type === "isr") {
      // An ISR whose rating get_disagreements did not give shows its date, as another report does.
      if (!item.rating) return { header: markLabel(item), main: long(item.date), line: words.tip.written.replace("{written}", copy.disagreement.written.isr) };
      return { header: markLabel(item), main: item.rating, line: words.tip.isr.replace("{date}", long(item.date)) };
    }
    const written = (copy.disagreement.written as Record<string, string>)[
      item.type === "icr_review" || item.type === "ppar" ? "ieg" : item.type === "pad" ? "pad" : item.type === "icr" ? "icr" : "isr"
    ];
    const against = othersOf(item, items);
    const line = item.replaced_by
      ? words.tip.replacedBy.replace("{date}", long(item.replaced_by.date))
      : against.length
        ? words.tip.writtenDisagrees.replace("{written}", written).replace("{other}", joinNames(against))
        : words.tip.written.replace("{written}", written);
    return { header: item.document_type, main: long(item.date), line };
  }
  if (item.kind === "event") {
    const source = item.source.type === "isr" ? shortName({ type: "isr", sequence: item.source.sequence }) : shortName({ type: item.source.type, sequence: null });
    return { header: markLabel(item), main: long(item.date), line: words.tip.from.replace("{source}", source) };
  }
  if (item.kind === "record") return { header: item.step_reference, main: long(item.date), line: words.tip.contract, mono: true };
  if (item.kind === "group") return { header: markLabel(item), main: String(item.year), line: words.tip.group };
  if (item.kind === "band") {
    return {
      header: item.first === item.last ? words.bandItemOne.replace("{first}", String(item.first)) : words.bandItem.replace("{first}", String(item.first)).replace("{last}", String(item.last)),
      main: item.rating,
      line: words.tip.band.replace("{start}", long(item.date)).replace("{end}", long(item.end)),
    };
  }
  const lean = item.sides.find((side) => side.leaned);
  return {
    header: words.chip,
    main: capitalize(words.sides.replace("{side1}", shortName(item.sides[0])).replace("{side2}", shortName(item.sides[1]))),
    line: lean ? words.tip.leans.replace("{lean}", shortName(lean)) : "",
  };
}

// Where each item's target sits over the svg, for the overlay and the tooltip.
type Target = { item: Item; box: Box; cx: number; cy: number };

export function EvidenceTrail({
  data,
  width,
  openId,
  lineStates = {},
  onOpen,
  lanesEmpty = {},
  onCodes,
}: {
  data: Timeline;
  width: number;
  // The evidence id the drawer shows, which takes the active look.
  openId: string | null;
  // A disagreement's state when an answer open on the page depends on it; info otherwise.
  lineStates?: Record<string, LineState>;
  onOpen: (item: Item, element: HTMLElement) => void;
  lanesEmpty?: Partial<Record<Lane, boolean>>;
  // The ratings whose bands show their code, so the Note spells out only those, before the page paints.
  onCodes?: (ratings: string[]) => void;
}) {
  const altId = useId();
  const helpId = useId();
  const fonts = useFontsReady();
  const type = chartType(width);
  const items = data.items;
  const asOf = data.asked_as_of;
  const showLines = data.disagreements.status === "ok";

  const layout = useMemo(() => {
    const axis = axisFor(items, asOf);
    const x = scaleFor(axis, width);
    const laneLabelBoxes: Box[] = LANES.map((lane) => {
      const w = measure(words.lane[lane].toUpperCase(), LANE_LABEL.size, LANE_LABEL.weight, false, LANE_LABEL.tracking);
      return { x0: PAD, x1: PAD + w, y0: ROWS[lane].label, y1: ROWS[lane].label + 24 };
    });
    const chipWidth = 8 + CHIP_ICON + 4 + measure(words.chip, type.s, 600) + 8;
    const lines: Line[] = [];
    if (showLines) {
      for (const item of items) {
        if (item.kind !== "disagreement") continue;
        lines.push(lineFor(item, x, chipWidth, laneLabelBoxes, width, lines.map((line) => line.chip)));
      }
    }
    const marks = items.filter((item): item is MarkItem => item.kind !== "band" && item.kind !== "disagreement");
    const labelHeight = type.s * 1.25;
    const placed = placeLabels(
      marks.map((item) => {
        const text = markLabel(item);
        return { id: item.id, lane: item.lane, x: x(item.date), text, width: measure(text, type.s, 400, item.kind === "record") };
      }),
      lines.map((line) => line.chip),
      width,
      labelHeight,
      lines.flatMap((line) => line.points),
    );
    const bands = items.filter((item): item is BandItem => item.kind === "band").map((band) => {
      const x0 = x(band.date);
      const x1 = Math.max(x(band.end), x0 + 8);
      const forms = bandLabels(band);
      const form = forms.findIndex((text) => bandLabelFits(text, measure(text, type.s), x1 - x0));
      // The last two forms name the rating by its code, which the Note spells out.
      return { band, x0, x1, label: form >= 0 ? forms[form] : null, coded: form >= 2 };
    });
    const targets: Target[] = [];
    for (const item of items) {
      if (item.kind === "band") {
        const found = bands.find((one) => one.band.id === item.id)!;
        const y0 = ROWS.how.band!;
        targets.push({ item, box: { x0: found.x0, x1: found.x1, y0, y1: y0 + BAND_ROW }, cx: (found.x0 + found.x1) / 2, cy: y0 });
      } else if (item.kind === "disagreement") {
        const line = lines.find((one) => one.id === item.id);
        if (line) targets.push({ item, box: line.chip, cx: line.cx, cy: line.chip.y0 });
      } else {
        const cx = x(item.date);
        const cy = markY(item.lane);
        targets.push({ item, box: { x0: cx - HIT / 2, x1: cx + HIT / 2, y0: cy - HIT / 2, y1: cy + HIT / 2 }, cx, cy: cy - 8 });
      }
    }
    return { axis, x, lines, placed, bands, targets, marks, chipWidth, laneLabelBoxes };
    // fonts: measured again once the web fonts arrive.
  }, [items, asOf, width, type.s, showLines, fonts]);

  const coded = [...new Set(layout.bands.filter((band) => band.coded).map((band) => band.band.rating))].join("|");
  useLayoutEffect(() => onCodes?.(coded ? coded.split("|") : []), [coded]);

  const [active, setActive] = useState(0);
  const [focused, setFocused] = useState<number | null>(null);
  const [hovered, setHovered] = useState<number | null>(null);
  const [dismissed, setDismissed] = useState<number | null>(null);
  const refs = useRef<(HTMLAnchorElement | null)[]>([]);
  const hideTimer = useRef<ReturnType<typeof setTimeout>>(undefined);
  const targets = layout.targets;
  const total = targets.length;
  const shown = hovered ?? focused;
  const tipIndex = shown !== null && shown !== dismissed ? shown : null;
  const tipRef = useRef<HTMLDivElement>(null);
  const [tipBox, setTipBox] = useState<{ width: number; height: number }>({ width: 0, height: 0 });
  useLayoutEffect(() => {
    const element = tipRef.current;
    if (!element) return;
    const next = { width: element.offsetWidth, height: element.offsetHeight };
    setTipBox((now) => (now.width === next.width && now.height === next.height ? now : next));
  });

  // Keys inside the group (section 8.2).
  const move = (to: number) => {
    const next = Math.max(0, Math.min(total - 1, to));
    setActive(next);
    setDismissed(null);
    refs.current[next]?.focus();
  };
  const laneOf = (item: Item): Lane | null => item.lane;
  const onKeyDown = (event: KeyboardEvent<HTMLAnchorElement>, index: number) => {
    const item = targets[index].item;
    if (event.key === "ArrowRight") move(index + 1);
    else if (event.key === "ArrowLeft") move(index - 1);
    else if (event.key === "Home") move(0);
    else if (event.key === "End") move(total - 1);
    else if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      const lane = laneOf(item);
      if (lane) {
        const step = event.key === "ArrowDown" ? 1 : -1;
        for (let at = LANES.indexOf(lane) + step; at >= 0 && at < LANES.length; at += step) {
          const candidates = targets.map((target, k) => ({ target, k })).filter(({ target }) => laneOf(target.item) === LANES[at]);
          if (candidates.length) {
            const near = candidates.reduce((best, one) => (Math.abs(one.target.cx - targets[index].cx) < Math.abs(best.target.cx - targets[index].cx) ? one : best));
            move(near.k);
            break;
          }
        }
      }
    } else if (event.key === " ") {
      refs.current[index]?.click();
    } else if (event.key === "Escape" && tipIndex !== null) {
      // The tooltip first; a second Escape reaches the drawer.
      setDismissed(index);
      event.preventDefault();
      event.stopPropagation();
      return;
    } else return;
    event.preventDefault();
  };

  const tip = tipIndex !== null ? targets[tipIndex] : null;
  const tipContent = tip ? tipFor(tip.item, items) : null;
  const tipLeft = tip ? Math.min(Math.max(tip.cx - tipBox.width / 2, 0), width - tipBox.width) : 0;
  const above = tip ? tip.box.y0 - 8 - tipBox.height : 0;
  const tipTop = tip ? (above >= 0 ? above : tip.box.y1 + 8) : 0;

  const x = layout.x;
  const placedFor = (id: string) => layout.placed.find((one) => one.id === id) as Placed | undefined;
  const lineState = (id: string): LineState => lineStates[id] ?? "info";

  return (
    <div
      data-evidence-trail
      className="relative select-none"
      style={{ width, height: HEIGHT }}
      onPointerLeave={() => {
        clearTimeout(hideTimer.current);
        hideTimer.current = setTimeout(() => setHovered(null), 100);
      }}
    >
      <p id={altId} className="sr-only" data-chart-alt>
        <SegmentText segments={data.alt} plain />
      </p>
      <svg role="img" aria-labelledby={altId} width={width} height={HEIGHT} className="block overflow-visible" data-chart-drawing style={{ fontSize: type.s }}>
        {LANES.map((lane, index) => {
          const rows = ROWS[lane];
          const y = markY(lane);
          const box = layout.laneLabelBoxes[index];
          return (
            <g key={lane} data-lane={lane}>
              {/* data-label-width: the width its box was measured at, which keeps a disagreement chip off it. */}
              <text x={PAD} y={rows.label + 16} data-label-width={box.x1 - box.x0} className="fill-chart-text-subtle text-chart-label uppercase">
                {words.lane[lane]}
              </text>
              <line x1={PAD} x2={width - PAD} y1={y} y2={y} className="stroke-chart-grey200" strokeWidth={1} />
              {lanesEmpty[lane] && (
                <text x={PAD} y={rows.rowA + 14} className="fill-chart-text-subtle">
                  {words.laneEmpty[lane]}
                </text>
              )}
              {lane !== "what" && <line x1={PAD} x2={width - PAD} y1={rows.bottom + 8} y2={rows.bottom + 8} className="stroke-line" strokeWidth={1} />}
            </g>
          );
        })}
        {/* The How lane's band row: one band per run of equal ratings. */}
        <g data-band-row>
          {layout.bands.length === 0 && (
            <text x={PAD} y={ROWS.how.band! + 16} className="fill-chart-text-subtle">
              {/* When get_disagreements did not answer, Strata could not read the ratings: that is not having none. */}
              {data.disagreements.status === "failed" ? words.ratingsFailed : words.noRatings}
            </text>
          )}
          {layout.bands.map(({ band, x0, x1, label }) => {
            const look = BAND_LOOK[band.rating] ?? BAND_LOOK.Satisfactory;
            const isActive = openId === band.evidence_id;
            const index = targets.findIndex((target) => target.item.id === band.id);
            return (
              <g key={band.id} data-band={band.rating}>
                <rect x={x0} y={ROWS.how.band!} width={x1 - x0} height={BAND_ROW} rx={2} className={cx(look.fill, "stroke-line-strong")} strokeWidth={1} />
                {isActive && <rect x={x0 + 1.5} y={ROWS.how.band! + 1.5} width={x1 - x0 - 3} height={BAND_ROW - 3} rx={1} className="fill-none stroke-primary stroke-2" />}
                {hovered === index && !isActive && <rect x={x0 - 2} y={ROWS.how.band! - 2} width={x1 - x0 + 4} height={BAND_ROW + 4} rx={3} className="fill-none stroke-chart-grey500 stroke-2" />}
                {label && (
                  <text x={(x0 + x1) / 2} y={ROWS.how.band! + 16} textAnchor="middle" className={look.text} data-band-label>
                    {label}
                  </text>
                )}
              </g>
            );
          })}
        </g>
        {/* The as-of date's reference line, behind the lines and the marks, so a mark on that date stays whole. Its
            label sits at the right of the What lane's label row, which no dashed line or chip reaches: a disagreement
            joins two reports, reports sit only in the Why and How lanes, and two ISRs never form one. */}
        {asOf && (
          <g data-as-of>
            <line x1={width - PAD} x2={width - PAD} y1={0} y2={AXIS_Y} className="stroke-chart-grey300" strokeWidth={3} />
            <text x={width - PAD - 6} y={ROWS.what.label + 16} textAnchor="end" className="fill-chart-text-subtle text-chart-label uppercase">
              {words.asOf.replace("{date}", formatDate(asOf, { style: "table" }))}
            </text>
          </g>
        )}
        {/* The disagreement lines, under the marks. */}
        {layout.lines.map((line) => (
          <path
            key={line.id}
            d={line.path}
            data-disagreement-line={lineState(line.id)}
            className={cx("fill-none stroke-2", lineState(line.id) === "warning" ? "stroke-warning-icon" : "stroke-info-icon")}
            strokeDasharray="6 4"
            strokeLinecap="round"
          />
        ))}
        {layout.marks.map((item) => {
          const index = targets.findIndex((target) => target.item.id === item.id);
          return <Shape key={item.id} item={item} x={x(item.date)} y={markY(item.lane)} active={openId === item.evidence_id} hovered={hovered === index} />;
        })}
        {layout.marks.map((item) => {
          const placed = placedFor(item.id);
          if (!placed || "dropped" in placed) return null;
          const replaced = item.kind === "report" && Boolean(item.replaced_by);
          return (
            <g key={item.id}>
              {/* The label's surface knockout (DESIGN.md section 6): a line that must pass a label goes behind it. It
                  stays inside the label's text row, so it never cuts the band row's edge below row B. */}
              <rect x={placed.box.x0 - 2} y={placed.box.y0} width={placed.box.x1 - placed.box.x0 + 4} height={placed.box.y1 - placed.box.y0} className="fill-surface" data-label-knockout />
              <text
                x={placed.x}
                y={placed.y}
                textAnchor={placed.anchor}
                dominantBaseline="central"
                data-mark-label={item.id}
                className={cx("stroke-surface stroke-[3px] [paint-order:stroke]", replaced ? "fill-chart-text-subtle" : "fill-chart-text", item.kind === "record" && "font-mono")}
              >
                {placed.text}
              </text>
            </g>
          );
        })}
        {/* The time axis: no title, ticks on whole years, no gridlines. */}
        <g data-axis>
          <line x1={PAD} x2={width - PAD} y1={AXIS_Y} y2={AXIS_Y} className="stroke-line-strong" strokeWidth={1} />
          {layout.axis.ticks.map((year) => {
            const at = yearX(year, x);
            // A year centred on its tick would run off the drawing near an edge, as the last one does when the
            // as-of date falls on January 1: there it ends, or starts, at its tick.
            const half = measure(String(year), type.s) / 2;
            const anchor = at + half > width ? "end" : at - half < 0 ? "start" : "middle";
            return (
              <g key={year}>
                <line x1={at} x2={at} y1={AXIS_Y} y2={AXIS_Y + 4} className="stroke-line-strong" strokeWidth={1} />
                <text x={at} y={AXIS_Y + 20} textAnchor={anchor} className="fill-chart-text-subtle tabular-nums" data-tick>
                  {String(year)}
                </text>
              </g>
            );
          })}
        </g>
      </svg>

      <p id={helpId} className="sr-only">
        {words.help}
      </p>
      <div role="group" aria-label={words.group(String(total), data.project.project_id)} aria-describedby={helpId} className="pointer-events-none absolute inset-0">
        {targets.map((target, index) => {
          const item = target.item;
          const chip = item.kind === "disagreement";
          const state = chip ? lineState(item.id) : "info";
          const isActive = openId === item.evidence_id;
          return (
            <a
              key={item.id}
              ref={(element) => {
                refs.current[index] = element;
              }}
              href={evidenceHref(item.evidence_id)}
              aria-label={itemName(item, index, total, items)}
              aria-current={isActive ? "true" : undefined}
              tabIndex={index === active ? 0 : -1}
              data-item={item.id}
              data-item-kind={item.kind}
              onFocus={() => {
                setFocused(index);
                setActive(index);
                setDismissed(null);
              }}
              onBlur={() => setFocused(null)}
              onPointerEnter={() => {
                clearTimeout(hideTimer.current);
                setHovered(index);
                setDismissed(null);
              }}
              onKeyDown={(event) => onKeyDown(event, index)}
              onClick={(event: MouseEvent<HTMLAnchorElement>) => {
                if (event.metaKey || event.ctrlKey || event.shiftKey || event.button !== 0) return;
                event.preventDefault();
                setActive(index);
                onOpen(item, event.currentTarget);
              }}
              className={cx(
                "pointer-events-auto absolute",
                chip
                  ? cx(
                      "inline-flex items-center gap-1 rounded-pill border px-2 text-small font-semibold whitespace-nowrap",
                      state === "warning" ? "border-warning-icon text-warning" : "border-info-icon text-info",
                      // Open in the drawer: the active list item's look, a tint with a 1px inset in the state colour.
                      isActive
                        ? state === "warning"
                          ? "bg-tint shadow-[inset_0_0_0_1px_var(--color-warning-icon)]"
                          : "bg-tint shadow-[inset_0_0_0_1px_var(--color-info-icon)]"
                        : hovered === index
                          ? state === "warning"
                            ? "bg-warning-bg"
                            : "bg-info-bg"
                          : "bg-surface",
                    )
                  : "rounded-xs",
              )}
              style={{
                left: target.box.x0,
                top: target.box.y0,
                width: target.box.x1 - target.box.x0,
                height: target.box.y1 - target.box.y0,
                ...(chip ? { fontSize: type.s } : {}),
              }}
            >
              {chip && (
                <>
                  {state === "warning" ? (
                    <TriangleAlert aria-hidden="true" className="size-4 shrink-0 text-warning-icon" />
                  ) : (
                    <Info aria-hidden="true" className="size-4 shrink-0 text-info-icon" />
                  )}
                  <span aria-hidden="true">{words.chip}</span>
                </>
              )}
            </a>
          );
        })}
      </div>

      {tip && tipContent && (
        <div
          ref={tipRef}
          aria-hidden="true"
          data-trail-tooltip
          onPointerEnter={() => clearTimeout(hideTimer.current)}
          className="pointer-events-auto absolute z-10 w-max max-w-[240px] animate-fade-in rounded-sm border-[0.5px] border-chart-grey200 bg-surface px-3 py-2 shadow-popover"
          style={{ left: tipLeft, top: tipTop, fontSize: type.s }}
        >
          <p className={cx("font-semibold text-chart-text", tipContent.mono && "font-mono [overflow-wrap:anywhere]")}>{tipContent.header}</p>
          <p className="font-bold text-chart-text tabular-nums" style={{ fontSize: type.m }}>
            {tipContent.main}
          </p>
          {tipContent.line && <p className="text-chart-text-subtle">{tipContent.line}</p>}
        </div>
      )}
    </div>
  );
}

// The shapes a subtitle names, inline with its words, hidden from screen readers.
export function Glyph({ kind }: { kind: "report" | "event" | "record" }): ReactNode {
  return (
    <svg aria-hidden="true" width={12} height={12} viewBox="0 0 12 12" className="mx-0.5 inline-block align-[-1px]">
      {kind === "report" && <circle cx={6} cy={6} r={4.5} className="fill-surface stroke-chart-grey500 stroke-2" />}
      {kind === "event" && <polygon points="6,1 11,6 6,11 1,6" className="fill-surface stroke-chart-grey500 stroke-2" />}
      {kind === "record" && <rect x={2} y={2} width={8} height={8} className="fill-surface stroke-chart-grey500 stroke-2" />}
    </svg>
  );
}
