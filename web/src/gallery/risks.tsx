// The gallery's risks page (ticket 30): section 3 of the package workspace in each of its states, from the answers
// the server wrote on the fixture (tests/record_risks_api.py), so each sample is the builder's own rows. A state no
// recording holds is a recording with one value changed. Hover and keyboard focus are captured from the app
// (web/capture/shots.ts, the risks-- shots).
import india from "../../../tests/fixtures/api/risks-ke-nwwda-541055-india.json";
import kenya from "../../../tests/fixtures/api/risks-ke-nwwda-541055.json";
import { useLayoutEffect, useState, type ReactNode } from "react";
import { Checkbox } from "../components/Checkbox";
import { AllReportsView, RiskReportsView, RowClaim, RowSwitcher } from "../components/RiskDrawer";
import { RisksView, type RisksState } from "../components/RisksSection";
import { SourcePill } from "../components/SourcePill";
import type { IegStatus } from "../lib/lessons";
import { allReportsList, reportsList, type RiskRow, type RisksResult } from "../lib/risks";
import { copy } from "../copy";
import { galleryCopy } from "./copy";
import type { GalleryPage } from "./pages";

const t = galleryCopy.riskSections;
const st = galleryCopy.riskStates;
const READY = india as unknown as RisksResult;
const NONE = kenya as unknown as RisksResult;
const [COST, PERMITS] = READY.rows as [RiskRow, RiskRow];
const KEY = "KE-NWWDA-541055-CW-RFB";
const nothing = () => undefined;

const ready = (result: RisksResult): RisksState => ({ status: "ready", result });
const changed = (edit: Partial<RisksResult>): RisksResult => ({ ...READY, ...edit });

const oneMost = changed({ rows: [{ ...COST, k: 1 }, { ...PERMITS }], most_common: { risk_keys: [COST.risk_key], k_max: 1 } });
// A row with another risk's key and name, or with another IEG part in its lesson's evidence. Function calls, so the
// copy lint reads their settings as settings.
const renamed = (row: RiskRow, riskKey: string, label: string): RiskRow => ({ ...row, risk_key: riskKey, risk_label: label });
const withIeg = (row: RiskRow, status: IegStatus): RiskRow => ({
  ...row,
  lesson: { ...row.lesson, ieg_status: status, ieg_quote: null, review_date: status === "not_restated" ? row.sources.at(-1)?.date ?? null : null },
});
const third = renamed(PERMITS, "evaluation_delays", st.thirdRisk);
const manyTied = changed({ rows: [COST, PERMITS, third], most_common: { risk_keys: [COST.risk_key, PERMITS.risk_key, third.risk_key], k_max: 1 } });
const dropped = changed({ selected_not_shown: [{ risk_key: third.risk_key, risk_label: third.risk_label }] });
const removedCount = {
  risk_key: PERMITS.risk_key,
  risk_label: PERMITS.risk_label,
  claim_kind: "count" as const,
  k: PERMITS.k,
  lesson_text: PERMITS.lesson.text,
  check: 1,
  reason_code: "number_not_in_records",
};
const removedHelped = { ...removedCount, risk_key: COST.risk_key, risk_label: COST.risk_label, claim_kind: "helped" as const, lesson_text: COST.lesson.text, check: 2, reason_code: "id_not_returned" };
const withRemoved = changed({
  rows: [COST],
  most_common: { risk_keys: [COST.risk_key], k_max: COST.k },
  verifier: { ...READY.verifier!, removed: [removedCount] },
});
const allRemoved = changed({ rows: [], most_common: null, empty_reason: "all_removed", written: 2, verifier: { ...READY.verifier!, removed: [removedHelped, removedCount] } });
const empty = (edit: Partial<RisksResult>) => changed({ rows: [], most_common: null, verifier: null, ...edit });
const asOf = changed({ as_of: "2026-03-31" });

// A sample as wide as the workspace column at 1440 px, so the section shows as its table there and as its list
// below 640 px of card content.
function Column({ children }: { children: ReactNode }) {
  return <div className="flex max-w-[46.5rem] flex-col gap-8">{children}</div>;
}

function Labeled({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-2">
      <p className="text-caption text-ink-muted">{label}</p>
      {children}
    </div>
  );
}

function Section({ state, selected = [], ...rest }: { state: RisksState; selected?: string[]; preview?: boolean; saveFailed?: boolean; missingList?: string; kind?: "step" | "planned" }) {
  const [chosen, setChosen] = useState(selected);
  return (
    <Column>
      <RisksView
        state={state}
        packageKey={KEY}
        kind={rest.kind ?? "step"}
        selected={chosen}
        onToggle={(key, on) => setChosen((now) => (on ? [...now, key] : now.filter((one) => one !== key)))}
        preview={rest.preview}
        saveFailed={rest.saveFailed}
        onRetrySave={nothing}
        missingList={rest.missingList}
      />
    </Column>
  );
}

// A rerun over 400 ms (ticket 59): the risks draw once, so their height is known, then the rerun starts before the first
// paint, and the skeleton holds that height with the instruction and the foot strip's place kept.
function Updating() {
  const [updating, setUpdating] = useState(false);
  useLayoutEffect(() => setUpdating(true), []);
  return (
    <Column>
      <RisksView state={ready(READY)} packageKey={KEY} kind="step" selected={[]} onToggle={nothing} updating={updating} />
    </Column>
  );
}

function Toggle({ initial, readOnly = false, label }: { initial: boolean; readOnly?: boolean; label?: string }) {
  const [on, setOn] = useState(initial);
  return (
    <Checkbox checked={on} onChange={setOn} name={copy.packageRisks.checkbox(COST.risk_label)} readOnly={readOnly}>
      {label}
    </Checkbox>
  );
}

