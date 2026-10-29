// Section 2 of the package workspace, "Planned date for each step" (ticket 27; the 27 brief). A Collapsed section,
// closed on every load, whose summary line names the family's steps and the stage that ran longest, from the tool.
// Opened, it holds the start-date field when the package has no plan dates, the choice of dates (cautious by
// default, middle the other), the step table and its notes.
//
// - Every date, day count and count is estimate_time's (src/strata/estimates/step_dates.py). The browser adds no
//   days and divides nothing; both choices come in one answer, so switching renders in the same frame.
// - The steps' labels, STEP's full names and their phrases come from the step-label registry (web/src/steps.ts).
//   From a 768 px page area each label opens a DefinitionWindow with STEP's full name on hover, keyboard focus or a
//   click, which a screen reader also hears with the label; below it the table becomes a list and the full name is
//   printed under each label.
// - A step that abstains says so in its own row, in the first person. Under 20 comparable packages in all, the
//   section shows the steps and their counts with no dates and no controls, and so it does when no step has a date
//   or days in either choice (the tool's none_dated), as on the fixture.
// - Every count in a sentence is the tool's (dated_n, undated_n, few_n, dateable_n): the browser counts nothing.
// - Strata writes planned dates only: no cell, caption or note holds an actual date.
// - A count, a planned date, or the summary's "{n} of {m}" opens the evidence drawer at its list, and the row whose
//   list is open takes the tint fill.
import { useEffect, useId, useRef, useState, type ReactNode, type Ref } from "react";
import { CircleDashed, CircleX } from "lucide-react";
import { copy } from "../copy";
import { ApiError, getJson, putJson } from "../lib/api";
import { sharePlanDateChoice, useSharedPlanDateChoice } from "../lib/estimates";
import { cx } from "../lib/cx";
import { evidenceIn, openEvidence, origin } from "../lib/evidence";
import { formatCount, formatDate } from "../lib/format";
import { address } from "../lib/router";
import {
  CHOICES,
  fromStored,
  isStepList,
  longestListId,
  rememberStepLists,
  stepListId,
  stepsApi,
  stored,
  type Choice,
  type StepDate,
  type StepDates,
  type StepPoint,
  type StepsResult,
} from "../lib/steps";
import { useStore } from "../lib/store";
import { dataReadinessHref } from "../routes";
import { familyStep, stepFamily, type StepEntry, type StepFamily } from "../steps";
import { Alert } from "./Alert";
import { Button } from "./Button";
import { CollapsedSection } from "./CollapsedSection";
import { Fill, Joined } from "./Fill";
import { Num, NumLines, type NumCheck } from "./Num";
import { backtestFrom, FromLine, recordsFrom } from "./NumFrom";
import { SegmentedControl } from "./SegmentedControl";
import { Source } from "./Source";
import { DefinitionWindow } from "./Term";
import { TextLink } from "./TextLink";
import { FootStrip } from "./FootStrip";

const words = copy.stepDates;
const SLOW_MS = 400;

export type StepsState =
  | { status: "loading" }
  | { status: "ready"; result: StepsResult }
  | { status: "error"; error: ApiError | null; onRetry: () => void };

// What the start-date field holds and what it last said.
export type StartField = {
  value: string;
  error: "empty" | "range" | "failed" | null;
  committing: boolean;
  // A commit has waited longer than 400 ms: the date cells become skeleton bars at their own size.
  slow: boolean;
  status: string;
};

const EMPTY_START: StartField = { value: "", error: null, committing: false, slow: false, status: "" };

export type Opener = (id: string, element: HTMLElement) => void;

// ── Small helpers ────────────────────────────────────────────────────────

const number = (value: number) => <Num value={value} options={{ compact: false }} />;
const shortDate = (iso: string) => <Num date={iso} style="table" />;

// About how many in 10 comparable packages ran later, as the tool counted them; five in 10 is "about half".
const about = (in10: number | null) => (in10 === 5 ? words.aboutHalf : <Fill template={words.aboutIn10} slots={{ in10: number(in10 ?? 0) }} />);

// The days a planned date rests on, as its caption says them.
function dayCaption(point: StepPoint, previous: StepEntry | null): ReactNode {
  if (point.days === null || point.days_relation === null) return null;
  const one = point.days === 1;
  const d = words.days;
  switch (point.days_relation) {
    case "after_previous":
      return <Fill template={one ? d.afterOne : d.after} slots={{ days: number(point.days), previous: previous?.phrase ?? "" }} />;
    case "after_plan":
      return <Fill template={one ? d.afterPlanOne : d.afterPlan} slots={{ days: number(point.days) }} />;
    case "on_plan":
      return d.onPlan;
    case "before_plan":
      return <Fill template={one ? d.beforePlanOne : d.beforePlan} slots={{ days: number(point.days) }} />;
  }
}

// ── The summary line ─────────────────────────────────────────────────────

