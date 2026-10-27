// A project's Timeline tab (ticket 23; the 23 brief): What, How and Why in three lanes on one time axis, so you can
// see what was known when. One request, GET /api/projects/{pid}/timeline, gives every item in the order the arrow
// keys and the table follow, the finding the chart is titled with and its alt text, written on the server from copy
// templates and tool values; the tab calls no model and computes no number.
//
// The chart shows while the viewport is at least 768 px wide and the chart itself at least 520 px, so it stays a
// chart when the drawer opens at 1024 px; otherwise the list shows, in date order. Every mark, band, line and list
// item opens its source in the evidence drawer.
//
// States: loading (the h2, the purpose and the subtitle are real; the chart's 352 px box holds skeleton bars),
// populated, a lane with nothing in it, no ISR ratings, empty, the abstention line, disagreements that failed to
// load, an error, the public view of a project still under way (no disagreements), and as of a date.
import { useEffect, useId, useLayoutEffect, useRef, useState, type ReactNode } from "react";
import { Alert } from "../../components/Alert";
import { Button } from "../../components/Button";
import { EmptyState } from "../../components/Card";
import { EvidenceTrail, Glyph, type LineState } from "../../components/EvidenceTrail";
import { Fill, Joined } from "../../components/Fill";
import { LoadError } from "../../components/LoadError";
import { Num } from "../../components/Num";
import { SegmentText } from "../../components/SegmentText";
import { Skeleton, SkeletonLine } from "../../components/Skeleton";
import { Source } from "../../components/Source";
import { StatusBadge } from "../../components/StatusBadge";
import { Table, type Column, type Row } from "../../components/Table";
import { Term } from "../../components/Term";
import { copy } from "../../copy";
import { answer, type Run } from "../../lib/answer";
import { cx } from "../../lib/cx";
import { evidenceHref, evidenceIn, openEvidence } from "../../lib/evidence";
import { formatDate } from "../../lib/format";
import { useLoad } from "../../lib/load";
import { address } from "../../lib/router";
import { useStore } from "../../lib/store";
import {
  HEIGHT,
  LANES,
  bandLine,
  capitalize,
  fullLabel,
  joinNames,
  othersOf,
  shortName,
  type Item,
  type Lane,
  type Timeline,
} from "../../lib/timeline";
import { withReadParams } from "../../lib/view";

const words = copy.timeline;
const CHART_MIN = 520;
const WIDE = "(width >= 48rem)";

function useWide(): boolean {
  const [wide, setWide] = useState(() => typeof window === "undefined" || window.matchMedia(WIDE).matches);
  useEffect(() => {
    const query = window.matchMedia(WIDE);
    const update = () => setWide(query.matches);
    query.addEventListener("change", update);
    return () => query.removeEventListener("change", update);
  }, []);
  return wide;
}

// The width the chart may take: its box's, measured before paint and again on every resize, as when the drawer
// opens beside the page.
function useWidth<T extends HTMLElement>(): [React.RefObject<T | null>, number] {
  const ref = useRef<T>(null);
  const [width, setWidth] = useState(0);
  useLayoutEffect(() => {
    const element = ref.current;
    if (!element) return;
    const read = () => setWidth(Math.floor(element.getBoundingClientRect().width));
    read();
    const watch = new ResizeObserver(read);
    watch.observe(element);
    return () => watch.disconnect();
  }, []);
  return [ref, width];
}

// The title's size, in pixels, which the loading card's placeholder takes too, so nothing moves when the finding
// arrives: 20 on a chart card wider than 700 px, 18 on a narrower chart, 16 over the list.
const titleSize = (chart: boolean, width: number) => (chart ? (width > 700 ? 20 : 18) : 16);
// How many lines the placeholder draws: a finding fits on one line from a 1,000 px chart card, takes two on a
// narrower chart, three over the list on a 390 px phone, whose margins are 16 px (ticket 94), and four on a
// narrower one.
const titleLines = (chart: boolean, width: number) => (chart ? (width >= 1000 ? 1 : 2) : width >= 320 ? 3 : 4);

