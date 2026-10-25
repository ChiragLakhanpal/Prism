// The evidence drawer (DESIGN.md section 5; the 14 brief, section 4.5): the whole numbered paragraph a
// citation points to, beside the page and never over it. It is a column clamp(400px, 40vw, 600px) wide
// whose panel stays in view while the page scrolls; the page narrows and stays usable, so it is a
// non-modal dialog. Below 768 px it is a full-screen sheet: modal, with the page behind it inert.
//
// From top to bottom: the stratum eyebrow, the source as its heading, a 44 px close; the sentence it
// was opened from and a switcher for that sentence's other sources; the paragraph with the matching
// words highlighted under its meta line; and a link to the page in the World Bank's PDF. A source the
// stream sent opens at once; one opened from a link is read from GET /api/evidence.
import { Lang } from "./Lang";
import { ENGLISH, workingLanguage } from "../lib/lang";
import { Fragment, useEffect, useId, useLayoutEffect, useRef, useState, type KeyboardEvent, type ReactNode, type RefObject } from "react";
import { ChevronLeft, X } from "lucide-react";
import { copy } from "../copy";
import { citationNumbers, type EvidenceEvent, type Run } from "../lib/answer";
import { ApiError, getJson } from "../lib/api";
import { cx } from "../lib/cx";
import { formatCount, formatDate, formatNumber } from "../lib/format";
import {
  closeEvidence,
  evidenceIn,
  focusRequests,
  known,
  openEvidence,
  origin as originStore,
  recordOpened,
  takeFocusRequest,
  type Origin,
} from "../lib/evidence";
import { address } from "../lib/router";
import { highlightsFor, lessonOf, passageFields, placeOf, recordReference } from "../lib/sources";
import { useStore } from "../lib/store";
import { viewOf } from "../lib/view";
import { Alert } from "./Alert";
import { Button } from "./Button";
import { Highlight, highlighted, withoutMarkers } from "./Document";
import { sourcePageHref } from "../lib/documents";
import { ExternalLink, pdfPageHref } from "./ExternalLink";
import { linkProjectIds, ProjectId } from "./ProjectId";
import { TextLink } from "./TextLink";
import { eyebrow, RecordSourceLine, SourceNumber, sourceTitle } from "./EvidenceCard";
import { Num } from "./Num";
import { MethodText } from "./PlanCheck";
import { ComparableDotList, ComparableRecords, dotRegion } from "./ComparableRecords";
import { COMPARABLE, DOT, type DotEntry } from "../lib/packages";
import { isRiskList, pageRows, REPORTS, rowOf } from "../lib/risks";
import { AllReportsView, backToReports, RiskReportsView, RowClaim, RowSwitcher } from "./RiskDrawer";
import { isStepList } from "../lib/steps";
import { LongestView, StepComparablesView } from "./StepsDrawer";
import { CaseClaim, CaseSwitcher } from "./RebidDrawer";
import { caseOf, pageCases } from "../lib/rebidding";
import { LoadingLabel, Skeleton, SkeletonLine, SkeletonText } from "./Skeleton";
import { FeedbackRow, type RowStart } from "./FeedbackRow";
import { showsRow } from "../lib/retrieval";
import { criteriaLessonOf, heldOnPage, pageLessons, type LessonEntry } from "../lib/criteria";
import { routeStepRef, useWhy, WhyThisSource } from "./WhyThisSource";
import { backLabel, criteriaClose, criteriaEyebrow, CriteriaDrawerBody, criteriaTitle, LessonClaim } from "./CriteriaDrawer";
import { ClaimLine, isTimelineView, timelineClose, timelineEyebrow, timelineTitle, TimelineView, UnknownDisagreement } from "./TimelineDrawer";
import { sideShort, type SideData } from "../lib/disagreement";

export type DrawerData =
  | { status: "loading" }
  | { status: "ready"; evidence: EvidenceEvent }
  | { status: "missing" }
  | { status: "failed"; onRetry: () => void };

// The passages' table, before the colon of a passage's evidence id.
const PASSAGE_TABLE = "strata.gold.passage:";

// The source an evidence id names: from the stream if it sent it, or else from the server.
export function useEvidence(id: string, asOf: string | null): DrawerData {
  const all = useStore(known);
  const [fetched, setFetched] = useState<{ id: string; data: DrawerData } | null>(null);
  const [attempt, setAttempt] = useState(0);
  const held = all[id];
  const here = useStore(address);
  // A preview asks for what its view may see: the public view of a project still under way shows no disagreement.
  const view = viewOf(here.search);
  // On an activity page, a passage's "Why this source" names the page's own activity (ticket 22).
  const stepRef = routeStepRef(here.pathname);
  // A passage an answer or a page sent with it carries no "Why this source" (undefined): ask the server for it
  // once, with the route's activity, and add it to the passage the page sent (the 22 review, item 3).
  const [why, setWhy] = useState<{ id: string; why: EvidenceEvent["why"] } | null>(null);
  const asksWhy = Boolean(held && held.kind === "passage" && held.why === undefined && id.startsWith(PASSAGE_TABLE));
  useEffect(() => {
    if (!asksWhy) return;
    const controller = new AbortController();
    const query =
      `/api/evidence?id=${encodeURIComponent(id)}${asOf ? `&asof=${encodeURIComponent(asOf)}` : ""}` +
      (stepRef ? `&step_ref=${encodeURIComponent(stepRef)}` : "") +
      (view !== "staff" ? `&view=${view}` : "");
    getJson<EvidenceEvent>(query, { signal: controller.signal }).then(
      (found) => setWhy({ id, why: found.why ?? null }),
      () => undefined, // the passage still shows; only its "Why this source" is left out
    );
    return () => controller.abort();
  }, [id, asksWhy, asOf, stepRef, view]);
  useEffect(() => {
    // A quantile dot's list is no source on the server: the page that draws the dots holds it (ticket 15). So are
    // section 5's lists and cost records (ticket 31), the risks section's lists of completion reports (ticket 30),
    // and section 2's steps' lists (ticket 27).
    if (held || id.startsWith(DOT) || heldOnPage(id) || isRiskList(id) || isStepList(id)) return;
    const controller = new AbortController();
    setFetched({ id, data: { status: "loading" } });
    const query =
      `/api/evidence?id=${encodeURIComponent(id)}${asOf ? `&asof=${encodeURIComponent(asOf)}` : ""}` +
      (stepRef ? `&step_ref=${encodeURIComponent(stepRef)}` : "") +
      (view !== "staff" ? `&view=${view}` : "");
    getJson<EvidenceEvent>(query, { signal: controller.signal }).then(
      (evidence) => setFetched({ id, data: { status: "ready", evidence } }),
      (error: unknown) => {
        if (controller.signal.aborted) return;
        const missing = error instanceof ApiError && error.status === 404;
        setFetched({ id, data: missing ? { status: "missing" } : { status: "failed", onRetry: () => setAttempt((n) => n + 1) } });
      },
    );
    return () => controller.abort();
  }, [id, held, asOf, view, attempt, stepRef]);
  if (held) return { status: "ready", evidence: asksWhy && why?.id === id ? { ...held, why: why.why } : held };
  return fetched?.id === id ? fetched.data : { status: "loading" };
}

