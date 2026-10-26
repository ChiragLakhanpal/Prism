-- Tile 15: the sentences the verifier removed from answers in the dates chosen, by the label of the reason it gave
-- first (copy.dash.ai.removed), largest first, from strata.ops.answer_removals beside each run in
-- strata.ops.agent_runs (the run log; ticket 45). Codes that share a label count together.
WITH removed AS (
  SELECT a.reason
  FROM strata.ops.answer_removals AS a
  JOIN strata.ops.agent_runs AS r ON r.run_id = a.run_id
  WHERE r.status = 'answered' AND r.public_from BETWEEN :date_from AND :date_to
),
labelled AS (
  SELECT :removed_label__reason AS reason_label
  FROM removed
)
SELECT reason_label AS reason, count(*) AS sentences
FROM labelled
GROUP BY reason_label
ORDER BY sentences DESC, reason
