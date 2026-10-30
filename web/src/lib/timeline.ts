// A project's timeline (ticket 23): GET /api/projects/{pid}/timeline's answer (src/strata/server/timeline.py), the
// words each item is named by, and the chart's layout: where each mark, band, line and label sits at a width. The
// server orders the items as the arrow keys and the table follow them and writes the finding and the alt text;
// the page computes no number, it only places what the payload holds.
import { copy } from "../copy";
import { formatDate } from "./format";

export type Lane = "why" | "how" | "what";

export type Side = {
  item_id: string;
  evidence_id: string;
  assertion_id: string;
  type: string;
  sequence: number | null;
  document_type: string | null;
  paragraph: string | null;
  made_at: string;
  public_from: string;
  lane: Lane;
  doc_key: string | null;
  leaned: boolean;
};

type Base = { id: string; date: string; public_from: string; evidence_id: string };
export type ReportItem = Base & {
  kind: "report";
  type: string;
  lane: Lane;
  document_id: string;
  document_type: string;
  report_number: string | null;
  version: number | null;
  doc_key: string | null;
  sequence: number | null;
  rating: string | null;
  replaced_by: { evidence_id: string; date: string } | null;
  reissued: boolean;
  disagrees_with?: string[];
};
export type EventItem = Base & { kind: "event"; type: string; lane: "how"; source: { type: string; sequence: number | null; date: string | null } };
export type RecordItem = Base & { kind: "record"; type: "contract"; lane: "what"; step_reference: string; signed_amount_usd: string | null };
export type GroupItem = Base & { kind: "group"; type: "contracts"; lane: "what"; year: number; count: number };
export type BandItem = Base & { kind: "band"; lane: "how"; end: string; rating: string; first: number; last: number; count: number };
// Several reports of one kind on one side of a line: "13 ISRs", or "ISR 7" when there is one.
export type ReportKind = { type: string; count: number; sequence: number | null };
// The pairs a dashed line stands for (ticket 136): one report, its anchor, against one or more others about one fact.
// Every count is the server's; the page only names them.
export type Group = {
  count: number;
  disagreement_ids: string[];
  anchor_side: "earlier" | "later";
  anchor_item_id: string;
  anchor_reports: ReportKind[];
  other_reports: ReportKind[];
  reports: number;
  lean: "anchor" | "others" | null;
};
export type DisagreementItem = Base & {
  kind: "disagreement";
  lane: null;
  disagreement_id: string;
  attribute: string;
  rule_id: string | null;
  sides: [Side, Side];
  after: string;
  // A line on the chart has its group; a pair in the table has none.
  group?: Group;
};
export type MarkItem = ReportItem | EventItem | RecordItem | GroupItem;
export type Item = MarkItem | BandItem | DisagreementItem;

export type Segment = { text: string } | { number: number; capital?: boolean } | { year: number } | { date: string };

export type RecordSide = {
  record: "plan" | "contract_awards" | "award_notice";
  form: string;
  field_name: string;
  value: string;
  value_form: string;
  made_at: string;
  public_from: string;
  evidence_id: string;
  leaned: boolean;
};

export type RecordDisagreement = {
  id: string;
  evidence_id: string;
  disagreement_id: string;
  step_reference: string;
  attribute: string;
  rule_id: string | null;
  date: string;
  public_from: string;
  sides: RecordSide[];
};

