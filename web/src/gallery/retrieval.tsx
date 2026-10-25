// The gallery's retrieval loop page (ticket 32): the evidence drawer's feedback row in each of its states, toggle
// buttons and key hints, and the Passage reports and Judging parts, from the answers the server wrote on the
// fixture (tests/record_retrieval_api.py). A state no recording holds is a recording with one value changed. Hover
// and keyboard focus, and the pages themselves, are captured from the app (web/capture/shots.ts).
import paragraph54 from "../../../tests/fixtures/api/evidence-icr-p130164-54.json";
import mineWaiting from "../../../tests/fixtures/api/feedback-mine-waiting.json";
import mineRankedLower from "../../../tests/fixtures/api/feedback-mine-ranked-lower.json";
import mineKept from "../../../tests/fixtures/api/feedback-mine-kept.json";
import mineByAgreement from "../../../tests/fixtures/api/feedback-mine-by-agreement.json";
import reportsQueue from "../../../tests/fixtures/api/passage-reports.json";
import reportsOwn from "../../../tests/fixtures/api/passage-reports-own-report.json";
import reportsAudit from "../../../tests/fixtures/api/passage-reports-audit.json";
import reportsEmpty from "../../../tests/fixtures/api/passage-reports-empty.json";
import reportOne from "../../../tests/fixtures/api/passage-report.json";
import reportOwn from "../../../tests/fixtures/api/passage-report-own-report.json";
import reportAudit from "../../../tests/fixtures/api/passage-report-audit.json";
import reportSaved from "../../../tests/fixtures/api/passage-report-saved.json";
import reportStale from "../../../tests/fixtures/api/passage-report-stale.json";
import reportDecided from "../../../tests/fixtures/api/passage-report-decided.json";
import judgingList from "../../../tests/fixtures/api/judging-queries.json";
import judgingStart from "../../../tests/fixtures/api/judging-queries-start.json";
import judgingBoth from "../../../tests/fixtures/api/judging-queries-both.json";
import judgingQuery from "../../../tests/fixtures/api/judging-query-progress.json";
import judgingLocked from "../../../tests/fixtures/api/judging-query-locked.json";
import { useId, useState, type ReactNode } from "react";
import type { RowStart } from "../components/FeedbackRow";
import { EvidenceDrawerView } from "../components/EvidenceDrawer";
import { GradeBar, PassageMap, ProgressMeter } from "../components/Judging";
import { Fill } from "../components/Fill";
import { Num } from "../components/Num";
import { SegmentedControl } from "../components/SegmentedControl";
import { ToggleButton } from "../components/ToggleButton";
import { copy } from "../copy";
import type { EvidenceEvent } from "../lib/answer";
import type { Feedback, JudgingList, JudgingQuery, MyReport, ReportGroup, ReportsQueue } from "../lib/retrieval";
import { JudgingBody, JudgingDesk, JudgingQuerySkeleton, JudgingSkeleton } from "../pages/JudgingPages";
import { ReportGroupSkeleton, ReportGroupView, ReportsBody, ReportsSkeleton } from "../pages/PassageReportsPages";
import { galleryCopy } from "./copy";
import type { GalleryPage } from "./pages";

const t = galleryCopy.retrievalSections;
const s = galleryCopy.retrievalStates;
const nothing = () => undefined;
const REASON = (mineWaiting as { my_report: MyReport }).my_report.reason ?? "";
const FEEDBACK: Feedback = { allowed: true, why_not: null, run_id: "run-0001", mode: "pilot", my_report: null };
const PASSAGE = { ...(paragraph54 as unknown as EvidenceEvent), tool: "search_passages", feedback: FEEDBACK };
const report = (body: unknown) => (body as { my_report: MyReport }).my_report;

// The evidence drawer as it opens beside the page, with its feedback row in one state.
function DrawerSample({ start, feedback = FEEDBACK, preview = false }: { start: RowStart; feedback?: Feedback; preview?: boolean }) {
  const dialogId = useId();
  return (
    <div className="max-w-[37.5rem] overflow-hidden rounded-md border border-line">
      <EvidenceDrawerView
        id={PASSAGE.id}
        data={{ status: "ready", evidence: { ...PASSAGE, feedback } }}
        run={null}
        from={null}
        narrow={false}
        preview={preview}
        dialogId={dialogId}
        sample
        onClose={nothing}
        onChoose={nothing}
        feedbackStart={start}
      />
    </div>
  );
}

function Labeled({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-2">
      <p className="text-caption text-ink-muted">{label}</p>
      {children}
    </div>
  );
}

function Column({ children }: { children: ReactNode }) {
  return <div className="flex max-w-[46.5rem] flex-col gap-8">{children}</div>;
}

