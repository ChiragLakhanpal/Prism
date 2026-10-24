// Change tables (DESIGN.md section 5; the 21 brief, section 5.4): what changed in a Procurement Plan since
// the agency's version before it, on the version's Check a plan page under "What changed since the plan of
// {prev_date}" (#changes). Up to four short tables, one per kind of change, each with its own columns: an
// added or dropped activity with its method and estimate, a re-dated one with each moved step and both
// dates, a re-estimated one with both amounts. "Was" and "now" sit side by side. A kind with no change has
// no table, and the lead sentence says what did not change. Activities are matched on their STEP
// reference, so a reference that changed shows as dropped and added.
//
// Every count, moved day and changed amount is the route's (src/strata/server/changes.py); the screen
// writes them and works nothing out. Below a page area of 1024 px each table is cards.
import { forwardRef, type ReactNode } from "react";
import { copy } from "../copy";
import type { ChangedActivity, ChangeKind, PlanChanges } from "../lib/api";
import { cx } from "../lib/cx";
import { formatCount, formatDate, formatNumber } from "../lib/format";
import { CHANGE_KINDS as KINDS, changeList } from "../lib/changes";
import { EightColumns } from "./EightColumns";
import { Fill, Unbroken } from "./Fill";
import { Num } from "./Num";
import { MethodText } from "./PlanCheck";
import { Source } from "./Source";
import { CARD_BREAKPOINTS, CARD_FIELD, CARD_FIELDS } from "./Table";

const words = copy.changes;
const VIEW = CARD_BREAKPOINTS.lg;
const amount = (text: string) => formatNumber(Number(text), { decimals: 2, compact: false });
const blank = <span className="text-ink-muted">{copy.notInPlan}</span>;
const CELL = "px-3 py-3 align-top";

function Reference({ reference, description }: { reference: string; description: string | null }) {
  return (
    <>
      <span className="block font-mono font-medium wrap-anywhere text-ink">{reference}</span>
      {description && <span className="mt-1 block text-small text-ink">{description}</span>}
    </>
  );
}

function Head({ children, numeric, width }: { children: ReactNode; numeric?: boolean; width?: string }) {
  return (
    <th scope="col" className={cx("px-3 py-2 align-bottom font-semibold text-ink-heading", numeric ? "text-right" : "text-left", width)}>
      {children}
    </th>
  );
}

function Frame({ caption, children }: { caption: string; children: ReactNode }) {
  return (
    <div data-view="table" className={cx("mt-2 hidden overflow-hidden rounded-md border border-line bg-surface", VIEW.table)}>
      <table className="w-full table-fixed border-collapse text-small">
        <caption className="sr-only">{caption}</caption>
        {children}
      </table>
    </div>
  );
}

function Card({ heading, children }: { heading: ReactNode; children: ReactNode }) {
  return (
    <li className="rounded-md border border-line bg-surface p-4">
      <h4 className="text-small">{heading}</h4>
      <dl className={cx("mt-3 border-t border-line pt-3", CARD_FIELDS)} data-numbers>
        {children}
      </dl>
    </li>
  );
}

function Field({ label, children, wide }: { label: ReactNode; children: ReactNode; wide?: boolean }) {
  return (
    <div className={cx(CARD_FIELD, wide && "col-span-full")}>
      <dt className="text-caption text-ink-muted">{label}</dt>
      <dd className="text-small wrap-break-word text-ink">{children}</dd>
    </div>
  );
}

// Added and dropped activities: STEP's columns from the version that lists them.
function ActivityTable({ kind, rows, caption }: { kind: "added" | "dropped"; rows: ChangedActivity[]; caption: string }) {
  const columns = copy.checkPlan.columns;
  const status = kind === "dropped" ? words.col.lastStatus : columns.status;
  return (
    <>
      <Frame caption={caption}>
        <thead className="bg-surface-2">
          <tr>
            <Head width="w-[34%]">{columns.activity}</Head>
            <Head width="w-[26%]">{columns.method}</Head>
            <Head width="w-[20%]" numeric>
              {columns.estimated}
            </Head>
            <Head width="w-[20%]">{status}</Head>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.activity_reference_no} className="border-t border-line">
              <th scope="row" className={cx(CELL, "text-left font-normal")}>
                <Reference reference={row.activity_reference_no} description={row.description} />
              </th>
              <td className={CELL}>{row.method ? <MethodText method={row.method} approach={row.market_approach} /> : blank}</td>
              <td className={cx(CELL, "text-right tabular-nums")}>{row.estimated_amount_usd ? amount(row.estimated_amount_usd) : blank}</td>
              <td className={CELL}>{row.process_status ?? blank}</td>
            </tr>
          ))}
        </tbody>
      </Frame>
      <ul className={cx("mt-2 flex flex-col gap-3", VIEW.cards)}>
        {rows.map((row) => (
          <Card key={row.activity_reference_no} heading={<Reference reference={row.activity_reference_no} description={row.description} />}>
            <Field label={columns.method} wide>
              {row.method ? <MethodText method={row.method} approach={row.market_approach} /> : blank}
            </Field>
            <Field label={columns.estimated}>{row.estimated_amount_usd ? amount(row.estimated_amount_usd) : blank}</Field>
            <Field label={status} wide>
              {row.process_status ?? blank}
            </Field>
          </Card>
        ))}
      </ul>
    </>
  );
}

