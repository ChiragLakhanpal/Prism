// Section 1's "Advertised again" block (ticket 28; the 28 brief): at the end of section 1's card, after a 1px
// divider, it says how many of the comparable packages were advertised again and why, labeled experimental.
//
// - The heading row is the h3 "Advertised again" and the Experimental badge, then one sentence that says why it is
//   experimental, before the count, so you read the reason before the number. The block is no landmark: it is
//   named by its h3 inside section 1's region.
// - The count sentence is rebidding_risk's {n} of {m}; a different denominator gets its own caption. My model's
//   natural frequency shows only when the tool says so (model.shown), with its track record under it; otherwise
//   one first-person sentence says why I'm not giving an estimate. The page checks neither condition itself.
// - "Show the {n} packages and their reasons" opens the Reasons list (DESIGN.md section 5) from data already on the
//   page: one group per reason code in the tool's order, rows newest first, five a group. Each row is the STEP
//   reference (opens the package's records), the reason word for word or the evidence sentence with one citation
//   marker per record, and a caption naming each record. Markers are numbered once per page (lib/markers.ts) and
//   open the evidence drawer with no hover card, since the row is its own preview.
// - With none advertised again, the next step is a link to Data readiness for the notices.
// - It is hidden when section 1 has no comparable packages, cannot measure the package, or failed to load, and
//   when the server has no such route (404). A failed load shows an error Alert, "Try again" and the code.
// - A rerun after a criterion change replaces the block in place under 400 ms, and over 400 ms shows the skeleton
//   until the result arrives. The list keeps its open or closed state.
import { useEffect, useId, useLayoutEffect, useRef, useState, type ReactNode, type Ref } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import { copy } from "../copy";
import { ApiError, getJson } from "../lib/api";
import { cx } from "../lib/cx";
import { evidenceHref, evidenceIn, openEvidence, visited as visitedStore } from "../lib/evidence";
import { formatCount, formatDate } from "../lib/format";
import { SECTION_1, usePageNumbers } from "../lib/markers";
import { COMPARABLE } from "../lib/packages";
import { citedIds, pageCases, type RebidCase, type RebidEvidence, type RebiddingResult, type RebidModel } from "../lib/rebidding";
import { address } from "../lib/router";
import { useStore } from "../lib/store";
import { dataReadinessHref } from "../routes";
import type { ComparablesResult } from "../lib/api";
import { useFocusWithin } from "../lib/useFocusWithin";
import { useLastHeight } from "../lib/useLastHeight";
import { Alert } from "./Alert";
import { Button } from "./Button";
import { CitationMarker } from "./CitationMarker";
import { Fill, Joined } from "./Fill";
import { FootStrip } from "./FootStrip";
import { Num } from "./Num";
import { FromLine, modelFrom, recordsFrom, settingsFrom, testsFrom } from "./NumFrom";
import { ReasonGroup } from "./ReasonsList";
import { Skeleton, SkeletonLine } from "./Skeleton";
import { Source } from "./Source";
import { StatusBadge } from "./StatusBadge";
import { TextLink } from "./TextLink";

const words = copy.rebid;
const SKELETON_AFTER_MS = 400;

export type RebidState =
  | { status: "loading" }
  | { status: "ready"; result: RebiddingResult }
  | { status: "error"; requestId: string | null; onRetry: () => void };

export type RebidHandlers = {
  onMarker: (item: RebidEvidence, element: HTMLElement) => void;
  onPackage: (stepReference: string, element: HTMLElement) => void;
};

const noop = () => undefined;
const NO_HANDLERS: RebidHandlers = { onMarker: noop, onPackage: noop };

// Whether section 1 shows comparable packages the block can count: not when it has none, cannot measure the
// package, or did not load.
export function countsComparables(section: ComparablesResult | null): boolean {
  if (section === null) return false;
  const reason = section.abstention?.reason;
  return section.rows.length > 0 && reason !== "no_public_notice" && reason !== "none_measurable" && reason !== "no_comparables" && reason !== "unknown_package";
}

function Mono({ text }: { text: string }) {
  return <span className="font-mono wrap-anywhere">{text}</span>;
}

// ── The pure view, which the design gallery draws as it is ──────────────

