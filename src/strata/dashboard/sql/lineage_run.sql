-- Tile 24: the answer run the Run ID names, or the latest answer run when it is empty (the 45 brief, section 6.2), from
-- strata.ops.agent_runs (ticket 13) and its tool calls (strata.ops.tool_calls). A run that read a private upload
-- shows no question. A Run ID that matches nothing gives no row, and the text above says what that means.
WITH chosen AS (
  SELECT r.run_id, r.finished_at, r.view AS view_key, r.question, r.sentences_kept, r.sentences_removed
  FROM strata.ops.agent_runs AS r
  WHERE r.run_id = CASE WHEN :run_id = '' THEN (
      SELECT max_by(n.run_id, n.finished_at) FROM strata.ops.agent_runs AS n
    ) ELSE :run_id END
),
counted AS (
  SELECT
    c.run_id,
    c.finished_at,
    c.view_key,
    c.question,
    c.sentences_kept,
    c.sentences_removed,
    count(t.call_order) AS tool_calls,
    coalesce(max(CASE WHEN t.private_upload THEN 1 ELSE 0 END), 0) AS private_upload
  FROM chosen AS c
  LEFT JOIN strata.ops.tool_calls AS t ON t.run_id = c.run_id
  GROUP BY c.run_id, c.finished_at, c.view_key, c.question, c.sentences_kept, c.sentences_removed
)
SELECT
  run_id,
  finished_at AS asked,
  :view_label__view_key AS view,
  CASE WHEN private_upload = 1 THEN :copy__dash__gov__privateQuestion ELSE question END AS question,
  tool_calls,
  sentences_kept,
  sentences_removed
FROM counted