export type Timeline = {
  project: { project_id: string; project_name: string; display_name: string; status: string | null };
  as_of: string;
  asked_as_of: string | null;
  view: string;
  items: Item[];
  table: Item[];
  ratings: { attribute: string; field_name: string; first_rating: string; last_rating: string; direction: string; isr_count: number } | null;
  // count: the dashed lines; pairs: the pairs of reports the table lists (ticket 136).
  disagreements: { status: "ok" | "hidden" | "failed"; count: number; pairs: number };
  // Ticket 132: where a package's records disagree (a plan row, the contract awards, an award notice), which no dashed
  // line joins, the newest first. A recording made before the ticket may lack it.
  records_disagree?: RecordDisagreement[];
  // How many there are, as the route counts them, for the list's count line and its Show all.
  records_disagree_count?: number;
  // The state a dashed line takes when no answer or draft open on the page depends on it: config/project_page.toml's
  // [timeline] disagreement_line_state (the 23 brief, section 10), "info" unless it is switched back to "warning".
  disagreement_line_state: "info" | "warning";
  rejected: { count: number } | null;
  counts: Record<Lane, number>;
  finding: Segment[];
  alt: Segment[];
  sources: string[];
  data_through: string | null;
};

export const LANES: Lane[] = ["why", "how", "what"];

const words = copy.timeline;
const fill = (template: string, values: Record<string, string | number | null | undefined>) =>
  template.replace(/\{(\w+)\}/g, (slot, name: string) => (values[name] === undefined || values[name] === null ? slot : String(values[name])));
const long = (iso: string) => formatDate(iso);

// A report's label on the chart: "ISR 7", "ICR Review, replaced", "ICR Review, re-issued".
export function markLabel(item: MarkItem): string {
  if (item.kind === "group") return words.contracts(String(item.count));
  if (item.kind === "record") return fill(words.label.contract, { reference: item.step_reference });
  if (item.kind === "event") return words.label[item.type] ?? item.type;
  const base = fill(words.label[item.type] ?? words.label.other, { sequence: item.sequence });
  if (item.replaced_by) return fill(words.replaced, { label: base });
  if (item.reissued) return fill(words.reissued, { label: base });
  return base;
}

// An item's full name in the table and the list.
export function fullLabel(item: Item): string {
  if (item.kind === "report") {
    const base = fill(words.full[item.type] ?? words.full.other, { sequence: item.sequence });
    return item.replaced_by ? fill(words.replaced, { label: base }) : item.reissued ? fill(words.reissued, { label: base }) : base;
  }
  if (item.kind === "band") return bandItem(item);
  if (item.kind === "disagreement") return item.group ? pillText(item) : pairLabel(item);
  return markLabel(item);
}

// What the reports disagree about: "Overall risk".
export function factName(attribute: string): string {
  return words.fact[attribute] ?? words.factOther;
}

// One side of a line's reports: "the PAD", "ISR 7", "13 ISRs", "the ICR and 2 ICR Reviews".
export function reportsName(kinds: ReportKind[]): string {
  return joinNames(kinds.map((kind) => (kind.count === 1 ? shortName(kind) : fill(words.server.plural[kind.type] ?? words.server.plural.other, { n: kind.count }))));
}

// A dashed line's pill (ticket 136): "Overall risk: the PAD and 13 ISRs disagree".
export function pillText(item: DisagreementItem): string {
  const [anchor, others] = item.group ? [reportsName(item.group.anchor_reports), reportsName(item.group.other_reports)] : item.sides.map(shortName);
  return fill(words.pill, { fact: factName(item.attribute), anchor, others });
}

// The pill where the whole one has no room: "14 reports disagree".
export function chipShort(item: DisagreementItem): string {
  return fill(words.chipCount, { n: item.group?.reports ?? 2 });
}

// A pair of reports in the table: "Overall risk: the PAD and ISR 9".
export function pairLabel(item: DisagreementItem): string {
  return fill(words.pair, { fact: factName(item.attribute), side1: shortName(item.sides[0]), side2: shortName(item.sides[1]) });
}