export type RebiddingViewProps = {
  state: RebidState;
  numbers: Map<string, number>;
  // The page's as-of date, when it has one: the source line then says the records were read as of it.
  asOf?: string | null;
  // A "Compare with" toggle is on (ticket 26): the count stays this package's own, and a caption says so.
  comparing?: boolean;
  // A rerun has taken longer than 400 ms.
  updating?: boolean;
  openId?: string | null;
  visited?: ReadonlySet<string>;
  handlers?: RebidHandlers;
  headingRef?: Ref<HTMLHeadingElement>;
  // The gallery draws the list open.
  initiallyOpen?: boolean;
};

export function RebiddingView({
  state,
  numbers,
  asOf = null,
  comparing = false,
  updating = false,
  openId = null,
  visited = new Set(),
  handlers = NO_HANDLERS,
  headingRef,
  initiallyOpen = false,
}: RebiddingViewProps) {
  const headingId = useId();
  const result = state.status === "ready" ? state.result : null;
  const loading = state.status === "loading";
  // The list's open state lives here, above the ready block, so a rerun that shows the skeleton for a while keeps it
  // (ticket 59; the 28 review, follow-up 1).
  const [open, setOpen] = useState(initiallyOpen);
  // The ready block's last height: a rerun's skeleton holds it, so the sections under the block stay put (ticket 59).
  const [readyBlock, lastHeight] = useLastHeight(Boolean(result) && !updating, result);
  // Zone 1's second block (ticket 101): its body, then its source line in its own foot strip.
  return (
    <>
    <div
      aria-labelledby={headingId}
      aria-busy={loading || updating || undefined}
      data-rebidding={state.status === "ready" ? (result!.n > 0 ? "found" : "none") : state.status}
      data-zone-body
      data-block="again"
    >
      <div>
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
        <h3 ref={headingRef} id={headingId} tabIndex={-1} className="text-h2 text-ink-heading focus:outline-none">
          {words.heading}
        </h3>
        <StatusBadge kind="experimental" />
      </div>
      {state.status !== "error" && (
        <p className="mt-2 max-w-prose text-caption text-ink-muted" data-rebid-why>
          {words.why}
        </p>
      )}
      {loading && <RebidSkeleton />}
      {updating && (
        <div className={cx(lastHeight !== null && "overflow-hidden")} style={{ height: lastHeight ?? undefined }} data-rebid-updating>
          <RebidSkeleton />
        </div>
      )}
      {state.status === "error" && <RebidError state={state} />}
      {/* A failed load is said once, politely; the Alert itself is no alert, so it is not heard twice. */}
      <p role="status" className="sr-only">
        {state.status === "error" ? words.error : ""}
      </p>
      {result && !updating && (
        <div ref={readyBlock} className="flow-root">
          <Ready
            result={result}
            numbers={numbers}
            asOf={asOf}
            comparing={comparing}
            openId={openId}
            visited={visited}
            handlers={handlers}
            open={open}
            setOpen={setOpen}
          />
        </div>
      )}
      </div>
    </div>
    {/* While the block loads, the foot strip holds the source line's lines: three in the card from a 26rem page area,
        a fourth below it and a fifth below 22.5rem, as the fixture's source line takes (ticket 59; the critique of round
        1, measured at 320 to 1440 px). */}
    {loading && (
      <FootStrip>
        <div aria-hidden="true" data-rebid-source-skeleton>
          <SkeletonLine className="text-caption" width="w-full" />
          <SkeletonLine className="text-caption" width="w-full" />
          <SkeletonLine className="hidden text-caption @max-[26rem]/page:flex" width="w-full" />
          <SkeletonLine className="hidden text-caption @max-[22.5rem]/page:flex" width="w-full" />
          <SkeletonLine className="text-caption" width="w-2/5" />
        </div>
      </FootStrip>
    )}
    {/* While a rerun shows the skeleton, the foot strip keeps its place with the last source line unseen. */}
    {result && (
      <FootStrip>
        <div className={cx(updating && "invisible")} aria-hidden={updating || undefined}>
          <RebidSource result={result} asOf={asOf} />
        </div>
      </FootStrip>
    )}
    </>
  );
}

function RebidSource({ result, asOf }: { result: RebiddingResult; asOf: string | null }) {
  return (
    <Source>
      {asOf ? (
        <Fill template={words.sourceAsOf} slots={{ sources: <Joined items={result.sources.map((source) => source.dataset_name)} />, asOf: <Num date={asOf} /> }} />
      ) : (
        <Fill
          template={words.source}
          slots={{ sources: <Joined items={result.sources.map((source) => source.dataset_name)} />, through: result.records_through ? <Num date={result.records_through} /> : "" }}
        />
      )}
    </Source>
  );
}

