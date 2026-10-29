// The gallery's Drafts page (ticket 35): every new draft component in each of its states, from the drafts
// the server wrote on the fixture (tests/record_drafts_api.py), so each sample is a real draft with the
// server's own counts. Hover and keyboard focus are captured from the app (web/capture/shots.ts).
import checked from "../../../tests/fixtures/api/drafts-review-notes-checked.json";
import discarded from "../../../tests/fixtures/api/drafts-review-notes-discarded.json";
import draft from "../../../tests/fixtures/api/drafts-review-notes-draft.json";
import exported from "../../../tests/fixtures/api/drafts-review-notes-exported.json";
import teammate from "../../../tests/fixtures/api/drafts-review-notes-teammate.json";
import list from "../../../tests/fixtures/api/drafts-list.json";
import teammates from "../../../tests/fixtures/api/drafts-list-teammate.json";
import empty from "../../../tests/fixtures/api/drafts-list-empty.json";
import type { ReactNode } from "react";
import { Button } from "../components/Button";
import { DiscardedNotice, DraftBar, ExportSuccess } from "../components/DraftBar";
import { DraftNotes, NoteSentences, type NoteRow } from "../components/DraftNotes";
import { checkPill, PlanCheckHeader, planSubtitle, type CheckedPlan } from "../components/PlanCheck";
import { SourcesList } from "../components/SourcesList";
import { DiscardedOn, StateStepper } from "../components/StateStepper";
import { copy } from "../copy";
import type { Draft, DraftList } from "../lib/drafts";
import { formatDate } from "../lib/format";
import { DraftsList } from "../pages/DraftsPage";
import { galleryCopy } from "./copy";
import type { GalleryPage } from "./pages";

const t = galleryCopy.sections;
const ds = galleryCopy.draftStates;
const kind = copy.draft.kinds.review_notes;
const D = draft as unknown as Draft;
const CHECKED = checked as unknown as Draft;
const EXPORTED = exported as unknown as Draft;
const TEAMMATE = teammate as unknown as Draft;
const DISCARDED = discarded as unknown as Draft;
// A preview of another view: the server holds both acts with the preview's reason.
const PREVIEW: Draft = { ...D, may_act: false, holds: [{ key: "preview", copy: "preview", left: 1, first_anchor: null }] };
const MISSING: Draft = { ...EXPORTED, export: { ...EXPORTED.export!, files: [], files_available: false } };
const day = (iso: string) => formatDate(iso.slice(0, 10));
const nothing = () => undefined;

function Labeled({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-2">
      <p className="text-caption text-ink-muted">{label}</p>
      {children}
    </div>
  );
}

// A sample as wide as a draft's document column at 1440 px.
function Column({ children }: { children: ReactNode }) {
  return <div className="@container/doc max-w-[46.5rem]">{children}</div>;
}

const numbers = new Map(D.sources.map((source) => [source.evidence_id, source.number]));
const opened = new Set([D.sources[1].evidence_id]);
const open = { id: null, sentence: null };
const rows: NoteRow[] = D.notes.map((note) => ({
  key: note.activity_reference_no,
  mark: note.mark,
  description: note.description,
  href: `#${note.activity_reference_no}`,
  note: <NoteSentences sentences={note.sentences} evidence={D.evidence} numbers={numbers} opened={opened} open={open} />,
}));

function bar(sample: Draft, more: Partial<Parameters<typeof DraftBar>[0]> = {}) {
  return <DraftBar draft={sample} words={kind} opened={sample.opened.count} busy={null} failed={null} status="" onAct={nothing} {...more} />;
}

// Check a plan's header with the draft action in its slot, from the gallery's sample plan check.
function actionHeader(plan: CheckedPlan, slot: { action?: ReactNode; feedforward?: ReactNode }) {
  return (
    <PlanCheckHeader level={2} sticky={false} agency={plan.plan.implementing_agency} plan={planSubtitle(plan.plan.plan_date)} pill={checkPill(plan)} {...slot} />
  );
}

