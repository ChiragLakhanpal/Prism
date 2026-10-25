// Section 2 of the package workspace, "Planned date for each step" (ticket 27; the 27 brief). A Collapsed section,
// closed on every load, whose summary line names the family's steps and the stage that ran longest, from the tool.
// Opened, it holds the start-date field when the package has no plan dates, the choice of dates (cautious by
// default, middle the other), the step table and its notes.
//
// - Every date, day count and count is estimate_time's (src/strata/estimates/step_dates.py). The browser adds no
//   days and divides nothing; both choices come in one answer, so switching renders in the same frame.
// - The steps' labels, STEP's full names and their phrases come from the step-label registry (web/src/steps.ts).
//   From a 768 px page area each label opens a DefinitionWindow with STEP's full name, which a screen reader also
//   hears with the label; below it the table becomes a list and the full name is printed under each label.
// - A step that abstains says so in its own row, in the first person. Under 20 comparable packages in all, the
//   section shows the steps and their counts with no dates and no controls.
// - Strata writes planned dates only: no cell, caption or note holds an actual date.
// - A count, a planned date, or the summary's "{n} of {m}" opens the evidence drawer at its list, and the row whose
//   list is open takes the tint fill.
import { useEffect, useId, useRef, useState, type ReactNode, type Ref } from "react";
import { CircleDashed, CircleX } from "lucide-react";
import { copy } from "../copy";
import { ApiError, getJson, putJson } from "../lib/api";
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
import { SegmentedControl } from "./SegmentedControl";
import { Source } from "./Source";
import { DefinitionWindow } from "./Term";
import { TextLink } from "./TextLink";

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

type Opener = (id: string, element: HTMLElement) => void;

// ── Small helpers ────────────────────────────────────────────────────────

const number = (value: number) => <Num value={value} options={{ compact: false }} />;
const shortDate = (iso: string) => <Num date={iso} style="table" />;

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

// A Num's click handler that hands on the button it was clicked on, so the drawer can give focus back to it. React
// passes the click to Num's onOpen as its first argument, as RisksSection's counts rely on.
function opener(open: (element: HTMLElement) => void): () => void {
  return ((event?: { currentTarget?: unknown }) => {
    const element = event?.currentTarget;
    if (element instanceof HTMLElement) open(element);
  }) as () => void;
}

// How many steps abstain for want of comparables, which the summary's partial sentence counts. A step whose
// comparables had not reached it yet says so in its own row, not here.
const thin = (dates: StepDates) => dates.steps.filter((step) => step.abstain_reason === "few_comparables").length;

// ── The summary line ─────────────────────────────────────────────────────

