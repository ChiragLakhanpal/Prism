// The plan check (the 10 brief, section 2; ticket 100's redesign): check_plan's result for one Procurement Plan
// version.
//
// - PlanCheckHeader: the agency's name (the h1, wrapping in full), the plan's date, the check pill and the page's one
//   action. It sticks under the bar from a 1024 px window 50rem tall, and only while it holds that action.
// - PlanCheck: the finding in the finding style, with "How I checked" beside it from a 75rem page area (ticket 130),
//   then the activities panel: its name and count line, the rows in STEP's columns with each mark's badge and reason,
//   the activities with no signals folded behind "Show them", and a foot strip with the source line and what Prism
//   cannot see. Below that page area "How I checked" follows the activities. Then the zones the page passes: "What
//   changed" as a closed row and the baseline as a row.
// - PlanCheckSkeleton: the same places while the check loads, under the real panel name and column heads.
//
// A row's reference is a button that opens the row's records in the evidence drawer (PlanRowRecords.tsx), and the
// row keeps the current mark while they show. A count word in the finding marks the rows it counts and moves focus to
// the first one's reference.
//
// Every number comes from the tool: the counts, the days, the ratio and the amounts. The screen
// writes them (web/src/lib/format.ts) and counts nothing. Marked rows come first, by their strongest
// mark, then in the order check_plan returns them. Each row and each card names its STEP reference
// in data-activity, and an address whose hash names a reference opens the fold if it must, brings
// that activity into view with nothing cut at the top edge, and focuses it (ticket 14 links to plan
// rows this way).
import { createElement, Fragment, useEffect, useId, useRef, useState, type ReactNode, type Ref } from "react";
import { usePageAtLeast } from "../lib/usePageAtLeast";
import { copy } from "../copy";
import type { EvidenceEvent } from "../lib/answer";
import type { Activity, CheckPlanResult, Mark, Reason } from "../lib/api";
import { cx } from "../lib/cx";
import { evidenceHref, evidenceIn, openEvidence, remember, visited } from "../lib/evidence";
import { formatAmountText, formatCount, formatDate, formatNumber } from "../lib/format";
import { planRowCheckId } from "../lib/planRows";
import { address } from "../lib/router";
import { fill } from "../routes";
import { sticks } from "../lib/sticky";
import { useStore } from "../lib/store";
import { Button } from "./Button";
import { CheckPill } from "./CheckPill";
import { CitationMarker } from "./CitationMarker";
import { Fill, Joined, Unbroken } from "./Fill";
import { FootStrip } from "./FootStrip";
import { useShows } from "../lib/view";
import { ListedRefs, MonoWords } from "./MonoWords";
import { Num, type NumCheck } from "./Num";
import { checkFrom, FromLine, planFrom } from "./NumFrom";
import { ProjectId } from "./ProjectId";
import { SidePanel } from "./SidePanel";
import { Skeleton, SkeletonLine, SkeletonText } from "./Skeleton";
import { Source } from "./Source";
import { StatusBadge, type BadgeKind } from "./StatusBadge";
import { Steps, type Step } from "./Steps";
import { CARD_FIELD, CARD_FIELDS } from "./Table";
import { TaskZone } from "./TaskZone";
import { DefinitionWindow } from "./Term";
import { TextLink } from "./TextLink";

const words = copy.checkPlan;
export const BADGE: Record<Mark, BadgeKind> = { needs_a_look: "needs-a-look", watch: "watch", moved_on: "moved-on", data_note: "data-note" };
const RANK: Record<Mark, number> = { needs_a_look: 0, watch: 1, moved_on: 2, data_note: 3 };

export type CheckedPlan = CheckPlanResult & {
  plan: NonNullable<CheckPlanResult["plan"]>;
  project: NonNullable<CheckPlanResult["project"]>;
  counts: NonNullable<CheckPlanResult["counts"]>;
};

const whole = (value: number) => formatNumber(value, { compact: false });
const amount = (text: string) => formatNumber(Number(text), { decimals: 2, compact: false });
const day = (iso: string) => <Num date={iso} />;

// A number's tooltip (DESIGN.md, Number tooltip): what it is, in one sentence of its own, and where it came from: the
// plan row for a value the row holds, or my check of this plan on its as-of date for the days it worked out from more
// than one record. None opens anything yet, so none has an action line.
function checked(result: CheckedPlan, what: ReactNode, from: "plan" | "check" = "check"): NumCheck {
  const words = from === "plan" ? planFrom(result.plan.implementing_agency, result.plan.plan_date) : checkFrom(result.as_of);
  return { tooltip: what, from: <FromLine words={words} /> };
}

function Days({ days, check }: { days: number; check: NumCheck }) {
  return <Num value={days} options={{ compact: false }} check={check} />;
}

// The delay from the baseline (ticket 21), the sentence that follows a reason's first sentence when a
// baseline is saved for the agency's plans. Its days explain themselves, as the first delay's do.
function BaselineSentence({ reason, result, kind }: { reason: Reason; result: CheckedPlan; kind: "signing" | "completion" }) {
  const found = reason.baseline;
  if (!found) return null;
  const b = words.reason.baseline;
  const e = words.explain;
  const days = found.days ?? 0;
  const planned = found.planned_on;
  const plan = { plan: <span className="whitespace-nowrap">{formatDate(found.plan_date)}</span> };
  const daysNum = (template: string) => <Days days={days} check={checked(result, <Fill template={template} slots={plan} />)} />;
  let sentence: ReactNode = null;
  switch (found.state) {
    case "late":
    case "early":
      sentence = (
        <Fill template={b[found.state](days)} slots={{ days: daysNum(e.baselineSigningDays), date: planned ? day(planned) : "" }} />
      );
      break;
    case "on_date":
      sentence = b.on_date;
      break;
    case "past":
      sentence = (
        <Fill
          template={b.past(days)}
          slots={{
            date: planned ? day(planned) : "",
            days: daysNum(kind === "signing" ? e.baselinePastSigning : e.baselinePastCompletion),
            as_of: day(result.as_of),
          }}
        />
      );
      break;
    case "ahead":
      sentence = <Fill template={b.ahead} slots={{ date: planned ? day(planned) : "" }} />;
      break;
    case "not_in_baseline":
      sentence = b.not_in_baseline;
      break;
    case "no_date":
      sentence = b.no_date;
      break;
  }
  return (
    <>
      {" "}
      <span data-baseline-delay={found.state}>{sentence}</span>
    </>
  );
}

// The citation of a moved-on reason (ticket 132): the disagreement between the plan row and the record that says the
// contract was signed, which opens in the evidence drawer with both sides, as the Timeline tab's list opens it.
function DisagreementCite({ id, record }: { id: string; record?: string | null }) {
  const key = `disagreement:${id}`;
  const opened = useStore(visited).has(key);
  const open = evidenceIn(useStore(address).search) === key;
  return (
    <CitationMarker
      n={1}
      source={words.movedOnSource[record ?? ""] ?? words.movedOnSource.contract_awards}
      href={evidenceHref(key)}
      evidenceId={key}
      opened={opened}
      active={open}
      onOpen={(marker) => openEvidence(key, { serial: null, sentence: null, marker, runId: null })}
    />
  );
}

