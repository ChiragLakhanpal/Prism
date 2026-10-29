// The source view (the 21 brief, section 7), at /projects/:pid/documents/:doc?page=&para=: one PDF page of
// a document's own words, divided into the paragraphs the document numbers, with the paragraph a citation
// names highlighted, and a link to the World Bank's PDF at that page. It is the last step of the answer,
// the drawer and the page. It shows only the document's words and the rows read from its tables, never
// Strata's summary of a table.
//
// :doc is a document's key in its project, such as icr-2019-10-10; a bare type such as icr opens the one
// current document of that type, and the address is rewritten to its key in place. A paragraph on another
// page, a paragraph the document does not have, or a page past the last is corrected with a note, and the
// address is rewritten in place, so Back never returns to the wrong one. On load the highlighted paragraph
// sits about a third of the way down the window and takes focus, so a screen reader reads it first.
//
// States: loading (the page bar is real, with the page from the address), a page with a paragraph, a page
// with none asked, a corrected address, a page not read, a page with no text, front matter, a document not
// read, not found, ambiguous, not public by the as-of date, a service that didn't answer, and an account
// that can't read Strata's tables.
import { Lang } from "../components/Lang";
import { useEffect, useId, useLayoutEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Alert } from "../components/Alert";
import { Breadcrumb } from "../components/Breadcrumb";
import { Button } from "../components/Button";
import { EmptyState } from "../components/Card";
import { ExternalLink, pdfPageHref } from "../components/ExternalLink";
import { drawable } from "../components/Document";
import { Fill } from "../components/Fill";
import { LoadError } from "../components/LoadError";
import { Num } from "../components/Num";
import { MethodText } from "../components/PlanCheck";
import { linkProjectIds, ProjectId, ProjectIdText } from "../components/ProjectId";
import { Skeleton, SkeletonLine, SkeletonText } from "../components/Skeleton";
import { CARD_FIELD, CARD_FIELDS } from "../components/Table";
import { TextLink } from "../components/TextLink";
import { copy } from "../copy";
import type { SourcePageAnswer } from "../lib/api";
import { cx } from "../lib/cx";
import { formatDate, formatNumber } from "../lib/format";
import { useLoad } from "../lib/load";
import { address, navigate } from "../lib/router";
import { useStore } from "../lib/store";
import { setPageTitle } from "../lib/title";
import { fill } from "../routes";

const words = copy.sourceView;
const whole = (value: number) => formatNumber(value, { compact: false });
const table = (iso: string) => formatDate(iso, { style: "table" });

type Doc = NonNullable<SourcePageAnswer["document"]>;
type Correction = NonNullable<SourcePageAnswer["correction"]>;

// The address's page, paragraph and passage.
function asked(search: string) {
  const params = new URLSearchParams(search);
  const page = Number(params.get("page"));
  return {
    page: Number.isInteger(page) && page >= 1 ? page : null,
    para: params.get("para"),
    passage: params.get("passage"),
  };
}

// The source view's address for a page, keeping ?view=, ?asof= and ?lang=.
function pageAddress(pid: string, doc: string, page: number, extra: Record<string, string> = {}, search = address.get().search): string {
  const params = new URLSearchParams(search);
  const kept = new URLSearchParams();
  kept.set("page", String(page));
  for (const [key, value] of Object.entries(extra)) kept.set(key, value);
  for (const key of ["view", "asof", "lang"]) {
    const value = params.get(key);
    if (value) kept.set(key, value);
  }
  return `/projects/${pid}/documents/${doc}?${kept.toString()}`;
}

function apiPath(pid: string, doc: string, search: string): string {
  const want = asked(search);
  const params = new URLSearchParams();
  if (want.page !== null) params.set("page", String(want.page));
  if (want.para) params.set("para", want.para);
  if (want.passage) params.set("passage", want.passage);
  const asOf = new URLSearchParams(search).get("asof");
  if (asOf) params.set("asof", asOf);
  const rest = params.toString();
  return `/api/projects/${encodeURIComponent(pid)}/documents/${encodeURIComponent(doc)}${rest ? `?${rest}` : ""}`;
}