// A disagreement's line takes its card's state: amber only while an answer open on this page has a sentence it
// changes (the 23 brief, section 4.4), and the default otherwise.
export function lineStates(data: Timeline, run: Run | null): Record<string, LineState> {
  const states: Record<string, LineState> = {};
  for (const item of data.items) {
    if (item.kind !== "disagreement") continue;
    const found = run?.disagreements.find((one) => one.id.endsWith(`:${item.disagreement_id}`));
    states[item.id] = found ? (found.changes_answer ? "warning" : "info") : data.disagreement_line_state;
  }
  return states;
}

// The Note line: each abbreviation that appears, what the bands show and each code a band shows. The list writes
// each run's rating in words and draws no bands, so there the Note says nothing about them.
function Note({ data, codes, chart }: { data: Timeline; codes: string[]; chart: boolean }) {
  const types = new Set(data.items.flatMap((item) => (item.kind === "report" ? [item.type] : [])));
  if (data.items.some((item) => item.kind === "band")) types.add("isr");
  const abbreviations = (["pad", "isr", "icr", "icr_review", "ppar"] as const).filter((type) => types.has(type)).map((type) => words.abbrev[type]);
  const banded = data.items.some((item) => item.kind === "band");
  const spelled = codes.map((rating) => words.codeNote(words.codes[rating] ?? rating, rating));
  const parts = [...abbreviations, ...(banded && chart ? [words.bands, ...spelled] : [])];
  if (!parts.length) return null;
  return (
    <p data-timeline-note className="max-w-prose text-caption text-chart-text-subtle">
      <span className="font-bold text-chart-text">{words.noteLead}</span> {parts.join(" ")}
    </p>
  );
}

// The source line's words, which Table wraps in its own Source line under the table twin. As of a date they end at
// that date, as the chart's label and the list's line do, not at the date the data were read through.
function SourceWords({ data }: { data: Timeline }) {
  const names = data.sources.map((key) => words.sourceNames[key] ?? key);
  const date = data.asked_as_of ?? data.data_through ?? data.as_of;
  return <Fill template={data.asked_as_of ? words.sourceAsOf : words.source} slots={{ sources: <Joined items={names} />, date: <Num date={date} /> }} />;
}

function SourceLine({ data }: { data: Timeline }) {
  return (
    <Source className="max-w-prose">
      <SourceWords data={data} />
    </Source>
  );
}

function Abstention({ count }: { count: number }) {
  return (
    <p data-timeline-abstention className="max-w-prose text-caption text-ink-muted">
      <Fill template={words.abstention(count)} slots={{ n: <Num count={count} inCaption check={{ tooltip: words.abstentionCheck }} /> }} />
    </p>
  );
}