// The report a line or a pair leans on, as its tooltip's and the table's last line says it, or null.
export function leanLine(item: DisagreementItem): string | null {
  const group = item.group;
  if (group && group.count > 1) {
    if (group.lean === "anchor") return fill(words.tip.leans, { lean: reportsName(group.anchor_reports) });
    if (group.lean === "others") {
      const one = group.other_reports.length === 1 && group.other_reports[0].count === 1;
      return one ? fill(words.tip.leans, { lean: reportsName(group.other_reports) }) : fill(words.tip.leansEach, { others: reportsName(group.other_reports) });
    }
    return words.tip.leansTable;
  }
  const lean = item.sides.find((side) => side.leaned);
  return lean ? fill(words.tip.leans, { lean: shortName(lean) }) : null;
}

export function bandItem(band: BandItem): string {
  return fill(band.first === band.last ? words.bandItemOne : words.bandItem, { first: band.first, last: band.last });
}

export function bandLine(band: BandItem): string {
  return fill(band.first === band.last ? words.bandLineOne : words.bandLine, { first: band.first, last: band.last, rating: band.rating });
}

// The band's label, the first form that fits its room: the rating with its ISRs, the rating, the code with its
// ISRs, the code, or none.
export function bandLabels(band: BandItem): string[] {
  const code = words.codes[band.rating] ?? band.rating;
  const one = band.first === band.last;
  const values = { rating: band.rating, code, first: band.first, last: band.last };
  return [
    fill(one ? words.band.fullOne : words.band.full, values),
    fill(words.band.rating, values),
    fill(one ? words.band.codeOne : words.band.code, values),
    code,
  ];
}

// Whether a band's label fits its band: the code alone ("MU") with 4 px a side, as the last form before none, and
// every longer form with 8 px a side.
export function bandLabelFits(text: string, textWidth: number, bandWidth: number): boolean {
  const pad = Object.values(words.codes).includes(text) ? 4 : 8;
  return textWidth <= bandWidth - 2 * pad;
}

// A side's short name in a sentence: "ISR 7", "the ICR".
export function shortName(side: { type: string; sequence: number | null }): string {
  return fill(words.short[side.type] ?? words.short.other, { sequence: side.sequence });
}

export function capitalize(text: string): string {
  return text ? text[0].toUpperCase() + text.slice(1) : text;
}

// Names in a sentence: "ISR 7", "ISR 7 and the ICR Review", "A, B and C", with no serial comma, as Joined writes
// them in an element.
export function joinNames(names: string[]): string {
  return names.reduce((out, name, index) => (index === 0 ? name : `${out}${index === names.length - 1 ? copy.list.and : copy.list.comma}${name}`), "");
}

// The short names of the reports a report disagrees with, in the order of its disagreements: for a line's one report
// (its anchor), every report on the line's other side, as "13 ISRs".
export function othersOf(item: ReportItem, items: Item[]): string[] {
  return (item.disagrees_with ?? [])
    .map((id) => items.find((one) => one.id === id))
    .flatMap((found) => {
      if (!found || found.kind !== "disagreement") return [];
      if (found.group && found.group.anchor_item_id === item.id) return [reportsName(found.group.other_reports)];
      return [shortName(found.sides.find((side) => side.item_id !== item.id)!)];
    });
}