function Summary({ dates, packageKey, onOpen }: { dates: StepDates; packageKey: string; onOpen: Opener }) {
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
  const abstaining = thin(dates);
  const dateable = dates.steps.filter((step) => !step.is_anchor).length;
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
                    onOpen: opener((element) => onOpen(longestListId(packageKey), element)),
                  }}
                />
              ),
            }}
          />
        </>
      )}
      {abstaining > 0 && (
        <>
          {" "}
          {abstaining >= dateable
            ? words.summaryPartialAll(formatCount(count))
            : words.summaryPartial(formatCount(abstaining), formatCount(count))}
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
            "h-11 w-full rounded-md border bg-surface px-3 text-body text-ink tabular-nums @md/page:w-48",
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

type Row = {
  step: StepDate;
  entry: StepEntry;
  previous: StepEntry | null;
  listId: string;
};

function rowsOf(dates: StepDates, family: StepFamily, packageKey: string): Row[] {
  return dates.steps.map((step, index) => ({
    step,
    entry: familyStep(family, step.step_key) ?? { key: step.step_key, label: step.step_key, step_name: step.step_key, phrase: step.step_key, stage: null },
    previous: index > 0 ? familyStep(family, dates.steps[index - 1].step_key) : null,
    listId: stepListId(packageKey, step.step_key),
  }));
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

// The planned date in the choice shown, or why there is none.
function Planned({ row, dates, family, choice, onOpen, slow }: { row: Row; dates: StepDates; family: StepFamily; choice: Choice; onOpen: Opener; slow: boolean }) {
  const { step, entry, previous } = row;
  const point = step[choice];
  if (!point) return null;
  if (step.is_anchor) {
    return point.planned_date ? (
      <span className="flex flex-col" data-planned={point.planned_date}>
        <span className="text-body font-semibold text-ink tabular-nums">{formatDate(point.planned_date, { style: "table" })}</span>
        <span className="text-caption text-ink-muted">{words.yours}</span>
      </span>
    ) : (
      <span className="flex flex-col">
        <span className="text-small text-ink-muted">{words.undated}</span>
        <span className="text-caption text-ink-muted">{words.undatedStart}</span>
      </span>
    );
  }
  const days = dayCaption(point, previous);
  const n = step.comparables_n ?? 0;
  switch (step.abstain_reason) {
    case "few_comparables":
      return (
        <Abstention>
          {n === 0 ? words.abstainNone : n === 1 ? words.abstainOne : <Fill template={words.abstain} slots={{ n: number(n) }} />}
        </Abstention>
      );
    case "not_reached":
      return <Abstention>{words.notReached}</Abstention>;
    case "not_in_plan":
      return <Abstention>{words.notInPlan}</Abstention>;
    case "needs_earlier_step":
      return <Abstention days={days}>{words.needsEarlier(previous?.phrase ?? "")}</Abstention>;
  }
  if (slow) return <span aria-hidden="true" className="block h-4 w-24 rounded-xs bg-surface-2" data-skeleton />;
  const slots = {
    longer: number(point.longer ?? 0),
    n: number(n),
    in10: number(point.in10 ?? 0),
    step: entry.phrase,
    days: number(point.days ?? 0),
    previous: previous?.phrase ?? "",
    first: family.steps[0].phrase,
  };
  const tip = !point.planned_date
    ? words.tips.dateUndated
    : point.days_relation === "after_previous"
      ? words.tips.dateDuration
      : point.days_relation === "before_plan"
        ? words.tips.dateBefore
        : words.tips.dateDelay;
  const check: NumCheck = { tooltip: <Fill template={tip} slots={slots} />, onOpen: opener((element) => onOpen(row.listId, element)) };
  return (
    <span data-planned={point.planned_date ?? "undated"}>
      <NumLines
        check={check}
        first={point.planned_date ? shortDate(point.planned_date) : words.undated}
        second={days}
        firstClassName={point.planned_date ? "text-body font-semibold text-ink" : "text-small text-ink-muted"}
        secondClassName="text-caption text-ink-muted"
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

function Comparables({ row, onOpen }: { row: Row; onOpen: Opener }) {
  const { step, entry } = row;
  if (step.is_anchor) return <span className="text-small text-ink-muted">{words.comparablesStart}</span>;
  const n = step.comparables_n ?? 0;
  if (n === 0) return <span className="text-small text-ink-muted">{words.comparablesNone}</span>;
  return (
    <Num
      value={n}
      options={{ compact: false }}
      className="text-small"
      check={{
        tooltip: words.tips.count(entry.phrase),
        name: words.countName(String(n), entry.label),
        onOpen: opener((element) => onOpen(row.listId, element)),
      }}
    />
  );
}

// The step's label: from a 768 px page area a DefinitionWindow with STEP's full name, which a screen reader hears
// with the label (aria-describedby); below it the name is printed (the list's own rendering).
function StepLabel({ row }: { row: Row }) {
  const nameId = useId();
  return (
    <>
      <DefinitionWindow
        label={row.entry.label}
        title={row.entry.label}
        describedBy={nameId}
        triggerClassName="text-small font-semibold text-ink-heading"
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
  openId: string | null;
  onOpen: Opener;
  slow: boolean;
  caption: ReactNode;
  captionId: string;
};

function StepTable({ dates, family, rows, choice, kind, openId, onOpen, slow, caption }: Body) {
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
              {choice === "cautious" ? words.columns.cautious : words.columns.middle}
              <span className={note}>{choice === "cautious" ? words.columns.cautiousNote(String(dates.cautious_in10)) : words.columns.middleNote}</span>
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
            <th scope="row" className="px-3 py-3 text-left align-top font-normal">
              <StepLabel row={row} />
              {dating && dates.longest?.step_key === row.step.step_key && <LongestMark dates={dates} />}
            </th>
            {plan && (
              <td className="px-3 py-3 align-top">
                <PlanDate step={row.step} />
              </td>
            )}
            {dating && (
              <td className="px-3 py-3 align-top">
                <Planned row={row} dates={dates} family={family} choice={choice} onOpen={onOpen} slow={slow} />
              </td>
            )}
            <td className="px-3 py-3 text-right align-top">
              <Comparables row={row} onOpen={onOpen} />
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function LongestMark({ dates }: { dates: StepDates }) {
  const longest = dates.longest!;
  return (
    <span className="mt-1 block text-caption text-ink-muted" data-longest-mark>
      <Fill template={words.longest} slots={{ nm: <Num part={longest.n} whole={longest.m} show="count" /> }} />
    </span>
  );
}

function StepList({ dates, family, rows, choice, kind, openId, onOpen, slow, caption, captionId }: Body) {
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
          {dating && dates.longest?.step_key === row.step.step_key && <LongestMark dates={dates} />}
          <dl className="mt-2 grid grid-cols-[minmax(0,1fr)_auto] gap-x-2 gap-y-2">
            {kind === "step" && (
              <>
                <dt className={label}>{words.columns.plan}</dt>
                <dd className="text-right">
                  <PlanDate step={row.step} />
                </dd>
              </>
            )}
            {dating && (
              <>
                <dt className={cx(label, row.step.abstain_reason && "col-span-2")}>
                  {choice === "cautious" ? words.columns.cautious : words.columns.middle}
                </dt>
                {/* A sentence takes the item's full width under its label, so the labels keep their column. */}
                <dd className={row.step.abstain_reason ? "col-span-2" : "flex justify-end text-right"}>
                  <Planned row={row} dates={dates} family={family} choice={choice} onOpen={onOpen} slow={slow} />
                </dd>
              </>
            )}
            <dt className={label}>{words.columns.comparables}</dt>
            <dd className="text-right">
              <Comparables row={row} onOpen={onOpen} />
            </dd>
          </dl>
        </li>
      ))}
    </ol>
    </>
  );
}

// ── The caption and the notes ────────────────────────────────────────────

function Caption({ dates, family, rows, choice, onOpen }: { dates: StepDates; family: StepFamily; rows: Row[]; choice: Choice; onOpen: Opener }) {
  const count = family.steps.length;
  let title: ReactNode;
  if (dates.abstain_all) title = words.captionAbstain(family.family_name);
  else if (dates.needs_start_date) title = words.captionUndated;
  else {
    const signed = rows.find((row) => row.step.step_key === family.longest_through);
    const point = signed?.step[choice];
    const dated = rows.filter((row) => !row.step.is_anchor && row.step[choice]?.planned_date).length;
    if (signed && point?.planned_date) {
      const n = signed.step.comparables_n ?? 0;
      const slots = {
        longer: number(point.longer ?? 0), n: number(n), in10: number(point.in10 ?? 0), step: signed.entry.phrase,
        days: number(point.days ?? 0), previous: signed.previous?.phrase ?? "", first: family.steps[0].phrase,
      };
      const tip = point.days_relation === "after_previous" ? words.tips.dateDuration : point.days_relation === "before_plan" ? words.tips.dateBefore : words.tips.dateDelay;
      title = (
        <Fill
          template={words.captionSigned[choice]}
          slots={{
            date: (
              <Num
                date={point.planned_date}
                check={{ tooltip: <Fill template={tip} slots={slots} />, onOpen: opener((element) => onOpen(signed.listId, element)) }}
              />
            ),
          }}
        />
      );
    } else title = dated === 0 ? words.captionNone : words.captionPartial(formatCount(dated), formatCount(count));
  }
  return (
    <span className="flex flex-col gap-1">
      <span className="block text-title text-ink-heading" data-step-caption>
        {title}
      </span>
      <span className="block text-caption text-ink-muted">{words.count(formatCount(count))}</span>
    </span>
  );
}

function Notes({ dates, family, choice, kind, result, asOf }: { dates: StepDates; family: StepFamily; choice: Choice; kind: "step" | "planned"; result: StepsResult; asOf: string | null }) {
  const track = dates.abstain_all ? null : dates.track_record?.[choice] ?? null;
  const counted = { tooltip: words.tips.counted };
  const coverage = dates.coverage;
  const link = <TextLink href={dataReadinessHref(coverage.sources, "estimate_time")}>{words.coverageLink}</TextLink>;
  const covered = (value: number) => <Num value={value} options={{ compact: false }} check={counted} inCaption />;
  const date = asOf ?? result.records_through;
  return (
    <div className="mt-4 flex max-w-prose flex-col gap-2 text-caption text-ink-muted" data-step-notes>
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
                  check={{ tooltip: <Fill template={words.tips.track} slots={{ year: <Num year={track.year} />, run: <span className="font-mono">{track.run_id ?? ""}</span> }} /> }}
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
        {coverage.missing > 0 ? (
          <Fill template={words.coverage} slots={{ used: covered(coverage.used), total: covered(coverage.total), missing: covered(coverage.missing) }} />
        ) : (
          <Fill template={words.coverageAll} slots={{ total: covered(coverage.total) }} />
        )}{" "}
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
  let summary: ReactNode = null;
  if (state.status === "error") {
    const code = state.error?.body?.trace_id;
    summary = (
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
                <Fill template={words.errorCode} slots={{ code: <span className="font-mono">{code}</span> }} />
              </p>
            )}
          </div>
        }
      >
        {words.error}
      </Alert>
    );
  } else if (dates) {
    summary = <Summary dates={dates} packageKey={packageKey} onOpen={onOpen} />;
  }
  const rows = dates && family ? rowsOf(dates, family, packageKey) : [];
  const body =
    state.status === "loading" ? (
      <StepsSkeleton />
    ) : dates && family && result ? (
      <>
        <p className="max-w-prose text-body text-ink" data-step-intro>
          {dates.abstain_all ? (
            <>
              {dates.abstain_all.n === 1 ? words.summaryAbstainOne : <Fill template={words.summaryAbstain} slots={{ n: number(dates.abstain_all.n) }} />}{" "}
              <Fill template={words.introAbstain(family.family_name)} slots={{ min: number(dates.min_comparables) }} />
            </>
          ) : dates.basis === "delay" ? (
            words.introDelay(family.family_name)
          ) : (
            words.introDuration(family.family_name)
          )}
        </p>
        {!dates.abstain_all && (
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
        <div className="mt-6" aria-busy={start.committing || undefined}>
          <div className="hidden @md/page:block">
            <StepTable
              dates={dates} family={family} rows={rows} choice={choice} kind={kind} openId={openId} onOpen={onOpen} slow={start.slow}
              caption={<Caption dates={dates} family={family} rows={rows} choice={choice} onOpen={onOpen} />} captionId={`${captionId}-wide`}
            />
          </div>
          <div className="@md/page:hidden">
            <StepList
              dates={dates} family={family} rows={rows} choice={choice} kind={kind} openId={openId} onOpen={onOpen} slow={start.slow}
              caption={<Caption dates={dates} family={family} rows={rows} choice={choice} onOpen={onOpen} />} captionId={captionId}
            />
          </div>
        </div>
        <Notes dates={dates} family={family} choice={choice} kind={kind} result={result} asOf={asOf} />
      </>
    ) : null;
  return (
    <CollapsedSection
      id="planned-dates"
      eyebrow={words.eyebrow}
      number={words.number}
      heading={words.heading}
      summary={summary}
      loading={state.status === "loading"}
      canOpen={state.status === "loading" || Boolean(family)}
      open={open}
      onToggle={onToggle}
      showLabel={words.show}
      hideLabel={words.hide}
      busy={state.status === "loading" && open}
      headingRef={headingRef}
      stateKey={state.status === "ready" ? (dates?.abstain_all ? "abstain" : family ? (dates?.basis ?? "ready") : (dates?.family_reason ?? "none")) : state.status}
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

function StepsSkeleton() {
  return (
    <div aria-hidden="true" className="flex flex-col gap-4">
      <span className="flex flex-col gap-2">
        <span className="block h-4 w-9/10 rounded-xs bg-surface-2" />
        <span className="block h-4 w-9/20 rounded-xs bg-surface-2" />
      </span>
      <span className="flex flex-col">
        {Array.from({ length: 6 }, (_, index) => (
          <span key={index} className="block h-12 border-t border-line" />
        ))}
      </span>
    </div>
  );
}

// ── The section on a page: it reads, chooses, dates and opens ───────────

export function StepsSection({ packageKey, kind, rerunKey = "" }: { packageKey: string; kind: "step" | "planned"; rerunKey?: string }) {
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
    const query = new URLSearchParams();
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
  }, [api, asOf, view, rerunKey, attempt]);

  // A link to #planned-dates opens the section and moves focus to its heading.
  useEffect(() => {
    if (window.location.hash === "#planned-dates") heading.current?.focus();
  }, []);

  // Hold each step's list for the drawer while the section shows it.
  useEffect(() => {
    if (state.status === "ready") rememberStepLists(packageKey, state.result);
  }, [state, packageKey]);

  const toggle = () => {
    if (!open && state.status === "loading") setAnnounce(words.loading);
    setOpen((now) => !now);
  };

  const choose = (next: Choice) => {
    chosen.current = true;
    setChoice(next);
    setAnnounce(words.showing[next]);
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
    putJson<StepsResult>(`${api}/step-start`, { start_date: value }).then(
      (result) => {
        if (commits.current !== serial) return;
        clearTimeout(slow);
        setState({ status: "ready", result });
        setStart((now) => ({ ...now, committing: false, slow: false, status: "" }));
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
