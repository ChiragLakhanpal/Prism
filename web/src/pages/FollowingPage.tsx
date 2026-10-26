// Following (ticket 37; the 37 brief, sections 3 to 5 and 10.1), at /projects/following: the projects a World Bank
// staff member follows, each with its status first, the signals that put it there one line each, and one next
// step. Projects with no signals fold away with a count, the page says what Strata cannot see, and "How I check the
// projects you follow" gives the method and the track record the replay harness stored. No model writes the list:
// every status, signal, count and date is project_signals' (GET /api/following), and the page counts nothing.
//
// From a page area of 1,200 px (@xl/page) the rows are a four-column table, with each column's definition in its
// header; below that each row is a block in a list, with the Status and Next definitions above it. Both are in the
// page, and the container query shows one, as Table's cards do. Rows come in the server's order: Needs a look,
// Watch, Not checked, then the fold, each by its soonest closing date and then its name, never by its signals.
//
// States: loading, populated, fold open, all quiet, one project, partly checked rows, a Not checked row, closed or
// pipeline rows, an existing mission brief, as of a past date, empty, error, permission, not World Bank staff (the
// server's 403), and the two previews.
import { useEffect, useId, useMemo, useState, type ReactNode } from "react";
import { Alert } from "../components/Alert";
import { Button } from "../components/Button";
import { EmptyState } from "../components/Card";
import { EightColumns } from "../components/EightColumns";
import { Fill } from "../components/Fill";
import { LoadError } from "../components/LoadError";
import { Num } from "../components/Num";
import { PageHeader } from "../components/PageHeader";
import { ProjectIdText } from "../components/ProjectId";
import { Tag } from "../components/LessonParts";
import { ProjectsTabs } from "../components/ProjectsTabs";
import { SignalLine } from "../components/SignalLine";
import { Skeleton, SkeletonLine, SkeletonText } from "../components/Skeleton";
import { Source } from "../components/Source";
import { StatusBadge, type BadgeKind } from "../components/StatusBadge";
import { DefinitionWindow } from "../components/Term";
import { TextLink } from "../components/TextLink";
import { copy } from "../copy";
import { dataReadinessHref } from "../routes";
import { draftHref, startMissionBrief, stopped } from "../lib/drafts";
import { navigate } from "../lib/router";
import { known, remember, visited } from "../lib/evidence";
import { formatCount, formatDate, formatNumber } from "../lib/format";
import {
  CHECK_ORDER,
  FOLDED,
  FOLLOWING_HREF,
  finding,
  markerRecord,
  metaTemplate,
  missingReasons,
  shortDate,
  statusDef,
  type FollowedProject,
  type Following,
  type Thresholds,
  type TrackCounts,
} from "../lib/following";
import { useLoad } from "../lib/load";
import { useStore } from "../lib/store";
import { viewOf, withReadParams } from "../lib/view";
import { cx } from "../lib/cx";

const words = copy.following;
const BADGES: Partial<Record<FollowedProject["status"], BadgeKind>> = {
  needs_a_look: "needs-a-look", watch: "watch", no_signals: "no-signals", not_checked: "not-checked",
};
const TRACK_ID = "how-i-check";

