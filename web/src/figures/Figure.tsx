// How a figure draws (the 47 brief, sections 4.1 and 4.2): a diagram is its exported SVG inlined at 1:1, so its
// title and description name it (role="img", aria-labelledby) and it uses the app's fonts; the hairline figure is
// the hairline kernel, vendored unchanged, mounting the figure file in a [data-hairline] element with the strata-wb
// palette set through the kernel's custom properties. Neither carries a logo or a word that is not in the drawing's
// own source. When a drawing cannot draw, its text version takes its place (FigureText).
import { useEffect, useLayoutEffect, useMemo, useRef, useState, type RefObject } from "react";
import { deckCopy, figureCopy } from "../deck/copy";
import { FIGURES, inline, type FigureId } from "./registry";
import kernelSource from "./hairline/kernel.js?raw";
import coreSampleSource from "./hairline/core-sample.js?raw";

type HairlineApi = {
  inject: (root: Document) => void;
  mk: (tag: string, attrs: Record<string, string>, parent: Element) => SVGSVGElement;
};
type HairlineFigureDef = {
  name: string;
  means: string;
  range: [number, number, number];
  mount: (host: { stage: HTMLElement; svg: SVGSVGElement; read: { textContent: string } }, value: number) => { set: (v: number) => void; destroy: () => void };
};

let kernel: HairlineApi | null = null;

// The kernel is a classic script that defines HL; it runs once, unchanged, and gives back HL.
function hairlineKernel(): HairlineApi {
  kernel ??= new Function(`${kernelSource}\nreturn HL;`)() as HairlineApi;
  return kernel;
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

export const CORE_SAMPLE_MEANS = (() => {
  try {
    return hairlineFigure(coreSampleSource).means;
  } catch {
    return figureCopy["core-sample"].title;
  }
})();

// The strata-wb palette for hairline figures (DESIGN.md section 11), light only.
const HAIRLINE_PALETTE = {
  "--hairline-plate": "#f5f7f9",
  "--hairline-hi": "#0071bc",
  "--hairline-edge": "#586e84",
  "--hairline-mid": "#bdccdb",
  "--hairline-lo": "#dae3eb",
} as Record<string, string>;

export function HairlineFigure({ onFail, className }: { onFail: () => void; className?: string }) {
  const host = useRef<HTMLDivElement>(null);
  const [read, setRead] = useState(figureCopy["core-sample"].readout.rest);
  useEffect(() => {
    const stage = host.current;
    if (!stage) return;
    try {
      const HL = hairlineKernel();
      const figure = hairlineFigure(coreSampleSource);
      HL.inject(document);
      const svg = HL.mk("svg", { viewBox: "0 0 400 320", "aria-hidden": "true" }, stage);
      const readout = figureCopy["core-sample"].readout as Record<string, string>;
      const handle = figure.mount(
        {
          stage,
          svg,
          read: {
            get textContent() {
              return "";
            },
            set textContent(value: string) {
              setRead(readout[value] ?? readout.rest);
            },
          },
        },
        figure.range[1],
      );
      return () => {
        handle.destroy();
        svg.remove();
      };
    } catch {
      onFail();
    }
  }, [onFail]);
  return (
    <div
      ref={host}
      data-hairline="core-sample"
      data-hairline-theme="light"
      role="img"
      aria-label={CORE_SAMPLE_MEANS}
      className={className}
      style={HAIRLINE_PALETTE}
    >
      <span aria-hidden="true" data-hairline-read className="absolute top-2 left-3 z-10 text-caption text-ink-muted">
        {read}
      </span>
    </div>
  );
}

export function Diagram({ id }: { id: FigureId }) {
  const figure = FIGURES[id];
  const markup = useMemo(() => (figure.svg ? inline(figure.svg) : ""), [figure.svg]);
  return <div data-figure={id} className="block shrink-0" dangerouslySetInnerHTML={{ __html: markup }} />;
}

// A figure's text version: its steps as an ordered list, in small.
export function FigureText({ id, listId }: { id: FigureId; listId?: string }) {
  return (
    <ol id={listId} className="list-decimal space-y-1 pl-6 text-small text-ink" data-figure-text={id}>
      {figureCopy[id].steps.map((step) => (
        <li key={step}>{step}</li>
      ))}
    </ol>
  );
}

// The words that stand in for a drawing that did not draw.
export function FigureFailed({ id }: { id: FigureId }) {
  return (
    <div data-figure-failed={id}>
      <p className="text-caption text-ink-muted">{deckCopy.states.figureFailed}</p>
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
