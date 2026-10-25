-- get_lessons: the evidence of every lesson, as of a date. Each lesson rests on the proposals a lead added
-- to it (strata.ops.lesson_sources) by :decided_by, at the version that added each, and each proposal on its own
-- quote and IEG's restatements (strata.silver.lesson_evidence). Only evidence from documents public on or before
-- :evidence_through is returned (ADR 0002), with the passage's project for its source line. Both dates are the
-- as-of date, except in the hindsight test's replays (ticket 34), where both are the replay's own date and the
-- tool keeps only the evidence public by the as-of date.
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
WHERE s.public_from <= :decided_by
  AND e.public_from <= :evidence_through
ORDER BY s.lesson_id, e.role DESC, e.document_date, e.passage_id