function Ready({ result, numbers, asOf, comparing, openId, visited, handlers, open, setOpen }: {
  result: RebiddingResult; numbers: Map<string, number>; asOf: string | null; comparing: boolean; openId: string | null;
  visited: ReadonlySet<string>; handlers: RebidHandlers; open: boolean; setOpen: (open: boolean | ((now: boolean) => boolean)) => void;
}) {
  const listId = useId();
  const [focusFirst, setFocusFirst] = useState(false);
  const { n, m } = result;
  // Selecting {n} or {m} opens the list and moves focus to its first group's heading, where the count can be
  // checked (the 28 brief, section 6.2).
  useLayoutEffect(() => {
    if (!focusFirst || !open) return;
    document.getElementById(`${listId}-group-0`)?.focus();
    setFocusFirst(false);
  }, [focusFirst, open, listId]);
  const toRows = () => {
    setOpen(true);
    setFocusFirst(true);
  };
  const different = result.denominator_reason !== null;
  // Each count comes from every record set the tool read (a package canceled in the Procurement Plan comes from the
  // plan's rows, in Documents & Reports) and, when any was advertised again, opens the list below (ticket 96).
  const records = recordsFrom(result.sources, result.records_through, result.sources.map((source) => source.key));
  // A count standing alone is one to nine in words; "{n} of the {m}" keeps its numerals (DESIGN.md section 7, rule 12).
  const count = (value: number, tooltip: string, act: string, alone = false) => {
    const base = { tooltip, from: records ? <FromLine words={records} /> : undefined };
    const check = n > 0 ? { ...base, act, opens: "rows" as const, onOpen: toRows } : base;
    return alone ? <Num count={value} check={check} /> : <Num value={value} options={{ compact: false }} check={check} />;
  };
  const nNum = count(n, words.tips.n, words.tips.nAct);
  const mNum = count(m, different ? words.tips.mOther : words.tips.m, words.tips.mAct);
  const mAlone = count(m, different ? words.tips.mOther : words.tips.m, words.tips.mAct, true);
  const sentence =
    n === 0 ? (
      <Fill template={words.countNone} slots={{ m: mAlone }} />
    ) : n === m ? (
      <Fill template={words.countAll} slots={{ m: mAlone }} />
    ) : n === 1 ? (
      <Fill template={words.countOne} slots={{ m: mAlone }} />
    ) : (
      <Fill template={words.count} slots={{ n: nNum, m: mNum }} />
    );
  const byRef = new Map(result.rows.map((row) => [row.step_reference, row]));
  return (
    <>
      <p className="mt-3 max-w-prose text-body text-pretty text-ink" data-rebid-count>
        {sentence}
      </p>
      {different && (
        <p className="mt-1 max-w-prose text-caption text-ink-muted" data-rebid-denominator>
          <Fill
            template={words.denominator}
            slots={{
              m: <Num value={m} options={{ compact: false }} />,
              total: <Num value={result.past_range_total} options={{ compact: false }} />,
              reason: words.denominatorReasons[result.denominator_reason!] ?? result.denominator_reason!,
            }}
          />
        </p>
      )}
      {comparing && <p className="mt-1 max-w-prose text-caption text-ink-muted" data-rebid-compare>{words.compareNote}</p>}
      <ModelLines model={result.model} />
      {n > 0 ? (
        <div className="mt-4">
          <Button
            variant="ghost"
            flush
            icon={open ? ChevronUp : ChevronDown}
            aria-expanded={open}
            aria-controls={listId}
            onClick={() => setOpen((now) => !now)}
            data-rebid-disclosure
          >
            {open ? (n === 1 ? words.listHideOne : words.listHide) : n === 1 ? words.listShowOne : <Fill template={words.listShow} slots={{ n: formatCount(n) }} />}
          </Button>
        </div>
      ) : (
        <div className="mt-4" data-rebid-next>
          <p className="max-w-prose text-small text-ink">{words.noneNext}</p>
          <p className="mt-1">
            <TextLink href={dataReadinessHref(result.notice_source_keys, "rebidding_risk")} className="text-small">
              {words.noneLink}
            </TextLink>
          </p>
        </div>
      )}
      <div id={listId} hidden={!open} className="mt-4 flex max-w-prose animate-open-in flex-col gap-6" data-rebid-list>
        {result.groups.map((group, index) => (
          <div key={group.reason_code} className="@container/reasons" data-rebid-group={group.reason_code}>
            <ReasonGroup
              headingId={`${listId}-group-${index}`}
              label={words.reasons[group.reason_code] ?? words.reasons.other}
              count={<Fill template={words.groupCount} slots={{ c: String(group.count), n: String(n) }} />}
              name={words.groupName(words.reasons[group.reason_code] ?? words.reasons.other, String(group.count), String(n))}
              perGroup={result.rows_per_group}
              rows={group.step_references
                .map((ref) => byRef.get(ref))
                .filter((row): row is RebidCase => Boolean(row))
                .map((row) => (
                  <CaseRow key={row.step_reference} row={row} through={result.records_through} numbers={numbers} openId={openId} visited={visited} handlers={handlers} />
                ))}
              moreLabel={(more) => (more === 1 ? words.moreOne : <Fill template={words.more} slots={{ count: formatCount(more) }} />)}
            />
          </div>
        ))}
      </div>
    </>
  );
}

