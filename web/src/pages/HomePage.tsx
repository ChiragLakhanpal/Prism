// Home (ticket 41; the 41 design brief), at /: Home answers before anyone types. One request, GET /api/home, gives the
// whole page, built on the server from fixed checks and no model:
//
// - The h1 is the briefing: a date line, then sentences whose count words open what they count. Each count equals the
//   lines of its kind below, folded lines included.
// - The Start here strip, for World Bank staff in their own view today: one example per stage, which "Remove" hides
//   for this viewer on every later visit (kept on the server), with an undo row for the visit.
// - "Worth knowing · fixed checks, no model": one past-tense line per activity, project or lesson, each with its
//   status, its source and one action. More than eight fold behind "Show them".
// - "Waiting for you": the viewer's own drafts to check, with their progress, eight at most, then a link to Drafts.
//
// An implementing agency officer, the agency preview and the public preview get their own content from the server
// (the roles table); a past date leaves out the lesson lines, the drafts and the strip. The page counts nothing.
import { Fragment, useEffect, useId, useRef, useState, type ReactNode } from "react";
import { ChevronDown, Circle, CircleCheck, CircleX } from "lucide-react";
import { Button } from "../components/Button";
import { CitationMarker } from "../components/CitationMarker";
import { EmptyState } from "../components/Card";
import { Fill } from "../components/Fill";
import { Tag } from "../components/LessonParts";
import { LoadError } from "../components/LoadError";
import { Num } from "../components/Num";
import { ProjectId } from "../components/ProjectId";
import { Skeleton, SkeletonLine } from "../components/Skeleton";
import { Source } from "../components/Source";
import { StatusBadge, type BadgeKind } from "../components/StatusBadge";
import { DefinitionWindow } from "../components/Term";
import { TextLink } from "../components/TextLink";
import { copy } from "../copy";
import { postJson } from "../lib/api";
import { draftHref } from "../lib/drafts";
import { evidenceHref, openEvidence } from "../lib/evidence";
import { cx } from "../lib/cx";
import { formatDate, formatDayLine, formatNumber } from "../lib/format";
import { HOME_PATH, START_HERE_PATH, startHereVisible, type HomeAnswer, type HomeLine, type HomeSegment } from "../lib/home";
import { draftTitle } from "../lib/lessonsPage";
import { keepLinks, markDone, START_HERE_ANCHOR, startHereList } from "../lib/startHere";
import { useLoad } from "../lib/load";
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

function Segments({ segments, popover }: { segments: HomeSegment[]; popover?: (segment: Extract<HomeSegment, { count: number }>) => ReactNode }) {
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
            <Num written={segment.written} />
          ) : (
            <Num value={segment.number} options={{ compact: false }} />
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
    return (
      <span data-count-kind={kind} data-count={segment.count}>
        <DefinitionWindow label={segment.word} title={title}>
          {items}
        </DefinitionWindow>
      </span>
    );
  };
}

// ── The briefing heading ─────────────────────────────────────────────────

