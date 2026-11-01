// The slides (the second draft's brief, section 3), built from the deck's data: the bookends, the five topics and
// their openers, the rubric map, what is designed but not built, and the close. Each slide names its kind, its part
// of the talk, its title (the finding), how many presses it takes, what shows under its title at each press, its
// source line and its speaker notes. The deck lays the same slide out on the 960 by 540 canvas and as a section of
// one page in the reading view (Deck.tsx), so the two never say different things.
//
// A slide whose number was not measured yet says so in its own words, in place of the sentence that would hold it.
import type { ReactNode } from "react";
import { Fill } from "../components/Fill";
import { numText } from "../components/Num";
import { FIGURES, type FigureId } from "../figures/registry";
import { formatDate, formatNumber } from "../lib/format";
import { deckCopy, figureCopy } from "./copy";
import { measured, type DeckData, type DeckResult } from "./data";
import { Demo, NewTabLink, NotMeasured, Phases, Points, Step, Tiles } from "./layouts";
import { NoteNum, ResultNum, RubricPoints, SettingWord } from "./nums";
import { Hairline } from "../figures/Figure";
import { type, type Mode } from "./ramp";
import { recordingOf, type Recording } from "./Recorded";
import type { Theme } from "./Frame";
import type { Part, TopicKey } from "./talk";

export type Kind = "title" | "agenda" | "opener" | "figure" | "text" | "close";

export type Slide = {
  n: number;
  id: string;
  part: Part;
  theme: Theme;
  kind: Kind;
  title: ReactNode;
  // The title as plain text for the notes window's outline, where a title sits inside a button: a number in it is
  // bound to its source but not a button of its own. A slide whose title holds no number shows its title.
  outline?: ReactNode;
  // How many presses the slide takes before the deck moves on.
  steps: number;
  // A figure slide's drawing, which takes the slide's first presses (its own steps), and its slot on the slide.
  figure?: { id: FigureId; steps: number; wide: boolean };
  // What shows under the title (or beside a half figure), given how many of the slide's own items a press has
  // brought in: a figure slide counts only the items after its figure's steps.
  body?: (at: number, mode: Mode) => ReactNode;
  source?: { lead: string; text: ReactNode };
  // An opener's topic and the hairline figure that plays on it; the title slide's figure.
  topic?: TopicKey;
  hairline?: string;
  hairlineLabel?: string;
  // A chart drawn from the snapshot, with its table twin and the keys of the numbers it draws.
  chart?: { drawing: (mode: Mode, labelledById: string) => ReactNode; table: ReactNode; source: string };
  // A demo's recorded answer, which a press on the slide swaps in on the canvas (ticket 116; Recorded.tsx).
  recorded?: Recording;
  notes: ReactNode;
  // What the presenter does on the slide, and the questions a technical panel may ask about it, each with an answer
  // to give as written (deckCopy.speaker, by the slide's id).
  cue?: ReactNode;
  // An extra line to say at each press, under the words that press brings onto the screen.
  adds?: (string | null)[];
  asked?: { q: string; a: string }[];
  // The study guide's diagrams behind the slide, for the presenter's answers (web/public/deck/notes).
  diagrams?: string[];
};

// Each slide's title has this id, so a chart and a table region can be named by it.
export const TITLE_ID = (n: number) => `slide-${n}-title`;

const s = deckCopy.slides;
const day = (iso: string | undefined | null) => (iso ? formatDate(iso) : "");
const whole = (value: number) => formatNumber(value, { compact: false });
const mono = (text: string) => <span className="font-mono">{text}</span>;
function ratio(result: DeckResult, name: string) {
  return <ResultNum result={result} resultKey={name} value={{ part: result.n ?? 0, whole: result.d ?? 0, show: "count" }} />;
}

function count(result: DeckResult, name: string) {
  return <ResultNum result={result} resultKey={name} value={{ count: Number(result.n ?? 0) }} />;
}