// The table twin (section 4.9): every item, every contract on its own row, in arrow-key order.
function TimelineTable({ data, id, onOpen }: { data: Timeline; id: string; onOpen: (item: Item, element: HTMLElement) => void }) {
  const items = data.table;
  const columns: Column[] = [
    { key: "date", header: words.columns.date, width: "w-1/6", short: true },
    {
      key: "stratum",
      header: (
        <span className="flex flex-col">
          <Term term="Stratum">{words.columns.stratum}</Term>
          <span className="text-caption font-normal text-ink-muted">{words.stratumCaption}</span>
        </span>
      ),
      cardHeader: words.columns.stratum,
      width: "w-1/6",
      short: true,
    },
    { key: "item", header: words.columns.item, width: "w-1/4" },
    { key: "rating", header: words.columns.rating, width: "w-1/6", short: true },
    { key: "note", header: words.columns.note },
  ];
  const note = (item: Item): ReactNode => {
    if (item.kind === "band") return words.note.trajectory;
    if (item.kind === "disagreement") {
      const lean = item.sides.find((side) => side.leaned);
      return lean ? words.note.leans.replace("{lean}", shortName(lean)) : null;
    }
    if (item.kind === "report" && item.replaced_by) return words.note.replaced.replace("{date}", formatDate(item.replaced_by.date));
    if (item.kind === "report" && item.disagrees_with?.length) return words.note.disagrees.replace("{other}", joinNames(othersOf(item, data.items)));
    return null;
  };
  const rows: Row[] = items.map((item) => ({
    id: item.id,
    cells: {
      date:
        item.kind === "band" ? (
          <Fill template={words.tableRange} slots={{ start: <Num date={item.date} style="table" />, end: <Num date={item.end} style="table" /> }} />
        ) : (
          <Num date={item.date} style="table" />
        ),
      stratum: item.lane ? words.laneWord[item.lane] : null,
      item: (
        <a
          href={evidenceHref(item.evidence_id)}
          data-table-item={item.id}
          onClick={(event) => {
            if (event.metaKey || event.ctrlKey || event.shiftKey || event.button !== 0) return;
            event.preventDefault();
            onOpen(item, event.currentTarget);
          }}
          className={cx("inline-flex min-h-6 items-center py-1 text-primary underline underline-offset-3 hover:text-link-hover", item.kind === "record" && "font-mono [overflow-wrap:anywhere]")}
        >
          {fullLabel(item)}
        </a>
      ),
      rating: item.kind === "band" ? item.rating : item.kind === "report" && item.type === "isr" ? item.rating : null,
      note: note(item),
    },
  }));
  return (
    <div id={id} data-timeline-table className="mt-4">
      <Table
        title={words.caption(data.project.display_name ?? data.project.project_id)}
        count={{ noun: words.itemsNoun, total: rows.length, text: words.count(String(rows.length)) }}
        columns={columns}
        state={{ status: "ready", rows }}
        rowHeader="item"
        level={4}
        source={<SourceWords data={data} />}
      />
    </div>
  );
}

// Below 768 px, or where the chart would be narrower than 520 px: the items as a list in date order, each a link
// at least 44 px tall on a rail, its shape on the rail.
function TimelineList({ data, openId, states, onOpen }: { data: Timeline; openId: string | null; states: Record<string, LineState>; onOpen: (item: Item, element: HTMLElement) => void }) {
  return (
    <ol data-timeline-list className="relative mt-4 border-l border-line-strong pl-0">
      {data.items.map((item) => {
        const active = openId === item.evidence_id;
        const glyph = item.kind === "report" ? "report" : item.kind === "event" ? "event" : item.kind === "band" ? null : item.kind === "disagreement" ? null : "record";
        const state = item.kind === "disagreement" ? (states[item.id] ?? "info") : null;
        return (
          <li
            key={item.id}
            className={cx("relative", item.kind === "disagreement" && "border-l border-dashed", state === "warning" ? "border-warning-icon" : state ? "border-info-icon" : "")}
            style={item.kind === "disagreement" ? { marginLeft: -1 } : undefined}
          >
            <span aria-hidden="true" className="absolute top-3 -left-[7px] flex size-3 items-center justify-center bg-surface">
              {glyph ? <Glyph kind={glyph} /> : item.kind === "band" ? <span className="block h-3 w-1.5 rounded-xs border border-line-strong bg-chart-grey200" /> : null}
            </span>
            <a
              href={evidenceHref(item.evidence_id)}
              data-list-item={item.id}
              aria-current={active ? "true" : undefined}
              onClick={(event) => {
                if (event.metaKey || event.ctrlKey || event.shiftKey || event.button !== 0) return;
                event.preventDefault();
                onOpen(item, event.currentTarget);
              }}
              className={cx(
                "block min-h-11 py-2 pr-2 pl-6 transition-paint duration-150 hover:bg-tint-hover",
                active && "bg-tint shadow-[inset_3px_0_0_0_var(--color-primary)]",
              )}
            >
              <ListItemText item={item} data={data} states={states} />
            </a>
          </li>
        );
      })}
    </ol>
  );
}