// A section name this long or shorter, such as "III.B" or "Annex 3.C", keeps to one line in the meta
// line. An ISR's section names run to 40 characters ("Project Development Objective Indicators") and
// wrap, or a 320 px sheet would scroll sideways.
const SHORT_SECTION = 12;

// The meta line. The document type and the project's name may wrap; the date, a short section, the
// paragraph and the page ("October 10, 2019", "Section III.B", "¶54", "PDF page 23 of 66") each keep
// to one line. Each dot stays with the part before it, so a line breaks only after a dot or inside a
// long section's name.
// A table row's meta line names its table and row; a notice's names its type and section and has no
// page; a passage in another language ends with its language (the 18 brief, section 7).
function MetaLine({ evidence }: { evidence: EvidenceEvent }) {
  const fields = passageFields(evidence);
  const place = placeOf(fields);
  const words = copy.evidence.meta;
  const table = fields.kind === "table_row" || fields.kind === "table_summary";
  const notice = fields.kind === "notice_text";
  const language = fields.lang && fields.lang !== "en" ? copy.language.name[fields.lang] : null;
  const parts: { text: ReactNode; whole: boolean }[] = [
    { text: fields.docType, whole: false },
    {
      text: (
        <>
          {words.project.split(/\{(\w+)\}/).map((part, index) =>
            index % 2 === 0 ? part : part === "pcode" ? <ProjectId key={index} pid={fields.pcode} /> : <span key={index}>{fields.project}</span>,
          )}
        </>
      ),
      whole: false,
    },
    { text: fields.date, whole: true },
    ...(table
      ? [
          ...(fields.tableTitle ? [{ text: fields.tableTitle, whole: false }] : []),
          ...(fields.tableRow ? [{ text: copy.evidence.rowOf(String(fields.tableRow)), whole: true }] : []),
        ]
      : notice
        ? fields.section
          ? [{ text: fields.section, whole: false }]
          : []
        : [
            ...(fields.section ? [{ text: words.section(fields.section), whole: fields.section.length <= SHORT_SECTION }] : []),
            ...(place.kind === "paragraph" ? [{ text: words.para(place.text), whole: true }] : []),
          ]),
    ...(fields.page
      ? [
          {
            text:
              fields.kind === "table_summary" && fields.lastPage && fields.lastPage !== fields.page && fields.pages
                ? words.pageRange(String(fields.page), String(fields.lastPage), String(fields.pages))
                : fields.pages
                  ? words.page(String(fields.page), String(fields.pages))
                  : words.pageOnly(String(fields.page)),
            whole: true,
          },
        ]
      : []),
    ...(language ? [{ text: copy.evidence.inLanguage(language), whole: true }] : []),
  ].filter((part) => part.text !== "");
  return (
    <p data-meta-line className="rounded-t-md bg-surface-2 px-3 py-2 text-caption text-ink-muted">
      {parts.map((part, index) => (
        <Fragment key={index}>
          {index > 0 && " "}
          <span data-meta-part className={part.whole ? "whitespace-nowrap" : undefined}>
            {part.text}
            {index < parts.length - 1 && words.dot}
          </span>
        </Fragment>
      ))}
    </p>
  );
}

// Where each cell's value sits in the row's text, which joins the cells as "Risk: Capacity; Rating: Low",
// so a highlight in the text lands on the cell it matched. Null when the text is not that join.
function cellSpans(fields: ReturnType<typeof passageFields>): [number, number][] | null {
  const spans: [number, number][] = [];
  let at = 0;
  for (const [label, value] of fields.cells) {
    const start = at + label.length + 2;
    spans.push([start, start + value.length]);
    at = start + value.length + 2;
  }
  return fields.cells.map(([label, value]) => `${label}: ${value}`).join("; ") === fields.text ? spans : null;
}

// A highlight's part inside one cell, counted from the cell's own start.
function inCell([start, end]: [number, number], ranges: [number, number][]): [number, number][] {
  return ranges.filter(([from, to]) => from < end && to > start).map(([from, to]) => [Math.max(from, start) - start, Math.min(to, end) - start]);
}

// A table row's cells: each column head as a row header on the left and its value on the right, as the
// layout parser read them. A Procurement Plan's heads are STEP's own field names. The cell whose value a
// sentence quoted carries the highlight (the 18 brief, section 7.2).
function RowCells({ fields, ranges }: { fields: ReturnType<typeof passageFields>; ranges: [number, number][] }) {
  const spans = cellSpans(fields);
  return (
    <table data-row-cells className="m-4 w-[calc(100%-2rem)] border-collapse text-small">
      <thead className="sr-only">
        <tr>
          <th scope="col">{copy.evidence.rowField}</th>
          <th scope="col">{copy.evidence.rowValue}</th>
        </tr>
      </thead>
      <Lang as="tbody" code={fields.lang}>
        {fields.cells.map(([label, value], index) => (
          <tr key={index} className="border-t border-line first:border-t-0 align-top">
            <th scope="row" className="w-2/5 py-2 pr-3 text-left font-semibold text-ink">
              {label}
            </th>
            <td className={cx("py-2 wrap-break-word text-ink", /^[\d,.\s]+$/.test(value) && "text-right tabular-nums")}>
              {spans ? highlighted(value, inCell(spans[index], ranges), true) : value}
            </td>
          </tr>
        ))}
      </Lang>
    </table>
  );
}

