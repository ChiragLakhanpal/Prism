// A project's Deep research tab (ticket 149): the latest brief from GET /api/projects/{pid}/research (ticket 148), a
// run started with "Research this project" (POST, the answer stream's steps shown while it runs, as the ask box shows
// them), and "Download as PDF", which prints the brief as the sample does (.notes/prism-sample/template/build5.py)
// through the print view in ResearchPrint.tsx and the browser's own print, with no server renderer.
//
// On screen the sections stack in the page column in the sample's order: the picture and the bottom line;
// developments, newest first; by site, with the Sentinel-2 grids side by side; what people are saying; what this means
// for procurement, with what I could not see; and the sources. Each marker opens the evidence drawer at its item, and
// each source's "Open the source" opens the item's own page in a new tab. A source the run did not reach is one line
// under the section it feeds, from the run's coverage. Removed sentences show under the brief with their reasons, as
// answers do.
//
// States: loading, no brief yet (the button and one sentence on what the run reads), running (the run's plan as a
// progress rail, components/ResearchProgress.tsx, ticket 157; a failed or dropped run keeps the ask box's steps), the brief,
// a source not reached, the service that didn't answer (the read or the run), and an account that can't read
// Prism's tables.
import { useEffect, useRef, useState, type ReactNode } from "react";
import { Alert } from "../../components/Alert";
import { DRAWER_ID } from "../../components/AnswerPanel";
import { Button } from "../../components/Button";
import { RemovedBox, removedFrom } from "../../components/Checks";
import { ResearchProgress } from "../../components/ResearchProgress";
import { CitationMarker } from "../../components/CitationMarker";
import { EightColumns } from "../../components/EightColumns";
import { ExternalLink } from "../../components/ExternalLink";
import { Fill } from "../../components/Fill";
import { LoadError } from "../../components/LoadError";
import { linkProjectIds } from "../../components/ProjectId";
import { SkeletonLine, SkeletonText } from "../../components/Skeleton";
import { Steps, type Step } from "../../components/Steps";
import { copy } from "../../copy";
import type { EvidenceEvent } from "../../lib/answer";
import { evidenceHref, evidenceIn, openEvidence, remember, visited as visitedStore } from "../../lib/evidence";
import { formatCount, formatDate } from "../../lib/format";
import { useLoad } from "../../lib/load";
import {
  briefFrom,
  briefNumbers,
  itemFor,
  sourceName,
  sourceWords,
  voiceTemplate,
  notReachedIn,
  paragraphsOf,
  planFrom,
  satelliteFor,
  tileYear,
  withStep,
  type Brief,
  type ResearchItem,
  type ResearchPlan,
  type ResearchSentence,
  type ResearchStep,
  type Sections,
  type Site,
} from "../../lib/research";
import { address } from "../../lib/router";
import { StreamError, streamEvents } from "../../lib/sse";
import { useStore } from "../../lib/store";
import { asOfOf, viewOf, withReadParams } from "../../lib/view";
import { FieldPhotos } from "./FieldPhotos";
import { ResearchPrint } from "./ResearchPrint";

const words = copy.research;

const capital = (text: string) => text.charAt(0).toUpperCase() + text.slice(1);

// The page's markers after one sentence, numbered as the Sources list numbers them.
function Marks({ ids, brief, numbers }: { ids: string[]; brief: Brief; numbers: Map<string, number> }) {
  const here = useStore(address);
  const seen = useStore(visitedStore);
  const open = evidenceIn(here.search);
  return (
    <>
      {ids.map((id) => {
        const n = numbers.get(id);
        if (n === undefined) return null;
        return (
          <CitationMarker
            key={id}
            n={n}
            evidenceId={id}
            source={sourceName(brief, id)}
            href={evidenceHref(id)}
            drawerId={DRAWER_ID}
            active={open === id}
            opened={seen.has(id)}
            onOpen={(marker) => openEvidence(id, { serial: null, sentence: null, marker, runId: brief.run_id })}
          />
        );
      })}
    </>
  );
}

function Said({ sentence, brief, numbers }: { sentence: ResearchSentence; brief: Brief; numbers: Map<string, number> }) {
  return (
    <span data-research-sentence>
      {linkProjectIds(sentence.text)}
      <Marks ids={sentence.evidence_ids} brief={brief} numbers={numbers} />
    </span>
  );
}

