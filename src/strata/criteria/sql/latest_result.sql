-- The newest run of one kind on one package that finished with a result, for one person only (CLAUDE.md rule 8).
-- When the newest comparison failed after its text was saved, the section still shows the last table that
-- finished, under the newest text. Written without QUALIFY, so it runs on Lakebase's Postgres as on DuckDB.
SELECT check_id, owner_id, package_key, kind, pasted_text, status, result, comparables_signature, records_through,
       created_at
FROM (
  SELECT c.*, row_number() OVER (ORDER BY c.created_at DESC, c.check_id DESC) AS newest
  FROM strata.app.criteria_checks AS c
  WHERE c.owner_id = :owner_id
    AND c.package_key = :package_key
    AND c.kind = :kind
    AND c.status IN ('ready', 'refused')
) AS runs
WHERE newest = 1