export function FollowingPage({ search }: { search: string }) {
  const view = viewOf(search);
  const [load, retry] = useLoad<Following>(withReadParams("/api/following", search));
  // The notice after "Stop writing" on a mission brief, shown once.
  const notice = useStore(stopped);
  const [said] = useState(() => (notice === FOLLOWING_HREF ? words.stopped : null));
  useEffect(() => {
    if (notice) stopped.set(null);
  }, []);
  const data = load.status === "ready" ? load.data : null;
  // Each signal's record opens in the evidence drawer at once, from what the route sent, with no request.
  useEffect(() => {
    if (data) for (const event of data.evidence) remember(event);
  }, [data]);

  // A viewer who cannot follow (a preview, or not World Bank staff) gets All projects' purpose, not Following's.
  const header = (tabs = true, purpose: string = copy.pages.following.purpose) => (
    <div className="col-span-12">
      <PageHeader title={copy.pages.following.title} purpose={purpose} />
      {tabs && <ProjectsTabs following />}
    </div>
  );

  if (view !== "staff") {
    return (
      <div className="layout-grid" data-following-page="preview">
        {header(false, copy.pages.projects.purpose)}
        <EightColumns className="col-span-12 mt-8">
          <EmptyState
            title={view === "piu" ? words.previewPiuTitle : words.previewPublicTitle}
            body={view === "piu" ? words.previewPiuBody : words.previewPublicBody}
          />
        </EightColumns>
      </div>
    );
  }
  if (load.status === "error" && load.error?.status === 403 && load.error.body.code === "not_staff") {
    return (
      <div className="layout-grid" data-following-page="not-staff">
        {header(false, copy.pages.projects.purpose)}
        <EightColumns className="col-span-12 mt-8">
          <EmptyState title={words.notStaffTitle} body={words.notStaffBody} link={{ href: "/projects", text: words.notStaffLink }} />
        </EightColumns>
      </div>
    );
  }
  if (load.status === "error") {
    return (
      <div className="layout-grid" data-following-page="error">
        {header()}
        <EightColumns className="col-span-12 mt-8">
          <h2 className="sr-only">{words.heading}</h2>
          <LoadError error={load.error} message={words.error} permission={words.permission} onRetry={retry} retrying={load.retrying} attempt={load.attempt} />
        </EightColumns>
      </div>
    );
  }
  if (!data) {
    return (
      <div className="layout-grid" data-following-page="loading" aria-busy="true">
        {header()}
        <div className="col-span-12 mt-8">
          <p role="status" className="sr-only">
            {words.loading}
          </p>
          <FollowingSkeleton />
        </div>
      </div>
    );
  }
  return (
    <div className="layout-grid" data-following-page="ready">
      {header()}
      {said && (
        <div className="col-span-12 mt-6 @md/page:col-span-8">
          <Alert state="info" live="status">
            {said}
          </Alert>
        </div>
      )}
      <div className="col-span-12 mt-8">
        {data.counts.total === 0 ? (
          <>
            <EightColumns>
              <EmptyState title={words.emptyTitle} body={words.emptyBody} link={{ href: "/projects", text: words.emptyLink }} />
            </EightColumns>
            <p className="mt-6 max-w-[72ch] text-small text-ink-muted">{copy.checkPlan.notVisible}</p>
          </>
        ) : (
          <FollowingBody data={data} />
        )}
      </div>
    </div>
  );
}

