-- get_lessons: every lesson version decided on or before :decided_by, oldest first within each lesson, so the
-- last row of a lesson is the version current on that date (ADR 0002). :decided_by is the as-of date, except in
-- the hindsight test's replays (ticket 34), where it is the replay's own date and the tool then dates each version
-- by the passages it rests on. A version that retired the lesson is returned too, so the tool can leave the
-- lesson out and count it.
SELECT
  v.lesson_id,
  v.version,
  v.statement,
  v.risk_factors,
  v.stage,
  v.kind,
  v.edition_key,
  v.project_id,
  v.state,
  v.decided_on,
  v.public_from
FROM strata.ops.lesson_versions AS v
WHERE v.decided_on <= :decided_by
ORDER BY v.lesson_id, v.version
