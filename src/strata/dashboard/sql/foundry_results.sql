-- Tile 14: each Microsoft Foundry evaluation run in the dates chosen, by evaluator: the answers that met its
-- threshold, the answers it scored, and the mean score from 1 to 5 at one decimal, as ticket 33 stored them
-- (strata.ops.evaluation_result, scorer foundry_evaluation). Newest first.
WITH evaluators AS (
  SELECT
    run_id,
    segment AS evaluator_key,
    max(ran_at) AS ran_at,
    CAST(max(CASE WHEN measure = 'met' THEN value END) AS BIGINT) AS met,
    CAST(max(CASE WHEN measure = 'scored' THEN value END) AS BIGINT) AS scored,
    max(CASE WHEN measure = 'mean_score' THEN value END) AS mean_score
  FROM strata.ops.evaluation_result
  WHERE scorer = 'foundry_evaluation' AND segment_kind = 'evaluator' AND public_from BETWEEN :date_from AND :date_to
  GROUP BY run_id, segment
)
SELECT
  CAST(ran_at AS DATE) AS run_on,
  CASE evaluator_key WHEN 'groundedness' THEN 1 WHEN 'relevance' THEN 2 WHEN 'task_adherence' THEN 3 ELSE 4 END
    AS position,
  :evaluator_label__evaluator_key AS evaluator,
  met,
  scored,
  round(mean_score, 1) AS mean_score
FROM evaluators
ORDER BY ran_at DESC, position
