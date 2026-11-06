// ResearchProgress: a deep research run while it goes (tickets 157, 159 and 161), in place of the ask box's steps, which
// keep their no-check-marks rule (Steps.tsx). The run's plan event (src/strata/research/run.py) lists every step it will
// take, and the rail groups them into the run's four phases:
//
// - The head: the title, and at its right "m:ss elapsed · usually 2 to 3 minutes" ("longer than usual" past the usual
//   high end). The clock ticks each second from the run's start on this computer; it is the only time the tab claims as
//   a fact. Under it the Progress meter (DESIGN.md), full width, a progressbar valued by the plan's steps done.
// - A timeline of four cards on one 2 px rule: Project facts, Reading <n> sources, Writing the brief, Checking every
//   sentence. Each card has a header row (its name and a pill: done, to do, or the live card's count) and one sub-line.
//   Each card's 14 px dot sits inside its header row, centred on the row and on the rule, so a long sub-line never moves
//   it; the rule is drawn as one segment per card, from its dot's centre to the next dot's centre, so it moves with the
//   cards and runs from the first dot to the last and no further.
// - The live card (the first phase not done) holds one "now" line that says in everyday words what I'm doing right now,
//   and under it a window of a fixed height (WINDOW_LINES lines) that scrolls inside the card: each source's state, the
//   writer's one line, or each checked sentence with its section. The window keeps its newest line in view at its
//   bottom unless the person scrolls up. Over the window's top 55 percent, four stacked backdrop blurs (1, 2, 4 and
//   8 px), each masked to fade out toward the sharp zone, and a fade to the card's white, so older lines drift up into
//   the blur as new ones come. The blur is on while lines stream in (the checks) and whenever the lines overflow.
// - The foot: keep this tab open, and each source's note behind one closed disclosure.
// - One polite live region says the now line, once per change.
//
// Nothing moves inside a phase: every header, sub-line, now line and window has a fixed height, the clock sits in a box
// of fixed width in tabular figures, and the usual time and "longer than usual" share one box. When a phase ends, the
// window closes on its card and opens on the next with one 300 ms height transition (motion-meter), so only the next
// card moves, by the window's height; the cards below it and the foot stay put. Under reduced motion the transition,
// the meter's fill, the spinner and the window's scrolling are instant; the blur stays, since it does not move.
import { useEffect, useLayoutEffect, useRef, useState, type ReactNode } from "react";
import { Check, Circle, CircleMinus, LoaderCircle, X } from "lucide-react";
import { copy } from "../copy";
import { cx } from "../lib/cx";
import { formatDate } from "../lib/format";
import type { CheckedLine, PlannedStep, ResearchPlan, ResearchStep } from "../lib/research";
import { Disclosure } from "./Disclosure";
import { Fill } from "./Fill";

const words = copy.research;
const STILL_WORKING_MS = 30_000;
const TYPICAL_SECONDS: [number, number] = [120, 180];

// research.progress.window_lines: the live card's window holds this many lines, and is this tall in every phase.
export const WINDOW_LINES = 7;
// The window's line, the now line and the gaps above each, in px; the live part of a card is their sum.
const LINE = 24;
const NOW = 20;
const GAP = 8;
const WINDOW = WINDOW_LINES * LINE;
const LIVE = GAP + NOW + GAP + WINDOW;
// The timeline's geometry, in px: the cards start GUTTER from the timeline's left edge, the rule's centre is RULE from
// it, and each card has a 1 px border, PAD_X and PAD_Y inside it, a HEADER-tall header row, and CARD_GAP between cards.
const GUTTER = 32;
const RULE = 12;
const BORDER = 1;
const PAD_X = 16;
const PAD_Y = 12;
const HEADER = 24;
const CARD_GAP = 12;
const DOT = 14;
// A checked sentence's words in the window: the first 70 characters.
const CUT = 70;