// One reason's sentence from the copy file, filled with the tool's values for it.
function ReasonText({ reason, result }: { reason: Reason; result: CheckedPlan }) {
  const r = words.reason;
  const e = words.explain;
  switch (reason.code) {
    case "completion_passed_no_contract":
      return (
        <>
          <Fill template={r.completion_passed_no_contract} slots={{ date: day(reason.planned_completion_on!) }} />
          <BaselineSentence reason={reason} result={result} kind="completion" />
          {reason.closing_date && (
            <>
              {" "}
              <Fill
                template={(reason.days_to_close ?? 0) < 0 ? r.projectClosed : r.projectCloses}
                slots={{ date: day(reason.closing_date) }}
              />
            </>
          )}
        </>
      );
    case "pending_near_closing": {
      const days = reason.days_to_close!;
      return <Fill template={r.pending_near_closing(days)} slots={{ days: <Days days={days} check={checked(result, e.closingDays)} /> }} />;
    }
    case "pending_on_closing_day":
      return <>{r.pending_on_closing_day}</>;
    case "pending_after_closing":
      return <Fill template={r.pending_after_closing} slots={{ date: day(reason.closing_date!) }} />;
    case "signed_late_over_estimate":
    case "signed_over_estimate": {
      // The ratio's tooltip names no number the page does not show: the row's amounts are in its own columns, and the
      // tool's unrounded ratio is not given.
      const ratio = <Num value={reason.ratio!} options={{ compact: false }} check={checked(result, e.ratio, "plan")} />;
      const slots: Record<string, ReactNode> = { date: day(reason.signed_on!), actual: amount(reason.actual_amount_usd!), ratio };
      if (reason.code === "signed_over_estimate") return <Fill template={r.signed_over_estimate} slots={slots} />;
      const days = reason.days_late!;
      slots.days = <Days days={days} check={checked(result, e.signingDays)} />;
      // With a baseline, the first delay is named as from the first published planned date, and the
      // delay from the baseline follows it (the 21 brief, section 5.3).
      if (reason.baseline) {
        return (
          <>
            <Fill template={r.signed_late_first(days)} slots={slots} />
            <BaselineSentence reason={reason} result={result} kind="signing" />
          </>
        );
      }
      return <Fill template={r.signed_late_over_estimate(days)} slots={slots} />;
    }
    case "method_differs_from_reference":
      return (
        <Fill
          template={r.method_differs_from_reference}
          slots={{ code: reason.reference_method_code, referenceMethod: reason.reference_method, method: reason.method }}
        />
      );
    case "actual_amount_zero":
      return <Fill template={r.actual_amount_zero} slots={{ status: reason.process_status, actual: amount(reason.actual_amount_usd!) }} />;
    case "method_unknown":
      return <Fill template={r.method_unknown} slots={{ method: reason.method }} />;
    case "no_planned_date":
      return <Fill template={r.no_planned_date} slots={{ step: reason.step }} />;
    case "no_estimate":
      return <>{r.no_estimate}</>;
    case "moved_on_since_plan":
      // Ticket 132: what the record shows, with the disagreement between the plan row and that record cited.
      return (
        <>
          <Fill
            template={r.moved_on_since_plan[reason.record ?? ""] ?? r.moved_on_since_plan.contract_awards}
            slots={{ date: day(reason.signed_on!), status: r.stillSays[reason.process_status ?? ""] ?? reason.process_status }}
          />
          {reason.disagreement_id && <DisagreementCite id={reason.disagreement_id} record={reason.record} />}
        </>
      );
    default:
      // The registry refuses a reason code config/tools.toml does not list, so none reaches here.
      return null;
  }
}

// One paragraph per mark: its reasons' sentences, in the order check_plan returns them. The row's records in the
// drawer give the same sentences (PlanRowRecords.tsx).
export function MarkReasons({ mark, result }: { mark: Activity["marks"][number]; result: CheckedPlan }) {
  return (
    <p className="text-small text-ink">
      {mark.reasons.map((reason, index) => (
        <span key={index}>
          {index > 0 && " "}
          <ReasonText reason={reason} result={result} />
        </span>
      ))}
    </p>
  );
}

const blank = <span className="text-ink-muted">{copy.notInPlan}</span>;

// "Request for Bids ·" then "Open - National": the dot is tied to the Method with a no-break space,
// and the Market Approach moves to the next line whole when it fits there, so no line starts with
// the dot or with STEP's own dash. The evidence drawer's record view writes them the same way.
export function MethodText({ method, approach }: { method: string; approach?: string | null }) {
  return approach ? (
    <>
      {method}
      {words.methodDot}{" "}
      <span data-market-approach className="inline-block max-w-full">
        {approach}
      </span>
    </>
  ) : (
    method
  );
}

function methodText(row: Activity): ReactNode {
  if (!row.method) return blank;
  return <MethodText method={row.method} approach={row.market_approach} />;
}

// The rows a mark's count word counts, for its tooltip: one sentence that says what it counts, by its mark, and lists
// their references.
function Counted({ rows, mark }: { rows: Activity[]; mark: Mark }) {
  const template = words.explain.countedBy[mark];
  return <ListedRefs template={rows.length === 1 ? template.one : template.many} refs={rows.map((row) => row.activity_reference_no)} end={words.explain.countedEnd} />;
}

// The finding. Each count word marks the rows it counts with tint and moves focus to the first one's reference (ticket
// 100; DESIGN.md section 5, Plan check table), and its tooltip says so.
function Finding({ result, onMark }: { result: CheckedPlan; onMark?: (mark: Mark) => void }) {
  const { needs_a_look: look, watch, data_note: notes } = result.counts;
  const moved = result.counts.moved_on ?? 0;
  const f = words.finding;
  const word = (count: number, mark: Mark, capital: boolean) => {
    const what = checked(result, <Counted mark={mark} rows={result.rows.filter((row) => row.marks.some((m) => m.mark === mark))} />);
    const check: NumCheck =
      onMark && count > 0 ? { ...what, onOpen: () => onMark(mark), act: count === 1 ? copy.num.act.markOne : copy.num.act.mark, opens: "rows" } : what;
    return <Num count={count} capital={capital} check={check} />;
  };
  // In the public view of a project still under way the server sent no signal, and the finding says why (ticket 40).
  const first = result.withheld ? f.withheld : look && watch ? f.lookAndWatch(look, watch) : look ? f.lookOnly(look) : watch ? f.watchOnly(watch) : f.none;
  return (
    <>
      <Fill template={first} slots={{ look: word(look, "needs_a_look", true), watch: word(watch, "watch", false) }} />
      {moved > 0 && <Fill template={f.movedOn(moved)} slots={{ moved: word(moved, "moved_on", false) }} />}
      {notes > 0 && <Fill template={f.notes(notes)} slots={{ notes: word(notes, "data_note", false) }} />}
      {f.end}
    </>
  );
}

// How I checked and how I measure delay: "I checked every activity against its own dates, ... because each plan update
// can move the planned dates." Since ticket 126 it opens the "What Prism found" column's window, since a reader who
// questions a delay opens that column, and no longer sits under the finding.
function MethodSentence({ result }: { result: CheckedPlan }) {
  const phrases = result.checks_run.map((check) => words.checks[check as keyof typeof words.checks]).filter(Boolean);
  return result.baseline ? (
    <Fill template={words.methodBaseline} slots={{ checks: <Joined items={phrases} />, baseline_date: day(result.baseline.plan_date) }} />
  ) : (
    <Fill template={words.method} slots={{ checks: <Joined items={phrases} /> }} />
  );
}

