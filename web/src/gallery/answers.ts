// The gallery's answers: the answer streams ticket 13's server wrote, recorded in tests/fixtures/api
// and checked against the server byte for byte, played into runs as the answer panel builds them. So
// every sample here is a real answer, with the stream's own counts.
import agentUnavailable from "../../../tests/fixtures/api/ask-agent-unavailable.sse?raw";
import contentFilter from "../../../tests/fixtures/api/ask-content-filter.sse?raw";
import beforeTheIcr from "../../../tests/fixtures/api/ask-p130164-before-the-icr.sse?raw";
import isrSection from "../../../tests/fixtures/api/ask-p130164-isr-section.sse?raw";
import nothingFound from "../../../tests/fixtures/api/ask-p130164-nothing-found.sse?raw";
import rebidding from "../../../tests/fixtures/api/ask-p130164-rebidding.sse?raw";
import removedNumber from "../../../tests/fixtures/api/ask-p130164-removed-number.sse?raw";
import tableRow from "../../../tests/fixtures/api/ask-p130164-table-row.sse?raw";
import tableSummary from "../../../tests/fixtures/api/ask-p130164-table-summary.sse?raw";
// Ticket 24: the six checks and the refusals.
import pastRange from "../../../tests/fixtures/api/ask-ke-nwwda-541055-past-range.sse?raw";
import pastRangeAdvice from "../../../tests/fixtures/api/ask-ke-nwwda-541055-advice.sse?raw";
import summaries from "../../../tests/fixtures/api/ask-p130164-summaries.sse?raw";
import unsupportedSummary from "../../../tests/fixtures/api/ask-p130164-unsupported.sse?raw";
import adviceWithout from "../../../tests/fixtures/api/ask-p130164-advice-without-lesson.sse?raw";
import severalRemoved from "../../../tests/fixtures/api/ask-p130164-several-removed.sse?raw";
import disagreementsUnavailable from "../../../tests/fixtures/api/ask-p130164-disagreements-unavailable.sse?raw";
import isr7 from "../../../tests/fixtures/api/ask-p130164-isr-7-rating.sse?raw";
import bothSides from "../../../tests/fixtures/api/ask-p130164-both-sides.sse?raw";
import judgeSilent from "../../../tests/fixtures/api/ask-p130164-judge-no-response.sse?raw";
import judgeSilentNoneKept from "../../../tests/fixtures/api/ask-p130164-judge-no-response-none-kept.sse?raw";
import refusesPart from "../../../tests/fixtures/api/ask-refuses-part-supplier-scores.sse?raw";
import refusesSupplierScores from "../../../tests/fixtures/api/ask-refuses-supplier-scores.sse?raw";
import refusesFraudAndRedactions from "../../../tests/fixtures/api/ask-refuses-fraud-and-redactions.sse?raw";
import refusesLiveTenders from "../../../tests/fixtures/api/ask-refuses-live-tenders.sse?raw";
import refusesReviewDecisions from "../../../tests/fixtures/api/ask-refuses-review-decisions.sse?raw";
import refusesEstimatesForDecisions from "../../../tests/fixtures/api/ask-refuses-estimates-for-decisions.sse?raw";
import refusesDividingPackages from "../../../tests/fixtures/api/ask-refuses-dividing-packages.sse?raw";
import refusesRuleBreachFindings from "../../../tests/fixtures/api/ask-refuses-rule-breach-findings.sse?raw";
import refusesPersonalDetails from "../../../tests/fixtures/api/ask-refuses-personal-details.sse?raw";
import refusesWrongEdition from "../../../tests/fixtures/api/ask-refuses-wrong-edition.sse?raw";
import refusesPrivateUploads from "../../../tests/fixtures/api/ask-refuses-private-uploads.sse?raw";
import checkPlan from "../../../tests/fixtures/api/check-plan-p156634-nwwda-2026-10-09.json";
import icr54 from "../../../tests/fixtures/api/evidence-icr-p130164-54.json";
import isrS4 from "../../../tests/fixtures/api/evidence-isr-p130164-s4.json";
import frenchIcr from "../../../tests/fixtures/api/evidence-icr-p127203-fr.json";
import noticeContacts from "../../../tests/fixtures/api/evidence-notice-op00118817.json";
import noticeQualifications from "../../../tests/fixtures/api/evidence-notice-op00118817-qualifications.json";
import riskRow from "../../../tests/fixtures/api/evidence-pad-p130164-risk-row.json";
import riskSummary from "../../../tests/fixtures/api/evidence-pad-p130164-risk-summary.json";
import scanned from "../../../tests/fixtures/api/evidence-pad-p130164-scanned.json";
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

