-- The newest run of one kind on one package, for one person only (CLAUDE.md rule 8: pasted text is read only for
-- its owner). A comparison writes a running row when the text is saved and a second row with the same check_id
-- when it ends, so of two rows written in the same moment the ended one is newer. Written without QUALIFY, so it
-- runs on Lakebase's Postgres as on DuckDB (src/strata/appstate).
SELECT check_id, owner_id, package_key, kind, pasted_text, status, result, comparables_signature, records_through,
       created_at
FROM (
  SELECT c.*, row_number() OVER (ORDER BY c.created_at DESC, CASE WHEN c.status = 'running' THEN 1 ELSE 0 END,
                                          c.check_id DESC) AS newest
  FROM strata.app.criteria_checks AS c
  WHERE c.owner_id = :owner_id
    AND c.package_key = :package_key
    AND c.kind = :kind
) AS runs
WHERE newest = 1