function ModelLines({ model }: { model: RebidModel }) {
  const track = model.track_record;
  const baseline = track ? (words.baselines[track.baseline_code] ?? words.baselines.comparables_rate) : words.baselines.comparables_rate;
  if (model.shown && track) {
    const scored = model.score_date ? <FromLine words={modelFrom(model.score_date)} /> : undefined;
    const k = <Num value={model.in10!} options={{ compact: false }} check={{ tooltip: words.tips.k, from: scored }} />;
    const tip = { tooltip: words.tips.track, from: <FromLine words={testsFrom(track.run_date)} /> };
    return (
      <>
        <p className="mt-2 max-w-prose text-body text-pretty text-ink" data-rebid-model>
          {model.band === "below_1" ? words.modelBelow1 : model.band === "above_9" ? words.modelAbove9 : <Fill template={words.model} slots={{ k }} />}
        </p>
        <p className="mt-2 max-w-prose text-caption text-ink-muted" data-rebid-track>
          <Fill
            template={words.track}
            slots={{
              n: <Num value={track.n_test} options={{ compact: false }} check={tip} inCaption />,
              year: <Num year={track.test_year} />,
              baseline,
            }}
          />
        </p>
      </>
    );
  }
  const reason = model.not_shown_reason ?? "no_results";
  const tip = track ? { tooltip: words.tips.track, from: <FromLine words={testsFrom(track.run_date)} /> } : null;
  // The smallest count the model gives an estimate from is one of my settings, as the scored run used it.
  const setting = model.score_date ? <FromLine words={settingsFrom(model.score_date)} /> : undefined;
  return (
    <p className="mt-2 max-w-prose text-body text-pretty text-ink" data-rebid-model-off={reason}>
      <Fill
        template={words.off[reason] ?? words.off.no_results}
        slots={{
          min: <Num value={model.min_comparables} options={{ compact: false }} check={{ tooltip: words.tips.min, from: setting }} />,
          n: track && tip ? <Num value={track.n_test} options={{ compact: false }} check={tip} /> : "",
          year: track ? <Num year={track.test_year} /> : "",
          baseline,
        }}
      />
    </p>
  );
}

function markerLabel(item: RebidEvidence): string {
  const label = words.markers[item.record_kind] ?? words.markers.notice;
  return label(item.reference, formatDate(item.date));
}

// A row's second line: the reason word for word, or the sentence that says what the records show. The drawer's claim
// repeats it.
export function caseLine(row: RebidCase, through: string | null): ReactNode {
  if (row.row_kind === "quote" && row.quote) return words.quoted(row.quote.text);
  if (row.row_kind === "again") {
    return <Fill template={copy.trail.notice.again} slots={{ date: row.dates.again_on ? <Num date={row.dates.again_on} /> : "" }} />;
  }
  if (row.row_kind === "canceled_row") {
    return <Fill template={words.canceledRow} slots={{ plan: row.dates.plan_date ? <Num date={row.dates.plan_date} /> : "", status: row.process_status ?? "" }} />;
  }
  return (
    <Fill
      template={words.noAward}
      slots={{ notice: row.dates.notice_date ? <Num date={row.dates.notice_date} /> : "", through: through ? <Num date={through} /> : "" }}
    />
  );
}

