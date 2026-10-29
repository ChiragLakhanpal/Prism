// The gallery's "Check your criteria" page (ticket 31): section 5 of the package workspace in each state, from the
// server's own answers on the fixture (tests/record_criteria_api.py), so each sample is a real package with the
// server's values. The one exception is the cost lane with 20 packages or more, which no fixture package has: it
// is a made-up sample, labelled so. Hover, keyboard focus and the drawer opened from the page are captured from
// the app (web/capture/shots.ts).
import worksSummary from "../../../tests/fixtures/api/criteria-summary-ke-nwwda-541055.json";
import consultantSummary from "../../../tests/fixtures/api/criteria-summary-ke-cwsb-224323.json";
import comparedSummary from "../../../tests/fixtures/api/criteria-summary-ke-cwsb-224323-compared.json";
import awardNotice from "../../../tests/fixtures/api/evidence-award-notice-op00125282.json";
import noticePassage from "../../../tests/fixtures/api/evidence-passage-op00077276-s3.json";
import lessonParagraph from "../../../tests/fixtures/api/evidence-icr-p130164-54.json";
import worksRun from "../../../tests/fixtures/api/criteria-run-ke-nwwda-541055.sse?raw";
import consultantRun from "../../../tests/fixtures/api/criteria-run-ke-cwsb-224323.sse?raw";
import similar from "../../../tests/fixtures/api/criteria-compare-similar-experience.sse?raw";
import liveTender from "../../../tests/fixtures/api/criteria-compare-live-tender.sse?raw";
import partial from "../../../tests/fixtures/api/criteria-compare-partial-refusal.sse?raw";
import noneFound from "../../../tests/fixtures/api/criteria-compare-none-found.sse?raw";
import swapped from "../../../tests/fixtures/api/criteria-compare-swapped-reading.sse?raw";
// A mock above 60 packages, whose lane draws quantile dots (ticket 59): made up, as the file says.
import quantileCost from "../../../tests/fixtures/api/criteria-cost-mock-quantile-dots.json";
import { useId, type ReactNode } from "react";
import { CheckCriteriaView, type CompareState, type RunState, type SummaryState, type ViewProps } from "../components/CheckCriteria";
import { CostEstimate } from "../components/CostLane";
import { EvidenceDrawerView } from "../components/EvidenceDrawer";
import type { EvidenceEvent } from "../lib/answer";
import type { Origin } from "../lib/evidence";
import {
  costRecordEvent,
  itemListEvent,
  itemListId,
  publicListEvent,
  type Comparison,
  type Cost,
  type CriteriaSummary,
  type LessonEntry,
  type PackageRun,
} from "../lib/criteria";
import { dataReadinessHref } from "../routes";
import { galleryCopy } from "./copy";
import type { GalleryPage } from "./pages";

const cs = galleryCopy.criteriaStates;
const nothing = () => undefined;

function eventOf<T>(text: string, type: string): T {
  for (const block of text.split("\n\n")) {
    const lines = block.split("\n").filter((line) => line && !line.startsWith(":"));
    if (lines.length && lines[0] === `event: ${type}`) return JSON.parse(lines[1].slice("data: ".length)) as T;
  }
  throw new Error(`No ${type} event in the recording.`);
}

const WORKS = worksSummary as unknown as CriteriaSummary;
const CONSULTANT = consultantSummary as unknown as CriteriaSummary;
const COMPARED = comparedSummary as unknown as CriteriaSummary;
const WORKS_RUN = eventOf<PackageRun>(worksRun, "package_run");
const CONSULTANT_RUN = eventOf<PackageRun>(consultantRun, "package_run");
const SIMILAR = eventOf<Comparison>(similar, "comparison");
const LIVE = eventOf<Comparison>(liveTender, "comparison");
const PARTIAL = eventOf<Comparison>(partial, "comparison");
const NONE = eventOf<Comparison>(noneFound, "comparison");
const SWAPPED = eventOf<Comparison>(swapped, "comparison");
const PASTED =
  "1. Similar experience: at least two contracts of similar works of US$10 million each.\n" +
  "2. Average annual turnover: US$25 million over the last three years.\n" +
  "3. The bid must be signed by a person with a power of attorney.";