export function FollowingBody({ data }: { data: Following }) {
  const findingId = useId();
  const nextDefId = useId();
  const foldId = useId();
  const foldSentenceId = useId();
  const listFoldSentenceId = useId();
  const listNextDefId = useId();
  const listFoldId = useId();
  const [open, setOpen] = useState(false);
  const seen = useStore(visited);
  const events = useStore(known);
  const shown = data.projects.filter((entry) => !FOLDED.has(entry.status));
  const folded = data.projects.filter((entry) => FOLDED.has(entry.status));
  const checks = formatCount(data.checks);
  // Markers are numbered once per page, in the rows' order, counting the folded rows, so a number never changes
  // when the fold opens.
  const numbers = useMemo(() => {
    const found = new Map<string, number>();
    for (const entry of data.projects) {
      for (const signal of entry.rows) {
        const id = markerRecord(signal);
        if (id && !found.has(id)) found.set(id, found.size + 1);
      }
    }
    return found;
  }, [data]);
  const counts = data.counts;
  const statusOfOne = counts.total === 1 ? data.projects[0].status : null;
  const madeBy = data.past ? (
    <Fill template={words.madeByAsOf} slots={{ checks, date: formatDate(data.as_of) }} />
  ) : data.data_through ? (
    <Fill template={words.madeBy} slots={{ checks, checked: formatDate(data.checked_on), through: formatDate(data.data_through) }} />
  ) : (
    <Fill template={words.madeByUndated} slots={{ checks, checked: formatDate(data.checked_on) }} />
  );
  const shownCount = open ? counts.total : counts.shown;
  const row = (entry: FollowedProject) => ({ entry, numbers, events, seen, data, nextDefId });

  return (
    <>
      <section aria-labelledby={findingId}>
        <h2 id={findingId} data-lead tabIndex={-1} className="max-w-[72ch] text-title text-pretty text-ink-heading focus:outline-none">
          {finding(counts, statusOfOne)}
        </h2>
        <p className="mt-2 max-w-[72ch] text-caption text-ink-muted">{madeBy}</p>
        {counts.partly > 0 && (
          <p data-coverage-line className="mt-6 max-w-[72ch] text-small text-ink">
            {/* Numerals beside "of" (the 37 brief, section 9); when no project had every check, a sentence that says so. */}
            {counts.fully === 0 ? words.coverageNone : (
              <Fill template={words.coverage} slots={{ k: <Num value={counts.fully} />, n: <Num value={counts.checked} />, m: <Num count={counts.partly} /> }} />
            )}{" "}
            <TextLink href={dataReadinessHref(data.sources, "project_signals")}>{words.coverageLink}</TextLink>
          </p>
        )}
        {/* The two definitions that matter without columns move above the list (the 37 brief, section 3.3). */}
        <div className="mt-6 flex max-w-[72ch] flex-col gap-1 text-caption text-ink-muted @xl/page:hidden" data-list-definitions>
          <p>
            <StatusTerm thresholds={data.thresholds} track={data.track_record} checks={data.checks} />
            {words.headerJoin}
            {statusDef(data.thresholds)}
            {words.defEnd}
          </p>
          <p id={listNextDefId}>
            {words.cols.next.label}
            {words.headerJoin}
            {data.past ? words.cols.next.defAsOf : words.cols.next.def}
            {words.defEnd}
          </p>
        </div>
        <p className="mt-4 text-caption text-ink-muted @xl/page:mt-6" data-count-line>
          {words.countLine(shownCount, counts.total)}
        </p>

        {/* The table, from a page area of 1,200 px. */}
        <div data-following-view="table" className="mt-2 hidden overflow-hidden rounded-md border border-line bg-surface @xl/page:block">
          <table className="w-full table-fixed border-collapse text-left">
            <caption className="sr-only">{words.tableCaption}</caption>
            <thead className="bg-surface-2">
              <tr>
                <HeaderCell className="w-[13rem]" label={<StatusTerm thresholds={data.thresholds} track={data.track_record} checks={data.checks} />} def={statusDef(data.thresholds)} />
                <HeaderCell className="w-[16rem]" label={words.cols.project.label} def={words.cols.project.def} />
                <HeaderCell label={words.cols.signals.label} def={words.cols.signals.def} />
                <HeaderCell className="w-[15rem]" label={words.cols.next.label} def={data.past ? words.cols.next.defAsOf : words.cols.next.def} defId={nextDefId} />
              </tr>
            </thead>
            <tbody>
              {shown.map((entry) => (
                <TableRow key={entry.project.project_id} {...row(entry)} describedBy={nextDefId} />
              ))}
              {folded.length > 0 && (
                <tr className="border-t-2 border-line bg-page">
                  <td colSpan={4} className="px-4 py-3">
                    <Fold counts={counts} open={open} onToggle={() => setOpen(!open)} controls={foldId} sentenceId={foldSentenceId} />
                  </td>
                </tr>
              )}
            </tbody>
            {folded.length > 0 && (
              <tbody id={foldId} hidden={!open} className="motion-safe:animate-fade-in">
                {folded.map((entry) => (
                  <TableRow key={entry.project.project_id} {...row(entry)} describedBy={nextDefId} />
                ))}
              </tbody>
            )}
          </table>
        </div>

        {/* The list of row blocks, below a page area of 1,200 px. */}
        <div data-following-view="list" className="mt-2 @xl/page:hidden">
          <ul aria-labelledby={findingId}>
            {shown.map((entry) => (
              <ListRow key={entry.project.project_id} {...row(entry)} describedBy={listNextDefId} />
            ))}
            {folded.length > 0 && (
              <li className="border-t-2 border-line py-4">
                <Fold counts={counts} open={open} onToggle={() => setOpen(!open)} controls={listFoldId} sentenceId={listFoldSentenceId} />
              </li>
            )}
          </ul>
          {folded.length > 0 && (
            <ul id={listFoldId} hidden={!open} aria-labelledby={findingId}>
              {folded.map((entry) => (
                <ListRow key={entry.project.project_id} {...row(entry)} describedBy={listNextDefId} />
              ))}
            </ul>
          )}
        </div>

        <Source className="mt-2">
          {data.data_through ? <Fill template={words.source} slots={{ date: formatDate(data.data_through) }} /> : words.sourceUndated}
        </Source>
        <p className="mt-6 max-w-[72ch] text-small text-ink-muted" data-not-visible>
          {copy.checkPlan.notVisible}
        </p>
      </section>
      <TrackRecordSection data={data} />
    </>
  );
}

