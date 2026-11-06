// The deep research talk's slides (ticket 162; .notes/deck3/brief.md, section 4), built from the deck's data on the
// engine's own layouts: the bookends, the agenda, the five topics with their navy openers, figure slides, points,
// tiles and a live demo with its backup. Every number on a slide is bound to a setting or a recorded entry; every
// word is in research/copy.ts.
import { useContext, type ReactNode } from "react";
import { History } from "lucide-react";
import { Fill } from "../../components/Fill";
import { FIGURES, type FigureId } from "../../figures/registry";
import { cx } from "../../lib/cx";
import { deckCopy } from "../copy";
import type { DeckData } from "../data";
import { Demo, PressTo, Points, Step, Tiles } from "../layouts";
import { numText } from "../../components/Num";
import { NoteNum, RecordedNum, SettingWord } from "../nums";
import { type, type Mode } from "../ramp";
import type { Slide } from "../slides";
import { TOPICS } from "../talk";
import { researchCopy } from "./copy";

const s = researchCopy.slides;
type Topic = (typeof TOPICS.research)[number];
type Draft = Omit<Slide, "n">;

const mono = (text: string) => <span className="font-mono">{text}</span>;
// The demo's backup images (web/public/deck/research), each with its width over its height, so its box keeps the
// image's own shape: the recorded run's two screenshots, cropped above the Ask bar, at 604 by 612; and four pages of the
// printed brief, rendered at 110 dpi, at 935 by 1210.
const SHOT = "/deck/research/";
const RUN_RATIO = 604 / 612;
const PAGE_RATIO = 935 / 1210;
const RUN_SHOTS = [
  { file: "run.png", alt: s.demo.runAlt },
  { file: "checking.png", alt: s.demo.checkingAlt },
];
const PAGES = [
  { file: "cover.png", alt: s.demo.coverAlt },
  { file: "ground.png", alt: s.demo.groundAlt },
  { file: "by-site.png", alt: s.demo.bySiteAlt },
  { file: "by-site-photos.png", alt: s.demo.bySitePhotosAlt },
];
// The run's screenshots' height on the canvas, so they and their caption fill the box's place; the pages fill its width.
const RUN_HEIGHT = 410;
// The demo's lines, then its two backup presses.
const DEMO_LINES = s.demo.lines.length;

// The topics' names and lines, with the counts in the third topic's line bound to their settings.
export function researchTopics(data: DeckData): Record<Topic, { name: string; line: ReactNode }> {
  const t = researchCopy.topics;
  return {
    ...t,
    works: {
      name: t.works.name,
      line: (
        <Fill
          template={t.works.line}
          slots={{
            sources: <SettingWord data={data} settingKey="research-source-count" capital />,
            checks: <SettingWord data={data} settingKey="check-count" />,
          }}
        />
      ),
    },
  };
}

// A note-size line under a figure, brought in by a press.
function NoteStep({ n, at, mode, children }: { n: number; at: number; mode: Mode; children: ReactNode }) {
  return (
    <Step n={n} at={at} as="p" className="text-pretty text-ink">
      <span {...type("note", mode)}>{children}</span>
    </Step>
  );
}

// A backup image in a bordered box with the image's own shape: a fixed height, or the width it is given, and the
// other side from the ratio. The image is contained in the box, so it is never stretched.
function Shot({ file, alt, ratio, height }: { file: string; alt: string; ratio: number; height?: number }) {
  return (
    <div className={cx("shrink-0 overflow-hidden rounded-sm border border-line bg-surface", !height && "w-full")} style={{ aspectRatio: ratio, height }} data-research-shot>
      <img src={SHOT + file} alt={alt} className="block size-full object-contain" draggable={false} />
    </div>
  );
}

