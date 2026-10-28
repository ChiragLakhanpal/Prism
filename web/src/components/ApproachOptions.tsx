// Section 4 of the package workspace, "Procurement approach options" (ticket 26; the 26 brief, sections 6.4 and
// 7.7), for section 6 of the borrower's PPSD: up to three approaches comparable packages went with, as
// estimate_time returned them, most first, each with how many went with it and the time estimate for this package
// with it. A Collapsed section, closed by default; its summary still says the finding. Every number is the tool's.
//
// Its table is four columns, and becomes one card per approach when its own frame is under 480 px (30rem), as the
// brief's container rule says, so the evidence drawer can narrow it. A time estimate that abstains takes one cell
// across both estimate columns. Each "{k} of {n}" opens the evidence drawer's list of the packages it names.
import { useRef, useState, type ReactNode } from "react";
import { copy } from "../copy";
import type { Approach, ComparablesResult, EstimateResult } from "../lib/api";
import { formatCount, formatNumber } from "../lib/format";
import { openWentWith } from "../lib/packages";
import { Alert } from "./Alert";
import { Button } from "./Button";
import { CollapsedSection, type CollapsedState } from "./CollapsedSection";
import { Fill, Joined } from "./Fill";
import { Num } from "./Num";
import { fromLine, recordsFrom } from "./NumFrom";
import { Source } from "./Source";
import type { EstimateState } from "./TimeEstimate";
import { months1 } from "./TimeEstimate";

const words = copy.approachOptions;
const what = copy.whatIf;

export type ApproachOptionsState =
  | { kind: "loading" }
  | { kind: "waiting" }
  | { kind: "empty" }
  | { kind: "error"; onRetry: () => void }
  | { kind: "ready"; comparables: ComparablesResult; estimate: EstimateResult };

// The state section 4 takes from section 1's two answers and the page: the comparables, the time estimate, and
// whether section 1 is still asking for the plan.
export function approachState(
  comparables: { status: "loading" } | { status: "error" } | { status: "ready"; result: ComparablesResult },
  estimate: EstimateState | undefined,
  waiting: boolean,
  onRetry: () => void,
): ApproachOptionsState {
  if (waiting) return { kind: "waiting" };
  if (comparables.status === "loading") return { kind: "loading" };
  if (comparables.status === "error") return { kind: "error", onRetry };
  const reason = comparables.result.abstention?.reason;
  if (reason === "no_comparables" || reason === "none_measurable" || reason === "no_public_notice" || reason === "unknown_package") {
    return { kind: "empty" };
  }
  if (!estimate || estimate.status === "loading") return { kind: "loading" };
  if (estimate.status === "error") return { kind: "error", onRetry: estimate.onRetry };
  return { kind: "ready", comparables: comparables.result, estimate: estimate.result };
}

// An approach's name: "Open international, 2 lots, post-qualification", or in a sentence, "open international, 2
// lots, post-qualification".
function approachName(approach: Approach, inSentence = false): string {
  const market = inSentence ? what.inSentence_market_approach : what.label_market_approach;
  return words.approach(
    market[approach.market_approach] ?? approach.market_approach,
    what.lots(approach.lots),
    what.inSentence_prequalification[approach.prequalification] ?? approach.prequalification,
  );
}

// An approach's time estimate cells: its middle half and its 8-in-10 point, or one sentence that says why it has none.
type Cells = { kind: "points"; middle: string; in10: string } | { kind: "none"; text: ReactNode };

function estimateCells(approach: Approach): Cells {
  if (approach.estimate) {
    return { kind: "points", middle: `${months1(approach.estimate.q25)}–${months1(approach.estimate.q75)}`, in10: months1(approach.estimate.q80) };
  }
  const reason = approach.abstention?.reason ?? "value_not_learned";
  const template = words.cell[reason as keyof typeof words.cell] ?? words.cell.value_not_learned;
  return { kind: "none", text: <Fill template={template} slots={{ k: <Num count={approach.k} /> }} /> };
}

function KOfN({ approach, n, index, comparables }: { approach: Approach; n: number; index: number; comparables: ComparablesResult }) {
  const anchor = useRef<HTMLSpanElement>(null);
  const option = approachName(approach, true);
  return (
    <span ref={anchor} className="whitespace-nowrap">
      <Fill
        template={words.kOfN}
        slots={{
          k: (
            <Num
              value={approach.k}
              options={{ compact: false }}
              check={{
                tooltip: what.explainCount(option, formatNumber(n, { compact: false })),
                // Counted from the comparable packages' records, as the past range's numbers are.
                from: fromLine(recordsFrom(comparables.sources, comparables.records_through)),
                act: what.explainCountAct,
                opens: "record",
                onOpen: () => {
                  const button = anchor.current?.querySelector("button");
                  if (button) openWentWith(comparables, { key: `approach-${index}`, k: approach.k, n, matching_ids: approach.matching_ids }, option, button);
                },
              }}
            />
          ),
          n: <Num value={n} options={{ compact: false }} />,
        }}
      />
    </span>
  );
}

