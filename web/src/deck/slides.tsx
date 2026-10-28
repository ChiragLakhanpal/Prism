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
import { AwardChart, AwardKey, AwardTable, CHART_WIDTH } from "./AwardChart";
import { deckCopy, figureCopy } from "./copy";
import { measured, type DeckData, type DeckResult } from "./data";
import { Demo, NewTabLink, NotMeasured, Phases, Points, Step, Tiles } from "./layouts";
import { NoteNum, ResultNum, RubricPoints, SettingWord } from "./nums";
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
};

// Each slide's title has this id, so a chart and a table region can be named by it.
export const TITLE_ID = (n: number) => `slide-${n}-title`;
const ALT_ID = "slide-gap-chart-alt";

const s = deckCopy.slides;
const day = (iso: string | undefined | null) => (iso ? formatDate(iso) : "");
const whole = (value: number) => formatNumber(value, { compact: false });
const mono = (text: string) => <span className="font-mono">{text}</span>;
// A sentence from the data with each project ID in it set in Roboto Mono, as the source lines set them.
function MonoIds({ text }: { text: string }) {
  const parts = text.split(/\b(P\d{6})\b/);
  return <>{parts.map((part, index) => (index % 2 === 1 ? <span key={index} className="font-mono">{part}</span> : part))}</>;
}

function ratio(result: DeckResult, name: string) {
  return <ResultNum result={result} resultKey={name} value={{ part: result.n ?? 0, whole: result.d ?? 0, show: "count" }} />;
}

function count(result: DeckResult, name: string) {
  return <ResultNum result={result} resultKey={name} value={{ value: result.n ?? 0, options: { compact: false } }} />;
}

// A number in the speaker notes, plain text bound to its source.
const note = (sourceKey: string, text: string) => <NoteNum sourceKey={sourceKey} text={text} />;
const noteRatio = (result: DeckResult, name: string) => note(`r:${name}`, numText({ part: result.n ?? 0, whole: result.d ?? 0, show: "count" }));
const noteWord = (data: DeckData, name: string, capital = false) => note(`s:${name}`, numText({ count: data.settings[name].value, capital }));

// The figure's own steps, from its drawing: none when the drawing is missing, so its text version stands in.
const figureSteps = (id: FigureId) => FIGURES[id].steps;

// The parts of the talk in order, slide by slide, without their numbers: buildSlides numbers them.
type Draft = Omit<Slide, "n">;

