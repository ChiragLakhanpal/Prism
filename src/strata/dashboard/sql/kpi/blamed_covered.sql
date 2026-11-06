-- KPI blamed_covered (config/kpis.toml), the knowledge loop's lagging indicator, with the rest of each release's
-- hindsight test (tile 27): the blamed risks, how many a lesson covered at approval, how many were shown when
-- covered, hindsight recall (coverage times shown-when-covered, stored by ticket 34 with its counts), and what the
-- checklist caught, from strata.ops.evaluation_result (scorer hindsight_test, segment_kind release). Projects exposed
-- to Prism were left out by the test itself. Newest first, in the dates chosen.
WITH releases AS (
  SELECT
    run_id,
    segment AS release_name,
    max(ran_at) AS ran_at,
    CAST(max(CASE WHEN measure = 'projects' THEN value END) AS BIGINT) AS projects,
    CAST(max(CASE WHEN measure = 'blamed' THEN value END) AS BIGINT) AS blamed,
    CAST(max(CASE WHEN measure = 'covered' THEN value END) AS BIGINT) AS covered,
    max(CASE WHEN measure = 'shown_when_covered' THEN value_text END) AS shown_when_covered,
    max(CASE WHEN measure = 'hindsight_recall' THEN value_text END) AS recall_counts,
    max(CASE WHEN measure = 'hindsight_recall' THEN value END) AS recall,
    CAST(max(CASE WHEN measure = 'checklist_caught' THEN value END) AS BIGINT) AS checklist_caught
  FROM strata.ops.evaluation_result
  WHERE scorer = 'hindsight_test' AND segment_kind = 'release' AND public_from BETWEEN :date_from AND :date_to
  GROUP BY run_id, segment
)
SELECT
  release_name,
  CAST(ran_at AS DATE) AS ran_on,
  projects,
  blamed,
  covered,
  covered AS numerator,
  blamed AS denominator,
  shown_when_covered,
  recall,
  CASE
    WHEN blamed >= :threshold__data_readiness__fewest_for_a_percentage AND recall IS NOT NULL
      THEN replace(replace(:copy__dash__ratio__percent, '{count}', recall_counts), '{pct}',
                   CAST(CAST(round(100 * recall) AS BIGINT) AS STRING))
    WHEN blamed >= :threshold__data_readiness__fewest_for_a_share AND recall > 0 AND recall < 1
      THEN replace(replace(:copy__dash__ratio__inTen, '{count}', recall_counts), '{in10}',
                   CAST(CAST(round(10 * recall) AS BIGINT) AS STRING))
    ELSE recall_counts
  END AS hindsight_recall,
  checklist_caught
FROM releases
ORDER BY ran_at DESC
