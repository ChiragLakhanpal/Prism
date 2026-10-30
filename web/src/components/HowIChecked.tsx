// "How I checked" (ticket 130, the design lead's Option W2 of October 29, 2026): a Side panel on Check a plan that
// gathers how the check was done, beside the finding from a page area of 75rem and after the activities below it
// (PlanCheck.tsx places it). Three facts, each a label over its sentences and ending with its source line, kept short so
// the first marked row stays in a 1440 by 900 window's first screen:
//
// - Method: the check in one sentence, from check_plan's checks_run, and the plan and project record it read.
// - Compared with: the version before, from the changes route (ticket 21): what this version changed, with "See what
//   changed", which opens "What changed since the plan of ..." in place; the same activities; the earliest plan; or a
//   version before it I haven't read. When only the comparison failed, it says so and links that zone's Try again. A
//   route with no comparison answers 404, and then the fact is left out.
// - Baseline: the plan saved as the baseline for the agency's plans and who saved it, or that none is. Its controls
//   stay in the "Baseline for delay" row at the page's end, which "Go to Baseline for delay" reaches. The public view
//   has no baseline, so the fact is left out there.
//
// Every date and count is the routes'. The page writes them and counts nothing (CLAUDE.md rule 1).
import type { MouseEvent, ReactNode } from "react";
import { copy } from "../copy";
import type { PlanChanges } from "../lib/api";
import { changed, changeList } from "../lib/changes";
import { Fill, Joined, Unbroken } from "./Fill";
import { Num } from "./Num";
import type { CheckedPlan } from "./PlanCheck";
import { SidePanel, type SideFact } from "./SidePanel";
import { Source } from "./Source";
import { TextLink } from "./TextLink";

const words = copy.checkPlan.howChecked;
const line = copy.checkPlan.changes;
const day = (iso: string) => <Num date={iso} />;

// The comparison as the page read it: the changes route's answer, or that it failed.
export type Comparison = { changes: PlanChanges | null; failed: boolean };

export function HowIChecked({
  result,
  comparison,
  baselineView,
  baselineRow,
  onSeeChanges,
}: {
  result: CheckedPlan;
  comparison: Comparison;
  // How the baseline shows in the view the server applied (BaselinePanel.tsx's useBaselineView).
  baselineView: "staff" | "piu" | "public";
  // Whether the page draws the "Baseline for delay" row, which the link goes to.
  baselineRow: boolean;
  // Opens "What changed" in place and moves focus to its heading.
  onSeeChanges: () => void;
}) {
  const facts: SideFact[] = [{ label: words.method, value: <MethodFact result={result} />, wide: true }];
  const compared = comparedFact(result, comparison, onSeeChanges);
  if (compared) facts.push({ label: words.compared, value: compared, wide: true });
  if (baselineView !== "public") facts.push({ label: words.baseline, value: <BaselineFact result={result} view={baselineView} row={baselineRow} />, wide: true });
  return (
    <div data-how-checked>
      <SidePanel title={words.title} facts={facts} />
    </div>
  );
}

function MethodFact({ result }: { result: CheckedPlan }) {
  const phrases = result.checks_run.map((check) => copy.checkPlan.checks[check as keyof typeof copy.checkPlan.checks]).filter(Boolean);
  const { project, plan } = result;
  // The project record gave the closing date, when that check ran.
  const closing = result.checks_run.includes("closing_date") && project.record_date;
  return (
    <>
      <p data-method-one>
        <Fill template={result.baseline ? words.methodSentenceBaseline : words.methodSentence} slots={{ checks: <Joined items={phrases} /> }} />
      </p>
      <Source className="mt-1">
        {closing ? (
          <Fill template={words.methodSource} slots={{ date: day(plan.plan_date), record: day(project.record_date!) }} />
        ) : (
          <Fill template={words.methodSourcePlan} slots={{ date: day(plan.plan_date) }} />
        )}
      </Source>
    </>
  );
}

function comparedFact(result: CheckedPlan, { changes, failed }: Comparison, onSeeChanges: () => void): ReactNode {
  if (failed) {
    // As the change line said under the finding before ticket 130: the zone below holds the alert and Try again.
    return (
      <p data-change-line>
        {line.error}{" "}
        <TextLink href="#changes" className="whitespace-nowrap">
          {line.errorLink}
        </TextLink>
      </p>
    );
  }
  if (!changes) return null;
  const versions = (
    <Source className="mt-1">
      <Fill template={words.versionsSource} slots={{ date: day(result.as_of) }} />
    </Source>
  );
  if (changes.state === "earliest") {
    return (
      <>
        <p data-change-line>{line.earliest}</p>
        {versions}
      </>
    );
  }
  const prev = changes.previous ? day(changes.previous.plan_date) : null;
  if (changes.state === "previous_not_read") {
    return (
      <>
        <p data-change-line>
          <Fill template={line.prevUnread} slots={{ prev_date: prev }} />
        </p>
        {versions}
      </>
    );
  }
  // The plans are named in the sentence above it, so the source line says how they were compared.
  const source = <Source className="mt-1">{words.comparedSource}</Source>;
  if (!changed(changes.counts)) {
    return (
      <>
        <p data-change-line>
          <Fill template={line.same} slots={{ prev_date: prev }} />
        </p>
        {source}
      </>
    );
  }
  const open = (event: MouseEvent<HTMLAnchorElement>) => {
    event.preventDefault();
    onSeeChanges();
  };
  return (
    <>
      <p data-compared>
        <Fill template={words.previous} slots={{ prev_date: prev }} />{" "}
        <Fill template={copy.changes.lead} slots={{ change_list: <Unbroken text={changeList(changes.counts!)} /> }} />{" "}
        <TextLink href="#changes" onClick={open} className="whitespace-nowrap">
          {words.seeChanges}
        </TextLink>
      </p>
      {source}
    </>
  );
}

function BaselineFact({ result, view, row }: { result: CheckedPlan; view: "staff" | "piu"; row: boolean }) {
  const baseline = result.baseline ?? null;
  const named = view === "staff" && baseline?.saved_by;
  let text: ReactNode = words.none;
  if (baseline) {
    const saved = { saved_by: baseline.saved_by ?? "", saved_date: day(baseline.saved_on), baseline_date: day(baseline.plan_date) };
    const isThis = baseline.plan_date === result.plan.plan_date;
    const template = isThis ? (named ? words.thisPlan : words.thisPlanUnnamed) : named ? words.another : words.anotherUnnamed;
    text = <Fill template={template} slots={saved} />;
  }
  return (
    <>
      <p data-baseline-fact>
        {text}
        {row && (
          <>
            {" "}
            <TextLink href="#baseline" className="whitespace-nowrap">
              {words.baselineLink}
            </TextLink>
          </>
        )}
      </p>
      <Source className="mt-1">
        <Fill template={words.baselineSource} slots={{ date: day(result.as_of) }} />
      </Source>
    </>
  );
}
