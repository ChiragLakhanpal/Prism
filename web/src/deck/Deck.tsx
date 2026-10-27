// The deck at /present (ticket 47; the second draft's brief): Strata's story in five topics between the bookends,
// outside the app's frame, with nothing in the app linking to it. Its address lives in the proposal and the README.
//
// - /present and /present/{n}: presentation mode, the 960 by 540 canvas scaled as one unit, when the window can show
//   it at its own size or larger ((min-width: 63rem) and (min-height: 40.25rem)); otherwise the reading view. The
//   arrow keys, Page Up and Page Down move one press at a time: a press brings in a slide's next point or figure step,
//   and after its last step moves to the next slide. Home and End go to the first and the last slide. Each slide
//   change replaces the address.
// - /present/page: the reading view at any size, every slide whole as a section of one page, with its notes.
// - /present/notes: the speaker notes, in their own window, kept in step with the deck through a BroadcastChannel.
//
// The deck reads its numbers from /deck/data.json (web/src/deck/data.ts), the measures snapshot the proposal cites.
import { useCallback, useEffect, useId, useLayoutEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { ChevronDown, ChevronLeft, ChevronRight, ChevronUp, ExternalLink as ExternalIcon, Maximize, Minimize, Table2 } from "lucide-react";
import { Alert } from "../components/Alert";
import { Button } from "../components/Button";
import { ExternalLink } from "../components/ExternalLink";
import { Footer } from "../components/Frame";
import { TextLink } from "../components/TextLink";
import { copy } from "../copy";
import { cx } from "../lib/cx";
import { formatDate } from "../lib/format";
import { Diagram, FigureFailed, FigureText, Hairline, hasHairline, useOverflow } from "../figures/Figure";
import { FIGURES, SLOTS } from "../figures/registry";
import { deckCopy, figureCopy } from "./copy";
import { loadDeck, type DeckData } from "./data";
import { SlideFrame, type Theme } from "./Frame";
import { SourceLine, Step, WholeSlides } from "./layouts";
import { type, type Mode } from "./ramp";
import { buildSlides, figureStepText, TITLE_ID, type Slide } from "./slides";
import { arrive, moved, moveFor, segments, TOPIC_ORDER, type Move, type Place } from "./talk";
import { slideInAddress, type DeckView } from "./view";
import "./deck.css";

const CANVAS = { width: 960, height: 540 };
const PRESENT = "(min-width: 63rem) and (min-height: 40.25rem)";
const CHANNEL = "strata-deck";
// How long the control bar stays after the pointer last moved, in full screen.
const BAR_REST_MS = 2500;
const GHOST =
  "inline-flex h-11 shrink-0 items-center justify-center gap-2 rounded-sm border-2 border-transparent px-4 text-button " +
  "transition-paint duration-150 select-none disabled:invisible";

type Message = { type: "at"; n: number; step: number } | { type: "where" } | { type: "move"; move: Move } | { type: "go"; n: number };

function useMatch(query: string): boolean {
  const [matches, setMatches] = useState(() => window.matchMedia(query).matches);
  useEffect(() => {
    const list = window.matchMedia(query);
    const update = () => setMatches(list.matches);
    list.addEventListener("change", update);
    return () => list.removeEventListener("change", update);
  }, [query]);
  return matches;
}

export function DeckApp({ view }: { view: DeckView }) {
  const [data, setData] = useState<DeckData | null>(null);
  const [failed, setFailed] = useState(false);
  const load = useCallback(() => {
    setFailed(false);
    loadDeck().then(setData, () => setFailed(true));
  }, []);
  useEffect(load, [load]);
  const big = useMatch(PRESENT);
  const slides = useMemo(() => (data ? buildSlides(data) : null), [data]);
  if (failed) {
    return (
      <main className="flex min-h-dvh items-center justify-center bg-surface-2 p-6" data-deck="error">
        <div className="max-w-prose">
          <Alert
            state="error"
            live="alert"
            action={
              <Button variant="secondary" onClick={() => window.location.reload()}>
                {deckCopy.states.reload}
              </Button>
            }
          >
            {deckCopy.states.loadError}
          </Alert>
        </div>
      </main>
    );
  }
  if (!data || !slides) return <Loading />;
  if (view.kind === "notes") return <NotesView slides={slides} />;
  if (view.kind === "page" || !big) return <ReadingView slides={slides} data={data} page={view.kind === "page"} big={big} />;
  // The slide the address shows now, which presentation mode keeps current, so a window that shrinks to the reading
  // view and grows again comes back to the same slide.
  return <Presentation slides={slides} data={data} start={slideInAddress() ?? 1} />;
}

// The stage at its final size, with the footer sentence, while the deck's data arrive.
function Loading() {
  return (
    <main className="flex min-h-dvh flex-col items-center justify-center bg-surface-2 p-6" data-deck="loading">
      <div className="border border-line bg-page" style={{ width: "min(100%, 960px)", aspectRatio: "16 / 9" }}>
        <p className="p-6 text-caption text-ink-muted">{copy.footer}</p>
      </div>
    </main>
  );
}

// ── One slide on the canvas ─────────────────────────────────────────────

function Presenter({ data, mode, navy }: { data: DeckData; mode: Mode; navy: boolean }) {
  if (!data.presenter.name && !data.presenter.date) return null;
  return (
    <div className={mode === "present" ? "mt-8" : "mt-4"} data-presenter>
      {data.presenter.name && (
        <p className={navy ? "font-semibold text-surface" : "font-semibold text-ink"} {...type("note", mode)}>
          {data.presenter.name}
        </p>
      )}
      {data.presenter.date && (
        <p className={navy ? "text-surface/75" : "text-ink-muted"} {...type("note", mode)}>
          {formatDate(data.presenter.date)}
        </p>
      )}
    </div>
  );
}

// A hairline figure in its box, mounted only while its slide is on screen, so it plays from its rest pose on arrival.
// A figure the deck lacks gives way to the core sample, the deck's first figure.
function HairlineBox({ figureKey, label, live, style }: { figureKey: string; label: string; live: boolean; style: React.CSSProperties }) {
  const [broken, setBroken] = useState(false);
  const onFail = useCallback(() => setBroken(true), []);
  const drawn = hasHairline(figureKey) ? figureKey : "core-sample";
  return (
    <div className="absolute" style={style} data-deck-hairline={drawn}>
      {live && !broken && <Hairline figureKey={drawn} paletteKey="navy" play label={label} onFail={onFail} />}
    </div>
  );
}

// The drawing of a figure slide, scaled to its box, at the step the deck hands it (whole when it hands none). A figure
// whose drawing is missing shows its text version instead.
function FigureBox({ slide, step, className, style }: { slide: Slide; step?: number; className?: string; style?: React.CSSProperties }) {
  const id = slide.figure!.id;
  if (!FIGURES[id].svg) return <FigureFailed id={id} />;
  return (
    <div className={cx("relative", className)} style={style} data-deck-figure={id} data-figure-frame={FIGURES[id].slot}>
      <Diagram id={id} step={step} />
      <div className="sr-only">
        <FigureText id={id} upTo={step} />
      </div>
    </div>
  );
}

function SlideCanvas({
  slide,
  data,
  slides,
  total,
  current,
  step,
  twin,
}: {
  slide: Slide;
  data: DeckData;
  slides: Slide[];
  total: number;
  current: boolean;
  // How many presses the slide shows; a slide off screen is drawn whole.
  step: number;
  twin: boolean;
}) {
  const titleId = TITLE_ID(slide.n);
  const navy = slide.theme === "navy";
  const figureSteps = slide.figure?.steps ?? 0;
  const figureStep = slide.figure ? Math.min(step, figureSteps) : 0;
  const own = Math.max(0, step - figureSteps);
  const topic = slide.part === "open" || slide.part === "close" ? null : slide.part;
  const parts = slides.map((one) => one.part);
  const bare = slide.kind === "title" || slide.kind === "close";
  return (
    <section
      aria-roledescription={deckCopy.roleSlide}
      aria-labelledby={titleId}
      hidden={!current}
      data-slide={slide.n}
      data-slide-id={slide.id}
      data-step-current={step}
      data-step-count={slide.steps}
      className={cx("absolute inset-0 overflow-hidden", navy ? "bg-navy text-surface" : "bg-page text-ink")}
    >
      <SlideFrame
        theme={slide.theme}
        tracker={!bare && slide.kind !== "agenda"}
        segments={segments(parts, slide.n)}
        topic={topic}
        counter={bare ? null : deckCopy.counter(String(slide.n), String(total))}
      >
        {slide.kind === "title" && <TitleSlide slide={slide} data={data} current={current} />}
        {slide.kind === "close" && <CloseSlide slide={slide} data={data} current={current} />}
        {slide.kind === "opener" && <OpenerSlide slide={slide} current={current} />}
        {slide.kind === "agenda" && <AgendaSlide slide={slide} step={step} />}
        {slide.kind === "figure" && (
          <div className="absolute flex flex-col" style={{ left: 48, top: 64, width: 864, bottom: 32 }}>
            <h1 id={titleId} tabIndex={-1} className="shrink-0 text-balance text-ink-heading outline-none" style={{ ...type("figureTitle", "present").style, maxWidth: 820 }}>
              {slide.title}
            </h1>
            {slide.figure!.wide ? (
              <>
                <FigureBox slide={slide} step={current ? figureStep : undefined} className="mt-3 min-h-0 flex-1" />
                {slide.body && <div className="mt-2 shrink-0">{slide.body(current ? own : slide.steps, "present")}</div>}
              </>
            ) : (
              <div className="mt-3 flex min-h-0 flex-1 gap-8">
                <FigureBox slide={slide} step={current ? figureStep : undefined} className="shrink-0" style={{ width: SLOTS.half.width }} />
                <div className="flex min-w-0 flex-1 flex-col justify-center">{slide.body?.(current ? own : slide.steps, "present")}</div>
              </div>
            )}
            {slide.source && (
              <div className="mt-2 shrink-0">
                <SourceLine lead={slide.source.lead} mode="present">
                  {slide.source.text}
                </SourceLine>
              </div>
            )}
          </div>
        )}
        {slide.kind === "text" && (
          <div className="absolute flex flex-col" style={{ left: 48, top: 48, width: 864, bottom: 32 }}>
            <Fit live={current} className="flex min-h-0 flex-1 flex-col justify-center gap-8">
              <h1 id={titleId} tabIndex={-1} className="text-balance text-ink-heading outline-none" style={{ ...type("title", "present").style, maxWidth: 800 }}>
                {slide.title}
              </h1>
              {slide.chart ? (
                <div className="grid grid-cols-2 items-center gap-8">
                  <figure data-source-key={slide.chart.source} className="relative rounded-md border border-line bg-surface p-4" data-chart={twin ? "table" : "chart"}>
                    {/* A chart measures its own text as it draws, which a hidden slide cannot, so only the slide on
                        screen draws its chart. */}
                    {!current ? null : twin ? (
                      <div tabIndex={0} role="region" aria-labelledby={titleId} data-scroll-region className="max-h-64 overflow-auto">
                        {slide.chart.table}
                      </div>
                    ) : (
                      slide.chart.drawing("present", titleId)
                    )}
                  </figure>
                  <div>{slide.body?.(current ? step : slide.steps, "present")}</div>
                </div>
              ) : (
                slide.body?.(current ? step : slide.steps, "present")
              )}
            </Fit>
            {slide.source && (
              <div className="mt-2 shrink-0">
                <SourceLine lead={slide.source.lead} mode="present">
                  {slide.source.text}
                </SourceLine>
              </div>
            )}
          </div>
        )}
      </SlideFrame>
    </section>
  );
}

const MIN_ZOOM = 0.6;
const ZOOM_STEP = 0.025;

// A text slide's title and body, in the space the frame leaves. Content taller than that space (a dense table, or more
// than a slide should hold) zooms out as a whole, a step at a time, until it fits, so nothing runs into the header or
// the footer; content that fits stays on the ramp. Items not yet reached keep their places, so the zoom holds while
// the slide steps. A slide off screen has no size, so it measures only while it shows, and again once the fonts are in.
function Fit({ live, className, children }: { live: boolean; className: string; children: ReactNode }) {
  const box = useRef<HTMLDivElement>(null);
  const [zoom, setZoom] = useState(1);
  const [fonts, setFonts] = useState(0);
  useEffect(() => {
    let on = true;
    document.fonts?.ready.then(() => {
      if (!on) return;
      setZoom(1);
      setFonts((k) => k + 1);
    });
    return () => {
      on = false;
    };
  }, []);
  useLayoutEffect(() => {
    const el = box.current;
    if (!live || !el || zoom <= MIN_ZOOM) return;
    if (el.scrollHeight > el.clientHeight + 1) setZoom((z) => Math.max(MIN_ZOOM, Math.round((z - ZOOM_STEP) * 1000) / 1000));
  }, [live, zoom, fonts]);
  return (
    <div ref={box} data-fit-zoom={zoom} className={cx(className, "overflow-hidden")}>
      <div className="flex flex-col justify-center gap-8" style={zoom < 1 ? { zoom } : undefined}>
        {children}
      </div>
    </div>
  );
}

function TitleSlide({ slide, data, current }: { slide: Slide; data: DeckData; current: boolean }) {
  return (
    <>
      <div className="absolute flex flex-col justify-center" style={{ left: 48, top: 72, width: 500, bottom: 56 }}>
        <p className="text-surface/75" style={{ fontSize: 20, lineHeight: 1.2, fontWeight: 700 }}>
          {deckCopy.wordmark}
        </p>
        <h1 id={TITLE_ID(slide.n)} tabIndex={-1} className="mt-4 text-balance text-surface outline-none" {...type("statement", "present")}>
          {slide.title}
        </h1>
        <p className="mt-6 text-surface/75" {...type("note", "present")}>
          {deckCopy.slides.welcome.line}
        </p>
        <Presenter data={data} mode="present" navy />
      </div>
      <HairlineBox figureKey={slide.hairline ?? "core-sample"} label={slide.hairlineLabel ?? ""} live={current} style={{ left: 572, top: 112, width: 360, height: 288 }} />
    </>
  );
}

function OpenerSlide({ slide, current }: { slide: Slide; current: boolean }) {
  const topic = slide.topic!;
  return (
    <>
      <HairlineBox figureKey={slide.hairline!} label={slide.hairlineLabel ?? ""} live={current} style={{ left: 300, top: 60, width: 360, height: 288 }} />
      <div className="absolute flex flex-col items-center text-center" style={{ left: 48, top: 364, width: 864 }}>
        <p data-chrome data-topic-number className="text-surface/60 tabular-nums" style={{ fontSize: 14, lineHeight: 1, fontWeight: 600 }}>
          {TOPIC_ORDER.indexOf(topic) + 1}
        </p>
        <h1 id={TITLE_ID(slide.n)} tabIndex={-1} className="mt-3 text-surface outline-none" {...type("topic", "present")}>
          {slide.title}
        </h1>
        <p className="mt-4 text-balance text-surface/75" style={{ ...type("note", "present").style, maxWidth: 620 }}>
          {deckCopy.topics[topic].line}
        </p>
      </div>
    </>
  );
}

function AgendaSlide({ slide, step }: { slide: Slide; step: number }) {
  return (
    <div className="absolute flex flex-col justify-center gap-8" style={{ left: 48, top: 48, width: 864, bottom: 32 }}>
      <h1 id={TITLE_ID(slide.n)} tabIndex={-1} className="text-ink-heading outline-none" {...type("title", "present")}>
        {slide.title}
      </h1>
      <Agenda step={step} mode="present" />
    </div>
  );
}

// The five topics, a press each: the topic's number, its name and its line.
function Agenda({ step, mode }: { step: number; mode: Mode }) {
  return (
    <ol className={cx("flex flex-col", mode === "present" ? "gap-4" : "gap-3")}>
      {TOPIC_ORDER.map((key, index) => (
        <Step key={key} n={index + 1} at={step} as="li" className="flex gap-6">
          <span data-chrome aria-hidden="true" className="w-6 shrink-0 text-info-icon tabular-nums" {...type("head", mode)}>
            {index + 1}
          </span>
          <div className="min-w-0">
            <p className="text-ink-heading" {...type("head", mode)}>
              {deckCopy.topics[key].name}
            </p>
            <p className="text-ink-muted" {...type("note", mode)}>
              {deckCopy.topics[key].line}
            </p>
          </div>
        </Step>
      ))}
    </ol>
  );
}

function CloseSlide({ slide, data, current }: { slide: Slide; data: DeckData; current: boolean }) {
  const w = deckCopy.slides.thanks;
  const urls = data.urls;
  return (
    <>
      <div className="absolute flex flex-col justify-center" style={{ left: 48, top: 72, width: 456, bottom: 56 }}>
        <h1 id={TITLE_ID(slide.n)} tabIndex={-1} className="text-surface outline-none" {...type("topic", "present")}>
          {slide.title}
        </h1>
        <Presenter data={data} mode="present" navy />
        <p className="mt-6 text-surface" {...type("body", "present")}>
          {w.ask}
        </p>
        <ul className="mt-8 flex flex-col gap-2" {...type("note", "present")} data-close-links>
          <li>
            <a href="/" target="_blank" rel="noreferrer" className="text-surface underline underline-offset-3 focus-visible:outline-focus-on-dark">
              {w.links.app}
            </a>
          </li>
          {(["proposal", "dashboard", "repo"] as const).map((key) =>
            urls[key] ? (
              <li key={key}>
                <a href={urls[key]!} target="_blank" rel="noreferrer" className="text-surface underline underline-offset-3 focus-visible:outline-focus-on-dark">
                  {w.links[key]}
                </a>
              </li>
            ) : null,
          )}
        </ul>
      </div>
      <HairlineBox figureKey={slide.hairline ?? "core-sample"} label={deckCopy.slides.welcome.figure} live={current} style={{ left: 520, top: 104, width: 400, height: 320 }} />
    </>
  );
}

// ── Presentation mode ───────────────────────────────────────────────────

function useFullScreen(): { able: boolean; on: boolean; toggle: () => void } {
  const able = typeof document !== "undefined" && Boolean(document.fullscreenEnabled);
  const [on, setOn] = useState(Boolean(document.fullscreenElement));
  useEffect(() => {
    const update = () => setOn(Boolean(document.fullscreenElement));
    document.addEventListener("fullscreenchange", update);
    return () => document.removeEventListener("fullscreenchange", update);
  }, []);
  const toggle = () => {
    if (document.fullscreenElement) void document.exitFullscreen();
    else void document.documentElement.requestFullscreen();
  };
  return { able, on, toggle };
}

// The canvas's scale: as large as the window allows, with room for the control bar unless the deck is full screen.
function useScale(full: boolean): number {
  const measure = useCallback(
    () =>
      full
        ? Math.max(0.1, Math.min(window.innerWidth / CANVAS.width, window.innerHeight / CANVAS.height))
        : Math.max(0.1, Math.min((window.innerWidth - 48) / CANVAS.width, (window.innerHeight - 104) / CANVAS.height)),
    [full],
  );
  const [scale, setScale] = useState(measure);
  useEffect(() => {
    setScale(measure());
    const update = () => setScale(measure());
    window.addEventListener("resize", update);
    return () => window.removeEventListener("resize", update);
  }, [measure]);
  return scale;
}

// In full screen the control bar rests out of sight, and comes back while the pointer moves or a control has focus.
function useBarAwake(full: boolean): boolean {
  const [awake, setAwake] = useState(true);
  useEffect(() => {
    if (!full) {
      setAwake(true);
      return;
    }
    let rest = window.setTimeout(() => setAwake(false), BAR_REST_MS);
    const wake = () => {
      setAwake(true);
      window.clearTimeout(rest);
      rest = window.setTimeout(() => setAwake(false), BAR_REST_MS);
    };
    window.addEventListener("pointermove", wake);
    return () => {
      window.clearTimeout(rest);
      window.removeEventListener("pointermove", wake);
    };
  }, [full]);
  return awake;
}

// What the live region says after a press: the new point's words, or the figure step's text version.
function pressWords(slide: Slide, step: number): string {
  if (step === 0) return "";
  const figureSteps = slide.figure?.steps ?? 0;
  if (slide.figure && step <= figureSteps) return figureStepText(slide.figure.id, step);
  const own = step - figureSteps;
  const item = document.querySelector(`section[data-slide='${slide.n}'] [data-step='${own}']`);
  return item?.textContent?.trim() ?? "";
}

function Presentation({ slides, data, start }: { slides: Slide[]; data: DeckData; start: number }) {
  const total = slides.length;
  const [place, setPlace] = useState<Place>(() => arrive(start, null, slides));
  const [twin, setTwin] = useState(false);
  const [announce, setAnnounce] = useState("");
  const full = useFullScreen();
  const scale = useScale(full.on);
  const awake = useBarAwake(full.on);
  const stage = useRef<HTMLDivElement>(null);
  const bar = useRef<HTMLElement>(null);
  const [barFocus, setBarFocus] = useState(false);
  const first = useRef(true);
  const channel = useRef<BroadcastChannel | null>(null);
  const at = useRef(place);
  at.current = place;
  const slide = slides[place.n - 1];

  const go = useCallback(
    (next: Place) => {
      const inside = stage.current?.contains(document.activeElement) ?? false;
      if (next.n !== at.current.n) {
        setTwin(false);
        if (inside) requestAnimationFrame(() => document.getElementById(TITLE_ID(next.n))?.focus());
      }
      setPlace(next);
    },
    [],
  );

  // The address and the tab's title follow the slide; Back leaves the deck instead of walking through slides.
  useLayoutEffect(() => {
    window.history.replaceState(window.history.state, "", `/present/${place.n}`);
    document.title = deckCopy.title(String(place.n), String(total));
  }, [place.n, total]);

  // The live region: the slide and its title on arrival, then each press's new words.
  const shown = useRef(place);
  useEffect(() => {
    const before = shown.current;
    shown.current = place;
    if (first.current) {
      first.current = false;
    } else if (before.n !== place.n) {
      setAnnounce(deckCopy.announce(String(place.n), String(total), document.getElementById(TITLE_ID(place.n))?.textContent?.trim() ?? ""));
    } else if (place.step > before.step) {
      setAnnounce(pressWords(slides[place.n - 1], place.step));
    }
    try {
      channel.current?.postMessage({ type: "at", n: place.n, step: place.step } satisfies Message);
    } catch {
      // The channel closed with the page; the notes window asks again when it opens.
    }
  }, [place, slides, total]);

  useEffect(() => {
    if (typeof BroadcastChannel === "undefined") return;
    const open = new BroadcastChannel(CHANNEL);
    channel.current = open;
    open.onmessage = (event: MessageEvent<Message>) => {
      const message = event.data;
      if (message.type === "where") open.postMessage({ type: "at", n: at.current.n, step: at.current.step } satisfies Message);
      if (message.type === "move") go(moved(at.current, message.move, slides));
      if (message.type === "go") go(arrive(message.n, at.current.n, slides));
    };
    open.postMessage({ type: "at", n: at.current.n, step: at.current.step } satisfies Message);
    return () => {
      if (channel.current === open) channel.current = null;
      open.close();
    };
  }, [go, slides]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const move = moveFor(event);
      if (move === null) return;
      event.preventDefault();
      const next = moved(at.current, move, slides);
      if (next.n !== at.current.n || next.step !== at.current.step) go(next);
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [go, slides]);

  const press = (move: Move) => go(moved(at.current, move, slides));
  const width = CANVAS.width * scale;
  const height = CANVAS.height * scale;
  const charted = Boolean(slide.chart);
  const showBar = !full.on || awake || barFocus;
  const atStart = place.n === 1 && place.step === 0;
  const atEnd = place.n === total && place.step >= slide.steps;
  return (
    <main
      className={cx("flex min-h-dvh flex-col items-center justify-center", full.on ? (slide.theme === "navy" ? "bg-navy" : "bg-page") : "bg-surface-2 p-6")}
      data-deck="present"
      data-full-screen={full.on ? "" : undefined}
    >
      <div ref={stage} className={cx("relative shrink-0 overflow-hidden", !full.on && "border border-line")} style={{ width, height }} data-stage>
        <div style={{ width: CANVAS.width, height: CANVAS.height, transform: `scale(${scale})`, transformOrigin: "0 0" }} data-canvas>
          {slides.map((one) => (
            <SlideCanvas
              key={one.n}
              slide={one}
              data={data}
              slides={slides}
              total={total}
              current={one.n === place.n}
              step={one.n === place.n ? place.step : one.steps}
              twin={one.n === place.n && twin}
            />
          ))}
        </div>
      </div>
      <nav
        ref={bar}
        aria-label={deckCopy.bar.label}
        onFocus={() => setBarFocus(true)}
        onBlur={(event) => {
          if (!bar.current?.contains(event.relatedTarget as Node | null)) setBarFocus(false);
        }}
        className={cx(
          "flex h-11 shrink-0 items-center justify-between gap-2 transition-opacity duration-200",
          full.on ? "fixed inset-x-0 bottom-3 mx-auto rounded-sm bg-surface/95 px-2 shadow-sm" : "mt-3",
          showBar ? "opacity-100" : "pointer-events-none opacity-0",
        )}
        style={{ width: full.on ? Math.min(width, 960) : width }}
        data-deck-bar
      >
        <div className="flex items-center gap-2">
          <button type="button" onClick={() => press("back")} disabled={atStart} className={cx(GHOST, "text-primary hover:bg-tint-hover")} data-previous>
            <ChevronLeft aria-hidden="true" className="size-4" />
            {deckCopy.bar.previous}
          </button>
          <button type="button" onClick={() => press("forward")} disabled={atEnd} className={cx(GHOST, "text-primary hover:bg-tint-hover")} data-next>
            {deckCopy.bar.next}
            <ChevronRight aria-hidden="true" className="size-4" />
          </button>
          {slide.steps > 0 && (
            <span data-chrome className="text-caption text-ink-muted tabular-nums" data-press-counter>
              {deckCopy.pressOf(String(place.step), String(slide.steps))}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {charted && (
            <button type="button" onClick={() => setTwin((now) => !now)} className={cx(GHOST, "text-primary hover:bg-tint-hover")} data-table-toggle>
              <Table2 aria-hidden="true" className="size-4" />
              {twin ? deckCopy.bar.showChart : deckCopy.bar.showTable}
            </button>
          )}
          <a href={`/present/page#slide-${place.n}`} className={cx(GHOST, "text-primary hover:bg-tint-hover")} data-read-as-page>
            {deckCopy.bar.readAsPage}
          </a>
          <a href="/present/notes" target="_blank" rel="noopener" aria-label={deckCopy.bar.notesName} className={cx(GHOST, "text-primary hover:bg-tint-hover")} data-notes-link>
            {deckCopy.bar.notes}
            <ExternalIcon aria-hidden="true" className="size-4" />
          </a>
          {full.able && (
            <button type="button" onClick={full.toggle} className={cx(GHOST, "text-primary hover:bg-tint-hover")} data-full-screen-toggle>
              {full.on ? <Minimize aria-hidden="true" className="size-4" /> : <Maximize aria-hidden="true" className="size-4" />}
              {full.on ? deckCopy.bar.leaveFullScreen : deckCopy.bar.fullScreen}
            </button>
          )}
        </div>
      </nav>
      <p role="status" className="sr-only" data-deck-status>
        {announce}
      </p>
    </main>
  );
}

// ── The reading view ────────────────────────────────────────────────────

function Disclosure({ show, hide, open: initially = false, children, testId }: { show: string; hide: string; open?: boolean; children: ReactNode; testId: string }) {
  const [open, setOpen] = useState(initially);
  const id = useId();
  useEffect(() => setOpen(initially), [initially]);
  return (
    <div data-disclosure={testId}>
      <Button variant="ghost" flush icon={open ? ChevronUp : ChevronDown} aria-expanded={open} aria-controls={id} onClick={() => setOpen((now) => !now)}>
        {open ? hide : show}
      </Button>
      <div id={id} hidden={!open} className="mt-2">
        {children}
      </div>
    </div>
  );
}

function ScrollFrame({ width, label, children }: { width: number; label: string; children: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);
  const over = useOverflow(ref, width);
  return (
    <div
      ref={ref}
      className="max-w-full overflow-x-auto"
      tabIndex={over ? 0 : undefined}
      role={over ? "region" : undefined}
      aria-label={over ? label : undefined}
      data-overflow={over ? "" : undefined}
    >
      <div style={{ width }}>{children}</div>
    </div>
  );
}

function ReadingSlide({ slide, data, total }: { slide: Slide; data: DeckData; total: number }) {
  const headingId = TITLE_ID(slide.n);
  const figure = slide.figure ? FIGURES[slide.figure.id] : null;
  const wide = figure && figure.slot !== "hairline" ? SLOTS[figure.slot].width : 0;
  const frameRef = useRef<HTMLDivElement>(null);
  const overflows = useOverflow(frameRef, wide);
  const topic = slide.topic ?? null;
  return (
    <section id={`slide-${slide.n}`} aria-labelledby={headingId} className="scroll-mt-6" data-reading-slide={slide.n}>
      <p data-chrome className="text-caption text-ink-muted">
        {deckCopy.slideOf(String(slide.n), String(total))}
      </p>
      {slide.kind === "title" ? (
        <>
          <p className="mt-2 text-h2 text-ink-heading">{deckCopy.wordmark}</p>
          <h1 id={headingId} className="mt-2 text-display text-ink-heading">
            {slide.title}
          </h1>
          <p className="mt-4 text-body text-ink-muted">{deckCopy.slides.welcome.line}</p>
          <Presenter data={data} mode="read" navy={false} />
        </>
      ) : (
        <h2 id={headingId} className="mt-2 text-h1 text-ink-heading">
          {slide.title}
        </h2>
      )}
      <div className="mt-6 flex max-w-full flex-col gap-6">
        {topic && <p className="max-w-prose text-body text-ink-muted">{deckCopy.topics[topic].line}</p>}
        {slide.kind === "agenda" && <Agenda step={TOPIC_ORDER.length} mode="read" />}
        {slide.kind === "close" && <p className="text-body text-ink">{deckCopy.slides.thanks.ask}</p>}
        {figure && (
          <div ref={frameRef}>
            {figure.svg ? (
              <ScrollFrame width={wide} label={deckCopy.reading.scrolls(figureCopy[figure.id].title)}>
                <Diagram id={figure.id} />
              </ScrollFrame>
            ) : (
              <FigureFailed id={figure.id} />
            )}
            {figure.svg && (
              <div className="mt-4">
                <Disclosure show={deckCopy.reading.showText} hide={deckCopy.reading.hideText} open={overflows} testId="text">
                  <FigureText id={figure.id} />
                </Disclosure>
              </div>
            )}
          </div>
        )}
        {slide.chart && (
          <div data-figure-frame="chart">
            <figure data-source-key={slide.chart.source} tabIndex={0} role="region" aria-labelledby={headingId} className="max-w-full overflow-x-auto rounded-md border border-line bg-surface p-4">
              {slide.chart.drawing("read", headingId)}
            </figure>
            <div className="mt-4">
              <Disclosure show={deckCopy.reading.showTable} hide={deckCopy.reading.hideTable} testId="table">
                <figure data-source-key={slide.chart.source} tabIndex={0} role="region" aria-labelledby={headingId} className="max-w-full overflow-x-auto">
                  {slide.chart.table}
                </figure>
              </Disclosure>
            </div>
          </div>
        )}
        {slide.body && <div className="max-w-full">{slide.body(slide.steps, "read")}</div>}
        {slide.source && (
          <SourceLine lead={slide.source.lead} mode="read">
            {slide.source.text}
          </SourceLine>
        )}
        <Disclosure show={deckCopy.reading.showNotes} hide={deckCopy.reading.hideNotes} testId="notes">
          <div className="max-w-prose text-body text-ink" data-notes={slide.n}>
            {slide.notes}
          </div>
        </Disclosure>
      </div>
    </section>
  );
}

function ReadingView({ slides, data, page, big }: { slides: Slide[]; data: DeckData; page: boolean; big: boolean }) {
  const total = slides.length;
  useEffect(() => {
    document.title = deckCopy.readingTitle;
    // The section the hash names, or else the slide the address names (/present/{n}), as presentation mode left it.
    const id = decodeURIComponent(window.location.hash.slice(1));
    const at = slideInAddress();
    const target = id ? document.getElementById(id) : at && at > 1 ? document.getElementById(`slide-${Math.min(at, total)}`) : null;
    target?.scrollIntoView();
  }, [total]);
  return (
    <div className="flex min-h-dvh flex-col bg-page" data-deck="read">
      <main className="layout flex-1 py-8">
        {page && big && (
          <p className="mb-8">
            <TextLink href="/present/1" data-present>
              {deckCopy.reading.present}
            </TextLink>
          </p>
        )}
        <WholeSlides value={true}>
          <div className="flex max-w-[65rem] flex-col gap-12 divide-y divide-line">
            {slides.map((slide) => (
              <div key={slide.n} className="pt-12 first:pt-0">
                <ReadingSlide slide={slide} data={data} total={total} />
              </div>
            ))}
          </div>
        </WholeSlides>
        {data.urls.repo && (
          <p className="mt-12">
            <ExternalLink href={data.urls.repo}>{deckCopy.slides.thanks.links.repo}</ExternalLink>
          </p>
        )}
      </main>
      <Footer />
    </div>
  );
}

// ── The speaker notes view ──────────────────────────────────────────────

function minutes(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

function NotesView({ slides }: { slides: Slide[] }) {
  const total = slides.length;
  const [place, setPlace] = useState<Place>({ n: 1, step: 0 });
  const [alone, setAlone] = useState(false);
  const [started, setStarted] = useState(() => Date.now());
  const [now, setNow] = useState(() => Date.now());
  const [announce, setAnnounce] = useState("");
  const heard = useRef(false);
  const channel = useRef<BroadcastChannel | null>(null);
  const at = useRef(place);
  at.current = place;
  const slide = slides[place.n - 1];

  useEffect(() => {
    const tick = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(tick);
  }, []);

  useEffect(() => {
    if (typeof BroadcastChannel === "undefined") {
      setAlone(true);
      return;
    }
    const open = new BroadcastChannel(CHANNEL);
    channel.current = open;
    open.onmessage = (event: MessageEvent<Message>) => {
      const message = event.data;
      if (message.type === "at") {
        heard.current = true;
        setAlone(false);
        setPlace({ n: Math.min(Math.max(message.n, 1), total), step: message.step });
      }
    };
    open.postMessage({ type: "where" } satisfies Message);
    const wait = setTimeout(() => {
      if (!heard.current) setAlone(true);
    }, 1000);
    return () => {
      clearTimeout(wait);
      if (channel.current === open) channel.current = null;
      open.close();
    };
  }, [total]);

  // A move made here: the deck makes it and says where it landed; alone, the notes move on their own.
  const send = useCallback(
    (move: Move) => {
      if (!alone && channel.current) {
        try {
          channel.current.postMessage({ type: "move", move } satisfies Message);
          return;
        } catch {
          // fall through and move alone
        }
      }
      setPlace((current) => moved(current, move, slides));
    },
    [alone, slides],
  );
  const goTo = useCallback(
    (n: number) => {
      if (!alone && channel.current) {
        try {
          channel.current.postMessage({ type: "go", n } satisfies Message);
          return;
        } catch {
          // fall through and move alone
        }
      }
      setPlace((current) => arrive(n, current.n, slides));
    },
    [alone, slides],
  );

  const shownN = useRef(place.n);
  useEffect(() => {
    document.title = deckCopy.notesTitle(String(place.n), String(total));
    if (shownN.current !== place.n)
      setAnnounce(deckCopy.announce(String(place.n), String(total), document.getElementById("notes-title")?.textContent?.trim() ?? ""));
    shownN.current = place.n;
  }, [place.n, total]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const move = moveFor(event);
      if (move === null) return;
      event.preventDefault();
      send(move);
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [send]);

  const next = slides[place.n] ?? null;
  const figureSteps = slide.figure?.steps ?? 0;
  const figureLine = slide.figure && place.step > 0 && place.step <= figureSteps ? figureStepText(slide.figure.id, place.step) : null;
  return (
    <div className="flex min-h-dvh flex-col bg-page" data-deck="notes">
      <main className="layout flex-1 py-8">
        <div className="grid gap-12 lg:grid-cols-[minmax(0,1fr)_18rem]">
          <div className="flex max-w-prose flex-col gap-6">
            <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
              <p className="text-caption text-ink-muted tabular-nums">
                <span data-chrome>{deckCopy.slideOf(String(place.n), String(total))}</span>
                {slide.steps > 0 && (
                  <>
                    {" "}
                    <span data-chrome data-notes-press>
                      {deckCopy.pressOf(String(place.step), String(slide.steps))}
                    </span>
                  </>
                )}
              </p>
              <div className="flex items-center gap-3">
                <p data-chrome role="timer" aria-label={deckCopy.notesView.timerName} className="text-h2 text-ink-heading tabular-nums" data-timer>
                  {minutes(Math.max(0, Math.floor((now - started) / 1000)))}
                </p>
                <Button variant="ghost" onClick={() => setStarted(Date.now())}>
                  {deckCopy.notesView.restart}
                </Button>
              </div>
            </div>
            {alone && (
              <Alert
                state="info"
                action={
                  <a href="/present/1" className="text-body text-primary underline underline-offset-3">
                    {deckCopy.notesView.openDeck}
                  </a>
                }
              >
                {deckCopy.notesView.noDeck}
              </Alert>
            )}
            <h1 id="notes-title" className="text-h1 text-ink-heading">
              {slide.title}
            </h1>
            <div className="text-body text-ink" data-notes-view={place.n}>
              {slide.notes}
            </div>
            {figureLine && (
              <p className="border-l-4 border-info-icon bg-surface py-2 pl-4 text-small text-ink" data-notes-step>
                {figureLine}
              </p>
            )}
            <p className="text-small text-ink-muted" data-next-title>
              {next ? <NextTitle slide={next} /> : deckCopy.notesView.last}
            </p>
            <div className="flex gap-3">
              <Button variant="secondary" icon={ChevronLeft} onClick={() => send("back")} disabled={place.n === 1 && place.step === 0}>
                {deckCopy.notesView.previous}
              </Button>
              <Button variant="primary" onClick={() => send("forward")} disabled={place.n === total && place.step >= slide.steps}>
                {deckCopy.notesView.nextButton}
              </Button>
            </div>
          </div>
          <nav aria-label={deckCopy.notesView.outline} data-notes-outline>
            <h2 className="text-h2 text-ink-heading">{deckCopy.notesView.outline}</h2>
            <ol className="mt-3 flex flex-col">
              {slides.map((one) => (
                <li key={one.n}>
                  <button
                    type="button"
                    onClick={(event) => {
                      goTo(one.n);
                      event.currentTarget.blur();
                    }}
                    aria-current={one.n === place.n ? "step" : undefined}
                    className={cx(
                      "w-full rounded-sm px-2 py-1 text-left text-small hover:bg-tint-hover",
                      one.n === place.n ? "bg-tint font-semibold text-ink-heading" : "text-ink",
                    )}
                  >
                    {one.kind === "opener" ? deckCopy.topics[one.topic!].name : (one.outline ?? one.title)}
                  </button>
                </li>
              ))}
            </ol>
          </nav>
        </div>
      </main>
      <p role="status" className="sr-only">
        {announce}
      </p>
    </div>
  );
}

function NextTitle({ slide }: { slide: Slide }) {
  const parts = deckCopy.notesView.next.split("{title}");
  return (
    <>
      {parts[0]}
      <span data-next={slide.n}>{slide.kind === "opener" ? deckCopy.topics[slide.topic!].name : slide.title}</span>
      {parts[1]}
    </>
  );
}

export type { Theme };
