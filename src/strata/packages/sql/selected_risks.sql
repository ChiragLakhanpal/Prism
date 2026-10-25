-- The risks a viewer has selected now for one package's PPSD (ticket 30), in the order they were first
-- selected, then by key.
SELECT r.risk_key
FROM strata.app.risk_selections AS r
WHERE r.viewer_id = :viewer_id
  AND r.package_kind = :package_kind
  AND r.package_key = :package_key
  AND r.selected
ORDER BY r.public_from, r.risk_key
