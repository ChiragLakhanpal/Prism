// A comparable package's records in the evidence drawer (the 15 brief, section 7.8): opened from a dot on
// the range chart or a row of its table. Under the heading (the STEP reference): the notice's description,
// a meta line with the project and the country, the finding that states the months, "Why I compared it"
// with the package's own values under STEP's field names, then the specific procurement notice and the
// contract award, stacked in date order, because both dates are needed to check the months. A package still
// open shows its notice and a neutral line in place of the contract. Each record ends with its source line,
// whose dataset line is the source registry's attribution, and the notice links to its page on worldbank.org.
// The server reads it all (GET /api/evidence?id=strata.gold.package:...); every number and date is a record's.
import type { ReactNode } from "react";
import { CircleDashed } from "lucide-react";
import { copy } from "../copy";
import type { EvidenceEvent } from "../lib/answer";
import { cx } from "../lib/cx";
import { formatNumber } from "../lib/format";
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
function Fields({ fields }: { fields: { label: string; value: ReactNode; numeric?: boolean; wide?: boolean }[] }) {
  return (
    <dl data-record data-numbers className="grid grid-cols-2 gap-x-4 gap-y-2">
      {fields.map((field) => (
        <div key={field.label} className={cx("min-w-0", field.wide && "col-span-full", field.numeric && "text-right")}>
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
        <p className="text-label text-ink-muted uppercase">{words.recordEyebrow}</p>
        <h3 className="mt-1 text-title text-ink-heading">{title}</h3>
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
  const why: [string, ReactNode][] = [
    [words.why.method, row.method],
    [words.why.category, row.category],
    [words.why.marketApproach, row.market_approach],
    [words.why.reviewType, row.review_type],
    [words.why.country, row.country_name],
  ];
  const datasets = (row.datasets ?? {}) as { notices?: Dataset; awards?: Dataset };
  return (
    <div data-comparable={row.still_open ? "open" : "signed"} className="flex flex-col gap-4">
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
        {row.still_open ? (
          <Fill template={words.findingOpen} slots={{ months, notice, through: <Num date={String(row.records_through)} /> }} />
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