// A made-up cost lane with 24 packages, to show the middle half, the middle and the range sentence, which only
// 20 packages or more draw. Its numbers are a sample, never a finding.
const RANGED: Cost = (() => {
  const diffs = [-38.2, -31.5, -27.9, -22.4, -18.6, -15.1, -12.7, -9.8, -7.4, -5.2, -3.1, -1.6, 0, 2.4, 4.9, 7.3, 9.9,
    13.5, 18.2, 24.6, 31.8, 47.5, 72.3, 118];
  const rows = diffs.map((diff, index) => {
    const reference = `KE-SAMPLE-${String(index + 1).padStart(4, "0")}-CW-RFB`;
    return { ...WORKS_RUN.cost.rows[0], evidence_id: `strata.gold.package:${reference}/cost`, step_reference: reference, diff_pct: diff, rank: index + 1 };
  });
  return {
    ...WORKS_RUN.cost,
    rows,
    counts: { ...WORKS_RUN.cost.counts, m: 24, total: 30, open: 4, no_estimate: 2, above: 11, below: 12, at: 1 },
    quartiles: { q25: -13.9, q50: 1.2, q75: 14.7 },
    abstention: null,
  };
})();

const ready = (data: CriteriaSummary): SummaryState => ({ status: "ready", data });
const ranRun = (result: PackageRun): RunState => ({ status: "ready", result });
const compared = (result: Comparison, stale = false): CompareState => ({ status: "ready", result, stale });

function view(overrides: Partial<ViewProps>): ViewProps {
  return {
    summary: ready(CONSULTANT),
    open: false,
    onToggle: nothing,
    run: { status: "idle" },
    comparison: { status: "idle" },
    text: "",
    onText: nothing,
    onCompare: nothing,
    fieldError: null,
    edited: false,
    preview: false,
    checks: null,
    ...overrides,
  };
}

function Labeled({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-2">
      <p className="text-caption text-ink-muted">{label}</p>
      {children}
    </div>
  );
}

// A sample as wide as the workspace's column at 1440 px: columns 1 to 7.
function Column({ children }: { children: ReactNode }) {
  return <div className="@container/page max-w-[46.5rem]">{children}</div>;
}

function Sample({ label, props }: { label: string; props: ViewProps }) {
  const id = useId();
  return (
    <Labeled label={label}>
      <Column>
        <CheckCriteriaView {...props} sectionId={id} />
      </Column>
    </Labeled>
  );
}

function Drawer({ label, evidence, from = null, lesson = null }: {
  label: string; evidence: EvidenceEvent; from?: Origin | null; lesson?: LessonEntry | null;
}) {
  const id = useId();
  return (
    <Labeled label={label}>
      <div className="max-w-[36rem] border border-line">
        <EvidenceDrawerView id={evidence.id} data={{ status: "ready", evidence }} run={null} from={from} narrow={false} preview={false}
          dialogId={`gallery-${id}`} sample onClose={nothing} onChoose={nothing} onBack={nothing} lesson={lesson} />
      </div>
    </Labeled>
  );
}

const similarItem = SIMILAR.items.find((item) => item.item_key === "similar_experience")!;
// View C opened from view B: the notice names the list it came from, so the drawer offers the way back.
const FROM_ITEM_LIST: Origin = {
  id: (noticePassage as unknown as EvidenceEvent).id, serial: null, sentence: null, marker: null, runId: null, top: null,
  list: { id: itemListId(SIMILAR.check_id, similarItem.item_key), count: similarItem.stated },
  highlight: (() => {
    const notice = similarItem.notices.find((entry) => (noticePassage as unknown as EvidenceEvent).id.endsWith(entry.passage_id));
    return notice ? [notice.requirement.start, notice.requirement.end] as [number, number] : null;
  })(),
};

