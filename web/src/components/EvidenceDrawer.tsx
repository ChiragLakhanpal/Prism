// The evidence drawer (DESIGN.md section 5; the 14 brief, section 4.5): the whole numbered paragraph a
// citation points to, beside the page and never over it. It is a column clamp(400px, 40vw, 600px) wide
// whose panel stays in view while the page scrolls; the page narrows and stays usable, so it is a
// non-modal dialog. Below 768 px it is a full-screen sheet: modal, with the page behind it inert.
//
// From top to bottom: the stratum eyebrow, the source as its heading, a 44 px close; the sentence it
// was opened from and a switcher for that sentence's other sources; the paragraph with the matching
// words highlighted under its meta line; and a link to the page in the World Bank's PDF. A source the
// stream sent opens at once; one opened from a link is read from GET /api/evidence.
import { Fragment, useEffect, useId, useLayoutEffect, useRef, useState, type KeyboardEvent, type ReactNode, type RefObject } from "react";
import { ExternalLink, X } from "lucide-react";
import { copy } from "../copy";
import { citationNumbers, type EvidenceEvent, type Run } from "../lib/answer";
import { ApiError, getJson } from "../lib/api";
import { cx } from "../lib/cx";
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
import { highlightsFor, passageFields, recordReference, recordSource } from "../lib/sources";
import { useStore } from "../lib/store";
import { Alert } from "./Alert";
import { Button } from "./Button";
import { highlighted } from "./Document";
import { eyebrow, SourceNumber, sourceTitle } from "./EvidenceCard";
import { Fill } from "./Fill";
import { Num } from "./Num";
import { MethodText } from "./PlanCheck";
import { LoadingLabel, Skeleton, SkeletonLine, SkeletonText } from "./Skeleton";
import { Source } from "./Source";
import { CARD_FIELD, CARD_FIELDS } from "./Table";
import { TextLink } from "./TextLink";

export type DrawerData =
  | { status: "loading" }
  | { status: "ready"; evidence: EvidenceEvent }
  | { status: "missing" }
  | { status: "failed"; onRetry: () => void };

// The source an evidence id names: from the stream if it sent it, or else from the server.
export function useEvidence(id: string, asOf: string | null): DrawerData {
  const all = useStore(known);
  const [fetched, setFetched] = useState<{ id: string; data: DrawerData } | null>(null);
  const [attempt, setAttempt] = useState(0);
  const held = all[id];
  useEffect(() => {
    if (held) return;
    const controller = new AbortController();
    setFetched({ id, data: { status: "loading" } });
    const query = `/api/evidence?id=${encodeURIComponent(id)}${asOf ? `&asof=${encodeURIComponent(asOf)}` : ""}`;
    getJson<EvidenceEvent>(query, { signal: controller.signal }).then(
      (evidence) => setFetched({ id, data: { status: "ready", evidence } }),
      (error: unknown) => {
        if (controller.signal.aborted) return;
        const missing = error instanceof ApiError && error.status === 404;
        setFetched({ id, data: missing ? { status: "missing" } : { status: "failed", onRetry: () => setAttempt((n) => n + 1) } });
      },
    );
    return () => controller.abort();
  }, [id, held, asOf, attempt]);
  if (held) return { status: "ready", evidence: held };
  return fetched?.id === id ? fetched.data : { status: "loading" };
}

// The meta line, with each part whole: after the document type and the project's name, which may
// wrap, a part ("October 10, 2019", "Section III.B", "PDF page 23 of 66") keeps to one line, and each
// dot stays with the part before it, so a line breaks only after a dot.
function MetaLine({ evidence }: { evidence: EvidenceEvent }) {
  const fields = passageFields(evidence);
  const words = copy.evidence.meta;
  const parts: ReactNode[] = [
    fields.docType,
    <>
      {words.project.split(/\{(\w+)\}/).map((part, index) =>
        index % 2 === 0 ? part : part === "pcode" ? <span key={index} className="font-mono">{fields.pcode}</span> : <span key={index}>{fields.project}</span>,
      )}
    </>,
    fields.date,
    fields.section ? words.section(fields.section) : null,
    fields.numbered ? words.para(fields.para) : null,
    fields.page ? (fields.pages ? words.page(String(fields.page), String(fields.pages)) : words.pageOnly(String(fields.page))) : null,
  ].filter((part) => part !== null && part !== "");
  return (
    <p data-meta-line className="rounded-t-md bg-surface-2 px-3 py-2 text-caption text-ink-muted">
      {parts.map((part, index) => (
        <Fragment key={index}>
          {index > 0 && " "}
          <span data-meta-part className={index >= 2 ? "whitespace-nowrap" : undefined}>
            {part}
            {index < parts.length - 1 && words.dot}
          </span>
        </Fragment>
      ))}
    </p>
  );
}