function HeaderCell({ label, def, className, defId }: { label: ReactNode; def: string; className?: string; defId?: string }) {
  return (
    <th scope="col" className={cx("px-4 py-3 align-top", className)}>
      <span className="block text-small font-bold text-ink-heading">{label}</span>
      <span className="sr-only">{words.headerJoin}</span>
      <span id={defId} className="block text-caption font-normal text-ink-muted">
        {def}
      </span>
    </th>
  );
}

// "Status", which opens the full rules, the strong checks and the track record's status sentence.
function StatusTerm({ thresholds, track, checks }: { thresholds: Thresholds; track: Following["track_record"]; checks: number }) {
  const look = formatCount(thresholds.look_min);
  const inSentence = (keys: string[]) => keys.map((key, index) => (index === 0 ? copy.signals.check[key].name : copy.signals.checkInSentence(copy.signals.check[key].name)));
  const strong = thresholds.strong;
  const joinedNames = joinAnd(inSentence(strong));
  // With no strong check, the checks that turn strong from a count of activities, and that count when they share one.
  const counted = Object.entries(thresholds.strong_from) as [string, number][];
  const shared = new Set(counted.map(([, n]) => n)).size === 1 ? counted[0]?.[1] : undefined;
  const strongNone = shared !== undefined
    ? words.statusDefinition.strongNone(joinAnd(inSentence(counted.map(([key]) => key))), formatCount(shared))
    : words.statusDefinition.strongNoneMixed;
  return (
    <DefinitionWindow label={words.statusDefinition.title} title={words.statusDefinition.title} triggerClassName="inline-flex min-h-6 items-center">
      <dl className="flex flex-col gap-1" data-status-rules>
        {words.statusDefinition.rules(look, formatCount(checks)).map(([status, rule]) => (
          <div key={status}>
            <dt className="inline font-semibold">
              {status}
              {words.headerJoin}
            </dt>
            <dd className="inline">{rule}</dd>
          </div>
        ))}
      </dl>
      <p className="mt-2">{words.statusDefinition.signalIs}</p>
      <p className="mt-2">{strong.length ? words.statusDefinition.strong(joinedNames) : strongNone}</p>
      <p className="mt-2">{track ? <StatusLead track={track} /> : copy.track.none}</p>
      <p className="mt-2">
        <TextLink href={`#${TRACK_ID}`}>{words.statusDefinition.link}</TextLink>
      </p>
    </DefinitionWindow>
  );
}

type RowProps = {
  entry: FollowedProject;
  numbers: Map<string, number>;
  events: ReturnType<typeof known.get>;
  seen: ReadonlySet<string>;
  data: Following;
  nextDefId: string;
  describedBy: string;
};

function StatusCell({ entry }: { entry: FollowedProject }) {
  const badge = BADGES[entry.status];
  if (!badge) return <p className="text-small text-ink-muted">{words.status[entry.status] ?? entry.status}</p>;
  return (
    <>
      <StatusBadge kind={badge} />
      {(entry.status === "needs_a_look" || entry.status === "watch") && (
        <p className="mt-2 text-caption text-ink-muted" data-signal-count>
          {words.signalCount(entry.counts.signals)}
        </p>
      )}
    </>
  );
}

