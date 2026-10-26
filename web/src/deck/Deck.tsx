// The deck at /present (ticket 47; the 47 brief): Strata's story in sixteen slides, outside the app's frame, with
// nothing in the app linking to it. Its address lives in the proposal and the README.
//
// - /present and /present/{n}: presentation mode, the 960 by 540 canvas scaled as one unit, when the window can show
//   it at its own size or larger ((min-width: 63rem) and (min-height: 40.25rem)); otherwise the reading view.
//   Arrow keys, Page Up, Page Down, Home and End move between slides, and each move replaces the address.
// - /present/page: the reading view at any size, every slide as a section of one page with its notes inline.
// - /present/notes: the speaker notes, in their own window, kept in step with the deck through a BroadcastChannel.
//
// The deck reads its numbers from /deck/data.json (web/src/deck/data.ts), the measures snapshot the proposal cites.
import { useCallback, useEffect, useId, useLayoutEffect, useRef, useState, type MouseEvent, type ReactNode } from "react";
import { ChevronDown, ChevronLeft, ChevronRight, ChevronUp, ExternalLink as ExternalIcon, Maximize, Minimize, Table2 } from "lucide-react";
import lightLogo from "../assets/world-bank-logo-light.svg";
import { Alert } from "../components/Alert";
import { Button } from "../components/Button";
import { Footer } from "../components/Frame";
import { copy } from "../copy";
import { cx } from "../lib/cx";
import { formatDate } from "../lib/format";
import { Diagram, FigureFailed, FigureText, HairlineFigure, useOverflow } from "../figures/Figure";
import { FIGURES, SLOTS, type Slot } from "../figures/registry";
import { deckCopy, figureCopy } from "./copy";
import { loadDeck, type DeckData } from "./data";
import { buildSlides, type Mode, type Slide } from "./slides";

const CANVAS = { width: 960, height: 540 };
const PRESENT = "(min-width: 63rem) and (min-height: 40.25rem)";
const CHANNEL = "strata-deck";
const GHOST =
  "inline-flex h-11 shrink-0 items-center justify-center gap-2 rounded-pill border-2 border-transparent px-4 text-button text-primary " +
  "transition-paint duration-150 select-none hover:bg-tint-hover active:bg-tint active:text-primary-pressed";

export type DeckView = { kind: "slides"; n: number | null } | { kind: "page" } | { kind: "notes" };

// Which part of the deck an address under /present names, or null for an address that is not the deck's.
export function deckView(pathname: string): DeckView | null {
  const path = pathname.replace(/\/+$/, "");
  if (path === "/present") return { kind: "slides", n: null };
  if (path === "/present/page") return { kind: "page" };
  if (path === "/present/notes") return { kind: "notes" };
  const match = /^\/present\/(\d{1,4})$/.exec(path);
  return match ? { kind: "slides", n: Number(match[1]) } : null;
}

const clampSlide = (n: number, total: number) => Math.min(Math.max(n, 1), total);
const counter = (n: number, total: number) => deckCopy.counter(String(n), String(total));
const titleText = (n: number) => document.getElementById(`slide-${n}-title`)?.textContent?.trim() ?? "";

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
  if (!data) return <Loading />;
  const slides = buildSlides(data);
  if (view.kind === "notes") return <NotesView slides={slides} />;
  if (view.kind === "page" || !big) return <ReadingView slides={slides} data={data} page={view.kind === "page"} big={big} />;
  return <Presentation slides={slides} data={data} start={view.n ?? 1} />;
}

// The stage at its final size, with the empty slide's border and footer, while the deck's data arrive.
function Loading() {
  return (
    <main className="flex min-h-dvh flex-col items-center bg-surface-2 p-6" data-deck="loading">
      <div className="border border-line bg-page" style={{ width: "min(100%, 960px)", aspectRatio: "16 / 9" }}>
        <p className="p-6 text-caption text-ink-muted">{copy.footer}</p>
      </div>
    </main>
  );
}

// ── The figure frame: the drawing slot and a 36 px credit row with the source or note and the logo ──

function Logo() {
  return <img src={lightLogo} width={121} height={24} alt={deckCopy.logo} className="block h-6 w-[121px] shrink-0" data-deck-logo />;
}

function CreditRow({ credit, stack = false }: { credit?: ReactNode; stack?: boolean }) {
  return (
    <div className={cx("mt-3 flex gap-3", stack ? "flex-col" : "items-start justify-between")} data-credit-row>
      <div className="min-w-0 flex-1">{credit}</div>
      <div className={cx(stack && "self-end")}>
        <Logo />
      </div>
    </div>
  );
}