function PassageView({ evidence, sentence, fromAnswer }: { evidence: EvidenceEvent; sentence: number | null; fromAnswer: boolean }) {
  const fields = passageFields(evidence);
  const ranges = highlightsFor(evidence, sentence);
  const pdf = fields.pdfUrl && fields.page ? `${fields.pdfUrl}#page=${fields.page}` : null;
  return (
    <>
      <div className="rounded-md border border-line">
        <MetaLine evidence={evidence} />
        {fromAnswer && ranges.length === 0 && <p className="px-4 pt-3 text-caption text-ink-muted">{copy.evidence.noHighlight}</p>}
        <p data-passage lang={fields.lang ?? undefined} className="max-w-prose p-4 text-body text-ink">
          {highlighted(fields.text, ranges, true)}
        </p>
      </div>
      <p className="text-caption text-ink-muted">{copy.evidence.whole}</p>
      {pdf !== null && (
        <p className="text-small">
          <TextLink href={pdf} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1">
            {copy.document.openAtPage(String(fields.page))}
            <span className="sr-only">{copy.document.newTab}</span>
            <ExternalLink aria-hidden="true" className="size-4 shrink-0" />
          </TextLink>
        </p>
      )}
    </>
  );
}

// The What stratum's view: the fields of the record a tool returned, under STEP's own names, laid out
// as the plan check's activity card lays them out (the 14 brief, section 4.5.3): the Description and
// the Method across, Review and the amount side by side, the amount right-aligned in STEP's form with
// its cents (DESIGN.md section 6), then the source line.
function RecordView({ evidence }: { evidence: EvidenceEvent }) {
  const row = evidence.row;
  const columns = copy.checkPlan.columns;
  const given = (value: unknown) => value !== null && value !== undefined && value !== "";
  const fields: { label: string; value: ReactNode; wide?: boolean; numeric?: boolean }[] = [];
  if (given(row.description)) fields.push({ label: copy.evidence.recordDescription, value: String(row.description), wide: true });
  if (given(row.method)) fields.push({ label: columns.method, value: <MethodText method={String(row.method)} approach={row.market_approach} />, wide: true });
  if (given(row.review_type)) fields.push({ label: columns.review, value: String(row.review_type) });
  if (given(row.estimated_amount_usd)) {
    fields.push({ label: columns.estimated, value: <Num value={Number(row.estimated_amount_usd)} options={{ decimals: 2, compact: false }} />, numeric: true });
  }
  if (given(row.process_status)) fields.push({ label: columns.status, value: String(row.process_status), wide: true });
  return (
    <div className="flex flex-col gap-4 rounded-md border border-line p-4">
      <dl data-record data-numbers className={CARD_FIELDS}>
        {fields.map((field) => (
          <div key={field.label} className={cx(CARD_FIELD, field.wide && "col-span-full", field.numeric && "text-right")}>
            <dt className="text-caption text-ink-muted">{field.label}</dt>
            <dd className={cx("text-small wrap-break-word text-ink", field.numeric && "text-right tabular-nums")}>{field.value}</dd>
          </div>
        ))}
      </dl>
      <RecordSourceLine evidence={evidence} />
    </div>
  );
}