export function draftsPage(plan: CheckedPlan): GalleryPage {
  const action = copy.checkPlan.draftAction;
  return {
    slug: "drafts",
    current: "drafts",
    sections: [
      {
        id: "stepper",
        title: t.stepper,
        body: (
          <div className="flex flex-col gap-4">
            <Labeled label={ds.stepDraft}>
              <StateStepper state="draft" />
            </Labeled>
            <Labeled label={ds.stepChecked}>
              <StateStepper state="checked" />
            </Labeled>
            <Labeled label={ds.stepExported}>
              <StateStepper state="exported" />
            </Labeled>
            <Labeled label={ds.stepTeammate}>
              <StateStepper state="checked" checkedBy={TEAMMATE.author.name} />
            </Labeled>
            <Labeled label={ds.stepDiscarded}>
              <DiscardedOn date={day(DISCARDED.discarded!.at)} />
            </Labeled>
            <Labeled label={ds.stepColumn}>
              <StateStepper state="checked" layout="column" />
            </Labeled>
          </div>
        ),
      },
      {
        id: "held",
        title: t.held,
        body: (
          <div className="flex flex-col gap-2">
            <p id="gallery-hold" className="text-small text-ink">
              {kind.holdNotChecked}
            </p>
            <div>
              <Button held aria-describedby="gallery-hold">
                {copy.draft.bar.export}
              </Button>
            </div>
          </div>
        ),
      },
      {
        id: "busy",
        title: t.busy,
        body: (
          <div className="flex flex-wrap items-center gap-4">
            <Button variant="primary" loading busyLabel={copy.draft.bar.busy.check}>
              {copy.draft.bar.check}
            </Button>
            <Button variant="secondary" loading busyLabel={copy.draft.bar.busy.export}>
              {copy.draft.bar.export}
            </Button>
            <Button variant="ghost" flush loading busyLabel={copy.draft.bar.busy.discard}>
              {copy.draft.bar.discard}
            </Button>
          </div>
        ),
      },
      {
        id: "notes",
        title: t.notes,
        body: (
          <div className="flex flex-col gap-6">
            <Labeled label={ds.table}>
              <Column>
                <DraftNotes rows={rows} columns={D.layout.columns.map((column) => (kind.columns as Record<string, string>)[column])} caption={kind.tableCaption(D.subject.implementing_agency, day(D.subject.plan_date))} cardsLabelId="gallery-notes" />
              </Column>
            </Labeled>
            <Labeled label={ds.cards}>
              <div className="@container/doc max-w-[24rem]">
                <p id="gallery-notes" className="sr-only">
                  {kind.tableCaption(D.subject.implementing_agency, day(D.subject.plan_date))}
                </p>
                <DraftNotes rows={rows} columns={D.layout.columns.map((column) => (kind.columns as Record<string, string>)[column])} caption={kind.tableCaption(D.subject.implementing_agency, day(D.subject.plan_date))} cardsLabelId="gallery-notes" />
              </div>
            </Labeled>
          </div>
        ),
      },
      {
        id: "sources",
        title: t.sources,
        body: (
          <Labeled label={ds.sourceStates}>
            <Column>
              <SourcesList sources={D.sources} evidence={D.evidence} opened={opened} openedCount={1} total={D.opened.of} citations={D.citations} open={open} />
            </Column>
          </Labeled>
        ),
      },
      {
        id: "bar",
        title: t.draftBar,
        body: (
          <div className="flex flex-col gap-6">
            <Labeled label={ds.author}>
              <Column>{bar(D)}</Column>
            </Labeled>
            <Labeled label={ds.saving}>
              <Column>{bar(D, { busy: "check" })}</Column>
            </Labeled>
            <Labeled label={ds.checked}>
              <Column>{bar(CHECKED)}</Column>
            </Labeled>
            <Labeled label={ds.exporting}>
              <Column>{bar(CHECKED, { busy: "export", status: copy.draft.bar.exportStarted })}</Column>
            </Labeled>
            <Labeled label={ds.teammate}>
              <Column>{bar(TEAMMATE)}</Column>
            </Labeled>
            <Labeled label={ds.preview}>
              <Column>{bar(PREVIEW)}</Column>
            </Labeled>
            <Labeled label={ds.failed}>
              <Column>{bar(D, { failed: "check" })}</Column>
            </Labeled>
            <Labeled label={ds.conflict}>
              <Column>{bar(CHECKED, { notice: copy.draft.conflict })}</Column>
            </Labeled>
          </div>
        ),
      },
      {
        id: "end",
        title: t.draftEnd,
        body: (
          <div className="flex flex-col gap-6">
            <Labeled label={ds.fresh}>
              <Column>
                <ExportSuccess draft={EXPORTED} fresh date={day} />
              </Column>
            </Labeled>
            <Labeled label={ds.revisit}>
              <Column>
                <ExportSuccess draft={EXPORTED} fresh={false} date={day} />
              </Column>
            </Labeled>
            <Labeled label={ds.missing}>
              <Column>
                <ExportSuccess draft={MISSING} fresh={false} date={day} />
              </Column>
            </Labeled>
            <Labeled label={ds.discarded}>
              <Column>
                <DiscardedNotice sentence={kind.discarded} restoring={false} may_act failed={false} onRestore={nothing} />
              </Column>
            </Labeled>
          </div>
        ),
      },
      {
        id: "action",
        title: t.draftAction,
        body: (
          <div className="flex flex-col gap-6">
            <Labeled label={ds.actionSome}>
              {actionHeader(plan, {
                action: <Button variant="primary">{action.button(plan.counts.signal, String(plan.counts.signal))}</Button>,
                feedforward: <p className="text-caption text-ink-muted @lg/page:text-right">{action.feedforward}</p>,
              })}
            </Labeled>
            <Labeled label={ds.actionNone}>
              {/* Ticket 100: with no signal to draft from, the head holds the check pill alone. */}
              {actionHeader(plan, {})}
            </Labeled>
            <Labeled label={ds.actionAsOf}>
              {actionHeader(plan, { feedforward: <p className="text-caption text-ink-muted">{action.asof}</p> })}
            </Labeled>
          </div>
        ),
      },
      {
        id: "rows",
        title: t.draftRows,
        body: (
          <div className="flex max-w-[54rem] flex-col gap-8">
            <Labeled label={ds.own}>
              <DraftsList list={list as unknown as DraftList} />
            </Labeled>
            <Labeled label={ds.teammates}>
              <DraftsList list={teammates as unknown as DraftList} />
            </Labeled>
            <Labeled label={ds.noDrafts}>
              <DraftsList list={empty as unknown as DraftList} />
            </Labeled>
          </div>
        ),
      },
    ],
  };
}
