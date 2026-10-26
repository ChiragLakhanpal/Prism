-- Tile 16: the answers in the dates chosen in which I held back, by the label of the reason a tool gave
-- (copy.dash.ai.held), largest first, from strata.ops.tool_calls beside each run in strata.ops.agent_runs. An answer
-- counts once for each reason it held back for. The codes are the ones KPI answers_held_back counts.
WITH held AS (
  SELECT DISTINCT c.run_id, c.abstention
  FROM strata.ops.tool_calls AS c
  JOIN strata.ops.agent_runs AS r ON r.run_id = c.run_id
  WHERE r.status = 'answered' AND r.public_from BETWEEN :date_from AND :date_to
    AND c.abstention IN ('too_few_comparables', 'outside_training', 'asof_before_training', 'no_public_notice',
                         'none_measurable')
),
labelled AS (
  SELECT run_id, :held_label__abstention AS reason_label
  FROM held
)
SELECT reason_label AS reason, count(DISTINCT run_id) AS answers
FROM labelled
GROUP BY reason_label
ORDER BY answers DESC, reason