// Several sentences, one after another in a paragraph.
function Paragraph({ sentences, brief, numbers, className }: { sentences: ResearchSentence[]; brief: Brief; numbers: Map<string, number>; className?: string }) {
  if (sentences.length === 0) return null;
  return (
    <p className={className ?? "max-w-prose text-body text-ink"}>
      {sentences.map((sentence, index) => (
        <span key={index}>
          {index > 0 && " "}
          <Said sentence={sentence} brief={brief} numbers={numbers} />
        </span>
      ))}
    </p>
  );
}

// One sentence to a bullet, each with its markers (ticket 156).
function Bullets({ sentences, brief, numbers, className }: { sentences: ResearchSentence[]; brief: Brief; numbers: Map<string, number>; className?: string }) {
  if (sentences.length === 0) return null;
  return (
    <ul data-bullets className={className ?? "mt-2 flex max-w-prose list-disc flex-col gap-1 pl-6 text-body text-ink marker:text-primary"}>
      {sentences.map((sentence, index) => (
        <li key={index}>
          <Said sentence={sentence} brief={brief} numbers={numbers} />
        </li>
      ))}
    </ul>
  );
}

// The one line a source not reached leaves under the section it feeds, with the reader's own note.
function NotReached({ brief, sectionKey }: { brief: Brief; sectionKey: keyof Sections }) {
  const missed = notReachedIn(brief, sectionKey);
  if (missed.length === 0) return null;
  return (
    <ul className="mt-2 flex flex-col gap-1">
      {missed.map((entry) => (
        <li key={entry.source} data-not-reached={entry.source} className="max-w-prose text-caption text-ink-muted">
          {words.notReached(capital(sourceWords(entry.source, entry.label)))}
          {entry.note && " "}
          {entry.note}
        </li>
      ))}
    </ul>
  );
}

// A site's two Sentinel-2 grids, side by side, oldest year first, nine tiles each, and the caption.
export function SatelliteFigure({ item, mark }: { item: ResearchItem; mark: ReactNode }) {
  const [first, last] = [item.image_urls[0], item.image_urls[item.image_urls.length - 1]];
  const years = [tileYear(first) ?? "", tileYear(last) ?? ""];
  return (
    <figure data-s2-figure className="mt-4 max-w-xl">
      <div className="grid grid-cols-2 gap-4">
        {[first, last].map((tiles, index) => (
          <div key={index} data-s2-grid>
            <p className="mb-1 text-small font-semibold text-ink-heading">{years[index]}</p>
            <div className="grid grid-cols-3 border border-line">
              {tiles.slice(0, 9).map((url) => (
                <img key={url} src={url} alt="" width={256} height={256} className="block aspect-square h-auto w-full bg-surface-2" />
              ))}
            </div>
          </div>
        ))}
      </div>
      <figcaption className="mt-2 text-caption text-ink-muted">
        <Fill template={words.satellite} slots={{ place: item.location?.name ?? item.title, first: years[0], last: years[1] }} />
        {mark}
      </figcaption>
    </figure>
  );
}

function SiteGroup({ site, brief, numbers }: { site: Site; brief: Brief; numbers: Map<string, number> }) {
  const satellites = satelliteFor(brief, site);
  return (
    <div data-site className="mt-6">
      <h3 className="max-w-prose text-h3 text-ink-heading">
        <Said sentence={site.title} brief={brief} numbers={numbers} />
      </h3>
      <Bullets sentences={site.sentences} brief={brief} numbers={numbers} />
      {satellites.map((item) => (
        <SatelliteFigure key={item.evidence_id} item={item} mark={<Marks ids={[item.evidence_id]} brief={brief} numbers={numbers} />} />
      ))}
    </div>
  );
}

function Section({ id, title, children }: { id: string; title: string; children: ReactNode }) {
  return (
    <section data-research-section={id} aria-labelledby={`research-${id}`} className="mt-12 first:mt-0">
      {/* The navy rule under each section's title, the band that sets one section off from the next (ticket 156). */}
      <h2 id={`research-${id}`} className="border-b-2 border-navy pb-2 text-h2 text-ink-heading">
        {title}
      </h2>
      {children}
    </section>
  );
}