// One tab name per record a row cites, as its marker names it, without the date: "Notice OP00083890".
export function recordTab(item: RebidEvidence): string {
  return (words.tabs[item.record_kind] ?? words.tabs.notice)(item.reference);
}

function CaseRow({ row, through, numbers, openId, visited, handlers }: {
  row: RebidCase; through: string | null; numbers: Map<string, number>; openId: string | null; visited: ReadonlySet<string>;
  handlers: RebidHandlers;
}) {
  const active = row.evidence.some((item) => item.evidence_id === openId);
  const lang = row.quote && row.quote.lang !== "en" ? row.quote.lang : undefined;
  const line = caseLine(row, through);
  const quotedKind = row.evidence[0]?.record_kind === "award_notice" ? "award_notice" : "notice";
  return (
    <li className={cx("flex flex-col gap-1", active && "-mx-2 rounded-xs bg-tint px-2")} data-rebid-row={row.step_reference} data-open={active || undefined}>
      <p className="text-small">
        <button
          type="button"
          aria-label={words.openRecords(row.step_reference)}
          onClick={(event) => handlers.onPackage(row.step_reference, event.currentTarget)}
          className="relative -my-1 py-1 text-left font-mono text-small text-primary underline hover:text-link-hover"
          data-step-ref
        >
          <Mono text={row.step_reference} />
        </button>
        {row.country_name && <span className="text-ink-muted">{copy.list.comma}{row.country_name}</span>}
      </p>
      <p className="text-small text-ink" lang={lang} data-rebid-line={row.row_kind}>
        {line}
        {row.evidence.map((item) => (
          <CitationMarker
            key={item.evidence_id}
            n={numbers.get(item.evidence_id) ?? 0}
            source={markerLabel(item)}
            href={evidenceHref(item.evidence_id)}
            opened={visited.has(item.evidence_id)}
            active={item.evidence_id === openId}
            drawerId="evidence-drawer"
            evidenceId={item.evidence_id}
            onOpen={(marker) => handlers.onMarker(item, marker)}
          />
        ))}
      </p>
      <p className="text-caption text-ink-muted" data-rebid-sources>
        {row.evidence.map((item, index) => (
          <span key={item.evidence_id}>
            {index > 0 && " "}
            <Fill
              template={words.sources[item.record_kind] ?? words.sources.notice}
              slots={{
                id: <Mono text={item.reference} />,
                agency: item.agency ?? "",
                date: <span className="whitespace-nowrap"><Num date={item.date} style="table" /></span>,
              }}
            />
          </span>
        ))}
      </p>
      {lang && copy.language.name[lang] && <p className="text-caption text-ink-muted">{words.inLanguage[quotedKind](copy.language.name[lang])}</p>}
    </li>
  );
}

function RebidSkeleton() {
  return (
    <div aria-hidden="true" className="mt-3 flex flex-col gap-2" data-rebid-skeleton>
      <SkeletonLine className="text-body" width="w-[70%]" />
      <SkeletonLine className="text-body" width="w-[90%]" />
      {/* The sentences take a line more below a page area of 34rem, and another below 22.5rem (ticket 59, measured on
          the fixture's demo package at 320 to 1440 px). */}
      <SkeletonLine className="hidden text-body @max-[34rem]/page:flex" width="w-4/5" />
      <SkeletonLine className="hidden text-body @max-[22.5rem]/page:flex" width="w-3/5" />
      <SkeletonLine className="text-caption" width="w-4/5" />
      <Skeleton className="mt-2 h-11 w-60" radius="rounded-sm" />
      <SkeletonLine className="mt-2 text-caption" width="w-1/2" />
    </div>
  );
}

function RebidError({ state }: { state: Extract<RebidState, { status: "error" }> }) {
  return (
    <div className="mt-4 flex flex-col gap-4" data-rebid-error>
      <Alert state="error">{words.error}</Alert>
      <div>
        <Button variant="secondary" onClick={state.onRetry}>
          {words.tryAgain}
        </Button>
      </div>
      {state.requestId && (
        <p className="text-caption text-ink-muted">
          <Fill template={words.errorCode} slots={{ code: <Mono text={state.requestId} /> }} />
        </p>
      )}
    </div>
  );
}

// ── The block on a page: it reads, reruns and opens ──────────────────────

