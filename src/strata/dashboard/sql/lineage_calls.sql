-- Tile 25: the tool calls of the answer run the Run ID names, or of the latest answer run when it is empty, in call
-- order (strata.ops.tool_calls, which the run log writes; ticket 45). An input that named a private upload reads
-- "a private upload" there already.
SELECT t.call_order, t.tool, t.inputs, t.rows_returned, t.took_ms, t.evidence_ids
FROM strata.ops.tool_calls AS t
WHERE t.run_id = CASE WHEN :run_id = '' THEN (
    SELECT max_by(n.run_id, n.finished_at) FROM strata.ops.agent_runs AS n
  ) ELSE :run_id END
ORDER BY t.call_order
