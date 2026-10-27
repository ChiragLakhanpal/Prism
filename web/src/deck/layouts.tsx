// The deck's slide layouts, on the type ramp (ramp.ts): points with a question to the room, tiles, a live demo, a
// measured result, the rollout's phases and the agenda. Each takes `at`, how many of its items a press has brought in,
// and the mode: on the canvas they sit in the content box the frame leaves (x 48 to 912), and in the reading view they
// flow in the page. Every word comes from copy.ts through the slides that call these.
import { createContext, useContext, useState, type CSSProperties, type ReactNode } from "react";
import { ChevronRight, CircleDashed, Copy, ExternalLink as ExternalIcon } from "lucide-react";
import { cx } from "../lib/cx";
import { deckCopy } from "./copy";
import { SHOWN, STEP, type, UNREACHED, type Mode } from "./ramp";

// Inside the reading view every item shows whole and none recedes: there is no press to follow there.
const Whole = createContext(false);
export const WholeSlides = Whole.Provider;

// An item a press brings in, the n-th of its slide (from 1). It is drawn all along, so it holds its place while it
// waits, hidden from the eye and from assistive tech; it is current on its step and recedes after it.
export function Step({
  n,
  at,
  as: Tag = "div",
  className = "",
  style,
  children,
}: {
  n: number;
  at: number;
  as?: "div" | "li" | "section" | "p";
  className?: string;
  style?: CSSProperties;
  children: ReactNode;
}) {
  const whole = useContext(Whole);
  const shown = whole || n <= at;
  return (
    <Tag
      data-step={n}
      data-current={!whole && n === at ? "" : undefined}
      data-receded={!whole && n < at ? "" : undefined}
      aria-hidden={shown ? undefined : true}
      className={cx(STEP, shown ? SHOWN : UNREACHED, className)}
      style={style}
    >
      {children}
    </Tag>
  );
}

// A point's marker, a square on its first line: the figures' accent on the newest point, muted once it recedes.
function Marker({ mode }: { mode: Mode }) {
  return (
    <span aria-hidden="true" className="flex shrink-0 items-center text-info-icon" style={{ height: mode === "present" ? 27 : 24 }}>
      <span className="size-2 bg-current" />
    </span>
  );
}

// Points said one after another, a press each, and then, when there is one, the question to the room in a callout,
// set like the World Bank's info alert.
export function Points({ lines, ask, at, mode, first = 1 }: { lines: ReactNode[]; ask?: ReactNode; at: number; mode: Mode; first?: number }) {
  return (
    <div className="flex flex-col">
      <ul className={cx("flex flex-col", mode === "present" ? "gap-4" : "gap-3")} style={mode === "present" ? { maxWidth: 780 } : undefined}>
        {lines.map((line, index) => (
          <Step key={index} n={first + index} at={at} as="li" className="flex gap-4">
            <Marker mode={mode} />
            <span className="text-pretty text-ink" {...type("body", mode)}>
              {line}
            </span>
          </Step>
        ))}
      </ul>
      {ask && (
        <Step
          n={first + lines.length}
          at={at}
          className={cx("w-fit border-l-4 border-info-icon bg-info-bg", mode === "present" ? "mt-8 px-6 py-4" : "mt-6 px-4 py-3")}
          style={mode === "present" ? { maxWidth: 780 } : undefined}
        >
          <p className="text-pretty font-semibold text-primary" {...type("body", mode)}>
            {ask}
          </p>
        </Step>
      )}
    </div>
  );
}

// Two to four tiles, a press each, each a head and a note, then an optional closing line under them.
export function Tiles({ tiles, closing, at, mode }: { tiles: { head: ReactNode; body: ReactNode }[]; closing?: ReactNode; at: number; mode: Mode }) {
  const columns = mode === "present" ? `repeat(${tiles.length === 4 ? 2 : tiles.length}, minmax(0, 1fr))` : undefined;
  return (
    <div className="flex flex-col">
      <div className={cx("grid gap-6", mode === "read" && "md:grid-cols-3")} style={columns ? { gridTemplateColumns: columns } : undefined}>
        {tiles.map((tile, index) => (
          <Step
            key={index}
            n={index + 1}
            at={at}
            as="section"
            className="flex flex-col rounded-md border border-line bg-surface p-6 [&[data-current]]:border-info-icon"
          >
            <h2 className="text-ink-heading" {...type("head", mode)}>
              {tile.head}
            </h2>
            <p className="mt-2 text-ink-muted" {...type("note", mode)}>
              {tile.body}
            </p>
          </Step>
        ))}
      </div>
      {closing && (
        <Step n={tiles.length + 1} at={at} as="p" className={cx("text-pretty text-ink", mode === "present" ? "mt-8" : "mt-6")}>
          <span {...type("body", mode)}>{closing}</span>
        </Step>
      )}
    </div>
  );
}

