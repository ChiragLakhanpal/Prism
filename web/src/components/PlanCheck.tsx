// The plan check (the 10 brief, section 2): check_plan's result for one Procurement Plan version, as
// a table from 1024 px and as activity cards below it.
//
// - PlanCheckHeader: the agency's name (the h1), the plan's date, and the check pill. From 1024 px
//   it sticks to the top of the window with a hairline under it.
// - PlanCheck: the finding as an h2 in the title token, the method sentence, the count line, the rows
//   in STEP's columns with each mark's badge and reason, the activities with no signals folded
//   behind "Show them", the source line and what Strata cannot see.
// - PlanCheckSkeleton: the same places while the check loads, under the real column heads.
//
// Every number comes from the tool: the counts, the days, the ratio and the amounts. The screen
// writes them (web/src/lib/format.ts) and counts nothing. Marked rows come first, by their strongest
// mark, then in the order check_plan returns them. Each row and each card names its STEP reference
// in data-activity, and an address whose hash names a reference opens the fold if it must, brings
// that activity into view with nothing cut at the top edge, and focuses it (ticket 14 links to plan
// rows this way).
import { createElement, useEffect, useId, useState, type ReactNode, type Ref } from "react";
import { copy } from "../copy";
import type { Activity, CheckPlanResult, Mark, Reason } from "../lib/api";
import { cx } from "../lib/cx";
import { formatAmountText, formatCount, formatDate, formatNumber } from "../lib/format";
import { Button } from "./Button";
import { Byline } from "./Byline";
import { CheckPill } from "./CheckPill";
import { EightColumns } from "./EightColumns";
import { Fill, Joined, Unbroken } from "./Fill";
import { useShows, type View } from "../lib/view";
import { Num } from "./Num";
import { ProjectId } from "./ProjectId";
import { Skeleton, SkeletonLine, SkeletonText } from "./Skeleton";
import { Source } from "./Source";
import { StatusBadge, type BadgeKind } from "./StatusBadge";
import { Steps, type Step } from "./Steps";
import { CARD_BREAKPOINTS, CARD_FIELD, CARD_FIELDS } from "./Table";
import { DefinitionWindow } from "./Term";
import { TextLink } from "./TextLink";

const words = copy.checkPlan;
const VIEW = CARD_BREAKPOINTS.lg;
const BADGE: Record<Mark, BadgeKind> = { needs_a_look: "needs-a-look", watch: "watch", data_note: "data-note" };
const RANK: Record<Mark, number> = { needs_a_look: 0, watch: 1, data_note: 2 };

export type CheckedPlan = CheckPlanResult & {
  plan: NonNullable<CheckPlanResult["plan"]>;
  project: NonNullable<CheckPlanResult["project"]>;
  counts: NonNullable<CheckPlanResult["counts"]>;
};

const whole = (value: number) => formatNumber(value, { compact: false });
const amount = (text: string) => formatNumber(Number(text), { decimals: 2, compact: false });
const day = (iso: string) => <Num date={iso} />;