// A number in the speaker notes, plain text bound to its source.
const note = (sourceKey: string, text: string) => <NoteNum sourceKey={sourceKey} text={text} />;
const noteRatio = (result: DeckResult, name: string) => note(`r:${name}`, numText({ part: result.n ?? 0, whole: result.d ?? 0, show: "count" }));
const noteWord = (data: DeckData, name: string, capital = false) => note(`s:${name}`, numText({ count: data.settings[name].value, capital }));

// The figure's own steps, from its drawing: none when the drawing is missing, so its text version stands in.
const figureSteps = (id: FigureId) => FIGURES[id].steps;

// The parts of the talk in order, slide by slide, without their numbers: buildSlides numbers them.
type Draft = Omit<Slide, "n">;

// The data slide's hairline figure: the awards record year by year, with its break. It mounts when its press comes,
// so it plays its tour from rest as it appears, and the reading view shows it at rest. Its box keeps the drawing's
// size all along, so the row never moves when it arrives.
function AwardsGap({ live, mode }: { live: boolean; mode: Mode }) {
  const width = mode === "present" ? 190 : 260;
  return (
    <div style={{ width, height: (width * 4) / 5 }}>
      {live && <Hairline figureKey="awards-gap" play={mode === "present"} label={s.data.figure} />}
    </div>
  );
}