function ProjectCell({ entry }: { entry: FollowedProject }) {
  const project = entry.project;
  return (
    <>
      <h3 className="text-title text-ink-heading">
        <TextLink href={`/projects/${project.project_id}`}>{project.project_name}</TextLink>
        {/* A follow the seed command made for you (ticket 41). */}
        {entry.example && (
          <span className="ml-2 inline-block align-middle">
            <Tag>{copy.home.example}</Tag>
          </span>
        )}
      </h3>
      <p className="mt-1 text-caption text-ink-muted" data-meta data-project-row-meta>
        <Fill template={metaTemplate(project)} slots={{
          country: project.country ?? "",
          pid: <ProjectIdText pid={project.project_id} />,
          date: project.closing_date ? shortDate(project.closing_date) : "",
        }} />
      </p>
    </>
  );
}

function SignalsCell({ entry, numbers, events, seen, data }: RowProps) {
  const checks = formatCount(data.checks);
  const reasons = missingReasons(entry);
  // The plan window is the thresholds file's [signals].plan_months, as the route sent it.
  const reasonText = reasons.map((reason) => (words.missing[reason] ?? reason).replace("{months}", formatCount(data.thresholds.plan_months)));
  const joined = reasonText.join(words.missingJoin);
  const partial = entry.counts.not_ran > 0 && entry.status !== "not_checked" && reasons.length > 0 && (
    <p className="mt-2 max-w-[72ch] text-caption text-ink-muted" data-partial>
      <Fill template={words.partial} slots={{ k: formatCount(entry.counts.not_ran), n: checks, reasons: joined }} />
    </p>
  );
  if (entry.status === "not_checked") {
    return <p className="max-w-[72ch] text-small text-ink">{words.notCheckedSignals.replace("{checks}", checks)}</p>;
  }
  if (entry.status === "closed" || entry.status === "dropped") {
    return (
      <p className="max-w-[72ch] text-small text-ink">
        <Fill template={words.closedSignals} slots={{ date: entry.project.closing_date ? formatDate(entry.project.closing_date) : "" }} />
      </p>
    );
  }
  if (entry.status === "pipeline") return <p className="max-w-[72ch] text-small text-ink">{words.pipelineSignals}</p>;
  if (entry.status === "no_signals") {
    return (
      <>
        <p className="max-w-[72ch] text-small text-ink">
          {entry.counts.not_ran > 0
            ? words.noneSignalsPartial.replace("{ran}", formatCount(entry.counts.ran))
            : words.noneSignals.replace("{checks}", checks)}
        </p>
        {partial}
      </>
    );
  }
  return (
    <>
      <ul aria-label={words.signalsLabel(entry.project.project_name)} className="flex flex-col gap-2">
        {entry.rows.map((signal) => {
          const id = markerRecord(signal);
          return <SignalLine key={signal.check} signal={signal} asOf={data.as_of} n={id ? numbers.get(id) : undefined} event={id ? events[id] : undefined} opened={id ? seen.has(id) : false} />;
        })}
      </ul>
      {partial}
    </>
  );
}

function NextCell({ entry, data, describedBy }: RowProps) {
  if (entry.status === "not_checked") return <p className="text-caption text-ink-muted">{words.notCheckedNext}</p>;
  if (entry.status === "closed" || entry.status === "dropped" || entry.status === "pipeline") {
    return <p className="text-caption text-ink-muted">{words.closedNext}</p>;
  }
  if (data.past) return null;
  const brief = entry.mission_brief;
  return (
    <>
      <Button
        variant="secondary"
        className="max-[30rem]:w-full"
        aria-label={words.addLabel(entry.project.project_name)}
        aria-describedby={describedBy}
        data-add-brief
        onClick={() => navigate(startMissionBrief({ project_id: entry.project.project_id, project_name: entry.project.project_name, country: entry.project.country }))}
      >
        {words.add}
      </Button>
      {brief && (
        <p className="mt-2 text-caption text-ink-muted" data-existing-brief>
          <Fill template={words.existing} slots={{ date: shortDate(brief.created_at) }} />{" "}
          <TextLink href={draftHref(brief.draft_id)}>{words.existingLink}</TextLink>
        </p>
      )}
    </>
  );
}