// The passage block outside the drawer (ticket 32): a passage under review on Passage reports, or one to grade on
// Judging, shown whole with its meta strip and "Open at page", and no highlight, since no sentence opened it.
export function PassageBlock({ evidence }: { evidence: EvidenceEvent }) {
  return <PassageView evidence={evidence} sentence={null} fromAnswer={false} given={[]} />;
}

// given: the quote's place when no answer's sentence opened the drawer, such as a lesson's evidence card.
function PassageView({ evidence, sentence, fromAnswer, given = null }: { evidence: EvidenceEvent; sentence: number | null; fromAnswer: boolean; given?: [number, number][] | null }) {
  const fields = passageFields(evidence);
  const place = placeOf(fields);
  const section = place.kind === "section";
  // Ticket 22: a passage that appeared together with a contract highlights the words they share, unless a
  // sentence or a card opened it at its own quote.
  const why = useWhy(evidence);
  const shared = why ? why.mentions.map((mention) => [mention.start, mention.end] as [number, number]) : [];
  const quoted = highlightsFor(evidence, sentence);
  const ranges = given ?? (quoted.length > 0 || fromAnswer ? quoted : shared);
  const working = useStore(workingLanguage)?.code ?? ENGLISH;
  const pdf = fields.pdfUrl && fields.page ? pdfPageHref(fields.pdfUrl, fields.page) : null;
  // Ticket 21: "Open at page N" opens the in-app source view at the page, in the same tab, with the
  // paragraph highlighted, or the passage when it has no paragraph number. The PDF link lives there.
  const here = fields.docKey && fields.pcode && fields.page
    ? sourcePageHref(fields.pcode, fields.docKey, fields.page, place.kind === "paragraph" ? { para: fields.para } : { passage: fields.passageId })
    : null;
  const notice = fields.kind === "notice_text";
  const row = fields.kind === "table_row";
  const summary = fields.kind === "table_summary";
  const note = notice
    ? copy.evidence.noticeWhole
    : row
      ? copy.evidence.rowNote
      : summary
        ? null
        : fields.scanned
          ? copy.evidence.wholeScanned
          : section
            ? copy.evidence.wholeSection
            : copy.evidence.whole;
  return (
    <>
      <div className="rounded-md border border-line">
        <MetaLine evidence={evidence} />
        {summary && fields.page && (
          <p className="px-4 pt-3 text-caption text-ink-muted">
            {copy.evidence.summaryNote(String(fields.page), fields.lastPage && fields.lastPage !== fields.page ? String(fields.lastPage) : null)}
          </p>
        )}
        {fromAnswer && ranges.length === 0 && (
          <p className="px-4 pt-3 text-caption text-ink-muted">
            {row ? copy.evidence.noHighlightRow : section ? copy.evidence.noHighlightSection : copy.evidence.noHighlight}
          </p>
        )}
        {row ? (
          <RowCells fields={fields} ranges={ranges} />
        ) : (
          <Lang as="p" code={fields.lang} data-passage data-kind={fields.kind} className="max-w-prose p-4 text-body text-ink">
            {notice ? withoutMarkers(highlighted(fields.text, ranges, true)) : highlighted(fields.text, ranges, true)}
          </Lang>
        )}
      </div>
      {note && (
        <p className="text-caption text-ink-muted">
          {note}
          {/* A passage in another language than yours: I never translate a source (the 42 brief, section 5.7). */}
          {fields.lang && fields.lang !== working && (
            <>
              {" "}
              {copy.evidence.ownLanguage}
            </>
          )}
        </p>
      )}
      {why && <WhyThisSource why={why} />}
      {notice && fields.noticeUrl ? (
        <p>
          <ExternalLink href={fields.noticeUrl}>{copy.evidence.openNotice}</ExternalLink>
        </p>
      ) : here !== null ? (
        <p>
          <TextLink href={here} className="text-small" data-open-at-page>
            {copy.document.openAtPageHere(String(fields.page))}
          </TextLink>
        </p>
      ) : (
        pdf !== null && (
          <p>
            <ExternalLink href={pdf}>{copy.document.openAtPage(String(fields.page))}</ExternalLink>
          </p>
        )
      )}
    </>
  );
}

// A side of a disagreement in the drawer's disagreement view (ticket 23): its passage or record, read as any source
// opened from a link is, with no highlight, since no sentence opened it.
function SidePassage({ id, asOf }: { id: string; asOf: string | null }) {
  const data = useEvidence(id, asOf);
  if (data.status === "loading") {
    return (
      <div aria-busy="true" className="rounded-md border border-line">
        <Skeleton className="h-8 w-full rounded-b-none" />
        <SkeletonText className="max-w-prose p-4 text-body" widths={["w-full", "w-full", "w-3/5"]} />
      </div>
    );
  }
  if (data.status === "missing") return <Alert state="neutral">{copy.document.missing}</Alert>;
  if (data.status === "failed") {
    return (
      <Alert state="error" action={<Button variant="secondary" onClick={data.onRetry}>{copy.answer.tryAgain}</Button>}>
        {copy.document.failed}
      </Alert>
    );
  }
  if (data.evidence.kind === "record") return <RecordView evidence={data.evidence} />;
  return <PassageView evidence={data.evidence} sentence={null} fromAnswer={false} />;
}