// Today in the browser's own time zone, as an ISO date, for the date line while Home's answer loads.
function browserToday(): string {
  const now = new Date();
  const pad = (value: number) => String(value).padStart(2, "0");
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

function Briefing({ answer }: { answer: HomeAnswer | null }) {
  const day = answer ? answer.as_of ?? answer.today : null;
  // The date line needs no data: while Home loads, or when it fails, it names today.
  const line = !answer || !day
    ? words.dateLine(formatDayLine(browserToday()))
    : answer.as_of
      ? words.dateLineAsOf(formatDayLine(day, { withYear: true }))
      : answer.view === "public"
        ? formatDayLine(day, { today: answer.today })
        : words.dateLine(formatDayLine(day, { today: answer.today }));
  const popover = answer ? countWindow(answer) : undefined;
  return (
    <h1 id="briefing" tabIndex={-1} className="max-w-[72ch] focus:outline-none" data-briefing={answer ? "ready" : "loading"}>
      <span className="block text-small font-semibold text-ink-muted">{line}</span>
      <span className="sr-only">{words.dateLineEnd}</span>
      {answer ? (
        <span className="mt-2 block text-lead text-pretty text-ink-heading">
          {answer.briefing.sentences.map((sentence, index) => (
            <Fragment key={index}>
              {index > 0 && " "}
              <Segments segments={sentence} popover={popover} />
            </Fragment>
          ))}
        </span>
      ) : null}
    </h1>
  );
}

// ── The Start here strip ─────────────────────────────────────────────────

type StripState = "shown" | "removing" | "removed" | "restoring" | "remove-failed" | "restore-failed";

function StartHere({ links }: { links: HomeAnswer["start_here"]["links"] }) {
  const [state, setState] = useState<StripState>("shown");
  const countId = useId();
  const captionId = useId();
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
    return (
      <section data-start-here="removed" className="rounded-md bg-surface-2 px-4 py-3 @md/page:px-6">
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
  return (
    <section aria-labelledby={`${START_HERE_ANCHOR} ${countId}`} data-start-here="shown" className="rounded-md bg-surface-2 px-4 py-4 @md/page:px-6">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        <h2 ref={title} id={START_HERE_ANCHOR} tabIndex={-1} className="text-label text-ink-muted focus:outline-none">
          {start.title}
        </h2>
        <span id={countId} data-start-count className="text-caption text-ink-muted">
          {copy.nav.startHere.count(formatNumber(doneCount, { compact: false }), formatNumber(links.length, { compact: false }))}
        </span>
        <span id={captionId} className="text-caption text-ink-muted @md/page:ml-auto">
          {start.caption}
        </span>
        <Button variant="ghost" aria-label={start.removeName} loading={state === "removing"} busyLabel={start.removing} onClick={() => void choose(false)}>
          {start.remove}
        </Button>
      </div>
      {state === "remove-failed" && <FailedLine>{start.removeFailed}</FailedLine>}
      <ul aria-labelledby={captionId} className="mt-3 flex flex-col gap-1 @md/page:flex-row @md/page:flex-wrap @md/page:gap-x-8 @md/page:gap-y-2">
        {links.map((link) => {
          // Each link leads with its tick, which appears at once and never moves; its name ends with "done" only once
          // the person followed it.
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
    </section>
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

function Line({ line, n, hidden }: { line: HomeLine; n: number; hidden: boolean }) {
  const action = (words.worth.actions as Record<string, string>)[line.action.key] ?? words.publicView.action;
  const badge = BADGES[line.status];
  return (
    <li
      id={line.id}
      tabIndex={-1}
      hidden={hidden}
      data-line-kind={line.kind}
      data-line-status={line.status}
      className="border-t border-line py-4 focus:outline-none @container/line"
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
        <Segments segments={line.segments} />{" "}
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

function WorthKnowing({ answer }: { answer: HomeAnswer }) {
  const titleId = useId();
  const worth = answer.worth;
  const [open, setOpen] = useState(false);
  const folded = Math.max(0, worth.lines.length - worth.fold_after);
  const title = worth.kind === "public" ? words.publicView.title : words.worth.title;
  const through = formatDate(worth.through, { style: "short" });
  const checked = formatDate(worth.checked_on, { style: "short" });
  const source =
    worth.kind === "public" ? words.publicView.source(through) : worth.kind === "agency" ? words.worth.sourceAgency(through, checked) : words.worth.source(through, checked);
  return (
    <section aria-labelledby={titleId} data-worth={worth.kind} className="rounded-md border border-line bg-surface p-4 @md/page:p-6">
      <h2 id={titleId} className="text-label text-ink-muted">
        {title}
      </h2>
      {worth.lines.length > 0 ? (
        <ul className="mt-4">
          {worth.lines.map((line, index) => (
            <Line key={line.id} line={line} n={index + 1} hidden={!open && index >= worth.fold_after} />
          ))}
        </ul>
      ) : (
        <WorthEmpty answer={answer} />
      )}
      {folded > 0 && (
        <div className="border-t border-line pt-3">
          <p className="text-small text-ink">{folded === 1 ? words.worth.foldOne : words.worth.fold(String(folded))}</p>
          <Button variant="ghost" flush icon={ChevronDown} aria-expanded={open} onClick={() => setOpen(!open)}>
            {open ? (folded === 1 ? words.worth.hideOne : words.worth.hide) : folded === 1 ? words.worth.showOne : words.worth.show}
          </Button>
        </div>
      )}
      <Source className="mt-4 border-t border-line pt-4">{source}</Source>
    </section>
  );
}

function WorthEmpty({ answer }: { answer: HomeAnswer }) {
  const worth = answer.worth;
  const w = words.worth;
  if (worth.empty === "first_run") {
    return <EmptyState className="mt-4" level={3} title={w.firstRunTitle} body={w.firstRunBody} link={{ href: "/projects", text: w.firstRunLink }} />;
  }
  if (worth.empty === "no_closed") return <p className="mt-4 text-small text-ink-muted">{words.publicView.empty}</p>;
  if (worth.empty === "nothing_behind" || worth.empty === "no_plan") return <p className="mt-4 text-small text-ink-muted">{w.agencyNothing}</p>;
  if (worth.empty === "nothing_marked") return <p className="mt-4 text-small text-ink-muted">{w.nothingMarked}</p>;
  // The window's words are the server's (the page picks no count word).
  return (
    <p className="mt-4 text-small text-ink-muted">
      <Fill template={w.quiet} slots={{ window: answer.window ? <Segments segments={answer.window.phrase} /> : "" }} />{" "}
      <TextLink href="/projects/following">{w.quietLink}</TextLink>
    </p>
  );
}

// ── Waiting for you ──────────────────────────────────────────────────────

function WaitingForYou({ answer }: { answer: HomeAnswer }) {
  const titleId = useId();
  const waiting = answer.waiting;
  const w = words.waiting;
  const reason = waiting.reason === "preview" ? w.preview : waiting.reason === "asof" ? w.asOf : null;
  return (
    <section aria-labelledby={titleId} data-waiting className="rounded-md border border-line bg-surface p-4 @md/page:p-6">
      <h2 id={titleId} className="text-label text-ink-muted">
        {w.title}
      </h2>
      {reason ? (
        <p className="mt-4 text-small text-ink-muted">{reason}</p>
      ) : waiting.rows.length === 0 ? (
        <p className="mt-4 text-small text-ink-muted" data-waiting-empty>
          {answer.view === "piu" ? w.emptyAgency : w.empty}{" "}
          <TextLink href="/packages">{w.emptyLink}</TextLink>
        </p>
      ) : (
        <>
          <ul className="mt-4 -mx-4">
            {waiting.rows.map((row) => (
              <DraftRow key={row.draft_id} row={row} />
            ))}
          </ul>
          <p className="mt-2 text-small">
            <TextLink href="/drafts">{waiting.more ? w.more(String(waiting.total)) : w.toDrafts}</TextLink>
          </p>
        </>
      )}
    </section>
  );
}

// ── The page ─────────────────────────────────────────────────────────────

function Loading() {
  const strip = useStore(startHereVisible);
  return (
    <>
      <span role="status" className="sr-only">
        {words.loading}
      </span>
      <div className="mt-2 flex max-w-[72ch] flex-col gap-2" aria-hidden="true">
        <SkeletonLine width="w-full" />
        <SkeletonLine width="w-full" />
        <SkeletonLine width="w-3/5" />
      </div>
      {strip && <Skeleton className="mt-8 h-28 w-full" />}
      <Skeleton className="mt-8 h-64 w-full" />
    </>
  );
}

export function HomePage() {
  // Showing the examples again from the end of Home reads Home once more, with the strip.
  const [reading, setReading] = useState(0);
  const [load, retry] = useLoad<HomeAnswer>(HOME_PATH, String(reading));
  const answer = load.status === "ready" ? load.data : null;
  useEffect(() => {
    if (load.status === "ready" && (load.afterRetry || reading > 0)) document.getElementById("briefing")?.focus();
  }, [load, reading]);
  // Start here goes with the person (ticket 114): World Bank staff's own Home today keeps its links in this browser,
  // so the sidebar on every other page shows the next one with no request of its own.
  useEffect(() => {
    if (answer && answer.view === "staff" && !answer.preview && !answer.as_of && answer.start_here.links.length > 0) keepLinks(answer.start_here.links);
  }, [answer]);
  const strip =Boolean(answer?.start_here.visible && answer.start_here.links.length > 0);
  // A later visit after Remove: World Bank staff today, with the strip's links but not the strip.
  const restore = Boolean(answer && !strip && answer.view === "staff" && !answer.as_of && answer.start_here.links.length > 0);
  return (
    <div className="layout-grid" data-home={load.status}>
      <div className="col-span-12">
        <Briefing answer={answer} />
        {load.status === "loading" && <Loading />}
        {load.status === "error" && (
          <div className="mt-6">
            <LoadError error={load.error} message={words.error} permission={words.permission} onRetry={retry} retrying={load.retrying} attempt={load.attempt} />
          </div>
        )}
        {answer && (
          <>
            {strip && (
              <div className="mt-6 @md/page:mt-8">
                <StartHere links={answer.start_here.links} />
              </div>
            )}
            {/* An implementing agency officer's own Home: "Check my plan" takes the strip's place (the 41 brief, 5.8). */}
            {answer.view === "piu" && !answer.preview && !answer.as_of && (
              <p className="mt-6 text-body @md/page:mt-8" data-check-my-plan>
                <TextLink href={CHECK_MY_PLAN}>{words.worth.agencyCheck}</TextLink>
              </p>
            )}
            <div className="mt-6 grid grid-cols-1 gap-6 @md/page:mt-8 @[75rem]/page:grid-cols-12 @[75rem]/page:gap-8">
              <div className="@[75rem]/page:col-span-7">
                <WorthKnowing answer={answer} />
              </div>
              {answer.view !== "public" && (
                <div className="@[75rem]/page:col-span-5">
                  <WaitingForYou answer={answer} />
                </div>
              )}
            </div>
            {restore && <RestoreLine onRestored={() => setReading((count) => count + 1)} />}
          </>
        )}
      </div>
    </div>
  );
}