export function buildSlides(data: DeckData): Slide[] {
  const word = (name: string, capital = false) => <SettingWord data={data} settingKey={name} capital={capital} />;
  const r = (key: string) => measured(data, key);
  const demo = data.demo;
  const showcase = data.showcase.project_id;
  const planDate = demo.plan_date ? day(demo.plan_date) : "";
  const links = demo.links ?? {};
  // The package demo's backup, the comparable packages recorded for the demo plan's package (ticket 116).
  const recording = recordingOf(demo.comparables, demo.step_reference);

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
          box={demo.sentence ?? ""}
          action={s.demoPackage.action}
          href={links.planPackage ?? "/packages"}
          recorded={recording}
          lines={s.demoPackage.lines}
          at={at}
          mode={mode}
        />
      ),
      recorded: recording,
      source: { lead: deckCopy.noteLead, text: s.demoPackage.note },
      notes: recording ? (
        <>
          {s.demoPackage.notes}{" "}
          <Fill template={s.demoPackage.notesRecorded} slots={{ step: recording.step, date: day(recording.result.as_of) }} />
        </>
      ) : (
        s.demoPackage.notes
      ),
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
          box={<MonoIds text={demo.question ?? ""} />}
          question={demo.question}
          action={<Fill template={s.demoAnswer.action} slots={{ project: mono(showcase) }} />}
          href={`/projects/${showcase}`}
          lines={s.demoAnswer.lines}
          at={at}
          mode={mode}
        />
      ),
      source: { lead: deckCopy.sourceLead, text: <Fill template={s.demoAnswer.source} slots={{ project: mono(showcase) }} /> },
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
      id: "knowledge",
      part: "built",
      theme: "light",
      kind: "figure",
      title: s.knowledge.title,
      ...figure("knowledge-model"),
      source: { lead: deckCopy.noteLead, text: s.knowledge.note },
      notes: s.knowledge.notes,
    },
    {
      id: "gap",
      part: "built",
      theme: "light",
      kind: "text",
      title: gap ? <Fill template={s.gap.title} slots={{ start: String(gap.start), end: String(gap.end) }} /> : rows ? s.gap.titleNoGap : s.gap.titleNone,
      steps: (gap ? 1 : 0) + (linked ? 1 : 0) + (rows ? 0 : 1),
      chart: rows
        ? {
            source: "r:award-rows-by-year",
            // On the slide the chart fills its card, half the content box; in the reading view it keeps its size and
            // its frame scrolls on a phone.
            drawing: (mode, labelledById) => (
              <div className="flex flex-col gap-2">
                <AwardKey result={rows} />
                <AwardChart
                  result={rows}
                  gap={gap}
                  width={CHART_WIDTH[mode]}
                  height={240}
                  fluid={mode === "present"}
                  labelledById={labelledById}
                  describedById={ALT_ID}
                />
                <p id={ALT_ID} className="sr-only">
                  <Fill template={s.gap.chartAlt} slots={{ first: String(Math.min(...years)), last: String(Math.max(...years)) }} />{" "}
                  {gap && <Fill template={s.gap.chartGap} slots={{ start: String(gap.start), end: String(gap.end) }} />}
                </p>
              </div>
            ),
            table: <AwardTable result={rows} caption={s.gap.table.rows} />,
          }
        : undefined,
      body: (at, mode) => {
        const lines = [
          ...(gap ? [s.gap.gapNote] : []),
          ...(linked ? [<Fill key="linked" template={s.gap.linked} slots={{ ratio: ratio(linked, "linked-notice") }} />] : []),
        ];
        return (
          <div className="flex flex-col gap-6">
            {lines.length > 0 && <Points lines={lines} at={at} mode={mode} />}
            {rows && lines.length > 0 ? (
              <Step n={lines.length} at={at} as="p">
                <span {...type("note", mode)}>
                  <NewTabLink href="/data">{s.gap.link}</NewTabLink>
                </span>
              </Step>
            ) : rows ? (
              <p {...type("note", mode)}>
                <NewTabLink href="/data">{s.gap.link}</NewTabLink>
              </p>
            ) : (
              <NotMeasured n={lines.length + 1} at={at} mode={mode}>
                {s.gap.noneLine}
              </NotMeasured>
            )}
          </div>
        );
      },
      source: rows ? { lead: deckCopy.sourceLead, text: <Fill template={s.gap.source} slots={{ date: day(rows.measured_on) }} /> } : { lead: deckCopy.sourceLead, text: s.gap.knownSource },
      notes:
        rows && gap && linked ? (
          <Fill template={s.gap.notes} slots={{ start: String(gap.start), end: String(gap.end), ratio: noteRatio(linked, "linked-notice") }} />
        ) : gap ? (
          <Fill template={s.gap.notesGap} slots={{ start: String(gap.start), end: String(gap.end) }} />
        ) : (
          s.gap.notesNone
        ),
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
    {
      id: "hindsight",
      part: "answers",
      theme: "light",
      kind: "text",
      title: caught ? <Fill template={s.hindsight.title} slots={{ ratio: ratio(caught, "hindsight-caught") }} /> : s.hindsight.titleNone,
      outline: caught ? <Fill template={s.hindsight.title} slots={{ ratio: noteRatio(caught, "hindsight-caught") }} /> : s.hindsight.titleNone,
      steps: caught ? (checklist ? 2 : 1) : 1,
      body: (at, mode) =>
        caught ? (
          <Points
            lines={[
              <Fill key="method" template={s.hindsight.method} slots={{ coders: word("hindsight-coders") }} />,
              ...(checklist
                ? [
                    <Fill
                      key="checklist"
                      template={s.hindsight.checklist}
                      slots={{ top: word("risks-per-package"), checklist: word("checklist-size"), ratio: ratio(checklist, "hindsight-checklist") }}
                    />,
                  ]
                : []),
            ]}
            at={at}
            mode={mode}
          />
        ) : (
          <div className="flex flex-col gap-6">
            <p className="text-ink" style={mode === "present" ? { maxWidth: 780 } : undefined} {...type("body", mode)}>
              <Fill template={s.hindsight.methodPlanned} slots={{ coders: word("hindsight-coders") }} />
            </p>
            <NotMeasured n={1} at={at} mode={mode}>
              {s.hindsight.none}
            </NotMeasured>
          </div>
        ),
      source: caught ? { lead: deckCopy.sourceLead, text: <Fill template={s.hindsight.source} slots={{ date: day(caught.measured_on) }} /> } : undefined,
      notes: (
        <>
          <Fill template={s.hindsight.notes} slots={{ coders: noteWord(data, "hindsight-coders", true) }} />
          {interval && interval.low !== undefined && interval.high !== undefined && interval.level !== undefined && (
            <>
              {" "}
              <Fill
                template={s.hindsight.notesInterval}
                slots={{
                  level: note("r:hindsight-interval", deckCopy.percent(whole(interval.level))),
                  low: note("r:hindsight-interval", whole(interval.low)),
                  high: note("r:hindsight-interval", whole(interval.high)),
                }}
              />
            </>
          )}
        </>
      ),
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
      id: "spend",
      part: "grows",
      theme: "light",
      kind: "text",
      title: s.spend.title,
      steps: s.spend.caps.length + 1,
      body: (at, mode) => (
        <div className="flex flex-col gap-8">
          <Points lines={s.spend.caps} at={at} mode={mode} />
          {spend ? (
            <Step n={s.spend.caps.length + 1} at={at} as="p" className="text-ink">
              <span {...type("note", mode)}>
                <Fill
                  template={s.spend.spent}
                  slots={{
                    date: day(spend.latest ?? spend.measured_on),
                    spent: <ResultNum result={spend} resultKey="azure-spend" value={{ written: money(spend.n ?? 0) }} tooltipValue={amount(spend.n ?? 0)} />,
                    budget: (
                      <ResultNum
                        result={{ ...spend, n: spend.budget ?? spend.d }}
                        resultKey="azure-spend"
                        value={{ written: money(spend.budget ?? spend.d ?? 0) }}
                        tooltipValue={amount(spend.budget ?? spend.d ?? 0)}
                      />
                    ),
                    period: <NoteNum sourceKey="r:azure-spend" text={spend.period ?? ""} />,
                  }}
                />
              </span>
            </Step>
          ) : (
            <NotMeasured n={s.spend.caps.length + 1} at={at} mode={mode}>
              {s.spend.noSpend}
            </NotMeasured>
          )}
        </div>
      ),
      source: spend ? { lead: deckCopy.sourceLead, text: <Fill template={s.spend.source} slots={{ date: day(spend.latest ?? spend.measured_on) }} /> } : undefined,
      notes: s.spend.notes,
    },
    {
      id: "change",
      part: "grows",
      theme: "light",
      kind: "text",
      title: s.change.title,
      steps: s.change.lines.length + 1,
      body: (at, mode) => <Points lines={s.change.lines} ask={s.change.ask} at={at} mode={mode} />,
      notes: s.change.notes,
    },

    // ── The close ──
    {
      id: "rubric",
      part: "close",
      theme: "light",
      kind: "text",
      title: s.rubric.title,
      steps: data.rubric.dimensions.length,
      body: (at, mode) => <RubricMap data={data} at={at} mode={mode} />,
      source: { lead: deckCopy.sourceLead, text: s.rubric.source },
      notes: s.rubric.notes,
    },
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
    .map((draft, index) => ({ ...draft, n: index + 1 }));
}