// The What stratum's view: the fields of the record a tool returned, under STEP's own names, in a
// two-column definition list (the 14 brief, section 4.5.3): the Description, the Method and the
// Process status across, Review and the amount side by side, the amount right-aligned on the list's
// edge in STEP's form with its cents (DESIGN.md section 6), then the source line.
function RecordView({ evidence }: { evidence: EvidenceEvent }) {
  const row = evidence.row;
  const here = useStore(address).pathname;
  const columns = copy.checkPlan.columns;
  const given = (value: unknown) => value !== null && value !== undefined && value !== "";
  const fields: { label: string; value: ReactNode; wide?: boolean; numeric?: boolean; ledger?: boolean }[] = [];
  // A record a project's Summary cites (ticket 21) lists its fields by key: dates as dates, amounts in
  // their source's form with cents, and text as the record gives it. Each amount takes a whole line, its
  // label on the left and the amount on the list's right edge, so a loan's three amounts line up and the
  // date after them starts its own line at the left (the 21 design review, round 2, F19).
  const listed = (Array.isArray(row.fields) ? row.fields : []) as { key: string; value: string; kind: string; highlight?: boolean }[];
  // A signed amount's currency: the trail's contract carries it on the row (ticket 22), and a mission brief's
  // award record as its own field beside an amount it has in no other currency (ticket 37).
  const listedCurrency = listed.find((field) => field.key === "currency")?.value;
  const currency = typeof row.currency === "string" ? row.currency : typeof listedCurrency === "string" ? listedCurrency : null;
  for (const field of listed) {
    // A key is Strata's own name for a value, such as a rating's "pdo", which means nothing to a reader.
    if (field.kind === "key") continue;
    // A contract's signed amount carries its currency in its label (ticket 22): "Signed amount (INR)".
    const label =
      field.key === "signed_amount"
        ? !currency || currency === "USD"
          ? copy.trail.contract.field.signedAmountUsd
          : copy.trail.contract.field.signedAmount(currency)
        : (copy.evidence.summaryRecordFields[field.key] ?? field.key);
    // The field a line states, such as the date a plan signal fired on (ticket 37), is highlighted.
    const marked = (value: ReactNode) => (field.highlight ? <Highlight>{value}</Highlight> : value);
    if (field.kind === "date") fields.push({ label, value: marked(<Num date={field.value} />) });
    else if (field.kind === "usd" || field.kind === "amount") {
      fields.push({ label, value: marked(<Num value={Number(field.value)} options={{ decimals: 2, compact: false }} />), numeric: true, ledger: true });
    }
    // A contract signed by an individual consultant names no one (ticket 22).
    else if (field.kind === "supplier" && field.value === "individual_consultant") fields.push({ label, value: copy.trail.bids.individual, wide: true });
    // The field a sentence or a row quoted, such as an award notice's Reason for Rejection (ticket 31), is highlighted.
    else if (field.highlight) fields.push({ label, value: <Highlight>{String(field.value)}</Highlight>, wide: true });
    else fields.push({ label, value: linkProjectIds(String(field.value)), wide: String(field.value).length > 24 });
  }
  if (given(row.description)) fields.push({ label: copy.evidence.recordDescription, value: String(row.description), wide: true });
  if (given(row.method)) fields.push({ label: columns.method, value: <MethodText method={String(row.method)} approach={row.market_approach} />, wide: true });
  if (given(row.review_type)) fields.push({ label: columns.review, value: String(row.review_type) });
  if (given(row.estimated_amount_usd)) {
    fields.push({ label: columns.estimated, value: <Num value={Number(row.estimated_amount_usd)} options={{ decimals: 2, compact: false }} />, numeric: true });
  }
  if (given(row.process_status)) fields.push({ label: columns.status, value: String(row.process_status), wide: true });
  return (
    <div className="flex flex-col gap-4 rounded-md border border-line p-4">
      {/* A lesson has no STEP fields: its statement is the drawer's title, so only its source line shows. */}
      {fields.length > 0 && <dl data-record data-numbers className="grid grid-cols-2 gap-x-4 gap-y-2">
        {fields.map((field, index) =>
          field.ledger ? (
            <div key={index} className="col-span-full flex min-w-0 items-baseline justify-between gap-4">
              <dt className="text-caption text-ink-muted">{field.label}</dt>
              <dd className="text-right text-small whitespace-nowrap text-ink tabular-nums">{field.value}</dd>
            </div>
          ) : (
            <div key={index} className={cx("min-w-0", field.wide && "col-span-full", field.numeric && "text-right")}>
              <dt className="text-caption text-ink-muted">{field.label}</dt>
              <dd className={cx("text-small wrap-break-word text-ink", field.numeric && "text-right tabular-nums")}>{field.value}</dd>
            </div>
          ),
        )}
      </dl>}
      <RecordSourceLine evidence={evidence} />
      {/* A notice, award notice, contract or plan row whose activity Strata holds opens its trail (ticket 22), unless
          the drawer is open on that trail already. */}
      {typeof row.activity_href === "string" && row.activity_href !== here && (
        <p>
          <TextLink href={row.activity_href} className="inline-flex min-h-6 items-center text-small" data-record-activity>
            {copy.evidence.openActivity}
            <span className="clip-visually">{copy.evidence.openActivityFor(String(row.step_reference ?? ""))}</span>
          </TextLink>
        </p>
      )}
    </div>
  );
}

