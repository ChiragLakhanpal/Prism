// The gallery's timeline page (ticket 23): a project's Timeline tab in each of its states, the disagreement card
// with its keep action, the source tag, the reason field and the drawer's views a timeline mark opens. Each sample
// is an answer the server wrote on the fixture (tests/record_timeline_api.py), or one with a value changed, so its
// words and dates are a real project's. The tab's loading and error states, and the card under an answer, are also
// captured from the production build (web/capture/shots.ts).
import contracts2019 from "../../../tests/fixtures/api/evidence-contracts-p156634-2019.json";
import pdoRow from "../../../tests/fixtures/api/evidence-disagreement-p130164-pdo.json";
import reviewDoc from "../../../tests/fixtures/api/evidence-doc-p130164-icr-review-2020.json";
import isr7Doc from "../../../tests/fixtures/api/evidence-doc-p130164-isr-7.json";
import ratings19 from "../../../tests/fixtures/api/evidence-ratings-p130164-1-9.json";
import asOf from "../../../tests/fixtures/api/timeline-p130164-2016-08-26.json";
import asOfLate from "../../../tests/fixtures/api/timeline-p130164-2024-01-01.json";
import failed from "../../../tests/fixtures/api/timeline-p130164-failed.json";
import p130164 from "../../../tests/fixtures/api/timeline-p130164.json";
import p156634Public from "../../../tests/fixtures/api/timeline-p156634-public.json";
import p156634 from "../../../tests/fixtures/api/timeline-p156634.json";
import { useId, useState, type ReactNode } from "react";
import { EmptyState } from "../components/Card";
import { DisagreementCard, type KeepState } from "../components/DisagreementCard";
import { EvidenceDrawerView } from "../components/EvidenceDrawer";
import { SourceTag } from "../components/SourceTag";
import { cardFromRow } from "../components/TimelineDrawer";
import { copy } from "../copy";
import type { EvidenceEvent } from "../lib/answer";
import { sideShort, type SideData } from "../lib/disagreement";
import type { Item, Timeline } from "../lib/timeline";
import { TimelineCard, TimelineLoading } from "../pages/project/TimelineTab";
import { galleryCopy } from "./copy";
import type { GalleryPage } from "./pages";

const s = galleryCopy.timelineStates;
const nothing = () => undefined;
const SHOWCASE = p130164 as unknown as Timeline;
const PDO = pdoRow as unknown as EvidenceEvent;
// The two reports' short names, from the recorded sides: "ISR 7" and "ICR paragraph 78".
const [ISR_7, ICR_78] = (PDO.row.sides as SideData[]).map(sideShort);

// The showcase as the server answers when get_disagreements does not (tests/record_timeline_api.py, FAILED): no
// dashed lines and no bands, and the newest ISR as the How lane's one ISR mark.
const FAILED = failed as unknown as Timeline;
// The showcase with no records and no ratings: the What lane's caption and the band row's.
const SPARSE: Timeline = {
  ...SHOWCASE,
  items: SHOWCASE.items.filter((item) => item.kind !== "record" && item.kind !== "band"),
};

function Labeled({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-2">
      <p className="text-caption text-ink-muted">{label}</p>
      {children}
    </div>
  );
}

function Card({ data, wide = true }: { data: Timeline; wide?: boolean }) {
  const [open, setOpen] = useState<string | null>(null);
  return <TimelineCard data={data} wide={wide} openId={open} states={{}} onOpen={(item: Item) => setOpen(item.evidence_id)} />;
}

function Drawer({ evidence }: { evidence: EvidenceEvent }) {
  const dialogId = useId();
  return (
    <div className="max-w-[37.5rem] overflow-hidden rounded-md border border-line">
      <EvidenceDrawerView id={evidence.id} data={{ status: "ready", evidence }} run={null} from={null} narrow={false} preview={false} dialogId={dialogId} sample onClose={nothing} onChoose={nothing} />
    </div>
  );
}

// The showcase's card as a sample: on the timeline (no keep target), or under an answer whose sentence it changes.
function CardSample({
  answer = false,
  state = null,
  reason = "",
  preview = false,
  backFailed = false,
}: {
  answer?: boolean;
  state?: KeepState | null;
  reason?: string;
  preview?: boolean;
  backFailed?: boolean;
}) {
  const { sides, props } = cardFromRow(PDO.row, nothing);
  const keep = props.keep && answer ? { ...props.keep, target: { disagreementId: PDO.row.disagreement_id, runId: "run-0001", draftId: null, preview } } : props.keep;
  return (
    <div className="max-w-[46.5rem]">
      <DisagreementCard
        warning={answer}
        level={4}
        sides={sides}
        {...props}
        name={answer ? copy.disagreement.groupName(copy.badge.twoReportsDisagree, ISR_7, ICR_78) : props.name}
        changes={answer ? copy.disagreement.card.changesAnswer(1).replace("{n}", copy.num.words[0]) : undefined}
        keep={keep}
        initialKept={state}
        initialReason={reason}
        initialBackFailed={backFailed}
        sample
      />
    </div>
  );
}

