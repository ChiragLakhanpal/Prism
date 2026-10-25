-- Promotion (ticket 44): the challenger's first night in shadow, from which its quarter in shadow is counted.
SELECT min(s.public_from) AS started_on, min(s.public_from) AS public_from
FROM strata.ops.time_estimate_shadow AS s
WHERE s.model = :model
  AND s.model_version = :version
