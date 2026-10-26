-- Tile 13: each full gate run in the dates chosen, by kind of question, with its target and where it stands against
-- it in words, as ticket 33 stored them (strata.ops.evaluation_result, scorer benchmark: questions, passed, target,
-- gap and met, by kind). Newest first.
WITH kinds AS (
  SELECT
    run_id,
    segment AS kind_key,
    max(ran_at) AS ran_at,
    CAST(max(CASE WHEN measure = 'passed' THEN value END) AS BIGINT) AS passed,
    CAST(max(CASE WHEN measure = 'questions' THEN value END) AS BIGINT) AS questions,
    max(CASE WHEN measure = 'share' THEN value END) AS share,
    max(CASE WHEN measure = 'target' THEN value END) AS target,
    max(CASE WHEN measure = 'gap' THEN value END) AS gap,
    max(CASE WHEN measure = 'met' THEN value END) AS met
  FROM strata.ops.evaluation_result
  WHERE scorer = 'benchmark' AND segment_kind = 'kind' AND public_from BETWEEN :date_from AND :date_to
  GROUP BY run_id, segment
)
SELECT
  run_id,
  CAST(ran_at AS DATE) AS run_on,
  kind_key,
  share,
  target AS target_share,
  met,
  CASE kind_key WHEN 'sql' THEN 1 WHEN 'documents' THEN 2 WHEN 'estimates' THEN 3 WHEN 'must_refuse' THEN 4 ELSE 5 END
    AS position,
  :benchmark_kind_label__kind_key AS kind,
  passed,
  questions,
  concat(CAST(CAST(round(100 * target) AS BIGINT) AS STRING), '%') AS target,
  CASE WHEN met = 1 THEN :copy__dash__ai__against__met
       ELSE replace(:copy__dash__ai__against__missedBy, '{gap}', CAST(CAST(round(100 * gap) AS BIGINT) AS STRING))
  END AS against
FROM kinds
ORDER BY ran_at DESC, position