type Phase = "facts" | "sources" | "writing" | "checking";
const PHASES: Phase[] = ["facts", "sources", "writing", "checking"];
type LineState = "done" | "running" | "todo" | "not_reached";

const finished = (step: ResearchStep | undefined) => step !== undefined && step.status !== "running";

function lineState(step: ResearchStep | undefined): LineState {
  if (!step) return "todo";
  return step.status === "running" ? "running" : step.status === "not_reached" ? "not_reached" : "done";
}

const clock = (seconds: number) => `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
// The rail's lines are status lines beside a clock, so their counts stay figures.
const figure = (count: number) => String(count);
const cut = (text: string) => (text.length > CUT ? `${text.slice(0, CUT).trimEnd()}…` : text);

// The brief's own name for the section a checked sentence sits in (the stream's section key, src/strata/research/brief.py).
const SECTION_WORDS: Record<string, string> = {
  headline: words.section.picture,
  picture: words.section.picture,
  bottom_line: words.section.bottomLine,
  developments: words.section.developments,
  by_site: words.section.bySite,
  voices: words.section.voices,
  questions: words.section.questions,
  could_not_see: words.section.couldNotSee,
};
const sectionName = (section: string | null) => (section ? (SECTION_WORDS[section] ?? null) : null);

const sourceKey = (planned: PlannedStep, step: ResearchStep | undefined) => step?.source ?? planned.id.replace(/^source-/, "");
const doingOf = (planned: PlannedStep, step: ResearchStep | undefined) => words.progress.doing[sourceKey(planned, step)] ?? words.progress.doingSource(step?.label ?? planned.label);

function keptWords(count: number): string {
  const kept = words.progress.notes.kept;
  return count === 0 ? kept.none : count === 1 ? kept.one : kept.several(figure(count));
}

// A source's line behind the disclosure: its note once read ("read on November 5, 2026"), why it was not reached, or
// its state while it waits or runs.
function noteOf(step: ResearchStep | undefined, state: LineState): string {
  if (state === "not_reached") return words.progress.notes.notReached(step?.note);
  if (state === "done") return step?.note || keptWords(step?.items ?? 0);
  return words.progress.state[state];
}

const LINE_ICONS = {
  done: { Icon: Check, className: "text-primary" },
  running: { Icon: LoaderCircle, className: "animate-spin text-primary motion-reduce:animate-none" },
  todo: { Icon: Circle, className: "text-ink-muted" },
  not_reached: { Icon: CircleMinus, className: "text-ink-muted" },
  kept: { Icon: Check, className: "text-primary" },
  removed: { Icon: X, className: "text-ink-muted" },
} as const;

function LineIcon({ state }: { state: keyof typeof LINE_ICONS }) {
  const { Icon, className } = LINE_ICONS[state];
  return (
    <span data-progress-icon aria-hidden="true" className="flex size-4 shrink-0 items-center justify-center">
      <Icon className={cx("size-3.5", className)} />
    </span>
  );
}

// The progressive blur over the window's top 55 percent: four backdrop blurs, each masked from full at the top edge to
// none further down, the strongest fading out first, and a fade to the card's white. Browsers without backdrop-filter
// keep the fade. Nothing in it takes the pointer, so the lines under it still scroll and select.
const BLUR_LAYERS: { blur: number; mask: string }[] = [
  { blur: 1, mask: "linear-gradient(to bottom, black 0%, black 60%, transparent 100%)" },
  { blur: 2, mask: "linear-gradient(to bottom, black 0%, black 40%, transparent 80%)" },
  { blur: 4, mask: "linear-gradient(to bottom, black 0%, black 20%, transparent 60%)" },
  { blur: 8, mask: "linear-gradient(to bottom, black 0%, transparent 40%)" },
];
const FADE = "linear-gradient(to bottom, var(--color-surface) 0%, color-mix(in srgb, var(--color-surface) 70%, transparent) 35%, transparent 100%)";

function Blur() {
  return (
    <div data-progress-blur aria-hidden="true" className="pointer-events-none absolute inset-x-0 top-0" style={{ height: "55%" }}>
      {BLUR_LAYERS.map(({ blur, mask }) => (
        <div
          key={blur}
          data-blur-layer={blur}
          className="pointer-events-none absolute inset-0"
          style={{ backdropFilter: `blur(${blur}px)`, WebkitBackdropFilter: `blur(${blur}px)`, maskImage: mask, WebkitMaskImage: mask }}
        />
      ))}
      <div data-blur-fade className="pointer-events-none absolute inset-0" style={{ backgroundImage: FADE }} />
    </div>
  );
}

// The live card's window: a fixed height that scrolls inside the card. It keeps its current line (the newest sentence,
// or the source being read) as its last visible line, unless the person has scrolled up; scrolling back to the bottom
// lets it follow again. stream puts the lines at the bottom, so they rise into the blur as new ones come.
function Window({ label, stream, follow, children }: { label: string; stream: boolean; follow: string; children: ReactNode }) {
  const scroller = useRef<HTMLDivElement>(null);
  const pinned = useRef(true);
  const lastTop = useRef(0);
  const height = useRef(0);
  const [overflow, setOverflow] = useState(false);

  useLayoutEffect(() => {
    const element = scroller.current;
    if (!element) return;
    setOverflow(element.scrollHeight > element.clientHeight + 1);
    // A scroll whose event has not come yet still counts: up, the person is reading; at the bottom of the lines there
    // were before this one, they are following again.
    if (element.scrollTop < lastTop.current - 1) pinned.current = false;
    if (height.current > 0 && element.scrollTop + element.clientHeight >= height.current - 2) pinned.current = true;
    height.current = element.scrollHeight;
    if (!pinned.current) return;
    const current = element.querySelector<HTMLElement>("[data-window-current]");
    if (!current) return;
    const top = Math.max(0, current.offsetTop + current.offsetHeight - element.clientHeight);
    if (Math.abs(element.scrollTop - top) > 1) element.scrollTop = top;
  }, [follow]);

  useEffect(() => {
    const element = scroller.current;
    if (!element || typeof ResizeObserver === "undefined") return;
    const watch = new ResizeObserver(() => setOverflow(element.scrollHeight > element.clientHeight + 1));
    watch.observe(element);
    return () => watch.disconnect();
  }, []);

  const scrolled = () => {
    const element = scroller.current;
    if (!element) return;
    // A scroll up is the person's: the window stays where they put it until they come back to the bottom.
    if (element.scrollTop < lastTop.current - 1) pinned.current = false;
    if (element.scrollTop + element.clientHeight >= element.scrollHeight - 2) pinned.current = true;
    lastTop.current = element.scrollTop;
  };

  return (
    <div data-progress-window className="relative" style={{ height: WINDOW, marginTop: GAP }}>
      <div
        ref={scroller}
        data-progress-scroll
        role="group"
        aria-label={label}
        tabIndex={overflow ? 0 : undefined}
        onScroll={scrolled}
        className="relative h-full overflow-y-auto overscroll-contain scroll-smooth motion-reduce:scroll-auto focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
      >
        <div className={cx("flex min-h-full flex-col", stream && "justify-end")}>{children}</div>
      </div>
      {(stream || overflow) && <Blur />}
    </div>
  );
}

type Card = {
  phase: Phase;
  name: string;
  state: "done" | "live" | "todo";
  open: boolean;
  pill: string;
  sub: string;
};

function Pill({ state, children }: { state: Card["state"]; children: ReactNode }) {
  return (
    <span
      data-progress-pill
      className={cx(
        "inline-flex h-5 shrink-0 items-center rounded-pill px-2 text-label tabular-nums whitespace-nowrap",
        state === "done" ? "bg-tint text-primary" : state === "live" ? "bg-primary text-surface" : "bg-surface-2 text-ink-muted",
      )}
    >
      {children}
    </span>
  );
}

export function ResearchProgress({
  name,
  country = null,
  plan,
  steps,
  checks,
  started,
  lastEventAt,
  stored = false,
}: {
  // The project's name, for the title, and its country, for the facts card.
  name: string;
  country?: string | null;
  // The run's plan, once it has come; until then the sources card waits for its count.
  plan: ResearchPlan | null;
  steps: ResearchStep[];
  // The sentences checked so far, in order: the stream's sentence and removed events.
  checks: CheckedLine[];
  // When the run started and when its last event came, from Date.now().
  started: number;
  lastEventAt: number;
  // The run writes from sources read ahead of time (research.live_sources false, ticket 152): the sources card says the
  // day they were read.
  stored?: boolean;
}) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);

  const byId = new Map(steps.map((step) => [step.id, step]));
  const facts = byId.get("facts");
  const writing = byId.get("writing");
  const checking = byId.get("checking");
  const plannedSources: PlannedStep[] = plan
    ? plan.steps.filter((step) => step.kind === "source")
    : steps.filter((step) => step.kind === "source").map((step) => ({ id: step.id, kind: step.kind, label: step.label ?? step.id }));
  const sources = plannedSources.map((planned) => ({ planned, step: byId.get(planned.id), state: lineState(byId.get(planned.id)) }));
  const sourcesDone = sources.filter((one) => one.state === "done" || one.state === "not_reached").length;
  // The source being read: the one started last, if a source's end never came.
  const runningSource = sources.map((one) => one.state).lastIndexOf("running");

  // Each phase: begun once a step of it has come, done by its own last step or once a later phase has begun. A writer
  // that failed in the demo's setting keeps the last brief (ticket 152), so the checks never run.
  const begun: Record<Phase, boolean> = { facts: facts !== undefined, sources: steps.some((step) => step.kind === "source"), writing: writing !== undefined, checking: checking !== undefined };
  const ownDone: Record<Phase, boolean> = {
    facts: finished(facts),
    sources: plan !== null && sources.every((one) => one.state === "done" || one.state === "not_reached"),
    writing: finished(writing),
    checking: finished(checking) || Boolean(writing?.kept_from),
  };
  const done = (at: number) => ownDone[PHASES[at]] || PHASES.slice(at + 1).some((phase) => begun[phase]);
  const firstOpen = PHASES.findIndex((_, at) => !done(at));
  // Once every phase is done the last one begun keeps its window, so the rail keeps its height until the brief comes.
  const lastBegun = PHASES.reduce((last, phase, at) => (begun[phase] ? at : last), PHASES.length - 1);
  const open = firstOpen >= 0 ? firstOpen : lastBegun;
  const openPhase = PHASES[open];

  const total = plan ? plan.steps.length : 0;
  const stepsDone = plan ? plan.steps.filter((step) => finished(byId.get(step.id))).length : 0;
  const elapsed = Math.max(0, Math.floor((now - started) / 1000));
  // Before the plan comes, the usual time's box is held at a typical run's width.
  const [low, high] = plan ? plan.usual_seconds : TYPICAL_SECONDS;
  const usual = words.progress.usual(figure(Math.round(low / 60)), figure(Math.round(high / 60)));
  const longer = plan !== null && elapsed > high;
  const stillWorking = longer && now - lastEventAt > STILL_WORKING_MS;
  const readOn = steps.find((step) => step.stored_on)?.stored_on ?? null;
  const missed = sources.filter((one) => one.state === "not_reached").length;
  const items = sources.reduce((sum, one) => sum + (one.state === "done" ? (one.step?.items ?? 0) : 0), 0);
  const kept = checks.filter((line) => line.kept).length;

  const progress = words.progress;
  const stateOf = (at: number): Card["state"] => (done(at) ? "done" : at === open ? "live" : "todo");
  const pillOf = (at: number, live: string): string => (stateOf(at) === "done" ? progress.pill.done : stateOf(at) === "live" ? live : progress.pill.todo);
  const closing = facts?.closing_date ? progress.sub.closing(formatDate(facts.closing_date)) : null;
  const sourcesSub = (() => {
    if (done(1) && plan) {
      const read = sourcesDone - missed;
      return [readOn ? progress.sub.readStored(figure(read), formatDate(readOn)) : progress.sub.read(figure(read)), missed > 0 ? progress.sub.notReached(figure(missed)) : null, progress.sub.items(figure(items))]
        .filter(Boolean)
        .join(" · ");
    }
    return readOn ? progress.sub.sourcesStored(formatDate(readOn)) : progress.sub.sources;
  })();
  const cards: Card[] = [
    { phase: "facts", name: progress.phase.facts, state: stateOf(0), open: open === 0, pill: pillOf(0, progress.pill.reading), sub: [facts?.project_name || name, country, closing].filter(Boolean).join(", ") },
    {
      phase: "sources",
      name: plan ? progress.phase.sourcesCount(figure(plannedSources.length)) : progress.phase.sources,
      state: stateOf(1),
      open: open === 1,
      pill: pillOf(1, plan ? progress.pill.count(figure(sourcesDone), figure(plannedSources.length)) : progress.pill.reading),
      sub: sourcesSub,
    },
    {
      phase: "writing",
      name: progress.phase.writing,
      state: stateOf(2),
      open: open === 2,
      pill: pillOf(2, progress.pill.writing),
      sub: writing?.kept_from ? progress.sub.keptBrief : finished(writing) ? progress.sub.sentences(figure(writing?.sentences ?? 0)) : progress.sub.writing,
    },
    {
      phase: "checking",
      name: progress.phase.checking,
      state: stateOf(3),
      open: open === 3,
      pill: pillOf(3, checking?.sentences ? progress.pill.count(figure(Math.min(checks.length, checking.sentences)), figure(checking.sentences)) : progress.pill.checking),
      sub: finished(checking) ? progress.sub.checked(figure(checking?.kept ?? kept), figure(checking?.removed ?? checks.length - kept)) : progress.sub.checking,
    },
  ];

  // What I'm doing right now, in everyday words: the source being read (or the next one), the writer, or the section
  // of the brief whose sentences are being checked.
  const doing = (() => {
    if (openPhase === "facts") return progress.doingFacts;
    if (openPhase === "sources") {
      const current = sources[runningSource] ?? sources.find((one) => one.state === "todo") ?? sources[sources.length - 1];
      return current ? doingOf(current.planned, current.step) : progress.doingSources;
    }
    if (openPhase === "writing") return progress.doingWriting;
    const section = sectionName(checks.length > 0 ? checks[checks.length - 1].section : null);
    return section ? progress.doingSection(section) : progress.doingChecking;
  })();
  const nowLine = stillWorking ? copy.steps.stillWorking : progress.now(doing);

  // The window's lines for the open phase, and the one it keeps in view.
  const followSource = runningSource >= 0 ? runningSource : Math.max(0, sourcesDone - 1);
  const windowLines = (): ReactNode => {
    if (openPhase === "sources") {
      return (
        <ul className="grid grid-cols-1 gap-x-4 @min-[36rem]/progress:grid-cols-2">
          {sources.map(({ planned, step, state }, at) => (
            <li
              key={planned.id}
              data-progress-source={planned.id}
              data-progress-step={state}
              data-window-current={at === followSource ? "" : undefined}
              className={cx("flex min-w-0 items-center gap-2 text-small", state === "todo" ? "text-ink-muted" : "text-ink")}
              style={{ height: LINE }}
            >
              <LineIcon state={state} />
              <span title={planned.label} className="min-w-0 truncate">
                {planned.label}
                {state === "done" && ` · ${figure(step?.items ?? 0)}`}
                {state === "not_reached" && ` · ${progress.window.notReached}`}
                {state === "running" && ` · ${progress.window.reading}`}
                <span className="sr-only">, {progress.state[state]}</span>
              </span>
            </li>
          ))}
        </ul>
      );
    }
    if (openPhase === "checking") {
      return (
        <ol>
          {checks.map((line, at) => {
            const section = sectionName(line.section);
            return (
              <li
                key={`${line.index}-${line.kept ? "kept" : "removed"}`}
                data-progress-check={line.kept ? "kept" : "removed"}
                data-window-current={at === checks.length - 1 ? "" : undefined}
                className={cx("flex min-w-0 items-center gap-2 text-small", line.kept ? "text-ink" : "text-ink-muted")}
                style={{ height: LINE }}
              >
                <LineIcon state={line.kept ? "kept" : "removed"} />
                <span data-progress-check-text className="min-w-0 truncate" title={line.text}>
                  <span className="sr-only">{progress.state[line.kept ? "kept" : "removed"]}: </span>
                  {section && <span className={cx("font-semibold", line.kept ? "text-primary" : "text-ink-muted")}>{section}</span>}
                  {section && " · "}
                  {cut(line.text)}
                </span>
              </li>
            );
          })}
        </ol>
      );
    }
    const phaseDone = openPhase === "facts" ? finished(facts) : finished(writing);
    const text = openPhase === "facts" ? progress.window.facts : writing?.kept_from ? progress.sub.keptBrief : progress.window.writing;
    return (
      <ul>
        <li data-window-current="" className="flex min-w-0 items-center gap-2 text-small text-ink" style={{ height: LINE }}>
          <LineIcon state={phaseDone ? "done" : "running"} />
          <span className="min-w-0 truncate">{text}</span>
        </li>
      </ul>
    );
  };
  const follow = `${openPhase}:${openPhase === "checking" ? checks.length : openPhase === "sources" ? `${followSource}/${sourcesDone}` : ""}`;

  return (
    <div data-research-progress className="@container/progress max-w-prose">
      <div className="flex flex-col gap-1 @min-[36rem]/progress:flex-row @min-[36rem]/progress:items-baseline @min-[36rem]/progress:justify-between @min-[36rem]/progress:gap-4">
        <p data-progress-heading className="min-w-0 text-body font-semibold text-ink-heading">
          {progress.title(name)}
        </p>
        <p data-progress-line className="shrink-0 whitespace-nowrap text-small text-ink-muted tabular-nums">
          <Fill
            template={progress.elapsed}
            slots={{
              clock: (
                <span data-progress-clock className="inline-block min-w-[3.5ch] font-semibold text-primary">
                  {clock(elapsed)}
                </span>
              ),
            }}
          />
          {/* The usual time and "longer than usual" share one box as wide as the wider, held before the plan says the
              usual time, so the title beside them never rewraps. */}
          <span aria-hidden={plan ? undefined : true} className={cx(!plan && "invisible")}>
            {" · "}
            <span className="inline-grid">
              <span data-progress-usual className="col-start-1 row-start-1">
                {longer ? progress.longer : usual}
              </span>
              <span aria-hidden="true" className="invisible col-start-1 row-start-1">
                {longer ? usual : progress.longer}
              </span>
            </span>
          </span>
        </p>
      </div>
      {plan ? (
        <div
          role="progressbar"
          aria-label={progress.meter}
          aria-valuemin={0}
          aria-valuemax={total}
          aria-valuenow={stepsDone}
          aria-valuetext={progress.meterText(figure(stepsDone), figure(total))}
          className="mt-3 h-2 w-full overflow-hidden rounded-pill bg-surface-2"
        >
          <div
            className="h-full rounded-pill bg-primary transition-[width] duration-(--motion-meter) ease-[ease] motion-reduce:transition-none"
            style={{ width: `${total > 0 ? (stepsDone / total) * 100 : 0}%` }}
          />
        </div>
      ) : (
        <div aria-hidden="true" className="mt-3 h-2 w-full rounded-pill bg-surface-2" />
      )}
      <ol data-progress-timeline className="relative mt-4 flex flex-col" style={{ paddingLeft: GUTTER, gap: CARD_GAP }}>
        {cards.map((card, at) => (
          <li
            key={card.phase}
            data-progress-phase={card.phase}
            data-progress-state={card.state}
            data-progress-open={card.open ? "" : undefined}
            className={cx(
              "relative rounded-[6px] border bg-surface",
              card.state === "live" ? "border-primary shadow-[0_0_0_3px_var(--color-tint)]" : "border-line",
            )}
            style={{ padding: `${PAD_Y}px ${PAD_X}px` }}
          >
            {at < cards.length - 1 && (
              // The rule from this card's dot to the next card's, in the gutter: it stretches with the card.
              <span
                data-progress-rule
                aria-hidden="true"
                className="absolute w-0.5 bg-line"
                style={{ left: RULE - 1 - GUTTER - BORDER, top: PAD_Y + HEADER / 2, bottom: -(BORDER + CARD_GAP + BORDER + PAD_Y + HEADER / 2) }}
              />
            )}
            <div data-progress-header className="relative flex items-center justify-between gap-3" style={{ height: HEADER }}>
              <span
                data-progress-dot={card.state}
                aria-hidden="true"
                className={cx(
                  "absolute box-border rounded-pill border-2",
                  card.state === "done" ? "border-primary bg-primary" : card.state === "live" ? "border-primary bg-surface" : "border-line bg-surface",
                )}
                style={{ width: DOT, height: DOT, left: RULE - DOT / 2 - GUTTER - BORDER - PAD_X, top: `calc(50% - ${DOT / 2}px)` }}
              />
              <span data-progress-name title={card.name} className={cx("min-w-0 truncate text-small", card.state === "todo" ? "text-ink-muted" : "font-semibold text-navy")}>
                {card.name}
                <span className="sr-only">, {card.state === "live" ? progress.state.running : progress.state[card.state]}</span>
              </span>
              <Pill state={card.state}>{card.pill}</Pill>
            </div>
            <p data-progress-sub title={card.sub} className="h-5 truncate text-small text-ink-muted">
              {card.sub}
            </p>
            <div
              data-progress-live={card.open ? "open" : "closed"}
              aria-hidden={card.open ? undefined : true}
              className="overflow-hidden transition-[height] duration-(--motion-meter) ease-[ease] motion-reduce:transition-none"
              style={{ height: card.open ? LIVE : 0 }}
            >
              {card.open && (
                <>
                  <p data-progress-now className="flex items-center gap-2 text-small text-ink" style={{ height: NOW, marginTop: GAP }}>
                    <span aria-hidden="true" className="size-1.5 shrink-0 rounded-pill bg-primary" />
                    <span title={nowLine} className="min-w-0 truncate">
                      {nowLine}
                    </span>
                  </p>
                  <Window key={card.phase} label={card.name} stream={card.phase === "checking"} follow={follow}>
                    {windowLines()}
                  </Window>
                </>
              )}
            </div>
          </li>
        ))}
      </ol>
      <p data-progress-keep className="mt-4 text-small text-ink-muted">
        {progress.keepOpen}
      </p>
      {/* Held from the start, so the plan's coming does not add a line under the cards. */}
      {(plan === null || sources.length > 0) && (
        <Disclosure label={missed > 0 ? progress.notes.missed : progress.notes.all} className="mt-2">
          <ul className="flex flex-col gap-1 text-small text-ink-muted">
            {sources.map(({ planned, step, state }) => (
              <li key={planned.id} data-progress-note={planned.id}>
                <span className="text-ink">{planned.label}</span>: {noteOf(step, state)}
              </li>
            ))}
          </ul>
        </Disclosure>
      )}
      <p aria-live="polite" className="sr-only">
        {nowLine}
      </p>
    </div>
  );
}
