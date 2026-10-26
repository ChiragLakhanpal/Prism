-- KPI answers_held_back (config/kpis.toml): answers in the dates chosen in which a tool call held back a range, a time
-- estimate or a share because the evidence fell short, out of all answers. The codes that count are the abstentions
-- copy.dash.ai.held names; a refusal gives none of them, so it is never held back but counts among all answers. Each
-- call is in strata.ops.tool_calls (the run log, ticket 45). Always one row: "None yet" before the first answer.
WITH answers AS (
  SELECT run_id
  FROM strata.ops.agent_runs
  WHERE status = 'answered' AND public_from BETWEEN :date_from AND :date_to
),
held AS (
  SELECT DISTINCT c.run_id
  FROM strata.ops.tool_calls AS c
  JOIN answers AS a ON c.run_id = a.run_id
  WHERE c.abstention IN ('too_few_comparables', 'outside_training', 'asof_before_training', 'no_public_notice',
                         'none_measurable')
),
counted AS (
  SELECT (SELECT count(*) FROM held) AS held, (SELECT count(*) FROM answers) AS answers
)
SELECT
  held AS numerator,
  answers AS denominator,
  held AS value,
  CASE
    WHEN answers = 0 THEN :copy__kpi__display__none
    ELSE replace(replace(:copy__kpi__display__share, '{n}', format_number(held, 0)), '{d}', format_number(answers, 0))
  END AS display
FROM counted
