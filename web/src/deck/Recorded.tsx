// The planning demo's recorded answer (ticket 116), the backup for the package demo when the App is down: the
// comparable packages find_comparables gave for the demo plan's package, recorded on the workspace
// (ops/proposal/record_demo_live.py, into the deck's data). The package workspace's own range chart draws it,
// read-only, with the day it was recorded and the coverage line and source line the workspace prints under its chart.
// Every number in it is the recording's, so the whole answer is one element bound to the tool's key, which the number
// check reads as sourced. The button shows only when the deck's data holds a recording with packages to draw.
//
// On the canvas, "Show the recorded answer" swaps the demo's box and points for the answer: the chart, scaled as one
// picture to the space under the title, then its lines beside "Hide the recorded answer". The deck holds whether it is
// open (RecordedAnswer), so the slide's last press comes in with it and the next press moves on, the control bar's
// "Show the table" swaps the chart's table twin in, and a press back or another slide closes it. In the reading view
// the same button opens the answer under the points, at the column's width, with its table in a disclosure.
import { createContext, useEffect, useId, useLayoutEffect, useRef, useState, type ReactNode, type Ref } from "react";
import { ChevronDown, ChevronUp, History } from "lucide-react";
import { Button } from "../components/Button";
import { Fill } from "../components/Fill";
import { RangeFigure, RangeFigureLines } from "../components/PastRange";
import type { ComparablesResult } from "../lib/api";
import { formatDate } from "../lib/format";
import { deckCopy } from "./copy";
import { TOOL_KEY } from "./nums";
import { type } from "./ramp";

export type Recording = { result: ComparablesResult; step: string };

// The deck's hold on the recorded answer, on the canvas: open or close it.
export const RecordedAnswer = createContext<((open: boolean) => void) | null>(null);

// A recording the chart can draw: one with comparable packages in it. One that found none, or none it could measure,
// keeps the slide as it is.
export function recordingOf(result: ComparablesResult | null, step: string): Recording | undefined {
  const drawable = result && result.counts && result.rows.length > 0 && (!result.abstention || result.abstention.reason === "too_few_comparables");
  return drawable ? { result, step } : undefined;
}

// The width the chart draws at before it is scaled, as the first draft's chart slide drew it: wide enough for the
// chart's largest type sizes (DESIGN.md section 6).
const DRAWN_WIDTH = 831;
const BUTTON =
  "inline-flex h-11 shrink-0 items-center gap-2 rounded-sm border-2 border-primary px-4 text-button text-primary transition-paint duration-150 hover:bg-tint";

export function RecordedButton({ open, controls, onClick, buttonRef }: { open?: boolean; controls?: string; onClick: () => void; buttonRef?: Ref<HTMLButtonElement> }) {
  return (
    <button ref={buttonRef} type="button" onClick={onClick} aria-expanded={open} aria-controls={controls} data-recorded-toggle className={BUTTON}>
      <History aria-hidden="true" className="size-4" />
      {open ? deckCopy.demo.hideRecorded : deckCopy.demo.showRecorded}
    </button>
  );
}

function RecordedLine({ recording, id }: { recording: Recording; id: string }) {
  return (
    <p id={id} className="text-small text-ink" data-recorded-on>
      <Fill
        template={deckCopy.slides.demoPackage.recorded}
        slots={{ date: formatDate(recording.result.as_of), step: <span className="font-mono">{recording.step}</span> }}
      />
    </p>
  );
}