function Summary({ dates, packageKey, onOpen, from }: { dates: StepDates; packageKey: string; onOpen: Opener; from: ReactNode }) {
  const family = stepFamily(dates.family);
  if (!family) {
    return <>{dates.family_reason === "method_not_listed" && dates.method ? words.summaryNotListed(dates.method) : words.summaryNoFamily}</>;
  }
  const count = family.steps.length;
  const steps = (
    <Fill template={words.summarySteps(formatCount(count, { capital: true }))} slots={{ first: family.steps[0].phrase, last: family.steps[count - 1].phrase }} />
  );
  if (dates.abstain_all) {
    const n = dates.abstain_all.n;
    return (
      <>
        {steps}{" "}
        {n === 0 ? words.summaryAbstainNone : n === 1 ? words.summaryAbstainOne : <Fill template={words.summaryAbstain} slots={{ n: number(n) }} />}
      </>
    );
  }
  const longest = dates.longest;
  const stage = longest ? familyStep(family, longest.step_key)?.stage : null;
  // The tool's counts: every step it could not date, and how many of those for too few comparable packages. "Any of
  // the six" only when every step was the tool's to date; a package from a sentence's first step is your date, so
  // there it says "five of the six".
  const all = dates.basis === "delay" && dates.undated_n >= dates.dateable_n;
  const undated =
    dates.undated_n === 0
      ? null
      : dates.few_n === dates.undated_n
        ? all
          ? words.summaryPartialAll(formatCount(count))
          : words.summaryPartial(formatCount(dates.few_n), formatCount(count))
        : all
          ? words.summaryUndatedAll(formatCount(count))
          : words.summaryUndated(formatCount(dates.undated_n), formatCount(count));
  return (
    <>
      {steps}
      {longest && stage && (
        <>
          {" "}
          <Fill
            template={words.summaryLongest}
            slots={{
              stage,
              nm: (
                <Num
                  part={longest.n}
                  whole={longest.m}
                  show="count"
                  check={{
                    tooltip: <Fill template={words.tips.longest} slots={{ m: number(longest.m), n: number(longest.n), stage: stage.toLowerCase() }} />,
                    from,
                    act: words.tips.listAct,
                    opens: "record",
                    onOpen: (element) => onOpen(longestListId(packageKey), element),
                  }}
                />
              ),
            }}
          />
        </>
      )}
      {undated && (
        <>
          {" "}
          {undated}
        </>
      )}
    </>
  );
}

// ── The controls ─────────────────────────────────────────────────────────

function StartDate({
  phrase,
  field,
  range,
  preview,
  noPlan,
  onChange,
  onCommit,
}: {
  phrase: string;
  field: StartField;
  range: { from: string; to: string };
  preview: boolean;
  noPlan: boolean;
  onChange: (value: string) => void;
  onCommit: () => void;
}) {
  const inputId = useId();
  const hintId = useId();
  const errorId = useId();
  const error =
    field.error === "empty"
      ? words.start.errorEmpty(phrase)
      : field.error === "range"
        ? words.start.errorRange(formatDate(range.from), formatDate(range.to))
        : field.error === "failed"
          ? words.start.failed
          : null;
  return (
    <div data-start-date className="flex flex-col">
      <label htmlFor={inputId} className="text-small font-bold text-ink-heading">
        {words.start.label(phrase)}
      </label>
      <div className="mt-2 flex flex-col gap-2 @md/page:flex-row @md/page:items-center @md/page:gap-3">
        <input
          id={inputId}
          type="date"
          value={field.value}
          min={range.from}
          max={range.to}
          readOnly={preview}
          aria-invalid={field.error ? true : undefined}
          aria-describedby={[error ? errorId : null, hintId].filter(Boolean).join(" ")}
          onChange={(event) => onChange(event.currentTarget.value)}
          onKeyDown={(event) => {
            if (event.key !== "Enter" || preview) return;
            event.preventDefault();
            onCommit();
          }}
          className={cx(
            "h-11 w-full rounded-sm border bg-surface px-3 text-body text-ink tabular-nums @md/page:w-48",
            field.error ? "border-error" : "border-line-strong",
            preview && "bg-surface-2",
          )}
        />
        {!preview && (
          <Button variant="secondary" onClick={onCommit} className="w-full @md/page:w-auto" data-commit-start>
            {words.start.commit}
          </Button>
        )}
      </div>
      {error && (
        <p id={errorId} className="mt-2 text-caption text-error">
          {error}
        </p>
      )}
      <p id={hintId} className="mt-2 text-caption text-ink-muted">
        {preview ? words.start.preview : noPlan ? words.start.hintNoPlan(phrase) : words.start.hint}
      </p>
      {field.status && (
        <p className="mt-1 text-caption text-ink-muted" data-start-status>
          {field.status}
        </p>
      )}
    </div>
  );
}

function ChoiceControl({
  dates,
  choice,
  onChoose,
  preview,
  saveFailed,
}: {
  dates: StepDates;
  choice: Choice;
  onChoose: (choice: Choice) => void;
  preview: boolean;
  saveFailed: boolean;
}) {
  const previewId = useId();
  return (
    <div data-choice>
      <SegmentedControl
        legend={words.choice.legend}
        value={choice}
        onChange={onChoose}
        describedBy={preview ? previewId : undefined}
        options={CHOICES.map((value) => ({
          value,
          label: value === "middle" ? words.choice.middle : words.choice.cautious(String(dates.cautious_in10)),
        }))}
      />
      {preview && (
        <p id={previewId} className="mt-2 text-caption text-ink-muted">
          {words.choice.preview}
        </p>
      )}
      {saveFailed && (
        <p className="mt-2 flex items-start gap-2 text-caption text-error" data-save-failed>
          <CircleX aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-error-icon" />
          {words.choice.saveFailed}
        </p>
      )}
    </div>
  );
}

// ── One step's cells ─────────────────────────────────────────────────────

export type Row = {
  step: StepDate;
  entry: StepEntry;
  previous: StepEntry | null;
  listId: string;
  // Where the step's date and count came from: the record sets the tool read, through the date they run to (ticket 96).
  from?: ReactNode;
};

function rowsOf(dates: StepDates, family: StepFamily, packageKey: string, from: ReactNode): Row[] {
  return dates.steps.map((step, index) => ({
    step,
    entry: familyStep(family, step.step_key) ?? { key: step.step_key, label: step.step_key, step_name: step.step_key, phrase: step.step_key, stage: null },
    previous: index > 0 ? familyStep(family, dates.steps[index - 1].step_key) : null,
    listId: stepListId(packageKey, step.step_key),
    from,
  }));
}

// The From line of every count and date in the section: the record sets the tool counted the comparable packages'
// steps from, as its coverage line names them, through the date its records run to.
function stepsFrom(result: StepsResult, dates: StepDates): ReactNode {
  const words = recordsFrom(result.sources, result.records_through, dates.coverage.sources);
  return words ? <FromLine words={words} /> : undefined;
}

function Abstention({ children, days }: { children: ReactNode; days?: ReactNode }) {
  return (
    <span className="flex items-start gap-2" data-abstains>
      <CircleDashed aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-line-strong" />
      <span className="min-w-0">
        <span className="block text-small text-neutral">{children}</span>
        {days && <span className="block text-caption text-ink-muted">{days}</span>}
      </span>
    </span>
  );
}