// The demo slide's body: the box that opens the project's Deep research tab, a line a press, and then, for when the
// App is down, the recorded run and the printed brief, a press each. On the canvas each backup takes the box's place;
// in the reading view both show under the lines.
function ResearchDemo({ data, at, mode }: { data: DeckData; at: number; mode: Mode }) {
  const press = useContext(PressTo);
  const demo = data.research.demo;
  const project = mono(demo.project_id);
  // The run's two screenshots side by side at one height; in the reading view, half the column each.
  const run = (
    <figure className="flex flex-col gap-2" data-research-backup="run">
      <div className={mode === "present" ? "flex gap-4" : "grid grid-cols-2 gap-4"}>
        {RUN_SHOTS.map((shot) => (
          <Shot key={shot.file} {...shot} ratio={RUN_RATIO} height={mode === "present" ? RUN_HEIGHT : undefined} />
        ))}
      </div>
      <figcaption className="text-ink-muted" {...type("note", mode)}>
        <Fill template={s.demo.run} slots={{ project }} />
      </figcaption>
    </figure>
  );
  // The brief's four pages in a row across the stage; in the reading view, two to a row.
  const printed = (
    <figure className="flex flex-col gap-2" data-research-backup="printed">
      <div className={mode === "present" ? "grid grid-cols-4 gap-3" : "grid grid-cols-2 gap-4"}>
        {PAGES.map((page) => (
          <Shot key={page.file} {...page} ratio={PAGE_RATIO} />
        ))}
      </div>
      <figcaption className="text-ink-muted" {...type("note", mode)}>
        <Fill template={s.demo.printed} slots={{ project }} />
      </figcaption>
    </figure>
  );
  const backup = (label: string, step: number) => (
    <button
      type="button"
      onClick={() => press?.(step)}
      data-research-backup-button={step}
      className="inline-flex h-11 shrink-0 items-center gap-2 rounded-sm border-2 border-primary px-4 text-button text-primary transition-paint duration-150 hover:bg-tint"
    >
      <History aria-hidden="true" className="size-4" />
      {label}
    </button>
  );
  const box = (
    <Demo
      box={<Fill template={s.demo.box} slots={{ project, name: demo.project_name }} />}
      action={s.demo.action}
      href={demo.href}
      lines={s.demo.lines}
      at={Math.min(at, DEMO_LINES)}
      mode={mode}
      extra={mode === "present" ? <>{backup(s.demo.showRun, DEMO_LINES + 1)}{backup(s.demo.showPrinted, DEMO_LINES + 2)}</> : undefined}
    />
  );
  if (mode === "read") {
    return (
      <div className="flex flex-col gap-6">
        {box}
        {run}
        {printed}
      </div>
    );
  }
  // On the canvas a backup lies over the box, which keeps its place unseen and out of reach, so the slide measures the
  // same at every press and its title keeps its size whichever way the talk arrives. Opacity, not visibility: the
  // lines a press has reached set their own visibility.
  const shown = at === DEMO_LINES + 1 ? run : at > DEMO_LINES + 1 ? printed : null;
  return (
    <div className="relative" data-research-demo>
      <div className={shown ? "opacity-0" : undefined} aria-hidden={shown ? true : undefined} inert={shown ? true : undefined}>
        {box}
      </div>
      {shown && (
        <Step n={at} at={at} className="absolute inset-x-0 top-0">
          {shown}
        </Step>
      )}
    </div>
  );
}

