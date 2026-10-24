// The gallery's Lessons page (ticket 29): every new Lessons component in each of its states, from the answers
// the server wrote on the fixture (tests/record_lessons_api.py), so each sample is a real lesson with the
// server's own values. A state no recording holds is a recording with one value changed. Hover and keyboard
// focus are captured from the app (web/capture/shots.ts, the lessons-- shots).
import library from "../../../tests/fixtures/api/lessons-library-reviewer.json";
import rechecking from "../../../tests/fixtures/api/lessons-library-rechecking.json";
import queue from "../../../tests/fixtures/api/lessons-queue.json";
import queueSamePerson from "../../../tests/fixtures/api/lessons-queue-same-person.json";
import queueOwn from "../../../tests/fixtures/api/lessons-queue-own-project.json";
import queueOverdue from "../../../tests/fixtures/api/lessons-queue-overdue.json";
import queueCross from "../../../tests/fixtures/api/lessons-queue-cross-check.json";
import recommendRepeats from "../../../tests/fixtures/api/lessons-item-recommend-repeats.json";
import decide from "../../../tests/fixtures/api/lessons-item-decide.json";
import recheckRecommend from "../../../tests/fixtures/api/lessons-item-recheck-recommend.json";
import recheckDecide from "../../../tests/fixtures/api/lessons-item-recheck-decide.json";
import crossCheck from "../../../tests/fixtures/api/lessons-item-cross-check.json";
import decidedMerged from "../../../tests/fixtures/api/lessons-item-decided-merged.json";
import decidedKept from "../../../tests/fixtures/api/lessons-item-decided-kept.json";
import meReviewer from "../../../tests/fixtures/api/lessons-me-reviewer.json";
import { useId, type ReactNode } from "react";
import { DecisionForm, LessonEditor, ReasonField, currentChange, validChange } from "../components/DecisionForm";
import { EvidenceCard } from "../components/EvidenceCard";
import { EvidenceDrawerView } from "../components/EvidenceDrawer";
import { LessonCard } from "../components/LessonCard";
import { EvidenceBadge, SourceChip, Tag } from "../components/LessonParts";
import { Pagination } from "../components/Pagination";
import { HistoryList, OutcomePanel, QueueRow } from "../components/LessonReview";
import { StatusBadge } from "../components/StatusBadge";
import { copy } from "../copy";
import type { EvidenceEvent } from "../lib/answer";
import type { Library, Me, Queue, ReviewItem } from "../lib/lessons";
import { LibrarySkeleton, QueueSkeleton } from "../pages/LessonsPages";
import { EvidenceCardFull, ReviewSkeleton } from "../pages/ReviewPage";
import { galleryCopy } from "./copy";
import type { GalleryPage } from "./pages";

const t = galleryCopy.lessonSections;
const ls = galleryCopy.lessonStates;
const o = copy.lessons.outcome;
const LIBRARY = library as unknown as Library;
const RECHECKING = rechecking as unknown as Library;
const QUEUE = queue as unknown as Queue;
const item = (body: unknown) => body as unknown as ReviewItem;
const DECIDE = item(decide);
const card = LIBRARY.lessons[1];
const manySources = {
  ...card,
  evidence: [
    ...card.evidence,
    ...Array.from({ length: 6 }, (_, n) => ({ ...card.evidence[0], evidence_id: `${card.evidence[0].evidence_id}-${n}`, locator: { kind: "paragraph" as const, text: String(60 + n) } })),
  ],
};
const nothing = () => undefined;
const lists = DECIDE.lists;
// The library lesson the lesson review writer cites under "This may repeat a lesson in the library".
const REPEATS = item(recommendRepeats);
const LESSON_SOURCE = Object.values(REPEATS.summary.evidence ?? {}).find((evidence: EvidenceEvent) => evidence.kind === "record") as EvidenceEvent;

