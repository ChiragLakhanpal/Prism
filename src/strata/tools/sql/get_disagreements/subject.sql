-- get_disagreements: whether Prism holds the subject, as a project or as a package by its STEP reference,
-- the project it belongs to, and its id as Prism holds it. A project ID or a STEP reference is matched whatever
-- its case, as check_plan matches an agency, so ke-mowasco-307378-go-rfb names KE-MOWASCO-307378-GO-RFB.
SELECT
  :project AS subject_kind,
  p.project_id AS subject_id,
  p.project_id
FROM strata.gold.project AS p
WHERE upper(p.project_id) = upper(:subject_id)
UNION ALL
SELECT
  :package AS subject_kind,
  k.step_reference AS subject_id,
  k.project_id
FROM strata.gold.package AS k
WHERE upper(k.step_reference) = upper(:subject_id)
UNION ALL
SELECT DISTINCT
  a.subject_kind,
  a.subject_id,
  a.project_id
FROM strata.gold.assertion AS a
WHERE upper(a.subject_id) = upper(:subject_id)
