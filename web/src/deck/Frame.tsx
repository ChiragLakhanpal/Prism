// The frame every slide sits in, on the 960 by 540 canvas (the second draft's brief, section 2). Along the top, a
// strip from y 0 to 48: the World Bank logo at x 48 (121 by 24, with clear space of half its height on every side,
// DESIGN.md section 9), a hairline, then the five topics as a tracker from x 217 to 852, each with a 3 px segment
// per slide, like the World Bank's tab underline: primary for the slides already shown, the figures' accent for this
// one and the hairline colour for those to come. The slide counter ends at x 912. Along the bottom, from y 516 to
// 540, DESIGN.md section 8's sentence, word for word, on one line.
//
// A light slide's strip is white with a hairline under it, and carries the logo for light backgrounds; a navy slide
// (the bookends and the topic openers) carries the World Bank's white logo, as the app's navy bar does, and its words
// in white. The title slide and the close show the logo alone, and the agenda shows no tracker, since it is the list
// of topics itself.
import type { ReactNode } from "react";
import lightLogo from "../assets/world-bank-logo-light.svg";
import whiteLogo from "../assets/world-bank-logo.svg";
import { copy } from "../copy";
import { cx } from "../lib/cx";
import { deckCopy } from "./copy";
import { FOOTER, TRACKER } from "./ramp";
import { type Segment, type TopicKey } from "./talk";

export type Theme = "light" | "navy";

const SEGMENT: Record<Theme, Record<Segment, string>> = {
  light: { passed: "bg-primary", current: "bg-info-icon", later: "bg-line" },
  navy: { passed: "bg-surface/60", current: "bg-surface", later: "bg-surface/20" },
};

export function Logo({ theme }: { theme: Theme }) {
  return theme === "navy" ? (
    <img src={whiteLogo} width={120} height={24} alt={deckCopy.logo} className="block h-6 w-[120px]" data-deck-logo="white" draggable={false} />
  ) : (
    <img src={lightLogo} width={121} height={24} alt={deckCopy.logo} className="block h-6 w-[121px]" data-deck-logo="light" draggable={false} />
  );
}

export function SlideFrame({
  theme,
  tracker,
  segments,
  topic,
  order,
  names,
  counter,
  footer = true,
  children,
}: {
  theme: Theme;
  // Whether the strip shows the tracker; the logo always shows.
  tracker: boolean;
  segments: Record<string, Segment[]>;
  topic: TopicKey | null;
  // The talk's topics in order, and each one's name in the tracker.
  order: readonly TopicKey[];
  names: Record<string, string>;
  // The counter's words, or none on the title slide and the close.
  counter: string | null;
  // Whether DESIGN.md section 8's sentence runs along this slide's foot: every slide of Prism's own talk, and none of
  // the research talk's (talk.ts, footerOn).
  footer?: boolean;
  children: ReactNode;
}) {
  const navy = theme === "navy";
  return (
    <>
      <div
        data-frame="header"
        className={cx("absolute inset-x-0 top-0 h-12", navy ? "" : "border-b border-line bg-surface")}
      >
        <div className="absolute" style={{ left: 48, top: 12 }}>
          <Logo theme={theme} />
        </div>
        {tracker && (
          <>
            <span aria-hidden="true" className={cx("absolute w-px", navy ? "bg-surface/30" : "bg-line")} style={{ left: 193, top: 12, height: 24 }} />
            <Tracker theme={theme} segments={segments} topic={topic} order={order} names={names} />
          </>
        )}
        {counter && (
          <p
            data-chrome
            className={cx("absolute text-right tabular-nums", navy ? "text-surface/75" : "text-ink-muted")}
            style={{ ...TRACKER, right: 48, top: 18, width: 56 }}
          >
            {counter}
          </p>
        )}
      </div>
      {children}
      {footer && (
        <p
          data-slide-footer
          className={cx("absolute whitespace-nowrap", navy ? "text-surface/75" : "text-ink-muted")}
          style={{ ...FOOTER, left: 48, bottom: 9 }}
        >
          {copy.footer}
        </p>
      )}
    </>
  );
}

// The five topics in order: the lit one ink-heading and heavier, each with a segment per slide.
function Tracker({ theme, segments, topic, order, names }: { theme: Theme; segments: Record<string, Segment[]>; topic: TopicKey | null; order: readonly TopicKey[]; names: Record<string, string> }) {
  const navy = theme === "navy";
  return (
    <ol
      data-tracker
      aria-label={deckCopy.topicsLabel}
      className="absolute grid grid-cols-5 gap-x-3"
      style={{ left: 217, top: 0, width: 635, height: 48 }}
    >
      {order.map((key) => {
        const lit = topic === key;
        return (
          <li key={key} data-topic={key} className="relative">
            <span
              data-topic-name
              aria-current={lit ? "step" : undefined}
              className={cx(
                "absolute left-0 max-w-full truncate",
                lit ? (navy ? "font-semibold text-surface" : "font-semibold text-ink-heading") : navy ? "text-surface/70" : "text-ink-muted",
              )}
              style={{ ...TRACKER, top: 15 }}
            >
              {names[key]}
            </span>
            <span aria-hidden="true" className="absolute inset-x-0 flex gap-0.5" style={{ top: 32, height: 3 }}>
              {segments[key].map((state, index) => (
                <span key={index} data-segment={state} className={cx("h-full min-w-0 flex-1", SEGMENT[theme][state])} />
              ))}
            </span>
          </li>
        );
      })}
    </ol>
  );
}