// The chart drawn at its own width and scaled as one picture to the box it is in (DESIGN.md, Charts on slides). Where
// the box's height binds first, the chart draws wider, up to WIDEST, so the picture fills the box's width; a wider
// chart stacks its dots lower, so it still fits. It waits for its first measure before it shows, so it never draws at
// the wrong size.
const WIDEST = 1400;
function Scaled({ children }: { children: ReactNode }) {
  const box = useRef<HTMLDivElement>(null);
  const picture = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(DRAWN_WIDTH);
  const [scale, setScale] = useState(0);
  useLayoutEffect(() => {
    const outer = box.current;
    const inner = picture.current;
    if (!outer || !inner) return;
    const fit = () => {
      if (inner.offsetHeight === 0) return;
      const byWidth = outer.clientWidth / inner.offsetWidth;
      const byHeight = outer.clientHeight / inner.offsetHeight;
      if (byHeight < byWidth - 0.01 && inner.offsetWidth < WIDEST) setWidth(Math.min(WIDEST, Math.floor(outer.clientWidth / byHeight)));
      setScale(Math.min(1, byWidth, byHeight));
    };
    fit();
    const observer = new ResizeObserver(fit);
    observer.observe(outer);
    observer.observe(inner);
    return () => observer.disconnect();
  }, []);
  return (
    <div ref={box} className="relative h-full overflow-hidden" data-scaled-chart={scale}>
      <div ref={picture} className="absolute top-0 left-0 origin-top-left" style={{ width, transform: `scale(${scale})`, visibility: scale ? undefined : "hidden" }}>
        {children}
      </div>
    </div>
  );
}

// The answer on the canvas, in place of the demo's box and points: the button that hides it beside the title, which
// holds its place, then the chart's card and its lines across the slide. Focus goes to that button, and back to the
// one that showed the answer.
export function RecordedSlide({
  recording,
  title,
  titleId,
  twin,
  onHide,
}: {
  recording: Recording;
  title: ReactNode;
  titleId: string;
  twin: boolean;
  onHide: () => void;
}) {
  const hide = useRef<HTMLButtonElement>(null);
  const lineId = useId();
  useEffect(() => hide.current?.focus(), []);
  return (
    <div className="absolute flex flex-col" style={{ left: 48, top: 64, width: 864, bottom: 32 }} data-recorded-view>
      <div className="flex shrink-0 items-start justify-between gap-6">
        <h1 id={titleId} tabIndex={-1} className="min-w-0 text-balance text-ink-heading outline-none" style={{ ...type("title", "present").style, maxWidth: 600 }}>
          {title}
        </h1>
        <RecordedButton open onClick={onHide} buttonRef={hide} />
      </div>
      <figure data-source-key={TOOL_KEY} data-recorded-answer aria-labelledby={lineId} className="mt-4 flex min-h-0 flex-1 flex-col">
        <div className="min-h-0 flex-1 rounded-md border border-line bg-surface p-3" data-chart={twin ? "table" : "chart"}>
          {twin ? (
            <div tabIndex={0} role="region" aria-labelledby={lineId} data-scroll-region className="h-full overflow-auto">
              <RangeFigure result={recording.result} twin />
            </div>
          ) : (
            <Scaled>
              <RangeFigure result={recording.result} twin={false} />
            </Scaled>
          )}
        </div>
        <div className="mt-3 flex shrink-0 flex-col gap-1">
          <RecordedLine recording={recording} id={lineId} />
          <RangeFigureLines result={recording.result} />
        </div>
      </figure>
    </div>
  );
}

// The answer in the reading view, under the demo's points: the chart at the column's width, its lines, and its table.
export function RecordedFigure({ recording }: { recording: Recording }) {
  const [table, setTable] = useState(false);
  const lineId = useId();
  const tableId = useId();
  return (
    <figure data-source-key={TOOL_KEY} data-recorded-answer aria-labelledby={lineId} className="mt-6 rounded-md border border-line bg-surface p-4">
      <RangeFigure result={recording.result} twin={false} />
      <div className="mt-4 flex flex-col gap-2">
        <RecordedLine recording={recording} id={lineId} />
        <RangeFigureLines result={recording.result} />
      </div>
      <div className="mt-4">
        <Button variant="ghost" flush icon={table ? ChevronUp : ChevronDown} aria-expanded={table} aria-controls={tableId} onClick={() => setTable((now) => !now)}>
          {table ? deckCopy.reading.hideTable : deckCopy.reading.showTable}
        </Button>
        <div id={tableId} hidden={!table} className="mt-2">
          {table && <RangeFigure result={recording.result} twin />}
        </div>
      </div>
    </figure>
  );
}