export function Rebidding({ path, section, sectionFailed = false, sectionLoading = false, comparing = false }: {
  // GET .../rebidding with section 1's criteria, or null while the package has none.
  path: string | null;
  // Section 1's result, when it has loaded: the block counts the same comparable packages.
  section: ComparablesResult | null;
  // Section 1 is loading its first result: the block holds its own skeleton under the past range's, so the card ends
  // where it will and the sections under it stay put (ticket 59; the critique of round 1). A page whose first result
  // may be a prompt in place of the range, such as a planned package, leaves it unset.
  sectionLoading?: boolean;
  // Section 1's own request failed: the block comes from its own tool, so it still shows under the error (ticket 101).
  sectionFailed?: boolean;
  comparing?: boolean;
}) {
  const here = useStore(address);
  const seen = useStore(visitedStore);
  const params = new URLSearchParams(here.search);
  const asOf = params.get("asof");
  const view = params.get("view");
  const shown = (sectionFailed || countsComparables(section)) && path !== null;
  const [state, setState] = useState<RebidState>({ status: "loading" });
  const [hidden, setHidden] = useState(false);
  const [updating, setUpdating] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const heading = useRef<HTMLHeadingElement>(null);
  const last = useRef<RebiddingResult | null>(null);
  const retried = useRef(false);
  // The block is zone 1's second block, with no element of its own around it (ticket 101): its body is the one its
  // heading sits in, and focus is tracked from the document.
  const body = () => heading.current?.closest<HTMLElement>("[data-block=again]") ?? null;
  const focusInside = useFocusWithin(body);

  useEffect(() => {
    if (!shown) return;
    const controller = new AbortController();
    const rerun = last.current !== null;
    const timer = rerun ? setTimeout(() => setUpdating(true), SKELETON_AFTER_MS) : undefined;
    const query = new URLSearchParams();
    if (asOf) query.set("asof", asOf);
    if (view && view !== "staff") query.set("view", view);
    const join = path!.includes("?") ? "&" : "?";
    getJson<RebiddingResult>(`${path}${query.size ? `${join}${query.toString()}` : ""}`, { signal: controller.signal })
      .then(
        (result) => {
          last.current = result;
          setHidden(false);
          setState({ status: "ready", result });
          if (retried.current) heading.current?.focus();
          retried.current = false;
        },
        (error: unknown) => {
          if (controller.signal.aborted) return;
          // No such route on this server, or no such package: there is nothing to count, so the block stays away.
          if (error instanceof ApiError && error.status === 404) {
            setHidden(true);
            return;
          }
          retried.current = false;
          setState({
            status: "error",
            requestId: error instanceof ApiError ? (error.body.trace_id ?? null) : null,
            onRetry: () => {
              retried.current = true;
              setAttempt((count) => count + 1);
            },
          });
        },
      )
      .finally(() => {
        clearTimeout(timer);
        if (!controller.signal.aborted) setUpdating(false);
      });
    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [shown, path, asOf, view, attempt]);

  // Hold the cases for the drawer while the block shows them.
  const result = state.status === "ready" && shown && !hidden ? state.result : null;
  useEffect(() => {
    pageCases.set({ rows: result ? result.rows : [], through: result?.records_through ?? null });
  }, [result]);
  useEffect(() => () => pageCases.set({ rows: [], through: null }), []);
  const numbers = usePageNumbers(SECTION_1, result ? citedIds(result) : []);

  // If a rerun removed the element that had focus, focus moves to the block's heading.
  useLayoutEffect(() => {
    const block = body();
    if (focusInside.current && block && !block.contains(document.activeElement)) heading.current?.focus();
  }, [state]);

  if (!shown && sectionLoading && path !== null) return <RebiddingView state={{ status: "loading" }} numbers={numbers} headingRef={heading} />;
  if (!shown || hidden) return null;
  const fallback = () => heading.current;
  const handlers: RebidHandlers = {
    onMarker: (item, element) => openEvidence(item.evidence_id, { serial: null, sentence: null, marker: element, runId: null, fallback: fallback() }),
    onPackage: (stepReference, element) =>
      openEvidence(`${COMPARABLE}${stepReference}`, { serial: null, sentence: null, marker: element, runId: null, fallback: fallback() }),
  };
  return (
    <RebiddingView
      state={state}
      numbers={numbers}
      asOf={asOf}
      comparing={comparing}
      updating={updating}
      openId={evidenceIn(here.search)}
      visited={seen}
      handlers={handlers}
      headingRef={heading}
    />
  );
}
