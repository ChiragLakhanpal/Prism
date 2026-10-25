-- The plan date a viewer chose for a package, if any (ticket 26): middle or eight_in_ten.
SELECT c.choice, c.saved_at
FROM strata.app.plan_date_choices AS c
WHERE c.viewer_id = :viewer_id
  AND c.package_kind = :package_kind
  AND c.package_key = :package_key
