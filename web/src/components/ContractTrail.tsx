// The contract trail (ticket 22; the 22 brief, sections 2.5 to 2.8; DESIGN.md section 5, Contract trail): an
// ordered list of five stages in procurement order, each a stage card on a rail. The rail's segment into a stage
// says how the two records are joined: solid for a shared key (the STEP reference), dashed for the scored
// "appeared together" link into the paragraphs. A stage with no record keeps its place with a dashed marker and
// card and one first-person sentence. Markers and segments are hidden from screen readers; the legend and each
// stage's source line say the same in words.
//
// Each record and each paragraph card has a citation pill at its top right, numbered in page order, which opens
// the evidence drawer at its evidence id. These pills open no hover card, since the card they sit on is the
// preview. Values inside cards are written as their source writes them, with no Num, because their source line
// sits beside them. Bids keep the award notice's order, with no sort, rank or lowest-price highlight, and a
// supplier's name is plain text, never a link. An individual consultant is never named.
import { useEffect, useRef, useState, type ReactNode } from "react";
import { CircleDashed } from "lucide-react";
import { copy } from "../copy";
import { cx } from "../lib/cx";
import { evidenceHref, evidenceIn, openEvidence, visited } from "../lib/evidence";
import { formatCount, formatDate } from "../lib/format";
import { address } from "../lib/router";
import { useStore } from "../lib/store";
import {
  amountCell,
  currencyName,
  joinWords,
  noticePrice,
  sectionName,
  stepLabel,
  topicWords,
  type AwardRecord,
  type Bid,
  type ContractRecord,
  type NoticeRecord,
  type ParagraphGroup,
  type ParagraphRecord,
  type PlanRecord,
  type Stage,
  type Trail,
} from "../lib/trail";
import { excerpt } from "../lib/sources";
import { useShows } from "../lib/view";
import { dataReadinessHref } from "../routes";
import { Button } from "./Button";
import { CitationMarker } from "./CitationMarker";
import { highlighted } from "./Document";
import { ExternalLink } from "./ExternalLink";
import { Fill } from "./Fill";
import { Source } from "./Source";
import { TextLink } from "./TextLink";

const words = copy.trail;
const table = (iso: string | null) => (iso ? formatDate(iso, { style: "table" }) : "");
const sentence = (iso: string | null) => (iso ? formatDate(iso) : "");

// The pills' numbers, in page order: each record, then each paragraph card.
export function pillNumbers(trail: Trail): Map<string, number> {
  const numbers = new Map<string, number>();
  for (const found of trail.stages) for (const record of found.records) if (!numbers.has(record.evidence_id)) numbers.set(record.evidence_id, numbers.size + 1);
  return numbers;
}

function Pill({ id, n, kind, reference, date }: { id: string; n: number; kind: string; reference: string; date: string }) {
  const opened = useStore(visited).has(id);
  const open = evidenceIn(useStore(address).search) === id;
  return (
    <CitationMarker
      n={n}
      source={words.pillSource(kind, reference, date)}
      href={evidenceHref(id)}
      evidenceId={id}
      opened={opened}
      active={open}
      onOpen={(marker) => openEvidence(id, { serial: null, sentence: null, marker, runId: null })}
    />
  );
}

// A stage on the rail: its marker, the segment to the next stage, and its card or cards. A marker sits on the first
// line of its stage's title: inside a card, below its padding; on the paragraphs stage, whose h2 has no card, at the
// h2's half line (design review F20). The segment ends at the next stage's marker.
function StageItem({ found, flat, nextFlat, joinKey, children }: { found: boolean; flat: boolean; nextFlat: boolean; joinKey?: "key" | "together"; children: ReactNode }) {
  return (
    <li data-stage-found={found} className="relative grid grid-cols-[1rem_minmax(0,1fr)] gap-x-3 @md/page:grid-cols-[1.5rem_minmax(0,1fr)] @md/page:gap-x-4">
      <span aria-hidden="true" className="relative">
        {found ? (
          <span
            data-marker
            className={cx(
              "absolute left-0.5 block size-3 rounded-pill bg-line-strong ring-2 ring-page @md/page:left-1 @md/page:size-4",
              flat ? "top-1" : "top-5 @md/page:top-7",
            )}
          />
        ) : (
          <CircleDashed className="absolute top-5 left-0.5 size-3 text-line-strong @md/page:top-5 @md/page:left-1 @md/page:size-4" />
        )}
      </span>
      {joinKey && (
        <span
          aria-hidden="true"
          data-join={joinKey}
          className={cx(
            "trail-rail top-10 left-[7px] @md/page:top-12 @md/page:left-[11px]",
            nextFlat ? "-bottom-5 @md/page:-bottom-7" : "-bottom-9 @md/page:-bottom-13",
          )}
        />
      )}
      <div className="min-w-0">{children}</div>
    </li>
  );
}

