-- check_plan: the activities of one plan version that the records have moved past (ticket 132). The nightly job's
-- detect_disagreements task defines the finding once (src/strata/knowledge/assertions.py): a plan row whose Process
-- Status says the contract is not signed yet disagrees with a record that dates the signing before the agency's
-- next plan replaced the row. The tool only reads those disagreements, for this version's rows, with the record's
-- signing date, its form (a contract record or an award notice) and its evidence id, each only once both sides were
-- public on the as-of date (ADR 0002). A replaced version's check still names its own rows' disagreements.
SELECT
  s.subject_id AS activity_reference_no,
  d.disagreement_id,
  r.form AS record_form,
  r.value AS signed_on,
  r.evidence_id AS record_evidence_id,
  d.public_from
FROM strata.gold.disagreement AS d
JOIN strata.gold.assertion AS s
  ON s.assertion_id = d.first_assertion_id OR s.assertion_id = d.second_assertion_id
JOIN strata.gold.assertion AS r
  ON r.assertion_id = CASE WHEN s.assertion_id = d.first_assertion_id THEN d.second_assertion_id
                           ELSE d.first_assertion_id END
WHERE s.document_id = :document_id
  AND s.form = :plan_row
  AND s.value_form = :status
  AND d.subject_kind = :package
  AND d.public_from <= :as_of
ORDER BY s.subject_id, r.value, d.disagreement_id
