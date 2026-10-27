// Section 3 of the package workspace, "Procurement risks and what helped" (ticket 30; the 30 brief). It is
// open by default, the same Card as section 1, with the eyebrow "Planning · PPSD section 3".
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
import { CircleDashed, CircleX } from "lucide-react";
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
import { Alert } from "./Alert";
import { Button } from "./Button";
import { Checkbox } from "./Checkbox";
import { CheckLine, notCheckedFor, RemovedBox, type Removed } from "./Checks";
import { Fill, Joined } from "./Fill";
import { Num } from "./Num";
import { Skeleton, SkeletonLine, SkeletonText } from "./Skeleton";
import { Source } from "./Source";
import { SourcePill } from "./SourcePill";
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
  const headingId = useId();
  const result = state.status === "ready" ? state.result : null;
  const populated = Boolean(result && result.rows.length > 0 && !result.empty_reason);
  return (
    <section
      id="risks"
      aria-labelledby={headingId}
      aria-busy={state.status === "loading" || updating || undefined}
      data-risks={state.status === "ready" ? (result!.empty_reason ?? "rows") : state.status}
      className="rounded-md border border-line bg-surface p-4 @md/page:p-6"
    >
      <div className="@container/risks">
        <p className="text-label text-ink-muted">{words.eyebrow}</p>
        <h2 ref={headingRef} id={headingId} tabIndex={-1} className="mt-2 text-h2 text-ink-heading focus:outline-none">
          <span aria-hidden="true">{words.number} </span>
          {words.heading}
        </h2>
        <p className="mt-2 max-w-prose text-body text-ink">{words.intro}</p>
        {populated && !updating && <p className="mt-2 max-w-prose text-body text-ink">{words.instruction}</p>}
        {(state.status === "loading" || updating) && <RisksSkeleton />}
        {state.status === "error" && <RisksError state={state} />}
        {result && !updating && (
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
        )}
        <p role="status" className="sr-only" data-risks-live>
          {announce}
        </p>
      </div>
    </section>
  );
}

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
  const ppar = rows.some((row) => row.sources.some((source) => source.doc_short === "PPAR"));
  return (
    <>
      <h3 id={findingId} data-finding className="mt-6 max-w-prose text-h2 text-balance text-ink-heading">
        <Finding result={result} onAll={handlers.onAll} onCount={handlers.onCount} />
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
        <p className="mt-2 flex flex-wrap items-center gap-2 text-small text-error" data-save-failed>
          <CircleX aria-hidden="true" className="size-4 shrink-0 text-error-icon" />
          {words.saveFailed}
          <Button variant="ghost" flush onClick={onRetrySave}>
            {words.tryAgain}
          </Button>
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
      />
      <RiskList rows={rows} m={m} findingId={findingId} selected={selected} onToggle={onToggle} preview={preview} opened={opened} handlers={handlers} packageKey={packageKey} />
      {action && <div className="mt-4 @md/page:hidden">{action}</div>}
      <Checks result={result} />
      <Notes result={result} ppar={ppar} />
    </>
  );
}

// The finding names the most common risk among the rows shown, as the builder picked it.
function Finding({
  result,
  onAll,
  onCount,
}: {
  result: RisksResult;
  onAll: (element: HTMLElement) => void;
  onCount: (row: RiskRow, element: HTMLElement) => void;
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
      check={one ? { tooltip: tips.k(kText), onOpen: (element) => onCount(one, element) } : { tooltip: tips.tie(kText) }}
    />
  );
  const all = <Num value={m} options={{ compact: false }} check={{ tooltip: tips.m(formatNumber(m, { compact: false })), onOpen: onAll }} />;
  if (one) return <Fill template={words.finding} slots={{ risk: one.risk_label, k, m: all }} />;
  if (tied.length === 2) return <Fill template={words.findingTwo} slots={{ a: tied[0].risk_label, b: tied[1].risk_label, k, m: all }} />;
  return <Fill template={words.findingMany} slots={{ tied: formatCount(tied.length, { capital: true }), k, m: all }} />;
}