// What hover or focus on a step's planned date, or on the days of a step that needs an earlier one, says about it,
// and what selecting it opens: the step's comparable packages. One place, so the row and the caption's signed date
// say the same. A draft of planned dates (ticket 38) uses it for its own dates.
export function dateCheck(point: StepPoint, row: Row, family: StepFamily, onOpen: Opener): NumCheck {
  const n = row.step.comparables_n ?? 0;
  const slots = {
    longer: number(point.longer ?? 0),
    n: number(n),
    about: about(point.in10),
    step: row.entry.phrase,
    days: number(point.days ?? 0),
    previous: row.previous?.phrase ?? "",
    first: family.steps[0].phrase,
  };
  // None ran later than the date's days, so the tooltip never says "0 of 25, about 0 in 10" (ticket 58).
  const noneLater = (point.longer ?? 0) === 0 && n > 0;
  const tip =
    row.step.abstain_reason === "needs_earlier_step"
      ? words.tips.daysNeedsEarlier
      : !point.planned_date
        ? words.tips.dateUndated
        : point.days_relation === "after_previous"
          ? noneLater
            ? words.tips.dateNoneLater
            : words.tips.dateDuration
          : point.days_relation === "before_plan"
            ? words.tips.dateBefore
            : noneLater
              ? words.tips.dateNoneLaterDelay
              : words.tips.dateDelay;
  return {
    tooltip: <Fill template={tip} slots={slots} />,
    from: row.from,
    act: <Fill template={words.tips.act} slots={{ n: slots.n }} />,
    opens: "record",
    onOpen: (element) => onOpen(row.listId, element),
  };
}

// Why a step has no date, in its own row.
function abstention(row: Row, recordsDate: string): ReactNode {
  const n = row.step.comparables_n ?? 0;
  switch (row.step.abstain_reason) {
    case "few_comparables":
      return n === 0 ? words.abstainNone : n === 1 ? words.abstainOne : <Fill template={words.abstain} slots={{ n: <Num count={n} /> }} />;
    case "not_reached": {
      const reached = row.step.reached_n ?? 0;
      const slots = { reached: number(reached), n: number(n), date: <Num date={recordsDate} /> };
      return <Fill template={reached === 0 ? words.notReachedNone : reached === 1 ? words.notReachedOne : words.notReached} slots={slots} />;
    }
    case "not_in_plan":
      return words.notInPlan;
    case "needs_earlier_step":
      return words.needsEarlier(row.previous?.phrase ?? "");
    default:
      return null;
  }
}

// The planned date in the choice shown, or why there is none. In the narrow list its lines end on the right edge.
function Planned({
  row,
  dates,
  family,
  choice,
  onOpen,
  slow,
  recordsDate,
  narrow = false,
}: {
  row: Row;
  dates: StepDates;
  family: StepFamily;
  choice: Choice;
  onOpen: Opener;
  slow: boolean;
  recordsDate: string;
  narrow?: boolean;
}) {
  const { step, previous } = row;
  const point = step[choice];
  if (!point) return null;
  const side = narrow ? "items-end text-right" : "items-start text-left";
  if (step.is_anchor) {
    return point.planned_date ? (
      <span className={cx("flex flex-col", side)} data-planned={point.planned_date}>
        <span className="text-body font-semibold text-ink tabular-nums">{formatDate(point.planned_date, { style: "table" })}</span>
        <span className="text-caption text-ink-muted">{words.yours}</span>
      </span>
    ) : (
      <span className={cx("flex flex-col", side)}>
        <span className="text-small text-ink-muted">{words.undated}</span>
        {/* With nothing to date, the section asks for no start date, so this points at no field. */}
        {!dates.none_dated && <span className="text-caption text-ink-muted">{words.undatedStart}</span>}
      </span>
    );
  }
  const days = dayCaption(point, previous);
  if (step.abstain_reason) {
    // A step that needs an earlier one keeps its days, which you can check as a dated step's days.
    const checked =
      step.abstain_reason === "needs_earlier_step" && days ? (
        <NumLines check={dateCheck(point, row, family, onOpen)} first={days} firstClassName="text-caption text-ink-muted" />
      ) : null;
    return <Abstention days={checked}>{abstention(row, recordsDate)}</Abstention>;
  }
  if (slow) return <span aria-hidden="true" className="block h-4 w-24 rounded-xs bg-surface-2" data-skeleton />;
  return (
    <span data-planned={point.planned_date ?? "undated"}>
      <NumLines
        check={dateCheck(point, row, family, onOpen)}
        first={point.planned_date ? shortDate(point.planned_date) : words.undated}
        second={days}
        firstClassName={point.planned_date ? "text-body font-semibold text-ink" : "text-small text-ink-muted"}
        secondClassName="text-caption text-ink-muted"
        className={side}
      />
    </span>
  );
}

// The plan's own date for the step as first published, and where a later plan moved it.
function PlanDate({ step }: { step: StepDate }) {
  if (!step.plan_first_date) return <span className="text-small text-ink-muted">{words.planNone}</span>;
  const moved = step.plan_latest_date && step.plan_latest_date !== step.plan_first_date && step.plan_latest_version_date;
  return (
    <span className="flex flex-col" data-plan-date>
      <span className="text-small text-ink tabular-nums">{formatDate(step.plan_first_date, { style: "table" })}</span>
      {moved && (
        <span className="text-caption text-ink-muted" data-plan-moved>
          <Fill
            template={words.planMoved}
            slots={{ date: formatDate(step.plan_latest_date!, { style: "table" }), plan: formatDate(step.plan_latest_version_date!, { style: "table" }) }}
          />
        </span>
      )}
    </span>
  );
}