// "{n} later": the route's count of days between the two planned dates, which explains itself.
function Moved({ step, changes }: { step: PlanChanges["redated"][number]["steps"][number]; changes: PlanChanges }) {
  // With a date missing there is nothing to measure: the cell stays empty and says so to a screen reader.
  if (step.days === null || step.direction === null) return <span className="sr-only">{words.notMeasured}</span>;
  const days = (
    <Num
      value={step.days}
      options={{ compact: false }}
      check={{
        tooltip: (
          <Fill
            template={words.explainMoved}
            slots={{
              was: <Num date={step.was} />,
              prev: <Num date={changes.previous!.plan_date} />,
              now: step.now ? <Num date={step.now} /> : words.noDate,
              plan: <Num date={changes.plan.plan_date} />,
              days: formatNumber(step.days, { compact: false }),
            }}
          />
        ),
      }}
    />
  );
  return <Fill template={step.direction === "later" ? words.later : words.earlier} slots={{ n: days }} />;
}

function RedatedTable({ changes, caption }: { changes: PlanChanges; caption: string }) {
  return (
    <>
      <Frame caption={caption}>
        <thead className="bg-surface-2">
          <tr>
            <Head width="w-[30%]">{copy.checkPlan.columns.activity}</Head>
            <Head width="w-[22%]">{words.col.step}</Head>
            <Head width="w-[16%]">{words.col.was}</Head>
            <Head width="w-[16%]">{words.col.now}</Head>
            <Head width="w-[16%]" numeric>
              {words.col.moved}
            </Head>
          </tr>
        </thead>
        {changes.redated.map((activity) => (
          <tbody key={activity.activity_reference_no} className="border-t border-line">
            {activity.steps.map((step, index) => (
              <tr key={step.step} className={cx(index > 0 && "border-t border-line")}>
                {index === 0 && (
                  <th scope="rowgroup" rowSpan={activity.steps.length} className={cx(CELL, "text-left font-normal")}>
                    <Reference reference={activity.activity_reference_no} description={activity.description} />
                  </th>
                )}
                <td className={CELL}>{step.step}</td>
                <td className={cx(CELL, "tabular-nums")}>
                  <Num date={step.was} style="table" />
                </td>
                <td className={cx(CELL, "tabular-nums")}>{step.now ? <Num date={step.now} style="table" /> : <span className="text-ink-muted">{words.noDate}</span>}</td>
                <td className={cx(CELL, "text-right tabular-nums")}>
                  <Moved step={step} changes={changes} />
                </td>
              </tr>
            ))}
          </tbody>
        ))}
      </Frame>
      <ul className={cx("mt-2 flex flex-col gap-3", VIEW.cards)}>
        {changes.redated.map((activity) => (
          <li key={activity.activity_reference_no} className="rounded-md border border-line bg-surface p-4">
            <h4 className="text-small">
              <Reference reference={activity.activity_reference_no} description={activity.description} />
            </h4>
            <dl className="mt-3 grid grid-cols-1 gap-2 border-t border-line pt-3 text-small xs:grid-cols-[minmax(0,1fr)_minmax(0,2fr)_auto]">
              {activity.steps.map((step) => (
                <div key={step.step} className="contents">
                  <dt className="font-semibold text-ink">{step.step}</dt>
                  <dd className="text-ink">
                    {step.now ? (
                      <Fill template={words.wasNow} slots={{ was: <Num date={step.was} style="table" />, now: <Num date={step.now} style="table" /> }} />
                    ) : (
                      <Fill template={words.wasNoDate} slots={{ was: <Num date={step.was} style="table" /> }} />
                    )}
                  </dd>
                  <dd className="text-ink xs:text-right">
                    <Moved step={step} changes={changes} />
                  </dd>
                </div>
              ))}
            </dl>
          </li>
        ))}
      </ul>
    </>
  );
}

function Change({ row, changes }: { row: PlanChanges["reestimated"][number]; changes: PlanChanges }) {
  const value = (
    <Num
      written={amount(row.change)}
      check={{
        tooltip: (
          <Fill
            template={words.explainAmount}
            slots={{ was: amount(row.was), prev: <Num date={changes.previous!.plan_date} />, now: amount(row.now), plan: <Num date={changes.plan.plan_date} /> }}
          />
        ),
      }}
    />
  );
  return <Fill template={row.direction === "more" ? words.more : words.less} slots={{ amount: value }} />;
}

