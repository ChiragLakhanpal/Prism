-- get_disagreements: the disagreements about a subject (a project with its packages, or one package by its
-- STEP reference) whose two sides were both public on the as-of date (ADR 0002), read as the viewer.
SELECT
  d.disagreement_id,
  d.project_id,
  d.subject_kind,
  d.subject_id,
  d.attribute,
  d.first_assertion_id,
  d.second_assertion_id,
  d.period_event,
  d.period_start,
  d.period_end,
  d.lean_assertion_id,
  d.rule_id,
  d.replaced_on,
  d.public_from
FROM strata.gold.disagreement AS d
WHERE (d.project_id = :subject_id OR (d.subject_kind = :package AND d.subject_id = :subject_id))
  AND d.public_from <= :as_of
ORDER BY d.public_from, d.subject_id, d.attribute, d.disagreement_id
