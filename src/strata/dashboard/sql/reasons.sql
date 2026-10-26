-- Tile 17: the table for tiles 15 and 16, the removed sentences and the held-back answers by reason in the dates
-- chosen, each with what it is out of: the sentences the answers wrote, or the answers given (strata.ops.agent_runs,
-- strata.ops.answer_removals and strata.ops.tool_calls).
WITH answers AS (
  SELECT run_id, sentences_written
  FROM strata.ops.agent_runs
  WHERE status = 'answered' AND public_from BETWEEN :date_from AND :date_to
),
totals AS (
  SELECT coalesce(sum(sentences_written), 0) AS written, count(*) AS answered
  FROM answers
),
removed AS (
  SELECT r.reason
  FROM strata.ops.answer_removals AS r
  JOIN answers AS a ON a.run_id = r.run_id
),
removed_labels AS (
  SELECT :removed_label__reason AS reason_label
  FROM removed
),
held AS (
  SELECT DISTINCT c.run_id, c.abstention
  FROM strata.ops.tool_calls AS c
  JOIN answers AS a ON a.run_id = c.run_id
  WHERE c.abstention IN ('too_few_comparables', 'outside_training', 'asof_before_training', 'no_public_notice',
                         'none_measurable')
),
held_labels AS (
  SELECT run_id, :held_label__abstention AS reason_label
  FROM held
),
counted AS (
  SELECT 1 AS position, reason_label, count(*) AS reason_count FROM removed_labels GROUP BY reason_label
  UNION ALL
  SELECT 2 AS position, reason_label, count(DISTINCT run_id) AS reason_count FROM held_labels GROUP BY reason_label
)
SELECT
  c.position,
  CASE WHEN c.position = 1 THEN :copy__dash__ai__what__removed ELSE :copy__dash__ai__what__held END AS what,
  c.reason_label AS reason,
  c.reason_count AS count,
  CASE WHEN c.position = 1 THEN replace(:copy__dash__ai__outOf__written, '{written}', format_number(t.written, 0))
       ELSE replace(:copy__dash__ai__outOf__answers, '{answers}', format_number(t.answered, 0)) END AS out_of
FROM counted AS c
CROSS JOIN totals AS t
ORDER BY c.position, c.reason_count DESC, c.reason_label
