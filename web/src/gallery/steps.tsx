// The gallery's steps page (ticket 27): section 2 of the package workspace in each of its states, from the answers
// the server wrote on the fixture and on the hand-made set (tests/record_steps_api.py), so each sample is the tool's
// own dates. A state no recording holds is a recording with one value changed. Hover and keyboard focus are captured
// from the app (web/capture/shots.ts, the steps-- shots).
import dated from "../../../tests/fixtures/api/steps-ke-hand-900000.json";
import few from "../../../tests/fixtures/api/steps-ke-hand-900000-few.json";
import fixture from "../../../tests/fixtures/api/steps-ke-nwwda-541055.json";
import needsEarlier from "../../../tests/fixtures/api/steps-planned-hand-made-needs-earlier.json";
import plannedDated from "../../../tests/fixtures/api/steps-planned-hand-made-dated.json";
import planned from "../../../tests/fixtures/api/steps-planned-hand-made.json";
import { useState, type ReactNode } from "react";
import { SegmentedControl } from "../components/SegmentedControl";
import { LongestView, StepComparablesView } from "../components/StepsDrawer";
import { StepsView, type StartField, type StepsState } from "../components/StepsSection";
import { copy } from "../copy";
import { formatDate } from "../lib/format";
import { CHOICES, longestList, stepList, type Choice, type StepDate, type StepDates, type StepsResult } from "../lib/steps";
import { stepFamilies } from "../steps";
import { galleryCopy } from "./copy";
import type { GalleryPage } from "./pages";

const t = galleryCopy.stepSections;
const st = galleryCopy.stepStates;
const DATED = dated as unknown as StepsResult;
const FEW = few as unknown as StepsResult;
const FIXTURE = fixture as unknown as StepsResult;
const PLANNED = planned as unknown as StepsResult;
const PLANNED_DATED = plannedDated as unknown as StepsResult;
const NEEDS_EARLIER = needsEarlier as unknown as StepsResult;
const KEY = "KE-HAND-900000-CW-RFB";

const ready = (result: StepsResult): StepsState => ({ status: "ready", result });
const changed = (result: StepsResult, edit: Partial<StepDates>): StepsResult => ({ ...result, step_dates: { ...result.step_dates!, ...edit } });
const field = (edit: Partial<StartField>): StartField => ({ value: "", error: null, committing: false, slow: false, status: "", ...edit });

// A step a later plan moved: the signed contract re-dated in a plan after its first listing. A function call, so the
// copy lint reads its settings as settings.
const movedStep = (step: StepDate): StepDate =>
  step.step_key === "contract_signed" ? { ...step, plan_latest_date: "2021-07-01", plan_latest_version_date: "2021-01-10" } : step;
const moved = changed(DATED, { steps: DATED.step_dates!.steps.map(movedStep) });
const withActuals = changed(DATED, { actual_steps_count: 3 });
const noFamily = changed(PLANNED, { family: null, family_reason: "no_family", steps: [], longest: null });
const notListed = changed(PLANNED, { family: null, family_reason: "method_not_listed", method: st.otherMethod, steps: [], longest: null });

// Each other family's steps with no comparable package yet, so the labels show in their rows.
function familySteps(family: "firms" | "individuals"): StepsResult {
  const steps = stepFamilies[family].steps.map(
    (entry, index): StepDate => ({
      step_key: entry.key, is_anchor: index < 0, comparables_n: 0, comparables: [], abstain_reason: "few_comparables",
      middle: { planned_date: null, days: null, days_relation: null, longer: null, in10: null },
      cautious: { planned_date: null, days: null, days_relation: null, longer: null, in10: null },
      plan_first_date: null, plan_first_version_date: null, plan_latest_date: null, plan_latest_version_date: null,
    }),
  );
  return changed(FIXTURE, { family, steps, longest: null });
}

// A sample as wide as the workspace column at 1440 px, which shows the table there and the list at 390 px.
function Column({ children }: { children: ReactNode }) {
  return <div className="@container/page flex max-w-[46.5rem] flex-col gap-8">{children}</div>;
}

// The two choices by name, so no sample writes an option's key as a word.
const [MIDDLE, CAUTIOUS] = CHOICES;

function Section({ state, open = false, choice = CAUTIOUS, start, preview, saveFailed, kind = "step" }: {
  state: StepsState; open?: boolean; choice?: Choice; start?: StartField; preview?: boolean; saveFailed?: boolean; kind?: "step" | "planned";
}) {
  const [shown, setShown] = useState(open);
  const [chosen, setChosen] = useState<Choice>(choice);
  return (
    <Column>
      <StepsView
        state={state}
        packageKey={KEY}
        kind={kind}
        open={shown}
        onToggle={() => setShown((now) => !now)}
        choice={chosen}
        onChoose={setChosen}
        start={start}
        preview={preview}
        saveFailed={saveFailed}
      />
    </Column>
  );
}

