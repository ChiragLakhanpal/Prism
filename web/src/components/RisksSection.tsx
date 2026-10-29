// Section 3 of the package workspace, "Procurement risks and what helped" (ticket 30; the 30 brief). Since ticket 101
// it is zone 3, tagged "PPSD section 3": a panel when it has risks, and a row while it holds only its first-person
// sentence and one link. Its notes, coverage line and source line end the panel in its foot strip.
//
// At most five risks, each counted in the completion reports of projects with comparable packages, each with a
// current lesson on what helped and the reports that say so. The risk-table builder
// (src/strata/packages/risks.py) counts, ranks and checks the rows; the page draws them in the builder's order,
// never sorting, and states only the counts it returned.
//
// - Layout: a table when the card's content box is 640 px or wider, and a list below that, through a container
//   query on the card (the 30 brief, section 3.4), so 1200 px, 768 px, 1024 px with the drawer open and phones
//   get the list. "What helped" is the section's one emphasis, in body type; every other cell is small.
// - Selecting: a checkbox per row, nothing selected for you and no "select all". A toggle shows at once and saves
//   at once (PUT .../risk-selection). A package from a STEP row saves per viewer and STEP reference, and a failed
//   save shows its line with "Try again" under the selection status; a package from a sentence saves with the
//   package, and the page's saved stamp says so (onSaveState). A selected risk no longer in the table stays
//   stored, is not counted, and one line names it. Ticket 36 drafts only the selected risks on screen.
// - Every count is a Num with its tooltip, and opens its reports in the evidence drawer: a row's count the
//   reports that raised its risk, the finding's {m} every report counted. A source pill opens the drawer at its
//   paragraph, and the row whose evidence is open takes the tint fill.
// - The rows passed the verifier's checks like any answer, so the section ends on its own check line and removed
//   box, then the notes, the coverage line and the source line.
// - A rerun after a criterion change replaces the table in place under 400 ms, and over 400 ms shows the
//   skeleton at the section's height until the result arrives (the 15 brief).
import { useEffect, useId, useLayoutEffect, useRef, useState, type ReactNode, type Ref } from "react";
import { CircleX } from "lucide-react";
import { copy } from "../copy";
import { ApiError, getJson, putJson } from "../lib/api";
import { cx } from "../lib/cx";
import { formatCount, formatNumber } from "../lib/format";
import { evidenceIn, openEvidence, origin, visited as visitedStore } from "../lib/evidence";
import { address } from "../lib/router";
import { dataReadinessHref } from "../routes";
import {
  allReportsId,
  forgetRisks,
  pillsOf,
  rememberRisks,
  reportsId,
  risksPath,
  selectionPath,
  type RemovedRow,
  type RiskRow,
  type RiskSource,
  type RisksResult,
} from "../lib/risks";
import { useStore } from "../lib/store";
import { useFocusWithin } from "../lib/useFocusWithin";
import { Alert } from "./Alert";
import { Button } from "./Button";
import { Checkbox } from "./Checkbox";
import { CheckLine, notCheckedFor, RemovedBox, type Removed } from "./Checks";
import { Fill, Joined } from "./Fill";
import { FootStrip } from "./FootStrip";
import { Num } from "./Num";
import { FromLine, reportsFrom } from "./NumFrom";
import { Skeleton, SkeletonLine, SkeletonText } from "./Skeleton";
import { Source } from "./Source";
import { SourcePill } from "./SourcePill";
import { TaskZone, ZoneBlock } from "./TaskZone";
import { TextLink } from "./TextLink";

const words = copy.packageRisks;
const SKELETON_AFTER_MS = 400;

export type RisksState =
  | { status: "loading" }
  | { status: "ready"; result: RisksResult }
  | { status: "error"; error: ApiError | null; onRetry: () => void };

// Which of the page's evidence is open in the drawer: its id, and the list it was opened from.
type Opened = { id: string | null; list: string | null; visited: ReadonlySet<string> };

type Handlers = {
  onPill: (source: RiskSource, element: HTMLElement) => void;
  onCount: (row: RiskRow, element: HTMLElement) => void;
  onAll: (element: HTMLElement) => void;
};

// ── The pure view, which the design gallery draws as it is ──────────────

export type RisksViewProps = {
  state: RisksState;
  packageKey: string;
  // A package from a STEP row or from a sentence: which empty-state sentence and which save failure apply.
  kind: "step" | "planned";
  selected: string[];
  onToggle: (key: string, checked: boolean) => void;
  preview?: boolean;
  // A STEP-row package's last save failed.
  saveFailed?: boolean;
  onRetrySave?: () => void;
  // A rerun has taken longer than 400 ms.
  updating?: boolean;
  // A package from a sentence that lacks a criterion: "the category and the country".
  missingList?: string;
  opened?: Opened;
  handlers?: Handlers;
  headingRef?: Ref<HTMLHeadingElement>;
  announce?: string;
  // Ticket 36: "Suggest {n} PPSD risk rows" below 768 px, under the last risk and before the check line.
  action?: ReactNode;
};

