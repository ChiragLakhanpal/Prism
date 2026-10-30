// How a figure draws (the 47 brief, sections 4.1 and 4.2; the second draft's brief, sections 4 to 6): a diagram is
// its exported SVG inlined at 1:1, so its title and description name it (role="img", aria-labelledby) and it uses the
// app's fonts; a hairline figure is the hairline kernel, vendored unchanged, mounting the figure file in a
// [data-hairline] element with a palette set through the kernel's custom properties. Neither carries a logo or a word
// that is not in the drawing's own source. When a drawing cannot draw, its text version takes its place (FigureText).
//
// The deck shows a diagram a step at a time: every part marked data-motion-item whose data-step is above the step it
// is given gets data-unreached, which the deck's stylesheet hides (styles/deck.css). With no step, it draws whole.
import { useEffect, useLayoutEffect, useMemo, useRef, useState, type RefObject } from "react";
import { figureCopy, figureStates } from "../deck/copy";
import { FIGURES, inline, type FigureId } from "./registry";
import kernelSource from "./hairline/kernel.js?raw";
import coreSampleSource from "./hairline/core-sample.js?raw";

type HairlineApi = {
  inject: (root: Document) => void;
  mk: (tag: string, attrs: Record<string, string>, parent: Element) => SVGSVGElement;
  tour: (stage: HTMLElement, stops: ([number, number] | null)[], onStop?: (i: number) => void) => { stop: () => void };
  reducedMotion: () => boolean;
};
type HairlineFigureDef = {
  figureKey: string;
  means: string;
  range: [number, number, number];
  tour: ([number, number] | null)[] | null;
  mount: (host: { stage: HTMLElement; svg: SVGSVGElement; read: { textContent: string } }, value: number) => { set: (v: number) => void; destroy: () => void };
};

let kernel: HairlineApi | null = null;

// The kernel is a classic script that defines HL; it runs once, unchanged, and gives back HL.
function hairlineKernel(): HairlineApi {
  kernel ??= new Function(`${kernelSource}\nreturn HL;`)() as HairlineApi;
  return kernel;
}

// The hairline figure files beside the kernel, by name. How Strata works draws only core-sample; the deck adds its
// openers' figures when it loads (registerHairlines), so they stay out of the app's first download, which a cold
// load on the 3G budget pays for (home.spec.ts, hub.spec.ts).
const HAIRLINE_SOURCES: Record<string, string> = { "core-sample": coreSampleSource };

// Adds hairline figure files, by their paths, as import.meta.glob gives them: ".../hairline/filter.js" is "filter".
export function registerHairlines(sources: Record<string, string>) {
  for (const [path, source] of Object.entries(sources)) HAIRLINE_SOURCES[path.slice(path.lastIndexOf("/") + 1, -3)] = source;
}

// A figure file ends with hairline({ ... }), as the skill writes it; this is that call.
function hairlineFigure(source: string): HairlineFigureDef {
  let found: HairlineFigureDef | null = null;
  new Function("HL", "hairline", source)(hairlineKernel(), (figure: HairlineFigureDef) => {
    found = figure;
  });
  if (!found) throw new Error("hairline");
  return found;
}

// Whether a hairline figure of that name is here to draw.
export function hasHairline(figureKey: string): boolean {
  return figureKey in HAIRLINE_SOURCES;
}

export const CORE_SAMPLE_MEANS = (() => {
  try {
    return hairlineFigure(HAIRLINE_SOURCES["core-sample"]).means;
  } catch {
    return figureCopy["core-sample"].title;
  }
})();

// The palettes for hairline figures, set through the kernel's custom properties: the strata-wb light palette
// (DESIGN.md section 11), and the navy one for the deck's bookends and topic openers (the second draft's brief,
// section 6).
export const HAIRLINE_PALETTES = {
  light: {
    "--hairline-plate": "#f5f7f9",
    "--hairline-hi": "#0071bc",
    "--hairline-edge": "#586e84",
    "--hairline-mid": "#bdccdb",
    "--hairline-lo": "#dae3eb",
  },
  navy: {
    "--hairline-plate": "#002244",
    "--hairline-hi": "#169af3",
    "--hairline-edge": "#dae3eb",
    "--hairline-mid": "#8a9db1",
    "--hairline-lo": "#2c4560",
  },
} as Record<"light" | "navy", Record<string, string>>;