function TableRow(props: RowProps) {
  return (
    <tr className="border-t-2 border-line align-top" data-project-row={props.entry.project.project_id} data-status={props.entry.status}>
      <td className="px-4 py-3">
        <StatusCell entry={props.entry} />
      </td>
      <th scope="row" className="px-4 py-3 text-left font-normal">
        <ProjectCell entry={props.entry} />
      </th>
      <td className="px-4 py-3">
        <SignalsCell {...props} />
      </td>
      <td className="px-4 py-3">
        <NextCell {...props} />
      </td>
    </tr>
  );
}

function ListRow(props: RowProps) {
  const entry = props.entry;
  return (
    <li className="border-t-2 border-line py-4" data-project-row={entry.project.project_id} data-status={entry.status}>
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
        <StatusCell entry={entry} />
      </div>
      <div className="mt-2">
        <ProjectCell entry={entry} />
      </div>
      <div className="mt-3">
        <SignalsCell {...props} />
      </div>
      <div className="mt-4">
        <NextCell {...props} />
      </div>
    </li>
  );
}

// The fold's sentence names what it holds, each kind counted: the quiet projects, then the closed ones and those in
// the pipeline, which it knows apart.
function Fold({ counts, open, onToggle, controls, sentenceId }: { counts: Following["counts"]; open: boolean; onToggle: () => void; controls: string; sentenceId: string }) {
  const quiet = counts.no_signals;
  const closed = counts.ended - counts.pipeline;
  const pipeline = counts.pipeline;
  const ended = closed + pipeline > 0 &&
    words.foldEnded(quiet === 0, closed, formatCount(closed, { capital: true }), pipeline, formatCount(pipeline, { capital: closed === 0 }));
  // The button sits under the sentence, flush on the text's edge.
  return (
    <div className="flex flex-col items-start gap-1">
      <p id={sentenceId} className="text-small text-ink-muted" data-fold-sentence>
        {quiet > 0 && words.fold(quiet, formatCount(quiet, { capital: true }))}
        {quiet > 0 && ended && " "}
        {ended}
        {counts.partly_folded > 0 && <> {words.foldPartial(counts.partly_folded, formatCount(counts.partly_folded))}</>}
      </p>
      <Button variant="ghost" flush onPage aria-expanded={open} aria-controls={controls} aria-describedby={sentenceId} onClick={onToggle} data-fold>
        {open ? words.hide(counts.folded) : words.show(counts.folded)}
      </Button>
    </div>
  );
}

// ── How I check the projects you follow ──────────────────────────────────

function countNum(counts: TrackCounts, track: NonNullable<Following["track_record"]>, which: "n" | "k") {
  const value = counts[which] ?? 0;
  // Numerals beside "of", in sentences and cells alike (the 37 brief, section 9).
  return (
    <Num
      value={value}
      check={{
        tooltip: copy.track.num(formatNumber(counts.n ?? 0), formatNumber(counts.k ?? 0), formatCount(track.window_months), formatDate(track.ran_on)),
      }}
    />
  );
}

function StatusLead({ track }: { track: NonNullable<Following["track_record"]> }) {
  const status = track.status;
  return (
    <Fill template={copy.track.statusLead} slots={{
      k_look: countNum(status.needs_a_look, track, "k"), n_look: countNum(status.needs_a_look, track, "n"),
      k_watch: countNum(status.watch, track, "k"), n_watch: countNum(status.watch, track, "n"),
      k_none: countNum(status.no_signals, track, "k"), n_none: countNum(status.no_signals, track, "n"),
    }} />
  );
}

function trigger(key: string, thresholds: Thresholds): string {
  const template = copy.signals.check[key].trigger;
  const values: Record<string, string> = {
    completion_passed: thresholds.completion_passed_min_millions,
    above_estimate: thresholds.actual_to_estimate_ratio,
  };
  return template
    .replace("{amount}", key === "late_direct" ? thresholds.late_direct_min_millions : values.completion_passed)
    .replace("{ratio}", values.above_estimate)
    .replace("{months}", formatCount(key === "late_direct" ? thresholds.late_direct_months : key === "restructured" ? thresholds.restructured_months : thresholds.disbursement_months))
    .replace("{n}", formatCount(thresholds.closing_moves_min))
    .replace("{levels}", thresholds.restructured_levels.join(words.missingJoin))
    .replace("{pct}", String(thresholds.disbursement_max_percent));
}