// Each item's accessible name, with its place in the arrow-key order. A dashed line's name starts with the words
// its chip shows (chip), the whole pill or its count alone.
export function itemName(item: Item, index: number, total: number, items: Item[], chip?: string): string {
  const at = { i: index + 1, n: total };
  const lane = (key: Lane | null) => (key ? words.laneWord[key] : "");
  if (item.kind === "report") {
    const others = othersOf(item, items);
    if (item.type === "isr") {
      const template = !item.rating ? words.name.isrNoRating : others.length ? words.name.isrDisagrees : words.name.isr;
      return fill(template, { sequence: item.sequence, date: long(item.date), rating: item.rating ?? "", other: joinNames(others), ...at });
    }
    if (item.replaced_by) return fill(words.name.reportReplaced, { type: item.document_type, date: long(item.date), replaced: long(item.replaced_by.date), lane: lane(item.lane), ...at });
    if (others.length) return fill(words.name.reportDisagrees, { type: item.document_type, date: long(item.date), other: joinNames(others), lane: lane(item.lane), ...at });
    return fill(words.name.report, { type: item.document_type, date: long(item.date), lane: lane(item.lane), ...at });
  }
  if (item.kind === "event") return fill(words.name.event, { label: markLabel(item), date: long(item.date), ...at });
  if (item.kind === "record") return fill(words.name.record, { reference: item.step_reference, date: long(item.date), ...at });
  if (item.kind === "group") return fill(words.name.group, { count: item.count, year: item.year, ...at });
  if (item.kind === "band") {
    return fill(item.first === item.last ? words.name.bandOne : words.name.band, {
      first: item.first,
      last: item.last,
      rating: item.rating,
      start: long(item.date),
      end: long(item.end),
      ...at,
    });
  }
  const pill = pillText(item);
  const lead = !chip || chip === pill ? pill : fill(words.name.lead, { chip, pill });
  if (item.group && item.group.count > 1) {
    const lean = leanLine(item);
    return fill(words.name.disagreementGroup, { lead, lean: lean ? fill(words.name.leanNext, { lean }) : "", ...at });
  }
  const [one, two] = item.sides;
  const lean = item.sides.find((side) => side.leaned);
  return fill(words.name.disagreement, {
    lead,
    side1: shortName(one),
    date1: long(one.made_at),
    side2: shortName(two),
    date2: long(two.made_at),
    lean: lean ? shortName(lean) : "",
    ...at,
  });
}

// ── The layout ───────────────────────────────────────────────────────────

// The chart's rows, top to bottom (the 23 brief, section 4.1): 352 px in every state.
export const HEIGHT = 352;
export const PAD = 8;
const ROW = { label: 24, text: 20, marks: 24, gap: 16, band: 24, axis: 32 };
export type LaneRows = { label: number; rowA: number; marks: number; rowB: number; band?: number; bottom: number };
export const ROWS: Record<Lane, LaneRows> = (() => {
  let y = 0;
  const lane = (band: boolean): LaneRows => {
    const label = y;
    const rowA = label + ROW.label;
    const marks = rowA + ROW.text;
    const rowB = marks + ROW.marks;
    let bottom = rowB + ROW.text;
    const rows: LaneRows = { label, rowA, marks, rowB, bottom };
    if (band) {
      rows.band = bottom;
      bottom += ROW.band;
      rows.bottom = bottom;
    }
    y = bottom + ROW.gap;
    return rows;
  };
  return { why: lane(false), how: lane(true), what: lane(false) };
})();
export const AXIS_Y = ROWS.what.bottom;
export const MARK_ROW = ROW.marks;
export const TEXT_ROW = ROW.text;
export const BAND_ROW = ROW.band;
export const markY = (lane: Lane) => ROWS[lane].marks + ROW.marks / 2;

const DAY_MS = 86_400_000;
const time = (iso: string) => Date.parse(`${iso}T00:00:00Z`);
const shiftMonths = (iso: string, months: number) => {
  const date = new Date(`${iso}T00:00:00Z`);
  date.setUTCMonth(date.getUTCMonth() + months);
  return date.toISOString().slice(0, 10);
};

// DESIGN.md section 6: type sizes by chart width (s, m, l).
export function chartType(width: number): { s: number; m: number; l: number } {
  if (width < 400) return { s: 12, m: 14, l: 16 };
  if (width <= 700) return { s: 13, m: 15, l: 18 };
  return { s: 14, m: 16, l: 20 };
}