// What stays under the finding: a check I could not run on this plan, and how many activities I could not check fully.
// Both change what the finding covers, so they stay on first sight; with neither, nothing shows.
function methodNotes(result: CheckedPlan): boolean {
  return !result.checks_run.includes("closing_date") || result.counts.not_fully_checked > 0;
}

function Method({ result }: { result: CheckedPlan }) {
  const partly = result.counts.not_fully_checked;
  const notes = [
    !result.checks_run.includes("closing_date") && words.noClosingDate,
    partly > 0 && <Fill key="partial" template={words.partial(partly)} slots={{ count: formatCount(partly) }} />,
  ].filter(Boolean);
  return (
    <p className="text-body text-ink" data-method>
      {notes.map((note, index) => (
        <Fragment key={index}>
          {index > 0 && " "}
          {note}
        </Fragment>
      ))}
    </p>
  );
}

function Definition({ result, triggerClassName }: { result: CheckedPlan; triggerClassName?: string }) {
  const limits = result.thresholds;
  return (
    <DefinitionWindow label={words.columns.found} title={words.columns.found} triggerClassName={triggerClassName}>
      <p data-method-sentence>
        <MethodSentence result={result} />
      </p>
      <p className="mt-2">
        <Fill
          template={words.foundDefinition}
          slots={{
            lookRule: <Fill template={words.lookRule} slots={{ amount: formatAmountText(Number(limits.completion_passed_min_estimated_usd)) }} />,
            watchRule: (
              <Fill
                template={words.watchRule}
                slots={{ days: whole(limits.days_before_closing), ratio: formatNumber(Number(limits.actual_to_estimate_ratio)) }}
              />
            ),
          }}
        />
      </p>
    </DefinitionWindow>
  );
}

// The fold's sentence: the references when there are a few, else how many. The count is
// check_plan's (counts.unmarked); the rows only give the references.
// In a view that holds back signals on a project still under way (ticket 40), an unmarked activity may still have one, so
// the sentence says only that it has no data notes.
function FoldSentence({ rows, unmarked, id, withheld = false }: { rows: Activity[]; unmarked: number; id: string; withheld?: boolean }) {
  const fold = withheld ? words.foldWithheld : words.fold;
  const count = formatCount(unmarked, { capital: true });
  // Each reference stays whole on one line when it fits there.
  const refs = rows.map((row) => <span className="inline-block max-w-full wrap-anywhere font-mono">{row.activity_reference_no}</span>);
  return (
    <p id={id} className="text-small text-ink-muted">
      {unmarked <= words.fold.listUpTo ? (
        <Fill template={fold.listed(unmarked)} slots={{ count, refs: <Joined items={refs} /> }} />
      ) : (
        <Fill template={fold.counted} slots={{ count }} />
      )}
    </p>
  );
}

function FoldButton({ count, open, controls, describedBy, onToggle }: {
  count: number;
  open: boolean;
  controls: string;
  describedBy: string;
  onToggle: () => void;
}) {
  return (
    <Button
      variant="ghost"
      flush
      onPage
      aria-expanded={open}
      aria-controls={controls}
      aria-describedby={describedBy}
      onClick={onToggle}
    >
      {open ? words.fold.hide(count) : words.fold.show(count)}
    </Button>
  );
}

// The table's columns (DESIGN.md section 5, Plan check table; ticket 100). All six from a table frame of 60rem (the
// plan container, inside the window's margins: a 1280 or 1440 px window with the rail); three below it, Activity,
// Estimated (US$) and What Prism found, since a row's records show the rest in the drawer: a 1024 px window with
// the rail, or a wide window beside the drawer; and cards below 34rem (app.css, --container-plan-six and
// --container-plan-cards). Estimated (US$) keeps a fixed 9rem, so "232,524,000.00" never wraps; Activity and What
// Prism found share what is left in three columns. Each width is measured on the real and the longest values in
// the fixture, so no word in a cell breaks inside itself (web/tests/check-plan.spec.ts).
const SIX = "hidden @plan-six/plan:table-cell";
const COLUMNS: { key: string; header: ReactNode; width: string; numeric?: boolean; six?: boolean }[] = [
  // In three columns Activity takes 40 percent, so beside the drawer at 1440 px with the sidebar open (576 px) a
  // 22-character reference keeps one line (ticket 100's design review, item 12).
  { key: "activity", header: words.columns.activity, width: "w-[40%] @plan-six/plan:w-[26%]" },
  { key: "method", header: words.columns.method, width: "@plan-six/plan:w-[16%]", six: true },
  { key: "review", header: words.columns.review, width: "@plan-six/plan:w-[8%]", six: true },
  { key: "estimated", header: words.columns.estimated, width: "w-36", numeric: true },
  { key: "status", header: words.columns.status, width: "@plan-six/plan:w-[13%]", six: true },
  { key: "found", header: null, width: "" },
];
// Cells are padded 12 px, and the row's first and last cells 24 px at the panel's edges, where the zone's name and its
// foot strip start.
const CELL = "px-3 py-3 first:pl-6 last:pr-6";
const columnClass = (column: (typeof COLUMNS)[number]) => cx(CELL, column.six && SIX);

// Each activity's links (ticket 22; the 22 brief, section 5.1): "Open the activity" to its contract trail, then
// "See the past range" to its package workspace (the 12 brief), 16 px apart and wrapping. Each accessible name
// adds the reference, so a list of links tells the activities apart, and starts with the visible words (WCAG
// 2.5.3). Every row gets both: a row with no public notice opens the workspace's "not measurable" state, which
// says why. The public view has no Packages tab, so it shows only the first. Since ticket 100 a row shows only "See
// the past range", and its records in the drawer show both.
export function ActivityLinks({ reference, pid, rangeOnly = false, className }: { reference: string; pid: string; rangeOnly?: boolean; className?: string }) {
  // The past range opens the package page, which the view the server applied may hide (the roles file's [views]).
  const showsPackage = useShows("package");
  if (rangeOnly && !showsPackage) return null;
  return (
    <span className={cx("flex flex-wrap gap-x-4 text-small font-normal", className)}>
      {!rangeOnly && (
        <TextLink href={`/projects/${pid}/packages/${encodeURIComponent(reference)}`} aria-label={words.openActivityLabel(reference)} data-activity-link={reference}>
          {words.openActivity}
        </TextLink>
      )}
      {showsPackage && (
        <TextLink href={`/packages/${encodeURIComponent(reference)}`} aria-label={words.pastRangeLabel(reference)} data-past-range-link={reference}>
          {words.pastRangeLink}
        </TextLink>
      )}
    </span>
  );
}

// "Re-estimated in this version": the caption at the end of a changed row's Activity cell (ticket 21),
// which ties the row to the change list under the plan check. It is text, never a badge.
function ChangedLine({ change }: { change?: keyof typeof copy.changes.cell }) {
  if (!change) return null;
  return (
    <span className="mt-1 block text-caption text-ink-muted" data-changed={change}>
      <Unbroken text={copy.changes.cell[change]} />
    </span>
  );
}

// A row's key, and the id a link's hash names: its STEP reference, or its place in an upload with no reference yet.
export const rowKey = (row: Activity) => row.activity_reference_no ?? `row-${row.position}`;

// The drawer's id for a row's records (lib/planRows.ts): the plan row's own evidence id, or the row's key in an upload.
const recordsId = (row: Activity) => planRowCheckId(row.evidence_id || rowKey(row));

// The row's records, as the drawer shows them (PlanRowRecords.tsx): the row and the check it belongs to.
export function rowRecords(row: Activity, result: CheckedPlan): EvidenceEvent {
  return { id: recordsId(row), kind: "plan-row-check", tool: "check_plan", stratum: "What", short_name: null, row: { activity: row, result }, highlights: [] };
}

