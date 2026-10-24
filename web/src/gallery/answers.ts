// The gallery's answers: the answer streams ticket 13's server wrote, recorded in tests/fixtures/api
// and checked against the server byte for byte, played into runs as the answer panel builds them. So
// every sample here is a real answer, with the stream's own counts.
import agentUnavailable from "../../../tests/fixtures/api/ask-agent-unavailable.sse?raw";
import contentFilter from "../../../tests/fixtures/api/ask-content-filter.sse?raw";
import beforeTheIcr from "../../../tests/fixtures/api/ask-p130164-before-the-icr.sse?raw";
import nothingFound from "../../../tests/fixtures/api/ask-p130164-nothing-found.sse?raw";
import rebidding from "../../../tests/fixtures/api/ask-p130164-rebidding.sse?raw";
import removedNumber from "../../../tests/fixtures/api/ask-p130164-removed-number.sse?raw";
import checkPlan from "../../../tests/fixtures/api/check-plan-p156634-nwwda-2026-10-09.json";
import icr54 from "../../../tests/fixtures/api/evidence-icr-p130164-54.json";
import loan from "../../../tests/fixtures/api/lookup-loan-ida-60290.json";
import activity from "../../../tests/fixtures/api/lookup-activity-ke-nwwda-541055-cw-rfb.json";
import project from "../../../tests/fixtures/api/project-p130164.json";
import { newRun, withEvent, type Asked, type EvidenceEvent, type Run } from "../lib/answer";
import { intentKey, intentsFor, type Lookup } from "../lib/intents";
import { galleryCopy } from "./copy";

const sample = galleryCopy.sample;

// The events a recorded stream holds, in order.
function events(text: string): { type: string; data: unknown }[] {
  return text
    .split("\n\n")
    .map((block) => {
      const type = /^event: (.*)$/m.exec(block)?.[1];
      const data = /^data: (.*)$/m.exec(block)?.[1];
      return type && data ? { type, data: JSON.parse(data) } : null;
    })
    .filter((event): event is { type: string; data: unknown } => event !== null);
}

const asked = (question: string, scope: string | null, more: Partial<Asked> = {}): Asked => ({
  question,
  scope,
  asOf: null,
  view: null,
  lang: null,
  key: "gallery",
  ...more,
});

// A run played from a stream, or from its first `upTo` events while it still streams.
function played(stream: string, question: Asked, upTo?: number): Run {
  const all = events(stream);
  return (upTo === undefined ? all : all.slice(0, upTo)).reduce((run, event) => withEvent(run, event.type, event.data), newRun(0, question));
}

const showcase = asked(sample.showcaseQuestion, "P130164");

export const RUNS = {
  // Two steps done (the search and reading the question), writing in progress, checking to do.
  streaming: played(removedNumber, showcase, 3),
  ready: played(removedNumber, showcase),
  allChecked: played(rebidding, showcase),
  unsupported: played(beforeTheIcr, showcase),
  emptyScoped: played(nothingFound, asked(sample.bridgesQuestion, "P130164")),
  emptyUnscoped: played(nothingFound, asked(sample.bridgesQuestion, null)),
  refused: played(contentFilter, showcase),
  error: played(agentUnavailable, showcase),
  dropped: { ...played(rebidding, showcase, 6), phase: "dropped" } as Run,
  asOf: played(removedNumber, asked(sample.showcaseQuestion, "P130164", { asOf: "2026-10-01" })),
  preview: played(removedNumber, asked(sample.showcaseQuestion, "P130164", { view: "public" })),
};

// The showcase answer with its first sentence citing paragraphs 54 and 55, for the source switcher.
export const SWITCHER_RUN: Run = {
  ...RUNS.ready,
  sentences: RUNS.ready.sentences.map((sentence) =>
    sentence.index === 0 ? { ...sentence, evidence_ids: [...sentence.evidence_ids, "strata.gold.passage:31525018/v1/55"] } : sentence,
  ),
};

export const ICR_54 = icr54 as unknown as EvidenceEvent;
export const ICR_54_ID = ICR_54.id;
export const ICR_55_ID = "strata.gold.passage:31525018/v1/55";

// The box's lookups as the server answered them (tests/fixtures/api).
const intent = (text: string) => intentsFor(text).ids[0];
export const LOOKUPS: Record<string, Lookup> = {
  [intentKey(intent("P130164"))]: {
    status: "found",
    found: { kind: "project", pcode: project.project.project_id, name: project.project.project_name, country: project.project.country },
  },
  [intentKey(intent("IDA-60290"))]: {
    status: "found",
    found: { kind: "loan", loan: loan.loan_number_as_written, pcode: loan.project_id, name: loan.project_name },
  },
  [intentKey(intent("60290"))]: { status: "pending" },
  [intentKey(intent(activity.activity_reference_no))]: {
    status: "found",
    found: {
      kind: "activity",
      stepRef: activity.activity_reference_no,
      pcode: activity.project_id,
      agency: activity.implementing_agency,
      agencyId: activity.agency_id,
      planDate: activity.plan_date,
      isLatest: activity.is_latest,
    },
  },
  [intentKey(intent(sample.unknownProject))]: { status: "missing" },
};
export const PENDING: Record<string, Lookup> = { [intentKey(intent(activity.activity_reference_no))]: { status: "pending" } };
export const FAILED: Record<string, Lookup> = { [intentKey(intent(activity.activity_reference_no))]: { status: "failed" } };
export const STEP_REF = activity.activity_reference_no;

// A check_plan row, as an answer citing a record would send it: the What stratum's drawer.
export function planRecord(row: Record<string, unknown>): EvidenceEvent {
  return { id: String(row.evidence_id), kind: "record", tool: "check_plan", stratum: "What", short_name: null, row, highlights: [] };
}

// KE-NWWDA-229129-CW-RFB as check_plan returned it for the NWWDA plan of October 9, 2026.
export const PLAN_RECORD = planRecord(checkPlan.rows[0] as unknown as Record<string, unknown>);