// The drawer's parts for a row, as wide as the drawer beside the page.
function DrawerPart({ children }: { children: ReactNode }) {
  return <div className="flex max-w-[37.5rem] flex-col gap-4 rounded-md border border-line p-6">{children}</div>;
}

export function risksPage(): GalleryPage {
  const [icr, review] = COST.sources;
  return {
    slug: "risks",
    current: "packages",
    sections: [
      {
        id: "pills",
        title: t.pills,
        body: (
          <div className="flex flex-col gap-4">
            <Labeled label={st.pill}>
              <div>
                <SourcePill source={icr} controlsId={null} onOpen={nothing} />
              </div>
            </Labeled>
            <Labeled label={st.pillLater}>
              <div>
                <SourcePill source={review} withProject={false} controlsId={null} onOpen={nothing} />
              </div>
            </Labeled>
            <Labeled label={st.pillActive}>
              <div>
                <SourcePill source={icr} active controlsId={null} onOpen={nothing} />
              </div>
            </Labeled>
            <Labeled label={st.pillVisited}>
              <div>
                <SourcePill source={icr} opened controlsId={null} onOpen={nothing} />
              </div>
            </Labeled>
          </div>
        ),
      },
      {
        id: "checkboxes",
        title: t.checkboxes,
        body: (
          <div className="flex flex-wrap items-start gap-8">
            <Labeled label={st.unchecked}>
              <Toggle initial={false} />
            </Labeled>
            <Labeled label={st.checked}>
              <Toggle initial />
            </Labeled>
            <Labeled label={st.readOnly}>
              <Toggle initial={false} readOnly />
            </Labeled>
            <Labeled label={st.readOnlyChecked}>
              <Toggle initial readOnly />
            </Labeled>
            <Labeled label={st.labelled}>
              <Toggle initial label={COST.risk_label} />
            </Labeled>
          </div>
        ),
      },
      { id: "table", title: t.table, body: <Section state={ready(READY)} /> },
      { id: "one-selected", title: t.oneSelected, body: <Section state={ready(READY)} selected={[COST.risk_key]} /> },
      { id: "all-selected", title: t.allSelected, body: <Section state={ready(READY)} selected={READY.rows.map((row) => row.risk_key)} /> },
      { id: "one-most", title: t.oneMost, body: <Section state={ready(oneMost)} /> },
      { id: "many-tied", title: t.manyTied, body: <Section state={ready(manyTied)} /> },
      { id: "preview", title: t.preview, body: <Section state={ready(READY)} selected={[COST.risk_key]} preview /> },
      { id: "dropped", title: t.dropped, body: <Section state={ready(dropped)} selected={[third.risk_key]} /> },
      { id: "save-failed", title: t.saveFailed, body: <Section state={ready(READY)} selected={[COST.risk_key]} saveFailed /> },
      { id: "removed", title: t.removed, body: <Section state={ready(withRemoved)} /> },
      { id: "all-removed", title: t.allRemoved, body: <Section state={ready(allRemoved)} /> },
      {
        id: "missing",
        title: t.missing,
        body: <Section state={ready(empty({ empty_reason: "missing_criteria", p: null, m: null }))} kind="planned" missingList={st.missingList} />,
      },
      { id: "no-comparables", title: t.noComparables, body: <Section state={ready(empty({ empty_reason: "no_comparables", p: null, m: null }))} kind="planned" /> },
      { id: "no-comparables-step", title: t.noComparablesStep, body: <Section state={ready(empty({ empty_reason: "no_comparables", p: null, m: null }))} /> },
      { id: "no-reports", title: t.noReports, body: <Section state={ready(NONE)} /> },
      { id: "no-lessons", title: t.noLessons, body: <Section state={ready(empty({ empty_reason: "no_lessons" }))} /> },
      { id: "as-of", title: t.asOf, body: <Section state={ready(asOf)} /> },
      { id: "loading", title: t.loading, body: <Section state={{ status: "loading" }} /> },
      { id: "updating", title: t.updating, body: <Updating /> },
      { id: "error", title: t.error, body: <Section state={{ status: "error", error: null, onRetry: nothing }} /> },
      {
        id: "claim",
        title: t.claim,
        body: (
          <DrawerPart>
            <RowClaim row={COST} />
            <RowSwitcher row={COST} current={icr.evidence_id} panelId="risks-gallery-claim" onChoose={nothing} />
            <div id="risks-gallery-claim" role="tabpanel" aria-labelledby="risks-gallery-claim-tab-0" />
          </DrawerPart>
        ),
      },
      {
        id: "awaiting",
        title: t.awaiting,
        body: (
          <DrawerPart>
            <RowClaim row={withIeg(COST, "awaiting")} />
          </DrawerPart>
        ),
      },
      {
        id: "not-restated",
        title: t.notRestated,
        body: (
          <DrawerPart>
            <RowClaim row={withIeg(COST, "not_restated")} />
          </DrawerPart>
        ),
      },
      {
        id: "reports",
        title: t.reports,
        body: (
          <DrawerPart>
            <RiskReportsView evidence={reportsList(KEY, COST, READY.m ?? 0)} />
          </DrawerPart>
        ),
      },
      {
        id: "all-reports",
        title: t.allReports,
        body: (
          <DrawerPart>
            <AllReportsView evidence={allReportsList(KEY, READY)} />
          </DrawerPart>
        ),
      },
    ],
  };
}
