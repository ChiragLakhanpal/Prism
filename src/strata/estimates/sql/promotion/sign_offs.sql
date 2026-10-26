-- Promotion (ticket 44): every sign-off given on one version of a model, oldest first.
SELECT o.role, o.signed_by, o.signed_at, o.public_from
FROM strata.ops.model_signoffs AS o
WHERE o.model = :model
  AND o.version = :version
ORDER BY o.signed_at, o.role
