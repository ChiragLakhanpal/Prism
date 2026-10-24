// The evidence drawer (DESIGN.md section 5; the 14 brief, section 4.5): the whole numbered paragraph a
// citation points to, beside the page and never over it. It is a column clamp(400px, 40vw, 600px) wide
// whose panel stays in view while the page scrolls; the page narrows and stays usable, so it is a
// non-modal dialog. Below 768 px it is a full-screen sheet: modal, with the page behind it inert.
//
// From top to bottom: the stratum eyebrow, the source as its heading, a 44 px close; the sentence it
// was opened from and a switcher for that sentence's other sources; the paragraph with the matching
// words highlighted under its meta line; and a link to the page in the World Bank's PDF. A source the
// stream sent opens at once; one opened from a link is read from GET /api/evidence.
import { useEffect, useId, useLayoutEffect, useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import { ExternalLink, X } from "lucide-react";
import { copy } from "../copy";
import type { EvidenceEvent, Run } from "../lib/answer";
import { ApiError, getJson } from "../lib/api";
import { cx } from "../lib/cx";
import { closeEvidence, known, openEvidence, origin as originStore, recordOpened, takeFocusRequest, focusRequests } from "../lib/evidence";
import { highlightsFor, passageFields, recordReference } from "../lib/sources";
import { useStore } from "../lib/store";
import { Alert } from "./Alert";
import { Button } from "./Button";
import { highlighted } from "./Document";
import { eyebrow, SourceNumber, sourceTitle } from "./EvidenceCard";
import { LoadingLabel, Skeleton, SkeletonLine, SkeletonText } from "./Skeleton";
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
        <span key={index}>
          {index > 0 && words.join}
          {part}
        </span>
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

// The What stratum's view: the fields of the record a tool returned, under STEP's own names.
function RecordView({ evidence }: { evidence: EvidenceEvent }) {
  const row = evidence.row;
  const columns = copy.checkPlan.columns;
  const fields: [string, unknown][] = [
    [columns.method, [row.method, row.market_approach].filter(Boolean).join(copy.checkPlan.methodDot + " ")],
    [columns.review, row.review_type],
    [columns.estimated, row.estimated_amount_usd],
    [columns.status, row.process_status],
  ];
  return (
    <dl data-record className="grid grid-cols-2 gap-x-4 gap-y-2 rounded-md border border-line p-4" data-numbers>
      {row.description && (
        <div className="col-span-full">
          <dd className="text-small text-ink">{String(row.description)}</dd>
        </div>
      )}
      {fields
        .filter(([, value]) => value !== null && value !== undefined && value !== "")
        .map(([label, value]) => (
          <div key={label}>
            <dt className="text-caption text-ink-muted">{label}</dt>
            <dd className="text-small text-ink">{String(value)}</dd>
          </div>
        ))}
    </dl>
  );
}

// The sources of the sentence the drawer was opened from: one pill-shaped tab each. Left and Right move
// between them, Home and End jump to the ends, and selection follows focus.
function SourceSwitcher({ ids, current, run, onChoose }: { ids: string[]; current: string; run: Run; onChoose: (id: string) => void }) {
  const refs = useRef<(HTMLButtonElement | null)[]>([]);
  const index = ids.indexOf(current);
  const label = (id: string) => {
    const evidence = run.evidence[id];
    if (!evidence) return { shown: id, name: id };
    if (evidence.kind === "record") return { shown: recordReference(evidence), name: recordReference(evidence) };
    const fields = passageFields(evidence);
    const short = evidence.short_name ?? fields.docType;
    return { shown: copy.evidence.tab(short, fields.para), name: copy.evidence.tabName(short, fields.para) };
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
        const { shown, name } = label(id);
        return (
          <button
            key={id}
            ref={(element) => {
              refs.current[at] = element;
            }}
            type="button"
            role="tab"
            id={`evidence-tab-${at}`}
            aria-selected={selected}
            aria-controls="evidence-passage"
            aria-label={name}
            tabIndex={selected ? 0 : -1}
            onClick={() => onChoose(id)}
            onKeyDown={onKeyDown}
            className={cx(
              "inline-flex h-8 items-center rounded-pill border border-line-strong px-3 text-small text-ink transition-paint duration-150",
              selected ? "bg-tint shadow-[inset_0_0_0_1px_var(--color-primary)]" : "bg-surface hover:bg-tint-hover",
            )}
          >
            {shown}
          </button>
        );
      })}
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
  // Below 768 px the drawer is a modal sheet.
  narrow: boolean;
  // A preview of another view records nothing, and the drawer says so.
  preview: boolean;
  asOf: string | null;
  // Called as the drawer closes, with where focus should go back to, if anywhere.
  onClosed: (returnFocus: boolean) => void;
}) {
  const data = useEvidence(id, asOf);
  const from = useStore(originStore);
  const requests = useStore(focusRequests);
  const headingId = useId();
  const panel = useRef<HTMLDivElement>(null);
  const heading = useRef<HTMLHeadingElement>(null);
  const [scrolled, setScrolled] = useState(false);
  const onClosedRef = useRef(onClosed);
  onClosedRef.current = onClosed;

  // The sentence it was opened from, while that answer is still on the page.
  const claimFrom = from && from.id === id && from.sentence !== null && run ? run.sentences.find((sentence) => sentence.index === from.sentence) : undefined;
  const claim = claimFrom && run ? claimFrom : undefined;
  const numbering = new Map<string, number>();
  for (const sentence of run?.sentences ?? []) for (const evidenceId of sentence.evidence_ids) if (!numbering.has(evidenceId)) numbering.set(evidenceId, numbering.size + 1);

  // Every source the drawer shows is marked visited and recorded for the viewer, once per opening.
  useEffect(() => {
    recordOpened(id, from?.runId ?? run?.runId ?? null);
    // The source is recorded when it changes, not when the answer does.
  }, [id]);

  // Focus moves to the heading when a marker, a number or a link opened on a phone asked for it.
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

  // Closed by any route, Back included: say whether focus was inside, so it can go back to the marker.
  useLayoutEffect(() => {
    const element = panel.current;
    return () => onClosedRef.current(Boolean(element && document.activeElement && element.contains(document.activeElement)));
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

  const evidence = data.status === "ready" ? data.evidence : null;
  const switcherIds = claim && claim.evidence_ids.length > 1 ? claim.evidence_ids : null;

  return (
    <div
      role="dialog"
      id="evidence-drawer"
      aria-modal={narrow}
      aria-labelledby={headingId}
      data-evidence-drawer={narrow ? "sheet" : "drawer"}
      className={cx(
        "bg-surface",
        narrow ? "fixed inset-0 z-50 animate-sheet-in" : "w-[clamp(400px,40vw,600px)] shrink-0 self-stretch border-l border-line",
      )}
    >
      <div
        ref={panel}
        onScroll={(event) => setScrolled(event.currentTarget.scrollTop > 0)}
        className={cx("overflow-y-auto", narrow ? "h-dvh" : "sticky top-0 max-h-dvh")}
        style={narrow ? { paddingBottom: "env(safe-area-inset-bottom)" } : undefined}
      >
        <div className={cx("sticky top-0 z-10 flex items-start gap-4 bg-surface px-6 pt-6 pb-4", scrolled ? "border-b border-line" : "border-b border-transparent")}>
          <div className="min-w-0 flex-1">
            {evidence ? (
              <p className="text-label text-ink-muted uppercase">{eyebrow(evidence)}</p>
            ) : (
              <SkeletonLine className="text-label" width="w-1/3" />
            )}
            <h2 ref={heading} id={headingId} tabIndex={-1} className="mt-1 text-title wrap-anywhere text-ink-heading focus:outline-none">
              {evidence ? sourceTitle(evidence) : data.status === "loading" ? <LoadingLabel /> : copy.evidence.untitled}
              {data.status === "loading" && <SkeletonText widths={["w-4/5"]} />}
            </h2>
          </div>
          <Button variant="ghost" icon={X} iconOnly onClick={closeEvidence} className="-mt-2 -mr-2">
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
          {switcherIds && run && from && (
            <SourceSwitcher
              ids={switcherIds}
              current={id}
              run={run}
              onChoose={(next) => openEvidence(next, { sentence: from.sentence, marker: from.marker, runId: from.runId }, { replace: true, focus: false })}
            />
          )}
          <div id="evidence-passage" role={switcherIds ? "tabpanel" : undefined} className="flex flex-col gap-4">
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
