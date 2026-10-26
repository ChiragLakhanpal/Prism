-- Tile 12: the share of answers Microsoft Foundry scored in the latest evaluation run in the dates chosen that met its
-- threshold, for each evaluator in a fixed order, as ticket 33 stored them (strata.ops.evaluation_result, scorer
-- foundry_evaluation: scored, met and share). From fewer than data_readiness.fewest_for_a_percentage answers the bar
-- is left out, and the table under it gives the counts.
WITH latest AS (
  SELECT run_id
  FROM strata.ops.evaluation_result
  WHERE scorer = 'foundry_evaluation' AND public_from BETWEEN :date_from AND :date_to
  ORDER BY ran_at DESC
  LIMIT 1
),
evaluators AS (
  SELECT
    e.segment AS evaluator_key,
    CAST(max(CASE WHEN e.measure = 'scored' THEN e.value END) AS BIGINT) AS scored,
    CAST(max(CASE WHEN e.measure = 'met' THEN e.value END) AS BIGINT) AS met,
    max(CASE WHEN e.measure = 'share' THEN e.value END) AS share
  FROM strata.ops.evaluation_result AS e
  JOIN latest AS l ON e.run_id = l.run_id
  WHERE e.scorer = 'foundry_evaluation' AND e.segment_kind = 'evaluator'
  GROUP BY e.segment
)
SELECT
  CASE evaluator_key WHEN 'groundedness' THEN 1 WHEN 'relevance' THEN 2 WHEN 'task_adherence' THEN 3 ELSE 4 END
    AS position,
  :evaluator_label__evaluator_key AS evaluator,
  met,
  scored,
  CASE WHEN scored >= :threshold__data_readiness__fewest_for_a_percentage
       THEN CAST(round(100 * share) AS BIGINT) END AS share_percent
FROM evaluators
ORDER BY position
