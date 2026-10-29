// A comparable package's records in the evidence drawer (the 15 brief, section 7.8): opened from a dot on
// the range chart or a row of its table. Under the heading (the STEP reference): the notice's description,
// a meta line with the project and the country, the finding that states the months, "Why I compared it"
// with the package's own values under STEP's field names, then the specific procurement notice and the
// contract award, stacked in date order, because both dates are needed to check the months. A package still
// open shows its notice and a neutral line in place of the contract. Each record ends with its source line,
// whose dataset line is the source registry's attribution, and the notice links to its page on worldbank.org.
// The server reads it all (GET /api/evidence?id=strata.gold.package:...); every number and date is a record's.
//
// A quantile dot opens the drawer at the packages it stands for instead (ComparableDotList): a sentence with
// how many, of how many, and their shortest and longest months, as find_comparables gave them, then one button
// per package, which opens its records.
import { useEffect, useRef, type ReactNode } from "react";
import { CircleDashed } from "lucide-react";
import { copy } from "../copy";
import type { EvidenceEvent } from "../lib/answer";
import type { QuantileDot } from "../lib/api";
import { cx } from "../lib/cx";
import { formatCount, formatNumber } from "../lib/format";
import { rangeCriteria, type DotEntry } from "../lib/packages";
import { useStore } from "../lib/store";
import { ExternalLink } from "./ExternalLink";
import { Fill } from "./Fill";
import { Num } from "./Num";
import { Source } from "./Source";
import { TextLink } from "./TextLink";

const words = copy.evidence.package;

type RecordRow = { [key: string]: string | number | boolean | null };
type Dataset = { dataset_name: string; license: string; data_source: string | null; record_url: string | null };

const given = (value: unknown) => value !== null && value !== undefined && value !== "";

function datasetLine(dataset: Dataset | undefined): string {
  if (!dataset) return "";
  return words.dataset(dataset.dataset_name, dataset.data_source ?? dataset.dataset_name, dataset.license);
}

// A record's fields under their source's names, in a two-column list, amounts in STEP's form with cents.
// Two fields to a row, each seated at the bottom of its row, as the Tables cards seat theirs (DESIGN.md section 5),
// so when one label wraps to two lines, as "Submission Deadline Date" does, the two values still line up.
function Fields({ fields }: { fields: { label: string; value: ReactNode; numeric?: boolean; wide?: boolean }[] }) {
  return (
    <dl data-record data-numbers className="grid grid-cols-2 gap-x-4 gap-y-2">
      {fields.map((field) => (
        <div key={field.label} className={cx("min-w-0 self-end", field.wide && "col-span-full", field.numeric && "text-right")}>
          <dt className="text-caption text-ink-muted">{field.label}</dt>
          <dd className={cx("text-small wrap-break-word text-ink", field.numeric && "tabular-nums")}>{field.value}</dd>
        </div>
      ))}
    </dl>
  );
}

function RecordCard({ title, children, source, link }: { title: string; children: ReactNode; source: ReactNode; link?: ReactNode }) {
  return (
    <section data-comparable-record className="flex flex-col gap-3 rounded-md border border-line p-4">
      <div>
        <p className="text-label text-ink-muted">{words.recordEyebrow}</p>
        <h3 className="mt-1 text-h2 text-ink-heading">{title}</h3>
      </div>
      {children}
      <Source>{source}</Source>
      {link}
    </section>
  );
}

const amount = (value: unknown) => <Num value={Number(value)} options={{ decimals: 2, compact: false }} />;

function NoticeCard({ notice, dataset, award = false }: { notice: RecordRow; dataset: Dataset | undefined; award?: boolean }) {
  const f = words.fields;
  const fields: { label: string; value: ReactNode; numeric?: boolean; wide?: boolean }[] = [];
  if (given(notice.notice_type)) fields.push({ label: f.noticeType, value: String(notice.notice_type), wide: true });
  if (given(notice.notice_date)) fields.push({ label: f.published, value: <Num date={String(notice.notice_date)} style="table" /> });
  if (!award && given(notice.submission_deadline))
    fields.push({ label: f.deadline, value: <Num date={String(notice.submission_deadline)} style="table" /> });
  if (award && given(notice.contract_signature_date))
    fields.push({ label: f.signature, value: <Num date={String(notice.contract_signature_date)} style="table" /> });
  if (given(notice.bid_reference_no))
    fields.push({ label: f.bidReference, value: <span className="font-mono wrap-anywhere">{String(notice.bid_reference_no)}</span>, wide: true });
  if (given(notice.bid_description)) fields.push({ label: f.description, value: String(notice.bid_description), wide: true });
  if (given(notice.procurement_method)) fields.push({ label: f.method, value: String(notice.procurement_method), wide: true });
  if (award && given(notice.signed_contract_price)) {
    const price = formatNumber(Number(notice.signed_contract_price), { decimals: 2, compact: false });
    fields.push({ label: f.price, value: words.price(price, String(notice.signed_contract_currency ?? "")), numeric: true, wide: true });
  }
  const url = dataset?.record_url ? dataset.record_url.replace("{id}", String(notice.notice_id)) : null;
  return (
    <RecordCard
      title={award ? words.awardNoticeTitle : words.noticeTitle}
      source={
        <Fill
          template={words.noticeSource}
          slots={{
            id: <span className="font-mono">{String(notice.notice_id)}</span>,
            date: <Num date={String(notice.notice_date)} style="table" />,
            dataset: datasetLine(dataset),
          }}
        />
      }
      link={url ? <p><ExternalLink href={url}>{words.openNotice}</ExternalLink></p> : undefined}
    >
      <Fields fields={fields} />
    </RecordCard>
  );
}