function StageCard({ title, date, pill, active, children }: { title: ReactNode; date?: ReactNode; pill?: ReactNode; active?: boolean; children: ReactNode }) {
  return (
    <section
      data-stage-card
      className={cx(
        "rounded-md border bg-surface p-4 @md/page:p-6",
        active ? "border-primary shadow-[inset_0_0_0_1px_var(--color-primary)]" : "border-line",
      )}
    >
      <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
        <h2 className="text-title text-ink-heading">{title}</h2>
        <p className="flex items-baseline gap-3 text-small text-ink-muted tabular-nums">
          {date && <span>{date}</span>}
          {pill}
        </p>
      </div>
      <div className="mt-3 flex flex-col gap-4">{children}</div>
    </section>
  );
}

function MissingCard({ title, children }: { title: ReactNode; children: ReactNode }) {
  return (
    <section data-stage-card="missing" className="rounded-md border border-dashed border-line-strong bg-surface p-4">
      <h2 className="text-title text-ink-heading">{title}</h2>
      <div className="mt-2 flex flex-col gap-2 text-small text-ink">{children}</div>
    </section>
  );
}

// A record's fields under its source's own names, in a grid that wraps; a blank reads "Not in the record".
function Fields({ fields }: { fields: { label: string; value: ReactNode; numeric?: boolean; wide?: boolean }[] }) {
  return (
    <dl className="grid grid-cols-1 gap-x-4 gap-y-3 @md/page:grid-cols-[repeat(auto-fit,minmax(10rem,1fr))]">
      {fields.map((field) => (
        <div key={field.label} className={cx("min-w-0", field.wide && "col-span-full")}>
          {/* An amount's label keeps the grid's left edge; only its value sits right, in tabular numerals. */}
          <dt className="text-caption text-ink-muted">{field.label}</dt>
          <dd className={cx("text-small wrap-break-word text-ink", field.numeric && "tabular-nums @md/page:text-right")}>
            {field.value ?? <span className="text-ink-muted">{words.blank}</span>}
          </dd>
        </div>
      ))}
    </dl>
  );
}

const mono = (text: string) => <span className="font-mono font-medium wrap-anywhere">{text}</span>;

function datasetLine(source: Record<string, string | number | null>): string {
  const name = String(source.dataset_name ?? "");
  return name ? copy.evidence.package.dataset(name, String(source.data_source ?? name), String(source.license ?? "")) : "";
}

// ── 1. In the Procurement Plan ───────────────────────────────────────────