// "ICR of Oct 10, 2019", the last crumb.
function crumbName(document: Doc): string {
  return fill(words.crumb, { doc: words.short[document.type] ?? words.short.other, date: document.document_date ? table(document.document_date) : "" });
}

function heading(document: Doc): string {
  return words.typeName[document.type] ?? document.document_type;
}

// The page bar: Previous page, "Page n of m" (which takes focus after a move), Go to page, Next page.
export function PageBar({
  pid,
  doc,
  page,
  pages,
  full,
  onMove,
  positionRef,
}: {
  pid: string;
  doc: string;
  page: number;
  pages: number | null;
  full: boolean;
  onMove: () => void;
  positionRef?: React.Ref<HTMLParagraphElement>;
}) {
  const inputId = useId();
  const [value, setValue] = useState(String(page));
  useEffect(() => setValue(String(page)), [page]);
  // Until the page arrives no tool has said how many pages the document has (CLAUDE.md rule 1), so the bar
  // gives only the page from the address, Next page keeps its place unseen, and the field has no maximum.
  const atEnd = pages === null || page >= pages;
  const link = "inline-flex h-11 items-center gap-1 text-small";
  const go = (event: FormEvent) => {
    event.preventDefault();
    const to = Number(value);
    if (!Number.isInteger(to) || to < 1) return;
    onMove();
    navigate(pageAddress(pid, doc, pages === null ? to : Math.min(to, pages)));
  };
  // Below a page area of 30rem, 480 px, the two links say "Previous" and "Next", so "Page 65 of 100" keeps one row with
  // them on a phone (the 21 brief, 7.2; ticket 59).
  return (
    <nav aria-label={words.pages.label} data-page-bar className="flex flex-wrap items-center justify-between gap-x-6 gap-y-2 border-y border-line py-2">
      <TextLink href={pageAddress(pid, doc, page - 1)} onClick={onMove} className={cx(link, page <= 1 && "invisible")} aria-label={copy.pagination.previous}>
        <ChevronLeft aria-hidden="true" className="size-4 shrink-0" />
        <span className="@table-narrow/page:hidden">{copy.pagination.previousShort}</span>
        <span className="hidden @table-narrow/page:inline">{copy.pagination.previous}</span>
      </TextLink>
      {full ? (
        <>
          <p ref={positionRef} tabIndex={-1} data-page-lead className="text-caption text-ink-muted tabular-nums focus:outline-none">
            {pages === null ? words.pages.positionOnly(whole(page)) : words.pages.position(whole(page), whole(pages))}
          </p>
          <form onSubmit={go} className="order-last flex w-full items-center gap-3 @md/page:order-none @md/page:w-auto">
            <label htmlFor={inputId} className="text-small text-ink">
              {words.pages.goLabel}
            </label>
            <input
              id={inputId}
              type="number"
              inputMode="numeric"
              min={1}
              max={pages ?? undefined}
              value={value}
              onChange={(event) => setValue(event.target.value)}
              className="h-11 w-[6ch] min-w-16 rounded-sm border border-line-strong bg-surface px-2 text-right text-body text-ink tabular-nums"
            />
            <Button variant="secondary" type="submit">
              {words.pages.goButton}
            </Button>
          </form>
        </>
      ) : (
        <span aria-hidden="true" />
      )}
      <TextLink href={pageAddress(pid, doc, page + 1)} onClick={onMove} className={cx(link, atEnd && "invisible")} aria-label={copy.pagination.next}>
        <span className="@table-narrow/page:hidden">{copy.pagination.nextShort}</span>
        <span className="hidden @table-narrow/page:inline">{copy.pagination.next}</span>
        <ChevronRight aria-hidden="true" className="size-4 shrink-0" />
      </TextLink>
    </nav>
  );
}