// The rubric's dimensions, a press each: its points, where Strata earns them, and what a reviewer can open.
function RubricMap({ data, at, mode }: { data: DeckData; at: number; mode: Mode }) {
  const w = s.rubric;
  const t = (role: Parameters<typeof type>[0]) => type(role, mode);
  // In the reading view each dimension is a block of its own, so the map reflows to a phone's width.
  if (mode === "read") {
    return (
      <ul className="flex flex-col divide-y divide-line">
        {data.rubric.dimensions.map((dimension, index) => (
          <Step key={dimension.key} n={index + 1} at={at} as="li" className="flex flex-col gap-1 py-3">
            <p className="font-semibold text-ink-heading" {...t("note")}>
              {dimension.name}, <RubricPoints dimensionKey={dimension.key} points={dimension.points} /> {w.columns.points.toLowerCase()}
            </p>
            <p className="text-ink" {...t("note")}>
              <Fill template={w.where[dimension.key] ?? ""} slots={{ checks: <SettingWord data={data} settingKey="check-count" /> }} />
            </p>
            <div {...t("note")}>
              <RubricOpen data={data} dimension={dimension.key} />
            </div>
          </Step>
        ))}
      </ul>
    );
  }
  return (
    <div className="flex flex-col">
      <div className="grid gap-x-6 border-b border-line pb-2 text-ink-muted" style={{ gridTemplateColumns: "13rem 4rem minmax(0,1fr) 13rem" }}>
        <span {...t("label")}>{w.columns.dimension}</span>
        <span className="text-right" {...t("label")}>
          {w.columns.points}
        </span>
        <span {...t("label")}>{w.columns.where}</span>
        <span {...t("label")}>{w.columns.open}</span>
      </div>
      {data.rubric.dimensions.map((dimension, index) => (
        <Step
          key={dimension.key}
          n={index + 1}
          at={at}
          className="grid gap-x-6 border-b border-line py-3"
          style={{ gridTemplateColumns: "13rem 4rem minmax(0,1fr) 13rem" }}
        >
          <span className="font-semibold text-ink-heading" {...t("note")}>
            {dimension.name}
          </span>
          <span className="text-right text-ink tabular-nums" {...t("note")}>
            <RubricPoints dimensionKey={dimension.key} points={dimension.points} />
          </span>
          <span className="text-ink" {...t("note")}>
            <Fill template={w.where[dimension.key] ?? ""} slots={{ checks: <SettingWord data={data} settingKey="check-count" /> }} />
          </span>
          <span {...t("note")}>
            <RubricOpen data={data} dimension={dimension.key} />
          </span>
        </Step>
      ))}
    </div>
  );
}