function ReestimatedTable({ changes, caption }: { changes: PlanChanges; caption: string }) {
  return (
    <>
      <Frame caption={caption}>
        <thead className="bg-surface-2">
          <tr>
            <Head width="w-[40%]">{copy.checkPlan.columns.activity}</Head>
            <Head width="w-[18%]" numeric>
              {words.col.wasUsd}
            </Head>
            <Head width="w-[18%]" numeric>
              {words.col.nowUsd}
            </Head>
            <Head width="w-[24%]" numeric>
              {words.col.changeUsd}
            </Head>
          </tr>
        </thead>
        <tbody>
          {changes.reestimated.map((row) => (
            <tr key={row.activity_reference_no} className="border-t border-line">
              <th scope="row" className={cx(CELL, "text-left font-normal")}>
                <Reference reference={row.activity_reference_no} description={row.description} />
              </th>
              <td className={cx(CELL, "text-right tabular-nums")}>{amount(row.was)}</td>
              <td className={cx(CELL, "text-right tabular-nums")}>{amount(row.now)}</td>
              <td className={cx(CELL, "text-right tabular-nums")}>
                <Change row={row} changes={changes} />
              </td>
            </tr>
          ))}
        </tbody>
      </Frame>
      <ul className={cx("mt-2 flex flex-col gap-3", VIEW.cards)}>
        {changes.reestimated.map((row) => (
          <Card key={row.activity_reference_no} heading={<Reference reference={row.activity_reference_no} description={row.description} />}>
            <Field label={words.col.wasUsd}>{amount(row.was)}</Field>
            <Field label={words.col.nowUsd}>{amount(row.now)}</Field>
            <Field label={words.col.changeUsd}>
              <Change row={row} changes={changes} />
            </Field>
          </Card>
        ))}
      </ul>
    </>
  );
}

// The rows of this version that changed, for the caption line in their Activity cell.
export function changedRows(changes: PlanChanges | null): Record<string, keyof typeof words.cell> {
  const found: Record<string, keyof typeof words.cell> = {};
  if (!changes || changes.state !== "compared") return found;
  for (const row of changes.added) found[row.activity_reference_no] = "added";
  for (const row of changes.redated) found[row.activity_reference_no] = "redated";
  for (const row of changes.reestimated) found[row.activity_reference_no] = found[row.activity_reference_no] === "redated" ? "both" : "reestimated";
  return found;
}

export const ChangeTables = forwardRef<HTMLHeadingElement, { changes: PlanChanges; agency: string }>(function ChangeTables({ changes, agency }, ref) {
  const counts = changes.counts!;
  const previous = changes.previous!;
  const prev = formatDate(previous.plan_date);
  const plan = formatDate(changes.plan.plan_date);
  const shown = KINDS.filter((kind) => counts[kind] > 0);
  const unchanged = KINDS.filter((kind) => counts[kind] === 0);
  const references = shown.flatMap((kind) =>
    kind === "redated" ? changes.redated.map((row) => row.activity_reference_no) : kind === "reestimated" ? changes.reestimated.map((row) => row.activity_reference_no) : [],
  );
  const overlap = new Set(references).size < references.length;
  const title = (kind: ChangeKind) => words.tableTitle[kind](counts[kind], formatCount(counts[kind], { capital: true }));
  return (
    <section aria-labelledby="changes" data-changes>
      <EightColumns prose>
        <h2 ref={ref} id="changes" tabIndex={-1} className="scroll-mt-4 text-title text-ink-heading focus:outline-none">
          <Fill template={words.title} slots={{ prev_date: <Num date={previous.plan_date} /> }} />
        </h2>
        <p className="mt-2 text-body text-ink">
          <Fill template={words.lead} slots={{ change_list: <Unbroken text={changeList(counts)} /> }} />{" "}
          {unchanged.length > 0 && <Unbroken text={words.unchanged(unchanged)} />}
        </p>
        <p className="mt-2 text-caption text-ink-muted">
          {words.matchNote}
          {overlap && (
            <>
              {" "}
              {words.overlapNote}
            </>
          )}
        </p>
      </EightColumns>
      <div className="mt-6 flex flex-col gap-8">
        {shown.map((kind) => (
          <div key={kind} data-change-kind={kind}>
            <h3 className="text-title text-ink-heading">
              <Unbroken text={title(kind)} />
            </h3>
            {kind === "added" && <ActivityTable kind="added" rows={changes.added} caption={words.caption.added(plan)} />}
            {kind === "dropped" && <ActivityTable kind="dropped" rows={changes.dropped} caption={words.caption.dropped(prev)} />}
            {kind === "redated" && <RedatedTable changes={changes} caption={words.caption.redated(prev)} />}
            {kind === "reestimated" && <ReestimatedTable changes={changes} caption={words.caption.reestimated(prev)} />}
          </div>
        ))}
      </div>
      <EightColumns prose className="mt-2">
        <Source>
          <Fill template={words.source} slots={{ agency, prev_date: <Num date={previous.plan_date} />, plan_date: <Num date={changes.plan.plan_date} /> }} />
        </Source>
      </EightColumns>
    </section>
  );
});
