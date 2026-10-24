-- get_lessons: the evidence of every lesson, as of a date. Each lesson rests on the proposals a lead added
-- to it (strata.ops.lesson_sources) at the version that added each, and each proposal on its own quote and
-- IEG's restatements (strata.silver.lesson_evidence). Only evidence from documents public on or before the
-- as-of date is returned (ADR 0002), with the passage's project for its source line.
SELECT
  s.lesson_id,
  s.version AS added_at_version,
  e.proposal_id,
  e.role,
  e.passage_id,
  e.document_id,
  e.version,
  e.project_id,
  e.document_type,
  e.report_number,
  e.document_date,
  e.paragraph,
  e.cited_page,
  e.quote,
  e.restated_by_ieg,
  e.public_from
FROM strata.ops.lesson_sources AS s
JOIN strata.silver.lesson_evidence AS e ON e.proposal_id = s.proposal_id
WHERE s.public_from <= :as_of
  AND e.public_from <= :as_of
ORDER BY s.lesson_id, e.role DESC, e.document_date, e.passage_id