export function buildSlides(data: DeckData): Slide[] {
  const word = (name: string, capital = false) => <SettingWord data={data} settingKey={name} capital={capital} />;
  const r = (key: string) => measured(data, key);
  const demo = data.demo;
  const showcase = data.showcase.project_id;
  const planDate = demo.plan_date ? day(demo.plan_date) : "";
  const links = demo.links ?? {};
  // The package demo's backup, the comparable packages recorded for the demo plan's package (ticket 116).
  const recording = recordingOf(demo.comparables, demo.step_reference);
  // The talk's one case, end to end: the package the plan check flags is the one the next two demos open.
  const packageHref = `/packages/${encodeURIComponent(demo.step_reference)}`;

  // A fact on the data slide: its sentence with each measured result in place, or what is not measured yet.
  const fact = (tile: { body: string; results: Record<string, string>; counts?: string[] }) => {
    const found = Object.entries(tile.results).map(([slot, key]) => [slot, key, r(key)] as const);
    if (found.some(([, , result]) => !result)) return deckCopy.states.notMeasured;
    const slots = Object.fromEntries(
      found.map(([slot, key, result]) => [slot, tile.counts?.includes(slot) || result!.d == null ? count(result!, key) : ratio(result!, key)]),
    );
    return <Fill template={tile.body} slots={slots} />;
  };

  // A figure slide: the drawing's steps, then `extra` items of the slide's own.
  const figure = (id: FigureId, extra = 0, wide = true) => {
    const steps = figureSteps(id);
    return { figure: { id, steps, wide }, steps: steps + extra };
  };

  const opener = (id: string, topic: TopicKey, hairline: string, label: string, notes: string): Draft => ({
    id,
    part: topic,
    theme: "navy",
    kind: "opener",
    title: deckCopy.topics[topic].name,
    steps: 0,
    topic,
    hairline,
    hairlineLabel: label,
    notes,
  });

  // ── Measured results the slides read ──
  const passages = r("passages");
  const documents = r("documents-read");
  const pages = r("pages-read-well");
  const rows = r("award-rows-by-year");
  const linked = r("linked-notice");
  const gap = data.award_gap;
  const years = (rows?.series ?? []).map((row) => Number(row.fiscal_year));
  const backtest = r("backtest-years");
  const latestYear = backtest?.series?.filter((row) => Number(row.d) > 0).at(-1) ?? null;
  const passed = r("benchmark-passed");
  const refused = r("must-refuse");
  const caught = r("hindsight-caught");
  const checklist = r("hindsight-checklist");
  const interval = r("hindsight-interval");
  const spend = r("azure-spend");
  // In a sentence an amount keeps its cents, with a trailing ".00" dropped (DESIGN.md section 7, rule 49).
  const amount = (value: number) => formatNumber(value, { decimals: 2, compact: false }).replace(/\.00$/, "");
  const money = (value: number) => deckCopy.money(amount(value));

  const drafts: Draft[] = [
    // ── The welcome and the agenda ──
    {
      id: "welcome",
      part: "open",
      theme: "navy",
      kind: "title",
      title: s.welcome.statement,
      steps: 0,
      hairline: "core-sample",
      hairlineLabel: s.welcome.figure,
      notes: s.welcome.notes,
    },
    {
      id: "agenda",
      part: "open",
      theme: "light",
      kind: "agenda",
      title: s.agenda.title,
      steps: 5,
      notes: s.agenda.notes,
    },

    // ── 1. Three strata ──
    {
      id: "strata",
      part: "strata",
      theme: "light",
      kind: "figure",
      title: s.strata.title,
      ...figure("strata"),
      source: { lead: deckCopy.sourceLead, text: s.strata.source },
      notes: s.strata.notes,
    },
    {
      id: "cost",
      part: "strata",
      theme: "light",
      kind: "text",
      title: s.cost.title,
      steps: s.cost.lines.length + 1,
      body: (at, mode) => <Points lines={s.cost.lines} ask={s.cost.ask} at={at} mode={mode} />,
      source: { lead: deckCopy.sourceLead, text: s.cost.source },
      notes: s.cost.notes,
    },
    {
      id: "who",
      part: "strata",
      theme: "light",
      kind: "text",
      title: s.who.title,
      steps: s.who.tiles.length + 1,
      body: (at, mode) => <Tiles tiles={s.who.tiles} closing={s.who.closing} at={at} mode={mode} />,
      notes: s.who.notes,
    },
    {
      id: "idea",
      part: "strata",
      theme: "light",
      kind: "figure",
      title: s.idea.title,
      ...figure("one-answer"),
      notes: s.idea.notes,
    },

    // ── 2. Strata at work ──
    opener("work", "work", "plan-rows", deckCopy.topics.work.line, s.workOpener.notes),
    {
      id: "demo-plan",
      part: "work",
      theme: "light",
      kind: "text",
      title: s.demoPlan.title,
      steps: s.demoPlan.lines.length,
      body: (at, mode) => (
        <Demo
          box={<Fill template={s.demoPlan.box} slots={{ agency: demo.agency, date: planDate, project: mono(demo.project_id) }} />}
          action={s.demoPlan.action}
          href={links.checkPlan ?? demo.plan_href}
          lines={s.demoPlan.lines}
          at={at}
          mode={mode}
        />
      ),
      source: { lead: deckCopy.sourceLead, text: <Fill template={s.demoPlan.source} slots={{ date: planDate, project: mono(demo.project_id) }} /> },
      notes: <Fill template={s.demoPlan.notes} slots={{ step: demo.step_reference }} />,
    },
    {
      id: "demo-package",
      part: "work",
      theme: "light",
      kind: "text",
      title: s.demoPackage.title,
      steps: s.demoPackage.lines.length,
      body: (at, mode) => (
        <Demo
          box={<Fill template={s.demoPackage.box} slots={{ step: mono(demo.step_reference) }} />}
          action={s.demoPackage.action}
          href={packageHref}
          recorded={recording}
          lines={s.demoPackage.lines}
          at={at}
          mode={mode}
        />
      ),
      recorded: recording,
      source: { lead: deckCopy.noteLead, text: s.demoPackage.note },
      notes: s.demoPackage.notes,
      cue: recording ? <Fill template={s.demoPackage.cueRecorded} slots={{ step: recording.step, date: day(recording.result.as_of) }} /> : undefined,
    },
    {
      id: "demo-answer",
      part: "work",
      theme: "light",
      kind: "text",
      title: s.demoAnswer.title,
      steps: s.demoAnswer.lines.length,
      body: (at, mode) => (
        <Demo
          box={s.demoAnswer.question}
          question={s.demoAnswer.question}
          action={s.demoAnswer.action}
          href={packageHref}
          lines={s.demoAnswer.lines}
          at={at}
          mode={mode}
        />
      ),
      source: { lead: deckCopy.noteLead, text: s.demoAnswer.note },
      notes: s.demoAnswer.notes,
    },

    // ── 3. How it is built ──
    opener("built", "built", "passages", deckCopy.topics.built.line, s.builtOpener.notes),
    {
      id: "layers",
      part: "built",
      theme: "light",
      kind: "figure",
      title: s.layers.title,
      ...figure("layers"),
      notes: s.layers.notes,
    },
    {
      id: "architecture",
      part: "built",
      theme: "light",
      kind: "figure",
      title: s.architecture.title,
      ...figure("architecture"),
      notes: s.architecture.notes,
    },
    {
      id: "pipeline",
      part: "built",
      theme: "light",
      kind: "figure",
      title: s.pipeline.title,
      ...figure("pipeline"),
      notes: s.pipeline.notes,
    },
    {
      id: "reading",
      part: "built",
      theme: "light",
      kind: "figure",
      title: s.reading.title,
      ...figure("reading", 1),
      // With nothing counted yet, the grey not-measured note, as the other slides show it; with one of the two
      // counted, the sentence that has its number and the one that says what is still to come.
      body: (at, mode) =>
        !(passages && documents) && !pages ? (
          <NotMeasured n={1} at={at} mode={mode}>
            {s.reading.bothNone}
          </NotMeasured>
        ) : (
          <Step n={1} at={at} className="flex flex-col gap-1">
            <p className="text-ink" {...type("note", mode)}>
              {passages && documents ? (
                <Fill template={s.reading.passages} slots={{ passages: count(passages, "passages"), documents: count(documents, "documents-read") }} />
              ) : (
                s.reading.passagesNone
              )}{" "}
              {pages ? <Fill template={s.reading.pages} slots={{ ratio: ratio(pages, "pages-read-well") }} /> : s.reading.pagesNone}
            </p>
          </Step>
        ),
      source: pages ? { lead: deckCopy.sourceLead, text: <Fill template={s.reading.source} slots={{ date: day(pages.measured_on) }} /> } : undefined,
      notes: s.reading.notes,
    },
    {
      id: "data",
      part: "built",
      theme: "light",
      kind: "text",
      title: s.data.title,
      steps: s.data.tiles.length + 1,
      body: (at, mode) => (
        <div className="flex flex-col gap-6">
          <Tiles
            tiles={[
              ...s.data.tiles.slice(0, 1).map((tile) => ({ head: tile.head, body: fact(tile) })),
              { figure: <AwardsGap live={mode === "read" || at >= 2} mode={mode} /> },
              ...s.data.tiles.slice(1).map((tile) => ({ head: tile.head, body: fact(tile) })),
            ]}
            at={at}
            mode={mode}
          />
          <p {...type("note", mode)}>
            <NewTabLink href="/data">{s.data.link}</NewTabLink>
          </p>
        </div>
      ),
      source: data.pulled_on
        ? { lead: deckCopy.sourceLead, text: <Fill template={s.data.source} slots={{ date: day(data.pulled_on) }} /> }
        : undefined,
      notes: s.data.notes,
    },

    // ── 4. How it answers ──
    opener("answers", "answers", "filter", deckCopy.topics.answers.line, s.answersOpener.notes),
    {
      id: "retrieval",
      part: "answers",
      theme: "light",
      kind: "figure",
      title: s.retrieval.title,
      ...figure("retrieval"),
      notes: s.retrieval.notes,
    },
    {
      id: "languages",
      part: "answers",
      theme: "light",
      kind: "figure",
      title: s.languages.title,
      ...figure("languages"),
      body: (_at, mode) => (
        <p {...type("note", mode)}>
          <NewTabLink href="/projects/P127203">{s.languages.action}</NewTabLink>
        </p>
      ),
      notes: s.languages.notes,
    },
    {
      id: "estimate",
      part: "answers",
      theme: "light",
      kind: "figure",
      title: s.estimate.title,
      ...figure("estimate", 1),
      body: (at, mode) => (
        <Step n={1} at={at} className="flex flex-col gap-1">
          <p className="text-ink" {...type("note", mode)}>
            <Fill template={s.estimate.few} slots={{ min: word("fewest-comparables") }} />{" "}
            {backtest && latestYear ? (
              <Fill
                template={s.estimate.backtest}
                slots={{
                  year: String(latestYear.label),
                  ratio: (
                    <ResultNum
                      result={{ ...backtest, n: Number(latestYear.n), d: Number(latestYear.d) }}
                      resultKey="backtest-years"
                      value={{ part: Number(latestYear.n), whole: Number(latestYear.d), show: "count" }}
                    />
                  ),
                }}
              />
            ) : (
              s.estimate.backtestNone
            )}
          </p>
        </Step>
      ),
      source: backtest ? { lead: deckCopy.sourceLead, text: <Fill template={s.estimate.source} slots={{ date: day(backtest.measured_on) }} /> } : undefined,
      notes: <Fill template={s.estimate.notes} slots={{ min: noteWord(data, "fewest-comparables") }} />,
    },
    {
      id: "checks",
      part: "answers",
      theme: "light",
      kind: "figure",
      title: <Fill template={s.checks.title} slots={{ checks: word("check-count") }} />,
      outline: <Fill template={s.checks.title} slots={{ checks: noteWord(data, "check-count") }} />,
      ...figure("checks", 1),
      body: (at, mode) =>
        passed && refused ? (
          <Step n={1} at={at}>
            <p className="text-ink" {...type("note", mode)}>
              <span className="font-semibold">{s.checks.heading}</span>{" "}
              <Fill template={s.checks.passed} slots={{ ratio: ratio(passed, "benchmark-passed") }} />{" "}
              <Fill template={s.checks.refused} slots={{ ratio: ratio(refused, "must-refuse") }} />
            </p>
          </Step>
        ) : (
          <NotMeasured n={1} at={at} mode={mode}>
            <Fill template={s.checks.none} slots={{ checks: word("check-count") }} />
          </NotMeasured>
        ),
      source: passed ? { lead: deckCopy.sourceLead, text: <Fill template={s.checks.source} slots={{ date: day(passed.measured_on) }} /> } : undefined,
      notes: s.checks.notes,
    },
    {
      id: "ladder",
      part: "answers",
      theme: "light",
      kind: "figure",
      title: s.ladder.title,
      ...figure("ladder", 2, false),
      body: (at, mode) => (
        <div className="flex flex-col gap-4" data-showcase>
          <Step n={1} at={at} as="p" className="text-ink">
            <span {...type("note", mode)}>{s.ladder.point}</span>
          </Step>
          <Step n={2} at={at} className="flex flex-col gap-3">
            <p className="border-l-4 border-info-icon bg-surface py-2 pl-4 text-ink" {...type("note", mode)}>
              <Fill template={s.ladder.example} slots={{ project: mono(showcase) }} />
            </p>
            <p {...type("note", mode)}>
              <NewTabLink href={links.wholeStory ?? `/projects/${showcase}/timeline`}>{s.ladder.action}</NewTabLink>
            </p>
          </Step>
        </div>
      ),
      source: { lead: deckCopy.sourceLead, text: <Fill template={s.ladder.source} slots={{ project: mono(showcase) }} /> },
      notes: s.ladder.notes,
    },

    // ── 5. How it grows ──
    opener("grows", "grows", "sediment", deckCopy.topics.grows.line, s.growsOpener.notes),
    {
      id: "loops",
      part: "grows",
      theme: "light",
      kind: "figure",
      title: <Fill template={s.loops.title} slots={{ loops: word("loop-count", true) }} />,
      outline: <Fill template={s.loops.title} slots={{ loops: noteWord(data, "loop-count", true) }} />,
      ...figure("loops"),
      notes: s.loops.notes,
    },
    {
      id: "rollout",
      part: "grows",
      theme: "light",
      kind: "text",
      title: <Fill template={s.rollout.title} slots={{ phases: word("rollout-phases") }} />,
      outline: <Fill template={s.rollout.title} slots={{ phases: noteWord(data, "rollout-phases") }} />,
      steps: s.rollout.phases.length,
      body: (at, mode) => (
        <Phases
          phases={s.rollout.phases.map((phase) => ({
            name: phase.name,
            who: <Fill template={phase.who} slots={{ countries: word("pilot-countries") }} />,
            measured: phase.measured,
          }))}
          whoLabel={s.rollout.whoLabel}
          measuredLabel={s.rollout.measuredLabel}
          measuredLastLabel={s.rollout.measuredLastLabel}
          at={at}
          mode={mode}
        />
      ),
      notes: <Fill template={s.rollout.notes} slots={{ countries: noteWord(data, "pilot-countries") }} />,
    },
    {
      id: "next-reach",
      part: "grows",
      theme: "light",
      kind: "text",
      title: s.nextReach.title,
      steps: s.nextReach.tiles.length,
      body: (at, mode) => <Tiles tiles={s.nextReach.tiles} at={at} mode={mode} />,
      notes: s.nextReach.notes,
    },
    {
      id: "next-product",
      part: "grows",
      theme: "light",
      kind: "text",
      title: s.nextProduct.title,
      steps: s.nextProduct.tiles.length,
      body: (at, mode) => <Tiles tiles={s.nextProduct.tiles} at={at} mode={mode} />,
      notes: s.nextProduct.notes,
    },

    // ── The close ──
    {
      id: "limits",
      part: "close",
      theme: "light",
      kind: "text",
      title: s.limits.title,
      steps: data.designed_not_built.length,
      body: (at, mode) =>
        data.designed_not_built.length === 0 ? (
          <p className="text-ink" {...type("body", mode)}>
            {s.limits.empty}
          </p>
        ) : (
          <Points
            lines={data.designed_not_built.map((item) => (
              <Fill key={item.key} template={s.limits.itemAt} slots={{ name: item.name, route: mono(item.route) }} />
            ))}
            at={at}
            mode={mode}
          />
        ),
      notes: data.designed_not_built.length === 0 ? s.limits.notesEmpty : s.limits.notes,
    },
    {
      id: "thanks",
      part: "close",
      theme: "navy",
      kind: "close",
      title: s.thanks.title,
      steps: 0,
      hairline: "sediment",
      hairlineLabel: s.thanks.figure,
      notes: data.designed_not_built.length === 0 ? s.thanks.notes : s.thanks.notesAfterLimits,
    },
  ];
  // What is designed but not built gets its own slide only when there is something on the list; with nothing on it,
  // the close's notes say that everything shown is built.
  return drafts
    .filter((draft) => draft.id !== "limits" || data.designed_not_built.length > 0)
    .map((draft, index) => ({
      ...draft,
      n: index + 1,
      cue: draft.cue ?? deckCopy.speaker[draft.id]?.cue,
      adds: deckCopy.speaker[draft.id]?.adds,
      asked: deckCopy.speaker[draft.id]?.asked,
      diagrams: deckCopy.speaker[draft.id]?.diagrams,
    }));
}

// The step texts a figure's presses bring in, for the live region and the speaker notes.
export function figureStepText(id: FigureId, step: number): string {
  return (figureCopy[id].steps as readonly string[])[step - 1] ?? "";
}
