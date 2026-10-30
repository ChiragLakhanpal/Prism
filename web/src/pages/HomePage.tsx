// Home (ticket 41; the 41 design brief; ticket 98 moves it onto the workspace layout), at /: Home answers before anyone
// types. One request, GET /api/home, gives the whole page, built on the server from fixed checks and no model:
//
// - The h1 is the briefing: a date line, then sentences whose count words open what they count. Each count equals the
//   lines of its kind below, folded lines included. When an answer opens on Home, it folds to its first sentence.
// - The Start here strip, a Task zone row for World Bank staff in their own view today: one example per stage, which
//   "Remove" hides for this viewer on every later visit (kept on the server), with an undo row for the visit. Ticket
//   114 makes it a to-do list: a tick on each example followed and a count, kept in this browser (lib/startHere.ts),
//   and the sidebar shows the next one on every page.
// - "Worth knowing", a panel tagged "Fixed checks, no model": one past-tense line per activity, project or lesson,
//   each with its status, its source and one action. More than eight fold behind "Show them".
// - "Waiting for you", the side panel: the viewer's own drafts to check, with their progress, eight at most, then a
//   link to Drafts.
//
// An implementing agency officer, the agency preview and the public preview get their own content from the server
// (the roles table); a past date leaves out the lesson lines, the drafts and the strip. The page counts nothing.
import { Fragment, useEffect, useId, useRef, useState, type ReactNode } from "react";
import { ChevronDown, ChevronUp, Circle, CircleCheck, CircleX } from "lucide-react";
import { useAnswerInPage } from "../components/AnswerSlot";
import { Button } from "../components/Button";
import { CitationMarker } from "../components/CitationMarker";
import { Fill } from "../components/Fill";
import { FootStrip } from "../components/FootStrip";
import { Tag } from "../components/LessonParts";
import { LoadError } from "../components/LoadError";
import { MadeBy } from "../components/MadeBy";
import { MeasureNum } from "../components/MeasureNum";
import { Num, type NumCheck } from "../components/Num";
import { FromLine, homeFrom, planFrom } from "../components/NumFrom";
import { PageAlert } from "../components/PageAlert";
import { ProjectId } from "../components/ProjectId";
import { SidePanel } from "../components/SidePanel";
import { Skeleton, SkeletonLine } from "../components/Skeleton";
import { Source } from "../components/Source";
import { StatusBadge, type BadgeKind } from "../components/StatusBadge";
import { TaskZone, ZoneBlock } from "../components/TaskZone";
import { TextLink } from "../components/TextLink";
import { Workspace } from "../components/Workspace";
import { copy } from "../copy";
import { postJson } from "../lib/api";
import { draftHref } from "../lib/drafts";
import { evidenceHref, openEvidence } from "../lib/evidence";
import { cx } from "../lib/cx";
import { formatDate, formatDayLine, formatNumber } from "../lib/format";
import { HOME_PATH, START_HERE_PATH, startHereVisible, type HomeAnswer, type HomeLine, type HomeSegment } from "../lib/home";
import { draftTitle } from "../lib/lessonsPage";
import { keepLinks, markDone, START_HERE_ANCHOR, startHereList } from "../lib/startHere";
import { useLoad, type Load } from "../lib/load";
import { useStore } from "../lib/store";
import { CHECK_MY_PLAN } from "../lib/uploads";
import { DraftRow } from "./DraftsPage";

const words = copy.home;
const BADGES: Record<string, BadgeKind> = {
  needs_a_look: "needs-a-look",
  watch: "watch",
  changed: "changed",
  retired_wrong: "retired-wrong",
  retired_outdated: "retired-outdated",
};
const short = (iso: string) => formatDate(iso, { style: "short" });

// ── The server's sentences ───────────────────────────────────────────────

type Valued = Extract<HomeSegment, { written: string }> | Extract<HomeSegment, { number: number }>;

