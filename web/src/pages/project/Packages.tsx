// A project's Packages (the 21 brief, section 4.1), at the end of its Procurement tab: every activity in
// each implementing agency's latest Procurement Plan, by STEP reference, 20 a page, with a List search
// that filters on the server as you type. ?packages_q= and ?packages_page= keep the search and the page in
// the address. A reference links to its row in that agency's latest plan check, which brief 10 and ticket
// 14 support (…/:agencyId/:version#{reference}). Rows keep the order the route gives: agencies with the
// newest plan first, then each plan's own row order. Below a page area of 1024 px the rows are cards.
//
// A reference can be listed by two agencies' latest plans, such as NWWDA-WSDP-03-2019-2020, so each row is
// keyed by its agency and its reference. A description keeps the PDF's wrap spaces ("Exploratory Bo
// reholes"); the route's search ignores them, so "boreholes" finds it.
import { useId } from "react";
import { EmptyState } from "../../components/Card";
import { EightColumns } from "../../components/EightColumns";
import { Fill } from "../../components/Fill";
import { ListSearch } from "../../components/ListSearch";
import { Pagination } from "../../components/Pagination";
import { Source } from "../../components/Source";
import { MethodText } from "../../components/PlanCheck";
import { Table, type Column, type Row } from "../../components/Table";
import { Alert } from "../../components/Alert";
import { Button } from "../../components/Button";
import { TextLink } from "../../components/TextLink";
import { copy } from "../../copy";
import type { PackageList } from "../../lib/api";
import { formatDate, formatNumber } from "../../lib/format";
import { pageHref, usePagedList } from "../../lib/paged";
import { address } from "../../lib/router";
import { useStore } from "../../lib/store";
import { readParams } from "../../lib/view";

const words = copy.packages;
const NAMES = { query: "packages_q", page: "packages_page" };
const amount = (text: string) => formatNumber(Number(text), { decimals: 2, compact: false });
const blank = <span className="text-ink-muted">{copy.notInPlan}</span>;

const columns: Column[] = [
  { key: "activity", header: words.columns.activity, width: "w-[30%]" },
  { key: "agency", header: words.columns.agency, width: "w-[20%]" },
  { key: "method", header: words.columns.method, width: "w-[20%]" },
  { key: "estimated", header: words.columns.estimated, width: "w-[14%]", numeric: true },
  { key: "status", header: words.columns.status, width: "w-[16%]" },
];

// While the packages load, each Activity cell holds a bar for the reference and two for the Description.
const ACTIVITY_SKELETON = (
  <span aria-hidden="true" className="flex flex-col gap-1">
    <span className="flex h-lh items-center text-small">
      <span className="block h-[1em] w-4/5 rounded-xs bg-surface-2" />
    </span>
    <span className="flex h-lh items-center text-small">
      <span className="block h-[1em] w-3/5 rounded-xs bg-surface-2" />
    </span>
  </span>
);

export function Packages({ pid, none }: { pid: string; none: boolean }) {
  const headingId = useId();
  const list = usePagedList<PackageList>(`/api/projects/${encodeURIComponent(pid)}/packages`, NAMES, readParams(useStore(address).search));
  const { load, shown } = list;

  let body;
  if (none) {
    body = <p className="max-w-prose text-body text-ink">{words.none}</p>;
  } else if (load.status === "error") {
    body = (
      <EightColumns>
        <Alert
          state="error"
          live="alert"
          action={
            <Button variant="secondary" loading={load.retrying} onClick={list.retry}>
              {copy.answer.tryAgain}
            </Button>
          }
        >
          {words.error}
        </Alert>
      </EightColumns>
    );
  } else if (!shown) {
    body = (
      <Table
        title={words.title}
        labelledBy={headingId}
        level={2}
        count={{ noun: words.noun, total: 0 }}
        columns={columns}
        rowHeader="activity"
        cardsBelow="lg"
        state={{ status: "loading", rows: 5, header: ACTIVITY_SKELETON }}
      />
    );
  } else if (shown.total === 0 && !shown.query) {
    body = <p className="max-w-prose text-body text-ink">{words.none}</p>;
  } else if (shown.total === 0) {
    body = (
      <EightColumns>
        <EmptyState level={3} title={words.noMatchTitle} body={words.noMatchBody} link={{ href: pageHref(NAMES, "", 1), text: words.noMatchLink }} />
      </EightColumns>
    );
  } else {
    const rows: Row[] = shown.rows.map((row) => ({
      id: `${row.agency_id}/${row.activity_reference_no}`,
      cells: {
        activity: (
          <>
            <TextLink
              href={`/projects/${pid}/procurement/${row.agency_id}/${row.plan_date}#${encodeURIComponent(row.activity_reference_no)}`}
              className="font-mono font-medium wrap-anywhere"
            >
              {row.activity_reference_no}
            </TextLink>
            {row.description && <span className="mt-1 block text-small text-ink">{row.description}</span>}
          </>
        ),
        agency: row.implementing_agency,
        method: row.method ? <MethodText method={row.method} approach={row.market_approach} /> : blank,
        estimated: row.estimated_amount_usd ? amount(row.estimated_amount_usd) : blank,
        status: row.process_status ?? blank,
      },
    }));
    const through = shown.read_through;
    body = (
      <>
        <Table
          title={words.title}
          labelledBy={headingId}
          level={2}
          count={{ noun: words.noun, total: shown.total, from: shown.first, to: shown.last }}
          countLead
          busy={list.waiting && list.searching ? words.searching : undefined}
          columns={columns}
          rowHeader="activity"
          cardsBelow="lg"
          state={{ status: "ready", rows }}
        />
        <Pagination className="mt-4" label={words.pages} page={shown.page} pages={shown.pages} href={list.href} />
        <Source className="mt-2">{through ? <Fill template={words.source} slots={{ date: formatDate(through) }} /> : words.sourceUndated}</Source>
      </>
    );
  }

  return (
    <section aria-labelledby={headingId} data-packages={none ? "none" : load.status}>
      <EightColumns prose>
        <h2 id={headingId} className="text-h2 text-ink-heading">
          {words.title}
        </h2>
        <p className="mt-2 text-body text-ink">{words.purpose}</p>
      </EightColumns>
      {!none && (load.status !== "ready" || load.data.total > 0 || load.data.query) && (
        <div className="layout-grid mt-6">
          <ListSearch className="col-span-12 @md/page:col-span-6" label={words.searchLabel} hint={words.searchHint} value={list.query} onSearch={list.search} />
        </div>
      )}
      <div className="mt-4">{body}</div>
    </section>
  );
}