function OptionsTable({ comparables, estimate }: { comparables: ComparablesResult; estimate: EstimateResult }) {
  const options = estimate.options!;
  const [first] = options.approaches;
  const columns = words.columns;
  // "The most common approach" only when no approach is ruled out: the tool doesn't count each ruled-out one.
  const title = options.ruled_out > 0 ? words.titleAllowed : words.title;
  return (
    <div className="@container/options flex flex-col gap-3" data-approach-table>
      <table className="w-full border-collapse text-small @max-[30rem]/options:hidden">
        <caption className="pb-2 text-left text-h2 text-ink-heading">
          <Fill template={title} slots={{ k1: <Num count={first.k} capital />, n: <Num value={options.n} options={{ compact: false }} />, option1: approachName(first, true) }} />
          <span className="mt-1 block text-caption font-normal text-ink-muted">{words.count(formatCount(options.approaches.length))}</span>
        </caption>
        <thead className="bg-surface-2 text-left text-caption text-ink-muted">
          <tr>
            <th scope="col" className="w-2/5 p-3 align-bottom font-semibold">{columns.approach}</th>
            <th scope="col" className="p-3 text-right align-bottom font-semibold">
              {columns.wentWith}
              <span className="block font-normal">{columns.wentWithNote}</span>
            </th>
            <th scope="col" className="p-3 text-right align-bottom font-semibold">
              {columns.middle}
              <span className="block font-normal">{columns.middleNote}</span>
            </th>
            <th scope="col" className="p-3 text-right align-bottom font-semibold">{columns.in10}</th>
          </tr>
        </thead>
        <tbody>
          {options.approaches.map((approach, index) => {
            const cells = estimateCells(approach);
            return (
              <tr key={index} className="border-t border-line align-top" data-approach={index}>
                <th scope="row" className="p-3 text-left font-normal text-ink">
                  {approachName(approach)}
                  {approach.is_as_described && <span className="block text-caption text-ink-muted">{words.asDescribed}</span>}
                </th>
                <td className="p-3 text-right tabular-nums">
                  <KOfN approach={approach} n={options.n} index={index} comparables={comparables} />
                </td>
                {cells.kind === "none" ? (
                  <td colSpan={2} className="p-3 text-left text-ink-muted">
                    {cells.text}
                  </td>
                ) : (
                  <>
                    <td className="p-3 text-right tabular-nums">{cells.middle}</td>
                    <td className="p-3 text-right tabular-nums">{cells.in10}</td>
                  </>
                )}
              </tr>
            );
          })}
        </tbody>
      </table>
      {/* Below a 480 px frame: one card per approach. */}
      <div className="hidden flex-col gap-3 @max-[30rem]/options:flex">
        <p className="text-h2 text-ink-heading">
          <Fill template={title} slots={{ k1: <Num count={first.k} capital />, n: <Num value={options.n} options={{ compact: false }} />, option1: approachName(first, true) }} />
        </p>
        <p className="text-caption text-ink-muted">{words.count(formatCount(options.approaches.length))}</p>
        <ul className="flex flex-col gap-3">
          {options.approaches.map((approach, index) => (
            <li key={index} className="rounded-md border border-line p-4" data-approach-card={index}>
              <h4 className="text-small font-semibold text-ink-heading">{approachName(approach)}</h4>
              {approach.is_as_described && <p className="text-caption text-ink-muted">{words.asDescribed}</p>}
              <p className="mt-2 text-small text-ink">
                <Fill template={words.card.wentWith} slots={{ k: <Num count={approach.k} capital />, n: <Num value={options.n} options={{ compact: false }} /> }} />
              </p>
              <p className="mt-1 text-small text-ink">
                {approach.estimate ? (
                  <Fill
                    template={words.card.estimate}
                    slots={{
                      w25: <Num value={approach.estimate.q25} options={{ decimals: 1, compact: false }} />,
                      w75: <Num value={approach.estimate.q75} options={{ decimals: 1, compact: false }} />,
                      w80: <Num value={approach.estimate.q80} options={{ decimals: 1, compact: false }} />,
                    }}
                  />
                ) : (
                  <span className="text-ink-muted">{(estimateCells(approach) as { text: ReactNode }).text}</span>
                )}
              </p>
            </li>
          ))}
        </ul>
      </div>
      <Notes comparables={comparables} estimate={estimate} />
    </div>
  );
}