function RecordSourceLine({ evidence }: { evidence: EvidenceEvent }) {
  const source = recordSource(evidence);
  const words = copy.evidence;
  const date = source.date ? <Num date={source.date} /> : null;
  const pid = <span className="font-mono">{source.pcode}</span>;
  return (
    <Source>
      {source.agency && source.page && date ? (
        <Fill template={words.recordSource} slots={{ doc: source.docType, agency: source.agency, pid, date, page: String(source.page) }} />
      ) : (
        <Fill template={words.recordSourceShort} slots={{ doc: source.docType, pid, date: date ?? recordReference(evidence) }} />
      )}
    </Source>
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
    if (evidence.kind === "record") return recordReference(evidence);
    const fields = passageFields(evidence);
    // One inline span, so the space after the short name stays: a tab is a flex container, and flex
    // drops a text node that holds only a space.
    return (
      <span>
        {evidence.short_name ?? fields.docType}{" "}
        <span aria-hidden="true" data-para-mark>
          {copy.evidence.paraMark}
        </span>
        <span className="sr-only">{copy.evidence.paraSpoken}</span>
        {fields.para}
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
              "inline-flex h-8 items-center rounded-pill border border-line-strong px-3 text-small text-ink transition-paint duration-150",
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
  dialogId = "evidence-drawer",
  sample = false,
  panelRef,
  headingRef,
  onClose,
  onChoose,
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
  dialogId?: string;
  // A design gallery sample: as wide as its frame, and not held in view.
  sample?: boolean;
  panelRef?: RefObject<HTMLDivElement | null>;
  headingRef?: RefObject<HTMLHeadingElement | null>;
  onClose: () => void;
  // A switcher tab chose another source of the same sentence.
  onChoose: (id: string) => void;
}) {
  const headingId = useId();
  const passageId = useId();
  const [scrolled, setScrolled] = useState(false);

  // The sentence it was opened from, while that same answer is still on the page.
  const claim =
    from && run && from.id === id && from.serial === run.serial && from.sentence !== null
      ? run.sentences.find((sentence) => sentence.index === from.sentence && sentence.evidence_ids.includes(id))
      : undefined;
  const numbering = run ? citationNumbers(run) : new Map<string, number>();
  const evidence = data.status === "ready" ? data.evidence : null;
  const switcherIds = claim && claim.evidence_ids.length > 1 ? claim.evidence_ids : null;

  return (
    <div
      role="dialog"
      id={dialogId}
      aria-modal={narrow}
      aria-labelledby={headingId}
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
        <div className={cx("sticky top-0 z-10 flex items-start gap-4 border-b bg-surface px-6 pt-6 pb-4", scrolled ? "border-line" : "border-transparent")}>
          <div className="min-w-0 flex-1">
            {evidence && <p className="text-label text-ink-muted uppercase">{eyebrow(evidence)}</p>}
            {data.status === "loading" && <SkeletonLine className="text-label" width="w-1/3" />}
            <h2 ref={headingRef} id={headingId} tabIndex={-1} className="mt-1 text-title wrap-break-word text-ink-heading focus:outline-none">
              {evidence ? sourceTitle(evidence) : data.status === "loading" ? <LoadingLabel /> : copy.evidence.untitled}
              {data.status === "loading" && <SkeletonText widths={["w-4/5"]} />}
            </h2>
          </div>
          <Button variant="ghost" icon={X} iconOnly onClick={onClose} className="-mt-2 -mr-2">
            {copy.evidence.close}
          </Button>
        </div>
        <div className="flex animate-drawer-in flex-col gap-4 px-6 pt-2 pb-6">
          {claim && (
            <div data-claim>
              <p className="text-caption text-ink-muted">{copy.evidence.fromAnswer}</p>
              <p className="mt-1 border-l-2 border-line-strong pl-3 text-small text-ink">
                {claim.text}
                {numbering.get(id) && (
                  <span className="ml-1 inline-flex align-[1px]">
                    <SourceNumber n={numbering.get(id)!} />
                  </span>
                )}
              </p>
            </div>
          )}
          {switcherIds && run && (
            <SourceSwitcher ids={switcherIds} current={id} run={run} panelId={passageId} onChoose={onChoose} />
          )}
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
            {data.status === "missing" && <Alert state="neutral">{copy.document.missing}</Alert>}
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
                {copy.document.failed}
              </Alert>
            )}
            {evidence?.kind === "passage" && <PassageView evidence={evidence} sentence={claim ? claim.index : null} fromAnswer={Boolean(claim)} />}
            {evidence?.kind === "record" && <RecordView evidence={evidence} />}
          </div>
          {preview && <p className="text-caption text-ink-muted">{copy.evidence.preview}</p>}
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
    recordOpened(id, from?.runId ?? run?.runId ?? null);
    // The source is recorded when it changes, not when the answer does.
  }, [id]);

  // Focus moves to the heading when a marker or a number asked for it, or when a link opens the sheet.
  useEffect(() => {
    if (takeFocusRequest() || (narrow && !from)) heading.current?.focus();
  }, [requests, id]);

  // The first highlight sits in the middle of the view.
  useEffect(() => {
    const container = panel.current;
    const mark = container?.querySelector("mark");
    if (!container || !mark) return;
    const offset = mark.getBoundingClientRect().top - container.getBoundingClientRect().top + container.scrollTop;
    container.scrollTop = Math.max(0, offset - container.clientHeight / 2);
  }, [id, data.status]);

  // Closed by any route, Back included: say whether focus was inside. A real close has taken
  // ?evidence= out of the address first; React's StrictMode unmounts and mounts the drawer once in
  // development with the address unchanged, and that is not a close.
  useLayoutEffect(() => {
    const element = panel.current;
    return () => {
      if (evidenceIn(window.location.search) !== null) return;
      onClosedRef.current(Boolean(element && document.activeElement && element.contains(document.activeElement)));
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
      panelRef={panel}
      headingRef={heading}
      onClose={closeEvidence}
      onChoose={(next) =>
        from && openEvidence(next, { serial: from.serial, sentence: from.sentence, marker: from.marker, runId: from.runId }, { replace: true, focus: false })
      }
    />
  );
}
