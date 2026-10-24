// A project's Documents tab (the 21 brief, section 6): every document the World Bank published for the
// project, in one table grouped by type in the order a project produces them (the appraisal document,
// Project Papers, ISRs, Procurement Plans, the completion report, its reviews, performance assessments,
// then the rest), newest first in each group. One tbody per group, headed by the group's name and count;
// a group of more than five shows its five newest and folds the rest behind "Show all {n}". A report
// re-issued under the same number, such as P130164's ICR Review, is one row: the re-issue, with the
// version it replaced under it.
//
// Dated is the date printed on the document and Disclosed the day the World Bank made it public (its
// public_from, ADR 0002); both heads open their definitions. Pages read puts the number first, with a
// Partial badge only when pages were missed; a document I haven't read says "Not read" and is not a link.
// Every date and count is the route's. Below 768 px each group is a heading and a list of cards.
//
// States: loading, populated, some documents not read, partly read, no documents, a service that didn't
// answer, and an account that can't read Strata's tables.
import { useId, useState, type ReactNode } from "react";
import { Button } from "../../components/Button";
import { EmptyState } from "../../components/Card";
import { EightColumns } from "../../components/EightColumns";
import { ExternalLink } from "../../components/ExternalLink";
import { Fill } from "../../components/Fill";
import { LoadError } from "../../components/LoadError";
import { Num } from "../../components/Num";
import { LoadingLabel, Skeleton, SkeletonLine } from "../../components/Skeleton";
import { Source } from "../../components/Source";
import { StatusBadge } from "../../components/StatusBadge";
import { DefinitionWindow } from "../../components/Term";
import { TextLink } from "../../components/TextLink";
import { copy } from "../../copy";
import type { DocumentList, ListedDocument } from "../../lib/api";
import { cx } from "../../lib/cx";
import { formatDate, formatNumber } from "../../lib/format";
import { useLoad } from "../../lib/load";
import { fill } from "../../routes";

const words = copy.documents;
const whole = (value: number) => formatNumber(value, { compact: false });
const table = (iso: string) => formatDate(iso, { style: "table" });
const CELL = "px-3 py-3 align-top";

// A date in a cell or a link, kept on one line so it reads as one unit (DESIGN.md section 3).
function Day({ iso }: { iso: string }) {
  return (
    <span data-day className="whitespace-nowrap">
      <Num date={iso} style="table" />
    </span>
  );
}

// A group's count, kept on one line with its noun: "1 document".
function GroupCount({ count }: { count: number }) {
  return (
    <span data-group-count className="ml-2 whitespace-nowrap text-caption font-normal text-ink-muted">
      {words.groupCount(count, whole(count))}
    </span>
  );
}

// A document's name in the list, from the copy file by its type, never the API's long title.
export function documentName(document: Pick<ListedDocument, "type" | "document_type" | "document_date" | "sequence" | "agency">): string {
  const date = document.document_date ? table(document.document_date) : "";
  const name = words.name;
  switch (document.type) {
    case "isr":
      return document.sequence !== null ? fill(name.isr, { sequence: String(document.sequence) }) : fill(name.isrUndated, { date });
    case "procurement_plan":
      return document.agency ? fill(name.procurement_plan, { agency: document.agency, date }) : fill(name.procurementPlanUnnamed, { date });
    case "other":
      if (document.document_type) return document.document_type;
      return date ? fill(name.untyped, { date }) : name.untypedUndated;
    default:
      return fill(name[document.type], { date });
  }
}

const head = (label: string, definition: string) => (
  <DefinitionWindow label={label} title={label}>
    {definition}
  </DefinitionWindow>
);

const COLUMNS: { key: string; header: ReactNode; width: string; numeric?: boolean }[] = [
  { key: "document", header: words.col.document, width: "w-[38%]" },
  { key: "dated", header: head(words.col.dated, words.def.dated), width: "w-[16%]" },
  { key: "disclosed", header: head(words.col.disclosed, words.def.disclosed), width: "w-[16%]" },
  { key: "pages", header: head(words.col.pages, words.def.pages), width: "w-[18%]", numeric: true },
  { key: "pdf", header: words.col.pdf, width: "w-[12%]" },
];