// Ticket 24's answers, each the stream its scripted case gives (tests/fixtures/agent/cases.toml), asked with
// the case's own question.
const checked = galleryCopy.sixChecks.questions;
const refusalQuestions = galleryCopy.sixChecks.refusalQuestions;
export const CHECK_RUNS = {
  pastRange: played(pastRange, asked(checked.pastRange, "KE-NWWDA-541055-CW-RFB")),
  advice: played(pastRangeAdvice, asked(checked.pastRange, "KE-NWWDA-541055-CW-RFB")),
  summaries: played(summaries, asked(checked.summaries, "P130164")),
  unsupported: played(unsupportedSummary, showcase),
  adviceWithout: played(adviceWithout, showcase),
  several: played(severalRemoved, showcase),
  disagreementsUnavailable: played(disagreementsUnavailable, showcase),
  isr7: played(isr7, asked(checked.isr7, "P130164")),
  bothSides: played(bothSides, asked(checked.bothSides, "P130164")),
  judgeSilent: played(judgeSilent, showcase),
  judgeSilentNoneKept: played(judgeSilentNoneKept, asked(checked.summaries, "P130164")),
  partial: played(refusesPart, asked(refusalQuestions.partial, "P130164")),
};
export const REFUSAL_RUNS = {
    supplier_scores: played(refusesSupplierScores, asked(refusalQuestions.supplier_scores, null)),
    fraud_and_redactions: played(refusesFraudAndRedactions, asked(refusalQuestions.fraud_and_redactions, null)),
    live_tenders: played(refusesLiveTenders, asked(refusalQuestions.live_tenders, null)),
    review_decisions: played(refusesReviewDecisions, asked(refusalQuestions.review_decisions, null)),
    estimates_for_decisions: played(refusesEstimatesForDecisions, asked(refusalQuestions.estimates_for_decisions, null)),
    dividing_packages: played(refusesDividingPackages, asked(refusalQuestions.dividing_packages, null)),
    rule_breach_findings: played(refusesRuleBreachFindings, asked(refusalQuestions.rule_breach_findings, null)),
    personal_details: played(refusesPersonalDetails, asked(refusalQuestions.personal_details, null)),
    wrong_edition: played(refusesWrongEdition, asked(refusalQuestions.wrong_edition, null)),
    private_uploads: played(refusesPrivateUploads, asked(refusalQuestions.private_uploads, null)),
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

// A section of P130164's first ISR, which numbers no paragraphs, as GET /api/evidence answers it.
export const ISR_S4 = isrS4 as unknown as EvidenceEvent;

// The showcase answer with a fourth sentence that quotes the table in that ISR section and also cites
// the ICR's Annex 1.A, for a switcher whose tabs name two sections, and a card that highlights the quote.
export const SECTION_SWITCHER_RUN: Run = played(isrSection, showcase);
export const ISR_S4_SENT = SECTION_SWITCHER_RUN.evidence[ISR_S4.id];

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

// Ticket 18's kinds of passage, as GET /api/evidence gives them on the fixture, and the two answers that
// cite a table: one quoting a row's rating, one whose number only the table's summary held.
export const SCANNED = scanned as unknown as EvidenceEvent;
export const RISK_ROW = riskRow as unknown as EvidenceEvent;
export const RISK_SUMMARY = riskSummary as unknown as EvidenceEvent;
export const NOTICE = noticeQualifications as unknown as EvidenceEvent;
export const NOTICE_CONTACTS = noticeContacts as unknown as EvidenceEvent;
export const FRENCH = frenchIcr as unknown as EvidenceEvent;
export const TABLE_ROW_RUN: Run = played(tableRow, showcase);
export const TABLE_SUMMARY_RUN: Run = played(tableSummary, showcase);