// An upload's row with no reference yet says so where the reference goes, and one no published plan lists says that
// under its Description (ticket 38; the 38 brief, 3.4). A published plan's rows have neither.
function UploadLines({ row }: { row: Activity }) {
  return row.listed === false ? (
    <span className="mt-1 block text-caption text-ink-muted" data-new-activity>
      {copy.uploadCheck.newActivity}
    </span>
  ) : null;
}

// How a row is marked: the current mark while the drawer shows its records, the tint of a row a count word counted,
// or of a row a link's hash named (DESIGN.md: tint, Selected row; app.css, "The plan check's marked rows").
type RowMark = "open" | "counted" | "named" | undefined;

type RowProps = {
  row: Activity;
  result: CheckedPlan;
  fresh?: boolean;
  mark?: RowMark;
  change?: keyof typeof copy.changes.cell;
  onOpen: (row: Activity, element: HTMLElement) => void;
};

// The row's reference: a button that opens its records in the drawer, with aria-expanded while they show. A row with
// no reference yet, as in an upload, says so instead.
function Reference({ row, open, onOpen }: { row: Activity; open: boolean; onOpen: (row: Activity, element: HTMLElement) => void }) {
  const ref = row.activity_reference_no;
  if (!ref) return <span className="block text-small text-ink-muted">{copy.uploadCheck.noRef}</span>;
  return (
    <button
      type="button"
      data-row-ref={rowKey(row)}
      aria-expanded={open}
      aria-haspopup="dialog"
      onClick={(event) => onOpen(row, event.currentTarget)}
      className={cx(
        "inline cursor-pointer py-1 text-left font-mono font-medium wrap-break-word text-primary underline decoration-1 underline-offset-3",
        "transition-paint duration-150 hover:text-link-hover active:text-primary-pressed",
      )}
    >
      {/* A parent's underline never reaches inside the parts' inline blocks, so each part draws its own: the reference
          is a text link to the row's records (DESIGN.md section 10; ticket 100's design review, item 1). */}
      <MonoWords text={ref} medium className="underline decoration-1 underline-offset-3" />
    </button>
  );
}

// Under a reference that breaks STEP's form and that the plan reader kept as it read it (ticket 131), so the reader
// knows the odd characters come from the plan, not from Prism.
function AsRead({ row }: { row: Activity }) {
  return row.reference_as_read ? <span className="block text-small text-ink-muted">{words.referenceAsRead}</span> : null;
}

function Found({ row, result }: { row: Activity; result: CheckedPlan }) {
  return row.marks.length > 0 ? (
    <div className="flex flex-col gap-3">
      {row.marks.map((mark) => (
        <div key={mark.mark} className="flex flex-col items-start gap-1">
          <StatusBadge kind={BADGE[mark.mark]} />
          <MarkReasons mark={mark} result={result} />
        </div>
      ))}
    </div>
  ) : (
    <p className="text-small text-ink-muted">{result.withheld ? words.noDataNotes : words.noSignals}</p>
  );
}

function TableRow({ row, result, fresh, mark, change, onOpen }: RowProps) {
  const ref = row.activity_reference_no;
  return (
    <tr id={rowKey(row)} data-named={mark === "named" || undefined} data-row-mark={mark} className={cx("border-t border-line align-top", fresh && "animate-fade-in")}>
      <th scope="row" tabIndex={-1} data-activity={rowKey(row)} className={cx(CELL, "text-left font-normal focus-visible:outline-offset-[-2px]")}>
        <Reference row={row} open={mark === "open"} onOpen={onOpen} />
        <AsRead row={row} />
        {row.description && <span className="mt-1 block text-small text-ink">{row.description}</span>}
        <UploadLines row={row} />
        <ChangedLine change={change} />
        {ref && row.listed !== false && <ActivityLinks reference={ref} pid={result.plan.project_id} rangeOnly className="mt-1" />}
      </th>
      <td className={columnClass(COLUMNS[1])}>{methodText(row)}</td>
      <td className={columnClass(COLUMNS[2])}>{row.review_type ?? blank}</td>
      <td className={cx(CELL, "text-right whitespace-nowrap tabular-nums")}>{row.estimated_amount_usd ? amount(row.estimated_amount_usd) : blank}</td>
      <td className={columnClass(COLUMNS[4])}>{row.process_status ?? blank}</td>
      <td className={CELL}>
        <Found row={row} result={result} />
      </td>
    </tr>
  );
}

// An activity card below a frame of 34rem: the badges and the reference as its heading, so a screen reader's list of
// headings says "Needs a look KE-NWWDA-541055-CW-RFB"; then the Description, the reasons, a hairline and the four
// STEP fields. Method and Process status take the card's full width, since STEP's values, such as "Pending
// Implementation", are wider than a 120 px column; Review and the amount share a row.
function ActivityCard({ row, result, fresh, mark, change, onOpen }: RowProps) {
  const ref = row.activity_reference_no;
  const field = (label: ReactNode, value: ReactNode, wide?: boolean, numeric?: boolean) => (
    <div className={cx(CARD_FIELD, wide && "col-span-full")}>
      <dt className="text-caption text-ink-muted">{label}</dt>
      <dd className={cx("text-small text-ink", numeric ? "whitespace-nowrap tabular-nums" : "wrap-break-word")}>{value}</dd>
    </div>
  );
  return (
    <li data-row-mark={mark} className={cx("rounded-md border border-line p-4", mark ? "bg-tint" : "bg-surface", fresh && "animate-fade-in")}>
      <article>
        <h3 className="flex flex-col items-start gap-2 text-small">
          {row.marks.map((mark) => (
            <StatusBadge key={mark.mark} kind={BADGE[mark.mark]} />
          ))}
          <span tabIndex={-1} data-activity={rowKey(row)} className="text-ink-heading">
            <Reference row={row} open={mark === "open"} onOpen={onOpen} />
          </span>
        </h3>
        <AsRead row={row} />
        {/* The Description in ink-muted and the reasons in ink, so the reason under it reads as the finding (ticket 59). */}
        {row.description && <p className="mt-1 text-small text-ink-muted">{row.description}</p>}
        <UploadLines row={row} />
        <ChangedLine change={change} />
        <div className="mt-2 flex flex-col gap-2">
          {row.marks.length > 0 ? (
            row.marks.map((mark) => <MarkReasons key={mark.mark} mark={mark} result={result} />)
          ) : (
            <p className="text-small text-ink-muted">{result.withheld ? words.noDataNotes : words.noSignals}</p>
          )}
        </div>
        <dl className={cx("mt-3 border-t border-line pt-3", CARD_FIELDS)} data-numbers>
          {field(words.columns.method, methodText(row), true)}
          {field(words.columns.review, row.review_type ?? blank)}
          {field(words.columns.estimated, row.estimated_amount_usd ? amount(row.estimated_amount_usd) : blank, false, true)}
          {field(words.columns.status, row.process_status ?? blank, true)}
        </dl>
        {ref && row.listed !== false && <ActivityLinks reference={ref} pid={result.plan.project_id} rangeOnly className="mt-3" />}
      </article>
    </li>
  );
}

function hashReference(): string | null {
  try {
    const hash = decodeURIComponent(window.location.hash.slice(1));
    return hash || null;
  } catch {
    return null;
  }
}