function NameCell({ document, pid }: { document: ListedDocument; pid: string }) {
  const name = documentName(document);
  const reissue = document.reissue;
  return (
    <>
      {document.read && document.doc_key ? (
        <TextLink href={`/projects/${pid}/documents/${document.doc_key}`} className="text-small font-semibold">
          {name}
        </TextLink>
      ) : (
        <span className="text-small text-ink">{name}</span>
      )}
      {reissue && reissue.document_date && (
        <span className="mt-1 block text-caption text-ink-muted">
          <Fill template={words.reissueNote} slots={{ date: <Num date={reissue.document_date} /> }} />{" "}
          {reissue.doc_key && (
            <TextLink href={`/projects/${pid}/documents/${reissue.doc_key}`}>
              <Fill template={words.reissueLink} slots={{ date: <span data-day className="whitespace-nowrap">{table(reissue.document_date)}</span> }} />
            </TextLink>
          )}
        </span>
      )}
    </>
  );
}

// Dated: the date on the document; for a re-issue, the original's date, then the re-issue's.
function DatedCell({ document }: { document: ListedDocument }) {
  const reissue = document.reissue;
  if (reissue?.document_date && document.document_date) {
    return (
      <>
        <Day iso={reissue.document_date} />
        <span className="block">
          <Fill template={words.reissueDated} slots={{ date: <Day iso={document.document_date} /> }} />
        </span>
      </>
    );
  }
  return document.document_date ? <Day iso={document.document_date} /> : <span className="text-ink-muted">{copy.notInRecord}</span>;
}

function DisclosedCell({ document }: { document: ListedDocument }) {
  const reissue = document.reissue;
  const one = (iso: string | null) => (iso ? <Day iso={iso} /> : <span className="text-ink-muted">{copy.notInRecord}</span>);
  if (reissue) {
    return (
      <>
        {one(reissue.disclosed_on)}
        <span className="block">{one(document.disclosed_on)}</span>
      </>
    );
  }
  return one(document.disclosed_on);
}

// Pages read: right-aligned in the table, and at the card's left edge below 768 px, where every value
// starts at one edge (DESIGN.md section 5, Tables).
function PagesCell({ document, align = "end" }: { document: ListedDocument; align?: "end" | "start" }) {
  if (!document.read || document.pages_read === null || document.pdf_pages === null) {
    return <span className="text-ink-muted">{words.notRead}</span>;
  }
  return (
    <span className={cx("inline-flex flex-col gap-1", align === "end" ? "items-end" : "items-start")}>
      <span data-pages-read className="whitespace-nowrap tabular-nums">
        <Fill template={words.pagesOf} slots={{ read: whole(document.pages_read), pages: whole(document.pdf_pages) }} />
      </span>
      {document.partial && <StatusBadge kind="partial" />}
    </span>
  );
}