// A section's caption: "Section III.B", or the section's own name when it already says what it is, such as
// "Annex 8", never "Section Annex 8".
const NAMED_PART = /^(annex|appendix|attachment)\b/i;
function sectionCaption(section: string): string {
  return NAMED_PART.test(section) ? section : fill(words.section, { section });
}

// The highlighted passage: the highlight fill, a 4 px primary bar on its left edge, and the caption above
// it that says why it is marked. Screen readers hear where the highlight starts and ends.
function Highlighted({ caption, children, blockRef }: { caption: ReactNode; children: ReactNode; blockRef: React.Ref<HTMLDivElement> }) {
  const captionId = useId();
  return (
    <div className="flex flex-col gap-2">
      <p id={captionId} className="text-caption text-ink-muted">
        {caption}
      </p>
      <div
        ref={blockRef}
        tabIndex={-1}
        aria-describedby={captionId}
        data-highlighted
        className="scroll-mt-24 animate-settle rounded-sm border-l-4 border-primary bg-highlight px-4 py-3 focus-visible:outline-offset-2"
      >
        <span className="sr-only">{copy.document.highlightStarts} </span>
        {children}
        <span className="sr-only"> {copy.document.highlightEnds}</span>
      </div>
    </div>
  );
}

export function Passages({ answer, blockRef }: { answer: SourcePageAnswer; blockRef: React.Ref<HTMLDivElement> }) {
  const passages = answer.passages ?? [];
  const highlight = answer.highlight;
  let section: string | null = null;
  // The words keep to 72 characters a line; a table on the page spans the page bar's width (ticket 59).
  return (
    <div className="flex flex-col gap-4" data-passages>
      {passages.map((passage) => {
        const newSection = passage.section_path && passage.section_path !== section ? passage.section_path : null;
        section = passage.section_path ?? section;
        const id = passage.numbered ? `para-${passage.paragraph}` : `passage-${passage.passage_id}`;
        const text = (
          <Lang as="p" code={passage.language} className="text-body wrap-anywhere text-ink" data-passage-id={passage.passage_id} id={id}>
            {linkProjectIds(drawable(passage.text))}
          </Lang>
        );
        const marked = highlight?.passage_id === passage.passage_id;
        return (
          <div key={passage.passage_id} className="flex max-w-[72ch] flex-col gap-1">
            {newSection && <p className="text-caption text-ink-muted">{sectionCaption(newSection)}</p>}
            {marked ? (
              <Highlighted
                blockRef={blockRef}
                caption={highlight?.para ? fill(words.opened, { para: highlight.para }) : words.openedPassage}
              >
                {text}
              </Highlighted>
            ) : (
              text
            )}
          </div>
        );
      })}
      {(answer.tables ?? []).map((found, index) => (
        <RowsTable key={index} title={found.title} page={answer.page ?? 1} rows={found.rows} highlight={highlight?.passage_id ?? null} blockRef={blockRef} />
      ))}
      {(answer.plan_rows ?? []).length > 0 && <PlanRows answer={answer} />}
      {(answer.page_text ?? []).map((line, index) => (
        <p key={index} className="max-w-[72ch] text-body wrap-anywhere text-ink">
          {line}
        </p>
      ))}
    </div>
  );
}

