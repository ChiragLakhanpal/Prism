// A plan check row's records in the evidence drawer (ticket 100; DESIGN.md section 5, Plan check table): what a
// row's reference opens. The drawer's head names the row by its reference and says what it is ("Activity in the
// Northern Water Works Development Agency plan of October 9, 2026"); under it, each mark's badge and the reasons'
// sentences, as the row gives them, then "What I checked", the values each reason rests on, then "From the plan
// row", the row's STEP fields under STEP's names, its source line, and "Open the activity" and "See the past range".
//
// Every value is check_plan's, as the page already holds it (lib/planRows.ts): the screen works nothing out. A value
// the plan row does not give, such as a contract signed date, says so.
import { useId, type ReactNode } from "react";
import { copy } from "../copy";
import type { EvidenceEvent } from "../lib/answer";
import type { Activity, Reason } from "../lib/api";
import { cx } from "../lib/cx";
import { formatDate } from "../lib/format";
import { Fill } from "./Fill";
import { MonoWords } from "./MonoWords";
import { Num } from "./Num";
import { ActivityLinks, BADGE, MarkReasons, PlanSource, type CheckedPlan } from "./PlanCheck";
import { Source } from "./Source";
import { StatusBadge } from "./StatusBadge";

const words = copy.checkPlan;
const fields = copy.evidence.summaryRecordFields;

type Records = { activity: Activity; result: CheckedPlan & { upload?: { uploaded_on: string; upload_id: string } } };

// What each reason rests on, in the order the records list it (config/tools.toml, check_plan's reason codes). A row
// with no reason lists what the checks read from it, and so does a reason this list does not name, such as an
// upload's reading notes (unread_date, unread_amount, duplicate_ref) or a code added to config/tools.toml later, so
// "What I checked" never stands over nothing (ticket 100's review, F1).
const CHECKED: Record<string, string[]> = {
  completion_passed_no_contract: ["planned_completion_on", "planned_completion_plan_date", "signed_on", "closing_date", "as_of"],
  pending_near_closing: ["process_status", "closing_date", "days_to_close", "as_of"],
  pending_on_closing_day: ["process_status", "closing_date", "as_of"],
  pending_after_closing: ["process_status", "closing_date", "as_of"],
  signed_late_over_estimate: ["planned_signing_on", "planned_signing_plan_date", "signed_on", "days_late", "actual_amount_usd", "estimated_amount_usd", "ratio"],
  signed_over_estimate: ["signed_on", "actual_amount_usd", "estimated_amount_usd", "ratio"],
  method_differs_from_reference: ["method", "reference_method_code"],
  actual_amount_zero: ["process_status", "actual_amount_usd"],
  no_planned_date: ["step"],
  no_estimate: ["estimated_amount_usd", "actual_amount_usd"],
  no_method: ["method"],
};
const UNMARKED = ["process_status", "planned_completion_on", "signed_on", "as_of"];

// A line's label: a check's own words, or the STEP field's one label (evidence.summaryRecordFields).
const label = (key: string) => words.checkedFields[key] ?? fields[key] ?? key;

const date = (iso: string) => <Num date={iso} style="table" />;
const usd = (text: string) => <Num value={Number(text)} options={{ decimals: 2, compact: false }} />;

// The plan a planned date came from: "Apr 21, 2021", or "your upload of Oct 20, 2026" on an upload's row that no
// published plan lists, where check_plan measured from the upload's own date.
function planOf(on: string | null | undefined, result: Records["result"]): ReactNode | null {
  if (!on) return null;
  const upload = result.upload;
  return upload && on === upload.uploaded_on.slice(0, 10) ? <Fill template={words.yourUploadOf} slots={{ date: date(on) }} /> : date(on);
}

// One value of "What I checked", from the reason when it gives it and from the row otherwise; null leaves the line out.
function checkedValue(key: string, reason: Reason | null, row: Activity, result: Records["result"]): ReactNode | null {
  const notInRow = <span className="text-ink-muted">{words.notInRow}</span>;
  switch (key) {
    case "planned_signing_plan_date":
      return planOf(reason?.planned_signing_plan_date, result);
    case "planned_completion_plan_date":
      return planOf(reason?.planned_completion_plan_date, result);
    case "planned_completion_on": {
      const on = reason?.planned_completion_on ?? row.planned_completion_on;
      return on ? date(on) : notInRow;
    }
    case "planned_signing_on": {
      const on = reason?.planned_signing_on ?? row.planned_signing_on;
      return on ? date(on) : notInRow;
    }
    case "signed_on": {
      const on = reason?.signed_on ?? row.signed_on;
      return on ? date(on) : notInRow;
    }
    case "days_late":
      return reason?.days_late != null ? <Num value={reason.days_late} options={{ compact: false }} /> : null;
    case "closing_date": {
      const on = reason?.closing_date ?? result.project.closing_date;
      if (!on) return null;
      const record = result.project.record_date;
      return record ? <Fill template={words.closingFrom} slots={{ date: date(on), record: date(record) }} /> : date(on);
    }
    case "days_to_close":
      return reason?.days_to_close != null ? <Num value={reason.days_to_close} options={{ compact: false }} /> : null;
    case "as_of":
      return date(result.as_of);
    case "process_status":
      return reason?.process_status ?? row.process_status ?? notInRow;
    case "actual_amount_usd": {
      const value = reason?.actual_amount_usd ?? row.actual_amount_usd;
      return value ? usd(value) : notInRow;
    }
    case "estimated_amount_usd": {
      const value = reason?.estimated_amount_usd ?? row.estimated_amount_usd;
      return value ? usd(value) : notInRow;
    }
    case "ratio":
      return reason?.ratio != null ? <Fill template={words.ratioAbout} slots={{ ratio: <Num value={reason.ratio} options={{ compact: false }} /> }} /> : null;
    case "method":
      return reason?.method ?? row.method ?? notInRow;
    case "reference_method_code":
      return reason?.reference_method_code ?? null;
    case "step":
      return reason?.step ?? null;
    default:
      return null;
  }
}