// The time axis (section 4.6): from 4 months before the first item to 4 months after the last, or to the as-of
// date when the page asks for one; ticks on whole years, every 1, 2, 5 or 10 years, the first step that gives four
// to six ticks.
export function axisFor(items: Item[], asOf: string | null): { from: number; to: number; ticks: number[] } {
  const dates = items.flatMap((item) => (item.kind === "band" ? [item.date, item.end] : item.kind === "disagreement" ? [] : [item.date]));
  const first = dates.reduce((a, b) => (a < b ? a : b), dates[0] ?? asOf ?? "2000-01-01");
  const last = dates.reduce((a, b) => (a > b ? a : b), dates[0] ?? asOf ?? "2000-01-01");
  const from = time(shiftMonths(first, -4));
  const to = asOf ? Math.max(time(asOf), time(last)) : time(shiftMonths(last, 4));
  const startYear = new Date(from).getUTCFullYear();
  const endYear = new Date(to).getUTCFullYear();
  const years = (step: number) => {
    const found: number[] = [];
    for (let year = Math.ceil(startYear / step) * step; year <= endYear; year += step) {
      const at = Date.UTC(year, 0, 1);
      if (at >= from && at <= to) found.push(year);
    }
    return found;
  };
  const step = [1, 2, 5, 10].find((one) => years(one).length >= 4 && years(one).length <= 6) ?? 1;
  return { from, to, ticks: years(step) };
}

export type Scale = (iso: string) => number;
export function scaleFor(axis: { from: number; to: number }, width: number): Scale {
  const left = PAD;
  const right = width - PAD;
  const span = Math.max(axis.to - axis.from, DAY_MS);
  return (iso: string) => left + ((time(iso) - axis.from) / span) * (right - left);
}
export const yearX = (year: number, x: Scale) => x(`${year}-01-01`);

export type Box = { x0: number; x1: number; y0: number; y1: number };
const GAP = 8;
const clear = (a: Box, b: Box) => a.x1 + GAP <= b.x0 || b.x1 + GAP <= a.x0 || a.y1 <= b.y0 || b.y1 <= a.y0;

export type Placed = { id: string; text: string; x: number; y: number; anchor: "start" | "middle" | "end"; box: Box } | { id: string; dropped: true };

// A disagreement's line and its chip (section 4.4). Between marks in two lanes it is a straight line; between two
// marks in one lane it is a bracket, so it passes over every mark between them and joins only its two reports:
// straight up from each mark, with 4 px rounded corners, and across the lane's label row, 44 px above the marks, so
// row A stays free for the mark labels; where the lane's own label sits in the way, across row A instead, 28 px
// above. Either way it stops 4 px short of each mark's ring. The chip sits at the line's middle (on the bracket's top) and slides toward
// the later mark, 8 px at a time, off a lane's label and an earlier chip. points samples the drawn line every 4 px,
// so the mark labels can keep off it.
export type Point = { x: number; y: number };
// form: which of the chip's widths it took, the pill's whole words (0) or its count alone (1).
export type Line = { id: string; path: string; chip: Box; cx: number; cy: number; points: Point[]; form: number };
const RING = 6 + 2 + 4;
// How far a bracket's top sits above its marks: in the lane's label row, or in row A when the lane label is in the way.
const RISE = { labelRow: ROW.text + ROW.label, rowA: 28 };
const CORNER = 4;

function sample(from: Point, to: Point): Point[] {
  const steps = Math.max(1, Math.ceil(Math.hypot(to.x - from.x, to.y - from.y) / 4));
  return Array.from({ length: steps + 1 }, (_, k) => ({ x: from.x + ((to.x - from.x) * k) / steps, y: from.y + ((to.y - from.y) * k) / steps }));
}

