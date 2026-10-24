-- Which proposals each lesson rests on, from the version that added each.
SELECT
  s.lesson_id,
  s.version,
  s.proposal_id,
  s.item_id
FROM strata.ops.lesson_sources AS s
ORDER BY s.lesson_id, s.version, s.proposal_id