function PdfCell({ document }: { document: ListedDocument }) {
  if (!document.pdf_url) return null;
  const name = documentName(document);
  return (
    <ExternalLink href={document.pdf_url.replace(/^http:\/\//, "https://")} label={words.pdfName(name, document.document_date ? formatDate(document.document_date) : "")}>
      {words.pdf}
    </ExternalLink>
  );
}

type Group = DocumentList["groups"][number];

function GroupRows({ group, pid, open, onToggle, bodyId }: { group: Group; pid: string; open: boolean; onToggle: () => void; bodyId: string }) {
  const shown = group.documents.filter((document) => open || document.shown);
  const folds = group.shown_count < group.count;
  return (
    <tbody id={bodyId} data-group={group.type}>
      <tr className="border-t border-line bg-surface">
        <th colSpan={COLUMNS.length} scope="rowgroup" className="px-3 pt-6 pb-2 text-left font-normal">
          <span className="text-title text-ink-heading">{words.group[group.type]}</span>
          <GroupCount count={group.count} />
        </th>
      </tr>
      {shown.map((document) => (
        <tr key={document.document_id} className={cx("border-t border-line", !document.shown && "animate-fade-in")} data-document={document.doc_key ?? document.document_id}>
          <th scope="row" className={cx(CELL, "text-left font-normal")}>
            <NameCell document={document} pid={pid} />
          </th>
          <td className={CELL}>
            <DatedCell document={document} />
          </td>
          <td className={CELL}>
            <DisclosedCell document={document} />
          </td>
          <td className={cx(CELL, "text-right")}>
            <PagesCell document={document} />
          </td>
          <td className={CELL}>
            <PdfCell document={document} />
          </td>
        </tr>
      ))}
      {folds && (
        <tr className="border-t border-line">
          <td colSpan={COLUMNS.length} className="px-3 py-1">
            <Button variant="ghost" flush aria-expanded={open} aria-controls={bodyId} onClick={onToggle}>
              {open ? words.less : words.more(whole(group.count))}
            </Button>
          </td>
        </tr>
      )}
    </tbody>
  );
}

// Below 768 px: each group is a heading and a list of cards.
function GroupCards({ group, pid, open, onToggle, listId }: { group: Group; pid: string; open: boolean; onToggle: () => void; listId: string }) {
  const shown = group.documents.filter((document) => open || document.shown);
  const folds = group.shown_count < group.count;
  const field = (label: string, value: ReactNode) => (
    <div className="flex min-w-0 flex-col">
      <dt className="text-caption text-ink-muted">{label}</dt>
      <dd className="text-caption text-ink">{value}</dd>
    </div>
  );
  return (
    <section data-group={group.type}>
      <h3 className="text-title text-ink-heading">
        {words.group[group.type]}
        <GroupCount count={group.count} />
      </h3>
      <ul id={listId} className="mt-2 flex flex-col gap-3">
        {shown.map((document) => (
          <li key={document.document_id} className="rounded-md border border-line bg-surface p-4">
            <NameCell document={document} pid={pid} />
            <dl className="mt-2 grid grid-cols-[repeat(auto-fit,minmax(6.5rem,1fr))] gap-x-4 gap-y-2">
              {field(words.col.dated, <DatedCell document={document} />)}
              {field(words.col.disclosed, <DisclosedCell document={document} />)}
              {field(words.col.pages, <PagesCell document={document} align="start" />)}
            </dl>
            <div className="mt-2">
              <PdfCell document={document} />
            </div>
          </li>
        ))}
      </ul>
      {folds && (
        <div className="mt-2">
          <Button variant="ghost" flush onPage aria-expanded={open} aria-controls={listId} onClick={onToggle}>
            {open ? words.less : words.more(whole(group.count))}
          </Button>
        </div>
      )}
    </section>
  );
}

export function DocumentsSkeleton() {
  return (
    <div aria-hidden="true" data-documents-skeleton>
      <SkeletonLine className="text-caption" width="w-40" />
      <div className="mt-2 hidden overflow-hidden rounded-md border border-line bg-surface @md/page:block">
        <table className="w-full table-fixed border-collapse text-small">
          <thead className="bg-surface-2">
            <tr>
              {COLUMNS.map((column) => (
                <th key={column.key} scope="col" className={cx("px-3 py-2 text-left font-semibold text-ink-heading", column.numeric && "text-right", column.width)}>
                  {column.key === "dated" ? words.col.dated : column.key === "disclosed" ? words.col.disclosed : column.key === "pages" ? words.col.pages : column.header}
                </th>
              ))}
            </tr>
          </thead>
          {[0, 1].map((group) => (
            <tbody key={group}>
              <tr className="border-t border-line">
                <td colSpan={COLUMNS.length} className="px-3 pt-6 pb-2">
                  <Skeleton className="h-[18px] w-60" />
                </td>
              </tr>
              {[0, 1, 2, 3].map((row) => (
                <tr key={row} className="h-14 border-t border-line">
                  {COLUMNS.map((column) => (
                    <td key={column.key} className={CELL}>
                      <SkeletonLine width={column.numeric ? "ml-auto w-1/2" : "w-4/5"} />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          ))}
        </table>
      </div>
      <div className="mt-2 flex flex-col gap-3 @md/page:hidden">
        {[0, 1].map((group) => (
          <div key={group} className="flex flex-col gap-3">
            <Skeleton className="h-[18px] w-60" />
            {[0, 1, 2].map((card) => (
              <div key={card} className="h-28 rounded-md border border-line bg-surface p-4">
                <SkeletonLine className="text-small" width="w-3/5" />
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

// The populated list: the count line, the grouped table from 768 px and the groups as cards below it,
// the note on documents not read, and the source line.
export function DocumentsList({ data, pid }: { data: DocumentList; pid: string }) {
  const [open, setOpen] = useState<Record<string, boolean>>({});
  const id = useId();
  const toggle = (type: string) => setOpen((now) => ({ ...now, [type]: !now[type] }));
  // The rows the list shows: each group's folded rows, or all of them once it is open.
  const shownRows = data.groups.reduce((sum, group) => sum + (open[group.type] ? group.count : group.shown_count), 0);
  const name = data.project.display_name ?? pid;
  const unread = data.groups.some((group) => group.documents.some((document) => !document.read));
  return (
    <>
      <p className="text-caption text-ink-muted tabular-nums" data-documents-count>
        {shownRows === data.total ? copy.table.showingAll(whole(data.total), words.noun) : words.showing(whole(shownRows), whole(data.total))}
      </p>
      <div className="mt-2 hidden overflow-hidden rounded-md border border-line bg-surface @md/page:block" data-view="table">
        <table className="w-full table-fixed border-collapse text-small">
          <caption className="sr-only">{words.caption(name)}</caption>
          <thead className="bg-surface-2">
            <tr>
              {COLUMNS.map((column) => (
                <th key={column.key} scope="col" className={cx("px-3 py-2 align-bottom font-semibold text-ink-heading", column.numeric ? "text-right" : "text-left", column.width)}>
                  {column.header}
                </th>
              ))}
            </tr>
          </thead>
          {data.groups.map((group) => (
            <GroupRows key={group.type} group={group} pid={pid} open={Boolean(open[group.type])} onToggle={() => toggle(group.type)} bodyId={`${id}-${group.type}`} />
          ))}
        </table>
      </div>
      <div className="mt-2 flex flex-col gap-8 @md/page:hidden" data-view="cards">
        {data.groups.map((group) => (
          <GroupCards key={group.type} group={group} pid={pid} open={Boolean(open[group.type])} onToggle={() => toggle(group.type)} listId={`${id}-cards-${group.type}`} />
        ))}
      </div>
      {unread && (
        <p className="mt-2 max-w-prose text-caption text-ink-muted">
          <Fill template={words.notReadNote} slots={{ link: <TextLink href="/data?sources=documents">{words.notReadLink}</TextLink> }} />
        </p>
      )}
      <Source className="mt-2">{data.documents_through ? <Fill template={words.source} slots={{ date: formatDate(data.documents_through) }} /> : words.sourceUndated}</Source>
    </>
  );
}

export function DocumentsTab({ pid }: { pid: string }) {
  const [load, retry] = useLoad<DocumentList>(`/api/projects/${encodeURIComponent(pid)}/documents`);
  let body: ReactNode;
  if (load.status === "loading") {
    body = (
      <>
        <LoadingLabel />
        <DocumentsSkeleton />
        <p role="status" className="sr-only">
          {words.loading}
        </p>
      </>
    );
  } else if (load.status === "error") {
    body = (
      <EightColumns>
        <LoadError error={load.error} message={words.error} permission={words.permission} onRetry={retry} retrying={load.retrying} attempt={load.attempt} />
      </EightColumns>
    );
  } else if (load.data.groups.length === 0 && !load.data.in_document_set) {
    body = <EmptyState level={3} title={words.outsideTitle} body={words.outsideBody} link={{ href: "/data?sources=documents", text: words.outsideLink }} />;
  } else if (load.data.groups.length === 0) {
    body = <EmptyState level={3} title={words.emptyTitle} body={words.emptyBody} link={{ href: "/data?sources=documents", text: words.emptyLink }} />;
  } else {
    body = <DocumentsList data={load.data} pid={pid} />;
  }
  return (
    <div className="layout-grid" data-documents={load.status}>
      <div className="col-span-12 @xl/page:col-span-7">
        <h2 className="sr-only">{words.heading}</h2>
        <p className="max-w-prose text-body text-ink-muted">{words.purpose}</p>
        <div className="mt-6">{body}</div>
      </div>
    </div>
  );
}
