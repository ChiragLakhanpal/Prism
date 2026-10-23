-- The data-freshness stamp (the 06 design brief, "The freshness stamp"): the earliest day on
-- which a daily source was last loaded, so the stamp never claims more freshness than the
-- stalest daily source.
--
-- It reads each daily source's fresh_fetched measure, which the nightly job's measure_data_readiness
-- task writes per source and country: the day of the last fetch that loaded pages whose records
-- reached silver. A run that loads nothing writes no such row, so ticket 04's runs, which record
-- each task while loading nothing, never light the stamp. Only the newest measurement of each
-- source and country counts. With no row, the result is NULL: no data loaded yet.
--
-- A daily source that has no fresh_fetched measure yet, such as documents, is not counted.
-- :cadence is "daily", the source registry's word, which the measure keeps in its detail column.
WITH latest AS (
  SELECT source, subject, max_by(as_of, measured_at) AS loaded_on
  FROM strata.ops.data_readiness
  WHERE kind = 'fresh'
    AND measure = 'fresh_fetched'
    AND detail = :cadence
  GROUP BY source, subject
)
SELECT min(loaded_on) AS data_through
FROM latest