// The sources of the sentence the drawer was opened from: one pill-shaped tab each. Left and Right move
// between them, Home and End jump to the ends, and selection follows focus.
function SourceSwitcher({
  ids,
  current,
  run,
  panelId,
  onChoose,
}: {
  ids: string[];
  current: string;
  run: Run;
  panelId: string;
  onChoose: (id: string) => void;
}) {
  const refs = useRef<(HTMLButtonElement | null)[]>([]);
  const index = ids.indexOf(current);
  const label = (id: string): ReactNode => {
    const evidence = run.evidence[id];
    if (!evidence) return id;
    const lesson = lessonOf(evidence);
    if (lesson) return copy.evidence.switcherLesson(formatNumber(lesson.version, { compact: false }));
    if (evidence.kind === "record") return recordReference(evidence);
    const fields = passageFields(evidence);
    const place = placeOf(fields);
    const short = evidence.short_name ?? fields.docType;
    if (place.kind === "section") return <span>{copy.evidence.switcherSection(short, place.text)}</span>;
    // One inline span, so the space after the short name stays: a tab is a flex container, and flex
    // drops a text node that holds only a space.
    return (
      <span>
        {short}{" "}
        <span aria-hidden="true" data-para-mark>
          {copy.evidence.paraMark}
        </span>
        <span className="sr-only">{copy.evidence.paraSpoken}</span>
        {place.text}
      </span>
    );
  };
  const onKeyDown = (event: KeyboardEvent<HTMLButtonElement>) => {
    const moves: Record<string, number> = { ArrowRight: index + 1, ArrowLeft: index - 1, Home: 0, End: ids.length - 1 };
    if (!(event.key in moves)) return;
    event.preventDefault();
    const next = (moves[event.key] + ids.length) % ids.length;
    refs.current[next]?.focus();
    onChoose(ids[next]);
  };
  return (
    <div role="tablist" aria-label={copy.evidence.switcher} className="flex flex-wrap gap-2">
      {ids.map((id, at) => {
        const selected = id === current;
        return (
          <button
            key={id}
            ref={(element) => {
              refs.current[at] = element;
            }}
            type="button"
            role="tab"
            id={`${panelId}-tab-${at}`}
            aria-selected={selected}
            aria-controls={panelId}
            tabIndex={selected ? 0 : -1}
            onClick={() => onChoose(id)}
            onKeyDown={onKeyDown}
            className={cx(
              "inline-flex min-h-8 items-center rounded-pill border border-line-strong px-3 py-1 text-left text-small text-ink transition-paint duration-150",
              selected ? "bg-tint shadow-[inset_0_0_0_1px_var(--color-primary)]" : "bg-surface hover:bg-tint-hover",
            )}
          >
            {label(id)}
          </button>
        );
      })}
    </div>
  );
}