function ContractCard({ contract, dataset }: { contract: RecordRow; dataset: Dataset | undefined }) {
  const f = words.fields;
  const fields: { label: string; value: ReactNode; numeric?: boolean; wide?: boolean }[] = [];
  if (given(contract.wb_contract_number))
    fields.push({ label: f.contractNumber, value: <span className="font-mono">{String(contract.wb_contract_number)}</span> });
  if (given(contract.contract_signing_date))
    fields.push({ label: f.signed, value: <Num date={String(contract.contract_signing_date)} style="table" /> });
  if (given(contract.contract_description)) fields.push({ label: f.contractDescription, value: String(contract.contract_description), wide: true });
  if (given(contract.procurement_method)) fields.push({ label: f.method, value: String(contract.procurement_method) });
  if (given(contract.review_type)) fields.push({ label: f.reviewType, value: String(contract.review_type) });
  if (given(contract.contract_amount_usd)) fields.push({ label: f.amount, value: amount(contract.contract_amount_usd), numeric: true, wide: true });
  return (
    <RecordCard
      title={words.contractTitle}
      source={
        <Fill
          template={words.contractSource}
          slots={{
            id: <span className="font-mono">{String(contract.contract_id)}</span>,
            date: <Num date={String(contract.contract_signing_date)} style="table" />,
            dataset: datasetLine(dataset),
          }}
        />
      }
    >
      <Fields fields={fields} />
    </RecordCard>
  );
}

export function ComparableRecords({ evidence }: { evidence: EvidenceEvent }) {
  const row = evidence.row;
  const months = <Num value={Number(row.months)} options={{ decimals: 1, compact: false }} />;
  const notice = <Num date={String(row.notice_date)} />;
  // Only the criteria find_comparables used for the past range on this page, each with this package's own value; with
  // no past range on the page, all five (ticket 60).
  const criteria = useStore(rangeCriteria);
  const all: [keyof NonNullable<typeof criteria>, string, ReactNode][] = [
    ["method", words.why.method, row.method],
    ["category", words.why.category, row.category],
    ["market_approach", words.why.marketApproach, row.market_approach],
    ["review_type", words.why.reviewType, row.review_type],
    ["country", words.why.country, row.country_name],
  ];
  const why = all.filter(([key]) => !criteria || criteria[key] !== null).map(([, label, value]): [string, ReactNode] => [label, value]);
  const datasets = (row.datasets ?? {}) as { notices?: Dataset; awards?: Dataset };
  return (
    <div data-comparable={row.canceled ? "canceled" : row.still_open ? "open" : "signed"} className="flex flex-col gap-4">
      {given(row.description) && <p className="text-body text-ink">{String(row.description)}</p>}
      <p data-meta-line className="text-caption text-ink-muted">
        <Fill
          template={words.meta}
          slots={{
            project: String(row.project_name ?? row.project_id),
            pcode: (
              <TextLink href={`/projects/${String(row.project_id)}`} className="font-mono">
                {String(row.project_id)}
              </TextLink>
            ),
          }}
        />
        {given(row.country_name) && (
          <>
            {copy.evidence.meta.dot} {String(row.country_name)}
          </>
        )}
      </p>
      <p className="text-body text-ink" data-finding>
        {row.canceled ? (
          words.findingCanceled
        ) : row.still_open ? (
          <Fill
            template={words.findingOpen}
            slots={{ months, notice, counted: <Num date={String(row.counted_to)} />, through: <Num date={String(row.records_through)} /> }}
          />
        ) : (
          <Fill template={words.findingSigned} slots={{ months, notice, signed: <Num date={String(row.signed_on)} /> }} />
        )}
      </p>
      <div>
        <h3 className="text-small font-bold text-ink-heading">{words.whyHeading}</h3>
        <dl className="mt-2 grid grid-cols-[minmax(8rem,auto)_1fr] gap-x-4 gap-y-1 text-small">
          {why.map(([label, value]) => (
            <div key={label} className="contents">
              <dt className="text-ink-muted">{label}</dt>
              <dd className="text-ink">{given(value) ? value : copy.notInRecord}</dd>
            </div>
          ))}
        </dl>
      </div>
      {row.notice && <NoticeCard notice={row.notice as RecordRow} dataset={datasets.notices} />}
      {row.contract ? (
        <ContractCard contract={row.contract as RecordRow} dataset={datasets.awards} />
      ) : row.award_notice ? (
        <NoticeCard notice={row.award_notice as RecordRow} dataset={datasets.notices} award />
      ) : (
        <p data-no-contract className="flex items-start gap-2 rounded-md border border-line bg-neutral-bg p-4 text-small text-neutral">
          <CircleDashed aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
          <span>
            <Fill template={words.noContract} slots={{ date: <Num date={String(row.records_through)} /> }} />
          </span>
        </p>
      )}
      <p>
        <TextLink href={`/projects/${String(row.project_id)}`}>{words.projectLink}</TextLink>
      </p>
    </div>
  );
}