function Segments({
  segments,
  popover,
  check,
}: {
  segments: HomeSegment[];
  popover?: (segment: Extract<HomeSegment, { count: number }>) => ReactNode;
  // A line's amount or number that names the value it is explains itself and opens its record (ticket 96).
  check?: (segment: Valued) => NumCheck | undefined;
}) {
  return (
    <>
      {segments.map((segment, index) => (
        <Fragment key={index}>
          {"text" in segment ? (
            segment.text
          ) : "count" in segment ? (
            segment.kind && popover ? (
              popover(segment)
            ) : (
              <span data-num className="tabular-nums">
                {segment.word}
              </span>
            )
          ) : "date" in segment ? (
            segment.date ? <Num date={segment.date} style={segment.style === "short" ? "short" : "sentence"} /> : null
          ) : "year" in segment ? (
            <Num year={segment.year} />
          ) : "ref" in segment ? (
            <span className="font-mono font-medium [overflow-wrap:anywhere]">{segment.ref}</span>
          ) : "pid" in segment ? (
            <ProjectId pid={segment.pid} />
          ) : "written" in segment ? (
            <Num written={segment.written} check={check?.(segment)} />
          ) : (
            <Num value={segment.number} options={{ compact: false }} check={check?.(segment)} />
          )}
        </Fragment>
      ))}
    </>
  );
}

// A count word's window: what the count counts, each a link to its line or its page (the 39 brief's pattern).
function countWindow(answer: HomeAnswer) {
  const p = words.popovers;
  const lines = new Map(answer.worth.lines.map((line) => [line.id, line]));
  const drafts = new Map(answer.waiting.rows.map((row) => [row.draft_id, row]));
  return (segment: Extract<HomeSegment, { count: number }>): ReactNode => {
    const kind = segment.kind ?? "";
    const ids = segment.ids ?? [];
    let title: ReactNode = "";
    let items: ReactNode = null;
    if (kind === "plans") {
      const window = answer.window;
      title = window ? p.plans(short(window.start), short(window.end)) : "";
      items = (
        <>
          <ul className="flex flex-col gap-2">
            {answer.briefing.plans.map((plan) => (
              <li key={plan.document_id}>
                <Fill
                  template={p.planItem}
                  slots={{
                    agency: plan.implementing_agency ?? "",
                    date: (
                      <TextLink href={`/projects/${plan.project_id}/procurement/${plan.agency_id}/${plan.plan_date}`}>
                        {formatDate(plan.plan_date)}
                      </TextLink>
                    ),
                    project: plan.project_name ?? "",
                    pid: <ProjectId pid={plan.project_id} />,
                    disclosed: plan.disclosed_on ? short(plan.disclosed_on) : "",
                  }}
                />
              </li>
            ))}
          </ul>
          {window?.data_through && (
            <p className="mt-2 text-caption text-ink-muted">
              <Fill template={p.plansNote} slots={{ window: <Segments segments={window.phrase} />, through: formatDate(window.data_through) }} />
            </p>
          )}
        </>
      );
    } else if (kind === "drafts") {
      title = p.drafts;
      items = (
        <ul className="flex flex-col gap-2">
          {ids.map((id) => {
            const row = drafts.get(id);
            return (
              <li key={id}>
                <TextLink href={draftHref(id)}>{row ? draftTitle(row.kind, row.subject as unknown as Record<string, string | null>) : id}</TextLink>
              </li>
            );
          })}
        </ul>
      );
    } else {
      title = (p as Record<string, unknown>)[kind] as string;
      items = (
        <ul className="flex flex-col gap-2">
          {ids.map((id) => {
            const line = lines.get(id);
            return (
              <li key={id}>
                <TextLink href={`#${id}`} className={line?.kind === "activity" ? "font-mono" : undefined}>
                  {line ? (line.kind === "lesson" ? line.action.hidden : line.key) : id}
                </TextLink>
              </li>
            );
          })}
        </ul>
      );
    }
    // Its tooltip says what it counts, that it comes from my checks on the day they ran, and that a click lists them
    // (DESIGN.md, Number tooltip, Window variant).
    return (
      <span data-count-kind={kind} data-count={segment.count}>
        <MeasureNum
          value={{ written: segment.word }}
          tooltip={words.tips.counts[kind] ?? title}
          from={<FromLine words={homeFrom(answer.worth.checked_on)} />}
          act={segment.count === 1 ? copy.num.act.listOne : copy.num.act.list}
          measure={{ title, definition: items }}
          inText
        />
      </span>
    );
  };
}

