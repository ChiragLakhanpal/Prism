// The step-label registry (ticket 27; the 27 brief, section 5): STEP's steps for each method family, in STEP's
// order, with the short label a screen shows, STEP's full name word for word, the step as a noun phrase inside
// a sentence, and the stage of work that leads up to it. It is the one place these live (CLAUDE.md rule 9):
// the package workspace's section 2 reads it, and so do ticket 21's re-dated table, ticket 22's "Dates in the
// plan" and ticket 38's export.
//
// - label is the blueprint's "Step labels taken from STEP", word for word.
// - step_name is STEP's own column name, copied from the fixtures' exports, and equal to one of
//   src/strata/reader/step.py's STEPS. tests/test_step_registry.py ties the two, so each name is defined once.
// - phrase and stage are Strata's plain English. The copy lint checks them, and every label, like the copy file.
// - A family's first step has no stage: nothing leads up to it.
//
// The family rule, in two parts:
//
// - A package from a STEP row belongs to the family whose sections hold the STEP table its plan lists it in. STEP
//   itself splits individual consultants from consulting firms by table, and the same Method, such as Direct
//   Selection, can sit in either.
// - A package with no plan row, such as one planned from a sentence, belongs to the first family whose categories
//   hold its procurement category and whose methods hold its Method. A sentence cannot tell a firm from an
//   individual, so Consultant Services under Direct Selection goes to consulting firms, the first family that
//   lists the pair.
//
// A package with no category or Method yet has no family; one whose Method fits no family's list is outside the
// three families. The server reads all of this from its copy,
// src/strata/estimates/steps.json, which web/lint/server-copy.ts writes from this file; the lint fails when the
// copy is out of date. Matching is by step name, never by a step's place in a plan's table.

export type StepEntry = {
  key: string;
  label: string;
  step_name: string;
  phrase: string;
  stage: string | null;
};

export type StepFamily = {
  family_name: string;
  abbreviation_note: string | null;
  // STEP's plan tables whose packages belong to this family, as src/strata/reader/step.py's SECTIONS name them.
  sections: string[];
  categories: string[];
  methods: string[];
  // "Ran longest" counts the stages up to this step: the contract's completion measures its work, not its
  // procurement (the 27 brief, section 6.5).
  longest_through: string;
  steps: StepEntry[];
};

const signed = (stage: string): StepEntry => ({
  key: "contract_signed",
  label: "Contract signed",
  step_name: "Signed Contract",
  phrase: "the signed contract",
  stage,
});

const completed: StepEntry = {
  key: "contract_completed",
  label: "Contract completed",
  step_name: "Contract Completion",
  phrase: "the contract's completion",
  stage: "The contract's work",
};

const termsOfReference: StepEntry = {
  key: "terms_of_reference",
  label: "Terms of reference",
  step_name: "Terms of Reference",
  phrase: "the terms of reference",
  stage: null,
};

export const stepFamilies = {
  goods: {
    family_name: "goods, works and non-consulting services",
    abbreviation_note: "SPN is the specific procurement notice.",
    sections: ["GOODS", "WORKS", "NON CONSULTING SERVICES"],
    categories: ["Goods", "Works", "Non-consulting Services"],
    methods: ["Request for Bids", "Request for Quotations", "Request for Proposals", "Direct Selection"],
    longest_through: "contract_signed",
    steps: [
      { key: "bid_invitation", label: "Bid invitation (SPN)", step_name: "Specific Procurement Notice / Invitation", phrase: "the bid invitation", stage: null },
      {
        key: "bidding_document_issued",
        label: "Bidding document issued",
        step_name: "Bidding Documents as Issued",
        phrase: "the issued bidding document",
        stage: "Issuing the bidding document",
      },
      { key: "bid_opening", label: "Bid opening", step_name: "Proposal Submission / Opening / Minutes", phrase: "the bid opening", stage: "The bidding period" },
      {
        key: "bid_evaluation_report",
        label: "Bid evaluation report",
        step_name: "Bid Evaluation Report and Recommendation for Award",
        phrase: "the bid evaluation report",
        stage: "Bid evaluation",
      },
      signed("Award and signing"),
      completed,
    ],
  },
  firms: {
    family_name: "consulting firms",
    abbreviation_note: "RFP is the Request for Proposals.",
    sections: ["CONSULTING FIRMS"],
    categories: ["Consultant Services"],
    methods: [
      "Quality And Cost-Based Selection",
      "Quality Based Selection",
      "Fixed Budget Selection",
      "Least Cost Selection",
      "Consultant Qualification Selection",
      "Direct Selection",
    ],
    longest_through: "contract_signed",
    steps: [
      termsOfReference,
      { key: "eoi_notice", label: "Expression of interest notice", step_name: "Expression of Interest Notice", phrase: "the expression of interest notice", stage: "Preparing the notice" },
      {
        key: "short_list_draft_rfp",
        label: "Short list and draft RFP",
        step_name: "Short List and Draft Request for Proposals",
        phrase: "the short list and draft RFP",
        stage: "Short-listing",
      },
      { key: "rfp_issued", label: "RFP issued", step_name: "Request for Proposals as Issued", phrase: "the issued RFP", stage: "Issuing the RFP" },
      {
        key: "technical_proposals_opened",
        label: "Technical proposals opened",
        step_name: "Opening of Technical Proposals / Minutes",
        phrase: "the opening of technical proposals",
        stage: "Proposal preparation",
      },
      { key: "technical_evaluation", label: "Technical evaluation", step_name: "Evaluation of Technical Proposal", phrase: "the technical evaluation", stage: "Technical evaluation" },
      {
        key: "combined_evaluation_report",
        label: "Combined evaluation report",
        step_name: "Combined Evaluation Report and Draft Negotiated Contract",
        phrase: "the combined evaluation report",
        stage: "Combined evaluation",
      },
      signed("Negotiation and signing"),
      completed,
    ],
  },
  individuals: {
    family_name: "individual consultants",
    abbreviation_note: null,
    sections: ["INDIVIDUAL CONSULTANTS"],
    categories: ["Consultant Services"],
    methods: ["Individual Consultant Selection"],
    longest_through: "contract_signed",
    steps: [
      termsOfReference,
      { key: "invitation", label: "Invitation", step_name: "Invitation to Identified/Selected Consultant", phrase: "the invitation", stage: "Preparing the invitation" },
      {
        key: "draft_negotiated_contract",
        label: "Draft negotiated contract",
        step_name: "Draft Negotiated Contract",
        phrase: "the draft negotiated contract",
        stage: "Selection and negotiation",
      },
      signed("Signing"),
      completed,
    ],
  },
} satisfies Record<string, StepFamily>;

export type FamilyKey = keyof typeof stepFamilies;

export function stepFamily(family: string | null | undefined): StepFamily | null {
  return family && family in stepFamilies ? stepFamilies[family as FamilyKey] : null;
}

// One step of a family by its key, or null when the family has no such step.
export function familyStep(family: StepFamily | null, key: string): StepEntry | null {
  return family?.steps.find((step) => step.key === key) ?? null;
}