// The parts' other states, each the works package's recorded run with one value changed.
const firstReason = WORKS_RUN.rejected.rows.find((row) => row.item_key === WORKS_RUN.rejected.groups[0].item_key)!;
const firstLesson = WORKS_RUN.lessons.groups[0]?.lessons[0];
// View F opened from the lesson card's marker: the paragraph with the lesson's words highlighted.
const FROM_LESSON: Origin = {
  id: (lessonParagraph as unknown as EvidenceEvent).id, serial: null, sentence: null, marker: null, runId: null, top: null,
  highlight: (firstLesson?.excerpt?.range as [number, number] | undefined) ?? null,
};
const RUN_NO_LESSONS: PackageRun = { ...WORKS_RUN, lessons: { state: "none", groups: [] } };
const RUN_AWAITING: PackageRun = {
  ...WORKS_RUN,
  lessons: { state: "ok", groups: WORKS_RUN.lessons.groups.map((group) => ({ ...group, lessons: group.lessons.map((lesson) => ({ ...lesson, ieg_status: "awaiting" })) })) },
};
const RUN_NO_NOTICES: PackageRun = {
  ...WORKS_RUN,
  rejected: { ...WORKS_RUN.rejected, state: "no_award_notices", counts: { ...WORKS_RUN.rejected.counts, m: 0, n: 0 }, groups: [], rows: [] },
};
const RUN_FRENCH: PackageRun = {
  ...WORKS_RUN,
  rejected: { ...WORKS_RUN.rejected, rows: WORKS_RUN.rejected.rows.map((row) => (row === firstReason ? { ...row, reason: { ...row.reason, lang: "fr" } } : row)) },
};
const RUN_REMOVED: PackageRun = {
  ...WORKS_RUN,
  rejected: { ...WORKS_RUN.rejected, rows: WORKS_RUN.rejected.rows.map((row) => (row === firstReason ? { ...row, removed: true } : row)) },
  removed: [{ index: 0, sentence: `"${firstReason.reason.quote}"`, reason: "quote_not_on_page", reasons: [], about: firstReason.evidence_id, source: "record_quote" }],
  checks: {
    ...WORKS_RUN.checks,
    sentences: { ...WORKS_RUN.checks.sentences, kept: WORKS_RUN.checks.sentences.kept - 1, removed: 1 },
    quotes: { ...WORKS_RUN.checks.quotes, found: WORKS_RUN.checks.quotes.found - 1 },
    ...(WORKS_RUN.checks.shown && {
      shown: {
        ...WORKS_RUN.checks.shown,
        quotes: { total: WORKS_RUN.checks.shown.quotes.total - 1, found: WORKS_RUN.checks.shown.quotes.found - 1 },
        proven: WORKS_RUN.checks.shown.proven - 1,
      },
    }),
  },
};
// A made-up comparison whose second item is one the works package's comparables had bids rejected over.
const YOURS: Comparison = {
  ...SIMILAR,
  items: SIMILAR.items.map((item) => (item.item_key === "similar_experience" ? item : {
    ...item, item_key: "key_staff", label: "Key staff", phrase: "key staff", reading: null,
    your_excerpt: { text: cs.yoursExcerpt, shortened: false },
    rejected_packages: WORKS_RUN.rejected.groups.find((group) => group.item_key === "key_staff")?.count ?? 0,
  })),
};
const NO_ESTIMATE: Cost = { ...WORKS_RUN.cost, package: { ...WORKS_RUN.cost.package, estimated_amount_usd: null } };
const PUBLIC_LIST = publicListEvent(CONSULTANT.signature, CONSULTANT.public, CONSULTANT.public_criteria_count);
const ITEM_LIST = itemListEvent(SIMILAR, similarItem);
const COST_RECORDS = costRecordEvent(WORKS_RUN.cost.rows[0]);