export function buildResearchSlides(data: DeckData): Slide[] {
  const word = (name: string, capital = false) => <SettingWord data={data} settingKey={name} capital={capital} />;
  // A setting as plain text bound to its key, for the notes window's outline, where a title sits inside a button.
  const noteWord = (name: string, capital = false) => <NoteNum sourceKey={`s:${name}`} text={numText({ count: data.settings[name].value, capital })} />;
  // A recorded number, or the words for one not recorded yet.
  const rec = (key: string) => (data.recorded?.[key] ? <RecordedNum data={data} recordedKey={key} /> : deckCopy.states.notMeasured);
  const topics = researchTopics(data);
  const research = data.research;
  const presenters = { names: research.presenters, date: research.date };

  // A figure slide: the drawing's steps, then `extra` items of the slide's own. A drawing that has not landed takes
  // no presses, and its text version stands in its place.
  const figure = (id: FigureId, extra = 0, wide = true) => {
    const steps = FIGURES[id].steps;
    return { figure: { id, steps, wide }, steps: steps + extra };
  };
  const opener = (topic: Topic, hairline: string, label: string, notes: string, lead?: string): Draft => ({
    id: topic,
    part: topic,
    theme: "navy",
    kind: "opener",
    title: topics[topic].name,
    lead: lead ?? topics[topic].line,
    steps: 0,
    topic,
    hairline,
    hairlineLabel: label,
    notes,
  });
  const source = (text: ReactNode) => ({ lead: deckCopy.sourceLead, text });
  const note = (text: ReactNode) => ({ lead: deckCopy.noteLead, text });

  const drafts: Draft[] = [
    // ── The welcome and the agenda ──
    {
      id: "welcome",
      part: "open",
      theme: "navy",
      kind: "title",
      title: s.welcome.statement,
      lead: s.welcome.line,
      presenters,
      steps: 0,
      hairline: "ground",
      hairlineLabel: s.welcome.figure,
      notes: s.welcome.notes,
    },
    { id: "agenda", part: "open", theme: "light", kind: "agenda", title: s.agenda.title, steps: 5, notes: s.agenda.notes },

    // ── 1. How we got here ──
    opener("here", "two-slabs", s.hereOpener.figure, s.hereOpener.notes, s.hereOpener.line),
    {
      id: "timeline",
      part: "here",
      theme: "light",
      kind: "figure",
      title: s.timeline.title,
      ...figure("merge-timeline"),
      source: source(s.timeline.source),
      notes: s.timeline.notes,
    },
    {
      id: "two-apps",
      part: "here",
      theme: "light",
      kind: "figure",
      title: s.twoApps.title,
      ...figure("two-apps", 1),
      body: (at, mode) => (
        <NoteStep n={1} at={at} mode={mode}>
          <Fill
            template={s.twoApps.counted}
            slots={{
              linesPrism: rec("lines-prism"),
              testsPrism: rec("tests-prism"),
              linesProcintel: rec("lines-procintel"),
              testsProcintel: rec("tests-procintel"),
            }}
          />
        </NoteStep>
      ),
      source: source(s.twoApps.source),
      notes: s.twoApps.notes,
    },
    {
      id: "why-prism",
      part: "here",
      theme: "light",
      kind: "text",
      title: s.whyPrism.title,
      steps: s.whyPrism.lines.length + 1,
      body: (at, mode) => <Points lines={s.whyPrism.lines} ask={s.whyPrism.ask} at={at} mode={mode} />,
      notes: s.whyPrism.notes,
    },
    {
      id: "five-ways",
      part: "here",
      theme: "light",
      kind: "figure",
      title: s.fiveWays.title,
      ...figure("five-ways"),
      source: source(s.fiveWays.source),
      notes: s.fiveWays.notes,
    },
    {
      id: "set-aside",
      part: "here",
      theme: "light",
      kind: "text",
      title: s.setAside.title,
      steps: s.setAside.tiles.length + 1,
      body: (at, mode) => <Tiles tiles={s.setAside.tiles} closing={s.setAside.closing} at={at} mode={mode} />,
      notes: s.setAside.notes,
    },

    // ── 2. Deep research ──
    opener("brief", "passages", s.briefOpener.figure, s.briefOpener.notes),
    {
      id: "what-it-is",
      part: "brief",
      theme: "light",
      kind: "figure",
      title: s.whatItIs.title,
      ...figure("brief-sections", 2),
      body: (at, mode) => (
        <div className="flex flex-col gap-1">
          <NoteStep n={1} at={at} mode={mode}>
            <Fill template={s.whatItIs.lines[0]} slots={{ reports: word("isr-reports") }} />
          </NoteStep>
          <NoteStep n={2} at={at} mode={mode}>
            {s.whatItIs.lines[1]}
          </NoteStep>
        </div>
      ),
      source: note(s.whatItIs.source),
      notes: s.whatItIs.notes,
    },
    {
      id: "gap",
      part: "brief",
      theme: "light",
      kind: "figure",
      title: s.gap.title,
      ...figure("record-gap", 1),
      body: (at, mode) => (
        <NoteStep n={1} at={at} mode={mode}>
          <Fill
            template={s.gap.counted}
            slots={{
              isrProgress: rec("isr-progress"),
              wajirProgress: rec("wajir-progress"),
              lateAwards: rec("late-awards"),
              lateDays: word("late-award-days"),
            }}
          />
        </NoteStep>
      ),
      source: source(s.gap.source),
      notes: s.gap.notes,
    },
    {
      id: "considered",
      part: "brief",
      theme: "light",
      kind: "text",
      title: s.considered.title,
      steps: s.considered.lines.length + 1,
      body: (at, mode) => <Points lines={s.considered.lines} ask={s.considered.ask} at={at} mode={mode} />,
      notes: s.considered.notes,
    },

    // ── 3. How it works ──
    opener("works", "filter", s.worksOpener.figure, s.worksOpener.notes),
    {
      id: "demo-research",
      part: "works",
      theme: "light",
      kind: "text",
      title: s.demo.title,
      steps: DEMO_LINES + 2,
      body: (at, mode) => <ResearchDemo data={data} at={at} mode={mode} />,
      source: note(s.demo.note),
      notes: s.demo.notes,
    },
    {
      id: "pipeline",
      part: "works",
      theme: "light",
      kind: "figure",
      title: <Fill template={s.pipeline.title} slots={{ sources: word("research-source-count", true), checks: word("check-count") }} />,
      outline: <Fill template={s.pipeline.title} slots={{ sources: noteWord("research-source-count", true), checks: noteWord("check-count") }} />,
      ...figure("research-run"),
      source: source(s.pipeline.source),
      notes: s.pipeline.notes,
    },
    {
      id: "checks",
      part: "works",
      theme: "light",
      kind: "figure",
      title: <Fill template={s.checks.title} slots={{ checks: word("check-count") }} />,
      outline: <Fill template={s.checks.title} slots={{ checks: noteWord("check-count") }} />,
      ...figure("checks", 1),
      body: (at, mode) => (
        <NoteStep n={1} at={at} mode={mode}>
          <Fill template={s.checks.kept} slots={{ keptLow: rec("kept-low"), keptHigh: rec("kept-high") }} />
        </NoteStep>
      ),
      source: source(s.checks.source),
      notes: s.checks.notes,
    },
    {
      id: "honest",
      part: "works",
      theme: "light",
      kind: "text",
      title: s.honest.title,
      steps: s.honest.lines.length + 1,
      body: (at, mode) => <Points lines={s.honest.lines} ask={s.honest.ask} at={at} mode={mode} />,
      notes: s.honest.notes,
    },

    // ── 4. The decisions ──
    opener("decisions", "rungs", s.decisionsOpener.figure, s.decisionsOpener.notes),
    {
      id: "ladder",
      part: "decisions",
      theme: "light",
      kind: "figure",
      title: s.ladder.title,
      ...figure("evidence-ladder", 2, false),
      body: (at, mode) => (
        <div className="flex flex-col gap-4">
          <NoteStep n={1} at={at} mode={mode}>
            <Fill template={s.ladder.lines[0]} slots={{ metres: rec("tile-metres") }} />
          </NoteStep>
          <NoteStep n={2} at={at} mode={mode}>
            {s.ladder.lines[1]}
          </NoteStep>
        </div>
      ),
      source: source(s.ladder.source),
      notes: s.ladder.notes,
    },
    {
      id: "posts",
      part: "decisions",
      theme: "light",
      kind: "figure",
      title: s.posts.title,
      ...figure("post-funnel", 1),
      body: (at, mode) => (
        <NoteStep n={1} at={at} mode={mode}>
          {s.posts.line}
        </NoteStep>
      ),
      source: source(s.posts.source),
      notes: s.posts.notes,
    },
    {
      id: "other-decisions",
      part: "decisions",
      theme: "light",
      kind: "text",
      title: s.otherDecisions.title,
      steps: s.otherDecisions.tiles.length,
      body: (at, mode) => <Tiles tiles={s.otherDecisions.tiles} at={at} mode={mode} />,
      notes: s.otherDecisions.notes,
    },

    // ── 5. What comes next ──
    opener("next", "sediment", s.nextOpener.figure, s.nextOpener.notes),
    {
      id: "next-steps",
      part: "next",
      theme: "light",
      kind: "text",
      title: s.nextSteps.title,
      steps: s.nextSteps.tiles.length,
      body: (at, mode) => <Tiles tiles={s.nextSteps.tiles} at={at} mode={mode} />,
      source: note(s.nextSteps.source),
      notes: s.nextSteps.notes,
    },
    {
      id: "built-designed",
      part: "next",
      theme: "light",
      kind: "text",
      title: s.builtDesigned.title,
      steps: s.builtDesigned.tiles.length + 1,
      body: (at, mode) => <Tiles tiles={s.builtDesigned.tiles} closing={s.builtDesigned.closing} at={at} mode={mode} />,
      notes: s.builtDesigned.notes,
    },

    // ── The close ──
    {
      id: "thanks",
      part: "close",
      theme: "navy",
      kind: "close",
      title: s.thanks.title,
      lead: s.thanks.line,
      presenters,
      links: [
        { href: research.demo.href, label: s.thanks.links.tab },
        ...(data.urls.repo ? [{ href: data.urls.repo, label: s.thanks.links.repo }] : []),
      ],
      steps: 0,
      hairline: "ground",
      hairlineLabel: s.thanks.figure,
      notes: s.thanks.notes,
    },
  ];

  return drafts.map((draft, index) => {
    const speaker = researchCopy.speaker[draft.id];
    const figureSteps = draft.figure?.steps ?? 0;
    const figureAdds = Array.from({ length: figureSteps }, (_, k) => speaker?.figureAdds?.[k] ?? null);
    return {
      ...draft,
      n: index + 1,
      cue: speaker?.cue,
      adds: speaker ? [...figureAdds, ...(speaker.adds ?? [])] : undefined,
      asked: speaker?.asked,
      diagrams: speaker?.diagrams,
    };
  });
}