function Segments({ initial }: { initial: Choice }) {
  const [value, setValue] = useState<Choice>(initial);
  return (
    <SegmentedControl
      legend={copy.stepDates.choice.legend}
      value={value}
      onChange={setValue}
      options={CHOICES.map((choice) => ({
        value: choice,
        label: choice === MIDDLE ? copy.stepDates.choice.middle : copy.stepDates.choice.cautious(String(DATED.step_dates!.cautious_in10)),
      }))}
    />
  );
}

// The drawer's lists, as wide as the drawer beside the page.
function DrawerPart({ children }: { children: ReactNode }) {
  return <div className="flex max-w-[37.5rem] flex-col gap-4 rounded-md border border-line p-6">{children}</div>;
}

export function stepsPage(): GalleryPage {
  const signedIndex = DATED.step_dates!.steps.findIndex((step) => step.step_key === "contract_signed");
  return {
    slug: "steps",
    current: "packages",
    sections: [
      {
        id: "segmented",
        title: t.segmented,
        body: (
          <div className="@container/page flex flex-col gap-6">
            <p className="text-caption text-ink-muted">{st.cautiousChosen}</p>
            <Segments initial={CAUTIOUS} />
            <p className="text-caption text-ink-muted">{st.middleChosen}</p>
            <Segments initial={MIDDLE} />
          </div>
        ),
      },
      { id: "collapsed", title: t.collapsed, body: <Section state={ready(DATED)} /> },
      { id: "collapsed-partial", title: t.collapsedPartial, body: <Section state={ready(FIXTURE)} /> },
      { id: "collapsed-abstain", title: t.collapsedAbstain, body: <Section state={ready(FEW)} /> },
      { id: "collapsed-no-family", title: t.collapsedNoFamily, body: <Section state={ready(noFamily)} kind="planned" /> },
      { id: "collapsed-not-listed", title: t.collapsedNotListed, body: <Section state={ready(notListed)} kind="planned" /> },
      { id: "loading", title: t.loading, body: <Section state={{ status: "loading" }} /> },
      { id: "error", title: t.error, body: <Section state={{ status: "error", error: null, onRetry: () => undefined }} /> },
      { id: "cautious", title: t.cautious, body: <Section state={ready(DATED)} open /> },
      { id: "middle", title: t.middle, body: <Section state={ready(DATED)} open choice={MIDDLE} /> },
      { id: "moved", title: t.moved, body: <Section state={ready(moved)} open /> },
      { id: "fixture", title: t.fixture, body: <Section state={ready(FIXTURE)} open /> },
      { id: "actuals", title: t.actuals, body: <Section state={ready(withActuals)} open /> },
      { id: "preview", title: t.preview, body: <Section state={ready(DATED)} open preview /> },
      { id: "save-failed", title: t.saveFailed, body: <Section state={ready(DATED)} open saveFailed /> },
      { id: "undated", title: t.undated, body: <Section state={ready(PLANNED)} open kind="planned" /> },
      { id: "invalid", title: t.invalid, body: <Section state={ready(PLANNED)} open kind="planned" start={field({ error: "empty" })} /> },
      {
        id: "committing",
        title: t.committing,
        body: (
          <Section
            state={ready(PLANNED)}
            open
            kind="planned"
            start={field({ value: "2021-03-01", committing: true, slow: true, status: copy.stepDates.start.dating(formatDate("2021-03-01")) })}
          />
        ),
      },
      { id: "dated", title: t.dated, body: <Section state={ready(PLANNED_DATED)} open kind="planned" start={field({ value: "2021-03-01" })} /> },
      { id: "needs-earlier", title: t.needsEarlier, body: <Section state={ready(NEEDS_EARLIER)} open kind="planned" start={field({ value: "2021-03-01" })} /> },
      { id: "abstain", title: t.abstain, body: <Section state={ready(FEW)} open /> },
      { id: "firms", title: t.firms, body: <Section state={ready(familySteps("firms"))} open /> },
      { id: "individuals", title: t.individuals, body: <Section state={ready(familySteps("individuals"))} open /> },
      {
        id: "step-list",
        title: t.stepList,
        body: (
          <DrawerPart>
            <StepComparablesView evidence={stepList(KEY, DATED, signedIndex)} />
          </DrawerPart>
        ),
      },
      {
        id: "step-list-abstains",
        title: t.stepListAbstains,
        body: (
          <DrawerPart>
            <StepComparablesView evidence={stepList("KE-NWWDA-541055-CW-RFB", FIXTURE, signedIndex)} />
          </DrawerPart>
        ),
      },
      {
        id: "longest-list",
        title: t.longestList,
        body: (
          <DrawerPart>
            <LongestView evidence={longestList(KEY, DATED)} />
          </DrawerPart>
        ),
      },
    ],
  };
}