// side: in the narrow list a count's tooltip opens above it, over its own row, so it never covers the next row's count
// (ticket 96).
function Comparables({ row, onOpen, side }: { row: Row; onOpen: Opener; side?: "top" }) {
  const { step, entry } = row;
  if (step.is_anchor) return <span className="text-small text-ink-muted">{words.comparablesStart}</span>;
  const n = step.comparables_n ?? 0;
  if (n === 0) return <span className="text-small text-ink-muted">{words.comparablesNone}</span>;
  return (
    // Padded 12 px each side and pulled back as far, so a one-digit count's target is at least 24 px wide (the 27
    // brief, section 8.6) and the numbers stay on the column's right edge.
    <Num
      value={n}
      options={{ compact: false }}
      className="-mx-3 px-3 text-small"
      check={{
        tooltip: step.abstain_reason === "not_reached" ? words.tips.countChecked(entry.phrase) : words.tips.count(entry.phrase),
        from: row.from,
        act: words.tips.listAct,
        opens: "record",
        name: words.countName(String(n), entry.label),
        side,
        onOpen: (element) => onOpen(row.listId, element),
      }}
    />
  );
}

// The step's label: in a zone of 49rem or wider a DefinitionWindow with STEP's full name that opens on hover, keyboard
// focus or a click (criterion 4), which a screen reader hears with the label (aria-describedby); below it the name is
// printed (the list's own rendering).
function StepLabel({ row }: { row: Row }) {
  const nameId = useId();
  return (
    <>
      <DefinitionWindow
        label={row.entry.label}
        title={row.entry.label}
        describedBy={nameId}
        triggerClassName="text-small font-semibold text-ink-heading"
        openOnHover
      >
        {words.termBody(row.entry.step_name)}
      </DefinitionWindow>
      <span id={nameId} className="sr-only">
        {words.inStep(row.entry.step_name)}
      </span>
    </>
  );
}

// ── The table, from a 768 px page area, and the list below it ───────────

type Body = {
  dates: StepDates;
  family: StepFamily;
  rows: Row[];
  choice: Choice;
  kind: "step" | "planned";
  packageKey: string;
  openId: string | null;
  onOpen: Opener;
  slow: boolean;
  caption: ReactNode;
  captionId: string;
  // The date the records run to, by which a still-open comparable had not reached a step.
  recordsDate: string;
  // Where the section's counts came from (ticket 96).
  from: ReactNode;
};