// The one place an activity shows at this width: its table row header or its card's reference.
function visibleActivity(ref: string): HTMLElement | null {
  const found = Array.from(document.querySelectorAll<HTMLElement>("[data-activity]")).filter(
    (element) => element.dataset.activity === ref && element.getClientRects().length > 0,
  );
  return found[0] ?? null;
}

// The reference button of a row at this width: in its table row or on its card.
function visibleReference(key: string): HTMLElement | null {
  const found = Array.from(document.querySelectorAll<HTMLElement>("[data-row-ref]")).filter(
    (element) => element.dataset.rowRef === key && element.getClientRects().length > 0,
  );
  return found[0] ?? null;
}

// The space left above a named activity when the page lands on it: the cards' own gap, so the line
// above a card lands just past the edge instead of leaving a sliver of it in view. A table's rows touch, so a row
// lands right at the edge, and the row above it leaves the screen whole (ticket 100).
const landingGap = (activity: Element) => (activity.tagName === "TR" ? 0 : 12);

// The block on screen just above an element in the page's order: the row or card before it, or for the
// first card the count line's row, skipping the view this width hides.
function blockAbove(element: Element): Element | null {
  for (let at: Element | null = element; at && at.tagName !== "MAIN"; at = at.parentElement) {
    let before = at.previousElementSibling;
    while (before && before.getClientRects().length === 0) before = before.previousElementSibling;
    if (before) return before;
  }
  return null;
}

// Brings a named activity into view without cutting the navy bar or the page's title at the top
// edge: the page from its top when the activity fits on the first screen, or else the activity just
// under the sticky parts. The activity is its whole row or card, badges included, not only the
// reference that takes focus. The bar, below 1024 px where it does not stick, and the title are each
// shown whole when the activity still fits under them, and otherwise scrolled away whole. From 1024 px
// the bar sticks (ticket 93), so the activity lands under it, and under the head too where the head sticks
// (from 50rem of window height, ticket 100).
function bringIntoView(target: HTMLElement) {
  const place = (element: Element) => {
    const rect = element.getBoundingClientRect();
    return { top: rect.top + window.scrollY, bottom: rect.bottom + window.scrollY };
  };
  const activity = target.closest("tr, li") ?? target;
  const row = place(activity);
  const stuckHeight = (element: HTMLElement | null) => (sticks(element) ? element.offsetHeight : 0);
  const bar = document.querySelector<HTMLElement>("[data-nav-bar]")?.closest("header") ?? null;
  const barStuck = stuckHeight(bar);
  const header = document.querySelector<HTMLElement>("[data-plan-header]");
  const stuck = barStuck + stuckHeight(header);
  const gap = landingGap(activity);
  const fits = (from: number) => row.bottom + gap - from <= window.innerHeight;
  let top = fits(0) ? 0 : row.top - stuck - gap;
  // A block that sits closer above the activity than the gap, as the count line's row sits 8 px above the
  // first card, lands just past the edge too, so none of its lines is left as a sliver (ticket 90: the
  // caption's 20 px line left one pixel of it in view).
  const above = top > 0 ? blockAbove(activity) : null;
  if (above) {
    const { bottom } = place(above);
    if (bottom > top + stuck && bottom < row.top) top = bottom - stuck;
  }
  // Near the page's end the window cannot scroll that far, and the row above would be left cut under the parts that
  // stick. Then the nearest row above that the window can reach lands at the edge instead, and the activity stays in
  // view under it (ticket 100).
  const furthest = document.documentElement.scrollHeight - window.innerHeight;
  if (top > furthest) {
    // The rows or cards that show before the activity, its fold's included, nearest first.
    const blocks = Array.from(activity.closest("[data-view]")?.querySelectorAll("tbody > tr, ul > li") ?? []).filter(
      (block) => block.getClientRects().length > 0,
    );
    const before = blocks.slice(0, blocks.indexOf(activity)).reverse();
    const reachable = before.map((block) => place(block).top - stuck - landingGap(block)).find((edge) => edge <= furthest);
    top = reachable ?? 0;
  }
  // A title inside the sticky header, and a bar that sticks, stay in view whatever the page does. The edge a part
  // could be cut at is the sticking bar's foot, or the window's top.
  const parts = [barStuck ? null : bar, stuck > barStuck ? null : document.querySelector("main h1")];
  for (const part of parts) {
    if (!part) continue;
    const { top: partTop, bottom: partBottom } = place(part);
    const edge = top + barStuck;
    if (edge > partTop && edge < partBottom) top = (fits(partTop - barStuck) ? partTop : partBottom) - barStuck;
  }
  window.scrollTo({ top: Math.max(0, top) });
}

// A landing aims once, and a later change of layout, such as the fonts arriving on a slow connection or the floating ask
// bar taking its height, can move the row after it and leave it cut under the parts that stick. So for a second after a
// landing, the row is aimed again once the fonts have loaded and whenever it moves on the page. The reader's own scroll,
// key or touch ends this at once, so it never fights them (ticket 59; the design review of round 1, follow-up 2).
const SETTLE_MS = 1000;
function landAndHold(target: HTMLElement): () => void {
  const at = () => Math.round(target.getBoundingClientRect().top + window.scrollY);
  bringIntoView(target);
  let last = at();
  let done = false;
  const again = () => {
    if (done || !target.isConnected) return;
    const now = at();
    if (now === last) return;
    last = now;
    bringIntoView(target);
  };
  const watch = new ResizeObserver(again);
  watch.observe(document.documentElement);
  void document.fonts?.ready.then(again);
  const stop = () => {
    done = true;
    watch.disconnect();
    clearTimeout(timer);
    for (const kind of ["wheel", "touchstart", "keydown", "pointerdown"]) window.removeEventListener(kind, stop, true);
  };
  const timer = setTimeout(stop, SETTLE_MS);
  for (const kind of ["wheel", "touchstart", "keydown", "pointerdown"]) window.addEventListener(kind, stop, { capture: true, passive: true });
  return stop;
}

export function PlanCheckHeader({ agency, plan, pill, action, feedforward, level = 1, sticky = false, rule = true }: {
  agency: ReactNode;
  // "Procurement Plan of October 9, 2026", when the plan is known.
  plan?: ReactNode;
  pill?: ReactNode;
  // Ticket 35's slot to the right of the pill: "Draft review notes (3 rows)", with its feedforward
  // caption right-aligned on the subtitle's line. Below 1024 px they follow the pill, 8 px apart.
  action?: ReactNode;
  feedforward?: ReactNode;
  // The page's h1. The design gallery shows it one level down, under its own h1, and not sticky.
  level?: 1 | 2;
  // Whether it sticks under the bar where the window allows (app.css, head-sticks). It sticks only while it holds the
  // page's one action (DESIGN.md section 5, Page head; ticket 100), so it does not unless a caller with an action asks.
  sticky?: boolean;
  // The hairline under the head. A failed check draws nothing under its head, so it has none (ticket 100).
  rule?: boolean;
}) {
  return (
    <div
      data-plan-header
      data-sticky={sticky ? "top" : undefined}
      className={cx("bg-page pt-2 pb-4", rule && "border-b border-line", sticky && "head-sticks:@head/page:sticky head-sticks:@head/page:top-(--frame-top) head-sticks:@head/page:z-10")}
    >
      {/* The title block sits beside the actions block from a page area of 46rem, so a page the drawer narrows stacks
          them (DESIGN.md section 4, Page layouts; ticket 94). Only those two blocks stack: the pill and the action keep
          one row that wraps, their centres level (ticket 100, from ticket 94's critique). */}
      <div className="flex flex-col gap-3 @head/page:flex-row @head/page:items-start @head/page:justify-between @head/page:gap-6">
        {/* The name's column takes the row's free width, so a skeleton bar sized as a share of it
            is as wide as the name it stands for. The agency's name wraps in full, however long. */}
        <div className="min-w-0 @head/page:flex-1">
          {createElement(`h${level}`, { tabIndex: -1, className: "text-h1 wrap-break-word text-ink-heading focus:outline-none" }, agency)}
          {plan && <p className="mt-2 text-body text-ink-muted">{plan}</p>}
        </div>
        {(pill || action) && (
          <div className="flex min-w-0 flex-col items-start gap-2 @head/page:shrink-0 @head/page:items-end">
            <div data-head-actions className="flex flex-wrap items-center gap-x-3 gap-y-2 @head/page:justify-end">
              {pill}
              {action}
            </div>
            {feedforward}
          </div>
        )}
      </div>
    </div>
  );
}