// A number's tooltip: what it is and the values it comes from, one per line.
function Explain({ lines }: { lines: [ReactNode, ReactNode][] }) {
  return (
    <dl className="flex flex-col gap-1" data-numbers>
      {lines.map(([label, value], index) => (
        <div key={index}>
          <dt className="font-semibold">{label}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  );
}

function Days({ days, lines }: { days: number; lines: [ReactNode, ReactNode][] }) {
  return <Num value={days} options={{ compact: false }} check={{ tooltip: <Explain lines={lines} /> }} />;
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
  const lines = (to: [ReactNode, ReactNode]): [ReactNode, ReactNode][] => [
    [<Fill template={kind === "signing" ? e.baselineSigning : e.baselineCompletion} slots={{ plan: day(found.plan_date) }} />, planned ? day(planned) : ""],
    to,
    [e.daysBetween, whole(days)],
  ];
  const daysNum = (to: [ReactNode, ReactNode]) => <Days days={days} lines={lines(to)} />;
  let sentence: ReactNode = null;
  switch (found.state) {
    case "late":
    case "early":
      sentence = (
        <Fill
          template={b[found.state](days)}
          slots={{ days: daysNum([e.signed, day(reason.signed_on!)]), date: planned ? day(planned) : "" }}
        />
      );
      break;
    case "on_date":
      sentence = b.on_date;
      break;
    case "past":
      sentence = <Fill template={b.past(days)} slots={{ date: planned ? day(planned) : "", days: daysNum([e.asOf, day(result.as_of)]), as_of: day(result.as_of) }} />;
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

// One reason's sentence from the copy file, filled with the tool's values for it.
function ReasonText({ reason, result }: { reason: Reason; result: CheckedPlan }) {
  const r = words.reason;
  const e = words.explain;
  const closingLines = (days: number): [ReactNode, ReactNode][] => [
    // check_plan gives the record's date with every closing date; without one, the line gives the date alone.
    [
      e.closing,
      result.project.record_date ? (
        <Fill template={e.closingRecord} slots={{ date: day(reason.closing_date!), record: day(result.project.record_date) }} />
      ) : (
        day(reason.closing_date!)
      ),
    ],
    [e.asOf, day(result.as_of)],
    [e.daysBetween, whole(days)],
  ];
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
      return <Fill template={r.pending_near_closing(days)} slots={{ days: <Days days={days} lines={closingLines(days)} /> }} />;
    }
    case "pending_on_closing_day":
      return <>{r.pending_on_closing_day}</>;
    case "pending_after_closing":
      return <Fill template={r.pending_after_closing} slots={{ date: day(reason.closing_date!) }} />;
    case "signed_late_over_estimate":
    case "signed_over_estimate": {
      const ratio = (
        <Num
          value={reason.ratio!}
          options={{ compact: false }}
          check={{
            tooltip: (
              <Explain
                lines={[
                  [e.actual, amount(reason.actual_amount_usd!)],
                  [e.estimated, amount(reason.estimated_amount_usd!)],
                  [e.divided, reason.ratio_exact],
                ]}
              />
            ),
          }}
        />
      );
      const slots: Record<string, ReactNode> = { date: day(reason.signed_on!), actual: amount(reason.actual_amount_usd!), ratio };
      if (reason.code === "signed_over_estimate") return <Fill template={r.signed_over_estimate} slots={slots} />;
      const days = reason.days_late!;
      slots.days = (
        <Days
          days={days}
          lines={[
            [e.firstPlannedSigning, <Fill template={e.inPlanOf} slots={{ date: day(reason.planned_signing_on!), plan: day(reason.planned_signing_plan_date!) }} />],
            [e.signed, day(reason.signed_on!)],
            [e.daysBetween, whole(days)],
          ]}
        />
      );
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
    case "no_planned_date":
      return <Fill template={r.no_planned_date} slots={{ step: reason.step }} />;
    case "no_estimate":
      return <>{r.no_estimate}</>;
    default:
      // The registry refuses a reason code config/tools.toml does not list, so none reaches here.
      return null;
  }
}

// One paragraph per mark: its reasons' sentences, in the order check_plan returns them.
function MarkReasons({ mark, result }: { mark: Activity["marks"][number]; result: CheckedPlan }) {
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

// The rows a mark's count word counts, for its tooltip.
function Counted({ rows }: { rows: Activity[] }) {
  return (
    <div>
      <p className="font-semibold">{words.explain.counted}</p>
      <ul className="mt-1 font-mono">
        {rows.map((row) => (
          <li key={row.activity_reference_no}>{row.activity_reference_no}</li>
        ))}
      </ul>
    </div>
  );
}

function Finding({ result }: { result: CheckedPlan }) {
  const { needs_a_look: look, watch, data_note: notes } = result.counts;
  const f = words.finding;
  const word = (count: number, mark: Mark, capital: boolean) => (
    <Num
      count={count}
      capital={capital}
      check={{ tooltip: <Counted rows={result.rows.filter((row) => row.marks.some((m) => m.mark === mark))} /> }}
    />
  );
  // In the public view of a project still under way the server sent no signal, and the finding says why (ticket 40).
  const first = result.withheld ? f.withheld : look && watch ? f.lookAndWatch(look, watch) : look ? f.lookOnly(look) : watch ? f.watchOnly(watch) : f.none;
  return (
    <>
      <Fill template={first} slots={{ look: word(look, "needs_a_look", true), watch: word(watch, "watch", false) }} />
      {notes > 0 && <Fill template={f.notes(notes)} slots={{ notes: word(notes, "data_note", false) }} />}
      {f.end}
    </>
  );
}

function Method({ result }: { result: CheckedPlan }) {
  const phrases = result.checks_run.map((check) => words.checks[check as keyof typeof words.checks]).filter(Boolean);
  const partly = result.counts.not_fully_checked;
  return (
    <p className="text-body text-ink" data-method>
      {result.baseline ? (
        <Fill template={words.methodBaseline} slots={{ checks: <Joined items={phrases} />, baseline_date: day(result.baseline.plan_date) }} />
      ) : (
        <Fill template={words.method} slots={{ checks: <Joined items={phrases} /> }} />
      )}
      {!result.checks_run.includes("closing_date") && (
        <>
          {" "}
          {words.noClosingDate}
        </>
      )}
      {partly > 0 && (
        <>
          {" "}
          <Fill template={words.partial(partly)} slots={{ count: formatCount(partly) }} />
        </>
      )}
    </p>
  );
}

function Definition({ result, triggerClassName }: { result: CheckedPlan; triggerClassName?: string }) {
  const limits = result.thresholds;
  return (
    <DefinitionWindow label={words.columns.found} title={words.columns.found} triggerClassName={triggerClassName}>
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

// The table from 1024 px (the 10 brief, section 2.1, with round 2's design review). At 1024 px a
// 24-character reference (202 px) fits the Activity column, "Limited - National" (116 px) the
// Method column, "Review" and "Prior" the Review column, "2,000,000.00" the Estimated column and
// "Implementation" the Process status column; from 1100 px "Open - International" (132 px) fits
// too. What Strata found keeps the rest and stays the widest column. Cells are padded 8 px at the
// sides from 1024 px and 12 px from 1200 px (CELL).
const COLUMNS: { key: string; header: ReactNode; width: string; numeric?: boolean }[] = [
  { key: "activity", header: words.columns.activity, width: "w-[25%] @xl/page:w-[21.5%]" },
  { key: "method", header: words.columns.method, width: "w-[16%] @xl/page:w-[15%]" },
  { key: "review", header: words.columns.review, width: "w-[7.5%]" },
  { key: "estimated", header: words.columns.estimated, width: "w-[11.5%] @xl/page:w-[11%]", numeric: true },
  { key: "status", header: words.columns.status, width: "w-[14%] @xl/page:w-[12.5%]" },
  { key: "found", header: null, width: "w-[26%] @xl/page:w-[32.5%]" },
];
const CELL = "px-2 py-3 @xl/page:px-3";

// Each activity's links (ticket 22; the 22 brief, section 5.1): "Open the activity" to its contract trail, then
// "See the past range" to its package workspace (the 12 brief), 16 px apart and wrapping. Each accessible name
// adds the reference, so a list of links tells the activities apart, and starts with the visible words (WCAG
// 2.5.3). Every row gets both: a row with no public notice opens the workspace's "not measurable" state, which
// says why. The public view has no Packages tab, so it shows only the first. In a card they sit 12 px under the
// last field, so they don't read as part of the Process status value.
function ActivityLinks({ reference, pid, inCard = false }: { reference: string; pid: string; inCard?: boolean }) {
  // The past range opens the package page, which the view the server applied may hide (the roles file's [views]).
  const showsPackage = useShows("package");
  return (
    <span className={cx(inCard ? "mt-3" : "mt-1", "flex flex-wrap gap-x-4 text-small font-normal")}>
      <TextLink href={`/projects/${pid}/packages/${encodeURIComponent(reference)}`} aria-label={words.openActivityLabel(reference)} data-activity-link={reference}>
        {words.openActivity}
      </TextLink>
      {showsPackage && (
        <TextLink href={`/packages/${encodeURIComponent(reference)}`} aria-label={words.pastRangeLabel(reference)} data-past-range-link={reference}>
          {words.pastRangeLink}
        </TextLink>
      )}
    </span>
  );
}

// A row or card a link's hash names keeps the selected row's tint after focus moves on
// (DESIGN.md: tint, Selected row).
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

// An upload's row with no reference yet says so where the reference goes, and one no published plan lists says that
// under its Description (ticket 38; the 38 brief, 3.4). A published plan's rows have neither.
function UploadLines({ row }: { row: Activity }) {
  return row.listed === false ? (
    <span className="mt-1 block text-caption text-ink-muted" data-new-activity>
      {copy.uploadCheck.newActivity}
    </span>
  ) : null;
}

function TableRow({ row, result, fresh, named, change }: { row: Activity; result: CheckedPlan; fresh?: boolean; named?: boolean; change?: keyof typeof copy.changes.cell }) {
  const ref = row.activity_reference_no;
  return (
    <tr id={rowKey(row)} data-named={named || undefined} className={cx("border-t border-line align-top", named && "bg-tint", fresh && "animate-fade-in")}>
      <th scope="row" tabIndex={-1} data-activity={rowKey(row)} className={cx(CELL, "text-left font-normal focus-visible:outline-offset-[-2px]")}>
        {ref ? (
          <span className="block font-mono font-medium wrap-anywhere text-ink">{ref}</span>
        ) : (
          <span className="block text-small text-ink-muted">{copy.uploadCheck.noRef}</span>
        )}
        {row.description && <span className="mt-1 block text-small text-ink">{row.description}</span>}
        <UploadLines row={row} />
        <ChangedLine change={change} />
        {ref && row.listed !== false && <ActivityLinks reference={ref} pid={result.plan.project_id} />}
      </th>
      <td className={CELL}>{methodText(row)}</td>
      <td className={CELL}>{row.review_type ?? blank}</td>
      <td className={cx(CELL, "text-right tabular-nums")}>{row.estimated_amount_usd ? amount(row.estimated_amount_usd) : blank}</td>
      <td className={CELL}>{row.process_status ?? blank}</td>
      <td className={CELL}>
        {row.marks.length > 0 ? (
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
        )}
      </td>
    </tr>
  );
}

// An activity card below 1024 px: the badges and the reference as its heading, so a screen reader's
// list of headings says "Needs a look KE-NWWDA-541055-CW-RFB"; then the Description, the reasons, a
// hairline and the four STEP fields. Method and Process status take the card's full width, since
// STEP's values, such as "Pending Implementation", are wider than a 120 px column; Review and the
// amount share a row.
function ActivityCard({ row, result, fresh, named, change }: { row: Activity; result: CheckedPlan; fresh?: boolean; named?: boolean; change?: keyof typeof copy.changes.cell }) {
  const ref = row.activity_reference_no;
  const field = (label: ReactNode, value: ReactNode, wide?: boolean) => (
    <div className={cx(CARD_FIELD, wide && "col-span-full")}>
      <dt className="text-caption text-ink-muted">{label}</dt>
      <dd className="text-small wrap-break-word text-ink">{value}</dd>
    </div>
  );
  return (
    <li className={cx("rounded-md border border-line p-4", named ? "bg-tint" : "bg-surface", fresh && "animate-fade-in")}>
      <article>
        <h3 className="flex flex-col items-start gap-2 text-small">
          {row.marks.map((mark) => (
            <StatusBadge key={mark.mark} kind={BADGE[mark.mark]} />
          ))}
          <span tabIndex={-1} data-activity={rowKey(row)} className={cx(ref ? "font-mono font-medium" : "font-normal text-ink-muted", "wrap-anywhere text-ink-heading")}>
            {ref ?? copy.uploadCheck.noRef}
          </span>
        </h3>
        {row.description && <p className="mt-1 text-small text-ink">{row.description}</p>}
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
          {field(words.columns.estimated, row.estimated_amount_usd ? amount(row.estimated_amount_usd) : blank)}
          {field(words.columns.status, row.process_status ?? blank, true)}
        </dl>
        {ref && row.listed !== false && <ActivityLinks reference={ref} pid={result.plan.project_id} inCard />}
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

// The space left above a named activity when the page lands on it: the cards' own gap, so the line
// above a card lands just past the edge instead of leaving a sliver of it in view.
const LANDING_GAP = 12;

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
// the bar sticks (ticket 93), so the activity lands under it and the header both.
function bringIntoView(target: HTMLElement) {
  const place = (element: Element) => {
    const rect = element.getBoundingClientRect();
    return { top: rect.top + window.scrollY, bottom: rect.bottom + window.scrollY };
  };
  const activity = target.closest("tr, li") ?? target;
  const row = place(activity);
  const sticks = (element: HTMLElement | null) => (element && getComputedStyle(element).position === "sticky" ? element.offsetHeight : 0);
  const bar = document.querySelector<HTMLElement>("[data-nav-bar]")?.closest("header") ?? null;
  const barStuck = sticks(bar);
  const header = document.querySelector<HTMLElement>("[data-plan-header]");
  const stuck = barStuck + sticks(header);
  const fits = (from: number) => row.bottom + LANDING_GAP - from <= window.innerHeight;
  let top = fits(0) ? 0 : row.top - stuck - LANDING_GAP;
  // A block that sits closer above the activity than the gap, as the count line's row sits 8 px above the
  // first card, lands just past the edge too, so none of its lines is left as a sliver (ticket 90: the
  // caption's 20 px line left one pixel of it in view).
  const above = top > 0 ? blockAbove(activity) : null;
  if (above) {
    const { bottom } = place(above);
    if (bottom > top + stuck && bottom < row.top) top = bottom - stuck;
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

export function PlanCheckHeader({ agency, plan, pill, action, feedforward, headerRef, level = 1, sticky = true }: {
  agency: ReactNode;
  // "Procurement Plan of October 9, 2026", when the plan is known.
  plan?: ReactNode;
  pill?: ReactNode;
  // Ticket 35's slot to the right of the pill: "Draft review notes (3 rows)", with its feedforward
  // caption right-aligned on the subtitle's line. Below 1024 px they follow the pill, 8 px apart.
  action?: ReactNode;
  feedforward?: ReactNode;
  headerRef?: Ref<HTMLDivElement>;
  // The page's h1. The design gallery shows it one level down, under its own h1, and not sticky.
  level?: 1 | 2;
  sticky?: boolean;
}) {
  return (
    <div
      ref={headerRef}
      data-plan-header
      data-sticky={sticky ? "top" : undefined}
      className={cx("border-b border-line bg-page pt-2 pb-4", sticky && "@lg/page:sticky @lg/page:top-(--frame-top) @lg/page:z-10")}
    >
      {/* The title sits beside the actions from a page area of 46rem, so a page the drawer narrows stacks them
          (DESIGN.md section 4, Page layouts; ticket 94). */}
      <div className="flex flex-col gap-3 @head/page:flex-row @head/page:items-start @head/page:justify-between @head/page:gap-6">
        {/* The name's column takes the row's free width, so a skeleton bar sized as a share of it
            is as wide as the name it stands for. */}
        <div className="min-w-0 @head/page:flex-1">
          {createElement(`h${level}`, { tabIndex: -1, className: "text-h1 text-ink-heading focus:outline-none" }, agency)}
          {plan && <p className="mt-2 text-body text-ink-muted">{plan}</p>}
        </div>
        {(pill || action) && (
          <div className="flex shrink-0 flex-col items-start gap-2 @head/page:items-end">
            <div className="flex flex-col items-start gap-2 @head/page:flex-row @head/page:items-center @head/page:gap-3">
              {pill && <div className="@head/page:mt-0.5">{pill}</div>}
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
      {checked === activities ? words.pill(activities, whole(activities)) : words.pillPartial(whole(checked), whole(activities))}
    </CheckPill>
  );
}

export function PlanCheck({ result, findingRef, defaultOpen = false, afterMethod, changed = {}, after, method, source, reveal = false }: {
  result: CheckedPlan;
  // Ticket 111: the finding replaces a narration that showed for at least 400 ms, so its byline, the finding and the
  // method sentence enter, once: opacity and a 4 px rise over 200 ms.
  reveal?: boolean;
  // Ticket 38: an upload's check says how it measured delay, and names the upload as its source.
  method?: ReactNode;
  source?: ReactNode;
  findingRef?: Ref<HTMLHeadingElement>;
  // The gallery shows the fold open; the page opens it from a link's hash.
  defaultOpen?: boolean;
  // Ticket 21: the change line and the baseline panel, under the method sentence they qualify.
  afterMethod?: ReactNode;
  // Ticket 21: the rows this version changed since the one before, by STEP reference.
  changed?: Record<string, keyof typeof copy.changes.cell>;
  // Ticket 21: the change list, after what Strata cannot see.
  after?: ReactNode;
}) {
  const findingId = useId();
  const foldId = useId();
  const foldCardsId = useId();
  const sentenceId = useId();
  const cardSentenceId = useId();
  const [open, setOpen] = useState(defaultOpen);
  const [opened, setOpened] = useState(false);
  const [named, setNamed] = useState<string | null>(null);

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

  // A link whose hash names an activity: open the fold if the activity is in it, then bring the
  // activity into view and focus it.
  useEffect(() => {
    const follow = () => {
      const ref = hashReference();
      if (!ref || !result.rows.some((row) => rowKey(row) === ref)) return;
      setNamed(ref);
      if (unmarkedRows.some((row) => rowKey(row) === ref)) setOpen(true);
      requestAnimationFrame(() => {
        const target = visibleActivity(ref);
        if (!target) return;
        bringIntoView(target);
        target.focus({ preventScroll: true });
      });
    };
    follow();
    window.addEventListener("hashchange", follow);
    return () => window.removeEventListener("hashchange", follow);
    // The rows are fixed for a result, so following once per result is enough.
  }, [result]);

  const countLine = open || unmarked === 0 ? copy.table.showingAll(whole(activities), words.noun) : words.countLine(whole(marked), whole(activities));

  return (
    <section aria-labelledby={findingId} data-plan-check>
      <EightColumns prose className="mt-6">
        <div data-finding-block className={cx(reveal && "animate-reveal")}>
          {/* Strata's own words open with its byline, 8 px above them (ticket 111). */}
          <Byline kind="found" />
          <h2 ref={findingRef} id={findingId} tabIndex={-1} className="mt-2 text-h2 text-pretty text-ink-heading focus:outline-none">
            <Finding result={result} />
          </h2>
          <div className="mt-2">
            {method ?? <Method result={result} />}
          </div>
        </div>
        {afterMethod}
      </EightColumns>
      {/* Below 1024 px the cards have no column heads, so the definition of the marks sits at the
          right end of the count line's row, or on a line of its own when the two don't fit. */}
      <div className="mt-4 flex flex-wrap items-baseline justify-between gap-x-4 text-caption">
        <p className="whitespace-nowrap text-ink-muted" data-count-line data-numbers>
          {countLine}
        </p>
        <div className={cx("whitespace-nowrap", VIEW.cards)}>
          <Definition result={result} triggerClassName="inline-flex min-h-6 items-center" />
        </div>
      </div>

      {/* The frame clips its corners, so a row header a link focuses draws its ring inside. */}
      <div data-view="table" className={cx("mt-2 hidden overflow-hidden rounded-md border border-line bg-surface", VIEW.table)}>
        <table className="w-full table-fixed border-collapse text-small">
          <caption className="sr-only">{words.caption(result.plan.implementing_agency, formatDate(result.plan.plan_date))}</caption>
          <thead className="bg-surface-2">
            <tr>
              {COLUMNS.map((column) => (
                <th
                  key={column.key}
                  scope="col"
                  className={cx(CELL, "align-bottom font-semibold text-ink-heading", column.numeric ? "text-right" : "text-left", column.width)}
                >
                  {column.key === "found" ? <Definition result={result} /> : column.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {ordered.map((row) => (
              <TableRow key={rowKey(row)} row={row} result={result} named={named === rowKey(row)} change={changed[row.activity_reference_no]} />
            ))}
            {unmarked > 0 && (
              <tr className="border-t border-line bg-page" data-fold>
                <td colSpan={COLUMNS.length} className="px-2 py-2 @xl/page:px-3">
                  <div className="flex flex-wrap items-center gap-x-4">
                    <FoldSentence rows={unmarkedRows} unmarked={unmarked} id={sentenceId} withheld={Boolean(result.withheld)} />
                    <FoldButton count={unmarked} open={open} controls={foldId} describedBy={sentenceId} onToggle={toggle} />
                  </div>
                </td>
              </tr>
            )}
          </tbody>
          <tbody id={foldId} hidden={!open}>
            {unmarkedRows.map((row) => (
              <TableRow key={rowKey(row)} row={row} result={result} fresh={opened} named={named === rowKey(row)} change={changed[row.activity_reference_no]} />
            ))}
          </tbody>
        </table>
      </div>

      <div data-view="cards" className={cx("mt-2", VIEW.cards)}>
        <ul aria-labelledby={findingId} className="flex flex-col gap-3">
          {ordered.map((row) => (
            <ActivityCard key={rowKey(row)} row={row} result={result} named={named === rowKey(row)} change={changed[row.activity_reference_no]} />
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
        <ul id={foldCardsId} hidden={!open} aria-labelledby={findingId} className="mt-3 flex flex-col gap-3">
          {unmarkedRows.map((row) => (
            <ActivityCard key={rowKey(row)} row={row} result={result} fresh={opened} named={named === rowKey(row)} change={changed[row.activity_reference_no]} />
          ))}
        </ul>
      </div>

      <EightColumns prose className="mt-2">
        {source ?? <PlanSource result={result} />}
        <p className="mt-6 text-small text-ink-muted" data-not-visible>
          {words.notVisible}
        </p>
      </EightColumns>
      {after && <div className="mt-12">{after}</div>}
    </section>
  );
}

function PlanSource({ result }: { result: CheckedPlan }) {
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

// While the check loads: the header's places, then the narration in the places of the finding's byline, the
// finding and the method sentence (ticket 111), then the real column heads over five skeleton rows from 1024 px, and
// three skeleton cards below it. Nothing moves when the rows arrive, and nothing shimmers.
export function PlanCheckSkeleton({ slow, baseline }: {
  slow?: boolean;
  // The baseline panel's place under the method sentence (ticket 21): as tall as the panel with no baseline
  // saved, its words held invisibly, so the rows stay put when the check arrives. None in the public view.
  baseline?: View;
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
      <EightColumns prose className="mt-6">
        {/* The narration and the places it holds share one grid cell, so it is exactly as tall as the byline, the
            finding and the method sentence it stands for. The finding takes two lines below 768 px and at the eight
            columns' 1024 to 1199 px, and one line at the full width from 768 px and from 1200 px. Its count words keep
            to the line's height (Num). The method sentence takes five lines below 768 px and three from it. */}
        <div className="grid" data-plan-narration>
          <div aria-hidden="true" className="invisible col-start-1 row-start-1">
            <SkeletonLine className="text-label" width="w-24" />
            <div className="mt-2">
              <SkeletonText className="text-h2 @md/page:hidden @lg/page:flex @xl/page:hidden" widths={["w-full", "w-2/5"]} />
              <SkeletonLine className="hidden text-h2 @md/page:flex @lg/page:hidden @xl/page:flex" width="w-[70%]" />
            </div>
            <SkeletonText className="mt-2 text-body @md/page:hidden" widths={["w-full", "w-full", "w-full", "w-full", "w-2/5"]} />
            <SkeletonText className="mt-2 hidden text-body @md/page:flex" widths={["w-full", "w-full", "w-2/5"]} />
          </div>
          <div className="col-start-1 row-start-1">
            <Steps steps={[narration]} announce={false} />
          </div>
        </div>
        {baseline && baseline !== "public" && (
          <div aria-hidden="true" className="mt-4 rounded-md border border-line bg-surface p-4" data-baseline-skeleton>
            <p className="invisible text-body">{baseline === "piu" ? copy.baseline.piuNone : copy.baseline.none}</p>
            {baseline === "staff" && <span className="invisible mt-3 block h-11" />}
          </div>
        )}
      </EightColumns>
      {/* Below 1024 px the count line's row also holds the definition's 24 px trigger. */}
      <div aria-hidden="true" className="mt-4 flex min-h-6 items-center @lg/page:block @lg/page:min-h-0">
        <SkeletonLine className="text-caption" width="w-40" />
      </div>
      {/* The real column heads are only places: a screen reader hears the narration's step, not an empty table. */}
      <div aria-hidden="true" className={cx("mt-2 hidden overflow-hidden rounded-md border border-line bg-surface", VIEW.table)}>
        <table className="w-full table-fixed border-collapse text-small">
          <thead className="bg-surface-2">
            <tr>
              {COLUMNS.map((column) => (
                <th key={column.key} scope="col" className={cx(CELL, "text-left font-semibold text-ink-heading", column.numeric && "text-right", column.width)}>
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
                <td className={CELL}>
                  <SkeletonLine width="w-4/5" />
                </td>
                <td className={CELL}>
                  <SkeletonLine width="w-3/5" />
                </td>
                <td className={CELL}>
                  <SkeletonLine width="ml-auto w-4/5" />
                </td>
                <td className={CELL}>
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
          of Description (one from a 768 px page area, whose margins follow the window since ticket 94), two of
          reason, the hairline and the four STEP fields under their labels. */}
      <ul aria-hidden="true" data-skeleton-cards className={cx("mt-2 flex flex-col gap-3", VIEW.cards)}>
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
  );
}