function Notes({ comparables, estimate }: { comparables: ComparablesResult; estimate: EstimateResult }) {
  const options = estimate.options!;
  const n = <Num value={options.n} options={{ compact: false }} />;
  const sources = <Joined items={comparables.sources.map((source) => source.dataset_name)} />;
  return (
    <div className="flex flex-col gap-2 text-caption text-ink-muted">
      {options.unrecorded > 0 && (
        <p>
          <Fill template={words.unrecorded(options.unrecorded)} slots={{ rest: <Num count={options.unrecorded} capital />, n }} />
        </p>
      )}
      {options.ruled_out > 0 && (
        <p>
          <Fill template={words.ruledOut(options.ruled_out)} slots={{ ruled: <Num count={options.ruled_out} capital />, n }} />
        </p>
      )}
      {options.review_type && (
        <p>
          <Fill template={words.note} slots={{ reviewType: options.review_type }} />
        </p>
      )}
      <Source>
        {comparables.records_through ? (
          <Fill template={words.source} slots={{ sources, date: <Num date={comparables.records_through} /> }} />
        ) : (
          sources
        )}{" "}
        {estimate.estimate && <Fill template={copy.timeEstimate.source} slots={{ date: <Num date={estimate.estimate.scored_on} /> }} />}
      </Source>
    </div>
  );
}

export function ApproachOptions({ state }: { state: ApproachOptionsState }) {
  const [open, setOpen] = useState(false);
  // Ticket 31's Collapsed section: "empty" shows the summary alone with no button, for every state with nothing to
  // open (waiting for the plan, no comparables, an abstention or one approach only).
  let shown: CollapsedState = "empty";
  let summary: ReactNode = null;
  let error: ReactNode = null;
  let content: ReactNode = null;
  if (state.kind === "loading") shown = "loading";
  else if (state.kind === "waiting") summary = words.waiting;
  else if (state.kind === "empty") summary = words.empty;
  else if (state.kind === "error") {
    shown = "error";
    error = (
      <Alert
        state="error"
        live="alert"
        action={
          <Button variant="secondary" onClick={state.onRetry}>
            {words.tryAgain}
          </Button>
        }
      >
        {words.error}
      </Alert>
    );
  } else {
    const { estimate, comparables } = state;
    const n = estimate.comparables.n;
    const options = estimate.options;
    if (estimate.abstention?.reason === "too_few_comparables") {
      summary = n === 1 ? words.abstainOne : <Fill template={words.abstain} slots={{ n: <Num count={n} /> }} />;
    } else if (!options) {
      // No time estimate for another reason (no_model, asof_before_training): the count is not why.
      summary = words.noEstimate;
    } else if (options.approaches.length === 0) {
      // No approach to list: none recorded a whole one, or the thresholds rule out every one recorded.
      summary =
        options.ruled_out > 0 ? (
          <Fill template={words.summaryRuledOut(options.ruled_out)} slots={{ ruled: <Num count={options.ruled_out} /> }} />
        ) : (
          <Fill template={words.summaryNone} slots={{ n: <Num value={n} options={{ compact: false }} /> }} />
        );
    } else if (options.count === 1) {
      const only = options.approaches[0];
      const template =
        only.k === n ? words.summaryOne : options.ruled_out > 0 ? words.summaryOneRuledOut(options.ruled_out) : words.summaryOneRecorded;
      summary = (
        <Fill
          template={template}
          slots={{
            k1: <Num count={only.k} capital />,
            n: <Num value={n} options={{ compact: false }} />,
            option1: approachName(only, true),
            ruled: <Num count={options.ruled_out} capital />,
          }}
        />
      );
    } else {
      const [first] = options.approaches;
      shown = "ready";
      summary = (
        <Fill
          template={options.ruled_out > 0 ? words.summaryAllowed : words.summary}
          slots={{
            count: <Num count={options.count} />,
            option1: approachName(first, true),
            k1: <Num value={first.k} options={{ compact: false }} />,
            n: <Num value={n} options={{ compact: false }} />,
          }}
        />
      );
      content = (
        <div className="mt-4">
          <OptionsTable comparables={comparables} estimate={estimate} />
        </div>
      );
    }
  }
  return (
    <div data-approach-options={state.kind}>
      <CollapsedSection
        id="approach-options"
        eyebrow={words.eyebrow}
        number={words.number}
        heading={words.heading}
        summary={summary}
        error={error}
        state={shown}
        open={open && shown === "ready"}
        onToggle={() => setOpen((now) => !now)}
        showLabel={words.show}
        hideLabel={words.hide}
        sectionKey="approach-options"
      >
        {content}
      </CollapsedSection>
    </div>
  );
}