export function retrievalPage(): GalleryPage {
  const long = REASON.repeat(6).slice(0, 410);
  return {
    slug: "retrieval",
    current: "lessons",
    sections: [
      {
        id: "feedback-row",
        title: t.feedbackRow,
        body: (
          <Column>
            <Labeled label={s.idle}>
              <DrawerSample start={{}} />
            </Labeled>
            <Labeled label={s.chosen}>
              <DrawerSample start={{ chosen: "wrong_passage", text: "" }} />
            </Labeled>
            <Labeled label={s.switched}>
              <DrawerSample start={{ chosen: "not_useful", text: REASON }} />
            </Labeled>
            <Labeled label={s.counter}>
              <DrawerSample start={{ chosen: "wrong_passage", text: long }} />
            </Labeled>
            <Labeled label={s.sending}>
              <DrawerSample start={{ chosen: "wrong_passage", text: REASON, sending: true }} />
            </Labeled>
            <Labeled label={s.failed}>
              <DrawerSample start={{ chosen: "wrong_passage", text: REASON, failed: true }} />
            </Labeled>
            <Labeled label={s.sentWithReason}>
              <DrawerSample start={{ report: report(mineWaiting), fresh: true }} />
            </Labeled>
            <Labeled label={s.sentWithout}>
              <DrawerSample start={{ report: { ...report(mineWaiting), reason: null }, fresh: true }} />
            </Labeled>
            <Labeled label={s.withdrawFailed}>
              <DrawerSample start={{ report: report(mineWaiting), fresh: true, withdrawFailed: "failed" }} />
            </Labeled>
            <Labeled label={s.preview}>
              <DrawerSample start={{}} feedback={{ ...FEEDBACK, allowed: false, why_not: "preview" }} preview />
            </Labeled>
          </Column>
        ),
      },
      {
        id: "feedback-later",
        title: t.feedbackLater,
        body: (
          <Column>
            <Labeled label={s.waiting}>
              <DrawerSample start={{ report: report(mineWaiting) }} />
            </Labeled>
            <Labeled label={s.rankedLower}>
              <DrawerSample start={{ report: report(mineRankedLower) }} />
            </Labeled>
            <Labeled label={s.byAgreement}>
              <DrawerSample start={{ report: report(mineByAgreement) }} feedback={{ ...FEEDBACK, mode: "scale" }} />
            </Labeled>
            <Labeled label={s.kept}>
              <DrawerSample start={{ report: report(mineKept) }} />
            </Labeled>
          </Column>
        ),
      },
      {
        id: "toggles",
        title: t.toggles,
        body: (
          <Column>
            <Labeled label={s.ghostToggles}>
              <div className="flex flex-wrap gap-2">
                <ToggleButton pressed={false}>{copy.feedback.kind.wrong_passage}</ToggleButton>
                <ToggleButton pressed>{copy.feedback.kind.wrong_passage}</ToggleButton>
                <ToggleButton pressed={false} disabled aria-label={copy.feedback.kind.not_useful}>
                  {copy.feedback.kind.not_useful}
                </ToggleButton>
              </div>
            </Labeled>
            <Labeled label={s.secondaryToggles}>
              <div className="flex flex-wrap gap-3">
                {(["answers", "partly", "not_relevant"] as const).map((grade, index) => (
                  <ToggleButton key={grade} variant="secondary" pressed={index === 1} hint={copy.judging.keys[grade]} aria-keyshortcuts={copy.judging.keys[grade]}>
                    {copy.judging.grades[grade]}
                  </ToggleButton>
                ))}
              </div>
            </Labeled>
          </Column>
        ),
      },
    ],
  };
}

// ── Passage reports and judging ──────────────────────────────────────────

const QUEUE = reportsQueue as unknown as ReportsQueue;
const group = (body: unknown) => body as unknown as ReportGroup;
const refused = (body: unknown) => (body as { body: { values: { name: string; time: string }; item: ReportGroup } }).body;
const LIST = judgingList as unknown as JudgingList;
const QUERY = judgingQuery as unknown as JudgingQuery;
const LOCKED = judgingLocked as unknown as JudgingQuery;

function SegmentedSample() {
  const [value, setValue] = useState<string>(LIST.show);
  return (
    <SegmentedControl
      label={copy.judging.show}
      value={value}
      onChange={setValue}
      choices={(["to_judge", "finished_by_you", "finished_by_both"] as const).map((key) => ({ key, label: copy.judging.filters[key].replace("{count}", String(LIST.counts[key])) }))}
    />
  );
}

function Meter({ part, whole }: { part: number; whole: number }) {
  return (
    <ProgressMeter part={part} whole={whole}>
      <Fill template={copy.judging.meter} slots={{ graded: <Num value={part} options={{ compact: false }} />, pool: <Num value={whole} options={{ compact: false }} /> }} />
    </ProgressMeter>
  );
}