// chipWidths: the chip's widths, longest words first (ticket 136): the first that fits clear of a lane's label and an
// earlier chip, sliding toward the later mark and then toward the earlier, is drawn; when none fits, the last.
export function lineFor(item: DisagreementItem, x: Scale, chipWidths: number | number[], laneLabels: Box[], width: number, placed: Box[]): Line {
  const [one, two] = item.sides;
  const a = { x: x(one.made_at), y: markY(one.lane) };
  const b = { x: x(two.made_at), y: markY(two.lane) };
  const half = 12;
  let path: string;
  let points: Point[];
  let at: (t: number) => Point;
  if (one.lane === two.lane) {
    const high = a.y - RISE.labelRow;
    const inTheWay = laneLabels.some((label) => label.y0 <= high && high <= label.y1 && Math.min(a.x, b.x) <= label.x1 + GAP);
    const top = inTheWay ? a.y - RISE.rowA : high;
    const corner = Math.min(CORNER, Math.abs(b.x - a.x) / 2);
    const start = { x: a.x, y: a.y - RING };
    const end = { x: b.x, y: b.y - RING };
    path = [
      `M ${start.x} ${start.y}`,
      `L ${a.x} ${top + corner}`,
      `Q ${a.x} ${top} ${a.x + corner} ${top}`,
      `L ${b.x - corner} ${top}`,
      `Q ${b.x} ${top} ${b.x} ${top + corner}`,
      `L ${end.x} ${end.y}`,
    ].join(" ");
    points = [...sample(start, { x: a.x, y: top }), ...sample({ x: a.x, y: top }, { x: b.x, y: top }), ...sample({ x: b.x, y: top }, end)];
    at = (t: number) => ({ x: a.x + (b.x - a.x) * t, y: top });
  } else {
    const length = Math.hypot(b.x - a.x, b.y - a.y) || 1;
    const ux = (b.x - a.x) / length;
    const uy = (b.y - a.y) / length;
    const start = { x: a.x + ux * RING, y: a.y + uy * RING };
    const end = { x: b.x - ux * RING, y: b.y - uy * RING };
    path = `M ${start.x} ${start.y} L ${end.x} ${end.y}`;
    points = sample(start, end);
    at = (t: number) => ({ x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t });
  }
  const length = Math.hypot(b.x - a.x, b.y - a.y) || 1;
  const step = 8 / length;
  const widths = Array.isArray(chipWidths) ? chipWidths : [chipWidths];
  const blocked = (candidate: Box) => [...laneLabels, ...placed].some((other) => !clear(candidate, other));
  const made = (point: Point, box: Box, form: number): Line => ({ id: item.id, path, chip: box, cx: (box.x0 + box.x1) / 2, cy: point.y, points, form });
  let fallback: Line | null = null;
  for (const [form, chipWidth] of widths.entries()) {
    const boxAt = (point: Point): Box => {
      const left = Math.min(Math.max(point.x - chipWidth / 2, PAD), width - PAD - chipWidth);
      return { x0: left, x1: left + chipWidth, y0: point.y - half, y1: point.y + half };
    };
    // From the middle toward the later mark, as far as 0.9 of the way, then from the middle toward the earlier one.
    const forward = [0.5];
    for (let t = 0.5 + step; t < 0.9; t += step) forward.push(t);
    const backward: number[] = [];
    for (let t = 0.5 - step; t > 0.1; t -= step) backward.push(t);
    for (const t of [...forward, ...backward]) {
      const point = at(t);
      const box = boxAt(point);
      if (!blocked(box)) return made(point, box, form);
    }
    // Where nothing fits, the chip stays at its last place toward the later mark, as it did before ticket 136.
    const point = at(forward[forward.length - 1]);
    fallback = made(point, boxAt(point), form);
  }
  return fallback!;
}