// A quantile dot's list, or (ticket 26) the packages a "{k} of {n} went with" count names: went_with is then the
// option's words, such as "3 lots", and the list is the drawer's same list view.
type DotRow = QuantileDot & { total: number; entries: DotEntry[]; went_with?: string };

const months1 = (value: number) => formatNumber(value, { decimals: 1, compact: false });

// The drawer's title for a quantile dot's list: "Five comparable packages".
export function dotTitle(evidence: EvidenceEvent): string {
  const row = evidence.row as DotRow;
  if (row.went_with !== undefined) {
    return row.count === 1 ? copy.whatIf.drawer.titleOne : copy.whatIf.drawer.title(formatCount(row.count, { capital: true }));
  }
  return row.count === 1 ? words.dot.titleOne : words.dot.title(formatCount(row.count, { capital: true }));
}

// The drawer's region name for it: "The five comparable packages dot 20 stands for", or "Comparable packages that
// went with 3 lots".
export function dotRegion(evidence: EvidenceEvent): string {
  const row = evidence.row as DotRow;
  if (row.went_with !== undefined) return copy.whatIf.drawer.region(row.went_with);
  const k = formatNumber(row.k, { compact: false });
  return row.count === 1 ? words.dot.regionOne(k) : words.dot.region(formatCount(row.count), k);
}

// The packages a quantile dot stands for (the 15 brief, section 7.8). Coming back from one of them, its
// button takes focus, so the person keeps their place in the list.
export function ComparableDotList({
  evidence,
  focusEntry = null,
  onOpen,
}: {
  evidence: EvidenceEvent;
  focusEntry?: string | null;
  onOpen?: (entry: DotEntry) => void;
}) {
  const row = evidence.row as DotRow;
  const w = words.dot;
  const total = formatNumber(row.total, { compact: false });
  const low = months1(row.low_months);
  const high = months1(row.high_months);
  const sentence =
    row.went_with !== undefined
      ? row.count === 1
        ? copy.whatIf.drawer.sentenceOne(total, row.went_with)
        : copy.whatIf.drawer.sentence(formatCount(row.count), total, row.went_with)
      : row.count === 1
      ? row.still_open
        ? w.sentenceOneOpen(total, high)
        : w.sentenceOne(total, high)
      : row.still_open
        ? w.sentenceOpen(formatCount(row.count), total, low, high)
        : low === high
          ? w.sentenceSame(formatCount(row.count), total, low)
          : w.sentence(formatCount(row.count), total, low, high);
  const back = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    if (focusEntry) back.current?.focus();
  }, [focusEntry]);
  return (
    <div data-dot-packages={row.k} className="flex flex-col gap-4">
      <p className="text-body text-ink">{sentence}</p>
      <ul className="flex flex-col divide-y divide-line border-y border-line">
        {row.entries.map((entry) => {
          const months = entry.still_open ? w.open(months1(entry.months)) : w.signed(months1(entry.months));
          // The list lands on the row that was clicked, marked with tint (ticket 105).
          const landed = entry.step_reference === focusEntry;
          return (
            <li key={entry.step_reference}>
              <button
                ref={landed ? back : undefined}
                type="button"
                data-dot-entry={entry.step_reference}
                data-landed={landed ? "" : undefined}
                onClick={() => onOpen?.(entry)}
                className={cx(
                  "flex min-h-11 w-full cursor-pointer flex-wrap items-baseline justify-between gap-x-4 px-2 py-2 text-left",
                  landed ? "bg-tint" : "hover:bg-tint-hover",
                )}
              >
                <span className="min-w-0 font-mono text-small wrap-anywhere text-primary underline decoration-1 underline-offset-3">
                  {entry.step_reference}
                </span>
                <span className="text-small text-ink-muted tabular-nums">{months}</span>
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