function ListItemText({ item, data, states }: { item: Item; data: Timeline; states: Record<string, LineState> }) {
  if (item.kind === "band") {
    return (
      <>
        <span className="block text-caption text-ink-muted">
          <Fill template={words.range} slots={{ start: <Num date={item.date} style="table" />, end: <Num date={item.end} style="table" /> }} />
        </span>
        <span className="block text-small font-semibold text-ink">{bandLine(item)}</span>
        <span className="block text-caption text-ink-muted">{words.laneItem.how}</span>
      </>
    );
  }
  if (item.kind === "disagreement") {
    const state = states[item.id] ?? "info";
    return (
      <>
        <span className="block text-caption text-ink-muted">
          <Num date={item.date} style="table" />
        </span>
        <span className="mt-1 block">
          <StatusBadge kind={state === "warning" ? "chip-warning" : "chip-info"} />
        </span>
        <span className="mt-1 block text-caption text-ink">{capitalize(words.sides.replace("{side1}", shortName(item.sides[0])).replace("{side2}", shortName(item.sides[1])))}</span>
      </>
    );
  }
  const others = item.kind === "report" ? othersOf(item, data.items) : [];
  return (
    <>
      <span className="block text-caption text-ink-muted">
        <Num date={item.date} style="table" />
      </span>
      <span className={cx("block text-small font-semibold text-ink [overflow-wrap:anywhere]", item.kind === "record" && "font-mono")}>{fullLabel(item)}</span>
      <span className="block text-caption text-ink-muted">{words.laneItem[item.lane]}</span>
      {item.kind === "report" && item.replaced_by && (
        <span className="block text-caption text-ink-muted">{words.tip.replacedBy.replace("{date}", formatDate(item.replaced_by.date))}</span>
      )}
      {others.length > 0 && <span className="block text-caption text-ink-muted">{words.tip.disagrees.replace("{other}", joinNames(others))}</span>}
    </>
  );
}

// The chart card's loading look: the title's bars, then the 352 px box with the real lane labels and bars for
// each row of marks, and two caption bars for the notes. Below 768 px, five list items.
function TimelineSkeleton({ wide }: { wide: boolean }) {
  if (!wide) {
    return (
      <div aria-hidden="true" className="mt-4 flex flex-col gap-2">
        {[0, 1, 2, 3, 4].map((n) => (
          <Skeleton key={n} className="h-16 w-full" />
        ))}
      </div>
    );
  }
  return (
    <div aria-hidden="true" className="relative mt-4" style={{ height: HEIGHT }}>
      {LANES.map((lane, at) => (
        <div key={lane} className="absolute inset-x-2" style={{ top: [0, 104, 232][at] }}>
          <p className="text-chart-label text-chart-text-subtle uppercase">{words.lane[lane]}</p>
          <Skeleton className={cx("mt-8 h-3", ["w-[90%]", "w-[60%]", "w-[40%]"][at])} />
          {lane === "how" && <Skeleton className="mt-10 h-6 w-full" />}
        </div>
      ))}
      <div className="absolute inset-x-2 border-t border-line-strong" style={{ top: 320 }} />
    </div>
  );
}

// The chart card while the timeline loads. Its title placeholder has the finding's size and its likely number of
// lines at this card's width, so the subtitle and the chart stay where they are when the data arrive.
export function TimelineLoading({ wide, slow }: { wide: boolean; slow: boolean }) {
  const [box, width] = useWidth<HTMLDivElement>();
  const chart = wide && width >= CHART_MIN;
  const lines = titleLines(chart, width);
  return (
    <div data-timeline-card className="rounded-md border border-line bg-surface p-4 @md/page:p-6">
      <div ref={box}>
        <p aria-hidden="true" className="font-bold" style={{ fontSize: titleSize(chart, width) }}>
          {Array.from({ length: lines }, (_, at) => (
            <SkeletonLine key={at} width={at === lines - 1 && lines > 1 ? "w-[40%]" : "w-[70%]"} />
          ))}
        </p>
      </div>
      <p data-timeline-subtitle className="mt-1 max-w-prose text-small text-chart-text-subtle">
        {wide ? <Fill template={words.subtitle} slots={{ report: <Glyph kind="report" />, event: <Glyph kind="event" />, record: <Glyph kind="record" /> }} /> : words.subtitleList}
      </p>
      <TimelineSkeleton wide={wide} />
      <SkeletonLine width="w-3/5" className="mt-4 text-caption" />
      {/* After two seconds the card's last caption bar becomes "Still loading", one caption line tall, so nothing
          above it moves (design review, round 3, F2). */}
      {slow ? <p className="text-caption text-ink-muted">{words.stillLoading}</p> : <SkeletonLine width="w-2/5" className="text-caption" />}
      <p role="status" className="sr-only">
        {words.loading}
      </p>
    </div>
  );
}