export function criteriaPage(): GalleryPage {
  const open = { open: true };
  return {
    slug: "check-criteria",
    current: "packages",
    sections: [
      {
        id: "collapsed",
        title: cs.collapsed,
        body: (
          <div className="flex flex-col gap-8">
            <Sample label={cs.collapsedPopulated} props={view({})} />
            <Sample label={cs.collapsedCompared} props={view({ summary: ready(COMPARED), comparison: compared(SIMILAR) })} />
            <Sample label={cs.collapsedNonePublic} props={view({ summary: ready(WORKS) })} />
            <Sample label={cs.collapsedNoComparables} props={view({ summary: ready({ ...WORKS, state: "no_comparables", comparables_total: 0 }) })} />
            <Sample label={cs.collapsedLoading} props={view({ summary: { status: "loading" } })} />
            <Sample label={cs.collapsedError} props={view({ summary: { status: "error", requestId: "4bf92f3577b34da6a3ce929d0e0e4736", onRetry: nothing } })} />
          </div>
        ),
      },
      {
        id: "open",
        title: cs.open,
        body: (
          <div className="flex flex-col gap-8">
            <Sample label={cs.running} props={view({ ...open, run: { status: "running", steps: [{ key: "notices", state: "done" }, { key: "reasons", state: "running" }] } })} />
            <Sample label={cs.worksOpen} props={view({ ...open, summary: ready(WORKS), run: ranRun(WORKS_RUN), checks: WORKS_RUN.checks })} />
            <Sample label={cs.consultantOpen} props={view({
              ...open, run: ranRun(CONSULTANT_RUN), comparison: compared(SIMILAR), text: PASTED, checks: SIMILAR.section_checks ?? SIMILAR.checks,
            })} />
          </div>
        ),
      },
      {
        id: "field",
        title: cs.field,
        body: (
          <div className="flex flex-col gap-8">
            <Sample label={cs.fieldEmpty} props={view({ ...open, run: ranRun(CONSULTANT_RUN), fieldError: "empty" })} />
            <Sample label={cs.fieldTooLong} props={view({
              ...open, run: ranRun(CONSULTANT_RUN), fieldError: "tooLong", text: PASTED.repeat(Math.ceil(20500 / PASTED.length)).slice(0, 20500),
            })} />
            <Sample label={cs.fieldComparing} props={view({
              ...open, run: ranRun(CONSULTANT_RUN), text: PASTED,
              comparison: { status: "running", steps: [{ key: "read", state: "done" }, { key: "find", state: "running" }], previous: SIMILAR },
            })} />
            <Sample label={cs.fieldEdited} props={view({ ...open, run: ranRun(CONSULTANT_RUN), comparison: compared(SIMILAR), text: `${PASTED}\n4.`, edited: true })} />
            <Sample label={cs.fieldSaveFailed} props={view({ ...open, run: ranRun(CONSULTANT_RUN), text: PASTED, saveFailed: true,
              comparison: { status: "error", code: "store", previous: null } })} />
            <Sample label={cs.fieldPreview} props={view({ ...open, run: ranRun(CONSULTANT_RUN), comparison: compared(SIMILAR), text: PASTED, preview: true })} />
          </div>
        ),
      },
      {
        id: "results",
        title: cs.refusals,
        body: (
          <div className="flex flex-col gap-8">
            <Sample label={cs.refusalLive} props={view({ ...open, run: ranRun(CONSULTANT_RUN), comparison: compared(LIVE) })} />
            <Sample label={cs.refusalPartial} props={view({ ...open, run: ranRun(CONSULTANT_RUN), comparison: compared(PARTIAL) })} />
            <Sample label={cs.noneFound} props={view({ ...open, run: ranRun(CONSULTANT_RUN), comparison: compared(NONE) })} />
            <Sample label={cs.compareError} props={view({ ...open, run: ranRun(CONSULTANT_RUN), text: PASTED,
              comparison: { status: "error", code: "agent_unavailable", requestId: "4bf92f3577b34da6a3ce929d0e0e4736", previous: null } })} />
            <Sample label={cs.readingRemoved} props={view({ ...open, run: ranRun(CONSULTANT_RUN), comparison: compared(SWAPPED), text: PASTED,
              checks: SWAPPED.section_checks ?? SWAPPED.checks })} />
            <Sample label={cs.stale} props={view({ ...open, run: ranRun(CONSULTANT_RUN), comparison: compared(SIMILAR, true) })} />
          </div>
        ),
      },
      {
        id: "parts",
        title: cs.parts,
        body: (
          <div className="flex flex-col gap-8">
            <Sample label={cs.runError} props={view({ ...open, summary: ready(WORKS), run: { status: "error", code: "data_service", requestId: "4bf92f3577b34da6a3ce929d0e0e4736" }, onRetryRun: nothing })} />
            <Sample label={cs.lessonsNone} props={view({ ...open, summary: ready(WORKS), run: ranRun(RUN_NO_LESSONS) })} />
            {firstLesson && <Sample label={cs.lessonAwaiting} props={view({ ...open, summary: ready(WORKS), run: ranRun(RUN_AWAITING) })} />}
            <Sample label={cs.rejectedNoNotices} props={view({ ...open, summary: ready(WORKS), run: ranRun(RUN_NO_NOTICES) })} />
            <Sample label={cs.rejectedYours} props={view({ ...open, run: ranRun(WORKS_RUN), comparison: compared(YOURS), text: PASTED })} />
            <Sample label={cs.rejectedLanguage} props={view({ ...open, summary: ready(WORKS), run: ranRun(RUN_FRENCH) })} />
            <Sample label={cs.removedRow} props={view({ ...open, summary: ready(WORKS), run: ranRun(RUN_REMOVED), checks: RUN_REMOVED.checks })} />
          </div>
        ),
      },
      {
        id: "cost",
        title: cs.cost,
        body: (
          <div className="flex flex-col gap-8">
            <Labeled label={cs.costAbstain}>
              <Column>
                <CostEstimate cost={WORKS_RUN.cost} readinessHref={dataReadinessHref([], "compare_cost_estimates")} />
              </Column>
            </Labeled>
            <Labeled label={cs.costRanged}>
              <Column>
                <CostEstimate cost={RANGED} readinessHref={dataReadinessHref([], "compare_cost_estimates")} />
              </Column>
            </Labeled>
            <Labeled label={cs.costNone}>
              <Column>
                <CostEstimate cost={CONSULTANT_RUN.cost} readinessHref={dataReadinessHref([], "compare_cost_estimates")} />
              </Column>
            </Labeled>
            <Labeled label={cs.costNoEstimate}>
              <Column>
                <CostEstimate cost={NO_ESTIMATE} readinessHref={dataReadinessHref([], "compare_cost_estimates")} />
              </Column>
            </Labeled>
            <Labeled label={cs.costQuantile}>
              <Column>
                <div data-cost-sample="quantile">
                  <CostEstimate cost={quantileCost as unknown as Cost} readinessHref={dataReadinessHref([], "compare_cost_estimates")} />
                </div>
              </Column>
            </Labeled>
          </div>
        ),
      },
      {
        id: "drawer",
        title: cs.drawer,
        body: (
          <div className="flex flex-col gap-8">
            <Drawer label={cs.drawerPublic} evidence={PUBLIC_LIST} />
            <Drawer label={cs.drawerItem} evidence={ITEM_LIST} />
            <Drawer label={cs.drawerNotice} evidence={noticePassage as unknown as EvidenceEvent} from={FROM_ITEM_LIST} />
            <Drawer label={cs.drawerCost} evidence={COST_RECORDS} />
            <Drawer label={cs.drawerAward} evidence={awardNotice as unknown as EvidenceEvent} />
            <Drawer label={cs.drawerLesson} evidence={lessonParagraph as unknown as EvidenceEvent} from={FROM_LESSON} lesson={firstLesson ?? null} />
          </div>
        ),
      },
    ],
  };
}