// A table on the page, as the reader read it into rows: one column per head, in the order they first appear.
function RowsTable({
  title,
  page,
  rows,
  highlight,
  blockRef,
}: {
  title: string | null;
  page: number;
  rows: { passage_id: string; row: number | null; cells: [string, string][] }[];
  highlight: string | null;
  blockRef: React.Ref<HTMLDivElement>;
}) {
  const heads: string[] = [];
  for (const row of rows) for (const [head] of row.cells) if (!heads.includes(head)) heads.push(head);
  const marked = rows.some((row) => row.passage_id === highlight);
  const cell = (row: (typeof rows)[number], head: string) => drawable(row.cells.find(([name]) => name === head)?.[1] ?? "");
  const body = (
    <TableOrCards
      caption={title ? fill(words.tableTitled, { title, page: String(page) }) : fill(words.table, { page: String(page) })}
      table={(captionId, caption) => (
        <table className="w-full border-collapse text-small">
          <caption id={captionId} className="px-3 py-2 text-left text-caption text-ink-muted">
            {caption}
          </caption>
          <thead className="bg-surface-2">
            <tr>
              {heads.map((head) => (
                <th key={head} scope="col" className="min-w-[8ch] px-3 py-2 text-left align-bottom font-semibold wrap-break-word text-ink-heading">
                  {head}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.passage_id} id={`passage-${row.passage_id}`} className={cx("border-t border-line align-top", row.passage_id === highlight && "bg-highlight")}>
                {heads.map((head) => (
                  // Each column keeps room for a short word, and words break only when one is longer than its
                  // column, so "Stakeholder" never splits into "Stak / ehol / der" (the 21 design review, F18).
                  <td key={head} className="min-w-[8ch] px-3 py-2 wrap-break-word text-ink">
                    {cell(row, head)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      )}
      // Each card is headed by its row's name, the first column's value, as Table's cards are, and lists the other
      // columns under their heads (DESIGN.md section 5, Tables; ticket 59). A row with no name lists every column.
      cards={rows.map((row) => {
        const name = cell(row, heads[0]);
        const fields = name ? heads.slice(1) : heads;
        return (
          <li
            key={row.passage_id}
            data-passage-id={row.passage_id}
            className={cx("rounded-md border border-line p-4", row.passage_id === highlight ? "border-l-4 border-l-primary bg-highlight" : "bg-surface")}
          >
            {name && <h2 className="text-small font-semibold wrap-break-word text-ink-heading">{name}</h2>}
            {fields.length > 0 && (
              <dl className={cx("flex flex-col gap-2", name && "mt-2")}>
                {fields.map((head) => (
                  <div key={head}>
                    <dt className="text-caption text-ink-muted">{head}</dt>
                    <dd className="text-small wrap-break-word text-ink">{cell(row, head)}</dd>
                  </div>
                ))}
              </dl>
            )}
          </li>
        );
      })}
    />
  );
  return marked ? (
    <Highlighted blockRef={blockRef} caption={words.openedPassage}>
      {body}
    </Highlighted>
  ) : (
    body
  );
}

// A table on the page from a page area of 768 px, and one card per row below it, as every table in Strata
// becomes (DESIGN.md section 5, Tables; the 21 design review, round 3, F2): each card lists the column heads
// in caption over their values, from one left edge, so nothing scrolls sideways on a phone. The table's frame
// is a region named by its caption that takes focus, as Table's is, so a keyboard can scroll a table wider
// than its column in every browser (round 3, B1).
function TableOrCards({ caption, table, cards }: { caption: string; table: (captionId: string, caption: string) => ReactNode; cards: ReactNode }) {
  const tableCaption = useId();
  const cardsCaption = useId();
  return (
    <>
      <div tabIndex={0} role="region" aria-labelledby={tableCaption} data-table-view="table" className="hidden overflow-x-auto rounded-md border border-line bg-surface @md/page:block">
        {table(tableCaption, caption)}
      </div>
      <div data-table-view="cards" className="@md/page:hidden">
        <p id={cardsCaption} className="text-caption text-ink-muted">
          {caption}
        </p>
        <ul aria-labelledby={cardsCaption} className="mt-2 flex flex-col gap-3">
          {cards}
        </ul>
      </div>
    </>
  );
}

// A Procurement Plan's page: the STEP rows the layout parser read from its table. A card's heading is its
// STEP reference.
function PlanRows({ answer }: { answer: SourcePageAnswer }) {
  const columns = copy.checkPlan.columns;
  const rows = answer.plan_rows ?? [];
  const amount = (text: string | null) => (text ? formatNumber(Number(text), { decimals: 2, compact: false }) : copy.notInPlan);
  const method = (row: (typeof rows)[number]) => (row.method ? <MethodText method={row.method} approach={row.market_approach} /> : copy.notInPlan);
  return (
    <TableOrCards
      caption={fill(words.planRows, { page: String(answer.page ?? 1) })}
      table={(captionId, caption) => (
        <table className="w-full border-collapse text-small">
          <caption id={captionId} className="px-3 py-2 text-left text-caption text-ink-muted">
            {caption}
          </caption>
          <thead className="bg-surface-2">
            <tr>
              {[columns.activity, columns.method, columns.estimated, columns.status].map((head, index) => (
                <th key={index} scope="col" className={cx("px-3 py-2 align-bottom font-semibold text-ink-heading", index === 2 ? "text-right" : "text-left")}>
                  {head}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.activity_reference_no} className="border-t border-line align-top">
                <th scope="row" className="px-3 py-2 text-left font-normal">
                  <span className="block font-mono font-medium wrap-anywhere text-ink">{row.activity_reference_no}</span>
                  {row.description && <span className="mt-1 block text-ink">{drawable(row.description)}</span>}
                </th>
                <td className="px-3 py-2">{method(row)}</td>
                <td className="px-3 py-2 text-right tabular-nums">{amount(row.estimated_amount_usd)}</td>
                <td className="px-3 py-2">{row.process_status ?? copy.notInPlan}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      cards={rows.map((row) => (
        <li key={row.activity_reference_no} className="rounded-md border border-line bg-surface p-4">
          <h2 className="font-mono text-small font-semibold wrap-anywhere text-ink-heading">{row.activity_reference_no}</h2>
          {row.description && <p className="mt-1 text-small text-ink">{drawable(row.description)}</p>}
          {/* Method at the card's full width, then the estimate and Process status sharing Table's 120 px grid
              (DESIGN.md section 5, Tables; ticket 59). */}
          <dl className={cx("mt-2", CARD_FIELDS)}>
            <div className={cx(CARD_FIELD, "col-span-full")}>
              <dt className="text-caption text-ink-muted">{columns.method}</dt>
              <dd className="text-small text-ink">{method(row)}</dd>
            </div>
            <div className={CARD_FIELD}>
              <dt className="text-caption text-ink-muted">{columns.estimated}</dt>
              <dd className="text-small whitespace-nowrap text-ink tabular-nums">{amount(row.estimated_amount_usd)}</dd>
            </div>
            <div className={CARD_FIELD}>
              <dt className="text-caption text-ink-muted">{columns.status}</dt>
              <dd className="text-small wrap-break-word text-ink">{row.process_status ?? copy.notInPlan}</dd>
            </div>
          </dl>
        </li>
      ))}
    />
  );
}

function Meta({ document, answer }: { document: Doc; answer: SourcePageAnswer }) {
  const pair = (label: string, value: ReactNode) => (
    <div className="min-w-0">
      <dt className="text-caption text-ink-muted">{label}</dt>
      <dd className="text-small text-ink">{value}</dd>
    </div>
  );
  const language = document.language ? (copy.language.name[document.language] ?? document.language) : null;
  return (
    <dl className="mt-4 flex flex-col gap-2 @md/page:flex-row @md/page:flex-wrap @md/page:gap-x-6">
      {pair(words.meta.project, <Fill template={words.projectValue} slots={{ name: answer.project.display_name ?? "", pid: <ProjectId pid={answer.project.project_id} /> }} />)}
      {document.document_date && pair(words.meta.dated, <Num date={document.document_date} />)}
      {document.disclosed_on && pair(words.meta.disclosed, <Num date={document.disclosed_on} />)}
      {document.pdf_pages !== null && pair(words.meta.pages, <Num value={document.pdf_pages} options={{ compact: false }} />)}
      {language && pair(words.meta.language, language)}
    </dl>
  );
}

function correctionText(correction: Correction, pages: number | null): string {
  if (correction.kind === "moved") return fill(words.moved, { para: correction.para ?? "", page: String(correction.page) });
  if (correction.kind === "no_para") return fill(words.noPara, { para: correction.para ?? "", page: String(correction.page) });
  return fill(words.pageRange, { pages: String(pages ?? correction.page) });
}

// While the page loads: the crumb's bar, the h1's bar, five meta bars, the real page bar, and eight
// paragraphs of three lines, the fourth drawn with the highlight when a paragraph is asked for.
function SourceSkeleton({ para }: { para: boolean }) {
  return (
    <div aria-hidden="true" data-source-skeleton>
      <div className="mt-6 flex max-w-[72ch] flex-col gap-4">
        {Array.from({ length: 8 }, (_, index) => (
          <div key={index} className={cx(para && index === 3 && "rounded-sm border-l-4 border-primary bg-highlight px-4 py-3")}>
            <SkeletonText className="text-body" widths={["w-full", "w-full", "w-3/5"]} />
          </div>
        ))}
      </div>
    </div>
  );
}

export function SourcePage({ pid, doc, search }: { pid: string; doc: string; search: string }) {
  const [load, retry] = useLoad<SourcePageAnswer>(apiPath(pid, doc, search));
  const want = asked(search);
  const here = useStore(address);
  const title = useRef<HTMLHeadingElement>(null);
  const block = useRef<HTMLDivElement>(null);
  const position = useRef<HTMLParagraphElement>(null);
  // Set when the page bar moved the page, so focus stays on "Page n of m" instead of the highlight or h1.
  const viaBar = useRef(false);
  // A corrected address keeps its note after the address is rewritten, for the address it was written to.
  const [notice, setNotice] = useState<{ search: string; correction: Correction } | null>(null);
  const answer = load.status === "ready" ? load.data : null;
  const document = answer?.document ?? null;

  // A bare type, a corrected page or paragraph: the address becomes the right one, in place.
  useEffect(() => {
    if (!answer) return;
    const key = answer.canonical ?? doc;
    const correction = answer.correction;
    if (!answer.canonical && !correction) return;
    let to = here.pathname + here.search;
    if (answer.state === "page" && answer.page) {
      const extra: Record<string, string> = {};
      if (correction?.kind === "moved" && correction.para) extra.para = correction.para;
      else if (!correction && want.para) extra.para = want.para;
      if (want.passage && !correction) extra.passage = want.passage;
      to = pageAddress(pid, key, answer.page, extra);
    } else if (answer.canonical) {
      to = `/projects/${pid}/documents/${key}${here.search}`;
    }
    if (correction) setNotice({ search: new URL(to, window.location.origin).search, correction });
    navigate(to, { replace: true, quiet: true });
  }, [answer]);

  // The browser tab names the document and its page.
  useEffect(() => {
    if (document && answer?.page) setPageTitle(fill(words.documentTitle, { doc: crumbName(document), page: String(answer.page) }));
  }, [document, answer?.page]);

  // Focus on arrival: the highlighted paragraph, a third of the way down the window; with none, the h1.
  // After the page bar moved the page, focus stays on "Page n of m".
  useLayoutEffect(() => {
    if (!answer || answer.correction || answer.canonical) return;
    if (viaBar.current) {
      viaBar.current = false;
      position.current?.focus({ preventScroll: true });
      return;
    }
    const target = block.current;
    if (target) {
      const top = target.getBoundingClientRect().top + window.scrollY - window.innerHeight / 3;
      window.scrollTo({ top: Math.max(0, top) });
      target.focus({ preventScroll: true });
    } else if (here.moves > 0) title.current?.focus();
  }, [answer]);

  const projectsCrumb = { text: copy.breadcrumb.projects, href: "/projects" };
  const idText = <ProjectIdText pid={pid} />;
  const projectCrumb = {
    // The crumb is the link to the project, so its ID is plain mono inside it, never a link inside a link.
    text: answer?.project.display_name ? <Fill template={copy.breadcrumb.project} slots={{ name: answer.project.display_name, pid: idText }} /> : <Fill template={copy.breadcrumb.projectId} slots={{ pid: idText }} />,
    href: `/projects/${pid}`,
  };
  const documentsHref = `/projects/${pid}/documents`;
  const documentsCrumb = { text: words.documentsCrumb, href: documentsHref };
  const last = document ? crumbName(document) : load.status === "loading" ? <Skeleton className="inline-block h-[1em] w-40 align-middle" /> : copy.pages.document.title;

  const h1 = (text: ReactNode) => (
    <h1 ref={title} tabIndex={-1} className="mt-4 text-h1 text-balance text-ink-heading focus:outline-none">
      {text}
    </h1>
  );
  const page = answer?.page ?? want.page ?? 1;
  const shownNotice = notice && notice.search === here.search ? notice.correction : answer?.correction ?? null;

  let body: ReactNode;
  if (load.status === "loading") {
    body = (
      <>
        {h1(
          <>
            <span className="sr-only">{copy.pages.document.title}</span>
            <span aria-hidden="true" className="flex h-lh items-center">
              <Skeleton className="h-7 w-[420px] max-w-full" />
            </span>
          </>,
        )}
        <div aria-hidden="true" className="mt-4 flex flex-wrap gap-x-6 gap-y-2">
          {[0, 1, 2, 3, 4].map((index) => (
            <div key={index}>
              <SkeletonLine className="text-caption" width="w-12" />
              <SkeletonLine className="text-small" width="w-24" />
            </div>
          ))}
        </div>
        <SkeletonLine className="mt-3 text-caption" width="w-3/5" />
        <div className="mt-6">
          <PageBar pid={pid} doc={doc} page={page} pages={null} full onMove={() => (viaBar.current = true)} positionRef={position} />
        </div>
        <SourceSkeleton para={Boolean(want.para || want.passage)} />
        <p role="status" className="sr-only">
          {words.loading(String(page))}
        </p>
      </>
    );
  } else if (load.status === "error") {
    const notFound = load.error?.status === 404 && load.error.body.code === "unknown_project";
    body = notFound ? (
      <>
        {h1(<Fill template={copy.projectPage.notFoundTitle} slots={{ pid: <ProjectIdText pid={pid} /> }} />)}
        <p className="mt-2 max-w-prose text-body text-ink-muted">{copy.projectPage.notFoundBody}</p>
      </>
    ) : (
      <>
        {h1(copy.pages.document.title)}
        <div className="mt-6 max-w-[72ch]">
          <LoadError error={load.error} message={words.error} permission={words.permission} onRetry={retry} retrying={load.retrying} attempt={load.attempt} />
        </div>
      </>
    );
  } else if (answer!.state === "not_found" || answer!.state === "ambiguous") {
    const ambiguous = answer!.ambiguous;
    body = (
      <>
        {h1(copy.pages.document.title)}
        <div className="mt-6 max-w-[72ch]">
          {ambiguous ? (
            <EmptyState
              title={words.ambiguousTitle(whole(ambiguous.count), words.ambiguousPlural[ambiguous.type] ?? words.short.other)}
              body={words.ambiguousBody}
              link={{ href: documentsHref, text: words.notFoundLink }}
            />
          ) : (
            <EmptyState title={words.notFoundTitle} body={words.notFoundBody} link={{ href: documentsHref, text: words.notFoundLink }} />
          )}
        </div>
      </>
    );
  } else {
    const found = answer!;
    const doc_ = found.document!;
    const pdf = doc_.pdf_url;
    const key = doc_.doc_key ?? doc;
    let content: ReactNode;
    if (found.state === "not_public") {
      content = (
        <EmptyState
          title={fill(words.asofTitle, { date: formatDate(found.as_of) })}
          body={fill(words.asofBody, { date: found.disclosed_on ? formatDate(found.disclosed_on) : "" })}
          link={{ href: documentsHref, text: words.notFoundLink }}
        />
      );
    } else if (found.state === "doc_unread") {
      content = <EmptyState title={words.docUnreadTitle} body={words.docUnreadBody} link={pdf ? { href: pdf.replace(/^http:\/\//, "https://"), text: words.docUnreadLink } : undefined} />;
    } else {
      const state = found.page_state;
      const pdfLink = pdf ? { href: pdfPageHref(pdf, page), text: fill(words.pdf, { page: String(page) }) } : undefined;
      content = (
        <>
          <PageBar pid={pid} doc={key} page={page} pages={doc_.pdf_pages} full onMove={() => (viaBar.current = true)} positionRef={position} />
          <div className="mt-6">
            {state === "read" ? (
              <Passages answer={found} blockRef={block} />
            ) : (
              <EmptyState
                level={2}
                title={fill(state === "empty" ? words.pageEmptyTitle : state === "front_matter" ? words.pageFrontTitle : words.pageUnreadTitle, { page: String(page) })}
                body={state === "front_matter" ? words.pageFrontBody : words.pageUnreadBody}
                link={pdfLink}
              />
            )}
          </div>
          {state === "read" && (
            <div className="mt-6">
              <PageBar pid={pid} doc={key} page={page} pages={doc_.pdf_pages} full={false} onMove={() => (viaBar.current = true)} />
            </div>
          )}
        </>
      );
    }
    const reissue = doc_.replaces ?? doc_.replaced_by ?? null;
    body = (
      <>
        {h1(heading(doc_))}
        <Meta document={doc_} answer={found} />
        <p className="mt-3 max-w-prose text-caption text-ink-muted">{words.ownWords}</p>
        {(shownNotice || reissue) && (
          <div className="mt-4 flex max-w-[72ch] flex-col gap-2">
            {shownNotice && (
              <Alert state="info" live="status">
                {correctionText(shownNotice, doc_.pdf_pages)}
              </Alert>
            )}
            {doc_.replaces?.doc_key && doc_.replaces.document_date && doc_.document_date && (
              <Alert
                state="info"
                action={
                  <TextLink href={pageAddress(pid, doc_.replaces.doc_key, 1)}>
                    {fill(words.reissueCurrentLink, { date: table(doc_.replaces.document_date) })}
                  </TextLink>
                }
              >
                {fill(words.reissueCurrent, { reissue_date: formatDate(doc_.document_date), original_date: formatDate(doc_.replaces.document_date) })}
              </Alert>
            )}
            {doc_.replaced_by?.doc_key && doc_.replaced_by.document_date && (
              <Alert state="info" action={<TextLink href={pageAddress(pid, doc_.replaced_by.doc_key, 1)}>{words.reissueOldLink}</TextLink>}>
                {fill(words.reissueOld, { reissue_date: formatDate(doc_.replaced_by.document_date) })}
              </Alert>
            )}
          </div>
        )}
        {pdf && found.state === "page" && (
          <p className="mt-4">
            <ExternalLink href={pdfPageHref(pdf, page)} label={fill(words.pdf, { page: String(page) }) + copy.document.newTab}>
              {fill(words.pdf, { page: String(page) })}
            </ExternalLink>
          </p>
        )}
        <div className="mt-6">{content}</div>
      </>
    );
  }

  return (
    <div className="layout-grid" data-source-page={load.status === "ready" ? (answer!.state === "page" ? answer!.page_state : answer!.state) : load.status}>
      {/* A screen's height, as a project's tab body holds, so a short answer never pulls the footer up. */}
      <div className="col-span-12 min-h-svh @xl/page:col-span-7">
        <Breadcrumb trail={[projectsCrumb, projectCrumb, documentsCrumb, { text: last }]} />
        {body}
      </div>
    </div>
  );
}
