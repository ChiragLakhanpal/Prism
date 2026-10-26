-- KPI sentences_removed (config/kpis.toml): the sentences the verifier removed from answers in the dates chosen, out
-- of the sentences the answers wrote, as each run's row in strata.ops.agent_runs counts them (ticket 13). Always one
-- row: "None yet" before the first answer.
WITH counted AS (
  SELECT sum(sentences_removed) AS removed, sum(sentences_written) AS written
  FROM strata.ops.agent_runs
  WHERE status = 'answered' AND public_from BETWEEN :date_from AND :date_to
)
SELECT
  coalesce(removed, 0) AS numerator,
  coalesce(written, 0) AS denominator,
  coalesce(removed, 0) AS value,
  CASE
    WHEN coalesce(written, 0) = 0 THEN :copy__kpi__display__none
    ELSE replace(replace(:copy__kpi__display__share, '{n}', format_number(coalesce(removed, 0), 0)), '{d}',
                 format_number(written, 0))
  END AS display
FROM counted