// A hairline figure, mounted while it is on screen. With play on, it walks its own tour, as the skill's page does
// when it plays; a reader who asked for less motion sees it at rest. readout, when given, receives each word the
// figure writes to its read-out.
export function Hairline({
  figureKey,
  paletteKey = "light",
  play = false,
  label,
  onFail,
  onRead,
  className,
}: {
  figureKey: string;
  paletteKey?: "light" | "navy";
  play?: boolean;
  label: string;
  onFail?: () => void;
  onRead?: (word: string) => void;
  className?: string;
}) {
  const host = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const stage = host.current;
    const source = HAIRLINE_SOURCES[figureKey];
    if (!stage || !source) {
      onFail?.();
      return;
    }
    try {
      const HL = hairlineKernel();
      const figure = hairlineFigure(source);
      HL.inject(document);
      const svg = HL.mk("svg", { viewBox: "0 0 400 320", "aria-hidden": "true" }, stage);
      const handle = figure.mount(
        {
          stage,
          svg,
          read: {
            get textContent() {
              return "";
            },
            set textContent(value: string) {
              onRead?.(value);
            },
          },
        },
        figure.range[1],
      );
      const walk = play && figure.tour?.length && !HL.reducedMotion() ? HL.tour(stage, figure.tour) : null;
      return () => {
        walk?.stop();
        handle.destroy();
        svg.remove();
      };
    } catch {
      onFail?.();
    }
  }, [figureKey, play, onFail, onRead]);
  return (
    <div
      ref={host}
      data-hairline={figureKey}
      data-hairline-theme={paletteKey}
      role="img"
      aria-label={label}
      className={className}
      style={HAIRLINE_PALETTES[paletteKey]}
    />
  );
}

// The core sample as How Strata works shows it, with its read-out in the copy file's words.
export function HairlineFigure({ onFail, className }: { onFail: () => void; className?: string }) {
  const [read, setRead] = useState(figureCopy["core-sample"].readout.rest);
  const readout = figureCopy["core-sample"].readout as Record<string, string>;
  const onRead = useMemo(() => (value: string) => setRead(readout[value] ?? readout.rest), [readout]);
  return (
    <div className="relative h-full w-full">
      <Hairline figureKey="core-sample" label={CORE_SAMPLE_MEANS} onFail={onFail} onRead={onRead} className={className} />
      <span aria-hidden="true" data-hairline-read className="absolute top-2 left-3 z-10 text-caption text-ink-muted">
        {read}
      </span>
    </div>
  );
}

// A diagram, whole, or at a step when the deck gives one.
export function Diagram({ id, step }: { id: FigureId; step?: number }) {
  const figure = FIGURES[id];
  const box = useRef<HTMLDivElement>(null);
  const markup = useMemo(() => (figure.svg ? inline(figure.svg) : ""), [figure.svg]);
  // A part a press brings in draws itself (styles/deck.css). Each line or outline with a solid stroke gets pathLength
  // 1, so a single dash as long as the stroke can draw it from its start. A fill with no stroke, or a dashed stroke,
  // fades in instead.
  useLayoutEffect(() => {
    const root = box.current;
    if (!root) return;
    for (const shape of root.querySelectorAll<SVGElement>("[data-motion-item] :is(path, line, polyline, polygon, rect, circle, ellipse)")) {
      const stroke = shape.getAttribute("stroke");
      const solid = stroke !== null && stroke !== "none" && !shape.hasAttribute("stroke-dasharray");
      if (solid) shape.setAttribute("pathLength", "1");
      shape.toggleAttribute("data-draw", solid);
      shape.toggleAttribute("data-fade", !solid);
    }
  }, [markup]);
  useLayoutEffect(() => {
    const root = box.current;
    if (!root) return;
    for (const item of root.querySelectorAll<SVGElement>("[data-motion-item]")) {
      const at = Number(item.getAttribute("data-step"));
      item.toggleAttribute("data-unreached", step !== undefined && at > step);
      item.toggleAttribute("data-current", step !== undefined && at === step);
    }
  }, [markup, step]);
  return <div ref={box} data-figure={id} data-figure-step={step ?? figure.steps} className="block shrink-0" dangerouslySetInnerHTML={{ __html: markup }} />;
}

// A figure's text version: its steps as an ordered list, in small, up to a step when one is given.
export function FigureText({ id, listId, upTo }: { id: FigureId; listId?: string; upTo?: number }) {
  const steps = figureCopy[id].steps as readonly string[];
  return (
    <ol id={listId} className="list-decimal space-y-1 pl-6 text-small text-ink" data-figure-text={id}>
      {steps.slice(0, upTo ?? steps.length).map((step) => (
        <li key={step}>{step}</li>
      ))}
    </ol>
  );
}

// The words that stand in for a drawing that did not draw.
export function FigureFailed({ id }: { id: FigureId }) {
  return (
    <div data-figure-failed={id}>
      <p className="text-caption text-ink-muted">{figureStates.failed}</p>
      <div className="mt-2">
        <FigureText id={id} />
      </div>
    </div>
  );
}

// Whether an element's content is wider than the element: a drawing wider than its column scrolls sideways.
export function useOverflow(ref: RefObject<HTMLElement | null>, width: number): boolean {
  const [over, setOver] = useState(false);
  useLayoutEffect(() => {
    const element = ref.current;
    if (!element) return;
    const update = () => setOver(element.clientWidth + 1 < width);
    update();
    const observer = new ResizeObserver(update);
    observer.observe(element);
    return () => observer.disconnect();
  }, [ref, width]);
  return over;
}