// Mark labels (section 4.5): in date order within each lane, after the chips, each takes the first place that
// fits: row A centred on its mark, row A ending 8 px left of it, row A starting 8 px right of it, then the same
// three in row B. A label fits inside the plot, 16 px from every placed label (closer, two labels read as one
// phrase), 8 px from every chip, and 3 px from every point of a dashed line (avoid), so no line runs through a
// label. When a lane's labels cannot all fit in that order, an
// earlier label tries its next place, so the first layout in which none is dropped wins; when keeping off the lines
// would drop a label, the lane keeps its labels and lets the line pass behind them, on their surface knockouts. The
// same data and width always give the same layout. A label with no place left is dropped, and its mark keeps its
// name, its tooltip and its table row.
type LabelMark = { id: string; lane: Lane; x: number; text: string; width: number };
const LINE_GAP = 3;
const LABEL_GAP = 16;
const apart = (a: Box, b: Box) => a.x1 + LABEL_GAP <= b.x0 || b.x1 + LABEL_GAP <= a.x0 || a.y1 <= b.y0 || b.y1 <= a.y0;
const near = (box: Box, point: Point) =>
  point.x >= box.x0 - LINE_GAP && point.x <= box.x1 + LINE_GAP && point.y >= box.y0 - LINE_GAP && point.y <= box.y1 + LINE_GAP;

function laneLabels(mine: LabelMark[], lane: Lane, blocks: Box[], avoid: Point[], width: number, height: number): Placed[] {
  const rows = ROWS[lane];
  const candidates = (mark: LabelMark) =>
    [rows.rowA, rows.rowB].flatMap((top) => {
      const y0 = top + (TEXT_ROW - height) / 2;
      const y1 = y0 + height;
      const baseline = top + TEXT_ROW / 2;
      return [
        { anchor: "middle" as const, x: mark.x, box: { x0: mark.x - mark.width / 2, x1: mark.x + mark.width / 2, y0, y1 }, y: baseline },
        { anchor: "end" as const, x: mark.x - GAP, box: { x0: mark.x - GAP - mark.width, x1: mark.x - GAP, y0, y1 }, y: baseline },
        { anchor: "start" as const, x: mark.x + GAP, box: { x0: mark.x + GAP, x1: mark.x + GAP + mark.width, y0, y1 }, y: baseline },
      ].filter(
        (place) =>
          place.box.x0 >= PAD &&
          place.box.x1 <= width - PAD &&
          blocks.every((block) => clear(place.box, block)) &&
          !avoid.some((point) => near(place.box, point)),
      );
    });
  const options = mine.map(candidates);
  const chosen: number[] = [];
  let tries = 0;
  const solve = (at: number, taken: Box[]): boolean => {
    if (at === mine.length) return true;
    for (let k = 0; k < options[at].length; k += 1) {
      tries += 1;
      if (tries > 4000) return false;
      const place = options[at][k];
      if (taken.every((box) => apart(place.box, box))) {
        chosen[at] = k;
        if (solve(at + 1, [...taken, place.box])) return true;
      }
    }
    return false;
  };
  if (solve(0, [])) {
    return mine.map((mark, index) => {
      const place = options[index][chosen[index]];
      return { id: mark.id, text: mark.text, x: place.x, y: place.y, anchor: place.anchor, box: place.box };
    });
  }
  // No layout keeps every label: place them in order and drop the ones with no room.
  const taken: Box[] = [];
  return mine.map((mark, index): Placed => {
    const place = options[index].find((option) => taken.every((box) => apart(option.box, box)));
    if (!place) return { id: mark.id, dropped: true };
    taken.push(place.box);
    return { id: mark.id, text: mark.text, x: place.x, y: place.y, anchor: place.anchor, box: place.box };
  });
}

export function placeLabels(marks: LabelMark[], blocks: Box[], width: number, height: number, avoid: Point[] = []): Placed[] {
  const dropped = (placed: Placed[]) => placed.filter((one) => "dropped" in one).length;
  return LANES.flatMap((lane) => {
    const mine = marks.filter((mark) => mark.lane === lane);
    const clearOfLines = laneLabels(mine, lane, blocks, avoid, width, height);
    if (!avoid.length || dropped(clearOfLines) === 0) return clearOfLines;
    const kept = laneLabels(mine, lane, blocks, [], width, height);
    return dropped(kept) < dropped(clearOfLines) ? kept : clearOfLines;
  });
}