function CountCell({ row, m, onCount }: { row: RiskRow; m: number; onCount: (row: RiskRow, element: HTMLElement) => void }) {
  const k = formatNumber(row.k, { compact: false });
  return (
    <span data-count={row.risk_key} className="inline-flex flex-col items-end text-right">
      <span className="text-small font-semibold text-ink tabular-nums">
        <Num
          part={row.k}
          whole={m}
          show="count"
          check={{ tooltip: words.numTips.k(k), name: words.countName(k, formatNumber(m, { compact: false }), row.risk_label), onOpen: (element) => onCount(row, element) }}
        />
      </span>
      <span className="text-caption text-ink-muted">{words.reports}</span>
    </span>
  );
}

function Pills({ row, opened, onPill }: { row: RiskRow; opened: Opened; onPill: (source: RiskSource, element: HTMLElement) => void }) {
  return (
    <ul aria-label={words.pillsLabel} className="flex flex-col items-start gap-2 @max-[40rem]/risks:flex-row @max-[40rem]/risks:flex-wrap">
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
};

// At 640 px of card content and wider. table-layout: fixed, so nothing shifts when values change or a row is
// selected: Select 48 px, then Risk, How often, What helped and Sources share the rest.
function RiskTable({ rows, m, findingId, countId, selected, onToggle, preview, opened, handlers }: TableProps) {
  const c = words.columns;
  return (
    <div data-risk-view="table" className="mt-3 hidden rounded-md border border-line @min-[40rem]/risks:block">
      <table aria-labelledby={findingId} aria-describedby={countId} className="w-full table-fixed border-collapse text-small">
        <colgroup>
          <col className="w-12" />
          <col className="w-[23%]" />
          <col className="w-[15%]" />
          <col className="w-[34%]" />
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
                <CountCell row={row} m={m} onCount={handlers.onCount} />
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

// Below 640 px of card content: an ordered list, each risk's name the checkbox's label.
function RiskList({ rows, m, findingId, selected, onToggle, preview, opened, handlers }: TableProps) {
  return (
    <ol aria-labelledby={findingId} data-risk-view="list" className="mt-3 border-t border-line @min-[40rem]/risks:hidden">
      {rows.map((row) => (
        <li key={row.risk_key} data-risk-row={row.risk_key} data-open={rowIsOpen(row, opened) || undefined} className={cx("border-b border-line py-4", rowIsOpen(row, opened) && "-mx-2 rounded-md bg-tint px-2")}>
          <Checkbox checked={selected.includes(row.risk_key)} onChange={(checked) => onToggle(row.risk_key, checked)} name={words.checkbox(row.risk_label)} readOnly={preview}>
            <span className="text-small font-semibold text-ink-heading">{row.risk_label}</span>
          </Checkbox>
          <div className="mt-1 flex flex-col gap-2 pl-8">
            <p className="text-small">
              <ListCount row={row} m={m} onCount={handlers.onCount} />
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

// "{k} of {m}" in small 600, then " completion reports" in caption on the same line where it fits.
function ListCount({ row, m, onCount }: { row: RiskRow; m: number; onCount: (row: RiskRow, element: HTMLElement) => void }) {
  const k = formatNumber(row.k, { compact: false });
  return (
    <span data-count={row.risk_key}>
      <span className="font-semibold text-ink tabular-nums">
        <Num
          part={row.k}
          whole={m}
          show="count"
          check={{ tooltip: words.numTips.k(k), name: words.countName(k, formatNumber(m, { compact: false }), row.risk_label), onOpen: (element) => onCount(row, element) }}
        />
      </span>{" "}
      <span className="text-caption text-ink-muted">{words.reports}</span>
    </span>
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
    <div className="mt-4 flex flex-col gap-2" data-risk-checks>
      <CheckLine numbers={counts.numbers} dates={counts.dates} quotes={counts.quotes} notChecked={notCheckedFor({ checks_run: counts.checks_run, tools: checks.tools })} />
      <RemovedBox removed={removedOf(checks.removed, result.m ?? 0)} lead={words.removed} item={words.removed.item} />
    </div>
  );
}

function Notes({ result, ppar }: { result: RisksResult; ppar: boolean }) {
  return (
    <div className="mt-4 flex flex-col gap-2" data-risk-notes>
      <p className="max-w-prose text-caption text-ink-muted">
        <span className="font-semibold">{words.noteLabel}</span> {words.note(formatCount(result.max_rows))}
      </p>
      <p className="max-w-prose text-caption text-ink-muted">
        {words.abbr}
        {ppar && <> {words.abbrPpar}</>}
      </p>
      <Coverage result={result} />
      <SourceLine result={result} />
    </div>
  );
}

function Coverage({ result }: { result: RisksResult }) {
  const c = words.coverage;
  const tip = { tooltip: words.numTips.counted };
  const p = <Num value={result.p ?? 0} options={{ compact: false }} check={tip} inCaption />;
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
    return <Fill key={gap.reason_code} template={template} slots={{ n: <Num value={gap.count} options={{ compact: false }} check={tip} inCaption /> }} />;
  });
  return (
    <p className="max-w-prose text-caption text-ink-muted" data-coverage-line>
      <Fill template={c.some} slots={{ m: <Num value={result.m ?? 0} options={{ compact: false }} check={tip} inCaption />, p }} />
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
  const date = result.as_of && result.data_through && result.as_of < result.data_through ? result.as_of : result.data_through;
  const asOf = Boolean(result.as_of && result.data_through && result.as_of < result.data_through);
  const names = <Joined items={result.source_names} />;
  return (
    <Source>
      <Fill template={asOf ? words.sourceLineAsOf : words.sourceLine} slots={{ names, date: date ? <Num date={date} /> : "" }} />
    </Source>
  );
}

// ── Empty, loading and error ─────────────────────────────────────────────

function EmptyCard({ title, children }: { title: ReactNode; children?: ReactNode }) {
  return (
    <div className="mt-6 flex gap-3" data-no-risks>
      <CircleDashed aria-hidden="true" className="size-6 shrink-0 text-line-strong" />
      <div className="min-w-0">
        <h3 className="max-w-prose text-h2 text-balance text-ink-heading">{title}</h3>
        {children}
      </div>
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
            <p className="mt-4">
              <TextLink href={readiness}>{e.noComparablesLink}</TextLink>
            </p>
          )}
        </EmptyCard>
      );
    case "no_reports":
      return (
        <EmptyCard title={result.p === 1 ? e.noReportsOne : <Fill template={e.noReports} slots={{ p: <Num value={result.p ?? 0} options={{ compact: false }} /> }} />}>
          <p className="mt-2 max-w-prose text-body text-ink">{e.noReportsBody}</p>
          <p className="mt-4">
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
  const c = words.columns;
  return (
    <div aria-hidden="true" data-risks-skeleton>
      <SkeletonText className="mt-6 max-w-prose text-h2" widths={["w-[90%]", "w-1/2"]} />
      <SkeletonLine className="mt-2 text-caption" width="w-2/5" />
      <div className="mt-3 hidden rounded-md border border-line @min-[40rem]/risks:block">
        <table className="w-full table-fixed border-collapse text-small">
          <colgroup>
            <col className="w-12" />
            <col className="w-[23%]" />
            <col className="w-[15%]" />
            <col className="w-[34%]" />
            <col />
          </colgroup>
          <thead className="bg-surface-2 text-left align-bottom">
            <tr>
              <th className="p-3" />
              <th className="p-3 font-semibold text-ink-heading">{c.risk}</th>
              <th className="p-3 text-right font-semibold text-ink-heading">{c.often}</th>
              <th className="p-3 font-semibold text-ink-heading">{c.helped}</th>
              <th className="p-3 font-semibold text-ink-heading">{c.sources}</th>
            </tr>
          </thead>
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
      <ol className="mt-3 border-t border-line @min-[40rem]/risks:hidden">
        {[0, 1, 2].map((n) => (
          <li key={n} className="flex h-42 gap-4 border-b border-line py-4">
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
    <div className="mt-6 flex flex-col gap-4" data-risks-error>
      <Alert state="error">{words.error}</Alert>
      <div>
        <Button variant="secondary" onClick={state.onRetry}>
          {words.tryAgain}
        </Button>
      </div>
      {code && (
        <p className="text-caption text-ink-muted">
          <Fill template={words.errorCode} slots={{ code: <span className="font-mono">{code}</span> }} />
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
  const root = useRef<HTMLDivElement>(null);
  const focusInside = useRef(false);
  const last = useRef<RisksResult | null>(null);

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
    if (focusInside.current && root.current && !root.current.contains(document.activeElement)) heading.current?.focus();
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
    <div
      ref={root}
      onFocus={() => {
        focusInside.current = true;
      }}
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget as Node | null)) focusInside.current = false;
      }}
    >
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
    </div>
  );
}