// "A, B and C", as the finding joins its parts.
export function joinAnd(items: string[]): string {
  return items.length <= 1 ? items.join("") : `${items.slice(0, -1).join(words.partsJoin)}${words.partsTwo}${items.at(-1)}`;
}

function TrackRecordSection({ data }: { data: Following }) {
  const [open, setOpen] = useState(false);
  const checksId = useId();
  const track = data.track_record;
  const checks = formatCount(data.checks);
  const thresholds = data.thresholds;
  const cell = (counts: TrackCounts | undefined) =>
    !track || !counts ? (
      <span className="text-ink-muted">{copy.track.notReplayed}</span>
    ) : !counts.n ? (
      <span className="text-ink-muted">{copy.track.never}</span>
    ) : (
      <>
        <span className="whitespace-nowrap">
          <Fill template={copy.track.cell("{k}", "{n}")} slots={{ k: countNum(counts, track, "k"), n: countNum(counts, track, "n") }} />
        </span>
        {counts.few && <span className="block text-caption text-ink-muted">{copy.track.few}</span>}
      </>
    );
  const strongText = (key: string) => {
    const from = thresholds.strong_from[key as keyof typeof thresholds.strong_from];
    if (thresholds.strong.includes(key as never)) return copy.track.yes;
    return from ? copy.track.strongFrom(formatCount(from)) : copy.track.no;
  };
  const rows = [
    ...CHECK_ORDER.map((key) => ({ key, name: copy.signals.check[key].name, trigger: trigger(key, thresholds), strong: strongText(key), counts: track?.checks[key], baseline: false })),
    { key: "no_signals", name: copy.track.baseline.name, trigger: copy.track.baseline.trigger, strong: "", counts: track?.status.no_signals, baseline: true },
  ];
  return (
    <section aria-labelledby={TRACK_ID} className="mt-12" data-track-record={track ? "stored" : "none"}>
      <h2 id={TRACK_ID} tabIndex={-1} className="text-title text-ink-heading focus:outline-none">
        {copy.track.heading}
      </h2>
      <div className="max-w-[72ch]">
        <p className="mt-2 text-body text-ink">{copy.track.method.replace("{checks}", checks)}</p>
        {track ? (
          <>
            <p className="mt-4 text-body text-ink" data-track-status>
              <StatusLead track={track} />
              {track.status.needs_a_look.few && <> {copy.track.fewLook.replace("{n}", formatNumber(track.status.needs_a_look.n ?? 0))}</>}
              {track.status.watch.few && <> {copy.track.fewWatch.replace("{n}", formatNumber(track.status.watch.n ?? 0))}</>}
            </p>
            <p className="mt-2 text-body text-ink">{copy.track.why}</p>
            <p className="mt-2 text-caption text-ink-muted">
              <Fill template={copy.track.scope} slots={{
                dates: joinAnd(track.dates.map((date) => formatDate(date))),
                window: formatCount(track.window_months),
              }} />
            </p>
            <Source className="mt-2">
              <Fill template={copy.track.source} slots={{ date: formatDate(track.ran_on) }} />
            </Source>
          </>
        ) : (
          <p className="mt-4 text-body text-ink" data-track-status>
            {copy.track.none}
          </p>
        )}
      </div>
      <div className="mt-4">
        <Button variant="ghost" flush onPage aria-expanded={open} aria-controls={checksId} onClick={() => setOpen(!open)}>
          {open ? copy.track.hide : copy.track.show(checks)}
        </Button>
      </div>
      <div id={checksId} hidden={!open} className="mt-2">
        {/* From a page area of 1,024 px, a table; a region you can scroll from the keyboard if it is ever wider than
            its frame, positioned so the header's hidden ": " stays inside it. */}
        <div role="region" aria-label={copy.track.tableTitle} tabIndex={0} className="relative hidden overflow-x-auto rounded-md border border-line bg-surface @lg/page:block" data-track-view="table">
          <table className="w-full border-collapse text-left text-small">
            <caption className="sr-only">{copy.track.tableTitle}</caption>
            <thead className="bg-surface-2">
              <tr>
                <th scope="col" className="px-4 py-3 align-bottom text-small font-bold text-ink-heading">{copy.track.cols.check}</th>
                <th scope="col" className="px-4 py-3 align-bottom text-small font-bold text-ink-heading">{copy.track.cols.trigger}</th>
                <th scope="col" className="px-4 py-3 align-bottom text-small font-bold text-ink-heading">{copy.track.cols.strong}</th>
                <th scope="col" className="w-[16rem] px-4 py-3 text-right align-bottom">
                  <span className="block text-small font-bold text-ink-heading">{copy.track.cols.record}</span>
                  <span className="sr-only">{words.headerJoin}</span>
                  <span className="block text-caption font-normal text-ink-muted">{copy.track.cols.recordDef}</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {rows.filter((row) => !row.baseline).map((row) => (
                <tr key={row.key} className="border-t border-line align-top" data-track-check={row.key}>
                  <th scope="row" className="px-4 py-3 font-semibold text-ink">{row.name}</th>
                  <td className="px-4 py-3 text-ink">{row.trigger}</td>
                  <td className="px-4 py-3 text-ink">{row.strong}</td>
                  <td className="px-4 py-3 text-right tabular-nums">{cell(row.counts)}</td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              {rows.filter((row) => row.baseline).map((row) => (
                <tr key={row.key} className="border-t-2 border-line align-top">
                  <th scope="row" className="px-4 py-3 font-semibold text-ink">{row.name}</th>
                  <td className="px-4 py-3 text-ink">{row.trigger}</td>
                  <td className="px-4 py-3" />
                  <td className="px-4 py-3 text-right tabular-nums">{cell(row.counts)}</td>
                </tr>
              ))}
            </tfoot>
          </table>
        </div>
        {/* Below that, each check is a block: its name, then each column's head above its value (the 37 brief, 5.1). */}
        <ul aria-label={copy.track.tableTitle} className="@lg/page:hidden" data-track-view="blocks">
          {rows.map((row) => (
            <li key={row.key} className={cx("py-3", row.baseline ? "border-t-2 border-line" : "border-t border-line")} data-track-block={row.key}>
              <h3 className="text-small font-semibold text-ink-heading">{row.name}</h3>
              <dl className="mt-1 flex flex-col gap-2 text-small">
                <div>
                  <dt className="text-caption text-ink-muted">{copy.track.cols.trigger}</dt>
                  <dd className="text-ink">{row.trigger}</dd>
                </div>
                {!row.baseline && (
                  <div>
                    <dt className="text-caption text-ink-muted">{copy.track.cols.strong}</dt>
                    <dd className="text-ink">{row.strong}</dd>
                  </div>
                )}
                <div>
                  <dt className="text-caption text-ink-muted">{copy.track.cols.recordBlock}</dt>
                  <dd className="text-ink tabular-nums">{cell(row.counts)}</dd>
                </div>
              </dl>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

// While the list loads (the 37 brief, section 10.1): the finding's and caption's bars, then three rows of
// blocks with a badge, a name, a meta line, three signal lines and the button, static, no shimmer.
export function FollowingSkeleton() {
  return (
    <div aria-hidden="true">
      <SkeletonLine className="text-title" width="w-[70%] max-w-[72ch]" />
      <SkeletonLine className="mt-2 text-caption" width="w-1/2 max-w-[72ch]" />
      <div className="mt-8 flex flex-col">
        {[0, 1, 2].map((row) => (
          <div key={row} className="border-t-2 border-line py-4">
            <Skeleton className="h-7 w-32" radius="rounded-pill" />
            <SkeletonLine className="mt-2 text-title" width="w-[70%]" />
            <SkeletonLine className="mt-1 text-caption" width="w-1/2" />
            <SkeletonText className="mt-3 text-small" widths={["w-full", "w-[90%]", "w-[70%]"]} />
            <Skeleton className="mt-4 h-11 w-44" radius="rounded-pill" />
          </div>
        ))}
      </div>
    </div>
  );
}