export function timelinePage(): GalleryPage {
  return {
    slug: "timeline",
    current: "projects",
    sections: [
      { id: "chart", title: s.chart, body: <Card data={SHOWCASE} /> },
      { id: "as-of", title: s.asOf, body: <Card data={asOf as unknown as Timeline} /> },
      { id: "as-of-late", title: s.asOfLate, body: <Card data={asOfLate as unknown as Timeline} /> },
      { id: "crowded", title: s.crowded, body: <Card data={p156634 as unknown as Timeline} /> },
      { id: "hidden", title: s.hidden, body: <Card data={p156634Public as unknown as Timeline} /> },
      { id: "failed", title: s.failed, body: <Card data={FAILED} /> },
      { id: "lane-empty", title: s.laneEmpty, body: <Card data={SPARSE} /> },
      {
        id: "list",
        title: s.list,
        body: (
          <div className="max-w-[24rem]">
            <Card data={SHOWCASE} wide={false} />
          </div>
        ),
      },
      {
        id: "list-as-of",
        title: s.listAsOf,
        // The list has no chart to carry the "As of" label, so it says its date in a line under the subtitle.
        body: (
          <div className="max-w-[24rem]">
            <Card data={asOf as unknown as Timeline} wide={false} />
          </div>
        ),
      },
      {
        id: "loading",
        title: s.loading,
        // The card as the tab draws it while the timeline loads, its title placeholder sized to the finding.
        body: <TimelineLoading wide slow={false} />,
      },
      {
        id: "loading-slow",
        title: s.loadingSlow,
        // After two seconds: "Still loading" in place of the card's last caption bar, so nothing above it moves.
        body: <TimelineLoading wide slow />,
      },
      {
        id: "empty",
        title: s.empty,
        body: <EmptyState level={3} title={copy.timeline.emptyTitle} body={copy.timeline.emptyBody} link={{ href: "/gallery/timeline", text: copy.timeline.emptyLink }} />,
      },
      { id: "card-timeline", title: s.cardTimeline, body: <CardSample /> },
      { id: "card-warning", title: s.cardWarning, body: <CardSample answer /> },
      {
        id: "card-states",
        title: s.cardOpen,
        body: (
          <div className="flex flex-col gap-8">
            <CardSample answer state={{ phase: "open" }} reason={galleryCopy.timelineReason} />
            <Labeled label={s.cardEmpty}>
              <CardSample answer state={{ phase: "open", error: true }} />
            </Labeled>
            <Labeled label={s.cardSaving}>
              <CardSample answer state={{ phase: "saving" }} reason={galleryCopy.timelineReason} />
            </Labeled>
            <Labeled label={s.cardFailed}>
              <CardSample answer state={{ phase: "failed" }} reason={galleryCopy.timelineReason} />
            </Labeled>
            <Labeled label={s.cardKept}>
              <CardSample answer state={{ phase: "kept", madeAt: "2026-10-23T15:00:00+00:00", reason: galleryCopy.timelineReason }} />
            </Labeled>
            <Labeled label={s.cardBackFailed}>
              <CardSample answer state={{ phase: "kept", madeAt: "2026-10-23T15:00:00+00:00", reason: galleryCopy.timelineReason }} backFailed />
            </Labeled>
            <Labeled label={s.cardPreview}>
              <CardSample answer preview />
            </Labeled>
          </div>
        ),
      },
      {
        id: "tags",
        title: s.tags,
        body: (
          <div className="flex flex-wrap gap-2">
            <SourceTag>{copy.disagreement.lean}</SourceTag>
            <SourceTag>{copy.disagreement.card.kept}</SourceTag>
          </div>
        ),
      },
      {
        id: "reason",
        title: s.reason,
        body: <CardSample answer state={{ phase: "open" }} reason={galleryCopy.timelineLongReason} />,
      },
      { id: "drawer-document", title: s.drawerDocument, body: <Drawer evidence={isr7Doc as unknown as EvidenceEvent} /> },
      { id: "drawer-replaced", title: s.drawerReplaced, body: <Drawer evidence={reviewDoc as unknown as EvidenceEvent} /> },
      { id: "drawer-ratings", title: s.drawerRatings, body: <Drawer evidence={ratings19 as unknown as EvidenceEvent} /> },
      { id: "drawer-contracts", title: s.drawerContracts, body: <Drawer evidence={contracts2019 as unknown as EvidenceEvent} /> },
      { id: "drawer-disagreement", title: s.drawerDisagreement, body: <Drawer evidence={PDO} /> },
    ],
  };
}