export function judgingPage(): GalleryPage {
  const stale = refused(reportStale);
  const graded = Array.from({ length: 12 }, (_, index) => index < 5);
  return {
    slug: "judging",
    current: "lessons",
    sections: [
      {
        id: "queue",
        title: t.queue,
        body: (
          <Column>
            <Labeled label={s.queueBoth}>
              <ReportsBody queue={QUEUE} />
            </Labeled>
            <Labeled label={s.queueOwn}>
              <ReportsBody queue={reportsOwn as unknown as ReportsQueue} />
            </Labeled>
            <Labeled label={s.queueAudit}>
              <ReportsBody queue={reportsAudit as unknown as ReportsQueue} />
            </Labeled>
            <Labeled label={s.queueEmpty}>
              <ReportsBody queue={reportsEmpty as unknown as ReportsQueue} />
            </Labeled>
            <Labeled label={s.queueLoading}>
              <ReportsSkeleton />
            </Labeled>
          </Column>
        ),
      },
      {
        id: "report",
        title: t.report,
        body: (
          <Column>
            <Labeled label={s.reportWaiting}>
              <ReportGroupView sample group={group(reportOne)} />
            </Labeled>
            <Labeled label={s.reportNoReason}>
              <ReportGroupView sample group={group(reportOne)} initial={{ form: { error: true } }} />
            </Labeled>
            <Labeled label={s.reportOwn}>
              <ReportGroupView sample group={group(reportOwn)} />
            </Labeled>
            <Labeled label={s.reportAudit}>
              <ReportGroupView sample group={group(reportAudit)} />
            </Labeled>
            <Labeled label={s.reportSaved}>
              <ReportGroupView sample group={(reportSaved as unknown as { item: ReportGroup }).item} initial={{ saved: reportSaved as never }} />
            </Labeled>
            <Labeled label={s.reportStale}>
              <ReportGroupView sample group={stale.item} initial={{ gaveWay: { kind: "stale", name: stale.values.name, time: stale.values.time, reason: s.staleReason } }} />
            </Labeled>
            <Labeled label={s.reportLoading}>
              <ReportGroupSkeleton />
            </Labeled>
          </Column>
        ),
      },
      {
        id: "decided",
        title: t.decided,
        body: (
          <Column>
            <Labeled label={s.reportDecided}>
              <ReportGroupView sample group={group(reportDecided)} />
            </Labeled>
            <Labeled label={s.reportReopen}>
              <ReportGroupView sample group={group(reportDecided)} initial={{ reopenOpen: true }} />
            </Labeled>
            <Labeled label={s.reportReopenFailed}>
              <ReportGroupView sample group={group(reportDecided)} initial={{ reopenFailed: true }} />
            </Labeled>
          </Column>
        ),
      },
      {
        id: "judging-list",
        title: t.judgingList,
        body: (
          <Column>
            <Labeled label={s.judgingList}>
              <JudgingBody list={LIST} onShow={() => undefined} />
            </Labeled>
            <Labeled label={s.judgingStart}>
              <JudgingBody list={judgingStart as unknown as JudgingList} onShow={() => undefined} />
            </Labeled>
            <Labeled label={s.judgingBoth}>
              <JudgingBody list={judgingBoth as unknown as JudgingList} onShow={() => undefined} />
            </Labeled>
            <Labeled label={s.judgingLoading}>
              <JudgingSkeleton />
            </Labeled>
            <Labeled label={s.judgingBusy}>
              <JudgingBody list={LIST} busy onShow={() => undefined} />
            </Labeled>
          </Column>
        ),
      },
      {
        id: "judging",
        title: t.judging,
        body: (
          <Column>
            <Labeled label={s.segmented}>
              <SegmentedSample />
            </Labeled>
            <Labeled label={s.meterEmpty}>
              <div className="flex flex-col gap-3">
                <Meter part={0} whole={40} />
                <Meter part={12} whole={40} />
                <Meter part={40} whole={40} />
              </div>
            </Labeled>
            <Labeled label={s.map}>
              <PassageMap open onToggle={nothing} count={graded.length} current={6} graded={graded} href={(n) => `#passage-${n}`} onChoose={nothing} />
            </Labeled>
            <Labeled label={s.gradeReady}>
              <GradeBar sample n={6} chosen={null} locked={false} onGrade={nothing} />
            </Labeled>
            <Labeled label={s.gradePressed}>
              <GradeBar sample n={2} chosen="partly" locked={false} onGrade={nothing} />
            </Labeled>
            <Labeled label={s.gradeLocked}>
              <GradeBar sample n={1} chosen={null} locked mine="partly" theirs="not_relevant" onGrade={nothing} />
            </Labeled>
            <Labeled label={s.desk}>
              <JudgingDesk sample query={QUERY} />
            </Labeled>
            <Labeled label={s.deskFailed}>
              <JudgingDesk sample query={QUERY} initial={{ failed: 3, at: 4 }} />
            </Labeled>
            <Labeled label={s.deskLocked}>
              <JudgingDesk sample query={LOCKED} initial={{ at: 1 }} />
            </Labeled>
            <Labeled label={s.deskLockedWhileOpen}>
              <JudgingDesk sample query={LOCKED} initial={{ at: 1, lockedWhileOpen: true }} />
            </Labeled>
            <Labeled label={s.deskLoading}>
              <JudgingQuerySkeleton sample />
            </Labeled>
          </Column>
        ),
      },
    ],
  };
}
