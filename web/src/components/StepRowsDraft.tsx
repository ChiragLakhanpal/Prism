// A draft of planned dates (ticket 38; the 38 brief, sections 3.5, 4.2.3 and 6.7): the one choice of dates for the
// whole draft, what the STEP rows file leaves empty, the activity overview table, then one section per activity with
// its Step table, all open, in the order of the officer's file. Every date, count and day is the server's: the page
// adds no days and counts nothing.
import type { ReactNode } from "react";
import { copy } from "../copy";
import { formatCount, formatDate } from "../lib/format";
import type { DatesActivity, DatesStep, DatesView } from "../lib/drafts";
import { Fill } from "./Fill";
import { SegmentedControl } from "./SegmentedControl";

const kind = copy.draft.kinds.step_rows;
const words = kind.dates;
const short = (iso: string) => formatDate(iso, { style: "table" });
const CHOICES = ["middle", "cautious"] as const;

function signedCell(activity: DatesActivity, choice: "middle" | "cautious", min: number): ReactNode {
  if (!activity.family) return <span className="text-small text-ink-muted"><Fill template={words.notListed} slots={{ method: activity.fields.method ?? "" }} /></span>;
  const signed = activity.steps.find((step) => step.step_key === "contract_signed");
  const value = signed?.[choice];
  if (value?.planned_date) return <span className="text-body font-semibold tabular-nums">{short(value.planned_date)}</span>;
  if (activity.needs_start_date) return <span className="text-small text-ink-muted">{words.undated}</span>;
  const count = signed?.comparables_n ?? activity.abstain_all?.n ?? 0;
  return (
    <span className="text-small text-ink-muted">
      <Fill template={words.signedAbstain(count)} slots={{ count: formatCount(count), min: String(min) }} />
    </span>
  );
}

function stepCell(step: DatesStep, choice: "middle" | "cautious", min: number, abstainAll: boolean): ReactNode {
  if (step.removed) return <span className="text-small text-ink-muted">{words.removed}</span>;
  const value = step[choice];
  if (value?.planned_date) return <span className="tabular-nums">{short(value.planned_date)}</span>;
  if (step.abstain_reason === "not_in_plan") return <span className="text-small text-ink-muted">{words.notInPlan}</span>;
  if (step.abstain_reason || abstainAll) {
    return (
      <span className="text-small text-ink-muted">
        <Fill template={words.stepAbstain} slots={{ min: String(min) }} />
      </span>
    );
  }
  return <span className="text-small text-ink-muted">{words.undated}</span>;
}

function datedCount(activity: DatesActivity, choice: "middle" | "cautious") {
  const dateable = activity.steps.filter((step) => !step.is_anchor);
  return { dated: dateable.filter((step) => step[choice]?.planned_date).length, total: dateable.length };
}

export function StepRowsDraft({ view, editable, onChoice }: {
  view: DatesView;
  // Only the author switches the choice, and only in Draft; once checked, the control becomes a sentence.
  editable: boolean;
  onChoice: (choice: "middle" | "cautious") => void;
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
          <caption id="activities" tabIndex={-1} className="px-3 pt-3 text-left text-title text-ink-heading">
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
              const counted = datedCount(activity, choice);
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
                  <td className="px-3 py-3">{signedCell(activity, choice, min)}</td>
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
          <h3 id={`${activity.key}-heading`} tabIndex={-1} className={activity.reference ? "font-mono text-title font-medium text-ink-heading" : "text-title text-ink-heading"}>
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
                {activity.steps.map((step) => (
                  <tr key={step.step_key} className="border-t border-line align-top" data-step={step.step_key}>
                    <th scope="row" className="px-3 py-2 text-left font-normal text-ink">{step.label}</th>
                    <td className="px-3 py-2 tabular-nums">{step.plan_first_date ? short(step.plan_first_date) : ""}</td>
                    <td className="px-3 py-2">{stepCell(step, choice, min, Boolean(activity.abstain_all))}</td>
                    <td className="px-3 py-2 text-right tabular-nums">{step.comparables_n ?? ""}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      ))}
    </div>
  );
}