// A line's amount or number: what it is, the plan it comes from, and a click that opens the plan row (ticket 96). An
// amount in millions gives the plan row's own value. The days to closing were counted by my checks from the project's
// closing date, which the plan row does not hold, so they open nothing, as on the plan check.
function lineCheck(line: HomeLine, checkedOn: string) {
  const source = line.source;
  if (source.kind !== "plan" || !source.agency || !source.date) return () => undefined;
  const plan = <FromLine words={planFrom(source.agency, source.date)} />;
  const open = (element: HTMLElement) => openEvidence(source.evidence_id, { serial: null, sentence: null, marker: element, runId: null });
  return (segment: Valued): NumCheck | undefined => {
    if (!segment.what) return undefined;
    const t = words.tips;
    const what =
      segment.what === "millions" && "exact" in segment && segment.exact ? t.millions(segment.exact) : segment.what === "millions" ? t.estimated : t[segment.what];
    if (segment.what === "daysToClose") return { tooltip: what, from: <FromLine words={homeFrom(checkedOn)} /> };
    return { tooltip: what, from: plan, act: copy.num.act.planRow, opens: "record", onOpen: open };
  };
}

// ── The briefing heading ─────────────────────────────────────────────────

// Today in the browser's own time zone, as an ISO date, for the date line while Home's answer loads.
function browserToday(): string {
  const now = new Date();
  const pad = (value: number) => String(value).padStart(2, "0");
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

// How the briefing shows beside an answer asked from Home (ticket 98): not at all (no answer), folded to its first
// sentence, or unfolded with "Show the briefing".
type Fold = "none" | "folded" | "unfolded";

// Home's h1 (DESIGN.md section 5, Briefing heading; ticket 98): the date line in label, then the briefing's sentences in
// the finding style, or in lead when they report a state; beside an answer, in body, folded to the first sentence
// until "Show the briefing" unfolds the rest in place. It names the page instead ("Home") in the public view and when
// Home's one read failed. It is the same element in every state, so focus stays on it as the answer arrives or fails.
function Briefing({ answer, named, fold, sentencesId }: { answer: HomeAnswer | null; named: boolean; fold: Fold; sentencesId: string }) {
  if (named) {
    return (
      <h1 id="briefing" tabIndex={-1} className="text-h1 text-ink-heading focus:outline-none" data-briefing="named">
        {words.title}
      </h1>
    );
  }
  // The date line shows only as of a past date, which changes what the page shows (DESIGN.md section 7, rule 45). An
  // eyebrow that told you today's date went in ticket 126; a screen reader still hears the briefing named first.
  const line = answer?.as_of ? words.dateLineAsOf(formatDayLine(answer.as_of, { withYear: true })) : null;
  const popover = answer ? countWindow(answer) : undefined;
  const shown = answer ? (fold === "folded" ? answer.briefing.sentences.slice(0, 1) : answer.briefing.sentences) : [];
  const sentences = shown.map((sentence, index) => (
    <Fragment key={index}>
      {index > 0 && " "}
      <Segments segments={sentence} popover={popover} />
    </Fragment>
  ));
  return (
    <h1 id="briefing" tabIndex={-1} className="focus:outline-none" data-briefing={answer ? "ready" : "loading"}>
      {/* One hidden span with its full stop, so a screen reader hears "Your briefing. One plan ..." with no gap. */}
      {line ? (
        <>
          <span data-date-line className="mb-2 block text-label text-ink-muted">
            {line}
          </span>
          <span className="sr-only">{words.dateLineEnd}</span>
        </>
      ) : (
        <span className="sr-only">
          {copy.pages.home.title}
          {words.dateLineEnd}
        </span>
      )}
      {answer &&
        (fold !== "none" ? (
          // Beside an answer the answer leads, so the briefing steps down to body (fairshare's strip, plan 9, pattern 6).
          <span id={sentencesId} className="block max-w-prose text-body text-pretty text-ink" data-sentences data-fold={fold}>
            {sentences}
          </span>
        ) : reportsAState(answer) ? (
          // A first run or a quiet window reports a state, not a finding, so it takes lead (DESIGN.md section 1,
          // principle 6).
          <span id={sentencesId} className="block max-w-prose text-lead text-pretty text-ink" data-sentences data-status-lead>
            {sentences}
          </span>
        ) : (
          // The page's finding: a count word's tooltip opens under all of it (DESIGN.md, Number tooltip).
          <span id={sentencesId} className="block max-w-[22.5em] text-finding text-pretty text-ink-heading" data-sentences data-finding>
            {sentences}
          </span>
        ))}
    </h1>
  );
}

// Whether the briefing reports a state rather than a finding: a first run, a quiet window (which includes a past date
// before any followed project was public), or an officer whose team has no published plan yet.
function reportsAState(answer: HomeAnswer): boolean {
  const empty = answer.worth.empty;
  return empty === "first_run" || empty === "quiet" || empty === "no_plan";
}

// ── The Start here strip ─────────────────────────────────────────────────

type StripState = "shown" | "removing" | "removed" | "restoring" | "remove-failed" | "restore-failed";

function StartHere({ links }: { links: HomeAnswer["start_here"]["links"] }) {
  const [state, setState] = useState<StripState>("shown");
  const sentence = useRef<HTMLParagraphElement>(null);
  const title = useRef<HTMLHeadingElement>(null);
  const start = words.start;
  // The examples the person followed from here or from the sidebar (ticket 114), kept in this browser.
  const kept = useStore(startHereList);
  const followed = new Set(kept?.done ?? []);
  const doneCount = links.filter((link) => followed.has(link.key)).length;

  // "All six done" in the sidebar leads here (/#start-here): once Home has drawn the strip, its title takes focus.
  useEffect(() => {
    if (window.location.hash !== `#${START_HERE_ANCHOR}`) return;
    title.current?.scrollIntoView();
    title.current?.focus({ preventScroll: true });
  }, []);

  // Once the change is drawn, focus goes to what says what happened: the undo row's sentence after Remove, and the
  // strip's title after showing the examples again (the 41 brief, 6.2).
  const moved = useRef(false);
  useEffect(() => {
    if (!moved.current) return;
    if (state === "removed") sentence.current?.focus();
    if (state === "shown") title.current?.focus();
  }, [state]);

  const choose = async (visible: boolean) => {
    setState(visible ? "restoring" : "removing");
    try {
      await postJson(START_HERE_PATH, { visible, view: "staff" });
      moved.current = true;
      setState(visible ? "shown" : "removed");
      startHereVisible.set(visible);
    } catch {
      setState(visible ? "restore-failed" : "remove-failed");
    }
  };

  if (state === "removed" || state === "restoring" || state === "restore-failed") {
    // The undo row, on the page grey where the strip's row was.
    return (
      <section data-start-here="removed" className="border-y border-line py-4">
        <div className="flex flex-wrap items-center gap-3">
          <p ref={sentence} tabIndex={-1} className="text-small text-ink focus:outline-none">
            {start.removed}
          </p>
          <Button variant="ghost" loading={state === "restoring"} busyLabel={start.showing} onClick={() => void choose(true)}>
            {start.showAgain}
          </Button>
        </div>
        {state === "restore-failed" && <FailedLine>{start.restoreFailed}</FailedLine>}
      </section>
    );
  }
  // A Task zone row under the briefing (ticket 98): "Start here" and its count, the tag under the name at every width,
  // Remove at the row's right, then the six links in the ticket's order.
  const count = copy.nav.startHere.count(formatNumber(doneCount, { compact: false }), formatNumber(links.length, { compact: false }));
  return (
    <TaskZone
      name={start.title}
      headingId={START_HERE_ANCHOR}
      headingRef={title}
      note={<span data-start-count>{count}</span>}
      corner={
        <Button variant="ghost" flush onPage aria-label={start.removeName} loading={state === "removing"} busyLabel={start.removing} onClick={() => void choose(false)}>
          {start.remove}
        </Button>
      }
      summary={
        <>
          <ul className="flex flex-col gap-1 @md/page:flex-row @md/page:flex-wrap @md/page:gap-x-8 @md/page:gap-y-2">
            {links.map((link) => {
              // Each link leads with its tick, which appears at once and never moves; its name ends with "done" only
              // once the person followed it.
              const done = followed.has(link.key);
              const Tick = done ? CircleCheck : Circle;
              return (
                <li key={link.key} className="flex min-h-8 items-center">
                  <TextLink href={link.href} data-start-link={link.key} onClick={() => markDone(link.key)} className="inline-flex items-start gap-2 text-small font-semibold">
                    <Tick aria-hidden="true" data-start-tick={done ? "done" : "open"} className={cx("mt-0.5 size-4 shrink-0", done ? "text-primary" : "text-line-strong")} />
                    <span>
                      <Fill template={start.links[link.key] ?? link.key} slots={{ pid: <span className="font-mono font-medium">{link.pid}</span> }} />
                      {done && <span className="clip-visually">{copy.nav.startHere.doneHidden}</span>}
                    </span>
                  </TextLink>
                </li>
              );
            })}
          </ul>
          {state === "remove-failed" && <FailedLine>{start.removeFailed}</FailedLine>}
        </>
      }
      sectionKey="start-here"
      marks={{ "data-start-here": "shown" }}
    />
  );
}

function FailedLine({ children }: { children: ReactNode }) {
  return (
    <p role="alert" className="mt-2 flex items-center gap-2 text-small text-error">
      <CircleX aria-hidden="true" className="size-4 shrink-0 text-error-icon" />
      {children}
    </p>
  );
}

// Later visits, once the viewer removed the strip: one line at the end of Home that brings it back.
function RestoreLine({ onRestored }: { onRestored: () => void }) {
  const [state, setState] = useState<"idle" | "busy" | "failed">("idle");
  const start = words.start;
  return (
    <div data-restore-line className="mt-8 flex flex-wrap items-center gap-3">
      <p className="text-caption text-ink-muted">{start.removed}</p>
      <Button
        variant="ghost"
        loading={state === "busy"}
        busyLabel={start.showing}
        onClick={async () => {
          setState("busy");
          try {
            await postJson(START_HERE_PATH, { visible: true, view: "staff" });
            startHereVisible.set(true);
            onRestored();
          } catch {
            setState("failed");
          }
        }}
      >
        {start.showAgain}
      </Button>
      {state === "failed" && <FailedLine>{start.restoreFailed}</FailedLine>}
    </div>
  );
}

// ── Worth knowing ────────────────────────────────────────────────────────

function sourceName(line: HomeLine): string {
  const sources = words.worth.sources;
  const source = line.source;
  switch (source.kind) {
    case "plan":
      return sources.plan(short(source.date ?? ""));
    case "lesson":
      return sources.lesson(String(source.version ?? ""));
    case "retired":
      return sources.retired;
    case "loanHistory":
      return sources.loanHistory;
    case "isr":
      return sources.isr(short(source.date ?? ""));
    case "disbursement":
      return sources.disbursement(short(source.date ?? ""));
    default:
      return sources.record;
  }
}

function Line({ line, n, hidden, checkedOn }: { line: HomeLine; n: number; hidden: boolean; checkedOn: string }) {
  const action = (words.worth.actions as Record<string, string>)[line.action.key] ?? words.publicView.action;
  const badge = BADGES[line.status];
  return (
    <li
      id={line.id}
      tabIndex={-1}
      hidden={hidden}
      data-line-kind={line.kind}
      data-line-status={line.status}
      className="border-t border-line py-4 first:border-t-0 first:pt-1 focus:outline-none @container/line"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="flex flex-wrap items-center gap-2">
          {badge && <StatusBadge kind={badge} />}
          {line.example && <Tag>{words.example}</Tag>}
        </span>
        <TextLink href={line.action.href} data-line-action={line.action.key} className="text-small">
          {action}
          <span className="sr-only"> {line.action.hidden}</span>
        </TextLink>
      </div>
      <p className="mt-2 max-w-[72ch] text-body text-pretty text-ink">
        <Segments segments={line.segments} check={lineCheck(line, checkedOn)} />{" "}
        <CitationMarker
          n={n}
          source={sourceName(line)}
          href={evidenceHref(line.source.evidence_id)}
          evidenceId={line.source.evidence_id}
          onOpen={(marker) => openEvidence(line.source.evidence_id, { serial: null, sentence: null, marker, runId: null })}
        />
      </p>
    </li>
  );
}

// A panel in columns 1 to 7 named "Worth knowing", its tag "Fixed checks, no model" at the panel's right (ticket 98):
// each line a badge, its one verb at the first row's right, its sentence and its marker, then the foot strip's source.
// The public view's is "Closed projects", tagged "Contracts traced from public records". With no lines it is a row
// with its sentence and at most one link.
function WorthKnowing({ answer }: { answer: HomeAnswer }) {
  const worth = answer.worth;
  const [open, setOpen] = useState(false);
  const folded = Math.max(0, worth.lines.length - worth.fold_after);
  const isPublic = worth.kind === "public";
  const name = isPublic ? words.publicView.title : words.worth.title;
  // How I wrote the lines is in the made-by window at the zone's head (ticket 126), not a tag fragment such as "Fixed
  // checks, no model". The dates stay on first sight in the source line.
  const tag = isPublic ? (
    <MadeBy name={words.publicView.madeByName}>{words.publicView.madeBy}</MadeBy>
  ) : (
    <MadeBy name={words.worth.madeByName}>{words.worth.madeBy}</MadeBy>
  );
  const through = formatDate(worth.through, { style: "short" });
  const checked = formatDate(worth.checked_on, { style: "short" });
  const source = isPublic ? words.publicView.source(through) : worth.kind === "agency" ? words.worth.sourceAgency(through, checked) : words.worth.source(through, checked);
  const marks = { "data-worth": worth.kind };
  if (worth.lines.length === 0) {
    return <TaskZone name={name} tag={tag} summary={<WorthEmpty answer={answer} source={source} />} sectionKey="worth" marks={marks} />;
  }
  return (
    <TaskZone name={name} tag={tag} panel sectionKey="worth" marks={marks}>
      <ZoneBlock
        foot={
          <FootStrip>
            <Source>{source}</Source>
            {isPublic && (
              <p className="text-small">
                <TextLink href="/projects">{words.publicView.more}</TextLink>
              </p>
            )}
          </FootStrip>
        }
      >
        <ul>
          {worth.lines.map((line, index) => (
            <Line key={line.id} line={line} n={index + 1} hidden={!open && index >= worth.fold_after} checkedOn={worth.checked_on} />
          ))}
        </ul>
        {folded > 0 && (
          <div className="border-t border-line pt-3">
            <p className="text-small text-ink">{folded === 1 ? words.worth.foldOne : words.worth.fold(String(folded))}</p>
            <Button variant="ghost" flush icon={ChevronDown} aria-expanded={open} onClick={() => setOpen(!open)}>
              {open ? (folded === 1 ? words.worth.hideOne : words.worth.hide) : folded === 1 ? words.worth.showOne : words.worth.show}
            </Button>
          </div>
        )}
      </ZoneBlock>
    </TaskZone>
  );
}

// The row's sentence when Worth knowing has no lines, its one link, and the source of what it says. A first run says
// what Home will hold, so it has no source.
function WorthEmpty({ answer, source }: { answer: HomeAnswer; source: string }) {
  const worth = answer.worth;
  const w = words.worth;
  if (worth.empty === "first_run") {
    return (
      <>
        <p className="text-pretty">{w.firstRunBody}</p>
        <p className="mt-2">
          <TextLink href="/projects">{w.firstRunLink}</TextLink>
        </p>
      </>
    );
  }
  const sentence =
    worth.empty === "no_closed" ? (
      words.publicView.empty
    ) : worth.empty === "nothing_behind" || worth.empty === "no_plan" ? (
      w.agencyNothing
    ) : worth.empty === "nothing_marked" ? (
      w.nothingMarked
    ) : (
      // The window's words are the server's (the page picks no count word).
      <Fill template={w.quiet} slots={{ window: answer.window ? <Segments segments={answer.window.phrase} /> : "" }} />
    );
  return (
    <>
      <p className="text-pretty">{sentence}</p>
      {worth.empty === "quiet" && (
        <p className="mt-2">
          <TextLink href="/projects/following">{w.quietLink}</TextLink>
        </p>
      )}
      <Source className="mt-2">{source}</Source>
    </>
  );
}

// ── Waiting for you ──────────────────────────────────────────────────────

// The side panel in columns 9 to 12 from a frame of 75rem, after Worth knowing below it (ticket 98). With no drafts to
// list it holds only a sentence, so it is a row in the side column.
function WaitingForYou({ answer }: { answer: HomeAnswer }) {
  const waiting = answer.waiting;
  const w = words.waiting;
  const reason = waiting.reason === "preview" ? w.preview : waiting.reason === "asof" ? w.asOf : null;
  return (
    <div data-waiting>
      {reason ? (
        <SidePanel title={w.title} sentence={reason} />
      ) : waiting.rows.length === 0 ? (
        <SidePanel
          title={w.title}
          sentence={
            <span data-waiting-empty>
              {answer.view === "piu" ? w.emptyAgency : w.empty} <TextLink href="/packages">{w.emptyLink}</TextLink>
            </span>
          }
        />
      ) : (
        <SidePanel title={w.title}>
          <ul className="-mx-4">
            {waiting.rows.map((row) => (
              <DraftRow key={row.draft_id} row={row} />
            ))}
          </ul>
          <p className="mt-2 text-small">
            <TextLink href="/drafts">{waiting.more ? w.more(String(waiting.total)) : w.toDrafts}</TextLink>
          </p>
        </SidePanel>
      )}
    </div>
  );
}

// ── The page ─────────────────────────────────────────────────────────────

// While Home loads: the briefing's lines under the date line, and each zone's place.
function LoadingLines() {
  return (
    <>
      <span role="status" className="sr-only">
        {words.loading}
      </span>
      <div className="mt-2 flex max-w-[22.5em] flex-col gap-2 text-finding" aria-hidden="true">
        <SkeletonLine width="w-full" />
        <SkeletonLine width="w-full" />
        <SkeletonLine width="w-3/5" />
      </div>
    </>
  );
}

function LoadingZones() {
  const strip = useStore(startHereVisible);
  return (
    <div aria-hidden="true">
      {strip && <Skeleton className="mb-4 h-28 w-full" />}
      <Skeleton className="h-64 w-full" />
    </div>
  );
}

// Home's head: the h1, which is always the same element, so focus stays on it when the answer arrives or fails; under
// it the public view's one sentence in lead, or the briefing's lines while they load.
function HomeHead({
  load,
  answer,
  retry,
  answered,
}: {
  load: Load<HomeAnswer>;
  answer: HomeAnswer | null;
  retry: () => void;
  // An answer asked from Home is open above the head.
  answered: boolean;
}) {
  const isPublic = answer?.view === "public";
  const named = load.status === "error" || isPublic;
  const sentencesId = useId();
  const [unfolded, setUnfolded] = useState(false);
  // Closing the answer unfolds the briefing, and the next answer folds it again.
  useEffect(() => {
    if (!answered) setUnfolded(false);
  }, [answered]);
  const folds = answered && !named && (answer?.briefing.sentences.length ?? 0) > 1;
  const fold: Fold = !answered || named ? "none" : unfolded || !folds ? "unfolded" : "folded";
  return (
    <div data-page-head>
      {load.status === "error" && (
        // The page's one read failed: its error alert sits in the page's alert slot, and the h1 names the page.
        <PageAlert>
          <LoadError error={load.error} message={words.error} permission={words.permission} onRetry={retry} retrying={load.retrying} attempt={load.attempt} />
        </PageAlert>
      )}
      <Briefing answer={answer} named={named} fold={fold} sentencesId={sentencesId} />
      {folds && (
        <p className="mt-2">
          <Button
            variant="ghost"
            flush
            onPage
            icon={unfolded ? ChevronUp : ChevronDown}
            aria-expanded={unfolded}
            aria-controls={sentencesId}
            onClick={() => setUnfolded(!unfolded)}
            data-briefing-toggle
          >
            {unfolded ? words.briefingHide : words.briefingShow}
          </Button>
        </p>
      )}
      {isPublic && (
        <p className="mt-2 max-w-prose text-lead text-pretty text-ink" data-status-lead>
          {answer.briefing.sentences.map((sentence, index) => (
            <Fragment key={index}>
              {index > 0 && " "}
              <Segments segments={sentence} />
            </Fragment>
          ))}
        </p>
      )}
      {load.status === "loading" && <LoadingLines />}
    </div>
  );
}

export function HomePage() {
  // Showing the examples again from the end of Home reads Home once more, with the strip.
  const [reading, setReading] = useState(0);
  const [load, retry] = useLoad<HomeAnswer>(HOME_PATH, String(reading));
  const answer = load.status === "ready" ? load.data : null;
  // An answer asked from Home: in the work's columns above the head (ticket 98).
  const asked = useAnswerInPage();
  useEffect(() => {
    if (load.status === "ready" && (load.afterRetry || reading > 0)) document.getElementById("briefing")?.focus();
  }, [load, reading]);
  // Start here goes with the person (ticket 114): World Bank staff's own Home today keeps its links in this browser,
  // so the sidebar on every other page shows the next one with no request of its own.
  useEffect(() => {
    if (answer && answer.view === "staff" && !answer.preview && !answer.as_of && answer.start_here.links.length > 0) keepLinks(answer.start_here.links);
  }, [answer]);
  const strip = Boolean(answer?.start_here.visible && answer.start_here.links.length > 0);
  // A later visit after Remove: World Bank staff today, with the strip's links but not the strip.
  const restore = Boolean(answer && !strip && answer.view === "staff" && !answer.as_of && answer.start_here.links.length > 0);
  // Waiting for you is the side panel; the public view has none, and a failed read draws only the head.
  const side =
    load.status === "loading" ? (
      <Skeleton className="h-48 w-full" />
    ) : answer && answer.view !== "public" ? (
      <WaitingForYou answer={answer} />
    ) : undefined;
  return (
    <div data-home={load.status}>
      <Workspace answer={asked} head={<HomeHead load={load} answer={answer} retry={retry} answered={asked != null} />} side={side}>
        {load.status === "loading" && <LoadingZones />}
        {answer && (
          <>
            {strip && <StartHere links={answer.start_here.links} />}
            {/* An implementing agency officer's own Home: "Check my plan" takes the strip's place (the 41 brief, 5.8). */}
            {answer.view === "piu" && !answer.preview && !answer.as_of && (
              <p className="mb-4 text-body" data-check-my-plan>
                <TextLink href={CHECK_MY_PLAN}>{words.worth.agencyCheck}</TextLink>
              </p>
            )}
            <WorthKnowing answer={answer} />
            {restore && <RestoreLine onRestored={() => setReading((count) => count + 1)} />}
          </>
        )}
      </Workspace>
    </div>
  );
}