function Drawing({ slide, mode }: { slide: Slide; mode: Mode }) {
  const [broken, setBroken] = useState(false);
  const onFail = useCallback(() => setBroken(true), []);
  const id = slide.figure!;
  if (broken) return <FigureFailed id={id} />;
  if (id === "core-sample") return <HairlineFigure onFail={onFail} className={mode === "present" ? "w-full" : "w-full max-w-120"} />;
  return <Diagram id={id} />;
}

// ── One slide on the canvas ─────────────────────────────────────────────

function SlideCanvas({ slide, data, total, current, twin }: { slide: Slide; data: DeckData; total: number; current: boolean; twin: boolean }) {
  const titleId = `slide-${slide.n}-title`;
  const slot: Slot | null = slide.figure ? FIGURES[slide.figure].slot : slide.chart ? "narrow" : null;
  const frame = slot ? (
    <div style={{ width: SLOTS[slot].width }} data-figure-frame={slot}>
      <div className="relative" style={{ width: SLOTS[slot].width, height: SLOTS[slot].height }}>
        {slide.figure && (
          <>
            <Drawing slide={slide} mode="present" />
            <div className="sr-only">
              <FigureText id={slide.figure} />
            </div>
          </>
        )}
        {slide.chart && (
          <figure data-source-key={slide.chart.source} className="relative h-full overflow-hidden rounded-md border border-line bg-surface" data-chart={twin ? "table" : "chart"}>
            {/* A chart measures its own text as it draws, which a hidden slide cannot, so only the slide on screen
                draws its chart. */}
            {!current ? null : twin ? (
              <div tabIndex={0} role="region" aria-labelledby={titleId} data-scroll-region className="h-full overflow-auto p-2">
                {slide.chart.table}
              </div>
            ) : slide.n === 8 ? (
              slide.chart.drawing("present")
            ) : (
              <div className="p-4">{slide.chart.drawing("present")}</div>
            )}
          </figure>
        )}
      </div>
      <CreditRow credit={slide.credit} />
    </div>
  ) : null;
  let body: ReactNode;
  if (slide.template === "title") {
    body = null;
  } else if (slide.template === "wide") {
    body = frame;
  } else if (slide.template === "narrow" || slide.template === "half") {
    body = (
      <div className="flex gap-6">
        {frame}
        <div className="min-w-0 flex-1">{slide.side}</div>
      </div>
    );
  } else {
    body = slide.body;
  }
  return (
    <section
      aria-roledescription={deckCopy.roleSlide}
      aria-labelledby={titleId}
      hidden={!current}
      data-slide={slide.n}
      className="@container/deck absolute inset-0 bg-page"
    >
      {slide.template === "title" ? (
        <div className="absolute flex items-center gap-6" style={{ left: 48, top: 32, width: 864, height: 424 }}>
          <div style={{ width: 494 }}>
            <p className="text-h3 text-ink-heading">{deckCopy.wordmark}</p>
            <h1 id={titleId} tabIndex={-1} className="mt-4 text-display text-ink-heading outline-none">
              {slide.title}
            </h1>
            <p className="mt-6 text-body text-ink-muted">{deckCopy.slides.s1.line}</p>
            <Presenter data={data} />
          </div>
          <div style={{ width: 346 }} data-figure-frame="hairline">
            <div className="relative" style={{ width: 346, height: 277 }}>
              <Drawing slide={slide} mode="present" />
              <div className="sr-only">
                <FigureText id="core-sample" />
              </div>
            </div>
            <CreditRow />
          </div>
        </div>
      ) : (
        <>
          {slide.eyebrow && (
            <p className="absolute text-label text-ink-muted uppercase" style={{ left: 48, top: 32 }}>
              {slide.eyebrow}
            </p>
          )}
          <h1 id={titleId} tabIndex={-1} className="absolute text-display text-ink-heading outline-none" style={{ left: 48, top: 56, width: 716 }}>
            {slide.title}
          </h1>
          <div className="absolute" style={{ left: 48, top: 152, width: 864, minHeight: 304 }}>
            {body}
          </div>
        </>
      )}
      <div className="absolute border-t border-line" style={{ left: 48, top: 472, width: 864 }} />
      <p className="absolute text-caption text-ink-muted" style={{ left: 48, top: 484, width: 716 }} data-slide-footer>
        {copy.footer}
      </p>
      <p data-chrome className="absolute text-right text-caption text-ink-muted tabular-nums" style={{ left: 788, top: 484, width: 124 }}>
        {counter(slide.n, total)}
      </p>
    </section>
  );
}