const noop = () => undefined;
const NO_HANDLERS: Handlers = { onPill: noop, onCount: noop, onAll: noop };
const CLOSED: Opened = { id: null, list: null, visited: new Set() };

export function RisksView({
  state,
  packageKey,
  kind,
  selected,
  onToggle,
  preview = false,
  saveFailed = false,
  onRetrySave,
  updating = false,
  missingList,
  opened = CLOSED,
  handlers = NO_HANDLERS,
  headingRef,
  announce = "",
  action,
}: RisksViewProps) {
  const result = state.status === "ready" ? state.result : null;
  const populated = Boolean(result && result.rows.length > 0 && !result.empty_reason);
  const [readyPart, lastHeight] = useLastHeight(Boolean(result) && !updating, result);
  // Zone 3 (ticket 101): a row while it holds only its sentence (no completion report, no lesson, no comparable
  // package, or a criterion still missing), and a panel when it has risks, or a removed box when every row was
  // removed, since a zone that holds a removed sentence is never closed.
  const sentence = result && !updating && result.empty_reason && SENTENCE_ONLY.has(result.empty_reason) ? result : null;
  const live = (
    <p role="status" className="sr-only" data-risks-live>
      {announce}
    </p>
  );
  const zone = {
    id: "risks",
    number: words.number,
    name: words.heading,
    tag: words.ppsdTag,
    headingRef,
    busy: state.status === "loading" || updating,
    sectionKey: "risks",
    className: "scroll-mt-24",
    marks: { "data-risks": state.status === "ready" ? (result!.empty_reason ?? "rows") : state.status },
    live,
  };
  if (state.status === "loading" && !updating) return <TaskZone {...zone} state="loading" />;
  if (state.status === "error") return <TaskZone {...zone} state="error" error={<RisksError state={state} />} />;
  if (sentence) return <TaskZone {...zone} state="empty" summary={<Empty result={sentence} kind={kind} missingList={missingList} />} />;
  // A rerun over 400 ms keeps the instruction, holds the ready part's last height with the skeleton, and keeps the foot
  // strip's place with its last lines unseen, so nothing under the zone moves (ticket 59; the 30 design review, F6).
  return (
    <TaskZone {...zone} panel>
      <ZoneBlock
        data-block="risks"
        foot={
          populated && result ? (
            <FootStrip>
              <div className={cx(updating && "invisible")} aria-hidden={updating || undefined}>
                <Notes result={result} />
              </div>
            </FootStrip>
          ) : undefined
        }
      >
        <div className="@container/risks">
          <p className="max-w-prose text-body text-ink">{words.intro}</p>
          {populated && <p className="mt-2 max-w-prose text-body text-ink">{words.instruction}</p>}
          {updating && (
            <div className={cx(lastHeight !== null && "overflow-hidden")} style={{ height: lastHeight ?? undefined }} data-risks-updating>
              <RisksSkeleton />
            </div>
          )}
          {result && !updating && (
            <div ref={readyPart} className="flow-root">
            <Ready
              result={result}
              packageKey={packageKey}
              kind={kind}
              selected={selected}
              onToggle={onToggle}
              preview={preview}
              saveFailed={saveFailed}
              onRetrySave={onRetrySave}
              missingList={missingList}
              opened={opened}
              handlers={handlers}
              action={action}
            />
            </div>
          )}
        </div>
      </ZoneBlock>
    </TaskZone>
  );
}

// The ready part's height, kept while it shows, so a rerun's skeleton can hold it (ticket 59).
function useLastHeight(shown: boolean, key: unknown) {
  const ref = useRef<HTMLDivElement>(null);
  const [height, setHeight] = useState<number | null>(null);
  useLayoutEffect(() => {
    const element = ref.current;
    if (!shown || !element) return;
    const keep = () => setHeight(element.getBoundingClientRect().height);
    keep();
    const watch = new ResizeObserver(keep);
    watch.observe(element);
    return () => watch.disconnect();
  }, [shown, key]);
  return [ref, height] as const;
}

// The empty states that are one sentence and at most one link, so the zone is a row.
const SENTENCE_ONLY = new Set(["missing_criteria", "no_comparables", "no_reports", "no_lessons"]);

// ── Populated ────────────────────────────────────────────────────────────

