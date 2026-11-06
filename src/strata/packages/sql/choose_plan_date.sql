-- A viewer chose the plan date Prism drafts with for a package (ticket 26): its row in
-- strata.app.plan_date_choices is made the first time and changed every time after. Nothing is deleted.
MERGE INTO strata.app.plan_date_choices AS t
USING (
  SELECT
    :viewer_id AS viewer_id,
    :package_kind AS package_kind,
    :package_key AS package_key,
    :choice AS choice,
    CAST(:saved_at AS TIMESTAMP) AS saved_at
) AS s
ON t.viewer_id = s.viewer_id AND t.package_kind = s.package_kind AND t.package_key = s.package_key
WHEN MATCHED THEN UPDATE SET
  choice = s.choice,
  saved_at = s.saved_at
WHEN NOT MATCHED THEN INSERT
  (viewer_id, package_kind, package_key, choice, saved_at, public_from)
  VALUES (s.viewer_id, s.package_kind, s.package_key, s.choice, s.saved_at, CAST(s.saved_at AS DATE))