function StepTable({ dates, family, rows, choice, kind, packageKey, openId, onOpen, slow, caption, recordsDate, from }: Body) {
  const dating = !dates.abstain_all;
  const plan = kind === "step";
  const widths = plan ? (dating ? ["32%", "24%", "26%", "18%"] : ["44%", "32%", "24%"]) : dating ? ["40%", "36%", "24%"] : ["70%", "30%"];
  const head = "px-3 py-3 align-bottom text-left text-small font-bold text-ink-heading";
  const note = "block text-caption font-normal text-ink-muted";
  const firstVersion = rows.find((row) => row.step.plan_first_version_date)?.step.plan_first_version_date ?? null;
  return (
    <table className="w-full table-fixed border-collapse" data-step-table>
      <caption className="caption-top pb-3 text-left">{caption}</caption>
      <colgroup>
        {widths.map((width, index) => (
          <col key={index} style={{ width }} />
        ))}
      </colgroup>
      <thead className="bg-surface-2">
        <tr>
          <th scope="col" className={head}>
            {words.columns.step}
            <span className={note}>{words.columns.stepNote}</span>
          </th>
          {plan && (
            <th scope="col" className={head}>
              {words.columns.plan}
              <span className={note}>
                {firstVersion ? <Fill template={words.columns.planNote} slots={{ date: formatDate(firstVersion, { style: "table" }) }} /> : words.columns.planNoteNone}
              </span>
            </th>
          )}
          {dating && (
            <th scope="col" className={head} data-choice-header={choice}>
              {/* No step dated: the column says what dating takes, not how often packages ran later (ticket 58). */}
              {dates.none_dated ? words.columns.planned : choice === "cautious" ? words.columns.cautious : words.columns.middle}
              <span className={note}>
                {dates.none_dated ? (
                  <Fill template={words.columns.noneNote} slots={{ min: number(dates.min_comparables) }} />
                ) : choice === "cautious" ? (
                  words.columns.cautiousNote(String(dates.cautious_in10))
                ) : (
                  words.columns.middleNote
                )}
              </span>
            </th>
          )}
          <th scope="col" className={cx(head, "text-right")}>
            {words.columns.comparables}
            <span className={note}>{words.columns.comparablesNote}</span>
          </th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.step.step_key} data-step-row={row.step.step_key} className={cx("border-t border-line", openId === row.listId && "bg-tint")}>
            {/* Each cell's first line sits on one baseline: the label, the plan's date and the planned date. */}
            <th scope="row" className="px-3 py-3 text-left align-baseline font-normal">
              <StepLabel row={row} />
              {dating && dates.longest?.step_key === row.step.step_key && <LongestMark dates={dates} family={family} packageKey={packageKey} onOpen={onOpen} from={from} />}
            </th>
            {plan && (
              <td className="px-3 py-3 align-baseline">
                <PlanDate step={row.step} />
              </td>
            )}
            {dating && (
              <td className="px-3 py-3 align-baseline">
                <Planned row={row} dates={dates} family={family} choice={choice} onOpen={onOpen} slow={slow} recordsDate={recordsDate} />
              </td>
            )}
            <td className="px-3 py-3 text-right align-baseline">
              <Comparables row={row} onOpen={onOpen} />
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

// "Ran longest in {n} of {m}" under the longest stage's label: the same count, tooltip and list as the summary's.
function LongestMark({ dates, family, packageKey, onOpen, from }: { dates: StepDates; family: StepFamily; packageKey: string; onOpen: Opener; from: ReactNode }) {
  const longest = dates.longest!;
  const stage = familyStep(family, longest.step_key)?.stage ?? "";
  return (
    <span className="mt-1 block text-caption text-ink-muted" data-longest-mark>
      <Fill
        template={words.longest}
        slots={{
          nm: (
            <Num
              part={longest.n}
              whole={longest.m}
              show="count"
              inCaption
              check={{
                tooltip: <Fill template={words.tips.longest} slots={{ m: number(longest.m), n: number(longest.n), stage: stage.toLowerCase() }} />,
                from,
                act: words.tips.listAct,
                opens: "record",
                onOpen: (element) => onOpen(longestListId(packageKey), element),
              }}
            />
          ),
        }}
      />
    </span>
  );
}

function StepList({ dates, family, rows, choice, kind, packageKey, openId, onOpen, slow, caption, captionId, recordsDate, from }: Body) {
  const dating = !dates.abstain_all;
  const label = "text-caption text-ink-muted";
  return (
    <>
    <div id={captionId} className="pb-3">
      {caption}
    </div>
    <ol aria-labelledby={captionId} className="border-t border-line" data-step-list>
      {rows.map((row) => (
        <li key={row.step.step_key} data-step-item={row.step.step_key} className={cx("border-b border-line py-3", openId === row.listId && "bg-tint")}>
          <h3 className="text-small font-semibold text-ink-heading">{row.entry.label}</h3>
          <p className="text-caption text-ink-muted">{words.inStep(row.entry.step_name)}</p>
          {dating && dates.longest?.step_key === row.step.step_key && <LongestMark dates={dates} family={family} packageKey={packageKey} onOpen={onOpen} from={from} />}
          {/* Every item's label column is two fifths of the list and never under 7rem, so the labels line up from step
              to step and never print over a value; a long value, such as "30 days after the issued bidding
              document", wraps inside its own column, right-aligned. */}
          <dl className="mt-2 grid grid-cols-[minmax(7rem,2fr)_minmax(0,3fr)] gap-x-2 gap-y-2">
            {kind === "step" && (
              <>
                <dt className={label}>{words.columns.plan}</dt>
                <dd className="min-w-0 text-right">
                  <PlanDate step={row.step} />
                </dd>
              </>
            )}
            {dating && (
              <>
                <dt className={cx(label, row.step.abstain_reason && "col-span-2")}>
                  {dates.none_dated ? words.columns.planned : choice === "cautious" ? words.columns.cautious : words.columns.middle}
                </dt>
                {/* A sentence takes the item's full width under its label, so the labels keep their column. */}
                <dd className={row.step.abstain_reason ? "col-span-2" : "flex min-w-0 justify-end text-right"}>
                  <Planned row={row} dates={dates} family={family} choice={choice} onOpen={onOpen} slow={slow} recordsDate={recordsDate} narrow />
                </dd>
              </>
            )}
            <dt className={label}>{words.columns.comparables}</dt>
            <dd className="text-right">
              <Comparables row={row} onOpen={onOpen} side="top" />
            </dd>
          </dl>
        </li>
      ))}
    </ol>
    </>
  );
}

// ── The caption and the notes ────────────────────────────────────────────

// Which title sentence the table takes, decided once for the caption on screen and for what the live region says.
type CaptionPick =
  | { kind: "abstain" }
  | { kind: "none" }
  | { kind: "noneAfter" }
  | { kind: "undated" }
  | { kind: "signed"; row: Row; point: StepPoint & { planned_date: string } }
  | { kind: "partial"; dated: number };

function pickCaption(dates: StepDates, family: StepFamily, rows: Row[], choice: Choice): CaptionPick {
  // A package from a sentence whose only date is your start date says no later step is dated.
  const none = (): CaptionPick => (dates.basis === "duration" && dates.start_date ? { kind: "noneAfter" } : { kind: "none" });
  // No step dated: the caption names the steps, and the summary above says why (ticket 58), unless a package from a
  // sentence has its start date, whose caption says no later step is dated.
  if (dates.abstain_all) return { kind: "abstain" };
  if (dates.none_dated) return dates.basis === "duration" && dates.start_date ? none() : { kind: "abstain" };
  if (dates.needs_start_date) return { kind: "undated" };
  const signed = rows.find((row) => row.step.step_key === family.longest_through);
  const point = signed?.step[choice];
  if (signed && point?.planned_date) return { kind: "signed", row: signed, point: { ...point, planned_date: point.planned_date } };
  const dated = dates.dated_n[choice];
  return dated === 0 ? none() : { kind: "partial", dated };
}

// The title sentence as plain words, for the live region after the choice changes or the steps are dated.
function captionText(dates: StepDates, family: StepFamily, rows: Row[], choice: Choice): string {
  const pick = pickCaption(dates, family, rows, choice);
  switch (pick.kind) {
    case "abstain":
      return words.captionAbstain(family.family_name);
    case "none":
      return words.captionNone;
    case "noneAfter":
      return words.captionNoneAfter(family.steps[0].phrase);
    case "undated":
      return words.captionUndated;
    case "signed":
      return words.captionSigned[choice].replace("{date}", formatDate(pick.point.planned_date));
    case "partial":
      return words.captionPartial(formatCount(pick.dated), formatCount(family.steps.length));
  }
}

function Caption({ dates, family, rows, choice, onOpen }: { dates: StepDates; family: StepFamily; rows: Row[]; choice: Choice; onOpen: Opener }) {
  const count = family.steps.length;
  const pick = pickCaption(dates, family, rows, choice);
  const title: ReactNode =
    pick.kind === "signed" ? (
      <Fill
        template={words.captionSigned[choice]}
        slots={{ date: <Num date={pick.point.planned_date} check={dateCheck(pick.point, pick.row, family, onOpen)} /> }}
      />
    ) : pick.kind === "partial" ? (
      words.captionPartial(formatCount(pick.dated), formatCount(count))
    ) : (
      captionText(dates, family, rows, choice)
    );
  return (
    <span className="flex flex-col gap-1">
      <span className="block text-h2 text-ink-heading" data-step-caption>
        {title}
      </span>
      <span className="block text-caption text-ink-muted" data-step-count>{words.count(formatCount(count))}</span>
    </span>
  );
}

function Notes({ dates, family, choice, kind, result, asOf, from }: { dates: StepDates; family: StepFamily; choice: Choice; kind: "step" | "planned"; result: StepsResult; asOf: string | null; from: ReactNode }) {
  const track = dates.abstain_all ? null : dates.track_record?.[choice] ?? null;
  const trackTip = track && (
    <Fill
      template={track.run_id ? words.tips.track : words.tips.trackNoRun}
      slots={{ year: <Num year={track.year} />, run: <span className="font-mono">{track.run_id}</span> }}
    />
  );
  const coverage = dates.coverage;
  const link = <TextLink href={dataReadinessHref(coverage.sources, "estimate_time")}>{words.coverageLink}</TextLink>;
  // The comparable packages used and all of them each say what they count (ticket 96). The counts of those left out are
  // plain text, because the sentence already says what each counts.
  const counted = (value: number, tooltip: string) => <Num value={value} options={{ compact: false }} check={{ tooltip, from }} inCaption />;
  const used = counted(coverage.used, words.tips.used);
  const total = counted(coverage.total, words.tips.total);
  const plain = (value: number) => <Num value={value} options={{ compact: false }} />;
  const date = asOf ?? result.records_through;
  return (
    // In the zone's foot strip (ticket 101's design review), which gives it its place and its caption type.
    <div className="flex max-w-prose flex-col gap-2 text-caption text-ink-muted" data-step-notes>
      {family.abbreviation_note && <p>{family.abbreviation_note}</p>}
      {track && (
        <p data-track-record>
          <span className="font-bold">{words.trackLabel}</span>{" "}
          <Fill
            template={words.track[choice]}
            slots={{
              total: number(track.total),
              year: <Num year={track.year} />,
              inside: (
                <Num
                  value={track.inside}
                  options={{ compact: false }}
                  inCaption
                  check={{ tooltip: trackTip, from: <FromLine words={backtestFrom(String(track.year))} /> }}
                />
              ),
              catch: number(track.catch_in10),
            }}
          />
        </p>
      )}
      {kind === "step" && dates.actual_steps_count !== null && dates.actual_steps_count > 0 && (
        <p data-actuals>{dates.actual_steps_count === 1 ? words.actualsOne : words.actuals(formatCount(dates.actual_steps_count))}</p>
      )}
      <p data-coverage-line>
        {/* With no comparable package at all there is nothing to count, so only the link to Data readiness stays. */}
        {coverage.total > 0 && (
          <>
            {(coverage.other_family ?? 0) > 0 ? (
              <Fill
                template={coverage.missing > 0 ? words.coverageOtherFamilyAndMissing : words.coverageOtherFamily}
                slots={{ used, total, other: plain(coverage.other_family ?? 0), missing: plain(coverage.missing) }}
              />
            ) : coverage.missing > 0 ? (
              <Fill template={words.coverage} slots={{ used, total, missing: plain(coverage.missing) }} />
            ) : (
              <Fill template={words.coverageAll} slots={{ total }} />
            )}{" "}
          </>
        )}
        {link}
      </p>
      <Source>
        <Fill
          template={asOf ? words.sourceLineAsOf : words.sourceLine}
          slots={{ names: <Joined items={result.sources.map((source) => source.dataset_name)} />, date: date ? <Num date={date} /> : "" }}
        />
      </Source>
    </div>
  );
}

// ── The pure view, which the design gallery draws as it is ──────────────

export type StepsViewProps = {
  state: StepsState;
  // The package's key in the drawer's list ids: its STEP reference or its id.
  packageKey: string;
  kind: "step" | "planned";
  open: boolean;
  onToggle: () => void;
  choice: Choice;
  onChoose: (choice: Choice) => void;
  start?: StartField;
  onStartChange?: (value: string) => void;
  onCommitStart?: () => void;
  preview?: boolean;
  saveFailed?: boolean;
  // The evidence drawer's open list, whose row takes the tint fill.
  openId?: string | null;
  onOpen?: Opener;
  headingRef?: Ref<HTMLHeadingElement>;
  announce?: string;
  // The page's as-of date, when it has one.
  asOf?: string | null;
};

const noop = () => undefined;

export function StepsView({
  state,
  packageKey,
  kind,
  open,
  onToggle,
  choice,
  onChoose,
  start = EMPTY_START,
  onStartChange = noop,
  onCommitStart = noop,
  preview = false,
  saveFailed = false,
  openId = null,
  onOpen = noop,
  headingRef,
  announce = "",
  asOf = null,
}: StepsViewProps) {
  const captionId = useId();
  const result = state.status === "ready" ? state.result : null;
  const dates = result?.step_dates ?? null;
  const family = stepFamily(dates?.family);
  const from = result && dates ? stepsFrom(result, dates) : undefined;
  let summary: ReactNode = null;
  let error: ReactNode = null;
  if (state.status === "error") {
    const code = state.error?.body?.trace_id;
    error = (
      <Alert
        state="error"
        live="alert"
        action={
          <div className="flex flex-col items-start gap-2">
            <Button variant="secondary" onClick={state.onRetry}>
              {words.tryAgain}
            </Button>
            {code && (
              <p className="text-caption text-ink-muted">
                {/* A request id has no spaces, so it may break anywhere rather than push the page sideways at 320 px. */}
                <Fill template={words.errorCode} slots={{ code: <span className="font-mono wrap-anywhere">{code}</span> }} />
              </p>
            )}
          </div>
        }
      >
        {words.error}
      </Alert>
    );
  } else if (dates) {
    summary = <Summary dates={dates} packageKey={packageKey} onOpen={onOpen} from={from} />;
  }
  const rows = dates && family ? rowsOf(dates, family, packageKey, from) : [];
  // No step has a date or days in either choice: the choice and the start date would change nothing, so the section
  // offers neither and says why no step is dated.
  const controls = dates !== null && !dates.abstain_all && !dates.none_dated;
  // A row's "had reached this step by" names the date the source line names (ticket 58): the page's as-of date, or the
  // records' own.
  const recordsDate = result ? (asOf ?? result.records_through ?? result.as_of) : "";
  const body =
    state.status === "loading" ? (
      <div className="mt-6 @container/steps">
        <StepsSkeleton kind={kind} />
      </div>
    ) : dates && family && result ? (
      <div className="mt-6">
        <p className="max-w-prose text-body text-ink" data-step-intro>
          {/* The summary above says how few comparable packages there were, so the intro starts at the rule. */}
          {dates.abstain_all ? (
            <Fill template={words.introAbstain(family.family_name)} slots={{ min: number(dates.min_comparables) }} />
          ) : dates.none_dated ? (
            <Fill template={words.introNoneDated(family.family_name)} slots={{ min: number(dates.min_comparables) }} />
          ) : dates.basis === "delay" ? (
            words.introDelay(family.family_name)
          ) : dates.needs_start_date && !dates.start_date ? (
            // No step is dated before the start date, so the intro says how I date them, in the present (ticket 58).
            words.introDurationUndated(family.family_name)
          ) : (
            words.introDuration(family.family_name)
          )}
        </p>
        {controls && (
          <div className="mt-4 flex flex-col gap-4">
            {dates.basis === "duration" && (
              <StartDate
                phrase={family.steps[0].phrase}
                field={start}
                range={dates.start_range}
                preview={preview}
                noPlan={kind === "step"}
                onChange={onStartChange}
                onCommit={onCommitStart}
              />
            )}
            <ChoiceControl dates={dates} choice={choice} onChoose={onChoose} preview={preview} saveFailed={saveFailed} />
          </div>
        )}
        {/* The table or the list by the zone's own width, as zone 3's risks switch (ticket 101's critique, round 2): beside
            the side panel the work column is under 49rem, where four columns put one sentence on five lines. */}
        <div className="mt-6 @container/steps" aria-busy={start.committing || undefined}>
          <div className="hidden @min-[49rem]/steps:block">
            <StepTable
              dates={dates} family={family} rows={rows} choice={choice} kind={kind} packageKey={packageKey} openId={openId} onOpen={onOpen} slow={start.slow}
              caption={<Caption dates={dates} family={family} rows={rows} choice={choice} onOpen={onOpen} />} captionId={`${captionId}-wide`}
              recordsDate={recordsDate}
              from={from}
            />
          </div>
          <div className="@min-[49rem]/steps:hidden">
            <StepList
              dates={dates} family={family} rows={rows} choice={choice} kind={kind} packageKey={packageKey} openId={openId} onOpen={onOpen} slow={start.slow}
              caption={<Caption dates={dates} family={family} rows={rows} choice={choice} onOpen={onOpen} />} captionId={captionId}
              recordsDate={recordsDate}
              from={from}
            />
          </div>
        </div>
      </div>
    ) : null;
  // The zone's note, coverage line and source line end it in its foot strip, as zones 1 and 3 end theirs (ticket 101).
  const foot =
    state.status !== "loading" && dates && family && result ? (
      <FootStrip>
        <Notes dates={dates} family={family} choice={choice} kind={kind} result={result} asOf={asOf} from={from} />
      </FootStrip>
    ) : undefined;
  return (
    <CollapsedSection
      id="planned-dates"
      number={words.number}
      heading={words.heading}
      summary={summary}
      error={error}
      // A retry that failed after you opened the section keeps the button, so you can close it again; with no method
      // family there is nothing to open.
      state={state.status === "ready" ? (family ? "ready" : "empty") : state.status}
      open={open}
      onToggle={onToggle}
      showLabel={words.show}
      hideLabel={words.hide}
      busy={state.status === "loading" && open}
      headingRef={headingRef}
      sectionKey="steps"
      foot={foot}
      live={
        <p className="sr-only" role="status" aria-live="polite">
          {announce}
        </p>
      }
    >
      {body}
    </CollapsedSection>
  );
}

// Opened before the answer came: the intro as two bars, then the table's real header from a 49rem zone, and six
// 48 px rows, since the family, and so its count of steps, comes with the answer (the 27 brief, section 7.5). Static.
function StepsSkeleton({ kind }: { kind: "step" | "planned" }) {
  const plan = kind === "step";
  const head = "px-3 py-3 align-bottom text-left text-small font-bold text-ink-heading";
  const rows = Array.from({ length: 6 }, (_, index) => index);
  return (
    <div aria-hidden="true" className="flex flex-col gap-4" data-steps-skeleton>
      <span className="flex flex-col gap-2">
        <span className="block h-4 w-9/10 rounded-xs bg-surface-2" />
        <span className="block h-4 w-9/20 rounded-xs bg-surface-2" />
      </span>
      <table className="hidden w-full table-fixed border-collapse @min-[49rem]/steps:table">
        <colgroup>
          {(plan ? ["32%", "24%", "26%", "18%"] : ["40%", "36%", "24%"]).map((width, index) => (
            <col key={index} style={{ width }} />
          ))}
        </colgroup>
        <thead className="bg-surface-2">
          <tr>
            <th className={head}>{words.columns.step}</th>
            {plan && <th className={head}>{words.columns.plan}</th>}
            <th className={head}>{words.columns.cautious}</th>
            <th className={cx(head, "text-right")}>{words.columns.comparables}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((index) => (
            <tr key={index} className="h-12 border-t border-line">
              <td colSpan={plan ? 4 : 3} />
            </tr>
          ))}
        </tbody>
      </table>
      <span className="flex flex-col @min-[49rem]/steps:hidden">
        {rows.map((index) => (
          <span key={index} className="block h-12 border-t border-line" />
        ))}
      </span>
    </div>
  );
}

