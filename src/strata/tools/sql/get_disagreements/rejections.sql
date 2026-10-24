-- get_disagreements: how many assertions the latest run read from a project's reports and left out, by
-- reason, counting only reports public on the as-of date (ADR 0002).
SELECT
  r.reason,
  count(*) AS rejected
FROM strata.ops.assertion_rejections AS r
WHERE r.project_id = :project_id
  AND r.public_from <= :as_of
GROUP BY r.reason
ORDER BY r.reason