function Ready({
  result,
  packageKey,
  kind,
  selected,
  onToggle,
  preview,
  saveFailed,
  onRetrySave,
  missingList,
  opened,
  handlers,
  action,
}: {
  result: RisksResult;
  packageKey: string;
  kind: "step" | "planned";
  selected: string[];
  onToggle: (key: string, checked: boolean) => void;
  preview: boolean;
  saveFailed: boolean;
  onRetrySave?: () => void;
  missingList?: string;
  opened: Opened;
  handlers: Handlers;
  action?: ReactNode;
}) {
  const findingId = useId();
  const countId = useId();
  if (result.empty_reason || result.rows.length === 0) {
    return <Empty result={result} kind={kind} missingList={missingList} />;
  }
  const rows = result.rows;
  const m = result.m ?? 0;
  const chosen = rows.filter((row) => selected.includes(row.risk_key)).length;
  const dropped = result.selected_not_shown.filter((entry) => selected.includes(entry.risk_key));
  const from = risksFrom(result);
  return (
    <>
      <h3 id={findingId} data-finding className="mt-6 max-w-prose text-h2 text-balance text-ink-heading">
        <Finding result={result} onAll={handlers.onAll} onCount={handlers.onCount} from={from} />
      </h3>
      <div className="mt-2 flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1 text-small">
        <p id={countId} className="text-ink-muted" data-count-line>
          {rows.length === 1 ? words.countOne : words.count(formatCount(rows.length))}
        </p>
        <p className="text-ink" data-selection-status>
          {chosen === 0 ? words.selectedNone : words.selected(formatNumber(chosen, { compact: false }), formatNumber(rows.length, { compact: false }))}
          {preview && <span className="ml-2 text-caption text-ink-muted">{words.preview}</span>}
        </p>
      </div>
      {saveFailed && (
        // The icon keeps to the first line, and the sentence and "Try again" wrap beside it as one block, so the icon is
        // never left alone on a line (ticket 59). The button keeps its 44 px target over the 20 px line.
        <p className="mt-2 flex items-start gap-2 text-small text-error" data-save-failed>
          <CircleX aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-error-icon" />
          <span className="flex min-w-0 flex-wrap items-center gap-x-2">
            <span>{words.saveFailed}</span>
            <Button variant="ghost" flush onClick={onRetrySave} className="-my-3">
              {words.tryAgain}
            </Button>
          </span>
        </p>
      )}
      {dropped.length > 0 && (
        <p className="mt-2 max-w-prose text-caption text-ink-muted" data-dropped>
          {dropped.length === 1
            ? words.dropped(dropped[0].risk_label)
            : words.droppedMany(formatCount(dropped.length), dropped.map((entry) => words.quoted(entry.risk_label)).join(copy.list.comma))}
        </p>
      )}
      <RiskTable
        rows={rows}
        m={m}
        findingId={findingId}
        countId={countId}
        selected={selected}
        onToggle={onToggle}
        preview={preview}
        opened={opened}
        handlers={handlers}
        packageKey={packageKey}
        from={from}
      />
      <RiskList rows={rows} m={m} findingId={findingId} selected={selected} onToggle={onToggle} preview={preview} opened={opened} handlers={handlers} packageKey={packageKey} from={from} />
      <Checks result={result} />
      {/* "Suggest {n} PPSD risk rows", the page's one primary action for staff, in the flow after the risks it drafts
          from and their check line, which touches what it checks, so the zone ends on its action (ticket 101; DESIGN.md
          section 5, Task zone: an action other than Show or Hide follows its sentence). */}
      {action && <div className="mt-4">{action}</div>}
    </>
  );
}

// The records date the section's counts run to: the page's as-of date when it is the earlier, as the source line says.
function recordsDate(result: RisksResult): string | null {
  return result.as_of && result.data_through && result.as_of < result.data_through ? result.as_of : result.data_through;
}

// Where every count in the section came from: the completion reports I read, through the records date (ticket 96).
function risksFrom(result: RisksResult): ReactNode {
  const words = reportsFrom(recordsDate(result));
  return words ? <FromLine words={words} /> : undefined;
}

// The finding names the most common risk among the rows shown, as the builder picked it.
function Finding({
  result,
  onAll,
  onCount,
  from,
}: {
  result: RisksResult;
  onAll: (element: HTMLElement) => void;
  onCount: (row: RiskRow, element: HTMLElement) => void;
  from: ReactNode;
}) {
  const most = result.most_common!;
  const m = result.m ?? 0;
  const tips = words.numTips;
  const tied = most.risk_keys.map((key) => result.rows.find((row) => row.risk_key === key)).filter((row): row is RiskRow => Boolean(row));
  const one = tied.length === 1 ? tied[0] : null;
  const kText = formatNumber(most.k_max, { compact: false });
  const k = (
    <Num
      value={most.k_max}
      options={{ compact: false }}
      check={
        one
          ? { tooltip: tips.k, from, act: tips.kAct(kText), opens: "record", onOpen: (element) => onCount(one, element) }
          : { tooltip: tips.tie(kText), from }
      }
    />
  );
  const mText = formatNumber(m, { compact: false });
  const all = <Num value={m} options={{ compact: false }} check={{ tooltip: tips.m, from, act: tips.mAct(mText), opens: "record", onOpen: onAll }} />;
  if (one) return <Fill template={words.finding} slots={{ risk: one.risk_label, k, m: all }} />;
  if (tied.length === 2) return <Fill template={words.findingTwo} slots={{ a: tied[0].risk_label, b: tied[1].risk_label, k, m: all }} />;
  return <Fill template={words.findingMany} slots={{ tied: formatCount(tied.length, { capital: true }), k, m: all }} />;
}

