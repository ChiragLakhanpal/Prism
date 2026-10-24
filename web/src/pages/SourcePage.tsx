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
import { useEffect, useId, useLayoutEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Alert } from "../components/Alert";
import { Breadcrumb } from "../components/Breadcrumb";
import { Button } from "../components/Button";
import { EmptyState } from "../components/Card";
import { ExternalLink, pdfPageHref } from "../components/ExternalLink";
import { Fill } from "../components/Fill";
import { LoadError } from "../components/LoadError";
import { Num } from "../components/Num";
import { MethodText } from "../components/PlanCheck";
import { linkProjectIds, ProjectId } from "../components/ProjectId";
import { Skeleton, SkeletonLine, SkeletonText } from "../components/Skeleton";
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
function PageBar({
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
  const last = pages ?? page;
  const link = "inline-flex h-11 items-center gap-1 text-small";
  const go = (event: FormEvent) => {
    event.preventDefault();
    const to = Number(value);
    if (!Number.isInteger(to) || to < 1) return;
    onMove();
    navigate(pageAddress(pid, doc, Math.min(to, last)));
  };
  return (
    <nav aria-label={words.pages.label} data-page-bar className="flex flex-wrap items-center justify-between gap-x-6 gap-y-2 border-y border-line py-2">
      <TextLink href={pageAddress(pid, doc, page - 1)} onClick={onMove} className={cx(link, page <= 1 && "invisible")} aria-label={copy.pagination.previous}>
        <ChevronLeft aria-hidden="true" className="size-4 shrink-0" />
        <span className="xs:hidden">{copy.pagination.previousShort}</span>
        <span className="hidden xs:inline">{copy.pagination.previous}</span>
      </TextLink>
      {full ? (
        <>
          <p ref={positionRef} tabIndex={-1} data-lead className="text-caption text-ink-muted tabular-nums focus:outline-none">
            {words.pages.position(whole(page), whole(last))}
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
              max={last}
              value={value}
              onChange={(event) => setValue(event.target.value)}
              className="h-11 w-[6ch] min-w-16 rounded-md border border-line-strong bg-surface px-2 text-right text-body text-ink tabular-nums"
            />
            <Button variant="secondary" type="submit">
              {words.pages.goButton}
            </Button>
          </form>
        </>
      ) : (
        <span aria-hidden="true" />
      )}
      <TextLink href={pageAddress(pid, doc, page + 1)} onClick={onMove} className={cx(link, page >= last && "invisible")} aria-label={copy.pagination.next}>
        <span className="xs:hidden">{copy.pagination.nextShort}</span>
        <span className="hidden xs:inline">{copy.pagination.next}</span>
        <ChevronRight aria-hidden="true" className="size-4 shrink-0" />
      </TextLink>
    </nav>
  );
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

function Passages({ answer, blockRef }: { answer: SourcePageAnswer; blockRef: React.Ref<HTMLDivElement> }) {
  const passages = answer.passages ?? [];
  const highlight = answer.highlight;
  let section: string | null = null;
  return (
    <div className="flex max-w-[72ch] flex-col gap-4" data-passages>
      {passages.map((passage) => {
        const newSection = passage.section_path && passage.section_path !== section ? passage.section_path : null;
        section = passage.section_path ?? section;
        const id = passage.numbered ? `para-${passage.paragraph}` : `passage-${passage.passage_id}`;
        const text = (
          <p id={id} lang={passage.language ?? undefined} className="text-body wrap-anywhere text-ink" data-passage-id={passage.passage_id}>
            {linkProjectIds(passage.text)}
          </p>
        );
        const marked = highlight?.passage_id === passage.passage_id;
        return (
          <div key={passage.passage_id} className="flex flex-col gap-1">
            {newSection && <p className="text-caption text-ink-muted">{fill(words.section, { section: newSection })}</p>}
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
        <p key={index} className="text-body wrap-anywhere text-ink">
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
  const body = (
    <div className="overflow-x-auto rounded-md border border-line bg-surface">
      <table className="w-full border-collapse text-small">
        <caption className="px-3 py-2 text-left text-caption text-ink-muted">
          {title ? fill(words.tableTitled, { title, page: String(page) }) : fill(words.table, { page: String(page) })}
        </caption>
        <thead className="bg-surface-2">
          <tr>
            {heads.map((head) => (
              <th key={head} scope="col" className="px-3 py-2 text-left align-bottom font-semibold text-ink-heading">
                {head}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.passage_id} id={`passage-${row.passage_id}`} className={cx("border-t border-line align-top", row.passage_id === highlight && "bg-highlight")}>
              {heads.map((head) => (
                <td key={head} className="px-3 py-2 wrap-anywhere text-ink">
                  {row.cells.find(([name]) => name === head)?.[1] ?? ""}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
  return marked ? (
    <Highlighted blockRef={blockRef} caption={words.openedPassage}>
      {body}
    </Highlighted>
  ) : (
    body
  );
}

// A Procurement Plan's page: the STEP rows the layout parser read from its table.
function PlanRows({ answer }: { answer: SourcePageAnswer }) {
  const columns = copy.checkPlan.columns;
  const amount = (text: string | null) => (text ? formatNumber(Number(text), { decimals: 2, compact: false }) : copy.notInPlan);
  return (
    <div className="overflow-x-auto rounded-md border border-line bg-surface">
      <table className="w-full border-collapse text-small">
        <caption className="px-3 py-2 text-left text-caption text-ink-muted">{fill(words.planRows, { page: String(answer.page ?? 1) })}</caption>
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
          {(answer.plan_rows ?? []).map((row) => (
            <tr key={row.activity_reference_no} className="border-t border-line align-top">
              <th scope="row" className="px-3 py-2 text-left font-normal">
                <span className="block font-mono font-medium wrap-anywhere text-ink">{row.activity_reference_no}</span>
                {row.description && <span className="mt-1 block text-ink">{row.description}</span>}
              </th>
              <td className="px-3 py-2">{row.method ? <MethodText method={row.method} approach={row.market_approach} /> : copy.notInPlan}</td>
              <td className="px-3 py-2 text-right tabular-nums">{amount(row.estimated_amount_usd)}</td>
              <td className="px-3 py-2">{row.process_status ?? copy.notInPlan}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
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
  const projectCrumb = {
    text: answer?.project.display_name ? <Fill template={copy.breadcrumb.project} slots={{ name: answer.project.display_name, pid: <ProjectId pid={pid} /> }} /> : <Fill template={copy.breadcrumb.projectId} slots={{ pid: <ProjectId pid={pid} /> }} />,
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
        {h1(<Fill template={copy.projectPage.notFoundTitle} slots={{ pid: <span className="font-mono font-medium">{pid}</span> }} />)}
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
      <div className="col-span-12 @xl/page:col-span-7">
        <Breadcrumb trail={[projectsCrumb, projectCrumb, documentsCrumb, { text: last }]} />
        {body}
      </div>
    </div>
  );
}