// The brief on screen, every section in the sample's order.
export function BriefView({ brief }: { brief: Brief }) {
  const { sections } = brief;
  const numbers = briefNumbers(sections);
  const cited = [...numbers.keys()];
  return (
    <div data-research-brief>
      <Section id="picture" title={words.section.picture}>
        {sections.headline && (
          <p data-research-headline className="mt-2 max-w-prose text-lead font-semibold text-ink-heading">
            <Said sentence={sections.headline} brief={brief} numbers={numbers} />
          </p>
        )}
        {paragraphsOf(sections.picture).map((paragraph, index) => (
          <Paragraph key={index} sentences={paragraph} brief={brief} numbers={numbers} className="mt-3 max-w-prose text-body text-ink" />
        ))}
        <NotReached brief={brief} sectionKey="picture" />
        <h3 className="mt-6 text-h3 text-ink-heading">{words.section.bottomLine}</h3>
        <ol className="mt-2 flex max-w-prose list-decimal flex-col gap-2 pl-6 text-body text-ink marker:font-bold marker:text-primary">
          {sections.bottom_line.map((sentence, index) => (
            <li key={index} data-bottom-line>
              <Said sentence={sentence} brief={brief} numbers={numbers} />
            </li>
          ))}
        </ol>
      </Section>
      <Section id="developments" title={words.section.developments}>
        <ol className="mt-2 max-w-prose border-t border-line">
          {sections.developments.map((row, index) => (
            <li key={index} data-development className="flex flex-col gap-1 border-b border-line py-3 @md/page:flex-row @md/page:gap-4">
              <span data-development-date className="shrink-0 text-small font-semibold text-ink-heading @md/page:w-36">
                {row.date_known && row.date ? formatDate(row.date, { style: "table" }) : words.undated}
              </span>
              <Bullets sentences={row.sentences} brief={brief} numbers={numbers} className="flex list-disc flex-col gap-1 pl-6 text-body text-ink marker:text-primary" />
            </li>
          ))}
        </ol>
        <NotReached brief={brief} sectionKey="developments" />
      </Section>
      <Section id="by-site" title={words.section.bySite}>
        {sections.by_site.map((site, index) => (
          <SiteGroup key={index} site={site} brief={brief} numbers={numbers} />
        ))}
        <NotReached brief={brief} sectionKey="by_site" />
      </Section>
      <Section id="voices" title={words.section.voices}>
        <div className="mt-2 flex max-w-prose flex-col gap-4">
          {sections.voices.map((voice, index) => (
            <blockquote key={index} data-voice className="border-l-4 border-primary pl-4">
              <p className="text-lead text-ink">
                <Said sentence={voice} brief={brief} numbers={numbers} />
              </p>
              <footer className="mt-1 text-caption text-ink-muted">
                <Fill
                  template={voiceTemplate(voice)}
                  slots={{ who: voice.who, outlet: voice.outlet, date: voice.date ? formatDate(voice.date) : "" }}
                />
              </footer>
            </blockquote>
          ))}
        </div>
        <NotReached brief={brief} sectionKey="voices" />
      </Section>
      <Section id="questions" title={words.section.questions}>
        <ol className="mt-2 flex max-w-prose list-decimal flex-col gap-3 pl-6 text-body text-ink marker:font-bold marker:text-primary">
          {sections.questions.map((question, index) => (
            <li key={index} data-question>
              <b className="font-semibold text-ink-heading">{question.lead}</b>
              <Bullets sentences={question.sentences} brief={brief} numbers={numbers} className="mt-1 flex list-disc flex-col gap-1 pl-6 marker:font-normal marker:text-primary" />
            </li>
          ))}
        </ol>
        <NotReached brief={brief} sectionKey="questions" />
        <h3 className="mt-6 text-h3 text-ink-heading">{words.section.couldNotSee}</h3>
        <Bullets sentences={sections.could_not_see} brief={brief} numbers={numbers} />
      </Section>
      <Section id="sources" title={words.section.sources}>
        <ol data-research-sources className="mt-2 flex max-w-prose flex-col gap-3">
          {cited.map((id) => {
            const item = itemFor(brief, id);
            return (
              <li key={id} className="flex gap-3 text-small text-ink">
                <span data-source-number className="inline-flex h-5 min-w-6 shrink-0 items-center justify-center rounded-pill border border-primary px-1 text-label font-bold text-primary tabular-nums">
                  {numbers.get(id)}
                </span>
                <span className="min-w-0 wrap-break-word">
                  {item ? (
                    <>
                      {sourceName(brief, id)}
                      {". "}
                      {item.title}
                      {". "}
                      <ExternalLink href={item.url} name={`, ${sourceName(brief, id)}`}>
                        {words.openSource}
                      </ExternalLink>
                    </>
                  ) : (
                    sourceName(brief, id)
                  )}
                </span>
              </li>
            );
          })}
        </ol>
      </Section>
    </div>
  );
}