// The lines of "What I checked": each reason's values in its order, once each.
function checkedLines(row: Activity, result: Records["result"]): { key: string; value: ReactNode }[] {
  const reasons = row.marks.flatMap((mark) => mark.reasons);
  const wanted = reasons.length ? reasons.map((reason) => ({ reason, keys: CHECKED[reason.code] ?? UNMARKED })) : [{ reason: null, keys: UNMARKED }];
  const seen = new Set<string>();
  const lines: { key: string; value: ReactNode }[] = [];
  for (const { reason, keys } of wanted) {
    for (const key of keys) {
      if (seen.has(key)) continue;
      const value = checkedValue(key, reason, row, result);
      if (value === null) continue;
      seen.add(key);
      lines.push({ key, value });
    }
  }
  return lines;
}

function Pairs({ lines, kind }: { lines: { label: ReactNode; value: ReactNode; numeric?: boolean; wide?: boolean }[]; kind: string }) {
  return (
    <dl data-numbers data-records={kind} className="grid grid-cols-2 gap-x-4 gap-y-2">
      {lines.map((line, index) => (
        <div key={index} className={cx("min-w-0", line.wide && "col-span-full")}>
          <dt className="text-caption text-ink-muted">{line.label}</dt>
          <dd className={cx("text-small text-ink", line.numeric ? "whitespace-nowrap tabular-nums" : "wrap-break-word")}>{line.value}</dd>
        </div>
      ))}
    </dl>
  );
}

// The drawer's title: the row's reference, in mono, broken only at its spaces.
export function planRowTitle(evidence: EvidenceEvent): ReactNode {
  const { activity } = evidence.row as Records;
  return activity.activity_reference_no ? <MonoWords text={activity.activity_reference_no} medium /> : copy.uploadCheck.noRef;
}

// The caption under the title: "Activity in the Northern Water Works Development Agency plan of October 9, 2026", its
// date on one line, as every sentence date is.
export function planRowCaption(evidence: EvidenceEvent): ReactNode {
  const { result } = evidence.row as Records;
  return <Fill template={copy.evidence.planRowCaption} slots={{ agency: result.plan.implementing_agency, date: <Num date={result.plan.plan_date} /> }} />;
}

export function PlanRowRecords({ evidence }: { evidence: EvidenceEvent }) {
  const { activity: row, result } = evidence.row as Records;
  const checkedId = useId();
  const planId = useId();
  const ref = row.activity_reference_no;
  const plan = [
    row.description ? { label: fields.description, value: row.description, wide: true } : null,
    { label: fields.method, value: row.method ?? copy.notInPlan, wide: true },
    { label: fields.market_approach, value: row.market_approach ?? copy.notInPlan },
    { label: fields.review_type, value: row.review_type ?? copy.notInPlan },
    { label: fields.estimated_amount_usd, value: row.estimated_amount_usd ? usd(row.estimated_amount_usd) : copy.notInPlan, numeric: Boolean(row.estimated_amount_usd) },
    { label: fields.process_status, value: row.process_status ?? copy.notInPlan },
  ].filter((line) => line !== null);
  const upload = result.upload;
  const checkedOn = checkedLines(row, result);
  return (
    <div data-plan-row-records className="flex flex-col gap-4">
      <div data-row-found className="flex flex-col gap-3">
        {row.marks.length > 0 ? (
          row.marks.map((mark) => (
            <div key={mark.mark} className="flex flex-col items-start gap-2">
              <StatusBadge kind={BADGE[mark.mark]} />
              <MarkReasons mark={mark} result={result} />
            </div>
          ))
        ) : (
          <p className="text-small text-ink-muted">{result.withheld ? words.noDataNotes : words.noSignals}</p>
        )}
      </div>
      {checkedOn.length > 0 && (
        <section aria-labelledby={checkedId} className="flex flex-col gap-2">
          {/* A group of facts in the drawer is an h3 (DESIGN.md section 3; ticket 100's design review, item 9). */}
          <h3 id={checkedId} className="text-h3 text-ink-heading">
            {words.rowChecked}
          </h3>
          <Pairs kind="checked" lines={checkedOn.map((line) => ({ label: label(line.key), value: line.value }))} />
        </section>
      )}
      <section aria-labelledby={planId} className="flex flex-col gap-2">
        <h3 id={planId} className="text-h3 text-ink-heading">
          {words.rowPlan}
        </h3>
        <Pairs
          kind="plan"
          lines={plan}
        />
      </section>
      {upload ? <Source>{copy.uploadCheck.meta(formatDate(upload.uploaded_on), upload.upload_id)}</Source> : <PlanSource result={result} />}
      {ref && row.listed !== false && (
        <ActivityLinks reference={ref} pid={result.plan.project_id} className="min-h-6 border-t border-line pt-4" />
      )}
    </div>
  );
}

