// A draft of planned dates (ticket 38; the 38 brief, sections 3.5, 4.2.3 and 6.7): the one choice of dates for the
// whole draft, what the STEP rows file leaves empty, the activity overview table, then one section per activity with
// its Step table, all open, in the order of the officer's file. Every date, count and day is the server's: the page
// adds no days and counts nothing. A step's count, and its planned date, open its list of comparable packages in the
// evidence drawer, as section 2 of the package workspace does (DESIGN.md, Step table), from the list the draft keeps.
import type { ReactNode } from "react";
import { copy } from "../copy";
import type { EvidenceEvent } from "../lib/answer";
import { formatCount, formatDate } from "../lib/format";
import type { DatesActivity, DatesStep, DatesView } from "../lib/drafts";
import type { StepDate, StepListRow, StepPoint } from "../lib/steps";
import { familyStep, stepFamily, type StepFamily } from "../steps";
import { Fill } from "./Fill";
import { Num } from "./Num";
import { SegmentedControl } from "./SegmentedControl";
import { dateCheck, type Opener, type Row } from "./StepsSection";

const kind = copy.draft.kinds.step_rows;
const words = kind.dates;
const short = (iso: string) => formatDate(iso, { style: "table" });
const CHOICES = ["middle", "cautious"] as const;

// The signed contract's date opens its list, as the same date does in the activity's Step table. When the verifier
// removed the step's claim, its date and count are gone, and the cell says so instead of reading as too few packages.
function signedCell(activity: DatesActivity, choice: "middle" | "cautious", min: number, lists: Record<string, EvidenceEvent>, onOpen: Opener): ReactNode {
  if (!activity.family) return <span className="text-small text-ink-muted"><Fill template={words.notListed} slots={{ method: activity.fields.method ?? "" }} /></span>;
  const index = activity.steps.findIndex((step) => step.step_key === "contract_signed");
  const signed = index >= 0 ? activity.steps[index] : undefined;
  if (signed?.removed) return <span className="text-small text-ink-muted">{words.removed}</span>;
  const value = signed?.[choice];
  const held = signed ? rowOf(activity, index, lists) : null;
  if (value?.planned_date && held) {
    return <Num date={value.planned_date} style="table" className="text-body font-semibold" check={dateCheck(value as StepPoint, held.row, held.family, onOpen)} />;
  }
  if (value?.planned_date) return <span className="text-body font-semibold tabular-nums">{short(value.planned_date)}</span>;
  if (activity.needs_start_date) return <span className="text-small text-ink-muted">{words.undated}</span>;
  const count = signed?.comparables_n ?? activity.abstain_all?.n ?? 0;
  return (
    <span className="text-small text-ink-muted">
      <Fill template={words.signedAbstain(count)} slots={{ count: formatCount(count), min: String(min) }} />
    </span>
  );
}

// The step as the drawer's list holds it, with its place in the family, so its date and count open that list. A step
// whose list the draft does not keep (no comparable package recorded it) opens nothing.
function rowOf(activity: DatesActivity, index: number, lists: Record<string, EvidenceEvent>): { row: Row; family: StepFamily } | null {
  const step = activity.steps[index];
  const held = lists[step.list_id];
  const family = stepFamily(activity.family);
  if (!held || held.kind !== "steps" || !family) return null;
  const fallback = { key: step.step_key, label: step.label ?? step.step_key, step_name: step.step_name ?? step.step_key, phrase: step.label ?? step.step_key, stage: null };
  const previous = index > 0 ? familyStep(family, activity.steps[index - 1].step_key) : null;
  const row: Row = { step: (held.row as StepListRow).step as StepDate, entry: familyStep(family, step.step_key) ?? fallback, previous, listId: step.list_id };
  return { row, family };
}

function stepCell(step: DatesStep, choice: "middle" | "cautious", min: number, abstainAll: boolean, held: { row: Row; family: StepFamily } | null, onOpen: Opener): ReactNode {
  if (step.removed) return <span className="text-small text-ink-muted">{words.removed}</span>;
  const value = step[choice];
  if (value?.planned_date && held) {
    return <Num date={value.planned_date} style="table" check={dateCheck(value as StepPoint, held.row, held.family, onOpen)} />;
  }
  if (value?.planned_date) return <span className="tabular-nums">{short(value.planned_date)}</span>;
  if (step.abstain_reason === "not_in_plan") return <span className="text-small text-ink-muted">{words.notInPlan}</span>;
  if (step.abstain_reason === "not_reached") return <span className="text-small text-ink-muted">{words.notReached}</span>;
  if (step.abstain_reason === "needs_earlier_step") return <span className="text-small text-ink-muted">{words.undated}</span>;
  if (step.abstain_reason || abstainAll) {
    return (
      <span className="text-small text-ink-muted">
        <Fill template={words.stepAbstain} slots={{ min: String(min) }} />
      </span>
    );
  }
  return <span className="text-small text-ink-muted">{words.undated}</span>;
}

// A step's count of comparable packages: a button that opens their list when the draft keeps it.
function countCell(step: DatesStep, held: { row: Row; family: StepFamily } | null, onOpen: Opener): ReactNode {
  const n = step.comparables_n;
  if (n === null) return "";
  if (!held || n === 0) return <Num value={n} options={{ compact: false }} />;
  return (
    // Padded 12 px each side and pulled back as far, so a one-digit count's target is at least 24 px wide.
    <Num
      value={n}
      options={{ compact: false }}
      className="-mx-3 px-3 text-small"
      check={{
        tooltip: copy.stepDates.tips.count(held.row.entry.phrase),
        act: copy.stepDates.tips.listAct,
        opens: "record",
        name: copy.stepDates.countName(String(n), held.row.entry.label),
        onOpen: (element) => onOpen(step.list_id, element),
      }}
    />
  );
}

