-- A project's Summary: the outcome rating its Implementation Completion and Results Report (ICR) gives,
-- as the nightly detect_disagreements task read it from the ICR's text with its quote on the page
-- (strata.gold.assertion, evidence tier icr), newest report first, from the version current on the as-of
-- date, with the passage it rests on, so a citation opens it.
SELECT
  value,
  made_at,
  evidence_id,
  public_from
FROM strata.gold.assertion
WHERE project_id = :project_id
  AND subject_kind = :subject_kind
  AND attribute = :attribute
  AND evidence_tier = :evidence_tier
  AND public_from <= :as_of
  AND (replaced_on IS NULL OR replaced_on > :as_of)
ORDER BY made_at DESC, version DESC, evidence_id