// ── The section on a page: it reads, chooses, dates and opens ───────────

// onState hears each state the section's answer passes through, so the tracker at the top of the page (ticket 115)
// draws from the same answer and the page asks for the steps once. criteria is section 1's comparables query on a
// STEP row's page, find_comparables' criteria by its own parameter names, which the read and the start date both send,
// so the section counts the comparables section 1 shows (ticket 27's review round 2, follow-up 5).
export function StepsSection({
  packageKey,
  kind,
  rerunKey = "",
  criteria = "",
  onState,
}: {
  packageKey: string;
  kind: "step" | "planned";
  rerunKey?: string;
  criteria?: string;
  onState?: (state: StepsState) => void;
}) {
  const here = useStore(address);
  const from = useStore(origin);
  const params = new URLSearchParams(here.search);
  const asOf = params.get("asof");
  const view = params.get("view");
  // A preview of another view shows everything; the choice still switches the dates but is not saved.
  const preview = view !== null && view !== "staff";
  const api = stepsApi(kind, packageKey);
  const [state, setState] = useState<StepsState>({ status: "loading" });
  const [open, setOpen] = useState(() => window.location.hash === "#planned-dates");
  const [choice, setChoice] = useState<Choice>("cautious");
  const [start, setStart] = useState<StartField>(EMPTY_START);
  const [saveFailed, setSaveFailed] = useState(false);
  const [announce, setAnnounce] = useState("");
  const [attempt, setAttempt] = useState(0);
  const heading = useRef<HTMLHeadingElement>(null);
  const chosen = useRef(false);
  const commits = useRef(0);

  useEffect(() => {
    const controller = new AbortController();
    const query = new URLSearchParams(criteria);
    if (asOf) query.set("asof", asOf);
    if (view && view !== "staff") query.set("view", view);
    getJson<StepsResult>(`${api}/steps${query.size ? `?${query.toString()}` : ""}`, { signal: controller.signal }).then(
      (result) => {
        setState({ status: "ready", result });
        if (!chosen.current) setChoice(fromStored(result.plan_date_choice));
        setStart((now) => ({ ...now, value: now.value || result.step_dates?.start_date || "" }));
        if (attempt > 0) heading.current?.focus();
      },
      (error: unknown) => {
        if (controller.signal.aborted) return;
        setState({ status: "error", error: error instanceof ApiError ? error : null, onRetry: () => setAttempt((n) => n + 1) });
      },
    );
    return () => controller.abort();
  }, [api, asOf, view, rerunKey, criteria, attempt]);

  // A link to #planned-dates opens the section and moves focus to its heading.
  useEffect(() => {
    if (window.location.hash === "#planned-dates") heading.current?.focus();
  }, []);

  // Hold each step's list for the drawer while the section shows it.
  useEffect(() => {
    if (state.status === "ready") rememberStepLists(packageKey, state.result, asOf);
  }, [state, packageKey, asOf]);

  useEffect(() => {
    onState?.(state);
  }, [state, onState]);

  const toggle = () => {
    if (!open && state.status === "loading") setAnnounce(words.loading);
    setOpen((now) => !now);
  };

  // The new title sentence, which the live region says after "Showing cautious dates." or after dating the steps.
  const captionFor = (result: StepsResult, next: Choice) => {
    const dates = result.step_dates;
    const family = stepFamily(dates?.family);
    return dates && family ? captionText(dates, family, rowsOf(dates, family, packageKey, undefined), next) : "";
  };

  // Section 1's "Dates I draft for this package" (ticket 26) sets the same stored choice: one made there shows here.
  const shared = useSharedPlanDateChoice(`${api}/plan-dates`);
  useEffect(() => {
    if (shared === null) return;
    chosen.current = true;
    setChoice(fromStored(shared));
  }, [shared]);

  const choose = (next: Choice) => {
    chosen.current = true;
    setChoice(next);
    sharePlanDateChoice(`${api}/plan-dates`, stored(next));
    setAnnounce(state.status === "ready" ? `${words.showing[next]} ${captionFor(state.result, next)}` : words.showing[next]);
    if (preview) return;
    putJson(`${api}/plan-dates`, { choice: stored(next) }).then(
      () => setSaveFailed(false),
      () => {
        setSaveFailed(true);
        setAnnounce(words.choice.saveFailedSpoken);
      },
    );
  };

  const commit = () => {
    const dates = state.status === "ready" ? state.result.step_dates : null;
    if (!dates || preview) return;
    const value = start.value;
    if (!value) return setStart((now) => ({ ...now, error: "empty", status: "" }));
    if (value < dates.start_range.from || value > dates.start_range.to) return setStart((now) => ({ ...now, error: "range", status: "" }));
    const serial = ++commits.current;
    const status = words.start.dating(formatDate(value));
    setStart((now) => ({ ...now, error: null, committing: true, slow: false, status }));
    setAnnounce(status);
    const slow = setTimeout(() => commits.current === serial && setStart((now) => ({ ...now, slow: true })), SLOW_MS);
    // The page's as-of date and section 1's criteria date the steps from the comparables the first answer used.
    const query = new URLSearchParams(criteria);
    if (asOf) query.set("asof", asOf);
    putJson<StepsResult>(`${api}/step-start${query.size ? `?${query.toString()}` : ""}`, { start_date: value }).then(
      (result) => {
        if (commits.current !== serial) return;
        clearTimeout(slow);
        setState({ status: "ready", result });
        setStart((now) => ({ ...now, committing: false, slow: false, status: "" }));
        setAnnounce(captionFor(result, choice));
      },
      () => {
        if (commits.current !== serial) return;
        clearTimeout(slow);
        setStart((now) => ({ ...now, committing: false, slow: false, error: "failed", status: "" }));
      },
    );
  };

  // The row whose list the drawer shows, or whose list a package in the drawer was opened from, takes the tint.
  const id = evidenceIn(here.search);
  const openId = id && isStepList(id) ? id : from?.id === id && from?.list ? from.list.id : null;
  const onOpen: Opener = (listId, element) =>
    openEvidence(listId, { serial: null, sentence: null, marker: element, runId: null, fallback: heading.current });

  return (
    <StepsView
      state={state}
      packageKey={packageKey}
      kind={kind}
      open={open}
      onToggle={toggle}
      choice={choice}
      onChoose={choose}
      start={start}
      onStartChange={(value) => setStart((now) => ({ ...now, value, error: null }))}
      onCommitStart={commit}
      preview={preview}
      saveFailed={saveFailed}
      openId={openId}
      onOpen={onOpen}
      headingRef={heading}
      announce={announce}
      asOf={asOf}
    />
  );
}