// A row's "{k} of {m}" with " completion reports" in caption: stacked and right-aligned in the table's cell, on one
// line where it fits in the list. One Num with one check for both (ticket 30's review, F10).
function RiskCount({ row, m, onCount, from, stacked }: { row: RiskRow; m: number; onCount: (row: RiskRow, element: HTMLElement) => void; from: ReactNode; stacked: boolean }) {
  const k = formatNumber(row.k, { compact: false });
  return (
    <span data-count={row.risk_key} className={stacked ? "inline-flex flex-col items-end text-right" : undefined}>
      <span className={cx("font-semibold text-ink tabular-nums", stacked && "text-small")}>
        <Num
          part={row.k}
          whole={m}
          show="count"
          check={{ tooltip: words.numTips.k, from, act: words.numTips.kAct(k), opens: "record", name: words.countName(k, formatNumber(m, { compact: false }), row.risk_label), onOpen: (element) => onCount(row, element) }}
        />
      </span>
      {!stacked && " "}
      <span className="text-caption text-ink-muted">{words.reports}</span>
    </span>
  );
}

// The table's columns and header, which the skeleton draws too, so the table takes its place without a shift: Select
// 48 px, then Risk, How often, What helped and Sources share the rest.
function RiskColumns() {
  const c = words.columns;
  return (
    <>
      <colgroup>
        <col className="w-12" />
        <col className="w-[21%]" />
        <col className="w-[18%]" />
        <col className="w-[28%]" />
        <col />
      </colgroup>
      <thead className="bg-surface-2 text-left align-bottom">
        <tr>
          <th scope="col" className="p-3">
            <span className="sr-only">{c.select}</span>
          </th>
          <th scope="col" className="p-3 font-semibold text-ink-heading">
            {c.risk}
          </th>
          <th scope="col" className="p-3 text-right font-semibold text-ink-heading">
            {c.often}
            <span className="block text-caption font-normal text-ink-muted">{c.oftenNote}</span>
          </th>
          <th scope="col" className="p-3 font-semibold text-ink-heading">
            {c.helped}
            <span className="block text-caption font-normal text-ink-muted">{c.helpedNote}</span>
          </th>
          <th scope="col" className="p-3 font-semibold text-ink-heading">
            {c.sources}
            <span className="block text-caption font-normal text-ink-muted">{c.sourcesNote}</span>
          </th>
        </tr>
      </thead>
    </>
  );
}

function Pills({ row, opened, onPill }: { row: RiskRow; opened: Opened; onPill: (source: RiskSource, element: HTMLElement) => void }) {
  return (
    <ul aria-label={words.pillsLabel} className="flex flex-col items-start gap-2 @max-[49rem]/risks:flex-row @max-[49rem]/risks:flex-wrap">
      {pillsOf(row.sources).map(({ source, withProject }) => (
        <li key={source.evidence_id} className="max-w-full">
          <SourcePill
            source={source}
            withProject={withProject}
            active={opened.id === source.evidence_id && rowIsOpen(row, opened)}
            opened={opened.visited.has(source.evidence_id)}
            onOpen={(element) => onPill(source, element)}
          />
        </li>
      ))}
    </ul>
  );
}

function rowIsOpen(row: RiskRow, opened: Opened): boolean {
  if (!opened.id) return false;
  return row.sources.some((source) => source.evidence_id === opened.id) || opened.id.endsWith(`:${row.risk_key}`) || Boolean(opened.list?.endsWith(`:${row.risk_key}`));
}

type TableProps = {
  rows: RiskRow[];
  m: number;
  findingId: string;
  countId?: string;
  selected: string[];
  onToggle: (key: string, checked: boolean) => void;
  preview: boolean;
  opened: Opened;
  handlers: Handlers;
  packageKey: string;
  // Where the counts came from (ticket 96).
  from: ReactNode;
};

