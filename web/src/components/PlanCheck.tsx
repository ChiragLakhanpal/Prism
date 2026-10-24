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
// in data-activity, and an address whose hash names a reference opens the fold if it must, scrolls
// that activity into view and focuses it (ticket 14 links to plan rows this way).
import { createElement, useEffect, useId, useState, type ReactNode, type Ref } from "react";
import { copy } from "../copy";
import type { Activity, CheckPlanResult, Mark, Reason } from "../lib/api";
import { cx } from "../lib/cx";
import { formatAmountText, formatCount, formatDate, formatNumber } from "../lib/format";
import { Button } from "./Button";
import { CheckPill } from "./CheckPill";
import { EightColumns } from "./EightColumns";
import { Fill, Joined } from "./Fill";
import { Num } from "./Num";
import { Skeleton, SkeletonLine, SkeletonText } from "./Skeleton";
import { Source } from "./Source";
import { StatusBadge, type BadgeKind } from "./StatusBadge";
import { CARD_BREAKPOINTS } from "./Table";
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
const mono = (text: ReactNode) => <span className="font-mono">{text}</span>;

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
// the dot or with STEP's own dash.
function methodText(row: Activity): ReactNode {
  if (!row.method) return blank;
  return row.market_approach ? (
    <>
      {row.method}
      {words.methodDot}{" "}
      <span className="inline-block max-w-full">{row.market_approach}</span>
    </>
  ) : (
    row.method
  );
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
  const first = look && watch ? f.lookAndWatch(look, watch) : look ? f.lookOnly(look) : watch ? f.watchOnly(watch) : f.none;
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
    <p className="text-body text-ink">
      <Fill template={words.method} slots={{ checks: <Joined items={phrases} /> }} />
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
function FoldSentence({ rows, unmarked, id }: { rows: Activity[]; unmarked: number; id: string }) {
  const count = formatCount(unmarked, { capital: true });
  // Each reference stays whole on one line when it fits there.
  const refs = rows.map((row) => <span className="inline-block max-w-full wrap-anywhere font-mono">{row.activity_reference_no}</span>);
  return (
    <p id={id} className="text-small text-ink-muted">
      {unmarked <= words.fold.listUpTo ? (
        <Fill template={words.fold.listed(unmarked)} slots={{ count, refs: <Joined items={refs} /> }} />
      ) : (
        <Fill template={words.fold.counted} slots={{ count }} />
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
    // On the fold's page background the ghost hover (tint-hover) barely shows, so it hovers to tint.
    <Button
      variant="ghost"
      flush
      className="hover:bg-tint!"
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
// "Implementation" the Process status column; from 1200 px "Open - International" (132 px) fits
// too. What Strata found keeps the rest and stays the widest column. Cells are padded 8 px at the
// sides from 1024 px and 12 px from 1200 px (CELL).
const COLUMNS: { key: string; header: ReactNode; width: string; numeric?: boolean }[] = [
  { key: "activity", header: words.columns.activity, width: "w-[25%] xl:w-[21.5%]" },
  { key: "method", header: words.columns.method, width: "w-[16%] xl:w-[15%]" },
  { key: "review", header: words.columns.review, width: "w-[7.5%]" },
  { key: "estimated", header: words.columns.estimated, width: "w-[11.5%] xl:w-[11%]", numeric: true },
  { key: "status", header: words.columns.status, width: "w-[14%] xl:w-[12.5%]" },
  { key: "found", header: null, width: "w-[26%] xl:w-[32.5%]" },
];
const CELL = "px-2 py-3 xl:px-3";

// A row or card a link's hash names keeps the selected row's tint after focus moves on
// (DESIGN.md: tint, Selected row).
function TableRow({ row, result, fresh, named }: { row: Activity; result: CheckedPlan; fresh?: boolean; named?: boolean }) {
  const ref = row.activity_reference_no;
  return (
    <tr id={ref} data-named={named || undefined} className={cx("border-t border-line align-top", named && "bg-tint", fresh && "animate-fade-in")}>
      <th scope="row" tabIndex={-1} data-activity={ref} className={cx(CELL, "text-left font-normal focus-visible:outline-offset-[-2px]")}>
        <span className="block font-mono font-medium wrap-anywhere text-ink">{ref}</span>
        {row.description && <span className="mt-1 block text-small text-ink">{row.description}</span>}
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
          <p className="text-small text-ink-muted">{words.noSignals}</p>
        )}
      </td>
    </tr>
  );
}

// An activity card below 1024 px: the badges and the reference as its heading, so a screen reader's
// list of headings says "Needs a look KE-NWWDA-541055-CW-RFB"; then the Description, the reasons, a
// hairline and the four STEP fields.
function ActivityCard({ row, result, fresh, named }: { row: Activity; result: CheckedPlan; fresh?: boolean; named?: boolean }) {
  const ref = row.activity_reference_no;
  const field = (label: ReactNode, value: ReactNode, wide?: boolean) => (
    <div className={cx("flex min-w-0 flex-col justify-end", wide && "col-span-full")}>
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
          <span tabIndex={-1} data-activity={ref} className="font-mono font-medium wrap-anywhere text-ink-heading">
            {ref}
          </span>
        </h3>
        {row.description && <p className="mt-1 text-small text-ink">{row.description}</p>}
        <div className="mt-2 flex flex-col gap-2">
          {row.marks.length > 0 ? (
            row.marks.map((mark) => <MarkReasons key={mark.mark} mark={mark} result={result} />)
          ) : (
            <p className="text-small text-ink-muted">{words.noSignals}</p>
          )}
        </div>
        <dl className="mt-3 grid grid-cols-[repeat(auto-fit,minmax(7.5rem,1fr))] gap-x-4 gap-y-2 border-t border-line pt-3" data-numbers>
          {field(words.columns.method, methodText(row), true)}
          {field(words.columns.review, row.review_type ?? blank)}
          {field(words.columns.estimated, row.estimated_amount_usd ? amount(row.estimated_amount_usd) : blank)}
          {field(words.columns.status, row.process_status ?? blank)}
        </dl>
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

export function PlanCheckHeader({ agency, plan, pill, headerRef, level = 1, sticky = true }: {
  agency: ReactNode;
  // "Procurement Plan of October 9, 2026", when the plan is known.
  plan?: ReactNode;
  pill?: ReactNode;
  headerRef?: Ref<HTMLDivElement>;
  // The page's h1. The design gallery shows it one level down, under its own h1, and not sticky.
  level?: 1 | 2;
  sticky?: boolean;
}) {
  return (
    <div ref={headerRef} data-plan-header className={cx("border-b border-line bg-page py-4", sticky && "lg:sticky lg:top-0 lg:z-10")}>
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between lg:gap-6">
        <div className="min-w-0">
          {createElement(`h${level}`, { tabIndex: -1, className: "text-h1 text-ink-heading focus:outline-none" }, agency)}
          {plan && <p className="mt-2 text-body text-ink-muted">{plan}</p>}
        </div>
        {pill && <div className="shrink-0 lg:mt-0.5">{pill}</div>}
      </div>
    </div>
  );
}

export function checkPill(result: CheckedPlan): ReactNode {
  const { activities, checked } = result.counts;
  return (
    <CheckPill>
      {checked === activities ? words.pill(activities, whole(activities)) : words.pillPartial(whole(checked), whole(activities))}
    </CheckPill>
  );
}

export function PlanCheck({ result, findingRef, defaultOpen = false }: {
  result: CheckedPlan;
  findingRef?: Ref<HTMLHeadingElement>;
  // The gallery shows the fold open; the page opens it from a link's hash.
  defaultOpen?: boolean;
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
      if (!ref || !result.rows.some((row) => row.activity_reference_no === ref)) return;
      setNamed(ref);
      if (unmarkedRows.some((row) => row.activity_reference_no === ref)) setOpen(true);
      requestAnimationFrame(() => {
        const target = visibleActivity(ref);
        target?.scrollIntoView({ block: "center" });
        target?.focus({ preventScroll: true });
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
        <h2 ref={findingRef} id={findingId} tabIndex={-1} className="text-title text-pretty text-ink-heading focus:outline-none">
          <Finding result={result} />
        </h2>
        <div className="mt-2">
          <Method result={result} />
        </div>
      </EightColumns>
      {/* Below 1024 px the cards have no column heads, so the definition of the marks sits at the
          right end of the count line's row. */}
      <div className="mt-4 flex items-baseline justify-between gap-4 text-caption">
        <p className="text-ink-muted" data-count-line data-numbers>
          {countLine}
        </p>
        <div className={VIEW.cards}>
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
              <TableRow key={row.activity_reference_no} row={row} result={result} named={named === row.activity_reference_no} />
            ))}
            {unmarked > 0 && (
              <tr className="border-t border-line bg-page" data-fold>
                <td colSpan={COLUMNS.length} className="px-2 py-2 xl:px-3">
                  <div className="flex flex-wrap items-center gap-x-4">
                    <FoldSentence rows={unmarkedRows} unmarked={unmarked} id={sentenceId} />
                    <FoldButton count={unmarked} open={open} controls={foldId} describedBy={sentenceId} onToggle={toggle} />
                  </div>
                </td>
              </tr>
            )}
          </tbody>
          <tbody id={foldId} hidden={!open}>
            {unmarkedRows.map((row) => (
              <TableRow key={row.activity_reference_no} row={row} result={result} fresh={opened} named={named === row.activity_reference_no} />
            ))}
          </tbody>
        </table>
      </div>

      <div data-view="cards" className={cx("mt-2", VIEW.cards)}>
        <ul aria-labelledby={findingId} className="flex flex-col gap-3">
          {ordered.map((row) => (
            <ActivityCard key={row.activity_reference_no} row={row} result={result} named={named === row.activity_reference_no} />
          ))}
          {unmarked > 0 && (
            <li className="rounded-md border border-line bg-page p-4" data-fold>
              <FoldSentence rows={unmarkedRows} unmarked={unmarked} id={cardSentenceId} />
              <div className="mt-2">
                <FoldButton count={unmarked} open={open} controls={foldCardsId} describedBy={cardSentenceId} onToggle={toggle} />
              </div>
            </li>
          )}
        </ul>
        <ul id={foldCardsId} hidden={!open} aria-labelledby={findingId} className="mt-3 flex flex-col gap-3">
          {unmarkedRows.map((row) => (
            <ActivityCard key={row.activity_reference_no} row={row} result={result} fresh={opened} named={named === row.activity_reference_no} />
          ))}
        </ul>
      </div>

      <EightColumns prose className="mt-2">
        <PlanSource result={result} />
        <p className="mt-6 text-small text-ink-muted" data-not-visible>
          {words.notVisible}
        </p>
      </EightColumns>
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
          pid: mono(plan.project_id),
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

// While the check loads: the header's places, the finding and method lines, the real column heads
// over five skeleton rows from 1024 px, and three skeleton cards below it. Nothing moves when the
// rows arrive, and nothing shimmers.
export function PlanCheckSkeleton({ slow }: { slow?: boolean }) {
  const rows = [0, 1, 2, 3, 4];
  return (
    <div aria-hidden="true" data-plan-skeleton>
      <EightColumns prose className="mt-6">
        {/* The finding's count words are buttons whose 2 px padding makes its line 4 px taller,
            and the method sentence takes three lines at the prose width. */}
        <div className="py-0.5">
          <SkeletonLine className="text-title" width="w-[70%]" />
        </div>
        {slow && <p className="mt-1 text-caption text-ink-muted">{words.stillChecking}</p>}
        <SkeletonText className="mt-2 text-body" widths={["w-full", "w-full", "w-2/5"]} />
      </EightColumns>
      <SkeletonLine className="mt-4 text-caption" width="w-40" />
      <div className={cx("mt-2 hidden overflow-hidden rounded-md border border-line bg-surface", VIEW.table)}>
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
          of Description, two of reason, the hairline and the four STEP fields under their labels. */}
      <ul className={cx("mt-2 flex flex-col gap-3", VIEW.cards)}>
        {[0, 1, 2].map((index) => (
          <li key={index} className="rounded-md border border-line bg-surface p-4">
            <div className="flex flex-col items-start gap-2 text-small">
              <Skeleton className="h-[30px] w-28 rounded-pill" />
              <SkeletonLine width="w-[190px] max-w-full" />
            </div>
            <SkeletonText className="mt-1 text-small" widths={["w-full", "w-3/5"]} />
            <SkeletonText className="mt-2 text-small" widths={["w-full", "w-4/5"]} />
            <dl className="mt-3 grid grid-cols-[repeat(auto-fit,minmax(7.5rem,1fr))] gap-x-4 gap-y-2 border-t border-line pt-3">
              {[words.columns.method, words.columns.review, words.columns.estimated, words.columns.status].map((label, field) => (
                <div key={field} className={cx("flex min-w-0 flex-col justify-end", field === 0 && "col-span-full")}>
                  <dt className="text-caption text-ink-muted">{label}</dt>
                  <dd>
                    <SkeletonLine className="text-small" width={field === 0 ? "w-4/5" : "w-3/5"} />
                  </dd>
                </div>
              ))}
            </dl>
          </li>
        ))}
      </ul>
    </div>
  );
}
