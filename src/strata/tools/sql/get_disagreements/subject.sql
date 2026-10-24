-- get_disagreements: whether Strata holds the subject, as a project or as a package by its STEP reference,
-- and the project it belongs to.
SELECT
  :project AS subject_kind,
  p.project_id
FROM strata.gold.project AS p
WHERE p.project_id = :subject_id
UNION ALL
SELECT
  :package AS subject_kind,
  k.project_id
FROM strata.gold.package AS k
WHERE k.step_reference = :subject_id
UNION ALL
SELECT DISTINCT
  a.subject_kind,
  a.project_id
FROM strata.gold.assertion AS a
WHERE a.subject_id = :subject_id