// At 49rem of card content and wider, as a Table with cardsBelow="fit" (ticket 101). table-layout: fixed, so nothing
// shifts when values change or a row is selected: Select 48 px, then Risk, How often, What helped and Sources share
// the rest.
function RiskTable({ rows, m, findingId, countId, selected, onToggle, preview, opened, handlers, from }: TableProps) {
  return (
    <div data-risk-view="table" className="mt-3 hidden rounded-md border border-line @min-[49rem]/risks:block">
      <table aria-labelledby={findingId} aria-describedby={countId} className="w-full table-fixed border-collapse text-small">
        <RiskColumns />
        <tbody>
          {rows.map((row) => (
            <tr key={row.risk_key} data-risk-row={row.risk_key} data-open={rowIsOpen(row, opened) || undefined} className={cx("border-t border-line align-top", rowIsOpen(row, opened) && "bg-tint")}>
              <td className="p-0 text-center">
                <Checkbox checked={selected.includes(row.risk_key)} onChange={(checked) => onToggle(row.risk_key, checked)} name={words.checkbox(row.risk_label)} readOnly={preview} className="m-1" />
              </td>
              <th scope="row" className="p-3 text-left font-semibold text-ink-heading">
                {row.risk_label}
              </th>
              <td className="p-3 text-right">
                <RiskCount row={row} m={m} onCount={handlers.onCount} from={from} stacked />
              </td>
              <td className="p-3">
                <p className="max-w-[65ch] text-body text-ink" data-helped>
                  {row.lesson.text}
                </p>
              </td>
              <td className="p-3">
                <Pills row={row} opened={opened} onPill={handlers.onPill} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// Below 49rem of card content: an ordered list, each risk's name the checkbox's label.
function RiskList({ rows, m, findingId, selected, onToggle, preview, opened, handlers, from }: TableProps) {
  return (
    <ol aria-labelledby={findingId} data-risk-view="list" className="mt-3 border-t border-line @min-[49rem]/risks:hidden">
      {rows.map((row) => (
        <li key={row.risk_key} data-risk-row={row.risk_key} data-open={rowIsOpen(row, opened) || undefined} className={cx("border-b border-line py-4", rowIsOpen(row, opened) && "-mx-2 rounded-md bg-tint px-2")}>
          <Checkbox checked={selected.includes(row.risk_key)} onChange={(checked) => onToggle(row.risk_key, checked)} name={words.checkbox(row.risk_label)} readOnly={preview}>
            {/* A block, so a two-line name is set at small's own leading (ticket 59). */}
            <span className="block text-small font-semibold text-ink-heading">{row.risk_label}</span>
          </Checkbox>
          <div className="mt-1 flex flex-col gap-2 pl-8">
            <p className="text-small">
              <RiskCount row={row} m={m} onCount={handlers.onCount} from={from} stacked={false} />
            </p>
            <div>
              <p className="text-caption text-ink-muted">{words.helpedLabel}</p>
              <p className="text-body text-ink" data-helped>
                {row.lesson.text}
              </p>
            </div>
            <Pills row={row} opened={opened} onPill={handlers.onPill} />
          </div>
        </li>
      ))}
    </ol>
  );
}

// ── The checks and the notes ─────────────────────────────────────────────

function removedOf(rows: RemovedRow[], m: number): Removed[] {
  return rows.map((row) => {
    const reason = words.removed.reasons[row.reason_code] ?? copy.removed.reasons[row.reason_code as keyof typeof copy.removed.reasons] ?? copy.removed.unknownReason;
    const said =
      row.claim_kind === "count"
        ? words.removed.saidCount(row.risk_label, formatNumber(row.k, { compact: false }), formatNumber(m, { compact: false }))
        : words.removed.saidHelped(row.risk_label, row.lesson_text.replace(/[.\s]+$/, ""));
    return { sentence: said, reason: reason.item, reasonJoined: reason.joined };
  });
}

function Checks({ result }: { result: RisksResult }) {
  const checks = result.verifier;
  if (!checks) return null;
  const counts = checks.counts;
  return (
    // The check line and the removed box in one block (ticket 105).
    <div className="mt-4" data-risk-checks>
      <CheckLine
        numbers={counts.numbers}
        dates={counts.dates}
        quotes={counts.quotes}
        quoteWords={words.quotesInRecords}
        notChecked={notCheckedFor({ checks_run: counts.checks_run, tools: checks.tools })}
        removed={<RemovedBox removed={removedOf(checks.removed, result.m ?? 0)} lead={words.removed} item={words.removed.item} />}
      />
    </div>
  );
}

// The zone's Note, its abbreviations, its coverage line and its source line, in its foot strip (ticket 101).
function Notes({ result }: { result: RisksResult }) {
  const ppar = result.rows.some((row) => row.sources.some((source) => source.doc_short === "PPAR"));
  const from = risksFrom(result);
  return (
    <div className="flex flex-col gap-2" data-risk-notes>
      <p className="max-w-prose text-caption text-ink-muted">
        <span className="font-semibold">{words.noteLabel}</span> {words.note(formatCount(result.max_rows))}
      </p>
      <p className="max-w-prose text-caption text-ink-muted">
        {words.abbr}
        {ppar && <> {words.abbrPpar}</>}
      </p>
      <Coverage result={result} from={from} />
      <SourceLine result={result} />
    </div>
  );
}

// The projects whose reports I read and all the projects each say what they count (ticket 96); the counts of those I
// could not read from are plain text, because the sentence already says what each counts.
function Coverage({ result, from }: { result: RisksResult; from: ReactNode }) {
  const c = words.coverage;
  const p = <Num value={result.p ?? 0} options={{ compact: false }} check={{ tooltip: words.numTips.coverageP, from }} inCaption />;
  const missing = result.coverage.missing;
  const link = <TextLink href={dataReadinessHref(result.coverage.sources, "package_risks")}>{c.link}</TextLink>;
  if (missing.length === 0) {
    return (
      <p className="max-w-prose text-caption text-ink-muted" data-coverage-line>
        {result.p === 1 ? c.allOne : <Fill template={c.all} slots={{ p }} />} {link}
      </p>
    );
  }
  const reasons = missing.map((gap) => {
    const forms = c.reasons[gap.reason_code];
    const template = forms ? (gap.count === 1 ? forms.one : forms.many) : "";
    return <Fill key={gap.reason_code} template={template} slots={{ n: <Num value={gap.count} options={{ compact: false }} /> }} />;
  });
  return (
    <p className="max-w-prose text-caption text-ink-muted" data-coverage-line>
      <Fill template={c.some} slots={{ m: <Num value={result.m ?? 0} options={{ compact: false }} check={{ tooltip: words.numTips.coverageM, from }} inCaption />, p }} />
      {c.join}
      {reasons.map((reason, index) => (
        <span key={index}>
          {index > 0 && c.and}
          {reason}
        </span>
      ))}
      {c.end} {link}
    </p>
  );
}

function SourceLine({ result }: { result: RisksResult }) {
  const date = recordsDate(result);
  const asOf = Boolean(result.as_of && result.data_through && result.as_of < result.data_through);
  const names = <Joined items={result.source_names} />;
  return (
    <Source>
      <Fill template={asOf ? words.sourceLineAsOf : words.sourceLine} slots={{ names, date: date ? <Num date={date} /> : "" }} />
    </Source>
  );
}

// ── Empty, loading and error ─────────────────────────────────────────────

// The first-person sentence and its one link: all a row holds (ticket 101), or the start of the panel whose rows were
// all removed.
function EmptyCard({ title, children }: { title: ReactNode; children?: ReactNode }) {
  return (
    <div data-no-risks>
      <p className="max-w-prose text-body text-ink" data-no-risks-title>
        {title}
      </p>
      {children}
    </div>
  );
}

function Empty({ result, kind, missingList }: { result: RisksResult; kind: "step" | "planned"; missingList?: string }) {
  const e = words.empty;
  const readiness = dataReadinessHref(result.coverage.sources, "package_risks");
  switch (result.empty_reason) {
    case "missing_criteria":
      return <EmptyCard title={<Fill template={e.missing} slots={{ list: missingList ?? "" }} />} />;
    case "no_comparables":
      return (
        <EmptyCard title={e.noComparables}>
          <p className="mt-2 max-w-prose text-body text-ink">{kind === "planned" ? e.noComparablesPlanned : e.noComparablesStep}</p>
          {kind === "step" && (
            <p className="mt-2">
              <TextLink href={readiness}>{e.noComparablesLink}</TextLink>
            </p>
          )}
        </EmptyCard>
      );
    case "no_reports":
      return (
        <EmptyCard title={result.p === 1 ? e.noReportsOne : <Fill template={e.noReports} slots={{ p: <Num count={result.p ?? 0} /> }} />}>
          <p className="mt-2 max-w-prose text-body text-ink">{e.noReportsBody}</p>
          <p className="mt-2">
            <TextLink href={readiness}>{e.noReportsLink}</TextLink>
          </p>
        </EmptyCard>
      );
    case "no_lessons":
      return (
        <EmptyCard title={result.m === 1 ? e.noLessonsOne : <Fill template={e.noLessons} slots={{ m: <Num value={result.m ?? 0} options={{ compact: false }} /> }} />}>
          <p className="mt-2 max-w-prose text-body text-ink">{e.noLessonsBody}</p>
        </EmptyCard>
      );
    default: {
      const written = result.written ?? result.verifier?.removed.length ?? 0;
      return (
        <>
          <EmptyCard title={e.allRemoved}>
            <p className="mt-2 max-w-prose text-body text-ink">{written === 1 ? e.allRemovedBodyOne : e.allRemovedBody(formatCount(written))}</p>
          </EmptyCard>
          {result.verifier && (
            <div className="mt-4">
              <RemovedBox removed={removedOf(result.verifier.removed, result.m ?? 0)} all lead={words.removed} item={words.removed.item} />
            </div>
          )}
        </>
      );
    }
  }
}

// Static surface-2 blocks where the finding, the count line and three rows will be: the real header and 88 px
// rows in table form, 168 px items in list form.
export function RisksSkeleton() {
  return (
    <div aria-hidden="true" data-risks-skeleton>
      <SkeletonText className="mt-6 max-w-prose text-h2" widths={["w-[90%]", "w-1/2"]} />
      <SkeletonLine className="mt-2 text-caption" width="w-2/5" />
      <div className="mt-3 hidden rounded-md border border-line @min-[49rem]/risks:block">
        <table className="w-full table-fixed border-collapse text-small">
          <RiskColumns />
          <tbody>
            {[0, 1, 2].map((n) => (
              <tr key={n} className="h-22 border-t border-line align-top">
                <td className="p-3">
                  <Skeleton className="mx-auto size-5" />
                </td>
                <td className="p-3">
                  <SkeletonText widths={["w-4/5", "w-1/2"]} />
                </td>
                <td className="p-3">
                  <SkeletonLine className="justify-end" width="w-3/5" />
                </td>
                <td className="p-3 text-body">
                  <SkeletonText widths={["w-full", "w-[90%]", "w-3/5"]} />
                </td>
                <td className="flex flex-col gap-2 p-3">
                  <Skeleton className="h-5 w-30" radius="rounded-pill" />
                  <Skeleton className="h-5 w-24" radius="rounded-pill" />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <ol className="mt-3 border-t border-line @min-[49rem]/risks:hidden">
        {[0, 1, 2].map((n) => (
          <li key={n} className="flex h-42 gap-3 border-b border-line py-4">
            <Skeleton className="size-5 shrink-0" />
            <div className="flex min-w-0 flex-1 flex-col gap-2">
              <SkeletonLine width="w-3/5" />
              <SkeletonLine width="w-2/5" />
              <SkeletonText className="text-body" widths={["w-full", "w-4/5"]} />
              <div className="flex gap-2">
                <Skeleton className="h-5 w-30" radius="rounded-pill" />
                <Skeleton className="h-5 w-24" radius="rounded-pill" />
              </div>
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}

function RisksError({ state }: { state: Extract<RisksState, { status: "error" }> }) {
  const code = state.error?.body.trace_id;
  return (
    <div className="flex flex-col gap-4" data-risks-error>
      <Alert state="error">{words.error}</Alert>
      <div>
        <Button variant="secondary" onClick={state.onRetry}>
          {words.tryAgain}
        </Button>
      </div>
      {code && (
        <p className="text-caption text-ink-muted">
          {/* The code breaks anywhere, so at 320 px it never crosses the card's edge (ticket 59). */}
          <Fill template={words.errorCode} slots={{ code: <span className="font-mono wrap-anywhere">{code}</span> }} />
        </p>
      )}
    </div>
  );
}

// ── The section on a page: it reads, reruns, selects and opens ──────────

export function RisksSection({
  apiHref: base,
  packageKey,
  kind,
  rerunKey = "",
  preview = false,
  missingList,
  onSaveState,
  onSelection,
  action,
}: {
  // The package's API address, such as /api/packages/KE-NWWDA-541055-CW-RFB or /api/planned-packages/pkg-....
  apiHref: string;
  // The package's key in the drawer's list ids: its STEP reference or its id.
  packageKey: string;
  kind: "step" | "planned";
  // Changes when section 1's criteria change, so the builder reruns.
  rerunKey?: string;
  preview?: boolean;
  missingList?: string;
  // A package from a sentence: the page's saved stamp shows each save, and "Try again" after a failed one.
  onSaveState?: (state: "saving" | "saved" | "failed", retry: () => void) => void;
  // Ticket 36: what the section shows now, for the workspace's "Suggest {n} PPSD risk rows": how many risks, how many
  // of them you selected, and whether the last save failed; null while it loads, fails or has no rows.
  onSelection?: (selection: { rows: number; chosen: number; saveFailed: boolean } | null) => void;
  // The action itself, which the section draws under its last risk below 768 px.
  action?: ReactNode;
}) {
  const here = useStore(address);
  const from = useStore(origin);
  const seen = useStore(visitedStore);
  const params = new URLSearchParams(here.search);
  const asOf = params.get("asof");
  const view = params.get("view");
  // A preview of another view reads the table and changes nothing.
  const previewing = preview || (view !== null && view !== "staff");
  const [state, setState] = useState<RisksState>({ status: "loading" });
  const [updating, setUpdating] = useState(false);
  const [selected, setSelected] = useState<string[]>([]);
  const [saveFailed, setSaveFailed] = useState(false);
  const [announce, setAnnounce] = useState("");
  const [attempt, setAttempt] = useState(0);
  const pending = useRef<Record<string, boolean>>({});
  const heading = useRef<HTMLHeadingElement>(null);
  const last = useRef<RisksResult | null>(null);
  // The zone is the section its heading names (ticket 101), with no element of the page's around it, so the zones
  // keep their spacing; whether focus is inside it is tracked from the document.
  const root = () => heading.current?.closest<HTMLElement>("section") ?? null;
  const focusInside = useFocusWithin(root);

  useEffect(() => {
    const controller = new AbortController();
    const rerun = last.current !== null;
    if (!rerun) setAnnounce(words.loading);
    const timer = rerun ? setTimeout(() => setUpdating(true), SKELETON_AFTER_MS) : undefined;
    const query = new URLSearchParams();
    if (asOf) query.set("asof", asOf);
    if (view && view !== "staff") query.set("view", view);
    const path = `${risksPath(base)}${query.size ? `?${query.toString()}` : ""}`;
    getJson<RisksResult>(path, { signal: controller.signal })
      .then(
        (result) => {
          const before = last.current;
          const stored = [...result.selected_keys, ...result.selected_not_shown.map((entry) => entry.risk_key)];
          const mine = new Set(stored);
          for (const [key, on] of Object.entries(pending.current)) {
            if (on) mine.add(key);
            else mine.delete(key);
          }
          const next = [...mine];
          // A risk selected before that this run dropped from the table is named once.
          if (before) {
            const shownBefore = new Set(before.rows.map((row) => row.risk_key));
            const gone = result.selected_not_shown.filter((entry) => shownBefore.has(entry.risk_key) && mine.has(entry.risk_key));
            if (gone.length === 1) setAnnounce(words.dropped(gone[0].risk_label));
            else if (gone.length > 1) setAnnounce(words.droppedMany(formatCount(gone.length), gone.map((entry) => words.quoted(entry.risk_label)).join(copy.list.comma)));
          }
          last.current = result;
          setSelected(next);
          setState({ status: "ready", result });
        },
        (error: unknown) => {
          if (controller.signal.aborted) return;
          setState({ status: "error", error: error instanceof ApiError ? error : null, onRetry: () => setAttempt((n) => n + 1) });
          setAnnounce(words.error);
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
  }, [base, rerunKey, asOf, view, attempt]);

  // Hold the rows and lists for the drawer while the section shows them.
  useEffect(() => {
    if (state.status === "ready") rememberRisks(packageKey, state.result);
  }, [state, packageKey]);

  // The selection on screen, for the PPSD action (ticket 36): only the selected risks the table still shows count.
  const result = state.status === "ready" && !updating ? state.result : null;
  const shownRows = result && !result.empty_reason ? result.rows : [];
  const chosen = shownRows.filter((row) => selected.includes(row.risk_key)).length;
  useEffect(() => {
    onSelection?.(shownRows.length > 0 ? { rows: shownRows.length, chosen, saveFailed } : null);
  }, [shownRows.length, chosen, saveFailed]);
  useEffect(() => () => forgetRisks(), []);

  // If a rerun removed the element that had focus, focus moves to the section's heading.
  useLayoutEffect(() => {
    const zone = root();
    if (focusInside.current && zone && !zone.contains(document.activeElement)) heading.current?.focus();
  }, [state]);

  const save = () => {
    const changes = { ...pending.current };
    if (Object.keys(changes).length === 0) return;
    onSaveState?.("saving", save);
    putJson<{ selected: string[] }>(selectionPath(base), { changes }).then(
      () => {
        for (const [key, on] of Object.entries(changes)) if (pending.current[key] === on) delete pending.current[key];
        setSaveFailed(false);
        onSaveState?.("saved", save);
      },
      () => {
        if (kind === "step") setSaveFailed(true);
        setAnnounce(kind === "step" ? words.saveFailedSpoken : copy.packageWorkspace.saveFailed);
        onSaveState?.("failed", save);
      },
    );
  };

  const toggle = (key: string, checked: boolean) => {
    if (previewing) return;
    setSelected((now) => (checked ? [...now.filter((one) => one !== key), key] : now.filter((one) => one !== key)));
    pending.current[key] = checked;
    save();
  };

  const id = evidenceIn(here.search);
  const opened: Opened = { id, list: from?.id === id && from?.list ? from.list.id : null, visited: seen };
  const fallback = () => heading.current;
  const handlers: Handlers = {
    onPill: (source, element) => openEvidence(source.evidence_id, { serial: null, sentence: null, marker: element, runId: null, fallback: fallback() }),
    onCount: (row, element) => openEvidence(reportsId(packageKey, row.risk_key), { serial: null, sentence: null, marker: element, runId: null, fallback: fallback() }),
    onAll: (element) => openEvidence(allReportsId(packageKey), { serial: null, sentence: null, marker: element, runId: null, fallback: fallback() }),
  };

  return (
    <RisksView
      state={state}
      packageKey={packageKey}
      kind={kind}
      selected={selected}
      onToggle={toggle}
      preview={previewing}
      saveFailed={saveFailed}
      onRetrySave={save}
      updating={updating}
      missingList={missingList}
      opened={opened}
      handlers={handlers}
      headingRef={heading}
      announce={announce}
      action={action}
    />
  );
}