// The evidence drawer as it opens beside the page, from a sample's frame.
function DrawerSample({ evidence }: { evidence: EvidenceEvent }) {
  const dialogId = useId();
  return (
    <div className="max-w-[37.5rem] overflow-hidden rounded-md border border-line">
      <EvidenceDrawerView
        id={evidence.id}
        data={{ status: "ready", evidence }}
        run={null}
        from={null}
        narrow={false}
        preview={false}
        dialogId={dialogId}
        sample
        onClose={nothing}
        onChoose={nothing}
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

// A sample as wide as the Lessons column at 1440 px.
function Column({ children }: { children: ReactNode }) {
  return <div className="flex max-w-[46.5rem] flex-col gap-8">{children}</div>;
}

const firstRow = (rows: unknown) => (rows as Queue).groups;

export function lessonsPage(): GalleryPage {
  const own = firstRow(queueOwn).others[0];
  const samePerson = firstRow(queueSamePerson).others[0];
  const overdue = firstRow(queueOverdue).others[0];
  const cross = firstRow(queueCross).you[0];
  const evidence = DECIDE.evidence;
  const invalid = { ...currentChange(DECIDE), statement: "", risk_factors: [] };
  return {
    slug: "lessons",
    current: "lessons",
    sections: [
      {
        id: "badges",
        title: t.badges,
        body: (
          <div className="flex flex-wrap gap-3">
            <EvidenceBadge status="restated" />
            <EvidenceBadge status="ieg_lesson" />
            <EvidenceBadge status="awaiting" />
            <EvidenceBadge status="not_restated" />
            <StatusBadge kind="may-repeat" />
            <StatusBadge kind="rechecking" />
            <StatusBadge kind="overdue" />
          </div>
        ),
      },
      {
        id: "chips",
        title: t.chips,
        body: (
          <div className="flex flex-col gap-4">
            <Labeled label={ls.tag}>
              <div className="flex flex-wrap gap-2">
                {card.risk_factors.map((factor) => (
                  <Tag key={factor.key}>{factor.label}</Tag>
                ))}
                {card.sector && <Tag>{card.sector}</Tag>}
              </div>
            </Labeled>
            <Labeled label={ls.chipDefault}>
              <div>
                <SourceChip evidence={card.evidence[0]} />
              </div>
            </Labeled>
            <Labeled label={ls.chipActive}>
              <div>
                <SourceChip evidence={card.evidence[0]} active />
              </div>
            </Labeled>
            <Labeled label={ls.chipVisited}>
              <div>
                <SourceChip evidence={card.evidence[1]} visited />
              </div>
            </Labeled>
          </div>
        ),
      },
      {
        id: "card",
        title: t.card,
        body: (
          <Column>
            <Labeled label={ls.card}>
              <LessonCard card={card} canRecheck reasonMax={LIBRARY.limits.reason_max_chars} />
            </Labeled>
            <Labeled label={ls.rechecking}>
              <LessonCard card={RECHECKING.lessons[1]} canRecheck reasonMax={RECHECKING.limits.reason_max_chars} />
            </Labeled>
            <Labeled label={ls.manySources}>
              <LessonCard card={manySources} />
            </Labeled>
            <Labeled label={ls.viewer}>
              <LessonCard card={LIBRARY.lessons[0]} />
            </Labeled>
          </Column>
        ),
      },
      {
        id: "compact",
        title: t.compact,
        body: (
          <Column>
            <LessonCard card={item(recommendRepeats).repeats[0]} level={3} compact />
          </Column>
        ),
      },
      {
        id: "rows",
        title: t.rows,
        body: (
          <Column>
            {[
              [ls.rowYou, QUEUE.groups.you[0]],
              [ls.rowDecision, samePerson],
              [ls.rowOwn, own],
              [ls.rowOverdue, overdue],
              [ls.rowCrossCheck, cross],
            ].map(([label, row]) => (
              <Labeled key={label as string} label={label as string}>
                <ul>
                  <QueueRow row={row as Queue["groups"]["you"][number]} />
                </ul>
              </Labeled>
            ))}
          </Column>
        ),
      },
      {
        id: "evidence",
        title: t.evidence,
        body: (
          <Column>
            <Labeled label={ls.evidenceIcr}>
              <EvidenceCardFull evidence={evidence[0]} n={1} open={false} visited={false} />
            </Labeled>
            <Labeled label={ls.evidenceRestated}>
              <EvidenceCardFull evidence={evidence[1]} n={2} open={false} visited />
            </Labeled>
          </Column>
        ),
      },
      {
        id: "reason",
        title: t.reason,
        body: (
          <Column>
            <Labeled label={ls.reasonEmpty}>
              <ReasonField label={copy.lessons.form.reasonLabel} helper={copy.lessons.form.reasonHelperRecommend} value="" max={500} />
            </Labeled>
            <Labeled label={ls.reasonCounter}>
              <ReasonField label={copy.lessons.form.reasonLabel} helper={copy.lessons.form.reasonHelperDecide} value={DECIDE.history.map((event) => event.reason ?? "").join(" ").repeat(4).slice(0, 430)} max={500} />
            </Labeled>
            <Labeled label={ls.reasonInvalid}>
              <ReasonField label={copy.lessons.form.reasonLabel} helper={copy.lessons.form.reasonHelperRecommend} value="" max={500} error={copy.lessons.form.errors.noReasonRecommend} />
            </Labeled>
            <Labeled label={ls.reasonDisabled}>
              <ReasonField label={copy.lessons.form.reasonLabel} value={DECIDE.history.at(-1)?.reason ?? ""} max={500} disabled />
            </Labeled>
          </Column>
        ),
      },
      {
        id: "editor",
        title: t.editor,
        body: (
          <Column>
            <Labeled label={ls.editor}>
              <LessonEditor value={currentChange(DECIDE)} onChange={nothing} lists={lists} max={80} errors={{}} />
            </Labeled>
            <Labeled label={ls.editorInvalid}>
              <LessonEditor value={invalid} onChange={nothing} lists={lists} max={80} errors={validChange(invalid, 80)} />
            </Labeled>
          </Column>
        ),
      },
      {
        id: "forms",
        title: t.forms,
        body: (
          <Column>
            <Labeled label={ls.formRecommend}>
              <DecisionForm item={item(recommendRepeats)} onDone={nothing} onGaveWay={nothing} />
            </Labeled>
            <Labeled label={ls.formDecide}>
              <DecisionForm item={DECIDE} onDone={nothing} onGaveWay={nothing} initial={{ editor: true }} />
            </Labeled>
            <Labeled label={ls.formRecheckRecommend}>
              <DecisionForm item={item(recheckRecommend)} onDone={nothing} onGaveWay={nothing} initial={{ choiceKey: "change" }} />
            </Labeled>
            <Labeled label={ls.formRecheckDecide}>
              <DecisionForm item={item(recheckDecide)} onDone={nothing} onGaveWay={nothing} initial={{ choiceKey: "keep" }} />
            </Labeled>
            <Labeled label={ls.formCrossCheck}>
              <DecisionForm item={item(crossCheck)} onDone={nothing} onGaveWay={nothing} />
            </Labeled>
          </Column>
        ),
      },
      {
        id: "form-states",
        title: t.formStates,
        body: (
          <Column>
            <Labeled label={ls.formErrors}>
              <DecisionForm item={item(recommendRepeats)} onDone={nothing} onGaveWay={nothing} initial={{ errors: true }} />
            </Labeled>
            <Labeled label={ls.formSaving}>
              <DecisionForm item={DECIDE} onDone={nothing} onGaveWay={nothing} initial={{ savingKey: "add", reason: DECIDE.recommendation?.reason ?? "" }} />
            </Labeled>
            <Labeled label={ls.formFailed}>
              <DecisionForm item={DECIDE} onDone={nothing} onGaveWay={nothing} initial={{ failed: true, reason: DECIDE.recommendation?.reason ?? "" }} />
            </Labeled>
          </Column>
        ),
      },
      {
        id: "outcomes",
        title: t.outcomes,
        body: (
          <Column>
            <Labeled label={ls.outcomeSuccess}>
              <OutcomePanel state="success" lead={o.added.lead} body={o.added.body} links={[{ href: "/lessons", text: copy.lessons.form.seeInLibrary }, { href: "/lessons/review", text: copy.lessons.form.backToQueue }]} />
            </Labeled>
            <Labeled label={ls.outcomeInfo}>
              <OutcomePanel state="info" lead={o.recommendedReject.lead} body={o.rejected.body} links={[{ href: "/lessons/review", text: copy.lessons.form.nextItem }]} />
            </Labeled>
            <Labeled label={ls.outcomeNeutral}>
              <OutcomePanel state="neutral" lead={o.rejected.lead} body={o.rejected.body} />
            </Labeled>
          </Column>
        ),
      },
      {
        id: "history",
        title: t.history,
        body: (
          <Column>
            <Labeled label={ls.history}>
              <HistoryList events={item(decidedMerged).history} lists={lists} headingId="gallery-history" />
            </Labeled>
            <Labeled label={ls.historyKept}>
              <HistoryList events={item(decidedKept).history} lists={lists} headingId="gallery-history-kept" />
            </Labeled>
          </Column>
        ),
      },
      {
        id: "pagination",
        title: t.pagination,
        body: (
          <Column>
            <Labeled label={ls.paginationMiddle}>
              <Pagination page={2} pages={3} href={(n) => `/lessons?page=${n}`} />
            </Labeled>
            <Labeled label={ls.paginationFirst}>
              <Pagination page={1} pages={3} href={(n) => `/lessons?page=${n}`} />
            </Labeled>
          </Column>
        ),
      },
      {
        id: "lesson-source",
        title: t.lessonSource,
        body: (
          <Column>
            <Labeled label={ls.lessonCard}>
              <div className="max-w-[22rem] rounded-md border border-line bg-surface p-3">
                <EvidenceCard evidence={LESSON_SOURCE} n={2} sentence={null} />
              </div>
            </Labeled>
            <Labeled label={ls.lessonDrawer}>
              <DrawerSample evidence={LESSON_SOURCE} />
            </Labeled>
          </Column>
        ),
      },
      {
        id: "skeletons",
        title: t.skeletons,
        body: (
          <Column>
            <Labeled label={ls.skeletonLibrary}>
              <LibrarySkeleton />
            </Labeled>
            <Labeled label={ls.skeletonQueue}>
              <QueueSkeleton me={meReviewer as unknown as Me} />
            </Labeled>
            <Labeled label={ls.skeletonReview}>
              <ReviewSkeleton />
            </Labeled>
          </Column>
        ),
      },
    ],
  };
}