// The drawer as it looks, for a source in any state. The design gallery draws it as it is; the page
// draws it through EvidenceDrawer, which reads, records and moves focus.
export function EvidenceDrawerView({
  id,
  data,
  run,
  from,
  narrow,
  preview,
  asOf = null,
  dialogId = "evidence-drawer",
  sample = false,
  panelRef,
  headingRef,
  onClose,
  onChoose,
  onOpenEntry,
  onBack,
  onOpenListEntry,
  onChooseRow,
  onOpenReport,
  feedbackStart,
  lesson: givenLesson,
}: {
  id: string;
  data: DrawerData;
  // The answer on the page, if the drawer was opened from it.
  run: Run | null;
  // The marker or number that opened it, if it was opened from the answer.
  from: Origin | null;
  // Below 768 px the drawer is a modal sheet.
  narrow: boolean;
  // A preview of another view records nothing, and the drawer says so.
  preview: boolean;
  // The address's as-of date, which the drawer read the source as of.
  asOf?: string | null;
  dialogId?: string;
  // A design gallery sample: as wide as its frame, and not held in view.
  sample?: boolean;
  panelRef?: RefObject<HTMLDivElement | null>;
  headingRef?: RefObject<HTMLHeadingElement | null>;
  onClose: () => void;
  // A switcher tab chose another source of the same sentence.
  onChoose: (id: string) => void;
  // A package in a quantile dot's list was chosen, or the way back to that list (ticket 15).
  onOpenEntry?: (entry: DotEntry) => void;
  onBack?: (listId: string) => void;
  // A notice in one of section 5's lists was chosen (ticket 31).
  onOpenListEntry?: (entry: string, list: { id: string; count: number }, highlight?: [number, number] | null) => void;
  // A switcher tab of a risk's row chose another of its sources, and a report in a risk's list was chosen
  // (ticket 30).
  onChooseRow?: (id: string) => void;
  onOpenReport?: (evidenceId: string) => void;
  // A design gallery sample's feedback row state (ticket 32), which also shows the row without an answer.
  feedbackStart?: RowStart;
  // Section 5's lesson whose paragraph this is, for the design gallery; the page finds it in the section's lessons.
  lesson?: LessonEntry | null;
}) {
  const headingId = useId();
  const passageId = useId();
  const [scrolled, setScrolled] = useState(false);
  const headerRef = useRef<HTMLDivElement>(null);

  // The browser keeps a focused element below the sticky header (WCAG 2.2 SC 2.4.11, technique C43):
  // the panel's scroll padding is as tall as the header, plus 8 px, and follows it as the heading wraps.
  useLayoutEffect(() => {
    const header = headerRef.current;
    const container = panelRef?.current;
    if (!header || !container) return;
    const pad = () => container.style.setProperty("scroll-padding-top", `calc(${header.offsetHeight}px + var(--spacing) * 2)`);
    pad();
    const watch = new ResizeObserver(pad);
    watch.observe(header);
    return () => watch.disconnect();
  }, [panelRef]);

  // The sentence it was opened from, while that same answer is still on the page.
  const claim =
    from && run && from.id === id && from.serial === run.serial && from.sentence !== null
      ? run.sentences.find((sentence) => sentence.index === from.sentence && sentence.evidence_ids.includes(id))
      : undefined;
  // A side of a disagreement shown under a sentence, opened from the card's marker (ticket 24): the sentence does
  // not cite it, so no claim block shows, but the drawer highlights the words the side quotes, as the stream marks
  // them for the sentence the card follows.
  const cardSentence =
    !claim &&
    from &&
    run &&
    from.id === id &&
    from.serial === run.serial &&
    run.disagreements.some((found) => found.after === from.sentence && found.sides.some((side) => side.evidence_id === id))
      ? from.sentence
      : null;
  const numbering = run ? citationNumbers(run) : new Map<string, number>();
  const evidence = data.status === "ready" ? data.evidence : null;
  // A source opened from a risk's row, or from the address while the row shows (ticket 30): the drawer restores
  // the row's claim, its IEG line and its switcher when the source belongs to exactly one row on the page.
  const rows = useStore(pageRows);
  const riskRow = !claim && evidence?.kind === "passage" ? rowOf(id, rows) : null;
  const rowSwitcher = riskRow && riskRow.sources.length > 1 ? riskRow : null;
  // A record opened from a row of section 1's "Advertised again" block (ticket 28), or from the address while the
  // row shows: the row's line as the claim, and a tab for each of its records when it has two or more.
  const cases = useStore(pageCases);
  const rebidCase = !claim && !riskRow ? caseOf(id, cases.rows) : null;
  const caseSwitcher = rebidCase && rebidCase.evidence.length > 1 ? rebidCase : null;
  const switcherIds = claim && claim.evidence_ids.length > 1
    ? claim.evidence_ids
    : rowSwitcher
      ? rowSwitcher.sources.map((source) => source.evidence_id)
      : caseSwitcher
        ? caseSwitcher.evidence.map((item) => item.evidence_id)
        : null;
  // A lesson's paragraph opened from section 5 (ticket 31, view F): the lesson and its IEG line.
  const lessons = useStore(pageLessons);
  const criteriaLesson = !claim && !riskRow && evidence?.kind === "passage" ? (givenLesson ?? criteriaLessonOf(id, lessons)) : null;
  // A comparable package from the range chart (ticket 15): its region names it as one, and its close says
  // what it closes. A quantile dot's list of packages is named by its count and its dot, and a package
  // opened from that list has a way back to it above its title.
  const comparable = id.startsWith(COMPARABLE);
  const comparableRef = comparable ? id.slice(COMPARABLE.length) : null;
  const dotList = id.startsWith(DOT);
  // A notice opened from one of section 5's lists has a way back to that list too (ticket 31).
  const criteriaList = from?.list && heldOnPage(from.list.id) ? from.list : null;
  const riskList = isRiskList(id);
  const stepList = isStepList(id);
  const backTo = (comparable || criteriaList || evidence?.kind === "passage") && from?.id === id && from.list ? from.list : null;
  const criteriaView = evidence && (evidence.kind === "criteria_public" || evidence.kind === "criteria_item" || evidence.kind === "package_cost");
  // The feedback row: a passage a search found, opened from the answer it belongs to (a marker, a number or a
  // switcher tab of that answer), never from a bare link to the source (the 32 brief, section 4.1).
  const fromItsAnswer = Boolean(claim) || (from?.id === id && Boolean(from.runId) && from.runId === evidence?.feedback?.run_id);
  const row = evidence?.kind === "passage" && showsRow(evidence.feedback) && (fromItsAnswer || feedbackStart !== undefined);
  const region = evidence?.kind === "dot" ? dotRegion(evidence) : comparableRef ? copy.evidence.package.region(comparableRef) : undefined;
  // A project timeline's views (ticket 23), and a disagreement of the answer that opened the drawer from its sentence.
  const timelineView = isTimelineView(evidence);
  const timelineId = /^(doc|ratings|contracts|disagreement):/.test(id);
  // Every sentence the disagreement changes gets the line, not only the one its card follows.
  const claimDisagreement =
    claim && run ? (run.disagreements.find((found) => found.after === claim.index || found.changes_sentence_ids?.includes(claim.index)) ?? null) : null;

  return (
    <div
      role="dialog"
      id={dialogId}
      aria-modal={narrow}
      aria-labelledby={region ? undefined : headingId}
      aria-label={region}
      data-evidence-drawer={narrow ? "sheet" : "drawer"}
      className={cx(
        "bg-surface",
        sample
          ? "w-full"
          : narrow
            ? "fixed inset-0 z-50 animate-sheet-in"
            : "w-[clamp(400px,40vw,600px)] shrink-0 self-stretch border-l border-line",
      )}
    >
      <div
        ref={panelRef}
        onScroll={(event) => setScrolled(event.currentTarget.scrollTop > 0)}
        className={cx(!sample && "overflow-y-auto", !sample && (narrow ? "h-dvh" : "sticky top-0 max-h-dvh"))}
        style={narrow ? { paddingBottom: "env(safe-area-inset-bottom)" } : undefined}
      >
        <div
          ref={headerRef}
          data-drawer-header
          className={cx("sticky top-0 z-10 flex items-start gap-4 border-b bg-surface px-6 pt-6 pb-4", scrolled ? "border-line" : "border-transparent")}
        >
          <div className="min-w-0 flex-1">
            {backTo && onBack && (
              <Button variant="ghost" icon={ChevronLeft} onClick={() => onBack(backTo.id)} className="-mt-2 mb-2 -ml-3">
                {heldOnPage(backTo.id)
                  ? backLabel(backTo)
                  : backTo.id.startsWith(REPORTS)
                    ? backToReports(backTo.count)
                    : backTo.count === 1
                      ? copy.evidence.package.dot.backOne
                      : copy.evidence.package.dot.back(formatCount(backTo.count))}
              </Button>
            )}
            {evidence && (
              <p className="text-label text-ink-muted uppercase">
                {criteriaView ? criteriaEyebrow(evidence) : timelineView ? timelineEyebrow(evidence) : eyebrow(evidence)}
              </p>
            )}
            {data.status === "loading" && <SkeletonLine className="text-label" width="w-1/3" />}
            <h2 ref={headingRef} id={headingId} tabIndex={-1} className="mt-1 text-title wrap-break-word text-ink-heading focus:outline-none">
              {evidence ? (
                criteriaView ? criteriaTitle(evidence) : timelineView ? timelineTitle(evidence) : sourceTitle(evidence)
              ) : data.status === "loading" ? (
                <LoadingLabel />
              ) : comparableRef ? (
                // A comparable package that could not load is still titled by its STEP reference (brief 7.8).
                <span className="font-mono">{comparableRef}</span>
              ) : (
                copy.evidence.untitled
              )}
              {data.status === "loading" && <SkeletonText widths={["w-4/5"]} />}
            </h2>
          </div>
          <Button
            variant="ghost"
            icon={X}
            iconOnly
            onClick={onClose}
            className="-mt-2 -mr-2"
          >
            {heldOnPage(id)
              ? criteriaClose(evidence, id)
              : dotList
                ? copy.evidence.package.dot.close
                : riskList
                  ? copy.packageRisks.drawer.close
                  : stepList
                    ? copy.stepDates.drawer.close
                    : comparable
                      ? copy.evidence.package.close
                      : timelineView || timelineId
                        ? timelineClose(evidence, id)
                        : copy.evidence.close}
          </Button>
        </div>
        <div className="flex animate-drawer-in flex-col gap-4 px-6 pt-2 pb-6">
          {claim && (
            <div data-claim>
              <p className="text-caption text-ink-muted">{copy.evidence.fromAnswer}</p>
              {/* The claim is in the answer's language, and its source number in the copy file's English (ticket 42). */}
              <Lang as="p" code={run?.lang ?? null} className="mt-1 border-l-2 border-line-strong pl-3 text-small text-ink">
                {claim.text}
                {numbering.get(id) && (
                  <Lang code="en" className="ml-1 inline-flex align-[1px]">
                    <SourceNumber n={numbering.get(id)!} />
                  </Lang>
                )}
              </Lang>
            </div>
          )}
          {/* A timeline's event mark: "From the timeline" and the event, above the passage that dates it (ticket 23). */}
          {!claim && from?.id === id && from.context && (
            <div data-from-timeline>
              <p className="text-caption text-ink-muted">{from.context.lead}</p>
              <p className="mt-1 border-l-2 border-line-strong pl-3 text-small text-ink">{from.context.line}</p>
            </div>
          )}
          {claim && claimDisagreement && (
            <ClaimLine
              warning={claimDisagreement.changes_answer}
              disagreementId={`disagreement:${claimDisagreement.disagreement_id ?? claimDisagreement.id.split(":").pop()}`}
              text={copy.timeline.drawer.claimLine
                .replace("{side1}", sideShort(claimDisagreement.sides[0] as SideData))
                .replace("{side2}", sideShort(claimDisagreement.sides[1] as SideData))}
            />
          )}
          {riskRow && <RowClaim row={riskRow} />}
          {rebidCase && <CaseClaim row={rebidCase} id={id} through={cases.through} />}
          {criteriaLesson && <LessonClaim lesson={criteriaLesson} />}
          {switcherIds && claim && run && (
            <SourceSwitcher ids={switcherIds} current={id} run={run} panelId={passageId} onChoose={onChoose} />
          )}
          {rowSwitcher && <RowSwitcher row={rowSwitcher} current={id} panelId={passageId} onChoose={onChooseRow ?? onChoose} />}
          {caseSwitcher && <CaseSwitcher row={caseSwitcher} current={id} panelId={passageId} onChoose={onChooseRow ?? onChoose} />}
          <div
            id={passageId}
            role={switcherIds ? "tabpanel" : undefined}
            aria-labelledby={switcherIds ? `${passageId}-tab-${switcherIds.indexOf(id)}` : undefined}
            className="flex flex-col gap-4"
          >
            {data.status === "loading" && (
              <div aria-busy="true" className="rounded-md border border-line">
                <Skeleton className="h-8 w-full rounded-b-none" />
                <SkeletonText className="max-w-prose p-4 text-body" widths={["w-full", "w-full", "w-full", "w-full", "w-full", "w-3/5"]} />
              </div>
            )}
            {data.status === "missing" &&
              (id.startsWith("disagreement:") ? (
                <UnknownDisagreement asOf={asOf} />
              ) : (
                <Alert state="neutral">{asOf ? copy.document.missingAsOf(formatDate(asOf)) : copy.document.missing}</Alert>
              ))}
            {data.status === "failed" && (
              <Alert
                state="error"
                live="alert"
                action={
                  <Button variant="secondary" onClick={data.onRetry}>
                    {copy.answer.tryAgain}
                  </Button>
                }
              >
                {comparable ? copy.evidence.package.error : copy.document.failed}
              </Alert>
            )}
            {evidence?.kind === "passage" && (
              <PassageView
                evidence={evidence}
                sentence={claim ? claim.index : cardSentence}
                fromAnswer={Boolean(claim)}
                given={!claim && from?.id === id && from.highlight ? [from.highlight] : null}
              />
            )}
            {evidence?.kind === "record" && <RecordView evidence={evidence} />}
            {evidence && timelineView && <TimelineView evidence={evidence} renderSide={(sideId) => <SidePassage id={sideId} asOf={asOf} />} />}
            {evidence?.kind === "package" && <ComparableRecords evidence={evidence} />}
            {evidence?.kind === "dot" && (
              <ComparableDotList evidence={evidence} focusEntry={from?.id === id ? (from.entry ?? null) : null} onOpen={onOpenEntry} />
            )}
            {criteriaView && evidence && (
              <CriteriaDrawerBody
                evidence={evidence}
                focusEntry={from?.id === id ? (from.entry ?? null) : null}
                onOpen={(entry, list, _element, highlight) => onOpenListEntry?.(entry, list, highlight)}
              />
            )}
            {evidence?.kind === "risk-reports" && (
              <RiskReportsView evidence={evidence} focusEntry={from?.id === id ? (from.entry ?? null) : null} onOpen={onOpenReport} />
            )}
            {evidence?.kind === "risk-reports-all" && <AllReportsView evidence={evidence} />}
            {evidence?.kind === "steps" && (
              <StepComparablesView evidence={evidence} focusEntry={from?.id === id ? (from.entry ?? null) : null} onOpen={onOpenEntry} />
            )}
            {evidence?.kind === "steps-longest" && (
              <LongestView evidence={evidence} focusEntry={from?.id === id ? (from.entry ?? null) : null} onOpen={onOpenEntry} />
            )}
            {data.status === "loading" && comparable && (
              <div aria-hidden="true" className="flex flex-col gap-4">
                <Skeleton className="h-48 w-full rounded-md" />
                <Skeleton className="h-48 w-full rounded-md" />
              </div>
            )}
          </div>
          {/* Ticket 32: "Was this the right passage?", after the paragraph, for a passage a search found for the
              question of the answer it was opened from; never from a bare link. Its own preview line replaces
              brief 14's. */}
          {row && evidence?.feedback && (
            <FeedbackRow evidenceId={id} feedback={evidence.feedback} sentence={claim ? claim.index : null} preview={preview} start={feedbackStart} />
          )}
          {preview && !row && <p className="text-caption text-ink-muted">{copy.evidence.preview}</p>}
        </div>
      </div>
    </div>
  );
}

