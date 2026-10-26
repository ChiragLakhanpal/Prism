-- Tile 27: the answer runs in the dates chosen, newest first, with their run IDs to paste into Run ID
-- (strata.ops.agent_runs and strata.ops.tool_calls). No question shows here, so no upload's words can.
WITH counted AS (
  SELECT r.finished_at, r.run_id, r.view AS view_key, r.sentences_removed, count(t.call_order) AS tool_calls
  FROM strata.ops.agent_runs AS r
  LEFT JOIN strata.ops.tool_calls AS t ON t.run_id = r.run_id
  WHERE r.public_from BETWEEN :date_from AND :date_to
  GROUP BY r.finished_at, r.run_id, r.view, r.sentences_removed
)
SELECT finished_at AS asked, run_id, :view_label__view_key AS view, tool_calls, sentences_removed
FROM counted
ORDER BY finished_at DESC