// The chart card, in any state the payload gives: the finding, the subtitle, the chart or the list, the notes, the
// source line and the table twin. The design gallery draws it as it is.
export function TimelineCard({
  data,
  wide,
  openId,
  states,
  onOpen,
  onRetry,
}: {
  data: Timeline;
  wide: boolean;
  openId: string | null;
  states: Record<string, LineState>;
  onOpen: (item: Item, element: HTMLElement) => void;
  onRetry?: () => void;
}) {
  const titleId = useId();
  const tableId = useId();
  const [box, width] = useWidth<HTMLDivElement>();
  const [table, setTable] = useState(false);
  const [codes, setCodes] = useState<string[]>([]);
  const chart = wide && width >= CHART_MIN;
  // The title's count (the 23 brief, section 7.2) opens the table and moves focus to it, named by its caption.
  const openTable = () => {
    setTable(true);
    requestAnimationFrame(() => document.getElementById(tableId)?.querySelector<HTMLElement>("[tabindex='0']")?.focus());
  };
  const empty = (lane: Lane) => !data.items.some((item) => item.lane === lane);
  const lanesEmpty = Object.fromEntries(LANES.map((lane) => [lane, empty(lane)])) as Record<Lane, boolean>;
  return (
    // tabIndex -1: Try again in the disagreements alert brings you back to the chart (the 23 brief, section 8.4). The
    // global focus outline shows when you got there by keyboard, since the button you pressed is gone.
    <figure aria-labelledby={titleId} tabIndex={-1} data-timeline-card className="rounded-md border border-line bg-surface p-4 @md/page:p-6">
      <p id={titleId} data-timeline-finding className="text-pretty font-bold text-ink-heading" style={{ fontSize: titleSize(chart, width) }}>
        {/* The count's tooltip opens above it, so it never hides the finding's second line. */}
        <SegmentText segments={data.finding} check={chart ? { tooltip: words.findingCheck, onOpen: openTable, side: "top" } : undefined} />
      </p>
      <p data-timeline-subtitle className="mt-1 max-w-prose text-small text-chart-text-subtle">
        {chart ? (
          <Fill
            // No dashed line can be drawn when get_disagreements did not answer or the view hides disagreements.
            template={data.disagreements.status === "ok" ? words.subtitle : words.subtitleNoLines}
            slots={{ report: <Glyph kind="report" />, event: <Glyph kind="event" />, record: <Glyph kind="record" /> }}
          />
        ) : (
          words.subtitleList
        )}
      </p>
      {/* The list has no "As of" label, which the chart draws on its What lane, so it says its date here. */}
      {!chart && data.asked_as_of && (
        <p data-timeline-as-of className="mt-1 max-w-prose text-caption text-ink-muted">
          <Fill template={words.asOfList} slots={{ date: <Num date={data.asked_as_of} /> }} />
        </p>
      )}
      {data.disagreements.status === "hidden" && <p className="mt-1 max-w-prose text-caption text-ink-muted">{words.hidden}</p>}
      {data.disagreements.status === "failed" && (
        <Alert
          state="error"
          className="mt-4"
          action={
            onRetry && (
              <Button variant="secondary" onClick={onRetry}>
                {copy.answer.tryAgain}
              </Button>
            )
          }
        >
          {data.items.some((item) => item.kind === "report" && item.type === "isr") ? words.failed : words.failedNoIsr}
        </Alert>
      )}
      <div ref={box} className="mt-4 min-w-0">
        {chart ? (
          <EvidenceTrail data={data} width={width} openId={openId} lineStates={states} onOpen={onOpen} lanesEmpty={lanesEmpty} onCodes={setCodes} />
        ) : (
          <TimelineList data={data} openId={openId} states={states} onOpen={onOpen} />
        )}
      </div>
      <div className="mt-4 flex flex-col gap-2">
        <Note data={data} codes={chart ? codes : []} chart={chart} />
        {data.rejected && data.rejected.count > 0 && <Abstention count={data.rejected.count} />}
        <SourceLine data={data} />
      </div>
      {chart && (
        <>
          <Button variant="ghost" className="mt-2" flush aria-expanded={table} aria-controls={tableId} onClick={() => setTable((open) => !open)}>
            {table ? words.hide : words.show}
          </Button>
          {table ? <TimelineTable data={data} id={tableId} onOpen={onOpen} /> : <div id={tableId} hidden />}
        </>
      )}
    </figure>
  );
}