export function EvidenceDrawer({
  id,
  run,
  narrow,
  preview,
  asOf,
  onClosed,
}: {
  id: string;
  // The answer on the page, if the drawer was opened from it.
  run: Run | null;
  narrow: boolean;
  preview: boolean;
  asOf: string | null;
  // Called as the drawer closes, with whether focus was inside it, so it can go back to the marker.
  onClosed: (returnFocus: boolean) => void;
}) {
  const data = useEvidence(id, asOf);
  const from = useStore(originStore);
  const requests = useStore(focusRequests);
  const panel = useRef<HTMLDivElement>(null);
  const heading = useRef<HTMLHeadingElement>(null);
  const onClosedRef = useRef(onClosed);
  onClosedRef.current = onClosed;

  // Every source the drawer shows is marked visited and recorded for the viewer, once per opening.
  useEffect(() => {
    if (id.startsWith(DOT) || isRiskList(id) || isStepList(id)) return;
    recordOpened(id, from?.runId ?? run?.runId ?? null);
    // The source is recorded when it changes, not when the answer does.
  }, [id]);

  // Focus moves to the heading when a marker or a number asked for it, or when a link opens the sheet. Beside
  // the page the panel is sticky and its heading already in view, so the window must not scroll: the page's
  // scroll padding for its own sticky header would otherwise move the note away from its source (DESIGN.md
  // section 10). The sheet is fixed, so scrolling it into view moves nothing.
  useEffect(() => {
    if (takeFocusRequest() || (narrow && !from)) heading.current?.focus({ preventScroll: !narrow });
  }, [requests, id]);

  // On open, the drawer scrolls only when the first highlight is out of view, and then puts it in the
  // middle of the space under the sticky header, so the claim stays beside its source when it can.
  useEffect(() => {
    const container = panel.current;
    const mark = container?.querySelector("mark");
    if (!container || !mark) return;
    // Measured from the top of the panel's view, since the sheet slides in as it opens. Beside the page,
    // the panel may start below the window's top and run past its bottom.
    const view = container.getBoundingClientRect();
    const top = container.querySelector<HTMLElement>("[data-drawer-header]")?.offsetHeight ?? 0;
    const bottom = narrow ? container.clientHeight : Math.min(container.clientHeight, window.innerHeight - view.top);
    const box = mark.getBoundingClientRect();
    const start = box.top - view.top;
    if (start >= top && box.bottom - view.top <= bottom) return;
    container.scrollTop += start - top - Math.max(0, (bottom - top - box.height) / 2);
  }, [id, data.status]);

  // Closed by any route, Back included: say whether focus was inside. A real close has taken
  // ?evidence= out of the address first; React's StrictMode unmounts and mounts the drawer once in
  // development with the address unchanged, and that is not a close.
  useLayoutEffect(() => {
    const element = panel.current;
    return () => {
      if (evidenceIn(window.location.search) !== null) return;
      // Focus on the page's body counts as inside: a Tab past the sheet's last link reaches the browser, and
      // closing from there would otherwise leave focus nowhere (ticket 15's design review, round 2, F7).
      const active = document.activeElement;
      const lost = active === null || active === document.body;
      onClosedRef.current(Boolean(element && (lost || element.contains(active))));
    };
  }, []);

  // A sheet holds the page still behind it.
  useEffect(() => {
    if (!narrow) return;
    const root = document.documentElement;
    const before = root.style.overflow;
    root.style.overflow = "hidden";
    return () => {
      root.style.overflow = before;
    };
  }, [narrow]);

  // Escape closes the drawer, after the box, its list and any evidence card have had theirs.
  useEffect(() => {
    const onKey = (event: globalThis.KeyboardEvent) => {
      if (event.key !== "Escape" || event.defaultPrevented) return;
      event.preventDefault();
      closeEvidence();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  return (
    <EvidenceDrawerView
      id={id}
      data={data}
      run={run}
      from={from}
      narrow={narrow}
      preview={preview}
      asOf={asOf}
      panelRef={panel}
      headingRef={heading}
      onClose={closeEvidence}
      onChoose={(next) =>
        from && openEvidence(next, { serial: from.serial, sentence: from.sentence, marker: from.marker, runId: from.runId }, { replace: true, focus: false })
      }
      // From a quantile dot's list to one of its packages and back, in place: the dot stays the drawer's
      // opener, so closing gives focus back to it.
      onOpenEntry={(entry) => {
        // A dot's list counts its packages; a step's list and the ran-longest list count their entries (ticket 27).
        const row = data.status === "ready" ? data.evidence.row : null;
        const count = !row
          ? 0
          : data.status === "ready" && data.evidence.kind === "steps"
            ? row.step.comparables.length
            : data.status === "ready" && data.evidence.kind === "steps-longest"
              ? row.longest.entries.length
              : Number(row.count);
        openEvidence(
          entry.evidence_id,
          { serial: null, sentence: null, marker: from?.marker ?? null, runId: null, fallback: from?.fallback, list: { id, count } },
          { replace: true },
        );
      }}
      onBack={(listId) =>
        openEvidence(
          listId,
          {
            serial: null,
            sentence: null,
            marker: from?.marker ?? null,
            runId: null,
            fallback: from?.fallback,
            entry: heldOnPage(listId) || listId.startsWith(REPORTS) ? id : id.slice(COMPARABLE.length),
          },
          { replace: true, focus: false },
        )
      }
      // From one of section 5's lists to a notice and back, in place, as from a quantile dot's list (ticket 31),
      // with the requirement's words highlighted in the notice.
      onOpenListEntry={(entry, list, highlight) =>
        openEvidence(
          entry,
          { serial: null, sentence: null, marker: from?.marker ?? null, runId: null, fallback: from?.fallback, list, highlight },
          { replace: true },
        )
      }
      // A risk's row: another of its sources, in place, keeping the row's pill or count as the opener.
      onChooseRow={(next) =>
        openEvidence(next, { serial: null, sentence: null, marker: from?.marker ?? null, runId: null, fallback: from?.fallback }, { replace: true, focus: false })
      }
      // From a risk's list of reports to one report's paragraph and back, as a dot's list does.
      onOpenReport={(evidenceId) => {
        const count = data.status === "ready" ? Number(data.evidence.row.entries?.length ?? 0) : 0;
        openEvidence(
          evidenceId,
          { serial: null, sentence: null, marker: from?.marker ?? null, runId: null, fallback: from?.fallback, list: { id, count } },
          { replace: true },
        );
      }}
    />
  );
}