// reading: the run is done and its brief is being read, so the steps stay until the brief replaces them. code is the
// error event's (ticket 148's run.ERRORS), which picks the alert's sentence.
// plan is the run's plan event (ticket 157); started and lastEventAt are from Date.now(), for the elapsed clock and the
// still-working line; checked counts the sentence and removed events while the checks run.
type RunState = {
  phase: "idle" | "running" | "reading" | "failed" | "dropped";
  steps: ResearchStep[];
  status: number | null;
  code?: string | null;
  plan: ResearchPlan | null;
  started: number;
  lastEventAt: number;
  checked: number;
};
const IDLE: RunState = { phase: "idle", steps: [], status: null, plan: null, started: 0, lastEventAt: 0, checked: 0 };

// The run's steps in the ask box's words: present tense while running, past once done; a source not reached says so.
function stepLines(steps: ResearchStep[]): Step[] {
  return steps.map((step) => {
    const state = step.status === "running" ? "running" : "done";
    if (step.kind === "source") {
      const name = sourceWords(step.source, step.label);
      const count = step.items ?? 0;
      if (step.stored_on && step.status === "done") {
        const date = formatDate(step.stored_on);
        const lines = words.steps.stored;
        const done = count === 0 ? lines.none(name, date) : count === 1 ? lines.one(name, date) : lines.several(name, date, formatCount(count));
        return { key: step.id, running: words.steps.source.running(name), done, state };
      }
      const done =
        step.status === "not_reached" ? (
          <>
            {words.notReached(capital(name))}
            {step.note && " "}
            {step.note}
          </>
        ) : count === 0 ? (
          words.steps.source.none(name)
        ) : count === 1 ? (
          words.steps.source.one(name)
        ) : (
          words.steps.source.several(name, formatCount(count))
        );
      return { key: step.id, running: words.steps.source.running(name), done, state };
    }
    if (step.kind === "checking") {
      const removed = step.removed ?? 0;
      const done = removed === 0 ? words.steps.check.none : removed === 1 ? words.steps.check.one : words.steps.check.several(formatCount(removed));
      return { key: step.id, running: words.steps.check.running, done, state };
    }
    if (step.kind === "writing" && step.kept_from) {
      const kept = words.steps.kept(formatDate(step.kept_from));
      return { key: step.id, running: kept, done: kept, state };
    }
    const line = step.kind === "facts" ? words.steps.facts : step.kind === "writing" ? words.steps.write : null;
    return { key: step.id, running: line?.running ?? step.label ?? step.id, done: line?.done ?? step.label ?? step.id, state };
  });
}