// What a reviewer can open for a dimension of the rubric: screens in the app, and the dashboard when its address is set.
function RubricOpen({ data, dimension }: { data: DeckData; dimension: string }) {
  const o = s.rubric.open;
  const showcase = data.showcase.project_id;
  // Operations shows the dashboard once its address is set; until then, Data readiness, where the nightly job's
  // measures show.
  const readiness = (
    <NewTabLink key="data" href="/data">
      {o.readiness}
    </NewTabLink>
  );
  const links: Record<string, ReactNode[]> = {
    architecture: [
      readiness,
      <NewTabLink key="connections" href={`/projects/${showcase}/connections`}>
        <Fill template={o.connections} slots={{ project: <span className="font-mono">{showcase}</span> }} />
      </NewTabLink>,
    ],
    method: [
      <NewTabLink key="workspace" href={`/packages/${data.demo.step_reference}`}>
        {o.workspace}
      </NewTabLink>,
    ],
    domain: [
      <NewTabLink key="check" href={data.demo.links?.checkPlan ?? data.demo.plan_href}>
        {o.checkPlan}
      </NewTabLink>,
    ],
    operations: [
      data.urls.dashboard ? (
        <NewTabLink key="dashboard" href={data.urls.dashboard}>
          {o.dashboard}
        </NewTabLink>
      ) : (
        readiness
      ),
    ],
  };
  return (
    <ul className="flex flex-col gap-1">
      {(links[dimension] ?? []).map((link, index) => (
        <li key={index}>{link}</li>
      ))}
    </ul>
  );
}

// The step texts a figure's presses bring in, for the live region and the speaker notes.
export function figureStepText(id: FigureId, step: number): string {
  return (figureCopy[id].steps as readonly string[])[step - 1] ?? "";
}
