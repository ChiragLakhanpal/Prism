-- KPI precision_recall (config/kpis.toml), the retrieval loop's lagging indicator: precision at 10, recall at 20 and
-- nDCG at 10 for each query set of each evaluation run in the dates chosen, on all its queries (query_set) and on the
-- queries held out of tuning (held_out), as the replay harness stored them (strata.ops.evaluation_result, scorer
-- retrieval_evaluation; ticket 32). The chart's columns are empty for a held-out set of fewer than
-- retrieval.min_opened queries, so no point rests on a few. Newest first.
WITH runs AS (
  SELECT
    run_id,
    segment_kind,
    segment AS query_set_key,
    max(ran_at) AS ran_at,
    CAST(max(CASE WHEN measure = 'queries' THEN value END) AS BIGINT) AS queries,
    max(CASE WHEN measure LIKE 'precision_at_%' THEN value END) AS precision_at_10,
    max(CASE WHEN measure LIKE 'recall_at_%' THEN value END) AS recall_at_20,
    max(CASE WHEN measure LIKE 'ndcg_at_%' THEN value END) AS ndcg_at_10
  FROM strata.ops.evaluation_result
  WHERE scorer = 'retrieval_evaluation' AND segment_kind IN ('query_set', 'held_out')
    AND public_from BETWEEN :date_from AND :date_to
  GROUP BY run_id, segment_kind, segment
)
SELECT
  run_id,
  CAST(ran_at AS DATE) AS run_on,
  segment_kind,
  query_set_key,
  :query_set_label__query_set_key AS query_set,
  queries,
  precision_at_10,
  recall_at_20,
  ndcg_at_10,
  CASE WHEN segment_kind = 'held_out' AND queries >= :threshold__retrieval__min_opened THEN precision_at_10 END
    AS held_out_precision,
  CASE WHEN segment_kind = 'held_out' AND queries >= :threshold__retrieval__min_opened THEN recall_at_20 END
    AS held_out_recall
FROM runs
ORDER BY ran_at DESC, segment_kind, query_set_key
