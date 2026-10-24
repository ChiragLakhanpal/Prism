-- A viewer opened a source in the evidence drawer (ticket 14): its row in strata.ops.evidence_opened is
-- made the first time and updated every time after, so each viewer has one row per evidence id.
MERGE INTO strata.ops.evidence_opened AS t
USING (
  SELECT
    :viewer_id AS viewer_id,
    :evidence_id AS evidence_id,
    CAST(:opened_at AS TIMESTAMP) AS opened_at,
    :run_id AS run_id,
    :route AS route
) AS s
ON t.viewer_id = s.viewer_id AND t.evidence_id = s.evidence_id
WHEN MATCHED THEN UPDATE SET
  last_opened_at = s.opened_at,
  times_opened = t.times_opened + 1,
  last_run_id = s.run_id,
  last_route = s.route
WHEN NOT MATCHED THEN INSERT
  (viewer_id, evidence_id, first_opened_at, last_opened_at, times_opened, last_run_id, last_route, public_from)
  VALUES (s.viewer_id, s.evidence_id, s.opened_at, s.opened_at, 1, s.run_id, s.route, CAST(s.opened_at AS DATE))
