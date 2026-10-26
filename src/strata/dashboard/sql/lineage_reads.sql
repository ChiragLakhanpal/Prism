-- Tile 26: the tables the tool calls of the chosen answer run read (strata.ops.tool_call_reads; ticket 45), the step
-- from the answer back to its sources: each table, the Delta version the call read where the workspace keeps one,
-- the night of the nightly run that last wrote it before the call (the newest quality check of that table by then,
-- strata.ops.quality_checks, since a task checks the tables it writes when it finishes; or, for a table no check
-- names, the newest nightly run by then), and the source registry's names for what the tool reads.
WITH chosen AS (
  SELECT r.run_id, r.call_order, r.tool, r.table_name, r.version_read, r.sources, r.read_at
  FROM strata.ops.tool_call_reads AS r
  WHERE r.run_id = CASE WHEN :run_id = '' THEN (
      SELECT max_by(n.run_id, n.finished_at) FROM strata.ops.agent_runs AS n
    ) ELSE :run_id END
)
SELECT
  c.call_order,
  replace(replace(:copy__dash__gov__callName, '{order}', CAST(c.call_order AS STRING)), '{tool}', c.tool) AS call,
  c.table_name,
  c.version_read,
  coalesce(
    (SELECT max(q.night) FROM strata.ops.quality_checks AS q
     WHERE q.table_name = c.table_name AND q.checked_at <= c.read_at),
    (SELECT max(q.night) FROM strata.ops.quality_checks AS q WHERE q.checked_at <= c.read_at)
  ) AS written_by,
  c.sources
FROM chosen AS c
ORDER BY c.call_order, c.table_name
