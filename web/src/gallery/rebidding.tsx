// The gallery's rebidding page (ticket 28): section 1's "Advertised again" block in each of its states, from the
// answers the server wrote on the fixture (tests/record_rebidding_api.py), and two mocks for the states the fixture
// cannot hold: my model's estimate shown, and a model that did no better than its baseline. Each mock says it is one
// and uses made-up packages and numbers. Hover and keyboard focus are captured from the app (web/capture/shots.ts,
// the rebidding-- shots).
import fixture from "../../../tests/fixtures/api/rebidding-ke-nwwda-541055.json";
import prior from "../../../tests/fixtures/api/rebidding-ke-nwwda-541055-prior.json";
import planned from "../../../tests/fixtures/api/rebidding-planned-works-rfb-ke.json";
import shown from "../../../tests/fixtures/api/rebidding-mock-model-shown.json";
import notBetter from "../../../tests/fixtures/api/rebidding-mock-not-better.json";
import noticeRecord from "../../../tests/fixtures/api/evidence-notice-op00083890.json";
import planRecord from "../../../tests/fixtures/api/evidence-plan-row-ke-kimawasco-157517.json";
import awardRecord from "../../../tests/fixtures/api/evidence-mock-award-notice-op90000006.json";
import { useId, type ReactNode } from "react";
import { EvidenceDrawerView } from "../components/EvidenceDrawer";
import { CaseClaim, CaseSwitcher } from "../components/RebidDrawer";
import { RebiddingView, type RebidState } from "../components/RebiddingBlock";
import type { EvidenceEvent } from "../lib/answer";
import { numbersFrom, SECTION_1 } from "../lib/markers";
import { citedIds, type RebidCase, type RebiddingResult } from "../lib/rebidding";
import { galleryCopy } from "./copy";
import type { GalleryPage } from "./pages";

const t = galleryCopy.rebidSections;
const FIXTURE = fixture as unknown as RebiddingResult;
const PRIOR = prior as unknown as RebiddingResult;
const PLANNED = planned as unknown as RebiddingResult;
const SHOWN = shown as unknown as RebiddingResult;
const NOT_BETTER = notBetter as unknown as RebiddingResult;
const nothing = () => undefined;
const TWICE = SHOWN.rows.find((row) => row.evidence.length > 1) as RebidCase;

const ready = (result: RebiddingResult): RebidState => ({ status: "ready", result });

// A sample as wide as the workspace column at 1440 px, inside a card like section 1's.
function Card({ children }: { children: ReactNode }) {
  return <div className="max-w-[46.5rem] rounded-md border border-line bg-surface p-4 @md/page:p-6">{children}</div>;
}

function Block({ state, ...rest }: { state: RebidState; open?: boolean; comparing?: boolean; asOf?: string; updating?: boolean }) {
  const numbers = numbersFrom({ [SECTION_1]: state.status === "ready" ? citedIds(state.result) : [] });
  return (
    <Card>
      <RebiddingView state={state} numbers={numbers} initiallyOpen={rest.open} comparing={rest.comparing} asOf={rest.asOf ?? null} updating={rest.updating} />
    </Card>
  );
}

function Drawer({ evidence }: { evidence: EvidenceEvent }) {
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

export function rebiddingPage(): GalleryPage {
  const [first] = TWICE.evidence;
  return {
    slug: "rebidding",
    current: "packages",
    sections: [
      { id: "fixture", title: t.fixture, body: <Block state={ready(FIXTURE)} /> },
      { id: "fixture-open", title: t.fixtureOpen, body: <Block state={ready(FIXTURE)} open /> },
      { id: "shown", title: t.shown, body: <Block state={ready(SHOWN)} open /> },
      { id: "not-better", title: t.notBetter, body: <Block state={ready(NOT_BETTER)} /> },
      { id: "under-20", title: t.under20, body: <Block state={ready(PRIOR)} /> },
      { id: "planned", title: t.planned, body: <Block state={ready(PLANNED)} /> },
      { id: "comparing", title: t.comparing, body: <Block state={ready(FIXTURE)} comparing /> },
      { id: "as-of", title: t.asOf, body: <Block state={ready(FIXTURE)} asOf="2026-03-31" /> },
      { id: "loading", title: t.loading, body: <Block state={{ status: "loading" }} /> },
      { id: "updating", title: t.updating, body: <Block state={ready(FIXTURE)} updating /> },
      { id: "error", title: t.error, body: <Block state={{ status: "error", requestId: "0af7651916cd43dd8448eb211c80319c", onRetry: nothing }} /> },
      {
        id: "claim",
        title: t.claim,
        body: (
          <div className="flex max-w-[37.5rem] flex-col gap-4 rounded-md border border-line p-6">
            <CaseClaim row={TWICE} id={first.evidence_id} through={SHOWN.records_through} number={7} />
            <CaseSwitcher row={TWICE} current={first.evidence_id} panelId="rebid-gallery-claim" onChoose={nothing} />
            <div id="rebid-gallery-claim" role="tabpanel" aria-labelledby="rebid-gallery-claim-tab-0" />
          </div>
        ),
      },
      { id: "notice", title: t.notice, body: <Drawer evidence={noticeRecord as unknown as EvidenceEvent} /> },
      { id: "plan-row", title: t.planRow, body: <Drawer evidence={planRecord as unknown as EvidenceEvent} /> },
      { id: "award-notice", title: t.awardNotice, body: <Drawer evidence={awardRecord as unknown as EvidenceEvent} /> },
    ],
  };
}