export function ResearchTab({ pid, project }: { pid: string; project?: { name: string; country: string | null; agencies: string[] } | null }) {
  const search = useStore(address).search;
  const [reads, setReads] = useState(0);
  const [load, retry] = useLoad<unknown>(withReadParams(`/api/projects/${encodeURIComponent(pid)}/research`, search), String(reads));
  const [run, setRun] = useState<RunState>(IDLE);
  const stopping = useRef<AbortController | null>(null);
  // The read on screen when the run finished, so the steps give way only to the brief the run stored.
  const latest = useRef(load);
  latest.current = load;
  const before = useRef<unknown>(null);
  const answer = load.status === "ready" ? briefFrom(load.data) : null;
  const brief = answer?.status === "ready" ? answer : null;
  // The demo's setting (ticket 152): the server writes briefs only from sources read ahead of time.
  const storedOnly = load.status === "ready" && (load.data as { live_sources?: unknown } | null)?.live_sources === false;

  useEffect(() => {
    if (run.phase !== "reading") return;
    if ((load.status === "ready" && load.data !== before.current) || load.status === "error") setRun(IDLE);
  }, [run.phase, load]);

  // Each item the brief cites is known to the evidence drawer at once, so a marker opens it with no request.
  useEffect(() => {
    if (brief) for (const event of Object.values(brief.evidence)) remember(event);
  }, [brief]);
  useEffect(() => () => stopping.current?.abort(), []);

  const start = async () => {
    stopping.current?.abort();
    const controller = new AbortController();
    stopping.current = controller;
    const started = Date.now();
    setRun({ ...IDLE, phase: "running", started, lastEventAt: started });
    try {
      // The run reads as of the page's date in the page's view, as the brief's GET does (ticket 148 takes them in the body).
      const body = { view: viewOf(search), asof: asOfOf(search) };
      for await (const event of streamEvents(`/api/projects/${encodeURIComponent(pid)}/research`, body, { signal: controller.signal })) {
        const at = Date.now();
        if (event.type === "step") setRun((now) => ({ ...now, lastEventAt: at, steps: withStep(now.steps, event.data as ResearchStep) }));
        if (event.type === "plan") setRun((now) => ({ ...now, lastEventAt: at, plan: planFrom(event.data) }));
        if (event.type === "sentence" || event.type === "removed") setRun((now) => ({ ...now, lastEventAt: at, checked: now.checked + 1 }));
        if (event.type === "evidence") remember(event.data as EvidenceEvent);
        if (event.type === "error") {
          const code = (event.data as { code?: string }).code ?? null;
          setRun((now) => ({ ...now, phase: "failed", code }));
          return;
        }
        if (event.type === "done") {
          // The run stored its brief; reading it again shows it, as the next visit will.
          before.current = latest.current.status === "ready" ? latest.current.data : null;
          setRun((now) => ({ ...now, phase: "reading" }));
          setReads((count) => count + 1);
          return;
        }
      }
      if (!controller.signal.aborted) setRun((now) => ({ ...now, phase: "dropped" }));
    } catch (error) {
      if (controller.signal.aborted) return;
      setRun((now) => ({ ...now, phase: "failed", status: error instanceof StreamError ? error.status : null }));
    }
  };

  const running = run.phase === "running" || run.phase === "reading";
  const state = running ? "running" : load.status === "error" ? "error" : load.status === "loading" ? "loading" : brief ? "ready" : "none";
  const name = project?.name ?? brief?.project?.project_name ?? pid;

  return (
    <div data-research={state} className="@container/research">
      <h2 className="sr-only">{words.heading}</h2>
      <EightColumns>
        {load.status === "error" && !running ? (
          <LoadError error={load.error} message={words.error} permission={words.permission} onRetry={retry} retrying={load.retrying} attempt={load.attempt} />
        ) : running ? (
          <div data-research-run className="max-w-prose">
            <ResearchProgress name={name} plan={run.plan} steps={run.steps} checked={run.checked} started={run.started} lastEventAt={run.lastEventAt} />
          </div>
        ) : load.status === "loading" ? (
          <div aria-busy="true">
            <p role="status" className="sr-only">
              {words.loading}
            </p>
            <SkeletonLine width="w-2/5" className="text-h2" />
            <SkeletonText className="mt-2 max-w-prose text-lead" widths={["w-full", "w-full", "w-3/5"]} />
            <SkeletonText className="mt-3 max-w-prose text-body" widths={["w-full", "w-full", "w-full", "w-4/5"]} />
          </div>
        ) : (
          <>
            {(run.phase === "failed" || run.phase === "dropped") && (
              <div className="mb-6 max-w-prose">
                {run.status === 403 ? (
                  <Alert state="error" live="alert">
                    {words.permission}
                  </Alert>
                ) : (
                  <Alert
                    state="error"
                    live="alert"
                    action={
                      <Button variant="secondary" onClick={() => void start()}>
                        {copy.answer.tryAgain}
                      </Button>
                    }
                  >
                    {run.phase === "dropped" ? words.dropped : (run.code && words.errors[run.code]) || words.runError}
                  </Alert>
                )}
                {run.steps.length > 0 && (
                  <div className="mt-4">
                    <Steps steps={stepLines(run.steps)} announce={false} />
                  </div>
                )}
              </div>
            )}
            {brief ? (
              <>
                <div className="flex flex-wrap items-center gap-3" data-research-actions>
                  <Button variant="primary" onClick={() => window.print()}>
                    {words.print}
                  </Button>
                  <Button variant="secondary" onClick={() => void start()}>
                    {words.again}
                  </Button>
                </div>
                {brief.read_on && <p className="mt-2 max-w-prose text-caption text-ink-muted">{(storedOnly ? words.readOnStored : words.readOn)(formatDate(brief.read_on))}</p>}
                <div className="mt-8">
                  <BriefView brief={brief} />
                </div>
                {brief.removed.length > 0 && (
                  <div className="mt-10 max-w-prose">
                    <RemovedBox removed={removedFrom(brief.removed)} />
                  </div>
                )}
                <ResearchPrint brief={brief} pid={pid} name={name} country={project?.country ?? brief.project?.country_name ?? null} agencies={brief.project?.implementing_agencies ?? project?.agencies ?? []} />
              </>
            ) : (
              <div data-research-none className="max-w-prose">
                <p className="text-body text-ink">{storedOnly ? words.notPrepared : words.none}</p>
                <div className="mt-4">
                  <Button variant="primary" onClick={() => void start()}>
                    {words.run}
                  </Button>
                </div>
              </div>
            )}
            <FieldPhotos pid={pid} />
          </>
        )}
      </EightColumns>
    </div>
  );
}