function Presenter({ data }: { data: DeckData }) {
  if (!data.presenter.name && !data.presenter.date) return null;
  return (
    <div className="mt-8">
      {data.presenter.name && <p className="text-small text-ink">{data.presenter.name}</p>}
      {data.presenter.date && <p className="text-small text-ink-muted">{formatDate(data.presenter.date)}</p>}
    </div>
  );
}

// ── Presentation mode ───────────────────────────────────────────────────

function useScale(): number {
  const measure = () => Math.max(0.1, Math.min((window.innerWidth - 48) / CANVAS.width, (window.innerHeight - 104) / CANVAS.height));
  const [scale, setScale] = useState(measure);
  useEffect(() => {
    const update = () => setScale(measure());
    window.addEventListener("resize", update);
    return () => window.removeEventListener("resize", update);
  }, []);
  return scale;
}

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

// The keys that move slides (the 47 brief, section 10.1): no single-letter shortcuts, and none while a modifier is
// held, focus is in a form field, or focus is inside a table that scrolls.
export function slideKey(event: KeyboardEvent, n: number, total: number): number | null {
  if (event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return null;
  const target = event.target as HTMLElement | null;
  if (target?.closest?.("input, textarea, select, [contenteditable=true], [data-scroll-region], [role=dialog]")) return null;
  if (["ArrowRight", "ArrowDown", "PageDown"].includes(event.key)) return Math.min(n + 1, total);
  if (["ArrowLeft", "ArrowUp", "PageUp"].includes(event.key)) return Math.max(n - 1, 1);
  if (event.key === "Home") return 1;
  if (event.key === "End") return total;
  return null;
}

function Presentation({ slides, data, start }: { slides: Slide[]; data: DeckData; start: number }) {
  const total = slides.length;
  const [n, setN] = useState(() => clampSlide(start, total));
  const [twin, setTwin] = useState(false);
  const [announce, setAnnounce] = useState("");
  const scale = useScale();
  const full = useFullScreen();
  const stage = useRef<HTMLDivElement>(null);
  const first = useRef(true);
  const channel = useRef<BroadcastChannel | null>(null);
  const currentN = useRef(n);
  currentN.current = n;
  const slide = slides[n - 1];

  const go = useCallback(
    (next: number) => {
      const target = clampSlide(next, total);
      const inside = stage.current?.contains(document.activeElement) ?? false;
      setTwin(false);
      setN(target);
      if (inside) requestAnimationFrame(() => document.getElementById(`slide-${target}-title`)?.focus());
    },
    [total],
  );

  // The address and the tab's title follow the slide; Back leaves the deck instead of walking through slides.
  useLayoutEffect(() => {
    window.history.replaceState(window.history.state, "", `/present/${n}`);
    document.title = deckCopy.title(String(n), String(total));
    if (first.current) first.current = false;
    else setAnnounce(deckCopy.announce(String(n), String(total), titleText(n)));
    channel.current?.postMessage({ type: "at", n });
  }, [n, total]);

  useEffect(() => {
    if (typeof BroadcastChannel === "undefined") return;
    const open = new BroadcastChannel(CHANNEL);
    channel.current = open;
    open.onmessage = (event: MessageEvent<{ type: string; n?: number }>) => {
      if (event.data.type === "where") open.postMessage({ type: "at", n: currentN.current });
      if (event.data.type === "go" && event.data.n) go(event.data.n);
    };
    open.postMessage({ type: "at", n: currentN.current });
    return () => open.close();
  }, [go]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const next = slideKey(event, currentN.current, total);
      if (next === null) return;
      event.preventDefault();
      if (next !== currentN.current) go(next);
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [go, total]);

  const link = (to: number) => (event: MouseEvent<HTMLAnchorElement>) => {
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    go(to);
  };
  const width = CANVAS.width * scale;
  const charted = Boolean(slide.chart);
  return (
    <main className="flex min-h-dvh flex-col items-center bg-surface-2 p-6" data-deck="present">
      <div
        ref={stage}
        className="relative shrink-0 overflow-hidden border border-line bg-page"
        style={{ width, height: CANVAS.height * scale }}
        data-stage
      >
        <div style={{ width: CANVAS.width, height: CANVAS.height, transform: `scale(${scale})`, transformOrigin: "0 0" }} data-canvas>
          {slides.map((one) => (
            <SlideCanvas key={one.n} slide={one} data={data} total={total} current={one.n === n} twin={one.n === n && twin} />
          ))}
        </div>
      </div>
      <nav aria-label={deckCopy.bar.label} className="mt-3 flex h-11 shrink-0 items-center justify-between gap-2" style={{ width }} data-deck-bar>
        <div className="flex items-center gap-2">
          <a href={`/present/${n - 1}`} onClick={link(n - 1)} className={cx(GHOST, n === 1 && "invisible")} data-previous>
            <ChevronLeft aria-hidden="true" className="size-4" />
            {deckCopy.bar.previous}
          </a>
          <a href={`/present/${n + 1}`} onClick={link(n + 1)} className={cx(GHOST, n === total && "invisible")} data-next>
            {deckCopy.bar.next}
            <ChevronRight aria-hidden="true" className="size-4" />
          </a>
        </div>
        <div className="flex items-center gap-2">
          <button type="button" onClick={() => setTwin((now) => !now)} className={cx(GHOST, !charted && "invisible")} data-table-toggle>
            <Table2 aria-hidden="true" className="size-4" />
            {twin ? deckCopy.bar.showChart : deckCopy.bar.showTable}
          </button>
          <a href={`/present/page#slide-${n}`} className={GHOST} data-read-as-page>
            {deckCopy.bar.readAsPage}
          </a>
          <a href="/present/notes" target="_blank" rel="noopener" aria-label={deckCopy.bar.notesName} className={GHOST} data-notes-link>
            {deckCopy.bar.notes}
            <ExternalIcon aria-hidden="true" className="size-4" />
          </a>
          {full.able && (
            <button type="button" onClick={full.toggle} className={GHOST} data-full-screen>
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
  const headingId = `slide-${slide.n}-title`;
  const figure = slide.figure ? FIGURES[slide.figure] : null;
  const wide = figure && figure.slot !== "hairline" ? SLOTS[figure.slot].width : 0;
  const frameRef = useRef<HTMLDivElement>(null);
  const overflows = useOverflow(frameRef, wide);
  return (
    <section id={`slide-${slide.n}`} aria-labelledby={headingId} className="@container/deck scroll-mt-6" data-reading-slide={slide.n}>
      <p data-chrome className="text-caption text-ink-muted">
        {deckCopy.slideOf(String(slide.n), String(total))}
      </p>
      {slide.eyebrow && <p className="mt-2 text-label text-ink-muted uppercase">{slide.eyebrow}</p>}
      {slide.n === 1 ? (
        <>
          <p className="mt-2 text-h3 text-ink-heading">{deckCopy.wordmark}</p>
          <h1 id={headingId} className="mt-2 text-h1 text-ink-heading">
            {slide.title}
          </h1>
          <p className="mt-4 text-body text-ink-muted">{deckCopy.slides.s1.line}</p>
          <Presenter data={data} />
        </>
      ) : (
        <h2 id={headingId} className="mt-2 text-h2 text-ink-heading">
          {slide.title}
        </h2>
      )}
      <div className="mt-6 flex max-w-full flex-col gap-6">
        {slide.side && <div className="max-w-prose">{slide.side}</div>}
        {slide.body && <div className="max-w-full">{slide.body}</div>}
        {figure && (
          <div ref={frameRef} data-figure-frame={figure.slot}>
            {figure.slot === "hairline" ? (
              <div className="relative w-full max-w-120" style={{ aspectRatio: "5 / 4" }}>
                <Drawing slide={slide} mode="read" />
              </div>
            ) : (
              <ScrollFrame width={wide} label={deckCopy.reading.scrolls(figureCopy[figure.id].title)}>
                <Drawing slide={slide} mode="read" />
              </ScrollFrame>
            )}
            <CreditRow credit={slide.credit} stack />
            <div className="mt-4">
              <Disclosure show={deckCopy.reading.showText} hide={deckCopy.reading.hideText} open={overflows} testId="text">
                <FigureText id={figure.id} />
              </Disclosure>
            </div>
          </div>
        )}
        {slide.chart && (
          <div data-figure-frame="chart">
            <figure
              data-source-key={slide.chart.source}
              tabIndex={0}
              role="region"
              aria-labelledby={headingId}
              className="max-w-full overflow-x-auto rounded-md border border-line bg-surface p-4"
            >
              {slide.chart.drawing("read")}
            </figure>
            <CreditRow credit={slide.credit} stack />
            <div className="mt-4">
              <Disclosure show={deckCopy.reading.showTable} hide={deckCopy.reading.hideTable} testId="table">
                <figure data-source-key={slide.chart.source} tabIndex={0} role="region" aria-labelledby={headingId} className="max-w-full overflow-x-auto">
                  {slide.chart.table}
                </figure>
              </Disclosure>
            </div>
          </div>
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
    const id = decodeURIComponent(window.location.hash.slice(1));
    const target = id ? document.getElementById(id) : null;
    target?.scrollIntoView();
  }, []);
  return (
    <div className="flex min-h-dvh flex-col bg-page" data-deck="read">
      <main className="layout flex-1 py-8">
        {page && big && (
          <p className="mb-8">
            <a href="/present/1" className="text-body text-primary underline underline-offset-3 hover:text-link-hover" data-present>
              {deckCopy.reading.present}
            </a>
          </p>
        )}
        <div className="flex max-w-[65rem] flex-col gap-12 divide-y divide-line">
          {slides.map((slide) => (
            <div key={slide.n} className="pt-12 first:pt-0">
              <ReadingSlide slide={slide} data={data} total={total} />
            </div>
          ))}
        </div>
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
  const [n, setN] = useState(1);
  const [alone, setAlone] = useState(false);
  const [started, setStarted] = useState(() => Date.now());
  const [now, setNow] = useState(() => Date.now());
  const [announce, setAnnounce] = useState("");
  const heard = useRef(false);
  const channel = useRef<BroadcastChannel | null>(null);
  const slide = slides[n - 1];

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
    open.onmessage = (event: MessageEvent<{ type: string; n?: number }>) => {
      if (event.data.type === "at" && event.data.n) {
        heard.current = true;
        setAlone(false);
        setN(clampSlide(event.data.n, total));
      }
    };
    open.postMessage({ type: "where" });
    const wait = setTimeout(() => {
      if (!heard.current) setAlone(true);
    }, 1000);
    return () => {
      clearTimeout(wait);
      open.close();
    };
  }, [total]);

  const go = useCallback(
    (next: number) => {
      const target = clampSlide(next, total);
      setN(target);
      channel.current?.postMessage({ type: "go", n: target });
    },
    [total],
  );

  const shown = useRef(n);
  useEffect(() => {
    document.title = deckCopy.notesTitle(String(n), String(total));
    if (shown.current !== n) setAnnounce(deckCopy.announce(String(n), String(total), document.getElementById("notes-title")?.textContent?.trim() ?? ""));
    shown.current = n;
  }, [n, total]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const next = slideKey(event, shown.current, total);
      if (next === null) return;
      event.preventDefault();
      if (next !== shown.current) go(next);
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [go, total]);

  const next = slides[n] ?? null;
  return (
    <div className="flex min-h-dvh flex-col bg-page" data-deck="notes">
      <main className="layout flex-1 py-8">
        <div className="flex max-w-prose flex-col gap-6">
          <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
            <p data-chrome className="text-caption text-ink-muted tabular-nums">
              {deckCopy.slideOf(String(n), String(total))}
            </p>
            <div className="flex items-center gap-3">
              <p data-chrome role="timer" aria-label={deckCopy.notesView.timerName} className="text-title text-ink-heading tabular-nums" data-timer>
                {minutes(Math.max(0, Math.floor((now - started) / 1000)))}
              </p>
              <Button variant="ghost" onClick={() => setStarted(Date.now())}>
                {deckCopy.notesView.restart}
              </Button>
            </div>
          </div>
          {alone && (
            <Alert state="info" action={<a href="/present/1" className="text-body text-primary underline underline-offset-3">{deckCopy.notesView.openDeck}</a>}>
              {deckCopy.notesView.noDeck}
            </Alert>
          )}
          <h1 id="notes-title" className="text-h1 text-ink-heading">
            {slide.title}
          </h1>
          <div className="text-body text-ink" data-notes-view={n}>
            {slide.notes}
          </div>
          <p className="text-small text-ink-muted" data-next-title>
            {next ? <NextTitle slide={next} /> : deckCopy.notesView.last}
          </p>
          <div className="flex gap-3">
            <Button variant="secondary" icon={ChevronLeft} onClick={() => go(n - 1)} disabled={n === 1}>
              {deckCopy.notesView.previous}
            </Button>
            <Button variant="primary" onClick={() => go(n + 1)} disabled={n === total}>
              {deckCopy.notesView.nextButton}
            </Button>
          </div>
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
      <span data-next={slide.n}>{slide.title}</span>
      {parts[1]}
    </>
  );
}