export function StepRowsDraft({ view, lists, editable, onChoice, onOpen }: {
  view: DatesView;
  // The lists of comparable packages the draft keeps, by their ids, as the evidence drawer shows them.
  lists: Record<string, EvidenceEvent>;
  // Only the author switches the choice, and only in Draft; once checked, the control becomes a sentence.
  editable: boolean;
  onChoice: (choice: "middle" | "cautious") => void;
  // Opens the drawer at a list, with the number that opened it as the place focus goes back to.
  onOpen: Opener;
}) {
  const choice = view.choice;
  const min = view.min_comparables ?? 0;
  return (
    <div className="flex flex-col gap-8" data-step-rows>
      <div className="max-w-[72ch]">
        <p className="text-body text-ink">{words.fileNote}</p>
        <ul className="mt-2 list-disc pl-4 text-small text-ink" data-left-to-people>
          {view.left_to_people.map((name) => (
            <li key={name}>{name}</li>
          ))}
        </ul>
      </div>
      {editable ? (
        <SegmentedControl
          legend={words.choiceLegend}
          value={choice}
          onChange={(value) => onChoice(value as "middle" | "cautious")}
          options={CHOICES.map((value) => ({
            value,
            label: value === "middle" ? words.choices.middle : <Fill template={words.choices.cautious} slots={{ in10: String(view.cautious_in10) }} />,
          }))}
        />
      ) : (
        <p className="text-small text-ink" data-choice-locked>
          {words.choiceLocked[choice]}
        </p>
      )}
      <div className="overflow-hidden rounded-md border border-line bg-surface">
        <table className="w-full table-fixed border-collapse text-small" data-overview>
          <caption id="activities" tabIndex={-1} className="px-3 pt-3 text-left text-h2 text-ink-heading">
            {kind.tableCaption("", "")}
          </caption>
          <thead className="bg-surface-2">
            <tr>
              <th scope="col" className="w-[46%] px-3 py-3 text-left font-semibold text-ink-heading">{kind.columns.activity}</th>
              <th scope="col" className="w-[28%] px-3 py-3 text-left font-semibold text-ink-heading">{kind.columns.signed}</th>
              <th scope="col" className="w-[26%] px-3 py-3 text-right font-semibold text-ink-heading">{kind.columns.dated}</th>
            </tr>
          </thead>
          <tbody>
            {view.activities.map((activity) => {
              const counted = { dated: activity.counts.dated[choice], total: activity.counts.steps };
              return (
                <tr key={activity.key} className="border-t border-line align-top" data-overview-row>
                  <th scope="row" className="px-3 py-3 text-left font-normal">
                    <a href={`#${activity.key}`} className="font-mono font-medium wrap-anywhere text-primary underline">
                      {activity.reference ?? activity.description}
                    </a>
                    {activity.reference ? (
                      <span className="mt-1 block text-small text-ink">{activity.description}</span>
                    ) : (
                      <span className="mt-1 block text-caption text-ink-muted">{words.noRef}</span>
                    )}
                  </th>
                  <td className="px-3 py-3">{signedCell(activity, choice, min, lists, onOpen)}</td>
                  <td className="px-3 py-3 text-right tabular-nums">
                    <Fill template={words.stepsDated} slots={{ dated: String(counted.dated), total: String(counted.total) }} />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {view.activities.map((activity) => (
        <section key={activity.key} id={activity.key} aria-labelledby={`${activity.key}-heading`} className="border-t border-line pt-6" data-activity-section>
          <h3 id={`${activity.key}-heading`} tabIndex={-1} className={activity.reference ? "font-mono text-h2 font-medium text-ink-heading" : "text-h2 text-ink-heading"}>
            {activity.reference ?? activity.description}
          </h3>
          {activity.reference ? <p className="mt-1 text-body text-ink">{activity.description}</p> : <p className="mt-1 text-caption text-ink-muted">{words.noRef}</p>}
          {!activity.family ? (
            <p className="mt-3 text-body text-ink"><Fill template={words.notListed} slots={{ method: activity.fields.method ?? "" }} /></p>
          ) : (
            <table className="mt-4 w-full table-fixed border-collapse text-small" data-step-table>
              <thead className="bg-surface-2">
                <tr>
                  <th scope="col" className="w-[32%] px-3 py-2 text-left font-semibold text-ink-heading">{words.columns.step}</th>
                  <th scope="col" className="w-[24%] px-3 py-2 text-left font-semibold text-ink-heading">{words.columns.plan}</th>
                  <th scope="col" className="w-[26%] px-3 py-2 text-left font-semibold text-ink-heading">{words.columns.planned}</th>
                  <th scope="col" className="w-[18%] px-3 py-2 text-right font-semibold text-ink-heading">{words.columns.comparables}</th>
                </tr>
              </thead>
              <tbody>
                {activity.steps.map((step, index) => {
                  const held = rowOf(activity, index, lists);
                  return (
                    <tr key={step.step_key} className="border-t border-line align-top" data-step={step.step_key}>
                      <th scope="row" className="px-3 py-2 text-left font-normal text-ink">{step.label}</th>
                      <td className="px-3 py-2 tabular-nums">{step.plan_first_date ? short(step.plan_first_date) : ""}</td>
                      <td className="px-3 py-2">{stepCell(step, choice, min, Boolean(activity.abstain_all), held, onOpen)}</td>
                      <td className="px-3 py-2 text-right tabular-nums">{countCell(step, held, onOpen)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </section>
      ))}
    </div>
  );
}