// "Procurement Plan of October 9, 2026", with the date on one line, as every sentence date is.
export function planSubtitle(planDate: string): ReactNode {
  return <Fill template={words.subtitle} slots={{ date: day(planDate) }} />;
}

export function checkPill(result: CheckedPlan): ReactNode {
  const { activities, checked } = result.counts;
  return (
    <CheckPill>
      {checked === activities ? words.pill(activities, formatCount(activities, { capital: true })) : words.pillPartial(whole(checked), whole(activities))}
    </CheckPill>
  );
}

// The activities panel's name and its count line, the same while the check loads and once it is ready, so nothing
// under them moves when the rows arrive.
function ActivitiesZone({ id, tag, busy, children }: { id?: string; tag?: ReactNode; busy?: boolean; children: ReactNode }) {
  return (
    <TaskZone panel name={words.activitiesTitle} headingId={id} tag={tag} busy={busy} sectionKey="activities">
      {children}
    </TaskZone>
  );
}

export function PlanCheck({ result, findingRef, defaultOpen = false, afterMethod, changed = {}, after, method, source, reveal = false, howChecked }: {
  result: CheckedPlan;
  // Ticket 130: "How I checked" (HowIChecked.tsx), beside the finding in columns 9 to 12 from a page area of 75rem, and
  // after the activities below it, so the first marked row stays in the first screen at 1024 by 768. It renders in one
  // place only, so the reading order is the finding, how it was checked, then the activities, or the rows first.
  howChecked?: ReactNode;
  // Ticket 111: the finding replaces a narration that showed for at least 400 ms, so its byline, the finding and the
  // method sentence enter, once: opacity and a 4 px rise over 200 ms.
  reveal?: boolean;
  // Ticket 38: an upload's check says how it measured delay, and names the upload as its source.
  method?: ReactNode;
  source?: ReactNode;
  findingRef?: Ref<HTMLHeadingElement>;
  // The gallery shows the fold open; the page opens it from a link's hash.
  defaultOpen?: boolean;
  // Ticket 21: the change line, under the method sentence it qualifies.
  afterMethod?: ReactNode;
  // Ticket 21: the rows this version changed since the one before, by STEP reference.
  changed?: Record<string, keyof typeof copy.changes.cell>;
  // The zones after the activities: "What changed" as a closed row and the baseline as a row (ticket 100).
  after?: ReactNode;
}) {
  const findingId = useId();
  const zoneId = useId();
  const foldId = useId();
  const foldCardsId = useId();
  const sentenceId = useId();
  const cardSentenceId = useId();
  const [open, setOpen] = useState(defaultOpen);
  const [opened, setOpened] = useState(false);
  const [named, setNamed] = useState<string | null>(null);
  // The mark whose count word was pressed last, and how many times, so pressing it again moves focus again.
  const [counted, setCounted] = useState<{ mark: Mark; times: number } | null>(null);
  // The records the drawer shows now, from the address (lib/evidence.ts).
  const drawer = evidenceIn(useStore(address).search);

  const ordered = result.rows
    .map((row, index) => ({ row, index }))
    .filter(({ row }) => row.marks.length > 0)
    .sort((a, b) => Math.min(...a.row.marks.map((m) => RANK[m.mark])) - Math.min(...b.row.marks.map((m) => RANK[m.mark])) || a.index - b.index)
    .map(({ row }) => row);
  // The rows with no signals, to render in the fold. How many there are is the tool's count.
  const unmarkedRows = result.rows.filter((row) => row.marks.length === 0);
  const { activities, marked, unmarked } = result.counts;

  const toggle = () => {
    setOpen((now) => !now);
    setOpened(true);
  };

  // Each row's records are held on the page, so the drawer opens at once and a link to it shows them once the check
  // has loaded (lib/planRows.ts).
  useEffect(() => {
    for (const row of result.rows) remember(rowRecords(row, result));
  }, [result]);

  // A link whose hash names an activity: open the fold if the activity is in it, then bring the
  // activity into view and focus it.
  useEffect(() => {
    let stop = () => {};
    const follow = () => {
      const ref = hashReference();
      if (!ref || !result.rows.some((row) => rowKey(row) === ref)) return;
      setNamed(ref);
      if (unmarkedRows.some((row) => rowKey(row) === ref)) setOpen(true);
      requestAnimationFrame(() => {
        const target = visibleActivity(ref);
        if (!target) return;
        stop();
        stop = landAndHold(target);
        target.focus({ preventScroll: true });
      });
    };
    follow();
    window.addEventListener("hashchange", follow);
    return () => {
      stop();
      window.removeEventListener("hashchange", follow);
    };
    // The rows are fixed for a result, so following once per result is enough.
  }, [result]);

  // A count word in the finding marks the rows it counts and moves focus to the first one's reference, brought into
  // view under the parts that stick (ticket 100). The rows it counts are marked rows, so none is in the fold.
  useEffect(() => {
    if (!counted) return;
    const first = ordered.find((row) => row.marks.some((mark) => mark.mark === counted.mark));
    if (!first) return;
    const frame = requestAnimationFrame(() => {
      const target = visibleReference(rowKey(first));
      if (!target) return;
      bringIntoView(target);
      target.focus({ preventScroll: true });
    });
    return () => cancelAnimationFrame(frame);
  }, [counted]);

  const openRecords = (row: Activity, element: HTMLElement) => {
    const records = rowRecords(row, result);
    remember(records);
    openEvidence(records.id, { serial: null, sentence: null, marker: element, runId: null });
  };
  const markOf = (row: Activity): RowMark =>
    drawer === recordsId(row)
      ? "open"
      : counted && row.marks.some((mark) => mark.mark === counted.mark)
        ? "counted"
        : named === rowKey(row)
          ? "named"
          : undefined;
  const rowProps = (row: Activity) => ({ row, result, mark: markOf(row), change: changed[row.activity_reference_no], onOpen: openRecords });

  // An upload's own method sentence (ticket 38), or the notes that change what the finding covers.
  const notes = method ?? (methodNotes(result) ? <Method result={result} /> : null);
  const root = useRef<HTMLElement>(null);
  const wide = usePageAtLeast(root, 75);
  const beside = howChecked != null && wide;

  return (
    <section ref={root} aria-labelledby={findingId} data-plan-check>
      {/* Columns 1 to 8 as EightColumns draws them, or 1 to 7 with "How I checked" in 9 to 12 beside them; the row holds
          at least the panel's height, as the skeleton's does, so the activities stay put when the check arrives. */}
      <div className={cx("layout-grid mt-6", beside && HOW_CHECKED_ROW)}>
        <div className={cx("min-w-0 max-w-[72ch]", beside ? "col-span-7" : "col-span-12 @lg/page:col-span-8")}>
        {/* The finding's block keeps its byline's kind as data only: "found", or "heldBack" over the public view's
            finding, which holds the signals back (tickets 111 and 126; DESIGN.md section 5, Byline). Its 16 px foot is
            the room the narration's slow line takes while the check runs, so the panel under it never moves. */}
        <div data-finding-block data-byline={result.withheld ? "heldBack" : "found"} className={cx("pb-4", reveal && "animate-reveal")}>
          {/* The page's finding, in the finding style (ticket 100): a count word's tooltip opens under all of it
              (DESIGN.md, Number tooltip), and a press marks the rows it counts. */}
          <h2 ref={findingRef} id={findingId} tabIndex={-1} className="text-finding text-pretty text-ink-heading focus:outline-none" data-finding>
            <Finding result={result} onMark={(mark) => setCounted((now) => ({ mark, times: (now?.times ?? 0) + 1 }))} />
          </h2>
          {notes && <div className="mt-4">{notes}</div>}
        </div>
        {afterMethod}
        </div>
        {beside && <div className="col-span-4 col-start-9 min-w-0">{howChecked}</div>}
      </div>

      <div className="mt-8">
        {/* No count line: the fold row "Three more activities have no signals: ... Show them" says what is hidden
            (ticket 126). */}
        <ActivitiesZone id={zoneId}>
          {/* The table and the cards each read the plan container's width, which the evidence drawer narrows. */}
          <div data-zone-table className="@container/plan">
            {/* The frame keeps the row header's focus ring inside the panel. */}
            <div data-view="table" className="hidden overflow-hidden @plan-cards/plan:block">
              <table className="w-full table-fixed border-collapse text-small">
                <caption className="sr-only">{words.caption(result.plan.implementing_agency, formatDate(result.plan.plan_date))}</caption>
                <thead className="bg-surface-2">
                  <tr>
                    {COLUMNS.map((column) => (
                      <th
                        key={column.key}
                        scope="col"
                        className={cx(columnClass(column), "align-bottom font-semibold text-ink-heading", column.numeric ? "text-right" : "text-left", column.width)}
                      >
                        {column.key === "found" ? <Definition result={result} /> : column.header}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {ordered.map((row) => (
                    <TableRow key={rowKey(row)} {...rowProps(row)} />
                  ))}
                  {/* The fold's row spans the columns that show: a cell that spanned six while three show would add
                      three empty columns to the table's layout, so each count of columns has its own row, and only
                      one of them shows. */}
                  {unmarked > 0 &&
                    ([6, 3] as const).map((span) => (
                      <tr key={span} className={cx("border-t border-line bg-page", span === 6 ? "hidden @plan-six/plan:table-row" : "@plan-six/plan:hidden")} data-fold>
                        <td colSpan={span} className="px-6 py-2">
                          <div className="flex flex-wrap items-center gap-x-4">
                            <FoldSentence rows={unmarkedRows} unmarked={unmarked} id={`${sentenceId}-${span}`} withheld={Boolean(result.withheld)} />
                            <FoldButton count={unmarked} open={open} controls={foldId} describedBy={`${sentenceId}-${span}`} onToggle={toggle} />
                          </div>
                        </td>
                      </tr>
                    ))}
                </tbody>
                <tbody id={foldId} hidden={!open}>
                  {unmarkedRows.map((row) => (
                    <TableRow key={rowKey(row)} {...rowProps(row)} fresh={opened} />
                  ))}
                </tbody>
              </table>
            </div>

            {/* Below a frame of 34rem the cards have no column heads, so the definition of the marks heads them. */}
            <div data-view="cards" data-zone-inset className="pb-4 @plan-cards/plan:hidden">
              <p className="flex text-caption">
                <Definition result={result} triggerClassName="inline-flex min-h-6 items-center whitespace-nowrap" />
              </p>
              <ul aria-labelledby={zoneId} className="mt-2 flex flex-col gap-3">
                {ordered.map((row) => (
                  <ActivityCard key={rowKey(row)} {...rowProps(row)} />
                ))}
                {unmarked > 0 && (
                  <li className="rounded-md border border-line bg-page p-4" data-fold>
                    <FoldSentence rows={unmarkedRows} unmarked={unmarked} id={cardSentenceId} withheld={Boolean(result.withheld)} />
                    <div className="mt-2">
                      <FoldButton count={unmarked} open={open} controls={foldCardsId} describedBy={cardSentenceId} onToggle={toggle} />
                    </div>
                  </li>
                )}
              </ul>
              <ul id={foldCardsId} hidden={!open} aria-labelledby={zoneId} className="mt-3 flex flex-col gap-3">
                {unmarkedRows.map((row) => (
                  <ActivityCard key={rowKey(row)} {...rowProps(row)} fresh={opened} />
                ))}
              </ul>
            </div>
          </div>
          <FootStrip>
            {source ?? <PlanSource result={result} />}
            <p className="text-caption text-ink-muted" data-not-visible>
              {words.notVisible}
            </p>
          </FootStrip>
        </ActivitiesZone>
        {howChecked != null && !beside && <div className="my-4 max-w-[72ch]">{howChecked}</div>}
        {after}
      </div>
    </section>
  );
}

// The least height of the finding's row while "How I checked" sits beside it, which the skeleton's row holds too, so
// the activities under it never move when the check arrives (ticket 130). It is the panel's height with its three facts
// and a saved baseline at 1280 px (494 px), the narrowest window where it sits beside the finding, and it keeps the
// first marked row in a 1440 by 900 window's first screen; a longer panel grows the row.
const HOW_CHECKED_ROW = "min-h-[31rem]";
// The same least height for the skeleton's row, which reads the page area's width from its container instead of the
// hook. The two must match; Tailwind needs whole class names, so both are written out in full.
const HOW_CHECKED_ROW_LOADING = "@xl/page:min-h-[31rem]";

// The plan's source line: under the activities, and in a row's records in the drawer.
export function PlanSource({ result }: { result: CheckedPlan }) {
  const s = words.source;
  const { plan, project } = result;
  return (
    <Source>
      <Fill
        template={s.plan}
        slots={{
          agency: plan.implementing_agency,
          pid: <ProjectId pid={plan.project_id} />,
          date: day(plan.plan_date),
          disclosed: day(plan.disclosed_on ?? plan.public_from),
        }}
      />
      {project.closing_date && project.record_date && (
        <>
          {" "}
          <Fill template={s.closing} slots={{ date: day(project.record_date) }} />
        </>
      )}{" "}
      <Fill template={s.marks} slots={{ date: day(result.as_of) }} />
      {plan.pdf_url && (
        <>
          {" "}
          <TextLink href={plan.pdf_url} target="_blank" rel="noopener noreferrer">
            {s.open}
            <span className="sr-only">
              {" "}
              {copy.newTab}
            </span>
          </TextLink>
        </>
      )}
    </Source>
  );
}

// A finding as long as most are, "One needs a look and two are worth watching; two have moved on since the plan;
// three have data notes.", from the finding's own templates. It only holds the finding's place, unseen, while the
// check loads. Since ticket 132 a plan the records have moved past says so in its finding, so the typical one does.
function typicalFinding(): string {
  const f = words.finding;
  return (
    fill(f.lookAndWatch(1, 2), { look: formatCount(1, { capital: true }), watch: formatCount(2) }) +
    fill(f.movedOn(2), { moved: formatCount(2) }) +
    fill(f.notes(3), { notes: formatCount(3) }) +
    f.end
  );
}

// While the check loads: the header's places, then the narration in the places of the finding's byline, the
// finding and the method sentence (ticket 111), then the activities panel with its real name and column heads over
// five skeleton rows, or three skeleton cards below a frame of 34rem. Nothing moves when the rows arrive, and nothing
// shimmers.
export function PlanCheckSkeleton({ slow, afterNarration, howChecked = false }: {
  slow?: boolean;
  // The change line under the narration (ticket 59; the critique of round 1): the line itself once what changed has
  // answered, which needs nothing from the check, or its held lines until then, so the panel below stays put.
  afterNarration?: ReactNode;
  // Ticket 130: the page draws "How I checked", so from a page area of 75rem the narration keeps to columns 1 to 7 and
  // the row holds the panel's place in 9 to 12, its labels over value bars; below that the panel follows the activities,
  // so the skeleton holds nothing for it.
  howChecked?: boolean;
}) {
  const rows = [0, 1, 2, 3, 4];
  // The narration (ticket 111): the answer panel's own steps, with one running step and how I check under it, then,
  // after two seconds, why it can take longer. The page's polite status says the step, so the steps announce nothing.
  const narration: Step = {
    key: "check_plan",
    running: copy.steps.tools.check_plan.running(),
    done: "",
    state: "running",
    items: slow ? [copy.steps.tools.check_plan.how, words.databaseStarting] : [copy.steps.tools.check_plan.how],
  };
  return (
    <div data-plan-skeleton>
      {/* EightColumns' columns 1 to 8, or 1 to 7 beside "How I checked"'s place from a page area of 75rem, which holds
          the row's least height as the populated row does (HOW_CHECKED_ROW_LOADING). */}
      <div className={cx("layout-grid mt-6", howChecked && HOW_CHECKED_ROW_LOADING)}>
        <div className={cx("col-span-12 min-w-0 max-w-[72ch] @lg/page:col-span-8", howChecked && "@xl/page:col-span-7")}>
        {/* The narration and the place it holds share one grid cell, so it is exactly as tall as the finding it stands
            for. The place is a typical finding, written from the copy file's templates in the finding's own style and
            never seen or heard, so it takes the lines the real one takes at every width (ticket 59). Its count words
            keep to the line's height (Num). Since ticket 126 the finding has no byline over it and no method sentence
            under it, which moved into the "What Prism found" column's window; the place and the finding's block each
            keep 16 px under the finding, which the narration's slow line fills at 1440 and 390 px. */}
        <div className="grid" data-plan-narration>
          <div aria-hidden="true" className="invisible col-start-1 row-start-1">
            <p className="pb-4 text-finding text-pretty">{typicalFinding()}</p>
          </div>
          <div className="col-start-1 row-start-1">
            <Steps steps={[narration]} announce={false} />
          </div>
        </div>
        {afterNarration}
        </div>
        {howChecked && (
          <div aria-hidden="true" className="hidden min-w-0 @xl/page:col-span-4 @xl/page:col-start-9 @xl/page:block">
            <SidePanel
              title={copy.checkPlan.howChecked.title}
              loading
              facts={[copy.checkPlan.howChecked.method, copy.checkPlan.howChecked.compared, copy.checkPlan.howChecked.baseline].map((label) => ({
                label,
                value: null,
                wide: true,
              }))}
            />
          </div>
        )}
      </div>
      <div className="mt-8">
        <ActivitiesZone busy>
          <div data-zone-table className="@container/plan">
            {/* The real column heads are only places: a screen reader hears the narration's step, not an empty table. */}
            <div aria-hidden="true" className="hidden overflow-hidden @plan-cards/plan:block">
              <table className="w-full table-fixed border-collapse text-small">
                <thead className="bg-surface-2">
                  <tr>
                    {COLUMNS.map((column) => (
                      <th key={column.key} scope="col" className={cx(columnClass(column), "text-left font-semibold text-ink-heading", column.numeric && "text-right", column.width)}>
                        {column.key === "found" ? words.columns.found : column.header}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {rows.map((index) => (
                    <tr key={index} className="h-28 border-t border-line align-top">
                      <td className={CELL}>
                        <SkeletonText widths={["w-4/5", "w-3/5"]} />
                      </td>
                      <td className={columnClass(COLUMNS[1])}>
                        <SkeletonLine width="w-4/5" />
                      </td>
                      <td className={columnClass(COLUMNS[2])}>
                        <SkeletonLine width="w-3/5" />
                      </td>
                      <td className={CELL}>
                        <SkeletonLine width="ml-auto w-4/5" />
                      </td>
                      <td className={columnClass(COLUMNS[4])}>
                        <SkeletonLine width="w-4/5" />
                      </td>
                      <td className={CELL}>
                        <Skeleton className="h-7 w-28 rounded-pill" />
                        <SkeletonText className="mt-1" widths={["w-full", "w-3/5"]} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {/* Each skeleton card has an activity card's places: the badge and the reference, two lines
                of Description (one from a 768 px page area), two of reason, the hairline and the four STEP fields
                under their labels. */}
            <div aria-hidden="true" data-zone-inset className="pb-4 @plan-cards/plan:hidden">
              <div>
                <SkeletonLine className="min-h-6 text-caption" width="w-32" />
              </div>
              <ul data-skeleton-cards className="mt-2 flex flex-col gap-3">
                {[0, 1, 2].map((index) => (
                  <li key={index} className="rounded-md border border-line bg-surface p-4">
                    <div className="flex flex-col items-start gap-2 text-small">
                      <Skeleton className="h-[30px] w-28 rounded-pill" />
                      <SkeletonLine width="w-[190px] max-w-full" />
                    </div>
                    <SkeletonText className="mt-1 text-small @md/page:hidden" widths={["w-full", "w-3/5"]} />
                    <SkeletonLine className="mt-1 hidden text-small @md/page:flex" width="w-4/5" />
                    <SkeletonText className="mt-2 text-small" widths={["w-full", "w-4/5"]} />
                    <dl className={cx("mt-3 border-t border-line pt-3", CARD_FIELDS)}>
                      {[words.columns.method, words.columns.review, words.columns.estimated, words.columns.status].map((label, field) => (
                        <div key={field} className={cx(CARD_FIELD, (field === 0 || field === 3) && "col-span-full")}>
                          <dt className="text-caption text-ink-muted">{label}</dt>
                          <dd>
                            <SkeletonLine className="text-small" width={field === 0 ? "w-4/5" : "w-3/5"} />
                          </dd>
                        </div>
                      ))}
                    </dl>
                    {/* "See the past range", the card's last line. */}
                    <SkeletonLine className="mt-3 text-small" width="w-32" />
                  </li>
                ))}
              </ul>
            </div>
          </div>
          {/* The foot strip's places: the source line's bar, and what Prism cannot see, which reads the same before
              the check arrives, so the panel ends as it will (ticket 100's design review, item 7). */}
          <FootStrip>
            <SkeletonLine className="text-caption" width="w-3/5" />
            <p className="text-caption text-ink-muted" data-not-visible>
              {words.notVisible}
            </p>
          </FootStrip>
        </ActivitiesZone>
      </div>
    </div>
  );
}