// A live demo: what it opens, in a box like Strata's own one box, with the link that opens that screen in a new tab in
// the place of the box's button, and, for a question, a button that copies it. The box shows from the start; what to
// watch for comes in a press a line.
export function Demo({
  box,
  mono = false,
  action,
  href,
  question,
  lines,
  at,
  mode,
}: {
  box: ReactNode;
  mono?: boolean;
  action: ReactNode;
  href: string;
  question?: string;
  lines: ReactNode[];
  at: number;
  mode: Mode;
}) {
  return (
    <div className="flex flex-col">
      <div
        data-demo-box
        className={cx("flex items-center gap-4 rounded-sm border border-line-strong bg-surface", mode === "present" ? "py-2 pr-2 pl-6" : "flex-wrap p-2 pl-4")}
        style={mode === "present" ? { maxWidth: 864 } : undefined}
      >
        <span className={cx("min-w-0 flex-1 text-ink", mono && "font-mono")} {...type("note", mode)}>
          {box}
        </span>
        {question && <CopyQuestion question={question} />}
        <a
          href={href}
          target="_blank"
          rel="noreferrer"
          data-demo-link
          className="inline-flex h-11 shrink-0 items-center gap-2 rounded-sm bg-primary px-6 text-button text-surface no-underline transition-paint duration-150 hover:bg-primary-hover active:bg-primary-pressed"
        >
          {action}
          <ExternalIcon aria-hidden="true" className="size-4" />
          <span className="sr-only">{deckCopy.demo.opens}</span>
        </a>
      </div>
      <div className={mode === "present" ? "mt-8" : "mt-6"}>
        <Points lines={lines} at={at} mode={mode} />
      </div>
    </div>
  );
}

// A button that copies a demo's question, for pasting into Strata's box in the tab the demo link opens.
function CopyQuestion({ question }: { question: string }) {
  const [state, setState] = useState<"idle" | "copied" | "failed">("idle");
  const copyIt = () => {
    navigator.clipboard?.writeText(question).then(
      () => setState("copied"),
      () => setState("failed"),
    ) ?? setState("failed");
  };
  return (
    <button
      type="button"
      onClick={copyIt}
      data-copy-question
      className="inline-flex h-11 shrink-0 items-center gap-2 rounded-sm border-2 border-primary px-4 text-button text-primary transition-paint duration-150 hover:bg-tint"
    >
      <Copy aria-hidden="true" className="size-4" />
      <span aria-live="polite">{state === "copied" ? deckCopy.demo.copied : state === "failed" ? deckCopy.demo.copyFailed : deckCopy.demo.copy}</span>
    </button>
  );
}

// A measured result, a press: what was measured and how, the number as its result gave it, and a miss in the error
// colour when there is one. With nothing measured yet, the neutral state: a dashed circle and one sentence.
export function Result({ head, body, value, miss, n, at, mode }: { head: ReactNode; body?: ReactNode; value?: ReactNode; miss?: ReactNode; n: number; at: number; mode: Mode }) {
  return (
    <Step n={n} at={at} as="section" className="flex flex-col rounded-md border border-line bg-surface p-6 [&[data-current]]:border-info-icon">
      <h2 className="text-ink-heading" {...type("head", mode)}>
        {head}
      </h2>
      {body && (
        <p className="mt-2 text-ink-muted" {...type("note", mode)}>
          {body}
        </p>
      )}
      {value && (
        <p className="mt-4 text-primary" {...type("result", mode)}>
          {value}
        </p>
      )}
      {miss && (
        <p className="mt-3 text-error" {...type("note", mode)}>
          {miss}
        </p>
      )}
    </Step>
  );
}

export function NotMeasured({ children, n, at, mode }: { children: ReactNode; n: number; at: number; mode: Mode }) {
  return (
    <Step n={n} at={at} className="flex w-fit items-start gap-3 rounded-md bg-neutral-bg px-4 py-3 text-neutral" data-not-measured>
      <CircleDashed aria-hidden="true" className="mt-1 size-4 shrink-0" />
      <p {...type("note", mode)}>{children}</p>
    </Step>
  );
}

// The rollout's phases, a press each, left to right, each with who uses Strata and what is measured before the next.
export function Phases({
  phases,
  whoLabel,
  measuredLabel,
  at,
  mode,
}: {
  phases: { name: ReactNode; who: ReactNode; measured: ReactNode }[];
  whoLabel: string;
  measuredLabel: string;
  at: number;
  mode: Mode;
}) {
  return (
    <ol className={cx("grid gap-4", mode === "read" && "md:grid-cols-3")} style={mode === "present" ? { gridTemplateColumns: "repeat(3, minmax(0, 1fr))" } : undefined}>
      {phases.map((phase, index) => (
        <Step key={index} n={index + 1} at={at} as="li" className="relative flex flex-col rounded-md border border-line bg-surface p-6 [&[data-current]]:border-info-icon">
          <h2 className="text-ink-heading" {...type("head", mode)}>
            {phase.name}
          </h2>
          <p className="mt-4 text-ink-muted" {...type("label", mode)}>
            {whoLabel}
          </p>
          <p className="mt-1 text-ink" {...type("note", mode)}>
            {phase.who}
          </p>
          <p className="mt-4 text-ink-muted" {...type("label", mode)}>
            {measuredLabel}
          </p>
          <p className="mt-1 text-ink" {...type("note", mode)}>
            {phase.measured}
          </p>
          {mode === "present" && index < phases.length - 1 && (
            <ChevronRight aria-hidden="true" className="absolute top-1/2 -right-4 size-4 -translate-y-1/2 text-ink-muted" />
          )}
        </Step>
      ))}
    </ol>
  );
}

// The source line under a slide's content: "Source:" and where it came from, or "Note:" and a definition.
export function SourceLine({ lead, children, mode }: { lead: string; children: ReactNode; mode: Mode }) {
  return (
    <p className="text-ink-muted" data-source-line {...type("source", mode)}>
      <span className="font-semibold">{lead}</span> {children}
    </p>
  );
}