function PlanStage({ record, n, pid, stepRef }: { record: PlanRecord; n: number; pid: string; stepRef: string }) {
  const search = useStore(address).search;
  // "See the past range" opens the package page, so it shows only where the view shows that page (the roles file's
  // [views]): the public view hides it.
  const showsPackage = useShows("package");
  const value = (key: string) => record.fields.find((field) => field.key === key)?.value ?? null;
  const fields = ["method", "market_approach", "review_type", "estimated_amount_usd", "process_status"].map((key) => ({
    label: words.plan.field[key],
    value: key === "estimated_amount_usd" && value(key) ? amountCell(String(value(key))) : value(key),
    numeric: key === "estimated_amount_usd",
  }));
  const planHref = `/projects/${pid}/procurement/${record.agency_id}/${record.plan_date}#${encodeURIComponent(stepRef)}`;
  return (
    <StageCard
      active={evidenceIn(search) === record.evidence_id}
      title={words.plan.title}
      date={<Fill template={words.plan.date} slots={{ date: table(record.plan_date) }} />}
      pill={<Pill id={record.evidence_id} n={n} kind={words.pillKind.plan} reference={stepRef} date={table(record.plan_date)} />}
    >
      <Fields fields={fields} />
      {record.steps.length > 0 && (
        <div data-plan-dates>
          <h3 className="text-small font-bold text-ink-heading">{words.plan.datesTitle}</h3>
          <table className="mt-2 hidden w-full table-fixed text-small @md/page:table">
            <caption className="clip-visually">{words.plan.datesCaption}</caption>
            <thead className="bg-surface-2 text-caption text-ink-muted">
              <tr>
                <th scope="col" className="w-2/5 px-3 py-2 text-left font-semibold">{words.plan.col.step}</th>
                <th scope="col" className="px-3 py-2 text-left font-semibold">{words.plan.col.planned}</th>
                <th scope="col" className="px-3 py-2 text-left font-semibold">{words.plan.col.actual}</th>
              </tr>
            </thead>
            <tbody>
              {record.steps.map((step) => (
                <tr key={step.step} className="border-b border-line">
                  <th scope="row" className="px-3 py-2 text-left font-semibold text-ink-heading" title={step.step}>
                    {stepLabel(step.step)}
                    <span className="clip-visually">{words.plan.stepHidden(step.step)}</span>
                  </th>
                  <td className="px-3 py-2 tabular-nums">{step.first_planned_on ? table(step.first_planned_on) : <span className="text-ink-muted">{words.plan.notInPlan}</span>}</td>
                  <td className="px-3 py-2 tabular-nums">{step.actual_on ? table(step.actual_on) : <span className="text-ink-muted">{words.plan.noneRecorded}</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <ul className="mt-2 flex flex-col gap-2 @md/page:hidden">
            {record.steps.map((step) => (
              <li key={step.step} className="text-small">
                <span className="block font-semibold text-ink-heading">{stepLabel(step.step)}</span>
                <Fill
                  template={words.plan.plannedLine}
                  slots={{
                    planned: step.first_planned_on ? table(step.first_planned_on) : words.plan.notInPlan,
                    actual: step.actual_on ? table(step.actual_on) : words.plan.noneRecorded,
                  }}
                />
              </li>
            ))}
          </ul>
          {record.first_plan_date && (
            <p className="mt-2 text-caption text-ink-muted">
              <Fill template={words.plan.datesNote} slots={{ first_plan_date: sentence(record.first_plan_date) }} />
            </p>
          )}
        </div>
      )}
      <p className="flex flex-wrap gap-x-4 gap-y-1 text-small">
        <TextLink href={planHref} className="inline-flex min-h-6 items-center">
          {words.plan.showInPlan}
          <span className="clip-visually">{words.plan.forRef(stepRef)}</span>
        </TextLink>
        {showsPackage && (
          <TextLink href={`/packages/${encodeURIComponent(stepRef)}`} className="inline-flex min-h-6 items-center" data-past-range-link={stepRef}>
            {words.plan.pastRange}
            <span className="clip-visually">{words.plan.forRef(stepRef)}</span>
          </TextLink>
        )}
      </p>
      <Source>
        <Fill
          template={words.plan.source}
          slots={{
            agency: String(record.source.implementing_agency ?? ""),
            plan_date: sentence(record.plan_date),
            disclosed: sentence(String(record.source.disclosed_on ?? record.public_from)),
          }}
        />
      </Source>
    </StageCard>
  );
}

// ── 2. Notice ────────────────────────────────────────────────────────────

function NoticeBody({ record }: { record: NoticeRecord }) {
  // The card's header gives the date it was published, so the field is not repeated (design review F25).
  const fields = record.fields.filter((field) => field.key !== "published").map((field) => ({
    label: words.notice.field[field.key] ?? field.key,
    value: field.kind === "date" ? table(field.value) : field.value,
    wide: field.key === "bid_description" || field.key === "procurement_method",
  }));
  return (
    <div data-notice={record.notice_id} className="flex flex-col gap-4">
      {record.readvertised && (
        <p className="text-small text-ink">
          <Fill template={words.notice.again} slots={{ date: sentence(record.notice_date) }} />
        </p>
      )}
      <Fields fields={fields} />
      {record.url && (
        <p>
          <ExternalLink href={record.url}>{words.notice.open}</ExternalLink>
        </p>
      )}
      <Source>
        <Fill template={words.notice.source} slots={{ id: mono(record.notice_id), date: table(record.notice_date), dataset: datasetLine(record.source) }} />
      </Source>
    </div>
  );
}

function NoticeStage({ records, numbers }: { records: NoticeRecord[]; numbers: Map<string, number> }) {
  const [first] = records;
  const open = evidenceIn(useStore(address).search);
  const active = records.some((record) => record.evidence_id === open);
  if (records.length === 1) {
    return (
      <StageCard
        active={active}
        title={words.notice.title}
        date={<Fill template={words.notice.date} slots={{ date: table(first.notice_date) }} />}
        pill={<Pill id={first.evidence_id} n={numbers.get(first.evidence_id)!} kind={words.pillKind.notice} reference={first.notice_id} date={table(first.notice_date)} />}
      >
        <NoticeBody record={first} />
      </StageCard>
    );
  }
  return (
    <StageCard active={active} title={words.notice.titleMany}>
      {records.map((record, index) => (
        <div key={record.evidence_id} className={cx(index > 0 && "border-t border-line pt-4")}>
          <div className="mb-3 flex flex-wrap items-baseline justify-between gap-x-3">
            <h3 className="text-small font-bold text-ink-heading">{record.notice_type}</h3>
            <p className="flex items-baseline gap-3 text-small text-ink-muted tabular-nums">
              <Fill template={words.notice.date} slots={{ date: table(record.notice_date) }} />
              <Pill id={record.evidence_id} n={numbers.get(record.evidence_id)!} kind={words.pillKind.notice} reference={record.notice_id} date={table(record.notice_date)} />
            </p>
          </div>
          <NoticeBody record={record} />
        </div>
      ))}
    </StageCard>
  );
}

// ── 3. Bids ──────────────────────────────────────────────────────────────

// A bidder as the notice names it. A name the fetch took out as a person's contact detail reads as removed, not as
// missing, since the notice did name it.
function bidder(bid: Bid): ReactNode {
  if (bid.is_individual_consultant) return words.bids.individual;
  if (bid.is_joint_venture) return <Fill template={words.bids.jvUnnamed} slots={{ members: joinWords(bid.members, copy.activity.join) }} />;
  return bid.name ?? <span className="text-ink-muted">{copy.evidence.contactRemoved}</span>;
}

function result(bid: Bid): ReactNode {
  if (bid.outcome === "awarded") return <span className="font-semibold">{words.bids.awarded}</span>;
  if (bid.outcome === "not_awarded") return words.bids.notAwarded;
  if (bid.outcome === "rejected") return bid.reason ? <Fill template={words.bids.rejected} slots={{ reason: bid.reason }} /> : words.bids.rejectedNoReason;
  return words.bids.noResult;
}

const price = (value: string | null) => noticePrice(value) ?? <span className="text-ink-muted">{words.bids.notInNotice}</span>;

function BidsTable({ record }: { record: AwardRecord }) {
  const currency = record.currency ?? "";
  // The price columns carry the notice's own names, such as "Read Out Price" (DESIGN.md section 7, rule 17).
  const heads = {
    bidder: record.proposals ? words.bids.col.consultant : words.bids.col.bidder,
    opening: words.bids.colCurrency(record.labels.price_at_opening ?? words.bids.col.opening, currency),
    evaluated: words.bids.colCurrency(record.labels.evaluated_price ?? words.bids.col.evaluated, currency),
    result: words.bids.col.result,
  };
  return (
    <div data-bids={record.notice_id}>
      <p className="text-caption text-ink-muted">{words.bids.count(record.bid_count, formatCount(record.bid_count), record.proposals)}</p>
      <table className="mt-2 hidden w-full table-fixed text-small @md/page:table">
        <caption className="clip-visually">
          <Fill template={words.bids.caption} slots={{ id: record.notice_id }} />
        </caption>
        <thead className="bg-surface-2 text-caption text-ink-muted">
          <tr>
            <th scope="col" className="w-[34%] px-3 py-2 text-left font-semibold">{heads.bidder}</th>
            <th scope="col" className="w-[20%] px-3 py-2 text-right font-semibold">{heads.opening}</th>
            <th scope="col" className="w-[20%] px-3 py-2 text-right font-semibold">{heads.evaluated}</th>
            <th scope="col" className="w-[26%] px-3 py-2 text-left font-semibold">{heads.result}</th>
          </tr>
        </thead>
        <tbody>
          {record.bids.map((bid) => (
            <tr key={bid.bid} data-bid={bid.bid} className="border-b border-line align-top">
              <th scope="row" className="px-3 py-2 text-left font-normal wrap-break-word text-ink">{bidder(bid)}</th>
              <td className="px-3 py-2 text-right tabular-nums wrap-anywhere">{price(bid.price_at_opening)}</td>
              <td className="px-3 py-2 text-right tabular-nums wrap-anywhere">{price(bid.evaluated_price)}</td>
              <td className="px-3 py-2 text-left">{result(bid)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <ul className="mt-2 flex flex-col gap-3 @md/page:hidden">
        {record.bids.map((bid) => (
          <li key={bid.bid} data-bid-card={bid.bid} className="rounded-md border border-line p-3">
            <p className="text-small font-semibold text-ink-heading">{bidder(bid)}</p>
            {/* The two prices side by side on 120 px columns, as Tables asks for a card with two numbers. */}
            <dl className="mt-2 grid grid-cols-[repeat(auto-fit,minmax(7.5rem,1fr))] gap-x-4 gap-y-2 text-small">
              <div>
                <dt className="text-caption text-ink-muted">{heads.opening}</dt>
                <dd className="tabular-nums wrap-anywhere">{price(bid.price_at_opening)}</dd>
              </div>
              <div>
                <dt className="text-caption text-ink-muted">{heads.evaluated}</dt>
                <dd className="tabular-nums wrap-anywhere">{price(bid.evaluated_price)}</dd>
              </div>
              <div className="col-span-full">
                <dt className="text-caption text-ink-muted">{heads.result}</dt>
                <dd>{result(bid)}</dd>
              </div>
            </dl>
          </li>
        ))}
      </ul>
      {currency && (
        <p className="mt-2 text-caption text-ink-muted">
          <Fill template={words.bids.currency} slots={{ currency: currencyName(currency) }} />
        </p>
      )}
      {record.lists_scores && <p className="mt-2 text-small text-ink">{words.bids.noScores}</p>}
    </div>
  );
}

function AwardBody({ record }: { record: AwardRecord }) {
  return (
    <div className="flex flex-col gap-4">
      {record.bids.length > 0 && <BidsTable record={record} />}
      {record.url && (
        <p>
          <ExternalLink href={record.url}>{words.bids.open}</ExternalLink>
        </p>
      )}
      <Source>
        <Fill template={words.bids.source} slots={{ id: mono(record.notice_id), date: table(record.notice_date), dataset: datasetLine(record.source) }} />
      </Source>
    </div>
  );
}

// The bids of each award notice. Two or more notices, one for each of an activity's contracts, share one card, each
// under its own h3, as several notices do (design review F10).
function BidsStage({ records, numbers }: { records: AwardRecord[]; numbers: Map<string, number> }) {
  const open = evidenceIn(useStore(address).search);
  const [first] = records;
  const title = first.proposals ? words.bids.titleProposals : words.bids.title;
  const pill = (record: AwardRecord) => (
    <Pill id={record.evidence_id} n={numbers.get(record.evidence_id)!} kind={words.pillKind.award_notice} reference={record.notice_id} date={table(record.notice_date)} />
  );
  if (records.length === 1) {
    return (
      <StageCard active={open === first.evidence_id} title={title} date={<Fill template={words.bids.date} slots={{ date: table(first.notice_date) }} />} pill={pill(first)}>
        <AwardBody record={first} />
      </StageCard>
    );
  }
  return (
    <StageCard active={records.some((record) => record.evidence_id === open)} title={title}>
      {records.map((record, index) => (
        <div key={record.evidence_id} data-award={record.notice_id} className={cx(index > 0 && "border-t border-line pt-4")}>
          <div className="mb-3 flex flex-wrap items-baseline justify-between gap-x-3">
            <h3 className="text-small font-bold text-ink-heading">
              <Fill template={words.bids.noticeHeading} slots={{ id: mono(record.notice_id) }} />
            </h3>
            <p className="flex items-baseline gap-3 text-small text-ink-muted tabular-nums">
              <Fill template={words.bids.date} slots={{ date: table(record.notice_date) }} />
              {pill(record)}
            </p>
          </div>
          <AwardBody record={record} />
        </div>
      ))}
    </StageCard>
  );
}

// ── 4. Contract ──────────────────────────────────────────────────────────

// A contract's supplier, as the bids table writes a bidder: a joint venture names its members the same way.
function supplierText(record: ContractRecord): ReactNode {
  const supplier = record.supplier;
  if (supplier.is_individual_consultant) return words.bids.individual;
  if (!supplier.name) return null;
  return supplier.is_joint_venture && supplier.members.length > 1 ? (
    <Fill template={words.bids.jvUnnamed} slots={{ members: joinWords(supplier.members, copy.activity.join) }} />
  ) : (
    supplier.name
  );
}

function ContractBody({ record }: { record: ContractRecord }) {
  const currency = record.currency;
  const fields = [
    { label: words.contract.field.supplier, value: supplierText(record), wide: true },
    { label: words.contract.field.supplier_country, value: record.supplier.country },
    {
      label: !currency || currency === "USD" ? words.contract.field.signedAmountUsd : words.contract.field.signedAmount(currency),
      value: record.amount ? amountCell(record.amount) : null,
      numeric: true,
    },
    { label: words.contract.field.contract_reference, value: mono(record.contract_reference) },
    { label: words.contract.field.contract_description, value: record.description, wide: true },
  ];
  return (
    <div data-contract={record.contract_id} className="flex flex-col gap-4">
      {record.from_notice && (
        <p className="text-small text-ink">
          <Fill template={words.contract.fromNotice} slots={{ currency: currencyName(currency) }} />
        </p>
      )}
      <Fields fields={fields} />
      <Source>
        {record.from_notice ? (
          <Fill
            template={words.contract.sourceNotice}
            slots={{ id: mono(record.award_notice_id ?? record.contract_reference), date: table(record.public_from), dataset: datasetLine(record.source) }}
          />
        ) : (
          <Fill template={words.contract.source} slots={{ reference: mono(record.contract_reference), date: table(record.signed_on), dataset: datasetLine(record.source) }} />
        )}
      </Source>
    </div>
  );
}

function ContractStage({ records, numbers }: { records: ContractRecord[]; numbers: Map<string, number> }) {
  const open = evidenceIn(useStore(address).search);
  return (
    <StageCard
      active={records.some((record) => record.evidence_id === open)}
      title={records.length > 1 ? words.contract.titleMany : words.contract.title}
      date={records.length === 1 ? <Fill template={words.contract.date} slots={{ date: table(records[0].signed_on) }} /> : undefined}
      pill={
        records.length === 1 ? (
          <Pill id={records[0].evidence_id} n={numbers.get(records[0].evidence_id)!} kind={words.pillKind.contract} reference={records[0].contract_reference} date={table(records[0].signed_on)} />
        ) : undefined
      }
    >
      {records.map((record, index) => (
        <div key={record.evidence_id} className={cx(index > 0 && "border-t border-line pt-4")}>
          {records.length > 1 && (
            <div className="mb-3 flex flex-wrap items-baseline justify-between gap-x-3">
              <h3 className="text-small font-bold text-ink-heading">{mono(record.contract_reference)}</h3>
              <p className="flex items-baseline gap-3 text-small text-ink-muted tabular-nums">
                <Fill template={words.contract.date} slots={{ date: table(record.signed_on) }} />
                <Pill id={record.evidence_id} n={numbers.get(record.evidence_id)!} kind={words.pillKind.contract} reference={record.contract_reference} date={table(record.signed_on)} />
              </p>
            </div>
          )}
          <ContractBody record={record} />
        </div>
      ))}
    </StageCard>
  );
}

// ── 5. Paragraphs that appeared together ─────────────────────────────────

// A card's title names its paragraph; the report is its group's heading. Two cards of one report that would share a
// title say what tells them apart: "Annex 2.A, paragraph 27", or a section's page.
function cardTitle(record: ParagraphRecord): ReactNode {
  const t = words.together;
  if (record.paragraph_numbered) {
    return record.title_section ? (
      <Fill template={t.cardTitleIn} slots={{ section: record.title_section, para: record.paragraph }} />
    ) : (
      <Fill template={t.cardTitle} slots={{ para: record.paragraph }} />
    );
  }
  const section = sectionName(record.section_path);
  return record.title_page ? <Fill template={t.cardTitleSectionPage} slots={{ section, page: String(record.title_page) }} /> : section;
}

function ParagraphCard({ record, n, many, focusRef }: { record: ParagraphRecord; n: number; many: boolean; focusRef?: (element: HTMLElement | null) => void }) {
  const numbered = record.paragraph_numbered;
  const doc = record.document_type;
  const date = sentence(record.document_date);
  const shown = excerpt(record.text, record.highlights[0] ?? null);
  const topics = joinWords(topicWords(record.topics), copy.why.topicJoin);
  return (
    <article data-paragraph-card={record.passage_id} className="flex flex-col gap-3 rounded-md border border-line bg-surface p-4 @md/page:p-6">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-label text-ink-muted uppercase">{copy.evidence.eyebrow[record.stratum]}</p>
          <h4 className="mt-1 text-title text-ink-heading">{cardTitle(record)}</h4>
        </div>
        <span ref={focusRef}>
          <Pill id={record.evidence_id} n={n} kind={record.short_name ?? doc} reference={numbered ? words.paraShort(record.paragraph) : record.section_path} date={date} />
        </span>
      </div>
      <p className="text-small text-ink" lang={record.language && record.language !== "en" ? record.language : undefined}>
        {copy.evidence.quoteOpen}
        {shown.cutBefore && copy.evidence.cut}
        {highlighted(shown.text, shown.range ? [shown.range] : [])}
        {shown.cutAfter && copy.evidence.cut}
        {copy.evidence.quoteClose}
      </p>
      {topics && (
        <p className="text-caption text-ink-muted">
          {many && record.contract_reference ? (
            <Fill template={words.together.topicsWith} slots={{ ref: mono(record.contract_reference), topics }} />
          ) : (
            <Fill template={words.together.topics} slots={{ topics }} />
          )}
        </p>
      )}
      <Source>
        <Fill
          template={numbered ? words.together.source : words.together.sourceSection}
          slots={{ doc, date, para: record.paragraph, section: record.section_path, page: String(record.pdf_page ?? "") }}
        />
      </Source>
    </article>
  );
}

// One report's paragraphs: its name and date as an h3, how many of its paragraphs appeared together, the first few
// in document order, and a button for the rest, which moves focus to the first new card's pill.
function ReportGroup({ group, records, numbers, many }: { group: ParagraphGroup; records: ParagraphRecord[]; numbers: Map<string, number>; many: boolean }) {
  const [all, setAll] = useState(false);
  const [moved, setMoved] = useState(false);
  const firstNew = useRef<HTMLElement | null>(null);
  useEffect(() => {
    if (moved && all) firstNew.current?.querySelector("a")?.focus();
  }, [moved, all]);
  const id = `report-${group.document_id}`;
  const date = table(group.document_date);
  const shown = all ? records : records.slice(0, group.shown);
  return (
    <li data-report={group.document_id} aria-labelledby={id}>
      <h3 id={id} className="text-small font-bold text-ink-heading">
        <Fill template={words.together.reportTitle} slots={{ doc: group.document_type, date }} />
      </h3>
      <p className="text-caption text-ink-muted">{words.together.reportCount(group.count, formatCount(group.count))}</p>
      <ul className="mt-3 flex flex-col gap-4">
        {shown.map((record, index) => (
          <li key={record.evidence_id}>
            <ParagraphCard
              record={record}
              n={numbers.get(record.evidence_id)!}
              many={many}
              focusRef={index === group.shown ? (element) => (firstNew.current = element) : undefined}
            />
          </li>
        ))}
      </ul>
      {group.count > group.shown && (
        <Button
          variant="ghost"
          flush
          className="mt-3"
          aria-expanded={all}
          onClick={() => {
            setAll((open) => !open);
            setMoved(!all);
          }}
        >
          {all ? words.together.less : words.together.showAll(formatCount(group.count))}
          <span className="clip-visually">
            <Fill template={words.together.fromReport} slots={{ doc: group.document_type, date }} />
          </span>
        </Button>
      )}
    </li>
  );
}

// The paragraphs, grouped by report, oldest report first, so every report is on the page with its first few
// paragraphs and none is pushed out of view by a report with many links (the 22 critique, Hierarchy).
function ParagraphsStage({ found, numbers, many }: { found: Extract<Stage, { stage: "paragraphs" }>; numbers: Map<string, number>; many: boolean }) {
  return (
    <section data-paragraphs aria-labelledby="trail-together">
      <h2 id="trail-together" className="text-title text-ink-heading">{words.together.title}</h2>
      <p className="mt-2 max-w-prose text-body text-ink">{words.together.intro}</p>
      <ul className="mt-4 flex flex-col gap-6">
        {found.groups.map((group) => (
          <ReportGroup
            key={group.document_id}
            group={group}
            records={found.records.filter((record) => record.document_id === group.document_id)}
            numbers={numbers}
            many={many}
          />
        ))}
      </ul>
    </section>
  );
}

// ── Missing stages ───────────────────────────────────────────────────────

function Missing({ found, trail }: { found: Stage; trail: Trail }) {
  const m = words.missing;
  const pid = trail.activity.project_id;
  const through = sentence(trail.data_through ?? trail.as_of);
  const asOf = sentence(trail.as_of);
  const titles = {
    plan: words.plan.title,
    notice: words.notice.title,
    bids: trail.activity.consultants ? words.bids.titleProposals : words.bids.title,
    contract: words.contract.title,
    paragraphs: words.together.title,
  };
  const reason = found.reason ?? "none_found";
  let body: ReactNode;
  let link: ReactNode = null;
  if (reason === "after_asof") {
    body =
      found.stage === "paragraphs" ? (
        <Fill template={m.paragraphs_after_asof} slots={{ asof_date: asOf }} />
      ) : (
        <Fill template={m.after_asof} slots={{ record_noun: m.recordNoun[found.stage], asof_date: asOf }} />
      );
  } else if (found.stage === "plan") {
    const contract = trail.stages.find((stage) => stage.stage === "contract");
    const noun = contract && contract.stage === "contract" && contract.records[0]?.from_notice ? copy.trail.pillKind.award_notice : copy.trail.pillKind.contract;
    body = <Fill template={m.not_read} slots={{ record_noun: noun }} />;
    link = (
      <TextLink href={`/projects/${pid}/procurement`}>
        <Fill template={m.notReadLink} slots={{ pid }} />
      </TextLink>
    );
  } else if (found.stage === "notice") {
    if (reason === "method_no_notice") body = <Fill template={m.method_no_notice} slots={{ method: String(found.method ?? "") }} />;
    else if (reason === "approach_no_notice") body = <Fill template={m.approach_no_notice} slots={{ market_approach: String(found.market_approach ?? "") }} />;
    else {
      body = <Fill template={m.notice_none_found} slots={{ data_through: through }} />;
      link = <TextLink href={dataReadinessHref(["notices"], "contract_trail")}>{m.noticeLink}</TextLink>;
    }
  } else if (found.stage === "bids") {
    if (reason === "individual_consultant") body = m.individual_consultant;
    else if (reason === "direct_selection") body = m.direct_selection;
    else {
      body = <Fill template={m.bids_none_found} slots={{ data_through: through }} />;
      link = <TextLink href={dataReadinessHref(["notices"], "contract_trail")}>{m.bidsLink}</TextLink>;
    }
  } else if (found.stage === "contract") {
    body = <Fill template={m.contract_none_found} slots={{ data_through: through }} />;
  } else if (found.stage === "paragraphs") {
    if (reason === "no_links") {
      body = <Fill template={m.no_links} slots={{ threshold: found.threshold }} />;
      if (found.coverage)
        link = (
          <TextLink href={dataReadinessHref([found.coverage.source_key], "contract_trail")}>
            <Fill template={m.coverage} slots={{ read: String(found.coverage.read), total: String(found.coverage.total) }} />
          </TextLink>
        );
    } else body = m.no_contract;
  }
  return (
    <MissingCard title={titles[found.stage]}>
      <p>{body}</p>
      {link && <p>{link}</p>}
    </MissingCard>
  );
}

// ── The trail ────────────────────────────────────────────────────────────

export function ContractTrail({ trail }: { trail: Trail }) {
  const numbers = pillNumbers(trail);
  const pid = trail.activity.project_id;
  const stepRef = trail.activity.step_reference;
  const stages = trail.stages;
  const contracts = stages.find((stage) => stage.stage === "contract");
  const many = Boolean(contracts && contracts.records.length > 1);
  const label = words.label.replace("{stepRef}", stepRef);
  return (
    <ol aria-label={label} data-trail className="flex flex-col gap-4 @md/page:gap-6">
      {stages.map((found, index) => {
        const joinKey = stages[index + 1]?.joined_on;
        const isFlat = (stage: Stage | undefined) => Boolean(stage && stage.stage === "paragraphs" && stage.found && stage.records.length > 0);
        let content: ReactNode;
        if (!found.found || found.records.length === 0) content = <Missing found={found} trail={trail} />;
        else if (found.stage === "plan") content = <PlanStage record={found.records[0]} n={numbers.get(found.records[0].evidence_id)!} pid={pid} stepRef={stepRef} />;
        else if (found.stage === "notice") content = <NoticeStage records={found.records} numbers={numbers} />;
        else if (found.stage === "bids") content = <BidsStage records={found.records} numbers={numbers} />;
        else if (found.stage === "contract") content = <ContractStage records={found.records} numbers={numbers} />;
        else content = <ParagraphsStage found={found} numbers={numbers} many={many} />;
        return (
          <StageItem key={found.stage} found={found.found && found.records.length > 0} flat={isFlat(found)} nextFlat={isFlat(stages[index + 1])} joinKey={joinKey}>
            <div data-stage={found.stage}>{content}</div>
          </StageItem>
        );
      })}
    </ol>
  );
}