export function TimelineTab({ pid }: { pid: string }) {
  const here = useStore(address);
  const [load, retry] = useLoad<Timeline>(withReadParams(`/api/projects/${encodeURIComponent(pid)}/timeline`, here.search));
  const run = useStore(answer);
  const wide = useWide();
  const heading = useRef<HTMLHeadingElement>(null);
  const section = useRef<HTMLElement>(null);
  // Where Try again was pressed: the load error's (focus goes back to the heading) or the disagreements alert's,
  // inside the chart card (focus goes to the chart card).
  const retriedFrom = useRef<"page" | "card">("page");
  const openId = evidenceIn(here.search);
  const onOpen = (item: Item, element: HTMLElement) =>
    openEvidence(item.evidence_id, {
      serial: null,
      sentence: null,
      marker: element,
      runId: null,
      fallback: heading.current,
      context:
        item.kind === "event"
          ? { lead: words.drawer.fromTimeline, line: words.drawer.fromTimelineItem.replace("{label}", fullLabel(item)).replace("{date}", formatDate(item.date)) }
          : null,
    });

  useEffect(() => {
    if (load.status !== "ready" || !load.afterRetry) return;
    const card = retriedFrom.current === "card" ? section.current?.querySelector<HTMLElement>("figure[data-timeline-card]") : null;
    (card ?? heading.current)?.focus();
    retriedFrom.current = "page";
  }, [load]);
  const retryCard = () => {
    retriedFrom.current = "card";
    retry();
  };

  let body: ReactNode;
  if (load.status === "loading") {
    body = <TimelineLoading wide={wide} slow={load.slow} />;
  } else if (load.status === "error") {
    body = <LoadError error={load.error} message={words.error} permission={words.permission} onRetry={retry} retrying={load.retrying} attempt={load.attempt} />;
  } else if (load.data.items.length === 0) {
    body = <EmptyState level={3} title={words.emptyTitle} body={words.emptyBody} link={{ href: "/data", text: words.emptyLink }} />;
  } else {
    body = <TimelineCard data={load.data} wide={wide} openId={openId} states={lineStates(load.data, run)} onOpen={onOpen} onRetry={retryCard} />;
  }
  // The purpose asks you to select a mark only where there is one to select.
  const selectable = load.status === "loading" || (load.status === "ready" && load.data.items.length > 0);
  return (
    <section ref={section} data-timeline={load.status} className="@container/timeline">
      <h2 ref={heading} tabIndex={-1} className="text-h2 text-ink-heading focus:outline-none">
        {words.title}
      </h2>
      <p data-timeline-purpose className="mt-2 max-w-prose text-body text-ink-muted">
        {words.purpose}
        {selectable && <> {wide ? words.purposeSelect : words.purposeSelectList}</>}
      </p>
      <div className="mt-6">{body}</div>
    </section>
  );
}
